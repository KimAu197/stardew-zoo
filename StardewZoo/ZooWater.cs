namespace StardewZoo;

public enum WaterKind : byte
{
    None,

    /// <summary>A wading shelf, shoreline or stream.</summary>
    Shallow,

    /// <summary>Open water.</summary>
    Deep
}

/// <summary>Which water a species may stand in.</summary>
public enum WaterAccess
{
    None,
    Shallow,
    Any
}

/// <summary>
/// Zoo water rules. The map deliberately has no vanilla <c>Water</c> property (that would make vanilla treat the pens as
/// fishing water), so vanilla animal collision walks straight across pools. tools/make_map.py instead tags every pen water
/// tile with the <see cref="TileProperty"/> Back-tile property, and these rules decide who may enter it.
/// </summary>
public static class ZooWater
{
    public const string TileProperty = "ZooWater";

    private const int TileSize = 64;

    /// <summary>Any value other than <c>Deep</c> counts as shallow water.</summary>
    public static WaterKind Parse(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return WaterKind.None;
        return value.Trim().Equals("Deep", StringComparison.OrdinalIgnoreCase) ? WaterKind.Deep : WaterKind.Shallow;
    }

    /// <param name="animalType">The farm animal type.</param>
    /// <param name="asleep">After 8pm vanilla clears <c>isSwimming</c>, so an animal left in water would be drawn standing on it.</param>
    public static WaterAccess AccessFor(string? animalType, bool asleep = false) =>
        asleep ? WaterAccess.None : MoveProfiles.For(animalType).Water;

    public static bool CanEnter(WaterAccess access, WaterKind kind) =>
        kind == WaterKind.None || access == WaterAccess.Any || (access == WaterAccess.Shallow && kind == WaterKind.Shallow);

    /// <summary>Whether a pixel box (right and bottom exclusive) touches only tiles the access allows.</summary>
    public static bool CanOccupy(int left, int top, int right, int bottom, WaterAccess access, Func<int, int, WaterKind> kindAt)
    {
        if (access == WaterAccess.Any)
            return true;
        int x0 = FloorTile(left), x1 = FloorTile(right - 1);
        int y0 = FloorTile(top), y1 = FloorTile(bottom - 1);
        for (int y = y0; y <= y1; y++)
        {
            for (int x = x0; x <= x1; x++)
            {
                if (!CanEnter(access, kindAt(x, y)))
                    return false;
            }
        }
        return true;
    }

    /// <summary>Whether a straight walk between two ground points (pixels) stays on tiles the access allows.</summary>
    public static bool CanCross(float fromX, float fromY, float toX, float toY, WaterAccess access, Func<int, int, WaterKind> kindAt)
    {
        if (access == WaterAccess.Any)
            return true;
        float distance = MathF.Sqrt((toX - fromX) * (toX - fromX) + (toY - fromY) * (toY - fromY));
        int steps = Math.Max(1, (int)MathF.Ceiling(distance / (TileSize / 4f)));
        for (int i = 0; i <= steps; i++)
        {
            float t = i / (float)steps;
            if (!CanEnter(access, kindAt(FloorTile(fromX + (toX - fromX) * t), FloorTile(fromY + (toY - fromY) * t))))
                return false;
        }
        return true;
    }

    public static List<(int X, int Y)> StandableTiles(HabitatRect pen, WaterAccess access, Func<int, int, WaterKind> kindAt)
    {
        var tiles = new List<(int X, int Y)>();
        for (int y = pen.Y; y < pen.Y + pen.Height; y++)
        {
            for (int x = pen.X; x < pen.X + pen.Width; x++)
            {
                if (CanEnter(access, kindAt(x, y)))
                    tiles.Add((x, y));
            }
        }
        return tiles;
    }

    /// <summary>A random pen tile the access allows, or any pen tile if the pen has none.</summary>
    public static (int X, int Y) RandomStandableTile(HabitatRect pen, WaterAccess access, Func<int, int, WaterKind> kindAt, Random rng)
    {
        List<(int X, int Y)> tiles = StandableTiles(pen, access, kindAt);
        return tiles.Count > 0 ? tiles[rng.Next(tiles.Count)] : pen.RandomTile(rng);
    }

    private static int FloorTile(float pixels) => (int)MathF.Floor(pixels / TileSize);
}
