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

    /// <summary>Daily visitors any stocked zoo draws, before tier / price / rating.</summary>
    public double DemandBase { get; set; } = 2;

    /// <summary>Daily visitors for the first species; more species add less each (see <see cref="SpeciesDiminishing"/>).</summary>
    public double DemandPerSpecies { get; set; } = 10;

    /// <summary>Exponent on species count: 1 = linear, lower = stronger diminishing returns.</summary>
    public double SpeciesDiminishing { get; set; } = 0.75;

    /// <summary>Daily visitors per sqrt(total animals), a weaker pull than variety.</summary>
    public double DemandPerAnimal { get; set; } = 3;

    /// <summary>Extra demand as the price drops from fair toward 1g (0.5 = up to +50%).</summary>
    public double CheapPriceBoost { get; set; } = 0.5;

    /// <summary>Demand multiplier on a free (0g) day: the biggest crowd, but no ticket income.</summary>
    public double FreeEntryBoost { get; set; } = 1.6;

    /// <summary>How steeply demand falls above the fair price: multiplier = e^(-k * (price/fair - 1)).</summary>
    public double OverpriceElasticity { get; set; } = 1.6;

    /// <summary>Daily visitors represented by each visitor NPC walking around at once.</summary>
    public int VisitorsPerOnScreenNpc { get; set; } = 7;

    /// <summary>Most visitor NPCs walking around one zoo at once (performance cap).</summary>
    public int MaxVisitorsOnScreen { get; set; } = 14;

    public int MaxStoredReviews { get; set; } = 12;

    public int ReviewSampleSize { get; set; } = 8;

    /// <summary>Whether zoo animals call out when the player walks near them, without petting.</summary>
    public bool AnimalCallsOnApproach { get; set; } = true;

    /// <summary>How close, in tiles, the player must get for an animal to call.</summary>
    public float AnimalCallRadius { get; set; } = 3f;

    /// <summary>Minimum seconds before the same animal can call again (the player must also leave and come back).</summary>
    public double AnimalCallCooldownSeconds { get; set; } = 8;

    /// <summary>Whether zoo animals use species movement (birds fly, monkeys climb, sea lions swim laps, big animals plod).</summary>
    public bool AnimalMovementStyles { get; set; } = true;

    /// <summary>Whether the dinosaur's footsteps nudge the screen slightly when it stomps near the player.</summary>
    public bool DinosaurStompShake { get; set; } = true;

    /// <summary>Income / demand multiplier per zoo building ID; unknown IDs use 1.0.</summary>
    public Dictionary<string, double> Multipliers { get; set; } = new()
    {
        [ZooIds.Zoo] = 1.0,
        [ZooIds.BigZoo] = 1.5,
        [ZooIds.DeluxeZoo] = 2.0
    };
}
