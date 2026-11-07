"""Build the custom zoo interior TMX and a rendered preview."""

from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image

from draw_tiles import (
    COLS, TS, T_BAMBOO, T_BOARD, T_BONE, T_BOOTH, T_COLUMN, T_FENCE_H, T_FENCE_ICE,
    T_FENCE_POST, T_FENCE_V, T_FENCE_WATER, T_FENCE_WOOD, T_FOREST, T_FOREST2, T_HAY,
    T_ICE, T_ICE2, T_JUNGLE, T_JUNGLE2, T_LILY, T_MAT, T_MUSHROOM, T_PATH, T_PATH2,
    T_PLAZA, T_PLAZA2, T_PREHIST, T_PREHIST2, T_SAND, T_SAVANNA, T_SIGN_DINO,
    T_SIGN_FOREST, T_SIGN_ICE, T_SIGN_JUNGLE, T_SIGN_SAVANNA, T_SIGN_WATER, T_SNOW,
    T_STUDIO, T_TUFT, T_WALL, T_WALL_DARK, T_WALL_TOP, T_WATER, T_WATER2,
)
from zoo_layout import BOARD, BOOTH, ENTRANCE, HABITATS, HAY, MAP_H, MAP_W, PLAZA, STUDIO, WARP_TILES

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "[CP] Stardew Zoo" / "assets"
PREVIEW = Path(__file__).resolve().parent / "previews" / "zoo_map.png"

FLOORS = {
    "Ice": (T_ICE, T_ICE2, T_SNOW),
    "Water": (T_WATER, T_WATER2, T_LILY),
    "Savanna": (T_SAND, T_SAVANNA, T_TUFT),
    "Jungle": (T_JUNGLE, T_JUNGLE2, T_BAMBOO),
    "Forest": (T_FOREST, T_FOREST2, T_MUSHROOM),
    "Prehistoric": (T_PREHIST, T_PREHIST2, T_BONE),
}
FENCES = {
    "Ice": T_FENCE_ICE,
    "Water": T_FENCE_WATER,
    "Savanna": T_FENCE_WOOD,
    "Jungle": T_FENCE_WOOD,
    "Forest": T_FENCE_WOOD,
    "Prehistoric": T_FENCE_H,
}
SIGNS = {
    "Ice": T_SIGN_ICE,
    "Water": T_SIGN_WATER,
    "Savanna": T_SIGN_SAVANNA,
    "Jungle": T_SIGN_JUNGLE,
    "Forest": T_SIGN_FOREST,
    "Prehistoric": T_SIGN_DINO,
}

ACTION_TILES = {
    T_BOOTH: "StardewZoo_TicketBooth",
    T_BOARD: "StardewZoo_ReviewBoard",
    T_STUDIO: "StardewZoo_RecordingStudio",
}


def zeros():
    return [[0] * MAP_W for _ in range(MAP_H)]


def in_rect(x, y, rect):
    rx, ry, rw, rh = rect
    return rx <= x < rx + rw and ry <= y < ry + rh


def fence_rect(rect):
    x, y, w, h = rect
    return x - 1, y - 1, w + 2, h + 2


def build_layers():
    back, buildings, front = zeros(), zeros(), zeros()

    for y in range(MAP_H):
        for x in range(MAP_W):
            edge = x in (0, MAP_W - 1) or y in (0, MAP_H - 1)
            door = y == MAP_H - 1 and x in (18, 19)
            if edge and not door:
                buildings[y][x] = T_WALL
                if y == 0:
                    front[y][x] = T_WALL_TOP
                back[y][x] = T_WALL_DARK
            elif door:
                back[y][x] = T_MAT
            else:
                back[y][x] = T_PATH if (x + y) % 5 else T_PATH2

    px, py, pw, ph = PLAZA
    for y in range(py, py + ph):
        for x in range(px, px + pw):
            back[y][x] = T_PLAZA if (x + y) % 2 == 0 else T_PLAZA2

    for name, rect in HABITATS.items():
        floor_a, floor_b, prop = FLOORS[name]
        x0, y0, w, h = rect
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                back[y][x] = floor_a if (x + y) % 2 == 0 else floor_b
        # scatter a couple of props on Back so they don't block walking
        back[y0 + 1][x0 + 1] = prop
        back[y0 + h - 2][x0 + w - 2] = prop
        fx, fy, fw, fh = fence_rect(rect)
        fence = FENCES[name]
        for y in range(fy, fy + fh):
            for x in range(fx, fx + fw):
                on_border = x in (fx, fx + fw - 1) or y in (fy, fy + fh - 1)
                if on_border:
                    buildings[y][x] = T_FENCE_POST if x in (fx, fx + fw - 1) and y in (fy, fy + fh - 1) else (
                        T_FENCE_V if x in (fx, fx + fw - 1) else fence
                    )
        sign_x = x0 + w // 2
        sign_y = fy
        front[sign_y][sign_x] = SIGNS[name]

    buildings[BOOTH[1]][BOOTH[0]] = T_BOOTH
    buildings[BOARD[1]][BOARD[0]] = T_BOARD
    buildings[STUDIO[1]][STUDIO[0]] = T_STUDIO
    buildings[HAY[1]][HAY[0]] = T_HAY
    buildings[py][px] = T_COLUMN
    buildings[py][px + pw - 1] = T_COLUMN

    return back, buildings, front


