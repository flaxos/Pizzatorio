class_name LocationCatalog
extends Node

## Location type catalog — defines all location types, their properties,
## starting grid layouts, and production/consumption profiles.
##
## Supply chain flow:
##   Wheat Farm ──(flour)──→ Dough Factory ──(rolled_pizza_base)──→ Pizza Shop
##   Tomato Farm ──(tomato)──→ Sauce Plant ──(tomato_sauce)──→ Pizza Shop
##   Dairy Farm ──(cheese)──→ Cheese Facility ──(shredded_cheese/sliced_mozzarella)──→ Pizza Shop
##
## Farms are self-generating (source_free = true) — no ongoing ingredient cost.
## Factories take raw ingredients and output processed products.
## Pizza shops consume processed products and fulfill customer orders.

# ---------------------------------------------------------------------------
# Location category constants
# ---------------------------------------------------------------------------
const CATEGORY_SHOP: String = "shop"
const CATEGORY_FACTORY: String = "factory"
const CATEGORY_FARM: String = "farm"

# ---------------------------------------------------------------------------
# All location type definitions
# ---------------------------------------------------------------------------
const LOCATION_TYPES: Dictionary = {
	# =====================================================================
	# PIZZA SHOP — Starter location, assembles and bakes pizzas
	# =====================================================================
	"pizza_shop": {
		"display_name": "Pizza Shop",
		"category": CATEGORY_SHOP,
		"description": "Assemble and bake pizzas to fulfill customer orders.",
		"grid_w": 20,
		"grid_h": 15,
		"unlock_cost": 0,
		"has_orders": true,

		# What processed ingredients this location consumes (bought or shipped in)
		"inputs": [
			"rolled_pizza_base", "tomato_sauce",
			"shredded_cheese", "sliced_mozzarella",
			"sliced_pepperoni", "chopped_ham", "diced_chicken",
			"sliced_mushroom", "sliced_pepper", "diced_onion",
			"sliced_olives", "pineapple_chunks", "sliced_jalapeno",
			"artichoke_hearts", "bacon_strips", "sliced_sausage",
			"minced_garlic", "washed_spinach", "corn_kernels",
			"anchovy_fillets", "cooked_beef_crumble",
			"rocket_leaves", "fresh_basil",
		],
		# Outputs are fulfilled deliveries (orders), not physical items
		"outputs": [],

		# Source tile configuration
		"source_ingredients": [],  # Uses default weighted spawn from IngredientRegistry
		"source_spawn_interval": 1.8,
		"source_free": false,

		# All tile types allowed
		"allowed_tiles": [
			"conveyor", "processor", "oven", "bot_dock",
			"assembly_table", "splitter", "inserter",
			"priority_lane", "source", "sink",
		],

		# Starting layout — source on left, sink on right, short conveyor run
		"starting_tiles": [
			{"x": 1, "y": 7, "kind": "source", "rot": 0},
			{"x": 2, "y": 7, "kind": "conveyor", "rot": 0},
			{"x": 3, "y": 7, "kind": "conveyor", "rot": 0},
			{"x": 4, "y": 7, "kind": "processor", "rot": 0},
			{"x": 5, "y": 7, "kind": "conveyor", "rot": 0},
			{"x": 6, "y": 7, "kind": "conveyor", "rot": 0},
			{"x": 7, "y": 7, "kind": "conveyor", "rot": 0},
			{"x": 8, "y": 7, "kind": "oven", "rot": 0},
			{"x": 9, "y": 7, "kind": "conveyor", "rot": 0},
			{"x": 10, "y": 7, "kind": "conveyor", "rot": 0},
			{"x": 18, "y": 7, "kind": "sink", "rot": 0},
		],
	},

	# =====================================================================
	# DOUGH FACTORY — Processes flour into rolled pizza bases
	# =====================================================================
	"dough_factory": {
		"display_name": "Dough Factory",
		"category": CATEGORY_FACTORY,
		"description": "Process flour into dough and rolled pizza bases.",
		"grid_w": 16,
		"grid_h": 12,
		"unlock_cost": 500,
		"has_orders": false,

		"inputs": ["flour"],
		"outputs": ["rolled_pizza_base"],

		"source_ingredients": ["flour"],
		"source_spawn_interval": 1.8,
		"source_free": false,

		"allowed_tiles": [
			"conveyor", "processor", "splitter", "inserter",
			"priority_lane", "source", "sink",
		],

		"starting_tiles": [
			{"x": 1, "y": 5, "kind": "source", "rot": 0},
			{"x": 14, "y": 5, "kind": "sink", "rot": 0},
		],
	},

	# =====================================================================
	# SAUCE PLANT — Processes tomatoes into tomato sauce
	# =====================================================================
	"sauce_plant": {
		"display_name": "Sauce Plant",
		"category": CATEGORY_FACTORY,
		"description": "Process tomatoes into tomato sauce.",
		"grid_w": 16,
		"grid_h": 12,
		"unlock_cost": 600,
		"has_orders": false,

		"inputs": ["tomato"],
		"outputs": ["tomato_sauce"],

		"source_ingredients": ["tomato"],
		"source_spawn_interval": 1.8,
		"source_free": false,

		"allowed_tiles": [
			"conveyor", "processor", "splitter", "inserter",
			"priority_lane", "source", "sink",
		],

		"starting_tiles": [
			{"x": 1, "y": 5, "kind": "source", "rot": 0},
			{"x": 14, "y": 5, "kind": "sink", "rot": 0},
		],
	},

	# =====================================================================
	# CHEESE FACILITY — Processes cheese into shredded cheese and
	#                    sliced mozzarella
	# =====================================================================
	"cheese_facility": {
		"display_name": "Cheese Facility",
		"category": CATEGORY_FACTORY,
		"description": "Process cheese blocks into shredded cheese and sliced mozzarella.",
		"grid_w": 16,
		"grid_h": 12,
		"unlock_cost": 700,
		"has_orders": false,

		# cheese raw ingredient produces both shredded_cheese and sliced_mozzarella
		"inputs": ["cheese"],
		"outputs": ["shredded_cheese", "sliced_mozzarella"],

		"source_ingredients": ["cheese"],
		"source_spawn_interval": 1.8,
		"source_free": false,

		"allowed_tiles": [
			"conveyor", "processor", "splitter", "inserter",
			"priority_lane", "source", "sink",
		],

		"starting_tiles": [
			{"x": 1, "y": 5, "kind": "source", "rot": 0},
			{"x": 14, "y": 5, "kind": "sink", "rot": 0},
		],
	},

	# =====================================================================
	# WHEAT FARM — Self-generating flour source (no purchase cost)
	# =====================================================================
	"wheat_farm": {
		"display_name": "Wheat Farm",
		"category": CATEGORY_FARM,
		"description": "Grow and harvest wheat to produce flour. Free ingredients!",
		"grid_w": 24,
		"grid_h": 18,
		"unlock_cost": 1000,
		"has_orders": false,

		"inputs": [],
		"outputs": ["flour"],

		"source_ingredients": ["flour"],
		"source_spawn_interval": 3.0,  # Slower spawn but free
		"source_free": true,

		"allowed_tiles": [
			"conveyor", "processor", "splitter", "inserter",
			"priority_lane", "source", "sink",
		],

		# Multiple source points spread across left side, sink on right
		"starting_tiles": [
			{"x": 1, "y": 4, "kind": "source", "rot": 0},
			{"x": 1, "y": 9, "kind": "source", "rot": 0},
			{"x": 1, "y": 14, "kind": "source", "rot": 0},
			{"x": 22, "y": 9, "kind": "sink", "rot": 0},
		],
	},

	# =====================================================================
	# TOMATO FARM — Self-generating tomato source (no purchase cost)
	# =====================================================================
	"tomato_farm": {
		"display_name": "Tomato Farm",
		"category": CATEGORY_FARM,
		"description": "Grow tomatoes for your sauce plant. Free ingredients!",
		"grid_w": 24,
		"grid_h": 18,
		"unlock_cost": 1000,
		"has_orders": false,

		"inputs": [],
		"outputs": ["tomato"],

		"source_ingredients": ["tomato"],
		"source_spawn_interval": 3.0,
		"source_free": true,

		"allowed_tiles": [
			"conveyor", "processor", "splitter", "inserter",
			"priority_lane", "source", "sink",
		],

		"starting_tiles": [
			{"x": 1, "y": 4, "kind": "source", "rot": 0},
			{"x": 1, "y": 9, "kind": "source", "rot": 0},
			{"x": 1, "y": 14, "kind": "source", "rot": 0},
			{"x": 22, "y": 9, "kind": "sink", "rot": 0},
		],
	},

	# =====================================================================
	# DAIRY FARM — Self-generating cheese source (no purchase cost)
	# =====================================================================
	"dairy_farm": {
		"display_name": "Dairy Farm",
		"category": CATEGORY_FARM,
		"description": "Produce cheese for your cheese facility. Free ingredients!",
		"grid_w": 24,
		"grid_h": 18,
		"unlock_cost": 1200,
		"has_orders": false,

		"inputs": [],
		"outputs": ["cheese"],

		"source_ingredients": ["cheese"],
		"source_spawn_interval": 3.5,  # Slowest farm — higher-value product
		"source_free": true,

		"allowed_tiles": [
			"conveyor", "processor", "splitter", "inserter",
			"priority_lane", "source", "sink",
		],

		"starting_tiles": [
			{"x": 1, "y": 4, "kind": "source", "rot": 0},
			{"x": 1, "y": 9, "kind": "source", "rot": 0},
			{"x": 1, "y": 14, "kind": "source", "rot": 0},
			{"x": 22, "y": 9, "kind": "sink", "rot": 0},
		],
	},
}

