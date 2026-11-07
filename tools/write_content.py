"""Write [CP] Stardew Zoo/content.json from the approved design."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANIMALS = [
    # name, purchase (half shop), shop, size, days
    ("Penguin", 1500, 3000, 16, 3),
    ("Panda", 3000, 6000, 32, 5),
    ("Lion", 4000, 8000, 32, 5),
    ("Giraffe", 5000, 10000, 32, 5),
    ("Monkey", 2000, 4000, 16, 3),
    ("Capybara", 2500, 5000, 32, 5),
    ("Elephant", 7500, 15000, 32, 5),
    ("Dinosaur", 10000, 20000, 32, 5),
    ("Gorilla", 6000, 12000, 32, 5),
    ("Raccoon", 1250, 2500, 16, 3),
    ("Alpaca", 2250, 4500, 32, 5),
    ("SeaLion", 3500, 7000, 32, 5),
    ("Bear", 4500, 9000, 32, 5),
    ("Flamingo", 2750, 5500, 32, 5),
    ("Owl", 2250, 4500, 16, 3),
    ("Deer", 3000, 6000, 32, 5),
    ("NightHeron", 2500, 5000, 32, 5),
]

TEXTURES = [
    "Zoo", "BigZoo", "DeluxeZoo", "zoo_tiles",
    "Visitor0", "Visitor1", "Visitor2", "Visitor3",
]
for name, *_ in ANIMALS:
    TEXTURES += [name, f"Baby{name}", f"{name}Shop"]


def animal_entry(name, purchase, size, days):
    large = size == 32
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
    if large:
        entry["Shadow"] = {"Visible": False}
        entry["UpDownPetHitboxTileSize"] = "1.5, 1.75"
        entry["LeftRightPetHitboxTileSize"] = "1.75, 1.25"
        entry["BabyUpDownPetHitboxTileSize"] = "1, 1.75"
        entry["BabyLeftRightPetHitboxTileSize"] = "1.75, 1"
    else:
        entry["EmoteOffset"] = {"X": 0, "Y": -16}
        entry["UpDownPetHitboxTileSize"] = "1, 1"
        entry["LeftRightPetHitboxTileSize"] = "1, 1"
        entry["BabyUpDownPetHitboxTileSize"] = "1, 1"
        entry["BabyLeftRightPetHitboxTileSize"] = "1, 1"
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
            {"Id": "Default_FeedHopper", "ItemId": "(BC)99", "Tile": {"X": 21, "Y": 17}, "Indestructible": True, "ClearTile": True}
        ],
    }
    if name != "Zoo":
        data["NameForGeneralType"] = "{{i18n:building.Zoo.name}}"
        data["BuildingToUpgrade"] = "StardewZoo." + names[tier - 1]
    return data


def main():
    animal_targets = []
    for name, *_ in ANIMALS:
        animal_targets += [f"Mods/StardewZoo/{name}", f"Mods/StardewZoo/Baby{name}", f"Mods/StardewZoo/{name}Shop"]
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
                "LogName": "Zoo visitors",
                "Action": "Load",
                "Target": "Characters/StardewZooVisitor0, Characters/StardewZooVisitor1, Characters/StardewZooVisitor2, Characters/StardewZooVisitor3",
                "FromFile": "assets/{{TargetWithoutPath}}.png",
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
                    f"StardewZoo.{name}": animal_entry(name, purchase, size, days)
                    for name, purchase, shop, size, days in ANIMALS
                },
            },
        ],
    }
    path = ROOT / "[CP] Stardew Zoo" / "content.json"
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
