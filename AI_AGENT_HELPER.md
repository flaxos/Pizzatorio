# PIZZATORIO — Master Codex Prompt & AI Agent Build Plan

> **Header Notes**
> - Read `AI_QUICKSTART.md` first for execution tasks.
> - Keep this file as long-term design reference only.

> **Agent Runtime Notes**
> - This project is a Pygame desktop app, not a web app.
> - Do not use browser automation to validate gameplay loop.
> - Use `python main.py --headless --ticks <n> --dt <d>` for automated checks.
> - Graphical run requires a display session and manual quit.

> **Purpose:** This document is the single source of truth for any AI coding agent (Codex, Claude, etc.) working on Pizzatorio. It defines the complete vision, scope, architecture, asset conventions, gameplay systems, and implementation roadmap. Every task issued to the agent should reference this document for context.

---

## 1. PROJECT IDENTITY

**Name:** Pizzatorio  
**Genre:** Factory-automation tycoon (Factorio-meets-pizza)  
**Engine:** Python 3.10+ / Pygame 2.x (desktop-first, Pydroid-compatible)  
**Repo:** `https://github.com/flaxos/Pizzatorio`  
**Style Target:** Factorio-quality icon-driven 2D with clean, readable sprites at 32×32 / 64×64 tile resolution. Every ingredient, machine, and product must be instantly recognisable at a glance on a zoomed-out factory floor.

---

## 2. CURRENT STATE (Baseline from existing `main.py`)

The prototype is a single monolithic `main.py` (~single file). It already has:

| Feature | Status | Notes |
|---------|--------|-------|
| Grid-based factory floor | ✅ Working | Tile placement with conveyors, processors, ovens, bot docks |
| Build controls (1-5, R, click) | ✅ Working | Place / rotate / delete |
| Multi-stage food pipeline | ✅ Basic | Source → Processor → Oven → Sink delivery |
| Tech tree (XP-driven unlocks) | ✅ Skeleton | Ovens, bots, turbo belts |
| KPI panel | ✅ Basic | Bottleneck %, hygiene %, throughput, SLA |
| Delivery system (drone/scooter) | ✅ Basic | Travel time + SLA tracking |
| Save / Load (JSON) | ✅ Working | `midgame_save.json` |
| Headless simulation mode | ✅ Working | CLI flags `--headless --ticks --dt` |
| Expansion tiers | ✅ Skeleton | Triggered by cumulative production |

### Critical Gaps to Address

1. **No modular architecture** — everything is in one file
2. **No real ingredient variety** — generic "food" blobs, not distinct pizza ingredients
3. **No sprite/icon system** — coloured rectangles only
4. **No recipe system** — no concept of combining multiple processed ingredients
5. **No customer/order system** — deliveries aren't tied to specific pizza orders
6. **No money/economy** — no purchasing, pricing, or profit loop
7. **No research tree depth** — three unlocks total
8. **No multi-shop expansion** — single factory floor only
9. **No UI/UX polish** — raw debug KPI panel only
10. **No sound** — completely silent

---


### Recent UI Scaffolding Direction (Pydroid + Landscape)

- Add a **menu + submenu shell** in the in-game HUD for: `Build`, `Orders`, `R&D`, `Commercials`, and `Info`.
- Ensure `Orders` exposes channels for `Delivery`, `Takeaway`, and `Eat-in` as selectable UI context.
- Add direct **rotation controls** beyond keyboard-only flow (e.g., visible rotation actions in toolbar/chips).
- Prefer a **landscape-first layout** on Pydroid: keep grid unobstructed, move dense status/action controls into a right-side operations panel when aspect ratio is wide.
- This scaffolding is a structural UI phase; each menu can start with placeholders, then wire real gameplay systems progressively.

## 3. GAME VISION — THE FULL LOOP

### 3.1 One-Sentence Pitch

