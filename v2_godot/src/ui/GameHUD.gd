extends CanvasLayer

## GameHUD — Top-level UI overlay.
## Displays money, reputation, research, orders, location name, and build menu.

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

func _ready() -> void:
	# Connect to EventBus for notifications
	EventBus.show_notification.connect(_on_notification)
	EventBus.on_tick.connect(_on_tick_update)

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
			# Fallback for legacy: try direct SimulationCore child
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
