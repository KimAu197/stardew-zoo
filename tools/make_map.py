"""Build the zoo interior TMX from vanilla outdoor/town/festival tiles.

Custom zoo_tiles is used only for booth/board/studio, plaques, and fences.
Does not reuse barn interiors or the barn exterior.

Usage: python3 tools/make_map.py
"""

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
    T_IRON_H,
    T_IRON_H2,
    T_IRON_POST,
    T_IRON_V,
    T_PLAQUE_DINO,
    T_PLAQUE_FOREST,
    T_PLAQUE_ICE,
    T_PLAQUE_JUNGLE,
    T_PLAQUE_SAVANNA,
    T_PLAQUE_WATER,
    T_STONE_H,
    T_STONE_H2,
    T_STONE_POST,
    T_STONE_V,
    T_STUDIO_BOT_L,
    T_STUDIO_BOT_R,
    T_STUDIO_TOP_L,
    T_STUDIO_TOP_R,
    T_WOOD_H,
    T_WOOD_H2,
    T_WOOD_POST,
    T_WOOD_V,
    T_ZOO_BANNER,
)
from vanilla import MAPS
from zoo_layout import BOARD, BOOTH, ENTRANCE, HABITATS, HAY, MAP_H, MAP_W, PLAZA, STUDIO, WARP_TILES

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "[CP] Stardew Zoo" / "assets"


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
        Sheet("festivals", "Festivals", 512, 512, 32),
        Sheet("desert", "DesertTiles", 256, 368, 16),
        Sheet("zoo_tiles", "zoo_tiles", COLS * TS, ROWS * TS, COLS),
    ]
    gid = 1
    for s in sheets:
        s.firstgid = gid
        gid += s.tilecount
    return {s.name: s for s in sheets}


def zeros():
    return [[0] * MAP_W for _ in range(MAP_H)]


def in_rect(x, y, rect):
    rx, ry, rw, rh = rect
    return rx <= x < rx + rw and ry <= y < ry + rh


def fence_rect(rect):
    x, y, w, h = rect
    return x - 1, y - 1, w + 2, h + 2


def on_border(x, y, rect):
    fx, fy, fw, fh = fence_rect(rect)
    return (fx <= x < fx + fw and fy <= y < fy + fh) and (
        x in (fx, fx + fw - 1) or y in (fy, fy + fh - 1)
    )


# Outdoor local ids
G = 150          # grass
G_FLOWER = 151
G_WEED = 152
DIRT = 153
DIRT2 = 176
PATH = 227
PATH2 = 226
PATH3 = 230
BUSH = 163
STUMP = 158
ROCK = 232
TALL = 156
WATER = 1228
WATER2 = 1229
WATER3 = 1230
WATER_EDGE = 1253
WATER_EDGE2 = 1256
LILY_EDGE = 1227
STARFISH = 1225
# trees
TREE_C0, TREE_C1, TREE_C2 = 0, 1, 2
TREE_M0, TREE_M1, TREE_M2 = 25, 26, 27
TREE_T0, TREE_T1, TREE_T2 = 50, 51, 52
TRUNK = 101
# winter
SNOW = 150
SNOW2 = 151
ICE = 153
ICE2 = 154
ICE_CHUNK = 182
SNOW_TUFT = 178
# island
JUNGLE = 352
JUNGLE2 = 353
JUNGLE3 = 354
PALM_C0, PALM_C1, PALM_C2 = 364, 365, 366
PALM_M0, PALM_M1, PALM_M2 = 396, 397, 398
FERN = 369
FERN2 = 370
LEAF = 30
LEAF2 = 31
VOLC = 443
VOLC2 = 444
VOLC3 = 445
VOLC4 = 476
# desert
SAND = 17
SAND2 = 18
SAND3 = 33
CACTUS = 8
BONE_ROCK = 22
SKULL = 3
# town
COBBLE = 858
COBBLE2 = 890
COBBLE3 = 859
COBBLE4 = 891
LAMP_HEAD = 907
LAMP_MID = 939
LAMP_POST = 971
LAMP_BASE = 1003
POT = 1015
POT2 = 1016
STONE_WALL = 944
STONE_WALL2 = 945
TOWN_BUSH = 787
TOWN_TREE_C = 816
TOWN_TREE_M = 848
TOWN_TREE_T = 912
# festivals
FEST_FLAG = 15
FEST_CHAIR_L = 8
FEST_CHAIR_R = 10


