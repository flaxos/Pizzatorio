# Pizzatorio

A lightweight factory/automation prototype designed to run in **Pydroid on Android** and on desktop Python.

## Features implemented
- Running factory with moving items on conveyors.
- Build controls:
  - `1` conveyor
  - `2` machine
  - `3` delete
  - `R` rotate selected part
  - Left click to place/delete
- KPI panel updates live:
  - Bottleneck percentage
  - Hygiene percentage (random hygiene events + recovery)
  - Throughput/SLA on-time rate
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