def csv(layer):
    lines = []
    for y, row in enumerate(layer):
        line = ",".join(str(v) for v in row)
        if y != len(layer) - 1:
            line += ","
        lines.append(line)
    return "\n" + "\n".join(lines) + "\n"


def write_tmx(back, buildings, front):
    warp = " ".join(f"{x} {y} Farm 0 0" for x, y in WARP_TILES)
    tileset_tiles = []
    for tid, action in ACTION_TILES.items():
        tileset_tiles.append(
            f'    <tile id="{tid}">\n      <properties>\n'
            f'        <property name="Action" type="string" value="{action}" />\n'
            f"      </properties>\n    </tile>"
        )
    # Buildings-layer tiles are impassable; fences/walls already live there.
    xml = f"""<?xml version="1.0"?>
<map version="1.4" tiledversion="1.4.2" orientation="orthogonal" renderorder="right-down" compressionlevel="0" width="{MAP_W}" height="{MAP_H}" tilewidth="16" tileheight="16" infinite="0" nextlayerid="8" nextobjectid="6">
  <properties>
    <property name="AmbientLight" type="string" value="120 120 110" />
    <property name="AmbientNightLight" type="string" value="140 130 100" />
    <property name="Warp" type="string" value="{warp}" />
  </properties>
  <tileset firstgid="1" name="zoo_tiles" tilewidth="16" tileheight="16" tilecount="{COLS * 8}" columns="{COLS}">
    <image source="zoo_tiles.png" width="{COLS * TS}" height="{8 * TS}" />
{chr(10).join(tileset_tiles)}
  </tileset>
  <layer id="1" name="Back" width="{MAP_W}" height="{MAP_H}">
    <data encoding="csv">{csv([[v + 1 if v else 0 for v in row] for row in back])}</data>
  </layer>
  <layer id="2" name="Buildings" width="{MAP_W}" height="{MAP_H}">
    <data encoding="csv">{csv([[v + 1 if v else 0 for v in row] for row in buildings])}</data>
  </layer>
  <layer id="3" name="Front" width="{MAP_W}" height="{MAP_H}">
    <data encoding="csv">{csv([[v + 1 if v else 0 for v in row] for row in front])}</data>
  </layer>
  <objectgroup id="4" name="Buildings" visible="false">
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


def render_preview(back, buildings, front):
    tiles = Image.open(ASSETS / "zoo_tiles.png")
    img = Image.new("RGBA", (MAP_W * TS, MAP_H * TS), (20, 20, 20, 255))

    def blit(layer):
        for y, row in enumerate(layer):
            for x, tid in enumerate(row):
                if not tid:
                    continue
                sx, sy = (tid % COLS) * TS, (tid // COLS) * TS
                img.alpha_composite(tiles.crop((sx, sy, sx + TS, sy + TS)), (x * TS, y * TS))

    blit(back)
    blit(buildings)
    blit(front)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    img.resize((img.width * 2, img.height * 2), Image.NEAREST).save(PREVIEW)
    img.save(ASSETS / "zoo_map_preview.png")


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    back, buildings, front = build_layers()
    path = write_tmx(back, buildings, front)
    render_preview(back, buildings, front)
    print(f"Wrote map {MAP_W}x{MAP_H} to {path}")
    print(f"Habitats: {HABITATS}")
    print(f"Booth {BOOTH} board {BOARD} studio {STUDIO} hay {HAY} entrance {ENTRANCE}")


if __name__ == "__main__":
    main()
