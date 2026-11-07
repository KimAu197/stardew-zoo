using System.Text;

namespace StardewZoo;

/// <summary>A plaque's player-facing text.</summary>
public readonly record struct PlaqueText(string Title, string Body)
{
    public static readonly PlaqueText Empty = new("", "");

    public bool IsEmpty => this.Title.Length == 0 && this.Body.Length == 0;
}

/// <summary>Which zoo furniture carries editable text, where that text lives in modData, and how it is cleaned and wrapped.</summary>
public static class ZooPlaques
{
    public const string TitleKey = "Kenzie.StardewZoo/PlaqueTitle";
    public const string BodyKey = "Kenzie.StardewZoo/PlaqueBody";

    public const int TitleLimit = 20;
    public const int BodyLimit = 200;

    /// <summary>Hard paragraph cap so a body of bare newlines can't outgrow the reading box.</summary>
    public const int MaxBodyParagraphs = 8;

    /// <summary>Plaques that start with an i18n description (<c>plaque.default.{key}.title/body</c>).</summary>
    public static readonly IReadOnlyList<string> WithDefaults = new[]
    {
        "PlaqueIce", "PlaqueWater", "PlaqueSavanna", "PlaqueJungle", "PlaqueForest", "PlaquePrehistoric",
        "SignpostIceWater", "SignpostSavannaJungle", "SignpostForestPrehistoric", "ZooSign"
    };

    /// <summary>Plaques sold blank.</summary>
    public static readonly IReadOnlyList<string> Blank = new[] { "PlaqueBlank", "NoticeBoard" };

    private const string ClosingPunctuation = "，。、；：！？）》」』】〉…—,.;:!?)]}%";

    /// <summary>The furniture key (after <see cref="ZooIds.FurniturePrefix"/>) if the item is an editable plaque.</summary>
    public static string? ShortKey(string? qualifiedItemId)
    {
        if (qualifiedItemId == null || !qualifiedItemId.StartsWith(ZooIds.FurniturePrefix, StringComparison.Ordinal))
            return null;
        string key = qualifiedItemId[ZooIds.FurniturePrefix.Length..];
        return WithDefaults.Contains(key) || Blank.Contains(key) ? key : null;
    }

    public static bool IsPlaque(string? qualifiedItemId) => ShortKey(qualifiedItemId) != null;

    public static bool HasDefault(string shortKey) => WithDefaults.Contains(shortKey);

    public static string DefaultTitleKey(string shortKey) => $"plaque.default.{shortKey}.title";

    public static string DefaultBodyKey(string shortKey) => $"plaque.default.{shortKey}.body";

    /// <summary>Stored text wins once either field is set; otherwise the (language-following) default shows.</summary>
    public static PlaqueText Resolve(string? storedTitle, string? storedBody, PlaqueText defaults)
    {
        if (storedTitle == null && storedBody == null)
            return defaults;
        return new PlaqueText(storedTitle ?? "", storedBody ?? "");
    }

    /// <summary>What to write to modData after an edit, or null to clear the keys because the text is just the default.</summary>
    public static PlaqueText? ToStore(PlaqueText edited, PlaqueText defaults) => edited == defaults ? null : edited;

    /// <summary>One line: no control characters or line breaks, trimmed, at most <see cref="TitleLimit"/> characters.</summary>
    public static string CleanTitle(string? text, Func<char, bool>? canDraw = null)
    {
        string flat = Normalize(text).Replace('\n', ' ');
        return Clamp(Filter(flat, keepNewlines: false, canDraw).Trim(), TitleLimit).TrimEnd();
    }

    /// <summary>Multi-line: at most <see cref="MaxBodyParagraphs"/> paragraphs and <see cref="BodyLimit"/> characters, trailing space removed.</summary>
    public static string CleanBody(string? text, Func<char, bool>? canDraw = null)
    {
        string filtered = Filter(Normalize(text), keepNewlines: true, canDraw).Trim('\n').TrimEnd();
        string[] paragraphs = filtered.Split('\n');
        if (paragraphs.Length > MaxBodyParagraphs)
            filtered = string.Join('\n', paragraphs.Take(MaxBodyParagraphs - 1)) + "\n" + string.Join(' ', paragraphs.Skip(MaxBodyParagraphs - 1));
        return Clamp(filtered, BodyLimit).TrimEnd();
    }

