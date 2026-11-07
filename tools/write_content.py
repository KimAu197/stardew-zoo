"""Write [CP] Stardew Zoo/content.json from the approved design."""

import json
from pathlib import Path

from PIL import Image

from animal_sizes import CLIMBERS, FLIERS, SWIMMERS, frame
from draw_furniture import content_changes as furniture_changes
from zoo_layout import HAY

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "[CP] Stardew Zoo" / "assets"
ANIMALS = [
    # name, purchase (half shop), shop, days; sprite sizes come from animal_sizes.py
    ("Penguin", 1500, 3000, 3),
    ("Panda", 3000, 6000, 5),
    ("Lion", 4000, 8000, 5),
    ("Giraffe", 5000, 10000, 5),
    ("Monkey", 2000, 4000, 3),
    ("Capybara", 2500, 5000, 5),
    ("Elephant", 7500, 15000, 5),
    ("Dinosaur", 10000, 20000, 5),
    ("Gorilla", 6000, 12000, 5),
    ("Raccoon", 1250, 2500, 3),
    ("Alpaca", 2250, 4500, 5),
    ("SeaLion", 3500, 7000, 5),
    ("Bear", 4500, 9000, 5),
    ("Flamingo", 2750, 5500, 5),
    ("Owl", 2250, 4500, 3),
    ("Deer", 3000, 6000, 5),
    ("NightHeron", 2500, 5000, 5),
]


def texture_names(name):
    names = [name, f"Baby{name}", f"{name}Shop"]
    if name in FLIERS:
        names.append(f"{name}Fly")
    if name in CLIMBERS:
        names.append(f"{name}Climb")
    return names


