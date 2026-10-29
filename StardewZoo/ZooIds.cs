namespace StardewZoo;

/// <summary>Building IDs shared with the [CP] Stardew Zoo content pack.</summary>
public static class ZooIds
{
    public const string Zoo = "StardewZoo.Zoo";
    public const string BigZoo = "StardewZoo.BigZoo";
    public const string DeluxeZoo = "StardewZoo.DeluxeZoo";

    public static readonly IReadOnlyList<string> BuildingTypes = new[] { Zoo, BigZoo, DeluxeZoo };

    public static bool IsZoo(string? buildingType)
    {
        return buildingType != null && BuildingTypes.Contains(buildingType);
    }
}
