"""Build the zoo interior TMX.

Ground is a vertex terrain grid blended per pixel by draw_tiles.TerrainBlender
(vanilla grass/dark grass/water textures plus custom paving, sand, shallow water,
snow, ice, savanna grass, mud and volcanic ground). Every map cell holds a stack
of components per layer; stacks are composited into zoo_tiles so ground decals
can live on Back (under the animals) and canopies can overlap fences.

Layering rules:
  - pens never get Buildings tiles (HabitatKeeper drops animals on any pen tile);
    a prop's bottom row is baked into Back, upper rows go on Front, canopies on AlwaysFront;
  - plaza / park props use Buildings for their footprint and Front above it.

The map is one AnimalHouse split into isolated regions (see zoo_layout.py): the open-air
park plus four walk-in pavilion interiors (make_pavilions.py) surrounded by void.

Usage: python3 tools/make_map.py
"""

import random
from pathlib import Path

from PIL import Image

import make_pavilions
from draw_pavilions import build_pavilion_objects, extend_blender
from draw_tiles import OUT as ZOO_PNG
from draw_tiles import PRIORITY, TerrainBlender, ZooSheet, build_objects, hnoise, save_preview
from zoo_layout import (BOARD, BOOTH, FACADES, HABITATS, HAY, MAP_H, MAP_W, OPEN_PENS, OUTDOOR, PATHS, PAVILIONS,
                        PRODUCE_AREA, REGIONS, STUDIO, WARP_TILES, ZOO_PERCHES, facade_door, inside_door,
                        write_csharp)

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "[CP] Stardew Zoo" / "assets"
LAYERS = ("Back", "Buildings", "Front", "AlwaysFront")

PERCH_HEIGHT = {"palm": 3, "oak": 4, "snag": 2.5}
TOUCH_ACTION = "StardewZoo_Pavilion"


