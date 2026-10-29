# Stardew Zoo — Design

Date: 2026-10-29
Target: Stardew Valley 1.6, SMAPI 4.x, Content Patcher 2.9.x (all already installed)

## Goal

Let the player build a zoo on the farm, fill it with exotic animals, earn daily
ticket income that grows with animal count and species variety, and expand the
zoo by upgrading the building.

Out of scope for v1: visitors walking around, animal happiness affecting income,
staff/facilities, custom maps, final art, multiple-mod config UI (GMCM).

## Architecture

Two packages, deployed side by side into the game's `Mods` folder:

| Package | Kind | Responsibility |
|---|---|---|
| `[CP] Stardew Zoo` | Content Patcher pack | Building data, animal data, sprites |
| `StardewZoo` | SMAPI C# mod (.NET 6) | Daily income calculation and payout |

The C# mod depends on nothing but SMAPI; it finds zoo buildings by building
type ID, so it is decoupled from the content pack except for shared IDs.

Shared IDs (single source of truth, mirrored as constants in C#):

- Building types: `StardewZoo.Zoo`, `StardewZoo.BigZoo`, `StardewZoo.DeluxeZoo`
- Animal house type: `StardewZoo.Zoo`
- Animal types: `StardewZoo.Penguin`, `StardewZoo.Panda`, `StardewZoo.Lion`, `StardewZoo.Giraffe`

## Project layout

```
stardew_valley/
├── [CP] Stardew Zoo/
│   ├── manifest.json
│   ├── content.json
│   └── assets/animals/<Animal>.png, <Animal>_shop.png
├── StardewZoo/
│   ├── StardewZoo.csproj
│   ├── manifest.json
│   ├── ModEntry.cs
│   ├── ZooIncome.cs
│   └── ModConfig.cs
├── StardewZoo.Tests/
├── tools/make_sprites.py
└── deploy.sh
```

## Component: zoo building (content pack, `Data/Buildings`)

Three tiers, each an upgrade of the previous (built and upgraded by Robin):

| Building | Upgrades from | Capacity | Interior map | Income multiplier |
|---|---|---|---|---|
| Zoo | — | 8 | vanilla `Barn` | 1.0 |
| Big Zoo | Zoo | 12 | vanilla `Barn2` | 1.5 |
| Deluxe Zoo | Big Zoo | 16 | vanilla `Barn3` | 2.0 |

- Exterior texture reuses the vanilla barn sprites as a placeholder.
- `ValidOccupantTypes` contains only `StardewZoo.Zoo`, so only zoo animals live there.
- Build costs (gold + materials) are set to mirror the barn progression scaled
  up (Zoo ≈ 10,000g, Big Zoo ≈ 20,000g, Deluxe Zoo ≈ 35,000g plus wood/stone).
- Capacity is the building's `MaxOccupants`; the income multiplier lives in the
  C# config keyed by building ID (data files have no field for it).

## Component: exotic animals (content pack, `Data/FarmAnimals`)

| Animal | Price | Size |
|---|---|---|
| Penguin | 3,000g | small (16×16 frames) |
| Panda | 6,000g | large (32×32 frames) |
| Lion | 8,000g | large |
| Giraffe | 10,000g | large |

- `House` = `StardewZoo.Zoo`; sold at Marnie's, shown only once the player owns
  a zoo (exact unlock mechanism confirmed from `StardewValley.GameData.xml`
  during implementation).
- No produce.
- Sprite sheets follow the vanilla farm-animal sheet layout so swapping in final
  art is a drop-in PNG replacement.

## Component: placeholder sprites (`tools/make_sprites.py`)

Generates each animal's sprite sheet and shop icon as simple pixel shapes in
distinct colors, in the exact layout the game expects. Re-runnable; output is
committed under `assets/animals/`.

## Component: ticket income (C# mod)

`ZooIncome` is a pure function, no game types:

```
input:  list of zoos, each = (multiplier, animal type IDs inside)
output: per-zoo and total income, visitor count

zoo income = (animalCount × PricePerAnimal + distinctSpecies × PricePerSpecies) × multiplier
visitors   = total income / TicketPrice (rounded down)
```

Defaults in `ModConfig` (written to `config.json`): `PricePerAnimal` = 50,
`PricePerSpecies` = 200, `TicketPrice` = 50, multipliers per building ID as
above.

`ModEntry` wiring:

- `GameLoop.DayEnding` (main player only): scan farm buildings whose type is a
  zoo ID, collect animal type IDs from each building's interior, compute
  income, add to `Game1.player.Money` (shared team money), remember the result.
- `GameLoop.DayStarted`: if yesterday paid out > 0, show a HUD message:
  "Yesterday N visitors came to the zoo, ticket income Xg."
- Console command `zoo_status`: prints each zoo, its animals, and projected income.

## Error handling

- No zoos or empty zoos: income 0, no message.
- Unknown building ID in config: multiplier defaults to 1.0.
- Farmhands in multiplayer: mod does nothing (host pays shared money once).
- Missing content pack: C# mod simply finds no zoos; logs nothing noisy.

## Testing

- Unit tests (xUnit) for `ZooIncome`: empty, single zoo, species bonus,
  multiplier, multiple zoos, visitor rounding.
- Build verification: both packages load in SMAPI with no errors/warnings
  (check SMAPI log).
- In-game check: build Zoo, buy an animal at Marnie's, sleep, confirm money and
  HUD message; upgrade path visible at Robin's; `zoo_status` output matches.

## Environment prerequisites

- .NET 6 SDK installed per-user to `~/.dotnet` (not currently installed).
- Python 3 with Pillow for the sprite generator.

## Known risks

- Exact 1.6 data field names/semantics must be confirmed against
  `StardewValley.GameData.xml` in the game folder.
- Removing the mod from a save with zoos leaves invalid buildings/animals
  (same as any mod adding buildings).