> Build and automate pizza factories — from kneading dough to boxing deliveries — then expand into a food-processing empire with a deep research tree, tycoon economics, and Factorio-style logistics puzzles.

### 3.2 Core Gameplay Loop

```text
┌─────────────────────────────────────────────────────────────────┐
│                     THE PIZZATORIO LOOP                        │
│                                                                 │
│  ORDERS ARRIVE (customer demand)                                │
│       ↓                                                         │
│  RAW INGREDIENTS ENTER (flour, tomatoes, cheese, meats, veg)    │
│       ↓                                                         │
│  PROCESSING STAGES (knead, chop, slice, grate, mix, cook)       │
│       ↓                                                         │
│  ASSEMBLY (place toppings on prepared base in correct order)     │
│       ↓                                                         │
│  COOKING (oven with temperature + time management)              │
│       ↓                                                         │
│  FINISHING (cut, box, label)                                    │
│       ↓                                                         │
│  DELIVERY (scooter/drone/truck with SLA deadlines)              │
│       ↓                                                         │
│  REVENUE → REINVEST → RESEARCH → EXPAND → MORE ORDERS          │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Tycoon Layer

- **Money:** Earn per delivery, pay for ingredients, machines, staff, rent, research
- **Reputation:** On-time + quality builds rep → unlocks harder/more profitable orders
- **Expansion:** Buy adjacent lots, open satellite shops, franchise system
- **Competition events:** Rival pizzerias, food inspections, seasonal rushes

---

## 4. INGREDIENT & RECIPE SYSTEM (The Heart of the Game)

### 4.1 Master Ingredient Table

Every ingredient exists in multiple **stages**. Each stage has a distinct sprite icon. Items move through stages via specific machines.

#### Base Ingredients

| Raw Input | Stage 1 (Processed) | Stage 2 (Prepared) | Machine Required |
|-----------|---------------------|---------------------|------------------|
| Flour Bag | Dough Ball | Rolled Pizza Base | Kneader → Roller |
| Tomato (whole) | Crushed Tomato | Tomato Sauce | Crusher → Sauce Mixer |
| Cheese Block | Shredded Cheese | — | Grater |
| Mozzarella Ball | Sliced Mozzarella | — | Slicer |

#### Meat Toppings

| Raw Input | Stage 1 (Processed) | Machine Required |
|-----------|---------------------|------------------|
| Ham Joint | Chopped Ham | Chopper |
| Pepperoni Log | Sliced Pepperoni | Slicer |
| Chicken Breast | Diced Chicken | Chopper → (optional: Grill) |
| Bacon Slab | Bacon Strips | Slicer |
| Ground Beef | Cooked Beef Crumble | Fryer |
| Sausage Link | Sliced Sausage | Slicer |
| Anchovy Tin | Anchovy Fillets | — (pre-processed, premium cost) |

#### Vegetable Toppings

| Raw Input | Stage 1 (Processed) | Machine Required |
|-----------|---------------------|------------------|
| Pineapple (whole) | Pineapple Chunks | Chopper |
| Bell Pepper (whole) | Sliced Pepper | Slicer |
| Onion (whole) | Diced Onion | Chopper |
| Mushroom (whole) | Sliced Mushroom | Slicer |
| Olive Jar | Sliced Olives | Slicer |
| Jalapeño (whole) | Sliced Jalapeño | Slicer |
| Spinach Bunch | Washed Spinach | Washer |
| Corn Can | Corn Kernels | — (pre-processed) |
| Garlic Bulb | Minced Garlic | Crusher |
| Basil Plant | Fresh Basil Leaves | — (hand-pick / no machine) |
| Artichoke (whole) | Artichoke Hearts | Chopper |
| Rocket Bag | Rocket Leaves | — (post-oven garnish) |

### 4.2 Pizza Assembly Sequence

Assembly is the core puzzle. Pizzas must be built in the **correct layer order** on an Assembly Table:

```text
Layer 1:  Rolled Pizza Base          (from Roller)
Layer 2:  Sauce                      (from Sauce Mixer)
Layer 3:  Base Cheese                (from Grater)
Layer 4:  Toppings (1-5 items)       (from various processors)
Layer 5:  [Optional] Extra Cheese    (from Grater)
          ↓
       INTO OVEN (temperature + cook time)
          ↓
