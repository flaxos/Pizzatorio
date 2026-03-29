# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Pizzatorio — a factory-automation tycoon where you build and automate pizza production lines, then expand vertically up the supply chain into a food empire. Core inspiration: **Factorio mechanics** (belts, splitters, inserters, logistics puzzles) + **Transport Tycoon / OpenTTD** (network building, delivery routing) + **tycoon/empire sim economics** (R&D, franchising, supply chain ownership).

## Game Vision

You start as a single pizza shop. Raw ingredients arrive, you assemble pizzas on belts, and deliver via drones/robots to meet customer demand. As you grow:

1. **Pizza Shop** — Place conveyors, processors, ovens, assembly tables. Fulfill orders under SLA pressure.
2. **Supply Chain** — You run out of room. Build a dough factory offsite. Ship raw ingredients in, processed products out. Same for sauce, cheese processing.
3. **Vertical Integration** — Acquire farms (wheat, tomatoes). Automate harvesting with robots. Raw materials flow from your farms → your factories → your pizza shops.
4. **Empire** — Sell franchises, take over competitor stores, run multiple factories and shops. Control the entire ingredient-to-delivery pipeline.

**The fun is the Factorio part** — the logistics puzzle of routing ingredients through splitters, mergers, priority lanes, inserters, and assembly stations. R&D progressively automates everything until you control all ingredients for every production line.

**Delivery** uses flying drones and delivery robots — not human drivers. This is a robotic automated food delivery chain.

## Workflow

**Claude Code** handles code, architecture, and game logic. **Google Antigravity** generates pixel art sprites and visual assets. Both work in tandem — sprites drop into `assets/sprites/` and SpriteRegistry picks them up automatically.

## Commands

```bash
# Run the game
~/bin/godot --path ~/games/pizzatorio/v2_godot

# Run headless tests
~/bin/godot --headless --script res://test_headless.gd

# Generate placeholder sprites
python3 tools/generate_placeholders.py
```

## Project Status

**Phase: Core Mechanics — Foundation Complete, Systems Need Wiring**

### Working
- SimulationCore: tick-based engine with items, orders, deliveries, economy, hygiene, research
- 11 tile types: conveyor, processor, oven, bot_dock, assembly_table, splitter, inserter, priority_lane, source, sink, empty
- Assembly table: multi-ingredient pizza assembly with recipe matching
- 21 ingredient types with weighted spawning and processing chains
- 3 recipes (margherita, pepperoni, veggie) with tier-based unlocking
- 10-node tech tree with prerequisite chains
- Sprite pipeline with Antigravity-generated pixel art + SpriteRegistry
- Save/load, headless tests passing, HUD overlay

### Defined But Not Wired
These systems have data catalogs and config values but the simulation logic doesn't use them yet:
- **Order channel modifiers** — reward/SLA multipliers exist in OrderChannelCatalog but never applied
- **Commercial strategies** — 3 strategies defined (campaigns, promos, franchise) but no activation/effect logic
- **Expansion tiers** — expansion_level field exists but never progresses; recipe unlock tiers defined but gated on a value that never changes
- **Many research effects** — turbo_oven, precision_cooking, priority_dispatch bonuses defined in GlobalConfig but not integrated
- **Demand weighting** — recipes have demand_weight but orders spawn uniformly
- **Bot auto-delivery** — auto_bot_charge field exists but no autonomous bot behavior
- **Waste refund** — waste counted but precision_cooking refund never applied

### Not Yet Built
- **Multi-location** — only one factory floor (need: farm, sauce factory, dough factory, multiple shops)
- **Supply chain network** — no inter-location transport of goods
- **Franchise/takeover system** — no selling or acquiring locations
- **Drone/robot delivery simulation** — deliveries are just timers, no visual pathing
- **More recipes** — need 15-20+ for depth
- **Audio** — completely silent
- **Build mode feedback** — no green/red placement preview
- **Research/channel/commercial UI** — no player-facing panels for these systems

## Architecture

### Core Principle: Decoupled Simulation

`SimulationCore.gd` contains **zero rendering logic**. Pure tick-based engine that emits signals. **Do not add rendering/UI code to SimulationCore or data classes.**

### Autoload Singletons

- **GlobalConfig** — All constants and tuning values. Primary tuning surface.
- **EventBus** — Signal bus for cross-system communication.
- **TimeManager** — Fixed-rate tick driver (0.5s/tick). `--headless` flag for 10x speed.

### Scene Tree

```
Main (Node)
├── FactoryFloor (Node2D)          — Visual grid renderer
│   ├── SimulationCore (Node)      — Headless game engine, all state lives here
│   └── PlayerController (Node2D)  — Input: build (1-9), rotate (R), camera, save/load
└── GameHUD (CanvasLayer)          — UI overlay: money, rep, research, orders, event log
```

### Data Layer (`src/data/`)

Data-driven catalogs — all game content defined as data, not code:

| File | Purpose |
|------|---------|
| IngredientRegistry.gd | 21 ingredients with spawn weights, costs, processing chains |
| RecipeCatalog.gd | Pizza recipes with components, pricing, tier unlocks |
| ResearchCatalog.gd | 10-node tech tree with prerequisites and costs |
| OrderChannelCatalog.gd | Delivery/takeaway/eat-in with SLA and reward modifiers |
| CommercialCatalog.gd | Marketing strategies with demand/reward multipliers |
| SpriteRegistry.gd | Texture lookup with per-ingredient and per-stage sprites |

### Signal Flow

```
TimeManager ──on_tick──→ SimulationCore.sim_tick()
SimulationCore ──grid/item/economy signals──→ FactoryFloor + GameHUD
PlayerController ──place_tile()──→ SimulationCore
EventBus ──show_notification──→ GameHUD
```

### Save System

JSON via `SimulationCore.to_dict()` / `load_from_dict()`. Ctrl+S / Ctrl+L.

## Agents (`.claude/agents/`)

| Agent | Purpose | Status |
|-------|---------|--------|
| `fix-headless-tests` | Fix SceneTree init bug | Done |
| `sprite-pipeline` | Asset directory + SpriteRegistry | Done |
| `wire-sprites` | Sprite2D rendering in FactoryFloor | Done |
| `assembly-table` | Multi-ingredient assembly mechanics | Done |
| `advanced-conveyors` | Splitters, inserters, priority lanes | Done |

## Relationship to Python Version

Parent directory (`~/games/pizzatorio/`) has the original Pygame prototype (199 tests, complete but basic). The Godot port supersedes it. Parent's `AI_AGENT_HELPER.md` has the full ingredient table, recipe specs, and research tree design — still valid as reference.
