using StardewZoo;
using Xunit;

public class AnimalBrainTests
{
    private const double Tick = 1000.0 / 60;

    private static readonly HabitatRect Pen = new("Test", 26, 13, 9, 6);

    private static readonly PerchSpot[] Trees = { new(27, 15, 160), new(33, 15, 160) };

    private static readonly (int X, int Y)[] Pool =
    {
        (28, 15), (29, 15), (30, 15), (31, 15), (32, 15),
        (28, 16), (29, 16), (30, 16), (31, 16), (32, 16),
        (28, 17), (29, 17), (30, 17), (31, 17), (32, 17)
    };

    private sealed class Sim
    {
        public Sim(MoveProfile profile, BrainWorld world, int seed = 1)
        {
            this.Brain = new AnimalBrain(profile, world, new Random(seed));
            (this.X, this.Y) = AnimalBrain.TileCenter(30, 16);
        }

        public AnimalBrain Brain { get; }
        public float X { get; private set; }
        public float Y { get; private set; }
        public List<BrainOutput> Outputs { get; } = new();

        public BrainOutput Step(bool night = false, bool sleeping = false, bool baby = false)
        {
            BrainOutput output = this.Brain.Tick(new BrainInput(Tick, this.X, this.Y, night, sleeping, baby));
            if (output.Controlled)
                (this.X, this.Y) = (output.X, output.Y);
            this.Outputs.Add(output);
            return output;
        }

        public void Run(int ticks, bool night = false, bool sleeping = false, bool baby = false)
        {
            for (int i = 0; i < ticks; i++)
                this.Step(night, sleeping, baby);
        }
    }

    private static BrainWorld World(IReadOnlyList<PerchSpot>? perches = null, IReadOnlyList<(int X, int Y)>? water = null) =>
        new(Pen, perches ?? Array.Empty<PerchSpot>(), water ?? Array.Empty<(int X, int Y)>());

    private static bool InsidePen(BrainOutput o) =>
        o.X >= Pen.X * 64 && o.X < (Pen.X + Pen.Width) * 64 && o.Y >= Pen.Y * 64 && o.Y < (Pen.Y + Pen.Height) * 64;

    [Fact]
    public void Heron_TakesOffFliesAndLands_InsideThePen()
    {
        var sim = new Sim(MoveProfiles.For(ZooIds.NightHeron), World(water: Pool));
        sim.Run(60 * 60 * 5);

        Assert.Contains(sim.Outputs, o => o.Pose == BrainPose.Fly && o.Altitude >= 150);
        Assert.All(sim.Outputs.Where(o => o.Controlled), o => Assert.True(InsidePen(o), $"left pen at {o.X},{o.Y}"));
        int flights = sim.Outputs.Zip(sim.Outputs.Skip(1)).Count(p => p.First.Altitude == 0 && p.Second.Altitude > 0);
        int landings = sim.Outputs.Zip(sim.Outputs.Skip(1)).Count(p => p.First.Altitude > 0 && p.Second.Altitude == 0);
        Assert.True(flights >= 2, $"only {flights} flights");
        Assert.InRange(flights - landings, 0, 1);
    }

    [Fact]
    public void Flamingo_FliesRarely_AndWadesMore()
    {
        var flamingo = new Sim(MoveProfiles.For(ZooIds.Flamingo), World(water: Pool), seed: 3);
        var heron = new Sim(MoveProfiles.For(ZooIds.NightHeron), World(water: Pool), seed: 3);
        flamingo.Run(60 * 60 * 10);
        heron.Run(60 * 60 * 10);

        int Flights(Sim s) => s.Outputs.Zip(s.Outputs.Skip(1)).Count(p => p.First.Pose != BrainPose.Fly && p.Second.Pose == BrainPose.Fly);
        int Walks(Sim s) => s.Outputs.Zip(s.Outputs.Skip(1)).Count(p => p.First.Pose != BrainPose.Walk && p.Second.Pose == BrainPose.Walk);
        Assert.True(Flights(flamingo) < Flights(heron));
        Assert.True(Walks(flamingo) > Flights(flamingo));
    }

