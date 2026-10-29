# Stardew Zoo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Stardew Valley 1.6 mod where Robin builds an upgradable zoo, Marnie sells four exotic animals for it, and the zoo pays daily ticket income based on animal count and species variety.

**Architecture:** A Content Patcher pack (`[CP] Stardew Zoo`) adds the three zoo building tiers to `Data/Buildings`, the four animals to `Data/FarmAnimals`, and loads placeholder textures. A small SMAPI C# mod (`StardewZoo`) scans zoo buildings at day end and pays income; its formula lives in a pure, game-independent class that is unit-tested with xUnit.

**Tech Stack:** C# 10 / .NET 6, SMAPI 4.x, `Pathoschild.Stardew.ModBuildConfig`, xUnit, Content Patcher 2.9 (format `2.9.0`), Python 3 + Pillow.

**Spec:** `docs/superpowers/specs/2026-10-29-stardew-zoo-design.md`

## Global Constraints

- Repo root: `/Users/kenzieluo/Desktop/code/others/stardew_valley` (all relative paths below are from here).
- Game folder (`$GAME`): `/Users/kenzieluo/Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS`
- Unpacked vanilla content: `$GAME/Content (unpacked)` (already produced by StardewXnbHack).
- .NET 6 SDK lives in `~/.dotnet`. Every shell that runs `dotnet` must first run:
  `export DOTNET_ROOT="$HOME/.dotnet" PATH="$HOME/.dotnet:$PATH"`
- Mod target framework: `net6.0` only (the game runs .NET 6).
- Shared IDs (exact strings):
  - Buildings: `StardewZoo.Zoo`, `StardewZoo.BigZoo`, `StardewZoo.DeluxeZoo`
  - Animal house type: `StardewZoo.Zoo`
  - Animals: `StardewZoo.Penguin`, `StardewZoo.Panda`, `StardewZoo.Lion`, `StardewZoo.Giraffe`
- Capacity 8 / 12 / 16; income multipliers 1.0 / 1.5 / 2.0; shop prices 3000 / 6000 / 8000 / 10000 (data `PurchasePrice` = half).
- Income per zoo = round((animals × 50 + distinctSpecies × 200) × multiplier); visitors = total ÷ 50 (floor).
- All player-facing text via i18n with `default.json` (English) and `zh.json` (Chinese).
- The unit-test project must not reference any game or SMAPI assembly (it runs on arm64; the game is x64).

## File Structure

| File | Responsibility |
|---|---|
| `StardewZoo.sln` | Solution containing mod + tests |
| `StardewZoo/ZooIds.cs` | Shared building ID constants (pure) |
| `StardewZoo/ModConfig.cs` | Tunable income settings, serialized to `config.json` (pure) |
| `StardewZoo/ZooIncome.cs` | Pure income formula + result records |
| `StardewZoo/ModEntry.cs` | SMAPI wiring: day-end payout, morning HUD, `zoo_status` command |
| `StardewZoo/StardewZoo.csproj` | Mod project (ModBuildConfig auto-deploys to `Mods/StardewZoo`) |
| `StardewZoo/manifest.json` | SMAPI manifest |
| `StardewZoo/i18n/{default,zh}.json` | HUD/console text |
| `StardewZoo.Tests/StardewZoo.Tests.csproj` | xUnit project linking the three pure files |
| `StardewZoo.Tests/ZooIncomeTests.cs` | Income formula tests |
| `tools/make_sprites.py` | Generates placeholder PNGs from vanilla sprites |
| `[CP] Stardew Zoo/manifest.json` | Content pack manifest |
| `[CP] Stardew Zoo/content.json` | Building + animal data, texture loads |
| `[CP] Stardew Zoo/i18n/{default,zh}.json` | Names/descriptions |
| `[CP] Stardew Zoo/assets/*.png` | Generated placeholder art |
| `deploy.sh` | Builds the C# mod and copies the CP pack into the game |

---

### Task 1: Toolchain + pure income logic (TDD)

**Files:**
- Create: `StardewZoo/ZooIds.cs`, `StardewZoo/ModConfig.cs`, `StardewZoo/ZooIncome.cs`
- Create: `StardewZoo.Tests/StardewZoo.Tests.csproj`, `StardewZoo.Tests/ZooIncomeTests.cs`
- Create: `StardewZoo.sln`

**Interfaces:**
- Produces (namespace `StardewZoo`):
  - `static class ZooIds { const string Zoo, BigZoo, DeluxeZoo; static IReadOnlyList<string> BuildingTypes; static bool IsZoo(string? buildingType) }`
  - `sealed class ModConfig { int PricePerAnimal = 50; int PricePerSpecies = 200; int TicketPrice = 50; Dictionary<string,double> Multipliers }`
  - `record ZooSnapshot(string BuildingType, IReadOnlyList<string> AnimalTypes)`
  - `record ZooResult(string BuildingType, int AnimalCount, int SpeciesCount, int Income)`
  - `record DailyIncome(IReadOnlyList<ZooResult> Zoos, int TotalIncome, int Visitors)`
  - `static class ZooIncome { static DailyIncome Calculate(IEnumerable<ZooSnapshot> zoos, ModConfig config) }`

- [ ] **Step 1: Install the .NET 6 SDK per-user**

```bash
curl -sSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
bash /tmp/dotnet-install.sh --channel 6.0 --install-dir "$HOME/.dotnet"
export DOTNET_ROOT="$HOME/.dotnet" PATH="$HOME/.dotnet:$PATH"
dotnet --list-sdks
```

Expected: a line starting with `6.0.`.

- [ ] **Step 2: Create the pure source files**

`StardewZoo/ZooIds.cs`:

```csharp
namespace StardewZoo;

/// <summary>Building IDs shared with the [CP] Stardew Zoo content pack.</summary>
public static class ZooIds
{
    public const string Zoo = "StardewZoo.Zoo";
    public const string BigZoo = "StardewZoo.BigZoo";
    public const string DeluxeZoo = "StardewZoo.DeluxeZoo";

    public static readonly IReadOnlyList<string> BuildingTypes = new[] { Zoo, BigZoo, DeluxeZoo };

    public static bool IsZoo(string? buildingType)
    {
        return buildingType != null && BuildingTypes.Contains(buildingType);
    }
}
```

`StardewZoo/ModConfig.cs`:

```csharp
namespace StardewZoo;

/// <summary>Player-editable settings, stored in the mod's config.json.</summary>
public sealed class ModConfig
{
    public int PricePerAnimal { get; set; } = 50;

    public int PricePerSpecies { get; set; } = 200;

    public int TicketPrice { get; set; } = 50;

    /// <summary>Income multiplier per zoo building ID; unknown IDs use 1.0.</summary>
    public Dictionary<string, double> Multipliers { get; set; } = new()
    {
        [ZooIds.Zoo] = 1.0,
        [ZooIds.BigZoo] = 1.5,
        [ZooIds.DeluxeZoo] = 2.0
    };
}
```

