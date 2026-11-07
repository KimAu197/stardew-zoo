namespace StardewZoo;

public enum MoveStyle
{
    Default,
    Flier,
    Climber,
    Swimmer,
    BigWalker
}

public enum BrainState
{
    Ground,
    Sitting,
    WalkTo,
    Flying,
    Landing,
    Perched,
    ClimbUp,
    InTree,
    Swing,
    ClimbDown,
    Lap
}

public enum BrainPose
{
    None,
    Walk,
    Fly,
    Perch,
    Climb,
    Sit,
    Hang
}

/// <summary>A spot an animal can perch or climb: the ground tile at its base and the height of the perch above it, in pixels.</summary>
public readonly record struct PerchSpot(int TileX, int TileY, float Height);

/// <summary>Per-species movement tuning. Rates are average events per minute; speeds are pixels per second.</summary>
public sealed record MoveProfile(MoveStyle Style)
{
    public double FlightsPerMinute { get; init; }
    public double PerchesPerMinute { get; init; }
    public bool PerchesAtNight { get; init; }
    public double WaterTripsPerMinute { get; init; }
    public bool SwimsLaps { get; init; }
    public double ClimbsPerMinute { get; init; }
    public double SitsPerMinute { get; init; }
    public float CruiseAltitude { get; init; } = 160;
    public float FlySpeed { get; init; } = 180;
    public float WalkSpeed { get; init; } = 120;
    public float LapSpeed { get; init; } = 270;
    public int GroundSpeed { get; init; } = 2;
    public float StepIntervalMs { get; init; } = 175;
}

public static class MoveProfiles
{
    public static readonly MoveProfile Default = new(MoveStyle.Default);

    private static readonly IReadOnlyDictionary<string, MoveProfile> ByType = new Dictionary<string, MoveProfile>
    {
        [ZooIds.Owl] = new(MoveStyle.Flier) { FlightsPerMinute = 0.8, PerchesPerMinute = 1.2, PerchesAtNight = true, CruiseAltitude = 112, FlySpeed = 170 },
        [ZooIds.NightHeron] = new(MoveStyle.Flier) { FlightsPerMinute = 1.2, PerchesPerMinute = 0.2, WaterTripsPerMinute = 0.8, CruiseAltitude = 160, FlySpeed = 200 },
        [ZooIds.Flamingo] = new(MoveStyle.Flier) { FlightsPerMinute = 0.2, WaterTripsPerMinute = 2.5, CruiseAltitude = 150, FlySpeed = 170 },
        [ZooIds.Monkey] = new(MoveStyle.Climber) { ClimbsPerMinute = 2.5 },
        [ZooIds.SeaLion] = new(MoveStyle.Swimmer) { WaterTripsPerMinute = 3, SwimsLaps = true, LapSpeed = 280 },
        [ZooIds.Capybara] = new(MoveStyle.Swimmer) { WaterTripsPerMinute = 1.5, SitsPerMinute = 0.5 },
        [ZooIds.Elephant] = new(MoveStyle.BigWalker) { GroundSpeed = 1, StepIntervalMs = 300 },
        [ZooIds.Giraffe] = new(MoveStyle.BigWalker) { GroundSpeed = 1, StepIntervalMs = 260 },
        [ZooIds.Dinosaur] = new(MoveStyle.BigWalker) { GroundSpeed = 1, StepIntervalMs = 340 },
        [ZooIds.Gorilla] = new(MoveStyle.Default) { GroundSpeed = 1, StepIntervalMs = 240, SitsPerMinute = 1.2 },
        [ZooIds.Panda] = new(MoveStyle.Default) { SitsPerMinute = 1.5 }
    };

    public static MoveProfile For(string? animalType) =>
        animalType != null && ByType.TryGetValue(animalType, out MoveProfile? profile) ? profile : Default;
}

/// <summary>What the brain knows about the animal's pen.</summary>
public sealed class BrainWorld
{
    public BrainWorld(HabitatRect pen, IReadOnlyList<PerchSpot> perches, IReadOnlyList<(int X, int Y)> waterTiles)
    {
        this.Pen = pen;
        this.Perches = perches;
        this.WaterTiles = waterTiles;
        this.LapPath = LapPlanner.Build(waterTiles);
    }

