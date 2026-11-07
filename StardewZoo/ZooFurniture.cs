using System.Runtime.CompilerServices;
using HarmonyLib;
using Microsoft.Xna.Framework;
using StardewModdingAPI;
using StardewValley;
using StardewValley.Objects;
using xTile;

namespace StardewZoo;

/// <summary>
/// Keeps player furniture in zoo locations out of pens, off the visitor route (rugs excepted) and away from booths and doors.
/// Vanilla already allows furniture in building interiors (they aren't outdoors); this only narrows where.
/// </summary>
/// <remarks>
/// Harmony is needed because the only vanilla per-tile rule, the <c>NoFurniture</c> Back property, also refuses rugs indoors
/// and lives in the map asset. A postfix on <see cref="Furniture.canBePlacedHere"/> gives the vanilla red placement
/// highlight and refusal for every input method while letting rugs sit on paths.
/// </remarks>
internal sealed class ZooFurniture
{
    public const string HarmonyId = "Kenzie.StardewZoo.Furniture";

    private sealed class CachedLayout
    {
        public Map? Map;
        public int WarpCount;
        public FurnitureLayout Layout = null!;
    }

    private static readonly ConditionalWeakTable<GameLocation, CachedLayout> Layouts = new();
    private static ZooFurniture? instance;

    private readonly IMonitor monitor;
    private readonly ITranslationHelper translation;
    private int lastWarnTick = -1000;
    private bool loggedError;

    public ZooFurniture(IModHelper helper, IMonitor monitor)
    {
        this.monitor = monitor;
        this.translation = helper.Translation;
        instance = this;

        var harmony = new Harmony(HarmonyId);
        harmony.Patch(
            AccessTools.Method(typeof(Furniture), nameof(Furniture.canBePlacedHere)),
            postfix: new HarmonyMethod(typeof(ZooFurniture), nameof(After_CanBePlacedHere))
        );
    }

    /// <summary>Furniture pieces in a location, for the zoo decor bonus.</summary>
    public static int DecorCount(GameLocation location) => location.furniture.Count;

    public static FurnitureLayout LayoutFor(GameLocation location)
    {
        Map map = location.Map;
        if (Layouts.TryGetValue(location, out CachedLayout? cached) && cached.Map == map && cached.WarpCount == location.warps.Count)
            return cached.Layout;

        cached = new CachedLayout { Map = map, WarpCount = location.warps.Count, Layout = FurnitureLayout.Build(BuildInput(location)) };
        Layouts.AddOrUpdate(location, cached);
        return cached.Layout;
    }

    private static FurnitureLayoutInput BuildInput(GameLocation location)
    {
        Map map = location.Map;
        int width = map.Layers[0].LayerWidth;
        int height = map.Layers[0].LayerHeight;

        var pens = new List<HabitatRect>();
        var waypoints = new List<(int X, int Y)>();
        if (ZooLocations.IsZooInterior(location))
        {
            pens.AddRange(ZooHabitats.All);
            waypoints.AddRange(ZooHabitats.VisitorLoop);
        }
        if (location.TryGetMapProperty(ZooLocations.NoFurnitureProperty, out string? noFurniture))
            pens.AddRange(FurnitureLayout.ParseRects(noFurniture, ZooLocations.NoFurnitureProperty));
        if (location.TryGetMapProperty(ZooLocations.WaypointsProperty, out string? waypointList))
            waypoints.AddRange(FurnitureLayout.ParsePoints(waypointList));

        var interactions = new List<(int X, int Y)>();
        for (int y = 0; y < height; y++)
        {
            for (int x = 0; x < width; x++)
            {
                if (location.doesTileHaveProperty(x, y, "Action", "Buildings") != null
                    || location.doesTileHaveProperty(x, y, "TouchAction", "Back") != null)
                    interactions.Add((x, y));
            }
        }

        return new FurnitureLayoutInput
        {
            Width = width,
            Height = height,
            Walkable = (x, y) => location.hasTileAt(x, y, "Back")
                && !location.isWaterTile(x, y)
                && location.isTilePassable(new Vector2(x, y)),
            Pens = pens,
            Waypoints = waypoints,
            InteractionTiles = interactions,
            WarpTiles = location.warps.Select(warp => (warp.X, warp.Y)).ToList()
        };
    }

    private static void After_CanBePlacedHere(Furniture __instance, GameLocation __0, Vector2 __1, ref bool __result)
    {
        if (!__result || instance == null || !ZooLocations.IsZooLocation(__0))
            return;

        try
        {
            instance.Apply(__instance, __0, __1, ref __result);
        }
        catch (Exception ex)
        {
            if (!instance.loggedError)
                instance.monitor.Log($"Zoo furniture rules failed; placement left to vanilla.\n{ex}", LogLevel.Error);
            instance.loggedError = true;
        }
    }

    private void Apply(Furniture furniture, GameLocation location, Vector2 tile, ref bool result)
    {
        int wide = furniture.getTilesWide();
        int high = furniture.getTilesHigh();
        if (wide == 1 && high == 1 && IsOnFreeTable(location, tile))
            return;

        bool passable = furniture.furniture_type.Value == Furniture.rug;
        FurnitureBlock block = LayoutFor(location).Check((int)tile.X, (int)tile.Y, wide, high, passable);
        if (block == FurnitureBlock.None)
            return;

        result = false;
        if (Game1.player.ActiveObject == furniture && Game1.didPlayerJustLeftClick(ignoreNonMouseHeldInput: true) && Game1.ticks - this.lastWarnTick > 30)
        {
            this.lastWarnTick = Game1.ticks;
            Game1.showRedMessage(this.translation.Get("furniture.blocked." + block.ToString().ToLowerInvariant()));
        }
    }

    /// <summary>Mirrors the vanilla shortcut that sets a 1x1 item onto an empty table instead of the floor.</summary>
    private static bool IsOnFreeTable(GameLocation location, Vector2 tile)
    {
        var center = new Point((int)(tile.X * Game1.tileSize) + Game1.tileSize / 2, (int)(tile.Y * Game1.tileSize) + Game1.tileSize / 2);
        return location.furniture.Any(f => f.furniture_type.Value == Furniture.table && f.heldObject.Value == null && f.GetBoundingBox().Contains(center));
    }
}
