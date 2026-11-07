"""Draw original zoo building exteriors (7x4 footprint, 112x128 sprites).

Does not touch animal art. Three tiers look increasingly grand and all have a
visible ZOO sign. There is no animal door.

Usage: python3 tools/make_sprites.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent.parent / "[CP] Stardew Zoo" / "assets"
PREVIEW_DIR = Path(__file__).resolve().parent / "previews"
W, H = 112, 128


def rgb(hex_color: str) -> tuple[int, int, int, int]:
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def scaled(color, factor):
    return tuple(max(0, min(255, int(v * factor))) for v in color[:3]) + (255,)


def draw_building(tier: int) -> Image.Image:
    """tier 0/1/2 = Zoo / Big Zoo / Deluxe Zoo."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if tier == 0:
        roof, roof_dark, wall, trim, sign, sign_text = (
            rgb("#2d6a4f"), rgb("#1b4332"), rgb("#c4a574"), rgb("#6b4226"),
            rgb("#f4d35e"), rgb("#1d3557"),
        )
        column = None
        flags = False
        dome = False
    elif tier == 1:
        roof, roof_dark, wall, trim, sign, sign_text = (
            rgb("#1d3557"), rgb("#0d1b2a"), rgb("#d9d2c5"), rgb("#4a5759"),
            rgb("#e9c46a"), rgb("#1d3557"),
        )
        column = rgb("#9aa3ad")
        flags = True
        dome = False
    else:
        roof, roof_dark, wall, trim, sign, sign_text = (
            rgb("#7b2d3b"), rgb("#4a1520"), rgb("#efece4"), rgb("#c9a227"),
            rgb("#f4d35e"), rgb("#4a1520"),
        )
        column = rgb("#e8e4dc")
        flags = True
        dome = True

    # Roof (top 64px sits above the 4-tile footprint)
    d.polygon([(8, 52), (56, 8), (104, 52)], fill=roof)
    d.polygon([(8, 52), (56, 18), (104, 52)], fill=roof_dark)
    if dome:
        d.ellipse((40, 0, 72, 36), fill=trim)
        d.ellipse((44, 4, 68, 32), fill=roof)
        d.rectangle((54, 0, 58, 10), fill=trim)
        d.ellipse((52, 0, 60, 8), fill=rgb("#f4d35e"))
    else:
        d.polygon([(20, 48), (56, 14), (92, 48)], fill=roof)

    if flags:
        d.rectangle((18, 6, 20, 48), fill=trim)
        d.rectangle((92, 6, 94, 48), fill=trim)
        flag = rgb("#e63946") if tier == 1 else rgb("#f4d35e")
        d.polygon([(20, 8), (36, 14), (20, 20)], fill=flag)
        d.polygon([(92, 8), (76, 14), (92, 20)], fill=flag)

    # Body occupies the bottom 64px (4 tiles)
    d.rectangle((6, 52, 106, 126), fill=wall)
    d.rectangle((6, 52, 106, 58), fill=trim)
    d.rectangle((6, 120, 106, 126), fill=trim)
    d.rectangle((6, 52, 10, 126), fill=trim)
    d.rectangle((102, 52, 106, 126), fill=trim)

    if column:
        for x in (16, 48, 80):
            d.rectangle((x, 62, x + 8, 120), fill=column)
            d.rectangle((x - 1, 60, x + 9, 64), fill=trim)
            d.rectangle((x - 1, 116, x + 9, 120), fill=trim)

    # Windows
    glass = rgb("#7bdff2") if tier == 0 else rgb("#cae9ff")
    for x in (22, 70):
        d.rectangle((x, 78, x + 16, 96), fill=glass)
        d.rectangle((x, 78, x + 16, 96), outline=trim)
        d.line((x + 8, 78, x + 8, 96), fill=trim)
        d.line((x, 87, x + 16, 87), fill=trim)

    # Door at HumanDoor tile (X=1, Y=3) → pixel x=16-32, bottom row
    d.rectangle((16, 100, 40, 126), fill=rgb("#4a2e16") if tier == 0 else rgb("#2b2d42"))
    d.rectangle((16, 100, 40, 126), outline=trim)
    d.arc((18, 100, 38, 122), 180, 0, fill=trim)
    d.ellipse((34, 112, 38, 116), fill=trim)

    # ZOO sign
    d.rectangle((32, 56, 80, 78), fill=sign)
    d.rectangle((32, 56, 80, 78), outline=sign_text, width=2)
    d.rectangle((52, 50, 60, 56), fill=trim)
    letter = sign_text

    def glyph_z(x, y):
        d.rectangle((x, y, x + 10, y + 2), fill=letter)
        for i in range(8):
            d.point((x + 9 - i, y + 2 + i), fill=letter)
            d.point((x + 8 - i, y + 2 + i), fill=letter)
        d.rectangle((x, y + 10, x + 10, y + 12), fill=letter)

    def glyph_o(x, y):
        d.rectangle((x, y, x + 10, y + 12), fill=letter)
        d.rectangle((x + 2, y + 2, x + 8, y + 10), fill=sign)

    glyph_z(36, 60)
    glyph_o(50, 60)
    glyph_o(64, 60)

    if tier >= 1:
        d.rectangle((12, 64, 22, 70), fill=sign)
        d.rectangle((90, 64, 100, 70), fill=sign)
    if tier == 2:
        d.polygon([(56, 44), (60, 52), (52, 52)], fill=trim)

    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    names = ("Zoo", "BigZoo", "DeluxeZoo")
    for tier, name in enumerate(names):
        img = draw_building(tier)
        img.save(OUT_DIR / f"{name}.png")
        img.resize((W * 4, H * 4), Image.NEAREST).save(PREVIEW_DIR / f"{name}.png")
    print(f"Wrote {len(names)} zoo exteriors to {OUT_DIR}")


if __name__ == "__main__":
    main()
