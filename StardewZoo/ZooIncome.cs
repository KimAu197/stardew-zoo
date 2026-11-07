namespace StardewZoo;

public record ZooSnapshot(string BuildingType, IReadOnlyList<string> AnimalTypes);

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

    public static double BaseDemand(ZooSnapshot zoo, ModConfig config)
    {
        int animals = zoo.AnimalTypes.Count;
        if (animals == 0)
            return 0;
        int species = zoo.AnimalTypes.Distinct().Count();
        int habitats = ZooHabitats.CountFilled(zoo.AnimalTypes);
        return (config.BaseVisitors + animals * config.VisitorsPerAnimal + species * config.VisitorsPerSpecies + habitats * config.VisitorsPerHabitat)
            * TierMultiplier(zoo.BuildingType, config);
    }

    public static double PriceFactor(int ticketPrice, int fairValue)
    {
        if (ticketPrice <= 0)
            return 1.75;
        double ratio = ticketPrice / (double)Math.Max(fairValue, 1);
        return Math.Clamp(1.0 / ratio, 0.1, 2.0);
    }

    public static double RatingFactor(double averageRating) => Math.Clamp(averageRating / StartingRating, 0.25, 1.75);

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
                double demand = BaseDemand(zoo, config) * PriceFactor(config.TicketPrice, fair) * RatingFactor(rating);
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
