using Microsoft.Xna.Framework;
using StardewModdingAPI;
using StardewValley;
using StardewValley.Pathfinding;

namespace StardewZoo;

/// <summary>Temporary visitor NPCs that tour the zoo loop and despawn at night / before save.</summary>
internal sealed class VisitorManager
{
    private const string NamePrefix = "StardewZooVisitor_";
    private int nextId;
    private int projectedVisitors;
    private readonly IMonitor monitor;

    public VisitorManager(IMonitor monitor)
    {
        this.monitor = monitor;
    }

    public void SetProjection(int visitors) => this.projectedVisitors = visitors;

    public void TrySpawn()
    {
        if (!Context.IsMainPlayer || !Context.IsWorldReady)
            return;
        int hour = Game1.timeOfDay;
        if (hour < 800 || hour >= 1800 || this.projectedVisitors <= 0)
            return;

        Utility.ForEachBuilding(building =>
        {
            if (!ZooIds.IsZoo(building.buildingType.Value) || building.isUnderConstruction())
                return true;
            if (building.GetIndoors() is not AnimalHouse house)
                return true;

            int cap = Math.Clamp(this.projectedVisitors / 8, 1, 6);
            int current = house.characters.Count(IsVisitor);
            if (current >= cap)
                return true;

            this.SpawnOne(house);
            return true;
        });
    }

    public void RemoveAll()
    {
        Utility.ForEachLocation(location =>
        {
            for (int i = location.characters.Count - 1; i >= 0; i--)
            {
                if (IsVisitor(location.characters[i]))
                    location.characters.RemoveAt(i);
            }
            return true;
        });
    }

    private void SpawnOne(GameLocation location)
    {
        int variant = this.nextId % 4;
        string asset = $"Characters/StardewZooVisitor{variant}";
        var sprite = new AnimatedSprite(asset, 0, 16, 32);
        var npc = new NPC(sprite, new Vector2(18 * Game1.tileSize, 28 * Game1.tileSize), 0, NamePrefix + this.nextId)
        {
            Breather = false,
            HideShadow = false,
            displayName = "Visitor",
            farmerPassesThrough = true,
            Speed = 2
        };
        npc.collidesWithOtherCharacters.Value = false;
        npc.forceOneTileWide.Value = true;
        this.nextId++;
        location.characters.Add(npc);
        this.WalkLoop(npc, location, 0);
    }

    private void WalkLoop(NPC npc, GameLocation location, int waypoint)
    {
        if (waypoint >= ZooHabitats.VisitorLoop.Count)
        {
            location.characters.Remove(npc);
            return;
        }

        (int x, int y) = ZooHabitats.VisitorLoop[waypoint];
        npc.controller = new PathFindController(
            npc,
            location,
            new Point(x, y),
            0,
            (character, loc) =>
            {
                if (character is NPC visitor && loc != null)
                    this.WalkLoop(visitor, loc, waypoint + 1);
            }
        );
        if (npc.controller?.pathToEndPoint == null || npc.controller.pathToEndPoint.Count == 0)
        {
            npc.Position = new Vector2(x * Game1.tileSize, y * Game1.tileSize);
            this.WalkLoop(npc, location, waypoint + 1);
        }
    }

    private static bool IsVisitor(NPC? npc) => npc?.Name?.StartsWith(NamePrefix, StringComparison.Ordinal) == true;
}
