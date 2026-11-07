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
        if (pen is not HabitatRect habitat || !FitsMap(house, habitat))
            return;

        int tileX = animal.TilePoint.X;
        int tileY = animal.TilePoint.Y;
        if (!force && habitat.Contains(tileX, tileY))
            return;

        (int x, int y) = habitat.RandomTile(rng);
        animal.controller = null;
        SetGroundCenter(animal, x * Game1.tileSize + Game1.tileSize / 2, y * Game1.tileSize + Game1.tileSize / 2);
        animal.noWarpTimer = 3000;
    }

    /// <summary>Whether the location's map contains the pen (false while an older, smaller zoo map is loaded).</summary>
    public static bool FitsMap(GameLocation location, HabitatRect pen)
    {
        xTile.Layers.Layer? back = location.Map?.GetLayer("Back");
        return back != null && pen.X + pen.Width <= back.LayerWidth && pen.Y + pen.Height <= back.LayerHeight;
    }

    /// <summary>
    /// Place an animal so its bounding-box centre (what <see cref="Character.TilePoint"/> uses) is at the given pixel.
    /// <see cref="Character.Position"/> is the sprite's top-left, so the offset depends on the frame size.
    /// </summary>
    public static void SetGroundCenter(FarmAnimal animal, float x, float y)
    {
        AnimatedSprite sprite = animal.GetOrLoadTexture();
        animal.Position = new Vector2(x - sprite.SpriteWidth * 2, y + 32 - sprite.SpriteHeight * 4);
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
