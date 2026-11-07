"""Composite a Stardew TMX using its tilesheet PNGs (vanilla + custom).

Usage:
  python3 tools/render_map.py
  python3 tools/render_map.py path/to/map.tmx /tmp/out.png
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

from vanilla import MAPS

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "[CP] Stardew Zoo" / "assets"
FLIP_H = 0x80000000
FLIP_V = 0x40000000
FLIP_D = 0x20000000
GID_MASK = 0x1FFFFFFF


def find_sheet_image(source: str) -> Path:
    name = Path(source).name
    stem = Path(name).stem
    for folder in (ASSETS, MAPS):
        for candidate in (folder / name, folder / f"{stem}.png", folder / source):
            if candidate.exists():
                return candidate
    raise FileNotFoundError(f"Tilesheet not found: {source}")


def parse_csv(text: str, width: int, height: int) -> list[list[int]]:
    nums = [int(n) for n in text.replace("\n", "").split(",") if n.strip() != ""]
    rows = []
    for y in range(height):
        rows.append(nums[y * width:(y + 1) * width])
    return rows


def load_tilesets(map_el):
    sheets = []
    for ts in map_el.findall("tileset"):
        firstgid = int(ts.get("firstgid"))
        columns = int(ts.get("columns"))
        tilecount = int(ts.get("tilecount"))
        image_el = ts.find("image")
        src = image_el.get("source")
        path = find_sheet_image(src)
        img = Image.open(path).convert("RGBA")
        sheets.append((firstgid, tilecount, columns, img, src, path))
    sheets.sort(key=lambda s: s[0])
    return sheets


def lookup(sheets, gid):
    if gid <= 0:
        return None
    raw = gid & GID_MASK
    for i, (first, count, cols, img, src, path) in enumerate(sheets):
        nxt = sheets[i + 1][0] if i + 1 < len(sheets) else first + count
        if first <= raw < nxt:
            local = raw - first
            tw, th = 16, 16
            sx, sy = (local % cols) * tw, (local // cols) * th
            tile = img.crop((sx, sy, sx + tw, sy + th))
            flags = gid & (FLIP_H | FLIP_V | FLIP_D)
            if flags & FLIP_H:
                tile = tile.transpose(Image.FLIP_LEFT_RIGHT)
            if flags & FLIP_V:
                tile = tile.transpose(Image.FLIP_TOP_BOTTOM)
            return tile
    return None


LAYER_ORDER = ["Back", "Buildings", "Front", "AlwaysFront"]


def render_tmx(tmx_path: Path, out_path: Path, scale: int = 2, crop=None) -> Image.Image:
    tree = ET.parse(tmx_path)
    map_el = tree.getroot()
    width = int(map_el.get("width"))
    height = int(map_el.get("height"))
    tw, th = int(map_el.get("tilewidth")), int(map_el.get("tileheight"))
    sheets = load_tilesets(map_el)

    layers = {}
    for layer in map_el.findall("layer"):
        if layer.get("visible") == "0":
            continue
        data = layer.find("data")
        layers[layer.get("name")] = parse_csv(data.text or "", width, height)

    canvas = Image.new("RGBA", (width * tw, height * th), (0, 0, 0, 255))
    for name in LAYER_ORDER:
        grid = layers.get(name)
        if not grid:
            continue
        for y, row in enumerate(grid):
            for x, gid in enumerate(row):
                tile = lookup(sheets, gid)
                if tile is None:
                    continue
                canvas.alpha_composite(tile, (x * tw, y * th))

    if crop:
        canvas = canvas.crop(crop)
    if scale != 1:
        canvas = canvas.resize((canvas.width * scale, canvas.height * scale), Image.NEAREST)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    print(f"Rendered {tmx_path.name} -> {out_path} ({canvas.size})")
    return canvas


def main():
    tmx = Path(sys.argv[1]) if len(sys.argv) > 1 else ASSETS / "StardewZoo.tmx"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/zoo_art/interior.png")
    render_tmx(tmx, out, scale=2)


if __name__ == "__main__":
    main()
