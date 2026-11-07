using StardewZoo;
using Xunit;

public class VisitorDemandTests
{
    private static readonly ModConfig Config = new();

    /// <summary>A basic zoo with the first <paramref name="species"/> species, two of each.</summary>
    private static ZooSnapshot Zoo(int species, string building = ZooIds.Zoo) =>
        new(building, ZooIds.AnimalTypes.Take(species).SelectMany(type => new[] { type, type }).ToList());

    private static int Visitors(ZooSnapshot zoo, int price, double rating = 3.0) =>
        ZooIncome.ExpectedVisitors(zoo, Config, rating, price);

    private static int FairPrice(ZooSnapshot zoo) => ZooIncome.FairValue(zoo, Config);

    [Fact]
    public void MoreSpecies_MoreVisitors_WithDiminishingReturns()
    {
        var counts = Enumerable.Range(1, 17).Select(n => Visitors(Zoo(n), FairPrice(Zoo(n)))).ToList();

        for (int i = 1; i < counts.Count; i++)
            Assert.True(counts[i] > counts[i - 1], $"{i + 1} species: {counts[i]} vs {counts[i - 1]}");
        Assert.True(counts[1] - counts[0] > counts[16] - counts[15], "the 2nd species should add more than the 17th");
    }

    [Fact]
    public void SpeciesVariety_BeatsHeadCount()
    {
        var oneSpeciesTen = new ZooSnapshot(ZooIds.Zoo, Enumerable.Repeat(ZooIds.Penguin, 10).ToList());
        var fiveSpeciesTen = Zoo(5);

        Assert.True(ZooIncome.BaseDemand(fiveSpeciesTen, Config) > ZooIncome.BaseDemand(oneSpeciesTen, Config) * 2);
    }

    [Fact]
    public void PriceAboveFair_FewerVisitors_Steeply()
    {
        ZooSnapshot zoo = Zoo(6);
        int fair = FairPrice(zoo);
        int atFair = Visitors(zoo, fair);
        int at150 = Visitors(zoo, fair * 3 / 2);
        int atDouble = Visitors(zoo, fair * 2);
        int atTriple = Visitors(zoo, fair * 3);

        Assert.True(atFair > at150 && at150 > atDouble && atDouble > atTriple);
        Assert.True(atDouble < atFair / 3, $"double price should empty the zoo: {atDouble} vs {atFair}");
    }

    [Fact]
    public void CheapPrice_IsAModestBoost()
    {
        ZooSnapshot zoo = Zoo(6);
        int fair = FairPrice(zoo);

        Assert.Equal(1.0, ZooIncome.PriceFactor(fair, fair, Config), 3);
        Assert.InRange(ZooIncome.PriceFactor(fair / 2, fair, Config), 1.1, 1.5);
        Assert.True(Visitors(zoo, fair / 2) > Visitors(zoo, fair));
    }

    [Fact]
    public void FreeEntry_MaxCrowd_NoIncome()
    {
        ZooSnapshot zoo = Zoo(6);
        int free = Visitors(zoo, 0);
        foreach (int price in new[] { 1, 10, FairPrice(zoo), 500 })
            Assert.True(free > Visitors(zoo, price), $"price {price}");

        var config = new ModConfig { TicketPrice = 0 };
        DailyIncome day = ZooIncome.Calculate(new[] { zoo }, config, null, new Random(1));
        Assert.True(day.Visitors > 0);
        Assert.Equal(0, day.TotalIncome);
    }

    [Fact]
    public void NoAnimals_NoVisitors()
    {
        var empty = new ZooSnapshot(ZooIds.DeluxeZoo, Array.Empty<string>());

        Assert.Equal(0, Visitors(empty, 0));
        Assert.Equal(0, VisitorSpawnPlanner.MaxOnScreen(Visitors(empty, 0), Config));
        Assert.Equal(0, ZooIncome.SuggestedPrice(new[] { empty }, Config, 3.0));
    }

    [Fact]
    public void Income_PeaksNearFairPrice()
    {
        ZooSnapshot zoo = Zoo(8);
        int fair = FairPrice(zoo);
        int suggested = ZooIncome.SuggestedPrice(new[] { zoo }, Config, 3.0);

        Assert.InRange(suggested, fair - 10, fair + 10);
        int best = ZooIncome.Forecast(new[] { zoo }, Config, 3.0, suggested).Income;
        Assert.True(best > ZooIncome.Forecast(new[] { zoo }, Config, 3.0, fair / 2).Income);
        Assert.True(best > ZooIncome.Forecast(new[] { zoo }, Config, 3.0, fair * 2).Income);
    }

