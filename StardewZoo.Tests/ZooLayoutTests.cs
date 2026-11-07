using StardewZoo;
using Xunit;

public class ZooLayoutTests
{
    private static ZooRect Contains(HabitatRect pen) =>
        ZooHabitats.RegionAt(pen.X, pen.Y) is ZooRect region && region.Contains(pen.X + pen.Width - 1, pen.Y + pen.Height - 1)
            ? region
            : throw new Xunit.Sdk.XunitException($"{pen.Id} pen isn't inside one region");

    [Fact]
    public void IndoorSpecies_LiveInsideTheirPavilion()
    {
        foreach (string id in new[] { ZooHabitats.Ice, ZooHabitats.Water, ZooHabitats.Jungle, ZooHabitats.Prehistoric })
        {
            HabitatRect pen = ZooHabitats.All.Single(h => h.Id == id);
            PavilionInfo pavilion = ZooHabitats.Pavilion(id)!;
            Assert.Equal(pavilion.Region, Contains(pen));
            Assert.True(pavilion.Barrier.Contains(pen.X - 1, pen.Y - 1));
            Assert.False(pen.Contains(pavilion.InsideArrival.X, pavilion.InsideArrival.Y));
        }
        Assert.Equal(ZooLayout.Outdoor, Contains(ZooLayout.SavannaPen));
        Assert.Equal(ZooLayout.Outdoor, Contains(ZooLayout.ForestPen));
        Assert.Equal(ZooHabitats.Ice, ZooHabitats.ForAnimal(ZooIds.Penguin)!.Value.Id);
        Assert.Equal(ZooLayout.WaterPen, ZooHabitats.ForAnimal(ZooIds.Flamingo));
    }

    [Fact]
    public void Regions_DontOverlap_AndAreFarApart()
    {
        var regions = ZooHabitats.Regions;
        for (int i = 0; i < regions.Count; i++)
        {
            for (int j = i + 1; j < regions.Count; j++)
            {
                ZooRect a = regions[i], b = regions[j];
                int gap = Math.Max(b.X - (a.X + a.Width), a.X - (b.X + b.Width));
                Assert.True(gap >= 30, $"regions {a} and {b} are only {gap} tiles apart");
            }
        }
        Assert.All(regions, r => Assert.True(r.X + r.Width <= ZooLayout.MapWidth && r.Y + r.Height <= ZooLayout.MapHeight));
    }

    [Fact]
    public void Doors_SitOnTheEdgeOfTheirRegions()
    {
        foreach (PavilionInfo p in ZooLayout.Pavilions)
        {
            Assert.Equal(ZooLayout.Outdoor, ZooHabitats.RegionAt(p.OutsideDoor.X, p.OutsideDoor.Y));
            Assert.Equal(ZooLayout.Outdoor, ZooHabitats.RegionAt(p.OutsideArrival.X, p.OutsideArrival.Y));
            Assert.Equal(p.Region, ZooHabitats.RegionAt(p.InsideDoor.X, p.InsideDoor.Y));
            Assert.Equal(p.Region.Y + p.Region.Height - 1, p.InsideDoor.Y);
            Assert.Equal((p.InsideDoor.X, p.InsideDoor.Y - 1), p.InsideArrival);
            Assert.Equal((p.Facade.X + p.Facade.Width / 2, p.Facade.Y + p.Facade.Height - 1), p.OutsideDoor);
        }
    }

    [Fact]
    public void VisitorRoute_OnlyChangesRegionThroughDoors_AndVisitsEveryPavilion()
    {
        var route = ZooLayout.VisitorRoute;
        Assert.Equal(ZooLayout.Entrance, (route[0].X, route[0].Y));
        Assert.Equal(ZooLayout.Entrance, (route[^1].X, route[^1].Y));

        ZooRect? current = ZooHabitats.RegionAt(route[0].X, route[0].Y);
        var visited = new HashSet<ZooRect>();
        foreach (VisitorStep step in route)
        {
            ZooRect? next = ZooHabitats.RegionAt(step.X, step.Y);
            Assert.NotNull(next);
            if (!step.Teleport)
                Assert.Equal(current, next);
            current = next;
            visited.Add(next!.Value);
        }
        Assert.Equal(ZooHabitats.Regions.Count, visited.Count);
        Assert.Equal(route.Count, ZooHabitats.VisitorLoop.Count);
    }

    [Theory]
    [InlineData(500, 1920, 0, 2432, 500)]      // inside: unchanged
    [InlineData(-50, 1920, 0, 2432, 0)]        // past the left edge
    [InlineData(900, 1920, 0, 2432, 512)]      // past the right edge
    [InlineData(4000, 1920, 4608, 1408, 4352)] // region narrower than the screen: centred
    public void ViewportAxis_ClampsOrCentresOnTheRegion(int position, int view, int start, int size, int expected)
    {
        Assert.Equal(expected, ZooHabitats.ClampViewportAxis(position, view, start, size));
    }
}