def content_box(sheet, index, size):
    """Bounding box (left, top, right, bottom) of frame `index` in a 4-column sheet, in frame pixels."""
    x, y = (index % 4) * size, (index // 4) * size
    return sheet.crop((x, y, x + size, y + size)).getbbox()


def tiles(pixels):
    """Pixels to a pet-hitbox tile size, rounded to quarter tiles, at least one tile."""
    return max(1.0, round(pixels / 16 * 4) / 4)


def sprite_metrics(name):
    """Emote offset, pet hitboxes, and shadow scales measured from the rendered sheets."""
    size = frame(name)
    adult = Image.open(ASSETS / f"{name}.png")
    baby = Image.open(ASSETS / f"Baby{name}.png")
    a_front, a_side = content_box(adult, 0, size), content_box(adult, 4, size)
    b_front, b_side = content_box(baby, 0, size), content_box(baby, 4, size)

    def hitbox(box):
        return f"{tiles(box[2] - box[0]):g}, {tiles(box[3] - box[1]):g}"

    def shadow(box):
        # Game1.shadowTexture is 12px wide; aim for ~60% of the body's width.
        return round(max(1.5, (box[2] - box[0]) * 0.6 / 3), 1)

    top = min(a_front[1], a_side[1])
    return {
        # the emote's bottom edge sits 8px (screen) into the top of the drawing
        "EmoteOffset": {"X": 0, "Y": top * 4 - 16},
        "UpDownPetHitboxTileSize": hitbox(a_front),
        "LeftRightPetHitboxTileSize": hitbox(a_side),
        "BabyUpDownPetHitboxTileSize": hitbox(b_front),
        "BabyLeftRightPetHitboxTileSize": hitbox(b_side),
        "Shadow": {"Visible": True, "Scale": shadow(a_front)},
        "ShadowWhenBaby": {"Visible": True, "Scale": shadow(b_front)},
    }


def animal_entry(name, purchase, days):
    size = frame(name)
    large = size >= 32
    entry = {
        "DisplayName": f"{{{{i18n:animal.{name}.name}}}}",
        "House": "StardewZoo.Zoo",
        "Gender": "MaleOrFemale",
        "PurchasePrice": purchase,
        "SellPrice": purchase,
        "ShopTexture": f"Mods/StardewZoo/{name}Shop",
        "ShopSourceRect": {"X": 0, "Y": 0, "Width": 32, "Height": 16},
        "ShopDescription": f"{{{{i18n:animal.{name}.description}}}}",
        "ShopMissingBuildingDescription": "{{i18n:animal.missing-building}}",
        "RequiredBuilding": "StardewZoo.Zoo",
        "DaysToMature": days,
        "CanGetPregnant": False,
        "HarvestType": "DropOvernight",
        "ProduceItemIds": [],
        "DeluxeProduceItemIds": [],
        "CanEatGoldenCrackers": False,
        "ProfessionForHappinessBoost": 3,
        "ProfessionForQualityBoost": 3,
        "Sound": f"StardewZoo_{name}",
        "Texture": f"Mods/StardewZoo/{name}",
        "BabyTexture": f"Mods/StardewZoo/Baby{name}",
        "UseFlippedRightForLeft": True,
        "UseDoubleUniqueAnimationFrames": False,
        "SpriteWidth": size,
        "SpriteHeight": size,
        "SleepFrame": 12,
        "GrassEatAmount": 4 if large else 2,
        "HappinessDrain": 6 if large else 7,
        "ShowInSummitCredits": False,
    }
    entry.update(sprite_metrics(name))
    if name in SWIMMERS:
        # rows 5-9 are the same frames sunk into the water; the mod sets isSwimming on pond tiles
        entry["SwimOffset"] = {"X": 0, "Y": 5 * size}
        entry["ShadowWhenAdultSwims"] = {"Visible": False}
        entry["ShadowWhenBabySwims"] = {"Visible": False}
    return entry


def building(tier):
    names = ["Zoo", "BigZoo", "DeluxeZoo"]
    costs = [5000, 10000, 17500]
    wood = [200, 250, 325]
    stone = [100, 125, 175]
    cap = [8, 16, 24]
    name = names[tier]
    data = {
        "Name": f"{{{{i18n:building.{name}.name}}}}",
        "Description": f"{{{{i18n:building.{name}.description}}}}",
        "Texture": f"Mods/StardewZoo/{name}",
        "UpgradeSignTile": "3, 2",
        "UpgradeSignHeight": 40.0,
        "Size": {"X": 7, "Y": 4},
        "SourceRect": {"X": 0, "Y": 0, "Width": 112, "Height": 128},
        "Builder": "Robin",
        "BuildDays": 0,
        "BuildCost": costs[tier],
        "BuildMaterials": [
            {"ItemId": "(O)388", "Amount": wood[tier]},
            {"ItemId": "(O)390", "Amount": stone[tier]},
        ],
        "HumanDoor": {"X": 1, "Y": 3},
        "IndoorMap": "StardewZoo",
        "IndoorMapType": "StardewValley.AnimalHouse",
        "MaxOccupants": cap[tier],
        "HayCapacity": cap[tier] * 2,
        "ValidOccupantTypes": ["StardewZoo.Zoo"],
        "AllowAnimalPregnancy": False,
        "IndoorItems": [
            {"Id": "Default_FeedHopper", "ItemId": "(BC)99", "Tile": {"X": HAY[0], "Y": HAY[1]}, "Indestructible": True, "ClearTile": True}
        ],
    }
    if name != "Zoo":
        data["NameForGeneralType"] = "{{i18n:building.Zoo.name}}"
        data["BuildingToUpgrade"] = "StardewZoo." + names[tier - 1]
    return data


def main():
    animal_targets = []
    for name, *_ in ANIMALS:
        animal_targets += [f"Mods/StardewZoo/{texture}" for texture in texture_names(name)]
    content = {
        "Format": "2.9.0",
        "Changes": [
            {
                "LogName": "Zoo textures",
                "Action": "Load",
                "Target": ", ".join(
                    ["Mods/StardewZoo/Zoo", "Mods/StardewZoo/BigZoo", "Mods/StardewZoo/DeluxeZoo"] + animal_targets
                ),
                "FromFile": "assets/{{TargetWithoutPath}}.png",
            },
            {
                "LogName": "Zoo snowy roofs",
                "Action": "EditImage",
                "Target": "Mods/StardewZoo/Zoo, Mods/StardewZoo/BigZoo, Mods/StardewZoo/DeluxeZoo",
                "FromFile": "assets/{{TargetWithoutPath}}_winter.png",
                "PatchMode": "Replace",
                "When": {"Season": "winter"},
            },
            {
                "LogName": "Zoo tilesheet",
                "Action": "Load",
                "Target": "Maps/zoo_tiles",
                "FromFile": "assets/zoo_tiles.png",
            },
            {
                "LogName": "Zoo interior map",
                "Action": "Load",
                "Target": "Maps/StardewZoo",
                "FromFile": "assets/StardewZoo.tmx",
            },
            {
                "LogName": "Zoo buildings",
                "Action": "EditData",
                "Target": "Data/Buildings",
                "Entries": {
                    "StardewZoo.Zoo": building(0),
                    "StardewZoo.BigZoo": building(1),
                    "StardewZoo.DeluxeZoo": building(2),
                },
            },
            {
                "LogName": "Zoo animals",
                "Action": "EditData",
                "Target": "Data/FarmAnimals",
                "Entries": {
                    f"StardewZoo.{name}": animal_entry(name, purchase, days)
                    for name, purchase, shop, days in ANIMALS
                },
            },
            *furniture_changes(),
        ],
    }
    path = ROOT / "[CP] Stardew Zoo" / "content.json"
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
