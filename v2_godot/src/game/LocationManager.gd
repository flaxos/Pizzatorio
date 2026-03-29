extends Node
class_name LocationManager

## LocationManager — Manages multiple locations, each with its own SimulationCore.
## Provides transport links between locations and a shared economy.
## Backward compatible: a single pizza_shop location works identically to the old system.

const GC = preload("res://src/autoloads/GlobalConfig.gd")

signal location_added(key: String, type: String)
signal location_removed(key: String)
signal location_switched(old_key: String, new_key: String)
signal transport_arrived(from_key: String, to_key: String, items: Array)

# Each location entry:
# {
#   "key": String,
#   "type": String,              # e.g. "pizza_shop", "dough_factory"
#   "display_name": String,
#   "simulation": SimulationCore,
#   "unlocked": bool,
#   "grid_w": int,
#   "grid_h": int,
# }
var locations: Dictionary = {}  # key -> location dict

# Transport links between locations:
# {
#   "from_location": String,
#   "to_location": String,
#   "travel_time": float,
#   "in_transit": Array,  # Array of { "item": Dictionary, "remaining": float }
#   "auto_export": bool,
#   "filter": Array[String],  # product types to transport
# }
var transport_links: Array = []

var active_location: String = ""

# Shared economy — all locations contribute to and draw from this pool
var shared_money: int = GC.STARTING_MONEY

# --- Ordered list of location keys for Tab cycling ---
var _location_order: Array[String] = []

# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------

func _ready() -> void:
	pass

# ------------------------------------------------------------------
# Location Management
# ------------------------------------------------------------------

## Add a new location of the given type. Returns true if successful.
func add_location(key: String, type: String, display_name: String = "") -> bool:
	if locations.has(key):
		push_warning("LocationManager: location '%s' already exists" % key)
		return false

	var type_config: Dictionary = GC.LOCATION_TYPES.get(type, {})
	if type_config.is_empty():
		push_warning("LocationManager: unknown location type '%s'" % type)
		return false

	# Check unlock cost (skip for first location or zero-cost types)
	var cost: int = int(type_config.get("unlock_cost", 0))
	if not locations.is_empty() and cost > 0:
		if shared_money < cost:
			return false
		shared_money -= cost

	var loc_display_name: String = display_name if display_name != "" else type_config.get("display_name", key)

	# Create a new SimulationCore instance
	var sim := SimulationCore.new()
	sim.name = "SimulationCore_%s" % key
	sim.location_key = key
	sim.grid_w = int(type_config.get("grid_w", GC.GRID_W))
	sim.grid_h = int(type_config.get("grid_h", GC.GRID_H))
	add_child(sim)  # _ready() fires here, initializes grid with default money

	# Connect the export signal so transport links can pick up items
	sim.item_exported.connect(_on_item_exported.bind(key))
	# Connect money_changed to keep shared economy in sync
	sim.money_changed.connect(_on_sim_money_changed.bind(key))

	var location_data: Dictionary = {
		"key": key,
		"type": type,
		"display_name": loc_display_name,
		"simulation": sim,
		"unlocked": true,
		"grid_w": sim.grid_w,
		"grid_h": sim.grid_h,
	}
	locations[key] = location_data
	_location_order.append(key)

	# If this is the first location, make it active
	if active_location == "":
		active_location = key

	# Sync money to new sim
	_sync_money_to_all()

	emit_signal("location_added", key, type)
	return true

## Remove a location. Cannot remove the active location if it's the only one.
func remove_location(key: String) -> bool:
	if not locations.has(key):
		return false
	if locations.size() <= 1:
		push_warning("LocationManager: cannot remove the last location")
		return false

	var loc: Dictionary = locations[key]
	var sim: SimulationCore = loc["simulation"]

	# Remove transport links involving this location
	var links_to_remove: Array[int] = []
	for i in range(transport_links.size()):
		var link: Dictionary = transport_links[i]
		if link["from_location"] == key or link["to_location"] == key:
			links_to_remove.append(i)
	links_to_remove.reverse()
	for idx in links_to_remove:
		transport_links.remove_at(idx)

	# Switch away if this was active
	if active_location == key:
		var idx_in_order: int = _location_order.find(key)
		_location_order.erase(key)
		if _location_order.size() > 0:
			var new_idx: int = mini(idx_in_order, _location_order.size() - 1)
			switch_location(_location_order[new_idx])
	else:
		_location_order.erase(key)

	sim.queue_free()
	locations.erase(key)

	emit_signal("location_removed", key)
	return true

