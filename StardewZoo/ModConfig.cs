namespace StardewZoo;

/// <summary>Player-editable settings, stored in the mod's config.json.</summary>
public sealed class ModConfig
{
    public int PricePerAnimal { get; set; } = 50;

    public int PricePerSpecies { get; set; } = 200;

    public int TicketPrice { get; set; } = 50;

    /// <summary>Income multiplier per zoo building ID; unknown IDs use 1.0.</summary>
    public Dictionary<string, double> Multipliers { get; set; } = new()
    {
        [ZooIds.Zoo] = 1.0,
        [ZooIds.BigZoo] = 1.5,
        [ZooIds.DeluxeZoo] = 2.0
    };
}
