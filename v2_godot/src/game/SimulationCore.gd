extends Node
class_name SimulationCore

## The main headless simulation grid manager.
## Ported from game/simulation.py FactorySim class.
## Tracks grid state, items, orders, deliveries, economy — all decoupled from visuals.

# Preload config so this script works in both editor and headless --script mode
const GC = preload("res://src/autoloads/GlobalConfig.gd")

signal grid_changed(pos: Vector2i, tile_kind: String, rotation: int)
signal item_spawned(item_data: Dictionary)
signal item_moved(item_idx: int, new_pos: Vector2i)
signal item_removed(item_idx: int)
signal order_spawned(order_data: Dictionary)
signal delivery_completed(recipe_key: String, reward: int)
signal money_changed(new_amount: int)
signal research_unlocked(tech_key: String)
signal assembly_progress(pos: Vector2i, recipe_key: String, layers_complete: int, layers_total: int)
signal assembly_completed(pos: Vector2i, recipe_key: String)

# --- Grid State ---
# grid[y][x] = { "kind": String, "rot": int, "hygiene_penalty": int }
var grid: Array = []
var items: Array = []      # Array of item dicts
var orders: Array = []     # Array of order dicts
var deliveries: Array = [] # Array of delivery dicts

# Assembly table state: Vector2i -> { "recipe_key": String, "collected": Array, "needed": Array }
var assembly_state: Dictionary = {}

# Splitter toggle state: Vector2i -> bool (false=primary, true=secondary)
var splitter_toggles: Dictionary = {}
# Inserter cycle timers: Vector2i -> float
var inserter_timers: Dictionary = {}

# --- Economy ---
var money: int = 0
var total_revenue: int = 0
var total_spend: int = 0
var waste: int = 0

# --- Stats ---
var sim_time: float = 0.0
var spawn_timer: float = 0.0
var order_spawn_timer: float = 0.0
var hygiene: float = 100.0
var bottleneck: float = 0.0
var expansion_level: int = 1
var expansion_progress: float = 0.0
var research_points: float = 0.0
var tech_tree: Dictionary = {}
var auto_bot_charge: float = 0.0
var completed: int = 0
var ontime: int = 0
var reputation: float = 0.0
var order_channel: String = "delivery"
var commercial_strategy: String = "campaigns"
var research_focus: String = ""
var cost_timer: float = 0.0
var last_hygiene_event: float = 0.0
var event_log: Array[String] = []

# --- Registries (injected at scene load) ---
const _IngredientRegistry = preload("res://src/data/IngredientRegistry.gd")
const _RecipeCatalog = preload("res://src/data/RecipeCatalog.gd")
const _ResearchCatalog = preload("res://src/data/ResearchCatalog.gd")
const _CommercialCatalog = preload("res://src/data/CommercialCatalog.gd")
const _OrderChannelCatalog = preload("res://src/data/OrderChannelCatalog.gd")

var ingredient_registry
var recipe_catalog
var research_catalog
var commercial_catalog
var order_channel_catalog

var rng: RandomNumberGenerator = RandomNumberGenerator.new()

func _ready() -> void:
	# Initialize registries as child nodes
	ingredient_registry = _IngredientRegistry.new()
	add_child(ingredient_registry)
	recipe_catalog = _RecipeCatalog.new()
	add_child(recipe_catalog)
	research_catalog = _ResearchCatalog.new()
	add_child(research_catalog)
	commercial_catalog = _CommercialCatalog.new()
	add_child(commercial_catalog)
	order_channel_catalog = _OrderChannelCatalog.new()
	add_child(order_channel_catalog)
	
	_initialize()

func _initialize() -> void:
	rng.seed = 7
	money = GC.STARTING_MONEY
	reputation = GC.REPUTATION_STARTING
	
	# Build empty grid
	grid.clear()
	for y in range(GC.GRID_H):
		var row: Array = []
		for x in range(GC.GRID_W):
			row.append({"kind": GC.EMPTY, "rot": 0, "hygiene_penalty": 0})
		grid.append(row)
	
	# Initialize tech tree
	for tech_key in research_catalog.research:
		tech_tree[tech_key] = false
	
	# Place static world (source, sink, initial belt run)
	_place_static_world()
	_log_event("Factory initialized")
	
	emit_signal("money_changed", money)

