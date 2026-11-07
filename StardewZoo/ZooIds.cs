namespace StardewZoo;

/// <summary>Building and animal IDs shared with the [CP] Stardew Zoo content pack.</summary>
public static class ZooIds
{
    public const string Zoo = "StardewZoo.Zoo";
    public const string BigZoo = "StardewZoo.BigZoo";
    public const string DeluxeZoo = "StardewZoo.DeluxeZoo";

    public const string IndoorMap = "StardewZoo";
    public const string IndoorMapAsset = @"Maps\StardewZoo";

    public const string Penguin = "StardewZoo.Penguin";
    public const string Panda = "StardewZoo.Panda";
    public const string Lion = "StardewZoo.Lion";
    public const string Giraffe = "StardewZoo.Giraffe";
    public const string Monkey = "StardewZoo.Monkey";
    public const string Capybara = "StardewZoo.Capybara";
    public const string Elephant = "StardewZoo.Elephant";
    public const string Dinosaur = "StardewZoo.Dinosaur";
    public const string Gorilla = "StardewZoo.Gorilla";
    public const string Raccoon = "StardewZoo.Raccoon";
    public const string Alpaca = "StardewZoo.Alpaca";
    public const string SeaLion = "StardewZoo.SeaLion";
    public const string Bear = "StardewZoo.Bear";
    public const string Flamingo = "StardewZoo.Flamingo";
    public const string Owl = "StardewZoo.Owl";
    public const string Deer = "StardewZoo.Deer";
    public const string NightHeron = "StardewZoo.NightHeron";

    public const string TicketAction = "StardewZoo_TicketBooth";
    public const string ReviewAction = "StardewZoo_ReviewBoard";
    public const string StudioAction = "StardewZoo_RecordingStudio";

    /// <summary>Qualified item ID prefix of the zoo furniture in Data/Furniture.</summary>
    public const string FurniturePrefix = "(F)StardewZoo.";

    public static readonly IReadOnlyList<string> BuildingTypes = new[] { Zoo, BigZoo, DeluxeZoo };

    public static readonly IReadOnlyList<string> AnimalTypes = new[]
    {
        Penguin, Panda, Lion, Giraffe, Monkey, Capybara, Elephant, Dinosaur, Gorilla, Raccoon, Alpaca, SeaLion, Bear,
        Flamingo, Owl, Deer, NightHeron
    };

    public static bool IsZoo(string? buildingType)
    {
        return buildingType != null && BuildingTypes.Contains(buildingType);
    }

    public static string ShortName(string animalType)
    {
        const string prefix = "StardewZoo.";
        return animalType.StartsWith(prefix, StringComparison.Ordinal) ? animalType[prefix.Length..] : animalType;
    }

    public static string CueName(string animalType) => "StardewZoo_" + ShortName(animalType);
}
