using StardewZoo;
using Xunit;

/// <summary>Uses a fixed six-pen park fixture so the tests don't move when the real zoo map is redesigned.</summary>
public class FurnitureLayoutTests
{
    private const int Width = 38;
    private const int Height = 30;
    private static readonly (int X, int Y) Booth = (17, 14);
    private static readonly (int X, int Y) Board = (19, 14);
    private static readonly (int X, int Y) Studio = (18, 16);
    private static readonly (int X, int Y)[] Warps = { (18, 30), (19, 30) };

    private static readonly HabitatRect[] Pens =
    {
        new("Ice", 3, 3, 9, 6), new("Water", 26, 3, 9, 6), new("Savanna", 3, 13, 9, 6),
        new("Jungle", 26, 13, 9, 6), new("Forest", 3, 23, 9, 3), new("Prehistoric", 26, 23, 9, 3)
    };

    private static readonly (int X, int Y)[] Loop =
    {
        (18, 28), (1, 28), (1, 21), (1, 11), (1, 1), (7, 1), (18, 1), (30, 1), (36, 1),
        (36, 11), (30, 11), (18, 11), (7, 11), (7, 21), (18, 21), (30, 21), (36, 21), (36, 28), (18, 28)
    };

    /// <summary>The park as the game sees it: fences ring each pen and the plaza props are solid.</summary>
    private static bool ZooWalkable(int x, int y)
    {
        if ((x, y) == Booth || (x, y) == Board || (x, y) == Studio)
            return false;
        foreach (HabitatRect pen in Pens)
        {
            bool inFence = x >= pen.X - 1 && x <= pen.X + pen.Width && y >= pen.Y - 1 && y <= pen.Y + pen.Height;
            if (inFence && !pen.Contains(x, y))
                return false;
        }
        return true;
    }

    private static FurnitureLayout ZooLayout() => FurnitureLayout.Build(new FurnitureLayoutInput
    {
        Width = Width,
        Height = Height,
        Walkable = ZooWalkable,
        Pens = Pens,
        Waypoints = Loop,
        InteractionTiles = new[] { Booth, Board, Studio },
        WarpTiles = Warps
    });

    [Fact]
    public void Pens_RefuseAllFurniture_IncludingRugs()
    {
        FurnitureLayout layout = ZooLayout();

        foreach (HabitatRect pen in Pens)
        {
            for (int y = pen.Y; y < pen.Y + pen.Height; y++)
            {
                for (int x = pen.X; x < pen.X + pen.Width; x++)
                {
                    Assert.Equal(FurnitureBlock.Pen, layout.At(x, y));
                    Assert.False(layout.Allows(x, y, passable: true));
                }
            }
        }
    }

    [Fact]
    public void VisitorWaypoints_AreRugOnlyPath()
    {
        FurnitureLayout layout = ZooLayout();

        foreach ((int x, int y) in Loop.Where(p => layout.At(p.X, p.Y) != FurnitureBlock.Access))
        {
            Assert.Equal(FurnitureBlock.Path, layout.At(x, y));
            Assert.True(layout.Allows(x, y, passable: true));
            Assert.False(layout.Allows(x, y, passable: false));
        }
    }

    [Fact]
    public void BoothBoardStudioAndEntrance_KeepTheirStandingTilesClear()
    {
        FurnitureLayout layout = ZooLayout();

        Assert.Equal(FurnitureBlock.Access, layout.At(Booth.X, Booth.Y + 1));
        Assert.Equal(FurnitureBlock.Access, layout.At(Board.X, Board.Y + 1));
        Assert.Equal(FurnitureBlock.Access, layout.At(Studio.X, Studio.Y + 1));
        Assert.Equal(FurnitureBlock.Access, layout.At(18, 29));
        Assert.Equal(FurnitureBlock.Access, layout.At(19, 29));
        Assert.False(layout.Allows(18, 29, passable: true));
    }

    [Fact]
    public void OpenGrassAndPlazaCorners_AcceptFurniture()
    {
        FurnitureLayout layout = ZooLayout();

        Assert.True(layout.Allows(15, 5, passable: false));
        Assert.True(layout.Allows(22, 25, passable: false));
        Assert.True(layout.Allows(15, 19, passable: false));
        Assert.True(layout.Allows(22, 13, passable: false));
    }

