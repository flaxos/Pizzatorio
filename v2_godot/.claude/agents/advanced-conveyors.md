---
name: advanced-conveyors
description: Implement splitters, inserters, and priority lanes for advanced logistics
---

# Advanced Conveyor Features

## Goal

Add three new tile types that create Factorio-style logistics puzzles: **Splitters**, **Inserters**, and **Priority Lanes**. These transform the simple linear conveyor belt into a real logistics network.

## Design Spec (from AI_AGENT_HELPER.md)

The game targets "Factorio-quality logistics puzzles." The current system only has straight conveyors that move items in one direction. Advanced conveyors add branching, filtering, and prioritization.

## New Tile Types

### 1. Splitter

**Kind:** `"splitter"`
**Cost:** 40
**Behavior:** Takes items from one input direction and alternates output between two directions (rotation-based: primary = forward, secondary = 90° clockwise).

```
  Input → [SPLITTER] → Output A (forward, odd items)
                      ↓ Output B (90° CW, even items)
```

- Maintains an internal toggle (even/odd counter)
- If one output is blocked (no valid tile), all items go to the other output
- Visual: split arrow icon

### 2. Inserter

**Kind:** `"inserter"`
**Cost:** 60
**Behavior:** Picks items from an adjacent tile and places them onto another adjacent tile. Works perpendicular to conveyor flow — pulls items OFF a belt and pushes them ONTO a parallel belt or into a machine.

```
  Belt A →→→→→→→
                ↑ [INSERTER] (grabs from Belt A, places on Belt B)
  Belt B →→→→→→→
```

- Has a `source_dir` (where to grab from) and `dest_dir` (where to place) based on rotation
- Only moves one item per cycle (slower than conveyors)
- Speed affected by turbo_belts research
- Essential for feeding assembly tables from multiple ingredient lines

### 3. Priority Lane

**Kind:** `"priority_lane"`
**Cost:** 30
**Behavior:** Like a conveyor, but items on priority lanes move 50% faster and get preferential routing at splitters (always take the primary output).

- Items on priority lanes get a `priority: true` flag
- Splitters check this flag: priority items always go forward
- Visual: conveyor with highlighted/gold stripe

## Implementation Plan

### Step 1: Register New Tile Types

In `GlobalConfig.gd`:
```gdscript
const SPLITTER: String = "splitter"
const INSERTER: String = "inserter"
const PRIORITY_LANE: String = "priority_lane"
```

Add to `MACHINE_BUILD_COSTS`:
```gdscript
"splitter": 40,
"inserter": 60,
"priority_lane": 30,
```

### Step 2: Splitter Logic in SimulationCore

In `_process_items()`, when an item completes progress on a splitter tile:

```gdscript
# Splitter state tracking
var splitter_toggles: Dictionary = {}  # Vector2i -> bool (alternates)

# In movement logic:
if tile["kind"] == GC.SPLITTER:
    var pos = Vector2i(item["x"], item["y"])
    var toggle = splitter_toggles.get(pos, false)
    splitter_toggles[pos] = !toggle

    var primary_dir = GC.DIRS.get(tile["rot"], Vector2i(1, 0))
    var secondary_rot = (tile["rot"] + 1) % 4  # 90° CW
    var secondary_dir = GC.DIRS.get(secondary_rot, Vector2i(0, 1))

    # Priority items always go primary
    if item.get("priority", false) or toggle:
        dir_vec = primary_dir
    else:
        dir_vec = secondary_dir
```

### Step 3: Inserter Logic

Inserters don't use the normal item movement. Instead, they operate on a timer:

```gdscript
var inserter_timers: Dictionary = {}  # Vector2i -> float

func _process_inserters(dt: float) -> void:
    for y in range(GC.GRID_H):
        for x in range(GC.GRID_W):
            if grid[y][x]["kind"] != GC.INSERTER:
                continue
            var pos = Vector2i(x, y)
            var timer = inserter_timers.get(pos, 0.0) + dt
            if timer < 1.0:  # 1 second cycle
                inserter_timers[pos] = timer
                continue
            inserter_timers[pos] = 0.0

            # Grab from source tile, place on dest tile
            var rot = grid[y][x]["rot"]
            var source_dir = GC.DIRS.get((rot + 2) % 4)  # Behind
            var dest_dir = GC.DIRS.get(rot)  # Forward
            _try_inserter_transfer(pos, source_dir, dest_dir)
```

### Step 4: Priority Lane

Simple: in `_process_items()`, when on a priority_lane tile:
- Set `item["priority"] = true`
- Apply 1.5x speed multiplier
- Movement direction works same as conveyor

### Step 5: Build Tool Integration

In `PlayerController.gd`, add keys 7-9 (or extend the existing tool cycle) for the new tile types.

### Step 6: Visual Representation

In `FactoryFloor.gd`, add colors/sprites for the new tiles:
```gdscript
"splitter": Color(0.75, 0.75, 0.55),       # Olive/split
"inserter": Color(0.85, 0.70, 0.55),        # Tan/mechanical
"priority_lane": Color(0.90, 0.82, 0.55),   # Gold stripe
```

## Files to Modify

- `/home/flax/games/pizzatorio/v2_godot/src/autoloads/GlobalConfig.gd` — new constants + costs
- `/home/flax/games/pizzatorio/v2_godot/src/game/SimulationCore.gd` — splitter/inserter/priority logic
- `/home/flax/games/pizzatorio/v2_godot/src/scenes/FactoryFloor.gd` — visual representation
- `/home/flax/games/pizzatorio/v2_godot/src/scenes/PlayerController.gd` — build tool bindings

## Files to Read (for context)

- `/home/flax/games/pizzatorio/v2_godot/src/autoloads/GlobalConfig.gd` — existing tile constants
- `/home/flax/games/pizzatorio/v2_godot/src/game/SimulationCore.gd` — existing item processing
- `/home/flax/games/pizzatorio/AI_AGENT_HELPER.md` — design vision

## Validation

1. Headless test must still pass
2. Add test cases:
   - Splitter alternates items between two outputs
   - Inserter transfers item from one belt to another
   - Priority lane items move faster and get splitter priority
3. Run 200+ ticks headless to verify no item duplication or loss
4. Verify save/load works with new tile types (splitter_toggles and inserter_timers in to_dict/load_from_dict)

## Constraints

- Keep SimulationCore headless — no rendering code
- New state (splitter_toggles, inserter_timers) must be serialized in to_dict/load_from_dict
- Don't break existing conveyor/processor/oven flow
- Inserter cycle time should be affected by turbo_belts research
