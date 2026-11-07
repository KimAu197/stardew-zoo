namespace StardewZoo;

public enum VisitorPersona
{
    Explorer,
    Fancy,
    Grumpy,
    Granny
}

public enum VisitorMood
{
    Unhappy,
    Neutral,
    Happy
}

public enum VisitorWeather
{
    Sunny,
    Rain,
    Storm,
    Snow,
    Wind
}

/// <summary>What one visitor knows about the zoo at the moment the player talks to them.</summary>
public sealed record VisitorChatSnapshot
{
    public int TicketPrice { get; init; }
    public int FairValue { get; init; }
    public double AverageRating { get; init; } = ZooIncome.StartingRating;
    public int ReviewCount { get; init; }
    public IReadOnlyList<string> SpeciesPresent { get; init; } = Array.Empty<string>();
    public string? NearestSpecies { get; init; }
    public string? FavouriteSpecies { get; init; }
    public IReadOnlyList<string> EmptyHabitats { get; init; } = Array.Empty<string>();
    public string? NearestEmptyHabitat { get; init; }
    public int TimeOfDay { get; init; } = 1200;
    public VisitorWeather Weather { get; init; }
    public VisitorPersona Persona { get; init; }

    /// <summary>The stars this visitor's review will give, which sets their mood.</summary>
    public int Stars { get; init; } = 3;

    /// <summary>How many times the player already talked to this visitor today.</summary>
    public int TalkCount { get; init; }
}

/// <summary>An i18n key plus the species/habitat its tokens refer to.</summary>
public sealed record ChatLine(string Key, string? Species = null, string? Habitat = null);

public static class VisitorChat
{
    public const int TalksBeforeGoodbye = 3;
    public const string KeyPrefix = "chat.";

    /// <summary>Line pools and how many numbered variants each has in i18n (<c>chat.{pool}.{n}</c>, n from 1).</summary>
    public static readonly IReadOnlyDictionary<string, int> Pools = BuildPools();

    private static Dictionary<string, int> BuildPools()
    {
        var pools = new Dictionary<string, int>
        {
            ["price.free"] = 5,
            ["price.bargain"] = 6,
            ["price.fair"] = 5,
            ["price.pricey"] = 6,
            ["price.outrageous"] = 5,
            ["favorite.here"] = 5,
            ["favorite.missing"] = 5,
            ["habitat.empty"] = 6,
            ["habitat.full"] = 4,
            ["zoo.empty"] = 4,
            ["zoo.small"] = 4,
            ["rating.new"] = 4,
            ["rating.great"] = 5,
            ["rating.ok"] = 4,
            ["rating.poor"] = 5,
            ["time.morning"] = 4,
            ["time.midday"] = 4,
            ["time.afternoon"] = 4,
            ["weather.Sunny"] = 3,
            ["weather.Rain"] = 4,
            ["weather.Storm"] = 3,
            ["weather.Snow"] = 3,
            ["weather.Wind"] = 3,
            ["town"] = 6,
            ["farmer"] = 5,
            ["kids"] = 6,
            ["hint.cheaper"] = 4,
            ["hint.pricier"] = 4,
            ["hint.variety"] = 4,
            ["hint.habitat"] = 4,
            ["mood.Happy"] = 5,
            ["mood.Neutral"] = 4,
            ["mood.Unhappy"] = 5,
            ["goodbye.Happy"] = 4,
            ["goodbye.Neutral"] = 3,
            ["goodbye.Unhappy"] = 4,
            ["leave.Happy"] = 3,
            ["leave.Neutral"] = 3,
            ["leave.Unhappy"] = 3
        };
        foreach (string species in ZooIds.AnimalTypes)
            pools["species." + ZooIds.ShortName(species)] = 4;
        foreach (VisitorPersona persona in Enum.GetValues<VisitorPersona>())
        {
            foreach (VisitorMood mood in Enum.GetValues<VisitorMood>())
                pools[$"persona.{persona}.{mood}"] = 3;
        }
        return pools;
    }

