"""Centralised configuration constants for Pizzatorio."""
from __future__ import annotations

from pathlib import Path

from research_catalog import load_research_catalog

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
# Loaded from the data-driven research catalog with safe defaults.
# ---------------------------------------------------------------------------
TECH_UNLOCK_COSTS: dict[str, float] = {
    key: float(entry["cost"]) for key, entry in load_research_catalog().items()
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
# Economy — machine placement costs and starting capital
# ---------------------------------------------------------------------------
STARTING_MONEY: int = 1000             # seed capital given to player at game start

MACHINE_BUILD_COSTS: dict[str, int] = {
    "conveyor":        10,
    "processor":       80,
    "oven":           150,
    "bot_dock":       200,
    "assembly_table": 120,
}

# ---------------------------------------------------------------------------
# Reputation — tracks player standing with customers (0–100)
# ---------------------------------------------------------------------------
REPUTATION_STARTING: float = 50.0      # initial reputation score
REPUTATION_GAIN_ONTIME: float = 0.8    # reputation gained per on-time delivery
REPUTATION_LOSS_LATE: float = 1.5      # reputation lost per late delivery
REPUTATION_LOSS_MISSED_ORDER: float = 1.0  # reputation lost when an order expires before fulfillment
MISSED_ORDER_CASH_PENALTY_MULTIPLIER: float = 0.25  # fraction of reward charged when an order times out

# ---------------------------------------------------------------------------
# Expansion tech effects
# ---------------------------------------------------------------------------
SECOND_LOCATION_REWARD_BONUS: float = 0.15   # +15% delivery reward when unlocked
SECOND_LOCATION_SPAWN_INTERVAL_MULTIPLIER: float = 0.85  # faster order intake when multi-shop is unlocked
SECOND_LOCATION_ORDER_CAPACITY_BONUS: int = 2            # extra concurrent active orders
FRANCHISE_EXPANSION_BONUS: float = 2.0       # multiplier on delivery-driven expansion progress

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
    # Extended ingredient set — covers all recipe toppings
    "jalapeno",
    "artichoke",
    "bacon",
    "sausage",
    "garlic",
    "spinach",
    "corn",
    "anchovy",
    "beef",
    "rocket",
    "basil",
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
    "jalapeno": 0.7,
    "artichoke": 0.4,
    "bacon": 1.0,
    "sausage": 0.8,
    "garlic": 1.2,
    "spinach": 0.6,
    "corn": 0.5,
    "anchovy": 0.3,
    "beef": 0.7,
    "rocket": 0.4,
    "basil": 0.6,
}

# Mapping from raw ingredient type → processed product IDs it can produce.
# Used by the assembly table to validate that an arriving ingredient is
# relevant to the order's recipe before tagging it.
INGREDIENT_TO_PRODUCTS: dict[str, list[str]] = {
    "flour": ["rolled_pizza_base"],
    "tomato": ["tomato_sauce"],
    "cheese": ["shredded_cheese", "sliced_mozzarella"],
    "pepperoni": ["sliced_pepperoni"],
    "ham": ["chopped_ham"],
    "chicken": ["diced_chicken"],
    "mushroom": ["sliced_mushroom"],
    "pepper": ["sliced_pepper"],
    "onion": ["diced_onion"],
    "olive": ["sliced_olives"],
    "pineapple": ["pineapple_chunks"],
    "jalapeno": ["sliced_jalapeno"],
    "artichoke": ["artichoke_hearts"],
    "bacon": ["bacon_strips"],
    "sausage": ["sliced_sausage"],
    "garlic": ["minced_garlic"],
    "spinach": ["washed_spinach"],
    "corn": ["corn_kernels"],
    "anchovy": ["anchovy_fillets"],
    "beef": ["cooked_beef_crumble"],
    "rocket": ["rocket_leaves"],
    "basil": ["fresh_basil"],
}

# Per-item purchase cost when sourcing raw ingredients from SOURCE.
INGREDIENT_PURCHASE_COSTS: dict[str, int] = {
    "flour": 2,
    "tomato": 2,
    "cheese": 3,
    "pepperoni": 4,
    "ham": 4,
    "chicken": 4,
    "mushroom": 3,
    "pepper": 3,
    "onion": 2,
    "olive": 3,
    "pineapple": 3,
    "jalapeno": 3,
    "artichoke": 4,
    "bacon": 4,
    "sausage": 4,
    "garlic": 2,
    "spinach": 2,
    "corn": 2,
    "anchovy": 5,
    "beef": 4,
    "rocket": 2,
    "basil": 2,
}
