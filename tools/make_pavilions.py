"""Place the walk-in pavilions: park facades and the four interior regions of the zoo map.

Each interior is a closed hall (shell art on Buildings), a walkway ring of themed floor
left open for the player's furniture, and a railed exhibit pen in the middle. Pens never get Buildings tiles (HabitatKeeper
drops animals on any pen tile), so exhibit props live on Back / Front / AlwaysFront.
"""

from zoo_layout import FACADES, REGIONS, ZOO_PERCHES, barrier, facade_door, inside_door, pavilion_pen

FLOOR = {"Ice": "a", "Water": "b", "Jungle": "e", "Prehistoric": "f"}
PEN_BASE = {"Ice": "n", "Water": "s", "Jungle": "k", "Prehistoric": "v"}


def cells(t):
    """Terrain letters for the interiors (walls sit on walkway floor; the railing ring on pen ground)."""
    for name, (x, y, w, h) in REGIONS.items():
        for cy in range(y, y + h):
            for cx in range(x, x + w):
                t[cy][cx] = FLOOR[name]
        bx, by, bw, bh = barrier(name)
        for cy in range(by, by + bh):
            for cx in range(bx, bx + bw):
                t[cy][cx] = PEN_BASE[name]


def paint(V, blob):
    # Ice: frozen sheet with an open pool for swimming laps.
    blob(V, "Ice", 83.0, 16.2, 5.6, 2.7, "i", 21)
    blob(V, "Ice", 84.2, 16.3, 4.2, 2.1, "w", 22)
    # Aquarium: sand beach -> wide shallow wading shelf -> deep animated pool.
    blob(V, "Water", 142.5, 16.4, 8.0, 4.2, "h", 23)
    blob(V, "Water", 144.2, 16.2, 5.6, 3.0, "w", 24)
    # Greenhouse: dark jungle floor, mud, a trickling stream into a little pool.
    blob(V, "Jungle", 197.5, 17.6, 2.3, 1.3, "h", 26)
    blob(V, "Jungle", 197.5, 17.7, 1.4, 0.8, "w", 27)
    for i, (sx, sy) in enumerate(((199.6, 16.4), (201.0, 15.3), (202.2, 14.2), (203.0, 13.2))):
        blob(V, "Jungle", sx, sy, 1.1, 0.8, "h", 28 + i)
    blob(V, "Jungle", 204.6, 18.4, 1.9, 1.0, "m", 33)
    blob(V, "Jungle", 194.0, 13.6, 1.4, 0.8, "m", 34)
    # Prehistoric: volcanic ground with cracked baked earth.
    blob(V, "Prehistoric", 254.0, 16.6, 2.6, 1.3, "c", 35)
    blob(V, "Prehistoric", 260.6, 15.0, 1.9, 1.0, "c", 36)


def facades(m):
    """Facade art on Buildings (solid across the whole footprint); the door tile goes on Back."""
    blank = ("zoo", m.zs.blank)
    for name, (x, y, w, h) in FACADES.items():
        grid = m.zs.objects[f"facade_{name}"]
        door = facade_door(name)
        for r in range(h):
            for c in range(w):
                tid = grid[r][c]
                tile = ("zoo", tid) if tid is not None else blank
                if (x + c, y + r) == door:
                    m.put("Back", x + c, y + r, tile)
                else:
                    m.put("Buildings", x + c, y + r, tile)
                m.used.add((x + c, y + r))


def _shell(m, name):
    x, y, w, h = REGIONS[name]
    grid = m.zs.objects[f"shell_{name}"]
    door = inside_door(name)
    for r in range(h):
        for c in range(w):
            tid = grid[r][c]
            if tid is None:
                continue
            m.put("Back" if (x + c, y + r) == door else "Buildings", x + c, y + r, ("zoo", tid))
            m.used.add((x + c, y + r))


def _rails(m, name):
    bx, by, bw, bh = barrier(name)
    plaque_x = bx + bw // 2
    for cx in range(bx, bx + bw):
        for cy in range(by, by + bh):
            top, bottom, left, right = cy == by, cy == by + bh - 1, cx == bx, cx == bx + bw - 1
            if not (top or bottom or left or right):
                continue
            kind = ("T" if top else "B" if bottom else "") + ("L" if left else "R" if right else "")
            if bottom and cx == plaque_x:
                kind = "plaque"
            m.put("Buildings", cx, cy, m.tid(f"rail_{name}_{kind}"))
            m.used.add((cx, cy))