`StardewZoo/ZooIncome.cs` (stub so the tests compile and fail):

```csharp
namespace StardewZoo;

public record ZooSnapshot(string BuildingType, IReadOnlyList<string> AnimalTypes);

public record ZooResult(string BuildingType, int AnimalCount, int SpeciesCount, int Income);

public record DailyIncome(IReadOnlyList<ZooResult> Zoos, int TotalIncome, int Visitors);

public static class ZooIncome
{
    public static DailyIncome Calculate(IEnumerable<ZooSnapshot> zoos, ModConfig config)
    {
        throw new NotImplementedException();
    }
}
```

- [ ] **Step 3: Create the test project**

`StardewZoo.Tests/StardewZoo.Tests.csproj`:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net6.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsPackable>false</IsPackable>
  </PropertyGroup>

  <ItemGroup>
    <Compile Include="..\StardewZoo\ZooIds.cs" Link="Linked\ZooIds.cs" />
    <Compile Include="..\StardewZoo\ModConfig.cs" Link="Linked\ModConfig.cs" />
    <Compile Include="..\StardewZoo\ZooIncome.cs" Link="Linked\ZooIncome.cs" />
  </ItemGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.8.0" />
    <PackageReference Include="xunit" Version="2.6.6" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.5.6" />
  </ItemGroup>
</Project>
```

- [ ] **Step 4: Write the failing tests**

`StardewZoo.Tests/ZooIncomeTests.cs`:

```csharp
using StardewZoo;
using Xunit;

public class ZooIncomeTests
{
    private const string Penguin = "StardewZoo.Penguin";
    private const string Panda = "StardewZoo.Panda";

    private static DailyIncome Calc(ModConfig config, params ZooSnapshot[] zoos)
    {
        return ZooIncome.Calculate(zoos, config);
    }

    [Fact]
    public void NoZoos_PaysNothing()
    {
        DailyIncome result = Calc(new ModConfig());

        Assert.Empty(result.Zoos);
        Assert.Equal(0, result.TotalIncome);
        Assert.Equal(0, result.Visitors);
    }

    [Fact]
    public void EmptyZoo_PaysNothing()
    {
        DailyIncome result = Calc(new ModConfig(), new ZooSnapshot(ZooIds.Zoo, Array.Empty<string>()));

        Assert.Equal(0, result.TotalIncome);
        Assert.Equal(new ZooResult(ZooIds.Zoo, 0, 0, 0), result.Zoos.Single());
    }

    [Fact]
    public void BasicZoo_CountsAnimalsAndDistinctSpecies()
    {
        DailyIncome result = Calc(new ModConfig(), new ZooSnapshot(ZooIds.Zoo, new[] { Penguin, Penguin, Panda }));

        // (3 * 50 + 2 * 200) * 1.0 = 550
        Assert.Equal(new ZooResult(ZooIds.Zoo, 3, 2, 550), result.Zoos.Single());
        Assert.Equal(550, result.TotalIncome);
        Assert.Equal(11, result.Visitors);
    }

    [Theory]
    [InlineData(ZooIds.BigZoo, 825)]
    [InlineData(ZooIds.DeluxeZoo, 1100)]
    [InlineData("SomeOther.Building", 550)]
    public void Multiplier_DependsOnBuildingTier(string buildingType, int expected)
    {
        DailyIncome result = Calc(new ModConfig(), new ZooSnapshot(buildingType, new[] { Penguin, Penguin, Panda }));

        Assert.Equal(expected, result.TotalIncome);
    }

    [Fact]
    public void MultipleZoos_SumIncome_SpeciesCountedPerZoo()
    {
        DailyIncome result = Calc(
            new ModConfig(),
            new ZooSnapshot(ZooIds.Zoo, new[] { Penguin }),
            new ZooSnapshot(ZooIds.Zoo, new[] { Penguin })
        );

        // each zoo: (1 * 50 + 1 * 200) * 1.0 = 250
        Assert.Equal(2, result.Zoos.Count);
        Assert.Equal(500, result.TotalIncome);
        Assert.Equal(10, result.Visitors);
    }

    [Fact]
    public void Visitors_RoundDown()
    {
        var config = new ModConfig { TicketPrice = 300 };

        DailyIncome result = Calc(config, new ZooSnapshot(ZooIds.Zoo, new[] { Penguin, Penguin, Panda }));

        Assert.Equal(1, result.Visitors); // 550 / 300 = 1.83
    }

    [Fact]
    public void ZeroTicketPrice_HasNoVisitorsButStillPays()
    {
        var config = new ModConfig { TicketPrice = 0 };

        DailyIncome result = Calc(config, new ZooSnapshot(ZooIds.Zoo, new[] { Penguin }));

        Assert.Equal(250, result.TotalIncome);
        Assert.Equal(0, result.Visitors);
    }

    [Fact]
    public void FractionalIncome_RoundsHalfAwayFromZero()
    {
        var config = new ModConfig { PricePerAnimal = 1, PricePerSpecies = 0 };

        DailyIncome result = Calc(config, new ZooSnapshot(ZooIds.BigZoo, new[] { Penguin }));

        Assert.Equal(2, result.TotalIncome); // 1 * 1.5 = 1.5 -> 2
    }
}
```

- [ ] **Step 5: Create the solution and run tests to verify they fail**

```bash
export DOTNET_ROOT="$HOME/.dotnet" PATH="$HOME/.dotnet:$PATH"
dotnet new sln -n StardewZoo
dotnet sln StardewZoo.sln add StardewZoo.Tests/StardewZoo.Tests.csproj
dotnet test StardewZoo.Tests
```

Expected: build succeeds; tests FAIL with `System.NotImplementedException` (the 8 test methods / 10 test cases).

- [ ] **Step 6: Implement `ZooIncome.Calculate`**

Replace the `ZooIncome` class in `StardewZoo/ZooIncome.cs`:

```csharp
public static class ZooIncome
{
    public static DailyIncome Calculate(IEnumerable<ZooSnapshot> zoos, ModConfig config)
    {
        var results = new List<ZooResult>();
        foreach (ZooSnapshot zoo in zoos)
        {
            int animals = zoo.AnimalTypes.Count;
            int species = zoo.AnimalTypes.Distinct().Count();
            double multiplier = config.Multipliers.TryGetValue(zoo.BuildingType, out double value) ? value : 1.0;
            double raw = (animals * config.PricePerAnimal + species * config.PricePerSpecies) * multiplier;
            int income = (int)Math.Round(raw, MidpointRounding.AwayFromZero);

            results.Add(new ZooResult(zoo.BuildingType, animals, species, income));
        }

        int total = results.Sum(p => p.Income);
        int visitors = config.TicketPrice > 0 ? total / config.TicketPrice : 0;
        return new DailyIncome(results, total, visitors);
    }
}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `dotnet test StardewZoo.Tests`
Expected: `Passed!  - Failed: 0, Passed: 10`

