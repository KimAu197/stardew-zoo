using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewValley;
using xTile.Layers;
using xTile.Tiles;

namespace StardewZoo;

/// <summary>
/// Gives zoo animals species-specific movement (flying, perching, climbing, swimming laps, heavy steps).
/// The host drives positions; airborne/climbing animals are hidden from vanilla drawing (their sprite is pushed
/// off-screen via <see cref="Character.yJumpOffset"/>, which keeps the ground shadow) and redrawn here, elevated.
/// </summary>
internal sealed class AnimalMovement
{
    private const string AnimalTypePrefix = "StardewZoo.";
    private const string AssetPrefix = "Mods/StardewZoo/";
    private const int HideOffset = -40000;
    private const int VanillaStepInterval = 175;
    private const int StompSoundRadius = 6 * 64;
    private const int StompShakeRadius = 4 * 64;

    /// <summary>Back-layer tile indexes of the animated pond water on spring_outdoorsTileSheet (see tools/make_map.py).</summary>
    private static readonly HashSet<int> WaterTileIndexes = new() { 1229, 1230, 1231, 1306, 1249, 1274, 1322, 1324 };

    private static readonly HashSet<string> Waders = new() { ZooIds.Flamingo, ZooIds.NightHeron };

    private readonly IModHelper helper;
    private readonly ModConfig config;
    private readonly Dictionary<long, Entry> entries = new();
    private readonly Dictionary<string, BrainWorld> worlds = new();
    private readonly Dictionary<string, Texture2D?> textures = new();
    private readonly Dictionary<string, HashSet<Point>> waterByPen = new();
    private readonly Dictionary<long, int> stepFrames = new();
    private GameLocation? location;
    private int shakeTicks;
    private Point shakeApplied;

    public AnimalMovement(IModHelper helper, ModConfig config)
    {
        this.helper = helper;
        this.config = config;
        helper.Events.GameLoop.UpdateTicking += this.OnUpdateTicking;
        helper.Events.GameLoop.UpdateTicked += this.OnUpdateTicked;
        helper.Events.GameLoop.DayStarted += (_, _) => this.Clear();
        helper.Events.GameLoop.ReturnedToTitle += (_, _) => this.Clear();
        helper.Events.Display.RenderedWorld += this.OnRenderedWorld;
        helper.Events.Content.AssetsInvalidated += (_, _) => this.textures.Clear();
    }

    private sealed class Entry
    {
        public Entry(FarmAnimal animal, AnimalBrain brain, MoveProfile profile)
        {
            this.Animal = animal;
            this.Brain = brain;
            this.Profile = profile;
        }

        public FarmAnimal Animal { get; }
        public AnimalBrain Brain { get; }
        public MoveProfile Profile { get; }
        public BrainOutput Last { get; set; }
        public bool Controlling { get; set; }
        public bool Hidden { get; set; }
    }

    private void OnUpdateTicking(object? sender, UpdateTickingEventArgs e)
    {
        if (this.shakeApplied != Point.Zero)
        {
            Game1.viewport.X -= this.shakeApplied.X;
            Game1.viewport.Y -= this.shakeApplied.Y;
            this.shakeApplied = Point.Zero;
        }
    }

    private void OnUpdateTicked(object? sender, UpdateTickedEventArgs e)
    {
        if (!Context.IsWorldReady || Game1.currentLocation is not AnimalHouse house || !ZooIds.IsZoo(house.ParentBuilding?.buildingType.Value))
        {
            if (this.location != null)
                this.Clear();
            return;
        }
        if (!ReferenceEquals(house, this.location))
        {
            this.Clear();
            this.location = house;
        }
        if (!Context.IsMainPlayer || !this.config.AnimalMovementStyles)
            return;

        GameTime time = Game1.currentGameTime;
        double elapsed = Game1.shouldTimePass() ? time.ElapsedGameTime.TotalMilliseconds : 0;
        bool night = Game1.timeOfDay >= 1800;
        bool sleeping = Game1.timeOfDay >= 2000;
        var seen = new HashSet<long>();

        foreach (FarmAnimal animal in house.animals.Values)
        {
            string? type = animal.type.Value;
            if (type?.StartsWith(AnimalTypePrefix, StringComparison.Ordinal) != true || ZooHabitats.ForAnimal(type) is not HabitatRect pen)
                continue;

            MoveProfile profile = MoveProfiles.For(type);
            this.ApplyGroundTuning(animal, profile);
            if (profile.Style is MoveStyle.Default or MoveStyle.BigWalker && profile.SitsPerMinute <= 0)
            {
                if (type == ZooIds.Dinosaur)
                    this.CheckStomp(animal);
                continue;
            }

            long id = animal.myID.Value;
            seen.Add(id);
            if (!this.entries.TryGetValue(id, out Entry? entry) || !ReferenceEquals(entry.Animal, animal))
            {
                var brain = new AnimalBrain(profile, this.GetWorld(house, pen), new Random(unchecked((int)id) ^ Environment.TickCount));
                entry = new Entry(animal, brain, profile);
                this.entries[id] = entry;
            }

            Point center = animal.GetBoundingBox().Center;
            BrainOutput output = entry.Brain.Tick(new BrainInput(elapsed, center.X, center.Y, night, sleeping, animal.isBaby()));
            entry.Last = output;
            this.Apply(entry, output, time);
            if (profile.Style == MoveStyle.Swimmer || Waders.Contains(type))
                this.UpdateSwimming(entry, pen, sleeping);
        }

        foreach (long id in this.entries.Keys.Where(id => !seen.Contains(id)).ToList())
        {
            this.Release(this.entries[id]);
            this.entries.Remove(id);
        }

        if (this.shakeTicks > 0)
        {
            this.shakeTicks--;
            int dx = this.shakeTicks % 2 == 0 ? 2 : -2;
            int dy = this.shakeTicks % 3 == 0 ? 1 : 0;
            Game1.viewport.X += dx;
            Game1.viewport.Y += dy;
            this.shakeApplied = new Point(dx, dy);
        }
    }

