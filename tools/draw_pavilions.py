"""Hand-drawn art for the walk-in pavilions: park facades, interior shells (walls + frame),
exhibit railings, walkway floors and exhibit decor. Registered into the shared ZooSheet
by build_pavilion_objects(); make_pavilions.py places them.
"""

import math
import random

from PIL import Image, ImageChops, ImageDraw

from draw_tiles import (BASALT, BONE, C, DWOOD, FONT, GLASS, GOLD, ICE, INK, IRON, JLEAF, LEAF, ROCK, SNOW, TS,
                        WOOD, canvas, darker, hnoise, icon, mix, shade)

FONT.update({
    "D": ("110", "101", "101", "101", "110"), "F": ("111", "100", "110", "100", "100"),
    "G": ("111", "100", "101", "101", "111"), "H": ("101", "101", "111", "101", "101"),
    "L": ("100", "100", "100", "100", "111"), "M": ("101", "111", "111", "101", "101"),
    "N": ("101", "111", "111", "111", "101"), "P": ("110", "101", "110", "100", "100"),
    "Q": ("010", "101", "101", "111", "011"), "U": ("101", "101", "101", "101", "111"),
})

VOID = C("#100c0e")
OCEAN = [C(h) for h in ("#0b2a4a", "#154a78", "#2069a0", "#2f86b8", "#4aa3d8", "#8fd0f0")]
NAVY = [C(h) for h in ("#0c1a33", "#1a3360", "#264c8a", "#3a6fb8", "#5a94d8", "#9cc6f0")]
SAND = [C(h) for h in ("#6a4a2a", "#a8865a", "#c9a882", "#dcc29c", "#efdcbc")]
STONE = [C(h) for h in ("#2a201c", "#4a3a30", "#6a5444", "#86705a", "#a8907a", "#cbb59c")]
WHITE = [C(h) for h in ("#5a6a78", "#a9b8c4", "#d8e2ea", "#f2f6fa", "#ffffff")]
LAVA = [C(h) for h in ("#5a0c04", "#a8260a", "#e8540f", "#ff8a1a", "#ffc24a", "#fff0a0")]
BRICK = [C(h) for h in ("#3a1a12", "#7a3626", "#a0482e", "#c0603e")]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def text_width(s, scale=1, gap=1):
    return sum(2 * scale if ch == " " else (3 + gap) * scale for ch in s) - gap * scale


def big_text(img, x, y, s, color, scale=2, gap=1, shadow=None):
    d = ImageDraw.Draw(img)
    for pass_, col, off in ((0, shadow, 1), (1, color, 0)):
        if col is None:
            continue
        cx = x
        for ch in s:
            if ch == " ":
                cx += 2 * scale
                continue
            for r, row in enumerate(FONT[ch]):
                for c, bit in enumerate(row):
                    if bit == "1":
                        px, py = cx + c * scale + off, y + r * scale + off
                        d.rectangle((px, py, px + scale - 1, py + scale - 1), fill=col)
            cx += (3 + gap) * scale


