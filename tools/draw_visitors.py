"""Visitor NPCs in vanilla villager proportions (16x32, 4x4 walk sheet).

Layout matches vanilla: row 0 down, 1 right, 2 up, 3 left; 4 frames each.
"""

from pathlib import Path

from PIL import Image, ImageDraw

from vanilla import CHARS

OUT_DIR = Path(__file__).resolve().parent.parent / "[CP] Stardew Zoo" / "assets"
PREVIEW_DIR = Path(__file__).resolve().parent / "previews"
FW, FH = 16, 32
INK = (52, 28, 16, 255)


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


# Four tourists: red jacket, blue shirt, green vest, yellow sunhat.
VARIANTS = [
    dict(skin=rgb("#f4c2a1"), skin_sh=rgb("#d89a78"), hair=rgb("#3b2314"), hair_hi=rgb("#6b4226"),
         shirt=rgb("#c23b22"), shirt_dk=rgb("#8a140c"), pants=rgb("#3d4a6e"), shoes=rgb("#3b2314"),
         hat=rgb("#c23b22"), hat_brim=rgb("#8a140c")),
    dict(skin=rgb("#e8b896"), skin_sh=rgb("#c48a68"), hair=rgb("#d8c07a"), hair_hi=rgb("#f0e0a8"),
         shirt=rgb("#3d6ea0"), shirt_dk=rgb("#24486e"), pants=rgb("#5c4033"), shoes=rgb("#3b2314"),
         hat=None, hat_brim=None),
    dict(skin=rgb("#f1c27d"), skin_sh=rgb("#c49258"), hair=rgb("#2b1a10"), hair_hi=rgb("#4a2e16"),
         shirt=rgb("#2d6a4f"), shirt_dk=rgb("#1b4332"), pants=rgb("#2b2d42"), shoes=rgb("#1b140c"),
         hat=rgb("#6b3a1f"), hat_brim=rgb("#3b2314")),
    dict(skin=rgb("#f4c2a1"), skin_sh=rgb("#d89a78"), hair=rgb("#6b2210"), hair_hi=rgb("#a33b18"),
         shirt=rgb("#efe6c8"), shirt_dk=rgb("#c4b07a"), pants=rgb("#457b9d"), shoes=rgb("#3b2314"),
         hat=rgb("#e9c46a"), hat_brim=rgb("#c9a227")),
]


def pset(px, x, y, c):
    if 0 <= x < FW and 0 <= y < FH and c[3] > 0:
        px[x, y] = c