    [Fact]
    public void Owl_PerchesAtNight_AndStaysThere()
    {
        var sim = new Sim(MoveProfiles.For(ZooIds.Owl), World(Trees));
        sim.Run(60 * 30, night: true);
        Assert.Equal(BrainState.Perched, sim.Brain.State);
        Assert.Equal(160, sim.Brain.Altitude);

        sim.Run(60 * 120, night: true, sleeping: true);
        Assert.Equal(BrainState.Perched, sim.Brain.State);
        BrainOutput last = sim.Outputs[^1];
        Assert.Equal(BrainPose.Perch, last.Pose);
        Assert.Contains(Trees, t => AnimalBrain.TileCenter(t.TileX, t.TileY) == (last.X, last.Y));
    }

    [Fact]
    public void Sleeping_Fliers_DoNotTakeOff_AndAirborneOnesLand()
    {
        var sim = new Sim(MoveProfiles.For(ZooIds.NightHeron), World());
        sim.Run(60 * 60 * 3, sleeping: true);
        Assert.All(sim.Outputs, o => Assert.Equal(0, o.Altitude));

        var airborne = new Sim(MoveProfiles.For(ZooIds.NightHeron), World(), seed: 5);
        while (airborne.Brain.State != BrainState.Flying)
            airborne.Step();
        airborne.Run(60 * 5, sleeping: true);
        Assert.Equal(BrainState.Ground, airborne.Brain.State);
    }

    [Fact]
    public void Babies_KeepVanillaWandering()
    {
        var sim = new Sim(MoveProfiles.For(ZooIds.Monkey), World(Trees));
        sim.Run(60 * 60 * 3, baby: true);
        Assert.All(sim.Outputs, o => Assert.False(o.Controlled));
    }

    [Fact]
    public void Monkey_ClimbsSitsAndComesDown()
    {
        var sim = new Sim(MoveProfiles.For(ZooIds.Monkey), World(Trees), seed: 7);
        sim.Run(60 * 60 * 6);

        var poses = sim.Outputs.Select(o => o.Pose).ToList();
        int climb = poses.IndexOf(BrainPose.Climb);
        int sit = poses.IndexOf(BrainPose.Sit);
        Assert.True(climb >= 0 && sit > climb, "monkey never climbed then sat");
        Assert.Contains(sim.Outputs.Skip(sit), o => o.Pose == BrainPose.Climb && o.Altitude < 160);
        Assert.Contains(sim.Outputs, o => o.Pose == BrainPose.Hang);
        Assert.All(sim.Outputs.Where(o => o.Pose == BrainPose.Sit), o => Assert.Equal(160, o.Altitude));
        Assert.All(sim.Outputs.Where(o => o.Controlled), o => Assert.True(InsidePen(o)));
    }

    [Fact]
    public void Monkey_SleepsInTheTree()
    {
        var sim = new Sim(MoveProfiles.For(ZooIds.Monkey), World(Trees), seed: 2);
        while (sim.Brain.State != BrainState.InTree)
            sim.Step();
        sim.Run(60 * 120, night: true, sleeping: true);
        Assert.Equal(BrainState.InTree, sim.Brain.State);
    }

    [Fact]
    public void SeaLion_SwimsFastLapsAroundThePool()
    {
        var sim = new Sim(MoveProfiles.For(ZooIds.SeaLion), World(water: Pool), seed: 4);
        while (sim.Brain.State != BrainState.Lap)
            sim.Step();
        int start = sim.Outputs.Count;
        sim.Run(60 * 4);

        var lap = sim.Outputs.Skip(start).Where(o => o.Pose == BrainPose.Walk).ToList();
        Assert.NotEmpty(lap);
        var tiles = lap.Select(o => ((int)(o.X / 64), (int)(o.Y / 64))).Distinct().ToList();
        Assert.All(tiles, t => Assert.Contains(t, Pool));
        Assert.Contains(lap.Select(o => o.Facing).Distinct(), f => f == 0);
        Assert.Equal(4, lap.Select(o => o.Facing).Distinct().Count());
        float travelled = lap.Zip(lap.Skip(1)).Sum(p => MathF.Sqrt(MathF.Pow(p.Second.X - p.First.X, 2) + MathF.Pow(p.Second.Y - p.First.Y, 2)));
        Assert.True(travelled / (lap.Count / 60f) > 200, "laps should be faster than walking");
    }

