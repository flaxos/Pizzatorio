class_name IngredientRegistry
extends Node

## Registry of all ingredient types, spawn weights, purchase costs, and processing chains.
## Ported from config.py INGREDIENT_TYPES, INGREDIENT_SPAWN_WEIGHTS, etc.

# All known raw ingredient types
var INGREDIENT_TYPES: Array[String] = [
	"flour", "tomato", "cheese", "pepperoni", "ham", "chicken",
	"mushroom", "pepper", "onion", "olive", "pineapple",
	"jalapeno", "artichoke", "bacon", "sausage", "garlic",
	"spinach", "corn", "anchovy", "beef", "rocket", "basil",
]

# Weighted spawn pool
var SPAWN_WEIGHTS: Dictionary = {
	"flour": 3.0, "tomato": 2.5, "cheese": 2.5,
	"pepperoni": 1.5, "ham": 1.2, "chicken": 1.0,
	"mushroom": 1.0, "pepper": 0.8, "onion": 0.8,
	"olive": 0.7, "pineapple": 0.5, "jalapeno": 0.7,
	"artichoke": 0.4, "bacon": 1.0, "sausage": 0.8,
	"garlic": 1.2, "spinach": 0.6, "corn": 0.5,
	"anchovy": 0.3, "beef": 0.7, "rocket": 0.4,
	"basil": 0.6,
}

# Purchase cost per raw ingredient
var PURCHASE_COSTS: Dictionary = {
	"flour": 2, "tomato": 2, "cheese": 3,
	"pepperoni": 4, "ham": 4, "chicken": 4,
	"mushroom": 3, "pepper": 3, "onion": 2,
	"olive": 3, "pineapple": 3, "jalapeno": 3,
	"artichoke": 4, "bacon": 4, "sausage": 4,
	"garlic": 2, "spinach": 2, "corn": 2,
	"anchovy": 5, "beef": 4, "rocket": 2,
	"basil": 2,
}

# Raw ingredient → list of processed product IDs it can produce
var TO_PRODUCTS: Dictionary = {
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

func get_weighted_random_type(rng: RandomNumberGenerator) -> String:
	var total_weight: float = 0.0
	for ingredient_type in INGREDIENT_TYPES:
		total_weight += SPAWN_WEIGHTS.get(ingredient_type, 1.0)
	
	var roll: float = rng.randf() * total_weight
	var cumulative: float = 0.0
	for ingredient_type in INGREDIENT_TYPES:
		cumulative += SPAWN_WEIGHTS.get(ingredient_type, 1.0)
		if roll <= cumulative:
			return ingredient_type
	return INGREDIENT_TYPES[-1]

func get_purchase_cost(ingredient_type: String) -> int:
	return PURCHASE_COSTS.get(ingredient_type, 1)

func can_produce(ingredient_type: String, product_id: String) -> bool:
	var products = TO_PRODUCTS.get(ingredient_type, [])
	return product_id in products
