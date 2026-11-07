using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input;
using StardewModdingAPI;
using StardewValley;
using StardewValley.BellsAndWhistles;
using StardewValley.Menus;

namespace StardewZoo;

/// <summary>Reads a plaque on a cream board, and edits its title and body with vanilla text boxes (IME input included).</summary>
internal sealed class PlaqueMenu : IClickableMenu
{
    private const int MaxWidth = 860;
    private const int MaxHeight = 660;
    private const int ButtonHeight = 64;
    private const int BoardPadding = 28;

    private const int IdEdit = 1, IdClose = 2, IdTitle = 10, IdBody = 11, IdSave = 20, IdCancel = 21, IdReset = 22;

    private static readonly Rectangle BoardSource = new(384, 396, 15, 15);
    private static readonly Rectangle ButtonSource = new(432, 439, 9, 9);

    private readonly string header;
    private readonly PlaqueText defaults;
    private readonly bool hasDefault;
    private readonly ITranslationHelper i18n;
    private readonly Action<PlaqueText> onSave;
    private readonly Func<char, bool> canDraw;

    private PlaqueText shown;
    private bool editing;
    private int backPressedTick = -1;
    private string? hovered;

    private Rectangle board;
    private readonly ClickableComponent editButton = new(Rectangle.Empty, "edit") { myID = IdEdit, rightNeighborID = IdClose };
    private readonly ClickableComponent closeButton = new(Rectangle.Empty, "close") { myID = IdClose, leftNeighborID = IdEdit };
    private readonly ClickableComponent titleField = new(Rectangle.Empty, "title") { myID = IdTitle, downNeighborID = IdBody };
    private readonly ClickableComponent bodyField = new(Rectangle.Empty, "body") { myID = IdBody, upNeighborID = IdTitle, downNeighborID = IdSave };
    private readonly ClickableComponent saveButton = new(Rectangle.Empty, "save") { myID = IdSave, upNeighborID = IdBody, rightNeighborID = IdCancel };
    private readonly ClickableComponent cancelButton = new(Rectangle.Empty, "cancel") { myID = IdCancel, upNeighborID = IdBody, leftNeighborID = IdSave, rightNeighborID = IdReset };
    private readonly ClickableComponent resetButton = new(Rectangle.Empty, "reset") { myID = IdReset, upNeighborID = IdBody, leftNeighborID = IdCancel };

    private readonly PlaqueTextBox titleBox;
    private readonly PlaqueTextBox bodyBox;

    public PlaqueMenu(string header, PlaqueText text, PlaqueText defaults, bool hasDefault, ITranslationHelper i18n, Action<PlaqueText> onSave)
    {
        this.header = header;
        this.shown = text;
        this.defaults = defaults;
        this.hasDefault = hasDefault;
        this.i18n = i18n;
        this.onSave = onSave;

        Func<char, bool> small = PlaqueInteraction.CanDraw(Game1.smallFont);
        Func<char, bool> dialogue = PlaqueInteraction.CanDraw(Game1.dialogueFont);
        this.canDraw = c => small(c) && dialogue(c);

        this.titleBox = new PlaqueTextBox(Game1.content.Load<Texture2D>("LooseSprites\\textBox"), Game1.smallFont, multiline: false, ZooPlaques.TitleLimit, this.canDraw);
        this.bodyBox = new PlaqueTextBox(null, Game1.smallFont, multiline: true, ZooPlaques.BodyLimit, this.canDraw);
        this.titleBox.OnEnterPressed += _ => this.Select(this.bodyBox);
        this.titleBox.OnTabPressed += _ => this.Select(this.bodyBox);
        this.bodyBox.OnTabPressed += _ => this.Select(this.titleBox);
        this.bodyBox.Fits = candidate => ZooPlaques.Wrap(candidate, this.bodyBox.InnerWidth, Measure).Count <= this.bodyBox.VisibleLines;

        this.Layout();
        Game1.playSound("bigSelect");
    }

    private static float Measure(string s) => Game1.smallFont.MeasureString(s).X;

    private string T(string key, object? tokens = null) => this.i18n.Get(key, tokens);

