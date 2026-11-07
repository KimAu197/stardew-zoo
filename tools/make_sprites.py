"""Draw the zoo exteriors in vanilla farm-building style (7x4 footprint, 112x128 sprites).

Zoo -> BigZoo -> DeluxeZoo upgrade like Barn -> Big Barn -> Deluxe Barn: the same
plank hall gains a stone foundation, trim, a cupola, and finally a front gable.
HumanDoor is tile (1, 3) (pixels x 16-31 on the bottom row). Each tier also gets a
`_winter` variant with a snowy roof.

Does not touch animal art.

Usage: python3 tools/make_sprites.py
"""

from pathlib import Path

from PIL import Image

from vanilla import MAPS

OUT_DIR = Path(__file__).resolve().parent.parent / "[CP] Stardew Zoo" / "assets"
PREVIEW_DIR = Path(__file__).resolve().parent / "previews"
W, H = 112, 128
NAMES = ("Zoo", "BigZoo", "DeluxeZoo")


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def ramp(*hexes):
    return [rgb(h) for h in hexes]


# Vanilla building outline (Barn / Big Shed / Coop all use this wine color).
OUT = rgb("#3b0015")
# Ramps run light -> dark.
WOOD = ramp("#ffcf86", "#eea65a", "#d4843e", "#a95c2c", "#76361d")
LEAF = ramp("#b4dc6a", "#82be4c", "#5c9a3e", "#3f7536", "#2a522e")
LEAF_OUT = rgb("#1c3122")
TEAL = ramp("#8fd9a8", "#56b58a", "#38916f", "#276d5c", "#1b4b47")
TEAL_OUT = rgb("#112b33")
SNOW = ramp("#ffffff", "#eef4fb", "#d4e0f0", "#a9bcd9", "#7b8fb6")
SNOW_OUT = rgb("#3d4a6e")
STONE = ramp("#eeeceb", "#ccc8c6", "#a29c99", "#7a7472", "#524b4e")
TRIM = ramp("#fffaf2", "#eedddd", "#dbbaba", "#af7c7c")
GOLD = ramp("#fff1a1", "#ffc927", "#d3893b", "#894505")
DOOR = ramp("#d9a466", "#c28d54", "#9b6f41", "#704b2d", "#52352a")
GLASS = ramp("#c9e8f5", "#7f9fc4", "#4d4f80", "#2e2547")
IRON = ramp("#8e967e", "#635a5a", "#3a3436")
SIGN = ramp("#fff4d6", "#f4dca0", "#dcb878", "#b28650")
INK = rgb("#5a1a14")
FLOWERS = ramp("#ff7b9c", "#e8445f", "#ffe06b", "#ffffff")


class Canvas:
    def __init__(self):
        self.img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.px = self.img.load()

    def set(self, x, y, c):
        if 0 <= x < W and 0 <= y < H and c is not None:
            self.px[x, y] = c

    def get(self, x, y):
        return self.px[x, y] if 0 <= x < W and 0 <= y < H else (0, 0, 0, 0)

    def hline(self, x0, x1, y, c):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            self.set(x, y, c)

    def vline(self, x, y0, y1, c):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            self.set(x, y, c)

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            self.hline(x0, x1, y, c)

    def box(self, x0, y0, x1, y1, c):
        self.hline(x0, x1, y0, c)
        self.hline(x0, x1, y1, c)
        self.vline(x0, y0, y1, c)
        self.vline(x1, y0, y1, c)

    def pattern(self, x, y, rows, colors):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch in colors:
                    self.set(x + i, y + j, colors[ch])


# --- roof -----------------------------------------------------------------

# Scalloped shingle like the Big Shed's; rows step SHINGLE_STEP so each rounded
# bottom laps the row below.
SHINGLE = [
    "222222222222",
    "111111111122",
    "100001111223",
    "100111112223",
    "111111222223",
    "112222222233",
    "222222223333",
    "422222233334",
    " 4433333344 ",
    "   444444   ",
]
SHINGLE_W = 12
SHINGLE_STEP = 7


