---
name: assembly-table
description: Implement multi-ingredient pizza assembly mechanics on the Assembly Table
---

# Assembly Table Mechanics

## Goal

Wire up the Assembly Table as the core pizza-building mechanic. Currently `assembly_table` exists as a tile kind in GlobalConfig and SimulationCore handles it as a basic pass-through (just slows items to 0.6 speed). It needs to become a multi-input combiner that assembles pizza recipes from individual processed ingredients.

## Design Spec (from AI_AGENT_HELPER.md)

Assembly Tables accept items from conveyors. Pizzas must be built in correct **layer order**:

```
Layer 1: Rolled Pizza Base (base ingredient, processed stage)
Layer 2: Sauce (processed stage)
Layer 3: Base Cheese (processed stage)
Layer 4: Toppings 1-5 (processed stage)
Layer 5: [Optional] Extra Cheese
→ Output: assembled pizza (stage: "assembled") → goes to Oven
```

## Implementation Plan

### 1. Assembly Table State in SimulationCore

Add per-tile assembly state tracking:

```gdscript
# New state in SimulationCore
var assembly_state: Dictionary = {}  # Vector2i -> { "recipe_key": String, "layers": Array, "progress": float }
```

When a tile is set to `assembly_table`, initialize its assembly state. When removed, clean it up.

### 2. Assembly Logic in `_process_items()`

When an item reaches an assembly_table tile:

1. **If table is empty and item is a base ingredient (dough/pizza_base):**
   - Start a new assembly. Match against available recipes from RecipeCatalog.
   - Store the item as layer 1.

2. **If table has an in-progress assembly:**
   - Check if the incoming item matches the next required layer for the current recipe.
   - If yes: add to assembly, advance layer count.
   - If no: reject item (push back or waste it).

3. **If assembly is complete (all layers present):**
   - Output an assembled item with `stage: "assembled"` and the `recipe_key` set.
   - The assembled item continues down the conveyor to an oven.
   - Add a new stage `"assembled"` between `"processed"` and `"baked"` in the pipeline.

### 3. Recipe Matching

Use `RecipeCatalog.get_required_products(recipe_key)` to determine what ingredients are needed. The assembly table should try to match the simplest available recipe first, or allow the player to set a recipe target per table.

### 4. New Item Stage

Add `"assembled"` to the stage pipeline:
- In `GlobalConfig.gd`: update `ITEM_STAGE_ORDER` to `["raw", "processed", "assembled", "baked"]`
- In `PROCESS_FLOW`: the oven should accept `"assembled"` → `"baked"` (in addition to or instead of `"processed"` → `"baked"`)

### 5. Signals

Add new signal to SimulationCore:
```gdscript
signal assembly_progress(pos: Vector2i, recipe_key: String, layers_complete: int, layers_total: int)
signal assembly_completed(pos: Vector2i, recipe_key: String)
```

### 6. Multiple Input Directions

The assembly table should accept items from multiple directions (not just the tile's rotation direction). Items arriving from any adjacent conveyor should be consumed if they match the recipe requirements.

## Files to Modify

- `/home/flax/games/pizzatorio/v2_godot/src/game/SimulationCore.gd` — core assembly logic
- `/home/flax/games/pizzatorio/v2_godot/src/autoloads/GlobalConfig.gd` — add "assembled" stage, update PROCESS_FLOW
- `/home/flax/games/pizzatorio/v2_godot/src/data/RecipeCatalog.gd` — may need `get_required_products()` or `get_layer_sequence()` method

## Files to Read (for context)

- `/home/flax/games/pizzatorio/v2_godot/src/data/IngredientRegistry.gd` — ingredient types and processing chains
- `/home/flax/games/pizzatorio/v2_godot/src/data/RecipeCatalog.gd` — recipe definitions
- `/home/flax/games/pizzatorio/AI_AGENT_HELPER.md` — full assembly spec (section 4.2)

## Validation

1. Headless test should still pass after changes
2. Add new test cases to `test_headless.gd`:
   - Place an assembly table, feed it a base + sauce + cheese → verify assembled item output
   - Feed wrong ingredient → verify rejection
3. Run 100+ ticks headless and verify no crashes or item duplication
4. Verify orders can now be fulfilled through the full pipeline: source → processor → assembly_table → oven → sink

## Constraints

- Keep SimulationCore headless — no rendering code
- Assembly state must be included in `to_dict()` / `load_from_dict()` for save/load
- Don't break existing item flow for items that bypass assembly (backward compatible)
