namespace StardewZoo;

/// <summary>Turns a zoo's expected daily visitors into how many visitor NPCs walk around, and how often new ones arrive.</summary>
public sealed class VisitorSpawnPlanner
{
    public const int OpenTime = 800;
    public const int CloseTime = 1800;

    /// <summary>Ten-minute slots one visitor spends walking the loop (~180 tiles at speed 2 is ~97s, a slot is ~7s).</summary>
    public const double TourSlots = 14;

    /// <summary>Unspent arrivals a zoo may bank while full, so it doesn't burst when space frees up.</summary>
    private const double MaxBanked = 2;

    private readonly Dictionary<string, double> carry = new();

    /// <summary>Concurrent visitor NPCs for a day's demand: 0 with no visitors, one per <see cref="ModConfig.VisitorsPerOnScreenNpc"/>, capped.</summary>
    public static int MaxOnScreen(int dailyVisitors, ModConfig config)
    {
        if (dailyVisitors <= 0 || config.MaxVisitorsOnScreen <= 0)
            return 0;
        int perNpc = Math.Max(1, config.VisitorsPerOnScreenNpc);
        return Math.Clamp((dailyVisitors + perNpc - 1) / perNpc, 1, config.MaxVisitorsOnScreen);
    }

    /// <summary>Average NPC arrivals per ten-minute slot, so the steady crowd is about <see cref="MaxOnScreen"/>.</summary>
    public static double ArrivalsPerSlot(int dailyVisitors, ModConfig config)
    {
        if (dailyVisitors <= 0)
            return 0;
        return dailyVisitors / (Math.Max(1, config.VisitorsPerOnScreenNpc) * TourSlots);
    }

    /// <summary>Called every ten in-game minutes per zoo: how many NPCs to spawn now. The first slot of the day spawns one right away.</summary>
    public int SpawnsDue(string zooId, int dailyVisitors, int onScreen, ModConfig config)
    {
        int max = MaxOnScreen(dailyVisitors, config);
        if (max == 0)
        {
            this.carry.Remove(zooId);
            return 0;
        }

        double banked = (this.carry.TryGetValue(zooId, out double value) ? value : 1) + ArrivalsPerSlot(dailyVisitors, config);
        int due = Math.Min(Math.Max(0, max - onScreen), (int)Math.Floor(banked));
        this.carry[zooId] = Math.Min(banked - due, MaxBanked);
        return due;
    }

    public void Reset() => this.carry.Clear();
}
