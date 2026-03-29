extends Node

## GlobalConfig — Centralised constants ported from Python config.py

# ---------------------------------------------------------------------------
# Grid / display
# ---------------------------------------------------------------------------
const GRID_W: int = 20
const GRID_H: int = 15
const CELL: int = 48
const TILE_SIZE: int = 48

# ---------------------------------------------------------------------------
# Tile kind constants
# ---------------------------------------------------------------------------
const EMPTY: String = "empty"
const CONVEYOR: String = "conveyor"
const MACHINE: String = "machine"
const PROCESSOR: String = "processor"
const OVEN: String = "oven"
const BOT_DOCK: String = "bot_dock"
const ASSEMBLY_TABLE: String = "assembly_table"
const SPLITTER: String = "splitter"
const INSERTER: String = "inserter"
const PRIORITY_LANE: String = "priority_lane"
const SOURCE: String = "source"
const SINK: String = "sink"

# ---------------------------------------------------------------------------
# Item stage ordering
# ---------------------------------------------------------------------------
const ITEM_STAGE_ORDER: Array[String] = ["raw", "processed", "assembled", "baked"]

# ---------------------------------------------------------------------------
# Directional movement vectors (rotation index → Vector2i)
# ---------------------------------------------------------------------------
const DIRS: Dictionary = {
	0: Vector2i(1, 0),
	1: Vector2i(0, 1),
	2: Vector2i(-1, 0),
	3: Vector2i(0, -1),
}

# ---------------------------------------------------------------------------
# Processing flow: which tile kind transforms item stages
# ---------------------------------------------------------------------------
const PROCESS_FLOW: Dictionary = {
	"processor": {"from": "raw", "to": "processed", "research_gain": 0.12},
	"oven": {"from": "processed", "to": "baked", "research_gain": 0.25},
	"oven_assembled": {"from": "assembled", "to": "baked", "research_gain": 0.35},
	"bot_dock": {"from": "baked", "to": "baked", "research_gain": 0.06, "delivery_boost": 1.2},
}

# ---------------------------------------------------------------------------
# Research effect tuning constants
# ---------------------------------------------------------------------------
const TURBO_OVEN_SPEED_BONUS: float = 0.18
const PRECISION_COOKING_WASTE_REFUND: float = 0.40
const HYGIENE_TRAINING_RECOVERY_BONUS: float = 0.30
const PRIORITY_DISPATCH_LATE_MULTIPLIER: float = 0.75
const DOUBLE_SPAWN_INTERVAL_DIVISOR: float = 1.75
const RESEARCH_FOCUS_GAIN_BONUS: float = 0.35

# ---------------------------------------------------------------------------
# Simulation tuning
# ---------------------------------------------------------------------------
const ITEM_SPAWN_INTERVAL: float = 1.8
const ORDER_SPAWN_INTERVAL: float = 5.5
const HYGIENE_EVENT_COOLDOWN: float = 14.0
const HYGIENE_EVENT_CHANCE: float = 0.015
const HYGIENE_RECOVERY_RATE: float = 0.35
const EXPANSION_PROGRESS_RATE: float = 0.35
const EXPANSION_DELIVERY_BONUS: float = 0.002
const EXPANSION_BASE_NEEDED: float = 24.0
const TURBO_BELT_BONUS: float = 0.25
const ASSEMBLY_TABLE_SPEED: float = 0.60
const INSERTER_CYCLE_TIME: float = 1.0
const PRIORITY_LANE_SPEED_MULT: float = 1.5
const BOT_AUTO_CHARGE_RATE: float = 0.18
const BOT_AUTO_DELIVERY_REDUCTION: float = 0.8
const LATE_DELIVERY_PENALTY: float = 0.5
const TICK_RATE: float = 0.5

# ---------------------------------------------------------------------------
# Economy
# ---------------------------------------------------------------------------
const STARTING_MONEY: int = 1000
const INITIAL_FUNDS: int = 1000

const MACHINE_BUILD_COSTS: Dictionary = {
	"conveyor": 10,
	"processor": 80,
	"oven": 150,
	"bot_dock": 200,
	"assembly_table": 120,
	"splitter": 40,
	"inserter": 60,
	"priority_lane": 30,
}

# ---------------------------------------------------------------------------
# Reputation
# ---------------------------------------------------------------------------
const REPUTATION_STARTING: float = 50.0
const REPUTATION_GAIN_ONTIME: float = 0.8
const REPUTATION_LOSS_LATE: float = 1.5
const REPUTATION_LOSS_MISSED_ORDER: float = 1.0
const MISSED_ORDER_CASH_PENALTY_MULTIPLIER: float = 0.25

# ---------------------------------------------------------------------------
# Operating costs
# ---------------------------------------------------------------------------
const OPERATING_COST_INTERVAL: float = 10.0
const OPERATING_COST_BASE: int = 8
const OPERATING_COST_PER_TIER: int = 4

# ---------------------------------------------------------------------------
# Expansion tech effects
# ---------------------------------------------------------------------------
const SECOND_LOCATION_REWARD_BONUS: float = 0.15
const SECOND_LOCATION_SPAWN_INTERVAL_MULTIPLIER: float = 0.85
const SECOND_LOCATION_ORDER_CAPACITY_BONUS: int = 2
const FRANCHISE_EXPANSION_BONUS: float = 2.0

# ---------------------------------------------------------------------------
# Commercial strategy tuning
# ---------------------------------------------------------------------------
const COMMERCIAL_DURATION: float = 30.0

# ---------------------------------------------------------------------------
# Location types for multi-location architecture
# ---------------------------------------------------------------------------
const LOCATION_TYPES: Dictionary = {
	"pizza_shop": {
		"display_name": "Pizza Shop",
		"grid_w": 20, "grid_h": 15,
		"allowed_tiles": ["conveyor", "processor", "oven", "bot_dock", "assembly_table",
						  "splitter", "inserter", "priority_lane", "source", "sink"],
		"has_orders": true,
		"unlock_cost": 0,
	},
	"dough_factory": {
		"display_name": "Dough Factory",
		"grid_w": 16, "grid_h": 12,
		"allowed_tiles": ["conveyor", "processor", "splitter", "inserter",
						  "priority_lane", "source", "sink"],
		"has_orders": false,
		"unlock_cost": 500,
	},
	"sauce_plant": {
		"display_name": "Sauce Plant",
		"grid_w": 16, "grid_h": 12,
		"allowed_tiles": ["conveyor", "processor", "splitter", "inserter",
						  "priority_lane", "source", "sink"],
		"has_orders": false,
		"unlock_cost": 600,
	},
	"farm": {
		"display_name": "Farm",
		"grid_w": 24, "grid_h": 18,
		"allowed_tiles": ["conveyor", "processor", "splitter", "inserter",
						  "priority_lane", "source", "sink"],
		"has_orders": false,
		"unlock_cost": 1000,
	},
}

func _ready() -> void:
	print("GlobalConfig initialized. Grid: ", GRID_W, "x", GRID_H)
