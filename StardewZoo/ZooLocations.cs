using StardewValley;

namespace StardewZoo;

/// <summary>Which game locations belong to a zoo: the zoo building interiors plus any zoo pavilion.</summary>
internal static class ZooLocations
{
    /// <summary>Location names with this prefix are zoo locations.</summary>
    public const string NamePrefix = "StardewZoo_";

    /// <summary>Map property that marks a map (e.g. a pavilion) as part of the zoo.</summary>
    public const string MapProperty = "StardewZooLocation";

    /// <summary>Optional map property: "x y width height ..." areas that refuse furniture (pavilion pens).</summary>
    public const string NoFurnitureProperty = "StardewZooNoFurniture";

    /// <summary>Optional map property: "x y x y ..." waypoints visitors walk in order; the route between them stays open.</summary>
    public const string WaypointsProperty = "StardewZooWaypoints";

    public static bool IsZooLocation(GameLocation? location)
    {
        if (location == null)
            return false;
        if (IsZooInterior(location))
            return true;
        if (location.Name?.StartsWith(NamePrefix, StringComparison.Ordinal) == true)
            return true;
        return location.Map?.Properties.ContainsKey(MapProperty) == true;
    }

    /// <summary>The AnimalHouse interior of a zoo building, which uses the six-pen <see cref="ZooHabitats"/> layout.</summary>
    public static bool IsZooInterior(GameLocation? location) =>
        location is AnimalHouse && ZooIds.IsZoo(location.ParentBuilding?.buildingType.Value);
}
