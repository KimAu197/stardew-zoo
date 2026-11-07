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

from animal_sizes import CLIMBERS, FLIERS, SIZES, SWIMMERS, adult_scale, baby_scale, frame, sheet_rows

OUT_DIR = Path(__file__).resolve().parent.parent / "[CP] Stardew Zoo" / "assets"

# Extra details (toenails, claws, teeth, spots) only drawn when a sheet is rendered large enough to show them.
DETAIL = False


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


def render(parts, size, scale=1.0, design=None):
    """Render design-space parts into a size x size frame, design feet anchored to the frame's bottom centre.

    32-unit designs stand on y=30 and 16-unit designs on y=15; both land on output row size-2.
    """
    design = size if design is None else design
    design_x, design_y = design / 2, (design - 1 if design <= 16 else design - 2)
    anchor_x, anchor_y = size / 2, size - 2
    img = Image.new("RGBA", (size, size))
    for part in parts:
        layer = Image.new("RGBA", (size, size))
        px = layer.load()
        for oy in range(size):
            for ox in range(size):
                x = design_x + (ox + 0.5 - anchor_x) / scale
                y = design_y + (oy + 0.5 - anchor_y) / scale
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
# Monkey (16x16)
# ---------------------------------------------------------------------------

MK_FUR, MK_FACE, MK_DARK, MK_LINE = rgb("#8a4f2a"), rgb("#e2b989"), rgb("#5c3318"), rgb("#2a160c")


def monkey_front(phase=0, hd=0, blink=False, wave=False):
    a, b = lifts(phase)
    arm_y = 6 if wave else 9
    return [
        Part((rect(4, 14 - a, 6, 15 - a), MK_FACE), (rect(10, 14 - b, 12, 15 - b), MK_FACE), outline=MK_LINE, shade=False),
        Part((ell(3.2, arm_y, 1.3, 2.4), MK_FUR), (ell(12.8, 9, 1.3, 2.4), MK_FUR), outline=MK_LINE),
        Part((ell(8, 10.5, 4.2, 3.6), MK_FUR), outline=MK_LINE),
        Part((ell(8, 6 + hd, 4.4, 3.8), MK_FUR), outline=MK_LINE),
        Part((ell(3.5, 5.5 + hd, 1.6, 1.8), MK_FUR), (ell(12.5, 5.5 + hd, 1.6, 1.8), MK_FUR), outline=MK_LINE),
        Part((ell(8, 6.8 + hd, 3.2, 2.8), MK_FACE),
             *([] if blink else [(rect(6, 6 + hd, 7, 7 + hd), MK_LINE), (rect(9, 6 + hd, 10, 7 + hd), MK_LINE)]),
             (rect(7, 8 + hd, 9, 9 + hd), MK_DARK), shade=False),
    ]


def monkey_side(phase=0, eat=False):
    a, b = lifts(phase)
    return [
        Part((rect(6, 14 - a, 8, 15 - a), MK_FACE), (rect(9, 14 - b, 11, 15 - b), MK_FACE), outline=MK_LINE, shade=False),
        Part((seg(4, 11, 1.5, 13.5, 1.3), MK_DARK), (ell(1.4, 13.8, 1.3, 1.1), MK_DARK), outline=MK_LINE),
        Part((ell(8, 10.5, 4, 3.6), MK_FUR), outline=MK_LINE),
        Part((ell(11, 6.2, 3.4, 3.2), MK_FUR), outline=MK_LINE),
        Part((ell(4.8, 10, 1.2, 2.2), MK_FUR), shade=False),
        Part((ell(12.2, 7, 2.2, 2), MK_FACE), (rect(11, 6, 12, 7), MK_LINE),
             (rect(13, 7 if not eat else 6, 15, 8 if not eat else 7), MK_FACE), shade=False),
    ]


def monkey_back(phase=0):
    a, b = lifts(phase)
    return [
        Part((ell(3.5, 5.5, 1.6, 1.8), MK_FUR), (ell(12.5, 5.5, 1.6, 1.8), MK_FUR), outline=MK_LINE),
        Part((ell(8, 6, 4.2, 3.6), MK_FUR), outline=MK_LINE),
        Part((ell(8, 10.5, 4.2, 3.6), MK_FUR), outline=MK_LINE),
        Part((rect(4, 14 - a, 6, 15 - a), MK_FACE), (rect(10, 14 - b, 12, 15 - b), MK_FACE), outline=MK_LINE, shade=False),
    ]


def monkey_sleep():
    return [
        Part((ell(8, 12, 5.2, 3), MK_FUR), outline=MK_LINE),
        Part((ell(8, 9.5, 3.6, 2.8), MK_FUR), outline=MK_LINE),
        Part((ell(8, 10, 2.6, 2), MK_FACE), (rect(7, 10, 9, 11), MK_DARK), shade=False),
        Part((seg(11, 12, 14, 13, 1.2), MK_DARK), outline=MK_LINE),
    ]


def monkey_frames():
    return (
        [monkey_front(p) for p in range(4)]
        + [monkey_side(p) for p in range(4)]
        + [monkey_back(p) for p in range(4)]
        + [monkey_sleep(), monkey_front(wave=True), monkey_side(eat=True), monkey_back()]
        + [monkey_front(hd=d, blink=d == 1) for d in (0, 1, 1, 0)]
    )


# ---------------------------------------------------------------------------
# Raccoon (16x16)
# ---------------------------------------------------------------------------

RC_GRAY, RC_DARK, RC_WHITE, RC_LINE = rgb("#7a756e"), rgb("#2c2a28"), rgb("#efe6d8"), rgb("#1a1816")


def raccoon_front(phase=0, hd=0, blink=False):
    a, b = lifts(phase)
    return [
        Part((rect(4, 14 - a, 6, 15 - a), RC_DARK), (rect(10, 14 - b, 12, 15 - b), RC_DARK), outline=RC_LINE, shade=False),
        Part((ell(8, 10.8, 4.4, 3.4), RC_GRAY), outline=RC_LINE),
        Part((ell(8, 6.2 + hd, 4.2, 3.6), RC_GRAY), outline=RC_LINE),
        Part((ell(4.2, 4.2 + hd, 1.5, 1.6), RC_GRAY), (ell(11.8, 4.2 + hd, 1.5, 1.6), RC_GRAY), outline=RC_LINE),
        Part((ell(5.6, 6.6 + hd, 1.8, 1.6), RC_DARK), (ell(10.4, 6.6 + hd, 1.8, 1.6), RC_DARK),
             (ell(8, 8.4 + hd, 1.6, 1.1), RC_WHITE),
             *([] if blink else [(rect(5, 6 + hd, 6, 7 + hd), RC_WHITE), (rect(10, 6 + hd, 11, 7 + hd), RC_WHITE)]),
             (rect(7, 8 + hd, 9, 9 + hd), RC_DARK), shade=False),
    ]


def raccoon_side(phase=0):
    a, b = lifts(phase)
    return [
        Part((rect(6, 14 - a, 8, 15 - a), RC_DARK), (rect(9, 14 - b, 11, 15 - b), RC_DARK), outline=RC_LINE, shade=False),
        Part((seg(4, 11, 1, 10, 1.6), RC_GRAY), (ell(1.2, 10, 1.4, 1.3), RC_DARK),
             (ell(2.4, 10.2, 1.2, 1.1), RC_WHITE), outline=RC_LINE),
        Part((ell(8, 10.5, 4.2, 3.3), RC_GRAY), outline=RC_LINE),
        Part((ell(11.5, 6.4, 3.4, 3.2), RC_GRAY), outline=RC_LINE),
        Part((ell(12.6, 6.8, 2, 1.8), RC_DARK), (rect(11, 6, 12, 7), RC_WHITE),
             (rect(13, 7, 15, 8), RC_DARK), shade=False),
    ]


def raccoon_back(phase=0):
    a, b = lifts(phase)
    return [
        Part((ell(4.2, 4.2, 1.5, 1.6), RC_GRAY), (ell(11.8, 4.2, 1.5, 1.6), RC_GRAY), outline=RC_LINE),
        Part((ell(8, 6.2, 4.2, 3.6), RC_GRAY), outline=RC_LINE),
        Part((ell(8, 10.8, 4.4, 3.4), RC_GRAY), outline=RC_LINE),
        Part((seg(8, 13, 8, 15, 1.4), RC_DARK), (ell(8, 15, 1.2, 0.8), RC_WHITE), outline=RC_LINE),
        Part((rect(4, 14 - a, 6, 15 - a), RC_DARK), (rect(10, 14 - b, 12, 15 - b), RC_DARK), outline=RC_LINE, shade=False),
    ]


def raccoon_sleep():
    return [
        Part((ell(8, 12.2, 5.4, 2.8), RC_GRAY), outline=RC_LINE),
        Part((ell(5, 12.5, 2.2, 1.4), RC_DARK), (ell(3, 11.5, 1.4, 1.2), RC_WHITE), outline=RC_LINE),
        Part((ell(11, 9.5, 3.2, 2.8), RC_GRAY), outline=RC_LINE),
        Part((ell(11.5, 9.8, 1.8, 1.5), RC_DARK), (rect(10, 9, 12, 10), RC_DARK), shade=False),
    ]


def raccoon_frames():
    return (
        [raccoon_front(p) for p in range(4)]
        + [raccoon_side(p) for p in range(4)]
        + [raccoon_back(p) for p in range(4)]
        + [raccoon_sleep(), raccoon_front(hd=1, blink=True), raccoon_side(), raccoon_back()]
        + [raccoon_front(hd=d, blink=d == 1) for d in (0, 1, 1, 0)]
    )


# ---------------------------------------------------------------------------
# Capybara (32x32)
# ---------------------------------------------------------------------------

CP_FUR, CP_BELLY, CP_SN, CP_LINE = rgb("#b07a45"), rgb("#d4a574"), rgb("#c9925c"), rgb("#4a2e16")


def capy_front(u, phase=0, hd=0, hx=0, blink=False):
    a, b = lifts(phase)
    return [
        Part((rect(9, 25 - b, 13, 30 - b), CP_FUR), (rect(19, 25 - a, 23, 30 - a), CP_FUR), outline=CP_LINE),
        Part((ell(16, 21, 10, 7), CP_FUR), (both(ell(16, 21, 10, 7), lambda x, y: y > 22), CP_BELLY), outline=CP_LINE),
        Part((rect(11, 24, 15, 30 - a), CP_FUR), (rect(17, 24, 21, 30 - b), CP_FUR), outline=CP_LINE),
        Part((ell(16 + hx, 13 + hd, 8.5, 7), CP_FUR), outline=CP_LINE),
        Part((ell(10.5 + hx, 8 + hd, 1.6, 1.4), CP_FUR), (ell(21.5 + hx, 8 + hd, 1.6, 1.4), CP_FUR), outline=CP_LINE),
        Part((ell(16 + hx, 16 + hd, 5.5, 3.2), CP_SN),
             *([] if blink else [(rect(12 + hx, 12 + hd, 13 + hx + u, 14 + hd), CP_LINE),
                                 (rect(19 + hx, 12 + hd, 20 + hx + u, 14 + hd), CP_LINE)]),
             (rect(15 + hx, 16 + hd, 17 + hx, 17 + hd + u), CP_LINE), shade=False),
    ]


