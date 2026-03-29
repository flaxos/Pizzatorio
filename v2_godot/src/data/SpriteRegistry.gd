extends Node

## SpriteRegistry — Maps tile kinds, item stages, ingredients, and UI elements to textures.
## Drop-in replacement: swap PNGs in assets/sprites/ and textures update automatically.
## Per-ingredient sprites are looked up first; falls back to stage-based defaults.

static var _tile_cache: Dictionary = {}
static var _item_cache: Dictionary = {}
static var _ui_cache: Dictionary = {}

const TILE_PATHS: Dictionary = {
	"conveyor": "res://assets/sprites/tiles/conveyor.png",
	"processor": "res://assets/sprites/tiles/processor.png",
	"oven": "res://assets/sprites/tiles/oven.png",
	"bot_dock": "res://assets/sprites/tiles/bot_dock.png",
	"assembly_table": "res://assets/sprites/tiles/assembly_table.png",
	"source": "res://assets/sprites/tiles/source.png",
	"sink": "res://assets/sprites/tiles/sink.png",
	"splitter": "res://assets/sprites/tiles/splitter.png",
	"inserter": "res://assets/sprites/tiles/inserter.png",
	"priority_lane": "res://assets/sprites/tiles/priority_lane.png",
}

const STAGE_PATHS: Dictionary = {
	"raw": "res://assets/sprites/items/raw/default.png",
	"processed": "res://assets/sprites/items/processed/default.png",
	"baked": "res://assets/sprites/items/baked/default.png",
	"assembled": "res://assets/sprites/items/assembled/default.png",
}

# Per-ingredient sprites — looked up before stage fallback
const INGREDIENT_PATHS: Dictionary = {
	"flour": "res://assets/sprites/items/ingredients/flour.png",
	"tomato": "res://assets/sprites/items/ingredients/tomato.png",
	"cheese": "res://assets/sprites/items/ingredients/cheese.png",
	"dough": "res://assets/sprites/items/ingredients/dough.png",
	"sauce": "res://assets/sprites/items/ingredients/sauce.png",
	"pepperoni": "res://assets/sprites/items/ingredients/pepperoni.png",
	"mushroom": "res://assets/sprites/items/ingredients/mushroom.png",
	"ham": "res://assets/sprites/items/ingredients/ham.png",
	"pepper": "res://assets/sprites/items/ingredients/pepper.png",
	"onion": "res://assets/sprites/items/ingredients/onion.png",
	"olive": "res://assets/sprites/items/ingredients/olive.png",
	"chicken": "res://assets/sprites/items/ingredients/chicken.png",
	"bacon": "res://assets/sprites/items/ingredients/bacon.png",
	"pineapple": "res://assets/sprites/items/ingredients/pineapple.png",
	"sausage": "res://assets/sprites/items/ingredients/sausage.png",
	"garlic": "res://assets/sprites/items/ingredients/garlic.png",
	"spinach": "res://assets/sprites/items/ingredients/spinach.png",
	"jalapeno": "res://assets/sprites/items/ingredients/jalapeno.png",
	"mozzarella": "res://assets/sprites/items/ingredients/mozzarella.png",
	"basil": "res://assets/sprites/items/ingredients/basil.png",
	"anchovy": "res://assets/sprites/items/ingredients/anchovy.png",
	"beef": "res://assets/sprites/items/ingredients/beef.png",
	"corn": "res://assets/sprites/items/ingredients/corn.png",
	"artichoke": "res://assets/sprites/items/ingredients/artichoke.png",
	"rocket": "res://assets/sprites/items/ingredients/rocket.png",
}

# UI toolbar icons — one per build tool
const UI_TOOL_PATHS: Dictionary = {
	"conveyor": "res://assets/sprites/ui/tools/conveyor.png",
	"processor": "res://assets/sprites/ui/tools/processor.png",
	"oven": "res://assets/sprites/ui/tools/oven.png",
	"bot_dock": "res://assets/sprites/ui/tools/bot_dock.png",
	"assembly_table": "res://assets/sprites/ui/tools/assembly_table.png",
	"splitter": "res://assets/sprites/ui/tools/splitter.png",
	"inserter": "res://assets/sprites/ui/tools/inserter.png",
	"priority_lane": "res://assets/sprites/ui/tools/priority_lane.png",
	"delete": "res://assets/sprites/ui/tools/delete.png",
	"source": "res://assets/sprites/ui/tools/source.png",
	"sink": "res://assets/sprites/ui/tools/sink.png",
}

static func get_tile_texture(kind: String) -> Texture2D:
	if _tile_cache.has(kind):
		return _tile_cache[kind]
	var path = TILE_PATHS.get(kind, "")
	if path == "" or not ResourceLoader.exists(path):
		return null
	var tex = load(path)
	_tile_cache[kind] = tex
	return tex

static func get_item_texture(stage: String, ingredient_type: String = "") -> Texture2D:
	# Try per-ingredient sprite first
	if ingredient_type != "":
		var cache_key = ingredient_type
		if _item_cache.has(cache_key):
			return _item_cache[cache_key]
		var ingr_path = INGREDIENT_PATHS.get(ingredient_type, "")
		if ingr_path != "" and ResourceLoader.exists(ingr_path):
			var tex = load(ingr_path)
			_item_cache[cache_key] = tex
			return tex

	# Fall back to stage-based default
	if _item_cache.has(stage):
		return _item_cache[stage]
	var path = STAGE_PATHS.get(stage, "")
	if path == "" or not ResourceLoader.exists(path):
		return null
	var tex = load(path)
	_item_cache[stage] = tex
	return tex

static func get_tool_icon(tool_key: String) -> Texture2D:
	if _ui_cache.has(tool_key):
		return _ui_cache[tool_key]
	var path = UI_TOOL_PATHS.get(tool_key, "")
	if path == "" or not ResourceLoader.exists(path):
		return null
	var tex = load(path)
	_ui_cache[tool_key] = tex
	return tex
