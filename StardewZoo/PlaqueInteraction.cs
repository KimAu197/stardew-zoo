using System.Runtime.CompilerServices;
using HarmonyLib;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewValley;
using StardewValley.Menus;
using StardewValley.Objects;

namespace StardewZoo;

/// <summary>
/// Opens the read/edit menu when a player right-clicks (or presses action on) a zoo plaque, and shows its title on hover.
/// The text lives in the placed furniture's modData, which vanilla keeps on the same instance through pick-up and placement.
/// </summary>
/// <remarks>
/// Right-click on furniture goes through <see cref="Furniture.checkForAction"/>; pick-up is the separate left-click path
/// (<c>GameLocation.LowPriorityLeftClick</c>), so a prefix that claims the action for plaques leaves pick-up alone.
/// </remarks>
internal sealed class PlaqueInteraction
{
    public const string HarmonyId = "Kenzie.StardewZoo.Plaques";

    private static readonly ConditionalWeakTable<SpriteFont, Func<char, bool>> Glyphs = new();
    private static PlaqueInteraction? instance;

    private readonly ITranslationHelper translation;
    private readonly IMonitor monitor;
    private bool loggedError;

    public PlaqueInteraction(IModHelper helper, IMonitor monitor)
    {
        this.translation = helper.Translation;
        this.monitor = monitor;
        instance = this;

        new Harmony(HarmonyId).Patch(
            AccessTools.Method(typeof(Furniture), nameof(Furniture.checkForAction)),
            prefix: new HarmonyMethod(typeof(PlaqueInteraction), nameof(Before_CheckForAction))
        );
        helper.Events.Display.RenderedHud += this.OnRenderedHud;
    }

    public static PlaqueText Defaults(ITranslationHelper translation, string shortKey)
    {
        if (!ZooPlaques.HasDefault(shortKey))
            return PlaqueText.Empty;
        return new PlaqueText(
            ZooPlaques.CleanTitle(translation.Get(ZooPlaques.DefaultTitleKey(shortKey))),
            ZooPlaques.CleanBody(translation.Get(ZooPlaques.DefaultBodyKey(shortKey)))
        );
    }

    public static PlaqueText Read(Furniture furniture, ITranslationHelper translation, string shortKey)
    {
        furniture.modData.TryGetValue(ZooPlaques.TitleKey, out string? title);
        furniture.modData.TryGetValue(ZooPlaques.BodyKey, out string? body);
        return ZooPlaques.Resolve(title, body, Defaults(translation, shortKey));
    }

    public static void Write(Furniture furniture, PlaqueText text, PlaqueText defaults)
    {
        if (ZooPlaques.ToStore(text, defaults) is not { } stored)
        {
            furniture.modData.Remove(ZooPlaques.TitleKey);
            furniture.modData.Remove(ZooPlaques.BodyKey);
            return;
        }
        furniture.modData[ZooPlaques.TitleKey] = stored.Title;
        furniture.modData[ZooPlaques.BodyKey] = stored.Body;
    }

    /// <summary>The title of a titled plaque within <paramref name="radius"/> tiles, for visitor chatter.</summary>
    public static string? TitleNear(GameLocation location, Vector2 tile, int radius)
    {
        if (instance == null)
            return null;
        foreach (Furniture furniture in location.furniture)
        {
            string? key = ZooPlaques.ShortKey(furniture.QualifiedItemId);
            if (key == null || Math.Abs(furniture.TileLocation.X - tile.X) > radius || Math.Abs(furniture.TileLocation.Y - tile.Y) > radius)
                continue;
            string title = Read(furniture, instance.translation, key).Title;
            if (title.Length > 0)
                return title;
        }
        return null;
    }