def capy_side(u, phase=0, hd=0):
    a, b = lifts(phase)
    return [
        Part((rect(8, 25 - a, 12, 29 - a), CP_FUR), (rect(18, 25 - b, 22, 29 - b), CP_FUR), outline=CP_LINE),
        Part((ell(14, 20, 11, 6.5), CP_FUR), (both(ell(14, 20, 11, 6.5), lambda x, y: y > 22), CP_BELLY), outline=CP_LINE),
        Part((rect(6, 24, 10, 30 - b), CP_FUR), (rect(16, 24, 20, 30 - a), CP_FUR), outline=CP_LINE),
        Part((ell(24, 15 + hd, 6.5, 5.5), CP_FUR), outline=CP_LINE),
        Part((ell(24, 10.5 + hd, 1.5, 1.3), CP_FUR), outline=CP_LINE),
        Part((ell(28, 16.5 + hd, 3.4, 2.6), CP_SN), (rect(24, 13 + hd, 25 + u, 15 + hd), CP_LINE),
             (rect(29, 16 + hd, 31, 17 + hd), CP_LINE), shade=False),
    ]


def capy_back(u, phase=0, hx=0):
    a, b = lifts(phase)
    return [
        Part((ell(16, 20.5, 10, 7), CP_FUR), outline=CP_LINE),
        Part((rect(11, 24, 15, 30 - a), CP_FUR), (rect(17, 24, 21, 30 - b), CP_FUR), outline=CP_LINE),
        Part((ell(16 + hx, 12, 8, 6.5), CP_FUR), outline=CP_LINE),
        Part((ell(10.5 + hx, 7.5, 1.6, 1.4), CP_FUR), (ell(21.5 + hx, 7.5, 1.6, 1.4), CP_FUR), outline=CP_LINE),
    ]


def capy_sleep(u):
    return [
        Part((ell(16, 24, 12, 5.5), CP_FUR), outline=CP_LINE),
        Part((ell(16, 20, 8, 5.5), CP_FUR), outline=CP_LINE),
        Part((ell(16, 21.5, 5, 2.6), CP_SN), (rect(12, 19, 14, 20), CP_LINE), (rect(18, 19, 20, 20), CP_LINE),
             (rect(15, 22, 17, 23), CP_LINE), shade=False),
    ]


def capy_frames(u):
    return (
        [capy_front(u, p) for p in range(4)]
        + [capy_side(u, p) for p in range(4)]
        + [capy_back(u, p) for p in range(4)]
        + [capy_sleep(u), capy_front(u, hd=1, blink=True), capy_side(u, hd=2), capy_back(u, hx=1)]
        + [capy_front(u, hd=d) for d in (1, 2, 2, 1)]
    )


# ---------------------------------------------------------------------------
# Elephant (32x32)
# ---------------------------------------------------------------------------

EL_GRAY, EL_EAR, EL_TUSK, EL_LINE = rgb("#8d8f97"), rgb("#b7a4a8"), rgb("#f3efe4"), rgb("#3c3d44")


def elephant_front(u, phase=0, hd=0, hx=0, blink=False, trumpet=False):
    a, b = lifts(phase)
    trunk_end = 26 if trumpet else 29
    parts = [
        Part((rect(8, 24 - b, 12, 30 - b), EL_GRAY), (rect(20, 24 - a, 24, 30 - a), EL_GRAY), outline=EL_LINE),
        Part((ell(16, 20, 9.5, 7), EL_GRAY), outline=EL_LINE),
        Part((rect(10, 23, 14, 30 - a), EL_GRAY), (rect(18, 23, 22, 30 - b), EL_GRAY), outline=EL_LINE),
        Part((ell(6 + hx, 14 + hd, 4.5, 6), EL_EAR), (ell(26 + hx, 14 + hd, 4.5, 6), EL_EAR), outline=EL_LINE),
        Part((ell(16 + hx, 13 + hd, 6.5, 6), EL_GRAY), outline=EL_LINE),
        Part((rect(15 + hx, 17 + hd, 17 + hx, trunk_end), EL_GRAY), (ell(16 + hx, trunk_end, 1.8, 1.6), EL_GRAY), outline=EL_LINE),
        Part((rect(12 + hx, 20 + hd, 14 + hx, 23 + hd), EL_TUSK), (rect(18 + hx, 20 + hd, 20 + hx, 23 + hd), EL_TUSK), outline=EL_LINE, shade=False),
        Part(*([] if blink else [(rect(12 + hx, 11 + hd, 13 + hx + u, 13 + hd), EL_LINE),
                                 (rect(19 + hx, 11 + hd, 20 + hx + u, 13 + hd), EL_LINE)]), shade=False),
    ]
    if DETAIL:
        parts.append(Part(
            (both(rect(15 + hx, 18 + hd, 17 + hx, trunk_end - 1), lambda x, y: y % 2.5 < 0.5), EL_LINE),
            (ell(4.5 + hx, 14 + hd, 1.5, 3.5), scaled(EL_EAR, 0.88)), (ell(27.5 + hx, 14 + hd, 1.5, 3.5), scaled(EL_EAR, 0.88)),
            (ell(11, 29.6 - a, 0.8, 0.45), EL_TUSK), (ell(13, 29.6 - a, 0.8, 0.45), EL_TUSK),
            (ell(19, 29.6 - b, 0.8, 0.45), EL_TUSK), (ell(21, 29.6 - b, 0.8, 0.45), EL_TUSK),
            shade=False,
        ))
    return parts


def elephant_side(u, phase=0, hd=0):
    a, b = lifts(phase)
    parts = [
        Part((rect(8, 24 - a, 12, 29 - a), EL_GRAY), (rect(18, 24 - b, 22, 29 - b), EL_GRAY), outline=EL_LINE),
        Part((ell(4, 18, 2, 2.2), EL_GRAY), outline=EL_LINE),
        Part((ell(13, 19, 10, 6.5), EL_GRAY), outline=EL_LINE),
        Part((rect(6, 23, 10, 30 - b), EL_GRAY), (rect(16, 23, 20, 30 - a), EL_GRAY), outline=EL_LINE),
        Part((ell(22, 14 + hd, 4, 6), EL_EAR), outline=EL_LINE),
        Part((ell(24.5, 14 + hd, 5.5, 5), EL_GRAY), outline=EL_LINE),
        Part((seg(27, 17 + hd, 29, 26, 2.4), EL_GRAY), (ell(29, 27, 1.8, 1.6), EL_GRAY), outline=EL_LINE),
        Part((rect(26, 18 + hd, 28, 22 + hd), EL_TUSK), outline=EL_LINE, shade=False),
        Part((rect(24, 12 + hd, 25 + u, 14 + hd), EL_LINE), shade=False),
    ]
    if DETAIL:
        parts.append(Part(
            (ell(22, 14 + hd, 2, 4), scaled(EL_EAR, 0.88)),
            (both(seg(27.3, 18 + hd, 29, 25, 1.4), lambda x, y: y % 2.5 < 0.5), EL_LINE),
            (ell(7, 29.6 - b, 0.8, 0.45), EL_TUSK), (ell(9, 29.6 - b, 0.8, 0.45), EL_TUSK),
            (ell(17, 29.6 - a, 0.8, 0.45), EL_TUSK), (ell(19, 29.6 - a, 0.8, 0.45), EL_TUSK),
            (both(ell(13, 19, 10, 6.5), lambda x, y: (x + y) % 5 < 0.35 and y > 15), scaled(EL_GRAY, 0.9)),
            shade=False,
        ))
    return parts


def elephant_back(u, phase=0, hx=0):
    a, b = lifts(phase)
    return [
        Part((ell(6 + hx, 13, 4.5, 6), EL_EAR), (ell(26 + hx, 13, 4.5, 6), EL_EAR), outline=EL_LINE),
        Part((ell(16 + hx, 12, 6, 5.5), EL_GRAY), outline=EL_LINE),
        Part((ell(16, 20, 9.5, 7), EL_GRAY), outline=EL_LINE),
        Part((rect(10, 23, 14, 30 - a), EL_GRAY), (rect(18, 23, 22, 30 - b), EL_GRAY), outline=EL_LINE),
        Part((ell(16, 26, 1.6, 1.4), EL_EAR), outline=EL_LINE),
    ]


def elephant_sleep(u):
    return [
        Part((ell(16, 24, 12, 5.5), EL_GRAY), outline=EL_LINE),
        Part((ell(8, 18, 5, 6), EL_EAR), outline=EL_LINE),
        Part((ell(16, 19, 7, 5), EL_GRAY), outline=EL_LINE),
        Part((seg(20, 20, 26, 24, 2.2), EL_GRAY), outline=EL_LINE),
        Part((rect(12, 17, 14, 18), EL_LINE), (rect(16, 17, 18, 18), EL_LINE), shade=False),
    ]


def elephant_frames(u):
    return (
        [elephant_front(u, p) for p in range(4)]
        + [elephant_side(u, p) for p in range(4)]
        + [elephant_back(u, p) for p in range(4)]
        + [elephant_sleep(u), elephant_front(u, trumpet=True), elephant_side(u, hd=2), elephant_back(u, hx=1)]
        + [elephant_front(u, hd=d, blink=d == 2) for d in (1, 2, 2, 1)]
    )


# ---------------------------------------------------------------------------
# Dinosaur (32x32) — T. rex silhouette
# ---------------------------------------------------------------------------

DN_BODY, DN_BELLY, DN_DARK, DN_LINE = rgb("#3f8f4a"), rgb("#c5d96a"), rgb("#24582c"), rgb("#143318")


def dino_front(u, phase=0, hd=0, hx=0, blink=False, roar=False):
    a, b = lifts(phase)
    mouth = 4.2 if roar else 2.8
    parts = [
        Part((rect(10, 24 - b, 13, 30 - b), DN_DARK), (rect(19, 24 - a, 22, 30 - a), DN_DARK), outline=DN_LINE),
        Part((ell(16, 23, 6.5, 5.5), DN_BODY), (both(ell(16, 23, 6.5, 5.5), lambda x, y: y > 24), DN_BELLY), outline=DN_LINE),
        Part((rect(12, 24, 15, 30 - a), DN_BODY), (rect(17, 24, 20, 30 - b), DN_BODY), outline=DN_LINE),
        Part((rect(12, 17, 13.5, 21), DN_BODY), (rect(18.5, 17, 20, 21), DN_BODY), outline=DN_LINE),
        Part((ell(16 + hx, 9 + hd, 7.5, 6.5), DN_BODY), outline=DN_LINE),
        Part((ell(16 + hx, 12 + hd, 5.2, mouth), DN_BELLY),
             *([] if blink else [(rect(12 + hx, 7 + hd, 13 + hx + u, 9 + hd), DN_LINE),
                                 (rect(19 + hx, 7 + hd, 20 + hx + u, 9 + hd), DN_LINE)]),
             (rect(15 + hx, 11 + hd, 17 + hx, 12 + hd + u), DN_DARK), shade=False),
    ]
    if DETAIL:
        teeth = [(rect(12.5 + hx + i * 1.4, 11.6 + hd, 13.1 + hx + i * 1.4, 12.4 + hd), rgb("#f6f2e2")) for i in range(5)]
        parts.append(Part(
            *teeth,
            (ell(11, 4.5 + hd + 0, 0.9, 0.7), DN_DARK), (ell(21, 4.5 + hd, 0.9, 0.7), DN_DARK),
            (ell(13, 21, 0.8, 0.6), DN_DARK), (ell(19, 21.5, 0.8, 0.6), DN_DARK),
            (rect(12, 29.4 - a, 15, 30 - a), rgb("#d8d2b0")), (rect(17, 29.4 - b, 20, 30 - b), rgb("#d8d2b0")),
            shade=False,
        ))
    return parts


