using Microsoft.Xna.Framework;
using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewValley;
using StardewValley.Menus;

namespace StardewZoo;

internal sealed class ModEntry : Mod
{
    private ModConfig config = null!;
    private ZooSaveData save = new();
    private DailyIncome? lastPayout;
    private VisitorManager visitors = null!;
    private RecordingManager recording = null!;
    private AnimalMovement movement = null!;
    private int tick;

    public override void Entry(IModHelper helper)
    {
        this.config = helper.ReadConfig<ModConfig>();
        this.config.TicketPrice = Math.Clamp(this.config.TicketPrice, this.config.MinTicketPrice, this.config.MaxTicketPrice);
        this.visitors = new VisitorManager(helper, this.Monitor, () => this.config, () => this.save);
        this.recording = new RecordingManager(helper, this.Monitor);
        new AnimalCallHandler(helper, this.config);
        this.movement = new AnimalMovement(helper, this.config);
        WaterGuard.Apply(this.Monitor);
        new ZooFurniture(helper, this.Monitor);
        new PlaqueInteraction(helper, this.Monitor);
        new PavilionManager(helper, this.Monitor);

        helper.Events.GameLoop.GameLaunched += this.OnGameLaunched;
        helper.Events.GameLoop.SaveLoaded += this.OnSaveLoaded;
        helper.Events.GameLoop.Saving += this.OnSaving;
        helper.Events.GameLoop.DayEnding += this.OnDayEnding;
        helper.Events.GameLoop.DayStarted += this.OnDayStarted;
        helper.Events.GameLoop.TimeChanged += this.OnTimeChanged;
        helper.Events.GameLoop.UpdateTicked += this.OnUpdateTicked;
        helper.Events.Player.Warped += this.OnWarped;
        helper.Events.Input.ButtonPressed += this.OnButtonPressed;
        helper.ConsoleCommands.Add("zoo_status", "Shows each zoo, ticket price, rating, and projected visitors.", this.OnZooStatusCommand);
    }

    private void OnGameLaunched(object? sender, GameLaunchedEventArgs e)
    {
        GameLocation.RegisterTileAction(ZooIds.TicketAction, this.OnTicketTile);
        GameLocation.RegisterTileAction(ZooIds.ReviewAction, this.OnReviewTile);
        GameLocation.RegisterTileAction(ZooIds.StudioAction, this.OnStudioTile);
    }

    private void OnSaveLoaded(object? sender, SaveLoadedEventArgs e)
    {
        this.save = this.Helper.Data.ReadSaveData<ZooSaveData>(ZooSaveData.Key) ?? new ZooSaveData();
        HabitatKeeper.ReloadInteriors(msg => this.Monitor.Log(msg, LogLevel.Info));
        this.recording.Initialize(this.save);
        HabitatKeeper.SnapAll(Random.Shared);
        HabitatKeeper.FeedAll();
    }

    private void OnSaving(object? sender, SavingEventArgs e)
    {
        this.visitors.RemoveAll();
        this.Persist();
    }

    private void OnDayEnding(object? sender, DayEndingEventArgs e)
    {
        if (!Context.IsMainPlayer)
            return;

        this.visitors.RemoveAll();
        HabitatKeeper.FeedAll();
        DailyIncome result = this.Project(Game1.ticks);
        if (result.TotalIncome > 0)
            Game1.player.Money += result.TotalIncome;

        this.save.Reviews = ZooIncome.AppendReviews(this.save.Reviews, result.NewReviews, this.config.MaxStoredReviews);
        this.save.LastVisitors = result.Visitors;
        this.save.LastIncome = result.TotalIncome;
        this.save.LastRating = ZooIncome.AverageRating(this.save.Reviews);
        this.lastPayout = result;
        this.Persist();
        this.Monitor.Log($"Zoo day: {result.Visitors} visitors, {result.TotalIncome}g, rating {this.save.LastRating:0.0}.", LogLevel.Trace);
    }

    private void OnDayStarted(object? sender, DayStartedEventArgs e)
    {
        HabitatKeeper.SnapAll(Random.Shared);
        HabitatKeeper.FeedAll();
        this.visitors.StartDay();

        if (this.lastPayout is not { } payout)
            return;

        string message = this.Helper.Translation.Get("hud.payout", new
        {
            visitors = payout.Visitors,
            income = payout.TotalIncome,
            rating = this.save.LastRating.ToString("0.0")
        });
        Game1.addHUDMessage(new HUDMessage(message, HUDMessage.newQuest_type));
        this.lastPayout = null;
    }

