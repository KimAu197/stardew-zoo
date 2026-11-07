using StardewZoo;
using Xunit;

public class ZooWaterTests
{
    private const double Tick = 1000.0 / 60;

    private static readonly HabitatRect Pen = new("Test", 26, 13, 9, 6);

    /// <summary>A pool across x 28-32, rows 15-17: deep in the middle row, a shallow shelf above and below.</summary>
    private static WaterKind PoolAt(int x, int y) =>
        x is < 28 or > 32 || y is < 15 or > 17 ? WaterKind.None : y == 16 ? WaterKind.Deep : WaterKind.Shallow;

    private static readonly (int X, int Y)[] Pool =
        Enumerable.Range(28, 5).SelectMany(x => Enumerable.Range(15, 3).Select(y => (x, y))).ToArray();

    private static BrainWorld World(IReadOnlyList<PerchSpot>? perches = null) =>
        new(Pen, perches ?? Array.Empty<PerchSpot>(), Pool, PoolAt);

    private static (int X, int Y) TileOf(float x, float y) => ((int)MathF.Floor(x / 64), (int)MathF.Floor(y / 64));

    private static List<BrainOutput> Simulate(string type, BrainWorld world, (int X, int Y) start, int ticks, int seed = 1, bool sleepingAtEnd = false)
    {
        var brain = new AnimalBrain(MoveProfiles.For(type), world, new Random(seed));
        (float x, float y) = AnimalBrain.TileCenter(start.X, start.Y);
        var outputs = new List<BrainOutput>();
        for (int i = 0; i < ticks; i++)
        {
            bool sleeping = sleepingAtEnd && i > ticks * 3 / 4;
            BrainOutput o = brain.Tick(new BrainInput(Tick, x, y, sleeping, sleeping, false));
            if (o.Controlled)
                (x, y) = (o.X, o.Y);
            outputs.Add(o);
        }
        return outputs;
    }

    /// <summary>Ground positions the brain hands back to vanilla: where a walk, landing or climb-down ends.</summary>
    private static IEnumerable<(int X, int Y)> GroundStops(List<BrainOutput> outputs) =>
        outputs.Zip(outputs.Skip(1)).Where(p => p.First.Controlled && !p.Second.Controlled).Select(p => TileOf(p.First.X, p.First.Y));

    [Theory]
    [InlineData(ZooIds.SeaLion, WaterAccess.Any)]
    [InlineData(ZooIds.Capybara, WaterAccess.Any)]
    [InlineData(ZooIds.Flamingo, WaterAccess.Shallow)]
    [InlineData(ZooIds.NightHeron, WaterAccess.Shallow)]
    [InlineData(ZooIds.Penguin, WaterAccess.None)]
    [InlineData(ZooIds.Lion, WaterAccess.None)]
    [InlineData(ZooIds.Elephant, WaterAccess.None)]
    [InlineData(ZooIds.Monkey, WaterAccess.None)]
    [InlineData(ZooIds.Owl, WaterAccess.None)]
    [InlineData("Vanilla.Cow", WaterAccess.None)]
    public void Species_HaveTheExpectedWaterAccess(string type, WaterAccess expected)
    {
        Assert.Equal(expected, ZooWater.AccessFor(type));
    }

    [Theory]
    [InlineData(WaterAccess.None, WaterKind.None, true)]
    [InlineData(WaterAccess.None, WaterKind.Shallow, false)]
    [InlineData(WaterAccess.None, WaterKind.Deep, false)]
    [InlineData(WaterAccess.Shallow, WaterKind.Shallow, true)]
    [InlineData(WaterAccess.Shallow, WaterKind.Deep, false)]
    [InlineData(WaterAccess.Any, WaterKind.Shallow, true)]
    [InlineData(WaterAccess.Any, WaterKind.Deep, true)]
    public void CanEnter_FollowsDepth(WaterAccess access, WaterKind kind, bool expected)
    {
        Assert.Equal(expected, ZooWater.CanEnter(access, kind));
    }

