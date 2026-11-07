"""Shared zoo interior layout: the single source of truth for the map and the C# mod.

`python3 tools/zoo_layout.py` (also run by make_map.py) writes StardewZoo/ZooLayout.g.cs,
and validate_map.py fails if that file is stale.

The interior is one AnimalHouse map split into isolated regions: the open-air park
(OUTDOOR) plus four walk-in pavilions far to the east, separated by void. A pavilion
door on the park warps the player within the same location to the pavilion's region.
"""

from pathlib import Path

MAP_W = 268
MAP_H = 30

OUTDOOR = (0, 0, 38, 30)

# Open-air pens in the park (x, y, w, h): animal-walkable interiors, fences on the 1-tile border.
OPEN_PENS = {
    "Savanna": (3, 13, 9, 6),
    "Forest": (3, 23, 9, 3),
}

# Pavilion facades on the park: footprint (x, y, w, h); the door is the bottom-centre tile.
FACADES = {
    "Ice": (3, 2, 9, 8),
    "Water": (25, 2, 11, 8),
    "Jungle": (25, 12, 11, 8),
    "Prehistoric": (25, 22, 11, 5),
}

# Pavilion interiors (x, y, w, h), each a closed hall: row 0 wall cap, rows 1-3 back wall,
# a 2-tile walkway ring around a railed exhibit, and the exit door in the bottom wall.
REGIONS = {
    "Ice": (72, 6, 22, 17),
    "Water": (128, 5, 26, 20),
    "Jungle": (188, 5, 24, 19),
    "Prehistoric": (246, 6, 22, 17),
}
PAVILIONS = tuple(REGIONS)
WALL_ROWS = 4      # cap + 3 rows of wall face
WALKWAY = 2        # walkway ring width


