"""Custom zoo_tiles: hand-drawn props, generated terrain transitions, and composites.

The sheet is built in three passes:
  1. hand-drawn objects (booth, board, studio, fountain, carts, pen props...) are
     registered as multi-tile objects with stable names;
  2. make_map asks the TerrainBlender for corner-blended ground tiles (paving,
     sand, shallow water, snow, volcanic ground...) on top of vanilla textures;
  3. make_map composites stacked tiles (ground + decal) into single tiles so ground
     detail can live on the Back layer under the animals.

Colours are sampled from / matched to vanilla sheets (spring_outdoors grass and
dirt, spring_town wood, Festivals stalls) and every sprite gets the dark-brown
vanilla outline with top-left lighting.

Usage: python3 tools/draw_tiles.py   (writes a preview of the hand-drawn part)
"""

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

from vanilla import MAPS

OUT = Path(__file__).resolve().parent.parent / "[CP] Stardew Zoo" / "assets" / "zoo_tiles.png"
PREVIEW = Path(__file__).resolve().parent / "previews" / "zoo_tiles.png"
COLS = 16
TS = 16


def C(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def darker(c, f):
    return (round(c[0] * f), round(c[1] * f), round(c[2] * f), c[3])


INK = C("#3c2016")
WOOD = [C(h) for h in ("#3c2016", "#653623", "#845025", "#b27b37", "#c4974e", "#ebc071")]
DWOOD = [C(h) for h in ("#24130b", "#4a2a1a", "#5f3a24", "#7a4e30", "#956240", "#b07a50")]
ROCK = [C(h) for h in ("#2f2a33", "#4f4a57", "#6e6878", "#8f8999", "#b3aebb", "#d6d2dc")]
SNOW = [C(h) for h in ("#5b7fa0", "#a9c4dc", "#cfe0ee", "#e9f3fb", "#ffffff")]
ICE = [C(h) for h in ("#2f6f99", "#5fa8d0", "#8fcbe6", "#bfe8f6", "#ecfbff")]
LEAF = [C(h) for h in ("#123a1c", "#1d5e26", "#2b7c2a", "#3f9a2a", "#5fb92f", "#8bd645")]
JLEAF = [C(h) for h in ("#0b2e1d", "#14532d", "#1d7037", "#2b8f3e", "#46ad45", "#79cc5a")]
DRYG = [C(h) for h in ("#4f3d16", "#7d6427", "#a88c38", "#ccb04c", "#e3cd72", "#f3e4a0")]
BONE = [C(h) for h in ("#5a4a3a", "#a8987c", "#d6c9ad", "#efe6d0", "#fffaf0")]
EARTH = [C(h) for h in ("#4a2412", "#7a3e1e", "#a8592c", "#c97a42", "#e0a066")]
BASALT = [C(h) for h in ("#151012", "#2a2226", "#40363c", "#574a52", "#72636c")]
IRON = [C(h) for h in ("#1c1f24", "#2e3a3a", "#3f5450", "#5a7468", "#86a08c")]
RED = [C(h) for h in ("#4a0f0f", "#9e2a1e", "#d8452f", "#ee6a48")]
CREAM = C("#f6ead0")
GOLD = [C(h) for h in ("#7a4a08", "#c98a16", "#f0c23a", "#ffe58a")]
GLASS = [C(h) for h in ("#2d5c7a", "#6fb3d8", "#a9dcf0", "#e6f8ff")]
WATER = [C(h) for h in ("#1f4f63", "#2f6f86", "#3b7e96", "#5aa6c4", "#9ad4e6", "#e6f6ff")]

FONT = {
    "A": ("010", "101", "111", "101", "101"), "C": ("111", "100", "100", "100", "111"),
    "E": ("111", "100", "110", "100", "111"), "I": ("111", "010", "010", "010", "111"),
    "K": ("101", "101", "110", "101", "101"), "O": ("111", "101", "101", "101", "111"),
    "R": ("110", "101", "110", "101", "101"), "S": ("111", "100", "111", "001", "111"),
    "T": ("111", "010", "010", "010", "010"), "Z": ("111", "001", "010", "100", "111"),
}


def text(img, x, y, s, color, gap=1):
    for ch in s:
        if ch == " ":
            x += 2
            continue
        for r, row in enumerate(FONT[ch]):
            for c, bit in enumerate(row):
                if bit == "1":
                    img.putpixel((x + c, y + r), color)
        x += 3 + gap


def canvas(w, h):
    return Image.new("RGBA", (w * TS, h * TS), (0, 0, 0, 0))


def hnoise(x, y, s=0):
    h = (x * 374761393 + y * 668265263 + s * 982451653) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0 * 2 - 1


# ---------------------------------------------------------------------------
# shading helpers
# ---------------------------------------------------------------------------

def shade(img, draw_fn, ramp, light=(-0.55, -0.83), outline=True, dither=True, bias=0.0):
    """Fill a mask (drawn by draw_fn on an L image) with a lit ramp and outline.

    ramp[0] is the outline colour, ramp[1:] go from shadow to highlight.
    """
    mask = Image.new("L", img.size, 0)
    draw_fn(ImageDraw.Draw(mask))
    m = mask.load()
    W, H = img.size
    pts = [(x, y) for y in range(H) for x in range(W) if m[x, y]]
    if not pts:
        return
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    rx, ry = max(1.0, (max(xs) - min(xs)) / 2), max(1.0, (max(ys) - min(ys)) / 2)
    inner = ramp[1:]
    px = img.load()
    for x, y in pts:
        edge = any(
            not (0 <= nx < W and 0 <= ny < H) or not m[nx, ny]
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
        )
        if outline and edge:
            px[x, y] = ramp[0]
            continue
        nx, ny = (x - cx) / rx, (y - cy) / ry
        lit = -(nx * light[0] + ny * light[1]) * 0.75 + bias
        t = (lit + 1) / 2
        if dither:
            t += 0.07 if (x + y) % 2 else -0.07
        i = max(0, min(len(inner) - 1, int(t * len(inner))))
        px[x, y] = inner[i]


def outline_alpha(img, color=INK):
    """Add a 1px outline around opaque pixels (outside)."""
    src = img.copy()
    s = src.load()
    p = img.load()
    W, H = img.size
    for y in range(H):
        for x in range(W):
            if s[x, y][3]:
                continue
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < W and 0 <= ny < H and s[nx, ny][3] > 128:
                    p[x, y] = color
                    break


def rect_wood(d, box, ramp=WOOD, vertical=True, step=4, outline=True):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=ramp[3])
    if vertical:
        for x in range(x0 + step, x1, step):
            d.line((x, y0, x, y1), fill=ramp[2])
            d.line((x + 1, y0, x + 1, y1), fill=ramp[4])
    else:
        for y in range(y0 + step, y1, step):
            d.line((x0, y, x1, y), fill=ramp[2])
            d.line((x0, y + 1, x1, y + 1), fill=ramp[4])
    if outline:
        d.rectangle(box, outline=ramp[0])


def star(img, cx, cy, ramp=GOLD):
    for dx, dy in ((0, -2), (0, -1), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (0, 1), (-1, 2), (1, 2)):
        img.putpixel((cx + dx, cy + dy), ramp[2])
    img.putpixel((cx, cy - 1), ramp[3])
    img.putpixel((cx - 1, cy + 2), ramp[1])
    img.putpixel((cx + 1, cy + 2), ramp[1])


def coin(img, cx, cy):
    d = ImageDraw.Draw(img)
    d.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=GOLD[2], outline=GOLD[0])
    d.line((cx, cy - 1, cx, cy + 1), fill=GOLD[1])
    img.putpixel((cx - 1, cy - 2), GOLD[3])


def note(img, x, y, color=INK):
    d = ImageDraw.Draw(img)
    d.ellipse((x, y + 4, x + 2, y + 6), fill=color)
    d.line((x + 2, y, x + 2, y + 5), fill=color)
    d.line((x + 3, y, x + 4, y + 1), fill=color)


# ---------------------------------------------------------------------------
# biome icons (7x7) used on plaques and signposts
# ---------------------------------------------------------------------------

