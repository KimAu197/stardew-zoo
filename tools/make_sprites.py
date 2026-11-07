"""Draw Stardew-style zoo exteriors (7x4 footprint, 112x128 sprites).

Does not touch animal art. Three tiers share the same footprint so placed
buildings keep working. HumanDoor is tile (1, 3) — drawn as a wide arched gate.

Usage: python3 tools/make_sprites.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

from vanilla import BUILDINGS, LOOSE, MAPS, SHEETS

OUT_DIR = Path(__file__).resolve().parent.parent / "[CP] Stardew Zoo" / "assets"
PREVIEW_DIR = Path(__file__).resolve().parent / "previews"
W, H = 112, 128

# ConcernedApe outline: dark colored, never pure black.
INK = (52, 11, 14, 255)
INK2 = (40, 18, 12, 255)


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def pset(px, x, y, c):
    if 0 <= x < W and 0 <= y < H and c[3] > 0:
        px[x, y] = c


def mix_over(px, x, y, c):
    if not (0 <= x < W and 0 <= y < H) or c[3] == 0:
        return
    dst = px[x, y]
    if dst[3] == 0:
        px[x, y] = c
        return
    a = c[3] / 255
    px[x, y] = tuple(int(c[i] * a + dst[i] * (1 - a)) for i in range(3)) + (255,)


def hline(px, x0, x1, y, c):
    if x1 < x0:
        x0, x1 = x1, x0
    for x in range(x0, x1 + 1):
        pset(px, x, y, c)


def vline(px, x, y0, y1, c):
    if y1 < y0:
        y0, y1 = y1, y0
    for y in range(y0, y1 + 1):
        pset(px, x, y, c)


def fill_rect(px, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        hline(px, x0, x1, y, c)


def roof_top(x, peak_x, peak_y, left, right, eave_y):
    if x <= left or x >= right:
        return eave_y
    if x < peak_x:
        t = (x - left) / max(1, peak_x - left)
        return int(round(eave_y + t * (peak_y - eave_y)))
    t = (x - peak_x) / max(1, right - peak_x)
    return int(round(peak_y + t * (eave_y - peak_y)))


def draw_shingles(px, left, right, peak_x, peak_y, eave_y, palette):
    """Trapezoid roof with horizontal overlapping shingles like the Shed."""
    hi, mid, shade, ink = palette
    for x in range(left, right + 1):
        y0 = roof_top(x, peak_x, peak_y, left, right, eave_y)
        for y in range(y0, eave_y + 1):
            pset(px, x, y, mid)

    row_h = 6
    shingle_w = 10
    y = peak_y + 2
    row = 0
    while y < eave_y:
        offset = (row * (shingle_w // 2)) % shingle_w
        x = left - offset
        while x < right + 2:
            for dx in range(shingle_w):
                sx = x + dx
                if sx < left or sx > right:
                    continue
                y0 = roof_top(sx, peak_x, peak_y, left, right, eave_y)
                for dy in range(row_h):
                    sy = y + dy
                    if sy < y0 or sy > eave_y:
                        continue
                    if dy == 0:
                        col = hi
                    elif dy >= row_h - 2:
                        col = ink if dy == row_h - 1 else shade
                    elif dx == 0:
                        col = shade
                    elif dx == shingle_w - 1:
                        col = ink
                    elif dx <= 2 and dy == 1:
                        col = hi
                    else:
                        col = mid
                    pset(px, sx, sy, col)
            x += shingle_w
        y += row_h - 2
        row += 1

    for x in range(left, right + 1):
        y0 = roof_top(x, peak_x, peak_y, left, right, eave_y)
        pset(px, x, y0, ink)
        if x > left:
            pset(px, x, min(eave_y, y0 + 1), hi)
        pset(px, x, eave_y, ink)
        pset(px, x, eave_y - 1, shade)
    vline(px, left, roof_top(left, peak_x, peak_y, left, right, eave_y), eave_y, ink)
    vline(px, right, roof_top(right, peak_x, peak_y, left, right, eave_y), eave_y, ink)


def draw_wood_wall(px, x0, y0, x1, y1, colors):
    hi, mid, shade, grain = colors
    plank = 6
    for x in range(x0, x1 + 1):
        pi = (x - x0) // plank
        base = (hi, mid, mid, shade)[pi % 4]
        for y in range(y0, y1 + 1):
            col = base
            local = (x - x0) % plank
            if local == 0:
                col = grain
            elif local == 1:
                col = hi
            elif local == plank - 1:
                col = shade
            if (y + pi * 5) % 13 == 0 and local in (2, 3):
                col = grain
            pset(px, x, y, col)
    # outer outline
    hline(px, x0, x1, y0, INK)
    hline(px, x0, x1, y1, INK)
    vline(px, x0, y0, y1, INK)
    vline(px, x1, y0, y1, INK)
    # top-left rim light
    hline(px, x0 + 1, x1 - 1, y0 + 1, hi)
    vline(px, x0 + 1, y0 + 1, y1 - 1, hi)


def draw_stone_wall(px, x0, y0, x1, y1, colors):
    hi, mid, shade, grout = colors
    for y in range(y0, y1 + 1):
        row = (y - y0) // 5
        odd = row % 2
        for x in range(x0, x1 + 1):
            col_i = (x - x0 + (3 if odd else 0)) // 7
            local_x = (x - x0 + (3 if odd else 0)) % 7
            local_y = (y - y0) % 5
            if local_x == 0 or local_y == 0:
                col = grout
            elif local_x == 1 or local_y == 1:
                col = hi
            elif local_x >= 5 or local_y >= 4:
                col = shade
            else:
                col = mid
            if (col_i + row) % 5 == 0 and local_x == 2:
                col = hi
            pset(px, x, y, col)
    hline(px, x0, x1, y0, INK)
    hline(px, x0, x1, y1, INK)
    vline(px, x0, y0, y1, INK)
    vline(px, x1, y0, y1, INK)


def draw_window(px, x, y, w=16, h=14, glass=None, frame=None):
    glass = glass or rgb("#7ec8e3")
    glass_dk = lerp(glass, (20, 40, 60, 255), 0.35)
    glass_hi = lerp(glass, (255, 255, 255, 255), 0.45)
    frame = frame or rgb("#6b3a1f")
    fill_rect(px, x, y, x + w - 1, y + h - 1, frame)
    fill_rect(px, x + 1, y + 1, x + w - 2, y + h - 2, glass)
    # 4 panes, light top-left
    mid_x = x + w // 2
    mid_y = y + h // 2
    vline(px, mid_x, y, y + h - 1, frame)
    hline(px, x, x + w - 1, mid_y, frame)
    for yy in range(y + 2, mid_y):
        for xx in range(x + 2, mid_x):
            if xx - x + yy - y < 7:
                pset(px, xx, yy, glass_hi)
    for yy in range(mid_y + 1, y + h - 2):
        for xx in range(mid_x + 1, x + w - 2):
            pset(px, xx, yy, glass_dk)
    hline(px, x, x + w - 1, y, INK)
    hline(px, x, x + w - 1, y + h - 1, INK)
    vline(px, x, y, y + h - 1, INK)
    vline(px, x + w - 1, y, y + h - 1, INK)


def draw_arch_gate(px, x0, y0, x1, y1, wood, dark_in):
    """Arched entrance covering HumanDoor tile (1,3) and the tile to its right."""
    hi, mid, shade = wood
    arch_h = min(12, (y1 - y0) // 2)
    cx = (x0 + x1) / 2
    rx = (x1 - x0) / 2

    def inside(x, y):
        if y > y0 + arch_h:
            return x0 + 3 <= x <= x1 - 3
        nx = (x - cx) / max(1.0, rx)
        ny = (y0 + arch_h - y) / max(1.0, arch_h)
        return nx * nx + ny * ny <= 1.02

    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if inside(x, y):
                pset(px, x, y, dark_in)

    # Wood frame
    for y in range(y0, y1 + 1):
        for t, col in ((0, INK), (1, hi), (2, mid), (3, shade)):
            pset(px, x0 + t, y, col)
            pset(px, x1 - t, y, INK if t == 0 else shade if t == 1 else mid)
    # Arch voussoirs
    for x in range(x0, x1 + 1):
        nx = (x - cx) / max(1, rx)
        y_arch = int(y0 + arch_h - (arch_h * (1 - min(1, nx * nx)) ** 0.5))
        for dy in range(0, 4):
            col = INK if dy == 0 else hi if dy == 1 else mid
            pset(px, x, y_arch + dy, col)
            pset(px, x, y_arch - 1, INK)
    # Door boards inside the opening
    for x in range(x0 + 4, x1 - 3):
        local = (x - x0) % 4
        col = hi if local == 1 else shade if local == 3 else mid
        for y in range(y0 + arch_h + 2, y1):
            pset(px, x, y, col)
    # Handle on the right leaf, about chest height
    hx, hy = x1 - 8, y0 + (y1 - y0) * 2 // 3
    pset(px, hx, hy, rgb("#e6c07b"))
    pset(px, hx + 1, hy, rgb("#c9a227"))
    pset(px, hx, hy + 1, rgb("#6b3a1f"))


GLYPHS = {
    "Z": ["#####", "#   #", "   # ", "  #  ", " #   ", "#   #", "#####"],
    "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "o": ["     ", " ### ", "#   #", "#   #", "#   #", " ### ", "     "],
}


def blit_glyph(px, gx, gy, ch, col, shadow=None):
    rows = GLYPHS[ch]
    for j, row in enumerate(rows):
        for i, bit in enumerate(row):
            if bit != "#":
                continue
            if shadow:
                pset(px, gx + i + 1, gy + j + 1, shadow)
            pset(px, gx + i, gy + j, col)


def draw_zoo_sign(px, x, y, w, h, letter, letter_hi, board, board_hi, board_dk, gold=False):
    fill_rect(px, x, y, x + w - 1, y + h - 1, board)
    fill_rect(px, x + 1, y + 1, x + w - 2, y + 2, board_hi)
    fill_rect(px, x + 1, y + h - 2, x + w - 2, y + h - 1, board_dk)
    hline(px, x, x + w - 1, y, INK)
    hline(px, x, x + w - 1, y + h - 1, INK)
    vline(px, x, y, y + h - 1, INK)
    vline(px, x + w - 1, y, y + h - 1, INK)
    if gold:
        hline(px, x + 2, x + w - 3, y + 2, rgb("#e9c46a"))
        hline(px, x + 2, x + w - 3, y + h - 3, rgb("#c9a227"))
    # hanging chains
    vline(px, x + 6, y - 5, y, INK2)
    vline(px, x + w - 7, y - 5, y, INK2)
    # letters
    gap = 2
    total = 5 * 3 + gap * 2
    sx = x + (w - total) // 2
    sy = y + (h - 7) // 2
    blit_glyph(px, sx, sy, "Z", letter, INK2)
    blit_glyph(px, sx + 5 + gap, sy, "O", letter, INK2)
    blit_glyph(px, sx + 10 + gap * 2, sy, "O", letter, INK2)
    # tiny paw / animal mark on deluxe
    if gold:
        cx, cy = x + w - 9, y + h - 6
        pset(px, cx, cy, letter_hi)
        pset(px, cx + 2, cy, letter_hi)
        pset(px, cx + 1, cy + 2, letter_hi)


def draw_flag(px, pole_x, top_y, bot_y, facing=1, cloth=None, pole=None):
    cloth = cloth or rgb("#c23b22")
    cloth_dk = lerp(cloth, INK, 0.35)
    cloth_hi = lerp(cloth, (255, 255, 255, 255), 0.25)
    pole = pole or rgb("#6b3a1f")
    vline(px, pole_x, top_y, bot_y, INK)
    vline(px, pole_x + 1, top_y, bot_y, pole)
    length = 15
    for y in range(0, 11):
        wave = 1 if (y // 2) % 2 else 0
        width = max(2, length - abs(y - 4) - (y // 5))
        for i in range(width):
            if facing > 0:
                x = pole_x + 2 + i + wave
            else:
                x = pole_x - 1 - i - wave
            col = cloth_hi if y <= 2 and i < 3 else cloth_dk if i > width - 3 else cloth
            pset(px, x, top_y + 2 + y, col)
        tip = (pole_x + 2 + width - 1 + wave) if facing > 0 else (pole_x - width - wave)
        pset(px, tip, top_y + 2 + y, INK)
    pset(px, pole_x, top_y, rgb("#e9c46a"))


def draw_column(px, x, y0, y1, stone, gold=False):
    hi, mid, shade = stone
    fill_rect(px, x, y0 + 3, x + 7, y1 - 3, mid)
    vline(px, x, y0 + 3, y1 - 3, hi)
    vline(px, x + 1, y0 + 3, y1 - 3, hi)
    vline(px, x + 6, y0 + 3, y1 - 3, shade)
    vline(px, x + 7, y0 + 3, y1 - 3, INK)
    vline(px, x, y0 + 3, y1 - 3, INK)
    # capital / base
    cap = rgb("#e9c46a") if gold else hi
    cap_dk = rgb("#c9a227") if gold else shade
    fill_rect(px, x - 2, y0, x + 9, y0 + 4, cap)
    hline(px, x - 2, x + 9, y0, INK)
    hline(px, x - 2, x + 9, y0 + 4, INK)
    fill_rect(px, x - 2, y1 - 4, x + 9, y1, cap_dk)
    hline(px, x - 2, x + 9, y1 - 4, INK)
    hline(px, x - 2, x + 9, y1, INK)


def stamp_plant(img, dest_x, dest_y):
    plants = Image.open(SHEETS / "Craftables.png").convert("RGBA")
    # second potted plant (leafy), 16x32
    spr = plants.crop((16, 0, 32, 32))
    img.alpha_composite(spr, (dest_x, dest_y))


def stamp_flower_pot(img, dest_x, dest_y):
    town = Image.open(MAPS / "spring_town.png").convert("RGBA")
    # flower barrel 1015-1017 around row 31, but use a 16x16 pot from craftables cactus
    plants = Image.open(SHEETS / "Craftables.png").convert("RGBA")
    spr = plants.crop((80, 0, 96, 32))  # cactus pot
    img.alpha_composite(spr, (dest_x, dest_y))


def draw_lion_silhouette(px, cx, cy, col, hi):
    # tiny sitting-lion statue for deluxe peak
    body = [
        "  ####  ",
        " ##  ###",
        "########",
        " ##  ## ",
        " #    # ",
    ]
    for j, row in enumerate(body):
        for i, bit in enumerate(row):
            if bit == "#":
                pset(px, cx + i, cy + j, col if j > 0 else hi)
    pset(px, cx + 7, cy + 1, col)  # tail tip


def draw_building(tier: int) -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()

    if tier == 0:
        roof = (rgb("#f0a03a"), rgb("#c23a12"), rgb("#8a140c"), rgb("#4a0c0c"))
        wood = (rgb("#e0a35a"), rgb("#c17a32"), rgb("#8a4e18"), rgb("#6b3a1f"))
        wall_fn = draw_wood_wall
        flags = True
        columns = False
        gold = False
        stone_base = False
        letter = rgb("#6b2210")
        letter_hi = rgb("#a33b18")
        board = rgb("#e8d59a")
        board_hi = rgb("#f4e8c0")
        board_dk = rgb("#c4a35a")
        glass = rgb("#7ec8e3")
        gate_in = rgb("#3a1c10")
    elif tier == 1:
        roof = (rgb("#8eb4d4"), rgb("#3d6ea0"), rgb("#24486e"), rgb("#14283c"))
        wood = (rgb("#d8c4a0"), rgb("#c4a574"), rgb("#8a6a3d"), rgb("#5c4033"))
        wall_fn = draw_stone_wall
        flags = True
        columns = False
        gold = False
        stone_base = True
        letter = rgb("#1d3557")
        letter_hi = rgb("#457b9d")
        board = rgb("#efe6c8")
        board_hi = rgb("#fff8dc")
        board_dk = rgb("#c4b07a")
        glass = rgb("#b8e0f0")
        gate_in = rgb("#2b2d42")
        stone = (rgb("#d0ccc4"), rgb("#a8a39a"), rgb("#6e6a64"), rgb("#4a4742"))
    else:
        roof = (rgb("#e8b84a"), rgb("#b03a2e"), rgb("#6e1610"), rgb("#3c0c0c"))
        wood = (rgb("#efece4"), rgb("#d9d2c5"), rgb("#9a9180"), rgb("#5c5548"))
        wall_fn = draw_stone_wall
        flags = True
        columns = True
        gold = True
        stone_base = True
        letter = rgb("#7b2d3b")
        letter_hi = rgb("#c9a227")
        board = rgb("#f4e3c1")
        board_hi = rgb("#fff4d4")
        board_dk = rgb("#c9a227")
        glass = rgb("#cae9ff")
        gate_in = rgb("#241410")
        stone = (rgb("#e8e4dc"), rgb("#c8c2b6"), rgb("#8a8478"), rgb("#4a4742"))

    left, right = 6, 105
    peak_x, peak_y, eave_y = 56, 8, 56
    body_top, body_bot = 54, 126

    # Roof first (sits above the 4-tile footprint).
    if tier == 2:
        # slightly taller / wider eaves
        peak_y = 4
        eave_y = 54
    draw_shingles(px, left, right, peak_x, peak_y, eave_y, roof)

    # Decorative ridge board
    hline(px, peak_x - 8, peak_x + 8, peak_y, INK)
    if gold:
        fill_rect(px, peak_x - 3, peak_y - 4, peak_x + 3, peak_y, rgb("#e9c46a"))
        hline(px, peak_x - 3, peak_x + 3, peak_y - 4, INK)
        draw_lion_silhouette(px, peak_x - 3, peak_y - 12, rgb("#c9a227"), rgb("#f4d35e"))
    else:
        # small chimney like the shed
        fill_rect(px, 86, peak_y + 10, 94, eave_y - 8, rgb("#8a6a3d") if tier == 0 else rgb("#9aa3ad"))
        hline(px, 86, 94, peak_y + 10, INK)
        vline(px, 86, peak_y + 10, eave_y - 8, INK)
        vline(px, 94, peak_y + 10, eave_y - 8, INK)
        fill_rect(px, 85, peak_y + 8, 95, peak_y + 11, INK)

    if flags:
        cloth0 = rgb("#2d6a4f") if tier == 0 else rgb("#1d3557") if tier == 1 else rgb("#e9c46a")
        cloth1 = rgb("#c23b22") if tier != 2 else rgb("#7b2d3b")
        draw_flag(px, 14, 14, eave_y + 4, facing=1, cloth=cloth0)
        draw_flag(px, 96, 14, eave_y + 4, facing=-1, cloth=cloth1)

    # Body
    if tier == 0:
        draw_wood_wall(px, left, body_top, right, body_bot, wood)
    else:
        draw_stone_wall(px, left, body_top, right, body_bot, stone)
        if tier == 1:
            # wood upper half over stone
            draw_wood_wall(px, left + 1, body_top, right - 1, body_top + 28, wood)

    if columns:
        draw_column(px, 10, body_top + 4, body_bot - 2, (rgb("#efece4"), rgb("#d9d2c5"), rgb("#8a8478")), gold=True)
        draw_column(px, 94, body_top + 4, body_bot - 2, (rgb("#efece4"), rgb("#d9d2c5"), rgb("#8a8478")), gold=True)
        # gold eave trim
        hline(px, left + 2, right - 2, body_top + 2, rgb("#e9c46a"))
        hline(px, left + 2, right - 2, body_top + 3, rgb("#c9a227"))

    # Windows (upper story of the 4-tile body)
    draw_window(px, 70, 78, 16, 14, glass=glass)
    if tier >= 1:
        draw_window(px, 88, 78, 12, 14, glass=glass)

    # Arched gate at HumanDoor X=1 (px 16-32) spanning into tile X=2.
    draw_arch_gate(px, 16, 96, 48, 126, (wood[0], wood[1], wood[2]), gate_in)

    # Hanging ZOO sign, centered on the facade under the eaves.
    draw_zoo_sign(px, 34, 58, 44, 18, letter, letter_hi, board, board_hi, board_dk, gold=gold)

    # Ground contact shadow
    hline(px, left + 2, right - 2, 127, (40, 18, 12, 180))

    img = img.convert("RGBA")
    # Potted plants flanking the gate (vanilla craftable pixels).
    stamp_plant(img, 50, 96)
    if tier == 0:
        stamp_flower_pot(img, 2, 96)
    else:
        stamp_plant(img, 0, 96)
        stamp_flower_pot(img, 98, 96)
    return img


def grass_backdrop() -> Image.Image:
    grass = Image.open(MAPS / "spring_outdoorsTileSheet.png").convert("RGBA")
    tile = grass.crop((0, 6 * 16, 16, 7 * 16))  # tile 150
    cols, rows = 24, 10
    bg = Image.new("RGBA", (cols * 16, rows * 16), (0, 0, 0, 0))
    for y in range(rows):
        for x in range(cols):
            bg.paste(tile, (x * 16, y * 16))
    return bg


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    names = ("Zoo", "BigZoo", "DeluxeZoo")
    sprites = []
    for tier, name in enumerate(names):
        img = draw_building(tier)
        img.save(OUT_DIR / f"{name}.png")
        img.resize((W * 4, H * 4), Image.NEAREST).save(PREVIEW_DIR / f"{name}.png")
        sprites.append(img)

    bg = grass_backdrop()
    canvas = bg.resize((bg.width * 4, bg.height * 4), Image.NEAREST)
    # place three buildings on the grass, aligned to the 4-tile footprint
    # sprite is 112x128; footprint is bottom 64px. Scale 4 → 448x512
    gap = 24 * 4
    total_w = 3 * W * 4 + 2 * gap + 32 * 4
    sheet = Image.new("RGBA", (total_w, 160 * 4), (0, 0, 0, 0))
    grass4 = grass_backdrop().resize((total_w, 160 * 4), Image.NEAREST)
    sheet.paste(grass4, (0, 0))
    for i, spr in enumerate(sprites):
        big = spr.resize((W * 4, H * 4), Image.NEAREST)
        x = 16 * 4 + i * (W * 4 + gap)
        y = 24 * 4
        sheet.alpha_composite(big, (x, y))
    dest = Path("/tmp/zoo_art")
    dest.mkdir(parents=True, exist_ok=True)
    sheet.save(dest / "exteriors.png")
    print(f"Wrote {len(names)} zoo exteriors to {OUT_DIR}")
    print(f"Wrote {dest / 'exteriors.png'}")


if __name__ == "__main__":
    main()
