"""Generate the custom zoo interior tilesheet (no vanilla barn/farm tiles)."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "[CP] Stardew Zoo" / "assets" / "zoo_tiles.png"
PREVIEW = Path(__file__).resolve().parent / "previews" / "zoo_tiles.png"
COLS = 16
ROWS = 8
TS = 16


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


# Keep these in sync with tools/make_map.py
T_EMPTY = 0
T_WALL = 1
T_WALL_TOP = 2
T_PATH = 3
T_PLAZA = 4
T_ICE = 5
T_ICE2 = 6
T_WATER = 7
T_WATER2 = 8
T_SAND = 9
T_SAVANNA = 10
T_JUNGLE = 11
T_JUNGLE2 = 12
T_FOREST = 13
T_FOREST2 = 14
T_PREHIST = 15
T_PREHIST2 = 16
T_FENCE_H = 17
T_FENCE_V = 18
T_FENCE_POST = 19
T_FENCE_ICE = 20
T_FENCE_WATER = 21
T_BOOTH = 22
T_BOARD = 23
T_STUDIO = 24
T_HAY = 25
T_MAT = 26
T_SIGN_ICE = 27
T_SIGN_WATER = 28
T_SIGN_SAVANNA = 29
T_SIGN_JUNGLE = 30
T_SIGN_FOREST = 31
T_SIGN_DINO = 32
T_SNOW = 33
T_LILY = 34
T_TUFT = 35
T_BAMBOO = 36
T_MUSHROOM = 37
T_BONE = 38
T_WALL_DARK = 39
T_COLUMN = 40
T_FENCE_WOOD = 41
T_PLAZA2 = 42
T_PATH2 = 43


def tile(img, index, painter):
    x, y = (index % COLS) * TS, (index // COLS) * TS
    cell = Image.new("RGBA", (TS, TS), (0, 0, 0, 0))
    painter(ImageDraw.Draw(cell), cell)
    img.paste(cell, (x, y), cell)


def fill(draw, color):
    draw.rectangle((0, 0, 15, 15), fill=color)


def speckle(draw, color, step=3, ox=0):
    for y in range(0, 16, step):
        for x in range((y + ox) % step, 16, step):
            draw.point((x, y), fill=color)


def main():
    img = Image.new("RGBA", (COLS * TS, ROWS * TS), (0, 0, 0, 0))

    def wall(d, _):
        fill(d, rgb("#6b4f2a"))
        d.rectangle((0, 0, 15, 2), fill=rgb("#3d2914"))
        speckle(d, rgb("#8a6a3d"), 4)

    def wall_top(d, _):
        fill(d, rgb("#8b5a2b"))
        d.rectangle((0, 10, 15, 15), fill=rgb("#6b4f2a"))

    def wall_dark(d, _):
        fill(d, rgb("#3d2914"))

    def path(d, _):
        fill(d, rgb("#c4b59a"))
        speckle(d, rgb("#a89070"), 4)

    def path2(d, _):
        fill(d, rgb("#b9a888"))
        speckle(d, rgb("#c4b59a"), 3, 1)

    def plaza(d, _):
        fill(d, rgb("#d7c4a3"))
        d.rectangle((0, 0, 15, 15), outline=rgb("#b08968"))
        speckle(d, rgb("#e6d5b8"), 5)

    def plaza2(d, _):
        fill(d, rgb("#cbb892"))
        d.rectangle((0, 0, 15, 15), outline=rgb("#b08968"))

    def ice(d, _):
        fill(d, rgb("#d8eef8"))
        speckle(d, rgb("#ffffff"), 3)
        speckle(d, rgb("#9fd4ea"), 5, 1)

    def ice2(d, _):
        fill(d, rgb("#c5e4f5"))
        speckle(d, rgb("#ffffff"), 4)

    def water(d, _):
        fill(d, rgb("#3a86c8"))
        speckle(d, rgb("#5dade2"), 3)
        d.line((1, 6, 6, 4), fill=rgb("#a9def9"))

    def water2(d, _):
        fill(d, rgb("#2d6a9f"))
        speckle(d, rgb("#3a86c8"), 3, 1)

    def sand(d, _):
        fill(d, rgb("#e6c07b"))
        speckle(d, rgb("#d4a373"), 3)

    def savanna(d, _):
        fill(d, rgb("#c3d46a"))
        speckle(d, rgb("#8aaa3a"), 3)
        d.line((4, 12, 4, 8), fill=rgb("#6b8f2a"))

    def jungle(d, _):
        fill(d, rgb("#3f6b2a"))
        speckle(d, rgb("#2d4a1c"), 3)
        speckle(d, rgb("#6aa83a"), 4, 1)

    def jungle2(d, _):
        fill(d, rgb("#2d4a1c"))
        speckle(d, rgb("#3f6b2a"), 3)

    def forest(d, _):
        fill(d, rgb("#5c4033"))
        speckle(d, rgb("#3d2914"), 3)
        speckle(d, rgb("#6b8f2a"), 5, 1)

    def forest2(d, _):
        fill(d, rgb("#4a7c3a"))
        speckle(d, rgb("#2d4a1c"), 4)

    def pre(d, _):
        fill(d, rgb("#8a7a68"))
        speckle(d, rgb("#6b5b4a"), 3)

    def pre2(d, _):
        fill(d, rgb("#6b5b4a"))
        speckle(d, rgb("#c9b896"), 4, 2)

    def fence_h(d, _):
        d.rectangle((0, 6, 15, 10), fill=rgb("#8b5a2b"))
        d.rectangle((0, 5, 15, 6), fill=rgb("#c4a574"))

    def fence_v(d, _):
        d.rectangle((6, 0, 10, 15), fill=rgb("#8b5a2b"))
        d.rectangle((5, 0, 6, 15), fill=rgb("#c4a574"))

    def fence_post(d, _):
        d.rectangle((5, 2, 11, 15), fill=rgb("#6b4226"))
        d.rectangle((4, 0, 12, 4), fill=rgb("#8b5a2b"))

    def fence_ice(d, _):
        d.rectangle((0, 5, 15, 11), fill=rgb("#a9def9"))
        d.rectangle((0, 5, 15, 11), outline=rgb("#5dade2"))

    def fence_water(d, _):
        d.rectangle((6, 0, 10, 15), fill=rgb("#1d3557"))
        d.rectangle((5, 4, 11, 8), fill=rgb("#5dade2"))

    def fence_wood(d, _):
        d.rectangle((0, 4, 15, 7), fill=rgb("#6b4226"))
        d.rectangle((0, 9, 15, 12), fill=rgb("#8b5a2b"))
        d.rectangle((6, 0, 10, 15), fill=rgb("#4a2e16"))

    def booth(d, _):
        fill(d, rgb("#c0392b"))
        d.rectangle((1, 4, 14, 14), fill=rgb("#f4d35e"))
        d.rectangle((2, 6, 13, 12), fill=rgb("#1d3557"))
        d.point((5, 8), fill=rgb("#ffffff"))
        d.point((8, 8), fill=rgb("#ffffff"))
        d.point((11, 8), fill=rgb("#ffffff"))

    def board(d, _):
        fill(d, rgb("#6b4226"))
        d.rectangle((2, 1, 13, 13), fill=rgb("#f4e3c1"))
        d.line((4, 4, 11, 4), fill=rgb("#4a2e16"))
        d.line((4, 7, 11, 7), fill=rgb("#4a2e16"))
        d.line((4, 10, 9, 10), fill=rgb("#4a2e16"))

    def studio(d, _):
        fill(d, rgb("#2b2d42"))
        d.ellipse((3, 3, 12, 12), fill=rgb("#8d99ae"))
        d.ellipse((5, 5, 10, 10), fill=rgb("#ef233c"))
        d.rectangle((7, 12, 9, 15), fill=rgb("#8d99ae"))

    def hay(d, _):
        fill(d, rgb("#6b4226"))
        d.rectangle((2, 4, 13, 14), fill=rgb("#e9c46a"))
        speckle(d, rgb("#f4d35e"), 2)

    def mat(d, _):
        fill(d, rgb("#6b4226"))
        speckle(d, rgb("#8b5a2b"), 2)

    def sign(label, bg):
        def painter(d, _):
            fill(d, bg)
            d.rectangle((0, 0, 15, 15), outline=rgb("#2b2d42"))
            d.rectangle((1, 1, 14, 5), fill=rgb("#f4d35e"))
        return painter

    def snow(d, cell):
        d.ellipse((2, 6, 14, 15), fill=rgb("#f8fbff"))
        d.ellipse((4, 8, 10, 14), fill=rgb("#d8eef8"))

    def lily(d, _):
        d.ellipse((2, 4, 14, 14), fill=rgb("#6aa83a"))
        d.ellipse((6, 6, 11, 11), fill=rgb("#e9c46a"))

    def tuft(d, _):
        d.line((4, 14, 4, 6), fill=rgb("#6b8f2a"))
        d.line((8, 14, 8, 4), fill=rgb("#8aaa3a"))
        d.line((12, 14, 12, 7), fill=rgb("#6b8f2a"))

    def bamboo(d, _):
        d.rectangle((4, 0, 7, 15), fill=rgb("#6aa83a"))
        d.rectangle((9, 2, 12, 15), fill=rgb("#3f6b2a"))
        d.line((4, 5, 7, 5), fill=rgb("#d8f3dc"))
        d.line((9, 8, 12, 8), fill=rgb("#d8f3dc"))

    def mushroom(d, _):
        d.rectangle((7, 8, 9, 15), fill=rgb("#efece4"))
        d.ellipse((3, 3, 13, 11), fill=rgb("#e63946"))
        d.point((6, 6), fill=rgb("#ffffff"))
        d.point((10, 7), fill=rgb("#ffffff"))

    def bone(d, _):
        d.rectangle((4, 7, 12, 9), fill=rgb("#efece4"))
        d.ellipse((2, 5, 7, 11), fill=rgb("#efece4"))
        d.ellipse((10, 5, 15, 11), fill=rgb("#efece4"))

    def column(d, _):
        d.rectangle((5, 0, 11, 15), fill=rgb("#efece4"))
        d.rectangle((4, 0, 12, 3), fill=rgb("#c9a227"))
        d.rectangle((4, 13, 12, 15), fill=rgb("#c9a227"))

    painters = {
        T_WALL: wall, T_WALL_TOP: wall_top, T_WALL_DARK: wall_dark,
        T_PATH: path, T_PATH2: path2, T_PLAZA: plaza, T_PLAZA2: plaza2,
        T_ICE: ice, T_ICE2: ice2, T_WATER: water, T_WATER2: water2,
        T_SAND: sand, T_SAVANNA: savanna, T_JUNGLE: jungle, T_JUNGLE2: jungle2,
        T_FOREST: forest, T_FOREST2: forest2, T_PREHIST: pre, T_PREHIST2: pre2,
        T_FENCE_H: fence_h, T_FENCE_V: fence_v, T_FENCE_POST: fence_post,
        T_FENCE_ICE: fence_ice, T_FENCE_WATER: fence_water, T_FENCE_WOOD: fence_wood,
        T_BOOTH: booth, T_BOARD: board, T_STUDIO: studio, T_HAY: hay, T_MAT: mat,
        T_SIGN_ICE: sign("ICE", rgb("#d8eef8")),
        T_SIGN_WATER: sign("WTR", rgb("#3a86c8")),
        T_SIGN_SAVANNA: sign("SAV", rgb("#c3d46a")),
        T_SIGN_JUNGLE: sign("JUN", rgb("#3f6b2a")),
        T_SIGN_FOREST: sign("FOR", rgb("#5c4033")),
        T_SIGN_DINO: sign("PRE", rgb("#8a7a68")),
        T_SNOW: snow, T_LILY: lily, T_TUFT: tuft, T_BAMBOO: bamboo,
        T_MUSHROOM: mushroom, T_BONE: bone, T_COLUMN: column,
    }
    for index, painter in painters.items():
        tile(img, index, painter)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    img.resize((img.width * 4, img.height * 4), Image.NEAREST).save(PREVIEW)
    print(f"Wrote tilesheet {img.size} to {OUT}")


if __name__ == "__main__":
    main()