## Switch to a different location. Returns true if successful.
func switch_location(key: String) -> bool:
	if not locations.has(key):
		return false
	if key == active_location:
		return true

	var old_key: String = active_location
	active_location = key
	emit_signal("location_switched", old_key, key)
	return true

## Cycle to the next location (for Tab key).
func switch_to_next_location() -> bool:
	if _location_order.size() <= 1:
		return false
	var current_idx: int = _location_order.find(active_location)
	var next_idx: int = (current_idx + 1) % _location_order.size()
	return switch_location(_location_order[next_idx])

## Cycle to the previous location (for Shift+Tab).
func switch_to_prev_location() -> bool:
	if _location_order.size() <= 1:
		return false
	var current_idx: int = _location_order.find(active_location)
	var prev_idx: int = (current_idx - 1 + _location_order.size()) % _location_order.size()
	return switch_location(_location_order[prev_idx])

## Get the SimulationCore for the currently active location.
func get_active_simulation() -> SimulationCore:
	if active_location == "" or not locations.has(active_location):
		return null
	return locations[active_location]["simulation"]

## Get the SimulationCore for a specific location.
func get_simulation(key: String) -> SimulationCore:
	if not locations.has(key):
		return null
	return locations[key]["simulation"]

## Get location data dictionary for a specific location.
func get_location_data(key: String) -> Dictionary:
	return locations.get(key, {})

## Get the display name of the active location.
func get_active_display_name() -> String:
	if active_location == "" or not locations.has(active_location):
		return ""
	return locations[active_location].get("display_name", active_location)

## Get count of locations.
func get_location_count() -> int:
	return locations.size()

## Get all location keys in order.
func get_location_keys() -> Array[String]:
	return _location_order.duplicate()

# ------------------------------------------------------------------
# Transport Links
# ------------------------------------------------------------------

## Add a transport link between two locations.
func add_transport_link(from_key: String, to_key: String, filter: Array = [], travel_time: float = 5.0, auto_export: bool = true) -> bool:
	if not locations.has(from_key) or not locations.has(to_key):
		return false
	if from_key == to_key:
		return false

	var link: Dictionary = {
		"from_location": from_key,
		"to_location": to_key,
		"travel_time": travel_time,
		"in_transit": [],
		"auto_export": auto_export,
		"filter": filter.duplicate(),
	}
	transport_links.append(link)
	return true

## Remove a transport link by index.
func remove_transport_link(index: int) -> bool:
	if index < 0 or index >= transport_links.size():
		return false
	transport_links.remove_at(index)
	return true

## Process all transport links — move items in transit, deliver arrived items.
func process_transports(dt: float) -> void:
	for link in transport_links:
		var arrivals: Array = []
		var remaining_transit: Array = []

		for shipment in link["in_transit"]:
			shipment["remaining"] -= dt
			if shipment["remaining"] <= 0.0:
				arrivals.append(shipment["item"])
			else:
				remaining_transit.append(shipment)

		link["in_transit"] = remaining_transit

		# Deliver arrived items to destination location
		if arrivals.size() > 0:
			var dest_sim: SimulationCore = get_simulation(link["to_location"])
			if dest_sim != null:
				for item_data in arrivals:
					_inject_item_at_source(dest_sim, item_data)
				emit_signal("transport_arrived", link["from_location"], link["to_location"], arrivals)

## Inject an item into a location's source tile.
func _inject_item_at_source(sim: SimulationCore, item_data: Dictionary) -> void:
	# Find a source tile in the destination grid
	for y in range(sim.grid_h):
		for x in range(sim.grid_w):
			if sim.grid[y][x]["kind"] == "source":
				var new_item: Dictionary = item_data.duplicate()
				new_item["x"] = x
				new_item["y"] = y
				new_item["progress"] = 0.0
				sim.items.append(new_item)
				sim.emit_signal("item_spawned", new_item)
				return

