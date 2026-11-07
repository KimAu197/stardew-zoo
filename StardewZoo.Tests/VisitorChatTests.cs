using System.Text.Json;
using StardewZoo;
using Xunit;

public class VisitorChatTests
{
    private static readonly string[] SomeSpecies = { ZooIds.Penguin, ZooIds.Lion, ZooIds.Panda, ZooIds.Owl, ZooIds.Giraffe, ZooIds.Monkey };

    private static VisitorChatSnapshot Stocked(int stars = 3) => new()
    {
        TicketPrice = 50,
        FairValue = 50,
        AverageRating = 3.5,
        ReviewCount = 10,
        SpeciesPresent = SomeSpecies,
        FavouriteSpecies = ZooIds.Lion,
        EmptyHabitats = new[] { ZooHabitats.Prehistoric },
        Stars = stars
    };

    private static List<ChatLine> Sample(VisitorChatSnapshot snapshot, int runs = 400)
    {
        var lines = new List<ChatLine>();
        for (int seed = 0; seed < runs; seed++)
            lines.Add(VisitorChat.Next(snapshot, new HashSet<string>(), new Random(seed)));
        return lines;
    }

    [Theory]
    [InlineData("Characters/SafariGuy", VisitorPersona.Explorer)]
    [InlineData("Characters/Marcello", VisitorPersona.Fancy)]
    [InlineData("Characters/Morris", VisitorPersona.Grumpy)]
    [InlineData("Characters/Birdie", VisitorPersona.Granny)]
    [InlineData(null, VisitorPersona.Explorer)]
    public void Persona_FollowsSprite(string? texture, VisitorPersona expected)
    {
        Assert.Equal(expected, VisitorChat.PersonaFor(texture));
    }

    [Theory]
    [InlineData(1, VisitorMood.Unhappy)]
    [InlineData(2, VisitorMood.Unhappy)]
    [InlineData(3, VisitorMood.Neutral)]
    [InlineData(4, VisitorMood.Happy)]
    [InlineData(5, VisitorMood.Happy)]
    public void Mood_FollowsReviewStars(int stars, VisitorMood expected)
    {
        Assert.Equal(expected, VisitorChat.MoodFor(stars));
    }

    [Theory]
    [InlineData(0, 50, "price.free")]
    [InlineData(20, 50, "price.bargain")]
    [InlineData(50, 50, "price.fair")]
    [InlineData(80, 50, "price.pricey")]
    [InlineData(200, 50, "price.outrageous")]
    public void PricePool_ComparesTicketToFairValue(int price, int fair, string expected)
    {
        Assert.Equal(expected, VisitorChat.PricePool(price, fair));
    }

    [Fact]
    public void RepeatedTalks_DontRepeatLines()
    {
        var used = new HashSet<string>();
        var rng = new Random(7);
        var keys = Enumerable.Range(0, 40).Select(_ => VisitorChat.Next(Stocked(), used, rng).Key).ToList();

        Assert.Equal(keys.Count, keys.Distinct().Count());
    }

    [Fact]
    public void AfterThreeTalks_SaysGoodbye()
    {
        var used = new HashSet<string>();
        for (int talk = 0; talk < 6; talk++)
        {
            ChatLine line = VisitorChat.Next(Stocked(5) with { TalkCount = talk }, used, new Random(talk));
            if (talk < VisitorChat.TalksBeforeGoodbye)
                Assert.DoesNotContain("goodbye", line.Key);
            else
                Assert.StartsWith("chat.goodbye.Happy.", line.Key);
        }
    }

    [Fact]
    public void SpeciesLines_OnlyForAnimalsPresent()
    {
        var present = SomeSpecies.Select(ZooIds.ShortName).ToHashSet();
        var speciesKeys = Sample(Stocked()).Where(l => l.Key.StartsWith("chat.species.")).ToList();

        Assert.NotEmpty(speciesKeys);
        Assert.All(speciesKeys, line => Assert.Contains(line.Key.Split('.')[2], present));
    }

    [Fact]
    public void NearestPen_IsTalkedAboutMost()
    {
        var lines = Sample(Stocked() with { NearestSpecies = ZooIds.Owl }, 1000);
        int owl = lines.Count(l => l.Key.StartsWith("chat.species.Owl."));
        int lion = lines.Count(l => l.Key.StartsWith("chat.species.Lion."));

        Assert.True(owl > lion * 3, $"owl {owl}, lion {lion}");
    }

