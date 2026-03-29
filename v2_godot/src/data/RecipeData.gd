class_name RecipeData
extends Resource

## Data Definition for Pizza Recipes

@export var recipe_id: String
@export var display_name: String
@export var base_ingredient: String = "rolled_pizza_base"
@export var sauce: String = "tomato_sauce"
@export var cheese: String = "sliced_mozzarella"
@export var toppings: Array[String] = []  # Specific slice strings

@export var cook_time_ticks: int = 16
@export var sell_price: int = 12
@export var difficulty: int = 1