def rect(px, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            pset(px, x, y, c)


def draw_person(v, direction, frame):
    """direction: 0 down, 1 right, 2 up, 3 left."""
    img = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    px = img.load()
    bob = 1 if frame % 2 else 0
    step = 0 if frame in (0, 2) else (1 if frame == 1 else -1)

    # Shoes / legs
    ly = 26 + bob
    if direction in (0, 2):
        rect(px, 5, ly, 7, 31, v["pants"])
        rect(px, 9, ly, 11, 31, v["pants"])
        # step
        if direction == 0:
            rect(px, 5, ly + (1 if step > 0 else 0), 7, 31 - (1 if step < 0 else 0), v["pants"])
            rect(px, 9, ly + (1 if step < 0 else 0), 11, 31 - (1 if step > 0 else 0), v["pants"])
        rect(px, 5, 30 + bob, 7, 31, v["shoes"])
        rect(px, 9, 30 + bob, 11, 31, v["shoes"])
    else:
        rect(px, 6, ly, 10, 31, v["pants"])
        rect(px, 7, 30 + bob, 10, 31, v["shoes"])

    # Torso
    ty = 16 + bob
    rect(px, 5, ty, 11, 25 + bob, v["shirt"])
    rect(px, 5, ty, 5, 25 + bob, v["shirt_dk"])
    rect(px, 11, ty, 11, 25 + bob, INK)
    rect(px, 5, 25 + bob, 11, 25 + bob, INK)
    # highlight
    rect(px, 6, ty + 1, 7, ty + 3, v["shirt"])

    # Arms
    arm_y = ty + 2
    if direction == 1:
        rect(px, 12, arm_y, 13, arm_y + 6 + step, v["skin"])
        pset(px, 13, arm_y + 6 + step, v["skin_sh"])
        rect(px, 4, arm_y + 1, 5, arm_y + 5, v["shirt_dk"])
    elif direction == 3:
        rect(px, 2, arm_y, 3, arm_y + 6 + step, v["skin"])
        pset(px, 2, arm_y + 6 + step, v["skin_sh"])
        rect(px, 11, arm_y + 1, 12, arm_y + 5, v["shirt_dk"])
    else:
        rect(px, 4, arm_y, 5, arm_y + 5, v["skin"])
        rect(px, 11, arm_y, 12, arm_y + 5, v["skin"])

    # Head — rounded rectangle like vanilla villagers
    hy = 8 + bob
    rect(px, 5, hy, 11, hy + 8, v["skin"])
    rect(px, 4, hy + 1, 12, hy + 7, v["skin"])
    rect(px, 10, hy + 3, 12, hy + 7, v["skin_sh"])
    # outline
    for x in range(5, 12):
        pset(px, x, hy, INK)
        pset(px, x, hy + 8, INK)
    for y in range(hy + 1, hy + 8):
        pset(px, 4, y, INK)
        pset(px, 12, y, INK)
    pset(px, 5, hy + 1, INK)
    pset(px, 11, hy + 1, INK)
    pset(px, 5, hy + 7, INK)
    pset(px, 11, hy + 7, INK)
    rect(px, 5, hy + 2, 10, hy + 6, v["skin"])
    rect(px, 10, hy + 4, 11, hy + 6, v["skin_sh"])

    # Hair
    if direction == 2:
        rect(px, 5, hy, 11, hy + 4, v["hair"])
        rect(px, 6, hy + 1, 8, hy + 2, v["hair_hi"])
    else:
        rect(px, 5, hy, 11, hy + 3, v["hair"])
        rect(px, 6, hy + 1, 8, hy + 2, v["hair_hi"])
        pset(px, 4, hy + 2, v["hair"])
        pset(px, 12, hy + 2, v["hair"])

    # Face
    if direction == 0:
        pset(px, 6, hy + 5, INK)
        pset(px, 10, hy + 5, INK)
        pset(px, 7, hy + 5, rgb("#ffffff"))
        pset(px, 11, hy + 5, rgb("#ffffff"))
        pset(px, 8, hy + 7, v["skin_sh"])
    elif direction == 1:
        pset(px, 10, hy + 5, INK)
        pset(px, 11, hy + 5, rgb("#ffffff"))
        pset(px, 10, hy + 7, v["skin_sh"])
    elif direction == 3:
        pset(px, 6, hy + 5, INK)
        pset(px, 5, hy + 5, rgb("#ffffff"))
        pset(px, 6, hy + 7, v["skin_sh"])

    # Hat
    if v["hat"]:
        by = hy - 1 if direction != 2 else hy
        rect(px, 4, hy - 2, 12, hy + 1, v["hat"])
        hline_y = hy + 1
        if v["hat_brim"]:
            rect(px, 3, hline_y, 13, hline_y, v["hat_brim"])
        for x in range(4, 13):
            pset(px, x, hy - 2, INK)
        pset(px, 4, hy - 1, INK)
        pset(px, 12, hy - 1, INK)

    # Camera for the green-vest tourist
    if v["shirt"] == rgb("#2d6a4f") and direction in (0, 1):
        rect(px, 7, ty + 3, 10, ty + 6, rgb("#2b2d42"))
        pset(px, 8, ty + 4, rgb("#7ec8e3"))

    return img


def build_sheet(variant):
    sheet = Image.new("RGBA", (FW * 4, FH * 4), (0, 0, 0, 0))
    for direction in range(4):
        for frame in range(4):
            sprite = draw_person(variant, direction, frame)
            sheet.paste(sprite, (frame * FW, direction * FH), sprite)
    return sheet


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    for i, variant in enumerate(VARIANTS):
        sheet = build_sheet(variant)
        sheet.save(OUT_DIR / f"StardewZooVisitor{i}.png")
        sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(
            PREVIEW_DIR / f"StardewZooVisitor{i}.png"
        )
    print("Wrote 4 visitor sheets")


if __name__ == "__main__":
    main()