    public HabitatRect Pen { get; }
    public IReadOnlyList<PerchSpot> Perches { get; }
    public IReadOnlyList<(int X, int Y)> WaterTiles { get; }
    public IReadOnlyList<(float X, float Y)> LapPath { get; }
}

/// <param name="ElapsedMs">Time since the last tick.</param>
/// <param name="X">The animal's ground position (bounding-box centre), in pixels.</param>
/// <param name="Y">The animal's ground position (bounding-box centre), in pixels.</param>
/// <param name="Night">Whether it's evening (nocturnal animals look for perches).</param>
/// <param name="Sleeping">Whether farm animals are asleep (no new activities start).</param>
/// <param name="IsBaby">Babies keep vanilla wandering.</param>
public readonly record struct BrainInput(double ElapsedMs, float X, float Y, bool Night, bool Sleeping, bool IsBaby);

/// <param name="Controlled">Whether the brain owns the animal's position this tick (vanilla wandering is paused).</param>
/// <param name="X">The ground position to place the animal at, if controlled.</param>
/// <param name="Y">The ground position to place the animal at, if controlled.</param>
/// <param name="Altitude">Pixels to draw the animal above its ground position.</param>
/// <param name="Facing">0 up, 1 right, 2 down, 3 left.</param>
/// <param name="SitMs">If positive, an idle sit animation starts this tick and lasts this long.</param>
public readonly record struct BrainOutput(bool Controlled, float X, float Y, float Altitude, int Facing, BrainPose Pose, int SitMs);

/// <summary>Pure movement state machine for one zoo animal: walk, fly, perch, climb, swing, and swim laps.</summary>
public sealed class AnimalBrain
{
    private const float TileSize = 64;
    private const float ClimbUpSpeed = 70;
    private const float ClimbDownSpeed = 100;
    private const float AirClimbSpeed = 200;
    private const float SwingSpeed = 160;
    private const float SwingSag = 40;
    private const float MaxSwingTiles = 7;

    private readonly MoveProfile profile;
    private readonly BrainWorld world;
    private readonly Random rng;

    private float x;
    private float y;
    private float targetX;
    private float targetY;
    private float altitude;
    private float targetAltitude;
    private int facing = 2;
    private double stateMs;
    private double stateLimitMs;
    private double cooldownMs;
    private PerchSpot? perch;
    private PerchSpot? nextPerch;
    private float swingFromAltitude;
    private float swingFromX;
    private float swingFromY;
    private BrainState afterWalk;
    private int lapIndex;
    private int lapStepsLeft;
    private double clockMs;

    public AnimalBrain(MoveProfile profile, BrainWorld world, Random rng)
    {
        this.profile = profile;
        this.world = world;
        this.rng = rng;
        this.cooldownMs = 2000 + rng.Next(4000);
    }

    public BrainState State { get; private set; } = BrainState.Ground;

    public float Altitude => this.altitude;

    public PerchSpot? Perch => this.perch;

    public BrainOutput Tick(BrainInput input)
    {
        double dt = Math.Max(0, input.ElapsedMs);
        this.clockMs += dt;
        this.stateMs += dt;
        if (this.State is BrainState.Ground)
        {
            this.x = input.X;
            this.y = input.Y;
            this.altitude = 0;
            this.cooldownMs -= dt;
            if (!input.IsBaby && !input.Sleeping && this.cooldownMs <= 0)
                this.ChooseActivity(dt, input.Night);
            else if (!input.IsBaby && input.Sleeping && this.cooldownMs <= 0 && this.profile.PerchesAtNight)
                this.TryStartFlight(toPerch: true);
        }
        else
        {
            this.Advance(dt, input);
        }
        return this.Output();
    }

    /// <summary>Drop any activity and return to vanilla wandering at the given ground position.</summary>
    public void Reset(float groundX, float groundY)
    {
        this.x = groundX;
        this.y = groundY;
        this.altitude = 0;
        this.perch = null;
        this.Enter(BrainState.Ground);
        this.cooldownMs = 2000;
    }