func _place_static_world() -> void:
	_set_tile(1, 7, GC.SOURCE, 0)
	_set_tile(18, 7, GC.SINK, 0)
	for x in range(2, 18):
		_set_tile(x, 7, GC.CONVEYOR, 0)
	_set_tile(7, 7, GC.PROCESSOR, 0)
	_set_tile(12, 7, GC.OVEN, 0)
	_set_tile(12, 6, GC.BOT_DOCK, 1)

func _set_tile(x: int, y: int, kind: String, rot: int) -> void:
	if x < 0 or x >= GC.GRID_W or y < 0 or y >= GC.GRID_H:
		return
	var pos := Vector2i(x, y)
	# Clean up state if tile is changing
	var old_kind: String = grid[y][x].get("kind", GC.EMPTY)
	if old_kind == GC.ASSEMBLY_TABLE and kind != GC.ASSEMBLY_TABLE:
		assembly_state.erase(pos)
	if old_kind == GC.SPLITTER and kind != GC.SPLITTER:
		splitter_toggles.erase(pos)
	if old_kind == GC.INSERTER and kind != GC.INSERTER:
		inserter_timers.erase(pos)
	grid[y][x] = {"kind": kind, "rot": rot % 4, "hygiene_penalty": 0}
	# Initialize state when placing tiles
	if kind == GC.ASSEMBLY_TABLE:
		assembly_state[pos] = {"recipe_key": "", "collected": [], "needed": []}
	if kind == GC.SPLITTER:
		splitter_toggles[pos] = false
	if kind == GC.INSERTER:
		inserter_timers[pos] = 0.0
	emit_signal("grid_changed", pos, kind, rot % 4)

# ------------------------------------------------------------------
# Building
# ------------------------------------------------------------------

func can_place_tile(x: int, y: int, kind: String) -> bool:
	if x < 0 or x >= GC.GRID_W or y < 0 or y >= GC.GRID_H:
		return false
	var current_kind = grid[y][x]["kind"]
	if current_kind in [GC.SOURCE, GC.SINK]:
		return false
	if kind == GC.OVEN and not tech_tree.get("ovens", false):
		return false
	if kind == GC.BOT_DOCK and not tech_tree.get("bots", false):
		return false
	return true

func place_tile(x: int, y: int, kind: String, rot: int) -> bool:
	if not can_place_tile(x, y, kind):
		return false
	if kind == GC.EMPTY:
		_set_tile(x, y, GC.EMPTY, 0)
		return true
	# Charge for building on empty ground
	if grid[y][x]["kind"] == GC.EMPTY:
		var cost: int = GC.MACHINE_BUILD_COSTS.get(kind, 0)
		if money < cost:
			return false
		money -= cost
		total_spend += cost
		emit_signal("money_changed", money)
	_set_tile(x, y, kind, rot)
	return true

# ------------------------------------------------------------------
# Simulation Tick (called by TimeManager)
# ------------------------------------------------------------------

