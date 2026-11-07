using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input;
using StardewModdingAPI;
using StardewValley;
using StardewValley.Menus;

namespace StardewZoo;

internal sealed class RecordingMenu : IClickableMenu
{
    private const int MenuWidth = 800;
    private const int MenuHeight = 580;
    private const int RowHeight = 32;
    private const int ColumnWidth = 190;
    private const int PanelX = 440;
    private const int PanelWidth = MenuWidth - PanelX - 48;
    private const int ButtonCount = 4;

    private readonly RecordingManager recording;
    private readonly IModHelper helper;
    private readonly Action persist;
    private int selected;

    public RecordingMenu(RecordingManager recording, IModHelper helper, ZooSaveData save, Action persist)
        : base(0, 0, MenuWidth, MenuHeight, showUpperRightCloseButton: true)
    {
        this.recording = recording;
        this.helper = helper;
        this.persist = persist;
        Vector2 pos = Utility.getTopLeftPositionForCenteringOnScreen(this.width, this.height);
        this.xPositionOnScreen = (int)pos.X;
        this.yPositionOnScreen = (int)pos.Y;
        this.initializeUpperRightCloseButton();
        recording.PollChanges();
    }

    public override void receiveLeftClick(int x, int y, bool playSound = true)
    {
        base.receiveLeftClick(x, y, playSound);
        for (int i = 0; i < ZooIds.AnimalTypes.Count; i++)
        {
            if (this.AnimalHit(i).Contains(x, y))
            {
                this.selected = i;
                Game1.playSound("smallSelect");
                return;
            }
        }

        string animal = ZooIds.ShortName(ZooIds.AnimalTypes[this.selected]);
        if (this.Button(0).Contains(x, y))
        {
            this.recording.Record(animal);
        }
        else if (this.Button(1).Contains(x, y))
        {
            this.recording.Preview(animal);
        }
        else if (this.Button(2).Contains(x, y))
        {
            if (this.recording.TryReset(animal))
                this.persist();
        }
        else if (this.Button(3).Contains(x, y))
        {
            Game1.playSound("smallSelect");
            this.recording.OpenSoundsFolder();
        }
    }

    public override void receiveKeyPress(Keys key)
    {
        if (key is Keys.Escape or Keys.E)
            this.exitThisMenu();
        else
            base.receiveKeyPress(key);
    }

    public override void gameWindowSizeChanged(Rectangle oldBounds, Rectangle newBounds)
    {
        base.gameWindowSizeChanged(oldBounds, newBounds);
        Vector2 pos = Utility.getTopLeftPositionForCenteringOnScreen(this.width, this.height);
        this.xPositionOnScreen = (int)pos.X;
        this.yPositionOnScreen = (int)pos.Y;
        this.initializeUpperRightCloseButton();
    }

    public override void draw(SpriteBatch b)
    {
        b.Draw(Game1.fadeToBlackRect, Game1.graphics.GraphicsDevice.Viewport.Bounds, Color.Black * 0.4f);
        Game1.drawDialogueBox(this.xPositionOnScreen, this.yPositionOnScreen, this.width, this.height, speaker: false, drawOnlyBox: true);
        Utility.drawTextWithShadow(b, this.helper.Translation.Get("record.title"), Game1.dialogueFont, new Vector2(this.xPositionOnScreen + 40, this.yPositionOnScreen + 40), Game1.textColor);

        for (int i = 0; i < ZooIds.AnimalTypes.Count; i++)
        {
            string name = ZooIds.ShortName(ZooIds.AnimalTypes[i]);
            string label = this.recording.DisplayName(name);
            if (this.recording.IsCustom(name))
                label += " *";
            Color color = name == this.recording.BusyAnimal ? Color.Red
                : i == this.selected ? Color.ForestGreen
                : Game1.textColor;
            Rectangle hit = this.AnimalHit(i);
            label = Fit(label, hit.Width);
            Utility.drawTextWithShadow(b, label, Game1.smallFont, new Vector2(hit.X, hit.Y + 2), color);
        }

        string status = string.IsNullOrEmpty(this.recording.Status) ? this.helper.Translation.Get("record.hint") : this.recording.Status;
        string wrapped = Game1.parseText(status, Game1.smallFont, PanelWidth);
        Utility.drawTextWithShadow(b, wrapped, Game1.smallFont, new Vector2(this.xPositionOnScreen + PanelX, this.yPositionOnScreen + 112), Game1.textColor);

        string recordLabel = this.recording.Busy ? this.helper.Translation.Get("record.button.recording") : this.helper.Translation.Get("record.button.record");
        this.DrawButton(b, 0, recordLabel);
        this.DrawButton(b, 1, this.helper.Translation.Get("record.button.preview"));
        this.DrawButton(b, 2, this.helper.Translation.Get("record.button.reset"));
        this.DrawButton(b, 3, this.helper.Translation.Get("record.button.folder"));
        base.draw(b);
        this.drawMouse(b);
    }

    private int ListRows => (ZooIds.AnimalTypes.Count + 1) / 2;

    private Rectangle AnimalHit(int index)
    {
        int col = index / this.ListRows;
        int row = index % this.ListRows;
        return new Rectangle(this.xPositionOnScreen + 40 + col * ColumnWidth, this.yPositionOnScreen + 112 + row * RowHeight, ColumnWidth - 10, RowHeight);
    }

    private Rectangle Button(int index)
    {
        int top = this.yPositionOnScreen + this.height - 48 - ButtonCount * 52;
        return new Rectangle(this.xPositionOnScreen + PanelX, top + index * 52, PanelWidth, 44);
    }

    private void DrawButton(SpriteBatch b, int index, string label)
    {
        Rectangle rect = this.Button(index);
        bool hover = rect.Contains(Game1.getMouseX(), Game1.getMouseY());
        IClickableMenu.drawTextureBox(b, rect.X, rect.Y, rect.Width, rect.Height, hover ? Color.Wheat : Color.White);
        label = Fit(label, rect.Width - 16);
        Vector2 size = Game1.smallFont.MeasureString(label);
        b.DrawString(Game1.smallFont, label, new Vector2(rect.X + (rect.Width - size.X) / 2, rect.Y + (rect.Height - size.Y) / 2 + 2), Game1.textColor);
    }

    private static string Fit(string text, int width)
    {
        if (Game1.smallFont.MeasureString(text).X <= width)
            return text;
        while (text.Length > 1 && Game1.smallFont.MeasureString(text + "...").X > width)
            text = text[..^1];
        return text + "...";
    }
}
