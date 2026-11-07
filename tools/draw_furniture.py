"""Draw the zoo furniture sheet and describe the items for content.json.

The sheet is 16px cells, 16 per row; a sprite index addresses its top-left cell (vanilla
Furniture uses index * 16 % width, index * 16 / width * 16). Each sprite is bottom-aligned
over its footprint: a 1x2 sprite with a 1x1 bounding box stands on its bottom cell.
Lamps draw their lit sprite one sprite-width to the right of the unlit one (vanilla sourceIndexOffset).

The park decor that used to be baked into the zoo map (benches, planters, lamps, bins, carts,
signposts, plaques, fountain, arch) is drawn by draw_tiles / draw_pavilions and rendered here,
so the player buys and places it like any other furniture.

Usage: python3 tools/draw_furniture.py
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

import draw_tiles as dt
from draw_pavilions import draw_fern_pot

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "[CP] Stardew Zoo" / "assets" / "Furniture.png"
PREVIEW = Path(__file__).resolve().parent / "previews" / "furniture.png"
TEXTURE = "Mods/StardewZoo/Furniture"
SHEET_COLS = 16
SHEET_W = SHEET_COLS * 16
BIOMES = ("Ice", "Water", "Savanna", "Jungle", "Forest", "Prehistoric")
SIGNPOSTS = (("Ice", "Water"), ("Savanna", "Jungle"), ("Forest", "Prehistoric"))
PLANTERS = {
    "Red": ("#c23b22", "#ff8a6a"), "Yellow": ("#c98a16", "#ffe58a"),
    "Pink": ("#b0407a", "#ffb3cf"), "Blue": ("#3a5fc8", "#a9c8ff"),
}

# The first six shipped on an 8-wide sheet; their cells (top-left 8x2 block) keep the same pixels on the wider sheet.
FIXED_INDEX = {"Bench": 0, "PenguinStatue": 2, "ZooSign": 3, "BalloonStand": 5, "TrashBin": 6, "PottedPalm": 7}

# key, vanilla type, sprite size (tiles), bounding box (tiles), price
ITEMS = [
    ("Bench", "bench", (2, 2), (2, 1), 650),
    ("PenguinStatue", "decor", (1, 2), (1, 1), 2500),
    ("ZooSign", "decor", (2, 2), (2, 1), 800),
    ("BalloonStand", "decor", (1, 2), (1, 1), 1200),
    ("TrashBin", "decor", (1, 2), (1, 1), 250),
    ("PottedPalm", "decor", (1, 2), (1, 1), 900),
    ("ParkBench", "bench", (2, 1), (2, 1), 500),
    *[(f"Planter{c}", "decor", (1, 1), (1, 1), 300) for c in PLANTERS],
    ("FernPot", "decor", (1, 1), (1, 1), 350),
    ("ZooLampPost", "lamp", (1, 3), (1, 1), 1500),
    ("RecyclingBin", "decor", (1, 1), (1, 1), 250),
    ("SnackCart", "decor", (2, 2), (2, 1), 2500),
    ("IceCreamCart", "decor", (2, 2), (2, 1), 2500),
    *[(f"Signpost{a}{b}", "decor", (1, 2), (1, 1), 600) for a, b in SIGNPOSTS],
    *[(f"Plaque{b}", "decor", (1, 1), (1, 1), 400) for b in BIOMES],
    ("Turnstile", "decor", (1, 2), (1, 1), 750),
    ("ZooArch", "decor", (4, 3), (4, 1), 4000),
    ("Fountain", "decor", (3, 3), (3, 2), 5000),
]


def sprite_frames(kind):
    """Lamps carry a second (lit) sprite to the right of the unlit one."""
    return 2 if kind == "lamp" else 1


def layout():
    """key -> sprite index. Fixed items keep their cells; the rest are packed row by row into free cells."""
    taken = set()

    def free(col, row, w, h):
        return col + w <= SHEET_COLS and all((col + c, row + r) not in taken for r in range(h) for c in range(w))

    def claim(col, row, w, h):
        taken.update((col + c, row + r) for r in range(h) for c in range(w))

    out = {}
    for key, kind, (sw, sh), _, _ in ITEMS:
        if key in FIXED_INDEX:
            index = FIXED_INDEX[key]
            claim(index % SHEET_COLS, index // SHEET_COLS, sw * sprite_frames(kind), sh)
            out[key] = index
    for key, kind, (sw, sh), _, _ in ITEMS:
        if key in out:
            continue
        w = sw * sprite_frames(kind)
        row = 0
        while True:
            col = next((c for c in range(SHEET_COLS) if free(c, row, w, sh)), None)
            if col is not None:
                break
            row += 1
        claim(col, row, w, sh)
        out[key] = row * SHEET_COLS + col
    rows = 1 + max(r for _, r in taken)
    return out, rows


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


def lamp_post(lit):
    """The zoo map's iron lamp post; unlit glass by day, a warm lantern with a soft halo when on."""
    im = dt.draw_lamp()
    px = im.load()
    glass, glint = dt.C("#ffe89a"), (255, 255, 230, 255)
    for y in range(im.height):
        for x in range(im.width):
            if px[x, y] == glass:
                px[x, y] = dt.C("#ffe066") if lit else dt.C("#9aa6a0")
            elif px[x, y] == glint:
                px[x, y] = (255, 255, 240, 255) if lit else dt.C("#c4ccc8")
    if lit:
        halo = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(halo).ellipse((0, 0, 15, 14), fill=(255, 236, 140, 70))
        halo.alpha_composite(im)
        im = halo
    return im


