namespace StardewZoo;

/// <summary>Why a tile refuses furniture.</summary>
public enum FurnitureBlock : byte
{
    None,

    /// <summary>On a route that must stay walkable: only passable furniture (rugs) may go here.</summary>
    Path,

    /// <summary>Inside an animal pen.</summary>
    Pen,

    /// <summary>Where the player stands to use a booth, board, studio, door or warp.</summary>
    Access
}

/// <summary>Map facts needed to work out where furniture may go; built from a game location or by tests.</summary>
public sealed class FurnitureLayoutInput
{
    public int Width { get; init; }

    public int Height { get; init; }

    /// <summary>Whether a character can stand on the tile, ignoring furniture.</summary>
    public Func<int, int, bool> Walkable { get; init; } = (_, _) => true;

    /// <summary>Areas no furniture may enter; they're also excluded from routes.</summary>
    public IReadOnlyList<HabitatRect> Pens { get; init; } = Array.Empty<HabitatRect>();

    /// <summary>Points visitors walk between in order; the route joining each consecutive pair stays open.</summary>
    public IReadOnlyList<(int X, int Y)> Waypoints { get; init; } = Array.Empty<(int X, int Y)>();

    /// <summary>Tiles the player interacts with (usually unwalkable); their walkable neighbours stay clear.</summary>
    public IReadOnlyList<(int X, int Y)> InteractionTiles { get; init; } = Array.Empty<(int X, int Y)>();

    /// <summary>Warp tiles (may be just off the map edge); walkable tiles touching them stay clear.</summary>
    public IReadOnlyList<(int X, int Y)> WarpTiles { get; init; } = Array.Empty<(int X, int Y)>();
}

/// <summary>Per-tile furniture rules for a zoo location: pens and access tiles refuse everything, routes accept only rugs.</summary>
public sealed class FurnitureLayout
{
    private static readonly (int X, int Y)[] Steps = { (0, -1), (1, 0), (0, 1), (-1, 0) };

    private readonly FurnitureBlock[] cells;

    public int Width { get; }

    public int Height { get; }

    private FurnitureLayout(int width, int height)
    {
        this.Width = width;
        this.Height = height;
        this.cells = new FurnitureBlock[width * height];
    }

    /// <summary>Off-map tiles count as <see cref="FurnitureBlock.Access"/>.</summary>
    public FurnitureBlock At(int x, int y) => this.InBounds(x, y) ? this.cells[y * this.Width + x] : FurnitureBlock.Access;

    public bool Allows(int x, int y, bool passable)
    {
        FurnitureBlock block = this.At(x, y);
        return block == FurnitureBlock.None || (block == FurnitureBlock.Path && passable);
    }

    /// <summary>The strictest rule a furniture footprint hits, or <see cref="FurnitureBlock.None"/> if it fits.</summary>
    public FurnitureBlock Check(int x, int y, int width, int height, bool passable)
    {
        FurnitureBlock worst = FurnitureBlock.None;
        for (int dy = 0; dy < height; dy++)
        {
            for (int dx = 0; dx < width; dx++)
            {
                if (this.Allows(x + dx, y + dy, passable))
                    continue;
                FurnitureBlock block = this.At(x + dx, y + dy);
                if (block > worst)
                    worst = block;
            }
        }
        return worst;
    }

