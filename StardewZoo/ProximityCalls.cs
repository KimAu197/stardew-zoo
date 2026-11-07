namespace StardewZoo;

/// <summary>An animal's id and the pixel position of its bounding-box center.</summary>
public readonly record struct AnimalPosition(long Id, float X, float Y);

/// <summary>Decides which animals call out as the player walks near them.</summary>
/// <remarks>
/// An animal calls when the player enters its radius. It can call again only once the player has left and come back
/// AND its cooldown has passed, so standing next to a pen stays quiet. A global gap keeps a crowded pen from playing
/// several sounds at once; animals held back by it stay queued while the player remains near them.
/// </remarks>
public sealed class ProximityCalls
{
    public const float TileSize = 64f;

    private readonly Dictionary<long, AnimalState> states = new();
    private double? lastCallAt;

    public ProximityCalls(float radiusTiles, double cooldownSeconds, double globalGapSeconds)
    {
        this.RadiusPixels = Math.Max(0f, radiusTiles) * TileSize;
        this.CooldownSeconds = Math.Max(0, cooldownSeconds);
        this.GlobalGapSeconds = Math.Max(0, globalGapSeconds);
    }

    public float RadiusPixels { get; }

    public double CooldownSeconds { get; }

    public double GlobalGapSeconds { get; }

    /// <summary>Returns the animal ids that should call now (at most one per call).</summary>
    /// <param name="playerX">The player's standing pixel X.</param>
    /// <param name="playerY">The player's standing pixel Y.</param>
    /// <param name="animals">The animals in the player's location.</param>
    /// <param name="nowSeconds">A monotonic clock in seconds.</param>
    public IReadOnlyList<long> Update(float playerX, float playerY, IEnumerable<AnimalPosition> animals, double nowSeconds)
    {
        var seen = new HashSet<long>();
        long? best = null;
        float bestDistance = float.MaxValue;
        float radiusSquared = this.RadiusPixels * this.RadiusPixels;

        foreach (AnimalPosition animal in animals)
        {
            if (!seen.Add(animal.Id))
                continue;
            if (!this.states.TryGetValue(animal.Id, out AnimalState? state))
                this.states[animal.Id] = state = new AnimalState();

            float dx = animal.X - playerX;
            float dy = animal.Y - playerY;
            float distanceSquared = dx * dx + dy * dy;
            if (distanceSquared > radiusSquared)
            {
                state.Armed = true;
                continue;
            }

            bool cooledDown = state.LastCallAt is not { } last || nowSeconds - last >= this.CooldownSeconds;
            if (state.Armed && cooledDown && distanceSquared < bestDistance)
            {
                best = animal.Id;
                bestDistance = distanceSquared;
            }
        }

        foreach ((long id, AnimalState state) in this.states)
        {
            if (!seen.Contains(id))
                state.Armed = true;
        }

        if (best is not { } chosen || (this.lastCallAt is { } globalLast && nowSeconds - globalLast < this.GlobalGapSeconds))
            return Array.Empty<long>();

        AnimalState chosenState = this.states[chosen];
        chosenState.Armed = false;
        chosenState.LastCallAt = nowSeconds;
        this.lastCallAt = nowSeconds;
        return new[] { chosen };
    }

    /// <summary>Forget all animals, e.g. when the player changes location.</summary>
    public void Reset()
    {
        this.states.Clear();
        this.lastCallAt = null;
    }

    private sealed class AnimalState
    {
        /// <summary>Whether the player has been outside the radius since this animal last called.</summary>
        public bool Armed = true;

        public double? LastCallAt;
    }
}
