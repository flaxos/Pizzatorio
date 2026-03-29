---
name: wire-sprites
description: Replace ColorRect placeholders in FactoryFloor.gd with Sprite2D nodes loading from SpriteRegistry
---

# Wire Sprites into FactoryFloor

## Goal

Replace the ColorRect-based tile and item rendering in `FactoryFloor.gd` with Sprite2D nodes that load textures from the SpriteRegistry. This is the visual upgrade from colored rectangles to actual sprites.

## Prerequisites

- `sprite-pipeline` agent must have run first (creates `assets/sprites/` and `SpriteRegistry.gd`)

## Changes Required

### FactoryFloor.gd (`/home/flax/games/pizzatorio/v2_godot/src/scenes/FactoryFloor.gd`)

1. **`_create_tile_visual()`** — Replace the ColorRect background with a Sprite2D:
   ```gdscript
   # Instead of:
   var bg = ColorRect.new()
   bg.size = Vector2(GlobalConfig.TILE_SIZE - 1, GlobalConfig.TILE_SIZE - 1)
   bg.color = TILE_COLORS.get(kind, Color.WHITE)

   # Use:
   var sprite = Sprite2D.new()
   sprite.texture = SpriteRegistry.get_tile_texture(kind)
   sprite.centered = false  # Position from top-left
   # Keep the ColorRect as fallback if texture is null
   ```

2. **`_on_item_spawned()`** — Replace the 12x12 ColorRect with a Sprite2D:
   ```gdscript
   # Instead of:
   var item_node = ColorRect.new()
   item_node.size = Vector2(12, 12)
   item_node.color = STAGE_COLORS.get(...)

   # Use:
   var item_node = Sprite2D.new()
   item_node.texture = SpriteRegistry.get_item_texture(item_data.get("stage", "raw"))
   item_node.centered = false
   ```

3. **`_on_item_moved()`** — Update sprite texture when stage changes (item goes from raw to processed, etc.)

4. **Keep fallback rendering** — If a texture is null (missing sprite), fall back to the existing ColorRect approach. This ensures the game still works while sprites are being created.

5. **Keep direction arrows** — The rotation arrow labels should remain on top of sprite tiles.

6. **Keep kind labels** — The small abbreviation labels (BLT, PRC, OVN) should remain as overlays for now, can be removed later when sprites are self-explanatory.

### Don't Change

- SimulationCore.gd — no changes needed, it's headless
- PlayerController.gd — no changes needed
- GameHUD.gd — no changes needed
- Signal flow — keep the same signal connections

## Validation

1. Run the game graphically and verify tiles show sprites instead of plain colors
2. Verify items still animate/tween when moving between tiles
3. Verify the headless test still passes (no rendering in headless mode)
4. Verify fallback works: temporarily rename a sprite file and confirm the tile still renders (as ColorRect fallback)

## Files to Modify

- `/home/flax/games/pizzatorio/v2_godot/src/scenes/FactoryFloor.gd` — main changes here
- `/home/flax/games/pizzatorio/v2_godot/src/scenes/FactoryFloor.tscn` — may need SpriteRegistry reference

## Files to Read (for context)

- `/home/flax/games/pizzatorio/v2_godot/src/data/SpriteRegistry.gd` — created by sprite-pipeline agent
- `/home/flax/games/pizzatorio/v2_godot/src/autoloads/GlobalConfig.gd` — TILE_SIZE constant