# ------------------------------------------------------------------
# Shared Economy
# ------------------------------------------------------------------

## Sync the shared money pool to all SimulationCore instances.
func _sync_money_to_all() -> void:
	for key in locations:
		var sim: SimulationCore = locations[key]["simulation"]
		sim.money = shared_money

## Called when any SimulationCore's money changes — update shared pool.
func _on_sim_money_changed(new_amount: int, from_key: String) -> void:
	# Calculate the delta from this sim's change
	var sim: SimulationCore = get_simulation(from_key)
	if sim == null:
		return
	shared_money = new_amount
	# Propagate to other sims
	for key in locations:
		if key != from_key:
			var other_sim: SimulationCore = locations[key]["simulation"]
			other_sim.money = shared_money

## Called when a SimulationCore emits item_exported.
func _on_item_exported(item_data: Dictionary, from_key: String) -> void:
	# Check transport links for auto-export
	for link in transport_links:
		if link["from_location"] != from_key:
			continue
		if not link["auto_export"]:
			continue
		# Check filter
		if link["filter"].size() > 0:
			var product_type: String = item_data.get("product_type", "")
			var stage: String = item_data.get("stage", "")
			var recipe_key: String = item_data.get("recipe_key", "")
			var matched: bool = false
			for f in link["filter"]:
				if f == product_type or f == stage or f == recipe_key:
					matched = true
					break
			if not matched:
				continue
		# Enqueue shipment
		var shipment: Dictionary = {
			"item": item_data.duplicate(),
			"remaining": link["travel_time"],
		}
		link["in_transit"].append(shipment)
		return  # Only send to first matching link

# ------------------------------------------------------------------
# Tick all locations
# ------------------------------------------------------------------

## Tick all location simulations. Called by FactoryFloor or TimeManager.
func tick_all(tick_count: int) -> void:
	# Process transport first so items arrive before sim ticks
	process_transports(GC.TICK_RATE)

	# Tick each location
	for key in _location_order:
		var sim: SimulationCore = locations[key]["simulation"]
		sim.sim_tick(tick_count)

	# After all ticks, sync money from active sim to shared pool
	var active_sim: SimulationCore = get_active_simulation()
	if active_sim != null:
		shared_money = active_sim.money

# ------------------------------------------------------------------
# Save / Load
# ------------------------------------------------------------------

func to_dict() -> Dictionary:
	var locations_data: Dictionary = {}
	for key in locations:
		var loc: Dictionary = locations[key]
		var sim: SimulationCore = loc["simulation"]
		locations_data[key] = {
			"key": key,
			"type": loc["type"],
			"display_name": loc["display_name"],
			"unlocked": loc["unlocked"],
			"grid_w": loc["grid_w"],
			"grid_h": loc["grid_h"],
			"simulation": sim.to_dict(),
		}

	var links_data: Array = []
	for link in transport_links:
		var transit_data: Array = []
		for shipment in link["in_transit"]:
			transit_data.append({
				"item": shipment["item"].duplicate(),
				"remaining": shipment["remaining"],
			})
		links_data.append({
			"from_location": link["from_location"],
			"to_location": link["to_location"],
			"travel_time": link["travel_time"],
			"auto_export": link["auto_export"],
			"filter": link["filter"].duplicate(),
			"in_transit": transit_data,
		})

	return {
		"active_location": active_location,
		"shared_money": shared_money,
		"location_order": _location_order.duplicate(),
		"locations": locations_data,
		"transport_links": links_data,
	}

