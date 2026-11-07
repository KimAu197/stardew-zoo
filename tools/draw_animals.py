"""Draw the zoo animal sprite sheets (adult, baby, shop icon) as pixel art.

Every sheet uses the farm-animal layout with UseFlippedRightForLeft=true and
UseDoubleUniqueAnimationFrames=false (4 columns x 5 rows):
  0-3 walk down, 4-7 walk right, 8-11 walk up,
  12 sleep, 13 unique down, 14 unique right, 15 unique up, 16-19 eat.

Usage: python3 tools/draw_animals.py
"""

import math
from pathlib import Path

from PIL import Image

OUT_DIR = Path(__file__).resolve().parent.parent / "[CP] Stardew Zoo" / "assets"

BABY_SCALE = 0.7


def rgb(hex_color: str) -> tuple[int, int, int, int]:
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


# ---------------------------------------------------------------------------
# Shapes are predicates over continuous "design" coordinates. Rendering maps
# each output pixel back to design space, so one drawing can be rendered at
# adult size and at a smaller baby size.
# ---------------------------------------------------------------------------

def ell(cx, cy, rx, ry):
    return lambda x, y: ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1


def rect(x0, y0, x1, y1):
    return lambda x, y: x0 <= x < x1 and y0 <= y < y1


def seg(x0, y0, x1, y1, width):
    dx, dy = x1 - x0, y1 - y0
    length2 = dx * dx + dy * dy

    def inside(x, y):
        t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / length2))
        return math.hypot(x - (x0 + t * dx), y - (y0 + t * dy)) <= width / 2

    return inside


def both(a, b):
    return lambda x, y: a(x, y) and b(x, y)


class Part:
    """One layer of a drawing: fills painted in order, then shaded and outlined."""

    def __init__(self, *fills, outline=None, shade=True):
        self.fills = fills
        self.outline = outline
        self.shade = shade


def scaled(color, factor):
    return tuple(max(0, min(255, int(v * factor))) for v in color[:3]) + (255,)


def shade_layer(layer):
    src = layer.copy().load()
    dst = layer.load()
    w, h = layer.size
    for y in range(h):
        for x in range(w):
            if src[x, y][3] == 0:
                continue
            if y == 0 or src[x, y - 1][3] == 0:
                dst[x, y] = scaled(src[x, y], 1.12)
            elif y == h - 1 or src[x, y + 1][3] == 0:
                dst[x, y] = scaled(src[x, y], 0.82)


def outline_layer(layer, color):
    src = layer.copy().load()
    dst = layer.load()
    w, h = layer.size
    for y in range(h):
        for x in range(w):
            if src[x, y][3]:
                continue
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3]:
                    dst[x, y] = color
                    break


def render(parts, size, scale=1.0):
    anchor_x, anchor_y = size / 2, size - 2
    img = Image.new("RGBA", (size, size))
    for part in parts:
        layer = Image.new("RGBA", (size, size))
        px = layer.load()
        for oy in range(size):
            for ox in range(size):
                x = anchor_x + (ox + 0.5 - anchor_x) / scale
                y = anchor_y + (oy + 0.5 - anchor_y) / scale
                for shape, color in part.fills:
                    if shape(x, y):
                        px[ox, oy] = color(x, y) if callable(color) else color
        if part.shade:
            shade_layer(layer)
        if part.outline:
            outline_layer(layer, part.outline)
        img.alpha_composite(layer)
    return img


def lifts(phase):
    """Leg lift for the two diagonal leg pairs during the 4-frame walk cycle."""
    return (1 if phase == 1 else 0), (1 if phase == 3 else 0)


# ---------------------------------------------------------------------------
# Panda
# ---------------------------------------------------------------------------

P_WHITE, P_BLACK, P_FAR, P_LINE = rgb("#efece4"), rgb("#2e2b33"), rgb("#45414c"), rgb("#1c1a20")
BAMBOO, BAMBOO_LEAF = rgb("#6aa83a"), rgb("#9ed65a")


