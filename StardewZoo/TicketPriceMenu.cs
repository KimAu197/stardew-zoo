using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using StardewValley;
using StardewValley.Menus;

namespace StardewZoo;

/// <summary>The ticket booth number picker, plus a live forecast of visitors and income for the price being chosen.</summary>
internal sealed class TicketPriceMenu : NumberSelectionMenu
{
    private readonly Func<int, string> forecast;
    private int forecastPrice = -1;
    private string forecastText = "";

    public TicketPriceMenu(string message, behaviorOnNumberSelect onSelect, int minValue, int maxValue, int defaultNumber, Func<int, string> forecast)
        : base(message, onSelect, -1, minValue, maxValue, defaultNumber)
    {
        this.forecast = forecast;
    }

    public override void draw(SpriteBatch b)
    {
        base.draw(b);
        if (this.currentValue != this.forecastPrice)
        {
            this.forecastPrice = this.currentValue;
            this.forecastText = this.forecast(Math.Clamp(this.currentValue, this.minValue, this.maxValue));
        }

        var position = new Vector2(this.rightButton.bounds.Right + 24, this.rightButton.bounds.Y + 8);
        Utility.drawTextWithShadow(b, this.forecastText, Game1.smallFont, position, Game1.textColor);
        this.drawMouse(b);
    }
}
