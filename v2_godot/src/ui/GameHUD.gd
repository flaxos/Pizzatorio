extends CanvasLayer

## GameHUD — Top-level UI overlay.
## Displays money, reputation, research, orders, and build menu.

@onready var money_label: Label = $TopBar/MoneyLabel
@onready var reputation_label: Label = $TopBar/ReputationLabel
@onready var research_label: Label = $TopBar/ResearchLabel
@onready var orders_label: Label = $TopBar/OrdersLabel
@onready var event_log_label: RichTextLabel = $SidePanel/EventLog
@onready var build_menu: VBoxContainer = $SidePanel/BuildMenu
@onready var notification_label: Label = $NotificationLabel
@onready var tool_label: Label = $TopBar/ToolLabel

var simulation: SimulationCore
var notification_timer: float = 0.0

func _ready() -> void:
	# Connect to EventBus for notifications
	EventBus.show_notification.connect(_on_notification)
	EventBus.on_tick.connect(_on_tick_update)
	
	# We'll find the simulation core after the scene tree is ready
	await get_tree().process_frame
	var factory = get_tree().get_first_node_in_group("factory_floor")
	if factory:
		simulation = factory.get_node("SimulationCore")
		simulation.money_changed.connect(_on_money_changed)
		simulation.research_unlocked.connect(_on_research_unlocked)

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
		orders_label.text = "Orders: %d" % simulation.orders.size()
	if event_log_label:
		event_log_label.text = "\n".join(simulation.event_log)

func _process(delta: float) -> void:
	if notification_timer > 0.0:
		notification_timer -= delta
		if notification_timer <= 0.0 and notification_label:
			notification_label.visible = false
