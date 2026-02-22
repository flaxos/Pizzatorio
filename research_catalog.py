from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

RESEARCH_FILE = Path("data/research.json")
TECH_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class ResearchDefinition:
    key: str
    display_name: str
    branch: str
    cost: float
    prerequisites: Tuple[str, ...] = ()

    def to_runtime_dict(self) -> Dict[str, str | float | list[str]]:
        return {
            "display_name": self.display_name,
            "branch": self.branch,
            "cost": self.cost,
            "prerequisites": list(self.prerequisites),
        }


DEFAULT_RESEARCH: Dict[str, ResearchDefinition] = {
    "ovens": ResearchDefinition("ovens", "Oven Foundations", "cooking", 12.0),
    "bots": ResearchDefinition("bots", "Bot Docks", "automation", 28.0),
    "turbo_oven": ResearchDefinition("turbo_oven", "Turbo Ovens", "cooking", 40.0),
    "hygiene_training": ResearchDefinition("hygiene_training", "Hygiene Training", "automation", 50.0),
    "turbo_belts": ResearchDefinition("turbo_belts", "Turbo Belts", "logistics", 55.0),
    "priority_dispatch": ResearchDefinition("priority_dispatch", "Priority Dispatch", "logistics", 85.0),
    "precision_cooking": ResearchDefinition(
        "precision_cooking", "Precision Cooking", "cooking", 95.0, ("turbo_oven",)
    ),
    "double_spawn": ResearchDefinition("double_spawn", "Double Spawn", "logistics", 140.0),
    "second_location": ResearchDefinition("second_location", "Second Location", "expansion", 180.0),
    "franchise_system": ResearchDefinition("franchise_system", "Franchise System", "expansion", 320.0),
}


def _is_positive_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def _coerce_str_list(value: Any) -> Tuple[str, ...] | None:
    if not isinstance(value, list) or not all(isinstance(i, str) for i in value):
        return None
    return tuple(value)


def _is_valid_tech_id(value: str) -> bool:
    return bool(TECH_ID_RE.fullmatch(value))


def _parse_research_entry(key: str, entry: Dict[str, Any]) -> ResearchDefinition | None:
    if not _is_valid_tech_id(key):
        return None

    display_name = entry.get("display_name")
    branch = entry.get("branch", "general")
    cost = entry.get("cost")
    prerequisites = entry.get("prerequisites", [])

    if not isinstance(display_name, str) or not display_name.strip():
        return None
    if not isinstance(branch, str) or not branch.strip():
        return None
    if not _is_positive_number(cost):
        return None

    parsed_prereqs = _coerce_str_list(prerequisites)
    if parsed_prereqs is None:
        return None
    if any(not _is_valid_tech_id(prereq) for prereq in parsed_prereqs):
        return None
    if len(set(parsed_prereqs)) != len(parsed_prereqs):
        return None
    if key in parsed_prereqs:
        return None

    return ResearchDefinition(
        key=key,
        display_name=display_name.strip(),
        branch=branch.strip().lower(),
        cost=float(cost),
        prerequisites=parsed_prereqs,
    )


def _ordered_runtime_catalog(research_entries: Iterable[ResearchDefinition]) -> Dict[str, Dict[str, str | float | list[str]]]:
    ordered = sorted(research_entries, key=lambda entry: (entry.cost, entry.key))
    return {entry.key: entry.to_runtime_dict() for entry in ordered}


def _has_missing_prerequisites(research_entries: Dict[str, ResearchDefinition]) -> bool:
    available = set(research_entries)
    return any(prereq not in available for entry in research_entries.values() for prereq in entry.prerequisites)


def load_research_catalog(path: Path = RESEARCH_FILE) -> Dict[str, Dict[str, str | float | list[str]]]:
    defaults = _ordered_runtime_catalog(DEFAULT_RESEARCH.values())
    if not path.exists():
        return defaults

    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return defaults

    if not isinstance(raw, dict):
        return defaults

    parsed: Dict[str, ResearchDefinition] = {}
    for key, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        tech = _parse_research_entry(key, entry)
        if tech is None:
            continue
        parsed[key] = tech

    if not parsed or _has_missing_prerequisites(parsed):
        return defaults

    return _ordered_runtime_catalog(parsed.values())
