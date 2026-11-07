using StardewZoo;
using Xunit;

public class ProximityCallsTests
{
    private const float Tile = ProximityCalls.TileSize;

    private static ProximityCalls Make(double cooldown = 8, double gap = 0.75) => new(3f, cooldown, gap);

    private static AnimalPosition At(long id, float tilesAway) => new(id, tilesAway * Tile, 0);

    private static IReadOnlyList<long> Tick(ProximityCalls calls, double now, params AnimalPosition[] animals)
    {
        return calls.Update(0, 0, animals, now);
    }

    [Fact]
    public void FarAnimal_DoesNotCall()
    {
        Assert.Empty(Tick(Make(), 0, At(1, 5)));
    }

    [Fact]
    public void EnteringRadius_CallsOnce()
    {
        ProximityCalls calls = Make();

        Assert.Empty(Tick(calls, 0, At(1, 5)));
        Assert.Equal(new long[] { 1 }, Tick(calls, 1, At(1, 2)));
        Assert.Empty(Tick(calls, 2, At(1, 2)));
        Assert.Empty(Tick(calls, 20, At(1, 1)));
    }

    [Fact]
    public void AnimalAlreadyNearOnArrival_Calls()
    {
        Assert.Equal(new long[] { 1 }, Tick(Make(), 0, At(1, 1)));
    }

    [Fact]
    public void RadiusBoundary_IsInclusive()
    {
        Assert.Equal(new long[] { 1 }, Tick(Make(), 0, At(1, 3)));
        Assert.Empty(Tick(Make(), 0, At(1, 3.01f)));
    }

    [Fact]
    public void Diagonal_UsesEuclideanDistance()
    {
        // (2.5, 2.5) tiles is ~3.54 tiles away: outside a 3-tile radius even though each axis is within it.
        Assert.Empty(Make().Update(0, 0, new[] { new AnimalPosition(1, 2.5f * Tile, 2.5f * Tile) }, 0));
    }

    [Fact]
    public void LeaveAndReenter_BeforeCooldown_WaitsForCooldown()
    {
        ProximityCalls calls = Make(cooldown: 8);

        Assert.Equal(new long[] { 1 }, Tick(calls, 0, At(1, 1)));
        Assert.Empty(Tick(calls, 2, At(1, 6)));
        Assert.Empty(Tick(calls, 4, At(1, 1)));
        Assert.Equal(new long[] { 1 }, Tick(calls, 8, At(1, 1)));
    }

    [Fact]
    public void LeaveAndReenter_AfterCooldown_CallsAgain()
    {
        ProximityCalls calls = Make(cooldown: 8);

        Assert.Equal(new long[] { 1 }, Tick(calls, 0, At(1, 1)));
        Assert.Empty(Tick(calls, 9, At(1, 6)));
        Assert.Equal(new long[] { 1 }, Tick(calls, 10, At(1, 1)));
    }

    [Fact]
    public void StayingNearby_PastCooldown_DoesNotRecall()
    {
        ProximityCalls calls = Make(cooldown: 8);

        Assert.Equal(new long[] { 1 }, Tick(calls, 0, At(1, 1)));
        for (double t = 1; t < 60; t += 1)
            Assert.Empty(Tick(calls, t, At(1, 1)));
    }

    [Fact]
    public void CrowdedPen_CallsOneAtATime_ClosestFirst()
    {
        ProximityCalls calls = Make(gap: 0.75);
        AnimalPosition[] pen = { At(1, 2), At(2, 1), At(3, 2.5f) };

        Assert.Equal(new long[] { 2 }, Tick(calls, 0, pen));
        Assert.Empty(Tick(calls, 0.5, pen));
        Assert.Equal(new long[] { 1 }, Tick(calls, 0.75, pen));
        Assert.Equal(new long[] { 3 }, Tick(calls, 1.5, pen));
        Assert.Empty(Tick(calls, 2.25, pen));
    }

    [Fact]
    public void GlobalGap_AppliesAcrossDifferentAnimals()
    {
        ProximityCalls calls = Make(gap: 0.75);

        Assert.Equal(new long[] { 1 }, Tick(calls, 0, At(1, 1), At(2, 9)));
        Assert.Empty(Tick(calls, 0.3, At(1, 1), At(2, 1)));
        Assert.Equal(new long[] { 2 }, Tick(calls, 0.8, At(1, 1), At(2, 1)));
    }

    [Fact]
    public void QueuedAnimal_DroppedIfPlayerLeavesBeforeItsTurn()
    {
        ProximityCalls calls = Make(gap: 0.75);

        Assert.Equal(new long[] { 1 }, Tick(calls, 0, At(1, 1), At(2, 2)));
        Assert.Empty(Tick(calls, 0.5, At(1, 9), At(2, 9)));
        Assert.Empty(Tick(calls, 1, At(1, 9), At(2, 9)));
    }

    [Fact]
    public void Reset_ClearsCooldownsAndGlobalGap()
    {
        ProximityCalls calls = Make(cooldown: 8, gap: 0.75);

        Assert.Equal(new long[] { 1 }, Tick(calls, 0, At(1, 1)));
        calls.Reset();
        Assert.Equal(new long[] { 1 }, Tick(calls, 0.1, At(1, 1)));
    }

    [Fact]
    public void AnimalMissingFromLocation_IsTreatedAsLeft()
    {
        ProximityCalls calls = Make(cooldown: 8);

        Assert.Equal(new long[] { 1 }, Tick(calls, 0, At(1, 1)));
        Assert.Empty(Tick(calls, 5, At(2, 9)));
        Assert.Equal(new long[] { 1 }, Tick(calls, 10, At(1, 1)));
    }

    [Fact]
    public void ZeroRadius_NeverCallsUnlessExactlyOnTop()
    {
        var calls = new ProximityCalls(0f, 8, 0.75);

        Assert.Empty(calls.Update(0, 0, new[] { At(1, 0.5f) }, 0));
    }
}
