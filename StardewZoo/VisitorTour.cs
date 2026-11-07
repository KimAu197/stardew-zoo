using Microsoft.Xna.Framework;
using StardewValley;

namespace StardewZoo;

/// <summary>
/// The visitor tour through the park and the walk-in pavilions (<see cref="ZooLayout.VisitorRoute"/>). Walk steps stay
/// inside one map region; at a pavilion door the visitor steps through, i.e. reappears at the other side's arrival tile.
/// Every step target is a validated walkable tile (tools/validate_map.py), so a visitor can't end up in the void.
/// </summary>
internal static class VisitorTour
{
    public static int Count => ZooLayout.VisitorRoute.Count;

    public static Vector2 StartPosition => new(ZooLayout.Entrance.X * Game1.tileSize, ZooLayout.Entrance.Y * Game1.tileSize);

    public static (int X, int Y) Target(int step) => (ZooLayout.VisitorRoute[step].X, ZooLayout.VisitorRoute[step].Y);

    /// <summary>Carry out any door steps at <paramref name="step"/>; returns the next walk step (or <see cref="Count"/>).</summary>
    public static int ThroughDoors(NPC npc, GameLocation location, int step)
    {
        while (step < Count && ZooLayout.VisitorRoute[step].Teleport)
        {
            VisitorStep door = ZooLayout.VisitorRoute[step];
            npc.Halt();
            npc.controller = null;
            PlayDoorSound(location, npc.Tile);
            npc.Position = new Vector2(door.X * Game1.tileSize, door.Y * Game1.tileSize);
            PlayDoorSound(location, npc.Tile);
            step++;
        }
        return step;
    }

    private static void PlayDoorSound(GameLocation location, Vector2 tile)
    {
        if (!ReferenceEquals(Game1.currentLocation, location))
            return;
        Point player = Game1.player.TilePoint;
        bool sameRegion = ZooHabitats.RegionAt(player.X, player.Y) == ZooHabitats.RegionAt((int)tile.X, (int)tile.Y);
        if (sameRegion && Vector2.Distance(tile, Game1.player.Tile) <= 8)
            location.localSound("doorClose", tile);
    }
}