def dino_side(u, phase=0, hd=0):
    a, b = lifts(phase)
    parts = [
        Part((rect(10, 24 - a, 13, 29 - a), DN_DARK), (rect(16, 24 - b, 19, 29 - b), DN_DARK), outline=DN_LINE),
        Part((seg(6, 20, 2, 14, 2.4), DN_BODY), (ell(2, 13, 2, 2.2), DN_BODY), outline=DN_LINE),
        Part((ell(13, 20, 8.5, 6), DN_BODY), (both(ell(13, 20, 8.5, 6), lambda x, y: y > 22), DN_BELLY), outline=DN_LINE),
        Part((rect(8, 23, 11, 30 - b), DN_BODY), (rect(15, 23, 18, 30 - a), DN_BODY), outline=DN_LINE),
        Part((rect(18, 16, 21, 20), DN_BODY), outline=DN_LINE),
        Part((ell(25, 12 + hd, 6, 5), DN_BODY), outline=DN_LINE),
        Part((ell(28.5, 13.5 + hd, 3.2, 2.4), DN_BELLY), (rect(23, 10 + hd, 24 + u, 12 + hd), DN_LINE),
             (rect(29, 13 + hd, 31, 14 + hd), DN_DARK), shade=False),
    ]
    if DETAIL:
        spots = [(ell(cx, cy, 0.9, 0.6), DN_DARK) for cx, cy in ((8, 16.5), (11, 15.3), (14, 15), (17, 15.8), (10, 18.5), (15, 18))]
        teeth = [(rect(26 + i * 1.3, 14.4 + hd, 26.6 + i * 1.3, 15.2 + hd), rgb("#f6f2e2")) for i in range(4)]
        parts.append(Part(
            *spots, *teeth,
            (rect(8, 29.4 - b, 11, 30 - b), rgb("#d8d2b0")), (rect(15, 29.4 - a, 18, 30 - a), rgb("#d8d2b0")),
            shade=False,
        ))
    return parts


def dino_back(u, phase=0, hx=0):
    a, b = lifts(phase)
    return [
        Part((ell(16 + hx, 11, 6, 5.5), DN_BODY), outline=DN_LINE),
        Part((ell(16, 21, 7.5, 6.5), DN_BODY), outline=DN_LINE),
        Part((rect(12, 24, 15, 30 - a), DN_BODY), (rect(17, 24, 20, 30 - b), DN_BODY), outline=DN_LINE),
        Part((seg(16, 24, 16, 29, 2), DN_BODY), (ell(16, 29.5, 1.6, 1.4), DN_DARK), outline=DN_LINE),
    ]


def dino_sleep(u):
    return [
        Part((ell(14, 24.5, 11, 5), DN_BODY), outline=DN_LINE),
        Part((seg(22, 23, 29, 20, 2.2), DN_BODY), outline=DN_LINE),
        Part((ell(10, 19, 6, 5), DN_BODY), outline=DN_LINE),
        Part((ell(8, 20, 3, 2), DN_BELLY), (rect(7, 17, 9, 18), DN_LINE), shade=False),
    ]


def dino_frames(u):
    return (
        [dino_front(u, p) for p in range(4)]
        + [dino_side(u, p) for p in range(4)]
        + [dino_back(u, p) for p in range(4)]
        + [dino_sleep(u), dino_front(u, roar=True), dino_side(u, hd=2), dino_back(u, hx=1)]
        + [dino_front(u, hd=d, blink=d == 2) for d in (1, 2, 2, 1)]
    )


# ---------------------------------------------------------------------------
# Gorilla (32x32)
# ---------------------------------------------------------------------------

GO_FUR, GO_SKIN, GO_LINE = rgb("#3a3a42"), rgb("#c48a62"), rgb("#16161a")


def gorilla_front(u, phase=0, hd=0, hx=0, blink=False, pound=False):
    a, b = lifts(phase)
    arm_y = 18 if pound else 22
    return [
        Part((rect(8, 24, 12, 30 - b), GO_SKIN), (rect(20, 24, 24, 30 - a), GO_SKIN), outline=GO_LINE),
        Part((ell(16, 20, 9, 7), GO_FUR), outline=GO_LINE),
        Part((rect(10, 23, 14, 30 - a), GO_FUR), (rect(18, 23, 22, 30 - b), GO_FUR), outline=GO_LINE),
        Part((ell(7, arm_y, 3.2, 5), GO_FUR), (ell(25, 22, 3.2, 5), GO_FUR), outline=GO_LINE),
        Part((ell(16 + hx, 11 + hd, 8, 7.5), GO_FUR), outline=GO_LINE),
        Part((ell(16 + hx, 13.5 + hd, 5.5, 4.8), GO_SKIN),
             *([] if blink else [(rect(12 + hx, 12 + hd, 13 + hx + u, 14 + hd), GO_LINE),
                                 (rect(19 + hx, 12 + hd, 20 + hx + u, 14 + hd), GO_LINE)]),
             (rect(15 + hx, 16 + hd, 17 + hx, 17 + hd + u), GO_LINE), shade=False),
    ]


def gorilla_side(u, phase=0, hd=0):
    a, b = lifts(phase)
    return [
        Part((rect(8, 24 - a, 12, 29 - a), GO_SKIN), (rect(18, 24 - b, 22, 29 - b), GO_SKIN), outline=GO_LINE),
        Part((ell(14, 19.5, 9.5, 6.5), GO_FUR), outline=GO_LINE),
        Part((rect(7, 23, 11, 30 - b), GO_FUR), (rect(16, 23, 20, 30 - a), GO_FUR), outline=GO_LINE),
        Part((ell(8, 20, 3, 4.5), GO_FUR), outline=GO_LINE),
        Part((ell(24, 13 + hd, 6.5, 6), GO_FUR), outline=GO_LINE),
        Part((ell(26.5, 15 + hd, 4, 3.6), GO_SKIN), (rect(24, 12 + hd, 25 + u, 14 + hd), GO_LINE),
             (rect(28, 16 + hd, 30, 17 + hd), GO_LINE), shade=False),
    ]


def gorilla_back(u, phase=0, hx=0):
    a, b = lifts(phase)
    return [
        Part((ell(16 + hx, 11, 8, 7), GO_FUR), outline=GO_LINE),
        Part((ell(16, 20, 9, 7.5), GO_FUR),
             *([(both(ell(16, 20, 9, 7.5), lambda x, y: y < 22 and abs(x - 16) < 6.5 - (22 - y) * 0.3), rgb("#9a9aa6"))]
               if DETAIL else []),
             outline=GO_LINE),
        Part((ell(7, 22, 3.2, 5), GO_FUR), (ell(25, 22, 3.2, 5), GO_FUR), outline=GO_LINE),
        Part((rect(10, 23, 14, 30 - a), GO_FUR), (rect(18, 23, 22, 30 - b), GO_FUR), outline=GO_LINE),
    ]


def gorilla_sleep(u):
    return [
        Part((ell(16, 24, 12, 5.5), GO_FUR), outline=GO_LINE),
        Part((ell(16, 19.5, 8, 6), GO_FUR), outline=GO_LINE),
        Part((ell(16, 21, 5, 3.5), GO_SKIN), (rect(12, 19, 14, 20), GO_LINE), (rect(18, 19, 20, 20), GO_LINE), shade=False),
    ]


def gorilla_frames(u):
    return (
        [gorilla_front(u, p) for p in range(4)]
        + [gorilla_side(u, p) for p in range(4)]
        + [gorilla_back(u, p) for p in range(4)]
        + [gorilla_sleep(u), gorilla_front(u, pound=True), gorilla_side(u, hd=2), gorilla_back(u, hx=1)]
        + [gorilla_front(u, hd=d, blink=d == 2) for d in (1, 2, 2, 1)]
    )


# ---------------------------------------------------------------------------
# Alpaca (32x32)
# ---------------------------------------------------------------------------

AL_WOOL, AL_FACE, AL_DARK, AL_LINE = rgb("#f0e6d2"), rgb("#e2c8a0"), rgb("#5a3a22"), rgb("#6b5340")


def alpaca_front(u, phase=0, hd=0, hx=0, blink=False, ear=0):
    a, b = lifts(phase)
    hy = 8 + hd
    return [
        Part((rect(10, 23 - b, 13, 30 - b), AL_FACE), (rect(19, 23 - a, 22, 30 - a), AL_FACE), outline=AL_LINE),
        Part((ell(16, 21, 8, 6), AL_WOOL), outline=AL_LINE),
        Part((rect(12, 22, 15, 30 - a), AL_WOOL), (rect(17, 22, 20, 30 - b), AL_WOOL), outline=AL_LINE),
        Part((rect(14, hy + 2, 18, 18), AL_WOOL), outline=AL_LINE),
        Part((ell(12 + hx, hy - 3 - ear, 1.6, 2.4), AL_WOOL), (ell(20 + hx, hy - 3 - ear, 1.6, 2.4), AL_WOOL), outline=AL_LINE),
        Part((ell(16 + hx, hy, 5, 4.2), AL_WOOL), outline=AL_LINE),
        Part((ell(16 + hx, hy + 2.4, 3.2, 2.4), AL_FACE),
             *([] if blink else [(rect(13 + hx, hy, 14 + hx + u, hy + u), AL_DARK),
                                 (rect(18 + hx, hy, 19 + hx + u, hy + u), AL_DARK)]),
             (rect(15 + hx, hy + 3, 17 + hx, hy + 3 + u), AL_DARK), shade=False),
    ]


def alpaca_side(u, phase=0, hd=0):
    a, b = lifts(phase)
    hy = 8 + hd
    return [
        Part((rect(8, 23 - a, 11, 29 - a), AL_FACE), (rect(18, 23 - b, 21, 29 - b), AL_FACE), outline=AL_LINE),
        Part((seg(5, 18, 3, 24, 1.3), AL_WOOL), outline=AL_LINE),
        Part((ell(13, 20, 9, 5.5), AL_WOOL), outline=AL_LINE),
        Part((rect(7, 22, 10, 30 - b), AL_WOOL), (rect(16, 22, 19, 30 - a), AL_WOOL), outline=AL_LINE),
        Part((seg(18, 17, 23, hy + 1, 3.6), AL_WOOL), outline=AL_LINE),
        Part((ell(22, hy - 3, 1.5, 2.2), AL_WOOL), outline=AL_LINE),
        Part((ell(25.5, hy, 4.6, 3.4), AL_WOOL), outline=AL_LINE),
        Part((ell(28.5, hy + 1.6, 2.4, 1.8), AL_FACE), (rect(24, hy, 25 + u, hy + u), AL_DARK), shade=False),
    ]


def alpaca_back(u, phase=0, hx=0):
    a, b = lifts(phase)
    return [
        Part((ell(12 + hx, 4, 1.6, 2.4), AL_WOOL), (ell(20 + hx, 4, 1.6, 2.4), AL_WOOL), outline=AL_LINE),
        Part((ell(16 + hx, 7, 5, 4), AL_WOOL), outline=AL_LINE),
        Part((rect(14, 10, 18, 18), AL_WOOL), outline=AL_LINE),
        Part((ell(16, 21, 8, 6), AL_WOOL), outline=AL_LINE),
        Part((rect(12, 23, 15, 30 - a), AL_WOOL), (rect(17, 23, 20, 30 - b), AL_WOOL), outline=AL_LINE),
        Part((seg(16, 24, 16, 28, 1.2), AL_WOOL), outline=AL_LINE),
    ]


