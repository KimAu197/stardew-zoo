# Stardew Zoo — Design (operations update)

Date: 2026-11-07
Target: Stardew Valley 1.6.15, SMAPI 4.5.2, Content Patcher 2.9.1 (format `2.9.0`)

## Goal

A walk-in zoo on the farm with custom interior and exterior art, biome habitats,
ticketed visitors, reviews, a recording studio for animal sounds, and daily
income of `visitors × ticket price`.

## Architecture

| Package | Kind | Responsibility |
|---|---|---|
| `[CP] Stardew Zoo` | Content Patcher pack | Buildings, animals, map, tiles, visitor sprites, i18n |
| `StardewZoo` | SMAPI C# mod (.NET 6, no Harmony) | Economy, visitors, habitats, recording, HUD, `zoo_status` |

Shared IDs: `StardewZoo.Zoo` / `BigZoo` / `DeluxeZoo` buildings; animal house type `StardewZoo.Zoo`; animals `StardewZoo.{Name}`.

## Buildings

Three Robin-built tiers, 7×4 footprint, 112×128 exterior with a ZOO sign. No animal door (animals stay inside). Same custom interior map `Maps/StardewZoo` for every tier (`IndoorMapType` = `StardewValley.AnimalHouse`). Capacities 8 / 16 / 24. `BuildDays` 0. Hay autofilled in C#. Existing saves that still point at `Barn*` interiors are force-reloaded onto the new map.

## Interior map

~38×30 custom TMX, tilesheet `Maps/zoo_tiles` (not barn/farm). Six fenced biome pens around a walkable loop, plaza in the center:

| Habitat | Animals |
|---|---|
| Ice 冰原 | Penguin |
| Water 水域 | SeaLion, Capybara |
| Savanna 草原 | Lion, Giraffe, Elephant, Alpaca |
| Jungle 丛林 | Monkey, Gorilla, Panda |
| Forest 森林 | Bear, Raccoon |
| Prehistoric 史前 | Dinosaur |

Plaza: ticket booth, review board, recording studio. Warp at the south entrance. Empty pens still exist and look empty. Fences on the Buildings layer block walking; C# warps animals back if they leave their rect.

## Animals

Sold at Marnie's. `House` / `RequiredBuilding` = `StardewZoo.Zoo`. No produce. `PurchasePrice` is half the shop price. Sheets use `UseFlippedRightForLeft` true, `UseDoubleUniqueAnimationFrames` false, `SleepFrame` 12. Large 32×32 / 128×160; small 16×16 / 64×80. Sound cue `StardewZoo_{Name}`.

Shop / data: Penguin 3000/1500, Panda 6000/3000, Lion 8000/4000, Giraffe 10000/5000, Monkey 4000/2000, Capybara 5000/2500, Elephant 15000/7500, Dinosaur 20000/10000, Gorilla 12000/6000, Raccoon 2500/1250, Alpaca 4500/2250, SeaLion 7000/3500, Bear 9000/4500.

## Economy (pure C#, unit-tested)

Fair value from animal count, distinct species, filled habitats, and building tier. Demand from fair value, ticket vs fair, and rolling average review rating (starts at 3.0). Visitors ~ demand with light seedable noise. Income = visitors × ticketPrice (0 ticket = many visitors, 0 gold). A sample of visitors leave 1–5 star reviews with i18n flavor about price/animals/habitats. Last ~12 reviews stored via `Helper.Data.WriteSaveData`. High price + few animals → bad reviews → fewer visitors tomorrow.

Ticket price 0–1000g set at the in-zoo booth (`NumberSelectionMenu`), persisted in `ModConfig`.

## Visitors

Temporary NPCs (not town NPCs, not serialized). Spawn in the day, walk the loop, leave, removed at night and before save. 4 visitor sheets at 16×32.

## Recording

Studio tile (and menu): pick animal, Record ~2.5s, Preview, Reset to default. WAV saved under the C# mod `sounds/{Animal}.wav` and registered as `CueDefinition` `StardewZoo_{Animal}`. Mac capture: ffmpeg avfoundation `:0`, else sox `rec`, else OpenAL `Microphone`; else open the sounds folder for a manual drop. File-drop overwrites and reloads the cue. Custom recordings listed in save data. Default synthesized WAVs ship with the mod.

## HUD / command

Morning HUD: yesterday visitors, income, average rating. `zoo_status` also prints ticket price, rating, and projected visitors.
