extends Node2D

## FactoryFloor — Visual representation of the grid.
## Listens to SimulationCore signals and draws tiles/items accordingly.

const _SpriteRegistry = preload("res://src/data/SpriteRegistry.gd")

@onready var simulation: SimulationCore = $SimulationCore
@onready var player_controller: Node = $PlayerController

# Grid visual nodes
var tile_visuals: Dictionary = {}  # Vector2i -> Node2D
var item_visuals: Array = []

# Colors for tile kinds (food-grade clean palette)
const TILE_COLORS: Dictionary = {
	"empty": Color(0.92, 0.93, 0.95),         # Light grey floor
	"conveyor": Color(0.78, 0.82, 0.86),       # Steel grey
	"processor": Color(0.60, 0.78, 0.90),       # Soft blue (food machine)
	"oven": Color(0.95, 0.65, 0.45),            # Warm orange
	"bot_dock": Color(0.55, 0.80, 0.65),        # Soft green
	"assembly_table": Color(0.70, 0.65, 0.88),  # Soft purple
	"splitter": Color(0.75, 0.75, 0.55),        # Olive yellow
	"inserter": Color(0.85, 0.70, 0.55),        # Sandy orange
	"priority_lane": Color(0.90, 0.82, 0.55),   # Gold yellow
	"source": Color(0.45, 0.75, 0.45),          # Green (input)
	"sink": Color(0.85, 0.45, 0.45),            # Red (output)
}

const STAGE_COLORS: Dictionary = {
	"raw": Color(0.95, 0.85, 0.60),      # Raw ingredient yellow
	"processed": Color(0.60, 0.85, 0.60), # Processed green
	"baked": Color(0.85, 0.55, 0.35),     # Baked brown-orange
	"assembled": Color(0.80, 0.70, 0.90), # Light purple for assembled pizzas
}

# Direction arrows for conveyors/machines
const ROTATION_ARROWS: Dictionary = {
	0: "→", 1: "↓", 2: "←", 3: "↑",
}

func _ready() -> void:
	simulation.grid_changed.connect(_on_grid_changed)
	simulation.item_spawned.connect(_on_item_spawned)
	simulation.item_moved.connect(_on_item_moved)
	simulation.item_removed.connect(_on_item_removed)
	
	# Connect simulation tick to TimeManager
	EventBus.on_tick.connect(simulation.sim_tick)
	
	# Initial full grid draw
	_draw_full_grid()

func _draw_full_grid() -> void:
	for y in range(GlobalConfig.GRID_H):
		for x in range(GlobalConfig.GRID_W):
			var tile_data = simulation.grid[y][x]
			_create_tile_visual(Vector2i(x, y), tile_data["kind"], tile_data["rot"])

