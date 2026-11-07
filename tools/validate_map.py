"""Sanity checks for the zoo interior TMX (park + walk-in pavilion regions).

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
from zoo_layout import (BOARD, BOOTH, CS_PATH, ENTRANCE, FACADES, HABITATS, OPEN_PENS, OUTDOOR, PAVILIONS, PRODUCE_AREA,
                        REGIONS, STUDIO, VISITOR_ROUTE, WARP_TILES, ZOO_PERCHES, barrier, csharp, facade_door,
                        inner_loop, inside_arrival, inside_door, outside_arrival, region_of)

ROOT = Path(__file__).resolve().parent.parent
MOD = ROOT / "[CP] Stardew Zoo"
TMX = MOD / "assets" / "StardewZoo.tmx"
MOVEMENT_CS = ROOT / "StardewZoo" / "AnimalMovement.cs"
GID_MASK = 0x1FFFFFFF
TOUCH_ACTION = "StardewZoo_Pavilion"

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


def rect_tiles(r):
    x, y, w, h = r
    return {(cx, cy) for cy in range(y, y + h) for cx in range(x, x + w)}


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
        check(ok, f"tileset '{ts.get('name')}' image '{src}' resolves with exact case ({where})")
        tilesets.append((int(ts.get("firstgid")), int(ts.get("tilecount")), ts))
    tilesets.sort(key=lambda t: t[0])
    first_gid = {ts.get("name"): first for first, _, ts in tilesets}

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

    # --- tile data objects ---
    tile_props = {}
    for group in root.findall("objectgroup"):
        for obj in group.findall("object"):
            if obj.get("name") != "TileData":
                continue
            pos = (int(float(obj.get("x"))) // 16, int(float(obj.get("y"))) // 16)
            for p in obj.iter("property"):
                tile_props.setdefault(pos, {})[(group.get("name"), p.get("name"))] = p.get("value")

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

    def flood(start, blocked=frozenset()):
        seen = {start} if walkable(*start) and start not in blocked else set()
        q = deque(seen)
        while q:
            x, y = q.popleft()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n not in seen and n not in blocked and walkable(*n):
                    seen.add(n)
                    q.append(n)
        return seen

    # --- pens ---
    for name, rect in HABITATS.items():
        x, y, w, h = rect
        tiles = rect_tiles(rect)
        reach = flood((x + w // 2, y + h // 2))
        inside = all(t in reach for t in tiles if walkable(*t))
        walk = sum(1 for t in tiles if walkable(*t))
        leak = sorted(reach - tiles)
        check(bool(reach) and inside and not leak and walk == len(tiles),
              f"pen {name} {rect}: sealed (leaks {leak[:3]}), {walk}/{len(tiles)} tiles walkable, connected={inside}")

    # --- park ---
    wx, wy = WARP_TILES[0]
    entry = (wx, min(wy, H - 1))
    park = flood(entry)
    check(bool(park), f"park entrance {entry} is walkable ({len(park)} tiles reachable)")
    check(all(region_of(*t) == "Outdoor" for t in park), "park flood stays inside the park region")
    for name in PAVILIONS:
        door, arrive = facade_door(name), outside_arrival(name)
        props_here = tile_props.get(door, {})
        action = props_here.get(("Back", "TouchAction"))
        check(door in park and arrive in park and action == f"{TOUCH_ACTION} {name} In",
              f"pavilion {name}: park door {door} reachable={door in park}, arrival {arrive} reachable={arrive in park}, TouchAction '{action}'")
        fx, fy, fw, fh = FACADES[name]
        solid = [t for t in rect_tiles(FACADES[name]) if t != door and walkable(*t)]
        check(not solid, f"pavilion {name}: facade {FACADES[name]} is solid apart from its door (walkable {solid[:3]})")
    for label, (tx, ty) in (("booth", BOOTH), ("board", BOARD), ("studio", STUDIO)):
        adj = [n for n in ((tx, ty - 1), (tx, ty + 1), (tx - 1, ty), (tx + 1, ty)) if walkable(*n)]
        missing = [n for n in adj if n not in park]
        check(bool(adj) and not missing, f"{label} {(tx, ty)}: interaction tiles {adj}, unreachable {missing}")

    # --- pavilion interiors ---
    for name in PAVILIONS:
        rx, ry, rw, rh = REGIONS[name]
        start = inside_arrival(name)
        hall = flood(start)
        region = rect_tiles(REGIONS[name])
        out = sorted(hall - region)
        check(bool(hall) and not out, f"pavilion {name} {REGIONS[name]}: {len(hall)} tiles reachable, isolated (escapes {out[:3]})")
        door = inside_door(name)
        action = tile_props.get(door, {}).get(("Back", "TouchAction"))
        check(door in hall and action == f"{TOUCH_ACTION} {name} Out",
              f"pavilion {name}: exit door {door} reachable={door in hall}, TouchAction '{action}'")
        bx, by, bw, bh = barrier(name)
        ring = {t for t in hall if not (bx <= t[0] < bx + bw and by <= t[1] < by + bh)}
        cut = {(start[0], yy) for yy in range(by + bh, ry + rh)}
        left, right = (start[0] - 1, ry + rh - 3), (start[0] + 1, ry + rh - 3)
        around = right in flood(left, blocked=frozenset(cut | (region - ring)))
        check(around, f"pavilion {name}: walkway ring loops all the way around the exhibit (cut below at x={start[0]})")
        lost = [p for p in inner_loop(name) if p not in hall]
        check(not lost, f"pavilion {name}: inner-loop waypoints reachable (missing {lost})")

    # --- isolation: every walkable tile belongs to a region and to its region's component ---
    stray = [(x, y) for y in range(H) for x in range(W) if walkable(x, y) and region_of(x, y) is None]
    check(not stray, f"no walkable void tiles ({stray[:3]})")

    # --- visitor route ---
    pos, problems = ENTRANCE, []
    comp = flood(pos)
    for i, (kind, target) in enumerate(VISITOR_ROUTE):
        if kind == "teleport":
            if not walkable(*target):
                problems.append((i, kind, target))
            pos, comp = target, flood(target)
        else:
            if target not in comp:
                problems.append((i, kind, target))
            pos = target
    check(not problems and pos == ENTRANCE,
          f"visitor route: {len(VISITOR_ROUTE)} steps, each walk reachable in its region, ends at entrance (problems {problems[:3]})")

    # --- swimming water + perches ---
    water_ids = set(int(n) for n in re.findall(r"\d+", re.search(r"WaterTileIndexes = new\(\) \{([^}]*)\}", MOVEMENT_CS.read_text()).group(1)))
    outdoors = first_gid["outdoors"]
    for name in ("Ice", "Water"):
        n = sum(1 for (x, y) in rect_tiles(HABITATS[name]) if (back[y][x] & GID_MASK) - outdoors in water_ids)
        check(n >= 8, f"pen {name}: {n} swimmable water tiles recognised by AnimalMovement.WaterTileIndexes")
    for pen, spots in ZOO_PERCHES.items():
        tagged = [s for s in spots if ("Back", "ZooPerch") in tile_props.get(s, {})]
        inside = all(s in rect_tiles(HABITATS[pen]) for s in spots)
        check(len(tagged) == len(spots) and inside and len(spots) >= 3,
              f"pen {pen}: {len(tagged)}/{len(spots)} ZooPerch trees tagged inside the pen")

    # --- properties and generated C# ---
    produce = tuple(int(v) for v in (props.get("ProduceArea") or "0 0 0 0").split())
    check(produce == PRODUCE_AREA and region_of(produce[0], produce[1]) == "Outdoor",
          f"ProduceArea property present in the park ({props.get('ProduceArea')})")
    check(props.get("StardewZooLocation") == "T", "StardewZooLocation map property set")
    check(CS_PATH.exists() and CS_PATH.read_text() == csharp(), f"{CS_PATH.name} matches tools/zoo_layout.py")
    check(set(OPEN_PENS) | set(PAVILIONS) == set(HABITATS), "every habitat is an open pen or a pavilion")

    print(f"\n{'OK' if not failures else f'{len(failures)} FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