    private void Layout()
    {
        int w = Math.Min(MaxWidth, Game1.uiViewport.Width - 64);
        int h = Math.Min(MaxHeight, Game1.uiViewport.Height - 128);
        Vector2 pos = Utility.getTopLeftPositionForCenteringOnScreen(w, h, 0, 24);
        this.initialize((int)pos.X, (int)pos.Y, w, h, showUpperRightCloseButton: true);

        int left = this.xPositionOnScreen + 36;
        int inner = this.width - 72;
        int buttonY = this.yPositionOnScreen + this.height - ButtonHeight - 32;
        this.board = new Rectangle(left, this.yPositionOnScreen + 56, inner, buttonY - 20 - (this.yPositionOnScreen + 56));

        this.LayoutButtons(buttonY, this.editButton, this.closeButton);
        this.LayoutButtons(buttonY, this.saveButton, this.cancelButton, this.resetButton);

        int top = this.yPositionOnScreen + 56;
        int labelHeight = (int)Game1.smallFont.MeasureString("A").Y + 4;
        this.titleBox.X = left;
        this.titleBox.Y = top + labelHeight;
        this.titleBox.Width = inner;
        this.titleField.bounds = new Rectangle(left, this.titleBox.Y, inner, this.titleBox.Height);

        int bodyTop = this.titleBox.Y + this.titleBox.Height + 16 + labelHeight;
        int hintHeight = labelHeight + 4;
        this.bodyBox.X = left;
        this.bodyBox.Y = bodyTop;
        this.bodyBox.Width = inner;
        this.bodyBox.Height = buttonY - 16 - hintHeight - bodyTop;
        this.bodyField.bounds = new Rectangle(left, bodyTop, inner, this.bodyBox.Height);

        this.allClickableComponents = this.editing
            ? new List<ClickableComponent> { this.titleField, this.bodyField, this.saveButton, this.cancelButton, this.resetButton }
            : new List<ClickableComponent> { this.editButton, this.closeButton };
        if (Game1.options.SnappyMenus)
            this.snapToDefaultClickableComponent();
    }

    private void LayoutButtons(int y, params ClickableComponent[] buttons)
    {
        int[] widths = buttons.Select(b => Math.Max(150, (int)Game1.smallFont.MeasureString(this.Label(b)).X + 56)).ToArray();
        int total = widths.Sum() + 24 * (buttons.Length - 1);
        int x = this.xPositionOnScreen + (this.width - total) / 2;
        for (int i = 0; i < buttons.Length; i++)
        {
            buttons[i].bounds = new Rectangle(x, y, widths[i], ButtonHeight);
            x += widths[i] + 24;
        }
    }

    private string Label(ClickableComponent button) => button.name switch
    {
        "edit" => this.T("plaque.menu.edit"),
        "close" => this.T("plaque.menu.close"),
        "save" => this.T("plaque.menu.save"),
        "cancel" => this.T("plaque.menu.cancel"),
        _ => this.T(this.hasDefault ? "plaque.menu.reset" : "plaque.menu.clear")
    };

    public override void snapToDefaultClickableComponent()
    {
        this.currentlySnappedComponent = this.getComponentWithID(this.editing ? IdTitle : IdClose);
        this.snapCursorToCurrentSnappedComponent();
    }

    public override void gameWindowSizeChanged(Rectangle oldBounds, Rectangle newBounds)
    {
        base.gameWindowSizeChanged(oldBounds, newBounds);
        this.Layout();
    }

    private void StartEdit()
    {
        this.editing = true;
        this.titleBox.Text = this.shown.Title;
        this.bodyBox.Text = this.shown.Body;
        this.Layout();
        if (!UsingGamepad())
            this.Select(this.titleBox);
        Game1.playSound("smallSelect");
    }

    private void StopEdit()
    {
        this.Deselect();
        this.editing = false;
        this.Layout();
        Game1.playSound("bigDeSelect");
    }

    private void Save()
    {
        this.shown = new PlaqueText(ZooPlaques.CleanTitle(this.titleBox.Text, this.canDraw), ZooPlaques.CleanBody(this.bodyBox.Text, this.canDraw));
        this.onSave(this.shown);
        this.StopEdit();
    }

    private void Select(PlaqueTextBox box)
    {
        box.SelectMe();
        if (UsingGamepad())
            Game1.showTextEntry(box);
    }

    private void Deselect()
    {
        this.titleBox.Selected = false;
        this.bodyBox.Selected = false;
    }