def build_layers(S):
    out, win, isl, town, fest, des, zoo = (
        S["outdoors"], S["winter"], S["island"], S["town"], S["festivals"], S["desert"], S["zoo_tiles"]
    )
    back, buildings, front, always = zeros(), zeros(), zeros(), zeros()

    def put(layer, x, y, sheet, local, overwrite=True):
        if 0 <= x < MAP_W and 0 <= y < MAP_H:
            if overwrite or layer[y][x] == 0:
                layer[y][x] = sheet.gid(local)

    # --- base grass ---
    for y in range(MAP_H):
        for x in range(MAP_W):
            v = (x * 7 + y * 13) % 11
            local = G_FLOWER if v == 0 else G_WEED if v == 1 else G
            put(back, x, y, out, local)

    # visitor dirt paths: a loop around the pens + cross aisles
    path_tiles = {PATH, PATH2, PATH3}

    def is_path(x, y):
        if y in (1, 11, 21, 28) and 1 <= x <= 36:
            return True
        if x in (1, 7, 18, 30, 36) and 1 <= y <= 28:
            return True
        if y == 29 and x in (18, 19, 17, 20):
            return True
        return False

    for y in range(MAP_H):
        for x in range(MAP_W):
            if is_path(x, y):
                local = PATH2 if (x + y) % 3 == 0 else PATH3 if (x + y) % 5 == 0 else PATH
                put(back, x, y, out, local)

    # plaza cobble
    px, py, pw, ph = PLAZA
    for y in range(py, py + ph):
        for x in range(px, px + pw):
            local = [COBBLE, COBBLE2, COBBLE3, COBBLE4][(x + y) % 4]
            put(back, x, y, town, local)

    # --- biome floors ---
    ice = HABITATS["Ice"]
    for y in range(ice[1], ice[1] + ice[3]):
        for x in range(ice[0], ice[0] + ice[2]):
            v = (x + y * 3) % 4
            put(back, x, y, win, ICE if v == 0 else SNOW2 if v == 1 else SNOW_TUFT if v == 2 else SNOW)
    put(front, ice[0] + 2, ice[1] + 1, win, ICE_CHUNK)
    put(front, ice[0] + 7, ice[1] + 2, win, ICE_CHUNK)
    put(front, ice[0] + 5, ice[1] + 4, win, ICE_CHUNK)

    water = HABITATS["Water"]
    for y in range(water[1], water[1] + water[3]):
        for x in range(water[0], water[0] + water[2]):
            edge = (
                x in (water[0], water[0] + water[2] - 1)
                or y in (water[1], water[1] + water[3] - 1)
            )
            if edge:
                put(back, x, y, out, WATER_EDGE if (x + y) % 2 == 0 else WATER_EDGE2)
            else:
                put(back, x, y, out, [WATER, WATER2, WATER3][(x + y) % 3])
    put(back, water[0] + 2, water[1] + 2, out, LILY_EDGE)
    put(back, water[0] + 6, water[1] + 3, out, LILY_EDGE)
    put(front, water[0] + 4, water[1] + 4, out, STARFISH)
    put(front, water[0] + 1, water[1] + 3, out, STARFISH)

    sav = HABITATS["Savanna"]
    for y in range(sav[1], sav[1] + sav[3]):
        for x in range(sav[0], sav[0] + sav[2]):
            v = (x * 5 + y) % 6
            if v <= 2:
                put(back, x, y, des, SAND if v == 0 else SAND2 if v == 1 else SAND3)
            else:
                put(back, x, y, out, DIRT if v == 3 else DIRT2)
    put(front, sav[0] + 1, sav[1] + 1, des, CACTUS)
    put(front, sav[0] + 7, sav[1] + 3, des, CACTUS)
    put(front, sav[0] + 4, sav[1] + 2, out, TALL)
    put(front, sav[0] + 6, sav[1] + 4, out, TALL)

    jung = HABITATS["Jungle"]
    for y in range(jung[1], jung[1] + jung[3]):
        for x in range(jung[0], jung[0] + jung[2]):
            put(back, x, y, isl, [JUNGLE, JUNGLE2, JUNGLE3][(x + y) % 3])
    put(front, jung[0] + 1, jung[1] + 1, isl, FERN)
    put(front, jung[0] + 7, jung[1] + 2, isl, FERN2)
    put(front, jung[0] + 3, jung[1] + 4, isl, LEAF)
    put(front, jung[0] + 6, jung[1] + 4, isl, LEAF2)
    # palm canopy over the back of the pen (AlwaysFront so the player walks behind)
    put(always, jung[0] + 2, jung[1] - 1, isl, PALM_C0)
    put(always, jung[0] + 3, jung[1] - 1, isl, PALM_C1)
    put(always, jung[0] + 4, jung[1] - 1, isl, PALM_C2)
    put(front, jung[0] + 2, jung[1], isl, PALM_M0)
    put(front, jung[0] + 3, jung[1], isl, PALM_M1)
    put(front, jung[0] + 4, jung[1], isl, PALM_M2)

    forest = HABITATS["Forest"]
    for y in range(forest[1], forest[1] + forest[3]):
        for x in range(forest[0], forest[0] + forest[2]):
            put(back, x, y, out, G_FLOWER if (x + y) % 3 == 0 else G)
    put(front, forest[0] + 1, forest[1] + 1, out, STUMP)
    put(front, forest[0] + 6, forest[1] + 1, out, BUSH)
    put(back, forest[0] + 4, forest[1] + 2, out, G_WEED)
    put(front, forest[0] + 7, forest[1], out, ROCK)

    pre = HABITATS["Prehistoric"]
    for y in range(pre[1], pre[1] + pre[3]):
        for x in range(pre[0], pre[0] + pre[2]):
            put(back, x, y, isl, [VOLC, VOLC2, 446, 478][(x + y) % 4])
    put(front, pre[0] + 1, pre[1], des, SKULL)
    put(back, pre[0] + 6, pre[1] + 1, des, BONE_ROCK)
    put(back, pre[0] + 3, pre[1] + 2, des, BONE_ROCK)

    # --- fences ---
    fence_set = {
        "Ice": (T_IRON_H, T_IRON_V, T_IRON_POST, T_IRON_H2),
        "Water": (T_IRON_H, T_IRON_V, T_IRON_POST, T_IRON_H2),
        "Savanna": (T_WOOD_H, T_WOOD_V, T_WOOD_POST, T_WOOD_H2),
        "Jungle": (T_WOOD_H, T_WOOD_V, T_WOOD_POST, T_WOOD_H2),
        "Forest": (T_WOOD_H, T_WOOD_V, T_WOOD_POST, T_WOOD_H2),
        "Prehistoric": (T_STONE_H, T_STONE_V, T_STONE_POST, T_STONE_H2),
    }
    plaques = {
        "Ice": T_PLAQUE_ICE,
        "Water": T_PLAQUE_WATER,
        "Savanna": T_PLAQUE_SAVANNA,
        "Jungle": T_PLAQUE_JUNGLE,
        "Forest": T_PLAQUE_FOREST,
        "Prehistoric": T_PLAQUE_DINO,
    }
    for name, rect in HABITATS.items():
        fh, fv, fp, ftop = fence_set[name]
        fx, fy, fw, fhgt = fence_rect(rect)
        for y in range(fy, fy + fhgt):
            for x in range(fx, fx + fw):
                if not (x in (fx, fx + fw - 1) or y in (fy, fy + fhgt - 1)):
                    continue
                corner = x in (fx, fx + fw - 1) and y in (fy, fy + fhgt - 1)
                vert = x in (fx, fx + fw - 1)
                if corner:
                    piece = fp
                elif vert:
                    piece = fv
                else:
                    piece = fp if x % 2 == 0 else fh
                put(buildings, x, y, zoo, piece)
                put(front, x, y, zoo, ftop, overwrite=False)
        sign_x = rect[0] + rect[2] // 2
        sign_y = fy
        put(front, sign_x, sign_y, zoo, plaques[name])

    # --- map border: bushes / trees, open south door ---
    for x in range(MAP_W):
        for y in range(MAP_H):
            edge = x in (0, MAP_W - 1) or y == 0
            door = y == MAP_H - 1 and x in (18, 19)
            south = y == MAP_H - 1 and not door
            if door:
                put(back, x, y, out, PATH)
                continue
            if edge or south:
                put(buildings, x, y, out, BUSH)

    # corner oaks the player walks behind
    def place_oak(tx, ty):
        # canopy on AlwaysFront / Front, trunk on Buildings (outside loop if possible)
        put(always, tx - 1, ty - 2, out, TREE_C0, overwrite=False)
        put(always, tx, ty - 2, out, TREE_C1, overwrite=False)
        put(always, tx + 1, ty - 2, out, TREE_C2, overwrite=False)
        put(front, tx - 1, ty - 1, out, TREE_M0, overwrite=False)
        put(front, tx, ty - 1, out, TREE_M1, overwrite=False)
        put(front, tx + 1, ty - 1, out, TREE_M2, overwrite=False)
        put(buildings, tx, ty, out, TRUNK, overwrite=False)

    # Trunks sit in grass pockets off the visitor loop and outside pen fences.
    for tx, ty in ((14, 6), (23, 6), (14, 16), (23, 16), (14, 26), (23, 26)):
        place_oak(tx, ty)

    # flowers / rocks along the path (Back, walkable)
    for x, y in ((5, 1), (12, 1), (24, 1), (32, 1), (8, 11), (22, 11), (14, 21), (25, 21), (10, 28), (28, 28)):
        put(back, x, y, out, G_FLOWER)
    for x, y in ((3, 21), (34, 21), (15, 28)):
        put(front, x, y, out, ROCK)

    # lamp posts at plaza corners and path junctions (town lamps)
    def lamp(x, y):
        put(buildings, x, y, town, LAMP_BASE)
        put(front, x, y - 1, town, LAMP_POST, overwrite=False)
        put(always, x, y - 2, town, LAMP_HEAD, overwrite=False)

    lamp(px, py)
    lamp(px + pw - 1, py)
    lamp(2, 10)
    lamp(35, 10)
    lamp(2, 20)
    lamp(35, 20)

    # festival chairs as benches beside the plaza
    put(buildings, px - 1, py + 2, fest, FEST_CHAIR_L)
    put(buildings, px + pw, py + 2, fest, FEST_CHAIR_R)
    put(front, px + 2, py - 1, fest, FEST_FLAG)
    put(front, px + 3, py - 1, fest, FEST_FLAG)

    # flower pots
    put(front, px + pw - 2, py + ph - 1, town, POT)
    put(front, px + 1, py + ph - 1, town, POT2)

    # --- plaza props: booth, board, studio ---
    # Booth 3-wide at x=16-18, awning Front y=13, counter Buildings y=14. Action at (17,14).
    put(front, 16, 13, zoo, T_BOOTH_AWN_L)
    put(front, 17, 13, zoo, T_BOOTH_AWN_M)
    put(front, 18, 13, zoo, T_BOOTH_AWN_R)
    put(buildings, 16, 14, zoo, T_BOOTH_CTR_L)
    put(buildings, 17, 14, zoo, T_BOOTH_CTR_M)
    put(buildings, 18, 14, zoo, T_BOOTH_CTR_R)
    put(front, 16, 14, fest, 75)
    put(front, 18, 14, fest, 78)
    # Review board at (19,14), 2-wide
    put(front, 19, 13, zoo, T_BOARD_TOP_L)
    put(front, 20, 13, zoo, T_BOARD_TOP_R)
    put(buildings, 19, 14, zoo, T_BOARD_BOT_L)
    put(buildings, 20, 14, zoo, T_BOARD_BOT_R)
    # Recording studio at (18,16), 2-wide
    put(front, 18, 15, zoo, T_STUDIO_TOP_L)
    put(front, 19, 15, zoo, T_STUDIO_TOP_R)
    put(buildings, 18, 16, zoo, T_STUDIO_BOT_L)
    put(buildings, 19, 16, zoo, T_STUDIO_BOT_R)

    # ZOO banner over the entrance
    put(front, 18, 27, zoo, T_ZOO_BANNER)
    put(front, 19, 27, zoo, T_ZOO_BANNER)

    # hay hopper is an IndoorItem; keep cobble (or grass) on Back, no Buildings tile

    return back, buildings, front, always


