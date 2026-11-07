"""Draw the zoo furniture sheet and describe the items for content.json.

The sheet is 16px cells, 8 per row; a sprite index addresses its top-left cell (vanilla
Furniture uses index * 16 % width, index * 16 / width * 16). Each sprite is bottom-aligned
over its footprint: a 1x2 sprite with a 1x1 bounding box stands on its bottom cell.

Usage: python3 tools/draw_furniture.py
"""

import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "[CP] Stardew Zoo" / "assets" / "Furniture.png"
PREVIEW = Path(__file__).resolve().parent / "previews" / "furniture.png"
TEXTURE = "Mods/StardewZoo/Furniture"
SHEET_W, SHEET_H = 128, 32

# key, vanilla type, sprite size (tiles), bounding box (tiles), sprite index, price
ITEMS = [
    ("Bench", "bench", (2, 2), (2, 1), 0, 650),
    ("PenguinStatue", "decor", (1, 2), (1, 1), 2, 2500),
    ("ZooSign", "decor", (2, 2), (2, 1), 3, 800),
    ("BalloonStand", "decor", (1, 2), (1, 1), 5, 1200),
    ("TrashBin", "decor", (1, 2), (1, 1), 6, 250),
    ("PottedPalm", "decor", (1, 2), (1, 1), 7, 900),
]


def rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def scaled(color, factor):
    return tuple(max(0, min(255, round(c * factor))) for c in color[:3]) + (255,)


WOOD, WOOD_DARK, WOOD_LIGHT = rgb("#b8763d"), rgb("#8c4f27"), rgb("#dc9e5c")
IRON, IRON_DARK = rgb("#3f7d43"), rgb("#2a5a31")
STONE, STONE_DARK, STONE_LIGHT = rgb("#a9a9b6"), rgb("#7f7f91"), rgb("#d3d3dc")
CLAY, CLAY_DARK, CLAY_LIGHT = rgb("#c4622f"), rgb("#94431f"), rgb("#e38a52")
LEAF, LEAF_DARK, LEAF_LIGHT = rgb("#5daa33"), rgb("#3b7a24"), rgb("#8fcd4c")
TRUNK, TRUNK_DARK = rgb("#94643a"), rgb("#6b4426")
SIGN_GREEN, WHITE = rgb("#3f8c45"), rgb("#f4f1e4")
RED, YELLOW, BLUE = rgb("#e2423f"), rgb("#f2c93a"), rgb("#4b8fe2")
BIN, BIN_DARK, BIN_LIGHT = rgb("#4e8a3c"), rgb("#36672b"), rgb("#73b058")
GREY, GREY_DARK = rgb("#c9c9c9"), rgb("#8d8d8d")


def ell(cx, cy, rx, ry):
    return lambda x, y: ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1


def rect(x0, y0, x1, y1):
    """Pixels x0..x1-1, y0..y1-1."""
    return lambda x, y: x0 <= x < x1 and y0 <= y < y1


def seg(x0, y0, x1, y1, width):
    dx, dy = x1 - x0, y1 - y0
    length2 = dx * dx + dy * dy or 1

    def inside(x, y):
        px, py = x + 0.5, y + 0.5
        t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / length2))
        return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy)) <= width / 2

    return inside