    private void Apply(Entry entry, BrainOutput output, GameTime time)
    {
        FarmAnimal animal = entry.Animal;
        if (output.Controlled)
        {
            if (!entry.Controlling)
            {
                animal.Halt();
                animal.controller = null;
                animal.Sprite.CurrentAnimation = null;
                entry.Controlling = true;
            }
            animal.pauseTimer = Math.Max(animal.pauseTimer, 250);
            HabitatKeeper.SetGroundCenter(animal, output.X, output.Y);
            animal.FacingDirection = output.Facing;
            if (output.Pose == BrainPose.Walk)
                this.AnimateWalk(animal, output.Facing, time);
        }
        else if (entry.Controlling)
        {
            entry.Controlling = false;
            animal.pauseTimer = 0;
        }

        bool hide = output.Pose is BrainPose.Fly or BrainPose.Perch or BrainPose.Climb or BrainPose.Sit or BrainPose.Hang;
        if (hide)
        {
            animal.yJumpOffset = HideOffset;
            animal.yJumpVelocity = 0;
            entry.Hidden = true;
        }
        else if (entry.Hidden)
        {
            animal.yJumpOffset = 0;
            animal.yJumpVelocity = 0;
            entry.Hidden = false;
        }

        if (output.SitMs > 0)
            StartSit(animal, output.SitMs);
    }

    private void AnimateWalk(FarmAnimal animal, int facing, GameTime time)
    {
        AnimatedSprite sprite = animal.Sprite;
        sprite.loop = true;
        switch (facing)
        {
            case 0:
                sprite.AnimateUp(time);
                break;
            case 2:
                sprite.AnimateDown(time);
                break;
            default:
                sprite.AnimateRight(time);
                break;
        }
        ApplySwimOffset(animal);
    }

    private static void StartSit(FarmAnimal animal, int durationMs)
    {
        animal.Halt();
        animal.controller = null;
        var frames = new List<FarmerSprite.AnimationFrame>();
        int[] eat = { 16, 17, 18, 19 };
        for (int elapsed = 0; elapsed < durationMs; elapsed += 1200)
        {
            foreach (int frame in eat)
                frames.Add(new FarmerSprite.AnimationFrame(frame, 300));
        }
        animal.Sprite.loop = false;
        animal.Sprite.setCurrentAnimation(frames);
    }

    private void UpdateSwimming(Entry entry, HabitatRect pen, bool sleeping)
    {
        FarmAnimal animal = entry.Animal;
        bool swim = !sleeping && !entry.Hidden && this.GetWater(pen).Contains(animal.TilePoint);
        if (animal.isSwimming.Value != swim)
        {
            animal.isSwimming.Value = swim;
            animal.Sprite.UpdateSourceRect();
            ApplySwimOffset(animal);
        }
    }

    private static void ApplySwimOffset(FarmAnimal animal)
    {
        if (!animal.IsActuallySwimming())
            return;
        Rectangle source = animal.Sprite.SourceRect;
        source.Offset(animal.GetAnimalData()?.SwimOffset ?? new Point(0, 112));
        animal.Sprite.SourceRect = source;
    }

