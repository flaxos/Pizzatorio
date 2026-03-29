extends Node

## SpriteRegistry — Maps tile kinds and item stages to sprite textures.
## Drop-in replacement: swap PNGs in assets/sprites/ and textures update automatically.
## Per-ingredient sprites are looked up first; falls back to stage-based defaults.

static var _tile_cache: Dictionary = {}
static var _item_cache: Dictionary = {}

const TILE_PATHS: Dictionary = {
	"conveyor": "res://assets/sprites/tiles/conveyor.png",
	"processor": "res://assets/sprites/tiles/processor.png",
	"oven": "res://assets/sprites/tiles/oven.png",
	"bot_dock": "res://assets/sprites/tiles/bot_dock.png",
	"assembly_table": "res://assets/sprites/tiles/assembly_table.png",
	"source": "res://assets/sprites/tiles/source.png",
	"sink": "res://assets/sprites/tiles/sink.png",
}

const STAGE_PATHS: Dictionary = {
	"raw": "res://assets/sprites/items/raw/default.png",
	"processed": "res://assets/sprites/items/processed/default.png",
	"baked": "res://assets/sprites/items/baked/default.png",
	"assembled": "res://assets/sprites/items/processed/default.png",
}

# Per-ingredient sprites — looked up before stage fallback
const INGREDIENT_PATHS: Dictionary = {
	"flour": "res://assets/sprites/items/ingredients/flour.png",
	"tomato": "res://assets/sprites/items/ingredients/tomato.png",
	"cheese": "res://assets/sprites/items/ingredients/cheese.png",
	"dough": "res://assets/sprites/items/ingredients/dough.png",
	"sauce": "res://assets/sprites/items/ingredients/sauce.png",
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
