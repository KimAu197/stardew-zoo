"""Build the zoo interior TMX from vanilla tilesheets with corner-based autotiling.

The map is described as a terrain grid (one letter per cell) plus fenced pen
rectangles. Every Back tile is picked from the terrain at its four corners, so
grass, dirt, dark grass, snow/ice and water blend with vanilla transition tiles.
Custom zoo_tiles is used only for the booth, board, studio, plaques and banner.

Usage: python3 tools/make_map.py
"""

import random
from pathlib import Path

from draw_tiles import (
    ACTION_TILES,
    COLS,
    ROWS,
    TS,
    T_BOARD_BOT_L,
    T_BOARD_BOT_R,
    T_BOARD_TOP_L,
    T_BOARD_TOP_R,
    T_BOOTH_AWN_L,
    T_BOOTH_AWN_M,
    T_BOOTH_AWN_R,
    T_BOOTH_CTR_L,
    T_BOOTH_CTR_M,
    T_BOOTH_CTR_R,
    T_PLAQUE_DINO,
    T_PLAQUE_FOREST,
    T_PLAQUE_ICE,
    T_PLAQUE_JUNGLE,
    T_PLAQUE_SAVANNA,
    T_PLAQUE_WATER,
    T_STUDIO_BOT_L,
    T_STUDIO_BOT_R,
    T_STUDIO_TOP_L,
    T_STUDIO_TOP_R,
    T_ZOO_BANNER,
)
from zoo_layout import BOARD, BOOTH, HABITATS, HAY, MAP_H, MAP_W, PLAZA, STUDIO, WARP_TILES

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "[CP] Stardew Zoo" / "assets"

# Harmless open-grass rectangle (x y w h); AnimalHouse logs a parse warning without it.
PRODUCE_AREA = (13, 13, 2, 5)