def panda_front(u, phase=0, hd=0, hx=0, blink=False, bamboo=False):
    a, b = lifts(phase)
    body = ell(16, 21, 9, 7)
    parts = [
        Part((rect(8, 24, 11, 29 - b), P_FAR), (rect(21, 24, 24, 29 - a), P_FAR), outline=P_LINE),
        Part((body, P_WHITE), (both(body, lambda x, y: 16.5 <= y < 20), P_BLACK), outline=P_LINE),
        Part((rect(10, 23, 14, 30 - a), P_BLACK), (rect(18, 23, 22, 30 - b), P_BLACK), outline=P_LINE),
        Part((ell(9.5 + hx, 6.5 + hd, 2.6, 2.6), P_BLACK), (ell(22.5 + hx, 6.5 + hd, 2.6, 2.6), P_BLACK), outline=P_LINE),
        Part((ell(16 + hx, 12 + hd, 7.5, 6.5), P_WHITE), outline=P_LINE),
    ]
    face = [
        (ell(12.5 + hx, 12.5 + hd, 2, 2.6), P_BLACK),
        (ell(19.5 + hx, 12.5 + hd, 2, 2.6), P_BLACK),
        (rect(15 + hx, 15 + hd, 17 + hx, 15 + hd + u), P_BLACK),
    ]
    if not blink:
        face += [
            (rect(12 + hx, 12 + hd, 12 + hx + u, 12 + hd + u), P_WHITE),
            (rect(19 + hx, 12 + hd, 19 + hx + u, 12 + hd + u), P_WHITE),
        ]
    parts.append(Part(*face, shade=False))
    if bamboo:
        parts.append(Part(
            (seg(9 + hx, 18 + hd, 23 + hx, 16 + hd, 1.6 * u), BAMBOO),
            (ell(24 + hx, 15 + hd, 1.8, 1.1 * u), BAMBOO_LEAF),
            outline=P_LINE,
        ))
    return parts


def panda_side(u, phase=0, hd=0, blink=False):
    a, b = lifts(phase)
    body = ell(14, 19, 10, 6.5)
    return [
        Part((rect(10, 23, 13, 29 - a), P_FAR), (rect(20, 23, 23, 29 - b), P_FAR), outline=P_LINE),
        Part((ell(4.6, 16, 1.7, 1.7), P_WHITE), outline=P_LINE),
        Part((body, P_WHITE), (both(body, lambda x, y: 16.5 <= x < 21.5), P_BLACK), outline=P_LINE),
        Part((rect(7, 23, 10, 30 - b), P_BLACK), (rect(17, 23, 20, 30 - a), P_BLACK), outline=P_LINE),
        Part((ell(21, 7.5 + hd, 2.2, 2.2), P_BLACK), outline=P_LINE),
        Part((ell(24, 13 + hd, 6, 5.5), P_WHITE), outline=P_LINE),
        Part(
            (ell(26, 12.5 + hd, 2, 2.3), P_BLACK),
            (rect(28, 15 + hd, 30, 15 + hd + u), P_BLACK),
            *([] if blink else [(rect(26, 12 + hd, 26 + u, 12 + hd + u), P_WHITE)]),
            shade=False,
        ),
    ]


def panda_back(u, phase=0, hx=0):
    a, b = lifts(phase)
    body = ell(16, 20.5, 9, 7.5)
    return [
        Part((ell(9.5 + hx, 5.5, 2.5, 2.5), P_BLACK), (ell(22.5 + hx, 5.5, 2.5, 2.5), P_BLACK), outline=P_LINE),
        Part((ell(16 + hx, 11, 7, 6), P_WHITE), outline=P_LINE),
        Part((body, P_WHITE), (both(body, lambda x, y: 16 <= y < 19.5), P_BLACK), outline=P_LINE),
        Part((rect(10, 23, 14, 30 - a), P_BLACK), (rect(18, 23, 22, 30 - b), P_BLACK), outline=P_LINE),
        Part((ell(16, 25.5, 1.8, 1.5), P_WHITE), outline=P_LINE),
    ]


