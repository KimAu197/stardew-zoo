namespace StardewZoo;

public record ZooSnapshot(string BuildingType, IReadOnlyList<string> AnimalTypes, int DecorCount = 0);

public record ZooResult(
    string BuildingType,
    int AnimalCount,
    int SpeciesCount,
    int FilledHabitats,
    int FairValue,
    int Visitors,
    int Income);

public record ZooReview(int Stars, string TemplateKey, string Topic);

public record DailyIncome(
    IReadOnlyList<ZooResult> Zoos,
    int TotalIncome,
    int Visitors,
    double AverageRatingUsed,
    IReadOnlyList<ZooReview> NewReviews);

public static class ZooIncome
{
    public const double StartingRating = 3.0;

    public static double AverageRating(IReadOnlyList<ZooReview>? reviews)
    {
        if (reviews == null || reviews.Count == 0)
            return StartingRating;
        return reviews.Average(review => review.Stars);
    }

    public static double TierMultiplier(string buildingType, ModConfig config)
    {
        return config.Multipliers.TryGetValue(buildingType, out double value) ? value : 1.0;
    }

    public static int FairValue(ZooSnapshot zoo, ModConfig config)
    {
        int animals = zoo.AnimalTypes.Count;
        if (animals == 0)
            return 0;
        int species = zoo.AnimalTypes.Distinct().Count();
        int habitats = ZooHabitats.CountFilled(zoo.AnimalTypes);
        double raw = (config.BaseFair + animals * config.FairPerAnimal + species * config.FairPerSpecies + habitats * config.FairPerHabitat)
            * TierMultiplier(zoo.BuildingType, config);
        return Math.Max(0, (int)Math.Round(raw, MidpointRounding.AwayFromZero));
    }

    /// <summary>Visitors a zoo draws at a fair price and a neutral rating: species variety counts most (with diminishing returns), head count a little.</summary>
    public static double BaseDemand(ZooSnapshot zoo, ModConfig config)
    {
        int animals = zoo.AnimalTypes.Count;
        if (animals == 0)
            return 0;
        int species = zoo.AnimalTypes.Distinct().Count();
        double speciesPull = config.DemandPerSpecies * Math.Pow(species, config.SpeciesDiminishing);
        double animalPull = config.DemandPerAnimal * Math.Sqrt(animals);
        return (config.DemandBase + speciesPull + animalPull) * TierMultiplier(zoo.BuildingType, config);
    }

    /// <summary>
    /// Price elasticity: free entry draws the biggest crowd, a cheap ticket a modest boost, the fair price is neutral (1.0),
    /// and each step above fair cuts demand exponentially. Income (visitors x price) peaks at the fair price.
    /// </summary>
    public static double PriceFactor(int ticketPrice, int fairValue, ModConfig config)
    {
        double cheapBoost = Math.Max(0, config.CheapPriceBoost);
        if (ticketPrice <= 0)
            return Math.Max(config.FreeEntryBoost, 1 + cheapBoost);
        double ratio = ticketPrice / (double)Math.Max(fairValue, 1);
        if (ratio <= 1)
            return 1 + cheapBoost * (1 - ratio);
        return Math.Exp(-Math.Max(0, config.OverpriceElasticity) * (ratio - 1));
    }

    public static double RatingFactor(double averageRating) => Math.Clamp(averageRating / StartingRating, 0.25, 1.75);

    /// <summary>Noise-free visitors per day for one zoo at the given price (defaults to the configured price).</summary>
    public static double ExpectedDemand(ZooSnapshot zoo, ModConfig config, double averageRating, int? ticketPrice = null)
    {
        if (zoo.AnimalTypes.Count == 0)
            return 0;
        int price = ticketPrice ?? config.TicketPrice;
        return BaseDemand(zoo, config) * PriceFactor(price, FairValue(zoo, config), config) * RatingFactor(averageRating)
            * ZooDecor.DemandMultiplier(zoo.DecorCount, config.DecorBonusPerItem, config.MaxDecorBonus);
    }

    public static int ExpectedVisitors(ZooSnapshot zoo, ModConfig config, double averageRating, int? ticketPrice = null) =>
        (int)Math.Round(ExpectedDemand(zoo, config, averageRating, ticketPrice), MidpointRounding.AwayFromZero);

    /// <summary>Noise-free daily visitors and ticket income across all zoos at a price.</summary>
    public static (int Visitors, int Income) Forecast(IEnumerable<ZooSnapshot> zoos, ModConfig config, double averageRating, int ticketPrice)
    {
        int visitors = zoos.Sum(zoo => ExpectedVisitors(zoo, config, averageRating, ticketPrice));
        return (visitors, visitors * Math.Max(0, ticketPrice));
    }

