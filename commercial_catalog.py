from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable

COMMERCIALS_FILE = Path("data/commercials.json")


@dataclass(frozen=True)
class CommercialDefinition:
    key: str
    display_name: str
    activation_cost: int = 0
    demand_multiplier: float = 1.0
    reward_multiplier: float = 1.0
    required_research: str = ""

    def to_runtime_dict(self) -> Dict[str, str | int | float]:
        return {
            "display_name": self.display_name,
            "activation_cost": self.activation_cost,
            "demand_multiplier": self.demand_multiplier,
            "reward_multiplier": self.reward_multiplier,
            "required_research": self.required_research,
        }


DEFAULT_COMMERCIALS: Dict[str, CommercialDefinition] = {
    "campaigns": CommercialDefinition(
        key="campaigns",
        display_name="Campaigns",
        activation_cost=120,
        demand_multiplier=1.25,
        reward_multiplier=1.0,
    ),
    "promos": CommercialDefinition(
        key="promos",
        display_name="Promos",
        activation_cost=90,
        demand_multiplier=1.0,
        reward_multiplier=1.1,
    ),
    "franchise": CommercialDefinition(
        key="franchise",
        display_name="Franchise",
        activation_cost=180,
        demand_multiplier=1.15,
        reward_multiplier=1.08,
        required_research="franchise_system",
    ),
}


def _is_positive_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def _parse_commercial_entry(key: str, entry: Dict[str, Any]) -> CommercialDefinition | None:
    if not isinstance(key, str) or not key:
        return None

    display_name = entry.get("display_name")
    activation_cost = entry.get("activation_cost", 0)
    demand_multiplier = entry.get("demand_multiplier", 1.0)
    reward_multiplier = entry.get("reward_multiplier", 1.0)
    required_research = entry.get("required_research", "")

    if not isinstance(display_name, str) or not display_name.strip():
        return None
    if not isinstance(activation_cost, int) or activation_cost < 0:
        return None
    if not _is_positive_number(demand_multiplier):
        return None
    if not _is_positive_number(reward_multiplier):
        return None
    if not isinstance(required_research, str):
        return None

    return CommercialDefinition(
        key=key,
        display_name=display_name.strip(),
        activation_cost=activation_cost,
        demand_multiplier=float(demand_multiplier),
        reward_multiplier=float(reward_multiplier),
        required_research=required_research.strip(),
    )


def _ordered_runtime_catalog(commercials: Iterable[CommercialDefinition]) -> Dict[str, Dict[str, str | int | float]]:
    ordered = sorted(commercials, key=lambda commercial: commercial.key)
    return {commercial.key: commercial.to_runtime_dict() for commercial in ordered}


def load_commercial_catalog(path: Path = COMMERCIALS_FILE) -> Dict[str, Dict[str, str | int | float]]:
    if not path.exists():
        return _ordered_runtime_catalog(DEFAULT_COMMERCIALS.values())

    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return _ordered_runtime_catalog(DEFAULT_COMMERCIALS.values())

    if not isinstance(raw, dict):
        return _ordered_runtime_catalog(DEFAULT_COMMERCIALS.values())

    commercials: Dict[str, CommercialDefinition] = {}
    for key, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        commercial = _parse_commercial_entry(key, entry)
        if commercial is None:
            continue
        commercials[key] = commercial

    if not commercials:
        return _ordered_runtime_catalog(DEFAULT_COMMERCIALS.values())

    return _ordered_runtime_catalog(commercials.values())
