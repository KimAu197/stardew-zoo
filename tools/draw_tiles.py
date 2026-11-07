"""Custom zoo_tiles: only things vanilla sheets don't have.

Booth / board / studio are assembled from festival-stall and wooden-sign
pixels so they match ConcernedApe's fair booths and Pierre's bulletin board.
Fence pieces are cropped from vanilla LooseSprites fence sheets.
Habitat plaques are wooden name boards in the same sign language.

Usage: python3 tools/draw_tiles.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

from vanilla import LOOSE, MAPS, SHEETS, UNPACKED

OUT = Path(__file__).resolve().parent.parent / "[CP] Stardew Zoo" / "assets" / "zoo_tiles.png"
PREVIEW = Path(__file__).resolve().parent / "previews" / "zoo_tiles.png"
COLS = 16
ROWS = 16
TS = 16

# --- tile indices (keep in sync with make_map.py) ---
T_BOOTH_AWN_L, T_BOOTH_AWN_M, T_BOOTH_AWN_R = 0, 1, 2
T_BOARD_TOP_L, T_BOARD_TOP_R = 3, 4
T_STUDIO_TOP_L, T_STUDIO_TOP_R = 5, 6
T_PLAQUE_ICE, T_PLAQUE_WATER, T_PLAQUE_SAVANNA = 7, 8, 9
T_PLAQUE_JUNGLE, T_PLAQUE_FOREST, T_PLAQUE_DINO = 10, 11, 12
T_ZOO_BANNER = 13
T_STAR = 14
T_COIN = 15

T_BOOTH_CTR_L, T_BOOTH_CTR_M, T_BOOTH_CTR_R = 16, 17, 18
T_BOARD_BOT_L, T_BOARD_BOT_R = 19, 20
T_STUDIO_BOT_L, T_STUDIO_BOT_R = 21, 22

T_WOOD_H, T_WOOD_V, T_WOOD_POST = 32, 33, 34
T_IRON_H, T_IRON_V, T_IRON_POST = 35, 36, 37
T_STONE_H, T_STONE_V, T_STONE_POST = 38, 39, 40
T_WOOD_H2, T_IRON_H2, T_STONE_H2 = 41, 42, 43  # top half of 32px fence (Front)

T_HAY_CRATE = 48
T_MIC = 49

ACTION_TILES = {
    T_BOOTH_CTR_M: "StardewZoo_TicketBooth",
    T_BOARD_BOT_L: "StardewZoo_ReviewBoard",
    T_STUDIO_BOT_L: "StardewZoo_RecordingStudio",
}

INK = (52, 11, 14, 255)


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def paste_tile(sheet, index, src):
    x, y = (index % COLS) * TS, (index // COLS) * TS
    if src.mode != "RGBA":
        src = src.convert("RGBA")
    if src.size != (TS, TS):
        src = src.crop((0, 0, TS, TS))
    sheet.paste(src, (x, y), src)


def copy(src, box):
    return src.crop(box).convert("RGBA")


def overpaint_shop_sign(tile: Image.Image) -> Image.Image:
    """Replace the festival SHOP plaque with a ticket + coin sign."""
    px = tile.load()
    w, h = tile.size
    # Cover the original green SHOP band with a wood plaque.
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 10:
                continue
            # green-ish sign pixels
            if g > r + 20 and g > b and g > 80:
                px[x, y] = rgb("#6b3a1f")
    d = ImageDraw.Draw(tile)
    # small ticket rectangle
    d.rectangle((1, 4, 10, 12), fill=rgb("#f4e3c1"), outline=INK)
    d.line((1, 8, 10, 8), fill=rgb("#c9a227"))
    d.point((3, 6), fill=INK)
    d.point((5, 6), fill=INK)
    d.point((7, 6), fill=INK)
    # coin
    d.ellipse((10, 5, 15, 12), fill=rgb("#e9c46a"), outline=INK)
    d.point((12, 8), fill=rgb("#c9a227"))
    return tile


def draw_board_pair():
    """Cork bulletin board with wooden frame, pinned notes, and stars."""
    top = Image.new("RGBA", (32, 16), (0, 0, 0, 0))
    bot = Image.new("RGBA", (32, 16), (0, 0, 0, 0))
    dtop, dbot = ImageDraw.Draw(top), ImageDraw.Draw(bot)
    wood, wood_hi, wood_dk = rgb("#c17a32"), rgb("#e0a35a"), rgb("#6b3a1f")
    cork, cork2 = rgb("#d2b48c"), rgb("#c4a574")
    # frame
    dtop.rectangle((0, 0, 31, 15), fill=wood)
    dbot.rectangle((0, 0, 31, 15), fill=wood)
    dtop.rectangle((2, 2, 29, 15), fill=cork)
    dbot.rectangle((2, 0, 29, 13), fill=cork)
    # cork texture
    for y in range(2, 16):
        for x in range(2, 30):
            if (x * 3 + y * 5) % 7 == 0:
                top.putpixel((x, y), cork2)
    for y in range(0, 14):
        for x in range(2, 30):
            if (x * 3 + y * 5) % 7 == 0:
                bot.putpixel((x, y), cork2)
    # notes
    dtop.rectangle((4, 4, 12, 14), fill=rgb("#fff8dc"), outline=INK)
    dtop.rectangle((15, 6, 24, 15), fill=rgb("#f4d35e"), outline=INK)
    dbot.rectangle((6, 1, 14, 10), fill=rgb("#e8f4e0"), outline=INK)
    dbot.rectangle((17, 3, 27, 12), fill=rgb("#fff8dc"), outline=INK)
    # scribbles
    dtop.line((5, 7, 11, 7), fill=wood_dk)
    dtop.line((5, 9, 10, 9), fill=wood_dk)
    dbot.line((7, 4, 13, 4), fill=wood_dk)
    dbot.line((7, 6, 12, 6), fill=wood_dk)
    dbot.line((18, 6, 25, 6), fill=wood_dk)
    # stars
    for cx, cy, img in ((26, 4, top), (4, 12, bot), (28, 2, bot)):
        d = ImageDraw.Draw(img)
        d.point((cx, cy), fill=rgb("#e9c46a"))
        d.point((cx - 1, cy), fill=rgb("#e9c46a"))
        d.point((cx + 1, cy), fill=rgb("#e9c46a"))
        d.point((cx, cy - 1), fill=rgb("#e9c46a"))
        d.point((cx, cy + 1), fill=rgb("#c9a227"))
    # pins
    dtop.point((8, 4), fill=rgb("#c23b22"))
    dtop.point((19, 6), fill=rgb("#1d3557"))
    dbot.point((10, 1), fill=rgb("#2d6a4f"))
    dbot.point((22, 3), fill=rgb("#c23b22"))
    # outer ink
    dtop.rectangle((0, 0, 31, 15), outline=INK)
    dbot.rectangle((0, 0, 31, 13), outline=INK)
    dbot.rectangle((0, 14, 31, 15), fill=wood_dk)
    return top.crop((0, 0, 16, 16)), top.crop((16, 0, 32, 16)), bot.crop((0, 0, 16, 16)), bot.crop((16, 0, 32, 16))


def draw_studio_pair():
    """Small wooden recording booth with a mic and speaker grille."""
    top = Image.new("RGBA", (32, 16), (0, 0, 0, 0))
    bot = Image.new("RGBA", (32, 16), (0, 0, 0, 0))
    wood, hi, dk = rgb("#c17a32"), rgb("#e0a35a"), rgb("#6b3a1f")
    for img, y0, y1, floor in ((top, 2, 15, False), (bot, 0, 15, True)):
        d = ImageDraw.Draw(img)
        d.rectangle((1, y0, 30, y1), fill=wood)
        # vertical planks
        for x in range(2, 30, 4):
            d.line((x, y0, x, y1), fill=dk)
            d.line((x + 1, y0, x + 1, y1), fill=hi)
        d.rectangle((1, y0, 30, y1), outline=INK)
    dtop, dbot = ImageDraw.Draw(top), ImageDraw.Draw(bot)
    # roof slats
    dtop.rectangle((0, 0, 31, 4), fill=rgb("#8a4e18"), outline=INK)
    dtop.line((0, 2, 31, 2), fill=hi)
    # window
    dtop.rectangle((8, 7, 23, 15), fill=rgb("#7ec8e3"), outline=INK)
    dtop.line((15, 7, 15, 15), fill=INK)
    dtop.point((10, 9), fill=rgb("#d8f0f8"))
    # counter + mic + speaker
    dbot.rectangle((2, 1, 29, 8), fill=dk)
    dbot.rectangle((2, 1, 29, 8), outline=INK)
    # mic
    dbot.ellipse((8, 2, 14, 8), fill=rgb("#c0c4c8"), outline=INK)
    dbot.rectangle((10, 8, 12, 12), fill=rgb("#6b3a1f"))
    dbot.line((11, 8, 11, 12), fill=rgb("#8a8a8a"))
    # speaker grille
    dbot.rectangle((18, 3, 27, 10), fill=rgb("#3b2314"), outline=INK)
    for y in range(4, 10, 2):
        dbot.line((19, y, 26, y), fill=rgb("#8a8a8a"))
    dbot.rectangle((1, 13, 30, 15), fill=rgb("#4a2e16"))
    return top.crop((0, 0, 16, 16)), top.crop((16, 0, 32, 16)), bot.crop((0, 0, 16, 16)), bot.crop((16, 0, 32, 16))


def draw_plaque(icon_color, motif):
    """16x16 hanging wooden habitat sign."""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((1, 2, 14, 15), fill=rgb("#c17a32"))
    d.rectangle((1, 2, 14, 15), outline=INK)
    d.line((2, 3, 13, 3), fill=rgb("#e0a35a"))
    d.rectangle((3, 5, 12, 8), fill=icon_color)
    d.rectangle((3, 5, 12, 8), outline=INK)
    # hanging
    d.line((4, 0, 4, 2), fill=INK)
    d.line((11, 0, 11, 2), fill=INK)
    if motif == "ice":
        d.polygon([(8, 9), (5, 14), (11, 14)], fill=rgb("#d8eef8"), outline=INK)
    elif motif == "water":
        d.arc((4, 10, 12, 15), 0, 180, fill=rgb("#3a86c8"))
        d.arc((4, 8, 12, 13), 0, 180, fill=rgb("#7ec8e3"))
    elif motif == "savanna":
        d.ellipse((5, 9, 11, 15), fill=rgb("#f4d35e"), outline=INK)
        d.point((8, 12), fill=rgb("#c23b22"))
    elif motif == "jungle":
        d.polygon([(8, 9), (4, 14), (12, 14)], fill=rgb("#2d6a4f"), outline=INK)
        d.polygon([(8, 9), (6, 12), (10, 12)], fill=rgb("#6aa83a"))
    elif motif == "forest":
        d.rectangle((7, 12, 9, 15), fill=rgb("#6b3a1f"))
        d.ellipse((4, 8, 12, 14), fill=rgb("#2d6a4f"), outline=INK)
    else:
        d.ellipse((4, 10, 8, 15), fill=rgb("#efece4"), outline=INK)
        d.ellipse((8, 10, 12, 15), fill=rgb("#efece4"), outline=INK)
        d.rectangle((6, 12, 10, 13), fill=rgb("#efece4"))
    return img


def _split32(src: Image.Image, col: int, row: int):
    """Vanilla fence sprites are 16x32. Lower 16 → Buildings, upper 16 → Front."""
    x, y = col * 16, row * 32
    full = src.crop((x, y, x + 16, y + 32)).convert("RGBA")
    return full.crop((0, 16, 16, 32)), full.crop((0, 0, 16, 16))


def fence_tiles(src: Image.Image):
    """Crop vanilla 16x32 fence pieces (horizontal rail, vertical post, corner)."""
    h_bot, h_top = _split32(src, 0, 6)      # two-rail horizontal
    v_bot, v_top = _split32(src, 0, 1)      # vertical post
    p_bot, p_top = _split32(src, 0, 0)      # corner post with rails
    # Composite so a 16x16 Buildings tile still shows the rail if it lives in the top half.
    def merge(bot, top):
        img = bot.copy()
        img.alpha_composite(top)
        return img
    # Prefer the visible rail on the Buildings tile for horizontal runs.
    h_visible = merge(h_bot, h_top)
    return h_visible, merge(v_bot, v_top), merge(p_bot, p_top), h_top


def draw_banner():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((1, 1, 14, 12), fill=rgb("#2d6a4f"), outline=INK)
    d.polygon([(1, 12), (8, 15), (14, 12)], fill=rgb("#2d6a4f"), outline=INK)
    d.line((3, 4, 13, 4), fill=rgb("#e9c46a"))
    d.line((3, 7, 13, 7), fill=rgb("#e9c46a"))
    return img


def main():
    sheet = Image.new("RGBA", (COLS * TS, ROWS * TS), (0, 0, 0, 0))
    fest = Image.open(MAPS / "Festivals.png").convert("RGBA")

    # Festival SHOP stall: 3-wide awning (tiles 43-45) and wooden counter (139-141).
    paste_tile(sheet, T_BOOTH_AWN_L, copy(fest, (11 * 16, 1 * 16, 12 * 16, 2 * 16)))
    paste_tile(sheet, T_BOOTH_AWN_M, copy(fest, (12 * 16, 1 * 16, 13 * 16, 2 * 16)))
    paste_tile(sheet, T_BOOTH_AWN_R, copy(fest, (13 * 16, 1 * 16, 14 * 16, 2 * 16)))
    paste_tile(sheet, T_BOOTH_CTR_L, copy(fest, (11 * 16, 4 * 16, 12 * 16, 5 * 16)))
    paste_tile(sheet, T_BOOTH_CTR_M, copy(fest, (12 * 16, 4 * 16, 13 * 16, 5 * 16)))
    paste_tile(sheet, T_BOOTH_CTR_R, copy(fest, (13 * 16, 4 * 16, 14 * 16, 5 * 16)))
    # Cover the green SHOP band with a ticket + coin plaque (spans L+M).
    d = ImageDraw.Draw(sheet)
    y0 = (T_BOOTH_CTR_L // COLS) * TS
    x0 = (T_BOOTH_CTR_L % COLS) * TS
    d.rectangle((x0 + 2, y0 + 4, x0 + 28, y0 + 12), fill=rgb("#6b3a1f"), outline=INK)
    d.rectangle((x0 + 3, y0 + 5, x0 + 18, y0 + 11), fill=rgb("#f4e3c1"), outline=INK)
    d.line((x0 + 5, y0 + 8, x0 + 16, y0 + 8), fill=rgb("#c9a227"))
    d.ellipse((x0 + 20, y0 + 5, x0 + 27, y0 + 12), fill=rgb("#e9c46a"), outline=INK)
    d.ellipse((x0 + 22, y0 + 7, x0 + 25, y0 + 10), outline=rgb("#c9a227"))

    tl, tr, bl, br = draw_board_pair()
    paste_tile(sheet, T_BOARD_TOP_L, tl)
    paste_tile(sheet, T_BOARD_TOP_R, tr)
    paste_tile(sheet, T_BOARD_BOT_L, bl)
    paste_tile(sheet, T_BOARD_BOT_R, br)

    sl, sr, sbl, sbr = draw_studio_pair()
    paste_tile(sheet, T_STUDIO_TOP_L, sl)
    paste_tile(sheet, T_STUDIO_TOP_R, sr)
    paste_tile(sheet, T_STUDIO_BOT_L, sbl)
    paste_tile(sheet, T_STUDIO_BOT_R, sbr)

    paste_tile(sheet, T_PLAQUE_ICE, draw_plaque(rgb("#d8eef8"), "ice"))
    paste_tile(sheet, T_PLAQUE_WATER, draw_plaque(rgb("#3a86c8"), "water"))
    paste_tile(sheet, T_PLAQUE_SAVANNA, draw_plaque(rgb("#e9c46a"), "savanna"))
    paste_tile(sheet, T_PLAQUE_JUNGLE, draw_plaque(rgb("#2d6a4f"), "jungle"))
    paste_tile(sheet, T_PLAQUE_FOREST, draw_plaque(rgb("#3d6b2a"), "forest"))
    paste_tile(sheet, T_PLAQUE_DINO, draw_plaque(rgb("#8a7a68"), "dino"))
    paste_tile(sheet, T_ZOO_BANNER, draw_banner())

    # Star copied from Cursors (the gold UI star).
    cursors = Image.open(UNPACKED / "LooseSprites" / "Cursors.png").convert("RGBA")
    paste_tile(sheet, T_STAR, copy(cursors, (364, 373, 380, 389)))

    # Coin-ish gold from festival / craftables: draw a small coin.
    coin = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    dc = ImageDraw.Draw(coin)
    dc.ellipse((2, 2, 13, 13), fill=rgb("#e9c46a"), outline=INK)
    dc.ellipse((5, 5, 10, 10), outline=rgb("#c9a227"))
    paste_tile(sheet, T_COIN, coin)

    wood = Image.open(LOOSE / "Fence1.png").convert("RGBA")
    stone = Image.open(LOOSE / "Fence2.png").convert("RGBA")
    iron = Image.open(LOOSE / "Fence3.png").convert("RGBA")
    for base, src in (
        ((T_WOOD_H, T_WOOD_V, T_WOOD_POST, T_WOOD_H2), wood),
        ((T_IRON_H, T_IRON_V, T_IRON_POST, T_IRON_H2), iron),
        ((T_STONE_H, T_STONE_V, T_STONE_POST, T_STONE_H2), stone),
    ):
        h, v, post, top = fence_tiles(src)
        paste_tile(sheet, base[0], h)
        paste_tile(sheet, base[1], v)
        paste_tile(sheet, base[2], post)
        paste_tile(sheet, base[3], top)

    # Hay crate from outdoor wheat stacks (tiles 244-246 area) — decorative only.
    outdoor = Image.open(MAPS / "spring_outdoorsTileSheet.png").convert("RGBA")
    paste_tile(sheet, T_HAY_CRATE, copy(outdoor, ((244 % 25) * 16, (244 // 25) * 16, (244 % 25) * 16 + 16, (244 // 25) * 16 + 16)))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(PREVIEW)
    print(f"Wrote tilesheet {sheet.size} to {OUT}")


if __name__ == "__main__":
    main()