def _exhibit_ice(m, rng, scatter, allin):
    x, y, w, h = pavilion_pen("Ice")
    m.obj("igloo", x + 1, y, ["Front", "Back"])
    m.obj("ice_pillar", x + 12, y, ["Front", "Back"])
    m.obj("ice_pillar", x + 3, y + 3, ["Front", "Back"])
    m.obj("icy_rock", x + 8, y + 3, "Back")
    m.obj("icy_rock", x + 6, y + 2, "Back")
    m.obj("ice_block", x + 4, y, "Back")
    m.obj("ice_block", x + 11, y + 5, "Back")
    m.obj("ice_block", x, y + 5, "Back")
    scatter(m, rng, "Ice", ["snow_drift", "snow_drift", "ice_block"], 6, allin("n"))
    scatter(m, rng, "Ice", ["ice_crack"], 4, allin("i"))
    spots = [(x + c, y + r) for r in range(h) for c in range(w)]
    rng.shuffle(spots)
    for sx, sy in spots[:14]:
        m.put("AlwaysFront", sx, sy, m.tid("snowfall"))


def _exhibit_water(m, rng, scatter, allin):
    x, y, w, h = pavilion_pen("Water")
    m.obj("basking_rock", x + 12, y + 3, "Back")
    m.obj("water_rock", x + 15, y + 6, "Back")
    m.obj("water_rock", x + 9, y + 2, "Back")
    m.obj("reeds", x + 1, y, ["Front", "Back"])
    m.obj("reeds", x + 17, y, ["Front", "Back"])
    m.obj("reeds", x + 3, y + 6, ["Front", "Back"])
    m.obj("reeds", x + 17, y + 7, ["Front", "Back"])
    scatter(m, rng, "Water", ["lily", "lily_flower"], 5, lambda cs: "w" in cs and any(c != "w" for c in cs))
    scatter(m, rng, "Water", ["grass_tuft"], 6, allin("s"))


def _exhibit_jungle(m, rng, scatter, allin, ferns, island):
    x, y, w, h = pavilion_pen("Jungle")
    for px, py in ZOO_PERCHES["Jungle"]:
        m.palm(px, py, vines=True)
    for i, (bx, by) in enumerate(((x + 13, y + 7), (x + 14, y + 6), (x + 15, y + 7), (x + 15, y + 4), (x, y + 7))):
        m.obj(f"bamboo_{i % 3 + 1}", bx, by - 2, ["Front", "Front", "Back"])
    for fx, fy in ((x + 1, y), (x + 8, y), (x + 4, y + 7), (x + 11, y + 1), (x + 9, y + 7)):
        if (fx, fy) not in m.used:
            m.put("Back", fx, fy, island(ferns[(fx + fy) % 2]))
            m.used.add((fx, fy))
    scatter(m, rng, "Jungle", ["litter_a", "litter_b", "vine", "tropical_flower", "tropical_flower"], 12, allin("k", "m"))


def _exhibit_prehistoric(m, rng, scatter, allin):
    x, y, w, h = pavilion_pen("Prehistoric")
    m.obj("giant_fern", x, y, ["Front", "Back"])
    m.obj("giant_fern", x + 11, y, ["Front", "Back"])
    m.obj("giant_fern", x + 12, y + 4, ["Front", "Back"])
    m.obj("vent", x + 7, y, ["Front", "Back"])
    m.obj("vent", x + 2, y + 3, ["Front", "Back"])
    m.obj("lava_pool", x + 8, y + 4, "Back")
    m.obj("fossil_dig", x + 4, y + 2, "Back")
    m.obj("ribcage", x + 10, y + 2, "Back")
    m.obj("skull", x + 13, y + 3, "Back")
    m.obj("bone", x + 6, y + 5, "Back")
    scatter(m, rng, "Prehistoric", ["volcanic_rock_a", "volcanic_rock_b", "cracks"], 6, allin("v", "c"))


def interiors(m, rng, scatter, ferns, island):
    allin = lambda *ts: (lambda cs: all(c in ts for c in cs))
    for name in REGIONS:
        _shell(m, name)
        _rails(m, name)
    _exhibit_ice(m, rng, scatter, allin)
    _exhibit_water(m, rng, scatter, allin)
    _exhibit_jungle(m, rng, scatter, allin, ferns, island)
    _exhibit_prehistoric(m, rng, scatter, allin)