    private BrainOutput Output()
    {
        int sitMs = 0;
        if (this.State == BrainState.Sitting && this.stateMs == 0)
            sitMs = (int)this.stateLimitMs;
        BrainPose pose = this.State switch
        {
            BrainState.WalkTo or BrainState.Lap => BrainPose.Walk,
            BrainState.Flying or BrainState.Landing => BrainPose.Fly,
            BrainState.Perched => BrainPose.Perch,
            BrainState.ClimbUp or BrainState.ClimbDown => BrainPose.Climb,
            BrainState.InTree => BrainPose.Sit,
            BrainState.Swing => BrainPose.Hang,
            _ => BrainPose.None
        };
        bool controlled = this.State is not (BrainState.Ground or BrainState.Sitting);
        return new BrainOutput(controlled, this.x, this.y, this.altitude, this.facing, pose, sitMs);
    }

    private void ChooseActivity(double dt, bool night)
    {
        MoveProfile p = this.profile;
        if (p.PerchesAtNight && night && this.world.Perches.Count > 0)
        {
            if (this.TryStartFlight(toPerch: true))
                return;
        }
        if (Roll(p.FlightsPerMinute, dt) && this.TryStartFlight(toPerch: false))
            return;
        if (Roll(p.PerchesPerMinute, dt) && this.TryStartFlight(toPerch: true))
            return;
        if (Roll(p.ClimbsPerMinute, dt) && this.TryStartClimb())
            return;
        if (Roll(p.WaterTripsPerMinute, dt) && this.TryStartWaterTrip())
            return;
        if (Roll(p.SitsPerMinute, dt))
        {
            this.Enter(BrainState.Sitting);
            this.stateLimitMs = 3000 + this.rng.Next(4000);
        }
    }

    private bool Roll(double perMinute, double dt) =>
        perMinute > 0 && this.rng.NextDouble() < 1 - Math.Exp(-perMinute * dt / 60000.0);

    private bool TryStartFlight(bool toPerch)
    {
        if (this.profile.Style != MoveStyle.Flier)
            return false;
        if (toPerch)
        {
            if (this.world.Perches.Count == 0)
                return false;
            this.perch = this.world.Perches[this.rng.Next(this.world.Perches.Count)];
            (this.targetX, this.targetY) = TileCenter(this.perch.Value.TileX, this.perch.Value.TileY);
        }
        else
        {
            this.perch = null;
            (this.targetX, this.targetY) = this.RandomPenPoint(minTiles: 2);
        }
        this.targetAltitude = this.profile.CruiseAltitude;
        this.Enter(BrainState.Flying);
        return true;
    }

    private bool TryStartClimb()
    {
        if (this.profile.Style != MoveStyle.Climber || this.world.Perches.Count == 0)
            return false;
        this.perch = this.world.Perches[this.rng.Next(this.world.Perches.Count)];
        (this.targetX, this.targetY) = TileCenter(this.perch.Value.TileX, this.perch.Value.TileY);
        this.afterWalk = BrainState.ClimbUp;
        this.Enter(BrainState.WalkTo);
        return true;
    }

    private bool TryStartWaterTrip()
    {
        if (this.world.WaterTiles.Count == 0)
            return false;
        if (this.profile.SwimsLaps && this.world.LapPath.Count >= 3)
        {
            this.lapIndex = this.NearestLapIndex();
            (this.targetX, this.targetY) = this.world.LapPath[this.lapIndex];
            this.lapStepsLeft = this.world.LapPath.Count * (2 + this.rng.Next(2));
            this.afterWalk = BrainState.Lap;
        }
        else
        {
            (int tx, int ty) = this.world.WaterTiles[this.rng.Next(this.world.WaterTiles.Count)];
            (this.targetX, this.targetY) = TileCenter(tx, ty);
            this.afterWalk = BrainState.Ground;
        }
        this.Enter(BrainState.WalkTo);
        return true;
    }

