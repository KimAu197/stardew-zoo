using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewValley;

namespace StardewZoo;

/// <summary>The mod entry point.</summary>
internal sealed class ModEntry : Mod
{
    private ModConfig config = null!;

    /// <summary>The income paid at the end of the previous day, shown the next morning.</summary>
    private DailyIncome? lastPayout;

    public override void Entry(IModHelper helper)
    {
        this.config = helper.ReadConfig<ModConfig>();

        helper.Events.GameLoop.DayEnding += this.OnDayEnding;
        helper.Events.GameLoop.DayStarted += this.OnDayStarted;
        helper.ConsoleCommands.Add("zoo_status", "Shows each zoo, its animals, and projected ticket income.", this.OnZooStatusCommand);
    }

    private void OnDayEnding(object? sender, DayEndingEventArgs e)
    {
        if (!Context.IsMainPlayer)
            return;

        DailyIncome result = ZooIncome.Calculate(this.ScanZoos(), this.config);
        if (result.TotalIncome <= 0)
            return;

        Game1.player.Money += result.TotalIncome;
        this.lastPayout = result;
        this.Monitor.Log($"Paid {result.TotalIncome}g zoo income ({result.Visitors} visitors).", LogLevel.Trace);
    }

    private void OnDayStarted(object? sender, DayStartedEventArgs e)
    {
        if (this.lastPayout is not { } payout)
            return;

        string message = this.Helper.Translation.Get("hud.payout", new { visitors = payout.Visitors, income = payout.TotalIncome });
        Game1.addHUDMessage(new HUDMessage(message, HUDMessage.newQuest_type));
        this.lastPayout = null;
    }

    private void OnZooStatusCommand(string command, string[] args)
    {
        if (!Context.IsWorldReady)
        {
            this.Monitor.Log(this.Helper.Translation.Get("command.no-save"), LogLevel.Info);
            return;
        }

        DailyIncome result = ZooIncome.Calculate(this.ScanZoos(), this.config);
        if (result.Zoos.Count == 0)
        {
            this.Monitor.Log(this.Helper.Translation.Get("command.no-zoos"), LogLevel.Info);
            return;
        }

        foreach (ZooResult zoo in result.Zoos)
        {
            this.Monitor.Log(
                this.Helper.Translation.Get("command.zoo-line", new { building = zoo.BuildingType, animals = zoo.AnimalCount, species = zoo.SpeciesCount, income = zoo.Income }),
                LogLevel.Info
            );
        }
        this.Monitor.Log(this.Helper.Translation.Get("command.total", new { income = result.TotalIncome, visitors = result.Visitors }), LogLevel.Info);
    }

    /// <summary>Get the animal types living in each completed zoo building, in any location.</summary>
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

            zoos.Add(new ZooSnapshot(buildingType, animalTypes));
            return true;
        });

        return zoos;
    }
}
