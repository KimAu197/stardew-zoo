namespace StardewZoo;

public readonly record struct HabitatRect(string Id, int X, int Y, int Width, int Height)
{
    public bool Contains(int tileX, int tileY) =>
        tileX >= this.X && tileX < this.X + this.Width && tileY >= this.Y && tileY < this.Y + this.Height;

    public (int X, int Y) Clamp(int tileX, int tileY)
    {
        int x = Math.Clamp(tileX, this.X, this.X + this.Width - 1);
        int y = Math.Clamp(tileY, this.Y, this.Y + this.Height - 1);
        return (x, y);
    }

    public (int X, int Y) RandomTile(Random rng) =>
        (this.X + rng.Next(this.Width), this.Y + rng.Next(this.Height));
}

public readonly record struct ZooRect(int X, int Y, int Width, int Height)
{
    public bool Contains(int tileX, int tileY) =>
        tileX >= this.X && tileX < this.X + this.Width && tileY >= this.Y && tileY < this.Y + this.Height;
}

/// <summary>A walk-in exhibit hall: a door on the park, and an interior region of the same zoo map.</summary>
public sealed record PavilionInfo(
    string Id,
    ZooRect Region,
    ZooRect Facade,
    (int X, int Y) OutsideDoor,
    (int X, int Y) OutsideArrival,
    (int X, int Y) InsideDoor,
    (int X, int Y) InsideArrival,
    ZooRect Barrier
);

/// <summary>One leg of the visitor tour: walk to the tile, or (through a pavilion door) appear there.</summary>
public readonly record struct VisitorStep(int X, int Y, bool Teleport);

/// <summary>Biome pens and map regions. Coordinates come from tools/zoo_layout.py via ZooLayout.g.cs.</summary>
public static class ZooHabitats
{
    public const string Ice = "Ice";
    public const string Water = "Water";
    public const string Savanna = "Savanna";
    public const string Jungle = "Jungle";
    public const string Forest = "Forest";
    public const string Prehistoric = "Prehistoric";

    public static readonly IReadOnlyList<HabitatRect> All = new[]
    {
        ZooLayout.IcePen, ZooLayout.WaterPen, ZooLayout.SavannaPen, ZooLayout.JunglePen, ZooLayout.ForestPen, ZooLayout.PrehistoricPen
    };

    /// <summary>The park plus every pavilion interior; nothing outside them is walkable.</summary>
    public static readonly IReadOnlyList<ZooRect> Regions =
        new[] { ZooLayout.Outdoor }.Concat(ZooLayout.Pavilions.Select(p => p.Region)).ToArray();

    public static readonly IReadOnlyDictionary<string, string> AnimalHabitat = new Dictionary<string, string>
    {
        [ZooIds.Penguin] = Ice,
        [ZooIds.SeaLion] = Water,
        [ZooIds.Capybara] = Water,
        [ZooIds.Flamingo] = Water,
        [ZooIds.NightHeron] = Water,
        [ZooIds.Lion] = Savanna,
        [ZooIds.Giraffe] = Savanna,
        [ZooIds.Elephant] = Savanna,
        [ZooIds.Alpaca] = Savanna,
        [ZooIds.Monkey] = Jungle,
        [ZooIds.Gorilla] = Jungle,
        [ZooIds.Panda] = Jungle,
        [ZooIds.Bear] = Forest,
        [ZooIds.Raccoon] = Forest,
        [ZooIds.Owl] = Forest,
        [ZooIds.Deer] = Forest,
        [ZooIds.Dinosaur] = Prehistoric
    };

    /// <summary>
    /// Every tile of the visitor tour in order, across regions. Consecutive tiles in the same region are joined by a walk;
    /// a pair that straddles a pavilion door isn't walkable (visitors teleport there, see <see cref="ZooLayout.VisitorRoute"/>).
    /// </summary>
    public static readonly IReadOnlyList<(int X, int Y)> VisitorLoop = ZooLayout.VisitorRoute.Select(s => (s.X, s.Y)).ToArray();

    public static HabitatRect? ForAnimal(string? animalType)
    {
        if (animalType == null || !AnimalHabitat.TryGetValue(animalType, out string? id))
            return null;
        return All.First(h => h.Id == id);
    }

    /// <summary>The park or pavilion region containing a tile, if any.</summary>
    public static ZooRect? RegionAt(int tileX, int tileY)
    {
        foreach (ZooRect region in Regions)
        {
            if (region.Contains(tileX, tileY))
                return region;
        }
        return null;
    }

    public static PavilionInfo? Pavilion(string? id) => ZooLayout.Pavilions.FirstOrDefault(p => p.Id == id);

    /// <summary>
    /// Where a camera of the given pixel size should sit along one axis to show only the region: clamped inside it,
    /// or centred on it (with void around) when the region is smaller than the screen.
    /// </summary>
    public static int ClampViewportAxis(int position, int viewSize, int regionStart, int regionSize)
    {
        if (regionSize <= viewSize)
            return regionStart - (viewSize - regionSize) / 2;
        return Math.Clamp(position, regionStart, regionStart + regionSize - viewSize);
    }

    public static int CountFilled(IEnumerable<string> animalTypes)
    {
        return animalTypes
            .Select(type => AnimalHabitat.TryGetValue(type, out string? habitat) ? habitat : null)
            .Where(habitat => habitat != null)
            .Distinct()
            .Count();
    }
}