def icon(img, x, y, kind):
    d = ImageDraw.Draw(img)
    if kind == "Ice":
        for dx, dy in ((3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (0, 3), (1, 3), (2, 3), (4, 3), (5, 3), (6, 3),
                       (1, 1), (5, 1), (1, 5), (5, 5), (2, 2), (4, 2), (2, 4), (4, 4)):
            img.putpixel((x + dx, y + dy), C("#4aa3d8"))
        img.putpixel((x + 3, y + 3), C("#ffffff"))
    elif kind == "Water":
        d.line((x, y + 2, x + 1, y + 1), fill=C("#3a86c8"))
        d.line((x + 2, y + 1, x + 3, y + 2), fill=C("#3a86c8"))
        d.line((x + 4, y + 2, x + 5, y + 1), fill=C("#3a86c8"))
        d.line((x, y + 5, x + 1, y + 4), fill=C("#1f5fa0"))
        d.line((x + 2, y + 4, x + 3, y + 5), fill=C("#1f5fa0"))
        d.line((x + 4, y + 5, x + 5, y + 4), fill=C("#1f5fa0"))
        img.putpixel((x + 6, y + 4), C("#1f5fa0"))
    elif kind == "Savanna":
        d.ellipse((x + 1, y + 1, x + 5, y + 5), fill=C("#f0b429"), outline=C("#c2410c"))
        for dx, dy in ((3, -0), (3, 6), (0, 3), (6, 3)):
            img.putpixel((x + dx, y + dy), C("#c2410c"))
    elif kind == "Jungle":
        d.polygon([(x + 3, y), (x + 6, y + 3), (x + 3, y + 6), (x, y + 3)], fill=C("#2b8f3e"), outline=C("#14532d"))
        d.line((x + 1, y + 5, x + 5, y + 1), fill=C("#79cc5a"))
    elif kind == "Forest":
        d.polygon([(x + 3, y), (x + 6, y + 5), (x, y + 5)], fill=C("#2b7c2a"), outline=C("#123a1c"))
        d.line((x + 3, y + 5, x + 3, y + 6), fill=C("#653623"))
    else:  # Prehistoric: bone
        d.line((x + 1, y + 5, x + 5, y + 1), fill=C("#efe6d0"))
        for px_, py_ in ((x, y + 5), (x + 1, y + 6), (x + 5, y), (x + 6, y + 1)):
            img.putpixel((px_, py_), C("#efe6d0"))
        for px_, py_ in ((x, y + 6), (x + 6, y)):
            img.putpixel((px_, py_), C("#a8987c"))


BIOME_COLOR = {
    "Ice": C("#d8eef8"), "Water": C("#bfe3f5"), "Savanna": C("#f4dc8c"),
    "Jungle": C("#b7e4a8"), "Forest": C("#cfe3b0"), "Prehistoric": C("#e3cdb8"),
}


# ---------------------------------------------------------------------------
# plaza props
# ---------------------------------------------------------------------------

def draw_booth():
    """3x4 fair-style ticket stall: sign, striped awning, back wall + window, counter."""
    im = canvas(3, 4)
    d = ImageDraw.Draw(im)
    # back wall and posts
    rect_wood(d, (5, 26, 42, 50), WOOD, vertical=True, step=5)
    d.rectangle((17, 31, 30, 45), fill=INK)
    d.rectangle((18, 32, 29, 44), fill=GLASS[1])
    d.rectangle((18, 32, 29, 35), fill=GLASS[2])
    d.line((19, 33, 21, 33), fill=GLASS[3])
    d.line((23, 32, 23, 44), fill=WOOD[1])
    # clerk silhouette (round head + shoulders) behind glass
    d.ellipse((20, 36, 26, 42), fill=C("#e8b48a"), outline=INK)
    d.rectangle((19, 42, 27, 44), fill=C("#2f6f86"))
    # poster on the left wall
    d.rectangle((8, 31, 14, 41), fill=CREAM, outline=INK)
    icon(im, 8, 33, "Savanna")
    d.rectangle((33, 31, 39, 41), fill=CREAM, outline=INK)
    icon(im, 33, 33, "Water")
    for x0 in (2, 42):
        d.rectangle((x0, 14, x0 + 3, 62), fill=WOOD[2])
        d.line((x0 + 1, 14, x0 + 1, 62), fill=WOOD[4])
        d.rectangle((x0, 14, x0 + 3, 62), outline=INK)
    # counter
    d.rectangle((0, 48, 47, 52), fill=WOOD[4], outline=INK)
    d.line((1, 49, 46, 49), fill=WOOD[5])
    rect_wood(d, (2, 53, 45, 62), WOOD, vertical=True, step=6)
    d.line((2, 62, 45, 62), fill=WOOD[1])
    d.line((2, 63, 45, 63), fill=(0, 0, 0, 90))
    # ticket + coin emblem on the counter front
    d.polygon([(12, 54), (29, 54), (29, 56), (28, 57), (29, 58), (29, 60), (12, 60), (12, 58), (13, 57), (12, 56)],
              fill=CREAM, outline=INK)
    d.line((22, 55, 22, 59), fill=RED[2])
    text(im, 14, 55, "ZO", RED[1], gap=0)
    coin(im, 35, 57)
    # stack of tickets on the counter
    d.rectangle((6, 45, 11, 47), fill=CREAM, outline=INK)
    d.rectangle((38, 44, 42, 47), fill=GOLD[2], outline=INK)
    # awning (striped, scalloped)
    px = im.load()
    for y in range(13, 28):
        t = (y - 13) / 14
        half = 20 + 4 * t
        for x in range(48):
            u = (x - 23.5) / half
            if abs(u) > 1:
                continue
            stripe = int((u + 1) * 3.5) % 2
            c = RED[2] if stripe == 0 else CREAM
            if y < 16:
                c = mix(c, (255, 255, 255, 255), 0.18)
            elif y > 24:
                c = darker(c, 0.88)
            px[x, y] = c
    for i in range(8):
        cx = 3 + i * 6
        stripe = i % 2
        d.pieslice((cx - 3, 24, cx + 3, 31), 0, 180, fill=RED[2] if stripe == 0 else CREAM, outline=INK)
    d.line((4, 13, 43, 13), fill=INK)
    d.line((4, 13, 0, 27), fill=INK)
    d.line((43, 13, 47, 27), fill=INK)
    # top sign "TICKETS" with coin
    d.rectangle((7, 1, 40, 11), fill=WOOD[1], outline=INK)
    d.rectangle((8, 2, 39, 10), fill=CREAM)
    text(im, 10, 4, "TICKETS", RED[1], gap=0)
    coin(im, 36, 6)
    d.line((12, 11, 12, 13), fill=INK)
    d.line((35, 11, 35, 13), fill=INK)
    return im


def draw_board():
    """3x4 bulletin board like Pierre's: little roof, cork with notes and star stickers."""
    im = canvas(3, 4)
    d = ImageDraw.Draw(im)
    roof = [C(h) for h in ("#3a1410", "#6e2a1c", "#9a3d26", "#c25a35", "#dd8050")]
    # legs
    for x0 in (7, 37):
        d.rectangle((x0, 44, x0 + 3, 62), fill=WOOD[2], outline=INK)
        d.line((x0 + 1, 45, x0 + 1, 61), fill=WOOD[4])
    # frame + cork
    d.rectangle((2, 13, 45, 47), fill=WOOD[3], outline=INK)
    d.line((3, 14, 44, 14), fill=WOOD[5])
    d.rectangle((5, 16, 42, 44), fill=C("#c49a64"), outline=WOOD[1])
    rng = random.Random(7)
    for _ in range(90):
        x, y = rng.randint(6, 41), rng.randint(17, 43)
        im.putpixel((x, y), rng.choice([C("#b0844f"), C("#d6b07a")]))
    notes = [((7, 18, 17, 29), CREAM, RED[2]), ((19, 17, 29, 26), C("#f4d35e"), C("#2b5fa8")),
             ((31, 19, 40, 30), C("#cfe8c0"), C("#2b8f3e")), ((9, 31, 20, 42), C("#f6c6d0"), RED[2]),
             ((23, 29, 33, 41), CREAM, C("#2b5fa8"))]
    for box, col, pin in notes:
        x0, y0, x1, y1 = box
        d.rectangle((x0 + 1, y0 + 1, x1 + 1, y1 + 1), fill=(60, 30, 10, 90))
        d.rectangle(box, fill=col, outline=darker(col, 0.55))
        for ly in range(y0 + 3, y1 - 1, 2):
            d.line((x0 + 2, ly, x1 - 2 - (ly * 3) % 4, ly), fill=darker(col, 0.62))
        cx = (x0 + x1) // 2
        im.putpixel((cx, y0), pin)
        im.putpixel((cx, y0 + 1), darker(pin, 0.6))
    for sx, sy in ((26, 22), (37, 37), (14, 35), (35, 24)):
        star(im, sx, sy)
    # little drawing of a lion face on a note
    d.ellipse((25, 32, 31, 38), fill=C("#f0b429"), outline=C("#a85b10"))
    im.putpixel((27, 34), INK)
    im.putpixel((29, 34), INK)
    # roof
    d.polygon([(0, 13), (8, 2), (39, 2), (47, 13)], fill=roof[2], outline=roof[0])
    for y in range(4, 13, 3):
        d.line((1 + (13 - y) * 8 // 11, y, 46 - (13 - y) * 8 // 11, y), fill=roof[1])
    for y in range(5, 13, 3):
        for x in range(4, 44, 5):
            if 0 <= x < 48:
                im.putpixel((x + (y % 2) * 2, y), roof[3])
    d.line((9, 3, 38, 3), fill=roof[4])
    d.rectangle((15, 0, 32, 8), fill=WOOD[1], outline=INK)
    d.rectangle((16, 1, 31, 7), fill=CREAM)
    for sx in (19, 24, 29):
        star(im, sx, 4)
    # bottom plank
    d.rectangle((6, 50, 41, 55), fill=WOOD[4], outline=INK)
    d.line((7, 51, 40, 51), fill=WOOD[5])
    for sx in (13, 20, 27, 34):
        im.putpixel((sx, 53), GOLD[2])
        im.putpixel((sx - 1, 53), GOLD[1])
        im.putpixel((sx + 1, 53), GOLD[1])
        im.putpixel((sx, 52), GOLD[3])
    return im


def draw_studio():
    """2x2 recording cabin: teal gable, sound-wave sign, REC light, door + window."""
    im = canvas(2, 2)
    d = ImageDraw.Draw(im)
    roof = [C(h) for h in ("#163b3a", "#245e5c", "#2e7d7a", "#3f9e98", "#6cc4b8")]
    rect_wood(d, (2, 12, 29, 31), WOOD, vertical=True, step=4)
    d.line((2, 31, 29, 31), fill=WOOD[1])
    # door
    d.rectangle((4, 18, 12, 31), fill=DWOOD[2], outline=INK)
    d.rectangle((6, 20, 10, 24), fill=GLASS[1], outline=INK)
    d.ellipse((7, 21, 9, 23), fill=GLASS[2])
    im.putpixel((11, 26), GOLD[2])
    # window with mic silhouette
    d.rectangle((16, 20, 27, 28), fill=INK)
    d.rectangle((17, 21, 26, 27), fill=C("#5d3f86"))
    d.rectangle((17, 21, 26, 22), fill=C("#7d5fae"))
    d.ellipse((20, 22, 23, 25), fill=ROCK[4], outline=INK)
    d.line((21, 26, 22, 26), fill=INK)
    for x in (18, 25):
        d.line((x, 24, x, 26), fill=C("#c7a8f0"))
    # REC plate
    d.rectangle((14, 12, 30, 19), fill=INK)
    d.rectangle((15, 13, 29, 18), fill=C("#1e1e24"))
    d.ellipse((15, 14, 18, 17), fill=C("#ff3b3b"))
    im.putpixel((16, 14), C("#ffd0d0"))
    text(im, 20, 14, "REC", C("#ff6b6b"), gap=0)
    # roof
    d.polygon([(16, 0), (31, 11), (31, 13), (0, 13), (0, 11)], fill=roof[2], outline=roof[0])
    for y in range(4, 12, 3):
        half = int(y * 15 / 11)
        d.line((16 - half + 1, y, 16 + half - 1, y), fill=roof[1])
    d.line((15, 1, 4, 9), fill=roof[4])
    # sound-wave sign in the gable
    d.ellipse((10, 3, 21, 12), fill=C("#1e1e24"), outline=INK)
    for x, h in ((12, 1), (13, 2), (14, 3), (15, 2), (16, 4), (17, 2), (18, 3), (19, 1)):
        d.line((x, 7 - h // 2 - 0, x, 7 + (h + 1) // 2), fill=C("#5cf08a"))
    # antenna + REC bulb on the peak
    d.line((26, 1, 26, 7), fill=INK)
    d.ellipse((24, 0, 28, 3), fill=C("#ff3b3b"), outline=INK)
    im.putpixel((25, 1), C("#ffd0d0"))
    return im


def draw_speaker():
    im = canvas(1, 2)
    d = ImageDraw.Draw(im)
    note(im, 2, 3, C("#5d3f86"))
    note(im, 9, 7, C("#2e7d7a"))
    d.rectangle((2, 15, 13, 31), fill=C("#2a2228"), outline=INK)
    d.line((3, 16, 12, 16), fill=C("#4a3e48"))
    for cy, r in ((19, 2), (26, 3)):
        d.ellipse((8 - r, cy - r, 7 + r, cy + r), fill=C("#5a4f58"), outline=C("#120c10"))
        d.ellipse((7, cy - 1, 8, cy), fill=C("#9a8f98"))
    return im


def draw_mic():
    im = canvas(1, 2)
    d = ImageDraw.Draw(im)
    d.line((7, 13, 7, 28), fill=IRON[0])
    d.line((8, 13, 8, 28), fill=IRON[3])
    d.line((7, 28, 3, 31), fill=IRON[0])
    d.line((8, 28, 12, 31), fill=IRON[0])
    d.line((7, 28, 7, 31), fill=IRON[0])
    d.rectangle((6, 11, 9, 14), fill=IRON[1], outline=INK)
    d.ellipse((4, 3, 11, 11), fill=ROCK[4], outline=INK)
    for y in (5, 7, 9):
        d.line((6, y, 9, y), fill=ROCK[2])
    im.putpixel((6, 4), (255, 255, 255, 255))
    note(im, 11, 0, C("#d8452f"))
    return im


def fountain_frames():
    frames = []
    for f in range(4):
        im = canvas(2, 2)
        d = ImageDraw.Draw(im)
        shade(im, lambda m: m.ellipse((0, 12, 31, 31), fill=255), ROCK)
        d.ellipse((3, 15, 28, 27), fill=WATER[1])
        d.ellipse((4, 16, 27, 26), fill=WATER[2])
        for i in range(6):
            a = (i * 60 + f * 15) * math.pi / 180
            x = 16 + int(9 * math.cos(a))
            y = 21 + int(4 * math.sin(a))
            im.putpixel((x, y), WATER[4])
        d.arc((4, 16, 27, 26), 200, 340, fill=WATER[4])
        d.line((3, 28, 28, 28), fill=ROCK[2])
        # pedestal + upper bowl
        d.rectangle((13, 9, 18, 22), fill=ROCK[3], outline=ROCK[0])
        d.line((14, 10, 14, 21), fill=ROCK[5])
        shade(im, lambda m: m.ellipse((8, 6, 23, 12), fill=255), ROCK)
        d.ellipse((10, 7, 21, 10), fill=WATER[3])
        # jet + falling drops
        h = (0, 1, 2, 1)[f]
        d.line((15, 0 + h, 15, 8), fill=WATER[4])
        d.line((16, 1 + h, 16, 8), fill=WATER[5])
        for k in range(3):
            yy = (f * 3 + k * 4) % 10
            im.putpixel((11 - k, 4 + yy // 2 + 2), WATER[4])
            im.putpixel((20 + k, 4 + yy // 2 + 2), WATER[4])
        for k in range(4):
            x = (6 + k * 7 + f * 2) % 24 + 4
            im.putpixel((x, 13 + (k + f) % 2), WATER[5])
        frames.append(im)
    return frames


def draw_bench():
    im = canvas(2, 1)
    d = ImageDraw.Draw(im)
    for x0 in (3, 26):
        d.rectangle((x0, 2, x0 + 2, 15), fill=IRON[1], outline=IRON[0])
    d.rectangle((1, 2, 30, 4), fill=WOOD[3], outline=INK)
    d.line((2, 3, 29, 3), fill=WOOD[5])
    d.rectangle((1, 6, 30, 8), fill=WOOD[3], outline=INK)
    d.line((2, 7, 29, 7), fill=WOOD[4])
    d.rectangle((0, 10, 31, 12), fill=WOOD[4], outline=INK)
    d.line((1, 11, 30, 11), fill=WOOD[5])
    d.line((1, 13, 30, 13), fill=(0, 0, 0, 70))
    return im


def draw_planter(flower):
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    rect_wood(d, (2, 8, 13, 15), WOOD, vertical=True, step=3)
    d.rectangle((1, 7, 14, 9), fill=WOOD[4], outline=INK)
    shade(im, lambda m: m.ellipse((2, 1, 13, 10), fill=255), LEAF, outline=True)
    rng = random.Random(hash(flower) & 0xFFFF)
    petal = [C(h) for h in flower]
    for _ in range(7):
        x, y = rng.randint(4, 11), rng.randint(2, 7)
        im.putpixel((x, y), petal[1])
        im.putpixel((x + 1, y), petal[0])
        im.putpixel((x, y + 1), petal[0])
        im.putpixel((x - 1, y), petal[1])
    return im


def draw_lamp():
    """1x3 zoo lamp: green iron post, glass lantern, paw-print banner."""
    im = canvas(1, 3)
    d = ImageDraw.Draw(im)
    d.rectangle((7, 10, 8, 44), fill=IRON[2])
    d.line((7, 10, 7, 44), fill=IRON[0])
    d.line((8, 10, 8, 44), fill=IRON[3])
    d.rectangle((4, 42, 11, 47), fill=IRON[2], outline=IRON[0])
    d.line((5, 43, 10, 43), fill=IRON[4])
    d.rectangle((5, 34, 10, 36), fill=IRON[2], outline=IRON[0])
    # lantern
    d.polygon([(3, 3), (12, 3), (10, 0), (5, 0)], fill=IRON[2], outline=IRON[0])
    d.rectangle((4, 4, 11, 10), fill=C("#ffe89a"), outline=IRON[0])
    d.line((5, 5, 5, 9), fill=(255, 255, 230, 255))
    d.line((7, 4, 7, 10), fill=IRON[1])
    d.rectangle((5, 10, 10, 11), fill=IRON[1])
    # banner
    d.line((9, 14, 14, 14), fill=IRON[0])
    d.polygon([(9, 15), (14, 15), (14, 26), (11, 23), (9, 26)], fill=C("#2b8f3e"), outline=C("#14532d"))
    for x, y in ((11, 18), (12, 20), (10, 20), (11, 21), (12, 21)):
        im.putpixel((x, y), C("#f3e4a0"))
    return im


def draw_bin(recycle=False):
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    body = [C(h) for h in (("#10301f", "#1d5e3a", "#2b7c4a", "#45a065", "#7cc890") if not recycle else
                           ("#0f2440", "#1d4a7a", "#2b65a0", "#4a8ac8", "#8cc0ec"))]
    shade(im, lambda m: m.rectangle((3, 4, 12, 15), fill=255), body)
    for x in (5, 8, 11):
        d.line((x, 6, x, 14), fill=body[1])
    d.rectangle((2, 2, 13, 5), fill=body[2], outline=body[0])
    d.line((3, 3, 12, 3), fill=body[4])
    d.rectangle((6, 0, 9, 2), fill=body[1], outline=body[0])
    if recycle:
        d.polygon([(7, 8), (10, 13), (5, 13)], outline=(255, 255, 255, 255))
    else:
        for x, y in ((6, 9), (9, 9), (7, 11), (8, 11), (7, 12), (8, 12), (5, 10), (10, 10)):
            im.putpixel((x, y), C("#f3e4a0"))
    return im


def draw_cart(kind):
    """2x2 food cart: canopy row (Front) + cart body with wheels (Buildings)."""
    im = canvas(2, 2)
    d = ImageDraw.Draw(im)
    if kind == "snack":
        stripe_a, stripe_b = C("#f0c23a"), RED[2]
        body = [RED[0], RED[1], RED[2], RED[3], C("#f6a07a")]
    else:
        stripe_a, stripe_b = C("#f7c6d9"), C("#ffffff")
        body = [C(h) for h in ("#3a2a4a", "#6a8fd0", "#9ec5f0", "#c8e2fb", "#eef7ff")]
    # poles
    d.line((4, 8, 4, 22), fill=IRON[0])
    d.line((27, 8, 27, 22), fill=IRON[0])
    # canopy
    px = im.load()
    for y in range(2, 10):
        for x in range(32):
            if abs(x - 15.5) <= 13 + (y - 2) * 0.35:
                px[x, y] = stripe_a if (x // 4) % 2 == 0 else stripe_b
    for i in range(8):
        cx = 2 + i * 4
        d.pieslice((cx - 2, 7, cx + 2, 12), 0, 180, fill=stripe_a if i % 2 == 0 else stripe_b, outline=INK)
    d.polygon([(2, 2), (29, 2), (31, 9), (0, 9)], outline=INK)
    d.line((3, 3, 28, 3), fill=(255, 255, 255, 140))
    # goods on the counter
    if kind == "snack":
        for x0 in (8, 15, 21):
            d.rectangle((x0, 13, x0 + 4, 19), fill=CREAM, outline=INK)
            d.line((x0 + 2, 13, x0 + 2, 19), fill=RED[2])
            for k in range(3):
                im.putpixel((x0 + 1 + k, 12), C("#fff6c8"))
                im.putpixel((x0 + k, 11 + k % 2), C("#ffe58a"))
    else:
        for x0, scoop in ((8, "#f7c6d9"), (15, "#c8f0d0"), (22, "#fff1b8")):
            d.polygon([(x0, 15), (x0 + 4, 15), (x0 + 2, 20)], fill=C("#d9a05a"), outline=INK)
            d.ellipse((x0 - 1, 11, x0 + 5, 16), fill=C(scoop), outline=INK)
            im.putpixel((x0 + 1, 12), (255, 255, 255, 255))
    # body
    shade(im, lambda m: m.rectangle((1, 19, 30, 28), fill=255), body)
    d.rectangle((1, 19, 30, 20), fill=body[4] if kind != "snack" else C("#f6ead0"))
    d.line((1, 19, 30, 19), fill=INK)
    if kind == "snack":
        d.rectangle((9, 22, 22, 26), fill=CREAM, outline=INK)
        for k in range(4):
            im.putpixel((11 + k * 3, 24), C("#f0c23a"))
            im.putpixel((11 + k * 3, 23), C("#fff6c8"))
    else:
        d.polygon([(14, 21), (18, 21), (16, 27)], fill=C("#d9a05a"), outline=INK)
        d.ellipse((13, 19, 19, 23), fill=C("#f7c6d9"), outline=INK)
    for cx in (7, 24):
        d.ellipse((cx - 3, 25, cx + 3, 31), fill=IRON[1], outline=IRON[0])
        im.putpixel((cx, 28), IRON[4])
    return im


def draw_balloons():
    im = canvas(1, 2)
    d = ImageDraw.Draw(im)
    cols = [("#9e2a1e", "#d8452f", "#ff9a80"), ("#1d4a7a", "#3a86c8", "#a9dcf0"),
            ("#a07a10", "#f0c23a", "#fff1b0"), ("#8a3a6a", "#e070b0", "#ffc6e8")]
    spots = [(1, 2), (8, 0), (4, 7), (10, 6)]
    for (x, y), (dk, md, hi) in zip(spots, cols):
        d.line((x + 2, y + 6, 8, 22), fill=(80, 70, 70, 255))
    for (x, y), (dk, md, hi) in zip(spots, cols):
        d.ellipse((x, y, x + 5, y + 6), fill=C(md), outline=C(dk))
        im.putpixel((x + 1, y + 1), C(hi))
        im.putpixel((x + 2, y + 7), C(dk))
    # vendor cart post
    d.rectangle((5, 22, 11, 29), fill=WOOD[3], outline=INK)
    d.line((6, 23, 10, 23), fill=WOOD[5])
    d.ellipse((4, 27, 8, 31), fill=IRON[1], outline=IRON[0])
    d.ellipse((9, 27, 13, 31), fill=IRON[1], outline=IRON[0])
    return im


def draw_signpost(left, right):
    im = canvas(1, 2)
    d = ImageDraw.Draw(im)
    d.rectangle((7, 4, 9, 30), fill=WOOD[2], outline=INK)
    d.line((8, 5, 8, 29), fill=WOOD[4])
    d.rectangle((5, 29, 11, 31), fill=WOOD[1], outline=INK)
    # upper board points left, lower points right
    d.polygon([(0, 8), (3, 4), (15, 4), (15, 12), (3, 12)], fill=WOOD[4], outline=INK)
    d.line((4, 5, 14, 5), fill=WOOD[5])
    icon(im, 6, 5, left)
    d.polygon([(0, 15), (12, 15), (15, 19), (12, 23), (0, 23)], fill=WOOD[4], outline=INK)
    d.line((1, 16, 11, 16), fill=WOOD[5])
    icon(im, 3, 16, right)
    return im


def draw_plaque(biome):
    """Standing info plaque: coloured header, icon, text lines, two legs."""
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    for x in (3, 11):
        d.rectangle((x, 9, x + 1, 15), fill=WOOD[2], outline=INK)
    d.rectangle((0, 0, 15, 11), fill=WOOD[3], outline=INK)
    d.rectangle((1, 1, 14, 10), fill=BIOME_COLOR[biome])
    d.rectangle((1, 1, 14, 2), fill=WOOD[5])
    icon(im, 2, 3, biome)
    for y in (4, 6, 8):
        d.line((10, y, 13, y), fill=darker(BIOME_COLOR[biome], 0.55))
    return im


def draw_arch():
    """4x3 entrance arch: green ZOO sign with paw prints over two log posts."""
    im = canvas(4, 3)
    d = ImageDraw.Draw(im)
    for x0 in (3, 54):
        d.rectangle((x0, 8, x0 + 6, 47), fill=WOOD[2], outline=INK)
        d.line((x0 + 1, 9, x0 + 1, 46), fill=WOOD[4])
        d.line((x0 + 4, 9, x0 + 4, 46), fill=WOOD[1])
        for y in range(14, 46, 7):
            d.line((x0 + 1, y, x0 + 5, y), fill=WOOD[1])
    # vines on posts
    for x0 in (3, 54):
        for y in range(16, 44, 5):
            im.putpixel((x0 + (y // 5) % 5 + 1, y), LEAF[4])
            im.putpixel((x0 + (y // 5) % 5 + 1, y + 1), LEAF[2])
    d.rectangle((0, 6, 63, 22), fill=JLEAF[3], outline=INK)
    d.rectangle((2, 8, 61, 20), fill=JLEAF[2])
    d.line((2, 8, 61, 8), fill=JLEAF[4])
    # big ZOO letters (5px wide strokes)
    gold = GOLD
    d.rectangle((18, 9, 26, 10), fill=gold[2])
    d.rectangle((18, 17, 26, 18), fill=gold[2])
    d.line((18, 9, 26, 9), fill=gold[3])
    for k in range(6):
        d.rectangle((24 - k, 11 + k, 25 - k, 11 + k), fill=gold[2])
    for i, ch in enumerate("OO", start=1):
        x0 = 18 + i * 10
        for r, row in enumerate(FONT[ch]):
            for c, bit in enumerate(row):
                if bit == "1":
                    d.rectangle((x0 + c * 3, 9 + r * 2, x0 + c * 3 + 2, 10 + r * 2), fill=gold[2])
                    im.putpixel((x0 + c * 3, 9 + r * 2), gold[3])
    for cx in (8, 56):
        d.ellipse((cx - 2, 12, cx + 2, 16), fill=CREAM)
        for dx, dy in ((-3, 10), (-1, 9), (1, 9), (3, 10)):
            im.putpixel((cx + dx, dy), CREAM)
    # leafy trim on top
    for x in range(0, 64, 4):
        shade(im, lambda m, x=x: m.ellipse((x - 1, 2 + (x // 4) % 2, x + 4, 8), fill=255), LEAF)
    for x in (10, 30, 50):
        im.putpixel((x, 3), C("#f7c6d9"))
        im.putpixel((x + 1, 4), C("#ff8ab0"))
    return im


# ---------------------------------------------------------------------------
# pen props and ground decals (decals are composited onto Back tiles)
# ---------------------------------------------------------------------------

def draw_igloo():
    im = canvas(2, 2)
    d = ImageDraw.Draw(im)
    shade(im, lambda m: m.pieslice((1, 4, 30, 50), 180, 360, fill=255), SNOW)
    d.rectangle((1, 26, 30, 28), fill=SNOW[2])
    d.line((1, 28, 30, 28), fill=SNOW[0])
    for y in (11, 17, 23):
        d.line((4, y, 27, y), fill=SNOW[1])
    for y, off in ((8, 0), (14, 3), (20, 0), (25, 3)):
        for x in range(4 + off, 28, 6):
            d.line((x, y, x, y + 2), fill=SNOW[1])
    d.pieslice((10, 14, 21, 38), 180, 360, fill=C("#1e2a3a"), outline=SNOW[0])
    d.line((11, 26, 20, 26), fill=C("#1e2a3a"))
    d.rectangle((11, 22, 20, 26), fill=C("#1e2a3a"))
    d.arc((9, 13, 22, 38), 180, 360, fill=SNOW[4])
    d.line((2, 29, 29, 29), fill=(90, 130, 170, 90))
    return im


def draw_ice_block():
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    d.polygon([(2, 6), (8, 2), (14, 5), (14, 12), (8, 15), (2, 12)], fill=ICE[2], outline=ICE[0])
    d.polygon([(2, 6), (8, 2), (14, 5), (8, 8)], fill=ICE[4])
    d.line((8, 8, 8, 14), fill=ICE[1])
    d.line((9, 9, 13, 7), fill=ICE[3])
    im.putpixel((6, 4), (255, 255, 255, 255))
    return im


def draw_snow_drift():
    im = canvas(1, 1)
    shade(im, lambda m: (m.ellipse((0, 7, 10, 14), fill=255), m.ellipse((6, 5, 15, 13), fill=255)), SNOW)
    return im


def draw_ice_crack():
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    d.line((2, 3, 6, 7), fill=ICE[1])
    d.line((6, 7, 5, 12), fill=ICE[1])
    d.line((6, 7, 12, 8), fill=ICE[1])
    d.line((12, 8, 14, 5), fill=ICE[1])
    d.line((3, 3, 7, 7), fill=ICE[4])
    d.line((7, 8, 12, 9), fill=ICE[4])
    return im


def draw_icy_rock():
    im = canvas(1, 1)
    shade(im, lambda m: m.ellipse((1, 4, 14, 15), fill=255), ROCK)
    shade(im, lambda m: m.chord((2, 3, 13, 11), 180, 360, fill=255), SNOW, outline=False)
    d = ImageDraw.Draw(im)
    d.arc((1, 3, 14, 11), 180, 360, fill=SNOW[0])
    for x, h in ((4, 2), (8, 3), (11, 2)):
        d.line((x, 7, x, 7 + h), fill=ICE[3])
    return im


def draw_lily(flower):
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    d.pieslice((2, 4, 13, 13), 20, 340, fill=LEAF[4], outline=LEAF[1])
    d.line((8, 8, 12, 8), fill=LEAF[2])
    d.arc((3, 5, 12, 12), 200, 300, fill=LEAF[5])
    if flower:
        for dx, dy in ((0, -2), (-2, 0), (2, 0), (0, 0), (-1, -1), (1, -1)):
            im.putpixel((6 + dx, 8 + dy), C("#ffb3cf"))
        im.putpixel((6, 6), C("#ff6fa5"))
        im.putpixel((6, 8), C("#ffe58a"))
    return im


def draw_reeds():
    """1x2 cattails: tall leaves + brown heads on top tile, base leaves on bottom tile."""
    im = canvas(1, 2)
    d = ImageDraw.Draw(im)
    rng = random.Random(3)
    for x0, top in ((3, 6), (6, 2), (9, 5), (12, 9), (5, 11), (10, 12)):
        lean = rng.choice((-1, 0, 1))
        d.line((x0, 30, x0 + lean, top), fill=LEAF[2])
        d.line((x0 + 1, 30, x0 + 1 + lean, top + 2), fill=LEAF[4])
    for x0, y0 in ((6, 3), (9, 6), (3, 8)):
        d.rectangle((x0, y0, x0 + 1, y0 + 5), fill=C("#6b3a1f"), outline=C("#3a1d0a"))
        im.putpixel((x0, y0 + 1), C("#9a5a2c"))
    d.line((2, 31, 14, 31), fill=(30, 60, 50, 110))
    return im


def draw_water_rock(big=False):
    im = canvas(2 if big else 1, 1)
    w = 32 if big else 16
    shade(im, lambda m: m.ellipse((1, 4, w - 2, 14), fill=255), ROCK)
    d = ImageDraw.Draw(im)
    d.arc((0, 10, w - 1, 16), 0, 180, fill=WATER[4])
    d.line((4, 6, 8, 5), fill=ROCK[5])
    return im


def draw_tuft(seed, ramp=DRYG):
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    cx = rng.randint(5, 10)
    for i in range(7):
        x = cx + rng.randint(-4, 4)
        top = rng.randint(3, 8)
        lean = rng.choice((-2, -1, 1, 2))
        d.line((x, 14, x + lean, top), fill=ramp[1 + i % 3])
        im.putpixel((x + lean, top), ramp[5])
    d.line((cx - 4, 14, cx + 4, 14), fill=ramp[1])
    return im


def draw_termite():
    im = canvas(1, 2)
    shade(im, lambda m: m.polygon([(3, 31), (5, 14), (7, 3), (9, 2), (11, 12), (13, 31)], fill=255), EARTH)
    shade(im, lambda m: m.polygon([(10, 31), (11, 22), (13, 18), (15, 24), (15, 31)], fill=255), EARTH)
    d = ImageDraw.Draw(im)
    for x, y in ((7, 12), (9, 20), (6, 25), (12, 26)):
        d.ellipse((x, y, x + 1, y + 1), fill=EARTH[0])
    d.line((1, 31, 15, 31), fill=(60, 30, 10, 120))
    return im


def draw_acacia():
    """4x4: flat umbrella canopy (rows 0-1), forked trunk (row 2), root base (row 3)."""
    im = canvas(4, 4)
    d = ImageDraw.Draw(im)
    for x0, x1, top in ((32, 18, 22), (32, 46, 20), (32, 30, 18)):
        d.line((x0, 63, x1, top), fill=DWOOD[1], width=3)
    shade(im, lambda m: m.polygon([(29, 63), (30, 44), (31, 34), (34, 34), (35, 44), (36, 63)], fill=255), DWOOD)
    shade(im, lambda m: m.polygon([(31, 38), (19, 22), (22, 20), (33, 34)], fill=255), DWOOD)
    shade(im, lambda m: m.polygon([(33, 38), (45, 20), (48, 22), (35, 36)], fill=255), DWOOD)
    canopy = [C(h) for h in ("#1d3a12", "#3b5e1a", "#5a7e22", "#7c9a2e", "#a3b84a", "#c8d470")]
    for box in ((2, 6, 34, 22), (24, 2, 62, 20), (12, 1, 44, 14), (8, 10, 30, 24), (36, 9, 60, 24)):
        shade(im, lambda m, b=box: m.ellipse(b, fill=255), canopy)
    d.line((6, 23, 58, 23), fill=canopy[0])
    rng = random.Random(5)
    for _ in range(40):
        x, y = rng.randint(6, 58), rng.randint(4, 19)
        if im.getpixel((x, y))[3] and im.getpixel((x, y)) != canopy[0]:
            im.putpixel((x, y), canopy[5] if y < 10 else canopy[2])
    d.ellipse((24, 60, 41, 64), fill=(40, 30, 10, 70))
    return im


def draw_savanna_rock():
    im = canvas(1, 1)
    ramp = [C(h) for h in ("#3a2418", "#6e4a36", "#94684a", "#b8896a", "#d8b090")]
    shade(im, lambda m: m.ellipse((1, 5, 14, 15), fill=255), ramp)
    shade(im, lambda m: m.ellipse((8, 9, 15, 15), fill=255), ramp)
    return im


def draw_leaf_litter(seed):
    im = canvas(1, 1)
    rng = random.Random(seed)
    cols = [C("#8a5a1f"), C("#b0702a"), C("#6e8a2a"), C("#c98a3a"), C("#4f6e1f")]
    for _ in range(6):
        x, y = rng.randint(1, 12), rng.randint(2, 13)
        c = rng.choice(cols)
        d = ImageDraw.Draw(im)
        d.ellipse((x, y, x + 3, y + 2), fill=c)
        im.putpixel((x + 1, y + 1), darker(c, 0.6))
    return im


def draw_vine():
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    pts = [(0, 10), (3, 8), (6, 10), (9, 7), (12, 9), (15, 6)]
    d.line(pts, fill=JLEAF[1], width=1)
    for x, y in pts[1:-1]:
        d.ellipse((x - 1, y - 3, x + 1, y - 1), fill=JLEAF[4], outline=JLEAF[1])
    return im


def draw_hanging_vine():
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    for x0, length in ((3, 12), (8, 15), (12, 9)):
        d.line((x0, 0, x0 + (1 if x0 % 2 else 0), length), fill=JLEAF[1])
        for y in range(2, length, 3):
            im.putpixel((x0 + 1, y), JLEAF[4])
            im.putpixel((x0 - 1, y + 1), JLEAF[3])
    return im


def draw_tropical_flower():
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    shade(im, lambda m: m.ellipse((2, 6, 13, 15), fill=255), JLEAF)
    for cx, cy, col in ((6, 8, "#ff5a3a"), (10, 11, "#ffb02e")):
        for dx, dy in ((0, -2), (-2, 0), (2, 0), (0, 2)):
            d.ellipse((cx + dx - 1, cy + dy - 1, cx + dx + 1, cy + dy + 1), fill=C(col))
        im.putpixel((cx, cy), C("#fff1b8"))
    return im


def draw_moss():
    im = canvas(1, 1)
    rng = random.Random(11)
    for _ in range(22):
        x, y = rng.randint(1, 14), rng.randint(3, 14)
        im.putpixel((x, y), rng.choice([C("#7ccf3a"), C("#5fb92f"), C("#a7e04a")]))
        if x < 14:
            im.putpixel((x + 1, y), C("#3f9a2a"))
    return im


def draw_mushrooms():
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    for x, y, cap in ((3, 8, RED), (9, 5, [C("#3a1d0a"), C("#7a4e30"), C("#a8703f"), C("#c9925a")]), (10, 11, RED)):
        d.rectangle((x + 1, y + 2, x + 2, y + 5), fill=CREAM, outline=BONE[1])
        d.pieslice((x - 1, y - 1, x + 4, y + 4), 180, 360, fill=cap[2], outline=cap[0])
        im.putpixel((x + 1, y), (255, 255, 255, 255))
    return im


def draw_log():
    im = canvas(2, 1)
    d = ImageDraw.Draw(im)
    shade(im, lambda m: m.rounded_rectangle((1, 5, 28, 14), 4, fill=255), DWOOD)
    d.ellipse((24, 5, 31, 14), fill=DWOOD[4], outline=DWOOD[0])
    d.ellipse((26, 7, 29, 12), outline=DWOOD[2])
    for x in range(4, 24, 5):
        d.line((x, 8, x + 3, 8), fill=DWOOD[2])
    for x in range(3, 20, 2):
        im.putpixel((x, 5), C("#7ccf3a"))
        im.putpixel((x + 1, 6), C("#5fb92f"))
    d.pieslice((14, 1, 19, 7), 180, 360, fill=RED[2], outline=RED[0])
    d.line((16, 4, 16, 6), fill=CREAM)
    return im


def draw_stump():
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    shade(im, lambda m: m.rectangle((3, 6, 12, 14), fill=255), DWOOD)
    d.ellipse((3, 3, 12, 8), fill=WOOD[4], outline=DWOOD[0])
    d.ellipse((5, 4, 10, 7), outline=WOOD[3])
    d.line((2, 14, 13, 14), fill=DWOOD[0])
    return im


def draw_snag():
    """1x3 dead tree perch: broken top, a side branch for owls, root flare base."""
    im = canvas(1, 3)
    d = ImageDraw.Draw(im)
    shade(im, lambda m: m.polygon([(5, 47), (6, 8), (8, 4), (10, 7), (11, 47)], fill=255), DWOOD)
    shade(im, lambda m: m.polygon([(9, 18), (15, 13), (15, 15), (10, 21)], fill=255), DWOOD)
    shade(im, lambda m: m.polygon([(6, 26), (1, 22), (1, 24), (6, 29)], fill=255), DWOOD)
    shade(im, lambda m: m.polygon([(2, 47), (5, 40), (11, 40), (14, 47)], fill=255), DWOOD)
    d.ellipse((7, 22, 9, 26), fill=C("#120a06"))
    for y in (12, 31, 38):
        im.putpixel((7, y), C("#5fb92f"))
        im.putpixel((8, y + 1), C("#7ccf3a"))
    return im


def draw_volcanic_rock(seed):
    im = canvas(1, 1)
    rng = random.Random(seed)
    shade(im, lambda m: m.polygon([(1, 14), (3, 6), (7, 3), (12, 5), (14, 14)], fill=255), BASALT)
    d = ImageDraw.Draw(im)
    x = rng.randint(5, 9)
    d.line((x, 6, x + 2, 10), fill=C("#ff7a1a"))
    d.line((x + 2, 10, x + 1, 13), fill=C("#c2410c"))
    im.putpixel((x, 6), C("#ffd27a"))
    return im


def draw_skull():
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    shade(im, lambda m: (m.ellipse((2, 4, 11, 12), fill=255), m.rectangle((8, 8, 14, 12), fill=255)), BONE)
    d.ellipse((5, 6, 7, 8), fill=BONE[0])
    for x in (9, 11, 13):
        d.line((x, 12, x, 13), fill=BONE[3])
    return im


def draw_ribcage():
    im = canvas(2, 1)
    d = ImageDraw.Draw(im)
    d.line((2, 7, 30, 7), fill=BONE[0], width=3)
    d.line((2, 7, 30, 7), fill=BONE[3])
    for x in range(6, 28, 4):
        d.arc((x - 3, 4, x + 3, 15), 180, 360, fill=BONE[0])
        d.line((x - 2, 8, x - 3, 13), fill=BONE[2])
        d.line((x + 2, 8, x + 3, 13), fill=BONE[2])
        im.putpixel((x, 7), BONE[1])
    return im


def draw_bone():
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    d.line((4, 11, 11, 5), fill=BONE[3], width=2)
    for x, y in ((3, 10), (4, 12), (11, 4), (12, 6)):
        d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=BONE[3])
    outline_alpha(im, BONE[0])
    return im


def draw_cracked_earth_decal():
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    for seg in (((1, 4), (5, 6), (8, 4), (13, 6)), ((5, 6), (6, 11), (3, 14)), ((8, 4), (10, 9), (14, 12))):
        d.line(seg, fill=C("#4a3020"))
    return im


def draw_giant_fern():
    """2x2 prehistoric fern: big arching fronds."""
    im = canvas(2, 2)
    d = ImageDraw.Draw(im)
    fern = [C(h) for h in ("#0e2e14", "#1f5a24", "#2f7a2c", "#4f9e34", "#7cc24a", "#a8de6a")]
    for ang in (-150, -125, -100, -80, -55, -30):
        a = math.radians(ang)
        pts = []
        for t in range(0, 17):
            r = t * 1.0
            x = 16 + r * math.cos(a)
            y = 30 + r * math.sin(a) + (t * t) * 0.045
            pts.append((x, y))
        d.line(pts, fill=fern[1], width=1)
        for i, (x, y) in enumerate(pts[2::2]):
            ln = 4 - i // 3
            nx, ny = -math.sin(a), math.cos(a)
            for s in (-1, 1):
                d.line((x, y, x + s * nx * ln + math.cos(a), y + s * ny * ln + 1), fill=fern[3 + (i % 2)])
    d.ellipse((12, 27, 20, 31), fill=fern[0])
    return im


def vent_frames():
    frames = []
    for f in range(4):
        im = canvas(1, 2)
        d = ImageDraw.Draw(im)
        shade(im, lambda m: m.ellipse((1, 22, 14, 31), fill=255), BASALT)
        d.ellipse((5, 24, 10, 28), fill=C("#ff7a1a"), outline=C("#7a1f08"))
        im.putpixel((7, 25), C("#ffe08a"))
        for k in range(3):
            y = 20 - ((f * 5 + k * 7) % 20)
            x = 7 + int(2 * math.sin((y + k * 3) / 3))
            r = 2 + (20 - y) // 7
            alpha = max(70, 210 - (20 - y) * 7)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(235, 235, 240, alpha))
        frames.append(im)
    return frames


def draw_jungle_pond_plant():
    return draw_tuft(41, LEAF)


# ---------------------------------------------------------------------------
# terrain textures
# ---------------------------------------------------------------------------

def remap(tile, ramp):
    """Recolour a vanilla tile by luminance rank onto a new ramp (keeps its texture)."""
    tile = tile.convert("RGBA")
    cols = sorted({p[:3] for p in tile.getdata() if p[3]}, key=lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2])
    lut = {}
    for i, c in enumerate(cols):
        t = i / max(1, len(cols) - 1)
        lut[c] = ramp[min(len(ramp) - 1, int(t * len(ramp)))]
    out = Image.new("RGBA", tile.size)
    out.putdata([lut[p[:3]] if p[3] else p for p in tile.getdata()])
    return out


def paving_texture(seed, warm=True):
    """Light warm cobble: offset rows of rounded stones with soft mortar."""
    rng = random.Random(seed)
    if warm:
        mortar, stones = C("#b99a72"), [C("#ecd6ae"), C("#e4cb9e"), C("#f0dcb8"), C("#e0c496")]
        hi, lo = C("#faecd0"), C("#cdb088")
    else:
        mortar, stones = C("#b47a58"), [C("#e0a882"), C("#d8996f"), C("#e6b090"), C("#d49a78")]
        hi, lo = C("#f2c8a8"), C("#bb805e")
    im = Image.new("RGBA", (16, 16), mortar)
    px = im.load()
    rows = ((0, 5, 0), (5, 5, 4), (10, 6, 2))
    for y0, h, off in rows:
        x = -off
        while x < 16:
            w = rng.choice((5, 6, 6, 7)) if warm else 8
            col = rng.choice(stones)
            for yy in range(y0, y0 + h - 1):
                for xx in range(x, x + w - 1):
                    cx = xx % 16
                    corner = (xx in (x, x + w - 2)) and (yy in (y0, y0 + h - 2))
                    if corner:
                        continue
                    c = col
                    if yy == y0 or xx == x:
                        c = hi
                    elif yy == y0 + h - 2 or xx == x + w - 2:
                        c = lo
                    px[cx, yy] = c
            x += w
    return im


def snow_texture(seed):
    rng = random.Random(seed)
    im = Image.new("RGBA", (16, 16), C("#f2f9ff"))
    px = im.load()
    for _ in range(10):
        x, y = rng.randrange(16), rng.randrange(16)
        for dx in range(rng.randint(2, 4)):
            px[(x + dx) % 16, y] = C("#dfecf7")
    for _ in range(4):
        px[rng.randrange(16), rng.randrange(16)] = C("#c9dcec")
    for _ in range(4):
        px[rng.randrange(16), rng.randrange(16)] = (255, 255, 255, 255)
    return im


def ice_texture(seed):
    rng = random.Random(seed)
    im = Image.new("RGBA", (16, 16), C("#bfe6f4"))
    px = im.load()
    for k in range(3):
        x0 = rng.randrange(16)
        for t in range(6):
            px[(x0 + t) % 16, (k * 5 + t) % 16] = C("#e4f8fe")
    for _ in range(6):
        px[rng.randrange(16), rng.randrange(16)] = C("#a3d6ec")
    return im


def cracked_texture(seed):
    rng = random.Random(seed)
    im = Image.new("RGBA", (16, 16), C("#c9a47a"))
    px = im.load()
    for _ in range(14):
        px[rng.randrange(16), rng.randrange(16)] = C("#d8b88e")
    d = ImageDraw.Draw(im)
    a = (rng.randint(0, 4), 0)
    b = (rng.randint(5, 10), rng.randint(5, 9))
    c = (15, rng.randint(9, 14))
    d.line((a, b, c), fill=C("#7a5636"))
    d.line((b, (rng.randint(0, 5), 15)), fill=C("#7a5636"))
    return im


# ---------------------------------------------------------------------------
# the sheet
# ---------------------------------------------------------------------------

VANILLA = {
    "outdoors": ("spring_outdoorsTileSheet.png", 25),
    "winter": ("winter_outdoorsTileSheet.png", 25),
    "island": ("island_tilesheet_1.png", 32),
    "town": ("spring_town.png", 32),
}


class ZooSheet:
    def __init__(self):
        self.frames = {}       # id -> list[Image]
        self.images = []       # flat list of 16x16 tiles
        self.anims = {}        # id -> (frame ids, ms)
        self.objects = {}      # name -> grid of ids
        self._dedupe = {}
        self.vanilla = {k: Image.open(MAPS / f).convert("RGBA") for k, (f, _) in VANILLA.items()}
        self.vanilla_anims = {}

    # --- registration ---
    def add(self, frames, ms=600, dedupe=True):
        key = b"".join(f.tobytes() for f in frames) + bytes([len(frames)])
        if dedupe and key in self._dedupe:
            return self._dedupe[key]
        ids = []
        for f in frames:
            ids.append(len(self.images))
            self.images.append(f)
        self.frames[ids[0]] = frames
        if len(frames) > 1:
            self.anims[ids[0]] = (ids, ms)
        if dedupe:
            self._dedupe[key] = ids[0]
        return ids[0]

    def add_object(self, name, img, ms=600):
        frames = img if isinstance(img, list) else [img]
        w, h = frames[0].width // TS, frames[0].height // TS
        grid = []
        for r in range(h):
            row = []
            for c in range(w):
                box = (c * TS, r * TS, c * TS + TS, r * TS + TS)
                tiles = [f.crop(box) for f in frames]
                if all(t.getbbox() is None for t in tiles):
                    row.append(None)
                else:
                    row.append(self.add(tiles, ms, dedupe=False))
            grid.append(row)
        self.objects[name] = grid
        return grid

    # --- component access ---
    def vanilla_tile(self, kind, tid):
        img = self.vanilla[kind]
        cols = VANILLA[kind][1]
        return img.crop(((tid % cols) * TS, (tid // cols) * TS, (tid % cols) * TS + TS, (tid // cols) * TS + TS))

    def comp_frames(self, comp):
        kind, tid = comp
        if kind == "zoo":
            return self.frames[tid]
        seq = self.vanilla_anims.get((kind, tid), [tid])
        return [self.vanilla_tile(kind, t) for t in seq]

    def composite(self, comps):
        lists = [self.comp_frames(c) for c in comps]
        n = max(len(f) for f in lists)
        out = []
        for k in range(n):
            base = Image.new("RGBA", (TS, TS), (0, 0, 0, 0))
            for fl in lists:
                base.alpha_composite(fl[k % len(fl)])
            out.append(base)
        return ("zoo", self.add(out))

    # --- output ---
    def image(self):
        rows = (len(self.images) + COLS - 1) // COLS
        sheet = Image.new("RGBA", (COLS * TS, rows * TS), (0, 0, 0, 0))
        for i, t in enumerate(self.images):
            sheet.paste(t, ((i % COLS) * TS, (i // COLS) * TS))
        return sheet

    def save(self, path=OUT):
        sheet = self.image()
        path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(path)
        return sheet


def build_objects(zs: ZooSheet):
    """Register every hand-drawn object. Names are what make_map places."""
    zs.add_object("booth", draw_booth())
    zs.add_object("board", draw_board())
    zs.add_object("studio", draw_studio())
    zs.add_object("speaker", draw_speaker())
    zs.add_object("mic", draw_mic())
    zs.add_object("fountain", fountain_frames(), ms=180)
    zs.add_object("bench", draw_bench())
    for name, flower in (("planter_red", ("#c23b22", "#ff8a6a")), ("planter_yellow", ("#c98a16", "#ffe58a")),
                         ("planter_pink", ("#b0407a", "#ffb3cf")), ("planter_blue", ("#3a5fc8", "#a9c8ff"))):
        zs.add_object(name, draw_planter(flower))
    zs.add_object("lamp", draw_lamp())
    zs.add_object("bin", draw_bin())
    zs.add_object("bin_recycle", draw_bin(True))
    zs.add_object("snack_cart", draw_cart("snack"))
    zs.add_object("icecream_cart", draw_cart("icecream"))
    zs.add_object("balloons", draw_balloons())
    for left, right in (("Ice", "Water"), ("Savanna", "Jungle"), ("Forest", "Prehistoric")):
        zs.add_object(f"sign_{left}_{right}", draw_signpost(left, right))
    for biome in ("Ice", "Water", "Savanna", "Jungle", "Forest", "Prehistoric"):
        zs.add_object(f"plaque_{biome}", draw_plaque(biome))
    zs.add_object("arch", draw_arch())
    # pen props / decals
    zs.add_object("igloo", draw_igloo())
    zs.add_object("ice_block", draw_ice_block())
    zs.add_object("snow_drift", draw_snow_drift())
    zs.add_object("ice_crack", draw_ice_crack())
    zs.add_object("icy_rock", draw_icy_rock())
    zs.add_object("lily", draw_lily(False))
    zs.add_object("lily_flower", draw_lily(True))
    zs.add_object("reeds", draw_reeds())
    zs.add_object("water_rock", draw_water_rock())
    zs.add_object("basking_rock", draw_water_rock(True))
    zs.add_object("tuft_a", draw_tuft(1))
    zs.add_object("tuft_b", draw_tuft(2))
    zs.add_object("termite", draw_termite())
    zs.add_object("acacia", draw_acacia())
    zs.add_object("savanna_rock", draw_savanna_rock())
    zs.add_object("litter_a", draw_leaf_litter(1))
    zs.add_object("litter_b", draw_leaf_litter(2))
    zs.add_object("vine", draw_vine())
    zs.add_object("hanging_vine", draw_hanging_vine())
    zs.add_object("tropical_flower", draw_tropical_flower())
    zs.add_object("moss", draw_moss())
    zs.add_object("mushrooms", draw_mushrooms())
    zs.add_object("log", draw_log())
    zs.add_object("stump", draw_stump())
    zs.add_object("snag", draw_snag())
    zs.add_object("volcanic_rock_a", draw_volcanic_rock(1))
    zs.add_object("volcanic_rock_b", draw_volcanic_rock(2))
    zs.add_object("skull", draw_skull())
    zs.add_object("ribcage", draw_ribcage())
    zs.add_object("bone", draw_bone())
    zs.add_object("cracks", draw_cracked_earth_decal())
    zs.add_object("giant_fern", draw_giant_fern())
    zs.add_object("vent", vent_frames(), ms=220)
    zs.add_object("grass_tuft", draw_tuft(41, LEAF))


# ---------------------------------------------------------------------------
# terrain blending
# ---------------------------------------------------------------------------

# low -> high priority; a higher terrain is drawn over lower ones.
PRIORITY = "gkyrmscvnihwpq"
WATERY = set("hw")
GRASSY = set("gky")
SOILS = set("rmscdv")
AMP = {"g": 0, "k": 0.17, "y": 0.17, "r": 0.1, "m": 0.12, "s": 0.08, "c": 0.06, "v": 0.08,
       "n": 0.1, "i": 0.05, "h": 0.07, "w": 0.06, "p": 0.015, "q": 0.0}


def prio(t):
    return PRIORITY.index(t)


def field_noise(x, y):
    return 0.6 * hnoise(x // 2, y // 2, 1) + 0.4 * hnoise(x, y, 2)


class TerrainBlender:
    """Corner-based terrain tiles: vanilla textures where they exist, custom ones otherwise."""

    WATER_FRAMES = [1229, 1230, 1231, 1306]

    def __init__(self, zs: ZooSheet):
        self.zs = zs
        out = lambda t: zs.vanilla_tile("outdoors", t)
        dirt = [out(226), out(227), out(176)]
        grass = [out(175), out(150), out(175)]
        self.tex = {
            "g": [out(175)],
            "k": [out(351)],
            "y": [remap(t, DRYG[1:]) for t in grass],
            "r": [remap(t, [C(h) for h in ("#a8673e", "#bd7c4e", "#cc8c5a", "#d89c6a")]) for t in dirt],
            "m": [remap(t, [C(h) for h in ("#4f3520", "#5e4028", "#6e4c30", "#7d5838")]) for t in dirt],
            "s": [remap(t, [C(h) for h in ("#d9c08a", "#e4cd98", "#ecd8a8", "#f4e6bc")]) for t in dirt],
            "c": [cracked_texture(s) for s in (1, 2, 3)],
            "v": [remap(t, [C(h) for h in ("#2e262b", "#3a3036", "#463b42", "#54474f")]) for t in dirt],
            "n": [snow_texture(s) for s in (1, 2, 3)],
            "i": [ice_texture(s) for s in (1, 2)],
            "p": [paving_texture(s) for s in (1, 2, 3)],
            "q": [paving_texture(s, warm=False) for s in (4, 5)],
        }
        water = [out(t) for t in self.WATER_FRAMES]
        self.water = water
        shelf = C("#86d8c6")
        self.shallow = []
        for f in water:
            im = Image.new("RGBA", (16, 16))
            im.putdata([mix(p, shelf, 0.45) if p[3] else p for p in f.getdata()])
            for x, y in ((3, 4), (4, 4), (11, 9), (7, 13), (8, 13), (13, 2)):
                im.putpixel((x, y), C("#cfc28e"))
            self.shallow.append(im)
        # vanilla full-tile variants
        self.full_vanilla = {
            "g": [175] * 10 + [150] * 3 + [151, 152],
            "k": [351] * 6 + [329, 380, 304, 300],
            "w": [1229] * 8 + [1274, 1322, 1249, 1324],
        }
        self.full_zoo = {}
        for t in "yrmscvnipq":
            self.full_zoo[t] = [zs.add([img]) for img in self.tex[t]]
        self.full_zoo["h"] = [zs.add(self.shallow, ms=600)]
        self.cache = {}

    def texel(self, t, x, y, frame):
        if t == "w":
            return self.water[frame % 4].getpixel((x, y))
        if t == "h":
            return self.shallow[frame % 4].getpixel((x, y))
        return self.tex[t][0].getpixel((x, y))

    def style(self, T, U, dist, c, frame):
        pT, pU = prio(T), prio(U)
        if T == "p" and U != "q":
            if dist <= 1:
                return C("#8a6a48")
            if dist <= 2.3:
                return C("#f4e2bc")
            if dist <= 3:
                return C("#c9a77c")
            return c
        if T == "q" and U == "p":
            if dist <= 1:
                return C("#8e5a3c")
            if dist <= 2:
                return C("#e6c8a0")
            return c
        if U in "pq" and T not in "pq":
            return darker(c, 0.68) if dist <= 1 else (darker(c, 0.86) if dist <= 2 else c)
        if T in WATERY and U not in WATERY:
            if dist <= 1:
                return WATER[5] if frame % 2 == 0 else WATER[4]
            if dist <= 2:
                return mix(c, WATER[4], 0.5 if frame % 2 else 0.25)
            return c
        if T not in WATERY and U in WATERY:
            if dist <= 1:
                return C("#5b3a1e") if T not in "ni" else C("#6f9fc0")
            if dist <= 2:
                return darker(c, 0.75)
            return c
        if T == "w" and U == "h" and dist <= 1:
            return mix(c, self.texel("h", 0, 0, frame), 0.4)
        if T == "n" and U != "n" and pT > pU:
            return C("#b9cfe2") if dist <= 1 else (C("#dceaf5") if dist <= 2 else c)
        if T == "i" and U == "n":
            return C("#6fa8cc") if dist <= 1 else (C("#e9fbff") if dist <= 2 else c)
        if T == "v" and dist <= 1:
            return C("#1c1619")
        if T in SOILS and U in GRASSY and dist <= 1:
            return darker(c, 0.78)
        if T in GRASSY and U in SOILS and pU > pT and dist <= 1:
            return darker(c, 0.82)
        if T in "ky" and U in GRASSY and pT > pU and dist <= 1:
            return darker(c, 0.85)
        return c

    def full(self, t, rng):
        if t in self.full_vanilla:
            return ("outdoors", rng.choice(self.full_vanilla[t]))
        return ("zoo", rng.choice(self.full_zoo[t]))

    def tile(self, corners, rng):
        if len(set(corners)) == 1:
            return self.full(corners[0], rng)
        if corners in self.cache:
            return self.cache[corners]
        animated = any(c in WATERY for c in corners)
        frames = [self._gen(corners, f) for f in range(4 if animated else 1)]
        comp = ("zoo", self.zs.add(frames, ms=600))
        self.cache[corners] = comp
        return comp

    def _gen(self, corners, frame):
        M = 3
        N = TS + 2 * M
        present = sorted(set(corners), key=prio)
        terr = [[present[0]] * N for _ in range(N)]
        for L in present[1:]:
            ind = [1.0 if prio(c) >= prio(L) else 0.0 for c in corners]
            amp = AMP[L]
            for j in range(N):
                for i in range(N):
                    px, py = i - M, j - M
                    u, v = (px + 0.5) / TS, (py + 0.5) / TS
                    f = (ind[0] * (1 - u) * (1 - v) + ind[1] * u * (1 - v)
                         + ind[2] * (1 - u) * v + ind[3] * u * v)
                    f += amp * field_noise(px % TS, py % TS)
                    if f > 0.5:
                        terr[j][i] = L
        img = Image.new("RGBA", (TS, TS))
        p = img.load()
        for py in range(TS):
            for px in range(TS):
                T = terr[py + M][px + M]
                c = self.texel(T, px, py, frame)
                best = None
                for dy in range(-M, M + 1):
                    for dx in range(-M, M + 1):
                        dist = math.hypot(dx, dy)
                        if dist > 3.2 or (dx == 0 and dy == 0):
                            continue
                        U = terr[py + M + dy][px + M + dx]
                        if U != T and (best is None or dist < best[0]):
                            best = (dist, U)
                if best:
                    c = self.style(T, best[1], best[0], c, frame)
                p[px, py] = c
        return img


def save_preview(zs: ZooSheet, path=PREVIEW, max_side=512):
    sheet = zs.image()
    scale = max(1, min(max_side // sheet.width, max_side // sheet.height))
    out = sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST)
    if max(out.size) > max_side:
        f = max_side / max(out.size)
        out = out.resize((int(out.width * f), int(out.height * f)), Image.NEAREST)
    bg = Image.new("RGBA", out.size, (60, 120, 50, 255))
    bg.alpha_composite(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    bg.save(path)
    return path


def main():
    zs = ZooSheet()
    build_objects(zs)
    path = save_preview(zs, Path("/tmp/zoo_art/tiles_preview.png"))
    print(f"{len(zs.images)} hand-drawn tiles; preview {path}")


if __name__ == "__main__":
    main()