    /// <summary>The ticket price (in steps of 5g) that earns the most per day; 0 when there are no animals.</summary>
    public static int SuggestedPrice(IReadOnlyList<ZooSnapshot> zoos, ModConfig config, double averageRating)
    {
        if (zoos.All(zoo => zoo.AnimalTypes.Count == 0))
            return 0;
        int best = 0;
        int bestIncome = -1;
        for (int price = Math.Max(5, config.MinTicketPrice); price <= config.MaxTicketPrice; price += 5)
        {
            int income = Forecast(zoos, config, averageRating, price).Income;
            if (income > bestIncome)
            {
                best = price;
                bestIncome = income;
            }
        }
        return best;
    }

    public static DailyIncome Calculate(
        IEnumerable<ZooSnapshot> zoos,
        ModConfig config,
        IReadOnlyList<ZooReview>? previousReviews = null,
        Random? rng = null)
    {
        rng ??= Random.Shared;
        double rating = AverageRating(previousReviews);
        var results = new List<ZooResult>();
        var reviews = new List<ZooReview>();

        foreach (ZooSnapshot zoo in zoos)
        {
            int animals = zoo.AnimalTypes.Count;
            int species = zoo.AnimalTypes.Distinct().Count();
            int habitats = ZooHabitats.CountFilled(zoo.AnimalTypes);
            int fair = FairValue(zoo, config);
            int visitors = 0;
            if (animals > 0)
            {
                double demand = ExpectedDemand(zoo, config, rating);
                double noise = 0.9 + rng.NextDouble() * 0.2;
                visitors = Math.Max(0, (int)Math.Round(demand * noise, MidpointRounding.AwayFromZero));
            }

            int income = visitors * Math.Max(0, config.TicketPrice);
            results.Add(new ZooResult(zoo.BuildingType, animals, species, habitats, fair, visitors, income));
            reviews.AddRange(CreateReviews(zoo, config, fair, visitors, rng));
        }

        int totalVisitors = results.Sum(zoo => zoo.Visitors);
        int totalIncome = results.Sum(zoo => zoo.Income);
        return new DailyIncome(results, totalIncome, totalVisitors, rating, reviews);
    }

    public static List<ZooReview> AppendReviews(IReadOnlyList<ZooReview>? previous, IEnumerable<ZooReview> fresh, int maxStored)
    {
        var combined = new List<ZooReview>();
        if (previous != null)
            combined.AddRange(previous);
        combined.AddRange(fresh);
        if (combined.Count > maxStored)
            combined.RemoveRange(0, combined.Count - maxStored);
        return combined;
    }

    public static IReadOnlyList<ZooReview> CreateReviews(
        ZooSnapshot zoo,
        ModConfig config,
        int fairValue,
        int visitors,
        Random rng)
    {
        if (visitors <= 0)
            return Array.Empty<ZooReview>();

        int sample = Math.Min(visitors, Math.Max(1, config.ReviewSampleSize));
        int animals = zoo.AnimalTypes.Count;
        int habitats = ZooHabitats.CountFilled(zoo.AnimalTypes);
        double ratio = config.TicketPrice <= 0 ? 0 : config.TicketPrice / (double)Math.Max(fairValue, 1);
        var reviews = new List<ZooReview>(sample);
        for (int i = 0; i < sample; i++)
            reviews.Add(RateVisit(animals, habitats, ratio, rng));
        return reviews;
    }

    public static ZooReview RateVisit(int animals, int habitats, double priceRatio, Random rng)
    {
        double quality = 0;
        if (animals >= 6)
            quality += 1.1;
        else if (animals >= 3)
            quality += 0.3;
        else if (animals <= 1)
            quality -= 1.4;

        if (habitats >= 4)
            quality += 0.8;
        else if (habitats <= 1)
            quality -= 0.6;

        if (priceRatio <= 0)
            quality += 0.4;
        else if (priceRatio >= 3)
            quality -= 1.6;
        else if (priceRatio >= 1.8)
            quality -= 0.9;
        else if (priceRatio <= 0.7)
            quality += 0.4;

        quality += (rng.NextDouble() - 0.5) * 0.8;
        int stars = Math.Clamp((int)Math.Round(StartingRating + quality, MidpointRounding.AwayFromZero), 1, 5);
        return new ZooReview(stars, PickTemplate(stars, animals, habitats, priceRatio), TopicOf(animals, habitats, priceRatio));
    }

    private static string TopicOf(int animals, int habitats, double priceRatio)
    {
        if (priceRatio >= 1.8)
            return "price";
        if (animals <= 1)
            return "animals";
        if (habitats <= 1)
            return "habitats";
        return "overall";
    }

    private static string PickTemplate(int stars, int animals, int habitats, double priceRatio)
    {
        if (priceRatio >= 1.8)
            return "review.price.high";
        if (priceRatio <= 0)
            return "review.price.free";
        if (priceRatio <= 0.7)
            return "review.price.low";
        if (animals <= 1)
            return "review.animals.few";
        if (animals >= 6)
            return "review.animals.many";
        if (habitats <= 1)
            return "review.habitats.few";
        if (habitats >= 4)
            return "review.habitats.many";
        if (stars >= 5)
            return "review.overall.great";
        if (stars <= 2)
            return "review.overall.bad";
        return "review.overall.ok";
    }
}