class Sheet:
    def __init__(self, name, source, width, height, columns):
        self.name = name
        self.source = source
        self.width = width
        self.height = height
        self.columns = columns
        self.tilecount = (width // 16) * (height // 16)
        self.firstgid = 1


VANILLA_SHEETS = [
    Sheet("outdoors", "spring_outdoorsTileSheet", 400, 1264, 25),
    Sheet("winter", "winter_outdoorsTileSheet", 400, 1264, 25),
    Sheet("island", "island_tilesheet_1", 512, 1040, 32),
    Sheet("town", "spring_town", 512, 1152, 32),
]

# --- vanilla tiles ---------------------------------------------------------
WATER_FRAMES = [1229, 1230, 1231, 1306]

# spring_town wooden picket fence (Town.tmx 59-68,13-19 and 95-102,83-90; 12-17,55-56).
# Each piece is (Buildings tile, Front tile drawn one row above, or None).
FENCE_TL = (832, 800)
FENCE_TOP = (833, 801)
FENCE_TR = (834, 802)
FENCE_L = (864, None)
FENCE_R = (866, None)
FENCE_BL_UPPER = (896, None)
FENCE_BR_UPPER = (898, None)
FENCE_BL = (928, None)
FENCE_BR = (930, None)
FENCE_BOTTOM = (929, 897)
FENCE_GATE_L = (899, 867)
FENCE_GATE_R = (900, 868)

# spring_town street lamp (Town.tmx 24,50-53): Buildings base, Front post/head above.
LAMP_BASE, LAMP_POST, LAMP_MID, LAMP_HEAD = 1003, 971, 939, 907

# spring_outdoorsTileSheet oak trees: 3x4 canopy, trunk, root base.
OAK_A = ((0, 1, 2), (25, 26, 27), (50, 51, 52), (75, 76, 77), 101, 126)
OAK_B = ((3, 4, 5), (28, 29, 30), (53, 54, 55), (78, 79, 80), 104, 129)
BORDER_BUSH = 163

# island_tilesheet_1 palm and ferns.
PALM = ((364, 365, 366), (396, 397, 398), 429, 461)
FERNS = [369, 370]


def O(t):
    return ("outdoors", t)


def T(t):
    return ("town", t)


def I(t):
    return ("island", t)


# ---------------------------------------------------------------------------
# terrain
# ---------------------------------------------------------------------------

def build_cells():
    """One letter per cell (see draw_tiles.PRIORITY)."""
    t = [["x"] * MAP_W for _ in range(MAP_H)]

    def fill(x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                t[y][x] = c

    ox, oy, ow, oh = OUTDOOR
    fill(ox, oy, ox + ow - 1, oy + oh - 1, "g")
    for x, y, w, h in PATHS:
        fill(x, y, x + w - 1, y + h - 1, "p")
    fill(15, 13, 22, 19, "q")

    base = {"Savanna": "y", "Forest": "g"}
    for name, (x, y, w, h) in OPEN_PENS.items():
        fill(x, y, x + w - 1, y + h - 1, base[name])
    make_pavilions.cells(t)
    return t


def build_vertices(cells):
    V = [["g"] * (MAP_W + 1) for _ in range(MAP_H + 1)]
    for vy in range(MAP_H + 1):
        for vx in range(MAP_W + 1):
            around = [cells[cy][cx] for cx, cy in ((vx - 1, vy - 1), (vx, vy - 1), (vx - 1, vy), (vx, vy))
                      if 0 <= cx < MAP_W and 0 <= cy < MAP_H]
            V[vy][vx] = max(around, key=PRIORITY.index)
    return V


def blob(V, pen, cx, cy, rx, ry, terrain, seed=0):
    """Paint an organic ellipse of vertices strictly inside a pen."""
    x, y, w, h = HABITATS[pen]
    for vy in range(y + 1, y + h):
        for vx in range(x + 1, x + w):
            r = ((vx - cx) / rx) ** 2 + ((vy - cy) / ry) ** 2 + 0.18 * hnoise(vx, vy, seed)
            if r <= 1:
                V[vy][vx] = terrain


def paint_pens(V):
    blob(V, "Savanna", 5.5, 16.6, 2.3, 1.4, "r", 6)
    blob(V, "Savanna", 10.2, 14.4, 1.4, 1.0, "r", 7)
    blob(V, "Savanna", 9.6, 17.3, 2.0, 1.2, "h", 8)
    blob(V, "Savanna", 9.6, 17.4, 1.3, 0.7, "w", 9)

    blob(V, "Forest", 6.5, 24.6, 2.6, 1.0, "k", 12)
    blob(V, "Forest", 10.6, 24.4, 1.4, 1.0, "k", 13)

    make_pavilions.paint(V, blob)


# ---------------------------------------------------------------------------
# map with component stacks
# ---------------------------------------------------------------------------

class ZooMap:
    def __init__(self, zs: ZooSheet):
        self.zs = zs
        self.cells = {n: [[[] for _ in range(MAP_W)] for _ in range(MAP_H)] for n in LAYERS}
        self.used = set()
        self.lamps = []

    def put(self, layer, x, y, comp):
        if not (0 <= x < MAP_W and 0 <= y < MAP_H) or comp is None:
            return
        cell = self.cells[layer][y][x]
        if layer == "Buildings":
            cell[:] = [comp]
        else:
            cell.append(comp)

    def obj(self, name, x, y, rows):
        """Place a registered object; rows lists the layer per object row (None = skip)."""
        grid = self.zs.objects[name]
        for r, row in enumerate(grid):
            layer = rows[r] if isinstance(rows, (list, tuple)) else rows
            for c, tid in enumerate(row):
                if tid is None or layer is None:
                    continue
                self.put(layer, x + c, y + r, ("zoo", tid))
                self.used.add((x + c, y + r))

    def tid(self, name, r=0, c=0):
        return ("zoo", self.zs.objects[name][r][c])

    # --- vanilla multi-tile props ---
    def oak(self, x, y, oak, in_pen):
        rows, trunk, root = oak[:4], oak[4], oak[5]
        for i, row in enumerate(rows):
            for dx, t in enumerate(row):
                self.put("AlwaysFront" if i < 3 else "Front", x - 1 + dx, y - 5 + i, O(t))
        if in_pen:
            self.put("Front", x, y - 1, O(trunk))
            self.put("Back", x, y, O(root))
        else:
            self.put("Buildings", x, y - 1, O(trunk))
            self.put("Buildings", x, y, O(root))
        self.used.update({(x, y), (x, y - 1)})

    def palm(self, x, y, vines=False):
        canopy, mid, trunk, base = PALM
        for dx in range(3):
            self.put("AlwaysFront", x - 1 + dx, y - 3, I(canopy[dx]))
            self.put("Front", x - 1 + dx, y - 2, I(mid[dx]))
            if vines and dx != 1:
                self.put("Front", x - 1 + dx, y - 2, self.tid("hanging_vine"))
        self.put("Front", x, y - 1, I(trunk))
        self.put("Back", x, y, I(base))
        self.used.update({(x, y), (x, y - 1)})

    def town_lamp(self, x, y):
        self.put("Buildings", x, y, T(LAMP_BASE))
        self.put("Front", x, y - 1, T(LAMP_POST))
        self.put("Front", x, y - 2, T(LAMP_MID))
        self.put("Front", x, y - 3, T(LAMP_HEAD))
        self.lamps.append((x, y - 3))
        self.used.add((x, y))

    def zoo_lamp(self, x, y):
        self.obj("lamp", x, y - 2, ["Front", "Front", "Buildings"])
        self.lamps.append((x, y - 2))

    # --- resolve to gids ---
    def resolve(self):
        out = {}
        for layer in LAYERS:
            grid = []
            for row in self.cells[layer]:
                line = []
                for stack in row:
                    if not stack:
                        line.append(None)
                    elif len(stack) == 1:
                        line.append(stack[0])
                    else:
                        line.append(self.zs.composite(stack))
                grid.append(line)
            out[layer] = grid
        return out


def scatter(m, rng, pen, decals, count, ok, layer="Back"):
    """Drop single-tile decals on free cells of a pen whose terrain passes ok(corners)."""
    x, y, w, h = HABITATS[pen]
    spots = [(cx, cy) for cy in range(y, y + h) for cx in range(x, x + w)
             if (cx, cy) not in m.used and ok(m.corners[cy][cx])]
    rng.shuffle(spots)
    for i, (cx, cy) in enumerate(spots[:count]):
        m.put(layer, cx, cy, m.tid(decals[i % len(decals)]))
        m.used.add((cx, cy))


def fences(m):
    for name, (x, y, w, h) in OPEN_PENS.items():
        left, right, top, bottom = x - 1, x + w, y - 1, y + h
        gate = x + w // 2

        def piece(px, py, p):
            m.put("Buildings", px, py, T(p[0]))
            if p[1] is not None:
                m.put("Front", px, py - 1, T(p[1]))

        for px in range(left, right + 1):
            if px == left:
                piece(px, top, FENCE_TL)
                piece(px, bottom, FENCE_BL)
            elif px == right:
                piece(px, top, FENCE_TR)
                piece(px, bottom, FENCE_BR)
            else:
                piece(px, top, FENCE_TOP)
                piece(px, bottom, FENCE_GATE_L if px == gate else FENCE_GATE_R if px == gate + 1 else FENCE_BOTTOM)
        for py in range(top + 1, bottom):
            upper = py == bottom - 1
            piece(left, py, FENCE_BL_UPPER if upper else FENCE_L)
            piece(right, py, FENCE_BR_UPPER if upper else FENCE_R)


def pens(m, rng):
    allin = lambda *ts: (lambda cs: all(c in ts for c in cs))

    # Savanna: dry grass, red earth, watering hole, acacia, termite mounds.
    m.obj("acacia", 7, 12, ["AlwaysFront", "AlwaysFront", "Front", "Back"])
    m.obj("termite", 4, 13, ["Front", "Back"])
    m.obj("termite", 11, 16, ["Front", "Back"])
    m.obj("savanna_rock", 6, 18, "Back")
    m.obj("savanna_rock", 3, 15, "Back")
    scatter(m, rng, "Savanna", ["tuft_a", "tuft_b"], 9, allin("y", "r"))

    # Forest: two oaks + a dead snag for owls, fallen log, stump, moss, mushrooms.
    (ax, ay), (bx, by), (sx, sy) = ZOO_PERCHES["Forest"]
    m.oak(ax, ay, OAK_A, in_pen=True)
    m.oak(bx, by, OAK_B, in_pen=True)
    m.obj("snag", sx, sy - 2, ["Front", "Front", "Back"])
    m.obj("log", 5, 25, "Back")
    m.obj("stump", 11, 24, "Back")
    scatter(m, rng, "Forest", ["moss", "mushrooms", "litter_a", "moss"], 6, allin("g", "k"))

    # Ice, Water, Jungle, Prehistoric live in their walk-in pavilions.
    make_pavilions.facades(m)
    make_pavilions.interiors(m, rng, scatter, FERNS, I)


def strips(m):
    """Park furniture on the grass strips between pens and the loop path."""
    for row, (left_pen, right_pen) in ((10, ("Ice", "Water")), (20, ("Savanna", "Jungle")),
                                       (27, ("Forest", "Prehistoric"))):
        m.obj(f"plaque_{left_pen}", 6, row, "Buildings")
        m.obj(f"plaque_{right_pen}", 29, row, "Buildings")
        if row != 20:  # the forest oaks overhang the row-20 strip on the left
            m.zoo_lamp(3, row)
            m.obj("bin", 5, row, "Buildings")
            m.obj("planter_red", 10, row, "Buildings")
        m.zoo_lamp(12, row)
        m.zoo_lamp(25, row)
        m.obj("planter_yellow", 27, row, "Buildings")
        m.obj("bin_recycle", 32, row, "Buildings")
        m.zoo_lamp(34, row)


def lawns(m):
    # top lawns: carts, shade trees, benches facing the path, a signpost
    m.obj("snack_cart", 16, 2, ["Front", "Buildings"])
    m.obj("icecream_cart", 20, 2, ["Front", "Buildings"])
    m.oak(14, 8, OAK_A, in_pen=False)
    m.oak(23, 8, OAK_B, in_pen=False)
    m.zoo_lamp(17, 7)
    m.zoo_lamp(20, 7)
    m.obj("bench", 13, 10, "Buildings")
    m.obj("bench", 23, 10, "Buildings")
    m.obj("bin", 16, 10, "Buildings")
    m.obj("bin_recycle", 21, 10, "Buildings")
    m.obj("sign_Ice_Water", 17, 9, ["Front", "Buildings"])
    m.obj("balloons", 16, 5, ["Front", "Buildings"])
    m.obj("planter_pink", 24, 9, "Buildings")
    m.obj("planter_pink", 13, 9, "Buildings")
    m.obj("planter_blue", 13, 2, "Buildings")
    m.obj("planter_blue", 24, 2, "Buildings")

    # middle columns beside the plaza
    m.obj("planter_pink", 13, 12, "Buildings")
    m.obj("planter_pink", 24, 12, "Buildings")
    m.obj("bin", 24, 16, "Buildings")
    m.zoo_lamp(24, 20)
    m.obj("sign_Savanna_Jungle", 13, 18, ["Front", "Buildings"])

    # bottom lawns: entrance arch, trees, benches, ice cream
    m.obj("arch", 17, 25, ["AlwaysFront", "AlwaysFront", "Buildings"])
    m.oak(14, 26, OAK_B, in_pen=False)
    m.oak(23, 26, OAK_A, in_pen=False)
    m.obj("sign_Forest_Prehistoric", 17, 22, ["Front", "Buildings"])
    m.obj("icecream_cart", 20, 22, ["Front", "Buildings"])
    m.obj("balloons", 21, 25, ["Front", "Buildings"])
    m.zoo_lamp(16, 25)
    m.obj("bench", 15, 27, "Buildings")
    m.obj("bench", 21, 27, "Buildings")
    m.obj("planter_yellow", 13, 27, "Buildings")
    m.obj("planter_yellow", 24, 27, "Buildings")

    # beside the ice pavilion (the old pen fence ring)
    for y in (3, 6, 9):
        m.obj("planter_blue", 2, y, "Buildings")
        m.obj("planter_blue", 12, y, "Buildings")


def plaza(m):
    # booth / board / studio: bottom rows on Buildings carry the Action tiles
    m.obj("booth", 16, 11, ["Front", "Front", "Front", "Buildings"])
    m.obj("board", 19, 11, ["Front", "Front", "Front", "Buildings"])
    m.obj("speaker", 17, 15, ["Front", "Buildings"])
    m.obj("studio", 18, 15, ["Front", "Buildings"])
    m.obj("mic", 20, 15, ["Front", "Buildings"])
    m.obj("fountain", 18, 18, "Buildings")
    m.obj("bench", 15, 19, "Buildings")
    m.obj("bench", 21, 19, "Buildings")
    for x, y, kind in ((15, 14, "planter_yellow"), (22, 14, "planter_yellow"),
                       (15, 17, "planter_red"), (22, 17, "planter_red")):
        m.obj(kind, x, y, "Buildings")
    m.obj("bin", 14, 19, "Buildings")
    m.obj("bin_recycle", 23, 19, "Buildings")
    m.town_lamp(15, 12)
    m.town_lamp(22, 12)


def action_tiles(zs):
    """Every counter tile of a prop triggers its action; the C#-documented tiles are among them."""
    acts = {}
    for name, action in (("booth", "StardewZoo_TicketBooth"), ("board", "StardewZoo_ReviewBoard"),
                         ("studio", "StardewZoo_RecordingStudio")):
        for tid in zs.objects[name][-1]:
            if tid is not None:
                acts[tid] = action
    return acts


def build(zs):
    rng = random.Random(1234)
    blender = TerrainBlender(zs)
    extend_blender(blender, zs)
    zs.vanilla_anims.update({("outdoors", t): WATER_FRAMES[i:] + WATER_FRAMES[:i]
                             for i, t in enumerate(WATER_FRAMES)})

    cells = build_cells()
    V = build_vertices(cells)
    paint_pens(V)

    m = ZooMap(zs)
    m.terrain = cells
    m.corners = [[(V[y][x], V[y][x + 1], V[y + 1][x], V[y + 1][x + 1]) for x in range(MAP_W)] for y in range(MAP_H)]
    for y in range(MAP_H):
        for x in range(MAP_W):
            if cells[y][x] != "x":
                m.put("Back", x, y, blender.tile(m.corners[y][x], rng))

    ox, oy, ow, oh = OUTDOOR
    for x in range(ox, ox + ow):
        for y in range(oy, oy + oh):
            edge = x in (ox, ox + ow - 1) or y in (oy, oy + oh - 1)
            if edge and not (y == oy + oh - 1 and x in (18, 19)):
                m.put("Buildings", x, y, O(BORDER_BUSH))
    fences(m)
    plaza(m)
    pens(m, rng)
    strips(m)
    lawns(m)

    m.cells["Buildings"][HAY[1]][HAY[0]] = []
    return m


def csv(grid):
    lines = []
    for y, row in enumerate(grid):
        line = ",".join(str(v) for v in row)
        if y != len(grid) - 1:
            line += ","
        lines.append(line)
    return "\n" + "\n".join(lines) + "\n"


def animation_xml(anims):
    chunks = []
    for tid, (frames, ms) in sorted(anims.items()):
        body = "\n".join(f'        <frame tileid="{f}" duration="{ms}" />' for f in frames)
        chunks.append(f'    <tile id="{tid}">\n      <animation>\n{body}\n      </animation>\n    </tile>')
    return chunks


def write_tmx(zs, m, resolved):
    sheets = list(VANILLA_SHEETS)
    zsheet = zs.save(ZOO_PNG)
    zoo = Sheet("zoo_tiles", "zoo_tiles", zsheet.width, zsheet.height, zsheet.width // 16)
    sheets.append(zoo)
    gid = 1
    for s in sheets:
        s.firstgid = gid
        gid += s.tilecount
    by_name = {s.name: s for s in sheets}
    by_name["zoo"] = zoo

    layers = {}
    for layer, grid in resolved.items():
        layers[layer] = [[0 if c is None else by_name[c[0]].firstgid + c[1] for c in row] for row in grid]

    outdoor_anims = {t: (WATER_FRAMES[i:] + WATER_FRAMES[:i], 600) for i, t in enumerate(WATER_FRAMES)}
    acts = action_tiles(zs)
    zoo_tiles_xml = animation_xml(zs.anims)
    for tid, action in sorted(acts.items()):
        zoo_tiles_xml.append(
            f'    <tile id="{tid}">\n      <properties>\n'
            f'        <property name="Action" type="string" value="{action}" />\n'
            f"      </properties>\n    </tile>")

    tileset_xml = []
    for s in sheets:
        extra = ""
        if s.name == "outdoors":
            extra = "\n" + "\n".join(animation_xml(outdoor_anims))
        if s.name == "zoo_tiles":
            extra = "\n" + "\n".join(zoo_tiles_xml)
        tileset_xml.append(
            f'  <tileset firstgid="{s.firstgid}" name="{s.name}" tilewidth="16" tileheight="16" '
            f'tilecount="{s.tilecount}" columns="{s.columns}">\n'
            f'    <image source="{s.source}" width="{s.width}" height="{s.height}" />{extra}\n'
            f"  </tileset>")

    warp = " ".join(f"{x} {y} Farm 0 0" for x, y in WARP_TILES)
    lights = " ".join(f"{x} {y} 4" for x, y in m.lamps) + " 18 28 4"
    produce = " ".join(str(v) for v in PRODUCE_AREA)

    perch_objs = []
    oid = 4

    def tile_data(x, y, name, value):
        nonlocal oid
        perch_objs.append(
            f'    <object id="{oid}" name="TileData" x="{x * 16}" y="{y * 16}" width="16" height="16">\n'
            f'      <properties>\n'
            f'        <property name="{name}" type="string" value="{value}" />\n'
            f'      </properties>\n    </object>')
        oid += 1

    kinds = {"Jungle": ["palm"] * len(ZOO_PERCHES["Jungle"]), "Forest": ["oak", "oak", "snag"]}
    for pen, spots in ZOO_PERCHES.items():
        for (x, y), kind in zip(spots, kinds[pen]):
            tile_data(x, y, "ZooPerch", PERCH_HEIGHT[kind])
    for name in PAVILIONS:
        tile_data(*facade_door(name), "TouchAction", f"{TOUCH_ACTION} {name} In")
        tile_data(*inside_door(name), "TouchAction", f"{TOUCH_ACTION} {name} Out")

    def layer_xml(i, name):
        return (f'  <layer id="{i}" name="{name}" width="{MAP_W}" height="{MAP_H}">\n'
                f'    <data encoding="csv">{csv(layers[name])}</data>\n  </layer>')

    nl = "\n"
    xml = f"""<?xml version="1.0"?>
<map version="1.4" tiledversion="1.4.2" orientation="orthogonal" renderorder="right-down" compressionlevel="0" width="{MAP_W}" height="{MAP_H}" tilewidth="16" tileheight="16" infinite="0" nextlayerid="10" nextobjectid="{oid}">
  <properties>
    <property name="AmbientLight" type="string" value="255 255 255" />
    <property name="Light" type="string" value="{lights}" />
    <property name="ProduceArea" type="string" value="{produce}" />
    <property name="StardewZooLocation" type="string" value="T" />
    <property name="Warp" type="string" value="{warp}" />
  </properties>
{nl.join(tileset_xml)}
{nl.join(layer_xml(i + 1, n) for i, n in enumerate(LAYERS))}
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
  <objectgroup id="6" name="Back" visible="false">
{nl.join(perch_objs)}
  </objectgroup>
</map>
"""
    path = ASSETS / "StardewZoo.tmx"
    path.write_text(xml)
    return path, zsheet


def main():
    zs = ZooSheet()
    build_objects(zs)
    build_pavilion_objects(zs, FACADES, REGIONS)
    zs.blank = zs.add([Image.new("RGBA", (16, 16), (0, 0, 0, 0))])
    m = build(zs)
    resolved = m.resolve()
    path, zsheet = write_tmx(zs, m, resolved)
    save_preview(zs)
    cs = write_csharp()
    from render_map import render_tmx
    render_tmx(path, Path(__file__).resolve().parent / "previews" / "zoo_map.png", scale=1, crop=(0, 0, OUTDOOR[2] * 16, OUTDOOR[3] * 16))
    print(f"Wrote map {MAP_W}x{MAP_H} to {path}; zoo_tiles {zsheet.size} ({len(zs.images)} tiles); {cs.name}")


if __name__ == "__main__":
    main()