    /// <summary>Whether <paramref name="font"/> has a glyph for a character; SpriteFont throws on unknown ones without a default.</summary>
    public static Func<char, bool> CanDraw(SpriteFont font)
    {
        return Glyphs.GetValue(font, f =>
        {
            if (f.DefaultCharacter != null)
                return _ => true;
            var set = new HashSet<char>(f.Characters);
            return c => set.Contains(c);
        });
    }

    public static string FontSafe(SpriteFont font, string text)
    {
        Func<char, bool> canDraw = CanDraw(font);
        return text.All(c => c == '\n' || canDraw(c)) ? text : new string(text.Select(c => c == '\n' || canDraw(c) ? c : '?').ToArray());
    }

    private static bool Before_CheckForAction(Furniture __instance, Farmer __0, bool __1, ref bool __result)
    {
        if (instance == null || __instance.Location == null || ZooPlaques.ShortKey(__instance.QualifiedItemId) is not { } key)
            return true;
        if (__1)
        {
            __result = true;
            return false;
        }
        if (!__0.IsLocalPlayer)
            return true;

        try
        {
            instance.Open(__instance, key);
        }
        catch (Exception ex)
        {
            if (!instance.loggedError)
                instance.monitor.Log($"Couldn't open the plaque menu.\n{ex}", LogLevel.Error);
            instance.loggedError = true;
            return true;
        }
        __result = true;
        return false;
    }

    private void Open(Furniture furniture, string key)
    {
        PlaqueText defaults = Defaults(this.translation, key);
        Game1.activeClickableMenu = new PlaqueMenu(
            furniture.DisplayName,
            Read(furniture, this.translation, key),
            defaults,
            ZooPlaques.HasDefault(key),
            this.translation,
            text =>
            {
                Write(furniture, text, defaults);
                Game1.addHUDMessage(new HUDMessage(this.translation.Get("plaque.menu.saved"), HUDMessage.newQuest_type));
            }
        );
    }

    private void OnRenderedHud(object? sender, RenderedHudEventArgs e)
    {
        if (!Context.IsPlayerFree || Game1.currentLocation is not { } location || location.furniture.Count == 0)
            return;

        bool mouse = !Game1.options.gamepadControls || Game1.lastCursorMotionWasMouse;
        Vector2 tile = mouse ? Game1.currentCursorTile : Game1.player.GetGrabTile();
        Furniture? plaque = PlaqueAt(location, tile, out string? key);
        if (plaque == null)
            return;
        string title = Read(plaque, this.translation, key!).Title;
        if (title.Length == 0)
            return;

        title = FontSafe(Game1.smallFont, title);
        if (mouse)
        {
            IClickableMenu.drawHoverText(e.SpriteBatch, title, Game1.smallFont);
            return;
        }
        Rectangle box = plaque.GetBoundingBox();
        Vector2 screen = Utility.ModifyCoordinatesForUIScale(Game1.GlobalToLocal(new Vector2(box.Right, box.Top - 64)));
        IClickableMenu.drawHoverText(e.SpriteBatch, title, Game1.smallFont, overrideX: (int)screen.X, overrideY: (int)screen.Y);
    }

    /// <summary>A plaque whose drawn sprite (not just its footprint) covers the tile, so hovering a signpost's board works too.</summary>
    private static Furniture? PlaqueAt(GameLocation location, Vector2 tile, out string? key)
    {
        var point = new Point((int)tile.X, (int)tile.Y);
        foreach (Furniture furniture in location.furniture)
        {
            key = ZooPlaques.ShortKey(furniture.QualifiedItemId);
            if (key == null)
                continue;
            Rectangle box = furniture.GetBoundingBox();
            Rectangle source = furniture.sourceRect.Value;
            int wide = Math.Max(1, source.Width / 16);
            int high = Math.Max(1, source.Height / 16);
            var sprite = new Rectangle(box.X / Game1.tileSize, box.Bottom / Game1.tileSize - high, wide, high);
            if (sprite.Contains(point))
                return furniture;
        }
        key = null;
        return null;
    }
}