def alpaca_sleep(u):
    hy = 12
    return [
        Part((ell(16, 25, 11, 4.5), AL_WOOL), outline=AL_LINE),
        Part((rect(14, hy + 1, 18, 23), AL_WOOL), outline=AL_LINE),
        Part((ell(12, hy - 3, 1.6, 2.2), AL_WOOL), (ell(20, hy - 3, 1.6, 2.2), AL_WOOL), outline=AL_LINE),
        Part((ell(16, hy, 5, 4.2), AL_WOOL), outline=AL_LINE),
        Part((ell(16, hy + 2.4, 3.2, 2.4), AL_FACE), (rect(13, hy, 15, hy + u), AL_DARK),
             (rect(17, hy, 19, hy + u), AL_DARK), shade=False),
    ]


def alpaca_frames(u):
    return (
        [alpaca_front(u, p) for p in range(4)]
        + [alpaca_side(u, p) for p in range(4)]
        + [alpaca_back(u, p) for p in range(4)]
        + [alpaca_sleep(u), alpaca_front(u, ear=2, blink=True), alpaca_side(u, hd=3), alpaca_back(u, hx=1)]
        + [alpaca_front(u, hd=d) for d in (2, 4, 4, 2)]
    )


# ---------------------------------------------------------------------------
# Sea lion (32x32)
# ---------------------------------------------------------------------------

SL_BODY, SL_BELLY, SL_LINE = rgb("#6b4a36"), rgb("#c4a07a"), rgb("#2a1810")


def sealion_front(u, phase=0, hd=0, hx=0, blink=False, bark=False):
    a, b = lifts(phase)
    fy = 18 - a
    snout = 4.2 if bark else 3.4
    return [
        Part((ell(6, fy, 4.5, 3.2), SL_BODY), (ell(26, 18 - b, 4.5, 3.2), SL_BODY), outline=SL_LINE),
        Part((ell(16, 21, 8, 6.5), SL_BODY), (both(ell(16, 21, 8, 6.5), lambda x, y: y > 23), SL_BELLY), outline=SL_LINE),
        Part((ell(16 + hx, 12 + hd, 5.5, 5), SL_BODY), outline=SL_LINE),
        Part((ell(16 + hx, 16 + hd, snout, 2.6), SL_BELLY),
             (rect(11 + hx, 16 + hd, 12 + hx, 16 + hd + u), SL_LINE),
             (rect(20 + hx, 16 + hd, 21 + hx, 16 + hd + u), SL_LINE),
             *([] if blink else [(rect(13 + hx, 10 + hd, 14 + hx + u, 12 + hd), SL_LINE),
                                 (rect(18 + hx, 10 + hd, 19 + hx + u, 12 + hd), SL_LINE)]),
             (rect(15 + hx, 15 + hd, 17 + hx, 16 + hd), SL_LINE), shade=False),
        Part((ell(11, 27, 3.5, 2), SL_BODY), (ell(21, 27, 3.5, 2), SL_BODY), outline=SL_LINE),
    ]


def sealion_side(u, phase=0, hd=0):
    a, b = lifts(phase)
    return [
        Part((ell(6, 20 - a, 3, 4.5), SL_BODY), (ell(16, 22 - b, 4, 3.5), SL_BODY), outline=SL_LINE),
        Part((ell(14, 19, 10, 6), SL_BODY), (both(ell(14, 19, 10, 6), lambda x, y: y > 21), SL_BELLY), outline=SL_LINE),
        Part((ell(4, 18, 2.4, 2), SL_BODY), outline=SL_LINE),
        Part((ell(25, 14 + hd, 6, 5), SL_BODY), outline=SL_LINE),
        Part((ell(28.5, 15.5 + hd, 3, 2.2), SL_BELLY), (rect(24, 12 + hd, 25 + u, 14 + hd), SL_LINE),
             (rect(29, 15 + hd, 31, 16 + hd), SL_LINE), shade=False),
        Part((rect(20, 24, 26, 27), SL_BODY), outline=SL_LINE),
    ]


def sealion_back(u, phase=0, hx=0):
    a, b = lifts(phase)
    return [
        Part((ell(16 + hx, 11, 6, 5.5), SL_BODY), outline=SL_LINE),
        Part((ell(16, 20, 8.5, 7), SL_BODY), outline=SL_LINE),
        Part((ell(8, 18, 3.5, 5), SL_BODY), (ell(24, 18, 3.5, 5), SL_BODY), outline=SL_LINE),
        Part((ell(16, 27, 3, 2), SL_BODY), outline=SL_LINE),
    ]


def sealion_sleep(u):
    return [
        Part((ell(16, 23, 12, 5.5), SL_BODY), outline=SL_LINE),
        Part((ell(16, 20, 7, 5), SL_BODY), outline=SL_LINE),
        Part((ell(16, 21, 4, 2.4), SL_BELLY), (rect(12, 18, 14, 19), SL_LINE), (rect(18, 18, 20, 19), SL_LINE), shade=False),
    ]


def sealion_frames(u):
    return (
        [sealion_front(u, p) for p in range(4)]
        + [sealion_side(u, p) for p in range(4)]
        + [sealion_back(u, p) for p in range(4)]
        + [sealion_sleep(u), sealion_front(u, bark=True), sealion_side(u, hd=2), sealion_back(u, hx=1)]
        + [sealion_front(u, hd=d, blink=d == 2) for d in (1, 2, 2, 1)]
    )


# ---------------------------------------------------------------------------
# Bear (32x32)
# ---------------------------------------------------------------------------

BR_FUR, BR_SN, BR_LINE = rgb("#6a3e24"), rgb("#c9a07a"), rgb("#2c160c")


BR_CLAW = rgb("#e8dcc4")


def bear_claws(feet):
    return Part(*[(rect(x0 + 0.4 + i * 1.1, y - 0.7, x0 + 0.9 + i * 1.1, y), BR_CLAW) for x0, y in feet for i in range(3)],
                shade=False)


def bear_front(u, phase=0, hd=0, hx=0, blink=False):
    a, b = lifts(phase)
    claws = [bear_claws([(10, 30 - a), (18, 30 - b)])] if DETAIL else []
    return [
        Part((rect(8, 24 - b, 12, 30 - b), BR_FUR), (rect(20, 24 - a, 24, 30 - a), BR_FUR), outline=BR_LINE),
        Part((ell(16, 21, 9.5, 7), BR_FUR), outline=BR_LINE),
        Part((rect(10, 23, 14, 30 - a), BR_FUR), (rect(18, 23, 22, 30 - b), BR_FUR), outline=BR_LINE),
        Part((ell(10 + hx, 7 + hd, 2.4, 2.4), BR_FUR), (ell(22 + hx, 7 + hd, 2.4, 2.4), BR_FUR), outline=BR_LINE),
        Part((ell(16 + hx, 13 + hd, 7.5, 6.5), BR_FUR), outline=BR_LINE),
        Part((ell(16 + hx, 16 + hd, 3.8, 2.8), BR_SN),
             *([] if blink else [(rect(12 + hx, 12 + hd, 13 + hx + u, 14 + hd), BR_LINE),
                                 (rect(19 + hx, 12 + hd, 20 + hx + u, 14 + hd), BR_LINE)]),
             (rect(15 + hx, 16 + hd, 17 + hx, 17 + hd + u), BR_LINE), shade=False),
    ] + claws


def bear_side(u, phase=0, hd=0):
    a, b = lifts(phase)
    return [
        Part((rect(8, 24 - a, 12, 29 - a), BR_FUR), (rect(18, 24 - b, 22, 29 - b), BR_FUR), outline=BR_LINE),
        Part((ell(5, 18, 2, 1.8), BR_FUR), outline=BR_LINE),
        Part((ell(14, 19.5, 10, 6.5), BR_FUR), outline=BR_LINE),
        Part((rect(7, 23, 11, 30 - b), BR_FUR), (rect(16, 23, 20, 30 - a), BR_FUR), outline=BR_LINE),
        Part((ell(23, 9 + hd, 2.2, 2.2), BR_FUR), outline=BR_LINE),
        Part((ell(25, 14 + hd, 6, 5.5), BR_FUR), outline=BR_LINE),
        Part((ell(28.5, 16 + hd, 3.2, 2.4), BR_SN), (rect(24, 12 + hd, 25 + u, 14 + hd), BR_LINE),
             (rect(29, 16 + hd, 31, 17 + hd), BR_LINE), shade=False),
    ] + ([bear_claws([(7.6, 30 - b), (16.6, 30 - a)])] if DETAIL else [])


def bear_back(u, phase=0, hx=0):
    a, b = lifts(phase)
    return [
        Part((ell(10 + hx, 7, 2.4, 2.4), BR_FUR), (ell(22 + hx, 7, 2.4, 2.4), BR_FUR), outline=BR_LINE),
        Part((ell(16 + hx, 13, 7.5, 6.5), BR_FUR), outline=BR_LINE),
        Part((ell(16, 21, 9.5, 7), BR_FUR), outline=BR_LINE),
        Part((rect(10, 23, 14, 30 - a), BR_FUR), (rect(18, 23, 22, 30 - b), BR_FUR), outline=BR_LINE),
        Part((ell(16, 26, 1.8, 1.5), BR_FUR), outline=BR_LINE),
    ]


def bear_sleep(u):
    return [
        Part((ell(16, 24, 12, 5.5), BR_FUR), outline=BR_LINE),
        Part((ell(10, 16, 2.4, 2.4), BR_FUR), (ell(22, 16, 2.4, 2.4), BR_FUR), outline=BR_LINE),
        Part((ell(16, 19, 7.5, 6), BR_FUR), outline=BR_LINE),
        Part((ell(16, 21, 3.8, 2.6), BR_SN), (rect(12, 18, 14, 19), BR_LINE), (rect(18, 18, 20, 19), BR_LINE), shade=False),
    ]


def bear_frames(u):
    return (
        [bear_front(u, p) for p in range(4)]
        + [bear_side(u, p) for p in range(4)]
        + [bear_back(u, p) for p in range(4)]
        + [bear_sleep(u), bear_front(u, hd=1, blink=True), bear_side(u, hd=2), bear_back(u, hx=1)]
        + [bear_front(u, hd=d) for d in (1, 2, 2, 1)]
    )


# ---------------------------------------------------------------------------
# Flamingo (32x32) — pink, long legs, curved beak
# ---------------------------------------------------------------------------

FL_PINK, FL_DARK, FL_WING, FL_BEAK = rgb("#f48fb1"), rgb("#ec407a"), rgb("#e91e8c"), rgb("#f6c177")
FL_LEG, FL_LINE = rgb("#5a2e22"), rgb("#6b1d4a")


