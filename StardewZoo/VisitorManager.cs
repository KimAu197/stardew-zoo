using Microsoft.Xna.Framework;
using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewValley;
using StardewValley.Menus;
using StardewValley.Pathfinding;

namespace StardewZoo;

/// <summary>Temporary visitor NPCs that tour the zoo loop, chat with the player, and despawn at night / before save.</summary>
internal sealed class VisitorManager
{
    private const string NamePrefix = "StardewZooVisitor_";
    private const int LeaveDelayTicks = 150;
    private const int EmoteCooldownTicks = 60 * 25;

    /// <summary>Vanilla non-villager sheets with a full 16x32 four-direction walk cycle in rows 0-3.</summary>
    private static readonly string[] Textures =
    {
        "Characters/SafariGuy",
        "Characters/Marcello",
        "Characters/Morris",
        "Characters/Birdie"
    };

    private sealed class VisitorState
    {
        public VisitorPersona Persona;
        public int Stars = 3;
        public string? Favourite;
        public int TalkCount;
        public readonly HashSet<string> UsedLines = new();
        public bool Talking;
        public PathFindController? PausedController;
        public int NextEmoteTick;
        public int LeaveAtTick = -1;
    }

    private int nextId;
    private int projectedVisitors;
    private readonly IMonitor monitor;
    private readonly ITranslationHelper translation;
    private readonly IInputHelper input;
    private readonly Func<ModConfig> config;
    private readonly Func<ZooSaveData> save;
    private readonly Dictionary<string, VisitorState> states = new();

    public VisitorManager(IModHelper helper, IMonitor monitor, Func<ModConfig> config, Func<ZooSaveData> save)
    {
        this.monitor = monitor;
        this.translation = helper.Translation;
        this.input = helper.Input;
        this.config = config;
        this.save = save;
        helper.Events.Input.ButtonPressed += this.OnButtonPressed;
        helper.Events.GameLoop.UpdateTicked += this.OnUpdateTicked;
    }

    public void SetProjection(int visitors) => this.projectedVisitors = visitors;

    public void TrySpawn()
    {
        if (!Context.IsMainPlayer || !Context.IsWorldReady)
            return;
        int hour = Game1.timeOfDay;
        if (hour < 800 || hour >= 1800 || this.projectedVisitors <= 0)
            return;

        Utility.ForEachBuilding(building =>
        {
            if (!ZooIds.IsZoo(building.buildingType.Value) || building.isUnderConstruction())
                return true;
            if (building.GetIndoors() is not AnimalHouse house)
                return true;

            int cap = Math.Clamp(this.projectedVisitors / 8, 1, 6);
            int current = house.characters.Count(IsVisitor);
            if (current >= cap)
                return true;

            this.SpawnOne(house);
            return true;
        });
    }

    public void RemoveAll()
    {
        Utility.ForEachLocation(location =>
        {
            for (int i = location.characters.Count - 1; i >= 0; i--)
            {
                if (IsVisitor(location.characters[i]))
                    location.characters.RemoveAt(i);
            }
            return true;
        });
        this.states.Clear();
    }

    private void SpawnOne(AnimalHouse location)
    {
        string asset = PickTexture(location);
        var sprite = new AnimatedSprite(asset, 0, 16, 32);
        var npc = new NPC(sprite, new Vector2(18 * Game1.tileSize, 28 * Game1.tileSize), 0, NamePrefix + this.nextId)
        {
            Breather = false,
            HideShadow = false,
            displayName = this.translation.Get("visitor.name"),
            farmerPassesThrough = true,
            Speed = 2,
            // No Data/Characters entry: stop vanilla from looking up Portraits/<name>, Characters/<name>, or dialogue files.
            portraitOverridden = true,
            spriteOverridden = true,
            AllowDynamicAppearance = false,
            TemporaryDialogue = new Stack<Dialogue>()
        };
        npc.collidesWithOtherCharacters.Value = false;
        npc.forceOneTileWide.Value = true;
        this.nextId++;

        VisitorPersona persona = VisitorChat.PersonaFor(asset);
        List<string> animals = AnimalTypes(location);
        int fair = ZooIncome.FairValue(new ZooSnapshot(location.ParentBuilding?.buildingType.Value ?? ZooIds.Zoo, animals), this.config());
        double ratio = VisitorChat.PriceRatio(this.config().TicketPrice, fair);
        this.states[npc.Name] = new VisitorState
        {
            Persona = persona,
            Stars = ZooIncome.RateVisit(animals.Count, ZooHabitats.CountFilled(animals), ratio, Random.Shared).Stars,
            Favourite = VisitorChat.PickFavourite(persona, Random.Shared),
            NextEmoteTick = Game1.ticks + Game1.random.Next(EmoteCooldownTicks)
        };

        location.characters.Add(npc);
        this.WalkLoop(npc, location, 0);
    }