class Sheet:
    def __init__(self, name, source, width, height, columns):
        self.name = name
        self.source = source
        self.width = width
        self.height = height
        self.columns = columns
        self.tilecount = (width // 16) * (height // 16)
        self.firstgid = 1

    def gid(self, local):
        return 0 if local is None else self.firstgid + local


def build_sheets():
    sheets = [
        Sheet("outdoors", "spring_outdoorsTileSheet", 400, 1264, 25),
        Sheet("winter", "winter_outdoorsTileSheet", 400, 1264, 25),
        Sheet("island", "island_tilesheet_1", 512, 1040, 32),
        Sheet("town", "spring_town", 512, 1152, 32),
        Sheet("zoo_tiles", "zoo_tiles", COLS * TS, ROWS * TS, COLS),
    ]
    gid = 1
    for s in sheets:
        s.firstgid = gid
        gid += s.tilecount
    return {s.name: s for s in sheets}


# ---------------------------------------------------------------------------
# Vanilla tile tables. Corner keys are TL TR BL BR; "X" = the overlay terrain.
# ---------------------------------------------------------------------------

# spring_outdoorsTileSheet grass <-> dirt blob (Forest.tmx pond shore around 17-22,25-34;
# Town.tmx 70-71,20). Corners were verified by pixel sampling the sheet.
DIRT_ON_GRASS = {
    "...X": [200], "..XX": [201, 205], "..X.": [203],
    ".X.X": [225], "X.X.": [228],
    ".X..": [250], "XX..": [251, 230], "X...": [253],
    ".XXX": [202], "X.XX": [177], "XXX.": [178], "XX.X": [252],
    "XXXX": [226, 226, 227, 176],
    "X..X": [226], ".XX.": [226],
}
GRASS_FILL = [175] * 10 + [150] * 3 + [151, 152]

# spring_outdoorsTileSheet light grass <-> dark grass (Town.tmx 59-71,11-20; Forest.tmx 13-26,12-18).
DARK_ON_GRASS = {
    "...X": [325], "..XX": [326], "..X.": [327],
    ".X.X": [350], "X.X.": [352],
    ".X..": [375], "XX..": [376], "X...": [377],
    ".XXX": [328], "XXX.": [353], "X.XX": [378], "XX.X": [403],
    "XXXX": [351] * 6 + [329, 380, 304, 300],
    "X..X": [351], ".XX.": [351],
}

# winter_outdoorsTileSheet uses the same blob layout: snow ("grass") <-> ice ("dirt").
ICE_ON_SNOW = dict(DIRT_ON_GRASS, XXXX=[226, 227, 226, 206])
SNOW_FILL = [175] * 6 + [150, 151, 152, 254]

# Water body (Forest.tmx pond, e.g. 23-28,25-34). Plain frames 1229/1230/1231/1306 differ
# only in speckles; the Water=T flag is left off so animals can wade, so we animate instead.
WATER = 1229
WATER_FRAMES = [1229, 1230, 1231, 1306]
WATER_DECOR = [1274, 1274, 1322, 1249, 1324]
LILY_PAD = 1293                      # Forest.tmx Buildings, animated 1293-1296 @500ms
LILY_PAD_FRAMES = [1293, 1294, 1295, 1296]
LILY_FLOWER = 1318                   # animated 1318-1321 @450ms
LILY_FLOWER_FRAMES = [1318, 1319, 1320, 1321]
WATER_ROCK = 1252

# spring_town wooden picket fence (Town.tmx 59-68,13-19 and 95-102,83-90; 12-17,55-56).
# Each piece is (Buildings tile, Front tile drawn one row above, or None).
FENCE_TL = (832, 800)
FENCE_TOP = (833, 801)
FENCE_TR = (834, 802)
FENCE_L = (864, None)
FENCE_R = (866, None)
FENCE_BL_UPPER = (896, None)         # left post just above the bottom-left corner
FENCE_BR_UPPER = (898, None)
FENCE_BL = (928, None)
FENCE_BR = (930, None)
FENCE_BOTTOM = (929, 897)            # Front 897 is the picket tops on the row above
FENCE_GATE_L = (899, 867)            # braced end post (Town.tmx 64-65,18-19 pair)
FENCE_GATE_R = (900, 868)

# spring_town street lamp (Town.tmx 24,50-53): Buildings base, Front post/head above.
LAMP_BASE, LAMP_POST, LAMP_MID, LAMP_HEAD = 1003, 971, 939, 907
# spring_town cobble paving (Town.tmx 19-22,46-50).
COBBLE = [736, 737, 768, 769, 736, 768, 770]

# spring_outdoorsTileSheet oak trees: 3x4 canopy, trunk, root base.
OAK_A = ((0, 1, 2), (25, 26, 27), (50, 51, 52), (75, 76, 77), 101, 126)
OAK_B = ((3, 4, 5), (28, 29, 30), (53, 54, 55), (78, 79, 80), 104, 129)
BORDER_BUSH = 163
FLOWERS = [151, 152]

# island_tilesheet_1 palm and ferns.
PALM = ((364, 365, 366), (396, 397, 398), 429, 461)
FERNS = [369, 370]
JUNGLE_LEAVES = [30, 31]


def zeros():
    return [[0] * MAP_W for _ in range(MAP_H)]


def fence_rect(rect):
    x, y, w, h = rect
    return x - 1, y - 1, w + 2, h + 2


def build_terrain():
    """One letter per cell: g grass, d dirt, k dark grass, w water, c cobble, n snow, i ice."""
    t = [["g"] * MAP_W for _ in range(MAP_H)]

    def fill(x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                t[y][x] = c

    # visitor loop: outer ring, three cross rows, and a 2-wide central aisle to the door
    for y in (1, 11, 21, 28):
        fill(1, y, 36, y, "d")
    fill(1, 1, 1, 28, "d")
    fill(36, 1, 36, 28, "d")
    fill(18, 1, 19, MAP_H - 1, "d")

    # plaza: cobble square inside a dirt apron
    px, py, pw, ph = PLAZA
    fill(px - 1, py - 1, px + pw, py + ph, "d")
    fill(px, py, px + pw - 1, py + ph - 1, "c")

    ix, iy, iw, ih = HABITATS["Ice"]
    fill(ix, iy, ix + iw - 1, iy + ih - 1, "n")
    fill(ix + 2, iy + 2, ix + 6, iy + 4, "i")
    fill(ix + 3, iy + 1, ix + 5, iy + 1, "i")

    wx, wy, ww, wh = HABITATS["Water"]
    fill(wx, wy, wx + ww - 1, wy + wh - 1, "d")
    fill(wx + 2, wy + 2, wx + 6, wy + 4, "w")
    fill(wx + 1, wy + 3, wx + 7, wy + 3, "w")
    fill(wx + 3, wy + 1, wx + 5, wy + 1, "w")

    sx, sy, sw, sh = HABITATS["Savanna"]
    fill(sx + 1, sy + 2, sx + 7, sy + 4, "d")
    fill(sx + 3, sy + 1, sx + 6, sy + 1, "d")

    for name in ("Jungle", "Forest"):
        x, y, w, h = HABITATS[name]
        fill(x, y, x + w - 1, y + h - 1, "k")

    x, y, w, h = HABITATS["Prehistoric"]
    fill(x, y, x + w - 1, y + h - 1, "d")
    return t


def corner_mask(t, x, y, test, rule):
    """Corner key for cell (x, y). rule='any' grows the terrain, 'all' shrinks it."""
    key = []
    for vx, vy in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)):
        cells = [
            t[cy][cx]
            for cx, cy in ((vx - 1, vy - 1), (vx, vy - 1), (vx - 1, vy), (vx, vy))
            if 0 <= cx < MAP_W and 0 <= cy < MAP_H
        ]
        hits = [test(c) for c in cells]
        key.append("X" if (any(hits) if rule == "any" else all(hits)) else ".")
    return "".join(key)