    [Fact]
    public void HigherTier_AndBetterRating_DrawMore()
    {
        Assert.True(Visitors(Zoo(4, ZooIds.DeluxeZoo), 0) > Visitors(Zoo(4), 0));
        Assert.True(Visitors(Zoo(4), 50, 5.0) > Visitors(Zoo(4), 50, 2.0));
    }

    [Fact]
    public void Calculate_IsSeedableAndNearExpected()
    {
        var config = new ModConfig { TicketPrice = 100 };
        ZooSnapshot zoo = Zoo(10);
        int a = ZooIncome.Calculate(new[] { zoo }, config, null, new Random(5)).Visitors;
        int b = ZooIncome.Calculate(new[] { zoo }, config, null, new Random(5)).Visitors;
        int expected = ZooIncome.ExpectedVisitors(zoo, config, 3.0);

        Assert.Equal(a, b);
        Assert.InRange(a, expected * 0.89, expected * 1.11);
    }

    [Fact]
    public void OnScreen_IsMonotonicInDemand_AndCapped()
    {
        int previous = 0;
        for (int daily = 0; daily <= 500; daily++)
        {
            int onScreen = VisitorSpawnPlanner.MaxOnScreen(daily, Config);
            Assert.True(onScreen >= previous);
            Assert.InRange(onScreen, daily == 0 ? 0 : 1, Config.MaxVisitorsOnScreen);
            previous = onScreen;
        }
        Assert.Equal(Config.MaxVisitorsOnScreen, VisitorSpawnPlanner.MaxOnScreen(500, Config));
        Assert.Equal(3, VisitorSpawnPlanner.MaxOnScreen(500, new ModConfig { MaxVisitorsOnScreen = 3 }));
    }

    [Fact]
    public void OnScreen_TinyOrOverpricedZoo_IsOneOrTwo_GreatZoo_IsTenPlus()
    {
        ZooSnapshot tiny = Zoo(1);
        ZooSnapshot great = Zoo(17);

        Assert.InRange(VisitorSpawnPlanner.MaxOnScreen(Visitors(tiny, FairPrice(tiny)), Config), 1, 3);
        Assert.InRange(VisitorSpawnPlanner.MaxOnScreen(Visitors(great, FairPrice(great) * 3), Config), 0, 2);
        Assert.InRange(VisitorSpawnPlanner.MaxOnScreen(Visitors(great, FairPrice(great), 4.0), Config), 10, 14);
    }

    [Fact]
    public void Spawning_FollowsDemand_AndRespectsCap()
    {
        int SpawnedOverDay(int daily)
        {
            var planner = new VisitorSpawnPlanner();
            int total = 0;
            for (int slot = 0; slot < 60; slot++)
                total += planner.SpawnsDue("zoo", daily, 0, Config);
            return total;
        }

        Assert.Equal(0, SpawnedOverDay(0));
        Assert.True(SpawnedOverDay(100) > SpawnedOverDay(30) * 2);
        Assert.True(SpawnedOverDay(30) > SpawnedOverDay(5));

        var full = new VisitorSpawnPlanner();
        Assert.Equal(1, full.SpawnsDue("zoo", 7, 0, Config));
        for (int slot = 0; slot < 30; slot++)
            Assert.Equal(0, full.SpawnsDue("zoo", 7, 1, Config));
        Assert.Equal(1, full.SpawnsDue("zoo", 7, 0, Config));
    }

    [Fact]
    public void Spawning_ReactsToMidDayPriceChange()
    {
        var planner = new VisitorSpawnPlanner();
        ZooSnapshot zoo = Zoo(10);
        int fair = FairPrice(zoo);
        int fairSpawns = 0, overpricedSpawns = 0;
        for (int slot = 0; slot < 30; slot++)
            fairSpawns += planner.SpawnsDue("zoo", Visitors(zoo, fair), 0, Config);
        for (int slot = 0; slot < 30; slot++)
            overpricedSpawns += planner.SpawnsDue("zoo", Visitors(zoo, fair * 3), 0, Config);

        Assert.True(overpricedSpawns < fairSpawns / 3, $"{overpricedSpawns} vs {fairSpawns}");
    }
}