    [Fact]
    public void Asleep_NobodyStaysInWater()
    {
        // vanilla clears isSwimming at 8pm, so a swimmer left in the pool would be drawn standing on the water
        Assert.Equal(WaterAccess.None, ZooWater.AccessFor(ZooIds.SeaLion, asleep: true));
        Assert.Equal(WaterAccess.None, ZooWater.AccessFor(ZooIds.Flamingo, asleep: true));
        Assert.Equal(WaterAccess.Any, ZooWater.AccessFor(ZooIds.SeaLion, asleep: false));
    }

    [Theory]
    [InlineData("deep", WaterKind.Deep)]
    [InlineData("Deep", WaterKind.Deep)]
    [InlineData("Shallow", WaterKind.Shallow)]
    [InlineData("T", WaterKind.Shallow)]
    [InlineData("", WaterKind.None)]
    [InlineData(null, WaterKind.None)]
    public void Parse_TileProperty(string? value, WaterKind expected)
    {
        Assert.Equal(expected, ZooWater.Parse(value));
    }

    [Fact]
    public void CanOccupy_ChecksEveryTileTheBoxTouches()
    {
        // a 48x48 box in dry tile (27,15) whose right edge pokes 8px into the shallow tile (28,15)
        int left = 27 * 64 + 24, top = 15 * 64 + 8;
        Assert.False(ZooWater.CanOccupy(left, top, left + 48, top + 48, WaterAccess.None, PoolAt));
        Assert.True(ZooWater.CanOccupy(left, top, left + 48, top + 48, WaterAccess.Shallow, PoolAt));
        // fully inside the dry tile (right edge exclusive at the tile boundary)
        Assert.True(ZooWater.CanOccupy(27 * 64 + 8, top, 28 * 64, top + 48, WaterAccess.None, PoolAt));
        // a wader overlapping the deep row
        int deepTop = 16 * 64 - 8;
        Assert.False(ZooWater.CanOccupy(29 * 64 + 8, deepTop, 29 * 64 + 56, deepTop + 48, WaterAccess.Shallow, PoolAt));
        Assert.True(ZooWater.CanOccupy(29 * 64 + 8, deepTop, 29 * 64 + 56, deepTop + 48, WaterAccess.Any, PoolAt));
    }

    [Fact]
    public void CanCross_RejectsPathsThroughForbiddenWater()
    {
        (float ax, float ay) = AnimalBrain.TileCenter(27, 16);
        (float bx, float by) = AnimalBrain.TileCenter(33, 16);
        (float cx, float cy) = AnimalBrain.TileCenter(27, 18);
        (float dx, float dy) = AnimalBrain.TileCenter(33, 18);
        Assert.False(ZooWater.CanCross(ax, ay, bx, by, WaterAccess.None, PoolAt));
        Assert.False(ZooWater.CanCross(ax, ay, bx, by, WaterAccess.Shallow, PoolAt));
        Assert.True(ZooWater.CanCross(ax, ay, bx, by, WaterAccess.Any, PoolAt));
        Assert.True(ZooWater.CanCross(cx, cy, dx, dy, WaterAccess.None, PoolAt));
    }

    [Fact]
    public void StandableTiles_ExcludeForbiddenWater()
    {
        var dry = ZooWater.StandableTiles(Pen, WaterAccess.None, PoolAt);
        var wading = ZooWater.StandableTiles(Pen, WaterAccess.Shallow, PoolAt);
        var any = ZooWater.StandableTiles(Pen, WaterAccess.Any, PoolAt);
        Assert.Equal(Pen.Width * Pen.Height - 15, dry.Count);
        Assert.Equal(Pen.Width * Pen.Height - 5, wading.Count);
        Assert.Equal(Pen.Width * Pen.Height, any.Count);
        Assert.DoesNotContain(dry, t => PoolAt(t.X, t.Y) != WaterKind.None);
        Assert.DoesNotContain(wading, t => PoolAt(t.X, t.Y) == WaterKind.Deep);
    }