func sim_tick(_tick_count: int) -> void:
	var dt: float = GC.TICK_RATE
	sim_time += dt
	spawn_timer += dt
	order_spawn_timer += dt
	
	# Item spawning
	var effective_spawn_interval = GC.ITEM_SPAWN_INTERVAL
	if tech_tree.get("double_spawn", false):
		effective_spawn_interval /= GC.DOUBLE_SPAWN_INTERVAL_DIVISOR
	
	if spawn_timer >= effective_spawn_interval:
		spawn_timer = 0.0
		_spawn_item()
	
	# Order spawning
	var effective_order_interval = GC.ORDER_SPAWN_INTERVAL
	if order_spawn_timer >= effective_order_interval:
		order_spawn_timer = 0.0
		_spawn_order()
	
	# Operating costs
	cost_timer += dt
	if cost_timer >= GC.OPERATING_COST_INTERVAL:
		cost_timer -= GC.OPERATING_COST_INTERVAL
		var cost = GC.OPERATING_COST_BASE + GC.OPERATING_COST_PER_TIER * max(0, expansion_level - 1)
		var charged = min(money, cost)
		money -= charged
		total_spend += charged
		emit_signal("money_changed", money)
		_log_event("Operating costs: -$%d" % charged)
	
	# Hygiene fluctuation
	var hygiene_recovery = GC.HYGIENE_RECOVERY_RATE
	if tech_tree.get("hygiene_training", false):
		hygiene_recovery += GC.HYGIENE_TRAINING_RECOVERY_BONUS
	
	if sim_time - last_hygiene_event > GC.HYGIENE_EVENT_COOLDOWN and rng.randf() < GC.HYGIENE_EVENT_CHANCE:
		last_hygiene_event = sim_time
		hygiene = clampf(hygiene - rng.randf_range(8.0, 20.0), 0.0, 100.0)
	else:
		hygiene = clampf(hygiene + dt * hygiene_recovery, 0.0, 100.0)
	
	# Process items
	_process_items(dt)

	# Process inserters
	_process_inserters(dt)

	# Process deliveries
	_process_deliveries(dt)
	
	# Process orders (expiry)
	_process_orders(dt)
	
	# Research
	_process_research()

func _spawn_item() -> void:
	var ingredient_type = ingredient_registry.get_weighted_random_type(rng)
	var cost = ingredient_registry.get_purchase_cost(ingredient_type)
	if money < cost:
		return
	money -= cost
	total_spend += cost
	emit_signal("money_changed", money)
	
	var item_data = {
		"x": 1, "y": 7,
		"progress": 0.0,
		"stage": "raw",
		"delivery_boost": 0.0,
		"ingredient_type": ingredient_type,
		"product_type": "",
		"recipe_key": "",
	}
	items.append(item_data)
	emit_signal("item_spawned", item_data)

func _spawn_order() -> void:
	var available = recipe_catalog.get_available_recipes(expansion_level, tech_tree)
	if available.is_empty():
		return
	var key = available[rng.randi() % available.size()]
	var recipe = recipe_catalog.get_recipe(key)
	if recipe.is_empty():
		return
	var order_data = {
		"recipe_key": key,
		"remaining_sla": float(recipe.get("sla", 10.0)),
		"total_sla": float(recipe.get("sla", 10.0)),
		"reward": int(recipe.get("sell_price", 12)),
		"channel_key": order_channel,
	}
	orders.append(order_data)
	emit_signal("order_spawned", order_data)