    public static FurnitureLayout Build(FurnitureLayoutInput input)
    {
        var layout = new FurnitureLayout(Math.Max(0, input.Width), Math.Max(0, input.Height));
        foreach (HabitatRect pen in input.Pens)
        {
            for (int y = pen.Y; y < pen.Y + pen.Height; y++)
                for (int x = pen.X; x < pen.X + pen.Width; x++)
                    layout.Set(x, y, FurnitureBlock.Pen);
        }

        bool Open(int x, int y) => layout.InBounds(x, y) && layout.At(x, y) != FurnitureBlock.Pen && input.Walkable(x, y);

        var access = new List<(int X, int Y)>();
        void MarkAccess(int x, int y)
        {
            if (!Open(x, y) || layout.At(x, y) == FurnitureBlock.Access)
                return;
            layout.Set(x, y, FurnitureBlock.Access);
            access.Add((x, y));
        }

        foreach ((int x, int y) in input.InteractionTiles)
        {
            MarkAccess(x, y);
            foreach ((int dx, int dy) in Steps)
                MarkAccess(x + dx, y + dy);
        }
        foreach ((int x, int y) in input.WarpTiles)
        {
            for (int dy = -1; dy <= 1; dy++)
                for (int dx = -1; dx <= 1; dx++)
                    MarkAccess(x + dx, y + dy);
        }

        var route = new HashSet<(int X, int Y)>();
        for (int i = 0; i + 1 < input.Waypoints.Count; i++)
        {
            var path = FindPath(layout, Open, input.Waypoints[i], target => target == input.Waypoints[i + 1]);
            if (path != null)
                route.UnionWith(path);
        }

        // Every access tile must reach the route (or, with no waypoints, the first access tile).
        foreach ((int X, int Y) start in access)
        {
            if (route.Count == 0)
            {
                route.Add(start);
                continue;
            }
            var path = FindPath(layout, Open, start, route.Contains);
            if (path != null)
                route.UnionWith(path);
        }

        foreach ((int x, int y) in route)
        {
            if (layout.At(x, y) == FurnitureBlock.None)
                layout.Set(x, y, FurnitureBlock.Path);
        }
        return layout;
    }

    /// <summary>Breadth-first shortest walk from <paramref name="start"/> to the nearest goal tile, inclusive of both ends.</summary>
    private static List<(int X, int Y)>? FindPath(FurnitureLayout layout, Func<int, int, bool> open, (int X, int Y) start, Func<(int X, int Y), bool> isGoal)
    {
        if (!open(start.X, start.Y))
            return null;

        var cameFrom = new Dictionary<(int X, int Y), (int X, int Y)> { [start] = start };
        var queue = new Queue<(int X, int Y)>();
        queue.Enqueue(start);
        while (queue.Count > 0)
        {
            (int X, int Y) at = queue.Dequeue();
            if (isGoal(at))
            {
                var path = new List<(int X, int Y)> { at };
                while (at != start)
                {
                    at = cameFrom[at];
                    path.Add(at);
                }
                return path;
            }
            foreach ((int dx, int dy) in Steps)
            {
                (int X, int Y) next = (at.X + dx, at.Y + dy);
                if (cameFrom.ContainsKey(next) || !open(next.X, next.Y))
                    continue;
                cameFrom[next] = at;
                queue.Enqueue(next);
            }
        }
        return null;
    }

    private bool InBounds(int x, int y) => x >= 0 && y >= 0 && x < this.Width && y < this.Height;

    private void Set(int x, int y, FurnitureBlock block)
    {
        if (this.InBounds(x, y))
            this.cells[y * this.Width + x] = block;
    }

    /// <summary>Parse a map property of space-separated integers into (x, y) pairs; malformed input yields what parsed.</summary>
    public static List<(int X, int Y)> ParsePoints(string? value)
    {
        var numbers = ParseInts(value);
        var points = new List<(int X, int Y)>();
        for (int i = 0; i + 1 < numbers.Count; i += 2)
            points.Add((numbers[i], numbers[i + 1]));
        return points;
    }

    /// <summary>Parse a map property of space-separated "x y width height" groups.</summary>
    public static List<HabitatRect> ParseRects(string? value, string id)
    {
        var numbers = ParseInts(value);
        var rects = new List<HabitatRect>();
        for (int i = 0; i + 3 < numbers.Count; i += 4)
        {
            if (numbers[i + 2] > 0 && numbers[i + 3] > 0)
                rects.Add(new HabitatRect(id, numbers[i], numbers[i + 1], numbers[i + 2], numbers[i + 3]));
        }
        return rects;
    }

    private static List<int> ParseInts(string? value)
    {
        var numbers = new List<int>();
        if (string.IsNullOrWhiteSpace(value))
            return numbers;
        foreach (string part in value.Split(' ', StringSplitOptions.RemoveEmptyEntries))
        {
            if (!int.TryParse(part, out int n))
                break;
            numbers.Add(n);
        }
        return numbers;
    }
}
