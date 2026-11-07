"""Draw 16x32 visitor NPC sheets (4 walk frames x 4 directions)."""

from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent.parent / "[CP] Stardew Zoo" / "assets"
PREVIEW_DIR = Path(__file__).resolve().parent / "previews"
FW, FH = 16, 32


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


SKIN = rgb("#f1c27d")
LINE = rgb("#2b2d42")
HAIR_VARIANTS = [rgb("#2b2d42"), rgb("#6b4226"), rgb("#e9c46a"), rgb("#4a1520")]
SHIRT_VARIANTS = [rgb("#e63946"), rgb("#457b9d"), rgb("#2d6a4f"), rgb("#f4d35e")]
PANTS_VARIANTS = [rgb("#1d3557"), rgb("#6b4f2a"), rgb("#2b2d42"), rgb("#8d99ae")]


def draw_person(shirt, pants, hair, direction, frame):
    """direction: 0 down, 1 right, 2 up, 3 left. frame 0-3 walk."""
    img = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bob = 1 if frame % 2 else 0
    leg = 1 if frame in (1, 3) else 0
    # body
    d.rectangle((5, 14 + bob, 11, 23 + bob), fill=shirt, outline=LINE)
    d.rectangle((5, 22 + bob, 11, 28 + bob), fill=pants, outline=LINE)
    # legs
    if direction in (0, 2):
        d.rectangle((5, 27 + bob, 7, 31 + bob - (leg if direction == 0 else 0)), fill=pants)
        d.rectangle((9, 27 + bob, 11, 31 + bob - (0 if direction == 0 else leg)), fill=pants)
    else:
        d.rectangle((7, 27 + bob, 10, 31 + bob - leg), fill=pants)
    # head
    d.ellipse((4, 4 + bob, 12, 14 + bob), fill=SKIN, outline=LINE)
    d.rectangle((4, 4 + bob, 12, 8 + bob), fill=hair)
    # face
    if direction == 0:
        d.point((6, 10 + bob), fill=LINE)
        d.point((10, 10 + bob), fill=LINE)
        d.point((8, 12 + bob), fill=LINE)
        # hat brim
        d.rectangle((3, 6 + bob, 13, 8 + bob), fill=shirt)
    elif direction == 2:
        d.rectangle((4, 4 + bob, 12, 9 + bob), fill=hair)
        d.rectangle((3, 6 + bob, 13, 8 + bob), fill=shirt)
    else:
        eye_x = 10 if direction == 1 else 6
        d.point((eye_x, 10 + bob), fill=LINE)
        d.rectangle((3, 6 + bob, 13, 8 + bob), fill=shirt)
    # camera / backpack accent
    if shirt == SHIRT_VARIANTS[2]:
        d.rectangle((6, 16 + bob, 10, 19 + bob), fill=rgb("#2b2d42"))
    if pants == PANTS_VARIANTS[0] and direction == 1:
        d.rectangle((3, 16 + bob, 6, 22 + bob), fill=rgb("#6b4226"))
    return img


def build_sheet(variant):
    shirt, pants, hair = SHIRT_VARIANTS[variant], PANTS_VARIANTS[variant], HAIR_VARIANTS[variant]
    sheet = Image.new("RGBA", (FW * 4, FH * 4), (0, 0, 0, 0))
    for direction in range(4):
        for frame in range(4):
            sprite = draw_person(shirt, pants, hair, direction, frame)
            sheet.paste(sprite, (frame * FW, direction * FH), sprite)
    return sheet


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    for i in range(4):
        sheet = build_sheet(i)
        sheet.save(OUT_DIR / f"StardewZooVisitor{i}.png")
        sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(PREVIEW_DIR / f"StardewZooVisitor{i}.png")
    print("Wrote 4 visitor sheets")


if __name__ == "__main__":
    main()