    private bool Typing => this.titleBox.Selected || this.bodyBox.Selected;

    private static bool UsingGamepad() => Game1.options.gamepadControls && !Game1.lastCursorMotionWasMouse;

    public override void receiveLeftClick(int x, int y, bool playSound = true)
    {
        base.receiveLeftClick(x, y, playSound);
        if (!this.editing)
        {
            if (this.editButton.containsPoint(x, y))
                this.StartEdit();
            else if (this.closeButton.containsPoint(x, y))
                this.exitThisMenu();
            return;
        }

        if (this.titleField.containsPoint(x, y))
            this.Select(this.titleBox);
        else if (this.bodyField.containsPoint(x, y))
            this.Select(this.bodyBox);
        else if (this.saveButton.containsPoint(x, y))
            this.Save();
        else if (this.cancelButton.containsPoint(x, y))
            this.StopEdit();
        else if (this.resetButton.containsPoint(x, y))
        {
            this.titleBox.Text = this.defaults.Title;
            this.bodyBox.Text = this.defaults.Body;
            Game1.playSound("trashcan");
        }
    }

    public override void receiveRightClick(int x, int y, bool playSound = true)
    {
    }

    public override void performHoverAction(int x, int y)
    {
        base.performHoverAction(x, y);
        this.hovered = this.allClickableComponents?.FirstOrDefault(c => c.containsPoint(x, y))?.name;
    }

    public override void receiveGamePadButton(Buttons button)
    {
        base.receiveGamePadButton(button);
        if (button == Buttons.B)
            this.backPressedTick = Game1.ticks;
        else if (this.Typing && button is Buttons.DPadUp or Buttons.DPadDown or Buttons.DPadLeft or Buttons.DPadRight
                     or Buttons.LeftThumbstickUp or Buttons.LeftThumbstickDown or Buttons.LeftThumbstickLeft or Buttons.LeftThumbstickRight)
            this.Deselect();
    }

    /// <summary>
    /// While a box has focus every key is typing (and an IME may be composing), so only Escape or the controller's B
    /// back out, one step at a time: unfocus the box, then leave edit mode, then close.
    /// </summary>
    public override void receiveKeyPress(Keys key)
    {
        bool menuKey = Game1.options.doesInputListContain(Game1.options.menuButton, key);
        bool back = key == Keys.Escape || (menuKey && (!this.Typing || this.backPressedTick == Game1.ticks));
        if (back)
        {
            if (this.Typing)
                this.Deselect();
            else if (this.editing)
                this.StopEdit();
            else
                this.exitThisMenu();
            return;
        }
        if (this.Typing || menuKey)
            return;
        base.receiveKeyPress(key);
    }

    protected override void cleanupBeforeExit()
    {
        this.Deselect();
        base.cleanupBeforeExit();
    }

    public override void emergencyShutDown()
    {
        this.Deselect();
        base.emergencyShutDown();
    }

    public override void draw(SpriteBatch b)
    {
        if (!Game1.options.showClearBackgrounds)
            b.Draw(Game1.fadeToBlackRect, Game1.graphics.GraphicsDevice.Viewport.Bounds, Color.Black * 0.6f);

        drawTextureBox(b, this.xPositionOnScreen, this.yPositionOnScreen, this.width, this.height, Color.White);
        SpriteText.drawStringWithScrollCenteredAt(b, this.header, this.xPositionOnScreen + this.width / 2, this.yPositionOnScreen - 40);

        if (this.editing)
            this.DrawEditor(b);
        else
            this.DrawReader(b);

        base.draw(b);
        this.drawMouse(b);
    }