def centered_text(img, cx, y, s, color, scale=2, shadow=None):
    big_text(img, cx - text_width(s, scale) // 2, y, s, color, scale, shadow=shadow)


def vgrad(img, box, top, bottom, mask=None):
    x0, y0, x1, y1 = box
    px = img.load()
    for y in range(y0, y1 + 1):
        t = (y - y0) / max(1, y1 - y0)
        col = mix(top, bottom, t)
        for x in range(x0, x1 + 1):
            if mask is None or mask.getpixel((x, y)):
                px[x, y] = col


def masked(img, mask, draw_fn):
    """Draw on a scratch layer and keep only the pixels inside mask."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer), layer)
    alpha = ImageChops.multiply(layer.getchannel("A"), mask)
    layer.putalpha(alpha)
    img.alpha_composite(layer)


def make_mask(size, fn):
    m = Image.new("L", size, 0)
    fn(ImageDraw.Draw(m))
    return m


def fish(d, x, y, body, fin, flip=False, size=1):
    w, h = 6 * size, 3 * size
    if flip:
        d.ellipse((x, y, x + w, y + h), fill=body, outline=darker(body, 0.5))
        d.polygon([(x + w, y + h // 2), (x + w + 3 * size, y - size), (x + w + 3 * size, y + h + size)], fill=fin)
        d.point((x + 1 + size, y + 1), fill=INK)
    else:
        d.ellipse((x, y, x + w, y + h), fill=body, outline=darker(body, 0.5))
        d.polygon([(x, y + h // 2), (x - 3 * size, y - size), (x - 3 * size, y + h + size)], fill=fin)
        d.point((x + w - 1 - size, y + 1), fill=INK)


def icicles(d, x0, x1, y, rng, ramp=ICE, max_len=7):
    x = x0
    while x < x1:
        ln = rng.randint(2, max_len)
        d.polygon([(x, y), (x + 2, y), (x + 1, y + ln)], fill=ramp[3], outline=ramp[1])
        d.point((x, y), fill=ramp[4])
        x += rng.randint(3, 5)


def snowflake(img, x, y, col):
    for dx, dy in ((0, -2), (0, -1), (0, 0), (0, 1), (0, 2), (-2, 0), (-1, 0), (1, 0), (2, 0), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        if 0 <= x + dx < img.width and 0 <= y + dy < img.height:
            img.putpixel((x + dx, y + dy), col)


def penguin_icon(d, x, y):
    d.ellipse((x, y, x + 7, y + 10), fill=INK)
    d.ellipse((x + 2, y + 3, x + 5, y + 10), fill=(255, 255, 255, 255))
    d.point((x + 3, y + 2), fill=(255, 255, 255, 255))
    d.line((x + 3, y + 3, x + 4, y + 3), fill=C("#f0a020"))
    d.line((x + 1, y + 11, x + 6, y + 11), fill=C("#f0a020"))


def dino_skull(img, cx, cy, ramp=BONE, s=1):
    d = ImageDraw.Draw(img)
    shade(img, lambda m: (m.ellipse((cx - 7 * s, cy - 5 * s, cx + 3 * s, cy + 3 * s), fill=255),
                          m.polygon([(cx, cy - 3 * s), (cx + 10 * s, cy - 1 * s), (cx + 10 * s, cy + 3 * s), (cx, cy + 4 * s)], fill=255)), ramp)
    d.ellipse((cx - 4 * s, cy - 3 * s, cx - 1 * s, cy), fill=ramp[0])
    for k in range(4):
        d.line((cx + (2 + 2 * k) * s, cy + 3 * s, cx + (2 + 2 * k) * s, cy + 5 * s), fill=ramp[3])
    d.line((cx, cy + 4 * s, cx + 9 * s, cy + 4 * s), fill=ramp[0])


def skeleton(img, box, ramp=BONE):
    """Side-on fossil skeleton (spine, ribs, legs, tail, skull) inside box."""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    w, h = x1 - x0, y1 - y0
    spine = [(x0 + int(w * t), y0 + int(h * (0.45 - 0.18 * math.sin(t * math.pi * 1.1)))) for t in [i / 10 for i in range(11)]]
    d.line(spine, fill=ramp[3], width=2)
    for i in range(3, 8):
        x, y = spine[i]
        d.line((x, y, x - 1, y + h // 3), fill=ramp[2])
    for i in (3, 7):
        x, y = spine[i]
        d.line((x, y + 2, x + 1, y1 - 1), fill=ramp[3], width=2)
    hx, hy = spine[-1]
    d.ellipse((hx - 3, hy - 4, hx + 5, hy + 2), fill=ramp[3], outline=ramp[0])
    d.point((hx + 1, hy - 2), fill=ramp[0])


def ammonite(img, cx, cy, r, ramp=SAND):
    d = ImageDraw.Draw(img)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ramp[3], outline=ramp[0])
    for k in range(1, 4):
        rr = r * (1 - k * 0.25)
        d.arc((cx - rr, cy - rr, cx + rr, cy + rr), 30 * k, 30 * k + 300, fill=ramp[1])
    for a in range(0, 360, 40):
        x = cx + math.cos(math.radians(a)) * r * 0.9
        y = cy + math.sin(math.radians(a)) * r * 0.9
        d.line((cx + (x - cx) * 0.7, cy + (y - cy) * 0.7, x, y), fill=ramp[2])


# ---------------------------------------------------------------------------
# park facades (w x h tiles; the bottom-centre tile is the walkable door)
# ---------------------------------------------------------------------------

DOME = [C("#3d6f96"), C("#8fb8d8"), C("#b9d6ec"), C("#d9ebf7"), C("#f1f8fd"), C("#ffffff")]


def bricks(img, mask, y0, y1, row_h, brick_w, line, hi):
    def fn(d, _):
        for i, y in enumerate(range(y0, y1, row_h)):
            d.line((0, y, img.width, y), fill=line)
            d.line((0, y + 1, img.width, y + 1), fill=hi)
            off = (brick_w // 2) * (i % 2)
            for x in range(off, img.width, brick_w):
                d.line((x, y, x, y + row_h), fill=line)
    masked(img, mask, fn)


def draw_facade_ice(w, h):
    W, H = w * TS, h * TS
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = W // 2
    rng = random.Random(7)
    base = H - 9
    # snow ground under the hall
    shade(im, lambda m: m.ellipse((0, base - 6, W - 1, H + 10), fill=255), SNOW, outline=False)
    # dome
    dome = make_mask(im.size, lambda m: m.pieslice((4, 10, W - 5, 10 + 2 * (base - 10)), 180, 360, fill=255))
    shade(im, lambda m: m.pieslice((4, 10, W - 5, 10 + 2 * (base - 10)), 180, 360, fill=255), DOME)
    bricks(im, dome, 22, base, 11, 20, DOME[1], DOME[4])
    d.line((5, base, W - 6, base), fill=DOME[0])
    # snow cap on top of the dome
    shade(im, lambda m: m.chord((26, 9, W - 27, 40), 180, 360, fill=255), SNOW, outline=False)
    d.arc((26, 9, W - 27, 40), 180, 360, fill=DOME[0])
    icicles(d, 30, W - 30, 25, rng, max_len=5)
    # portholes with a penguin peeking out
    for wx in (26, W - 27):
        d.ellipse((wx - 10, 62, wx + 10, 82), fill=DOME[1], outline=DOME[0])
        d.ellipse((wx - 7, 65, wx + 7, 79), fill=GLASS[1], outline=DOME[0])
        d.line((wx - 4, 67, wx - 1, 67), fill=GLASS[3])
        d.point((wx - 5, 68), fill=GLASS[3])
    penguin_icon(d, 22, 67)
    # entrance tunnel
    tunnel = (cx - 30, 66, cx + 30, 66 + 2 * (base - 66))
    tmask = make_mask(im.size, lambda m: m.pieslice(tunnel, 180, 360, fill=255))
    shade(im, lambda m: m.pieslice(tunnel, 180, 360, fill=255), DOME, light=(-0.3, -0.9))
    bricks(im, tmask, 76, base, 10, 14, DOME[1], DOME[4])
    d.arc(tunnel, 180, 360, fill=DOME[0])
    # door arch (extends into the walkable door tile)
    d.pieslice((cx - 12, 86, cx + 12, 110), 180, 360, fill=C("#1e2a3a"))
    d.rectangle((cx - 12, 98, cx + 12, H - 1), fill=C("#1e2a3a"))
    d.arc((cx - 13, 85, cx + 13, 111), 180, 360, fill=DOME[5])
    d.line((cx - 13, 98, cx - 13, H - 1), fill=DOME[0])
    d.line((cx + 13, 98, cx + 13, H - 1), fill=DOME[0])
    d.rectangle((cx - 11, H - 5, cx + 11, H - 1), fill=C("#2e4a66"))
    # icicles under the tunnel rim
    icicles(d, cx - 22, cx + 22, 72, rng, max_len=6)
    # name sign
    d.rectangle((cx - 24, 44, cx + 24, 60), fill=NAVY[3], outline=NAVY[0])
    d.line((cx - 23, 45, cx + 23, 45), fill=NAVY[5])
    centered_text(im, cx, 48, "ICE", (255, 255, 255, 255), 2, shadow=NAVY[1])
    snowflake(im, cx - 18, 52, ICE[4])
    snowflake(im, cx + 18, 52, ICE[4])
    # flag
    d.line((cx, 0, cx, 12), fill=IRON[1])
    d.polygon([(cx + 1, 1), (cx + 10, 4), (cx + 1, 7)], fill=C("#4aa3d8"), outline=NAVY[1])
    # snow drifts at the base corners
    for x in (2, W - 30):
        shade(im, lambda m, x=x: m.ellipse((x, base - 4, x + 28, H - 2), fill=255), SNOW)
    for x in (18, W - 22):
        d.polygon([(x, base + 1), (x + 4, base - 9), (x + 8, base + 1)], fill=ICE[3], outline=ICE[0])
    return im


def draw_facade_water(w, h):
    W, H = w * TS, h * TS
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = W // 2
    rng = random.Random(9)
    # plinth
    d.rectangle((3, H - 12, W - 4, H - 1), fill=ROCK[3], outline=ROCK[0])
    for x in range(10, W - 4, 14):
        d.line((x, H - 11, x, H - 2), fill=ROCK[2])
    d.line((4, H - 11, W - 5, H - 11), fill=ROCK[5])
    # wall body
    body = (6, 40, W - 7, H - 12)
    vgrad(im, body, C("#6ab4e4"), C("#2f78b8"))
    d.rectangle(body, outline=NAVY[0])
    # wave band
    for x in range(8, W - 8):
        y = H - 22 + round(2 * math.sin(x / 4))
        d.point((x, y), fill=(255, 255, 255, 255))
        d.point((x, y + 1), fill=C("#a9dcf0"))
    # roof with a wavy foam edge
    d.rectangle((1, 14, W - 2, 30), fill=NAVY[2], outline=NAVY[0])
    for x in range(1, W - 1):
        yb = 38 + round(3 * math.sin(x / 6))
        d.line((x, 30, x, yb), fill=NAVY[2])
        d.point((x, yb), fill=NAVY[0])
        d.point((x, yb - 1), fill=(255, 255, 255, 255) if (x // 6) % 2 == 0 else C("#cfefff"))
    d.line((2, 15, W - 3, 15), fill=NAVY[5])
    centered_text(im, cx, 19, "AQUARIUM", (255, 255, 255, 255), 2, shadow=NAVY[0])
    # fish emblem on the roof
    shade(im, lambda m: m.ellipse((cx - 14, 1, cx + 8, 13), fill=255), [C("#7a2a08"), C("#d8541a"), C("#f07a2a"), C("#ff9a4a"), C("#ffc080")])
    d.polygon([(cx + 7, 7), (cx + 16, 0), (cx + 16, 14)], fill=C("#f07a2a"), outline=C("#7a2a08"))
    d.ellipse((cx - 10, 4, cx - 7, 7), fill=(255, 255, 255, 255))
    d.point((cx - 9, 5), fill=INK)
    for x in (cx - 4, cx, cx + 4):
        d.line((x, 3, x, 11), fill=C("#ffd6a0"))
    # big aquarium windows
    for x0 in (13, W - 67):
        box = (x0, 50, x0 + 53, 104)
        d.rectangle((box[0] - 2, box[1] - 2, box[2] + 2, box[3] + 2), fill=NAVY[1], outline=NAVY[0])
        vgrad(im, box, OCEAN[4], OCEAN[1])
        for k in range(4):
            kx = box[0] + 6 + k * 13
            pts = [(kx + round(2 * math.sin(y / 5 + k)), y) for y in range(box[3], box[3] - rng.randint(16, 36), -1)]
            d.line(pts, fill=C("#2f9a4a"), width=2)
            for x, y in pts[::5]:
                d.point((x + 2, y), fill=C("#5fd06a"))
        d.rectangle((box[0], box[3] - 4, box[2], box[3]), fill=SAND[3])
        for fx, fy, col, fl in ((box[0] + 10, 62, C("#ffb02e"), False), (box[0] + 32, 74, C("#ff6a8a"), True),
                                (box[0] + 18, 88, C("#ffe050"), True), (box[0] + 40, 58, C("#9af0ff"), False)):
            fish(d, fx, fy, col, darker(col, 0.8), flip=fl)
        for k in range(6):
            bx, by = box[0] + rng.randint(3, 50), box[1] + rng.randint(3, 45)
            d.ellipse((bx, by, bx + 2, by + 2), outline=(230, 250, 255, 255))
        d.line((box[0] + 3, box[1] + 14, box[0] + 14, box[1] + 3), fill=(255, 255, 255, 140), width=2)
        d.line((box[0] + 26, box[1], box[0] + 26, box[3]), fill=NAVY[1], width=2)
    # entrance with glass double doors
    d.rectangle((cx - 15, 60, cx + 15, H - 1), fill=NAVY[1], outline=NAVY[0])
    d.pieslice((cx - 15, 46, cx + 15, 76), 180, 360, fill=NAVY[1], outline=NAVY[0])
    d.pieslice((cx - 11, 52, cx + 11, 72), 180, 360, fill=GLASS[2])
    for a in range(200, 360, 30):
        d.line((cx, 62, cx + 11 * math.cos(math.radians(a)), 62 + 10 * math.sin(math.radians(a))), fill=NAVY[1])
    vgrad(im, (cx - 11, 64, cx + 11, H - 2), GLASS[2], GLASS[0])
    d.line((cx, 64, cx, H - 1), fill=NAVY[0])
    d.line((cx - 9, 68, cx - 4, 80), fill=GLASS[3])
    d.line((cx + 3, 68, cx + 8, 80), fill=GLASS[3])
    for x in (cx - 3, cx + 2):
        d.rectangle((x, 90, x + 1, 96), fill=GOLD[2])
    d.rectangle((cx - 13, H - 4, cx + 13, H - 1), fill=ROCK[4])
    return im


def draw_facade_jungle(w, h):
    W, H = w * TS, h * TS
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = W // 2
    rng = random.Random(13)
    # brick plinth
    d.rectangle((4, H - 18, W - 5, H - 1), fill=BRICK[2], outline=BRICK[0])
    for i, y in enumerate(range(H - 17, H - 1, 4)):
        d.line((5, y, W - 6, y), fill=BRICK[1])
        for x in range(5 + (i % 2) * 4, W - 5, 8):
            d.line((x, y, x, y + 3), fill=BRICK[1])
    d.rectangle((3, H - 20, W - 4, H - 17), fill=WHITE[3], outline=WHITE[0])
    # glass house silhouette: walls + gabled roof
    roof = [(4, 52), (cx, 6), (W - 5, 52)]
    glass = make_mask(im.size, lambda m: (m.polygon(roof, fill=255), m.rectangle((8, 50, W - 9, H - 20), fill=255)))
    vgrad(im, (0, 6, W - 1, H - 20), C("#bfe8f6"), C("#7fbcd8"), mask=glass)

    # plants behind the glass
    def plants(dd, layer):
        for k in range(7):
            px_ = 14 + k * 24 + rng.randint(-4, 4)
            top = rng.randint(40, 70)
            dd.line((px_, H - 20, px_ + rng.randint(-3, 3), top), fill=DWOOD[3], width=2)
            for a in range(0, 360, 45):
                ln = rng.randint(10, 16)
                ex = px_ + ln * math.cos(math.radians(a))
                ey = top + ln * 0.6 * math.sin(math.radians(a)) + 4
                dd.line((px_, top, ex, ey), fill=JLEAF[3], width=3)
                dd.line((px_, top, ex, ey), fill=JLEAF[5], width=1)
        for k in range(14):
            bx, by = rng.randint(8, W - 20), rng.randint(76, H - 34)
            dd.ellipse((bx, by, bx + rng.randint(10, 18), by + rng.randint(8, 14)), fill=JLEAF[rng.randint(2, 4)], outline=JLEAF[1])
        for k in range(8):
            fx, fy = rng.randint(12, W - 12), rng.randint(80, H - 26)
            dd.ellipse((fx, fy, fx + 3, fy + 3), fill=C("#ff5a3a") if k % 2 else C("#ffb02e"))
    masked(im, glass, plants)
    # glass tint + reflections
    tint = Image.new("RGBA", im.size, (200, 236, 250, 70))
    tint.putalpha(ImageChops.multiply(tint.getchannel("A"), glass))
    im.alpha_composite(tint)

    def frames(dd, layer):
        for x in range(8, W - 8, 16):
            dd.line((x, 0, x, H), fill=WHITE[4], width=2)
            dd.line((x + 2, 0, x + 2, H), fill=WHITE[1])
        for y in (50, 72, 94, 116 - 20 + 6):
            dd.line((0, y, W, y), fill=WHITE[4], width=2)
            dd.line((0, y + 2, W, y + 2), fill=WHITE[1])
        for x in range(14, W - 8, 22):
            dd.line((x, 60, x + 8, 52), fill=(255, 255, 255, 150))
            dd.line((x + 3, 86, x + 11, 78), fill=(255, 255, 255, 110))
    masked(im, glass, frames)
    # roof rafters and ridge
    for t in [i / 6 for i in range(1, 6)]:
        d.line((cx, 6, 4 + (W - 9) * t, 52), fill=WHITE[3])
    d.line(roof, fill=WHITE[4], width=3)
    d.line([(p[0], p[1] + 2) for p in roof], fill=WHITE[1])
    d.line((8, 50, 8, H - 20), fill=WHITE[4], width=3)
    d.line((W - 9, 50, W - 9, H - 20), fill=WHITE[4], width=3)
    d.rectangle((cx - 3, 0, cx + 3, 7), fill=WHITE[4], outline=WHITE[0])
    # door
    d.rectangle((cx - 12, 82, cx + 12, H - 1), fill=WHITE[4], outline=WHITE[0])
    vgrad(im, (cx - 9, 85, cx + 9, H - 3), C("#5fb06a"), C("#1d5e26"))
    d.line((cx, 85, cx, H - 1), fill=WHITE[4], width=2)
    d.line((cx - 7, 88, cx - 3, 96), fill=(255, 255, 255, 150))
    for x in (cx - 3, cx + 2):
        d.rectangle((x, 102, x + 1, 107), fill=GOLD[2])
    d.rectangle((cx - 13, H - 3, cx + 13, H - 1), fill=STONE[4])
    # name sign
    d.rectangle((cx - 32, 64, cx + 32, 78), fill=JLEAF[2], outline=JLEAF[0])
    d.line((cx - 31, 65, cx + 31, 65), fill=JLEAF[5])
    centered_text(im, cx, 67, "TROPICS", C("#fff1b8"), 2, shadow=JLEAF[0])
    # vines on the frame + potted ferns by the door
    for x in (10, W - 11):
        for y in range(54, H - 22, 3):
            d.point((x + round(2 * math.sin(y / 4)), y), fill=JLEAF[4])
    for x in (cx - 30, cx + 18):
        d.rectangle((x, H - 12, x + 11, H - 1), fill=C("#b0603a"), outline=BRICK[0])
        shade(im, lambda m, x=x: m.ellipse((x - 3, H - 26, x + 14, H - 10), fill=255), LEAF)
    return im


def draw_facade_prehistoric(w, h):
    W, H = w * TS, h * TS
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = W // 2
    # steps
    for k, y in enumerate((H - 8, H - 4)):
        d.rectangle((6 - k * 3, y, W - 7 + k * 3, y + 3), fill=SAND[3 - k], outline=SAND[0])
    # wall
    wall = (10, 30, W - 11, H - 8)
    d.rectangle(wall, fill=STONE[3], outline=STONE[0])
    wmask = make_mask(im.size, lambda m: m.rectangle((wall[0] + 1, wall[1] + 1, wall[2] - 1, wall[3] - 1), fill=255))
    bricks(im, wmask, 34, H - 8, 7, 18, STONE[2], STONE[4])
    # pediment with a dinosaur skull
    ped = [(4, 24), (cx, 0), (W - 5, 24)]
    d.polygon(ped, fill=SAND[3], outline=SAND[0])
    d.polygon([(18, 22), (cx, 4), (W - 19, 22)], fill=SAND[2], outline=SAND[1])
    dino_skull(im, cx - 4, 15, BONE, 1)
    # frieze with the name
    d.rectangle((2, 22, W - 3, 33), fill=SAND[4], outline=SAND[0])
    d.line((3, 23, W - 4, 23), fill=(255, 250, 235, 255))
    centered_text(im, cx, 24, "FOSSILS", STONE[1], 2, shadow=SAND[2])
    # columns
    for x in (16, 44, W - 56, W - 28):
        shade(im, lambda m, x=x: m.rectangle((x, 36, x + 11, H - 9), fill=255), [SAND[0], SAND[1], SAND[2], SAND[3], SAND[4]],
              light=(-1, 0))
        d.rectangle((x - 2, 33, x + 13, 37), fill=SAND[4], outline=SAND[0])
        d.rectangle((x - 2, H - 11, x + 13, H - 8), fill=SAND[3], outline=SAND[0])
        for k in (3, 6, 9):
            d.line((x + k, 39, x + k, H - 12), fill=SAND[2])
    # doorway
    d.rectangle((cx - 13, 40, cx + 13, H - 1), fill=SAND[4], outline=SAND[0])
    d.pieslice((cx - 10, 42, cx + 10, 62), 180, 360, fill=C("#24140c"))
    d.rectangle((cx - 10, 52, cx + 10, H - 1), fill=C("#24140c"))
    d.rectangle((cx - 10, H - 5, cx + 10, H - 1), fill=C("#4a2a1a"))
    for k in range(5):
        a = math.radians(190 + k * 40)
        d.ellipse((cx + 12 * math.cos(a) - 1, 52 + 11 * math.sin(a) - 1, cx + 12 * math.cos(a) + 2, 52 + 11 * math.sin(a) + 2),
                  fill=BONE[3], outline=BONE[0])
    # lava glow from inside
    for y in range(56, H - 5):
        a = int(90 * (y - 56) / (H - 61))
        d.line((cx - 9, y, cx + 9, y), fill=(255, 120, 30, a))
    # volcanic boulders at the corners
    for x0, flip in ((0, False), (W - 22, True)):
        shade(im, lambda m, x0=x0: m.polygon([(x0, H - 1), (x0 + 3, H - 18), (x0 + 11, H - 26), (x0 + 19, H - 16), (x0 + 22, H - 1)], fill=255), BASALT)
        lx = x0 + 11
        d.line((lx, H - 22, lx - 3, H - 12), fill=LAVA[3])
        d.line((lx - 3, H - 12, lx + 2, H - 4), fill=LAVA[2])
        d.point((lx, H - 21), fill=LAVA[5])
        for k in range(3):
            d.ellipse((lx - 2 + k * 3, H - 34 - k * 5, lx + 3 + k * 3, H - 29 - k * 5), fill=(225, 225, 230, 150 - k * 30))
    return im


FACADE_ART = {"Ice": draw_facade_ice, "Water": draw_facade_water, "Jungle": draw_facade_jungle,
              "Prehistoric": draw_facade_prehistoric}


# ---------------------------------------------------------------------------
# interior shells: wall cap (row 0), back wall face (rows 1-3), side walls, bottom wall + door
# ---------------------------------------------------------------------------

TRIM = {
    "Ice": [C(h) for h in ("#2a4a66", "#7fb0d4", "#bcdcf0", "#e6f4fc")],
    "Water": [C(h) for h in ("#0c1a33", "#264c8a", "#3a6fb8", "#7aa8e0")],
    "Jungle": [C(h) for h in ("#5a6a78", "#c8d4dc", "#eef3f6", "#ffffff")],
    "Prehistoric": [C(h) for h in ("#2a1a10", "#6a4a30", "#8a6644", "#b08a62")],
}


def wall_ice(im, box, frame, rng):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(im)
    vgrad(im, box, ICE[3], ICE[2])
    mask = make_mask(im.size, lambda m: m.rectangle(box, fill=255))
    bricks(im, mask, y0 + 3, y1 - 4, 9, 22, ICE[1], ICE[4])
    # arched frost windows and info boards
    for k, wx in enumerate(range(x0 + 40, x1 - 30, 88)):
        d.rectangle((wx - 13, y0 + 10, wx + 13, y1 - 8), fill=ICE[1], outline=ICE[0])
        d.pieslice((wx - 13, y0 + 2, wx + 13, y0 + 22), 180, 360, fill=ICE[1], outline=ICE[0])
        vgrad(im, (wx - 10, y0 + 12, wx + 10, y1 - 11), C("#1e3a66"), C("#5a8ec4"))
        d.pieslice((wx - 10, y0 + 5, wx + 10, y0 + 21), 180, 360, fill=C("#1e3a66"))
        for s in range(5):
            snowflake(im, wx - 7 + rng.randint(0, 14), y0 + 9 + rng.randint(0, 22), (255, 255, 255, 255))
        d.line((wx, y0 + 6, wx, y1 - 11), fill=ICE[1])
        bx = wx + 44
        if bx + 14 < x1:
            d.rectangle((bx - 14, y0 + 12, bx + 14, y0 + 34), fill=WOOD[3], outline=INK)
            d.rectangle((bx - 12, y0 + 14, bx + 12, y0 + 32), fill=C("#eaf6fc"))
            penguin_icon(d, bx - 10, y0 + 17)
            for ty in (y0 + 18, y0 + 22, y0 + 26):
                d.line((bx - 1, ty, bx + 9, ty), fill=ICE[0])
    icicles(d, x0, x1, y0, rng, max_len=8)
    d.rectangle((x0, y1 - 4, x1, y1), fill=SNOW[3], outline=SNOW[0])


def wall_water(im, box, frame, rng):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(im)
    vgrad(im, (x0, y0 + 3, x1, y1 - 4), OCEAN[4], OCEAN[1])
    # light rays
    for k in range(x0, x1, 40):
        d.polygon([(k + 10, y0 + 3), (k + 18, y0 + 3), (k + 4, y1 - 4), (k - 4, y1 - 4)], fill=(255, 255, 255, 22))
    d.rectangle((x0, y1 - 9, x1, y1 - 4), fill=SAND[3])
    for x in range(x0, x1, 3):
        d.point((x, y1 - 9 + (x * 7) % 3), fill=SAND[4])
    # kelp, swaying by frame
    krng = random.Random(21)
    for kx in range(x0 + 6, x1 - 4, 11):
        height = krng.randint(18, 36)
        pts = [(kx + round(2 * math.sin(y / 5 + frame * 1.5 + kx)), y) for y in range(y1 - 8, y1 - 8 - height, -1)]
        d.line(pts, fill=C("#1f7a3a"), width=2)
        for x, y in pts[2::4]:
            d.point((x + 2, y), fill=C("#5fd06a"))
            d.point((x - 1, y + 1), fill=C("#3fae4f"))
    # coral
    for cx_ in range(x0 + 20, x1, 57):
        col = C("#ff7a9a") if cx_ % 2 else C("#ffb04a")
        for a in (-40, -10, 20):
            d.line((cx_, y1 - 9, cx_ + round(7 * math.sin(math.radians(a))), y1 - 18), fill=col, width=2)
    # fish swimming (each panel wraps)
    frng = random.Random(33)
    span = x1 - x0 - 20
    for k in range((x1 - x0) // 22):
        col = frng.choice([C("#ffb02e"), C("#ff6a8a"), C("#ffe050"), C("#9af0ff"), C("#ff8a3a"), C("#c8a0ff")])
        flip = frng.random() < 0.5
        speed = frng.choice((3, 4, 5))
        base = frng.randint(0, span)
        fx = x0 + 10 + (base + (-1 if flip else 1) * frame * speed) % span
        fy = y0 + 7 + frng.randint(0, 24)
        fish(d, fx, fy, col, darker(col, 0.8), flip=not flip)
    # bubbles rising
    brng = random.Random(44)
    for k in range((x1 - x0) // 12):
        bx = x0 + brng.randint(2, x1 - x0 - 4)
        by = y1 - 10 - (brng.randint(0, 30) + frame * 4) % 32
        d.ellipse((bx, by, bx + 2, by + 2), outline=(230, 250, 255, 220))
    # tank frames, rim and info screens
    for mx in range(x0, x1 + 1, 64):
        d.rectangle((mx - 2, y0, mx + 1, y1), fill=NAVY[1], outline=NAVY[0])
    d.rectangle((x0, y0, x1, y0 + 3), fill=NAVY[2], outline=NAVY[0])
    d.rectangle((x0, y1 - 4, x1, y1), fill=NAVY[1], outline=NAVY[0])
    for k in range(3):
        d.line((x0 + 8 + k * 64 * 2, y0 + 8, x0 + 20 + k * 128, y0 + 6), fill=(255, 255, 255, 120))


def wall_jungle(im, box, frame, rng):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(im)
    vgrad(im, (x0, y0, x1, y1 - 8), C("#dff4ff"), C("#8fcbe6"))
    # distant foliage seen through the glass
    for k in range(x0, x1, 9):
        top = y1 - 20 - rng.randint(0, 12)
        d.ellipse((k - 4, top, k + 10, y1 - 6), fill=mix(JLEAF[3], C("#8fcbe6"), 0.45))
    for x in range(x0, x1 + 1, 16):
        d.line((x, y0, x, y1 - 8), fill=WHITE[4], width=2)
        d.line((x + 2, y0, x + 2, y1 - 8), fill=WHITE[1])
    for y in (y0 + 2, y0 + 20):
        d.line((x0, y, x1, y), fill=WHITE[4], width=2)
        d.line((x0, y + 2, x1, y + 2), fill=WHITE[1])
    for x in range(x0 + 4, x1, 32):
        d.line((x, y0 + 16, x + 9, y0 + 6), fill=(255, 255, 255, 170))
    # brick baseboard
    d.rectangle((x0, y1 - 8, x1, y1), fill=BRICK[2], outline=BRICK[0])
    for x in range(x0, x1, 8):
        d.line((x, y1 - 7, x, y1 - 4), fill=BRICK[1])
        d.line((x + 4, y1 - 3, x + 4, y1), fill=BRICK[1])
    d.line((x0, y1 - 4, x1, y1 - 4), fill=BRICK[1])
    # big leaves pressed against the glass
    for k in range(x0 + 10, x1, 45):
        for a in (-150, -120, -60, -30):
            ex = k + 16 * math.cos(math.radians(a))
            ey = y1 - 8 + 14 * math.sin(math.radians(a))
            d.line((k, y1 - 8, ex, ey), fill=JLEAF[2], width=4)
            d.line((k, y1 - 8, ex, ey), fill=JLEAF[4], width=1)
    # info boards
    for bx in range(x0 + 70, x1 - 20, 120):
        d.rectangle((bx - 14, y0 + 10, bx + 14, y0 + 32), fill=WOOD[3], outline=INK)
        d.rectangle((bx - 12, y0 + 12, bx + 12, y0 + 30), fill=C("#e8f6d8"))
        icon(im, bx - 10, y0 + 15, "Jungle")
        for ty in (y0 + 16, y0 + 20, y0 + 24):
            d.line((bx - 1, ty, bx + 9, ty), fill=JLEAF[1])


def wall_prehistoric(im, box, frame, rng):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(im)
    vgrad(im, box, STONE[3], STONE[2])
    mask = make_mask(im.size, lambda m: m.rectangle(box, fill=255))
    bricks(im, mask, y0 + 2, y1 - 4, 8, 20, STONE[1], STONE[4])
    # lava cracks glowing in the stone
    for k in range(x0 + 30, x1, 70):
        pts = [(k, y1 - 4), (k - 3, y1 - 14), (k + 2, y1 - 22), (k - 1, y1 - 30)]
        d.line(pts, fill=LAVA[2], width=1)
        d.point(pts[1], fill=LAVA[5])
    # fossil display cases between wall sconces
    kinds = ["skeleton", "ammonite", "skull", "skeleton"]
    for i, fx in enumerate(range(x0 + 34, x1 - 30, 64)):
        kind = kinds[i % len(kinds)]
        d.rectangle((fx - 22, y0 + 6, fx + 22, y1 - 10), fill=GOLD[1], outline=INK)
        d.rectangle((fx - 20, y0 + 8, fx + 20, y1 - 12), fill=SAND[3])
        d.line((fx - 19, y0 + 9, fx + 19, y0 + 9), fill=SAND[4])
        if kind == "skeleton":
            skeleton(im, (fx - 17, y0 + 12, fx + 15, y1 - 15))
        elif kind == "ammonite":
            ammonite(im, fx - 8, y0 + 22, 8)
            ammonite(im, fx + 10, y0 + 26, 5)
        else:
            dino_skull(im, fx - 4, y0 + 22, BONE, 1)
        d.line((fx - 18, y0 + 10, fx - 8, y0 + 20), fill=(255, 255, 255, 90))
        sx = fx + 32
        if sx + 4 < x1:
            d.rectangle((sx - 2, y0 + 20, sx + 2, y0 + 30), fill=IRON[1], outline=IRON[0])
            d.polygon([(sx - 3, y0 + 20), (sx, y0 + 10 + (frame % 2)), (sx + 3, y0 + 20)], fill=LAVA[3], outline=LAVA[1])
            d.point((sx, y0 + 17), fill=LAVA[5])
    d.rectangle((x0, y1 - 4, x1, y1), fill=STONE[1], outline=STONE[0])


WALLS = {"Ice": wall_ice, "Water": wall_water, "Jungle": wall_jungle, "Prehistoric": wall_prehistoric}
SHELL_FRAMES = {"Water": 4, "Prehistoric": 2}


def draw_shell(theme, w, h, frame=0):
    """Full-region wall art; transparent where the floor shows. Door gap at the bottom centre."""
    W, H = w * TS, h * TS
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    t = TRIM[theme]
    WALLS[theme](im, (TS, TS, W - TS - 1, 4 * TS - 1), frame, random.Random(5))
    # wall cap
    d.rectangle((0, 0, W - 1, 15), fill=VOID)
    d.rectangle((6, 6, W - 7, 15), fill=t[2])
    d.line((6, 6, W - 7, 6), fill=t[0])
    d.line((7, 7, W - 8, 7), fill=t[3])
    d.line((16, 15, W - 17, 15), fill=t[0])
    # side walls
    for x_out, x_in in ((0, 15), (W - 1, W - 16)):
        xs = sorted((x_out, x_in))
        d.rectangle((xs[0], 0, xs[1], H - 1), fill=VOID)
        band = (6, 15) if x_out == 0 else (W - 16, W - 7)
        d.rectangle((band[0], 6, band[1], H - 7), fill=t[2])
        edge_out = band[0] if x_out == 0 else band[1]
        edge_in = band[1] if x_out == 0 else band[0]
        d.line((edge_out, 6, edge_out, H - 7), fill=t[0])
        d.line((edge_in, 16, edge_in, H - 17), fill=t[0])
        hi = edge_out + (1 if x_out == 0 else -1)
        d.line((hi, 7, hi, H - 8), fill=t[3])
    # bottom wall with the door gap
    door = (w // 2) * TS
    d.rectangle((0, H - 16, W - 1, H - 1), fill=VOID)
    d.rectangle((6, H - 16, W - 7, H - 7), fill=t[2])
    d.line((6, H - 7, W - 7, H - 7), fill=t[0])
    d.line((16, H - 16, W - 17, H - 16), fill=t[0])
    d.line((7, H - 15, W - 8, H - 15), fill=t[3])
    d.rectangle((door, H - 16, door + 15, H - 1), fill=(0, 0, 0, 0))
    # door threshold: mat + jambs
    d.rectangle((door + 1, H - 16, door + 14, H - 1), fill=t[1])
    d.rectangle((door + 3, H - 15, door + 12, H - 3), fill=darker(t[1], 0.7))
    for y in range(H - 13, H - 4, 3):
        d.line((door + 5, y, door + 10, y), fill=t[3])
    d.polygon([(door + 7, H - 4), (door + 4, H - 8), (door + 11, H - 8)], fill=t[3])
    for jx in (door - 2, door + 16):
        d.rectangle((jx, H - 18, jx + 1, H - 1), fill=t[0])
    # rounded inner corners
    for cxp, cyp in ((16, 16), (W - 17, 16), (16, H - 17), (W - 17, H - 17)):
        d.point((cxp, cyp), fill=t[0])
    return im


# ---------------------------------------------------------------------------
# exhibit railings (one tile per piece)
# ---------------------------------------------------------------------------

def _rail_h(im, theme, x0, x1):
    d = ImageDraw.Draw(im)
    if theme in ("Ice", "Water"):
        frame = WHITE if theme == "Ice" else NAVY
        d.rectangle((x0, 4, x1, 13), fill=(200, 236, 250, 100))
        d.line((x0, 4, x1, 4), fill=frame[3])
        d.line((x0, 5, x1, 5), fill=frame[1])
        d.rectangle((x0, 13, x1, 15), fill=frame[2], outline=frame[0])
        d.line((x0 + 2, 11, x0 + 5, 7), fill=(255, 255, 255, 170))
        if theme == "Ice":
            for x in range(x0, x1, 3):
                d.point((x, 12 - (x % 2)), fill=(255, 255, 255, 200))
    elif theme == "Jungle":
        for y in (6, 10):
            d.rectangle((x0, y, x1, y + 2), fill=C("#c8b04a"), outline=C("#6a5a1a"))
            d.line((x0, y, x1, y), fill=C("#f0e08a"))
        for x in range(x0 + 7, x1, 8):
            d.line((x, 6, x, 12), fill=C("#6a5a1a"))
        d.line((x0, 15, x1, 15), fill=(0, 0, 0, 60))
    else:
        d.rectangle((x0, 7, x1, 15), fill=STONE[3], outline=STONE[0])
        d.rectangle((x0, 5, x1, 8), fill=STONE[4], outline=STONE[0])
        d.line((x0, 6, x1, 6), fill=STONE[5])
        for x in range(x0 + 5, x1, 8):
            d.line((x, 9, x, 14), fill=STONE[2])


def _rail_v(im, theme, y0, y1, x=6):
    d = ImageDraw.Draw(im)
    if theme in ("Ice", "Water"):
        frame = WHITE if theme == "Ice" else NAVY
        d.rectangle((x, y0, x + 3, y1), fill=(200, 236, 250, 120))
        d.line((x, y0, x, y1), fill=frame[3])
        d.line((x + 3, y0, x + 3, y1), fill=frame[0])
    elif theme == "Jungle":
        d.rectangle((x, y0, x + 3, y1), fill=C("#c8b04a"), outline=C("#6a5a1a"))
        d.line((x + 1, y0, x + 1, y1), fill=C("#f0e08a"))
        for y in range(y0 + 6, y1, 8):
            d.line((x, y, x + 3, y), fill=C("#6a5a1a"))
    else:
        d.rectangle((x - 1, y0, x + 4, y1), fill=STONE[4], outline=STONE[0])
        d.line((x, y0, x, y1), fill=STONE[5])


def _post(im, theme, x, y=4):
    d = ImageDraw.Draw(im)
    col = {"Ice": WHITE, "Water": NAVY, "Jungle": [C("#6a5a1a"), C("#a08a30"), C("#c8b04a"), C("#f0e08a")],
           "Prehistoric": STONE}[theme]
    d.rectangle((x, y, x + 3, 15), fill=col[2], outline=col[0])
    d.line((x + 1, y + 1, x + 1, 14), fill=col[3])


def rail_piece(theme, kind, plaque=None):
    im = canvas(1, 1)
    if kind == "T" or kind == "B":
        _rail_h(im, theme, 0, 15)
    elif kind in ("L", "R"):
        _rail_v(im, theme, 0, 15)
    elif kind in ("TL", "BL", "TR", "BR"):
        if kind[1] == "L":
            _rail_h(im, theme, 6, 15)
        else:
            _rail_h(im, theme, 0, 9)
        if kind[0] == "B":
            _rail_v(im, theme, 0, 5)
        else:
            _rail_v(im, theme, 12, 15)
        _post(im, theme, 6)
    if kind in ("T", "B") and plaque is None:
        _post(im, theme, 0)
    if plaque:
        d = ImageDraw.Draw(im)
        d.rectangle((1, 1, 14, 10), fill=WOOD[3], outline=INK)
        d.rectangle((2, 2, 13, 9), fill=(236, 246, 230, 255))
        icon(im, 3, 2, plaque)
        for y in (4, 6):
            d.line((10, y, 12, y), fill=INK)
    return im


# ---------------------------------------------------------------------------
# floors and decor
# ---------------------------------------------------------------------------

def slab_texture(seed, base, mortar, hi, lo, size=8, sparkle=None):
    rng = random.Random(seed)
    im = Image.new("RGBA", (16, 16), mortar)
    px = im.load()
    for sy in range(0, 16, size):
        for sx in range(0, 16, size):
            col = mix(base, hi, rng.uniform(-0.1, 0.25)) if rng.random() < 0.5 else mix(base, lo, rng.uniform(0, 0.3))
            for y in range(sy, sy + size - 1):
                for x in range(sx, sx + size - 1):
                    c = col
                    if y == sy or x == sx:
                        c = mix(col, hi, 0.5)
                    elif y == sy + size - 2 or x == sx + size - 2:
                        c = mix(col, lo, 0.4)
                    px[x, y] = c
    if sparkle:
        for _ in range(2):
            px[rng.randrange(16), rng.randrange(16)] = sparkle
    return im


def floor_textures(zs):
    interior = zs.vanilla_tile("interior", 2109)
    return {
        "a": [slab_texture(s, C("#dcefff"), C("#9cc4dc"), C("#ffffff"), C("#b4d4ea"), sparkle=(255, 255, 255, 255)) for s in (1, 2, 3)],
        "b": [slab_texture(s, C("#4f86ac"), C("#2a4f6a"), C("#7ab0d4"), C("#3a6a8c"), size=16) for s in (4, 5, 6)],
        "e": [interior],
        "f": [slab_texture(s, C("#c9a882"), C("#7a5a3e"), C("#e6ccaa"), C("#a8865e"), size=16) for s in (7, 8, 9)],
    }


def draw_bamboo(seed):
    im = canvas(1, 3)
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    green = [C(h) for h in ("#1f4a14", "#3f7a24", "#6aa83a", "#9ad05a", "#c8ec8a")]
    for x in (2, 7, 11):
        top = rng.randint(0, 8)
        d.rectangle((x, top, x + 2, 46), fill=green[2], outline=green[0])
        d.line((x + 1, top + 1, x + 1, 45), fill=green[3])
        for y in range(top + 6, 46, 7):
            d.line((x, y, x + 2, y), fill=green[0])
            d.point((x + 3, y - 1), fill=green[1])
        for k in range(3):
            ly = top + 4 + k * 9
            dx = 5 if k % 2 else -5
            d.line((x + 1, ly, x + 1 + dx, ly + 3), fill=green[3], width=2)
            d.line((x + 1, ly, x + 1 + dx, ly + 3), fill=green[1])
    d.ellipse((1, 44, 15, 48), fill=(20, 40, 10, 80))
    return im


def snowfall_frames():
    frames = []
    rng = random.Random(3)
    flakes = [(rng.randrange(16), rng.randrange(16), rng.choice((1, 2))) for _ in range(5)]
    for f in range(4):
        im = canvas(1, 1)
        for x, y, s in flakes:
            yy = (y + f * 4 * s // 1) % 16
            xx = (x + (f % 2)) % 16
            im.putpixel((xx, yy), (255, 255, 255, 230))
            if s == 2 and yy + 1 < 16:
                im.putpixel((xx, yy + 1), (230, 245, 255, 160))
        frames.append(im)
    return frames


def lava_frames():
    frames = []
    for f in range(4):
        im = canvas(2, 1)
        d = ImageDraw.Draw(im)
        shade(im, lambda m: m.ellipse((1, 3, 30, 14), fill=255), BASALT)
        glow = 0.5 + 0.5 * math.sin(f * math.pi / 2)
        d.ellipse((4, 5, 27, 12), fill=mix(LAVA[2], LAVA[3], glow), outline=LAVA[0])
        d.ellipse((8, 6, 22, 10), fill=mix(LAVA[3], LAVA[4], glow))
        for k, (bx, by) in enumerate(((9, 7), (17, 8), (22, 7))):
            if (f + k) % 4 < 2:
                d.ellipse((bx, by - (f % 2), bx + 2, by + 2 - (f % 2)), fill=LAVA[5])
        d.line((2, 9, 0, 12), fill=LAVA[2])
        d.line((29, 8, 31, 5), fill=LAVA[2])
        frames.append(im)
    return frames


def draw_ice_pillar():
    im = canvas(1, 2)
    d = ImageDraw.Draw(im)
    d.polygon([(3, 31), (5, 6), (8, 1), (11, 6), (13, 31)], fill=ICE[2], outline=ICE[0])
    d.polygon([(5, 6), (8, 1), (8, 31), (5, 31)], fill=ICE[3])
    d.line((7, 5, 7, 28), fill=ICE[4])
    d.ellipse((1, 28, 15, 32), fill=(80, 130, 170, 80))
    return im


def draw_fossil_dig():
    im = canvas(2, 1)
    d = ImageDraw.Draw(im)
    shade(im, lambda m: m.ellipse((0, 2, 31, 15), fill=255), [C(h) for h in ("#3a2418", "#6e4a36", "#94684a", "#b8896a", "#d8b090")])
    skeleton(im, (5, 4, 27, 13))
    return im


def draw_fern_pot():
    im = canvas(1, 1)
    d = ImageDraw.Draw(im)
    d.polygon([(3, 9), (12, 9), (11, 15), (4, 15)], fill=C("#b0603a"), outline=BRICK[0])
    d.line((4, 10, 11, 10), fill=C("#d88a5a"))
    for a in range(-160, -10, 25):
        ex = 8 + 8 * math.cos(math.radians(a))
        ey = 9 + 8 * math.sin(math.radians(a))
        d.line((8, 9, ex, ey), fill=JLEAF[3], width=2)
        d.point((round(ex), round(ey)), fill=JLEAF[5])
    return im


def build_pavilion_objects(zs, facades, regions):
    """Register facades, shells, railings and decor. facades/regions: name -> (x, y, w, h)."""
    for name, (_, _, w, h) in facades.items():
        zs.add_object(f"facade_{name}", FACADE_ART[name](w, h))
    for name, (_, _, w, h) in regions.items():
        n = SHELL_FRAMES.get(name, 1)
        frames = [draw_shell(name, w, h, f) for f in range(n)]
        add_object_dedupe(zs, f"shell_{name}", frames, ms=300 if name == "Water" else 500)
        for kind in ("TL", "T", "TR", "L", "R", "BL", "B", "BR"):
            zs.add_object(f"rail_{name}_{kind}", rail_piece(name, kind))
        zs.add_object(f"rail_{name}_plaque", rail_piece(name, "B", plaque=name))
    for seed in (1, 2, 3):
        zs.add_object(f"bamboo_{seed}", draw_bamboo(seed))
    zs.add_object("snowfall", snowfall_frames(), ms=260)
    zs.add_object("lava_pool", lava_frames(), ms=320)
    zs.add_object("ice_pillar", draw_ice_pillar())
    zs.add_object("fossil_dig", draw_fossil_dig())
    zs.add_object("fern_pot", draw_fern_pot())


def add_object_dedupe(zs, name, frames, ms):
    """Like ZooSheet.add_object, but identical tiles (long plain wall runs) share one id."""
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
                if all(t.tobytes() == tiles[0].tobytes() for t in tiles):
                    tiles = tiles[:1]
                row.append(zs.add(tiles, ms))
        grid.append(row)
    zs.objects[name] = grid
    return grid


def extend_blender(blender, zs):
    """Teach the TerrainBlender the pavilion walkway floors."""
    for t, imgs in floor_textures(zs).items():
        blender.tex[t] = imgs
        blender.full_zoo[t] = [zs.add([img]) for img in imgs]
