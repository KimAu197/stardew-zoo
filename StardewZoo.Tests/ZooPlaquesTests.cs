using System.Text.Json;
using StardewZoo;
using Xunit;

public class ZooPlaquesTests
{
    /// <summary>Monospace stand-in for a SpriteFont: CJK is two units wide, everything else one.</summary>
    private static float Measure(string s) => s.Sum(c => ZooPlaques.IsCjk(c) ? 2 : 1);

    [Theory]
    [InlineData("(F)StardewZoo.PlaqueIce", "PlaqueIce")]
    [InlineData("(F)StardewZoo.SignpostSavannaJungle", "SignpostSavannaJungle")]
    [InlineData("(F)StardewZoo.ZooSign", "ZooSign")]
    [InlineData("(F)StardewZoo.PlaqueBlank", "PlaqueBlank")]
    [InlineData("(F)StardewZoo.NoticeBoard", "NoticeBoard")]
    public void ShortKey_RecognisesEditablePlaques(string qualifiedId, string expected)
    {
        Assert.Equal(expected, ZooPlaques.ShortKey(qualifiedId));
        Assert.True(ZooPlaques.IsPlaque(qualifiedId));
    }

    [Theory]
    [InlineData("(F)StardewZoo.Bench")]
    [InlineData("(F)StardewZoo.Fountain")]
    [InlineData("(F)PlaqueIce")]
    [InlineData("(O)StardewZoo.PlaqueIce")]
    [InlineData("")]
    [InlineData(null)]
    public void ShortKey_IgnoresOtherItems(string? qualifiedId)
    {
        Assert.Null(ZooPlaques.ShortKey(qualifiedId));
        Assert.False(ZooPlaques.IsPlaque(qualifiedId));
    }

    [Fact]
    public void BlankPlaques_HaveNoDefault_AndBiomePlaquesDo()
    {
        Assert.All(ZooPlaques.Blank, key => Assert.False(ZooPlaques.HasDefault(key)));
        Assert.True(ZooPlaques.HasDefault("PlaqueJungle"));
        Assert.Equal("plaque.default.PlaqueJungle.title", ZooPlaques.DefaultTitleKey("PlaqueJungle"));
        Assert.Equal("plaque.default.PlaqueJungle.body", ZooPlaques.DefaultBodyKey("PlaqueJungle"));
    }

    [Fact]
    public void ModDataKeys_AreNamespacedByMod()
    {
        Assert.Equal("Kenzie.StardewZoo/PlaqueTitle", ZooPlaques.TitleKey);
        Assert.Equal("Kenzie.StardewZoo/PlaqueBody", ZooPlaques.BodyKey);
    }

    [Fact]
    public void Resolve_UsesDefault_UntilSomethingIsStored()
    {
        var defaults = new PlaqueText("南极企鹅", "它们不会飞。");
        Assert.Equal(defaults, ZooPlaques.Resolve(null, null, defaults));
        Assert.Equal(new PlaqueText("我的企鹅", ""), ZooPlaques.Resolve("我的企鹅", null, defaults));
        Assert.Equal(new PlaqueText("", "正文"), ZooPlaques.Resolve(null, "正文", defaults));
    }

    [Fact]
    public void Resolve_StoredEmpty_OverridesDefault()
    {
        var defaults = new PlaqueText("南极企鹅", "它们不会飞。");
        Assert.True(ZooPlaques.Resolve("", "", defaults).IsEmpty);
    }

    [Fact]
    public void ToStore_ClearsKeys_WhenTextMatchesDefault()
    {
        var defaults = new PlaqueText("Penguins", "They can't fly.");
        Assert.Null(ZooPlaques.ToStore(defaults, defaults));
        Assert.Null(ZooPlaques.ToStore(PlaqueText.Empty, PlaqueText.Empty));
        Assert.Equal(PlaqueText.Empty, ZooPlaques.ToStore(PlaqueText.Empty, defaults));
        Assert.Equal(new PlaqueText("A", "B"), ZooPlaques.ToStore(new PlaqueText("A", "B"), PlaqueText.Empty));
    }

    [Fact]
    public void CleanTitle_FlattensTrimsAndLimits()
    {
        Assert.Equal("南极 企鹅", ZooPlaques.CleanTitle("  南极\n企鹅\t "));
        Assert.Equal(ZooPlaques.TitleLimit, ZooPlaques.CleanTitle(new string('长', 50)).Length);
        Assert.Equal("", ZooPlaques.CleanTitle(null));
    }

