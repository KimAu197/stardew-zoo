using StardewZoo;
using Xunit;

public class ZooIncomeTests
{
    private const string Penguin = ZooIds.Penguin;
    private const string Panda = ZooIds.Panda;
    private const string Lion = ZooIds.Lion;

    private static readonly Random NoNoise = new FixedRandom(0.5);

    private static DailyIncome Calc(ModConfig config, IReadOnlyList<ZooReview>? reviews = null, params ZooSnapshot[] zoos)
    {
        return ZooIncome.Calculate(zoos, config, reviews, NoNoise);
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
        DailyIncome result = Calc(new ModConfig(), null, new ZooSnapshot(ZooIds.Zoo, Array.Empty<string>()));

        Assert.Equal(0, result.TotalIncome);
        Assert.Equal(0, result.Visitors);
        Assert.Equal(0, result.Zoos.Single().FairValue);
    }

    [Fact]
    public void Income_IsVisitorsTimesTicketPrice()
    {
        var config = new ModConfig { TicketPrice = 40 };

        DailyIncome result = Calc(config, null, new ZooSnapshot(ZooIds.Zoo, new[] { Penguin, Panda }));

        Assert.Equal(result.Visitors * 40, result.TotalIncome);
        Assert.True(result.Visitors > 0);
    }

    [Fact]
    public void ZeroTicketPrice_ManyVisitorsButNoGold()
    {
        var config = new ModConfig { TicketPrice = 0 };

        DailyIncome result = Calc(config, null, new ZooSnapshot(ZooIds.Zoo, new[] { Penguin }));

        Assert.True(result.Visitors > 0);
        Assert.Equal(0, result.TotalIncome);
    }

    [Fact]
    public void FairValue_CountsAnimalsSpeciesHabitatsAndTier()
    {
        var config = new ModConfig();
        var basic = new ZooSnapshot(ZooIds.Zoo, new[] { Penguin, Panda, Lion });
        var deluxe = new ZooSnapshot(ZooIds.DeluxeZoo, new[] { Penguin, Panda, Lion });

        int basicFair = ZooIncome.FairValue(basic, config);
        int deluxeFair = ZooIncome.FairValue(deluxe, config);

        // 3 animals, 3 species, 3 habitats (ice/jungle/savanna): 20+30+45+36 = 131
        Assert.Equal(131, basicFair);
        Assert.Equal(262, deluxeFair);
        Assert.Equal(3, ZooHabitats.CountFilled(basic.AnimalTypes));
    }

    [Fact]
    public void HighPrice_CutsDemand()
    {
        var cheap = new ModConfig { TicketPrice = 20 };
        var expensive = new ModConfig { TicketPrice = 400 };
        var zoo = new ZooSnapshot(ZooIds.Zoo, new[] { Penguin, Panda });

        DailyIncome low = Calc(cheap, null, zoo);
        DailyIncome high = Calc(expensive, null, zoo);

        Assert.True(high.Visitors < low.Visitors);
        Assert.True(high.NewReviews.Average(r => r.Stars) <= low.NewReviews.Average(r => r.Stars) + 0.5);
    }

    [Fact]
    public void BadReviews_ReduceTomorrowVisitors()
    {
        var config = new ModConfig { TicketPrice = 50 };
        var zoo = new ZooSnapshot(ZooIds.Zoo, new[] { Penguin, Panda, Lion });
        var bad = Enumerable.Repeat(new ZooReview(1, "review.overall.bad", "overall"), 8).ToList();
        var good = Enumerable.Repeat(new ZooReview(5, "review.overall.great", "overall"), 8).ToList();

        DailyIncome afterBad = Calc(config, bad, zoo);
        DailyIncome afterGood = Calc(config, good, zoo);

        Assert.True(afterBad.Visitors < afterGood.Visitors);
        Assert.Equal(1.0, afterBad.AverageRatingUsed);
        Assert.Equal(5.0, afterGood.AverageRatingUsed);
    }

    [Fact]
    public void StartingRating_IsThreeWhenNoReviews()
    {
        Assert.Equal(3.0, ZooIncome.AverageRating(null));
        Assert.Equal(3.0, ZooIncome.AverageRating(Array.Empty<ZooReview>()));
    }

    [Fact]
    public void AppendReviews_KeepsLastTwelve()
    {
        var previous = Enumerable.Range(0, 10).Select(i => new ZooReview(3, "a", "overall")).ToList();
        var fresh = Enumerable.Range(0, 5).Select(i => new ZooReview(5, "b", "overall")).ToList();

        List<ZooReview> stored = ZooIncome.AppendReviews(previous, fresh, 12);

        Assert.Equal(12, stored.Count);
        Assert.Equal(5, stored.Count(r => r.Stars == 5));
        Assert.Equal(7, stored.Count(r => r.Stars == 3));
    }

    [Fact]
    public void HighPriceFewAnimals_LeavesBadReviews()
    {
        ZooReview review = ZooIncome.RateVisit(animals: 1, habitats: 1, priceRatio: 4.0, NoNoise);

        Assert.InRange(review.Stars, 1, 2);
        Assert.Equal("review.price.high", review.TemplateKey);
    }

    [Fact]
    public void SeedableRandom_IsDeterministic()
    {
        var config = new ModConfig();
        var zoo = new ZooSnapshot(ZooIds.Zoo, new[] { Penguin, Panda });

        DailyIncome a = ZooIncome.Calculate(new[] { zoo }, config, null, new Random(123));
        DailyIncome b = ZooIncome.Calculate(new[] { zoo }, config, null, new Random(123));

        Assert.Equal(a.Visitors, b.Visitors);
        Assert.Equal(a.TotalIncome, b.TotalIncome);
    }

    [Fact]
    public void MultipleZoos_SumVisitorsAndIncome()
    {
        DailyIncome result = Calc(
            new ModConfig { TicketPrice = 10 },
            null,
            new ZooSnapshot(ZooIds.Zoo, new[] { Penguin }),
            new ZooSnapshot(ZooIds.BigZoo, new[] { Panda, Lion })
        );

        Assert.Equal(2, result.Zoos.Count);
        Assert.Equal(result.Zoos.Sum(z => z.Visitors), result.Visitors);
        Assert.Equal(result.Visitors * 10, result.TotalIncome);
    }

    private sealed class FixedRandom : Random
    {
        private readonly double value;

        public FixedRandom(double value) => this.value = value;

        public override double NextDouble() => this.value;

        public override int Next(int maxValue) => 0;
    }
}
