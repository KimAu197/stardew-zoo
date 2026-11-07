using Microsoft.Xna.Framework;
using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewValley;

namespace StardewZoo;

/// <summary>Makes zoo animals call out when the local player walks near them.</summary>
internal sealed class AnimalCallHandler
{
    private const double GlobalGapSeconds = 0.75;
    private const string AnimalTypePrefix = "StardewZoo.";

    private readonly ModConfig config;
    private readonly ProximityCalls calls;
    private GameLocation? lastLocation;

    public AnimalCallHandler(IModHelper helper, ModConfig config)
    {
        this.config = config;
        this.calls = new ProximityCalls(config.AnimalCallRadius, config.AnimalCallCooldownSeconds, GlobalGapSeconds);
        helper.Events.GameLoop.UpdateTicked += this.OnUpdateTicked;
    }

    private void OnUpdateTicked(object? sender, UpdateTickedEventArgs e)
    {
        if (!e.IsMultipleOf(10) || !this.config.AnimalCallsOnApproach)
            return;
        if (!Context.IsWorldReady)
        {
            this.lastLocation = null;
            this.calls.Reset();
            return;
        }

        GameLocation location = Game1.currentLocation;
        if (!ReferenceEquals(location, this.lastLocation))
        {
            this.calls.Reset();
            this.lastLocation = location;
        }

        if (!Context.IsPlayerFree || Game1.eventUp || location is not AnimalHouse house || !ZooIds.IsZoo(house.ParentBuilding?.buildingType.Value))
            return;

        var animals = new List<AnimalPosition>();
        var byId = new Dictionary<long, FarmAnimal>();
        foreach (FarmAnimal animal in house.animals.Values)
        {
            if (animal.type.Value?.StartsWith(AnimalTypePrefix, StringComparison.Ordinal) != true)
                continue;
            Point center = animal.GetBoundingBox().Center;
            animals.Add(new AnimalPosition(animal.myID.Value, center.X, center.Y));
            byId[animal.myID.Value] = animal;
        }

        Vector2 player = Game1.player.getStandingPosition();
        foreach (long id in this.calls.Update(player.X, player.Y, animals, e.Ticks / 60.0))
        {
            FarmAnimal animal = byId[id];
            animal.makeSound();
            if (!animal.isEmoting)
                animal.doEmote(Character.musicNoteEmote, false);
        }
    }
}