    private void Advance(double dt, BrainInput input)
    {
        float seconds = (float)(dt / 1000.0);
        switch (this.State)
        {
            case BrainState.Sitting:
                if (this.stateMs >= this.stateLimitMs)
                    this.Land();
                break;

            case BrainState.WalkTo:
                if (input.Sleeping && this.afterWalk != BrainState.ClimbUp)
                {
                    this.Land();
                    break;
                }
                if (this.MoveToward(this.targetX, this.targetY, this.profile.WalkSpeed * seconds))
                {
                    if (this.afterWalk == BrainState.ClimbUp)
                    {
                        this.targetAltitude = this.perch!.Value.Height;
                        this.facing = 0;
                    }
                    if (this.afterWalk == BrainState.Ground)
                        this.Land();
                    else
                        this.Enter(this.afterWalk);
                }
                break;

            case BrainState.Lap:
                if (input.Sleeping || this.lapStepsLeft <= 0)
                {
                    this.Land();
                    break;
                }
                if (this.MoveToward(this.targetX, this.targetY, this.profile.LapSpeed * seconds))
                {
                    this.lapIndex = (this.lapIndex + 1) % this.world.LapPath.Count;
                    (this.targetX, this.targetY) = this.world.LapPath[this.lapIndex];
                    this.lapStepsLeft--;
                }
                break;

            case BrainState.Flying:
            {
                if (input.Sleeping && this.perch == null)
                {
                    (this.targetX, this.targetY) = (this.x, this.y);
                }
                this.altitude = Approach(this.altitude, this.profile.CruiseAltitude, AirClimbSpeed * seconds);
                float lift = Math.Clamp(this.altitude / (this.profile.CruiseAltitude * 0.5f), 0.25f, 1f);
                if (this.MoveToward(this.targetX, this.targetY, this.profile.FlySpeed * lift * seconds))
                {
                    this.targetAltitude = this.perch?.Height ?? 0;
                    this.Enter(BrainState.Landing);
                }
                break;
            }

            case BrainState.Landing:
                this.altitude = Approach(this.altitude, this.targetAltitude, AirClimbSpeed * seconds);
                if (this.altitude == this.targetAltitude)
                {
                    if (this.perch != null)
                    {
                        this.facing = 2;
                        this.Enter(BrainState.Perched);
                        this.stateLimitMs = 8000 + this.rng.Next(14000);
                    }
                    else
                    {
                        this.Land();
                    }
                }
                break;

            case BrainState.Perched:
                if (this.stateMs >= this.stateLimitMs && !(this.profile.PerchesAtNight && (input.Night || input.Sleeping)))
                {
                    if (input.Sleeping)
                        break;
                    this.perch = null;
                    (this.targetX, this.targetY) = this.RandomPenPoint(minTiles: 1);
                    this.Enter(BrainState.Flying);
                }
                break;

            case BrainState.ClimbUp:
                this.facing = 0;
                this.altitude = Approach(this.altitude, this.targetAltitude, ClimbUpSpeed * seconds);
                if (this.altitude == this.targetAltitude)
                {
                    this.facing = 2;
                    this.Enter(BrainState.InTree);
                    this.stateLimitMs = 6000 + this.rng.Next(9000);
                }
                break;

            case BrainState.InTree:
                if (input.Sleeping || this.stateMs < this.stateLimitMs)
                    break;
                if (this.rng.NextDouble() < 0.5 && this.TryPickSwingTarget())
                {
                    this.swingFromAltitude = this.altitude;
                    this.swingFromX = this.x;
                    this.swingFromY = this.y;
                    float distance = Distance(this.x, this.y, this.targetX, this.targetY);
                    this.stateLimitMs = Math.Max(400, distance / SwingSpeed * 1000);
                    this.facing = this.targetX >= this.x ? 1 : 3;
                    this.Enter(BrainState.Swing);
                }
                else
                {
                    this.facing = 0;
                    this.Enter(BrainState.ClimbDown);
                }
                break;

            case BrainState.Swing:
            {
                float t = (float)Math.Clamp(this.stateMs / this.stateLimitMs, 0, 1);
                float toAltitude = this.nextPerch!.Value.Height;
                this.x = Lerp(this.swingFromX, this.targetX, t);
                this.y = Lerp(this.swingFromY, this.targetY, t);
                this.altitude = Lerp(this.swingFromAltitude, toAltitude, t) - SwingSag * (float)Math.Sin(Math.PI * t);
                if (t >= 1)
                {
                    this.perch = this.nextPerch;
                    this.nextPerch = null;
                    this.altitude = toAltitude;
                    this.facing = 2;
                    this.Enter(BrainState.InTree);
                    this.stateLimitMs = 4000 + this.rng.Next(8000);
                }
                break;
            }

            case BrainState.ClimbDown:
                this.facing = 0;
                this.altitude = Approach(this.altitude, 0, ClimbDownSpeed * seconds);
                if (this.altitude == 0)
                    this.Land();
                break;
        }
        this.ClampToPen();
    }