Layer 6:  [Optional] Post-oven garnish (Rocket, Fresh Basil)
          ↓
       CUTTING STATION → BOXING STATION → DELIVERY
```

**Assembly Tables** accept items from conveyors in specific **input slots** (left = base, top = sauce, right = toppings). Incorrect order = rejected / waste. This creates the logistics puzzle.

### 4.3 Recipe Definitions (Examples)

Each recipe is a data-driven definition the agent should implement as JSON/dict configs:

```python
RECIPES = {
    "margherita": {
        "display_name": "Margherita",
        "base": "rolled_pizza_base",
        "sauce": "tomato_sauce",
        "cheese": "sliced_mozzarella",
        "toppings": ["fresh_basil"],
        "post_oven": [],
        "cook_time": 8.0,
        "cook_temp": "medium",
        "sell_price": 12,
        "difficulty": 1,
        "unlock_tier": 0
    }
}
```

**Target: 20-30 recipes across unlock tiers, each requiring distinct logistics paths.**

---

## 5. MACHINE & BUILDING CATALOGUE

Includes processing machines, assembly/cooking, logistics, and utility building plans as the long-term implementation roadmap for agents.

---

## 6. RESEARCH TREE (Full Design)

Use this as the long-term progression design authority.

- Branches: Logistics, Automation, Cooking, Recipes, Expansion
- Uses Research Points (RP)
- Tiers progressively unlock speed, automation depth, content breadth, and scaling systems

---

## 7. GRAPHICS & ICON SPECIFICATION

- Factorio-inspired top-down icon readability
- Programmatic 32×32 icon generation first, optional artist replacement later
- Distinct silhouettes and stage differentiation for every ingredient state
- Palette and machine icon concepts should guide rendering consistency

---

## 8. ARCHITECTURE PLAN (Code Refactor)

Target module split:

```text
pizzatorio/
├── main.py
├── config.py
├── game/
├── ui/
├── sprites/
├── audio/
├── data/
└── tests/
```

Principles:
1. Data-driven definitions
2. Simulation-first (headless capable)
3. Lightweight entity-component patterns
4. Event bus decoupling
5. Fixed-tick deterministic simulation

---

## 9. ECONOMY & TYCOON SYSTEMS

Use this section as the reference for income/expense loops, reputation, and scale-up mechanics.

---

## Agent Usage Notes

- Treat this file as the default reference context for all implementation tasks.
- If a direct user task conflicts with this file, follow the direct user task.
- When unsure, preserve simulation determinism and data-driven content additions.

### Delivery Phase & Reporting Protocol

Use the following execution phases to keep implementation updates consistent and auditable:

- **Planning**: clarify scope, constraints, and architecture impact
- **Building**: implement data-driven features and modular changes
- **Stabilizing**: validate deterministic behavior, headless compatibility, and regressions
- **Shipping**: finalize change notes, commit, and PR metadata
- **Next Phase**: define trigger conditions and concrete follow-up plan

Status updates should use this structure:

```text
STATUS REPORT
- What was done:
  - <completed implementation items>
- What was shipped:
  - <items merged/released and commit or PR reference>
- Bugs fixed:
  - <bug + root cause + fix + validation>
- In progress:
  - <active tasks>
- Blockers/Risks:
  - <technical/product risks>
- Next phase trigger:
  - <condition that moves us to the next phase>
- Next phase plan:
  - <3-7 bullet execution plan>
```

When moving between phases, print:

```text
NEW PHASE ENTERED: <phase name>
REASON: <why we moved>
```