    /// <summary>Cuts to <paramref name="limit"/> UTF-16 units without splitting a surrogate pair.</summary>
    public static string Clamp(string text, int limit)
    {
        if (text.Length <= limit)
            return text;
        int cut = limit;
        if (cut > 0 && char.IsHighSurrogate(text[cut - 1]))
            cut--;
        return text[..cut];
    }

    /// <summary>
    /// Word-wraps to <paramref name="maxWidth"/>: Latin text breaks at spaces (over-long words by character), CJK breaks
    /// between any two characters, closing punctuation never starts a line, and explicit newlines are kept.
    /// </summary>
    public static IReadOnlyList<string> Wrap(string text, float maxWidth, Func<string, float> measure)
    {
        var lines = new List<string>();
        foreach (string paragraph in Normalize(text).Split('\n'))
            WrapParagraph(paragraph, maxWidth, measure, lines);
        return lines;
    }

    /// <summary>CJK ideographs, kana, hangul and full-width forms, which wrap per character.</summary>
    public static bool IsCjk(char c) =>
        c is >= '\u2E80' and <= '\u9FFF' or >= '\uAC00' and <= '\uD7AF' or >= '\uF900' and <= '\uFAFF' or >= '\uFF00' and <= '\uFFEF';

    private static void WrapParagraph(string paragraph, float maxWidth, Func<string, float> measure, List<string> lines)
    {
        var line = new StringBuilder();
        bool wrapped = false;

        void Flush()
        {
            lines.Add(line.ToString().TrimEnd());
            line.Clear();
            wrapped = true;
        }

        foreach (string token in Tokenize(paragraph))
        {
            bool space = token.All(char.IsWhiteSpace);
            if (space && line.Length == 0 && wrapped)
                continue;
            if (measure(line + token) <= maxWidth)
            {
                line.Append(token);
                continue;
            }
            if (space)
            {
                Flush();
                continue;
            }
            if (line.Length > 0 && token.Length == 1 && ClosingPunctuation.Contains(token[0]))
            {
                line.Append(token);
                continue;
            }
            if (line.Length > 0)
                Flush();
            if (measure(token) <= maxWidth)
            {
                line.Append(token);
                continue;
            }
            foreach (string ch in Characters(token))
            {
                if (line.Length > 0 && measure(line + ch) > maxWidth)
                    Flush();
                line.Append(ch);
            }
        }
        lines.Add(line.ToString().TrimEnd());
    }

    /// <summary>Space runs, Latin word runs, and single CJK characters (or surrogate pairs).</summary>
    private static IEnumerable<string> Tokenize(string text)
    {
        var word = new StringBuilder();
        for (int i = 0; i < text.Length; i++)
        {
            char c = text[i];
            bool pair = char.IsHighSurrogate(c) && i + 1 < text.Length && char.IsLowSurrogate(text[i + 1]);
            if (pair || IsCjk(c) || char.IsWhiteSpace(c))
            {
                bool continuesSpaces = char.IsWhiteSpace(c) && word.Length > 0 && char.IsWhiteSpace(word[^1]);
                if (!continuesSpaces && word.Length > 0)
                {
                    yield return word.ToString();
                    word.Clear();
                }
                if (char.IsWhiteSpace(c))
                {
                    word.Append(c);
                    continue;
                }
                yield return pair ? text.Substring(i++, 2) : c.ToString();
                continue;
            }
            if (word.Length > 0 && char.IsWhiteSpace(word[^1]))
            {
                yield return word.ToString();
                word.Clear();
            }
            word.Append(c);
        }
        if (word.Length > 0)
            yield return word.ToString();
    }

    private static IEnumerable<string> Characters(string token)
    {
        for (int i = 0; i < token.Length; i++)
        {
            if (char.IsHighSurrogate(token[i]) && i + 1 < token.Length)
                yield return token.Substring(i++, 2);
            else
                yield return token[i].ToString();
        }
    }

    private static string Normalize(string? text) => (text ?? "").Replace("\r\n", "\n").Replace('\r', '\n');

    private static string Filter(string text, bool keepNewlines, Func<char, bool>? canDraw)
    {
        var sb = new StringBuilder(text.Length);
        foreach (char c in text)
        {
            if (c == '\n')
            {
                if (keepNewlines)
                    sb.Append(c);
                continue;
            }
            if (c == '\t')
            {
                sb.Append(' ');
                continue;
            }
            if (char.IsControl(c) || (canDraw != null && !canDraw(c)))
                continue;
            sb.Append(c);
        }
        return sb.ToString();
    }
}