    private static readonly IReadOnlyDictionary<VisitorPersona, string[]> Favourites = new Dictionary<VisitorPersona, string[]>
    {
        [VisitorPersona.Explorer] = new[] { ZooIds.Lion, ZooIds.Elephant, ZooIds.Gorilla, ZooIds.Dinosaur, ZooIds.NightHeron, ZooIds.Owl },
        [VisitorPersona.Fancy] = new[] { ZooIds.Flamingo, ZooIds.Panda, ZooIds.Giraffe, ZooIds.Alpaca, ZooIds.Penguin },
        [VisitorPersona.Grumpy] = new[] { ZooIds.Owl, ZooIds.Bear, ZooIds.Gorilla, ZooIds.Raccoon, ZooIds.SeaLion, ZooIds.Lion },
        [VisitorPersona.Granny] = new[] { ZooIds.Penguin, ZooIds.Capybara, ZooIds.Alpaca, ZooIds.Deer, ZooIds.Monkey, ZooIds.Panda }
    };

    public static VisitorPersona PersonaFor(string? textureName)
    {
        if (textureName == null)
            return VisitorPersona.Explorer;
        if (textureName.Contains("Marcello", StringComparison.OrdinalIgnoreCase))
            return VisitorPersona.Fancy;
        if (textureName.Contains("Morris", StringComparison.OrdinalIgnoreCase))
            return VisitorPersona.Grumpy;
        if (textureName.Contains("Birdie", StringComparison.OrdinalIgnoreCase))
            return VisitorPersona.Granny;
        return VisitorPersona.Explorer;
    }

    public static VisitorMood MoodFor(int stars) => stars >= 4 ? VisitorMood.Happy : stars <= 2 ? VisitorMood.Unhappy : VisitorMood.Neutral;

    public static string PickFavourite(VisitorPersona persona, Random rng)
    {
        string[] options = Favourites[persona];
        return options[rng.Next(options.Length)];
    }

    public static double PriceRatio(int ticketPrice, int fairValue) =>
        ticketPrice <= 0 ? 0 : ticketPrice / (double)Math.Max(fairValue, 1);

    public static string PricePool(int ticketPrice, int fairValue)
    {
        if (ticketPrice <= 0)
            return "price.free";
        double ratio = PriceRatio(ticketPrice, fairValue);
        if (ratio <= 0.7)
            return "price.bargain";
        if (ratio <= 1.3)
            return "price.fair";
        if (ratio <= 1.8)
            return "price.pricey";
        return "price.outrageous";
    }

    public static string TimePool(int timeOfDay) =>
        timeOfDay < 1100 ? "time.morning" : timeOfDay < 1400 ? "time.midday" : "time.afternoon";

    public static string RatingPool(double averageRating, int reviewCount)
    {
        if (reviewCount <= 0)
            return "rating.new";
        if (averageRating >= 4.0)
            return "rating.great";
        if (averageRating >= 2.8)
            return "rating.ok";
        return "rating.poor";
    }

    /// <summary>Picks the next line for a visitor, avoiding keys in <paramref name="used"/>, and records the pick there.</summary>
    public static ChatLine Next(VisitorChatSnapshot snapshot, ISet<string> used, Random rng)
    {
        VisitorMood mood = MoodFor(snapshot.Stars);
        if (snapshot.TalkCount >= TalksBeforeGoodbye)
            return PickAllowingRepeats(new Candidate("goodbye." + mood, 1), used, rng);

        List<Candidate> candidates = BuildCandidates(snapshot, mood);
        while (candidates.Count > 0)
        {
            Candidate candidate = PickWeighted(candidates, rng);
            string? key = PickUnusedVariant(candidate.Pool, used, rng);
            if (key != null)
            {
                used.Add(key);
                return new ChatLine(key, candidate.Species, candidate.Habitat);
            }
            candidates.Remove(candidate);
        }

        return PickAllowingRepeats(new Candidate("mood." + mood, 1), used, rng);
    }

    /// <summary>A short line said aloud (above their head) as the visitor leaves.</summary>
    public static ChatLine LeaveLine(int stars, Random rng) =>
        new(Key("leave." + MoodFor(stars), rng.Next(Pools["leave." + MoodFor(stars)]) + 1));

    public static IEnumerable<string> AllKeys()
    {
        foreach ((string pool, int count) in Pools)
        {
            for (int i = 1; i <= count; i++)
                yield return Key(pool, i);
        }
    }

    private static string Key(string pool, int variant) => $"{KeyPrefix}{pool}.{variant}";

    private sealed record Candidate(string Pool, double Weight, string? Species = null, string? Habitat = null);