def build_layers(S):
    out, win, isl, town, zoo = (
        S["outdoors"], S["winter"], S["island"], S["town"], S["zoo_tiles"]
    )
    back, buildings, front, always = zeros(), zeros(), zeros(), zeros()
    rng = random.Random(1234)
    terrain = build_terrain()

    def put(layer, x, y, sheet, local, overwrite=True):
        if 0 <= x < MAP_W and 0 <= y < MAP_H:
            if overwrite or layer[y][x] == 0:
                layer[y][x] = sheet.gid(local)

    # --- Back: autotiled terrain ---
    for y in range(MAP_H):
        for x in range(MAP_W):
            c = terrain[y][x]
            if c == "w":
                put(back, x, y, out, rng.choice(WATER_DECOR) if rng.random() < 0.2 else WATER)
            elif c == "c":
                put(back, x, y, town, rng.choice(COBBLE))
            elif c in "ni":
                key = corner_mask(terrain, x, y, lambda v: v == "i", "all")
                table = ICE_ON_SNOW.get(key) if key != "...." else SNOW_FILL
                put(back, x, y, win, rng.choice(table))
            else:
                key = corner_mask(terrain, x, y, lambda v: v in "dwc", "any")
                if key != "....":
                    put(back, x, y, out, rng.choice(DIRT_ON_GRASS[key]))
                    continue
                key = corner_mask(terrain, x, y, lambda v: v == "k", "all")
                if key != "....":
                    put(back, x, y, out, rng.choice(DARK_ON_GRASS[key]))
                else:
                    put(back, x, y, out, rng.choice(GRASS_FILL))

    # --- pen fences: closed Town-style picket rectangles with a braced gate ---
    plaques = {
        "Ice": T_PLAQUE_ICE, "Water": T_PLAQUE_WATER, "Savanna": T_PLAQUE_SAVANNA,
        "Jungle": T_PLAQUE_JUNGLE, "Forest": T_PLAQUE_FOREST, "Prehistoric": T_PLAQUE_DINO,
    }
    for name, rect in HABITATS.items():
        fx, fy, fw, fh = fence_rect(rect)
        left, right, top, bottom = fx, fx + fw - 1, fy, fy + fh - 1
        gate = rect[0] + rect[2] // 2

        def piece(x, y, p):
            put(buildings, x, y, town, p[0])
            if p[1] is not None:
                put(front, x, y - 1, town, p[1])

        for x in range(left, right + 1):
            if x == left:
                piece(x, top, FENCE_TL)
                piece(x, bottom, FENCE_BL)
            elif x == right:
                piece(x, top, FENCE_TR)
                piece(x, bottom, FENCE_BR)
            else:
                piece(x, top, FENCE_TOP)
                piece(x, bottom, FENCE_GATE_L if x == gate else FENCE_GATE_R if x == gate + 1 else FENCE_BOTTOM)
        for y in range(top + 1, bottom):
            upper = y == bottom - 1
            piece(left, y, FENCE_BL_UPPER if upper else FENCE_L)
            piece(right, y, FENCE_BR_UPPER if upper else FENCE_R)
        put(always, rect[0] + rect[2] // 2, top - 1, zoo, plaques[name])

    # --- map border: bushes, open south door ---
    for x in range(MAP_W):
        for y in range(MAP_H):
            if (x in (0, MAP_W - 1) or y in (0, MAP_H - 1)) and not (y == MAP_H - 1 and x in (18, 19)):
                put(buildings, x, y, out, BORDER_BUSH)

    # --- props ---
    def tree(base_x, base_y, oak, solid=True):
        rows, trunk, root = oak[:4], oak[4], oak[5]
        for i, row in enumerate(rows):
            layer = always if i < 3 else front
            for dx, tid in enumerate(row):
                put(layer, base_x - 1 + dx, base_y - 5 + i, out, tid, overwrite=False)
        put(buildings if solid else front, base_x, base_y - 1, out, trunk)
        put(buildings if solid else front, base_x, base_y, out, root)

    def lamp(x, y):
        put(buildings, x, y, town, LAMP_BASE)
        put(front, x, y - 1, town, LAMP_POST)
        put(front, x, y - 2, town, LAMP_MID)
        put(front, x, y - 3, town, LAMP_HEAD)

    def flower_bed(x, y):
        for dx in range(3):
            put(back, x + dx, y, out, FLOWERS[dx % 2])

    # shade trees and flower beds in the open lawns beside the central aisle
    tree(14, 9, OAK_A)
    tree(23, 9, OAK_B)
    tree(14, 26, OAK_B)
    tree(23, 26, OAK_A)
    flower_bed(14, 3)
    flower_bed(21, 3)

    px, py, pw, ph = PLAZA
    lamps = [(px - 1, py - 1), (px + pw, py - 1), (13, 20), (24, 20), (16, 27), (21, 27)]
    for x, y in lamps:
        lamp(x, y)

    # flowers on lawn edges (Back, walkable)
    for x, y in ((13, 4), (16, 7), (21, 7), (24, 4), (13, 13), (24, 14), (13, 23), (24, 24), (16, 24), (21, 23)):
        if terrain[y][x] == "g":
            put(back, x, y, out, rng.choice(FLOWERS))

    # pen props stay off Buildings so animals can be placed on any pen tile
    wx, wy, ww, wh = HABITATS["Water"]
    for dx, dy in ((3, 3), (5, 4)):
        put(front, wx + dx, wy + dy, out, LILY_PAD)
    put(front, wx + 4, wy + 2, out, LILY_FLOWER)
    put(back, wx + 6, wy + 2, out, WATER_ROCK)

    sx, sy, sw, sh = HABITATS["Savanna"]
    tree(sx + 7, sy + 4, OAK_B, solid=False)
    for dx, dy in ((0, 5), (8, 5), (2, 0)):
        put(front, sx + dx, sy + dy, isl, FERNS[0])

    jx, jy, jw, jh = HABITATS["Jungle"]
    for bx in (jx + 1, jx + 7):
        canopy, mid, trunk, base = PALM
        for dx in range(3):
            put(always, bx - 1 + dx, jy - 1, isl, canopy[dx], overwrite=False)
            put(front, bx - 1 + dx, jy, isl, mid[dx])
        put(front, bx, jy + 1, isl, trunk)
        put(front, bx, jy + 2, isl, base)
    for i, (dx, dy) in enumerate(((4, 1), (3, 4), (6, 5), (0, 5), (8, 4))):
        put(front, jx + dx, jy + dy, isl, (FERNS + JUNGLE_LEAVES)[i % 4])

    fx_, fy_, fw_, fh_ = HABITATS["Forest"]
    tree(fx_ + 1, fy_ + 2, OAK_A, solid=False)
    tree(fx_ + 7, fy_ + 2, OAK_B, solid=False)
    put(front, fx_ + 4, fy_ + 2, isl, FERNS[1])

    hx, hy, hw, hh = HABITATS["Prehistoric"]
    for dx, dy in ((8, 0), (0, 2), (5, 0)):
        put(front, hx + dx, hy + dy, isl, FERNS[dx % 2])

    # --- plaza props: booth, board, studio (tiles/actions fixed for the C# side) ---
    put(front, 16, 13, zoo, T_BOOTH_AWN_L)
    put(front, 17, 13, zoo, T_BOOTH_AWN_M)
    put(front, 18, 13, zoo, T_BOOTH_AWN_R)
    put(buildings, 16, 14, zoo, T_BOOTH_CTR_L)
    put(buildings, 17, 14, zoo, T_BOOTH_CTR_M)
    put(buildings, 18, 14, zoo, T_BOOTH_CTR_R)
    put(front, 19, 13, zoo, T_BOARD_TOP_L)
    put(front, 20, 13, zoo, T_BOARD_TOP_R)
    put(buildings, 19, 14, zoo, T_BOARD_BOT_L)
    put(buildings, 20, 14, zoo, T_BOARD_BOT_R)
    put(front, 18, 15, zoo, T_STUDIO_TOP_L)
    put(front, 19, 15, zoo, T_STUDIO_TOP_R)
    put(buildings, 18, 16, zoo, T_STUDIO_BOT_L)
    put(buildings, 19, 16, zoo, T_STUDIO_BOT_R)

    # ZOO banner over the entrance
    put(always, 18, 27, zoo, T_ZOO_BANNER)
    put(always, 19, 27, zoo, T_ZOO_BANNER)

    # the feed hopper (IndoorItem) needs a clear tile
    buildings[HAY[1]][HAY[0]] = 0
    return (back, buildings, front, always), lamps


def csv(layer):
    lines = []
    for y, row in enumerate(layer):
        line = ",".join(str(v) for v in row)
        if y != len(layer) - 1:
            line += ","
        lines.append(line)
    return "\n" + "\n".join(lines) + "\n"


def animation_xml(frames_by_tile):
    chunks = []
    for tid, (frames, duration) in frames_by_tile.items():
        body = "\n".join(f'        <frame tileid="{f}" duration="{duration}" />' for f in frames)
        chunks.append(f'    <tile id="{tid}">\n      <animation>\n{body}\n      </animation>\n    </tile>')
    return "\n".join(chunks)


def outdoor_animations():
    anims = {}
    for i, tid in enumerate(WATER_FRAMES):
        anims[tid] = (WATER_FRAMES[i:] + WATER_FRAMES[:i], 600)
    anims[LILY_PAD] = (LILY_PAD_FRAMES, 500)
    anims[LILY_FLOWER] = (LILY_FLOWER_FRAMES, 450)
    return anims


def write_tmx(sheets, layers, lamps):
    back, buildings, front, always = layers
    warp = " ".join(f"{x} {y} Farm 0 0" for x, y in WARP_TILES)
    action_xml = []
    for tid, action in ACTION_TILES.items():
        action_xml.append(
            f'    <tile id="{tid}">\n      <properties>\n'
            f'        <property name="Action" type="string" value="{action}" />\n'
            f"      </properties>\n    </tile>"
        )

    tileset_xml = []
    for s in sheets.values():
        extra = ""
        if s.name == "outdoors":
            extra = "\n" + animation_xml(outdoor_animations())
        if s.name == "zoo_tiles":
            extra = "\n" + "\n".join(action_xml)
        tileset_xml.append(
            f'  <tileset firstgid="{s.firstgid}" name="{s.name}" tilewidth="16" tileheight="16" '
            f'tilecount="{s.tilecount}" columns="{s.columns}">\n'
            f'    <image source="{s.source}" width="{s.width}" height="{s.height}" />{extra}\n'
            f"  </tileset>"
        )

    lights = " ".join(f"{x} {y - 3} 4" for x, y in lamps) + " 18 28 4"
    produce = " ".join(str(v) for v in PRODUCE_AREA)
    xml = f"""<?xml version="1.0"?>
<map version="1.4" tiledversion="1.4.2" orientation="orthogonal" renderorder="right-down" compressionlevel="0" width="{MAP_W}" height="{MAP_H}" tilewidth="16" tileheight="16" infinite="0" nextlayerid="10" nextobjectid="8">
  <properties>
    <property name="AmbientLight" type="string" value="255 255 255" />
    <property name="Light" type="string" value="{lights}" />
    <property name="ProduceArea" type="string" value="{produce}" />
    <property name="Warp" type="string" value="{warp}" />
  </properties>
{chr(10).join(tileset_xml)}
  <layer id="1" name="Back" width="{MAP_W}" height="{MAP_H}">
    <data encoding="csv">{csv(back)}</data>
  </layer>
  <layer id="2" name="Buildings" width="{MAP_W}" height="{MAP_H}">
    <data encoding="csv">{csv(buildings)}</data>
  </layer>
  <layer id="3" name="Front" width="{MAP_W}" height="{MAP_H}">
    <data encoding="csv">{csv(front)}</data>
  </layer>
  <layer id="4" name="AlwaysFront" width="{MAP_W}" height="{MAP_H}">
    <data encoding="csv">{csv(always)}</data>
  </layer>
  <objectgroup id="5" name="Buildings" visible="false">
    <object id="1" name="TileData" x="{BOOTH[0] * 16}" y="{BOOTH[1] * 16}" width="16" height="16">
      <properties>
        <property name="Action" type="string" value="StardewZoo_TicketBooth" />
      </properties>
    </object>
    <object id="2" name="TileData" x="{BOARD[0] * 16}" y="{BOARD[1] * 16}" width="16" height="16">
      <properties>
        <property name="Action" type="string" value="StardewZoo_ReviewBoard" />
      </properties>
    </object>
    <object id="3" name="TileData" x="{STUDIO[0] * 16}" y="{STUDIO[1] * 16}" width="16" height="16">
      <properties>
        <property name="Action" type="string" value="StardewZoo_RecordingStudio" />
      </properties>
    </object>
  </objectgroup>
</map>
"""
    path = ASSETS / "StardewZoo.tmx"
    path.write_text(xml)
    return path


def main():
    import draw_tiles
    draw_tiles.main()
    ASSETS.mkdir(parents=True, exist_ok=True)
    sheets = build_sheets()
    layers, lamps = build_layers(sheets)
    path = write_tmx(sheets, layers, lamps)
    from render_map import render_tmx
    preview_dir = Path(__file__).resolve().parent / "previews"
    render_tmx(path, Path("/tmp/zoo_art") / "interior_v2.png", scale=2)
    render_tmx(path, preview_dir / "zoo_map.png", scale=2)
    print(f"Wrote map {MAP_W}x{MAP_H} to {path}")


if __name__ == "__main__":
    main()