func _process_items(dt: float) -> void:
	var turbo: float = GC.TURBO_BELT_BONUS if tech_tree.get("turbo_belts", false) else 0.0
	var items_to_remove: Array[int] = []

	for i in range(items.size()):
		var item = items[i]
		var tile = grid[item["y"]][item["x"]]
		var speed: float = 1.0 + turbo

		match tile["kind"]:
			GC.PROCESSOR:
				speed = 0.5 + (hygiene / 220.0)
			GC.OVEN:
				var oven_bonus = GC.TURBO_OVEN_SPEED_BONUS if tech_tree.get("turbo_oven", false) else 0.0
				speed = 0.35 + oven_bonus + (hygiene / 280.0)
			GC.ASSEMBLY_TABLE:
				speed = GC.ASSEMBLY_TABLE_SPEED
			GC.PRIORITY_LANE:
				speed = (1.0 + turbo) * GC.PRIORITY_LANE_SPEED_MULT

		item["progress"] += dt * speed

		if item["progress"] < 1.0:
			continue

		item["progress"] = 0.0

		# --- Assembly Table Logic ---
		if tile["kind"] == GC.ASSEMBLY_TABLE:
			var consumed = _handle_assembly_table(item, i)
			if consumed:
				items_to_remove.append(i)
				continue
			# If not consumed (item rejected / doesn't match), let it move on

		# Process transformation (processor: raw->processed, oven: processed/assembled->baked)
		var tile_kind_for_flow: String = tile["kind"]
		# Oven handles both processed->baked and assembled->baked
		if tile_kind_for_flow == GC.OVEN and item["stage"] == "assembled":
			tile_kind_for_flow = "oven_assembled"
		var flow = GC.PROCESS_FLOW.get(tile_kind_for_flow)
		if flow and item["stage"] == flow["from"]:
			item["stage"] = flow["to"]
			# Set product_type when processor transforms raw->processed
			if tile["kind"] == GC.PROCESSOR and item.get("ingredient_type", "") != "":
				var products = ingredient_registry.TO_PRODUCTS.get(item["ingredient_type"], [])
				if products.size() > 0:
					item["product_type"] = products[0]
			var rp_gain: float = float(flow["research_gain"])
			if research_focus != "" and not tech_tree.get(research_focus, false):
				rp_gain *= 1.0 + GC.RESEARCH_FOCUS_GAIN_BONUS
			research_points += rp_gain
			if flow.has("delivery_boost"):
				item["delivery_boost"] = float(flow["delivery_boost"])

		# Mark items on priority lanes
		if tile["kind"] == GC.PRIORITY_LANE:
			item["priority"] = true

		# Move to next tile
		if tile["kind"] in [GC.CONVEYOR, GC.SOURCE, GC.PROCESSOR,
							GC.OVEN, GC.BOT_DOCK, GC.ASSEMBLY_TABLE,
							GC.SPLITTER, GC.PRIORITY_LANE]:
			var dir_vec: Vector2i = GC.DIRS.get(tile["rot"], Vector2i(1, 0))

			# Splitter: alternate between primary (forward) and secondary (90 CW)
			if tile["kind"] == GC.SPLITTER:
				var spos := Vector2i(item["x"], item["y"])
				var is_priority: bool = item.get("priority", false)
				if is_priority:
					# Priority items always go primary (forward)
					pass  # dir_vec stays as forward
				else:
					var use_secondary: bool = splitter_toggles.get(spos, false)
					if use_secondary:
						# 90 degrees clockwise: rotation + 1
						var sec_rot: int = (tile["rot"] + 1) % 4
						var sec_dir: Vector2i = GC.DIRS.get(sec_rot, Vector2i(1, 0))
						var sx: int = item["x"] + sec_dir.x
						var sy: int = item["y"] + sec_dir.y
						if sx >= 0 and sx < GC.GRID_W and sy >= 0 and sy < GC.GRID_H:
							dir_vec = sec_dir
						# else: fallback to primary direction
					# Toggle for next item
					splitter_toggles[spos] = not use_secondary

			var nx: int = item["x"] + dir_vec.x
			var ny: int = item["y"] + dir_vec.y

			if nx >= 0 and nx < GC.GRID_W and ny >= 0 and ny < GC.GRID_H:
				item["x"] = nx
				item["y"] = ny
				emit_signal("item_moved", i, Vector2i(nx, ny))

				# Check if we reached a sink
				if grid[ny][nx]["kind"] == GC.SINK:
					# Resolve order
					var order = _resolve_order_for_item(item)
					if order != null:
						_enqueue_delivery(order)
					items_to_remove.append(i)
			else:
				items_to_remove.append(i)

	# Remove items in reverse to preserve indices
	items_to_remove.reverse()
	for idx in items_to_remove:
		items.remove_at(idx)
		emit_signal("item_removed", idx)

# ------------------------------------------------------------------
# Inserters
# ------------------------------------------------------------------

