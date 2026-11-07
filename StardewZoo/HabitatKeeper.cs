using Microsoft.Xna.Framework;
using StardewValley;
using StardewValley.Buildings;

namespace StardewZoo;

/// <summary>Keeps zoo animals inside their biome pens and fed.</summary>
internal static class HabitatKeeper
{
    public static void SnapAll(Random rng)
    {
        ForEachZooAnimal((house, animal) => Snap(house, animal, rng, force: true));
    }

    public static void SnapEscaped(Random rng)
    {
        ForEachZooAnimal((house, animal) => Snap(house, animal, rng, force: false));
    }

    public static void FeedAll()
    {
        ForEachZooAnimal((_, animal) =>
        {
            animal.fullness.Value = byte.MaxValue;
            if (animal.happiness.Value < 200)
                animal.happiness.Value = 200;
        });
    }

    public static void ReloadInteriors(Action<string> log)
    {
        Utility.ForEachBuilding(building =>
        {
            if (!ZooIds.IsZoo(building.buildingType.Value) || building.isUnderConstruction())
                return true;

            building.animalDoorOpen.Value = false;
            building.ReloadBuildingData(false, false);
            if (building.GetIndoors() is not GameLocation indoors)
                return true;

            string current = indoors.mapPath.Value ?? "";
            if (current.Contains("StardewZoo", StringComparison.OrdinalIgnoreCase))
                return true;

            string previous = current;
            indoors.mapPath.Value = ZooIds.IndoorMapAsset;
            indoors.loadMap(ZooIds.IndoorMapAsset, true);
            indoors.updateWarps();
            log($"Reloaded zoo interior onto {ZooIds.IndoorMapAsset} (was '{previous}').");
            return true;
        });
    }

    private static void Snap(AnimalHouse house, FarmAnimal animal, Random rng, bool force)
    {
        HabitatRect? pen = ZooHabitats.ForAnimal(animal.type.Value);
        if (pen is not HabitatRect habitat)
            return;

        int tileX = animal.TilePoint.X;
        int tileY = animal.TilePoint.Y;
        if (!force && habitat.Contains(tileX, tileY))
            return;

        (int x, int y) = habitat.RandomTile(rng);
        animal.controller = null;
        animal.Position = new Vector2(x * Game1.tileSize, y * Game1.tileSize);
        animal.noWarpTimer = 3000;
    }

    private static void ForEachZooAnimal(Action<AnimalHouse, FarmAnimal> action)
    {
        Utility.ForEachBuilding(building =>
        {
            if (!ZooIds.IsZoo(building.buildingType.Value) || building.GetIndoors() is not AnimalHouse house)
                return true;
            foreach (FarmAnimal animal in house.animals.Values)
                action(house, animal);
            return true;
        });
    }
}