def panda_sleep(u):
    return [
        Part((ell(16, 24.5, 11, 5.5), P_WHITE), outline=P_LINE),
        Part((ell(10.5, 27.5, 3, 1.8), P_BLACK), (ell(21.5, 27.5, 3, 1.8), P_BLACK), outline=P_LINE),
        Part((ell(10, 14.5, 2.4, 2.4), P_BLACK), (ell(22, 14.5, 2.4, 2.4), P_BLACK), outline=P_LINE),
        Part((ell(16, 19.5, 7, 6), P_WHITE), outline=P_LINE),
        Part(
            (ell(12.5, 20, 2, 1.8), P_BLACK), (ell(19.5, 20, 2, 1.8), P_BLACK),
            (rect(15, 22, 17, 22 + u), P_BLACK),
            shade=False,
        ),
    ]


def panda_frames(u):
    return (
        [panda_front(u, p) for p in range(4)]
        + [panda_side(u, p) for p in range(4)]
        + [panda_back(u, p) for p in range(4)]
        + [panda_sleep(u), panda_front(u, hd=1, hx=1, blink=True), panda_side(u, hd=2), panda_back(u, hx=1)]
        + [panda_front(u, hd=d, bamboo=True) for d in (1, 2, 2, 1)]
    )


# ---------------------------------------------------------------------------
# Lion
# ---------------------------------------------------------------------------

L_BODY, L_BELLY, L_FAR = rgb("#d9a352"), rgb("#f0cf8c"), rgb("#b9873f")
L_MANE, L_MANE_DARK, L_LINE = rgb("#a2541f"), rgb("#7c3c16"), rgb("#4a2410")
L_NOSE, L_EYE = rgb("#5a2e22"), rgb("#2a160c")


def mane_color(cx, cy, r):
    def color(x, y):
        d = math.hypot(x - cx, (y - cy) * 1.1) / r
        if d > 0.72 and (int(x) + int(y)) % 3 == 0:
            return L_MANE_DARK
        return L_MANE
    return color


def lion_front(u, phase=0, hd=0, hx=0, blink=False, roar=False):
    a, b = lifts(phase)
    body = ell(16, 22, 8.5, 6)
    parts = [
        Part((rect(8, 24, 11, 29 - b), L_FAR), (rect(21, 24, 24, 29 - a), L_FAR), outline=L_LINE),
        Part((body, L_BODY), (both(body, lambda x, y: y > 23.5 and abs(x - 16) < 4), L_BELLY), outline=L_LINE),
        Part((rect(10, 23, 13, 30 - a), L_BODY), (rect(19, 23, 22, 30 - b), L_BODY), outline=L_LINE),
        Part((ell(16 + hx, 12 + hd, 9, 8.2), mane_color(16 + hx, 12 + hd, 9)), outline=L_LINE),
        Part((ell(10.5 + hx, 5 + hd, 1.6, 1.6), L_BODY), (ell(21.5 + hx, 5 + hd, 1.6, 1.6), L_BODY), outline=L_LINE),
        Part((ell(16 + hx, 13 + hd, 5.5, 5), L_BODY), outline=L_MANE_DARK),
    ]
    face = [
        (ell(16 + hx, 16 + hd, 3, 2), L_BELLY),
        (rect(15 + hx, 14 + hd, 17 + hx, 15 + hd + u * 0.5), L_NOSE),
    ]
    if blink:
        face += [(rect(12.5 + hx, 12 + hd, 14.5 + hx, 12 + hd + u), L_EYE),
                 (rect(17.5 + hx, 12 + hd, 19.5 + hx, 12 + hd + u), L_EYE)]
    else:
        face += [(rect(13 + hx, 11 + hd, 13 + hx + u, 13 + hd), L_EYE),
                 (rect(18 + hx, 11 + hd, 18 + hx + u, 13 + hd), L_EYE)]
    if roar:
        face.append((ell(16 + hx, 17.5 + hd, 1.6, 1.5), L_NOSE))
    parts.append(Part(*face, shade=False))
    return parts