    private void WalkLoop(NPC npc, GameLocation location, int waypoint)
    {
        if (waypoint >= ZooHabitats.VisitorLoop.Count)
        {
            this.BeginLeaving(npc, location);
            return;
        }

        (int x, int y) = ZooHabitats.VisitorLoop[waypoint];
        npc.controller = new PathFindController(
            npc,
            location,
            new Point(x, y),
            0,
            (character, loc) =>
            {
                if (character is NPC visitor && loc != null)
                    this.WalkLoop(visitor, loc, waypoint + 1);
            }
        );
        if (npc.controller?.pathToEndPoint == null || npc.controller.pathToEndPoint.Count == 0)
        {
            npc.Position = new Vector2(x * Game1.tileSize, y * Game1.tileSize);
            this.WalkLoop(npc, location, waypoint + 1);
        }
    }

    /// <summary>At the exit the visitor says their verdict (matching their review stars) and leaves a moment later.</summary>
    private void BeginLeaving(NPC npc, GameLocation location)
    {
        npc.controller = null;
        if (!this.states.TryGetValue(npc.Name, out VisitorState? state))
        {
            location.characters.Remove(npc);
            return;
        }

        state.LeaveAtTick = Game1.ticks + LeaveDelayTicks;
        if (Game1.currentLocation == location)
        {
            ChatLine line = VisitorChat.LeaveLine(state.Stars, Game1.random);
            npc.showTextAboveHead(this.Translate(line, state));
        }
    }

    private void OnButtonPressed(object? sender, ButtonPressedEventArgs e)
    {
        if (!Context.IsPlayerFree || !e.Button.IsActionButton() || Game1.currentLocation is not { } location)
            return;

        NPC? visitor = FindVisitorAt(location, e.Cursor);
        if (visitor == null)
            return;

        this.input.Suppress(e.Button);
        this.Talk(visitor, location);
    }

    /// <summary>Mirrors vanilla targeting: the hovered tile if it's next to the player, otherwise the grab tile.</summary>
    private static NPC? FindVisitorAt(GameLocation location, ICursorPosition cursor)
    {
        Vector2 tile = cursor.Tile;
        bool mouseTarget = Game1.wasMouseVisibleThisFrame
            && Game1.mouseCursorTransparency != 0f
            && Utility.tileWithinRadiusOfPlayer((int)tile.X, (int)tile.Y, 1, Game1.player);
        if (!mouseTarget)
            tile = Game1.player.GetGrabTile();

        // Characters are two tiles tall, so the tile above their feet (their head) counts too.
        var targets = new[] { tile, tile + new Vector2(0, 1) };
        foreach (Vector2 target in targets)
        {
            var area = new Rectangle((int)target.X * Game1.tileSize, (int)target.Y * Game1.tileSize, Game1.tileSize, Game1.tileSize);
            NPC? hit = location.characters.FirstOrDefault(npc => IsVisitor(npc) && npc.GetBoundingBox().Intersects(area));
            if (hit != null)
                return hit;
        }
        return null;
    }

