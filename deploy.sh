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
