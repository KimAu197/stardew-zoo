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

/// <summary>Biome pens. Keep coordinates in sync with tools/zoo_layout.py.</summary>
public static class ZooHabitats
{
    public const string Ice = "Ice";
    public const string Water = "Water";
    public const string Savanna = "Savanna";
    public const string Jungle = "Jungle";
    public const string Forest = "Forest";
    public const string Prehistoric = "Prehistoric";

    public static readonly HabitatRect IcePen = new(Ice, 3, 3, 9, 6);
    public static readonly HabitatRect WaterPen = new(Water, 26, 3, 9, 6);
    public static readonly HabitatRect SavannaPen = new(Savanna, 3, 13, 9, 6);
    public static readonly HabitatRect JunglePen = new(Jungle, 26, 13, 9, 6);
    public static readonly HabitatRect ForestPen = new(Forest, 3, 23, 9, 3);
    public static readonly HabitatRect PrehistoricPen = new(Prehistoric, 26, 23, 9, 3);

    public static readonly IReadOnlyList<HabitatRect> All = new[]
    {
        IcePen, WaterPen, SavannaPen, JunglePen, ForestPen, PrehistoricPen
    };

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

    /// <summary>Walkable tiles visitors use while touring the loop.</summary>
    public static readonly IReadOnlyList<(int X, int Y)> VisitorLoop = new (int X, int Y)[]
    {
        (18, 28), (1, 28), (1, 21), (1, 11), (1, 1),
        (7, 1), (18, 1), (30, 1), (36, 1),
        (36, 11), (30, 11), (18, 11), (7, 11),
        (7, 21), (18, 21), (30, 21), (36, 21), (36, 28),
        (18, 28)
    };

    public static HabitatRect? ForAnimal(string? animalType)
    {
        if (animalType == null || !AnimalHabitat.TryGetValue(animalType, out string? id))
            return null;
        return All.First(h => h.Id == id);
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
