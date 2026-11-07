using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input;
using StardewModdingAPI;
using StardewValley;
using StardewValley.Menus;

namespace StardewZoo;

internal sealed class RecordingMenu : IClickableMenu
{
    private readonly RecordingManager recording;
    private readonly IModHelper helper;
    private readonly ZooSaveData save;
    private readonly Action persist;
    private int selected;
    private string status = "";

    public RecordingMenu(RecordingManager recording, IModHelper helper, ZooSaveData save, Action persist)
        : base(0, 0, 720, 520, showUpperRightCloseButton: true)
    {
        this.recording = recording;
        this.helper = helper;
        this.save = save;
        this.persist = persist;
        Vector2 pos = Utility.getTopLeftPositionForCenteringOnScreen(this.width, this.height);
        this.xPositionOnScreen = (int)pos.X;
        this.yPositionOnScreen = (int)pos.Y;
        this.status = helper.Translation.Get("record.hint");
    }

    public override void receiveLeftClick(int x, int y, bool playSound = true)
    {
        base.receiveLeftClick(x, y, playSound);
        int listX = this.xPositionOnScreen + 32;
        int listY = this.yPositionOnScreen + 88;
        for (int i = 0; i < ZooIds.AnimalTypes.Count; i++)
        {
            var row = new Rectangle(listX, listY + i * 24, 240, 24);
            if (row.Contains(x, y))
            {
                this.selected = i;
                Game1.playSound("smallSelect");
                return;
            }
        }

        string animal = ZooIds.ShortName(ZooIds.AnimalTypes[this.selected]);
        if (this.Button(0).Contains(x, y))
        {
            string via = this.recording.Record(animal, this.save);
            this.persist();
            this.status = via switch
            {
                "folder" => this.helper.Translation.Get("record.drop-wav"),
                "mic" => this.helper.Translation.Get("record.listening"),
                _ => this.helper.Translation.Get("record.saved", new { animal })
            };
            return;
        }
        if (this.Button(1).Contains(x, y))
        {
            this.recording.TryPreview(animal);
            this.status = this.helper.Translation.Get("record.preview", new { animal });
            return;
        }
        if (this.Button(2).Contains(x, y))
        {
            this.recording.TryReset(animal, this.save);
            this.persist();
            this.status = this.helper.Translation.Get("record.reset", new { animal });
        }
    }

    public override void receiveKeyPress(Keys key)
    {
        if (key is Keys.Escape or Keys.E)
            this.exitThisMenu();
        else
            base.receiveKeyPress(key);
    }

    public override void draw(SpriteBatch b)
    {
        b.Draw(Game1.fadeToBlackRect, Game1.graphics.GraphicsDevice.Viewport.Bounds, Color.Black * 0.4f);
        Game1.drawDialogueBox(this.xPositionOnScreen, this.yPositionOnScreen, this.width, this.height, speaker: false, drawOnlyBox: true);
        Utility.drawTextWithShadow(b, this.helper.Translation.Get("record.title"), Game1.dialogueFont, new Vector2(this.xPositionOnScreen + 32, this.yPositionOnScreen + 32), Game1.textColor);

        int listX = this.xPositionOnScreen + 32;
        int listY = this.yPositionOnScreen + 88;
        for (int i = 0; i < ZooIds.AnimalTypes.Count; i++)
        {
            string name = ZooIds.ShortName(ZooIds.AnimalTypes[i]);
            bool custom = this.save.CustomRecordings.Contains(ZooIds.AnimalTypes[i]);
            string label = custom ? name + " *" : name;
            Color color = i == this.selected ? Color.ForestGreen : Game1.textColor;
            Utility.drawTextWithShadow(b, label, Game1.smallFont, new Vector2(listX, listY + i * 24), color);
        }

        this.DrawButton(b, 0, this.helper.Translation.Get("record.button.record"));
        this.DrawButton(b, 1, this.helper.Translation.Get("record.button.preview"));
        this.DrawButton(b, 2, this.helper.Translation.Get("record.button.reset"));
        Utility.drawTextWithShadow(b, this.status, Game1.smallFont, new Vector2(this.xPositionOnScreen + 300, this.yPositionOnScreen + 88), Game1.textColor);
        this.drawMouse(b);
    }

    private Rectangle Button(int index) =>
        new(this.xPositionOnScreen + 300, this.yPositionOnScreen + 320 + index * 44, 220, 40);

    private void DrawButton(SpriteBatch b, int index, string label)
    {
        Rectangle rect = this.Button(index);
        IClickableMenu.drawTextureBox(b, rect.X, rect.Y, rect.Width, rect.Height, Color.White);
        Vector2 size = Game1.smallFont.MeasureString(label);
        b.DrawString(Game1.smallFont, label, new Vector2(rect.X + (rect.Width - size.X) / 2, rect.Y + 8), Game1.textColor);
    }
}
