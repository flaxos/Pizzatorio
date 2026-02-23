# AI Quickstart (Operational Only)

## Entry points
- Main runtime entry point: `main.py`
- Core simulation modules: `game/simulation.py` and `game/entities.py`
- Data/catalog loaders used by runtime: `*_catalog.py` plus `data/*.json`

## Headless command
- Run automated simulation checks with:
  - `python main.py --headless --ticks 300 --dt 0.1`

## Where tests live
- Pytest suite location: `tests/`
- Typical run command:
  - `pytest -q`

## Do not run browser app
- This project is a Pygame desktop app, not a browser/web app.
- Do **not** run browser-based automation for gameplay validation.

## Minimal PR checklist
- Keep changes scoped to the requested task.
- Run relevant checks (`pytest -q` and/or headless run).
- Update docs if behavior or workflow changed.
- Ensure commit message clearly states what changed.