def flamingo_front(u, phase=0, hd=0, hx=0, blink=False, one_leg=False):
    a, b = lifts(phase)
    return [
        Part((rect(14, 18, 15, 22 if one_leg else 30 - b), FL_LEG),
             (rect(18, 18, 19, 30 - a), FL_LEG), outline=FL_LINE, shade=False),
        Part((ell(16, 16, 5.4, 4.2), FL_PINK), (both(ell(16, 16, 5.4, 4.2), lambda x, y: y > 17), FL_DARK), outline=FL_LINE),
        Part((seg(16 + hx, 12, 16 + hx, 7 + hd, 2.2), FL_PINK), outline=FL_LINE),
        Part((ell(16 + hx, 5.2 + hd, 3, 2.6), FL_PINK), outline=FL_LINE),
        Part((seg(17 + hx, 6.2 + hd, 22 + hx, 9.5 + hd, 1.7), FL_BEAK),
             (ell(22.5 + hx, 10 + hd, 1.5, 1.1), FL_DARK), outline=FL_LINE),
        Part(*([] if blink else [(rect(14 + hx, 4.5 + hd, 15 + hx, 5.5 + hd), FL_LINE),
                                 (rect(17 + hx, 4.5 + hd, 18 + hx, 5.5 + hd), FL_LINE)]), shade=False),
    ]


def flamingo_side(u, phase=0, hd=0):
    a, b = lifts(phase)
    return [
        Part((rect(13, 19, 14, 29 - a), FL_LEG), (rect(16, 19, 17, 30 - b), FL_LEG), outline=FL_LINE, shade=False),
        Part((ell(14, 17.5, 7, 4.4), FL_PINK), (both(ell(14, 17.5, 7, 4.4), lambda x, y: x < 10), FL_WING), outline=FL_LINE),
        Part((seg(18, 15, 23, 8 + hd, 2.4), FL_PINK), outline=FL_LINE),
        Part((ell(24, 7 + hd, 3, 2.6), FL_PINK), outline=FL_LINE),
        Part((seg(25, 8 + hd, 30, 11 + hd, 1.7), FL_BEAK), (ell(30, 11.5 + hd, 1.5, 1.1), FL_DARK), outline=FL_LINE),
        Part((rect(23, 6 + hd, 24, 7 + hd), FL_LINE), shade=False),
    ]


def flamingo_back(u, phase=0, hx=0):
    a, b = lifts(phase)
    return [
        Part((ell(16 + hx, 6.5, 3, 2.6), FL_PINK), outline=FL_LINE),
        Part((rect(15, 8, 17, 14), FL_PINK), outline=FL_LINE),
        Part((ell(16, 18, 6.2, 5), FL_PINK), outline=FL_LINE),
        Part((rect(14, 21, 16, 30 - a), FL_LEG), (rect(17, 21, 19, 30 - b), FL_LEG), outline=FL_LINE, shade=False),
    ]


def flamingo_sleep(u):
    return [
        Part((ell(14, 26, 3, 1.6), FL_LEG), (ell(20, 26, 3, 1.6), FL_LEG), outline=FL_LINE),
        Part((ell(16, 22, 8, 4.2), FL_PINK), outline=FL_LINE),
        Part((seg(20, 20, 24, 18, 2.2), FL_PINK), outline=FL_LINE),
        Part((ell(25, 17, 3, 2.4), FL_PINK), outline=FL_LINE),
        Part((seg(26, 18, 29, 20, 1.5), FL_BEAK), outline=FL_LINE),
        Part((rect(23, 16, 25, 17), FL_LINE), shade=False),
    ]


def flamingo_frames(u):
    return (
        [flamingo_front(u, p) for p in range(4)]
        + [flamingo_side(u, p) for p in range(4)]
        + [flamingo_back(u, p) for p in range(4)]
        + [flamingo_sleep(u), flamingo_front(u, one_leg=True), flamingo_side(u, hd=2), flamingo_back(u, hx=1)]
        + [flamingo_front(u, hd=d, blink=d == 2) for d in (1, 2, 2, 1)]
    )


# ---------------------------------------------------------------------------
# Owl (16x16) — round head, ear tufts, big eyes
# ---------------------------------------------------------------------------

OW_BROWN, OW_CREAM, OW_EYE, OW_LINE = rgb("#7a4e28"), rgb("#f0e0c0"), rgb("#f4d35e"), rgb("#2c160c")
OW_TUFT, OW_BELLY = rgb("#5a3318"), rgb("#ead9b8")


def owl_front(phase=0, hd=0, blink=False, wings=False):
    a, b = lifts(phase)
    fx = 1.4 if wings else 0
    return [
        Part((rect(5, 14 - a, 7, 15 - a), OW_TUFT), (rect(9, 14 - b, 11, 15 - b), OW_TUFT), outline=OW_LINE, shade=False),
        Part((ell(8, 10.5, 4.6, 4), OW_BROWN), outline=OW_LINE),
        Part((ell(3.4 - fx, 10, 1.4, 2.4), OW_BROWN), (ell(12.6 + fx, 10, 1.4, 2.4), OW_BROWN), outline=OW_LINE),
        Part((ell(8, 6.2 + hd, 4.8, 4.2), OW_BROWN), outline=OW_LINE),
        Part((ell(4.2, 3.2 + hd, 1.3, 1.6), OW_TUFT), (ell(11.8, 3.2 + hd, 1.3, 1.6), OW_TUFT), outline=OW_LINE),
        Part((ell(8, 7 + hd, 3.6, 3), OW_CREAM), shade=False),
        Part(
            *([] if blink else [
                (ell(6, 6.6 + hd, 1.5, 1.6), OW_EYE), (ell(10, 6.6 + hd, 1.5, 1.6), OW_EYE),
                (rect(6, 6 + hd, 7, 8 + hd), OW_LINE), (rect(10, 6 + hd, 11, 8 + hd), OW_LINE),
            ]),
            (rect(7, 8.5 + hd, 9, 9.5 + hd), rgb("#d97706")),
            shade=False,
        ),
    ]


def owl_side(phase=0, hd=0):
    a, b = lifts(phase)
    return [
        Part((rect(7, 14 - a, 9, 15 - a), OW_TUFT), (rect(9, 14 - b, 11, 15 - b), OW_TUFT), outline=OW_LINE, shade=False),
        Part((ell(8, 10.5, 4.2, 4), OW_BROWN), outline=OW_LINE),
        Part((ell(11, 6.2 + hd, 3.6, 3.6), OW_BROWN), outline=OW_LINE),
        Part((ell(11.5, 3.4 + hd, 1.2, 1.5), OW_TUFT), outline=OW_LINE),
        Part((ell(12.2, 6.8 + hd, 2.2, 2.2), OW_CREAM), (ell(12.4, 6.6 + hd, 1.2, 1.3), OW_EYE),
             (rect(12, 6 + hd, 13, 8 + hd), OW_LINE), (rect(13, 8 + hd, 15, 9 + hd), rgb("#d97706")), shade=False),
        Part((ell(5.5, 10.5, 1.4, 2.2), OW_BROWN), shade=False),
    ]


def owl_back(phase=0):
    a, b = lifts(phase)
    return [
        Part((ell(4.2, 3.2, 1.3, 1.6), OW_TUFT), (ell(11.8, 3.2, 1.3, 1.6), OW_TUFT), outline=OW_LINE),
        Part((ell(8, 6.2, 4.8, 4.2), OW_BROWN), outline=OW_LINE),
        Part((ell(8, 10.5, 4.6, 4), OW_BROWN), outline=OW_LINE),
        Part((rect(5, 14 - a, 7, 15 - a), OW_TUFT), (rect(9, 14 - b, 11, 15 - b), OW_TUFT), outline=OW_LINE, shade=False),
    ]


def owl_sleep():
    return [
        Part((ell(8, 12, 5.2, 3.2), OW_BROWN), outline=OW_LINE),
        Part((ell(8, 9.2, 4.2, 3.2), OW_BROWN), outline=OW_LINE),
        Part((ell(4.4, 7.2, 1.2, 1.4), OW_TUFT), (ell(11.6, 7.2, 1.2, 1.4), OW_TUFT), outline=OW_LINE),
        Part((ell(8, 9.5, 3, 2), OW_CREAM), (rect(6, 9, 7, 10), OW_LINE), (rect(9, 9, 10, 10), OW_LINE),
             (rect(7, 10, 9, 11), rgb("#d97706")), shade=False),
    ]


def owl_frames():
    return (
        [owl_front(p) for p in range(4)]
        + [owl_side(p) for p in range(4)]
        + [owl_back(p) for p in range(4)]
        + [owl_sleep(), owl_front(wings=True), owl_side(hd=1), owl_back()]
        + [owl_front(hd=d, blink=d == 1) for d in (0, 1, 1, 0)]
    )


# ---------------------------------------------------------------------------
# Deer (32x32) — antlers, slender legs
# ---------------------------------------------------------------------------

DE_COAT, DE_BELLY, DE_DARK, DE_LINE = rgb("#c68642"), rgb("#f1d6b0"), rgb("#6b3e1c"), rgb("#4a2410")
DE_ANTLER = rgb("#8d6e4c")


def deer_antlers(hx, hy):
    return Part(
        (seg(13 + hx, hy - 1, 10 + hx, hy - 8, 1.2), DE_ANTLER),
        (seg(10 + hx, hy - 5, 7 + hx, hy - 8, 1.1), DE_ANTLER),
        (seg(11 + hx, hy - 4, 13 + hx, hy - 7, 1.0), DE_ANTLER),
        (seg(19 + hx, hy - 1, 22 + hx, hy - 8, 1.2), DE_ANTLER),
        (seg(22 + hx, hy - 5, 25 + hx, hy - 8, 1.1), DE_ANTLER),
        (seg(21 + hx, hy - 4, 19 + hx, hy - 7, 1.0), DE_ANTLER),
        outline=DE_LINE,
    )


def deer_front(u, phase=0, hd=0, hx=0, blink=False, ear=0):
    a, b = lifts(phase)
    hy = 9 + hd
    return [
        Part((rect(11, 22, 13, 30 - b), DE_COAT), (rect(19, 22, 21, 30 - a), DE_COAT), outline=DE_LINE),
        Part((ell(16, 20, 7.5, 5.5), DE_COAT), (both(ell(16, 20, 7.5, 5.5), lambda x, y: y > 21.5), DE_BELLY),
             (ell(13, 18, 0.8, 0.8), DE_BELLY), (ell(19, 18.5, 0.8, 0.8), DE_BELLY), outline=DE_LINE),
        Part((rect(13, 21, 15, 30 - a), DE_COAT), (rect(17, 21, 19, 30 - b), DE_COAT), outline=DE_LINE),
        Part((rect(14.5, hy + 3, 17.5, 17), DE_COAT), outline=DE_LINE),
        deer_antlers(hx, hy),
        Part((ell(12.2 + hx, hy - 1 - ear, 1.6, 1.8), DE_COAT), (ell(19.8 + hx, hy - 1 - ear, 1.6, 1.8), DE_COAT), outline=DE_LINE),
        Part((ell(16 + hx, hy + 1, 4.4, 4), DE_COAT), outline=DE_LINE),
        Part((ell(16 + hx, hy + 3.4, 2.6, 2), DE_BELLY),
             *([] if blink else [(rect(13.5 + hx, hy, 14.5 + hx, hy + u), DE_LINE),
                                 (rect(17.5 + hx, hy, 18.5 + hx, hy + u), DE_LINE)]),
             (rect(15 + hx, hy + 3, 17 + hx, hy + 4), DE_DARK), shade=False),
    ]