    [Fact]
    public void RandomStandableTile_NeverPicksWaterForNonSwimmers()
    {
        var rng = new Random(5);
        for (int i = 0; i < 2000; i++)
        {
            (int x, int y) = ZooWater.RandomStandableTile(Pen, WaterAccess.None, PoolAt, rng);
            Assert.True(Pen.Contains(x, y));
            Assert.Equal(WaterKind.None, PoolAt(x, y));
        }
    }

    [Fact]
    public void RandomStandableTile_FallsBackToThePen_WhenAllWet()
    {
        var pen = new HabitatRect("Wet", 28, 15, 2, 2);
        (int x, int y) = ZooWater.RandomStandableTile(pen, WaterAccess.None, PoolAt, new Random(1));
        Assert.True(pen.Contains(x, y));
    }

    [Fact]
    public void Owl_NeverLandsInWater()
    {
        var outputs = Simulate(ZooIds.Owl, World(), (27, 18), 60 * 60 * 20, seed: 2, sleepingAtEnd: true);
        Assert.Contains(outputs, o => o.Pose == BrainPose.Fly);
        Assert.All(GroundStops(outputs), t => Assert.Equal(WaterKind.None, PoolAt(t.X, t.Y)));
    }

    [Fact]
    public void Heron_WadesInTheShallows_ButNeverStopsInDeepWater()
    {
        var outputs = Simulate(ZooIds.NightHeron, World(), (27, 18), 60 * 60 * 20, seed: 4);
        var stops = GroundStops(outputs).ToList();
        Assert.Contains(stops, t => PoolAt(t.X, t.Y) == WaterKind.Shallow);
        Assert.DoesNotContain(stops, t => PoolAt(t.X, t.Y) == WaterKind.Deep);
        Assert.DoesNotContain(outputs.Where(o => o.Pose == BrainPose.Walk), o => PoolAt(TileOf(o.X, o.Y).X, TileOf(o.X, o.Y).Y) == WaterKind.Deep);
    }

    [Fact]
    public void SeaLion_StillSwimsInDeepWater()
    {
        var outputs = Simulate(ZooIds.SeaLion, World(), (27, 18), 60 * 60 * 5, seed: 3);
        Assert.Contains(outputs, o => o.Controlled && PoolAt(TileOf(o.X, o.Y).X, TileOf(o.X, o.Y).Y) != WaterKind.None);
    }

    [Fact]
    public void Monkey_NeverWalksThroughWater_AndClimbsDownOnDryGround()
    {
        // one tree on each side of the pool; walking from one to the other would wade through it
        PerchSpot[] trees = { new(27, 16, 160), new(33, 16, 160), new(30, 13, 160) };
        for (int seed = 1; seed <= 4; seed++)
        {
            var outputs = Simulate(ZooIds.Monkey, World(trees), (27, 18), 60 * 60 * 10, seed);
            Assert.Contains(outputs, o => o.Pose == BrainPose.Climb);
            Assert.All(outputs.Where(o => o.Pose == BrainPose.Walk), o =>
            {
                (int x, int y) = TileOf(o.X, o.Y);
                Assert.True(PoolAt(x, y) == WaterKind.None, $"seed {seed}: monkey walked through water at {x},{y}");
            });
            Assert.All(GroundStops(outputs), t => Assert.Equal(WaterKind.None, PoolAt(t.X, t.Y)));
        }
    }

    [Fact]
    public void Monkey_SkipsTreesStandingInWater()
    {
        PerchSpot[] trees = { new(30, 16, 160) };
        var outputs = Simulate(ZooIds.Monkey, World(trees), (27, 18), 60 * 60 * 5);
        Assert.DoesNotContain(outputs, o => o.Controlled);
    }
}