func load_from_dict(data: Dictionary) -> void:
	# Backward compatibility: detect old single-sim save format
	# Old saves have "grid" at top level but no "locations" key
	if data.has("grid") and not data.has("locations"):
		_load_legacy_save(data)
		return

	# Clear existing locations
	for key in locations.keys():
		var sim: SimulationCore = locations[key]["simulation"]
		sim.queue_free()
	locations.clear()
	_location_order.clear()
	transport_links.clear()

	if data.has("shared_money"):
		shared_money = int(data["shared_money"])

	var order: Array = data.get("location_order", [])
	var locs_data: Dictionary = data.get("locations", {})

	# Recreate locations in order
	for key in order:
		if not locs_data.has(key):
			continue
		var loc_data: Dictionary = locs_data[key]
		var loc_type: String = loc_data.get("type", "pizza_shop")
		var loc_display: String = loc_data.get("display_name", key)

		# Create sim without going through add_location (which charges cost)
		var type_config: Dictionary = GC.LOCATION_TYPES.get(loc_type, {})
		var sim := SimulationCore.new()
		sim.name = "SimulationCore_%s" % key
		sim.location_key = key
		sim.grid_w = int(loc_data.get("grid_w", type_config.get("grid_w", GC.GRID_W)))
		sim.grid_h = int(loc_data.get("grid_h", type_config.get("grid_h", GC.GRID_H)))
		add_child(sim)

		# Wait for _ready won't work here in headless; load_from_dict handles it
		if loc_data.has("simulation"):
			sim.load_from_dict(loc_data["simulation"])

		sim.item_exported.connect(_on_item_exported.bind(key))
		sim.money_changed.connect(_on_sim_money_changed.bind(key))

		var location_entry: Dictionary = {
			"key": key,
			"type": loc_type,
			"display_name": loc_display,
			"simulation": sim,
			"unlocked": loc_data.get("unlocked", true),
			"grid_w": sim.grid_w,
			"grid_h": sim.grid_h,
		}
		locations[key] = location_entry
		_location_order.append(key)

	# Restore transport links
	var links_data: Array = data.get("transport_links", [])
	for link_data in links_data:
		var link: Dictionary = {
			"from_location": link_data.get("from_location", ""),
			"to_location": link_data.get("to_location", ""),
			"travel_time": float(link_data.get("travel_time", 5.0)),
			"auto_export": bool(link_data.get("auto_export", true)),
			"filter": link_data.get("filter", []),
			"in_transit": [],
		}
		# Restore in-transit items
		for shipment_data in link_data.get("in_transit", []):
			link["in_transit"].append({
				"item": shipment_data.get("item", {}),
				"remaining": float(shipment_data.get("remaining", 0.0)),
			})
		transport_links.append(link)

	# Restore active location
	if data.has("active_location") and locations.has(data["active_location"]):
		active_location = data["active_location"]
	elif _location_order.size() > 0:
		active_location = _location_order[0]

	# Sync shared money
	_sync_money_to_all()

## Load a legacy save file (pre-multi-location format) into a single pizza_shop.
func _load_legacy_save(data: Dictionary) -> void:
	# Clear existing
	for key in locations.keys():
		var sim: SimulationCore = locations[key]["simulation"]
		sim.queue_free()
	locations.clear()
	_location_order.clear()
	transport_links.clear()

	# Create a pizza_shop and load the old data into it
	var type_config: Dictionary = GC.LOCATION_TYPES.get("pizza_shop", {})
	var sim := SimulationCore.new()
	sim.name = "SimulationCore_pizza_shop_1"
	sim.location_key = "pizza_shop_1"
	sim.grid_w = int(type_config.get("grid_w", GC.GRID_W))
	sim.grid_h = int(type_config.get("grid_h", GC.GRID_H))
	add_child(sim)

	sim.load_from_dict(data)

	sim.item_exported.connect(_on_item_exported.bind("pizza_shop_1"))
	sim.money_changed.connect(_on_sim_money_changed.bind("pizza_shop_1"))

	var location_entry: Dictionary = {
		"key": "pizza_shop_1",
		"type": "pizza_shop",
		"display_name": "Main Pizza Shop",
		"simulation": sim,
		"unlocked": true,
		"grid_w": sim.grid_w,
		"grid_h": sim.grid_h,
	}
	locations["pizza_shop_1"] = location_entry
	_location_order.append("pizza_shop_1")
	active_location = "pizza_shop_1"
	shared_money = sim.money
	_sync_money_to_all()
