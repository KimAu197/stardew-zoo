namespace StardewZoo;

/// <summary>Per-save zoo state written with Helper.Data.WriteSaveData.</summary>
public sealed class ZooSaveData
{
    public const string Key = "zoo-ops";

    public List<ZooReview> Reviews { get; set; } = new();

    public List<string> CustomRecordings { get; set; } = new();

    public int LastVisitors { get; set; }

    public int LastIncome { get; set; }

    public double LastRating { get; set; } = ZooIncome.StartingRating;
}
