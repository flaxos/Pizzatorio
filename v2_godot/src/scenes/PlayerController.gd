extends Node2D

## PlayerController — Handles mouse/touch input for building on the grid.
## Ported from Python main.py GameUI input handling.
## Updated to work with LocationManager for multi-location support.

var selected_tool: String = "conveyor"
var rotation: int = 0
var camera_offset: Vector2 = Vector2.ZERO
var zoom: float = 1.0
var is_dragging: bool = false
var drag_start: Vector2 = Vector2.ZERO
var last_drag_cell: Vector2i = Vector2i(-1, -1)

# Build tool config
var BUILD_TOOLS: Dictionary = {
	"conveyor": {"label": "Conveyor", "tile": "conveyor", "cost": 10},
	"processor": {"label": "Processor", "tile": "processor", "cost": 80},
	"oven": {"label": "Oven", "tile": "oven", "cost": 150},
	"bot_dock": {"label": "Bot Dock", "tile": "bot_dock", "cost": 200},
	"assembly": {"label": "Assembly", "tile": "assembly_table", "cost": 120},
	"splitter": {"label": "Splitter", "tile": "splitter", "cost": 40},
	"inserter": {"label": "Inserter", "tile": "inserter", "cost": 60},
	"priority_lane": {"label": "Priority Lane", "tile": "priority_lane", "cost": 30},
	"delete": {"label": "Delete", "tile": "empty", "cost": 0},
	"source": {"label": "Source [Test]", "tile": "source", "cost": 0},
	"sink": {"label": "Sink [Test]", "tile": "sink", "cost": 0},
}

@onready var factory_floor: Node2D = get_parent()
var simulation: SimulationCore
var location_manager: LocationManager

func _ready() -> void:
	location_manager = factory_floor.get_node("LocationManager")
	# Listen for location switches to update our simulation reference
	location_manager.location_switched.connect(_on_location_switched)
	# Defer getting simulation until after parent _ready has created the initial location
	call_deferred("_deferred_init")

func _deferred_init() -> void:
	simulation = location_manager.get_active_simulation()
	if simulation == null:
		push_warning("PlayerController: simulation is null after deferred init")
	# Listen for tool selection from HUD toolbar
	EventBus.tool_selected.connect(_on_tool_selected_from_hud)

func _on_tool_selected_from_hud(tool_key: String) -> void:
	if tool_key in BUILD_TOOLS:
		selected_tool = tool_key

func _on_location_switched(_old_key: String, new_key: String) -> void:
	simulation = location_manager.get_simulation(new_key)

func _unhandled_input(event: InputEvent) -> void:
	if simulation == null:
		simulation = location_manager.get_active_simulation()
		if simulation == null:
			return
	# Keyboard shortcuts (matching Python hotkeys)
	if event is InputEventKey and event.pressed:
		match event.keycode:
			KEY_1: _select_tool("conveyor")
			KEY_2: _select_tool("processor")
			KEY_3: _select_tool("oven")
			KEY_4: _select_tool("bot_dock")
			KEY_5: _select_tool("delete")
			KEY_6: _select_tool("assembly")
			KEY_7: _select_tool("splitter")
			KEY_8: _select_tool("inserter")
			KEY_9: _select_tool("priority_lane")
			KEY_0: _select_tool("source")
			KEY_MINUS: _select_tool("source")
			KEY_EQUAL: _select_tool("sink")
			KEY_R: _rotate()
			KEY_F1: _admin_add_money()
			KEY_F2: _admin_unlock_all_research()
			KEY_F3: _admin_advance_expansion()
			KEY_F4: _admin_spawn_items()
			KEY_F5: _admin_toggle_fast_forward()
			KEY_TAB:
				if event.shift_pressed:
					location_manager.switch_to_prev_location()
				else:
					location_manager.switch_to_next_location()
			KEY_S:
				if event.ctrl_pressed:
					_save_game()
			KEY_L:
				if event.ctrl_pressed:
					_load_game()

	# Mouse click to place
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				is_dragging = true
				drag_start = event.position
				last_drag_cell = Vector2i(-1, -1)
				_try_place_at_screen(event.position)
			else:
				is_dragging = false
				last_drag_cell = Vector2i(-1, -1)

		# Right click to delete
		elif event.button_index == MOUSE_BUTTON_RIGHT and event.pressed:
			var grid_pos = _screen_to_grid(event.position)
			if grid_pos != Vector2i(-1, -1) and simulation != null:
				simulation.place_tile(grid_pos.x, grid_pos.y, GlobalConfig.EMPTY, 0)

		# Scroll zoom
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP:
			_set_zoom(zoom * 1.1, event.position)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_set_zoom(zoom / 1.1, event.position)

	# Mouse drag to paint conveyors
	if event is InputEventMouseMotion and is_dragging:
		if selected_tool == "conveyor":
			var grid_pos = _screen_to_grid(event.position)
			if grid_pos != Vector2i(-1, -1) and grid_pos != last_drag_cell and simulation != null:
				simulation.place_tile(grid_pos.x, grid_pos.y,
					BUILD_TOOLS[selected_tool]["tile"], rotation)
				last_drag_cell = grid_pos
		elif event.button_mask & MOUSE_BUTTON_MASK_MIDDLE:
			camera_offset -= event.relative / zoom
			_update_camera()

