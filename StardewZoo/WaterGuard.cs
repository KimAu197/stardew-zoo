using System.Runtime.CompilerServices;
using HarmonyLib;
using Microsoft.Xna.Framework;
using StardewModdingAPI;
using StardewValley;
using xTile;

namespace StardewZoo;

/// <summary>
/// Reads the zoo map's <see cref="ZooWater.TileProperty"/> water tiles and keeps zoo animals out of water their species
/// can't enter.
/// </summary>
/// <remarks>
/// Vanilla farm-animal collision only stops at Buildings tiles and Back tiles marked <c>Passable</c>; a Back <c>Passable</c>
/// tag would also stop swimmers before they start swimming and strand fliers that land on it. A postfix on
/// <see cref="GameLocation.isCollidingPosition(Rectangle, xTile.Dimensions.Rectangle, bool, int, bool, Character, bool, bool, bool, bool)"/>
/// makes vanilla wandering, spawning and pathfinding treat forbidden water as a wall, per species.
/// </remarks>
internal static class WaterGuard
{
    public const string HarmonyId = "Kenzie.StardewZoo.Water";

    private const string AnimalTypePrefix = "StardewZoo.";

    private sealed class WaterMap
    {
        public WaterMap(int width, int height)
        {
            this.Width = width;
            this.Height = height;
            this.Cells = new WaterKind[width * height];
        }

        public int Width { get; }
        public int Height { get; }
        public WaterKind[] Cells { get; }
        public bool HasWater { get; set; }

        public WaterKind KindAt(int x, int y) =>
            x >= 0 && y >= 0 && x < this.Width && y < this.Height ? this.Cells[y * this.Width + x] : WaterKind.None;
    }

    private static readonly ConditionalWeakTable<Map, WaterMap> Maps = new();
    private static IMonitor? monitor;
    private static bool loggedError;

    public static void Apply(IMonitor log)
    {
        monitor = log;
        var harmony = new Harmony(HarmonyId);
        harmony.Patch(
            AccessTools.Method(typeof(GameLocation), nameof(GameLocation.isCollidingPosition), new[]
            {
                typeof(Rectangle), typeof(xTile.Dimensions.Rectangle), typeof(bool), typeof(int), typeof(bool), typeof(Character),
                typeof(bool), typeof(bool), typeof(bool), typeof(bool)
            }),
            postfix: new HarmonyMethod(typeof(WaterGuard), nameof(After_IsCollidingPosition))
        );
    }

    /// <summary>The water kind of each tile of the location's current map.</summary>
    public static Func<int, int, WaterKind> KindsFor(GameLocation location) => Get(location).KindAt;

    /// <summary>Whether a zoo animal is allowed where it currently stands (asleep, no animal stays in water).</summary>
    public static bool IsOnAllowedGround(GameLocation location, FarmAnimal animal)
    {
        Rectangle box = animal.GetBoundingBox();
        return ZooWater.CanOccupy(box.Left, box.Top, box.Right, box.Bottom, AccessFor(animal), KindsFor(location));
    }

    public static WaterAccess AccessFor(FarmAnimal animal) => ZooWater.AccessFor(animal.type.Value, asleep: Game1.timeOfDay >= 2000);

    private static void After_IsCollidingPosition(GameLocation __instance, Rectangle position, Character character, ref bool __result)
    {
        if (__result || character is not FarmAnimal animal || animal.type.Value?.StartsWith(AnimalTypePrefix, StringComparison.Ordinal) != true)
            return;
        try
        {
            WaterAccess access = AccessFor(animal);
            if (access == WaterAccess.Any)
                return;
            WaterMap water = Get(__instance);
            if (water.HasWater && !ZooWater.CanOccupy(position.Left, position.Top, position.Right, position.Bottom, access, water.KindAt))
                __result = true;
        }
        catch (Exception ex)
        {
            if (!loggedError)
            {
                loggedError = true;
                monitor?.Log($"Zoo water check failed; animals may walk into water.\n{ex}", LogLevel.Error);
            }
        }
    }

    private static WaterMap Get(GameLocation location)
    {
        Map map = location.Map;
        if (Maps.TryGetValue(map, out WaterMap? cached))
            return cached;

        xTile.Layers.Layer? back = map.GetLayer("Back");
        var water = new WaterMap(back?.LayerWidth ?? 0, back?.LayerHeight ?? 0);
        for (int y = 0; y < water.Height; y++)
        {
            for (int x = 0; x < water.Width; x++)
            {
                WaterKind kind = ZooWater.Parse(location.doesTileHaveProperty(x, y, ZooWater.TileProperty, "Back"));
                water.Cells[y * water.Width + x] = kind;
                water.HasWater |= kind != WaterKind.None;
            }
        }
        Maps.AddOrUpdate(map, water);
        return water;
    }
}
