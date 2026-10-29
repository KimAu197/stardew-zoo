namespace StardewZoo;

public record ZooSnapshot(string BuildingType, IReadOnlyList<string> AnimalTypes);

public record ZooResult(string BuildingType, int AnimalCount, int SpeciesCount, int Income);

public record DailyIncome(IReadOnlyList<ZooResult> Zoos, int TotalIncome, int Visitors);

public static class ZooIncome
{
    public static DailyIncome Calculate(IEnumerable<ZooSnapshot> zoos, ModConfig config)
    {
        var results = new List<ZooResult>();
        foreach (ZooSnapshot zoo in zoos)
        {
            int animals = zoo.AnimalTypes.Count;
            int species = zoo.AnimalTypes.Distinct().Count();
            double multiplier = config.Multipliers.TryGetValue(zoo.BuildingType, out double value) ? value : 1.0;
            double raw = (animals * config.PricePerAnimal + species * config.PricePerSpecies) * multiplier;
            int income = (int)Math.Round(raw, MidpointRounding.AwayFromZero);

            results.Add(new ZooResult(zoo.BuildingType, animals, species, income));
        }

        int total = results.Sum(p => p.Income);
        int visitors = config.TicketPrice > 0 ? total / config.TicketPrice : 0;
        return new DailyIncome(results, total, visitors);
    }
}