func _select_tool(tool_key: String) -> void:
	if tool_key in BUILD_TOOLS:
		selected_tool = tool_key
		EventBus.request_build_mode.emit(BUILD_TOOLS[tool_key]["tile"])
		EventBus.tool_selected.emit(tool_key)
		EventBus.show_notification.emit("Selected: %s" % BUILD_TOOLS[tool_key]["label"], "info")

func _rotate() -> void:
	rotation = (rotation + 1) % 4
	EventBus.rotation_changed.emit(rotation)

func _try_place_at_screen(screen_pos: Vector2) -> void:
	var grid_pos = _screen_to_grid(screen_pos)
	if grid_pos == Vector2i(-1, -1):
		return
	if simulation == null:
		return
	var tile_kind = BUILD_TOOLS[selected_tool]["tile"]
	simulation.place_tile(grid_pos.x, grid_pos.y, tile_kind, rotation)
	last_drag_cell = grid_pos

func _screen_to_grid(screen_pos: Vector2) -> Vector2i:
	# Account for camera transform
	var world_pos = (screen_pos + camera_offset) / zoom
	var gx = int(world_pos.x / GlobalConfig.TILE_SIZE)
	var gy = int(world_pos.y / GlobalConfig.TILE_SIZE)
	# Use simulation's grid dimensions for bounds checking
	var gw: int = GlobalConfig.GRID_W
	var gh: int = GlobalConfig.GRID_H
	if simulation != null:
		gw = simulation.grid_w
		gh = simulation.grid_h
	if gx >= 0 and gx < gw and gy >= 0 and gy < gh:
		return Vector2i(gx, gy)
	return Vector2i(-1, -1)

func _set_zoom(new_zoom: float, anchor: Vector2) -> void:
	new_zoom = clampf(new_zoom, 0.5, 3.0)
	var old_zoom = zoom
	zoom = new_zoom
	# Adjust camera to keep anchor point stable
	camera_offset = camera_offset * (new_zoom / old_zoom)
	_update_camera()

func _update_camera() -> void:
	factory_floor.scale = Vector2(zoom, zoom)
	factory_floor.position = -camera_offset * zoom

func _save_game() -> void:
	var save_data = location_manager.to_dict()
	var json_string = JSON.stringify(save_data, "\t")
	var file = FileAccess.open("user://pizzatorio_save.json", FileAccess.WRITE)
	if file:
		file.store_string(json_string)
		EventBus.show_notification.emit("Game saved!", "info")

func _load_game() -> void:
	var file = FileAccess.open("user://pizzatorio_save.json", FileAccess.READ)
	if file:
		var json_string = file.get_as_text()
		var parse_result = JSON.parse_string(json_string)
		if parse_result != null:
			location_manager.load_from_dict(parse_result)
			# Rebind simulation after load
			simulation = location_manager.get_active_simulation()
			EventBus.show_notification.emit("Game loaded!", "info")

# ------------------------------------------------------------------
# Admin / Testing Hotkeys
# ------------------------------------------------------------------

func _admin_add_money() -> void:
	if simulation == null:
		return
	simulation.admin_add_money(500)
	EventBus.show_notification.emit("Admin: +$500", "info")

func _admin_unlock_all_research() -> void:
	if simulation == null:
		return
	simulation.admin_unlock_all_research()
	EventBus.show_notification.emit("Admin: All research unlocked", "info")

func _admin_advance_expansion() -> void:
	if simulation == null:
		return
	simulation.admin_advance_expansion()
	EventBus.show_notification.emit("Admin: Expansion -> level %d" % simulation.expansion_level, "info")

func _admin_spawn_items() -> void:
	if simulation == null:
		return
	simulation.admin_spawn_items(5)
	EventBus.show_notification.emit("Admin: Spawned 5 items", "info")

func _admin_toggle_fast_forward() -> void:
	TimeManager.toggle_fast_forward()
	var speed = TimeManager.speed_multiplier
	EventBus.show_notification.emit("Admin: Speed x%s" % str(speed), "info")