    private void Talk(NPC npc, GameLocation location)
    {
        if (!this.states.TryGetValue(npc.Name, out VisitorState? state))
            this.states[npc.Name] = state = new VisitorState { Persona = VisitorChat.PersonaFor(npc.Sprite?.textureName.Value) };

        VisitorChatSnapshot snapshot = this.BuildSnapshot(npc, location, state);
        ChatLine line = VisitorChat.Next(snapshot, state.UsedLines, Game1.random);
        state.TalkCount++;

        if (!state.Talking)
        {
            state.PausedController = npc.controller;
            npc.controller = null;
            state.Talking = true;
        }
        npc.Halt();
        npc.faceGeneralDirection(Game1.player.getStandingPosition(), 0, false);

        string text = this.Translate(line, state);
        if (Game1.options.showPortraits)
            text = this.translation.Get("visitor.speech", new { name = npc.displayName, line = text });
        npc.CurrentDialogue.Clear();
        Game1.DrawDialogue(new Dialogue(npc, null, text));
    }

    private VisitorChatSnapshot BuildSnapshot(NPC npc, GameLocation location, VisitorState state)
    {
        ModConfig config = this.config();
        ZooSaveData save = this.save();
        var animals = location is AnimalHouse house ? AnimalTypes(house) : new List<string>();
        string building = location.ParentBuilding?.buildingType.Value ?? ZooIds.Zoo;
        var species = animals.Distinct().ToList();
        var filled = species.Select(type => ZooHabitats.AnimalHabitat.GetValueOrDefault(type)).Where(id => id != null).ToHashSet();
        var empty = ZooHabitats.All.Where(h => !filled.Contains(h.Id)).ToList();

        Point at = npc.TilePoint;
        string? nearestEmpty = empty
            .Select(h => (h.Id, Distance: TileDistance(at, h)))
            .Where(h => h.Distance <= 4)
            .OrderBy(h => h.Distance)
            .Select(h => h.Id)
            .FirstOrDefault();
        string? nearestSpecies = location.animals.Values
            .Select(animal => (Type: animal.type.Value, Distance: Vector2.Distance(animal.Tile, npc.Tile)))
            .Where(a => a.Distance <= 10)
            .OrderBy(a => a.Distance)
            .Select(a => a.Type)
            .FirstOrDefault();

        return new VisitorChatSnapshot
        {
            TicketPrice = config.TicketPrice,
            FairValue = ZooIncome.FairValue(new ZooSnapshot(building, animals), config),
            AverageRating = ZooIncome.AverageRating(save.Reviews),
            ReviewCount = save.Reviews.Count,
            SpeciesPresent = species,
            NearestSpecies = nearestSpecies,
            FavouriteSpecies = state.Favourite,
            EmptyHabitats = empty.Select(h => h.Id).ToList(),
            NearestEmptyHabitat = nearestEmpty,
            TimeOfDay = Game1.timeOfDay,
            Weather = CurrentWeather(),
            Persona = state.Persona,
            Stars = state.Stars,
            TalkCount = state.TalkCount
        };
    }

    private string Translate(ChatLine line, VisitorState state)
    {
        string animal = line.Species != null ? this.translation.Get("visitor.species." + ZooIds.ShortName(line.Species)) : "";
        string habitat = line.Habitat != null ? this.translation.Get("visitor.habitat." + line.Habitat) : "";
        ModConfig config = this.config();
        return this.translation.Get(line.Key, new
        {
            price = config.TicketPrice,
            rating = ZooIncome.AverageRating(this.save().Reviews).ToString("0.0"),
            stars = state.Stars,
            farmer = DialogueSafe(Game1.player.displayName),
            farm = DialogueSafe(Game1.player.farmName.Value),
            animal,
            habitat
        });
    }

    private void OnUpdateTicked(object? sender, UpdateTickedEventArgs e)
    {
        if (!Context.IsWorldReady || this.states.Count == 0)
            return;

        bool dialogueOpen = Game1.activeClickableMenu is DialogueBox;
        bool checkEmotes = e.IsMultipleOf(30) && Game1.currentLocation is AnimalHouse;
        foreach ((string name, VisitorState state) in this.states.ToList())
        {
            if (state.Talking && !dialogueOpen)
                this.Resume(name, state);
            if (state.LeaveAtTick >= 0 && Game1.ticks >= state.LeaveAtTick && !state.Talking)
                this.Remove(name);
        }

        if (checkEmotes)
            this.UpdateEmotes(Game1.currentLocation!);
    }

