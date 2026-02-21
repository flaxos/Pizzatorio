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
  - `R` rotate selected part
  - Left click to place/delete
- Progression systems:
  - Tech tree unlocks (`ovens`, `bots`, `turbo belts`) driven by production XP.
  - Expansion tiers increase as your factory runs and fulfills demand.
- KPI panel updates live:
  - Bottleneck percentage
  - Hygiene percentage (random hygiene events + recovery)
  - Throughput/SLA on-time rate
  - Tech unlock states, XP, and expansion tier
- Deliveries are launched from sink as either **drone** or **scooter** with travel time and SLA.
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