def csv(layer):
    lines = []
    for y, row in enumerate(layer):
        line = ",".join(str(v) for v in row)
        if y != len(layer) - 1:
            line += ","
        lines.append(line)
    return "\n" + "\n".join(lines) + "\n"


def water_animations(sheet):
    """Shimmer water without the Water=T flag so animals can walk the pond."""
    chunks = []
    frames = [1228, 1229, 1230, 1231]
    for tid in frames:
        body = "\n".join(
            f'        <frame tileid="{f}" duration="400" />' for f in frames
        )
        chunks.append(
            f'    <tile id="{tid}">\n      <animation>\n{body}\n      </animation>\n    </tile>'
        )
    return "\n".join(chunks)


def write_tmx(sheets, back, buildings, front, always):
    warp = " ".join(f"{x} {y} Farm 0 0" for x, y in WARP_TILES)
    zoo = sheets["zoo_tiles"]
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
            extra = "\n" + water_animations(s)
        if s.name == "zoo_tiles":
            extra = "\n" + "\n".join(action_xml)
        tileset_xml.append(
            f'  <tileset firstgid="{s.firstgid}" name="{s.name}" tilewidth="16" tileheight="16" '
            f'tilecount="{s.tilecount}" columns="{s.columns}">\n'
            f'    <image source="{s.source}" width="{s.width}" height="{s.height}" />{extra}\n'
            f"  </tileset>"
        )

    lights = [
        f"{PLAZA[0]} {PLAZA[1]} 4",
        f"{PLAZA[0] + PLAZA[2] - 1} {PLAZA[1]} 4",
        "2 10 4", "35 10 4", "2 20 4", "35 20 4",
        "18 28 4",
    ]
    xml = f"""<?xml version="1.0"?>
<map version="1.4" tiledversion="1.4.2" orientation="orthogonal" renderorder="right-down" compressionlevel="0" width="{MAP_W}" height="{MAP_H}" tilewidth="16" tileheight="16" infinite="0" nextlayerid="10" nextobjectid="8">
  <properties>
    <property name="AmbientLight" type="string" value="255 255 255" />
    <property name="Light" type="string" value="{" ".join(lights)}" />
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
    layers = build_layers(sheets)
    path = write_tmx(sheets, *layers)
    from render_map import render_tmx
    preview_dir = Path(__file__).resolve().parent / "previews"
    render_tmx(path, Path("/tmp/zoo_art") / "interior.png", scale=2)
    render_tmx(path, preview_dir / "zoo_map.png", scale=2)
    render_tmx(
        path,
        Path("/tmp/zoo_art") / "booths.png",
        scale=4,
        crop=(15 * 16, 12 * 16, 22 * 16, 18 * 16),
    )
    print(f"Wrote map {MAP_W}x{MAP_H} to {path}")
    print(f"Habitats: {HABITATS}")
    print(f"Booth {BOOTH} board {BOARD} studio {STUDIO} hay {HAY} entrance {ENTRANCE}")
    print("Tilesets:", ", ".join(f"{s.name} gid={s.firstgid} src={s.source}" for s in sheets.values()))


if __name__ == "__main__":
    main()
