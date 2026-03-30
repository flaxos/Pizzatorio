extends CanvasLayer

## GameHUD — Top-level UI overlay.
## Displays money, reputation, research, orders, location name, build toolbar.

const _SpriteRegistry = preload("res://src/data/SpriteRegistry.gd")

@onready var money_label: Label = $TopBar/MoneyLabel
@onready var reputation_label: Label = $TopBar/ReputationLabel
@onready var research_label: Label = $TopBar/ResearchLabel
@onready var orders_label: Label = $TopBar/OrdersLabel
@onready var event_log_label: RichTextLabel = $SidePanel/EventLog
@onready var build_menu: VBoxContainer = $SidePanel/BuildMenu
@onready var notification_label: Label = $NotificationLabel
@onready var tool_label: Label = $TopBar/ToolLabel
@onready var location_label: Label = $TopBar/LocationLabel

var simulation: SimulationCore
var location_manager: LocationManager
var notification_timer: float = 0.0
var deliveries_in_flight: int = 0

# Toolbar state
var _toolbar_buttons: Dictionary = {}  # tool_key -> Button node
var _selected_tool: String = "conveyor"
var _current_rotation: int = 0
var _rotation_label: Label
var _status_label: Label

# Tool definitions (mirrors PlayerController.BUILD_TOOLS)
const TOOLS: Array = [
	{"key": "conveyor", "label": "Conveyor", "cost": 10, "shortcut": "1"},
	{"key": "processor", "label": "Processor", "cost": 80, "shortcut": "2"},
	{"key": "oven", "label": "Oven", "cost": 150, "shortcut": "3"},
	{"key": "bot_dock", "label": "Bot Dock", "cost": 200, "shortcut": "4"},
	{"key": "delete", "label": "Delete", "cost": 0, "shortcut": "5"},
	{"key": "assembly", "label": "Assembly", "cost": 120, "shortcut": "6"},
	{"key": "splitter", "label": "Splitter", "cost": 40, "shortcut": "7"},
	{"key": "inserter", "label": "Inserter", "cost": 60, "shortcut": "8"},
	{"key": "priority_lane", "label": "Priority", "cost": 30, "shortcut": "9"},
	{"key": "source", "label": "Source", "cost": 0, "shortcut": "0"},
	{"key": "sink", "label": "Sink", "cost": 0, "shortcut": "="},
]

const ROTATION_ARROWS: Dictionary = {0: "→", 1: "↓", 2: "←", 3: "↑"}

func _ready() -> void:
	# Connect to EventBus for notifications and tool sync
	EventBus.show_notification.connect(_on_notification)
	EventBus.on_tick.connect(_on_tick_update)
	EventBus.tool_selected.connect(_on_tool_selected_sync)
	EventBus.rotation_changed.connect(_on_rotation_changed_sync)

	# Build the bottom toolbar
	_create_toolbar()

	# We'll find the LocationManager after the scene tree is ready
	await get_tree().process_frame
	var factory = get_tree().get_first_node_in_group("factory_floor")
	if factory:
		location_manager = factory.get_node_or_null("LocationManager")
		if location_manager:
			location_manager.location_switched.connect(_on_location_switched)
			simulation = location_manager.get_active_simulation()
			_connect_simulation(simulation)
			_update_location_label()
		else:
			simulation = factory.get_node_or_null("SimulationCore")
			_connect_simulation(simulation)

func _connect_simulation(sim: SimulationCore) -> void:
	if sim == null:
		return
	sim.money_changed.connect(_on_money_changed)
	sim.research_unlocked.connect(_on_research_unlocked)
	sim.delivery_created.connect(_on_delivery_created)
	sim.delivery_completed.connect(_on_delivery_completed_hud)

func _disconnect_simulation(sim: SimulationCore) -> void:
	if sim == null:
		return
	if sim.money_changed.is_connected(_on_money_changed):
		sim.money_changed.disconnect(_on_money_changed)
	if sim.research_unlocked.is_connected(_on_research_unlocked):
		sim.research_unlocked.disconnect(_on_research_unlocked)
	if sim.delivery_created.is_connected(_on_delivery_created):
		sim.delivery_created.disconnect(_on_delivery_created)
	if sim.delivery_completed.is_connected(_on_delivery_completed_hud):
		sim.delivery_completed.disconnect(_on_delivery_completed_hud)

func _on_location_switched(_old_key: String, _new_key: String) -> void:
	_disconnect_simulation(simulation)
	simulation = location_manager.get_active_simulation()
	_connect_simulation(simulation)
	deliveries_in_flight = 0
	_update_location_label()

func _update_location_label() -> void:
	if location_label == null:
		return
	if location_manager == null:
		location_label.text = ""
		return
	var name_text: String = location_manager.get_active_display_name()
	var count: int = location_manager.get_location_count()
	if count > 1:
		var keys: Array = location_manager.get_location_keys()
		var idx: int = keys.find(location_manager.active_location) + 1
		location_label.text = "%s (%d/%d)" % [name_text, idx, count]
	else:
		location_label.text = name_text