def lion_side(u, phase=0, hd=0):
    a, b = lifts(phase)
    body = ell(14, 19.5, 10, 5.5)
    return [
        Part((rect(10, 23, 13, 29 - a), L_FAR), (rect(20, 23, 23, 29 - b), L_FAR), outline=L_LINE),
        Part((seg(5, 18, 2.5, 11, 1.3), L_BODY), outline=L_LINE),
        Part((ell(2.5, 10, 1.6, 1.9), L_MANE_DARK), outline=L_LINE),
        Part((body, L_BODY), (both(body, lambda x, y: y > 21.5), L_BELLY), outline=L_LINE),
        Part((rect(7, 23, 10, 30 - b), L_BODY), (rect(17, 23, 20, 30 - a), L_BODY), outline=L_LINE),
        Part((ell(22, 13 + hd, 6.5, 7.2), mane_color(22, 13 + hd, 6.5)), outline=L_LINE),
        Part((ell(22.5, 6.5 + hd, 1.5, 1.5), L_BODY), outline=L_LINE),
        Part((ell(25.5, 14 + hd, 4, 4), L_BODY), outline=L_MANE_DARK),
        Part(
            (ell(28.5, 16 + hd, 2, 1.8), L_BELLY),
            (rect(29, 14 + hd, 30, 15 + hd), L_NOSE),
            (rect(26, 12 + hd, 26 + u, 14 + hd), L_EYE),
            shade=False,
        ),
    ]


def lion_back(u, phase=0, hx=0):
    a, b = lifts(phase)
    return [
        Part((ell(16, 21.5, 8.5, 7), L_BODY), outline=L_LINE),
        Part((rect(10, 23, 13, 30 - a), L_BODY), (rect(19, 23, 22, 30 - b), L_BODY), outline=L_LINE),
        Part((ell(16 + hx, 11.5, 9, 8.2), mane_color(16 + hx, 11.5, 9)), outline=L_LINE),
        Part((ell(10.5 + hx, 4.5, 1.6, 1.6), L_BODY), (ell(21.5 + hx, 4.5, 1.6, 1.6), L_BODY), outline=L_LINE),
        Part((seg(16, 22, 17, 27.5, 1.3), L_BODY), outline=L_LINE),
        Part((ell(17, 28.5, 1.5, 1.4), L_MANE_DARK), outline=L_LINE),
    ]


def lion_sleep(u):
    return [
        Part((ell(16, 24.5, 11, 5), L_BODY), outline=L_LINE),
        Part((ell(10.5, 28, 2.6, 1.5), L_BODY), (ell(21.5, 28, 2.6, 1.5), L_BODY), outline=L_LINE),
        Part((ell(16, 19, 8.5, 7.5), mane_color(16, 19, 8.5)), outline=L_LINE),
        Part((ell(16, 20, 5, 4.5), L_BODY), outline=L_MANE_DARK),
        Part(
            (ell(16, 22.2, 2.6, 1.6), L_BELLY),
            (rect(15, 21, 17, 21 + u * 0.8), L_NOSE),
            (rect(12.5, 19, 14.5, 19 + u), L_EYE), (rect(17.5, 19, 19.5, 19 + u), L_EYE),
            shade=False,
        ),
    ]


def lion_frames(u):
    return (
        [lion_front(u, p) for p in range(4)]
        + [lion_side(u, p) for p in range(4)]
        + [lion_back(u, p) for p in range(4)]
        + [lion_sleep(u), lion_front(u, hd=-1, roar=True), lion_side(u, hd=2), lion_back(u, hx=1)]
        + [lion_front(u, hd=d, blink=d == 2) for d in (1, 2, 2, 1)]
    )


# ---------------------------------------------------------------------------
# Giraffe
# ---------------------------------------------------------------------------

G_BASE, G_PATCH, G_PATCH2 = rgb("#f3d996"), rgb("#c0712f"), rgb("#a95f25")
G_MUZZLE, G_DARK, G_LINE, G_FAR = rgb("#ead1ad"), rgb("#5a3418"), rgb("#6b3e1c"), rgb("#d7b871")