def deer_side(u, phase=0, hd=0):
    a, b = lifts(phase)
    hy = 9 + hd
    return [
        Part((rect(8, 22, 10, 29 - a), DE_COAT), (rect(18, 22, 20, 29 - b), DE_COAT), outline=DE_LINE),
        Part((seg(5, 17, 3, 24, 1.2), DE_COAT), (ell(3, 25, 1.2, 1.4), DE_DARK), outline=DE_LINE),
        Part((ell(13, 19, 8.5, 5), DE_COAT), (both(ell(13, 19, 8.5, 5), lambda x, y: y > 21), DE_BELLY), outline=DE_LINE),
        Part((rect(7, 21, 9, 30 - b), DE_COAT), (rect(16, 21, 18, 30 - a), DE_COAT), outline=DE_LINE),
        Part((seg(18, 16, 23, hy + 2, 3.2), DE_COAT), outline=DE_LINE),
        Part((seg(22, hy - 1, 24, hy - 8, 1.2), DE_ANTLER),
             (seg(23, hy - 4, 27, hy - 6, 1.1), DE_ANTLER),
             (seg(24, hy - 6, 26, hy - 9, 1.0), DE_ANTLER), outline=DE_LINE),
        Part((ell(21.5, hy - 1, 1.5, 1.6), DE_COAT), outline=DE_LINE),
        Part((ell(25.5, hy + 1, 4.2, 3.4), DE_COAT), outline=DE_LINE),
        Part((ell(28.4, hy + 2.4, 2.2, 1.8), DE_BELLY), (rect(24, hy, 25, hy + u), DE_LINE),
             (rect(29, hy + 2, 31, hy + 3), DE_DARK), shade=False),
    ]


def deer_back(u, phase=0, hx=0):
    a, b = lifts(phase)
    return [
        deer_antlers(hx, 8),
        Part((ell(12.2 + hx, 7, 1.6, 1.8), DE_COAT), (ell(19.8 + hx, 7, 1.6, 1.8), DE_COAT), outline=DE_LINE),
        Part((ell(16 + hx, 9, 4.2, 3.6), DE_COAT), outline=DE_LINE),
        Part((rect(14.5, 12, 17.5, 18), DE_COAT), outline=DE_LINE),
        Part((ell(16, 20.5, 7.5, 5.5), DE_COAT), outline=DE_LINE),
        Part((rect(12, 22, 14, 30 - a), DE_COAT), (rect(18, 22, 20, 30 - b), DE_COAT), outline=DE_LINE),
        Part((seg(16, 24, 16, 28, 1.2), DE_COAT), (ell(16, 28.5, 1.3, 1.2), DE_DARK), outline=DE_LINE),
    ]


def deer_sleep(u):
    hy = 14
    return [
        Part((ell(16, 25.5, 11, 4.4), DE_COAT), outline=DE_LINE),
        Part((rect(14, hy + 2, 18, 23), DE_COAT), outline=DE_LINE),
        deer_antlers(0, hy),
        Part((ell(12, hy - 1, 1.6, 1.6), DE_COAT), (ell(20, hy - 1, 1.6, 1.6), DE_COAT), outline=DE_LINE),
        Part((ell(16, hy + 1, 4.4, 4), DE_COAT), outline=DE_LINE),
        Part((ell(16, hy + 3.4, 2.6, 2), DE_BELLY), (rect(13.5, hy, 15.5, hy + u), DE_LINE),
             (rect(16.5, hy, 18.5, hy + u), DE_LINE), shade=False),
    ]


def deer_frames(u):
    return (
        [deer_front(u, p) for p in range(4)]
        + [deer_side(u, p) for p in range(4)]
        + [deer_back(u, p) for p in range(4)]
        + [deer_sleep(u), deer_front(u, ear=1, blink=True), deer_side(u, hd=2), deer_back(u, hx=1)]
        + [deer_front(u, hd=d) for d in (1, 2, 2, 1)]
    )


# ---------------------------------------------------------------------------
# Night heron (32x32) — stocky, dark cap, long bill
# ---------------------------------------------------------------------------

NH_GRAY, NH_CAP, NH_CREAM, NH_BILL = rgb("#8d99ae"), rgb("#1d2433"), rgb("#efe6d2"), rgb("#2b2d42")
NH_LEG, NH_LINE = rgb("#e9c46a"), rgb("#14161f")


def heron_front(u, phase=0, hd=0, hx=0, blink=False, strike=False):
    a, b = lifts(phase)
    bill_y = 14 + hd if strike else 12 + hd
    return [
        Part((rect(13, 22, 15, 30 - b), NH_LEG), (rect(17, 22, 19, 30 - a), NH_LEG), outline=NH_LINE, shade=False),
        Part((ell(16, 20, 7, 6), NH_GRAY), (both(ell(16, 20, 7, 6), lambda x, y: y > 21), NH_CREAM), outline=NH_LINE),
        Part((rect(15, 12 + hd, 17, 16), NH_GRAY), outline=NH_LINE),
        Part((ell(16 + hx, 9 + hd, 5.2, 4.6), NH_GRAY), outline=NH_LINE),
        Part((ell(16 + hx, 8 + hd, 5, 3.2), NH_CAP), outline=NH_LINE),
        Part((ell(16 + hx, 10.5 + hd, 4, 2.6), NH_CREAM),
             *([] if blink else [(rect(13 + hx, 9 + hd, 14 + hx, 11 + hd), NH_LINE),
                                 (rect(18 + hx, 9 + hd, 19 + hx, 11 + hd), NH_LINE)]), shade=False),
        Part((rect(15 + hx, 11 + hd, 17 + hx, bill_y + 6), NH_BILL), (ell(16 + hx, bill_y + 6, 1.4, 1.2), NH_BILL), outline=NH_LINE),
    ]


def heron_side(u, phase=0, hd=0):
    a, b = lifts(phase)
    return [
        Part((rect(12, 22, 14, 29 - a), NH_LEG), (rect(16, 22, 18, 30 - b), NH_LEG), outline=NH_LINE, shade=False),
        Part((ell(13, 19, 7.5, 5.5), NH_GRAY), (both(ell(13, 19, 7.5, 5.5), lambda x, y: y > 21), NH_CREAM), outline=NH_LINE),
        Part((seg(18, 16, 22, 11 + hd, 3), NH_GRAY), outline=NH_LINE),
        Part((ell(23.5, 10 + hd, 4.4, 3.8), NH_GRAY), outline=NH_LINE),
        Part((ell(23.5, 8.8 + hd, 4.2, 2.4), NH_CAP), outline=NH_LINE),
        Part((ell(25.5, 11 + hd, 2.6, 2), NH_CREAM), (rect(24, 9 + hd, 25, 11 + hd), NH_LINE), shade=False),
        Part((seg(26, 11.5 + hd, 31.5, 12.5 + hd, 1.8), NH_BILL), outline=NH_LINE),
        Part((ell(8, 18, 2.2, 3.5), NH_GRAY), outline=NH_LINE),
    ]


def heron_back(u, phase=0, hx=0):
    a, b = lifts(phase)
    return [
        Part((ell(16 + hx, 9, 5.2, 4.6), NH_CAP), outline=NH_LINE),
        Part((rect(15, 13, 17, 16), NH_GRAY), outline=NH_LINE),
        Part((ell(16, 20, 7, 6), NH_GRAY), outline=NH_LINE),
        Part((ell(8, 18, 2.2, 3.5), NH_GRAY), (ell(24, 18, 2.2, 3.5), NH_GRAY), outline=NH_LINE),
        Part((rect(13, 22, 15, 30 - a), NH_LEG), (rect(17, 22, 19, 30 - b), NH_LEG), outline=NH_LINE, shade=False),
    ]


def heron_sleep(u):
    return [
        Part((ell(12, 26, 3, 1.6), NH_LEG), (ell(20, 26, 3, 1.6), NH_LEG), outline=NH_LINE),
        Part((ell(16, 22, 8, 4.5), NH_GRAY), outline=NH_LINE),
        Part((ell(22, 18, 5, 4), NH_GRAY), outline=NH_LINE),
        Part((ell(22, 16.5, 4.4, 2.2), NH_CAP), outline=NH_LINE),
        Part((ell(24, 18.5, 2.4, 1.8), NH_CREAM), (rect(25, 18, 30, 19), NH_BILL), shade=False),
    ]


def heron_frames(u):
    return (
        [heron_front(u, p) for p in range(4)]
        + [heron_side(u, p) for p in range(4)]
        + [heron_back(u, p) for p in range(4)]
        + [heron_sleep(u), heron_front(u, strike=True), heron_side(u, hd=2), heron_back(u, hx=1)]
        + [heron_front(u, hd=d, blink=d == 2) for d in (1, 2, 2, 1)]
    )


# ---------------------------------------------------------------------------
# Flight sheets ({Name}Fly.png): fly down, fly right, fly up, perch — 4 frames each
# ---------------------------------------------------------------------------

FLAP = (-4.0, -1.5, 2.5, -1.5)          # wing-tip offset per frame: up, mid, down, mid
BRANCH, BRANCH_LINE = rgb("#7a5230"), rgb("#3a2414")
OW_BEAK = rgb("#d97706")


def owl_fly_front(phase, back=False):
    off = FLAP[phase]
    left, right = seg(6, 9, 0.8, 9 + off, 3.2), seg(10, 9, 15.2, 9 + off, 3.2)
    parts = [
        Part((left, OW_BROWN), (right, OW_BROWN),
             (both(left, lambda x, y: x < 2.6), OW_TUFT), (both(right, lambda x, y: x > 13.4), OW_TUFT), outline=OW_LINE),
        Part((ell(8, 10, 3.4, 3.6), OW_BROWN), outline=OW_LINE),
        Part((ell(8, 6, 4, 3.4), OW_BROWN), outline=OW_LINE),
        Part((ell(5, 3.2, 1.1, 1.4), OW_TUFT), (ell(11, 3.2, 1.1, 1.4), OW_TUFT), outline=OW_LINE),
    ]
    if back:
        parts.append(Part((rect(7, 12.5, 9, 14.5), OW_TUFT), outline=OW_LINE))
    else:
        parts += [
            Part((ell(8, 6.8, 3, 2.4), OW_CREAM), (ell(8, 11, 2, 2), OW_BELLY), shade=False),
            Part((ell(6.3, 6.5, 1.2, 1.3), OW_EYE), (ell(9.7, 6.5, 1.2, 1.3), OW_EYE),
                 (rect(6, 6, 7, 7), OW_LINE), (rect(9, 6, 10, 7), OW_LINE), (rect(7.5, 8, 8.5, 9), OW_BEAK), shade=False),
        ]
    return parts


def owl_fly_side(phase):
    off = FLAP[phase]
    near = seg(8, 8.5, 4.5, 8.5 + off * 1.2, 3.4)
    return [
        Part((seg(7.5, 8.5, 5, 8.5 + off * 0.8, 3), scaled(OW_BROWN, 0.75)), outline=OW_LINE),
        Part((ell(7.5, 9.5, 4.6, 3), OW_BROWN), (rect(2, 9, 4, 10.5), OW_TUFT), outline=OW_LINE),
        Part((ell(11.5, 7, 3, 3), OW_BROWN), (ell(11.6, 4.4, 1, 1.3), OW_TUFT), outline=OW_LINE),
        Part((ell(12.6, 7.4, 1.9, 1.9), OW_CREAM), (ell(12.8, 7.2, 1, 1.1), OW_EYE), (rect(12.5, 7, 13.5, 8), OW_LINE),
             (rect(14, 8, 15, 9), OW_BEAK), shade=False),
        Part((near, OW_BROWN), (both(near, lambda x, y: x < 6), OW_TUFT), outline=OW_LINE),
    ]