- [ ] **Step 8: Commit**

```bash
git add StardewZoo.sln StardewZoo StardewZoo.Tests
git commit -m "feat: add pure zoo income calculation with tests"
```

---

### Task 2: SMAPI mod project and game wiring

**Files:**
- Create: `StardewZoo/StardewZoo.csproj`, `StardewZoo/manifest.json`, `StardewZoo/ModEntry.cs`
- Create: `StardewZoo/i18n/default.json`, `StardewZoo/i18n/zh.json`
- Modify: `StardewZoo.sln` (add project)

**Interfaces:**
- Consumes: everything Task 1 produces.
- Produces: SMAPI mod `UniqueID` `Kenzie.StardewZoo`; console command `zoo_status`.

- [ ] **Step 1: Create the project file**

`StardewZoo/StardewZoo.csproj`:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <AssemblyName>StardewZoo</AssemblyName>
    <RootNamespace>StardewZoo</RootNamespace>
    <Version>1.0.0</Version>
    <TargetFramework>net6.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <GamePath>$(HOME)/Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS</GamePath>
    <EnableHarmony>false</EnableHarmony>
  </PropertyGroup>
</Project>
```

Then add the build package (latest version):

```bash
export DOTNET_ROOT="$HOME/.dotnet" PATH="$HOME/.dotnet:$PATH"
dotnet add StardewZoo/StardewZoo.csproj package Pathoschild.Stardew.ModBuildConfig
dotnet sln StardewZoo.sln add StardewZoo/StardewZoo.csproj
```

- [ ] **Step 2: Create the manifest**

`StardewZoo/manifest.json`:

```json
{
  "Name": "Stardew Zoo",
  "Author": "Kenzie",
  "Version": "1.0.0",
  "Description": "Pays daily ticket income for the animals in your zoo.",
  "UniqueID": "Kenzie.StardewZoo",
  "EntryDll": "StardewZoo.dll",
  "MinimumApiVersion": "4.0.0",
  "UpdateKeys": []
}
```

- [ ] **Step 3: Create translations**

`StardewZoo/i18n/default.json`:

```json
{
  "hud.payout": "Yesterday {{visitors}} visitors came to the zoo. Ticket income: {{income}}g.",
  "command.no-save": "Load a save first.",
  "command.no-zoos": "You don't have any zoos yet.",
  "command.zoo-line": "{{building}}: {{animals}} animals, {{species}} species -> {{income}}g",
  "command.total": "Projected total: {{income}}g from {{visitors}} visitors."
}
```

`StardewZoo/i18n/zh.json`:

```json
{
  "hud.payout": "昨天有 {{visitors}} 位游客参观了动物园，门票收入 {{income}}g。",
  "command.no-save": "请先读取存档。",
  "command.no-zoos": "你还没有动物园。",
  "command.zoo-line": "{{building}}：{{animals}} 只动物，{{species}} 个物种 -> {{income}}g",
  "command.total": "预计总收入：{{income}}g，游客 {{visitors}} 位。"
}
```

- [ ] **Step 4: Write `ModEntry`**

`StardewZoo/ModEntry.cs`:

```csharp
using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewValley;

namespace StardewZoo;

/// <summary>The mod entry point.</summary>
internal sealed class ModEntry : Mod
{
    private ModConfig config = null!;

    /// <summary>The income paid at the end of the previous day, shown the next morning.</summary>
    private DailyIncome? lastPayout;

    public override void Entry(IModHelper helper)
    {
        this.config = helper.ReadConfig<ModConfig>();

        helper.Events.GameLoop.DayEnding += this.OnDayEnding;
        helper.Events.GameLoop.DayStarted += this.OnDayStarted;
        helper.ConsoleCommands.Add("zoo_status", "Shows each zoo, its animals, and projected ticket income.", this.OnZooStatusCommand);
    }

    private void OnDayEnding(object? sender, DayEndingEventArgs e)
    {
        if (!Context.IsMainPlayer)
            return;

        DailyIncome result = ZooIncome.Calculate(this.ScanZoos(), this.config);
        if (result.TotalIncome <= 0)
            return;

        Game1.player.Money += result.TotalIncome;
        this.lastPayout = result;
        this.Monitor.Log($"Paid {result.TotalIncome}g zoo income ({result.Visitors} visitors).", LogLevel.Trace);
    }

    private void OnDayStarted(object? sender, DayStartedEventArgs e)
    {
        if (this.lastPayout is not { } payout)
            return;

        string message = this.Helper.Translation.Get("hud.payout", new { visitors = payout.Visitors, income = payout.TotalIncome });
        Game1.addHUDMessage(new HUDMessage(message, HUDMessage.newQuest_type));
        this.lastPayout = null;
    }

    private void OnZooStatusCommand(string command, string[] args)
    {
        if (!Context.IsWorldReady)
        {
            this.Monitor.Log(this.Helper.Translation.Get("command.no-save"), LogLevel.Info);
            return;
        }

        DailyIncome result = ZooIncome.Calculate(this.ScanZoos(), this.config);
        if (result.Zoos.Count == 0)
        {
            this.Monitor.Log(this.Helper.Translation.Get("command.no-zoos"), LogLevel.Info);
            return;
        }

        foreach (ZooResult zoo in result.Zoos)
        {
            this.Monitor.Log(
                this.Helper.Translation.Get("command.zoo-line", new { building = zoo.BuildingType, animals = zoo.AnimalCount, species = zoo.SpeciesCount, income = zoo.Income }),
                LogLevel.Info
            );
        }
        this.Monitor.Log(this.Helper.Translation.Get("command.total", new { income = result.TotalIncome, visitors = result.Visitors }), LogLevel.Info);
    }