# ---------------------------------------------------------------------------
# Unlock progression order — suggested order for the player to expand
# ---------------------------------------------------------------------------
const UNLOCK_ORDER: Array = [
	"pizza_shop",       # Free — starting location
	"dough_factory",    # First supply chain step
	"sauce_plant",      # Second supply chain step
	"cheese_facility",  # Third supply chain step
	"wheat_farm",       # Vertical integration begins
	"tomato_farm",
	"dairy_farm",       # Most expensive farm
]


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

func get_location_type(type_key: String) -> Dictionary:
	return LOCATION_TYPES.get(type_key, {})

func get_display_name(type_key: String) -> String:
	return str(LOCATION_TYPES.get(type_key, {}).get("display_name", type_key))

func get_grid_size(type_key: String) -> Vector2i:
	var data := get_location_type(type_key)
	if data.is_empty():
		return Vector2i(20, 15)  # Fallback to default
	return Vector2i(int(data["grid_w"]), int(data["grid_h"]))

func get_unlock_cost(type_key: String) -> int:
	return int(LOCATION_TYPES.get(type_key, {}).get("unlock_cost", 9999))

func has_orders(type_key: String) -> bool:
	return bool(LOCATION_TYPES.get(type_key, {}).get("has_orders", false))

func get_source_ingredients(type_key: String) -> Array:
	return LOCATION_TYPES.get(type_key, {}).get("source_ingredients", [])