    [Fact]
    public void CleanBody_KeepsNewlines_LimitsLength_AndDropsUndrawable()
    {
        Assert.Equal("第一行\n第二行", ZooPlaques.CleanBody("\r\n第一行\r\n第二行\n\n  "));
        Assert.Equal(ZooPlaques.BodyLimit, ZooPlaques.CleanBody(new string('字', 500)).Length);
        Assert.Equal("ab", ZooPlaques.CleanBody("a😀b", c => !char.IsSurrogate(c)));
        Assert.Equal("ab", ZooPlaques.CleanBody("a\u0007b"));
    }

    [Fact]
    public void CleanBody_CapsParagraphs()
    {
        string many = string.Join('\n', Enumerable.Range(1, 20));
        string cleaned = ZooPlaques.CleanBody(many);
        Assert.Equal(ZooPlaques.MaxBodyParagraphs, cleaned.Split('\n').Length);
        Assert.EndsWith("8 9 10 11 12 13 14 15 16 17 18 19 20", cleaned);
    }

    [Fact]
    public void Clamp_DoesNotSplitSurrogatePairs()
    {
        Assert.Equal("ab", ZooPlaques.Clamp("ab😀", 3));
        Assert.Equal("ab😀", ZooPlaques.Clamp("ab😀", 4));
    }

    [Fact]
    public void Wrap_Chinese_BreaksByCharacter()
    {
        IReadOnlyList<string> lines = ZooPlaques.Wrap("企鹅是一种不会飞的鸟", 8, Measure);
        Assert.Equal(new[] { "企鹅是一", "种不会飞", "的鸟" }, lines);
    }

    [Fact]
    public void Wrap_Chinese_ClosingPunctuationHangsOnPreviousLine()
    {
        IReadOnlyList<string> lines = ZooPlaques.Wrap("企鹅很可爱。它们", 10, Measure);
        Assert.Equal(new[] { "企鹅很可爱。", "它们" }, lines);
    }

    [Fact]
    public void Wrap_English_BreaksAtSpaces()
    {
        IReadOnlyList<string> lines = ZooPlaques.Wrap("Penguins cannot fly at all", 12, Measure);
        Assert.Equal(new[] { "Penguins", "cannot fly", "at all" }, lines);
    }

    [Fact]
    public void Wrap_LongWord_BreaksByCharacter()
    {
        IReadOnlyList<string> lines = ZooPlaques.Wrap("Hippopotamus", 5, Measure);
        Assert.Equal(new[] { "Hippo", "potam", "us" }, lines);
    }

    [Fact]
    public void Wrap_MixedScripts()
    {
        IReadOnlyList<string> lines = ZooPlaques.Wrap("来看 Panda 熊猫吧", 10, Measure);
        Assert.Equal(new[] { "来看 Panda", "熊猫吧" }, lines);
    }

    [Fact]
    public void Wrap_KeepsExplicitNewlines_AndEmptyLines()
    {
        IReadOnlyList<string> lines = ZooPlaques.Wrap("第一行\n\nsecond", 20, Measure);
        Assert.Equal(new[] { "第一行", "", "second" }, lines);
    }

    [Fact]
    public void Wrap_Empty_IsOneEmptyLine()
    {
        Assert.Equal(new[] { "" }, ZooPlaques.Wrap("", 10, Measure));
    }

    [Theory]
    [InlineData("default.json")]
    [InlineData("zh.json")]
    public void EveryDefaultPlaque_HasTitleAndBody_WithinLimits(string file)
    {
        Dictionary<string, string> i18n = LoadI18n(file);
        foreach (string key in ZooPlaques.WithDefaults)
        {
            string title = i18n[ZooPlaques.DefaultTitleKey(key)];
            string body = i18n[ZooPlaques.DefaultBodyKey(key)];
            Assert.Equal(title, ZooPlaques.CleanTitle(title));
            Assert.Equal(body, ZooPlaques.CleanBody(body));
            Assert.NotEmpty(title);
            Assert.NotEmpty(body);
        }
    }

    private static Dictionary<string, string> LoadI18n(string file)
    {
        DirectoryInfo? dir = new(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "StardewZoo", "i18n", file)))
            dir = dir.Parent;
        Assert.NotNull(dir);
        string json = File.ReadAllText(Path.Combine(dir!.FullName, "StardewZoo", "i18n", file));
        return JsonSerializer.Deserialize<Dictionary<string, string>>(json)!;
    }
}
