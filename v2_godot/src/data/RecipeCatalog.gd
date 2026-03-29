class_name RecipeCatalog
extends Node

## Recipe catalog ported from recipe_catalog.py DEFAULT_RECIPE_DEFINITIONS

var recipes: Dictionary = {}

func _ready() -> void:
	_load_defaults()

func _load_defaults() -> void:
	recipes = {
		# ===== TIER 0 — Starter recipes (expansion level 1) =====
		"margherita": {
			"display_name": "Margherita",
			"sell_price": 12,
			"sla": 11.0,
			"unlock_tier": 0,
			"cook_time": 8.0,
			"cook_temp": "medium",
			"difficulty": 1,
			"demand_weight": 1.5,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "sliced_mozzarella",
			"toppings": ["fresh_basil"],
			"post_oven": [],
			"required_research": "",
		},
		"cheese": {
			"display_name": "Cheese Pizza",
			"sell_price": 10,
			"sla": 12.0,
			"unlock_tier": 0,
			"cook_time": 6.0,
			"cook_temp": "medium",
			"difficulty": 1,
			"demand_weight": 2.0,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": [],
			"post_oven": [],
			"required_research": "",
		},

		# ===== TIER 1 — Early game (expansion level 2) =====
		"pepperoni": {
			"display_name": "Pepperoni",
			"sell_price": 15,
			"sla": 11.0,
			"unlock_tier": 1,
			"cook_time": 7.5,
			"cook_temp": "high",
			"difficulty": 2,
			"demand_weight": 1.5,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["sliced_pepperoni"],
			"post_oven": [],
			"required_research": "",
		},
		"ham_mushroom": {
			"display_name": "Ham & Mushroom",
			"sell_price": 16,
			"sla": 12.0,
			"unlock_tier": 1,
			"cook_time": 8.0,
			"cook_temp": "medium",
			"difficulty": 2,
			"demand_weight": 1.2,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["chopped_ham", "sliced_mushroom"],
			"post_oven": [],
			"required_research": "",
		},
		"hawaiian": {
			"display_name": "Hawaiian",
			"sell_price": 16,
			"sla": 12.0,
			"unlock_tier": 1,
			"cook_time": 7.5,
			"cook_temp": "medium",
			"difficulty": 2,
			"demand_weight": 1.0,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["chopped_ham", "pineapple_chunks"],
			"post_oven": [],
			"required_research": "",
		},

		# ===== TIER 2 — Mid game (expansion level 3) =====
		"veggie": {
			"display_name": "Veggie Deluxe",
			"sell_price": 20,
			"sla": 14.0,
			"unlock_tier": 2,
			"cook_time": 8.5,
			"cook_temp": "medium",
			"difficulty": 3,
			"demand_weight": 0.8,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["sliced_pepper", "diced_onion", "sliced_mushroom", "sliced_olives"],
			"post_oven": [],
			"required_research": "",
		},
		"meat_feast": {
			"display_name": "Meat Feast",
			"sell_price": 24,
			"sla": 14.0,
			"unlock_tier": 2,
			"cook_time": 9.0,
			"cook_temp": "high",
			"difficulty": 3,
			"demand_weight": 0.8,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["sliced_pepperoni", "chopped_ham", "sliced_sausage", "bacon_strips"],
			"post_oven": [],
			"required_research": "",
		},
		"bbq_chicken": {
			"display_name": "BBQ Chicken",
			"sell_price": 22,
			"sla": 13.0,
			"unlock_tier": 2,
			"cook_time": 8.5,
			"cook_temp": "high",
			"difficulty": 3,
			"demand_weight": 0.9,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["diced_chicken", "diced_onion", "sliced_pepper"],
			"post_oven": [],
			"required_research": "",
		},
		"garlic_bread_pizza": {
			"display_name": "Garlic Bread Pizza",
			"sell_price": 14,
			"sla": 10.0,
			"unlock_tier": 2,
			"cook_time": 6.0,
			"cook_temp": "high",
			"difficulty": 2,
			"demand_weight": 1.0,
			"base": "rolled_pizza_base",
			"sauce": "",
			"cheese": "shredded_cheese",
			"toppings": ["minced_garlic"],
			"post_oven": [],
			"required_research": "",
		},
		"corn_fiesta": {
			"display_name": "Corn Fiesta",
			"sell_price": 18,
			"sla": 12.0,
			"unlock_tier": 2,
			"cook_time": 7.5,
			"cook_temp": "medium",
			"difficulty": 2,
			"demand_weight": 0.7,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["corn_kernels", "sliced_pepper", "diced_onion"],
			"post_oven": [],
			"required_research": "",
		},

		# ===== TIER 3 — Late game (expansion level 4) =====
		"seafood_special": {
			"display_name": "Seafood Special",
			"sell_price": 28,
			"sla": 15.0,
			"unlock_tier": 3,
			"cook_time": 9.0,
			"cook_temp": "medium",
			"difficulty": 3,
			"demand_weight": 0.5,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["anchovy_fillets", "minced_garlic", "sliced_olives"],
			"post_oven": [],
			"required_research": "",
		},
		"spicy_mexican": {
			"display_name": "Spicy Mexican",
			"sell_price": 26,
			"sla": 15.0,
			"unlock_tier": 3,
			"cook_time": 8.5,
			"cook_temp": "high",
			"difficulty": 4,
			"demand_weight": 0.5,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["sliced_jalapeno", "cooked_beef_crumble", "diced_onion", "sliced_pepper"],
			"post_oven": [],
			"required_research": "",
		},
		"mediterranean": {
			"display_name": "Mediterranean",
			"sell_price": 27,
			"sla": 15.0,
			"unlock_tier": 3,
			"cook_time": 9.0,
			"cook_temp": "medium",
			"difficulty": 4,
			"demand_weight": 0.5,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["artichoke_hearts", "sliced_olives", "washed_spinach", "minced_garlic"],
			"post_oven": [],
			"required_research": "",
		},
		"four_cheese": {
			"display_name": "Four Cheese",
			"sell_price": 22,
			"sla": 13.0,
			"unlock_tier": 3,
			"cook_time": 8.0,
			"cook_temp": "medium",
			"difficulty": 3,
			"demand_weight": 0.6,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["sliced_mozzarella"],
			"post_oven": [],
			"required_research": "",
		},
		"supreme": {
			"display_name": "Supreme",
			"sell_price": 32,
			"sla": 17.0,
			"unlock_tier": 3,
			"cook_time": 10.0,
			"cook_temp": "high",
			"difficulty": 5,
			"demand_weight": 0.4,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["sliced_pepperoni", "sliced_sausage", "sliced_mushroom", "sliced_pepper", "diced_onion", "sliced_olives"],
			"post_oven": [],
			"required_research": "",
		},

		# ===== TIER 4 — Empire (expansion level 5) =====
		"truffle_special": {
			"display_name": "Truffle Special",
			"sell_price": 38,
			"sla": 16.0,
			"unlock_tier": 4,
			"cook_time": 10.0,
			"cook_temp": "medium",
			"difficulty": 4,
			"demand_weight": 0.3,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "sliced_mozzarella",
			"toppings": ["sliced_mushroom", "minced_garlic"],
			"post_oven": ["rocket_leaves"],
			"required_research": "",
		},
		"the_everything": {
			"display_name": "The Everything",
			"sell_price": 45,
			"sla": 18.0,
			"unlock_tier": 4,
			"cook_time": 12.0,
			"cook_temp": "high",
			"difficulty": 5,
			"demand_weight": 0.2,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["sliced_pepperoni", "chopped_ham", "diced_chicken", "sliced_mushroom", "sliced_pepper"],
			"post_oven": ["fresh_basil"],
			"required_research": "",
		},
	}

func get_recipe(key: String) -> Dictionary:
	return recipes.get(key, {})

func get_available_recipes(expansion_level: int, tech_tree: Dictionary) -> Array[String]:
	var available: Array[String] = []
	for key in recipes:
		var recipe = recipes[key]
		if recipe.get("unlock_tier", 0) <= (expansion_level - 1):
			var required_research = str(recipe.get("required_research", ""))
			if required_research == "" or tech_tree.get(required_research, false):
				available.append(key)
	return available

func get_required_products(recipe_key: String) -> Array[String]:
	var recipe = get_recipe(recipe_key)
	if recipe.is_empty():
		return []
	var products: Array[String] = []
	if recipe.has("base") and recipe["base"] != "":
		products.append(recipe["base"])
	if recipe.has("sauce") and recipe["sauce"] != "":
		products.append(recipe["sauce"])
	if recipe.has("cheese") and recipe["cheese"] != "":
		products.append(recipe["cheese"])
	for topping in recipe.get("toppings", []):
		products.append(str(topping))
	return products
