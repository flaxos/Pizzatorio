class_name CommercialCatalog
extends Node

## Commercial catalog ported from commercial_catalog.py

var commercials: Dictionary = {}

func _ready() -> void:
	_load_defaults()

func _load_defaults() -> void:
	commercials = {
		"campaigns": {
			"display_name": "Campaigns",
			"activation_cost": 120,
			"demand_multiplier": 1.25,
			"reward_multiplier": 1.0,
			"required_research": "",
		},
		"promos": {
			"display_name": "Promos",
			"activation_cost": 90,
			"demand_multiplier": 1.0,
			"reward_multiplier": 1.1,
			"required_research": "",
		},
		"franchise": {
			"display_name": "Franchise",
			"activation_cost": 180,
			"demand_multiplier": 1.15,
			"reward_multiplier": 1.08,
			"required_research": "franchise_system",
		},
	}

func is_unlocked(strategy: String, tech_tree: Dictionary) -> bool:
	if strategy not in commercials:
		return false
	var required = str(commercials[strategy].get("required_research", ""))
	if required == "":
		return true
	return tech_tree.get(required, false)

func get_config(strategy: String) -> Dictionary:
	return commercials.get(strategy, {})
