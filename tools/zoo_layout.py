"""Shared zoo interior layout. Keep in sync with StardewZoo/ZooHabitats.cs."""

MAP_W = 38
MAP_H = 30

# Animal-walkable interiors (x, y, w, h). Fences occupy the 1-tile border outside.
HABITATS = {
    "Ice": (3, 3, 9, 6),
    "Water": (26, 3, 9, 6),
    "Savanna": (3, 13, 9, 6),
    "Jungle": (26, 13, 9, 6),
    "Forest": (3, 23, 9, 3),
    "Prehistoric": (26, 23, 9, 3),
}

PLAZA = (16, 13, 6, 6)
BOOTH = (17, 14)
BOARD = (19, 14)
STUDIO = (18, 16)
HAY = (21, 17)
WARP_TILES = ((18, 30), (19, 30))
ENTRANCE = (18, 28)

VISITOR_LOOP = [
    (18, 28), (1, 28), (1, 21), (1, 11), (1, 1),
    (7, 1), (18, 1), (30, 1), (36, 1),
    (36, 11), (30, 11), (18, 11), (7, 11),
    (7, 21), (18, 21), (30, 21), (36, 21), (36, 28),
    (18, 28),
]
