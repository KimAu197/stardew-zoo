"""Proportional sprite sizes for zoo animals, shared by draw_animals.py and write_content.py.

Each animal is drawn in a square design canvas (16 or 32 units) and rendered into a square
frame of FRAME pixels at SCALE output pixels per design unit, feet anchored bottom-centre.
Babies share the adult frame size (the game reads SpriteWidth/SpriteHeight once per animal
type), so a baby is the same drawing rendered at SCALE * BABY inside the same frame.

Scale is compressed from real life so everything stays readable in a 9x6-tile pen:
tiny (owl, raccoon, penguin) < small (heron, monkey, capybara) < medium (deer, alpaca,
flamingo, sea lion, panda) < large (lion, gorilla, bear) < huge (elephant, giraffe, dinosaur).
"""

# name: (design units, frame px, adult scale, baby ratio of adult)
SIZES = {
    "Owl": (16, 16, 0.80, 0.70),
    "Raccoon": (16, 16, 0.90, 0.65),
    "Penguin": (16, 16, 1.00, 0.75),
    "NightHeron": (32, 24, 0.72, 0.60),
    "Monkey": (16, 24, 1.25, 0.60),
    "Capybara": (32, 28, 0.85, 0.60),
    "Flamingo": (32, 36, 1.05, 0.55),
    "Deer": (32, 36, 1.10, 0.55),
    "Alpaca": (32, 36, 1.10, 0.55),
    "SeaLion": (32, 36, 1.10, 0.55),
    "Panda": (32, 36, 1.15, 0.50),
    "Lion": (32, 44, 1.35, 0.55),
    "Gorilla": (32, 44, 1.35, 0.55),
    "Bear": (32, 48, 1.45, 0.50),
    "Elephant": (32, 64, 2.00, 0.55),
    "Giraffe": (32, 72, 2.20, 0.55),
    "Dinosaur": (32, 72, 2.20, 0.55),
}

# Extra sheet rows 5-9: the same frames sunk into water (vanilla SwimOffset / isSwimming).
SWIMMERS = {"SeaLion": "swim", "Capybara": "swim", "Flamingo": "wade", "NightHeron": "wade"}

# {Name}Fly.png: rows fly-down, fly-right, fly-up, perch (4 frames each), adult frame size.
FLIERS = ("Owl", "NightHeron", "Flamingo")

# {Name}Climb.png: rows climb, sit on branch, hang/swing (4 frames each), adult frame size.
CLIMBERS = ("Monkey",)


def frame(name):
    return SIZES[name][1]


def adult_scale(name):
    return SIZES[name][2]


def baby_scale(name):
    return SIZES[name][2] * SIZES[name][3]


def sheet_rows(name):
    return 10 if name in SWIMMERS else 5