func _process_inserters(dt: float) -> void:
	var turbo: float = GC.TURBO_BELT_BONUS if tech_tree.get("turbo_belts", false) else 0.0
	var cycle_time: float = GC.INSERTER_CYCLE_TIME / (1.0 + turbo)

	for pos in inserter_timers.keys():
		inserter_timers[pos] += dt
		if inserter_timers[pos] < cycle_time:
			continue
		inserter_timers[pos] -= cycle_time

		var tile = grid[pos.y][pos.x]
		if tile["kind"] != GC.INSERTER:
			inserter_timers.erase(pos)
			continue

		var rot: int = tile["rot"]
		var forward: Vector2i = GC.DIRS.get(rot, Vector2i(1, 0))
		# Source is behind the inserter (opposite of forward)
		var source_pos: Vector2i = pos - forward
		var dest_pos: Vector2i = pos + forward

		# Bounds check
		if source_pos.x < 0 or source_pos.x >= GC.GRID_W or source_pos.y < 0 or source_pos.y >= GC.GRID_H:
			continue
		if dest_pos.x < 0 or dest_pos.x >= GC.GRID_W or dest_pos.y < 0 or dest_pos.y >= GC.GRID_H:
			continue

		# Find an item on the source tile
		var found_idx: int = -1
		for i in range(items.size()):
			if items[i]["x"] == source_pos.x and items[i]["y"] == source_pos.y:
				found_idx = i
				break

		if found_idx == -1:
			continue

		# Move the item to the dest tile
		items[found_idx]["x"] = dest_pos.x
		items[found_idx]["y"] = dest_pos.y
		items[found_idx]["progress"] = 0.0
		emit_signal("item_moved", found_idx, dest_pos)

# ------------------------------------------------------------------
# Assembly Table
# ------------------------------------------------------------------

## Handle an item arriving at an assembly table. Returns true if the item
## was consumed (added to assembly or wasted), false if it should pass through.
func _handle_assembly_table(item: Dictionary, _item_idx: int) -> bool:
	if item["stage"] != "processed":
		return false  # Only processed items can be assembled

	var pos := Vector2i(item["x"], item["y"])
	if not assembly_state.has(pos):
		return false

	var state: Dictionary = assembly_state[pos]
	var item_product: String = item.get("product_type", "")
	if item_product == "":
		return false  # Item has no product type, skip

	# --- Case A: No active assembly — try to start one ---
	if state["recipe_key"] == "":
		var matched_recipe := _find_recipe_for_product(item_product)
		if matched_recipe == "":
			# No recipe starts with this product; waste the item
			waste += 1
			_log_event("Assembly waste: %s (no matching recipe)" % item_product)
			return true
		var required = recipe_catalog.get_required_products(matched_recipe)
		state["recipe_key"] = matched_recipe
		state["needed"] = required.duplicate()
		state["collected"] = []
		# Fall through to Case B to consume the first ingredient

	# --- Case B: Active assembly — try to add ingredient ---
	var needed_arr: Array = state["needed"]
	var idx := -1
	for j in range(needed_arr.size()):
		if needed_arr[j] == item_product:
			idx = j
			break

	if idx == -1:
		# Item doesn't match any remaining need; waste it
		waste += 1
		_log_event("Assembly waste: %s (not needed for %s)" % [item_product, state["recipe_key"]])
		return true

	# Consume the ingredient
	needed_arr.remove_at(idx)
	state["collected"].append(item_product)

	var total_layers: int = state["collected"].size() + needed_arr.size()
	emit_signal("assembly_progress", pos, state["recipe_key"],
				state["collected"].size(), total_layers)

	# --- Case C: Assembly complete ---
	if needed_arr.is_empty():
		var recipe_key: String = state["recipe_key"]
		# Spawn an assembled item at this tile position
		var assembled_item := {
			"x": item["x"],
			"y": item["y"],
			"progress": 0.0,
			"stage": "assembled",
			"delivery_boost": 0.0,
			"ingredient_type": "",
			"product_type": "",
			"recipe_key": recipe_key,
		}
		items.append(assembled_item)
		emit_signal("item_spawned", assembled_item)
		emit_signal("assembly_completed", pos, recipe_key)
		_log_event("Assembly complete: %s" % recipe_key)
		# Reset the table for the next pizza
		state["recipe_key"] = ""
		state["collected"] = []
		state["needed"] = []

	return true

## Find a recipe whose required products include the given product_type.
## Prefers recipes where the product is the base ingredient.
func _find_recipe_for_product(product_type: String) -> String:
	var available = recipe_catalog.get_available_recipes(expansion_level, tech_tree)
	# First pass: look for recipes where product_type is the base
	for key in available:
		var recipe = recipe_catalog.get_recipe(key)
		if recipe.get("base", "") == product_type:
			return key
	# Second pass: any recipe that needs this product
	for key in available:
		var required = recipe_catalog.get_required_products(key)
		if product_type in required:
			return key
	return ""