    private void ApplyGroundTuning(FarmAnimal animal, MoveProfile profile)
    {
        if (profile.GroundSpeed != 2 && animal.speed != profile.GroundSpeed)
            animal.speed = profile.GroundSpeed;
        if (animal.Sprite != null && Math.Abs(animal.Sprite.interval - profile.StepIntervalMs) > 0.5f && profile.StepIntervalMs != VanillaStepInterval)
            animal.Sprite.interval = profile.StepIntervalMs;
    }

    private void CheckStomp(FarmAnimal animal)
    {
        long id = animal.myID.Value;
        int frame = animal.Sprite.currentFrame;
        bool landed = frame < 12 && frame % 2 == 0 && this.stepFrames.TryGetValue(id, out int last) && last % 2 == 1 && animal.isMoving();
        this.stepFrames[id] = frame;
        if (!landed || animal.isBaby())
            return;
        float distance = Vector2.Distance(animal.getStandingPosition(), Game1.player.getStandingPosition());
        if (distance > StompSoundRadius)
            return;
        Game1.playSound("thudStep");
        if (this.config.DinosaurStompShake && distance <= StompShakeRadius)
            this.shakeTicks = 6;
    }

    private void OnRenderedWorld(object? sender, RenderedWorldEventArgs e)
    {
        if (this.location == null || !ReferenceEquals(Game1.currentLocation, this.location))
            return;
        double clock = Game1.currentGameTime.TotalGameTime.TotalMilliseconds;
        foreach (Entry entry in this.entries.Values)
        {
            if (!entry.Hidden || entry.Animal.currentLocation != this.location)
                continue;
            this.DrawElevated(e.SpriteBatch, entry, clock + (entry.Animal.myID.Value % 997) * 37);
        }
    }

    private void DrawElevated(SpriteBatch b, Entry entry, double clock)
    {
        FarmAnimal animal = entry.Animal;
        BrainOutput output = entry.Last;
        AnimatedSprite sprite = animal.Sprite;
        int width = sprite.SpriteWidth;
        int height = sprite.SpriteHeight;
        string name = animal.type.Value.Substring(AnimalTypePrefix.Length);

        Texture2D? texture;
        int row;
        int column;
        switch (output.Pose)
        {
            case BrainPose.Fly:
                texture = this.GetTexture($"{name}Fly");
                row = output.Facing switch { 2 => 0, 0 => 2, _ => 1 };
                column = (int)(clock / 110) % 4;
                break;
            case BrainPose.Perch:
                texture = this.GetTexture($"{name}Fly");
                row = 3;
                column = IdleColumn(clock);
                break;
            case BrainPose.Climb:
                texture = this.GetTexture($"{name}Climb");
                row = 0;
                column = (int)(clock / 160) % 4;
                break;
            case BrainPose.Sit:
                texture = this.GetTexture($"{name}Climb");
                row = 1;
                column = Game1.timeOfDay >= 2000 ? 3 : Math.Min(2, IdleColumn(clock));
                break;
            default:
                texture = this.GetTexture($"{name}Climb");
                row = 2;
                column = (int)(clock / 130) % 4;
                break;
        }

        Rectangle source;
        if (texture != null && texture.Height >= (row + 1) * height)
        {
            source = new Rectangle(column * width, row * height, width, height);
        }
        else
        {
            texture = sprite.Texture;
            source = sprite.SourceRect;
        }

        bool flip = output.Facing == 3;
        Vector2 world = animal.Position - new Vector2(0, 24 + output.Altitude);
        Vector2 screen = Utility.snapDrawPosition(Game1.GlobalToLocal(Game1.viewport, world));
        b.Draw(texture, screen, source, Color.White, 0f, Vector2.Zero, 4f, flip ? SpriteEffects.FlipHorizontally : SpriteEffects.None, 1f);

        if (animal.isEmoting)
        {
            Point offset = animal.GetAnimalData()?.EmoteOffset ?? Point.Zero;
            Vector2 emote = Game1.GlobalToLocal(Game1.viewport, new Vector2(
                animal.Position.X + width / 2 * 4 - 32 + offset.X,
                animal.Position.Y - 64 + offset.Y - output.Altitude));
            int index = animal.CurrentEmoteIndex;
            Texture2D sheet = Game1.emoteSpriteSheet;
            b.Draw(sheet, emote, new Rectangle(index * 16 % sheet.Width, index * 16 / sheet.Width * 16, 16, 16), Color.White, 0f, Vector2.Zero, 4f, SpriteEffects.None, 1f);
        }
    }

    /// <summary>Mostly the resting frame, with an occasional blink and head turns.</summary>
    private static int IdleColumn(double clock)
    {
        int beat = (int)(clock / 500) % 16;
        return beat switch
        {
            5 => 1,
            9 or 10 => 2,
            13 or 14 => 3,
            _ => 0
        };
    }