def giraffe_pattern(x, y):
    """Reticulated coat: brown cells separated by light lines."""
    col = math.floor(x / 4)
    shifted = y + 2 * (col % 2)
    row = math.floor(shifted / 4)
    if x - col * 4 < 1 or shifted - row * 4 < 1:
        return G_BASE
    return G_PATCH if (col + row) % 2 else G_PATCH2


def giraffe_leg(x0, x1, y0, y1, color):
    return (rect(x0, y0, x1, y1), lambda x, y: G_DARK if y >= y1 - 1.5 else color)


def giraffe_front(u, phase=0, hd=0, hx=0, blink=False, ear=0):
    a, b = lifts(phase)
    hy = 7 + hd
    parts = [
        Part(giraffe_leg(9, 11, 22, 29 - b, G_FAR), giraffe_leg(21, 23, 22, 29 - a, G_FAR), outline=G_LINE),
        Part((ell(16, 20, 7.5, 5), giraffe_pattern), outline=G_LINE),
        Part(giraffe_leg(11, 13, 21, 30 - a, G_BASE), giraffe_leg(19, 21, 21, 30 - b, G_BASE), outline=G_LINE),
        Part((rect(14, hy + 1, 18, 19), giraffe_pattern), outline=G_LINE),
        Part((rect(13 + hx, hy - 5.5, 14 + hx, hy - 2), G_DARK), (rect(18 + hx, hy - 5.5, 19 + hx, hy - 2), G_DARK),
             (ell(13.5 + hx, hy - 5.5, 1, 1), G_DARK), (ell(18.5 + hx, hy - 5.5, 1, 1), G_DARK), outline=G_LINE),
        Part((ell(10.8 + hx, hy - 2 - ear, 1.9, 1), G_BASE), (ell(21.2 + hx, hy - 2 - ear, 1.9, 1), G_BASE), outline=G_LINE),
        Part((ell(16 + hx, hy, 4, 3.4), G_BASE), outline=G_LINE),
    ]
    face = [(ell(16 + hx, hy + 2.2, 2.6, 1.6), G_MUZZLE)]
    if blink:
        face += [(rect(12.5 + hx, hy - 1, 14.5 + hx, hy - 1 + u), G_DARK),
                 (rect(17.5 + hx, hy - 1, 19.5 + hx, hy - 1 + u), G_DARK)]
    else:
        face += [(rect(13 + hx, hy - 1, 13 + hx + u, hy - 1 + u), G_DARK),
                 (rect(18 + hx, hy - 1, 18 + hx + u, hy - 1 + u), G_DARK)]
    parts.append(Part(*face, shade=False))
    return parts


def giraffe_side(u, phase=0, hd=0):
    a, b = lifts(phase)
    hy = 7 + hd
    return [
        Part(giraffe_leg(8, 10, 21, 29 - a, G_FAR), giraffe_leg(18, 20, 21, 29 - b, G_FAR), outline=G_LINE),
        Part((seg(4.5, 17, 3, 23, 1), G_BASE), (ell(3, 24, 1, 1.6), G_DARK), outline=G_LINE),
        Part((ell(12, 19, 8.5, 4.8), giraffe_pattern), outline=G_LINE),
        Part(giraffe_leg(6, 8, 21, 30 - b, G_BASE), giraffe_leg(16, 18, 21, 30 - a, G_BASE), outline=G_LINE),
        Part((seg(17, 18, 23, hy + 1, 4.2), giraffe_pattern), outline=G_LINE),
        Part((seg(15.4, 16.6, 21.4, hy, 1.2), G_DARK), shade=False),
        Part((rect(23, hy - 5.5, 24, hy - 2), G_DARK), (ell(23.5, hy - 5.5, 1, 1), G_DARK), outline=G_LINE),
        Part((ell(21.5, hy - 2, 1.8, 1), G_BASE), outline=G_LINE),
        Part((ell(25.5, hy, 4.5, 2.9), G_BASE), outline=G_LINE),
        Part((ell(28.8, hy + 1, 1.8, 1.8), G_MUZZLE), (rect(25, hy - 1, 25 + u, hy - 1 + u), G_DARK), shade=False),
    ]


