class_name IngredientData
extends Resource

## Data Definition for an Ingredient Stream
## Instances of this represent specific foods (e.g. Flour Bag -> Dough Ball)

@export var ingredient_id: String
@export var display_name: String
@export var icon: Texture2D

# The machine type that processes this into the next stage
@export var process_machine: String
# The ID of the ingredient it turns into
@export var next_stage_id: String

## Check if it can be processed by a given machine type
func can_process(machine_type: String) -> bool:
    return process_machine != "" and process_machine == machine_type
