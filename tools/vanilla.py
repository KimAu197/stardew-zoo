"""Paths to unpacked Stardew Valley content."""

from pathlib import Path

GAME = Path.home() / "Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS"
UNPACKED = GAME / "Content (unpacked)"
MAPS = UNPACKED / "Maps"
BUILDINGS = UNPACKED / "Buildings"
SHEETS = UNPACKED / "TileSheets"
LOOSE = UNPACKED / "LooseSprites"
CHARS = UNPACKED / "Characters"