func _resolve_order_for_item(item: Dictionary):
	if orders.is_empty():
		return null
	
	if item.get("recipe_key", "") != "":
		for i in range(orders.size()):
			if orders[i]["recipe_key"] == item["recipe_key"]:
				return orders.pop_at(i)
		return null
	
	# Try to match by ingredient type
	if orders.size() == 1:
		return orders.pop_at(0)
	return orders.pop_at(0) if not orders.is_empty() else null

func _enqueue_delivery(order: Dictionary) -> void:
	if order.get("channel_key", "") == "eat_in":
		completed += 1
		ontime += 1
		money += order["reward"]
		total_revenue += order["reward"]
		reputation = clampf(reputation + GC.REPUTATION_GAIN_ONTIME, 0.0, 100.0)
		emit_signal("delivery_completed", order["recipe_key"], order["reward"])
		emit_signal("money_changed", money)
		return
	
	var travel = rng.randf_range(3.5, 7.5)
	var delivery = {
		"mode": "drone",
		"remaining": travel,
		"elapsed": 0.0,
		"sla": max(2.5, order.get("remaining_sla", 10.0)),
		"duration": travel,
		"recipe_key": order["recipe_key"],
		"reward": order["reward"],
		"channel_key": order.get("channel_key", "delivery"),
	}
	deliveries.append(delivery)

func _process_deliveries(dt: float) -> void:
	var completed_indices: Array[int] = []
	for i in range(deliveries.size()):
		deliveries[i]["remaining"] -= dt
		deliveries[i]["elapsed"] += dt
		
		if deliveries[i]["remaining"] <= 0.0:
			var d = deliveries[i]
			completed += 1
			var is_ontime = d["elapsed"] <= d["sla"]
			if is_ontime:
				ontime += 1
				reputation = clampf(reputation + GC.REPUTATION_GAIN_ONTIME, 0.0, 100.0)
				money += d["reward"]
				total_revenue += d["reward"]
			else:
				reputation = clampf(reputation - GC.REPUTATION_LOSS_LATE, 0.0, 100.0)
				var late_pay = int(d["reward"] * GC.LATE_DELIVERY_PENALTY)
				money += late_pay
				total_revenue += late_pay
			emit_signal("delivery_completed", d["recipe_key"], d["reward"])
			emit_signal("money_changed", money)
			completed_indices.append(i)
	
	completed_indices.reverse()
	for idx in completed_indices:
		deliveries.remove_at(idx)

func _process_orders(dt: float) -> void:
	var expired_indices: Array[int] = []
	for i in range(orders.size()):
		orders[i]["remaining_sla"] -= dt
		if orders[i]["remaining_sla"] <= 0.0:
			_mark_order_missed(orders[i])
			expired_indices.append(i)
	
	expired_indices.reverse()
	for idx in expired_indices:
		orders.remove_at(idx)

func _mark_order_missed(order: Dictionary) -> void:
	reputation = clampf(reputation - GC.REPUTATION_LOSS_MISSED_ORDER, 0.0, 100.0)
	var penalty = int(float(order.get("reward", 0)) * GC.MISSED_ORDER_CASH_PENALTY_MULTIPLIER)
	var charged = min(money, penalty)
	money -= charged
	total_spend += charged
	emit_signal("money_changed", money)
	_log_event("Order expired: %s (-$%d)" % [order.get("recipe_key", "?"), charged])

func _process_research() -> void:
	if research_focus != "":
		var focus_cost = research_catalog.get_cost(research_focus)
		if research_points >= focus_cost and not tech_tree.get(research_focus, false):
			if research_catalog.prerequisites_met(research_focus, tech_tree):
				tech_tree[research_focus] = true
				_log_event("Research unlocked: %s" % research_focus)
				emit_signal("research_unlocked", research_focus)
				research_focus = ""
		return
	
	# Auto-unlock if no focus
	for tech_key in research_catalog.research:
		if tech_tree.get(tech_key, false):
			continue
		if not research_catalog.prerequisites_met(tech_key, tech_tree):
			continue
		if research_points >= research_catalog.get_cost(tech_key):
			tech_tree[tech_key] = true
			_log_event("Research auto-unlocked: %s" % tech_key)
			emit_signal("research_unlocked", tech_key)