    [Fact]
    public void Sitters_RequestASitAnimation()
    {
        var sim = new Sim(MoveProfiles.For(ZooIds.Panda), World());
        sim.Run(60 * 120);
        Assert.Contains(sim.Outputs, o => o.SitMs >= 3000);
        Assert.All(sim.Outputs, o => Assert.False(o.Controlled));
    }

    [Fact]
    public void DefaultAnimals_AreNeverControlled()
    {
        var sim = new Sim(MoveProfiles.For(ZooIds.Lion), World(Trees, Pool));
        sim.Run(60 * 120);
        Assert.All(sim.Outputs, o => Assert.Equal(new BrainOutput(false, o.X, o.Y, 0, o.Facing, BrainPose.None, 0), o));
    }

    [Fact]
    public void LapPlanner_OrdersShoreTilesAroundTheCentre()
    {
        var path = LapPlanner.Build(Pool);
        Assert.Equal(12, path.Count);
        Assert.DoesNotContain(AnimalBrain.TileCenter(30, 16), path);
        Assert.DoesNotContain(AnimalBrain.TileCenter(29, 16), path);
        for (int i = 0; i < path.Count; i++)
        {
            var a = path[i];
            var b = path[(i + 1) % path.Count];
            Assert.True(Math.Abs(a.X - b.X) <= 128 && Math.Abs(a.Y - b.Y) <= 128, $"jump between {a} and {b}");
        }
    }

    [Fact]
    public void PerchFinder_FindsOnePerchPerTree_AtTheTrunk()
    {
        // Oak at trunk base (5, 25): 3-wide canopy rows 20-23, trunk 24, root 25; a fern and a fence picket row.
        var tiles = new HashSet<(int, int)>();
        for (int x = 4; x <= 6; x++)
            for (int y = 20; y <= 23; y++)
                tiles.Add((x, y));
        tiles.Add((5, 24));
        tiles.Add((5, 25));
        tiles.Add((9, 24));
        for (int x = 3; x < 12; x++)
            tiles.Add((x, 25));
        var pen = new HabitatRect("Forest", 3, 23, 9, 3);

        var perches = PerchFinder.FindTrees((x, y) => tiles.Contains((x, y)), pen);

        PerchSpot perch = Assert.Single(perches);
        Assert.Equal((5, 25), (perch.TileX, perch.TileY));
        Assert.Equal(4.5f * 64, perch.Height);
    }

    [Fact]
    public void Profiles_GiveEachStyleToTheRightSpecies()
    {
        Assert.Equal(MoveStyle.Flier, MoveProfiles.For(ZooIds.Owl).Style);
        Assert.Equal(MoveStyle.Flier, MoveProfiles.For(ZooIds.Flamingo).Style);
        Assert.Equal(MoveStyle.Climber, MoveProfiles.For(ZooIds.Monkey).Style);
        Assert.Equal(MoveStyle.Swimmer, MoveProfiles.For(ZooIds.Capybara).Style);
        Assert.Equal(MoveStyle.BigWalker, MoveProfiles.For(ZooIds.Dinosaur).Style);
        Assert.Equal(1, MoveProfiles.For(ZooIds.Elephant).GroundSpeed);
        Assert.Equal(MoveStyle.Default, MoveProfiles.For(ZooIds.Raccoon).Style);
        Assert.Equal(MoveStyle.Default, MoveProfiles.For("Unknown").Style);
    }
}