def giraffe_back(u, phase=0, hx=0):
    a, b = lifts(phase)
    return [
        Part((rect(14 + hx, 1.5, 15 + hx, 5), G_DARK), (rect(17 + hx, 1.5, 18 + hx, 5), G_DARK),
             (ell(14.5 + hx, 1.5, 1, 1), G_DARK), (ell(17.5 + hx, 1.5, 1, 1), G_DARK), outline=G_LINE),
        Part((ell(10.8 + hx, 5, 1.9, 1), G_BASE), (ell(21.2 + hx, 5, 1.9, 1), G_BASE), outline=G_LINE),
        Part((ell(16 + hx, 6.5, 4, 3.2), G_BASE), outline=G_LINE),
        Part((rect(14, 9, 18, 19), giraffe_pattern), (rect(15.5, 9, 16.5, 19), G_DARK), outline=G_LINE),
        Part((ell(16, 21, 7.5, 5), giraffe_pattern), outline=G_LINE),
        Part(giraffe_leg(10, 12, 23, 30 - a, G_BASE), giraffe_leg(20, 22, 23, 30 - b, G_BASE), outline=G_LINE),
        Part((seg(16, 23, 16, 27, 1), G_BASE), (ell(16, 28, 1, 1.5), G_DARK), outline=G_LINE),
    ]


def giraffe_sleep(u):
    hy = 11
    return [
        Part((ell(16, 25.5, 10.5, 4.5), giraffe_pattern), outline=G_LINE),
        Part((rect(14, hy + 1, 18, 23), giraffe_pattern), outline=G_LINE),
        Part((rect(13, hy - 5.5, 14, hy - 2), G_DARK), (rect(18, hy - 5.5, 19, hy - 2), G_DARK),
             (ell(13.5, hy - 5.5, 1, 1), G_DARK), (ell(18.5, hy - 5.5, 1, 1), G_DARK), outline=G_LINE),
        Part((ell(11, hy - 1, 1.9, 1), G_BASE), (ell(21, hy - 1, 1.9, 1), G_BASE), outline=G_LINE),
        Part((ell(16, hy, 4, 3.4), G_BASE), outline=G_LINE),
        Part((ell(16, hy + 2.2, 2.6, 1.6), G_MUZZLE),
             (rect(12.5, hy - 1, 14.5, hy - 1 + u), G_DARK), (rect(17.5, hy - 1, 19.5, hy - 1 + u), G_DARK),
             shade=False),
    ]


def giraffe_frames(u):
    return (
        [giraffe_front(u, p) for p in range(4)]
        + [giraffe_side(u, p) for p in range(4)]
        + [giraffe_back(u, p) for p in range(4)]
        + [giraffe_sleep(u), giraffe_front(u, ear=1, blink=True), giraffe_side(u, hd=3), giraffe_back(u, hx=1)]
        + [giraffe_front(u, hd=d) for d in (2, 4, 4, 2)]
    )


# ---------------------------------------------------------------------------
# Penguin (16x16 frames)
# ---------------------------------------------------------------------------

PG_BLACK, PG_FLIP, PG_WHITE = rgb("#252a3c"), rgb("#3a4260"), rgb("#f2f4f8")
PG_ORANGE, PG_LINE = rgb("#f0962a"), rgb("#14161f")
CHICK_GREY, CHICK_FEET = rgb("#9ea3ad"), rgb("#5b5f68")


