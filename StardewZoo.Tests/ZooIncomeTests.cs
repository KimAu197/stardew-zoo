using StardewZoo;
using Xunit;

public class ZooIncomeTests
{
    private const string Penguin = "StardewZoo.Penguin";
    private const string Panda = "StardewZoo.Panda";

    private static DailyIncome Calc(ModConfig config, params ZooSnapshot[] zoos)
    {
        return ZooIncome.Calculate(zoos, config);
    }

    [Fact]
    public void NoZoos_PaysNothing()
    {
        DailyIncome result = Calc(new ModConfig());

        Assert.Empty(result.Zoos);
        Assert.Equal(0, result.TotalIncome);
        Assert.Equal(0, result.Visitors);
    }

    [Fact]
    public void EmptyZoo_PaysNothing()
    {
        DailyIncome result = Calc(new ModConfig(), new ZooSnapshot(ZooIds.Zoo, Array.Empty<string>()));

        Assert.Equal(0, result.TotalIncome);
        Assert.Equal(new ZooResult(ZooIds.Zoo, 0, 0, 0), result.Zoos.Single());
    }

    [Fact]
    public void BasicZoo_CountsAnimalsAndDistinctSpecies()
    {
        DailyIncome result = Calc(new ModConfig(), new ZooSnapshot(ZooIds.Zoo, new[] { Penguin, Penguin, Panda }));

        // (3 * 50 + 2 * 200) * 1.0 = 550
        Assert.Equal(new ZooResult(ZooIds.Zoo, 3, 2, 550), result.Zoos.Single());
        Assert.Equal(550, result.TotalIncome);
        Assert.Equal(11, result.Visitors);
    }

    [Theory]
    [InlineData(ZooIds.BigZoo, 825)]
    [InlineData(ZooIds.DeluxeZoo, 1100)]
    [InlineData("SomeOther.Building", 550)]
    public void Multiplier_DependsOnBuildingTier(string buildingType, int expected)
    {
        DailyIncome result = Calc(new ModConfig(), new ZooSnapshot(buildingType, new[] { Penguin, Penguin, Panda }));

        Assert.Equal(expected, result.TotalIncome);
    }

    [Fact]
    public void MultipleZoos_SumIncome_SpeciesCountedPerZoo()
    {
        DailyIncome result = Calc(
            new ModConfig(),
            new ZooSnapshot(ZooIds.Zoo, new[] { Penguin }),
            new ZooSnapshot(ZooIds.Zoo, new[] { Penguin })
        );

        // each zoo: (1 * 50 + 1 * 200) * 1.0 = 250
        Assert.Equal(2, result.Zoos.Count);
        Assert.Equal(500, result.TotalIncome);
        Assert.Equal(10, result.Visitors);
    }

    [Fact]
    public void Visitors_RoundDown()
    {
        var config = new ModConfig { TicketPrice = 300 };

        DailyIncome result = Calc(config, new ZooSnapshot(ZooIds.Zoo, new[] { Penguin, Penguin, Panda }));

        Assert.Equal(1, result.Visitors); // 550 / 300 = 1.83
    }

    [Fact]
    public void ZeroTicketPrice_HasNoVisitorsButStillPays()
    {
        var config = new ModConfig { TicketPrice = 0 };

        DailyIncome result = Calc(config, new ZooSnapshot(ZooIds.Zoo, new[] { Penguin }));

        Assert.Equal(250, result.TotalIncome);
        Assert.Equal(0, result.Visitors);
    }

    [Fact]
    public void FractionalIncome_RoundsHalfAwayFromZero()
    {
        var config = new ModConfig { PricePerAnimal = 1, PricePerSpecies = 0 };

        DailyIncome result = Calc(config, new ZooSnapshot(ZooIds.BigZoo, new[] { Penguin }));

        Assert.Equal(2, result.TotalIncome); // 1 * 1.5 = 1.5 -> 2
    }
}
