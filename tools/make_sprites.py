"""Generate the zoo building sprites by recoloring the vanilla barn sprites.

Animal sprites are drawn separately by tools/draw_animals.py.

Usage: python3 tools/make_sprites.py [path to "Content (unpacked)"]
"""

import sys
from pathlib import Path

from PIL import Image

DEFAULT_CONTENT = Path.home() / (
    "Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS/Content (unpacked)"
)
OUT_DIR = Path(__file__).resolve().parent.parent / "[CP] Stardew Zoo" / "assets"

# name: vanilla building sheet
BUILDINGS = {"Zoo": "Barn", "BigZoo": "Big Barn", "DeluxeZoo": "Deluxe Barn"}

# hue rotation (0-255 scale) that turns the red barn green
BUILDING_HUE_SHIFT = 85


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
    if not (content / "Buildings").is_dir():
        sys.exit(f"Unpacked content not found at {content}; run StardewXnbHack first.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, vanilla in BUILDINGS.items():
        hue_shift(Image.open(content / "Buildings" / f"{vanilla}.png"), BUILDING_HUE_SHIFT).save(OUT_DIR / f"{name}.png")

    print(f"Wrote {len(BUILDINGS)} building sprites to {OUT_DIR}")


if __name__ == "__main__":
    main()