func get_source_spawn_interval(type_key: String) -> float:
	return float(LOCATION_TYPES.get(type_key, {}).get("source_spawn_interval", 1.8))

func is_source_free(type_key: String) -> bool:
	return bool(LOCATION_TYPES.get(type_key, {}).get("source_free", false))

func get_starting_tiles(type_key: String) -> Array:
	return LOCATION_TYPES.get(type_key, {}).get("starting_tiles", [])

func get_allowed_tiles(type_key: String) -> Array:
	return LOCATION_TYPES.get(type_key, {}).get("allowed_tiles", [])

func is_tile_allowed(type_key: String, tile_kind: String) -> bool:
	var allowed := get_allowed_tiles(type_key)
	if allowed.is_empty():
		return true  # No restrictions
	return tile_kind in allowed

func get_category(type_key: String) -> String:
	return str(LOCATION_TYPES.get(type_key, {}).get("category", ""))

func get_locations_by_category(category: String) -> Array[String]:
	var result: Array[String] = []
	for key in LOCATION_TYPES:
		if LOCATION_TYPES[key].get("category", "") == category:
			result.append(key)
	return result

func get_inputs(type_key: String) -> Array:
	return LOCATION_TYPES.get(type_key, {}).get("inputs", [])

func get_outputs(type_key: String) -> Array:
	return LOCATION_TYPES.get(type_key, {}).get("outputs", [])

func get_all_type_keys() -> Array[String]:
	var keys: Array[String] = []
	for key in LOCATION_TYPES:
		keys.append(key)
	return keys

## Returns location types the player can afford to unlock given current cash.
func get_affordable_locations(current_cash: int) -> Array[String]:
	var affordable: Array[String] = []
	for key in LOCATION_TYPES:
		var cost := get_unlock_cost(key)
		if cost <= current_cash:
			affordable.append(key)
	return affordable

## Returns the total ingredient cost savings per spawn cycle for a farm location.
## Useful for showing ROI in the shop UI.
func get_farm_savings_per_cycle(type_key: String, ingredient_registry: Node) -> int:
	if not is_source_free(type_key):
		return 0
	var total_savings: int = 0
	for ingredient in get_source_ingredients(type_key):
		if ingredient_registry and ingredient_registry.has_method("get_purchase_cost"):
			total_savings += ingredient_registry.get_purchase_cost(ingredient)
	return total_savings