def penguin_front(phase=0, hd=0, flap=False, blink=False):
    a, b = lifts(phase)
    fy = 6.5 if flap else 9.5
    fx = 1.2 if flap else 0
    return [
        Part((rect(4, 14 - a, 7, 15 - a), PG_ORANGE), (rect(9, 14 - b, 12, 15 - b), PG_ORANGE), outline=PG_LINE, shade=False),
        Part((ell(2.8 - fx, fy, 1.2, 2.8), PG_FLIP), (ell(13.2 + fx, fy, 1.2, 2.8), PG_FLIP), outline=PG_LINE),
        Part((ell(8, 9, 5, 5.8), PG_BLACK), outline=PG_LINE),
        Part((ell(8, 10.4, 3.4, 4.2), PG_WHITE),
             *([] if blink else [(rect(6, 5 + hd, 7, 6 + hd), PG_WHITE), (rect(9, 5 + hd, 10, 6 + hd), PG_WHITE)]),
             (rect(7, 6 + hd, 9, 7 + hd), PG_ORANGE), shade=False),
    ]


def penguin_side(phase=0, beak_up=False):
    a, b = lifts(phase)
    beak = rect(12, 5, 14, 6) if beak_up else rect(12, 6, 14, 7)
    return [
        Part((rect(7, 14 - a, 9, 15 - a), PG_ORANGE), (rect(9, 14 - b, 11, 15 - b), PG_ORANGE), outline=PG_LINE, shade=False),
        Part((ell(8, 9, 4.5, 5.8), PG_BLACK), outline=PG_LINE),
        Part((ell(9.8, 10.4, 2.6, 4.2), PG_WHITE), (rect(10, 5, 11, 6), PG_WHITE), (beak, PG_ORANGE), shade=False),
        Part((ell(6.5, 10, 1.3, 3), PG_FLIP), shade=False),
    ]


def penguin_back(phase=0, flap=False):
    a, b = lifts(phase)
    fy = 6.5 if flap else 9.5
    fx = 1.2 if flap else 0
    return [
        Part((ell(2.8 - fx, fy, 1.2, 2.8), PG_FLIP), (ell(13.2 + fx, fy, 1.2, 2.8), PG_FLIP), outline=PG_LINE),
        Part((ell(8, 9, 5, 5.8), PG_BLACK), outline=PG_LINE),
        Part((rect(4, 14 - a, 7, 15 - a), PG_ORANGE), (rect(9, 14 - b, 12, 15 - b), PG_ORANGE), outline=PG_LINE, shade=False),
    ]


def penguin_sleep():
    return [
        Part((ell(8, 11, 5.4, 4.5), PG_BLACK), outline=PG_LINE),
        Part((ell(8, 12.2, 3.4, 3), PG_WHITE), (rect(7, 8, 9, 9), PG_ORANGE), shade=False),
    ]


def penguin_frames():
    return (
        [penguin_front(p) for p in range(4)]
        + [penguin_side(p) for p in range(4)]
        + [penguin_back(p) for p in range(4)]
        + [penguin_sleep(), penguin_front(flap=True), penguin_side(beak_up=True), penguin_back(flap=True)]
        + [penguin_front(hd=d, blink=d == 1) for d in (0, 1, 1, 0)]
    )


def chick_front(phase=0, hd=0, flap=False, blink=False):
    a, b = lifts(phase)
    fy = 9 if flap else 11
    return [
        Part((rect(5, 14 - a, 7, 15 - a), CHICK_FEET), (rect(9, 14 - b, 11, 15 - b), CHICK_FEET), outline=PG_LINE, shade=False),
        Part((ell(3.6, fy, 1, 2), CHICK_GREY), (ell(12.4, fy, 1, 2), CHICK_GREY), outline=PG_LINE),
        Part((ell(8, 11, 4.5, 3.8), CHICK_GREY), outline=PG_LINE),
        Part((ell(8, 6.5 + hd, 3.6, 3.2), PG_BLACK), outline=PG_LINE),
        Part((ell(8, 7.3 + hd, 2.6, 1.9), PG_WHITE),
             *([] if blink else [(rect(6, 7 + hd, 7, 8 + hd), PG_BLACK), (rect(9, 7 + hd, 10, 8 + hd), PG_BLACK)]),
             (rect(7, 8 + hd, 9, 9 + hd), PG_LINE), shade=False),
    ]


