class_name MachineData
extends Resource

## Data Definition for a Machine Type

@export var machine_id: String
@export var display_name: String
@export var icon: Texture2D

@export var interact_type: String # "belt", "processor", "oven", "assembly", "sink"
@export var process_time_ticks: int = 4
@export var cost: int = 50
@export var power_draw: float = 10.0