func _log_event(message: String) -> void:
	event_log.append(message)
	if event_log.size() > 12:
		event_log = event_log.slice(-12)

# ------------------------------------------------------------------
# Save / Load
# ------------------------------------------------------------------

func to_dict() -> Dictionary:
	return {
		"grid": grid.duplicate(true),
		"items": items.duplicate(true),
		"orders": orders.duplicate(true),
		"deliveries": deliveries.duplicate(true),
		"sim_time": sim_time,
		"money": money,
		"total_revenue": total_revenue,
		"total_spend": total_spend,
		"waste": waste,
		"hygiene": hygiene,
		"expansion_level": expansion_level,
		"expansion_progress": expansion_progress,
		"research_points": research_points,
		"tech_tree": tech_tree.duplicate(),
		"completed": completed,
		"ontime": ontime,
		"reputation": reputation,
		"order_channel": order_channel,
		"commercial_strategy": commercial_strategy,
		"research_focus": research_focus,
		"event_log": event_log.duplicate(),
		"assembly_state": _serialize_assembly_state(),
		"splitter_toggles": _serialize_vec2i_dict(splitter_toggles),
		"inserter_timers": _serialize_vec2i_dict(inserter_timers),
	}

func load_from_dict(data: Dictionary) -> void:
	if data.has("grid"):
		grid = data["grid"]
	if data.has("money"):
		money = int(data["money"])
	if data.has("tech_tree"):
		tech_tree = data["tech_tree"]
	if data.has("reputation"):
		reputation = float(data["reputation"])
	if data.has("research_points"):
		research_points = float(data["research_points"])
	if data.has("assembly_state"):
		_deserialize_assembly_state(data["assembly_state"])
	if data.has("splitter_toggles"):
		splitter_toggles = _deserialize_vec2i_dict_bool(data["splitter_toggles"])
	if data.has("inserter_timers"):
		inserter_timers = _deserialize_vec2i_dict_float(data["inserter_timers"])
	emit_signal("money_changed", money)

## Convert assembly_state (Vector2i keys) to serializable format (string keys).
func _serialize_assembly_state() -> Dictionary:
	var result: Dictionary = {}
	for pos in assembly_state:
		var key_str: String = "%d,%d" % [pos.x, pos.y]
		result[key_str] = assembly_state[pos].duplicate(true)
	return result

## Restore assembly_state from serialized format (string keys -> Vector2i).
func _deserialize_assembly_state(data: Dictionary) -> void:
	assembly_state.clear()
	for key_str in data:
		var parts = str(key_str).split(",")
		if parts.size() == 2:
			var pos := Vector2i(int(parts[0]), int(parts[1]))
			assembly_state[pos] = data[key_str]

## Generic serializer for Vector2i-keyed dictionaries.
func _serialize_vec2i_dict(d: Dictionary) -> Dictionary:
	var result: Dictionary = {}
	for pos in d:
		var key_str: String = "%d,%d" % [pos.x, pos.y]
		result[key_str] = d[pos]
	return result

## Deserialize Vector2i-keyed dict with bool values.
func _deserialize_vec2i_dict_bool(data: Dictionary) -> Dictionary:
	var result: Dictionary = {}
	for key_str in data:
		var parts = str(key_str).split(",")
		if parts.size() == 2:
			var pos := Vector2i(int(parts[0]), int(parts[1]))
			result[pos] = bool(data[key_str])
	return result

## Deserialize Vector2i-keyed dict with float values.
func _deserialize_vec2i_dict_float(data: Dictionary) -> Dictionary:
	var result: Dictionary = {}
	for key_str in data:
		var parts = str(key_str).split(",")
		if parts.size() == 2:
			var pos := Vector2i(int(parts[0]), int(parts[1]))
			result[pos] = float(data[key_str])
	return result