def big_fountain():
    """3x3 tiered fountain in the map fountain's style: stone basin, pedestal, upper bowl and jet."""
    im = dt.canvas(3, 3)
    d = ImageDraw.Draw(im)
    rock, water = dt.ROCK, dt.WATER
    dt.shade(im, lambda m: m.ellipse((1, 21, 46, 47), fill=255), rock)
    d.ellipse((5, 25, 42, 42), fill=water[1])
    d.ellipse((6, 26, 41, 41), fill=water[2])
    d.arc((6, 26, 41, 41), 200, 340, fill=water[4])
    for i in range(10):
        a = math.radians(i * 36 + 10)
        d.point((24 + round(13 * math.cos(a)), 34 + round(5 * math.sin(a))), fill=water[4])
    d.line((5, 43, 42, 43), fill=rock[2])
    d.rectangle((20, 14, 27, 35), fill=rock[3], outline=rock[0])
    d.line((21, 15, 21, 34), fill=rock[5])
    dt.shade(im, lambda m: m.ellipse((11, 10, 36, 19), fill=255), rock)
    d.ellipse((14, 11, 33, 15), fill=water[3])
    d.line((23, 0, 23, 12), fill=water[4])
    d.line((24, 1, 24, 12), fill=water[5])
    for k in range(4):
        d.point((13 - k, 17 + k * 3), fill=water[4])
        d.point((34 + k, 17 + k * 3), fill=water[4])
    for x in (10, 18, 30, 37):
        d.point((x, 23 + (x % 2)), fill=water[5])
    return im


def turnstile():
    """Chrome entry turnstile: a waist-high post with three arms and a green go-light."""
    im = dt.canvas(1, 2)
    d = ImageDraw.Draw(im)
    rock = dt.ROCK
    d.rectangle((5, 15, 10, 30), fill=rock[3], outline=dt.INK)
    d.line((6, 16, 6, 29), fill=rock[5])
    d.rectangle((4, 29, 11, 31), fill=rock[1], outline=dt.INK)
    d.rectangle((4, 12, 11, 15), fill=rock[2], outline=dt.INK)
    d.point((7, 13), fill=dt.C("#5cf08a"))
    d.point((8, 13), fill=dt.C("#2b8f3e"))
    for x0, y0, x1, y1 in ((8, 19, 15, 19), (8, 19, 3, 24), (8, 19, 3, 14)):
        d.line((x0, y0, x1, y1), fill=rock[1], width=2)
        d.line((x0, y0 - 1, x1, y1 - 1), fill=rock[4])
    d.ellipse((6, 17, 10, 21), fill=rock[4], outline=dt.INK)
    return im


