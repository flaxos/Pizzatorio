class_name RecipeCatalog
extends Node

## Recipe catalog ported from recipe_catalog.py DEFAULT_RECIPE_DEFINITIONS

var recipes: Dictionary = {}

func _ready() -> void:
	_load_defaults()

func _load_defaults() -> void:
	recipes = {
		"margherita": {
			"display_name": "Margherita",
			"sell_price": 12,
			"sla": 11.0,
			"unlock_tier": 0,
			"cook_time": 8.0,
			"cook_temp": "medium",
			"difficulty": 1,
			"demand_weight": 1.0,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "sliced_mozzarella",
			"toppings": ["fresh_basil"],
			"post_oven": [],
			"required_research": "",
		},
		"pepperoni": {
			"display_name": "Pepperoni",
			"sell_price": 15,
			"sla": 10.0,
			"unlock_tier": 1,
			"cook_time": 7.5,
			"cook_temp": "high",
			"difficulty": 2,
			"demand_weight": 1.0,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["sliced_pepperoni"],
			"post_oven": [],
			"required_research": "",
		},
		"veggie": {
			"display_name": "Veggie Deluxe",
			"sell_price": 17,
			"sla": 9.5,
			"unlock_tier": 2,
			"cook_time": 8.2,
			"cook_temp": "medium",
			"difficulty": 2,
			"demand_weight": 1.0,
			"base": "rolled_pizza_base",
			"sauce": "tomato_sauce",
			"cheese": "shredded_cheese",
			"toppings": ["sliced_pepper", "sliced_mushroom", "diced_onion"],
			"post_oven": [],
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
