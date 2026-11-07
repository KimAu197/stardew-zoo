namespace StardewZoo;

/// <summary>Placed furniture makes a zoo a little more appealing.</summary>
public static class ZooDecor
{
    /// <summary>Visitor-demand multiplier: +<paramref name="perItem"/> per piece of furniture, capped at +<paramref name="maxBonus"/>.</summary>
    public static double DemandMultiplier(int decorCount, double perItem, double maxBonus)
    {
        if (decorCount <= 0 || perItem <= 0 || maxBonus <= 0)
            return 1.0;
        return 1.0 + Math.Min(decorCount * perItem, maxBonus);
    }
}