    [Fact]
    public void EmptyZoo_NeverMentionsAnimals()
    {
        var snapshot = new VisitorChatSnapshot { TicketPrice = 50, FairValue = 0, EmptyHabitats = ZooHabitats.All.Select(h => h.Id).ToList() };
        var keys = Sample(snapshot).Select(l => l.Key).ToList();

        Assert.Contains(keys, k => k.StartsWith("chat.zoo.empty."));
        Assert.DoesNotContain(keys, k => k.StartsWith("chat.species.") || k.StartsWith("chat.habitat.full.") || k.StartsWith("chat.hint.pricier."));
    }

    [Fact]
    public void FreeEntry_TalksAboutFreeTicketsNotPrices()
    {
        var keys = Sample(Stocked() with { TicketPrice = 0 }).Select(l => l.Key).ToList();

        Assert.Contains(keys, k => k.StartsWith("chat.price.free."));
        Assert.DoesNotContain(keys, k => k.StartsWith("chat.price.pricey.") || k.StartsWith("chat.price.outrageous.") || k.StartsWith("chat.hint.cheaper."));
    }

    [Fact]
    public void Overpriced_HintsAtCheaperTickets()
    {
        var keys = Sample(Stocked() with { TicketPrice = 300 }).Select(l => l.Key).ToList();

        Assert.Contains(keys, k => k.StartsWith("chat.hint.cheaper."));
        Assert.Contains(keys, k => k.StartsWith("chat.price.outrageous."));
        Assert.DoesNotContain(keys, k => k.StartsWith("chat.hint.pricier.") || k.StartsWith("chat.price.bargain."));
    }

    [Fact]
    public void NearbyEmptyPen_IsNamed()
    {
        var lines = Sample(Stocked() with { NearestEmptyHabitat = ZooHabitats.Prehistoric });
        var empty = lines.Where(l => l.Key.StartsWith("chat.habitat.empty.")).ToList();

        Assert.NotEmpty(empty);
        Assert.All(empty, line => Assert.Equal(ZooHabitats.Prehistoric, line.Habitat));
    }

    [Fact]
    public void UnhappyVisitors_DontGush_AndHappyOnesDontComplain()
    {
        var unhappy = Sample(Stocked(1)).Select(l => l.Key).ToList();
        var happy = Sample(Stocked(5)).Select(l => l.Key).ToList();

        Assert.DoesNotContain(unhappy, k => k.Contains(".Happy.") || k.Contains(".Neutral."));
        Assert.DoesNotContain(happy, k => k.Contains(".Unhappy.") || k.Contains(".Neutral."));
        Assert.Contains(unhappy, k => k.StartsWith("chat.persona."));
    }

    [Fact]
    public void FavouriteSpecies_ComesFromPersonaList()
    {
        foreach (VisitorPersona persona in Enum.GetValues<VisitorPersona>())
        {
            for (int seed = 0; seed < 20; seed++)
                Assert.Contains(VisitorChat.PickFavourite(persona, new Random(seed)), ZooIds.AnimalTypes);
        }
    }

    [Fact]
    public void LeaveLine_MatchesReviewMood()
    {
        Assert.StartsWith("chat.leave.Happy.", VisitorChat.LeaveLine(5, new Random(1)).Key);
        Assert.StartsWith("chat.leave.Unhappy.", VisitorChat.LeaveLine(1, new Random(1)).Key);
    }

    [Theory]
    [InlineData("default.json")]
    [InlineData("zh.json")]
    public void Translations_CoverEveryChatLine(string file)
    {
        Dictionary<string, string> i18n = LoadI18n(file);
        var expected = VisitorChat.AllKeys()
            .Concat(ZooIds.AnimalTypes.Select(t => "visitor.species." + ZooIds.ShortName(t)))
            .Concat(ZooHabitats.All.Select(h => "visitor.habitat." + h.Id))
            .Append("visitor.speech")
            .ToList();

        Assert.Empty(expected.Where(key => !i18n.ContainsKey(key)));
        Assert.Empty(i18n.Keys.Where(key => key.StartsWith(VisitorChat.KeyPrefix) && !expected.Contains(key)));

        // Dialogue parses these as commands (#, $, ^, %, *, @, []) or SpriteText icons (<, >).
        char[] special = { '#', '$', '^', '%', '*', '@', '[', ']', '<', '>' };
        var bad = expected
            .Where(key => System.Text.RegularExpressions.Regex.Replace(i18n[key], @"\{\{\w+\}\}", "").IndexOfAny(special) >= 0)
            .ToList();
        Assert.Empty(bad);
    }

    private static Dictionary<string, string> LoadI18n(string file)
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "StardewZoo", "i18n", file)))
            dir = dir.Parent;
        Assert.NotNull(dir);
        string json = File.ReadAllText(Path.Combine(dir!.FullName, "StardewZoo", "i18n", file));
        return JsonSerializer.Deserialize<Dictionary<string, string>>(json)!;
    }
}