    private bool TryPickSwingTarget()
    {
        if (this.perch is not PerchSpot current)
            return false;
        var options = this.world.Perches
            .Where(p => p != current && Math.Abs(p.TileX - current.TileX) + Math.Abs(p.TileY - current.TileY) <= MaxSwingTiles)
            .ToList();
        if (options.Count == 0)
            return false;
        this.nextPerch = options[this.rng.Next(options.Count)];
        (this.targetX, this.targetY) = TileCenter(this.nextPerch.Value.TileX, this.nextPerch.Value.TileY);
        return true;
    }

    private void Land()
    {
        this.altitude = 0;
        this.perch = null;
        this.Enter(BrainState.Ground);
        this.cooldownMs = 4000 + this.rng.Next(6000);
    }

    private void Enter(BrainState state)
    {
        this.State = state;
        this.stateMs = 0;
    }

    /// <summary>Move the ground position toward a target; returns true on arrival.</summary>
    private bool MoveToward(float tx, float ty, float step)
    {
        float dx = tx - this.x;
        float dy = ty - this.y;
        float distance = MathF.Sqrt(dx * dx + dy * dy);
        if (distance > 0.01f)
            this.facing = FacingFor(dx, dy);
        if (distance <= step)
        {
            this.x = tx;
            this.y = ty;
            return true;
        }
        this.x += dx / distance * step;
        this.y += dy / distance * step;
        return false;
    }

    private void ClampToPen()
    {
        HabitatRect pen = this.world.Pen;
        this.x = Math.Clamp(this.x, pen.X * TileSize + 8, (pen.X + pen.Width) * TileSize - 8);
        this.y = Math.Clamp(this.y, pen.Y * TileSize + 8, (pen.Y + pen.Height) * TileSize - 8);
    }

    private (float X, float Y) RandomPenPoint(int minTiles)
    {
        HabitatRect pen = this.world.Pen;
        (float X, float Y) best = TileCenter(pen.X, pen.Y);
        float bestDistance = -1;
        for (int attempt = 0; attempt < 8; attempt++)
        {
            (int tx, int ty) = pen.RandomTile(this.rng);
            (float X, float Y) point = TileCenter(tx, ty);
            float distance = Distance(this.x, this.y, point.X, point.Y);
            if (distance >= minTiles * TileSize)
                return point;
            if (distance > bestDistance)
                (best, bestDistance) = (point, distance);
        }
        return best;
    }

    private int NearestLapIndex()
    {
        int best = 0;
        float bestDistance = float.MaxValue;
        for (int i = 0; i < this.world.LapPath.Count; i++)
        {
            (float px, float py) = this.world.LapPath[i];
            float distance = Distance(this.x, this.y, px, py);
            if (distance < bestDistance)
                (best, bestDistance) = (i, distance);
        }
        return best;
    }

    public static int FacingFor(float dx, float dy)
    {
        if (Math.Abs(dx) > Math.Abs(dy))
            return dx > 0 ? 1 : 3;
        return dy > 0 ? 2 : 0;
    }