    private void DrawReader(SpriteBatch b)
    {
        drawTextureBox(b, Game1.mouseCursors, BoardSource, this.board.X, this.board.Y, this.board.Width, this.board.Height, Color.White, 4f, false);
        int innerX = this.board.X + BoardPadding;
        int innerWidth = this.board.Width - BoardPadding * 2;
        int y = this.board.Y + BoardPadding;

        if (this.shown.IsEmpty)
        {
            string hint = PlaqueInteraction.FontSafe(Game1.smallFont, this.T("plaque.menu.empty"));
            IReadOnlyList<string> hintLines = ZooPlaques.Wrap(hint, innerWidth, Measure);
            float lineHeight = Game1.smallFont.LineSpacing;
            float top = this.board.Center.Y - hintLines.Count * lineHeight / 2;
            foreach (string line in hintLines)
            {
                float lineWidth = Measure(line);
                b.DrawString(Game1.smallFont, line, new Vector2(this.board.Center.X - lineWidth / 2, top), Game1.textColor * 0.6f);
                top += lineHeight;
            }
            this.DrawButtons(b, this.editButton, this.closeButton);
            return;
        }

        if (this.shown.Title.Length > 0)
        {
            string title = PlaqueInteraction.FontSafe(Game1.dialogueFont, this.shown.Title);
            Vector2 size = Game1.dialogueFont.MeasureString(title);
            float scale = Math.Min(1f, innerWidth / Math.Max(1f, size.X));
            Utility.drawTextWithShadow(b, title, Game1.dialogueFont, new Vector2(this.board.Center.X - size.X * scale / 2, y), Game1.textColor, scale);
            y += (int)(size.Y * scale) + 6;
            b.Draw(Game1.staminaRect, new Rectangle(innerX, y, innerWidth, 3), Game1.textColor * 0.25f);
            y += 16;
        }

        string body = PlaqueInteraction.FontSafe(Game1.smallFont, this.shown.Body);
        int lineSpacing = Game1.smallFont.LineSpacing;
        int maxLines = Math.Max(1, (this.board.Bottom - BoardPadding + 8 - y) / lineSpacing);
        IReadOnlyList<string> lines = ZooPlaques.Wrap(body, innerWidth, Measure);
        for (int i = 0; i < lines.Count && i < maxLines; i++)
        {
            string line = i == maxLines - 1 && lines.Count > maxLines ? lines[i] + "…" : lines[i];
            b.DrawString(Game1.smallFont, PlaqueInteraction.FontSafe(Game1.smallFont, line), new Vector2(innerX, y), Game1.textColor);
            y += lineSpacing;
        }
        this.DrawButtons(b, this.editButton, this.closeButton);
    }

    private void DrawEditor(SpriteBatch b)
    {
        int labelOffset = (int)Game1.smallFont.MeasureString("A").Y + 4;
        Utility.drawTextWithShadow(b, this.T("plaque.menu.title-label"), Game1.smallFont, new Vector2(this.titleBox.X + 4, this.titleBox.Y - labelOffset), Game1.textColor);
        Utility.drawTextWithShadow(b, this.T("plaque.menu.body-label"), Game1.smallFont, new Vector2(this.bodyBox.X + 4, this.bodyBox.Y - labelOffset), Game1.textColor);

        string counter = this.T("plaque.menu.counter", new { count = this.bodyBox.Text.Length, max = ZooPlaques.BodyLimit });
        float counterWidth = Measure(counter);
        Color counterColor = this.bodyBox.Text.Length >= ZooPlaques.BodyLimit ? Color.Red : Game1.textColor * 0.7f;
        b.DrawString(Game1.smallFont, counter, new Vector2(this.bodyBox.X + this.bodyBox.Width - counterWidth - 4, this.bodyBox.Y - labelOffset), counterColor);

        this.titleBox.Draw(b);
        this.bodyBox.Draw(b);

        string keys = this.T("plaque.menu.keys");
        b.DrawString(Game1.smallFont, keys, new Vector2(this.bodyBox.X + 4, this.bodyBox.Y + this.bodyBox.Height + 6), Game1.textColor * 0.55f);

        this.DrawButtons(b, this.saveButton, this.cancelButton, this.resetButton);
    }

    private void DrawButtons(SpriteBatch b, params ClickableComponent[] buttons)
    {
        foreach (ClickableComponent button in buttons)
        {
            Rectangle r = button.bounds;
            drawTextureBox(b, Game1.mouseCursors, ButtonSource, r.X, r.Y, r.Width, r.Height, this.hovered == button.name ? Color.Wheat : Color.White, 4f, false);
            string label = this.Label(button);
            Vector2 size = Game1.smallFont.MeasureString(label);
            Utility.drawTextWithShadow(b, label, Game1.smallFont, new Vector2(r.Center.X - size.X / 2, r.Center.Y - size.Y / 2 + 2), Game1.textColor);
        }
    }
}

