extends Node

## Centralized Event Bus
## Replaces tight coupling from monolithic main.py callbacks

# Global simulation events
signal on_tick(tick_count: int)
signal on_ingredient_processed(ingredient_id: String, new_stage: String)
signal on_pizza_assembled(recipe_id: String)
signal on_order_completed(order_id: String, revenue: int)
signal on_research_unlocked(tech_id: String)

# UI Events
signal on_money_changed(new_amount: int)
signal show_notification(message: String, type: String)
signal request_build_mode(entity_type: String)
signal tool_selected(tool_key: String)
signal rotation_changed(rotation: int)