func _on_money_changed(new_amount: int) -> void:
	if money_label:
		money_label.text = "$%d" % new_amount

func _on_research_unlocked(tech_key: String) -> void:
	_on_notification("Research unlocked: %s" % tech_key, "success")

func _on_notification(message: String, type: String) -> void:
	if notification_label:
		notification_label.text = message
		notification_label.visible = true
		notification_timer = 3.0
		match type:
			"success": notification_label.add_theme_color_override("font_color", Color(0.3, 0.85, 0.4))
			"warning": notification_label.add_theme_color_override("font_color", Color(0.95, 0.75, 0.3))
			"error": notification_label.add_theme_color_override("font_color", Color(0.95, 0.35, 0.35))
			_: notification_label.add_theme_color_override("font_color", Color(0.85, 0.88, 0.95))

func _on_tick_update(_tick: int) -> void:
	if simulation == null:
		return

	if reputation_label:
		reputation_label.text = "Rep: %.0f" % simulation.reputation
	if research_label:
		research_label.text = "RP: %.1f" % simulation.research_points
	if orders_label:
		var delivery_text := ""
		if deliveries_in_flight > 0:
			delivery_text = " | Deliveries: %d in-flight" % deliveries_in_flight
		orders_label.text = "Orders: %d%s" % [simulation.orders.size(), delivery_text]
	if event_log_label:
		event_log_label.text = "\n".join(simulation.event_log)

func _on_delivery_created(_delivery_data: Dictionary) -> void:
	deliveries_in_flight += 1

func _on_delivery_completed_hud(_recipe_key: String, _reward: int) -> void:
	deliveries_in_flight = maxi(deliveries_in_flight - 1, 0)

func _process(delta: float) -> void:
	if notification_timer > 0.0:
		notification_timer -= delta
		if notification_timer <= 0.0 and notification_label:
			notification_label.visible = false

# ------------------------------------------------------------------
# Bottom Toolbar
# ------------------------------------------------------------------

func _create_toolbar() -> void:
	var toolbar = PanelContainer.new()
	toolbar.name = "BottomToolbar"
	# Anchor to bottom, full width
	toolbar.anchor_left = 0.0
	toolbar.anchor_right = 1.0
	toolbar.anchor_top = 1.0
	toolbar.anchor_bottom = 1.0
	toolbar.offset_top = -80.0
	toolbar.grow_vertical = Control.GROW_DIRECTION_BEGIN

	# Dark background
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.1, 0.1, 0.18, 0.92)
	style.border_color = Color(0.17, 0.17, 0.3)
	style.set_border_width_all(1)
	style.border_width_top = 2
	style.content_margin_left = 8
	style.content_margin_right = 8
	style.content_margin_top = 4
	style.content_margin_bottom = 4
	toolbar.add_theme_stylebox_override("panel", style)

	var vbox = VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 2)
	toolbar.add_child(vbox)

	# Row of build buttons
	var button_row = HBoxContainer.new()
	button_row.add_theme_constant_override("separation", 4)
	button_row.alignment = BoxContainer.ALIGNMENT_CENTER
	vbox.add_child(button_row)

	for tool_def in TOOLS:
		var btn = _create_tool_button(tool_def)
		button_row.add_child(btn)
		_toolbar_buttons[tool_def["key"]] = btn

	# Status line: rotation + selected tool info
	var status_row = HBoxContainer.new()
	status_row.add_theme_constant_override("separation", 20)
	status_row.alignment = BoxContainer.ALIGNMENT_CENTER
	vbox.add_child(status_row)

	_rotation_label = Label.new()
	_rotation_label.text = "Rot: →"
	_rotation_label.add_theme_font_size_override("font_size", 12)
	_rotation_label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.8))
	status_row.add_child(_rotation_label)

	_status_label = Label.new()
	_status_label.text = "Selected: Conveyor ($10)"
	_status_label.add_theme_font_size_override("font_size", 12)
	_status_label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.8))
	status_row.add_child(_status_label)

	add_child(toolbar)

	# Highlight initial selection
	_update_toolbar_selection("conveyor")

