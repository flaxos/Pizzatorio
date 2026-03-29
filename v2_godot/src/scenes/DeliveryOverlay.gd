extends Node2D

## DeliveryOverlay — Visual-only layer that renders active deliveries as
## animated drone sprites flying from the sink tile toward the screen edge.
## Listens to SimulationCore signals; never mutates simulation state.

const GC = preload("res://src/autoloads/GlobalConfig.gd")

# Sink tile position in grid coords
const SINK_POS := Vector2i(18, 7)

# Drone visual size
const DRONE_SIZE := Vector2(12, 12)

# Flight destination: off the right edge of the screen
var _flight_target_x: float = 0.0

# Active drone visuals keyed by delivery index
# Each entry: { "node": Node2D, "label": Label, "rect": ColorRect,
#                "start_pos": Vector2, "duration": float, "sla": float }
var _drones: Dictionary = {}

# Monotonic ID to track deliveries (since array indices shift on removal)
var _next_drone_id: int = 0
# Maps sim delivery index -> drone_id at creation time
# We rebuild this mapping each tick from delivery data
var _delivery_id_map: Dictionary = {}  # delivery dict ref hash -> drone_id

func _ready() -> void:
	# Compute the pixel position of the flight target (off right edge)
	_flight_target_x = (GC.GRID_W + 4) * GC.TILE_SIZE

var _connected_sim: SimulationCore = null

func connect_simulation(sim: SimulationCore) -> void:
	# Disconnect from previous simulation if any
	disconnect_simulation()
	_connected_sim = sim
	sim.delivery_created.connect(_on_delivery_created)
	sim.delivery_updated.connect(_on_delivery_updated)
	sim.delivery_completed.connect(_on_delivery_completed)

func disconnect_simulation() -> void:
	if _connected_sim == null:
		return
	if _connected_sim.delivery_created.is_connected(_on_delivery_created):
		_connected_sim.delivery_created.disconnect(_on_delivery_created)
	if _connected_sim.delivery_updated.is_connected(_on_delivery_updated):
		_connected_sim.delivery_updated.disconnect(_on_delivery_updated)
	if _connected_sim.delivery_completed.is_connected(_on_delivery_completed):
		_connected_sim.delivery_completed.disconnect(_on_delivery_completed)
	# Clear all active drone visuals on disconnect
	for drone_id in _drones:
		_drones[drone_id]["node"].queue_free()
	_drones.clear()
	_delivery_id_map.clear()
	_connected_sim = null

func _on_delivery_created(delivery_data: Dictionary) -> void:
	var drone_id := _next_drone_id
	_next_drone_id += 1

	# Store the drone_id on the delivery dict so we can track it
	# We use recipe_key + drone_id combo for matching
	var start_pixel := Vector2(
		SINK_POS.x * GC.TILE_SIZE + GC.TILE_SIZE * 0.5 - DRONE_SIZE.x * 0.5,
		SINK_POS.y * GC.TILE_SIZE + GC.TILE_SIZE * 0.5 - DRONE_SIZE.y * 0.5,
	)

	# Build the drone visual: a ColorRect with a "D" label
	var container := Node2D.new()
	container.position = start_pixel

	var rect := ColorRect.new()
	rect.size = DRONE_SIZE
	rect.color = Color(0.3, 0.85, 0.4)  # Start green
	container.add_child(rect)

	var lbl := Label.new()
	lbl.text = "D"
	lbl.position = Vector2(1, -2)
	lbl.add_theme_font_size_override("font_size", 10)
	lbl.add_theme_color_override("font_color", Color(0.1, 0.1, 0.1))
	container.add_child(lbl)

	add_child(container)

	_drones[drone_id] = {
		"node": container,
		"label": lbl,
		"rect": rect,
		"start_pos": start_pixel,
		"duration": delivery_data.get("duration", 5.0),
		"sla": delivery_data.get("sla", 10.0),
	}

	# Store mapping so delivery_updated can find this drone
	_delivery_id_map[delivery_data.get("_drone_id", drone_id)] = drone_id
	delivery_data["_drone_id"] = drone_id

func _on_delivery_updated(drone_id: int, remaining: float, elapsed: float, sla: float) -> void:
	if not _drones.has(drone_id):
		return

	var drone_info: Dictionary = _drones[drone_id]
	var duration: float = drone_info["duration"]

	# Progress 0..1 based on elapsed vs total travel duration
	var progress: float = clampf(elapsed / maxf(duration, 0.01), 0.0, 1.0)

	# Lerp position from sink toward off-screen right
	var start_x: float = drone_info["start_pos"].x
	var target_x: float = _flight_target_x
	var new_x: float = lerpf(start_x, target_x, progress)

	# Add a slight arc (rise then descend)
	var arc_height: float = -30.0 * sin(progress * PI)
	var base_y: float = drone_info["start_pos"].y
	drone_info["node"].position = Vector2(new_x, base_y + arc_height)

	# Color based on SLA usage
	var sla_ratio: float = elapsed / maxf(sla, 0.01)
	var rect: ColorRect = drone_info["rect"]
	if sla_ratio > 0.9:
		rect.color = Color(0.95, 0.3, 0.3)  # Red
	elif sla_ratio > 0.5:
		rect.color = Color(0.95, 0.85, 0.3)  # Yellow
	else:
		rect.color = Color(0.3, 0.85, 0.4)  # Green

func _on_delivery_completed(_recipe_key: String, _reward: int) -> void:
	# Remove the oldest drone (deliveries complete in FIFO order)
	if _drones.is_empty():
		return

	# Find the lowest drone_id (oldest)
	var oldest_id: int = -1
	for did in _drones:
		if oldest_id == -1 or did < oldest_id:
			oldest_id = did

	if oldest_id >= 0 and _drones.has(oldest_id):
		_drones[oldest_id]["node"].queue_free()
		_drones.erase(oldest_id)
