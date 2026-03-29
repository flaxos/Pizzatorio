class_name ResearchCatalog
extends Node

## Research catalog ported from research_catalog.py DEFAULT_RESEARCH

var research: Dictionary = {}

func _ready() -> void:
	_load_defaults()

func _load_defaults() -> void:
	research = {
		"ovens": {"display_name": "Oven Foundations", "branch": "cooking", "cost": 12.0, "prerequisites": []},
		"bots": {"display_name": "Bot Docks", "branch": "automation", "cost": 28.0, "prerequisites": []},
		"turbo_oven": {"display_name": "Turbo Ovens", "branch": "cooking", "cost": 40.0, "prerequisites": ["ovens"]},
		"hygiene_training": {"display_name": "Hygiene Training", "branch": "automation", "cost": 50.0, "prerequisites": ["bots"]},
		"turbo_belts": {"display_name": "Turbo Belts", "branch": "logistics", "cost": 55.0, "prerequisites": ["bots"]},
		"priority_dispatch": {"display_name": "Priority Dispatch", "branch": "logistics", "cost": 85.0, "prerequisites": ["turbo_belts"]},
		"precision_cooking": {"display_name": "Precision Cooking", "branch": "cooking", "cost": 95.0, "prerequisites": ["turbo_oven", "hygiene_training"]},
		"double_spawn": {"display_name": "Double Spawn", "branch": "logistics", "cost": 140.0, "prerequisites": ["turbo_belts"]},
		"second_location": {"display_name": "Second Location", "branch": "expansion", "cost": 180.0, "prerequisites": ["priority_dispatch", "precision_cooking"]},
		"franchise_system": {"display_name": "Franchise System", "branch": "expansion", "cost": 320.0, "prerequisites": ["second_location", "double_spawn"]},
	}

func get_cost(tech_key: String) -> float:
	return float(research.get(tech_key, {}).get("cost", 999999.0))

func get_prerequisites(tech_key: String) -> Array:
	return research.get(tech_key, {}).get("prerequisites", [])

func prerequisites_met(tech_key: String, tech_tree: Dictionary) -> bool:
	for prereq in get_prerequisites(tech_key):
		if not tech_tree.get(str(prereq), false):
			return false
	return true

func get_available_targets(tech_tree: Dictionary) -> Array[String]:
	var available: Array[String] = []
	for tech_key in research:
		if not tech_tree.get(tech_key, false) and prerequisites_met(tech_key, tech_tree):
			available.append(tech_key)
	return available