    private void Resume(string name, VisitorState state)
    {
        state.Talking = false;
        NPC? npc = FindVisitor(name, out _);
        if (npc != null && npc.controller == null && state.LeaveAtTick < 0)
            npc.controller = state.PausedController;
        state.PausedController = null;
    }

    private void Remove(string name)
    {
        this.states.Remove(name);
        NPC? npc = FindVisitor(name, out GameLocation? location);
        if (npc != null)
            location!.characters.Remove(npc);
    }

    /// <summary>Now and then a visitor reacts: a heart near their favourite animal, or a sigh if they're unhappy.</summary>
    private void UpdateEmotes(GameLocation location)
    {
        foreach (NPC npc in location.characters.Where(IsVisitor))
        {
            if (!this.states.TryGetValue(npc.Name, out VisitorState? state) || state.Talking || npc.IsEmoting || Game1.ticks < state.NextEmoteTick)
                continue;

            VisitorMood mood = VisitorChat.MoodFor(state.Stars);
            bool nearFavourite = location.animals.Values.Any(a => a.type.Value == state.Favourite && Vector2.Distance(a.Tile, npc.Tile) <= 4);
            int emote = -1;
            if (nearFavourite && mood != VisitorMood.Unhappy)
                emote = Character.heartEmote;
            else if (mood == VisitorMood.Unhappy && Game1.random.NextDouble() < 0.08)
                emote = Game1.random.Next(2) == 0 ? Character.sadEmote : Character.angryEmote;
            else if (mood == VisitorMood.Happy && Game1.random.NextDouble() < 0.04)
                emote = Character.happyEmote;

            if (emote < 0)
                continue;
            npc.doEmote(emote);
            state.NextEmoteTick = Game1.ticks + EmoteCooldownTicks + Game1.random.Next(EmoteCooldownTicks);
        }
    }

    private static NPC? FindVisitor(string name, out GameLocation? location)
    {
        NPC? found = null;
        GameLocation? foundIn = null;
        Utility.ForEachLocation(loc =>
        {
            found = loc.characters.FirstOrDefault(npc => npc.Name == name);
            foundIn = loc;
            return found == null;
        });
        location = found != null ? foundIn : null;
        return found;
    }

    private static List<string> AnimalTypes(AnimalHouse house)
    {
        var types = new List<string>();
        foreach (long id in house.animalsThatLiveHere)
        {
            FarmAnimal? animal = Utility.getAnimal(id);
            if (animal != null)
                types.Add(animal.type.Value);
        }
        return types;
    }

    private static int TileDistance(Point tile, HabitatRect rect)
    {
        (int x, int y) = rect.Clamp(tile.X, tile.Y);
        return Math.Max(Math.Abs(tile.X - x), Math.Abs(tile.Y - y));
    }

    private static VisitorWeather CurrentWeather()
    {
        if (Game1.isLightning)
            return VisitorWeather.Storm;
        if (Game1.isSnowing)
            return VisitorWeather.Snow;
        if (Game1.isRaining)
            return VisitorWeather.Rain;
        if (Game1.isDebrisWeather)
            return VisitorWeather.Wind;
        return VisitorWeather.Sunny;
    }

    /// <summary>Player-entered names could contain characters the dialogue parser treats as commands.</summary>
    private static string DialogueSafe(string? text) =>
        new((text ?? "").Where(c => "#$^%*@[]<>".IndexOf(c) < 0).ToArray());

    /// <summary>Prefers the sheet fewest current visitors here are using, so the same face rarely appears twice.</summary>
    private static string PickTexture(GameLocation location)
    {
        var inUse = location.characters
            .Where(IsVisitor)
            .Select(npc => npc.Sprite?.textureName.Value)
            .ToList();
        return Textures
            .OrderBy(texture => inUse.Count(used => used == texture))
            .ThenBy(_ => Game1.random.Next())
            .First();
    }

    private static bool IsVisitor(NPC? npc) => npc?.Name?.StartsWith(NamePrefix, StringComparison.Ordinal) == true;
}