    private static List<Candidate> BuildCandidates(VisitorChatSnapshot s, VisitorMood mood)
    {
        var list = new List<Candidate>();
        bool hasAnimals = s.SpeciesPresent.Count > 0;
        double ratio = PriceRatio(s.TicketPrice, s.FairValue);
        bool overpriced = s.TicketPrice > 0 && (ratio > 1.3 || !hasAnimals);
        bool underpriced = s.TicketPrice <= 0 || ratio < 0.7;

        string pricePool = hasAnimals ? PricePool(s.TicketPrice, s.FairValue) : s.TicketPrice <= 0 ? "price.free" : "price.outrageous";
        bool extremePrice = pricePool is "price.free" or "price.bargain" or "price.outrageous";
        list.Add(new Candidate(pricePool, extremePrice ? 3 : 2));

        if (!hasAnimals)
        {
            list.Add(new Candidate("zoo.empty", 8));
        }
        else
        {
            string? near = s.NearestSpecies != null && s.SpeciesPresent.Contains(s.NearestSpecies) ? s.NearestSpecies : null;
            if (near != null)
                list.Add(new Candidate("species." + ZooIds.ShortName(near), 5, near));
            foreach (string species in s.SpeciesPresent.Distinct().Where(sp => sp != near && Pools.ContainsKey("species." + ZooIds.ShortName(sp))))
                list.Add(new Candidate("species." + ZooIds.ShortName(species), 3.0 / s.SpeciesPresent.Distinct().Count(), species));
            if (s.SpeciesPresent.Distinct().Count() <= 2)
                list.Add(new Candidate("zoo.small", 2));
        }

        if (s.FavouriteSpecies != null)
        {
            bool here = s.SpeciesPresent.Contains(s.FavouriteSpecies);
            list.Add(new Candidate(here ? "favorite.here" : "favorite.missing", 2, s.FavouriteSpecies));
        }

        if (s.NearestEmptyHabitat != null)
            list.Add(new Candidate("habitat.empty", 3, Habitat: s.NearestEmptyHabitat));
        else if (hasAnimals && s.EmptyHabitats.Count == 0)
            list.Add(new Candidate("habitat.full", 1));

        list.Add(new Candidate(RatingPool(s.AverageRating, s.ReviewCount), 2));

        list.Add(new Candidate(TimePool(s.TimeOfDay), 1));
        list.Add(new Candidate("weather." + s.Weather, 1));
        list.Add(new Candidate("town", 1));
        list.Add(new Candidate("farmer", 1));
        list.Add(new Candidate("kids", 1));

        if (overpriced)
            list.Add(new Candidate("hint.cheaper", mood == VisitorMood.Unhappy ? 3 : 2));
        if (hasAnimals && underpriced)
            list.Add(new Candidate("hint.pricier", 1));
        if (hasAnimals && s.SpeciesPresent.Distinct().Count() < 5)
            list.Add(new Candidate("hint.variety", 1));
        if (hasAnimals && s.EmptyHabitats.Count > 0)
            list.Add(new Candidate("hint.habitat", 1, Habitat: s.EmptyHabitats[0]));

        list.Add(new Candidate($"persona.{s.Persona}.{mood}", 3));
        list.Add(new Candidate("mood." + mood, 2));
        return list;
    }

    private static Candidate PickWeighted(List<Candidate> candidates, Random rng)
    {
        double total = candidates.Sum(c => c.Weight);
        double roll = rng.NextDouble() * total;
        foreach (Candidate candidate in candidates)
        {
            roll -= candidate.Weight;
            if (roll < 0)
                return candidate;
        }
        return candidates[^1];
    }

    private static string? PickUnusedVariant(string pool, ISet<string> used, Random rng)
    {
        if (!Pools.TryGetValue(pool, out int count))
            return null;
        var free = Enumerable.Range(1, count).Select(i => Key(pool, i)).Where(key => !used.Contains(key)).ToList();
        return free.Count == 0 ? null : free[rng.Next(free.Count)];
    }

    private static ChatLine PickAllowingRepeats(Candidate candidate, ISet<string> used, Random rng)
    {
        string? key = PickUnusedVariant(candidate.Pool, used, rng);
        if (key == null)
        {
            for (int i = 1; i <= Pools[candidate.Pool]; i++)
                used.Remove(Key(candidate.Pool, i));
            key = Key(candidate.Pool, rng.Next(Pools[candidate.Pool]) + 1);
        }
        used.Add(key);
        return new ChatLine(key, candidate.Species, candidate.Habitat);
    }
}