def owl_perch(blink=False, hx=0):
    return [
        Part((ell(8, 10.6, 4.4, 4), OW_BROWN), outline=OW_LINE),
        Part((ell(8, 11.4, 2.8, 2.8), OW_BELLY), shade=False),
        Part((ell(8 + hx * 0.5, 6.2, 4.6, 4), OW_BROWN), outline=OW_LINE),
        Part((ell(4.2 + hx * 0.5, 3.2, 1.3, 1.6), OW_TUFT), (ell(11.8 + hx * 0.5, 3.2, 1.3, 1.6), OW_TUFT), outline=OW_LINE),
        Part((ell(8 + hx, 7, 3.4, 2.8), OW_CREAM), shade=False),
        Part(*([(rect(5 + hx, 6.5, 7 + hx, 7.5), OW_LINE), (rect(9 + hx, 6.5, 11 + hx, 7.5), OW_LINE)] if blink else [
                (ell(6 + hx, 6.6, 1.5, 1.6), OW_EYE), (ell(10 + hx, 6.6, 1.5, 1.6), OW_EYE),
                (rect(6 + hx, 6, 7 + hx, 8), OW_LINE), (rect(10 + hx, 6, 11 + hx, 8), OW_LINE)]),
             (rect(7 + hx, 8.5, 9 + hx, 9.5), OW_BEAK), shade=False),
        Part((seg(0.5, 15, 15.5, 14.6, 1.8), BRANCH), outline=BRANCH_LINE),
        Part((rect(6, 13.6, 7, 14.6), OW_BEAK), (rect(9, 13.6, 10, 14.6), OW_BEAK), shade=False),
    ]


def owl_fly_frames():
    return ([owl_fly_front(p) for p in range(4)] + [owl_fly_side(p) for p in range(4)]
            + [owl_fly_front(p, back=True) for p in range(4)]
            + [owl_perch(), owl_perch(blink=True), owl_perch(hx=-1), owl_perch(hx=1)])


def heron_fly_front(u, phase, back=False):
    off = FLAP[phase] * 2
    left, right = seg(13, 15, 2, 15 + off, 4.2), seg(19, 15, 30, 15 + off, 4.2)
    belly = ell(16, 16.5, 4, 5)
    parts = [
        Part((left, NH_GRAY), (right, NH_GRAY),
             (both(left, lambda x, y: x < 5), NH_CAP), (both(right, lambda x, y: x > 27), NH_CAP), outline=NH_LINE),
        Part((belly, NH_GRAY), *([] if back else [(both(belly, lambda x, y: y > 17), NH_CREAM)]), outline=NH_LINE),
    ]
    if back:
        parts += [
            Part((rect(14.5, 20, 15.5, 25), NH_LEG), (rect(16.5, 20, 17.5, 25), NH_LEG), outline=NH_LINE, shade=False),
            Part((ell(16, 11.5, 3.4, 3), NH_CAP), outline=NH_LINE),
        ]
    else:
        parts += [
            Part((ell(16, 11.5, 3.4, 3), NH_GRAY), (ell(16, 10.5, 3.2, 1.8), NH_CAP), outline=NH_LINE),
            Part((ell(16, 12.6, 2.4, 1.4), NH_CREAM), (rect(14.3, 11.3, 14.3 + u, 12.3), NH_LINE),
                 (rect(16.7, 11.3, 16.7 + u, 12.3), NH_LINE), shade=False),
            Part((rect(15.3, 13, 16.7, 17), NH_BILL), outline=NH_LINE),
        ]
    return parts


def heron_fly_side(u, phase):
    off = FLAP[phase] * 2
    near = seg(16, 15, 10, 15 + off, 4.4)
    body = ell(15, 16.5, 7, 3.6)
    return [
        Part((seg(15, 15, 9, 15 + off * 0.7, 4), scaled(NH_GRAY, 0.75)), outline=NH_LINE),
        Part((seg(10, 17, 1.5, 18.5, 1.2), NH_LEG), outline=NH_LINE, shade=False),
        Part((body, NH_GRAY), (both(body, lambda x, y: y > 17.5), NH_CREAM), outline=NH_LINE),
        Part((ell(23, 15, 3.6, 3.2), NH_GRAY), (ell(23, 14, 3.4, 2), NH_CAP), outline=NH_LINE),
        Part((ell(24.5, 16, 1.8, 1.4), NH_CREAM), (rect(24, 14.5, 24 + u, 15.5), NH_LINE), shade=False),
        Part((seg(26, 16, 31, 16.8, 1.6), NH_BILL), outline=NH_LINE),
        Part((near, NH_GRAY), (both(near, lambda x, y: x < 12.5), NH_CAP), outline=NH_LINE),
    ]


def perch_branch(y):
    return Part((seg(3, y, 29, y - 0.6, 2.4), BRANCH), outline=BRANCH_LINE)


def heron_fly_frames(u):
    return ([heron_fly_front(u, p) for p in range(4)] + [heron_fly_side(u, p) for p in range(4)]
            + [heron_fly_front(u, p, back=True) for p in range(4)]
            + [heron_front(u) + [perch_branch(29.5)], heron_front(u, blink=True) + [perch_branch(29.5)],
               heron_front(u, hx=-1) + [perch_branch(29.5)], heron_front(u, hx=1) + [perch_branch(29.5)]])


FL_BLACK = rgb("#2a2024")


def flamingo_fly_front(u, phase, back=False):
    off = FLAP[phase] * 2
    left, right = seg(14, 15, 3, 15 + off, 4.2), seg(18, 15, 29, 15 + off, 4.2)
    parts = [
        Part((left, FL_WING), (right, FL_WING),
             (both(left, lambda x, y: x < 6), FL_BLACK), (both(right, lambda x, y: x > 26), FL_BLACK), outline=FL_LINE),
        Part((ell(16, 16, 3.4, 4.4), FL_PINK), outline=FL_LINE),
    ]
    if back:
        parts += [
            Part((rect(15, 19, 16, 27), FL_LEG), (rect(16.6, 19, 17.6, 27), FL_LEG), outline=FL_LINE, shade=False),
            Part((ell(16, 9, 2, 1.8), FL_PINK), outline=FL_LINE),
        ]
    else:
        parts += [
            Part((seg(16, 12, 16, 9.5, 1.8), FL_PINK), (ell(16, 8.5, 2, 1.8), FL_PINK), outline=FL_LINE),
            Part((rect(15.4, 9.5, 16.6, 12), FL_BEAK), (rect(15.4, 12, 16.6, 13), FL_BLACK), outline=FL_LINE),
            Part((rect(14.5, 7.8, 14.5 + u, 8.8), FL_LINE), (rect(17, 7.8, 17 + u, 8.8), FL_LINE), shade=False),
        ]
    return parts


def flamingo_fly_side(u, phase):
    off = FLAP[phase] * 2
    far = seg(16, 15, 10, 15 + off * 0.7, 4)
    near = seg(17, 15, 11, 15 + off, 4.6)
    return [
        Part((far, scaled(FL_WING, 0.8)), (both(far, lambda x, y: x < 12.5), FL_BLACK), outline=FL_LINE),
        Part((seg(11, 16.5, 0.5, 17.5, 1.1), FL_LEG), outline=FL_LINE, shade=False),
        Part((ell(16, 16, 6, 3.2), FL_PINK), outline=FL_LINE),
        Part((seg(21, 15, 27.5, 13.5, 1.8), FL_PINK), outline=FL_LINE),
        Part((ell(28.5, 13.2, 2, 1.8), FL_PINK), outline=FL_LINE),
        Part((seg(29.5, 13.8, 31.3, 16, 1.4), FL_BEAK), (ell(31.2, 16.2, 0.9, 0.8), FL_BLACK), outline=FL_LINE),
        Part((rect(28.5, 12.5, 28.5 + u, 13.5), FL_LINE), shade=False),
        Part((near, FL_WING), (both(near, lambda x, y: x < 13.5), FL_BLACK), outline=FL_LINE),
    ]


def flamingo_fly_frames(u):
    return ([flamingo_fly_front(u, p) for p in range(4)] + [flamingo_fly_side(u, p) for p in range(4)]
            + [flamingo_fly_front(u, p, back=True) for p in range(4)]
            + [flamingo_front(u, one_leg=True), flamingo_front(u, one_leg=True, blink=True),
               flamingo_front(u, one_leg=True, hx=-1), flamingo_front(u, one_leg=True, hx=1)])


# ---------------------------------------------------------------------------
# Monkey climbing sheet (MonkeyClimb.png): climb, sit on branch, hang/swing — 4 frames each
# ---------------------------------------------------------------------------

def rotated(shape, cx, cy, angle):
    c, s = math.cos(-angle), math.sin(-angle)
    return lambda x, y: shape(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c)


def rotate_parts(parts, cx, cy, angle):
    return [Part(*[(rotated(shape, cx, cy, angle), color) for shape, color in p.fills], outline=p.outline, shade=p.shade)
            for p in parts]


def monkey_climb(phase):
    la, ra = (-2.5, 0, 1.5, 0)[phase], (1.5, 0, -2.5, 0)[phase]
    return [
        Part((seg(8, 12, 9.5, 15.5, 1.1), MK_DARK), outline=MK_LINE),
        Part((seg(5.5, 8, 4.6, 4 + la, 1.5), MK_FUR), (seg(10.5, 8, 11.4, 4 + ra, 1.5), MK_FUR), outline=MK_LINE),
        Part((ell(4.6, 3.6 + la, 1, 1), MK_FACE), (ell(11.4, 3.6 + ra, 1, 1), MK_FACE), shade=False),
        Part((seg(6, 12, 5, 13.5 - ra * 0.6, 1.6), MK_FUR), (seg(10, 12, 11, 13.5 - la * 0.6, 1.6), MK_FUR), outline=MK_LINE),
        Part((ell(8, 10, 3.6, 3.4), MK_FUR), outline=MK_LINE),
        Part((ell(4.6, 5.6, 1.2, 1.4), MK_FUR), (ell(11.4, 5.6, 1.2, 1.4), MK_FUR), outline=MK_LINE),
        Part((ell(8, 5.8, 3.6, 3.2), MK_FUR), outline=MK_LINE),
    ]


def monkey_sit(blink=False, scratch=False, sleep=False):
    hd = 1 if sleep else 0
    eyes_closed = blink or sleep
    return [
        Part((seg(1, 12.2, 15, 12, 1.6), BRANCH), outline=BRANCH_LINE),
        Part((seg(11, 12.5, 12.5, 15.2, 1.1), MK_DARK), (ell(12, 15.4, 1.1, 0.8), MK_DARK), outline=MK_LINE),
        Part((rect(5, 11.5, 6.6, 14.6), MK_FUR), (rect(9.4, 11.5, 11, 14.6), MK_FUR), outline=MK_LINE),
        Part((rect(5, 14, 6.6, 15), MK_FACE), (rect(9.4, 14, 11, 15), MK_FACE), shade=False),
        Part((ell(8, 10, 3.8, 3.2), MK_FUR), outline=MK_LINE),
        Part((ell(3.8, 10.5, 1.1, 2), MK_FUR), (ell(11.6, 5.5, 1.1, 2) if scratch else ell(12.2, 10.5, 1.1, 2), MK_FUR),
             outline=MK_LINE),
        Part((ell(8, 6 + hd, 4.2, 3.6), MK_FUR), outline=MK_LINE),
        Part((ell(3.5, 5.5 + hd, 1.6, 1.8), MK_FUR), (ell(12.5, 5.5 + hd, 1.6, 1.8), MK_FUR), outline=MK_LINE),
        Part((ell(8, 6.8 + hd, 3.2, 2.8), MK_FACE),
             *([] if eyes_closed else [(rect(6, 6 + hd, 7, 7 + hd), MK_LINE), (rect(9, 6 + hd, 10, 7 + hd), MK_LINE)]),
             *([(rect(5.6, 6.5 + hd, 7.4, 7 + hd), MK_DARK), (rect(8.6, 6.5 + hd, 10.4, 7 + hd), MK_DARK)] if eyes_closed else []),
             (rect(7, 8 + hd, 9, 9 + hd), MK_DARK), shade=False),
    ]