    private void OnTimeChanged(object? sender, TimeChangedEventArgs e)
    {
        if (e.NewTime >= 1800)
            this.visitors.RemoveAll();
        else
            this.visitors.TrySpawn();
    }

    private void OnUpdateTicked(object? sender, UpdateTickedEventArgs e)
    {
        if (!Context.IsWorldReady)
            return;
        this.recording.Tick();
        this.tick++;
        if (this.tick % 60 == 0)
        {
            HabitatKeeper.FeedAll();
            HabitatKeeper.SnapEscaped(Random.Shared, this.movement.IsControlling);
        }
    }

    private void OnWarped(object? sender, WarpedEventArgs e)
    {
        if (e.NewLocation is AnimalHouse && ZooIds.IsZoo(e.NewLocation.ParentBuilding?.buildingType.Value))
        {
            HabitatKeeper.SnapAll(Random.Shared);
            HabitatKeeper.FeedAll();
        }
    }

    private void OnButtonPressed(object? sender, ButtonPressedEventArgs e)
    {
        if (!Context.IsPlayerFree || !e.Button.IsActionButton() || Game1.currentLocation == null)
            return;

        Vector2 tile = Game1.player.GetGrabTile();
        string? action = Game1.currentLocation.doesTileHaveProperty((int)tile.X, (int)tile.Y, "Action", "Buildings", false);
        if (string.IsNullOrEmpty(action))
            return;
        if (action.StartsWith(ZooIds.TicketAction, StringComparison.Ordinal))
            this.OpenTicketMenu();
        else if (action.StartsWith(ZooIds.ReviewAction, StringComparison.Ordinal))
            this.OpenReviews();
        else if (action.StartsWith(ZooIds.StudioAction, StringComparison.Ordinal))
            this.OpenStudio();
        else
            return;
        this.Helper.Input.Suppress(e.Button);
    }

    private bool OnTicketTile(GameLocation location, string[] args, Farmer who, Point tile)
    {
        this.OpenTicketMenu();
        return true;
    }

    private bool OnReviewTile(GameLocation location, string[] args, Farmer who, Point tile)
    {
        this.OpenReviews();
        return true;
    }

    private bool OnStudioTile(GameLocation location, string[] args, Farmer who, Point tile)
    {
        this.OpenStudio();
        return true;
    }

    private void OpenTicketMenu()
    {
        List<ZooSnapshot> zoos = this.ScanZoos();
        double rating = ZooIncome.AverageRating(this.save.Reviews);
        int suggested = ZooIncome.SuggestedPrice(zoos, this.config, rating);
        string advice = suggested > 0
            ? this.Helper.Translation.Get("ticket.suggest", new { price = suggested, visitors = ZooIncome.Forecast(zoos, this.config, rating, suggested).Visitors })
            : this.Helper.Translation.Get("ticket.no-animals");

        Game1.activeClickableMenu = new TicketPriceMenu(
            this.Helper.Translation.Get("ticket.prompt") + "\n" + advice,
            this.OnTicketChosen,
            this.config.MinTicketPrice,
            this.config.MaxTicketPrice,
            this.config.TicketPrice,
            price =>
            {
                (int visitors, int income) = ZooIncome.Forecast(zoos, this.config, rating, price);
                return this.Helper.Translation.Get("ticket.forecast", new { visitors, income });
            }
        );
    }

    private void OnTicketChosen(int number, int price, Farmer who)
    {
        List<ZooSnapshot> zoos = this.ScanZoos();
        double rating = ZooIncome.AverageRating(this.save.Reviews);
        int before = ZooIncome.Forecast(zoos, this.config, rating, this.config.TicketPrice).Visitors;

        this.config.TicketPrice = Math.Clamp(number, this.config.MinTicketPrice, this.config.MaxTicketPrice);
        this.Helper.WriteConfig(this.config);
        Game1.addHUDMessage(new HUDMessage(
            this.Helper.Translation.Get("ticket.set", new { price = this.config.TicketPrice }),
            HUDMessage.newQuest_type
        ));

        int after = ZooIncome.Forecast(zoos, this.config, rating, this.config.TicketPrice).Visitors;
        int suggested = ZooIncome.SuggestedPrice(zoos, this.config, rating);
        string? crowdKey = CrowdHintKey(this.config.TicketPrice, suggested, before, after);
        if (crowdKey != null)
            Game1.addHUDMessage(new HUDMessage(this.Helper.Translation.Get(crowdKey, new { visitors = after }), HUDMessage.newQuest_type));
    }