func _create_tile_visual(pos: Vector2i, kind: String, rot: int) -> void:
	# Remove existing visual
	if tile_visuals.has(pos):
		tile_visuals[pos].queue_free()
		tile_visuals.erase(pos)
	
	var tile_node = Node2D.new()
	tile_node.position = Vector2(pos.x * GlobalConfig.TILE_SIZE, pos.y * GlobalConfig.TILE_SIZE)
	
	# Background: sprite if available, else ColorRect fallback
	var texture = _SpriteRegistry.get_tile_texture(kind)
	if texture:
		var sprite = Sprite2D.new()
		sprite.texture = texture
		sprite.centered = false
		var tex_size = texture.get_size()
		if tex_size.x > 0:
			sprite.scale = Vector2(GlobalConfig.TILE_SIZE / tex_size.x, GlobalConfig.TILE_SIZE / tex_size.y)
		tile_node.add_child(sprite)
	else:
		var bg = ColorRect.new()
		bg.size = Vector2(GlobalConfig.TILE_SIZE - 1, GlobalConfig.TILE_SIZE - 1)
		bg.color = TILE_COLORS.get(kind, Color.WHITE)
		tile_node.add_child(bg)
	
	# Direction arrow label for conveyors/machines
	if kind in [GlobalConfig.CONVEYOR, GlobalConfig.PROCESSOR, GlobalConfig.OVEN,
				GlobalConfig.BOT_DOCK, GlobalConfig.ASSEMBLY_TABLE,
				GlobalConfig.SPLITTER, GlobalConfig.INSERTER, GlobalConfig.PRIORITY_LANE]:
		var arrow_label = Label.new()
		arrow_label.text = ROTATION_ARROWS.get(rot, "→")
		arrow_label.position = Vector2(GlobalConfig.TILE_SIZE * 0.3, GlobalConfig.TILE_SIZE * 0.15)
		arrow_label.add_theme_font_size_override("font_size", 18)
		arrow_label.add_theme_color_override("font_color", Color(0.2, 0.2, 0.3, 0.7))
		tile_node.add_child(arrow_label)
	
	# Kind label (small abbreviation)
	if kind != GlobalConfig.EMPTY:
		var kind_label = Label.new()
		var abbreviations = {
			"conveyor": "BLT", "processor": "PRC", "oven": "OVN",
			"bot_dock": "BOT", "assembly_table": "ASM",
			"splitter": "SPL", "inserter": "INS", "priority_lane": "PRI",
			"source": "SRC", "sink": "SNK",
		}
		kind_label.text = abbreviations.get(kind, kind.substr(0, 3).to_upper())
		kind_label.position = Vector2(2, GlobalConfig.TILE_SIZE - 18)
		kind_label.add_theme_font_size_override("font_size", 10)
		kind_label.add_theme_color_override("font_color", Color(0.15, 0.15, 0.25, 0.8))
		tile_node.add_child(kind_label)
	
	add_child(tile_node)
	tile_visuals[pos] = tile_node

func _on_grid_changed(pos: Vector2i, kind: String, rot: int) -> void:
	_create_tile_visual(pos, kind, rot)

func _on_item_spawned(item_data: Dictionary) -> void:
	var stage = item_data.get("stage", "raw")
	var ingredient_type = item_data.get("ingredient_type", "")
	var item_texture = _SpriteRegistry.get_item_texture(stage, ingredient_type)
	var item_node: Node2D
	if item_texture:
		var sprite = Sprite2D.new()
		sprite.texture = item_texture
		sprite.centered = false
		var tex_size = item_texture.get_size()
		if tex_size.x > 0:
			var item_display_size := 12.0
			sprite.scale = Vector2(item_display_size / tex_size.x, item_display_size / tex_size.y)
		item_node = sprite
	else:
		var rect = ColorRect.new()
		rect.size = Vector2(12, 12)
		rect.color = STAGE_COLORS.get(stage, Color.YELLOW)
		item_node = rect
	var pos = Vector2(
		item_data["x"] * GlobalConfig.TILE_SIZE + GlobalConfig.TILE_SIZE * 0.35,
		item_data["y"] * GlobalConfig.TILE_SIZE + GlobalConfig.TILE_SIZE * 0.35,
	)
	item_node.position = pos
	add_child(item_node)
	item_visuals.append(item_node)

func _on_item_moved(item_idx: int, new_pos: Vector2i) -> void:
	if item_idx < item_visuals.size():
		var visual = item_visuals[item_idx]
		# Update appearance based on current stage
		if item_idx < simulation.items.size():
			var item = simulation.items[item_idx]
			var stage = item.get("stage", "raw")
			if visual is Sprite2D:
				var ingr = item.get("ingredient_type", "")
				var new_tex = _SpriteRegistry.get_item_texture(stage, ingr)
				if new_tex:
					visual.texture = new_tex
			elif visual is ColorRect:
				visual.color = STAGE_COLORS.get(stage, Color.YELLOW)
		# Tween to new position for smooth movement
		var target = Vector2(
			new_pos.x * GlobalConfig.TILE_SIZE + GlobalConfig.TILE_SIZE * 0.35,
			new_pos.y * GlobalConfig.TILE_SIZE + GlobalConfig.TILE_SIZE * 0.35,
		)
		var tween = create_tween()
		tween.tween_property(visual, "position", target, 0.3).set_ease(Tween.EASE_OUT)

func _on_item_removed(item_idx: int) -> void:
	if item_idx < item_visuals.size():
		item_visuals[item_idx].queue_free()
		item_visuals.remove_at(item_idx)