    [Fact]
    public void FullyFurnished_Zoo_StillConnectsEveryWaypointAndAccessTile()
    {
        FurnitureLayout layout = ZooLayout();
        // Worst case: solid furniture on every tile that accepts it.
        bool Open(int x, int y) => x is >= 0 and < Width && y is >= 0 and < Height
            && ZooWalkable(x, y) && layout.At(x, y) is FurnitureBlock.Path or FurnitureBlock.Access;

        var reachable = Flood(Loop[0], Open);

        foreach ((int X, int Y) waypoint in Loop)
            Assert.Contains(waypoint, reachable);
        Assert.Contains((Booth.X, Booth.Y + 1), reachable);
        Assert.Contains((Board.X, Board.Y + 1), reachable);
        Assert.Contains((Studio.X, Studio.Y + 1), reachable);
        Assert.Contains((18, 29), reachable);
    }

    [Fact]
    public void Check_ReportsStrictestTileInFootprint()
    {
        FurnitureLayout layout = ZooLayout();

        Assert.Equal(FurnitureBlock.None, layout.Check(14, 4, 2, 2, passable: false));
        Assert.Equal(FurnitureBlock.Path, layout.Check(14, 0, 2, 2, passable: false));
        Assert.Equal(FurnitureBlock.None, layout.Check(14, 0, 2, 2, passable: true));
        Assert.Equal(FurnitureBlock.Pen, layout.Check(11, 2, 3, 3, passable: true));
    }

    [Fact]
    public void OffMap_IsRefused()
    {
        FurnitureLayout layout = ZooLayout();

        Assert.False(layout.Allows(-1, 5, passable: true));
        Assert.False(layout.Allows(Width, 5, passable: true));
        Assert.Equal(FurnitureBlock.Path, layout.Check(36, 1, 1, 1, passable: false));
        Assert.Equal(FurnitureBlock.Access, layout.Check(37, 1, 2, 1, passable: true));
    }

    [Fact]
    public void WithoutWaypoints_AccessTilesAreJoinedToEachOther()
    {
        // A bare 10x5 pavilion: a door warp at the bottom and an exhibit sign at the top.
        FurnitureLayout layout = FurnitureLayout.Build(new FurnitureLayoutInput
        {
            Width = 10,
            Height = 5,
            Walkable = (x, y) => (x, y) != (8, 0),
            InteractionTiles = new[] { (8, 0) },
            WarpTiles = new[] { (1, 5) }
        });
        bool Open(int x, int y) => x is >= 0 and < 10 && y is >= 0 and < 5 && (x, y) != (8, 0) && layout.At(x, y) != FurnitureBlock.None;

        var reachable = Flood((1, 4), Open);

        Assert.Contains((8, 1), reachable);
        Assert.True(layout.Allows(5, 0, passable: false) || layout.Allows(5, 4, passable: false));
    }

    [Fact]
    public void RouteLegsBetweenDisconnectedRegions_AreSkipped()
    {
        // Two halls split by a solid column at x=5; visitors teleport between them through a door.
        FurnitureLayout layout = FurnitureLayout.Build(new FurnitureLayoutInput
        {
            Width = 11,
            Height = 3,
            Walkable = (x, _) => x != 5,
            Waypoints = new[] { (0, 1), (4, 1), (6, 1), (10, 1) }
        });

        Assert.Equal(FurnitureBlock.Path, layout.At(2, 1));
        Assert.Equal(FurnitureBlock.Path, layout.At(8, 1));
        Assert.Equal(FurnitureBlock.None, layout.At(5, 1));
        Assert.True(layout.Allows(2, 0, passable: false));
    }

    [Fact]
    public void ParsesMapProperties()
    {
        Assert.Equal(new[] { (1, 2), (3, 4) }, FurnitureLayout.ParsePoints("1 2 3 4 5"));
        Assert.Empty(FurnitureLayout.ParsePoints(null));
        Assert.Equal(new[] { new HabitatRect("p", 1, 2, 3, 4) }, FurnitureLayout.ParseRects("1 2 3 4 9 9 0 1", "p"));
        Assert.Empty(FurnitureLayout.ParseRects("1 two 3 4", "p"));
    }

    private static HashSet<(int X, int Y)> Flood((int X, int Y) start, Func<int, int, bool> open)
    {
        var seen = new HashSet<(int X, int Y)> { start };
        var queue = new Queue<(int X, int Y)>(seen);
        while (queue.Count > 0)
        {
            (int x, int y) = queue.Dequeue();
            foreach ((int X, int Y) next in new[] { (x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y) })
            {
                if (open(next.X, next.Y) && seen.Add(next))
                    queue.Enqueue(next);
            }
        }
        return seen;
    }
}
