namespace StardewZoo;

/// <summary>Player-editable settings, stored in the mod's config.json.</summary>
public sealed class ModConfig
{
    /// <summary>Admission fee charged per visitor, in gold. 0 means a free day.</summary>
    public int TicketPrice { get; set; } = 50;

    public int MinTicketPrice { get; set; } = 0;

    public int MaxTicketPrice { get; set; } = 1000;

    public int FairPerAnimal { get; set; } = 10;

    public int FairPerSpecies { get; set; } = 15;

    public int FairPerHabitat { get; set; } = 12;

    public int BaseFair { get; set; } = 20;

    public int BaseVisitors { get; set; } = 4;

    public int VisitorsPerAnimal { get; set; } = 3;

    public int VisitorsPerSpecies { get; set; } = 5;

    public int VisitorsPerHabitat { get; set; } = 4;

    public int MaxStoredReviews { get; set; } = 12;

    public int ReviewSampleSize { get; set; } = 8;

    /// <summary>Income / demand multiplier per zoo building ID; unknown IDs use 1.0.</summary>
    public Dictionary<string, double> Multipliers { get; set; } = new()
    {
        [ZooIds.Zoo] = 1.0,
        [ZooIds.BigZoo] = 1.5,
        [ZooIds.DeluxeZoo] = 2.0
    };
}