def monkey_hang(angle):
    figure = [
        Part((seg(10.5, 12, 13.5, 14, 1), MK_DARK), outline=MK_LINE),
        Part((seg(7, 12.5, 6.5, 15, 1.4), MK_FUR), (seg(10, 12.5, 10.5, 15, 1.4), MK_FUR), outline=MK_LINE),
        Part((ell(8.5, 10.5, 3.2, 3), MK_FUR), outline=MK_LINE),
        Part((seg(5.8, 9, 4.6, 12, 1.3), MK_FUR), outline=MK_LINE),
        Part((seg(8, 1.6, 8.4, 7, 1.4), MK_FUR), outline=MK_LINE),
        Part((ell(8.5, 6.6, 3.4, 3), MK_FUR), outline=MK_LINE),
        Part((ell(8.5, 7.2, 2.5, 2.1), MK_FACE), (rect(7.2, 6.6, 8, 7.4), MK_LINE), (rect(9.2, 6.6, 10, 7.4), MK_LINE),
             (rect(8, 8.4, 9, 9), MK_DARK), shade=False),
    ]
    return [Part((seg(0, 1, 16, 1.3, 1.6), BRANCH), outline=BRANCH_LINE)] + rotate_parts(figure, 8, 1.4, angle) + [
        Part((ell(8, 1.4, 1, 0.9), MK_FACE), outline=MK_LINE)]


def monkey_climb_frames():
    return ([monkey_climb(p) for p in range(4)]
            + [monkey_sit(), monkey_sit(blink=True), monkey_sit(scratch=True), monkey_sit(sleep=True)]
            + [monkey_hang(a) for a in (-0.4, 0, 0.4, 0)])


# ---------------------------------------------------------------------------
# Sheets
# ---------------------------------------------------------------------------

WATER_HI, WATER_LO = (214, 238, 255, 230), (150, 196, 235, 210)


def build_sheet(frames, size, scale=1.0, design=None, rows=5):
    sheet = Image.new("RGBA", (size * 4, size * rows))
    for index, parts in enumerate(frames):
        sheet.paste(render(parts, size, scale, design), ((index % 4) * size, (index // 4) * size))
    return sheet


def submerge(frame_img, mode):
    """Sink a frame into water: 'swim' lowers the body ~40% under the waterline, 'wade' hides the lower legs."""
    box = frame_img.getbbox()
    if not box:
        return frame_img
    top, bottom = box[1], box[3]
    height = bottom - top
    if mode == "swim":
        sink, line = round(height * 0.4), bottom - 1
    else:
        sink, line = 0, bottom - max(2, round(height * 0.18))
    out = Image.new("RGBA", frame_img.size)
    out.paste(frame_img, (0, sink))
    px = out.load()
    w, h = out.size
    cols = [x for x in range(w) if any(px[x, y][3] for y in range(max(0, line - 2), line))]
    for y in range(line, h):
        for x in range(w):
            px[x, y] = (0, 0, 0, 0)
    if cols:
        for x in range(max(0, min(cols) - 1), min(w, max(cols) + 2)):
            px[x, line] = WATER_HI if (x // 2) % 2 == 0 else WATER_LO
    return out


def add_water_rows(sheet, size, mode):
    out = Image.new("RGBA", (sheet.width, sheet.height * 2))
    out.paste(sheet, (0, 0))
    for index in range(20):
        x, y = (index % 4) * size, (index // 4) * size
        out.paste(submerge(sheet.crop((x, y, x + size, y + size)), mode), (x, y + 5 * size))
    return out


def shop_icon(frame, crop):
    icon = Image.new("RGBA", (32, 16))
    region = frame.crop(crop)
    icon.alpha_composite(region, ((32 - region.width) // 2, 16 - region.height))
    return icon


PREVIEW_DIR = Path(__file__).resolve().parent / "previews"


def write_preview(name, frame, scale=8):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    big = frame.resize((frame.width * scale, frame.height * scale), Image.NEAREST)
    big.save(PREVIEW_DIR / f"{name}.png")


def unit(scale):
    """Design units per output pixel, so one-unit details (eyes) never vanish when shrunk."""
    return 1 / scale if scale < 1 else 1


def frames_at(name, scale, baby=False):
    global DETAIL
    DETAIL = scale >= 1.3
    try:
        if name in BIG:
            return BIG[name][0](unit(scale))
        adult_frames, baby_frames = SMALL[name]
        return (baby_frames if baby and baby_frames else adult_frames)()
    finally:
        DETAIL = False


def write_lineup(path):
    """Adults (top) and babies (below) at true relative size, 2x, on a 16px tile grid."""
    groups = [
        ["Owl", "Raccoon", "Penguin", "NightHeron", "Monkey", "Capybara", "Flamingo", "Deer", "Alpaca", "SeaLion", "Panda"],
        ["Lion", "Gorilla", "Bear", "Elephant", "Giraffe", "Dinosaur"],
    ]
    gap = 6
    bands = []
    for group in groups:
        width = sum(frame(n) for n in group) + gap * (len(group) + 1)
        height = max(frame(n) for n in group)
        band = Image.new("RGBA", (width, height * 2 + gap * 3), (110, 160, 70, 255))
        px = band.load()
        for y in range(band.height):
            for x in range(band.width):
                if x % 16 == 0 or y % 16 == 0:
                    px[x, y] = (98, 146, 62, 255)
        x = gap
        for name in group:
            size = frame(name)
            adult = Image.open(OUT_DIR / f"{name}.png").crop((0, 0, size, size))
            baby = Image.open(OUT_DIR / f"Baby{name}.png").crop((0, 0, size, size))
            band.alpha_composite(adult, (x, gap + height - size))
            band.alpha_composite(baby, (x, gap * 2 + height * 2 - size))
            x += size + gap
        bands.append(band)
    lineup = Image.new("RGBA", (max(b.width for b in bands), sum(b.height for b in bands)), (110, 160, 70, 255))
    y = 0
    for band in bands:
        lineup.alpha_composite(band, (0, y))
        y += band.height
    lineup = lineup.resize((lineup.width * 2, lineup.height * 2), Image.NEAREST)
    path.parent.mkdir(parents=True, exist_ok=True)
    lineup.save(path)
    small = lineup.resize((512, round(lineup.height * 512 / lineup.width)), Image.NEAREST)
    small.save(path.with_name(path.stem + "_512.png"))


def write_extras(path):
    """Fly, climb, and swim rows side by side at 2x, for a quick visual check."""
    sheets = [Image.open(OUT_DIR / f"{n}Fly.png") for n in FLIERS] + [Image.open(OUT_DIR / f"{n}Climb.png") for n in CLIMBERS]
    for name in SWIMMERS:
        size = frame(name)
        sheets.append(Image.open(OUT_DIR / f"{name}.png").crop((0, 5 * size, 4 * size, 7 * size)))
    width = sum(s.width for s in sheets) + 4 * len(sheets)
    out = Image.new("RGBA", (width, max(s.height for s in sheets)), (90, 140, 190, 255))
    x = 0
    for sheet in sheets:
        out.alpha_composite(sheet, (x, 0))
        x += sheet.width + 4
    out = out.resize((out.width * 2, out.height * 2), Image.NEAREST)
    if out.width > 1200:
        out = out.resize((1200, round(out.height * 1200 / out.width)), Image.NEAREST)
    out.save(path)


BIG = {}
SMALL = {}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BIG.update({
        "Panda": (panda_frames, (0, 2, 32, 18)),
        "Lion": (lion_frames, (0, 2, 32, 18)),
        "Giraffe": (giraffe_frames, (0, 0, 32, 16)),
        "Capybara": (capy_frames, (0, 4, 32, 20)),
        "Elephant": (elephant_frames, (0, 2, 32, 18)),
        "Dinosaur": (dino_frames, (0, 2, 32, 18)),
        "Gorilla": (gorilla_frames, (0, 2, 32, 18)),
        "Alpaca": (alpaca_frames, (0, 0, 32, 16)),
        "SeaLion": (sealion_frames, (0, 4, 32, 20)),
        "Bear": (bear_frames, (0, 2, 32, 18)),
        "Flamingo": (flamingo_frames, (0, 0, 32, 16)),
        "Deer": (deer_frames, (0, 0, 32, 16)),
        "NightHeron": (heron_frames, (0, 2, 32, 18)),
    })
    SMALL.update({
        "Penguin": (penguin_frames, chick_frames),
        "Monkey": (monkey_frames, None),
        "Raccoon": (raccoon_frames, None),
        "Owl": (owl_frames, None),
    })
    fly_frames = {"Owl": lambda u: owl_fly_frames(), "NightHeron": heron_fly_frames, "Flamingo": flamingo_fly_frames}
    climb_frames = {"Monkey": monkey_climb_frames}

    for name, (design, size, _, _) in SIZES.items():
        adult_s, baby_s = adult_scale(name), baby_scale(name)
        adult = build_sheet(frames_at(name, adult_s), size, adult_s, design)
        baby = build_sheet(frames_at(name, baby_s, baby=True), size, baby_s, design)
        if name in SWIMMERS:
            adult = add_water_rows(adult, size, SWIMMERS[name])
            baby = add_water_rows(baby, size, SWIMMERS[name])
        assert adult.height == size * sheet_rows(name)
        adult.save(OUT_DIR / f"{name}.png")
        baby.save(OUT_DIR / f"Baby{name}.png")

        if name in fly_frames:
            build_sheet(fly_frames[name](unit(adult_s)), size, adult_s, design, rows=4).save(OUT_DIR / f"{name}Fly.png")
        if name in climb_frames:
            build_sheet(climb_frames[name](), size, adult_s, design, rows=3).save(OUT_DIR / f"{name}Climb.png")

        # shop icons stay 32x16, cut from the design-scale drawing
        if name in BIG:
            front = render(BIG[name][0](1)[0], 32)
            shop_icon(front, BIG[name][1]).save(OUT_DIR / f"{name}Shop.png")
        else:
            front = render(SMALL[name][0]()[0], 16)
            shop_icon(front, (0, 0, 16, 16)).save(OUT_DIR / f"{name}Shop.png")
        write_preview(name, adult.crop((0, 0, size, size)))

    write_lineup(Path("/tmp/zoo_art/animal_lineup.png"))
    write_extras(Path("/tmp/zoo_art/animal_extras.png"))
    print(f"Wrote animal sprites to {OUT_DIR}")


if __name__ == "__main__":
    main()
