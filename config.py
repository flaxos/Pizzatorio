"""Centralised configuration constants for Pizzatorio."""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Grid / display
# ---------------------------------------------------------------------------
GRID_W: int = 20
GRID_H: int = 15
CELL: int = 48

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
SAVE_FILE: Path = Path("midgame_save.json")
RECIPES_FILE: Path = Path("data/recipes.json")

# ---------------------------------------------------------------------------
# Tile kind constants
# ---------------------------------------------------------------------------
EMPTY: str = "empty"
CONVEYOR: str = "conveyor"
MACHINE: str = "machine"
PROCESSOR: str = "processor"
OVEN: str = "oven"
BOT_DOCK: str = "bot_dock"
ASSEMBLY_TABLE: str = "assembly_table"
SOURCE: str = "source"
SINK: str = "sink"

# ---------------------------------------------------------------------------
# Item stage ordering
# ---------------------------------------------------------------------------
ITEM_STAGE_ORDER: list[str] = ["raw", "processed", "baked"]

# ---------------------------------------------------------------------------
# Directional movement vectors (rotation index → (dx, dy))
# ---------------------------------------------------------------------------
DIRS: dict[int, tuple[int, int]] = {
    0: (1, 0),
    1: (0, 1),
    2: (-1, 0),
    3: (0, -1),
}

# ---------------------------------------------------------------------------
# Processing flow: which tile kind transforms item stages
# ---------------------------------------------------------------------------
PROCESS_FLOW: dict[str, dict] = {
    PROCESSOR: {"from": "raw", "to": "processed", "research_gain": 0.12},
    OVEN: {"from": "processed", "to": "baked", "research_gain": 0.25},
    BOT_DOCK: {"from": "baked", "to": "baked", "research_gain": 0.06, "delivery_boost": 1.2},
}

# ---------------------------------------------------------------------------
# Tech tree unlock thresholds (tech_key → research_points_required)
#
# Branches:
#   Cooking     — ovens, turbo_oven, precision_cooking
#   Automation  — bots, hygiene_training
#   Logistics   — turbo_belts, priority_dispatch, double_spawn
# ---------------------------------------------------------------------------
TECH_UNLOCK_COSTS: dict[str, float] = {
    # Cooking branch
    "ovens": 12.0,
    "turbo_oven": 40.0,
    "precision_cooking": 95.0,
    # Automation branch
    "bots": 28.0,
    "hygiene_training": 50.0,
    # Logistics branch
    "turbo_belts": 55.0,
    "priority_dispatch": 85.0,
    "double_spawn": 140.0,
}

# ---------------------------------------------------------------------------
# Research effect tuning constants
# ---------------------------------------------------------------------------
TURBO_OVEN_SPEED_BONUS: float = 0.18      # extra oven speed multiplier when turbo_oven unlocked
PRECISION_COOKING_WASTE_REFUND: float = 0.40  # fraction of sell_price refunded on wasted items
HYGIENE_TRAINING_RECOVERY_BONUS: float = 0.30  # extra hygiene/s recovery when unlocked
PRIORITY_DISPATCH_LATE_MULTIPLIER: float = 0.75  # late-delivery reward fraction (vs 0.5 default)
DOUBLE_SPAWN_INTERVAL_DIVISOR: float = 1.75   # divides item spawn interval when unlocked

# ---------------------------------------------------------------------------
# Simulation tuning
# ---------------------------------------------------------------------------
ITEM_SPAWN_INTERVAL: float = 1.8       # seconds between item spawns
ORDER_SPAWN_INTERVAL: float = 5.5      # seconds between order spawns
HYGIENE_EVENT_COOLDOWN: float = 14.0   # minimum seconds between hygiene penalties
HYGIENE_EVENT_CHANCE: float = 0.015    # probability per tick check
HYGIENE_RECOVERY_RATE: float = 0.35    # hygiene per second passive recovery
EXPANSION_PROGRESS_RATE: float = 0.35  # base expansion progress per second
EXPANSION_DELIVERY_BONUS: float = 0.002  # extra expansion progress per completed delivery
EXPANSION_BASE_NEEDED: float = 24.0    # base expansion threshold (× level)
TURBO_BELT_BONUS: float = 0.25         # additional speed multiplier when unlocked
ASSEMBLY_TABLE_SPEED: float = 0.60    # progress speed while tagging at assembly table
BOT_AUTO_CHARGE_RATE: float = 0.18     # auto-bot charge accumulation per dock per second
BOT_AUTO_DELIVERY_REDUCTION: float = 0.8  # seconds reduced from target delivery per bot charge
LATE_DELIVERY_PENALTY: float = 0.5     # fraction of reward paid for late deliveries

# ---------------------------------------------------------------------------
# Ingredient types (canonical item_type identifiers for spawned items)
# ---------------------------------------------------------------------------
INGREDIENT_TYPES: list[str] = [
    "flour",
    "tomato",
    "cheese",
    "pepperoni",
    "ham",
    "chicken",
    "mushroom",
    "pepper",
    "onion",
    "olive",
    "pineapple",
]

# Weighted pool used when spawning ingredients without a specific order context
INGREDIENT_SPAWN_WEIGHTS: dict[str, float] = {
    "flour": 3.0,
    "tomato": 2.5,
    "cheese": 2.5,
    "pepperoni": 1.5,
    "ham": 1.2,
    "chicken": 1.0,
    "mushroom": 1.0,
    "pepper": 0.8,
    "onion": 0.8,
    "olive": 0.7,
    "pineapple": 0.5,
}
