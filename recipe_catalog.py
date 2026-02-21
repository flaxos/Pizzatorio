from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

RECIPES_FILE = Path("data/recipes.json")
ITEM_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
MAX_TOPPINGS = 5


@dataclass(frozen=True)
class RecipeDefinition:
    key: str
    display_name: str
    sell_price: int
    sla: float
    unlock_tier: int
    cook_time: float = 8.0
    cook_temp: str = "medium"
    difficulty: int = 1
    base: str = "rolled_pizza_base"
    sauce: str = "tomato_sauce"
    cheese: str = "shredded_cheese"
    toppings: tuple[str, ...] = ()
    post_oven: tuple[str, ...] = ()

    def to_runtime_dict(self) -> Dict[str, str | int | float | List[str]]:
        return {
            "display_name": self.display_name,
            "sell_price": self.sell_price,
            "sla": self.sla,
            "unlock_tier": self.unlock_tier,
            "cook_time": self.cook_time,
            "cook_temp": self.cook_temp,
            "difficulty": self.difficulty,
            "base": self.base,
            "sauce": self.sauce,
            "cheese": self.cheese,
            "toppings": list(self.toppings),
            "post_oven": list(self.post_oven),
        }


DEFAULT_RECIPE_DEFINITIONS: Dict[str, RecipeDefinition] = {
    "margherita": RecipeDefinition(
        key="margherita",
        display_name="Margherita",
        sell_price=12,
        sla=11.0,
        unlock_tier=0,
        cook_time=8.0,
        cook_temp="medium",
        difficulty=1,
        cheese="sliced_mozzarella",
        toppings=("fresh_basil",),
    ),
    "pepperoni": RecipeDefinition(
        key="pepperoni",
        display_name="Pepperoni",
        sell_price=15,
        sla=10.0,
        unlock_tier=1,
        cook_time=7.5,
        cook_temp="high",
        difficulty=2,
        toppings=("sliced_pepperoni",),
    ),
    "veggie": RecipeDefinition(
        key="veggie",
        display_name="Veggie Deluxe",
        sell_price=17,
        sla=9.5,
        unlock_tier=2,
        cook_time=8.2,
        cook_temp="medium",
        difficulty=2,
        toppings=("sliced_pepper", "sliced_mushroom", "diced_onion"),
    ),
}


def _coerce_str_list(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, list) or not all(isinstance(i, str) for i in value):
        return None
    return tuple(value)


def _is_valid_item_id(value: str) -> bool:
    return bool(ITEM_ID_RE.fullmatch(value))


def _coerce_int(value: Any, *, minimum: int | None = None) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        result = value
    elif isinstance(value, float) and value.is_integer():
        result = int(value)
    else:
        return None

    if minimum is not None and result < minimum:
        return None
    return result


def _is_positive_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float)) and value > 0


def _parse_recipe_entry(key: str, entry: Dict[str, Any]) -> RecipeDefinition | None:
    if not _is_valid_item_id(key):
        return None

    display_name = entry.get("display_name")
    sell_price = _coerce_int(entry.get("sell_price"), minimum=1)
    sla = entry.get("sla")
    unlock_tier = _coerce_int(entry.get("unlock_tier", 0), minimum=0)
    cook_time = entry.get("cook_time", 8.0)
    cook_temp = entry.get("cook_temp", "medium")
    difficulty = _coerce_int(entry.get("difficulty", 1), minimum=1)

    if not isinstance(display_name, str) or not display_name.strip():
        return None
    if sell_price is None:
        return None
    if not _is_positive_number(sla):
        return None
    if unlock_tier is None:
        return None
    if not _is_positive_number(cook_time):
        return None
    if not isinstance(cook_temp, str):
        return None
    cook_temp = cook_temp.strip().lower()
    if not cook_temp:
        return None
    if cook_temp not in {"low", "medium", "high"}:
        return None
    if difficulty is None:
        return None

    base = entry.get("base", "rolled_pizza_base")
    sauce = entry.get("sauce", "tomato_sauce")
    cheese = entry.get("cheese", "shredded_cheese")
    toppings = entry.get("toppings", [])
    post_oven = entry.get("post_oven", [])

    if not isinstance(base, str) or not isinstance(sauce, str) or not isinstance(cheese, str):
        return None
    if not _is_valid_item_id(base) or not _is_valid_item_id(sauce) or not _is_valid_item_id(cheese):
        return None

    parsed_toppings = _coerce_str_list(toppings)
    parsed_post_oven = _coerce_str_list(post_oven)
    if parsed_toppings is None or parsed_post_oven is None:
        return None
    if not parsed_toppings or len(parsed_toppings) > MAX_TOPPINGS:
        return None
    if not all(_is_valid_item_id(item) for item in (*parsed_toppings, *parsed_post_oven)):
        return None
    if len(set(parsed_toppings)) != len(parsed_toppings):
        return None
    if set(parsed_toppings).intersection(parsed_post_oven):
        return None

    return RecipeDefinition(
        key=key,
        display_name=display_name,
        sell_price=sell_price,
        sla=float(sla),
        unlock_tier=unlock_tier,
        cook_time=float(cook_time),
        cook_temp=cook_temp,
        difficulty=difficulty,
        base=base,
        sauce=sauce,
        cheese=cheese,
        toppings=parsed_toppings,
        post_oven=parsed_post_oven,
    )


def _ordered_runtime_catalog(recipes: Iterable[RecipeDefinition]) -> Dict[str, Dict[str, str | int | float | List[str]]]:
    ordered = sorted(recipes, key=lambda recipe: (recipe.unlock_tier, recipe.key))
    return {recipe.key: recipe.to_runtime_dict() for recipe in ordered}


def load_recipe_catalog(path: Path = RECIPES_FILE) -> Dict[str, Dict[str, str | int | float | List[str]]]:
    if not path.exists():
        return _ordered_runtime_catalog(DEFAULT_RECIPE_DEFINITIONS.values())

    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return _ordered_runtime_catalog(DEFAULT_RECIPE_DEFINITIONS.values())

    if not isinstance(raw, dict):
        return _ordered_runtime_catalog(DEFAULT_RECIPE_DEFINITIONS.values())

    recipes: Dict[str, RecipeDefinition] = {}
    for key, entry in raw.items():
        if not isinstance(key, str) or not isinstance(entry, dict):
            continue
        recipe = _parse_recipe_entry(key, entry)
        if recipe is None:
            continue
        recipes[key] = recipe

    if not recipes:
        return _ordered_runtime_catalog(DEFAULT_RECIPE_DEFINITIONS.values())

    return _ordered_runtime_catalog(recipes.values())