    private Texture2D? GetTexture(string name)
    {
        if (this.textures.TryGetValue(name, out Texture2D? cached))
            return cached;
        string asset = AssetPrefix + name;
        Texture2D? texture = Game1.content.DoesAssetExist<Texture2D>(asset) ? this.helper.GameContent.Load<Texture2D>(asset) : null;
        this.textures[name] = texture;
        return texture;
    }

    private BrainWorld GetWorld(AnimalHouse house, HabitatRect pen)
    {
        if (this.worlds.TryGetValue(pen.Id, out BrainWorld? world))
            return world;
        world = new BrainWorld(pen, FindPerches(house, pen), this.GetWater(pen).Select(p => (p.X, p.Y)).ToList());
        this.worlds[pen.Id] = world;
        return world;
    }

    private HashSet<Point> GetWater(HabitatRect pen)
    {
        if (this.waterByPen.TryGetValue(pen.Id, out HashSet<Point>? water))
            return water;
        water = new HashSet<Point>();
        if (this.location != null)
        {
            for (int x = pen.X; x < pen.X + pen.Width; x++)
            {
                for (int y = pen.Y; y < pen.Y + pen.Height; y++)
                {
                    if (IsWater(this.location, x, y))
                        water.Add(new Point(x, y));
                }
            }
        }
        this.waterByPen[pen.Id] = water;
        return water;
    }

    private static bool IsWater(GameLocation location, int x, int y)
    {
        if (location.doesTileHaveProperty(x, y, "Water", "Back") != null || location.doesTileHaveProperty(x, y, "ZooWater", "Back") != null)
            return true;
        Tile? tile = location.Map.GetLayer("Back")?.Tiles[x, y];
        return tile != null
            && WaterTileIndexes.Contains(tile.TileIndex)
            && tile.TileSheet.ImageSource.Contains("outdoorsTileSheet", StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>Perches come from a <c>ZooPerch</c> tile property (value = height in tiles) if the map defines any, else from tree-shaped tile stacks.</summary>
    private static List<PerchSpot> FindPerches(GameLocation location, HabitatRect pen)
    {
        var tagged = new List<PerchSpot>();
        for (int x = pen.X; x < pen.X + pen.Width; x++)
        {
            for (int y = pen.Y; y < pen.Y + pen.Height; y++)
            {
                foreach (string layer in new[] { "Back", "Buildings", "Front" })
                {
                    string? value = location.doesTileHaveProperty(x, y, "ZooPerch", layer);
                    if (value == null)
                        continue;
                    float tiles = float.TryParse(value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float parsed) ? parsed : 2f;
                    tagged.Add(new PerchSpot(x, y, Math.Max(32, tiles * 64)));
                    break;
                }
            }
        }
        if (tagged.Count > 0)
            return tagged;

        Layer? buildings = location.Map.GetLayer("Buildings");
        Layer? alwaysFront = location.Map.GetLayer("AlwaysFront");
        Layer?[] inPen = { buildings, location.Map.GetLayer("Front"), alwaysFront };
        Layer?[] abovePen = { alwaysFront };
        // above the pen only canopy (AlwaysFront) counts, so fences and pickets don't extend the stack
        bool HasTile(int x, int y) =>
            x >= 0 && y >= 0 && (y >= pen.Y ? inPen : abovePen)
                .Any(layer => layer != null && x < layer.LayerWidth && y < layer.LayerHeight && layer.Tiles[x, y] != null);

        return PerchFinder.FindTrees(HasTile, pen)
            .Select(spot =>
            {
                bool solid = buildings?.Tiles[spot.TileX, spot.TileY] != null;
                return solid && spot.TileY + 1 < pen.Y + pen.Height
                    ? spot with { TileY = spot.TileY + 1, Height = spot.Height + 64 }
                    : spot;
            })
            .ToList();
    }

    private void Release(Entry entry)
    {
        FarmAnimal animal = entry.Animal;
        if (entry.Hidden)
        {
            animal.yJumpOffset = 0;
            animal.yJumpVelocity = 0;
        }
        if (entry.Controlling)
            animal.pauseTimer = 0;
        if (Context.IsMainPlayer && animal.isSwimming.Value && (entry.Profile.Style == MoveStyle.Swimmer || Waders.Contains(animal.type.Value)))
            animal.isSwimming.Value = false;
    }

    private void Clear()
    {
        foreach (Entry entry in this.entries.Values)
            this.Release(entry);
        this.entries.Clear();
        this.stepFrames.Clear();
        this.worlds.Clear();
        this.waterByPen.Clear();
        this.location = null;
        this.shakeTicks = 0;
    }
}