/// <summary>
/// A vanilla <see cref="TextBox"/> (so it gets the same keyboard dispatcher input as naming menus and text signs,
/// including committed IME text) that filters glyphs the font can't draw and, when multiline, wraps and takes Enter as a newline.
/// </summary>
internal sealed class PlaqueTextBox : TextBox
{
    private const int InnerPadding = 20;
    private static readonly Rectangle FieldSource = new(384, 396, 15, 15);

    private readonly bool multiline;
    private readonly int limit;
    private readonly Func<char, bool> canDraw;

    /// <summary>Extra check on a multiline candidate text (e.g. that it still fits the box).</summary>
    public Func<string, bool>? Fits;

    public PlaqueTextBox(Texture2D? texture, SpriteFont font, bool multiline, int limit, Func<char, bool> canDraw)
        : base(texture, null, font, Game1.textColor)
    {
        this.multiline = multiline;
        this.limit = limit;
        this.canDraw = canDraw;
        this.limitWidth = !multiline;
    }

    public float InnerWidth => this.Width - InnerPadding * 2;

    public int VisibleLines => Math.Max(1, (this.Height - InnerPadding * 2 + 8) / this.Font.LineSpacing);

    public override void RecieveTextInput(char inputChar)
    {
        if (this.Selected && !char.IsControl(inputChar) && this.canDraw(inputChar))
            this.Append(inputChar.ToString());
    }

    public override void RecieveTextInput(string text)
    {
        if (!this.Selected || string.IsNullOrEmpty(text))
            return;
        text = text.Replace("\r\n", "\n").Replace('\r', '\n');
        if (!this.multiline)
            text = text.Replace('\n', ' ');
        this.Append(new string(text.Where(c => c == '\n' || (!char.IsControl(c) && this.canDraw(c))).ToArray()));
    }

    public override void RecieveCommandInput(char command)
    {
        if (this.multiline && command == '\r')
        {
            if (this.Selected && this.Text.Split('\n').Length < ZooPlaques.MaxBodyParagraphs)
                this.Append("\n");
            return;
        }
        if (command == '\b' && this.Selected && this.Text.Length >= 2 && char.IsLowSurrogate(this.Text[^1]))
        {
            this.Text = this.Text[..^2];
            return;
        }
        base.RecieveCommandInput(command);
    }

    private void Append(string text)
    {
        if (text.Length == 0)
            return;
        string candidate = ZooPlaques.Clamp(this.Text + text, this.limit);
        if (candidate == this.Text)
            return;
        if (this.multiline && this.Fits != null && !this.Fits(candidate))
            return;
        this.Text = candidate;
    }

    public override void Draw(SpriteBatch spriteBatch, bool drawShadow = true)
    {
        if (!this.multiline)
        {
            base.Draw(spriteBatch, drawShadow);
            return;
        }

        int lineSpacing = this.Font.LineSpacing;
        bool compact = Game1.textEntry != null;
        int height = compact ? lineSpacing + InnerPadding * 2 : this.Height;
        IClickableMenu.drawTextureBox(spriteBatch, Game1.mouseCursors, FieldSource, this.X, this.Y, this.Width, height,
            this.Selected ? Color.White : Color.White * 0.85f, 4f, false);

        IReadOnlyList<string> lines = ZooPlaques.Wrap(this.Text, this.InnerWidth, s => this.Font.MeasureString(s).X);
        int visible = compact ? 1 : this.VisibleLines;
        int first = Math.Max(0, lines.Count - visible);
        float y = this.Y + InnerPadding;
        for (int i = first; i < lines.Count; i++)
        {
            spriteBatch.DrawString(this.Font, lines[i], new Vector2(this.X + InnerPadding, y), this.TextColor);
            y += lineSpacing;
        }

        bool caretOn = Game1.currentGameTime.TotalGameTime.TotalMilliseconds % 1000.0 >= 500.0;
        if (this.Selected && caretOn)
        {
            float caretX = this.X + InnerPadding + this.Font.MeasureString(lines[^1]).X + 2;
            float caretY = y - lineSpacing;
            spriteBatch.Draw(Game1.staminaRect, new Rectangle((int)caretX, (int)caretY + 2, 4, lineSpacing - 4), this.TextColor);
        }
    }
}
