---
name: sprite-pipeline
description: Set up the sprite asset directory structure and create placeholder sprites for all tile and item types
---

# Sprite Pipeline Setup

## Goal

Create the `assets/sprites/` directory structure with placeholder sprites for all game entities. These placeholders will later be replaced with proper art from Google Antigravity image generation.

## Directory Structure

Create the following under `/home/flax/games/pizzatorio/v2_godot/assets/sprites/`:

```
assets/sprites/
├── tiles/           # Machine/building sprites (48x48 to match TILE_SIZE)
│   ├── conveyor.png
│   ├── processor.png
│   ├── oven.png
│   ├── bot_dock.png
│   ├── assembly_table.png
│   ├── source.png
│   └── sink.png
├── items/           # Ingredient/item sprites (16x16 or 24x24, shown on belt)
│   ├── raw/         # Raw stage items (yellow-ish)
│   ├── processed/   # Processed stage items (green-ish)
│   └── baked/       # Baked stage items (brown-orange)
└── ui/              # UI icons for HUD/menus
    └── tools/       # Build tool icons
```

## Steps

1. Create the directory structure above
2. Generate simple placeholder PNG sprites using Godot-compatible format. Use solid colored squares with a 1px border and a letter/symbol in the center to identify each tile type. Use the color palette from FactoryFloor.gd:
   - conveyor: Steel grey `(0.78, 0.82, 0.86)` with "→"
   - processor: Soft blue `(0.60, 0.78, 0.90)` with "P"
   - oven: Warm orange `(0.95, 0.65, 0.45)` with "O"
   - bot_dock: Soft green `(0.55, 0.80, 0.65)` with "B"
   - assembly_table: Soft purple `(0.70, 0.65, 0.88)` with "A"
   - source: Green `(0.45, 0.75, 0.45)` with "▶"
   - sink: Red `(0.85, 0.45, 0.45)` with "■"
3. For item sprites, create small colored squares:
   - raw: Yellow `(0.95, 0.85, 0.60)`
   - processed: Green `(0.60, 0.85, 0.60)`
   - baked: Brown-orange `(0.85, 0.55, 0.35)`
4. Create a `SpriteRegistry.gd` autoload or static class in `src/data/` that maps tile kinds and item stages to their texture paths, making it easy to swap placeholders for real art later

## Placeholder Generation

Use Python with Pillow or pure GDScript to generate the placeholder PNGs. A simple Python script is fine:

```python
from PIL import Image, ImageDraw
# Generate 48x48 tile sprites and 16x16 item sprites
```

Or use Godot's Image class in a tool script.

## SpriteRegistry Design

```gdscript
# src/data/SpriteRegistry.gd
extends Node

const TILE_SPRITES: Dictionary = {
    "conveyor": preload("res://assets/sprites/tiles/conveyor.png"),
    "processor": preload("res://assets/sprites/tiles/processor.png"),
    # ...
}

const ITEM_SPRITES: Dictionary = {
    "raw": preload("res://assets/sprites/items/raw/default.png"),
    "processed": preload("res://assets/sprites/items/processed/default.png"),
    "baked": preload("res://assets/sprites/items/baked/default.png"),
}

static func get_tile_texture(kind: String) -> Texture2D:
    return TILE_SPRITES.get(kind)

static func get_item_texture(stage: String, ingredient_type: String = "") -> Texture2D:
    # Later: per-ingredient sprites. For now: stage-based
    return ITEM_SPRITES.get(stage)
```

## Key Constraints

- Tile sprites: 48x48 px (matches GlobalConfig.TILE_SIZE)
- Item sprites: 16x16 px (small, visible on belt)
- All PNGs must be valid Godot-importable images
- The SpriteRegistry must work as a drop-in for FactoryFloor.gd to consume
- Design for easy swap: when real Antigravity-generated art arrives, only the PNG files change — code stays the same

## Files to Create

- `assets/sprites/tiles/*.png` — 7 tile sprites
- `assets/sprites/items/raw/default.png` — raw stage sprite
- `assets/sprites/items/processed/default.png` — processed stage sprite
- `assets/sprites/items/baked/default.png` — baked stage sprite
- `src/data/SpriteRegistry.gd` — texture lookup registry