def chick_side(phase=0, beak_up=False):
    a, b = lifts(phase)
    return [
        Part((rect(7, 14 - a, 9, 15 - a), CHICK_FEET), (rect(8, 14 - b, 10, 15 - b), CHICK_FEET), outline=PG_LINE, shade=False),
        Part((ell(8, 11, 4.2, 3.8), CHICK_GREY), outline=PG_LINE),
        Part((ell(9, 6.5, 3.2, 3.2), PG_BLACK), outline=PG_LINE),
        Part((ell(10.4, 7.2, 1.6, 1.8), PG_WHITE), (rect(10, 6, 11, 7), PG_BLACK),
             (rect(12, 6 if beak_up else 7, 13, 7 if beak_up else 8), PG_LINE), shade=False),
        Part((ell(6.5, 11, 1, 2), scaled(CHICK_GREY, 0.85)), shade=False),
    ]


def chick_back(phase=0, flap=False):
    a, b = lifts(phase)
    fy = 9 if flap else 11
    return [
        Part((ell(3.6, fy, 1, 2), CHICK_GREY), (ell(12.4, fy, 1, 2), CHICK_GREY), outline=PG_LINE),
        Part((ell(8, 11, 4.5, 3.8), CHICK_GREY), outline=PG_LINE),
        Part((ell(8, 6.5, 3.6, 3.2), PG_BLACK), outline=PG_LINE),
        Part((rect(5, 14 - a, 7, 15 - a), CHICK_FEET), (rect(9, 14 - b, 11, 15 - b), CHICK_FEET), outline=PG_LINE, shade=False),
    ]


def chick_sleep():
    return [
        Part((ell(8, 12, 5, 3.4), CHICK_GREY), outline=PG_LINE),
        Part((ell(8, 9.5, 3.4, 2.8), PG_BLACK), outline=PG_LINE),
        Part((ell(8, 10.2, 2.4, 1.5), PG_WHITE), (rect(7, 11, 9, 12), PG_LINE), shade=False),
    ]


def chick_frames():
    return (
        [chick_front(p) for p in range(4)]
        + [chick_side(p) for p in range(4)]
        + [chick_back(p) for p in range(4)]
        + [chick_sleep(), chick_front(flap=True), chick_side(beak_up=True), chick_back(flap=True)]
        + [chick_front(hd=d, blink=d == 1) for d in (0, 1, 1, 0)]
    )


# ---------------------------------------------------------------------------
# Sheets
# ---------------------------------------------------------------------------

def build_sheet(frames, size, scale=1.0):
    sheet = Image.new("RGBA", (size * 4, size * 5))
    for index, parts in enumerate(frames):
        sheet.paste(render(parts, size, scale), ((index % 4) * size, (index // 4) * size))
    return sheet


def shop_icon(frame, crop):
    icon = Image.new("RGBA", (32, 16))
    region = frame.crop(crop)
    icon.alpha_composite(region, ((32 - region.width) // 2, 16 - region.height))
    return icon


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    big = {
        "Panda": (panda_frames, (0, 2, 32, 18)),
        "Lion": (lion_frames, (0, 2, 32, 18)),
        "Giraffe": (giraffe_frames, (0, 0, 32, 16)),
    }
    for name, (frames, crop) in big.items():
        build_sheet(frames(1), 32).save(OUT_DIR / f"{name}.png")
        build_sheet(frames(1 / BABY_SCALE), 32, BABY_SCALE).save(OUT_DIR / f"Baby{name}.png")
        shop_icon(render(frames(1)[0], 32), crop).save(OUT_DIR / f"{name}Shop.png")

    build_sheet(penguin_frames(), 16).save(OUT_DIR / "Penguin.png")
    build_sheet(chick_frames(), 16).save(OUT_DIR / "BabyPenguin.png")
    shop_icon(render(penguin_frames()[0], 16), (0, 0, 16, 16)).save(OUT_DIR / "PenguinShop.png")

    print(f"Wrote animal sprites to {OUT_DIR}")


if __name__ == "__main__":
    main()
