from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

ORDER_CHANNELS_FILE = Path("data/order_channels.json")
VALID_DELIVERY_MODES = {"drone", "scooter"}


@dataclass(frozen=True)
class OrderChannelDefinition:
    key: str
    display_name: str
    reward_multiplier: float = 1.0
    sla_multiplier: float = 1.0
    demand_weight: float = 1.0
    delivery_modes: tuple[str, ...] = ("drone", "scooter")
    min_reputation: float = 0.0
    min_recipe_difficulty: int = 1
    max_recipe_difficulty: int = 5
    max_active_orders: int = 6
    late_reward_multiplier: float = 1.0
    missed_order_penalty_multiplier: float = 1.0

    def to_runtime_dict(self) -> Dict[str, str | float | List[str]]:
        return {
            "display_name": self.display_name,
            "reward_multiplier": self.reward_multiplier,
            "sla_multiplier": self.sla_multiplier,
            "demand_weight": self.demand_weight,
            "delivery_modes": list(self.delivery_modes),
            "min_reputation": self.min_reputation,
            "min_recipe_difficulty": self.min_recipe_difficulty,
            "max_recipe_difficulty": self.max_recipe_difficulty,
            "max_active_orders": self.max_active_orders,
            "late_reward_multiplier": self.late_reward_multiplier,
            "missed_order_penalty_multiplier": self.missed_order_penalty_multiplier,
        }


DEFAULT_ORDER_CHANNELS: Dict[str, OrderChannelDefinition] = {
    "delivery": OrderChannelDefinition(
        key="delivery",
        display_name="Delivery",
        reward_multiplier=1.0,
        sla_multiplier=1.0,
        demand_weight=1.0,
        delivery_modes=("drone", "scooter"),
        min_reputation=0.0,
        min_recipe_difficulty=1,
        max_recipe_difficulty=5,
        max_active_orders=8,
        late_reward_multiplier=1.0,
        missed_order_penalty_multiplier=1.0,
    ),
    "takeaway": OrderChannelDefinition(
        key="takeaway",
        display_name="Takeaway",
        reward_multiplier=0.85,
        sla_multiplier=1.35,
        demand_weight=0.75,
        delivery_modes=("scooter",),
        min_reputation=10.0,
        min_recipe_difficulty=1,
        max_recipe_difficulty=3,
        max_active_orders=6,
        late_reward_multiplier=0.9,
        missed_order_penalty_multiplier=0.8,
    ),
    "eat_in": OrderChannelDefinition(
        key="eat_in",
        display_name="Eat-in",
        reward_multiplier=1.15,
        sla_multiplier=1.2,
        demand_weight=0.65,
        delivery_modes=("scooter",),
        min_reputation=25.0,
        min_recipe_difficulty=2,
        max_recipe_difficulty=5,
        max_active_orders=4,
        late_reward_multiplier=0.7,
        missed_order_penalty_multiplier=1.25,
    ),
}


def _is_positive_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def _coerce_delivery_modes(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, list) or not value:
        return None
    if not all(isinstance(mode, str) and mode in VALID_DELIVERY_MODES for mode in value):
        return None
    return tuple(dict.fromkeys(value))


def _parse_channel_entry(key: str, entry: Dict[str, Any]) -> OrderChannelDefinition | None:
    if not isinstance(key, str) or not key:
        return None

    display_name = entry.get("display_name")
    reward_multiplier = entry.get("reward_multiplier", 1.0)
    sla_multiplier = entry.get("sla_multiplier", 1.0)
    demand_weight = entry.get("demand_weight", 1.0)
    delivery_modes = entry.get("delivery_modes", ["drone", "scooter"])
    min_reputation = entry.get("min_reputation", 0.0)
    min_recipe_difficulty = entry.get("min_recipe_difficulty", 1)
    max_recipe_difficulty = entry.get("max_recipe_difficulty", 5)
    max_active_orders = entry.get("max_active_orders", 6)
    late_reward_multiplier = entry.get("late_reward_multiplier", 1.0)
    missed_order_penalty_multiplier = entry.get("missed_order_penalty_multiplier", 1.0)

    if not isinstance(display_name, str) or not display_name.strip():
        return None
    if not _is_positive_number(reward_multiplier):
        return None
    if not _is_positive_number(sla_multiplier):
        return None
    if not _is_positive_number(demand_weight):
        return None
    if isinstance(min_reputation, bool) or not isinstance(min_reputation, (int, float)) or not math.isfinite(min_reputation):
        return None
    if float(min_reputation) < 0.0:
        return None
    if isinstance(min_recipe_difficulty, bool) or not isinstance(min_recipe_difficulty, int):
        return None
    if isinstance(max_recipe_difficulty, bool) or not isinstance(max_recipe_difficulty, int):
        return None
    if isinstance(max_active_orders, bool) or not isinstance(max_active_orders, int):
        return None
    if min_recipe_difficulty < 1 or max_recipe_difficulty < min_recipe_difficulty:
        return None
    if max_active_orders < 1:
        return None
    if not _is_positive_number(late_reward_multiplier):
        return None
    if not _is_positive_number(missed_order_penalty_multiplier):
        return None

    parsed_modes = _coerce_delivery_modes(delivery_modes)
    if parsed_modes is None:
        return None

    return OrderChannelDefinition(
        key=key,
        display_name=display_name.strip(),
        reward_multiplier=float(reward_multiplier),
        sla_multiplier=float(sla_multiplier),
        demand_weight=float(demand_weight),
        delivery_modes=parsed_modes,
        min_reputation=float(min_reputation),
        min_recipe_difficulty=min_recipe_difficulty,
        max_recipe_difficulty=max_recipe_difficulty,
        max_active_orders=max_active_orders,
        late_reward_multiplier=float(late_reward_multiplier),
        missed_order_penalty_multiplier=float(missed_order_penalty_multiplier),
    )


def _ordered_runtime_catalog(channels: Iterable[OrderChannelDefinition]) -> Dict[str, Dict[str, str | float | List[str]]]:
    ordered = sorted(channels, key=lambda channel: channel.key)
    return {channel.key: channel.to_runtime_dict() for channel in ordered}


def load_order_channel_catalog(path: Path = ORDER_CHANNELS_FILE) -> Dict[str, Dict[str, str | float | List[str]]]:
    if not path.exists():
        return _ordered_runtime_catalog(DEFAULT_ORDER_CHANNELS.values())

    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return _ordered_runtime_catalog(DEFAULT_ORDER_CHANNELS.values())

    if not isinstance(raw, dict):
        return _ordered_runtime_catalog(DEFAULT_ORDER_CHANNELS.values())

    channels: Dict[str, OrderChannelDefinition] = {}
    for key, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        channel = _parse_channel_entry(key, entry)
        if channel is None:
            continue
        channels[key] = channel

    if not channels:
        return _ordered_runtime_catalog(DEFAULT_ORDER_CHANNELS.values())

    return _ordered_runtime_catalog(channels.values())