def roof_mask(top, eave, inset, slope):
    """Hip roof seen from the front: ridge at `top`, side triangles `inset` wide."""
    left, right = 0, W - 1
    shoulder = top + slope

    def inside(x, y):
        if y < top or y > eave:
            return False
        if x < left or x > right:
            return False
        if y >= shoulder:
            return True
        # Back hip edges rise from the shoulders to the ridge ends.
        t = (shoulder - y) / max(1, slope)
        return left + inset * t <= x <= right - inset * t

    return inside


def draw_roof(cv, top, eave, inset, slope, pal, out):
    inside = roof_mask(top, eave, inset, slope)
    seam_bottom = eave - 2

    def face(x, y):
        """-1 left hip, 0 front, +1 right hip."""
        if y >= seam_bottom:
            return 0
        t = (seam_bottom - y) / max(1, seam_bottom - top)
        if x < 2 + (inset - 2) * t:
            return -1
        if x > W - 3 - (inset - 2) * t:
            return 1
        return 0

    shade = {}
    row_top = eave - len(SHINGLE) + 1
    r = 0
    tops = []
    while row_top > top - len(SHINGLE):
        tops.append((row_top, r))
        row_top -= SHINGLE_STEP
        r += 1
    # Bottom row first: upper rows lap over the ones below.
    for y0, r in tops:
        off = SHINGLE_W // 2 if r % 2 else 0
        for x0 in range(-SHINGLE_W + off - 2, W + SHINGLE_W, SHINGLE_W):
            # A few weathered shingles per row, like vanilla roofs.
            weathered = (x0 * 7 + r * 13) % 5 == 0
            for j, row in enumerate(SHINGLE):
                for i, ch in enumerate(row):
                    if ch == " ":
                        continue
                    x, y = x0 + i, y0 + j
                    if inside(x, y) and y < eave - 1:
                        k = int(ch)
                        if weathered and 0 < k < 3:
                            k += 1
                        shade[(x, y)] = k

    full = pal + [out]
    for (x, y), k in shade.items():
        f = face(x, y)
        if f < 0 and k < 4:
            k = max(0, k - 1)
        elif f > 0:
            k = k + 1
        cv.set(x, y, full[k])

    # Hip ridge caps from the ridge ends down to the front corners.
    for y in range(top, seam_bottom + 1):
        t = (seam_bottom - y) / max(1, seam_bottom - top)
        xl = int(round(2 + (inset - 2) * t))
        xr = int(round(W - 3 - (inset - 2) * t))
        cv.set(xl - 1, y, pal[0])
        cv.set(xl, y, pal[1])
        cv.set(xl + 1, y, out)
        cv.set(xr - 1, y, out)
        cv.set(xr, y, pal[2])
        cv.set(xr + 1, y, pal[3])

    # Ridge board.
    xl, xr = inset, W - 1 - inset
    cv.hline(xl, xr, top, out)
    cv.hline(xl + 1, xr - 1, top + 1, pal[0])
    cv.hline(xl + 1, xr - 1, top + 2, pal[1])
    cv.hline(xl + 1, xr - 1, top + 3, out)

    # Silhouette outline.
    for y in range(top - 1, eave + 2):
        for x in range(-1, W + 1):
            if inside(x, y):
                continue
            if any(inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                if y <= eave:
                    cv.set(x, y, out)
    cv.hline(0, W - 1, eave, out)
    cv.hline(0, W - 1, eave - 1, pal[3])


def draw_eave_trim(cv, eave, pal):
    """Painted fascia board under the shingles (Big Barn's white trim)."""
    cv.hline(1, W - 2, eave + 1, pal[0])
    cv.hline(1, W - 2, eave + 2, pal[2])
    cv.hline(0, W - 1, eave + 3, OUT)


# --- walls ----------------------------------------------------------------

WALL_L, WALL_R = 3, W - 4


def draw_plank_wall(cv, y_top, pal):
    """Horizontal lap siding like the Big Shed, with staggered butt joints."""
    for y in range(y_top, H):
        dy = (y - y_top) % 5
        plank = (y - y_top) // 5
        k = (1, 1, 2, 2, 4)[dy]
        if dy == 0:
            k = 0 if plank % 2 == 0 else 1
        for x in range(WALL_L, WALL_R + 1):
            c = pal[k]
            joint = (x - WALL_L + plank * 17) % 34
            if dy < 4 and joint == 0:
                c = pal[4]
            elif dy < 4 and joint == 1:
                c = pal[0]
            elif dy in (1, 2) and (x * 7 + plank * 3) % 23 == 0:
                c = pal[3]
            cv.set(x, y, c)
    # Shadow cast by the eave.
    for y in range(y_top, y_top + 3):
        for x in range(WALL_L, WALL_R + 1):
            cv.set(x, y, pal[4] if y == y_top else pal[3])
    cv.vline(WALL_L - 1, y_top, H - 1, OUT)
    cv.vline(WALL_R + 1, y_top, H - 1, OUT)
    cv.hline(WALL_L - 1, WALL_R + 1, H - 1, OUT)


def draw_corner_posts(cv, y_top, pal):
    for x0 in (WALL_L, WALL_R - 3):
        cv.rect(x0, y_top + 1, x0 + 3, H - 2, pal[1])
        cv.vline(x0, y_top + 1, H - 2, pal[0])
        cv.vline(x0 + 3, y_top + 1, H - 2, pal[2])
        cv.vline(x0 + 4 if x0 == WALL_L else x0 - 1, y_top + 1, H - 2, OUT)


def draw_foundation(cv, y0, pal):
    for y in range(y0, H - 1):
        dy = y - y0
        row = dy // 4
        for x in range(WALL_L, WALL_R + 1):
            lx = (x - WALL_L + (5 if row % 2 else 0)) % 10
            ly = dy % 4
            if ly == 3 or lx == 9:
                c = pal[4]
            elif ly == 0 or lx == 0:
                c = pal[0] if lx < 6 else pal[1]
            elif lx >= 7:
                c = pal[3]
            else:
                c = pal[2] if ly == 2 else pal[1]
            cv.set(x, y, c)
    cv.hline(WALL_L - 1, WALL_R + 1, y0 - 1, OUT)
    cv.vline(WALL_L - 1, y0, H - 1, OUT)
    cv.vline(WALL_R + 1, y0, H - 1, OUT)
    cv.hline(WALL_L - 1, WALL_R + 1, H - 1, OUT)


# --- openings -------------------------------------------------------------

def draw_door(cv, trim):
    """Staff door on HumanDoor tile (1, 3)."""
    x0, x1, y0 = 15, 32, 96
    cv.rect(x0, y0, x1, H - 1, trim[1])
    cv.vline(x0 + 1, y0 + 1, H - 1, trim[0])
    cv.vline(x1 - 1, y0 + 1, H - 1, trim[2])
    cv.hline(x0 + 1, x1 - 1, y0 + 1, trim[0])
    cv.box(x0, y0, x1, H - 1, OUT)
    lx0, lx1, ly0 = x0 + 3, x1 - 3, y0 + 3
    cv.box(lx0 - 1, ly0 - 1, lx1 + 1, H - 1, OUT)
    for x in range(lx0, lx1 + 1):
        k = (1, 2, 2, 3)[(x - lx0) % 4]
        cv.vline(x, ly0, H - 2, DOOR[k])
        if (x - lx0) % 4 == 3:
            cv.vline(x, ly0, H - 2, DOOR[4])
    # recessed panels
    for py0, py1 in ((ly0 + 2, ly0 + 11), (ly0 + 15, H - 4)):
        cv.box(lx0 + 2, py0, lx1 - 2, py1, DOOR[4])
        cv.hline(lx0 + 3, lx1 - 3, py0 + 1, DOOR[0])
        cv.vline(lx0 + 3, py0 + 1, py1 - 1, DOOR[0])
    # hinges + knob
    for hy in (ly0 + 4, H - 8):
        cv.hline(lx0 - 1, lx0 + 1, hy, IRON[1])
    cv.set(lx1 - 2, ly0 + 13, GOLD[1])
    cv.set(lx1 - 1, ly0 + 13, GOLD[2])
    cv.set(lx1 - 2, ly0 + 14, GOLD[3])


def draw_gate(cv, x0, x1, y0, trim, arch=False, bars=True):
    """Big double gate with a barred transom, the zoo's answer to the barn's animal door."""
    cv.rect(x0, y0, x1, H - 1, trim[1])
    cv.vline(x0 + 1, y0 + 1, H - 1, trim[0])
    cv.vline(x1 - 1, y0 + 1, H - 1, trim[2])
    cv.hline(x0 + 1, x1 - 1, y0 + 1, trim[0])
    cv.box(x0, y0, x1, H - 1, OUT)
    ix0, ix1, iy0 = x0 + 3, x1 - 3, y0 + 3
    mid = (ix0 + ix1) // 2
    transom = iy0 + 9
    # barred window over the doors: dark enclosure, iron bars
    cv.rect(ix0, iy0, ix1, transom, GLASS[3])
    cv.hline(ix0, ix1, iy0, OUT)
    if arch:
        cx = (ix0 + ix1) / 2
        rx = (ix1 - ix0) / 2
        for x in range(ix0, ix1 + 1):
            n = (x - cx) / rx
            ya = int(round(iy0 + 6 - 6 * max(0.0, 1 - n * n) ** 0.5))
            for y in range(iy0 - 3, ya):
                cv.set(x, y, trim[1])
            cv.set(x, ya, OUT)
    for x in range(ix0 + 2, ix1 - 1, 4):
        top = iy0 + 1
        while cv.get(x, top) != GLASS[3] and top < transom:
            top += 1
        cv.vline(x, top, transom - 1, IRON[0])
        cv.vline(x + 1, top, transom - 1, IRON[2])
    cv.hline(ix0, ix1, iy0 + 4, IRON[1]) if bars else None
    cv.hline(ix0 - 1, ix1 + 1, transom + 1, OUT)
    cv.hline(ix0 - 1, ix1 + 1, transom + 2, trim[0])
    cv.hline(ix0 - 1, ix1 + 1, transom + 3, OUT)
    # two leaves of vertical boards with X braces
    ly0 = transom + 4
    for x in range(ix0, ix1 + 1):
        k = (1, 1, 2, 3)[(x - ix0) % 4]
        cv.vline(x, ly0, H - 2, DOOR[k])
        if (x - ix0) % 4 == 3:
            cv.vline(x, ly0, H - 2, DOOR[4])
    cv.vline(mid, ly0, H - 2, OUT)
    for a, b in ((ix0, mid - 1), (mid + 1, ix1)):
        cv.box(a, ly0, b, H - 2, trim[2])
        cv.hline(a, b, ly0, trim[0])
        span_h = H - 3 - ly0
        for t in range(span_h + 1):
            xa = a + 1 + int(round((b - a - 2) * t / span_h))
            xb = b - 1 - int(round((b - a - 2) * t / span_h))
            for xx in (xa, xb):
                cv.set(xx, ly0 + 1 + t, trim[0])
                cv.set(xx + 1, ly0 + 1 + t, DOOR[4])
    # ring handles
    for hx in (mid - 3, mid + 2):
        cv.set(hx, ly0 + 9, IRON[1])
        cv.set(hx + 1, ly0 + 9, IRON[1])
        cv.set(hx, ly0 + 10, IRON[2])
        cv.set(hx + 1, ly0 + 10, IRON[2])


def draw_window(cv, x0, y0, w, h, trim, shutters=False, box=False):
    x1, y1 = x0 + w - 1, y0 + h - 1
    if shutters:
        for sx0 in (x0 - 5, x1 + 2):
            cv.rect(sx0, y0, sx0 + 3, y1, LEAF[2])
            for yy in range(y0 + 2, y1 - 1, 3):
                cv.hline(sx0 + 1, sx0 + 2, yy, LEAF[3])
            cv.vline(sx0, y0, y1, LEAF[1])
            cv.box(sx0 - 1, y0 - 1, sx0 + 4, y1 + 1, OUT)
    cv.rect(x0, y0, x1, y1, trim[1])
    cv.hline(x0 + 1, x1 - 1, y0 + 1, trim[0])
    cv.vline(x0 + 1, y0 + 1, y1 - 1, trim[0])
    cv.box(x0, y0, x1, y1, OUT)
    gx0, gy0, gx1, gy1 = x0 + 3, y0 + 3, x1 - 3, y1 - 3
    cv.box(gx0 - 1, gy0 - 1, gx1 + 1, gy1 + 1, OUT)
    cv.rect(gx0, gy0, gx1, gy1, GLASS[2])
    for yy in range(gy0, gy1 + 1):
        for xx in range(gx0, gx1 + 1):
            d = (xx - gx0) + (yy - gy0)
            if d < 3:
                cv.set(xx, yy, GLASS[0])
            elif d < 6:
                cv.set(xx, yy, GLASS[1])
            elif yy > gy1 - 2:
                cv.set(xx, yy, GLASS[3])
    mx, my = (gx0 + gx1) // 2, (gy0 + gy1) // 2
    cv.vline(mx, gy0, gy1, trim[2])
    cv.hline(gx0, gx1, my, trim[2])
    cv.hline(x0 - 1, x1 + 1, y1 + 1, OUT)
    cv.hline(x0, x1, y1, trim[2])
    if box:
        bx0, bx1, by0 = x0 - 1, x1 + 1, y1 + 2
        cv.rect(bx0, by0, bx1, by0 + 3, DOOR[2])
        cv.hline(bx0, bx1, by0, DOOR[1])
        cv.box(bx0, by0, bx1, by0 + 4, OUT)
        for i, xx in enumerate(range(bx0 + 1, bx1, 2)):
            fc = FLOWERS[i % 3]
            cv.set(xx, by0 - 1, fc)
            cv.set(xx, by0 - 2 - (i % 2), fc)
            cv.set(xx + 1, by0 - 1, LEAF[1])
        cv.hline(bx0 + 1, bx1 - 1, by0, LEAF[2])


# --- sign + ornaments -----------------------------------------------------

GLYPHS = {
    "Z": ["#######", "#######", "    ###", "   ### ", "  ###  ", " ###   ", "#######", "#######"],
    "O": [" ##### ", "### ###", "##   ##", "##   ##", "##   ##", "##   ##", "### ###", " ##### "],
}

PAW = [" # # ", "#   #", " ### ", " ### "]


def draw_sign(cv, cx, y0, w, board, letter, edge=OUT, paws=False, chains=True):
    h = 14
    x0 = cx - w // 2
    x1 = x0 + w - 1
    y1 = y0 + h - 1
    if chains:
        for chx in (x0 + 4, x1 - 4):
            for y in range(y0 - 5, y0):
                cv.set(chx, y, IRON[1] if y % 2 else IRON[2])
    cv.rect(x0, y0, x1, y1, board[1])
    cv.hline(x0 + 1, x1 - 1, y0 + 1, board[0])
    cv.vline(x0 + 1, y0 + 1, y1 - 1, board[0])
    cv.hline(x0 + 1, x1 - 1, y1 - 1, board[2])
    cv.vline(x1 - 1, y0 + 1, y1 - 1, board[2])
    cv.box(x0, y0, x1, y1, edge)
    # plank seam
    cv.hline(x0 + 2, x1 - 2, y0 + h // 2, board[2]) if w > 60 else None
    text_w = 7 * 3 + 2 * 2
    tx = cx - text_w // 2
    ty = y0 + 3
    shadow = board[3]
    for i, ch in enumerate("ZOO"):
        gx = tx + i * 9
        cv.pattern(gx + 1, ty + 1, GLYPHS[ch], {"#": shadow})
    for i, ch in enumerate("ZOO"):
        gx = tx + i * 9
        cv.pattern(gx, ty, GLYPHS[ch], {"#": letter})
    if paws:
        cv.pattern(x0 + 3, y0 + 5, PAW, {"#": letter})
        cv.pattern(x1 - 7, y0 + 5, PAW, {"#": letter})


def draw_lantern(cv, x, y):
    cv.pattern(x, y, [
        " ooo ",
        "ogggo",
        "oGYGo",
        "oGYGo",
        "ogggo",
        " ooo ",
    ], {"o": OUT, "g": IRON[1], "G": GOLD[1], "Y": GOLD[0]})
    cv.hline(x - 1, x + 2, y - 1, IRON[2])


def draw_cupola(cv, cx, base_y, roof_pal, roof_out, walls, vane=False):
    """Small louvered vent house sitting on the ridge."""
    x0, x1 = cx - 7, cx + 6
    wall_top = base_y - 7
    cv.rect(x0, wall_top, x1, base_y, walls[1])
    cv.vline(x0 + 1, wall_top, base_y, walls[0])
    cv.vline(x1 - 1, wall_top, base_y, walls[2])
    cv.box(x0, wall_top, x1, base_y, OUT)
    lx0, lx1 = x0 + 3, x1 - 3
    cv.rect(lx0, wall_top + 2, lx1, base_y - 2, GLASS[3])
    for yy in range(wall_top + 3, base_y - 1, 2):
        cv.hline(lx0, lx1, yy, walls[2])
    cv.box(lx0 - 1, wall_top + 1, lx1 + 1, base_y - 1, OUT)
    # pyramid cap
    cap_bot = wall_top - 1
    for i in range(5):
        y = cap_bot - i
        a, b = x0 - 2 + (i * 3) // 2, x1 + 2 - (i * 3) // 2
        cv.hline(a, b, y, roof_pal[1] if i % 2 else roof_pal[2])
        cv.set(a, y, roof_out)
        cv.set(b, y, roof_out)
        cv.set(a + 1, y, roof_pal[0])
        cv.set(b - 1, y, roof_pal[3])
    cv.hline(x0 - 2, x1 + 2, cap_bot, roof_out)
    cv.hline(x0 - 1, x1 + 1, cap_bot - 1, roof_pal[3])
    top = cap_bot - 5
    cv.hline(cx - 3, cx + 2, top, roof_out)
    if vane:
        draw_weathervane(cv, cx, top)
    else:
        cv.set(cx - 1, top - 1, GOLD[1])
        cv.set(cx, top - 1, GOLD[2])
        cv.hline(cx - 2, cx + 1, top - 2, OUT)
        cv.set(cx - 2, top - 1, OUT)
        cv.set(cx + 1, top - 1, OUT)


def draw_weathervane(cv, cx, base):
    """Giraffe weathervane: an animal on the roof says 'zoo' from across the farm."""
    cv.vline(cx - 1, base - 3, base - 1, OUT)
    cv.vline(cx, base - 3, base - 1, IRON[2])
    cv.pattern(cx - 7, base - 5, [
        " o          o ",
        "oooooooooooooo",
        " o          o ",
    ], {"o": OUT})
    cv.set(cx - 7, base - 4, GOLD[2])
    cv.pattern(cx - 5, base - 13, [
        "       ## ",
        "       ###",
        "      ##  ",
        "     ##   ",
        "    ##    ",
        " ######   ",
        "#######   ",
        " #   #    ",
    ], {"#": OUT})
    cv.set(cx + 2, base - 13, GOLD[2])


def draw_paw_medallion(cv, cx, cy):
    for y in range(cy - 7, cy + 8):
        for x in range(cx - 7, cx + 8):
            dx, dy = x - cx, y - cy
            d = (dx * dx + dy * dy) ** 0.5
            if d <= 4.6:
                c = TRIM[0] if dx + dy < 0 else TRIM[1]
            elif d <= 5.8:
                c = GOLD[0] if dx + dy < -3 else GOLD[1] if dx + dy < 3 else GOLD[2]
            elif d <= 6.6:
                c = OUT
            else:
                continue
            cv.set(x, y, c)
    cv.pattern(cx - 3, cy - 3, [
        "  # #  ",
        "#     #",
        "  ###  ",
        " ##### ",
        " ##### ",
        "  # #  ",
    ], {"#": INK})


def draw_gable(cv, cx, base_y, half, height, roof_pal, roof_out, face_pal):
    """Front-facing gable dormer over the gate (the Deluxe tier)."""
    apex = base_y - height
    for y in range(apex, base_y + 1):
        t = (y - apex) / height
        hw = int(round(half * t))
        cv.hline(cx - hw, cx + hw, y, face_pal[1])
        cv.hline(cx - hw, cx + hw, y, face_pal[1])
    # vertical board-and-batten face
    for y in range(apex + 2, base_y + 1):
        t = (y - apex) / height
        hw = int(round(half * t)) - 1
        for x in range(cx - hw, cx + hw + 1):
            if (x - cx) % 5 == 0:
                cv.set(x, y, face_pal[2])
            elif (x - cx) % 5 == 1:
                cv.set(x, y, face_pal[0])
    # barge boards: thick shingle-capped edges
    for y in range(apex - 3, base_y + 2):
        t = (y - apex + 3) / (height + 3)
        hw = int(round((half + 4) * t))
        for side in (-1, 1):
            xe = cx + side * hw
            cols = (roof_out, roof_pal[0], roof_pal[1], roof_pal[2], roof_out)
            for i, c in enumerate(cols):
                cv.set(xe - side * i, y, c)
    cv.set(cx, apex - 4, roof_out)
    cv.hline(cx - 1, cx + 1, apex - 3, roof_pal[0])


def stamp_bush(cv, x, y, pal):
    cv.pattern(x, y, [
        "  oooo  ",
        " o1122o ",
        "o112223o",
        "o122233o",
        "o222333o",
        " o3333o ",
        "  oooo  ",
    ], {"o": LEAF_OUT, "1": pal[0], "2": pal[1], "3": pal[3]})


# --- tiers ----------------------------------------------------------------

def draw_building(tier: int, winter: bool = False) -> Image.Image:
    cv = Canvas()
    roof_pal, roof_out = (SNOW, SNOW_OUT) if winter else (TEAL, TEAL_OUT)
    trim = DOOR if tier == 0 else TRIM

    top = 24
    eave = 70
    inset = (26, 22, 18)[tier]

    draw_plank_wall(cv, eave + 1, WOOD)
    if tier >= 1:
        draw_foundation(cv, H - 9, STONE)
    draw_corner_posts(cv, eave + 1, trim if tier else WOOD)
    draw_roof(cv, top, eave, inset, 10, roof_pal, roof_out)
    if tier >= 1:
        draw_eave_trim(cv, eave, TRIM if not winter else SNOW)

    draw_door(cv, trim)
    gate_arch = tier == 2
    draw_gate(cv, 40, 83, 95 if tier < 2 else 93, trim, arch=gate_arch)
    draw_window(cv, 88, 88, 17, 18, trim, box=tier >= 1)

    if tier == 0:
        draw_sign(cv, 56, 78, 40, SIGN, INK)
    elif tier == 1:
        draw_sign(cv, 56, 77, 54, SIGN, INK, paws=True)
        draw_cupola(cv, 56, top + 3, roof_pal, roof_out, TRIM)
        draw_lantern(cv, 34, 92)
    else:
        draw_gable(cv, 56, eave, 26, 34, roof_pal, roof_out, TRIM)
        draw_paw_medallion(cv, 56, eave - 16)
        draw_sign(cv, 56, eave - 4, 60, ramp("#5c9a3e", "#3f7536", "#2a522e", "#1c3122"),
                  GOLD[1], paws=True, chains=False)
        cv.hline(56 - 29, 56 + 28, eave - 4, GOLD[2])
        draw_cupola(cv, 56, top + 3, roof_pal, roof_out, TRIM, vane=True)
        draw_lantern(cv, 34, 92)
        draw_lantern(cv, 86, 92)

    return cv.img


def grass_backdrop(w, h) -> Image.Image:
    grass = Image.open(MAPS / "spring_outdoorsTileSheet.png").convert("RGBA")
    tile = grass.crop((0, 6 * 16, 16, 7 * 16))
    bg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(0, h, 16):
        for x in range(0, w, 16):
            bg.paste(tile, (x, y))
    return bg


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    sprites = []
    for tier, name in enumerate(NAMES):
        img = draw_building(tier)
        img.save(OUT_DIR / f"{name}.png")
        draw_building(tier, winter=True).save(OUT_DIR / f"{name}_winter.png")
        sprites.append(img)

    # 1x lineup on grass, upscaled 1.25x (stays under 512px).
    gap = 8
    sheet = grass_backdrop(3 * W + 4 * gap, H + 2 * gap)
    for i, spr in enumerate(sprites):
        sheet.alpha_composite(spr, (gap + i * (W + gap), gap))
    sheet.resize((sheet.width * 5 // 4, sheet.height * 5 // 4), Image.NEAREST).save(PREVIEW_DIR / "zoo_exteriors.png")
    print(f"Wrote {len(NAMES)} zoo exteriors (+ winter) to {OUT_DIR}")


if __name__ == "__main__":
    main()