DRAWERS = {
    "Bench": bench,
    "PenguinStatue": penguin_statue,
    "ZooSign": zoo_sign,
    "BalloonStand": balloon_stand,
    "TrashBin": trash_bin,
    "PottedPalm": potted_palm,
    "ParkBench": dt.draw_bench,
    **{f"Planter{c}": (lambda f=f: dt.draw_planter(f)) for c, f in PLANTERS.items()},
    "FernPot": draw_fern_pot,
    "ZooLampPost": lambda: [lamp_post(False), lamp_post(True)],
    "RecyclingBin": lambda: dt.draw_bin(True),
    "SnackCart": lambda: dt.draw_cart("snack"),
    "IceCreamCart": lambda: dt.draw_cart("icecream"),
    **{f"Signpost{a}{b}": (lambda a=a, b=b: dt.draw_signpost(a, b)) for a, b in SIGNPOSTS},
    **{f"Plaque{b}": (lambda b=b: dt.draw_plaque(b)) for b in BIOMES},
    "Turnstile": turnstile,
    "ZooArch": dt.draw_arch,
    "Fountain": big_fountain,
}


def item(key):
    return next(entry for entry in ITEMS if entry[0] == key)


def sprite_images(key):
    """The item's sprite frames as RGBA images (unlit first)."""
    drawn = DRAWERS[key]()
    frames = drawn if isinstance(drawn, list) else [drawn]
    out = []
    for frame in frames:
        if isinstance(frame, Sprite):
            img = Image.new("RGBA", (frame.w, frame.h), (0, 0, 0, 0))
            frame.paste(img, 0, 0)
            frame = img
        out.append(frame)
    return out


def furniture_data(key):
    """Data/Furniture string: name/type/sprite size/bounding box/rotations/price/placement/display name/index/texture."""
    _, kind, (sw, sh), (bw, bh), price = item(key)
    index = layout()[0][key]
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
            # Field 10 ("false") keeps every item in the Furniture Catalogue's ALL_ITEMS (F) @isRandomSale list.
            "LogName": "Zoo furniture at Robin's",
            "Action": "EditData",
            "Target": "Data/Shops",
            "TargetField": ["Carpenter", "Items"],
            "Entries": {
                f"StardewZoo.{key}": {"Id": f"StardewZoo.{key}", "ItemId": f"(F)StardewZoo.{key}", "Price": price}
                for key, _, _, _, price in ITEMS
            },
        },
    ]


def build_sheet():
    index, rows = layout()
    sheet = Image.new("RGBA", (SHEET_W, rows * 16), (0, 0, 0, 0))
    for key, kind, (sw, sh), _, _ in ITEMS:
        frames = sprite_images(key)
        assert len(frames) == sprite_frames(kind), key
        x, y = index[key] * 16 % SHEET_W, index[key] * 16 // SHEET_W * 16
        for i, frame in enumerate(frames):
            assert frame.size == (sw * 16, sh * 16), (key, frame.size)
            sheet.alpha_composite(frame, (x + i * sw * 16, y))
    return sheet


def main():
    sheet = build_sheet()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    preview = Image.new("RGBA", sheet.size, (120, 170, 90, 255))
    preview.alpha_composite(sheet)
    preview.resize((sheet.width * 3, sheet.height * 3), Image.NEAREST).save(PREVIEW)
    print(f"Wrote {OUT} ({sheet.width}x{sheet.height}, {len(ITEMS)} items) and {PREVIEW}")


if __name__ == "__main__":
    main()