    /// <summary>Which hint (if any) explains how today's crowd reacts to a new price; visitors spawn at the new rate from now on.</summary>
    private static string? CrowdHintKey(int price, int suggested, int visitorsBefore, int visitorsAfter)
    {
        if (suggested <= 0)
            return null;
        if (price <= 0)
            return "ticket.crowd-free";
        if (visitorsAfter < visitorsBefore * 0.9)
            return price > suggested * 1.5 ? "ticket.crowd-empty" : "ticket.crowd-down";
        if (visitorsAfter > visitorsBefore * 1.1)
            return price > suggested * 1.15 ? "ticket.crowd-up-pricey" : "ticket.crowd-up";
        return null;
    }

    private void OpenReviews()
    {
        var lines = new List<string>();
        if (this.save.Reviews.Count == 0)
        {
            lines.Add(this.Helper.Translation.Get("review.empty"));
        }
        else
        {
            lines.Add(this.Helper.Translation.Get("review.header", new { rating = ZooIncome.AverageRating(this.save.Reviews).ToString("0.0") }));
            foreach (ZooReview review in this.save.Reviews)
            {
                string stars = new string('★', review.Stars) + new string('☆', 5 - review.Stars);
                lines.Add(this.Helper.Translation.Get(review.TemplateKey, new { stars, rating = review.Stars }));
            }
        }
        Game1.activeClickableMenu = new DialogueBox(lines);
    }

    private void OpenStudio()
    {
        Game1.activeClickableMenu = new RecordingMenu(this.recording, this.Helper, this.save, this.Persist);
    }

    private void OnZooStatusCommand(string command, string[] args)
    {
        if (!Context.IsWorldReady)
        {
            this.Monitor.Log(this.Helper.Translation.Get("command.no-save"), LogLevel.Info);
            return;
        }

        DailyIncome result = this.Project(Game1.Date.TotalDays);
        if (result.Zoos.Count == 0)
        {
            this.Monitor.Log(this.Helper.Translation.Get("command.no-zoos"), LogLevel.Info);
            return;
        }

        this.Monitor.Log(this.Helper.Translation.Get("command.ticket", new { price = this.config.TicketPrice }), LogLevel.Info);
        this.Monitor.Log(this.Helper.Translation.Get("command.rating", new { rating = ZooIncome.AverageRating(this.save.Reviews).ToString("0.0") }), LogLevel.Info);
        foreach (ZooResult zoo in result.Zoos)
        {
            this.Monitor.Log(
                this.Helper.Translation.Get("command.zoo-line", new
                {
                    building = zoo.BuildingType,
                    animals = zoo.AnimalCount,
                    species = zoo.SpeciesCount,
                    habitats = zoo.FilledHabitats,
                    fair = zoo.FairValue,
                    visitors = zoo.Visitors,
                    income = zoo.Income,
                    onscreen = VisitorSpawnPlanner.MaxOnScreen(zoo.Visitors, this.config)
                }),
                LogLevel.Info
            );
        }
        this.Monitor.Log(this.Helper.Translation.Get("command.total", new { income = result.TotalIncome, visitors = result.Visitors }), LogLevel.Info);

        List<ZooSnapshot> zoos = this.ScanZoos();
        double rating = ZooIncome.AverageRating(this.save.Reviews);
        int suggested = ZooIncome.SuggestedPrice(zoos, this.config, rating);
        if (suggested > 0)
        {
            (int visitors, int income) = ZooIncome.Forecast(zoos, this.config, rating, suggested);
            this.Monitor.Log(this.Helper.Translation.Get("command.suggest", new { price = suggested, visitors, income }), LogLevel.Info);
        }
    }

    private DailyIncome Project(int seed)
    {
        return ZooIncome.Calculate(this.ScanZoos(), this.config, this.save.Reviews, new Random(seed));
    }

    private void Persist()
    {
        this.Helper.Data.WriteSaveData(ZooSaveData.Key, this.save);
    }

    private List<ZooSnapshot> ScanZoos()
    {
        var zoos = new List<ZooSnapshot>();
        Utility.ForEachBuilding(building =>
        {
            string buildingType = building.buildingType.Value;
            if (!ZooIds.IsZoo(buildingType) || building.isUnderConstruction() || building.GetIndoors() is not AnimalHouse house)
                return true;

            var animalTypes = new List<string>();
            foreach (long id in house.animalsThatLiveHere)
            {
                FarmAnimal? animal = Utility.getAnimal(id);
                if (animal != null)
                    animalTypes.Add(animal.type.Value);
            }

            zoos.Add(new ZooSnapshot(buildingType, animalTypes, ZooFurniture.DecorCount(house)));
            return true;
        });
        return zoos;
    }
}
