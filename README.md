# Pizzatorio

A lightweight factory/automation prototype designed to run in **Pydroid on Android** and on desktop Python.

## Features implemented
- Multi-stage food pipeline:
  - Ingredients spawn from source.
  - Processors convert raw ingredients into prepared ingredients.
  - Ovens cook prepared ingredients into finished food.
  - Bot docks boost final-mile delivery speed.
- Build controls:
  - `1` conveyor
  - `2` processor
  - `3` oven *(unlocks from research)*
  - `4` bot dock *(unlocks from research)*
  - `5` delete
  - `R` / `Q` / `E` rotate selected part
  - Left click to place/delete
- Progression systems:
  - Tech tree unlocks now follow prerequisite chains across branches (e.g., `turbo_oven` needs `ovens`, `franchise_system` needs expansion + logistics unlocks), all data-driven from `data/research.json`.
  - Expansion tiers increase as your factory runs and fulfills demand.
- UI scaffolding includes menu + submenu chips (`Build`, `Orders`, `R&D`, `Commercials`, `Info`) and quick order-channel context (`Delivery`, `Takeaway`, `Eat-in`) for the upcoming overhaul.
- Commercial submenu actions are now wired to lightweight campaign strategies (`Campaigns`, `Promos`, `Franchise`) that charge cash once on activation and modify order demand/reward behavior.
- Order channels now carry distinct late-delivery and missed-order penalty tuning (data-driven in `data/order_channels.json`) so Delivery/Takeaway/Eat-in are economically different playstyles.
- Landscape-aware layout adds a right-side operations panel on wide displays (including Pydroid landscape) to keep controls and metrics visible.
- `Info` submenu now shows context-aware data: KPI snapshot, recent event log, and economy telemetry (revenue/spend/net + waste) to reduce UI dead-ends while systems are being wired.
- KPI panel updates live:
  - Bottleneck percentage
  - Hygiene percentage (random hygiene events + recovery)
  - Throughput/SLA on-time rate
  - Tech unlock states, XP, and expansion tier
- Deliveries are launched from sink as either **drone** or **scooter** with travel time and SLA.
- Customer orders are now generated from a small **data-driven recipe catalog** and fulfilled FIFO from produced pizzas.
- Recipe catalog entries are loaded from `data/recipes.json` with validation + fallback defaults for headless-safe simulation.
- Basic economy loop tracks **cash rewards** for fulfilled deliveries and **waste** when pizzas are produced without pending orders.
- Save/load to `midgame_save.json` using:
  - `S` save
  - `L` load
- Headless mode (no graphics) for simulation/testing.

## Run (graphical)
```bash
python main.py
```

## Run headless
```bash
python main.py --headless --ticks 1200 --dt 0.1
```

## Load saved game
```bash
python main.py --load
```

## Pydroid notes
Install pygame in Pydroid pip before running graphical mode:
```bash
pip install pygame
```
If pygame is unavailable, headless mode still works.

## CI quality gate (local preflight)
Before opening a PR, run the same checks used in CI:

```bash
python -m pytest tests/ -v --tb=short
python main.py --headless --ticks 200 --dt 0.1
python main.py --headless --ticks 1000 --dt 0.05
python -m pytest tests/test_recipe_catalog.py -v --tb=short
python - <<'EOF'
import sys
from pathlib import Path
sys.path.insert(0, ".")
from recipe_catalog import load_recipe_catalog

catalog = load_recipe_catalog(Path("data/recipes.json"))
assert len(catalog) >= 20, f"Expected >=20 recipes, got {len(catalog)}"

tiers = {r["unlock_tier"] for r in catalog.values()}
assert 0 in tiers, "Must have tier-0 (starter) recipes"
assert max(tiers) >= 2, "Must span at least 3 unlock tiers"

for key, recipe in catalog.items():
    assert recipe["sell_price"] >= 1, f"{key}: sell_price must be >= 1"
    assert recipe["sla"] > 0, f"{key}: sla must be positive"
    assert recipe["demand_weight"] > 0, f"{key}: demand_weight must be positive"
    assert len(recipe["toppings"]) >= 1, f"{key}: must have at least 1 topping"

print(f"OK: {len(catalog)} recipes validated across tiers {sorted(tiers)}")
EOF
```
