# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Godot 4.4 port of Pizzatorio — a factory/automation game (Factorio meets pizza tycoon). Refactored from a Pygame-based Python prototype in the parent directory. Multi-stage pizza production: ingredients flow through conveyors, processors, ovens, and bot docks to fulfill customer orders.

## Project Status

**Phase: Early Godot Port — Scaffold Complete, Visuals Placeholder**

The Python prototype (`~/games/pizzatorio/`) has 199 passing tests and complete game logic, but graphics are colored rectangles. The decision was made to migrate to Godot for proper game engine capabilities (rendering, physics, sprite system, export targets).

### What's Done (ported to Godot)
- SimulationCore with full tick-based game loop (items, orders, deliveries, research, economy, hygiene)
- All 5 data catalogs (ingredients, recipes, research, order channels, commercials)
- Grid-based factory floor renderer with color-coded tiles and item stage visualization
- Player input: build tools (1-6), rotation, camera pan/zoom, save/load
- HUD overlay (money, reputation, research, orders, event log, notifications)
- Headless test runner (partially working — has a SceneTree init bug to fix)
- Autoload singletons (GlobalConfig, EventBus, TimeManager)

### What's NOT Done Yet
- **Sprites/art assets** — everything is still colored rectangles (no sprites in `assets/` yet)
- **Assembly table mechanics** — recipe assembly (combining processed ingredients) not fully wired
- **Advanced conveyor logic** — splitters, inserters, priority lanes from the design doc
- **Multi-factory expansion** — single factory floor only
- **Audio** — completely silent
- **Polish** — no animations, particles, or visual feedback beyond basic tweens
- **Export/packaging** — no export presets configured
- **Test runner fix** — `test_headless.gd` has a null SceneTree bug at init

## Workflow

This project uses a combo of **Claude Code** and **Google Antigravity** (image generation for sprites). Claude handles code/architecture, Antigravity handles sprite asset creation.

## Commands

```bash
# Run the game
godot --path /home/flax/games/pizzatorio/v2_godot

# Run headless tests (no display needed)
godot --headless --script res://test_headless.gd --path /home/flax/games/pizzatorio/v2_godot
```

## Architecture

### Core Principle: Decoupled Simulation

`SimulationCore.gd` contains **zero rendering logic**. It is a pure tick-based engine that emits signals consumed by visual nodes. This mirrors the Python version's "headless-first" design. **Do not add rendering/UI code to SimulationCore or data classes.**

### Autoload Singletons (registered in project.godot)

- **GlobalConfig** — All game constants and tuning values (grid size, costs, speeds, thresholds). Primary tuning surface.
- **EventBus** — Centralized signal bus for cross-system communication (tick events, notifications, build requests).
- **TimeManager** — Fixed-rate deterministic tick driver (0.5s/tick). Supports `--headless` CLI flag for 10x speed.

### Scene Tree

```
Main (Node)
├── FactoryFloor (Node2D)          — Visual grid renderer, listens to SimulationCore signals
│   ├── SimulationCore (Node)      — Headless game engine, all game state lives here
│   └── PlayerController (Node2D)  — Input handling: build, rotate, camera pan/zoom, save/load
└── GameHUD (CanvasLayer)          — UI overlay: money, reputation, research, orders, event log
```

### Data Layer (`src/data/`)

All game content is data-driven via catalog/registry classes (all extend `Resource` or are static):

- **IngredientRegistry** — 21 ingredient types with spawn weights, costs, and processing chains
- **RecipeCatalog** — Pizza recipes gated by expansion level and tech tree
- **ResearchCatalog** — 10-node tech tree with prerequisite chains
- **OrderChannelCatalog** — Delivery/takeaway/eat-in channels with SLA and reward tuning
- **CommercialCatalog** — Marketing campaign strategies

### Signal Flow

```
TimeManager ──on_tick──→ SimulationCore.sim_tick()
SimulationCore ──grid_changed, item_spawned/moved/removed──→ FactoryFloor (visual updates)
SimulationCore ──money_changed, order_spawned, etc──→ GameHUD (UI updates)
PlayerController ──place_tile()──→ SimulationCore (state mutations)
EventBus ──show_notification──→ GameHUD (cross-cutting events)
```

### Save System

JSON serialization via `SimulationCore.to_dict()` / `load_from_dict()`. PlayerController handles Ctrl+S/Ctrl+L.

## Headless Testing

`test_headless.gd` runs as a standalone SceneTree (bypasses autoloads). It manually instantiates GlobalConfig and SimulationCore, then verifies grid placement, tile building with cost deduction, tick execution, and serialization. Assertions print pass/fail and exit with code 0/1.

## Agents (`.claude/agents/`)

Task-specific agent definitions for the next implementation phases. Run order matters — some depend on others:

| Agent | Purpose | Dependencies |
|-------|---------|--------------|
| `fix-headless-tests` | Fix SceneTree null bug in test runner | None — do this first |
| `sprite-pipeline` | Create `assets/sprites/` structure + placeholder PNGs + SpriteRegistry.gd | None |
| `wire-sprites` | Replace ColorRects in FactoryFloor with Sprite2D nodes | Requires `sprite-pipeline` |
| `assembly-table` | Multi-ingredient pizza assembly on Assembly Tables | None (core gameplay) |
| `advanced-conveyors` | Splitters, inserters, priority lanes | None (but test after `assembly-table`) |

## Relationship to Python Version

The parent directory (`/home/flax/games/pizzatorio/`) contains the original Pygame version. The v2_godot port preserves the same game design, data structures, and simulation logic. The parent's `CLAUDE.md`, `AI_AGENT_HELPER.md`, and `AI_QUICKSTART.md` document the game design vision and are useful context for understanding intended behavior.
