"""Core dataclasses for the Pizzatorio simulation."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Tile:
    """A single cell on the factory grid."""

    kind: str = "empty"
    rot: int = 0
    hygiene_penalty: int = 0


@dataclass
class Item:
    """An ingredient/food item travelling through the factory.

    ``ingredient_type`` tracks which real ingredient this item represents
    (e.g. ``"flour"``, ``"tomato"``).  An empty string means the type is
    unknown / legacy.  ``stage`` tracks the processing state: raw →
    processed → baked.  ``recipe_key`` is set when the item passes through
    an assembly table, linking it to the specific order it will fulfil.
    """

    x: int
    y: int
    progress: float = 0.0
    stage: str = "raw"
    delivery_boost: float = 0.0
    ingredient_type: str = ""
    recipe_key: str = ""


@dataclass
class Delivery:
    """An in-flight delivery travelling to a customer."""

    mode: str
    remaining: float
    sla: float
    duration: float
    recipe_key: str
    reward: int
    elapsed: float = 0.0
    late_reward_multiplier: float = 1.0


@dataclass
class Order:
    """A customer order waiting to be fulfilled."""

    recipe_key: str
    remaining_sla: float
    total_sla: float
    reward: int
    channel_key: str = "delivery"
