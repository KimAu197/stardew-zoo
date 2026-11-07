using Microsoft.Xna.Framework;
using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewValley;

namespace StardewZoo;

/// <summary>
/// Walk-in pavilions. Each pavilion interior is a separate region of the same zoo AnimalHouse map (so animals,
/// feeding and saving stay vanilla); stepping on a door tile fades the screen and moves the player between regions,
/// and the camera is clamped to the region the player is in so the halls feel like separate buildings.
/// </summary>
internal sealed class PavilionManager
{
    public const string TouchAction = "StardewZoo_Pavilion";

    private readonly IMonitor monitor;
    private bool transitioning;

    public PavilionManager(IModHelper helper, IMonitor monitor)
    {
        this.monitor = monitor;
        helper.Events.GameLoop.GameLaunched += (_, _) => GameLocation.RegisterTouchAction(TouchAction, this.OnDoorTouched);
        helper.Events.GameLoop.UpdateTicked += this.OnUpdateTicked;
        helper.Events.Player.Warped += this.OnWarped;
        helper.Events.GameLoop.DayStarted += (_, _) => this.transitioning = false;
        helper.Events.GameLoop.ReturnedToTitle += (_, _) => this.transitioning = false;
    }

    /// <summary>Whether the location is a zoo interior using the current multi-region map.</summary>
    public static bool HasRegions(GameLocation? location) =>
        location is AnimalHouse && ZooIds.IsZoo(location.ParentBuilding?.buildingType.Value)
        && location.Map?.Layers[0].LayerWidth == ZooLayout.MapWidth;

    private void OnDoorTouched(GameLocation location, string[] args, Farmer who, Vector2 tile)
    {
        if (this.transitioning || !who.IsLocalPlayer || !HasRegions(location))
            return;
        if (!ArgUtility.TryGet(args, 1, out string id, out string error, allowBlank: false, "string pavilionId")
            || !ArgUtility.TryGet(args, 2, out string direction, out error, allowBlank: false, "string direction"))
        {
            this.monitor.LogOnce($"Bad {TouchAction} touch action at {tile}: {error}", LogLevel.Warn);
            return;
        }
        if (ZooHabitats.Pavilion(id) is not PavilionInfo pavilion)
        {
            this.monitor.LogOnce($"Unknown zoo pavilion '{id}' at {tile}.", LogLevel.Warn);
            return;
        }

        bool inward = direction.Equals("In", StringComparison.OrdinalIgnoreCase);
        (int x, int y) = inward ? pavilion.InsideArrival : pavilion.OutsideArrival;
        int facing = inward ? Game1.up : Game1.down;

        this.transitioning = true;
        who.Halt();
        location.playSound("doorClose");
        Game1.globalFadeToBlack(() =>
        {
            if (ReferenceEquals(Game1.currentLocation, location))
                Place(who, x, y, facing);
            Game1.globalFadeToClear(() => this.transitioning = false, 0.04f);
        }, 0.04f);
    }

    private static void Place(Farmer who, int tileX, int tileY, int facing)
    {
        who.Halt();
        who.Position = new Vector2(tileX * Game1.tileSize, tileY * Game1.tileSize);
        who.faceDirection(facing);
        who.TemporaryPassableTiles.Clear();
        Game1.forceSnapOnNextViewportUpdate = true;
        Game1.UpdateViewPort(overrideFreeze: true, who.StandingPixel);
        ClampViewport(who);
    }

    private void OnUpdateTicked(object? sender, UpdateTickedEventArgs e)
    {
        if (!Context.IsWorldReady || Game1.eventUp || Game1.viewportFreeze || !HasRegions(Game1.currentLocation))
            return;
        ClampViewport(Game1.player);
    }

    /// <summary>
    /// Keep the camera inside the player's region. The vanilla camera clamps only to the map, which here spans every
    /// region; the gaps between regions are void, so this is cosmetic (no other hall is ever visible either way).
    /// </summary>
    private static void ClampViewport(Farmer who)
    {
        Point tile = who.TilePoint;
        if (ZooHabitats.RegionAt(tile.X, tile.Y) is not ZooRect region)
            return;

        int x = ZooHabitats.ClampViewportAxis(Game1.viewport.X, Game1.viewport.Width, region.X * Game1.tileSize, region.Width * Game1.tileSize);
        int y = ZooHabitats.ClampViewportAxis(Game1.viewport.Y, Game1.viewport.Height, region.Y * Game1.tileSize, region.Height * Game1.tileSize);
        if (x == Game1.viewport.X && y == Game1.viewport.Y)
            return;
        Game1.viewport.X = x;
        Game1.viewport.Y = y;
        Game1.viewportPositionLerp = new Vector2(x, y);
    }

    /// <summary>Entering the zoo: never leave the player inside a wall or the void (e.g. after the map layout changed).</summary>
    private void OnWarped(object? sender, WarpedEventArgs e)
    {
        this.transitioning = false;
        if (!e.IsLocalPlayer || !HasRegions(e.NewLocation))
            return;

        Point tile = e.Player.TilePoint;
        if (ZooHabitats.RegionAt(tile.X, tile.Y) != null && e.NewLocation.isTilePassable(new Vector2(tile.X, tile.Y)))
            return;
        (int x, int y) = ZooLayout.Entrance;
        this.monitor.Log($"Moved {e.Player.Name} from blocked zoo tile {tile} to the entrance.", LogLevel.Trace);
        Place(e.Player, x, y, Game1.up);
    }
}