    public static (float X, float Y) TileCenter(int tileX, int tileY) =>
        (tileX * TileSize + TileSize / 2, tileY * TileSize + TileSize / 2);

    private static float Approach(float value, float target, float step) =>
        value < target ? Math.Min(target, value + step) : Math.Max(target, value - step);

    private static float Lerp(float a, float b, float t) => a + (b - a) * t;

    private static float Distance(float ax, float ay, float bx, float by) =>
        MathF.Sqrt((ax - bx) * (ax - bx) + (ay - by) * (ay - by));
}

public static class LapPlanner
{
    /// <summary>Order the shoreline water tiles around the pool's centre, as pixel waypoints for a swimming lap.</summary>
    public static IReadOnlyList<(float X, float Y)> Build(IReadOnlyList<(int X, int Y)> waterTiles)
    {
        if (waterTiles.Count < 3)
            return Array.Empty<(float, float)>();
        var set = new HashSet<(int, int)>(waterTiles);
        double cx = waterTiles.Average(t => t.X);
        double cy = waterTiles.Average(t => t.Y);
        var ring = waterTiles
            .Where(t => !set.Contains((t.X + 1, t.Y)) || !set.Contains((t.X - 1, t.Y)) || !set.Contains((t.X, t.Y + 1)) || !set.Contains((t.X, t.Y - 1)))
            .OrderBy(t => Math.Atan2(t.Y - cy, t.X - cx))
            .Select(t => AnimalBrain.TileCenter(t.X, t.Y))
            .ToList();
        return ring.Count >= 3 ? ring : waterTiles.Select(t => AnimalBrain.TileCenter(t.X, t.Y)).ToList();
    }
}

public static class PerchFinder
{
    /// <summary>
    /// Find trees in a pen from map tiles: a tree is a vertical stack of at least <paramref name="minStack"/> drawn tiles
    /// (Front/AlwaysFront) whose bottom is inside the pen. Neighbouring columns of one canopy count once, using the column
    /// that reaches lowest (the trunk). The perch sits near the top of the stack.
    /// </summary>
    /// <param name="hasTile">Whether a tree-ish tile is drawn at (x, y).</param>
    /// <param name="pen">The pen; stacks may rise above it.</param>
    /// <param name="minStack">Minimum tiles in a stack.</param>
    public static List<PerchSpot> FindTrees(Func<int, int, bool> hasTile, HabitatRect pen, int minStack = 3)
    {
        var stacks = new List<(int X, int Bottom, int Top)>();
        for (int x = pen.X; x < pen.X + pen.Width; x++)
        {
            int y = pen.Y + pen.Height - 1;
            while (y >= pen.Y)
            {
                if (!hasTile(x, y))
                {
                    y--;
                    continue;
                }
                int bottom = y;
                int top = y;
                while (hasTile(x, top - 1) && top - 1 > pen.Y - 8)
                    top--;
                if (bottom - top + 1 >= minStack)
                    stacks.Add((x, bottom, top));
                y = top - 1;
            }
        }

        var perches = new List<PerchSpot>();
        var used = new bool[stacks.Count];
        for (int i = 0; i < stacks.Count; i++)
        {
            if (used[i])
                continue;
            var cluster = new List<int> { i };
            used[i] = true;
            for (int k = 0; k < cluster.Count; k++)
            {
                var a = stacks[cluster[k]];
                for (int j = 0; j < stacks.Count; j++)
                {
                    var b = stacks[j];
                    if (!used[j] && Math.Abs(a.X - b.X) == 1 && a.Top <= b.Bottom && b.Top <= a.Bottom)
                    {
                        used[j] = true;
                        cluster.Add(j);
                    }
                }
            }
            var trunk = cluster.Select(c => stacks[c]).OrderByDescending(s => s.Bottom).ThenBy(s => Math.Abs(s.X - cluster.Average(c => stacks[c].X))).First();
            int top = cluster.Min(c => stacks[c].Top);
            float height = (trunk.Bottom - top - 0.5f) * 64;
            perches.Add(new PerchSpot(trunk.X, trunk.Bottom, Math.Max(64, height)));
        }
        return perches;
    }
}
