"""Generate placeholder zoo sprites by recoloring vanilla Stardew Valley sprites.

Usage: python3 tools/make_sprites.py [path to "Content (unpacked)"]
"""

import sys
from pathlib import Path

from PIL import Image, ImageOps

DEFAULT_CONTENT = Path.home() / (
    "Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS/Content (unpacked)"
)
OUT_DIR = Path(__file__).resolve().parent.parent / "[CP] Stardew Zoo" / "assets"

# name: (vanilla adult sheet, vanilla baby sheet, shop icon rect in Cursors, (dark, mid, light))
ANIMALS = {
    "Penguin": ("White Chicken", "BabyWhite Chicken", (0, 448, 32, 16), ("#0b1020", "#2e3a59", "#e8eef7")),
    "Panda": ("White Cow", "BabyWhite Cow", (32, 448, 32, 16), ("#000000", "#404040", "#ffffff")),
    "Lion": ("Pig", "BabyPig", (0, 480, 32, 16), ("#3b1f05", "#c27a1e", "#f5c56a")),
    "Giraffe": ("Brown Cow", "BabyBrown Cow", (32, 448, 32, 16), ("#3d2410", "#c98b2b", "#f6e3a1")),
}

# name: vanilla building sheet
BUILDINGS = {"Zoo": "Barn", "BigZoo": "Big Barn", "DeluxeZoo": "Deluxe Barn"}

# hue rotation (0-255 scale) that turns the red barn green
BUILDING_HUE_SHIFT = 85


def colorize(image: Image.Image, palette: tuple[str, str, str]) -> Image.Image:
    """Map the image's brightness onto a dark/mid/light palette, keeping transparency."""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    dark, mid, light = palette
    colored = ImageOps.colorize(ImageOps.grayscale(rgba), black=dark, white=light, mid=mid).convert("RGBA")
    colored.putalpha(alpha)
    return colored


def hue_shift(image: Image.Image, shift: int) -> Image.Image:
    """Rotate the hue of every pixel, keeping transparency."""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    h, s, v = rgba.convert("RGB").convert("HSV").split()
    h = h.point(lambda value: (value + shift) % 256)
    shifted = Image.merge("HSV", (h, s, v)).convert("RGBA")
    shifted.putalpha(alpha)
    return shifted


def main() -> None:
    content = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONTENT
    if not (content / "Animals").is_dir():
        sys.exit(f"Unpacked content not found at {content}; run StardewXnbHack first.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cursors = Image.open(content / "LooseSprites" / "Cursors.png")

    for name, (adult, baby, shop_rect, palette) in ANIMALS.items():
        colorize(Image.open(content / "Animals" / f"{adult}.png"), palette).save(OUT_DIR / f"{name}.png")
        colorize(Image.open(content / "Animals" / f"{baby}.png"), palette).save(OUT_DIR / f"Baby{name}.png")
        x, y, width, height = shop_rect
        colorize(cursors.crop((x, y, x + width, y + height)), palette).save(OUT_DIR / f"{name}Shop.png")

    for name, vanilla in BUILDINGS.items():
        hue_shift(Image.open(content / "Buildings" / f"{vanilla}.png"), BUILDING_HUE_SHIFT).save(OUT_DIR / f"{name}.png")

    print(f"Wrote {len(list(OUT_DIR.glob('*.png')))} sprites to {OUT_DIR}")


if __name__ == "__main__":
    main()