def facade_door(name):
    x, y, w, h = FACADES[name]
    return (x + w // 2, y + h - 1)


def barrier(name):
    """Railing ring around the exhibit (x, y, w, h)."""
    x, y, w, h = REGIONS[name]
    return (x + 1 + WALKWAY, y + WALL_ROWS + WALKWAY, w - 2 - 2 * WALKWAY, h - WALL_ROWS - 1 - 2 * WALKWAY)


def pavilion_pen(name):
    bx, by, bw, bh = barrier(name)
    return (bx + 1, by + 1, bw - 2, bh - 2)


def inside_door(name):
    x, y, w, h = REGIONS[name]
    return (x + w // 2, y + h - 1)


def inside_arrival(name):
    dx, dy = inside_door(name)
    return (dx, dy - 1)


def outside_arrival(name):
    dx, dy = facade_door(name)
    return (dx, dy + 1)


def inner_loop(name):
    """Walkway corners visitors tour, clockwise from the entrance."""
    x, y, w, h = REGIONS[name]
    ax, ay = inside_arrival(name)
    top, bottom = y + WALL_ROWS + 1, y + h - 3
    left, right = x + 2, x + w - 3
    return [(ax, ay), (ax + 1, bottom), (right, bottom), (right, top), (left, top), (left, bottom), (ax - 1, bottom), (ax, ay)]


HABITATS = dict(OPEN_PENS)
HABITATS.update({name: pavilion_pen(name) for name in PAVILIONS})
HABITATS = {k: HABITATS[k] for k in ("Ice", "Water", "Savanna", "Jungle", "Forest", "Prehistoric")}

# Tree bases tagged with the ZooPerch Back-tile property (value = perch height in tiles).
_jx, _jy, _jw, _jh = pavilion_pen("Jungle")
ZOO_PERCHES = {
    "Jungle": ((_jx + 2, _jy + 3), (_jx + 7, _jy + 2), (_jx + 13, _jy + 3), (_jx + 10, _jy + 6)),
    "Forest": ((4, 25), (10, 25), (7, 24)),
}

# The exit warps sit on the gate tiles in the bottom hedge row. Vanilla drops a player entering a building one tile above
# warps[0], so the player arrives on the loop path (ENTRANCE) rather than in the hedge row with hedges on both sides.
WARP_TILES = ((18, 29), (19, 29))
ENTRANCE = (18, 28)
PRODUCE_AREA = (13, 13, 2, 5)

# Multi-tile props are placed by their top-left tile; the Action tile is on the bottom (counter) row.
# The ticket booth stands on the lawn just right of the centre avenue, its counter facing the gate across a paved
# queue apron, so it's the first thing a player sees on arrival. Board and studio stay on the plaza's north edge.
BOOTH_ORIGIN = (20, 23)          # 3x4
BOOTH = (21, 26)
BOOTH_APRON = (20, 27, 3, 1)     # where visitors queue and the player stands to buy tickets
BOOTH_FRONT = (21, 27)
BOARD_ORIGIN = (15, 11)          # 3x4
BOARD = (16, 14)
STUDIO_ORIGIN = (21, 13)         # 2x2, with a speaker on its left and a mic on its right
STUDIO = (21, 14)
HAY = (21, 17)

# Park paths (x, y, w, h): the loop (four rows joined by the side columns) must stay clear end to end; the centre
# avenue, plaza and booth apron are open paving; door spurs connect each facade door to the loop.
LOOP_PATHS = [(1, 1, 36, 1), (1, 11, 36, 1), (1, 21, 36, 1), (1, 28, 36, 1), (1, 1, 1, 28), (36, 1, 1, 28)]
PATHS = (LOOP_PATHS + [(18, 1, 2, 29), (14, 12, 10, 9), BOOTH_APRON]
         + [(outside_arrival(n)[0], outside_arrival(n)[1], 1, 1) for n in PAVILIONS])


def _visit(name):
    """Walk to the door, step in, tour the walkway ring, step out."""
    door, arrive = facade_door(name), outside_arrival(name)
    steps = [("walk", arrive), ("walk", door), ("teleport", inside_arrival(name))]
    steps += [("walk", p) for p in inner_loop(name)[1:]]
    steps += [("walk", inside_door(name)), ("teleport", arrive)]
    return steps


def _walk(*pts):
    return [("walk", p) for p in pts]


VISITOR_ROUTE = (
    [("walk", ENTRANCE)]
    + _walk(BOOTH_FRONT, (1, 28), (1, 21), (1, 11), (1, 1), (18, 1), (36, 1), (36, 11), (30, 11))
    + _visit("Water")
    + _walk((18, 11), (7, 11))
    + _visit("Ice")
    + _walk((7, 21), (18, 21), (30, 21))
    + _visit("Jungle")
    + _walk((36, 21), (36, 28), (30, 28))
    + _visit("Prehistoric")
    + _walk(ENTRANCE)
)


def region_of(x, y):
    for name, (rx, ry, rw, rh) in [("Outdoor", OUTDOOR)] + list(REGIONS.items()):
        if rx <= x < rx + rw and ry <= y < ry + rh:
            return name
    return None


# ---------------------------------------------------------------------------
# C# emission
# ---------------------------------------------------------------------------

CS_PATH = Path(__file__).resolve().parent.parent / "StardewZoo" / "ZooLayout.g.cs"


def _rect(r):
    return f"new({r[0]}, {r[1]}, {r[2]}, {r[3]})"


def _pt(p):
    return f"({p[0]}, {p[1]})"


def csharp():
    pens = "\n".join(f'    public static readonly HabitatRect {k}Pen = new("{k}", {v[0]}, {v[1]}, {v[2]}, {v[3]});'
                     for k, v in HABITATS.items())
    pavs = ",\n".join(
        f'        new("{n}", Region: {_rect(REGIONS[n])}, Facade: {_rect(FACADES[n])}, OutsideDoor: {_pt(facade_door(n))}, '
        f'OutsideArrival: {_pt(outside_arrival(n))}, InsideDoor: {_pt(inside_door(n))}, InsideArrival: {_pt(inside_arrival(n))}, '
        f'Barrier: {_rect(barrier(n))})'
        for n in PAVILIONS)
    route = ",\n".join(f"        new({x}, {y}, {'true' if kind == 'teleport' else 'false'})" for kind, (x, y) in VISITOR_ROUTE)
    paths = ", ".join(_rect(p) for p in PATHS)
    return f"""// <auto-generated>
// Generated by tools/zoo_layout.py. Do not edit; change the Python layout and rerun it.
// </auto-generated>
namespace StardewZoo;

public static partial class ZooLayout
{{
    public const int MapWidth = {MAP_W};
    public const int MapHeight = {MAP_H};

    public static readonly ZooRect Outdoor = {_rect(OUTDOOR)};
    public static readonly (int X, int Y) Entrance = {_pt(ENTRANCE)};

{pens}

    public static readonly IReadOnlyList<PavilionInfo> Pavilions = new PavilionInfo[]
    {{
{pavs}
    }};

    /// <summary>Visitor tour: walk between tiles in one region; teleport steps go through a pavilion door.</summary>
    public static readonly IReadOnlyList<VisitorStep> VisitorRoute = new VisitorStep[]
    {{
{route}
    }};

    /// <summary>Park paths and door spurs (pavilion walkways are <see cref="PavilionInfo.Walkway"/>).</summary>
    public static readonly IReadOnlyList<ZooRect> ParkPaths = new ZooRect[] {{ {paths} }};
}}
"""


def write_csharp():
    text = csharp()
    if not CS_PATH.exists() or CS_PATH.read_text() != text:
        CS_PATH.write_text(text)
    return CS_PATH


if __name__ == "__main__":
    print(f"Wrote {write_csharp()}")
