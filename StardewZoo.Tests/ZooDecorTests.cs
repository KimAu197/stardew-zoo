using StardewZoo;
using Xunit;

public class ZooDecorTests
{
    [Theory]
    [InlineData(0, 1.0)]
    [InlineData(1, 1.01)]
    [InlineData(5, 1.05)]
    [InlineData(10, 1.10)]
    [InlineData(250, 1.10)]
    public void Multiplier_GrowsPerItem_UpToCap(int decor, double expected)
    {
        Assert.Equal(expected, ZooDecor.DemandMultiplier(decor, 0.01, 0.10), 6);
    }

    [Fact]
    public void ZeroCap_DisablesBonus()
    {
        Assert.Equal(1.0, ZooDecor.DemandMultiplier(30, 0.01, 0));
    }

    [Fact]
    public void Decor_RaisesExpectedVisitors_ByAtMostTenPercent()
    {
        var config = new ModConfig();
        var animals = new[] { ZooIds.Penguin, ZooIds.Lion, ZooIds.Panda, ZooIds.Monkey };
        double bare = ZooIncome.ExpectedDemand(new ZooSnapshot(ZooIds.Zoo, animals), config, ZooIncome.StartingRating);
        double some = ZooIncome.ExpectedDemand(new ZooSnapshot(ZooIds.Zoo, animals, 4), config, ZooIncome.StartingRating);
        double lots = ZooIncome.ExpectedDemand(new ZooSnapshot(ZooIds.Zoo, animals, 99), config, ZooIncome.StartingRating);

        Assert.Equal(bare * 1.04, some, 6);
        Assert.Equal(bare * 1.10, lots, 6);
    }

    [Fact]
    public void Decor_AloneDrawsNoVisitors()
    {
        Assert.Equal(0, ZooIncome.ExpectedDemand(new ZooSnapshot(ZooIds.Zoo, Array.Empty<string>(), 20), new ModConfig(), 3.0));
    }
}
