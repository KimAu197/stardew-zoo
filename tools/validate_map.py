"""Sanity checks for the zoo interior TMX.

Usage: python3 tools/validate_map.py
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import deque
from pathlib import Path

from vanilla import MAPS
from zoo_layout import BOARD, BOOTH, HABITATS, STUDIO, VISITOR_LOOP, WARP_TILES

ROOT = Path(__file__).resolve().parent.parent
MOD = ROOT / "[CP] Stardew Zoo"
TMX = MOD / "assets" / "StardewZoo.tmx"
GID_MASK = 0x1FFFFFFF

failures = []


def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        failures.append(msg)


def loaded_map_assets():
    """Maps/<name> targets Loaded by content.json -> source file."""
    text = re.sub(r"^\s*//.*$", "", (MOD / "content.json").read_text(), flags=re.M)
    out = {}
    for change in json.loads(text).get("Changes", []):
        if change.get("Action") != "Load":
            continue
        for target in change["Target"].split(","):
            target = target.strip()
            if target.startswith("Maps/"):
                out[target[len("Maps/"):]] = MOD / change["FromFile"]
    return out


def exact_file(folder, name):
    return folder.is_dir() and name in os.listdir(folder)


def main():
    try:
        root = ET.parse(TMX).getroot()
        check(True, f"TMX parses ({TMX.name})")
    except ET.ParseError as e:
        check(False, f"TMX parses: {e}")
        return 1

    W, H = int(root.get("width")), int(root.get("height"))
    props = {p.get("name"): p.get("value") for p in root.find("properties")}

    # --- tilesets ---
    loaded = loaded_map_assets()
    tilesets = []
    for ts in root.findall("tileset"):
        src = ts.find("image").get("source")
        stem = Path(src).stem if src.endswith(".png") else src
        if stem in loaded:
            ok = loaded[stem].exists()
            where = f"content.json Load -> {loaded[stem].name}"
        else:
            ok = exact_file(MAPS, f"{stem}.png")
            where = "vanilla Maps/"
        check(ok, f"tileset '{ts.get('name')}' image '{src}' resolves ({where})")
        tilesets.append((int(ts.get("firstgid")), int(ts.get("tilecount")), ts))
    tilesets.sort(key=lambda t: t[0])

    def tileset_for(gid):
        for i, (first, count, ts) in enumerate(tilesets):
            nxt = tilesets[i + 1][0] if i + 1 < len(tilesets) else 1 << 31
            if first <= gid < nxt:
                return first, count, ts
        return None

    # --- gids ---
    layers = {}
    for layer in root.findall("layer"):
        nums = [int(n) for n in layer.find("data").text.replace("\n", "").split(",") if n.strip()]
        grid = [nums[y * W:(y + 1) * W] for y in range(H)]
        layers[layer.get("name")] = grid
        bad = []
        for y, row in enumerate(grid):
            for x, raw in enumerate(row):
                gid = raw & GID_MASK
                if gid == 0:
                    continue
                hit = tileset_for(gid)
                if hit is None or gid - hit[0] >= hit[1]:
                    bad.append((x, y, gid))
        check(len(nums) == W * H and not bad,
              f"layer {layer.get('name')}: {len(nums)} cells, out-of-range gids {bad[:5]}")

    # --- passability ---
    passable_tiles = set()
    for first, _, ts in tilesets:
        for tile in ts.findall("tile"):
            for p in tile.iter("property"):
                if p.get("name") == "Passable":
                    passable_tiles.add(first + int(tile.get("id")))

    bld = layers["Buildings"]
    back = layers["Back"]

    def walkable(x, y):
        if not (0 <= x < W and 0 <= y < H):
            return False
        g = bld[y][x] & GID_MASK
        return back[y][x] != 0 and (g == 0 or g in passable_tiles)

    def flood(start):
        seen = {start} if walkable(*start) else set()
        q = deque(seen)
        while q:
            x, y = q.popleft()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n not in seen and walkable(*n):
                    seen.add(n)
                    q.append(n)
        return seen

    # Visitors pathfind between waypoints (VisitorManager.WalkLoop), so the loop is its waypoints.
    loop = set(VISITOR_LOOP)

    for name, (x, y, w, h) in HABITATS.items():
        reach = flood((x + w // 2, y + h // 2))
        inside = all((px, py) in reach for px in range(x, x + w) for py in range(y, y + h) if walkable(px, py))
        leak = reach & loop
        check(bool(reach) and inside and not leak,
              f"pen {name}: {len(reach)} tiles reachable, interior connected={inside}, reaches loop at {sorted(leak)[:3]}")

    wx, wy = WARP_TILES[0]
    entry = (wx, min(wy, H - 1))
    reach = flood(entry)
    check(bool(reach), f"entrance {entry} is walkable ({len(reach)} tiles reachable)")
    missing = sorted(loop - reach)
    check(not missing, f"visitor loop: {len(loop)} waypoints, unreachable from entrance {missing}")
    for label, (tx, ty) in (("booth", BOOTH), ("board", BOARD), ("studio", STUDIO)):
        adj = [n for n in ((tx, ty - 1), (tx, ty + 1), (tx - 1, ty), (tx + 1, ty)) if walkable(*n)]
        missing = [n for n in adj if n not in reach]
        check(bool(adj) and not missing,
              f"{label} {(tx, ty)}: interaction tiles {adj}, unreachable {missing}")

    check("ProduceArea" in props, f"ProduceArea property present ({props.get('ProduceArea')})")

    print(f"\n{'OK' if not failures else f'{len(failures)} FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