class Sprite:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = {}

    def fill(self, shape, color):
        for y in range(self.h):
            for x in range(self.w):
                if shape(x, y):
                    self.px[x, y] = color

    def dot(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[x, y] = color

    def outline(self):
        """Vanilla-style dark rim: every empty pixel touching the sprite takes a darkened neighbour colour."""
        rim = {}
        for y in range(self.h):
            for x in range(self.w):
                if (x, y) in self.px:
                    continue
                for nx, ny in ((x, y + 1), (x, y - 1), (x - 1, y), (x + 1, y)):
                    if (nx, ny) in self.px:
                        rim[x, y] = scaled(self.px[nx, ny], 0.42)
                        break
        self.px.update(rim)

    def paste(self, sheet, ox, oy):
        for (x, y), color in self.px.items():
            sheet.putpixel((ox + x, oy + y), color)


def bench():
    s = Sprite(32, 32)
    for x0 in (3, 26):
        s.fill(rect(x0, 9, x0 + 3, 28), IRON)
        s.fill(rect(x0 + 2, 9, x0 + 3, 28), IRON_DARK)
    for y0 in (10, 14):
        s.fill(rect(2, y0, 30, y0 + 3), WOOD)
        s.fill(rect(2, y0, 30, y0 + 1), WOOD_LIGHT)
        s.fill(rect(2, y0 + 2, 30, y0 + 3), WOOD_DARK)
    s.fill(rect(1, 19, 31, 23), WOOD)
    s.fill(rect(1, 19, 31, 20), WOOD_LIGHT)
    s.fill(rect(1, 22, 31, 23), WOOD_DARK)
    for x in (8, 16, 24):
        s.fill(rect(x, 19, x + 1, 22), WOOD_DARK)
    for x0 in (3, 26):
        s.fill(rect(x0, 23, x0 + 3, 29), IRON)
        s.fill(rect(x0 - 1, 28, x0 + 4, 29), IRON_DARK)
    s.outline()
    return s


def penguin_statue():
    s = Sprite(16, 32)
    s.fill(rect(2, 27, 14, 31), STONE_DARK)
    s.fill(rect(2, 27, 14, 28), STONE)
    s.fill(rect(3, 21, 13, 27), STONE)
    s.fill(rect(3, 21, 5, 27), STONE_LIGHT)
    s.fill(rect(11, 21, 13, 27), STONE_DARK)
    s.fill(rect(2, 19, 14, 21), STONE_LIGHT)
    slate = scaled(STONE_DARK, 0.8)
    s.fill(ell(8, 13.5, 4.3, 6.2), STONE_DARK)
    s.fill(ell(4.2, 13.5, 1.4, 3.6), slate)
    s.fill(ell(11.8, 13.5, 1.4, 3.6), slate)
    s.fill(ell(8, 14.5, 2.6, 4.4), STONE_LIGHT)
    s.fill(ell(8, 6.5, 3.2, 3.0), STONE_DARK)
    s.fill(ell(8, 7.2, 2.0, 1.6), STONE_LIGHT)
    s.dot(6, 6, slate)
    s.dot(9, 6, slate)
    s.fill(rect(7, 8, 9, 10), rgb("#c9a65a"))
    s.fill(rect(5, 19, 7, 20), rgb("#c9a65a"))
    s.fill(rect(9, 19, 11, 20), rgb("#c9a65a"))
    s.dot(6, 4, STONE)
    s.outline()
    return s


LETTERS = {
    "Z": ["11111", "00010", "00100", "01000", "11111"],
    "O": ["01110", "10001", "10001", "10001", "01110"],
}


def zoo_sign():
    s = Sprite(32, 32)
    for x0 in (5, 24):
        s.fill(rect(x0, 14, x0 + 3, 31), WOOD)
        s.fill(rect(x0 + 2, 14, x0 + 3, 31), WOOD_DARK)
    s.fill(rect(1, 3, 31, 17), WOOD)
    s.fill(rect(1, 3, 31, 4), WOOD_LIGHT)
    s.fill(rect(1, 16, 31, 17), WOOD_DARK)
    s.fill(rect(3, 5, 29, 15), SIGN_GREEN)
    s.fill(rect(3, 14, 29, 15), scaled(SIGN_GREEN, 0.8))
    for i, letter in enumerate("ZOO"):
        for row, bits in enumerate(LETTERS[letter]):
            for col, bit in enumerate(bits):
                if bit == "1":
                    s.dot(7 + i * 7 + col, 7 + row, WHITE)
    s.fill(ell(4.5, 2.5, 2.2, 2.2), LEAF)
    s.fill(ell(27.5, 2.5, 2.2, 2.2), LEAF)
    s.dot(4, 1, LEAF_LIGHT)
    s.dot(27, 1, LEAF_LIGHT)
    s.fill(rect(4, 29, 9, 31), LEAF_DARK)
    s.fill(rect(23, 29, 28, 31), LEAF_DARK)
    s.outline()
    return s


def balloon_stand():
    s = Sprite(16, 32)
    for bx, by in ((4.5, 6.5), (11.5, 6.5), (8, 3.5)):
        s.fill(seg(bx, by + 3, 8, 15, 0.9), GREY)
    s.fill(rect(7, 13, 9, 24), GREY_DARK)
    s.fill(rect(7, 13, 8, 24), GREY)
    for (bx, by), color in (((4.5, 6.5), RED), ((11.5, 6.5), BLUE), ((8, 3.5), YELLOW)):
        s.fill(ell(bx, by, 3.0, 3.4), color)
        s.fill(ell(bx + 0.8, by + 0.9, 1.9, 2.2), scaled(color, 0.82))
        s.fill(ell(bx - 0.7, by - 0.9, 1.4, 1.6), color)
        s.dot(int(bx - 1), int(by - 2), WHITE)
    s.fill(rect(2, 22, 14, 29), WHITE)
    for x in range(2, 14, 4):
        s.fill(rect(x, 22, x + 2, 29), RED)
    s.fill(rect(1, 21, 15, 23), WOOD)
    s.fill(rect(1, 21, 15, 22), WOOD_LIGHT)
    s.fill(rect(2, 28, 14, 29), WOOD_DARK)
    s.fill(ell(4.5, 29.5, 1.8, 1.8), IRON_DARK)
    s.fill(ell(11.5, 29.5, 1.8, 1.8), IRON_DARK)
    s.outline()
    return s


def trash_bin():
    s = Sprite(16, 32)
    s.fill(lambda x, y: 18 <= y < 30 and 3 + (y - 18) // 6 <= x < 13 - (y - 18) // 6, BIN)
    for x in (5, 8, 11):
        s.fill(lambda px, py, x=x: px == x and 20 <= py < 29, BIN_DARK)
    s.fill(rect(4, 19, 5, 29), BIN_LIGHT)
    s.fill(rect(2, 16, 14, 19), BIN_DARK)
    s.fill(rect(2, 16, 14, 17), BIN_LIGHT)
    s.fill(rect(6, 14, 10, 16), BIN_DARK)
    s.fill(rect(7, 14, 9, 15), BIN_LIGHT)
    s.fill(rect(4, 29, 12, 30), BIN_DARK)
    s.outline()
    return s


def potted_palm():
    s = Sprite(16, 32)
    for i, y in enumerate(range(12, 24, 2)):
        x = 8 + (1 if i % 2 else 0) - (1 if y < 16 else 0)
        s.fill(rect(x - 1, y, x + 1, y + 2), TRUNK)
        s.dot(x, y + 1, TRUNK_DARK)
    # Each frond arcs from the crown up to a peak and droops to its tip.
    crown = (8, 10)
    fronds = [((4, 7), (0.8, 14)), ((12, 7), (15.2, 14)), ((4.5, 4), (1, 7.5)),
              ((11.5, 4), (15, 7.5)), ((7, 2), (3.5, 2.5)), ((9, 2), (12.5, 2.5))]
    for (mx, my), (x1, y1) in fronds:
        s.fill(seg(*crown, mx, my, 2.6), LEAF)
        s.fill(seg(mx, my, x1, y1, 2.0), LEAF)
        s.fill(seg(mx, my, x1, y1, 0.7), LEAF_DARK)
        s.fill(seg(*crown, mx, my, 0.7), LEAF_LIGHT)
    s.fill(ell(8, 10, 2.0, 1.6), LEAF_DARK)
    s.fill(rect(4, 25, 12, 31), CLAY)
    s.fill(rect(4, 25, 6, 31), CLAY_LIGHT)
    s.fill(rect(10, 25, 12, 31), CLAY_DARK)
    s.fill(rect(3, 23, 13, 25), CLAY)
    s.fill(rect(3, 23, 13, 24), CLAY_LIGHT)
    s.fill(rect(5, 23, 11, 24), TRUNK_DARK)
    s.outline()
    return s


DRAWERS = {
    "Bench": bench,
    "PenguinStatue": penguin_statue,
    "ZooSign": zoo_sign,
    "BalloonStand": balloon_stand,
    "TrashBin": trash_bin,
    "PottedPalm": potted_palm,
}


def furniture_data(key):
    """Data/Furniture string: name/type/sprite size/bounding box/rotations/price/placement/display name/index/texture."""
    _, kind, (sw, sh), (bw, bh), index, price = next(item for item in ITEMS if item[0] == key)
    return "/".join([
        f"StardewZoo.{key}", kind, f"{sw} {sh}", f"{bw} {bh}", "1", str(price), "2",
        f"{{{{i18n:furniture.{key}.name}}}}", str(index), TEXTURE, "false",
    ])


def content_changes():
    """content.json entries for the zoo furniture; write_content.py appends these."""
    return [
        {"LogName": "Zoo furniture texture", "Action": "Load", "Target": TEXTURE, "FromFile": "assets/Furniture.png"},
        {
            "LogName": "Zoo furniture",
            "Action": "EditData",
            "Target": "Data/Furniture",
            "Entries": {f"StardewZoo.{key}": furniture_data(key) for key, *_ in ITEMS},
        },
        {
            "LogName": "Zoo furniture at Robin's",
            "Action": "EditData",
            "Target": "Data/Shops",
            "TargetField": ["Carpenter", "Items"],
            "Entries": {
                f"StardewZoo.{key}": {"Id": f"StardewZoo.{key}", "ItemId": f"(F)StardewZoo.{key}", "Price": price}
                for key, _, _, _, _, price in ITEMS
            },
        },
    ]


def main():
    sheet = Image.new("RGBA", (SHEET_W, SHEET_H), (0, 0, 0, 0))
    for key, _, (sw, sh), _, index, _ in ITEMS:
        sprite = DRAWERS[key]()
        assert (sprite.w, sprite.h) == (sw * 16, sh * 16), key
        sprite.paste(sheet, index * 16 % SHEET_W, index * 16 // SHEET_W * 16)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    preview = Image.new("RGBA", (SHEET_W, SHEET_H), (120, 170, 90, 255))
    preview.alpha_composite(sheet)
    preview.resize((SHEET_W * 4, SHEET_H * 4), Image.NEAREST).save(PREVIEW)
    print(f"Wrote {OUT} ({SHEET_W}x{SHEET_H}) and {PREVIEW}")


if __name__ == "__main__":
    main()