    /// <summary>Get the animal types living in each completed zoo building, in any location.</summary>
    private List<ZooSnapshot> ScanZoos()
    {
        var zoos = new List<ZooSnapshot>();

        Utility.ForEachBuilding(building =>
        {
            string buildingType = building.buildingType.Value;
            if (!ZooIds.IsZoo(buildingType) || building.isUnderConstruction() || building.GetIndoors() is not AnimalHouse house)
                return true;

            var animalTypes = new List<string>();
            foreach (long id in house.animalsThatLiveHere)
            {
                FarmAnimal? animal = Utility.getAnimal(id);
                if (animal != null)
                    animalTypes.Add(animal.type.Value);
            }

            zoos.Add(new ZooSnapshot(buildingType, animalTypes));
            return true;
        });

        return zoos;
    }
}
```

- [ ] **Step 5: Build (also auto-deploys to the game's Mods folder)**

```bash
export DOTNET_ROOT="$HOME/.dotnet" PATH="$HOME/.dotnet:$PATH"
dotnet build StardewZoo/StardewZoo.csproj
ls "$HOME/Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS/Mods/StardewZoo"
```

Expected: `Build succeeded` with 0 errors; the listing contains `StardewZoo.dll`, `manifest.json`, and `i18n`.
If a compile error says a game member doesn't exist (e.g. `Utility.getAnimal`), stop and report the exact error; do not guess a replacement.

- [ ] **Step 6: Re-run unit tests**

Run: `dotnet test StardewZoo.Tests`
Expected: `Passed!  - Failed: 0, Passed: 10`

- [ ] **Step 7: Commit**

```bash
git add StardewZoo StardewZoo.sln
git commit -m "feat: add SMAPI mod that pays daily zoo income"
```

---

### Task 3: Placeholder sprite generator

**Files:**
- Create: `tools/make_sprites.py`
- Create (generated): `[CP] Stardew Zoo/assets/*.png` (15 files)

**Interfaces:**
- Produces these files under `[CP] Stardew Zoo/assets/`, which Task 4 loads by name:
  `Penguin.png BabyPenguin.png PenguinShop.png Panda.png BabyPanda.png PandaShop.png Lion.png BabyLion.png LionShop.png Giraffe.png BabyGiraffe.png GiraffeShop.png Zoo.png BigZoo.png DeluxeZoo.png`
- Sizes: Penguin/BabyPenguin 64×112; Panda/Lion/Giraffe and babies 128×160; shop icons 32×16; zoo buildings 112×128.

- [ ] **Step 1: Write the script**

`tools/make_sprites.py`:

```python
"""Generate placeholder zoo sprites by recoloring vanilla Stardew Valley sprites.

Usage: python3 tools/make_sprites.py [path to "Content (unpacked)"]
"""

import sys
from pathlib import Path

from PIL import Image, ImageOps

DEFAULT_CONTENT = Path.home() / (
    "Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS/Content (unpacked)"
)
OUT_DIR = Path(__file__).resolve().parent.parent / "[CP] Stardew Zoo" / "assets"

# name: (vanilla adult sheet, vanilla baby sheet, shop icon rect in Cursors, (dark, mid, light))
ANIMALS = {
    "Penguin": ("White Chicken", "BabyWhite Chicken", (0, 448, 32, 16), ("#0b1020", "#2e3a59", "#e8eef7")),
    "Panda": ("White Cow", "BabyWhite Cow", (32, 448, 32, 16), ("#000000", "#404040", "#ffffff")),
    "Lion": ("Pig", "BabyPig", (0, 480, 32, 16), ("#3b1f05", "#c27a1e", "#f5c56a")),
    "Giraffe": ("Brown Cow", "BabyBrown Cow", (32, 448, 32, 16), ("#3d2410", "#c98b2b", "#f6e3a1")),
}

# name: vanilla building sheet
BUILDINGS = {"Zoo": "Barn", "BigZoo": "Big Barn", "DeluxeZoo": "Deluxe Barn"}

# hue rotation (0-255 scale) that turns the red barn green
BUILDING_HUE_SHIFT = 85


def colorize(image: Image.Image, palette: tuple[str, str, str]) -> Image.Image:
    """Map the image's brightness onto a dark/mid/light palette, keeping transparency."""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    dark, mid, light = palette
    colored = ImageOps.colorize(ImageOps.grayscale(rgba), black=dark, white=light, mid=mid).convert("RGBA")
    colored.putalpha(alpha)
    return colored


def hue_shift(image: Image.Image, shift: int) -> Image.Image:
    """Rotate the hue of every pixel, keeping transparency."""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    h, s, v = rgba.convert("RGB").convert("HSV").split()
    h = h.point(lambda value: (value + shift) % 256)
    shifted = Image.merge("HSV", (h, s, v)).convert("RGBA")
    shifted.putalpha(alpha)
    return shifted


def main() -> None:
    content = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONTENT
    if not (content / "Animals").is_dir():
        sys.exit(f"Unpacked content not found at {content}; run StardewXnbHack first.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cursors = Image.open(content / "LooseSprites" / "Cursors.png")

    for name, (adult, baby, shop_rect, palette) in ANIMALS.items():
        colorize(Image.open(content / "Animals" / f"{adult}.png"), palette).save(OUT_DIR / f"{name}.png")
        colorize(Image.open(content / "Animals" / f"{baby}.png"), palette).save(OUT_DIR / f"Baby{name}.png")
        x, y, width, height = shop_rect
        colorize(cursors.crop((x, y, x + width, y + height)), palette).save(OUT_DIR / f"{name}Shop.png")

    for name, vanilla in BUILDINGS.items():
        hue_shift(Image.open(content / "Buildings" / f"{vanilla}.png"), BUILDING_HUE_SHIFT).save(OUT_DIR / f"{name}.png")

    print(f"Wrote {len(list(OUT_DIR.glob('*.png')))} sprites to {OUT_DIR}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `python3 tools/make_sprites.py`
Expected: `Wrote 15 sprites to .../[CP] Stardew Zoo/assets`

- [ ] **Step 3: Verify sizes**

```bash
python3 -c "
from pathlib import Path
from PIL import Image
expected = {'Penguin': (64, 112), 'BabyPenguin': (64, 112), 'Zoo': (112, 128), 'BigZoo': (112, 128), 'DeluxeZoo': (112, 128)}
for a in ['Panda', 'Lion', 'Giraffe']:
    expected[a] = expected['Baby' + a] = (128, 160)
for a in ['Penguin', 'Panda', 'Lion', 'Giraffe']:
    expected[a + 'Shop'] = (32, 16)
d = Path('[CP] Stardew Zoo/assets')
bad = {n: Image.open(d / f'{n}.png').size for n in expected if Image.open(d / f'{n}.png').size != expected[n]}
print('OK' if not bad and len(expected) == 15 else f'BAD {bad}')
"
```

Expected: `OK`

- [ ] **Step 4: Eyeball the output**

Open `[CP] Stardew Zoo/assets/Panda.png`, `Lion.png`, and `Zoo.png` with the Read tool and confirm they are recognizable recolored sprites (not blank or fully opaque).

- [ ] **Step 5: Commit**

```bash
git add tools/make_sprites.py "[CP] Stardew Zoo/assets"
git commit -m "feat: add placeholder zoo sprite generator and generated art"
```

---

### Task 4: Content Patcher pack

**Files:**
- Create: `[CP] Stardew Zoo/manifest.json`, `[CP] Stardew Zoo/content.json`
- Create: `[CP] Stardew Zoo/i18n/default.json`, `[CP] Stardew Zoo/i18n/zh.json`

**Interfaces:**
- Consumes: asset PNGs from Task 3; IDs from Global Constraints.
- Produces: game data entries `Data/Buildings` → `StardewZoo.Zoo|BigZoo|DeluxeZoo`, `Data/FarmAnimals` → `StardewZoo.Penguin|Panda|Lion|Giraffe`; texture assets `Mods/StardewZoo/<Name>`.

- [ ] **Step 1: Manifest**

`[CP] Stardew Zoo/manifest.json`:

```json
{
  "Name": "[CP] Stardew Zoo",
  "Author": "Kenzie",
  "Version": "1.0.0",
  "Description": "Adds an upgradable zoo building and exotic animals.",
  "UniqueID": "Kenzie.StardewZoo.CP",
  "UpdateKeys": [],
  "ContentPackFor": {
    "UniqueID": "Pathoschild.ContentPatcher",
    "MinimumVersion": "2.9.0"
  }
}
```

- [ ] **Step 2: Translations**

`[CP] Stardew Zoo/i18n/default.json`:

```json
{
  "building.Zoo.name": "Zoo",
  "building.Zoo.description": "Show off exotic animals. Visitors buy tickets every day. Holds 8 animals.",
  "building.BigZoo.name": "Big Zoo",
  "building.BigZoo.description": "A bigger zoo. Holds 12 animals and earns 1.5x ticket income.",
  "building.DeluxeZoo.name": "Deluxe Zoo",
  "building.DeluxeZoo.description": "The best zoo in the valley. Holds 16 animals and earns 2x ticket income.",
  "animal.Penguin.name": "Penguin",
  "animal.Penguin.description": "A waddling crowd-pleaser.",
  "animal.Panda.name": "Panda",
  "animal.Panda.description": "Visitors travel from far away to see it.",
  "animal.Lion.name": "Lion",
  "animal.Lion.description": "The king of the zoo.",
  "animal.Giraffe.name": "Giraffe",
  "animal.Giraffe.description": "Can see over the whole farm.",
  "animal.missing-building": "Requires a Zoo. Ask Robin to build one."
}
```

`[CP] Stardew Zoo/i18n/zh.json`:

```json
{
  "building.Zoo.name": "动物园",
  "building.Zoo.description": "展示珍奇动物。每天都有游客买票参观。可容纳 8 只动物。",
  "building.BigZoo.name": "大型动物园",
  "building.BigZoo.description": "更大的动物园。可容纳 12 只动物，门票收入 1.5 倍。",
  "building.DeluxeZoo.name": "豪华动物园",
  "building.DeluxeZoo.description": "山谷里最好的动物园。可容纳 16 只动物，门票收入 2 倍。",
  "animal.Penguin.name": "企鹅",
  "animal.Penguin.description": "摇摇摆摆，人见人爱。",
  "animal.Panda.name": "熊猫",
  "animal.Panda.description": "游客们不远千里来看它。",
  "animal.Lion.name": "狮子",
  "animal.Lion.description": "动物园之王。",
  "animal.Giraffe.name": "长颈鹿",
  "animal.Giraffe.description": "能看到整个农场。",
  "animal.missing-building": "需要动物园。请找罗宾建造。"
}
```

- [ ] **Step 3: `content.json`**

Layout values below are copied from vanilla `Barn` / `Big Barn` / `Deluxe Barn` (doors, draw layers, item moves) and `White Chicken` / `White Cow` (sprite metrics) in `$GAME/Content (unpacked)/Data/*.json`.

`[CP] Stardew Zoo/content.json`:

```json
{
  "Format": "2.9.0",
  "Changes": [
    {
      "LogName": "Zoo textures",
      "Action": "Load",
      "Target": "Mods/StardewZoo/Zoo, Mods/StardewZoo/BigZoo, Mods/StardewZoo/DeluxeZoo, Mods/StardewZoo/Penguin, Mods/StardewZoo/BabyPenguin, Mods/StardewZoo/PenguinShop, Mods/StardewZoo/Panda, Mods/StardewZoo/BabyPanda, Mods/StardewZoo/PandaShop, Mods/StardewZoo/Lion, Mods/StardewZoo/BabyLion, Mods/StardewZoo/LionShop, Mods/StardewZoo/Giraffe, Mods/StardewZoo/BabyGiraffe, Mods/StardewZoo/GiraffeShop",
      "FromFile": "assets/{{TargetWithoutPath}}.png"
    },
    {
      "LogName": "Zoo buildings",
      "Action": "EditData",
      "Target": "Data/Buildings",
      "Entries": {
        "StardewZoo.Zoo": {
          "Name": "{{i18n:building.Zoo.name}}",
          "Description": "{{i18n:building.Zoo.description}}",
          "Texture": "Mods/StardewZoo/Zoo",
          "UpgradeSignTile": "3, 3",
          "UpgradeSignHeight": 31.0,
          "Size": { "X": 7, "Y": 4 },
          "SourceRect": { "X": 0, "Y": 0, "Width": 112, "Height": 112 },
          "Builder": "Robin",
          "BuildDays": 3,
          "BuildCost": 10000,
          "BuildMaterials": [
            { "ItemId": "(O)388", "Amount": 400 },
            { "ItemId": "(O)390", "Amount": 200 }
          ],
          "HumanDoor": { "X": 1, "Y": 3 },
          "AnimalDoor": { "X": 3, "Y": 3, "Width": 2, "Height": 1 },
          "AnimalDoorOpenDuration": 0.4,
          "AnimalDoorOpenSound": "doorCreak",
          "AnimalDoorCloseDuration": 0.6,
          "AnimalDoorCloseSound": "doorCreakReverse",
          "IndoorMap": "Barn",
          "IndoorMapType": "StardewValley.AnimalHouse",
          "MaxOccupants": 8,
          "ValidOccupantTypes": [ "StardewZoo.Zoo" ],
          "AllowAnimalPregnancy": false,
          "IndoorItems": [
            { "Id": "Default_FeedHopper", "ItemId": "(BC)99", "Tile": { "X": 6, "Y": 3 }, "Indestructible": true, "ClearTile": true }
          ],
          "DrawLayers": [
            { "Id": "Default_AnimalDoor_Bottom", "SourceRect": { "X": 0, "Y": 112, "Width": 32, "Height": 16 }, "DrawPosition": "48, 96", "SortTileOffset": 0.02, "AnimalDoorOffset": { "X": 0, "Y": -19 } },
            { "Id": "Default_AnimalDoor_Top", "SourceRect": { "X": 0, "Y": 112, "Width": 32, "Height": 12 }, "DrawPosition": "48, 84", "SortTileOffset": 0.02, "AnimalDoorOffset": { "X": 0, "Y": -19 } },
            { "Id": "Default_AnimalDoor_Open_Top", "SourceRect": { "X": 32, "Y": 112, "Width": 32, "Height": 16 }, "DrawPosition": "48, 80", "SortTileOffset": 1.0 },
            { "Id": "Default_AnimalDoor_Open_Bottom", "SourceRect": { "X": 64, "Y": 112, "Width": 32, "Height": 16 }, "DrawPosition": "48, 96", "SortTileOffset": 1.0 }
          ]
        },
        "StardewZoo.BigZoo": {
          "Name": "{{i18n:building.BigZoo.name}}",
          "NameForGeneralType": "{{i18n:building.Zoo.name}}",
          "Description": "{{i18n:building.BigZoo.description}}",
          "Texture": "Mods/StardewZoo/BigZoo",
          "UpgradeSignTile": "3, 3",
          "UpgradeSignHeight": 31.0,
          "Size": { "X": 7, "Y": 4 },
          "SourceRect": { "X": 0, "Y": 0, "Width": 112, "Height": 112 },
          "Builder": "Robin",
          "BuildDays": 2,
          "BuildCost": 20000,
          "BuildMaterials": [
            { "ItemId": "(O)388", "Amount": 500 },
            { "ItemId": "(O)390", "Amount": 250 }
          ],
          "BuildingToUpgrade": "StardewZoo.Zoo",
          "HumanDoor": { "X": 1, "Y": 3 },
          "AnimalDoor": { "X": 4, "Y": 3, "Width": 2, "Height": 1 },
          "AnimalDoorOpenDuration": 0.4,
          "AnimalDoorOpenSound": "doorCreak",
          "AnimalDoorCloseDuration": 0.6,
          "AnimalDoorCloseSound": "doorCreakReverse",
          "IndoorMap": "Barn2",
          "IndoorMapType": "StardewValley.AnimalHouse",
          "MaxOccupants": 12,
          "ValidOccupantTypes": [ "StardewZoo.Zoo" ],
          "AllowAnimalPregnancy": false,
          "IndoorItemMoves": [
            { "Id": "Default_ClearSpace_WaterTrough_Left", "Source": { "X": 15, "Y": 3 }, "Destination": { "X": 18, "Y": 13 }, "Size": { "X": 1, "Y": 1 } },
            { "Id": "Default_ClearSpace_WaterTrough_Right", "Source": { "X": 16, "Y": 3 }, "Destination": { "X": 19, "Y": 13 }, "Size": { "X": 1, "Y": 1 } },
            { "Id": "Default_ClearSpace_Barrel", "Source": { "X": 1, "Y": 4 }, "Destination": { "X": 20, "Y": 3 }, "Size": { "X": 1, "Y": 1 } },
            { "Id": "Default_KeepAlongWall", "Source": { "X": 16, "Y": 4 }, "Destination": { "X": 20, "Y": 4 }, "Size": { "X": 1, "Y": 9 } }
          ],
          "IndoorItems": [
            { "Id": "Default_FeedHopper", "ItemId": "(BC)99", "Tile": { "X": 6, "Y": 3 }, "Indestructible": true, "ClearTile": true }
          ],
          "DrawLayers": [
            { "Id": "Default_AnimalDoor_Bottom", "SourceRect": { "X": 0, "Y": 112, "Width": 32, "Height": 16 }, "DrawPosition": "64, 96", "SortTileOffset": 0.02, "AnimalDoorOffset": { "X": 0, "Y": -19 } },
            { "Id": "Default_AnimalDoor_Top", "SourceRect": { "X": 0, "Y": 112, "Width": 32, "Height": 12 }, "DrawPosition": "64, 84", "SortTileOffset": 0.02, "AnimalDoorOffset": { "X": 0, "Y": -19 } },
            { "Id": "Default_AnimalDoor_Open_Top", "SourceRect": { "X": 32, "Y": 112, "Width": 32, "Height": 16 }, "DrawPosition": "64, 80", "SortTileOffset": 1.0 },
            { "Id": "Default_AnimalDoor_Open_Bottom", "SourceRect": { "X": 64, "Y": 112, "Width": 32, "Height": 16 }, "DrawPosition": "64, 96", "SortTileOffset": 1.0 }
          ]
        },
        "StardewZoo.DeluxeZoo": {
          "Name": "{{i18n:building.DeluxeZoo.name}}",
          "NameForGeneralType": "{{i18n:building.Zoo.name}}",
          "Description": "{{i18n:building.DeluxeZoo.description}}",
          "Texture": "Mods/StardewZoo/DeluxeZoo",
          "UpgradeSignTile": "4.5, 2",
          "UpgradeSignHeight": 31.0,
          "Size": { "X": 7, "Y": 4 },
          "SourceRect": { "X": 0, "Y": 0, "Width": 112, "Height": 112 },
          "Builder": "Robin",
          "BuildDays": 2,
          "BuildCost": 35000,
          "BuildMaterials": [
            { "ItemId": "(O)388", "Amount": 650 },
            { "ItemId": "(O)390", "Amount": 350 }
          ],
          "BuildingToUpgrade": "StardewZoo.BigZoo",
          "HumanDoor": { "X": 1, "Y": 3 },
          "AnimalDoor": { "X": 4, "Y": 3, "Width": 2, "Height": 1 },
          "AnimalDoorOpenDuration": 0.4,
          "AnimalDoorOpenSound": "doorCreak",
          "AnimalDoorCloseDuration": 0.6,
          "AnimalDoorCloseSound": "doorCreakReverse",
          "IndoorMap": "Barn3",
          "IndoorMapType": "StardewValley.AnimalHouse",
          "MaxOccupants": 16,
          "ValidOccupantTypes": [ "StardewZoo.Zoo" ],
          "AllowAnimalPregnancy": false,
          "IndoorItemMoves": [
            { "Id": "Default_ClearSpace_Barrel", "Source": { "X": 20, "Y": 3 }, "Destination": { "X": 1, "Y": 4 }, "Size": { "X": 1, "Y": 1 } },
            { "Id": "Default_KeepAlongWall_Top", "Source": { "X": 20, "Y": 5 }, "Destination": { "X": 21, "Y": 13 }, "Size": { "X": 1, "Y": 1 } },
            { "Id": "Default_KeepAlongWall_Middle", "Source": { "X": 20, "Y": 6 }, "Destination": { "X": 23, "Y": 6 }, "Size": { "X": 1, "Y": 6 } },
            { "Id": "Default_ClearSpace_Bucket", "Source": { "X": 20, "Y": 4 }, "Destination": { "X": 20, "Y": 13 }, "Size": { "X": 1, "Y": 1 } },
            { "Id": "Default_ShiftSpace_NextToBarrel", "Source": { "X": 20, "Y": 12 }, "Destination": { "X": 22, "Y": 13 }, "Size": { "X": 1, "Y": 1 } }
          ],
          "IndoorItems": [
            { "Id": "Default_FeedHopper", "ItemId": "(BC)99", "Tile": { "X": 6, "Y": 3 }, "Indestructible": true, "ClearTile": true }
          ],
          "DrawLayers": [
            { "Id": "Default_AnimalDoor_Bottom", "SourceRect": { "X": 0, "Y": 112, "Width": 32, "Height": 16 }, "DrawPosition": "64, 96", "SortTileOffset": 0.02, "AnimalDoorOffset": { "X": 0, "Y": -19 } },
            { "Id": "Default_AnimalDoor_Top", "SourceRect": { "X": 0, "Y": 112, "Width": 32, "Height": 12 }, "DrawPosition": "64, 84", "SortTileOffset": 0.02, "AnimalDoorOffset": { "X": 0, "Y": -19 } },
            { "Id": "Default_AnimalDoor_Open_Top", "SourceRect": { "X": 32, "Y": 112, "Width": 32, "Height": 16 }, "DrawPosition": "64, 80", "SortTileOffset": 1.0 },
            { "Id": "Default_AnimalDoor_Open_Bottom", "SourceRect": { "X": 64, "Y": 112, "Width": 32, "Height": 16 }, "DrawPosition": "64, 96", "SortTileOffset": 1.0 }
          ]
        }
      }
    },
    {
      "LogName": "Zoo animals",
      "Action": "EditData",
      "Target": "Data/FarmAnimals",
      "Entries": {
        "StardewZoo.Penguin": {
          "DisplayName": "{{i18n:animal.Penguin.name}}",
          "House": "StardewZoo.Zoo",
          "Gender": "MaleOrFemale",
          "PurchasePrice": 1500,
          "SellPrice": 1500,
          "ShopTexture": "Mods/StardewZoo/PenguinShop",
          "ShopSourceRect": { "X": 0, "Y": 0, "Width": 32, "Height": 16 },
          "ShopDescription": "{{i18n:animal.Penguin.description}}",
          "ShopMissingBuildingDescription": "{{i18n:animal.missing-building}}",
          "RequiredBuilding": "StardewZoo.Zoo",
          "DaysToMature": 3,
          "CanGetPregnant": false,
          "HarvestType": "DropOvernight",
          "ProduceItemIds": [],
          "DeluxeProduceItemIds": [],
          "CanEatGoldenCrackers": false,
          "ProfessionForHappinessBoost": 3,
          "ProfessionForQualityBoost": 3,
          "Sound": "Duck",
          "Texture": "Mods/StardewZoo/Penguin",
          "BabyTexture": "Mods/StardewZoo/BabyPenguin",
          "UseFlippedRightForLeft": false,
          "SpriteWidth": 16,
          "SpriteHeight": 16,
          "UseDoubleUniqueAnimationFrames": true,
          "SleepFrame": 16,
          "EmoteOffset": { "X": 0, "Y": -16 },
          "GrassEatAmount": 2,
          "HappinessDrain": 7,
          "UpDownPetHitboxTileSize": "1, 1",
          "LeftRightPetHitboxTileSize": "1, 1",
          "BabyUpDownPetHitboxTileSize": "1, 1",
          "BabyLeftRightPetHitboxTileSize": "1, 1",
          "ShowInSummitCredits": false
        },
        "StardewZoo.Panda": {
          "DisplayName": "{{i18n:animal.Panda.name}}",
          "House": "StardewZoo.Zoo",
          "Gender": "MaleOrFemale",
          "PurchasePrice": 3000,
          "SellPrice": 3000,
          "ShopTexture": "Mods/StardewZoo/PandaShop",
          "ShopSourceRect": { "X": 0, "Y": 0, "Width": 32, "Height": 16 },
          "ShopDescription": "{{i18n:animal.Panda.description}}",
          "ShopMissingBuildingDescription": "{{i18n:animal.missing-building}}",
          "RequiredBuilding": "StardewZoo.Zoo",
          "DaysToMature": 5,
          "CanGetPregnant": false,
          "HarvestType": "DropOvernight",
          "ProduceItemIds": [],
          "DeluxeProduceItemIds": [],
          "CanEatGoldenCrackers": false,
          "ProfessionForHappinessBoost": 3,
          "ProfessionForQualityBoost": 3,
          "Sound": "pig",
          "Texture": "Mods/StardewZoo/Panda",
          "BabyTexture": "Mods/StardewZoo/BabyPanda",
          "UseFlippedRightForLeft": true,
          "SpriteWidth": 32,
          "SpriteHeight": 32,
          "SleepFrame": 12,
          "Shadow": { "Visible": false },
          "GrassEatAmount": 4,
          "HappinessDrain": 6,
          "UpDownPetHitboxTileSize": "1, 1.75",
          "LeftRightPetHitboxTileSize": "1.75, 1.25",
          "BabyUpDownPetHitboxTileSize": "1, 1.75",
          "BabyLeftRightPetHitboxTileSize": "1.75, 1",
          "ShowInSummitCredits": false
        },
        "StardewZoo.Lion": {
          "DisplayName": "{{i18n:animal.Lion.name}}",
          "House": "StardewZoo.Zoo",
          "Gender": "MaleOrFemale",
          "PurchasePrice": 4000,
          "SellPrice": 4000,
          "ShopTexture": "Mods/StardewZoo/LionShop",
          "ShopSourceRect": { "X": 0, "Y": 0, "Width": 32, "Height": 16 },
          "ShopDescription": "{{i18n:animal.Lion.description}}",
          "ShopMissingBuildingDescription": "{{i18n:animal.missing-building}}",
          "RequiredBuilding": "StardewZoo.Zoo",
          "DaysToMature": 5,
          "CanGetPregnant": false,
          "HarvestType": "DropOvernight",
          "ProduceItemIds": [],
          "DeluxeProduceItemIds": [],
          "CanEatGoldenCrackers": false,
          "ProfessionForHappinessBoost": 3,
          "ProfessionForQualityBoost": 3,
          "Sound": "cow",
          "Texture": "Mods/StardewZoo/Lion",
          "BabyTexture": "Mods/StardewZoo/BabyLion",
          "UseFlippedRightForLeft": true,
          "SpriteWidth": 32,
          "SpriteHeight": 32,
          "SleepFrame": 12,
          "Shadow": { "Visible": false },
          "GrassEatAmount": 4,
          "HappinessDrain": 6,
          "UpDownPetHitboxTileSize": "1.5, 1.75",
          "LeftRightPetHitboxTileSize": "1.75, 1.25",
          "BabyUpDownPetHitboxTileSize": "1, 1.75",
          "BabyLeftRightPetHitboxTileSize": "1.75, 1",
          "ShowInSummitCredits": false
        },
        "StardewZoo.Giraffe": {
          "DisplayName": "{{i18n:animal.Giraffe.name}}",
          "House": "StardewZoo.Zoo",
          "Gender": "MaleOrFemale",
          "PurchasePrice": 5000,
          "SellPrice": 5000,
          "ShopTexture": "Mods/StardewZoo/GiraffeShop",
          "ShopSourceRect": { "X": 0, "Y": 0, "Width": 32, "Height": 16 },
          "ShopDescription": "{{i18n:animal.Giraffe.description}}",
          "ShopMissingBuildingDescription": "{{i18n:animal.missing-building}}",
          "RequiredBuilding": "StardewZoo.Zoo",
          "DaysToMature": 5,
          "CanGetPregnant": false,
          "HarvestType": "DropOvernight",
          "ProduceItemIds": [],
          "DeluxeProduceItemIds": [],
          "CanEatGoldenCrackers": false,
          "ProfessionForHappinessBoost": 3,
          "ProfessionForQualityBoost": 3,
          "Sound": "goat",
          "Texture": "Mods/StardewZoo/Giraffe",
          "BabyTexture": "Mods/StardewZoo/BabyGiraffe",
          "UseFlippedRightForLeft": true,
          "SpriteWidth": 32,
          "SpriteHeight": 32,
          "SleepFrame": 12,
          "Shadow": { "Visible": false },
          "GrassEatAmount": 4,
          "HappinessDrain": 6,
          "UpDownPetHitboxTileSize": "1, 1.75",
          "LeftRightPetHitboxTileSize": "1.75, 1.25",
          "BabyUpDownPetHitboxTileSize": "1, 1.75",
          "BabyLeftRightPetHitboxTileSize": "1.75, 1",
          "ShowInSummitCredits": false
        }
      }
    }
  ]
}
```

- [ ] **Step 4: Validate JSON syntax**

```bash
for f in "[CP] Stardew Zoo"/*.json "[CP] Stardew Zoo"/i18n/*.json StardewZoo/manifest.json StardewZoo/i18n/*.json; do
  python3 -m json.tool "$f" > /dev/null && echo "ok $f" || echo "BAD $f"
done
```

Expected: every line starts with `ok`.

- [ ] **Step 5: Check every i18n key used exists in both languages and every texture has a PNG**

```bash
python3 - <<'EOF'
import json, re
from pathlib import Path
root = Path("[CP] Stardew Zoo")
text = (root / "content.json").read_text()
keys = set(re.findall(r"\{\{i18n:([^}]+)\}\}", text))
for lang in ["default", "zh"]:
    missing = keys - set(json.loads((root / "i18n" / f"{lang}.json").read_text()))
    print(lang, "missing:", sorted(missing) or "none")
targets = re.findall(r"Mods/StardewZoo/(\w+)", text)
missing_png = sorted({t for t in targets if not (root / "assets" / f"{t}.png").exists()})
print("missing png:", missing_png or "none")
EOF
```

Expected: `default missing: none`, `zh missing: none`, `missing png: none`.

- [ ] **Step 6: Commit**

```bash
git add "[CP] Stardew Zoo"
git commit -m "feat: add Content Patcher pack with zoo buildings and animals"
```

---

### Task 5: Deploy script + in-game verification

**Files:**
- Create: `deploy.sh`

**Interfaces:**
- Consumes: both packages from Tasks 2 and 4.

- [ ] **Step 1: Write `deploy.sh`**

```bash
#!/usr/bin/env bash
# Builds the C# mod (ModBuildConfig copies it into Mods/StardewZoo) and syncs the content pack.
set -euo pipefail
cd "$(dirname "$0")"

GAME="$HOME/Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS"
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"

dotnet test StardewZoo.Tests
dotnet build StardewZoo/StardewZoo.csproj -c Release
rsync -a --delete "[CP] Stardew Zoo/" "$GAME/Mods/[CP] Stardew Zoo/"

echo "Deployed StardewZoo and [CP] Stardew Zoo to $GAME/Mods"
```

Run: `chmod +x deploy.sh && ./deploy.sh`
Expected: tests pass, build succeeds, final line `Deployed StardewZoo and [CP] Stardew Zoo to ...`.

- [ ] **Step 2: Launch SMAPI and check the log for load errors**

This opens the game window. Launch in the background, wait for the title screen, then quit:

```bash
GAME="$HOME/Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS"
LOG="$HOME/.config/StardewValley/ErrorLogs/SMAPI-latest.txt"
"$GAME/StardewModdingAPI" > /tmp/smapi-run.txt 2>&1 &
SMAPI_PID=$!
for i in $(seq 1 90); do grep -q "Type 'help' for help" "$LOG" 2>/dev/null && break; sleep 2; done
sleep 10
kill $SMAPI_PID
grep -nE "Stardew Zoo|StardewZoo" "$LOG"
grep -nE "^\[[0-9:]+ (ERROR|WARN)" "$LOG" | grep -iE "zoo|Content Patcher" || echo "no zoo-related errors or warnings"
```

Expected:
- Lines showing both `Stardew Zoo 1.0.0` and `[CP] Stardew Zoo 1.0.0` loaded.
- `no zoo-related errors or warnings`.

If the log path differs, find it with `ls -t ~/.config/StardewValley/ErrorLogs/`. If an error appears, fix the referenced field before continuing (use superpowers:systematic-debugging).

- [ ] **Step 3: Commit**

```bash
git add deploy.sh
git commit -m "chore: add deploy script"
```

- [ ] **Step 4: Hand the in-game checklist to the user**

The remaining checks need a loaded save and mouse interaction, so give the user this checklist (on a backup copy of a save, or a new save) and wait for their results:

1. At Robin's, the construction menu shows 动物园 with cost 10,000g + 400 wood + 200 stone. To afford it on a test save, type `player_setmoney 100000` and `player_add name Wood 999` / `player_add name Stone 999` in the SMAPI console (bundled Console Commands mod). Build it and sleep 3 days.
2. After it's built, Marnie's animal shop lists 企鹅 / 熊猫 / 狮子 / 长颈鹿 with prices 3,000 / 6,000 / 8,000 / 10,000g, buyable into the zoo.
3. Buy one panda and one penguin; type `zoo_status` in the SMAPI console. Expected: `StardewZoo.Zoo：2 只动物，2 个物种 -> 500g` and total 500g from 10 visitors.
4. Sleep. Next morning: money increased by 500g and the HUD shows `昨天有 10 位游客参观了动物园，门票收入 500g。`
5. At Robin's, the zoo shows an upgrade to 大型动物园; after upgrading, `zoo_status` shows the 1.5× multiplier (750g for the same two animals).
6. Animals render with recolored sprites, walk around, and sleep without visual glitches; the zoo exterior is green.