func _create_tool_button(tool_def: Dictionary) -> Button:
	var btn = Button.new()
	btn.custom_minimum_size = Vector2(56, 52)
	btn.focus_mode = Control.FOCUS_NONE
	btn.mouse_filter = Control.MOUSE_FILTER_STOP

	# Style
	var normal_style = StyleBoxFlat.new()
	normal_style.bg_color = Color(0.13, 0.13, 0.27)
	normal_style.border_color = Color(0.23, 0.23, 0.37)
	normal_style.set_border_width_all(1)
	normal_style.set_corner_radius_all(3)
	normal_style.content_margin_left = 2
	normal_style.content_margin_right = 2
	normal_style.content_margin_top = 2
	normal_style.content_margin_bottom = 2
	btn.add_theme_stylebox_override("normal", normal_style)

	var hover_style = normal_style.duplicate()
	hover_style.border_color = Color(0.35, 0.48, 0.87)
	hover_style.bg_color = Color(0.16, 0.16, 0.37)
	btn.add_theme_stylebox_override("hover", hover_style)

	var pressed_style = normal_style.duplicate()
	pressed_style.border_color = Color(0.48, 0.69, 1.0)
	pressed_style.bg_color = Color(0.16, 0.23, 0.43)
	btn.add_theme_stylebox_override("pressed", pressed_style)

	# Content layout via VBoxContainer
	var vbox = VBoxContainer.new()
	vbox.alignment = BoxContainer.ALIGNMENT_CENTER
	vbox.add_theme_constant_override("separation", 0)
	vbox.mouse_filter = Control.MOUSE_FILTER_IGNORE
	btn.add_child(vbox)

	# Shortcut hint
	var shortcut_label = Label.new()
	shortcut_label.text = tool_def["shortcut"]
	shortcut_label.add_theme_font_size_override("font_size", 9)
	shortcut_label.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	shortcut_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	shortcut_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	vbox.add_child(shortcut_label)

	# Icon (sprite or fallback colored rect)
	var icon_container = CenterContainer.new()
	icon_container.custom_minimum_size = Vector2(32, 20)
	icon_container.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var tile_key = tool_def["key"]
	if tile_key == "assembly":
		tile_key = "assembly_table"
	var texture = _SpriteRegistry.get_tool_icon(tile_key)
	if texture == null:
		texture = _SpriteRegistry.get_tile_texture(tile_key)
	if texture:
		var tex_rect = TextureRect.new()
		tex_rect.texture = texture
		tex_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		tex_rect.custom_minimum_size = Vector2(20, 20)
		tex_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
		icon_container.add_child(tex_rect)
	vbox.add_child(icon_container)

	# Tool name
	var name_label = Label.new()
	name_label.text = tool_def["label"]
	name_label.add_theme_font_size_override("font_size", 9)
	name_label.add_theme_color_override("font_color", Color(0.65, 0.65, 0.75))
	name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	vbox.add_child(name_label)

	# Cost
	var cost_text = "free" if tool_def["cost"] == 0 else "$%d" % tool_def["cost"]
	var cost_label = Label.new()
	cost_label.text = cost_text
	cost_label.add_theme_font_size_override("font_size", 9)
	cost_label.add_theme_color_override("font_color", Color(0.94, 0.75, 0.25) if tool_def["cost"] > 0 else Color(0.5, 0.7, 0.5))
	cost_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	cost_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	vbox.add_child(cost_label)

	# Connect click
	btn.pressed.connect(_on_toolbar_button_pressed.bind(tool_def["key"]))
	return btn

func _on_toolbar_button_pressed(tool_key: String) -> void:
	EventBus.tool_selected.emit(tool_key)
	EventBus.show_notification.emit("Selected: %s" % tool_key.capitalize(), "info")
	_update_toolbar_selection(tool_key)

func _on_tool_selected_sync(tool_key: String) -> void:
	_selected_tool = tool_key
	_update_toolbar_selection(tool_key)

func _on_rotation_changed_sync(rot: int) -> void:
	_current_rotation = rot
	if _rotation_label:
		_rotation_label.text = "Rot: %s" % ROTATION_ARROWS.get(rot, "→")

func _update_toolbar_selection(tool_key: String) -> void:
	_selected_tool = tool_key
	for key in _toolbar_buttons:
		var btn: Button = _toolbar_buttons[key]
		if key == tool_key:
			# Selected style
			var sel_style = StyleBoxFlat.new()
			sel_style.bg_color = Color(0.16, 0.23, 0.43)
			sel_style.border_color = Color(0.48, 0.69, 1.0)
			sel_style.set_border_width_all(2)
			sel_style.set_corner_radius_all(3)
			sel_style.content_margin_left = 2
			sel_style.content_margin_right = 2
			sel_style.content_margin_top = 2
			sel_style.content_margin_bottom = 2
			btn.add_theme_stylebox_override("normal", sel_style)
		else:
			# Normal style
			var norm_style = StyleBoxFlat.new()
			norm_style.bg_color = Color(0.13, 0.13, 0.27)
			norm_style.border_color = Color(0.23, 0.23, 0.37)
			norm_style.set_border_width_all(1)
			norm_style.set_corner_radius_all(3)
			norm_style.content_margin_left = 2
			norm_style.content_margin_right = 2
			norm_style.content_margin_top = 2
			norm_style.content_margin_bottom = 2
			btn.add_theme_stylebox_override("normal", norm_style)

	# Update status label
	if _status_label:
		for tool_def in TOOLS:
			if tool_def["key"] == tool_key:
				var cost_text = "free" if tool_def["cost"] == 0 else "$%d" % tool_def["cost"]
				_status_label.text = "Selected: %s (%s)" % [tool_def["label"], cost_text]
				break
