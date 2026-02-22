"""FactorySim — deterministic, headless-compatible factory simulation.

All gameplay constants are imported from ``config``.  The simulation has no
pygame dependency and is safe to import in headless / test contexts.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import (
    ASSEMBLY_TABLE,
    ASSEMBLY_TABLE_SPEED,
    BOT_AUTO_CHARGE_RATE,
    BOT_AUTO_DELIVERY_REDUCTION,
    BOT_DOCK,
    CONVEYOR,
    DIRS,
    DOUBLE_SPAWN_INTERVAL_DIVISOR,
    EMPTY,
    EXPANSION_BASE_NEEDED,
    EXPANSION_DELIVERY_BONUS,
    EXPANSION_PROGRESS_RATE,
    FRANCHISE_EXPANSION_BONUS,
    GRID_H,
    GRID_W,
    HYGIENE_EVENT_CHANCE,
    HYGIENE_EVENT_COOLDOWN,
    HYGIENE_RECOVERY_RATE,
    HYGIENE_TRAINING_RECOVERY_BONUS,
    INGREDIENT_SPAWN_WEIGHTS,
    INGREDIENT_TYPES,
    ITEM_SPAWN_INTERVAL,
    ITEM_STAGE_ORDER,
    LATE_DELIVERY_PENALTY,
    MACHINE,
    MACHINE_BUILD_COSTS,
    OVEN,
    PRECISION_COOKING_WASTE_REFUND,
    PRIORITY_DISPATCH_LATE_MULTIPLIER,
    PROCESS_FLOW,
    PROCESSOR,
    REPUTATION_GAIN_ONTIME,
    REPUTATION_LOSS_LATE,
    REPUTATION_STARTING,
    SAVE_FILE,
    SECOND_LOCATION_REWARD_BONUS,
    SINK,
    SOURCE,
    STARTING_MONEY,
    TECH_UNLOCK_COSTS,
    TURBO_BELT_BONUS,
    TURBO_OVEN_SPEED_BONUS,
    ORDER_SPAWN_INTERVAL,
)
from game.entities import Delivery, Item, Order, Tile
from commercial_catalog import load_commercial_catalog
from order_channel_catalog import load_order_channel_catalog
from recipe_catalog import load_recipe_catalog
from research_catalog import load_research_catalog

RECIPES_FILE = Path("data/recipes.json")
RECIPES = load_recipe_catalog(RECIPES_FILE)
ORDER_CHANNELS_FILE = Path("data/order_channels.json")
ORDER_CHANNELS = load_order_channel_catalog(ORDER_CHANNELS_FILE)
COMMERCIALS_FILE = Path("data/commercials.json")
COMMERCIALS = load_commercial_catalog(COMMERCIALS_FILE)
RESEARCH = load_research_catalog()


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class FactorySim:
    """Tick-based factory simulation.

    All state mutations happen inside :meth:`tick`.  The class is fully
    serialisable to/from a JSON-compatible dict via :meth:`to_dict` and
    :meth:`from_dict`.
    """

    def __init__(self, seed: int = 7) -> None:
        self.rng = random.Random(seed)
        self.grid: List[List[Tile]] = [[Tile() for _ in range(GRID_W)] for _ in range(GRID_H)]
        self.items: List[Item] = []
        self.deliveries: List[Delivery] = []
        self.orders: List[Order] = []
        self.time: float = 0.0
        self.spawn_timer: float = 0.0
        self.order_spawn_timer: float = 0.0
        self.hygiene: float = 100.0
        self.bottleneck: float = 0.0
        self.expansion_level: int = 1
        self.expansion_progress: float = 0.0
        self.research_points: float = 0.0
        self.tech_tree: Dict[str, bool] = {key: False for key in TECH_UNLOCK_COSTS}
        self.auto_bot_charge: float = 0.0
        self.completed: int = 0
        self.ontime: int = 0
        self.money: int = STARTING_MONEY
        self.waste: int = 0
        self.total_revenue: int = 0
        self.total_spend: int = 0
        self.event_log: List[str] = []
        self.last_hygiene_event: float = 0.0
        self.reputation: float = REPUTATION_STARTING
        self.order_channel: str = "delivery" if "delivery" in ORDER_CHANNELS else next(iter(ORDER_CHANNELS))
        self.commercial_strategy: str = next(iter(COMMERCIALS))
        self.research_focus: str = ""
        self._log_event("Factory initialized")

        self.place_static_world()

    # ------------------------------------------------------------------
    # World initialisation
    # ------------------------------------------------------------------

    def place_static_world(self) -> None:
        self.grid[7][1] = Tile(SOURCE, rot=0)
        self.grid[7][18] = Tile(SINK, rot=0)
        for x in range(2, 18):
            self.grid[7][x] = Tile(CONVEYOR, rot=0)
        self.grid[7][7] = Tile(PROCESSOR, rot=0)
        self.grid[7][12] = Tile(OVEN, rot=0)
        self.grid[6][12] = Tile(BOT_DOCK, rot=1)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict:
        return {
            "grid": [[asdict(tile) for tile in row] for row in self.grid],
            "items": [asdict(i) for i in self.items],
            "deliveries": [asdict(d) for d in self.deliveries],
            "orders": [asdict(o) for o in self.orders],
            "time": self.time,
            "spawn_timer": self.spawn_timer,
            "order_spawn_timer": self.order_spawn_timer,
            "hygiene": self.hygiene,
            "bottleneck": self.bottleneck,
            "expansion_level": self.expansion_level,
            "expansion_progress": self.expansion_progress,
            "research_points": self.research_points,
            "tech_tree": self.tech_tree,
            "auto_bot_charge": self.auto_bot_charge,
            "completed": self.completed,
            "ontime": self.ontime,
            "money": self.money,
            "waste": self.waste,
            "total_revenue": self.total_revenue,
            "total_spend": self.total_spend,
            "event_log": self.event_log,
            "last_hygiene_event": self.last_hygiene_event,
            "reputation": self.reputation,
            "order_channel": self.order_channel,
            "commercial_strategy": self.commercial_strategy,
            "research_focus": self.research_focus,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "FactorySim":
        sim = cls()
        raw_grid = data.get("grid")
        if (
            isinstance(raw_grid, list)
            and len(raw_grid) == GRID_H
            and all(isinstance(row, list) and len(row) == GRID_W for row in raw_grid)
        ):
            sim.grid = []
            for row in raw_grid:
                tile_row: List[Tile] = []
                for raw_tile in row:
                    if isinstance(raw_tile, dict):
                        try:
                            tile_row.append(
                                Tile(
                                    kind=str(raw_tile.get("kind", EMPTY)),
                                    rot=int(raw_tile.get("rot", 0)),
                                    hygiene_penalty=int(raw_tile.get("hygiene_penalty", 0)),
                                )
                            )
                        except (TypeError, ValueError):
                            tile_row.append(Tile())
                    else:
                        tile_row.append(Tile())
                sim.grid.append(tile_row)

        sim.items = []
        for raw_item in data.get("items", []):
            if not isinstance(raw_item, dict):
                continue
            sim.items.append(Item(**cls._normalize_item_state(raw_item)))

        sim.deliveries = []
        for raw_delivery in data.get("deliveries", []):
            if not isinstance(raw_delivery, dict):
                continue
            sim.deliveries.append(Delivery(**cls._normalize_delivery_state(raw_delivery)))

        sim.orders = []
        for raw_order in data.get("orders", []):
            if not isinstance(raw_order, dict):
                continue
            sim.orders.append(Order(**cls._normalize_order_state(raw_order)))

        sim.time = float(data.get("time", 0.0))
        sim.spawn_timer = float(data.get("spawn_timer", 0.0))
        sim.order_spawn_timer = float(data.get("order_spawn_timer", 0.0))
        sim.hygiene = float(data.get("hygiene", 100.0))
        sim.bottleneck = float(data.get("bottleneck", 0.0))
        sim.expansion_level = int(data.get("expansion_level", 1))
        sim.expansion_progress = float(data.get("expansion_progress", 0.0))
        sim.research_points = float(data.get("research_points", 0.0))
        saved_tech = data.get("tech_tree", {})
        sim.tech_tree = {key: bool(saved_tech.get(key, False)) for key in TECH_UNLOCK_COSTS}
        sim.auto_bot_charge = float(data.get("auto_bot_charge", 0.0))
        sim.completed = int(data.get("completed", 0))
        sim.ontime = int(data.get("ontime", 0))
        sim.money = int(data.get("money", STARTING_MONEY))
        sim.waste = int(data.get("waste", 0))
        sim.total_revenue = int(data.get("total_revenue", 0))
        sim.total_spend = int(data.get("total_spend", 0))
        raw_events = data.get("event_log", [])
        sim.event_log = [str(event) for event in raw_events if isinstance(event, str)][-12:]
        sim.last_hygiene_event = float(data.get("last_hygiene_event", 0.0))
        sim.reputation = float(data.get("reputation", REPUTATION_STARTING))
        sim.set_order_channel(str(data.get("order_channel", "delivery")))
        sim.set_commercial_strategy(str(data.get("commercial_strategy", sim.commercial_strategy)), charge=False)
        saved_focus = str(data.get("research_focus", ""))
        if saved_focus and saved_focus in TECH_UNLOCK_COSTS and not sim.tech_tree.get(saved_focus, False):
            if sim._research_prerequisites_met(saved_focus):
                sim.research_focus = saved_focus
        return sim

    def _log_event(self, message: str) -> None:
        self.event_log.append(message)
        self.event_log = self.event_log[-12:]

    def order_channel_is_unlocked(self, channel: str) -> bool:
        if channel not in ORDER_CHANNELS:
            return False
        return self.reputation >= self.order_channel_min_reputation(channel)

    def order_channel_min_reputation(self, channel: str) -> float:
        if channel not in ORDER_CHANNELS:
            return 0.0
        channel_cfg = ORDER_CHANNELS[channel]
        return max(0.0, float(channel_cfg.get("min_reputation", 0.0)))

    def unlocked_order_channels(self) -> List[str]:
        return [channel for channel in ORDER_CHANNELS if self.order_channel_is_unlocked(channel)]

    def set_order_channel(self, channel: str) -> bool:
        if channel not in ORDER_CHANNELS:
            return False
        min_reputation = self.order_channel_min_reputation(channel)
        if not self.order_channel_is_unlocked(channel):
            self._log_event(f"Order channel {channel} locked (need rep {min_reputation:.0f})")
            return False
        if channel != self.order_channel:
            self._log_event(f"Order channel switched to {channel}")
        self.order_channel = channel
        return True

    def set_commercial_strategy(self, strategy: str, *, charge: bool = True) -> bool:
        if strategy not in COMMERCIALS:
            return False
        if strategy == self.commercial_strategy:
            return True
        activation_cost = int(COMMERCIALS[strategy].get("activation_cost", 0))
        if charge and self.money < activation_cost:
            self._log_event(f"Commercial {strategy} failed (need ${activation_cost})")
            return False
        if charge:
            self.money -= activation_cost
            self.total_spend += activation_cost
            self._log_event(f"Commercial {strategy} activated (-${activation_cost})")
        self.commercial_strategy = strategy
        return True

    def set_research_focus(self, tech: str) -> bool:
        if not tech:
            self.research_focus = ""
            self._log_event("Research focus cleared")
            return True
        if tech not in TECH_UNLOCK_COSTS or self.tech_tree.get(tech, False):
            return False
        if not self._research_prerequisites_met(tech):
            return False
        self.research_focus = tech
        self._log_event(f"Research focus set: {tech}")
        return True

    def available_research_targets(self) -> List[str]:
        return [
            tech
            for tech in TECH_UNLOCK_COSTS
            if not self.tech_tree.get(tech, False) and self._research_prerequisites_met(tech)
        ]

    def cycle_research_focus(self) -> str:
        available = self.available_research_targets()
        if not available:
            self.research_focus = ""
            return ""
        if self.research_focus not in available:
            self.research_focus = available[0]
            return self.research_focus
        idx = available.index(self.research_focus)
        self.research_focus = available[(idx + 1) % len(available)]
        return self.research_focus

    def _research_prerequisites_met(self, tech: str) -> bool:
        prerequisites = RESEARCH.get(tech, {}).get("prerequisites", [])
        return all(self.tech_tree.get(str(prereq), False) for prereq in prerequisites)

    def try_unlock_research_focus(self) -> bool:
        if self.research_focus and not self.tech_tree.get(self.research_focus, False):
            if not self._research_prerequisites_met(self.research_focus):
                return False
            focus_cost = TECH_UNLOCK_COSTS.get(self.research_focus, float("inf"))
            if self.research_points >= focus_cost:
                self.tech_tree[self.research_focus] = True
                self._log_event(f"Research unlocked: {self.research_focus}")
                self.research_focus = ""
                return True
        return False

    @staticmethod
    def _normalize_item_state(raw_item: Dict) -> Dict:
        item = dict(raw_item)
        if "stage" not in item and "cooked" in item:
            item["stage"] = "baked" if item.get("cooked") else "raw"
        legacy_stage = item.get("stage", "raw")
        if isinstance(legacy_stage, int):
            idx = int(clamp(float(legacy_stage), 0, len(ITEM_STAGE_ORDER) - 1))
            item["stage"] = ITEM_STAGE_ORDER[idx]
        ingredient_type = item.get("ingredient_type", "")
        if not isinstance(ingredient_type, str):
            ingredient_type = ""
        return {
            "x": int(item.get("x", 0)),
            "y": int(item.get("y", 0)),
            "progress": float(item.get("progress", 0.0)),
            "stage": str(item.get("stage", "raw")),
            "delivery_boost": float(item.get("delivery_boost", 0.0)),
            "ingredient_type": ingredient_type,
            "recipe_key": str(item.get("recipe_key", "")),
        }

    @staticmethod
    def _normalize_delivery_state(raw_delivery: Dict) -> Dict:
        delivery = dict(raw_delivery)
        default_recipe = next(iter(RECIPES))
        recipe_key = str(delivery.get("recipe_key", default_recipe))
        if recipe_key not in RECIPES:
            recipe_key = default_recipe
        fallback_remaining = float(delivery.get("remaining", 0.0))
        return {
            "mode": str(delivery.get("mode", "drone")),
            "remaining": fallback_remaining,
            "elapsed": float(delivery.get("elapsed", 0.0)),
            "sla": float(delivery.get("sla", RECIPES[recipe_key]["sla"])),
            "duration": float(delivery.get("duration", fallback_remaining)),
            "recipe_key": recipe_key,
            "reward": int(delivery.get("reward", RECIPES[recipe_key]["sell_price"])),
        }

    @staticmethod
    def _normalize_order_state(raw_order: Dict) -> Dict:
        order = dict(raw_order)
        default_recipe = next(iter(RECIPES))
        recipe_key = str(order.get("recipe_key", default_recipe))
        if recipe_key not in RECIPES:
            recipe_key = default_recipe
        reward = int(order.get("reward", RECIPES[recipe_key]["sell_price"]))
        total_sla = float(order.get("total_sla", RECIPES[recipe_key]["sla"]))
        channel_key = str(order.get("channel_key", "delivery"))
        if channel_key not in ORDER_CHANNELS:
            channel_key = "delivery" if "delivery" in ORDER_CHANNELS else next(iter(ORDER_CHANNELS))
        return {
            "recipe_key": recipe_key,
            "remaining_sla": float(order.get("remaining_sla", total_sla)),
            "total_sla": total_sla,
            "reward": reward,
            "channel_key": channel_key,
        }

    # ------------------------------------------------------------------
    # Save / Load helpers
    # ------------------------------------------------------------------

    def save(self, path: Path = SAVE_FILE) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path = SAVE_FILE) -> "FactorySim":
        return cls.from_dict(json.loads(path.read_text()))

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def place_tile(self, x: int, y: int, kind: str, rot: int) -> None:
        if not (0 <= x < GRID_W and 0 <= y < GRID_H):
            return
        if self.grid[y][x].kind in (SOURCE, SINK):
            return
        if kind == EMPTY:
            self.grid[y][x] = Tile()
            return
        if kind == OVEN and not self.tech_tree.get("ovens", False):
            return
        if kind == BOT_DOCK and not self.tech_tree.get("bots", False):
            return
        # Only charge for building on empty ground; replacing an existing tile is free
        if self.grid[y][x].kind == EMPTY:
            cost = MACHINE_BUILD_COSTS.get(kind, 0)
            if self.money < cost:
                return
            self.money -= cost
            self.total_spend += cost
        self.grid[y][x] = Tile(kind=kind, rot=rot % 4)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_research(self) -> None:
        if self.try_unlock_research_focus():
            return

        tech_state_at_tick_start = dict(self.tech_tree)
        for tech, cost in TECH_UNLOCK_COSTS.items():
            if tech_state_at_tick_start.get(tech, False):
                continue
            prerequisites = RESEARCH.get(tech, {}).get("prerequisites", [])
            if not all(tech_state_at_tick_start.get(str(prereq), False) for prereq in prerequisites):
                continue
            if self.research_points >= cost:
                self.tech_tree[tech] = True
                self._log_event(f"Research auto-unlocked: {tech}")

    def _next_pos(self, x: int, y: int, rot: int) -> Tuple[int, int]:
        dx, dy = DIRS[rot % 4]
        return x + dx, y + dy

    def _available_recipes(self, *, channel_key: str | None = None) -> List[str]:
        available = [
            key
            for key, recipe in RECIPES.items()
            if recipe.get("unlock_tier", 0) <= (self.expansion_level - 1)
        ]
        if not channel_key:
            return available

        channel_cfg = ORDER_CHANNELS.get(channel_key, {})
        min_difficulty = int(channel_cfg.get("min_recipe_difficulty", 1))
        max_difficulty = int(channel_cfg.get("max_recipe_difficulty", 5))
        filtered = [
            key
            for key in available
            if min_difficulty <= int(RECIPES[key].get("difficulty", 1)) <= max_difficulty
        ]
        return filtered if filtered else available

    def _spawn_order(self) -> None:
        available = self._available_recipes(channel_key=self.order_channel)
        if not available:
            return
        channel_cfg = ORDER_CHANNELS.get(self.order_channel, {})
        commercial_cfg = COMMERCIALS.get(self.commercial_strategy, {})
        demand_multiplier = max(0.1, float(commercial_cfg.get("demand_multiplier", 1.0)))
        reward_bonus = max(0.1, float(commercial_cfg.get("reward_multiplier", 1.0)))
        channel_demand_weight = max(0.01, float(channel_cfg.get("demand_weight", 1.0)))
        weights = [
            max(0.01, float(RECIPES[key].get("demand_weight", 1.0)) * channel_demand_weight * demand_multiplier)
            for key in available
        ]
        key = self.rng.choices(available, weights=weights, k=1)[0]
        recipe = RECIPES[key]
        sla_multiplier = max(0.1, float(channel_cfg.get("sla_multiplier", 1.0)))
        reward_multiplier = max(0.1, float(channel_cfg.get("reward_multiplier", 1.0)))
        order_sla = float(recipe["sla"]) * sla_multiplier
        order_reward = max(1, int(round(float(recipe["sell_price"]) * reward_multiplier * reward_bonus)))
        self.orders.append(
            Order(
                recipe_key=key,
                remaining_sla=order_sla,
                total_sla=order_sla,
                reward=order_reward,
                channel_key=self.order_channel,
            )
        )

    def _spawn_item(self) -> None:
        """Spawn a new ingredient item at the source tile with a weighted random type."""
        all_types = list(INGREDIENT_SPAWN_WEIGHTS.keys())
        weights = [INGREDIENT_SPAWN_WEIGHTS[t] for t in all_types]
        ingredient_type = self.rng.choices(all_types, weights=weights, k=1)[0]
        self.items.append(Item(1, 7, 0.0, stage="raw", ingredient_type=ingredient_type))

    def _enqueue_delivery(self, order: Order) -> None:
        if order.channel_key == "eat_in":
            self.completed += 1
            self.ontime += 1
            self.money += order.reward
            self.total_revenue += order.reward
            self.reputation = clamp(self.reputation + REPUTATION_GAIN_ONTIME, 0.0, 100.0)
            return

        channel_cfg = ORDER_CHANNELS.get(order.channel_key, ORDER_CHANNELS.get(self.order_channel, {}))
        modes = channel_cfg.get("delivery_modes", ["drone", "scooter"])
        mode = self.rng.choice([str(m) for m in modes])
        travel = self.rng.uniform(3.5, 7.5) if mode == "drone" else self.rng.uniform(5.0, 10.0)
        reward = order.reward
        if self.tech_tree.get("second_location", False):
            reward = int(reward * (1.0 + SECOND_LOCATION_REWARD_BONUS))
        self.deliveries.append(
            Delivery(
                mode=mode,
                remaining=travel,
                elapsed=0.0,
                sla=max(2.5, order.remaining_sla),
                duration=travel,
                recipe_key=order.recipe_key,
                reward=reward,
            )
        )

    def _resolve_order_for_item(self, item: Item) -> Order | None:
        if not self.orders:
            return None

        if item.recipe_key:
            for idx, order in enumerate(self.orders):
                if order.recipe_key == item.recipe_key:
                    return self.orders.pop(idx)
            return None

        ordered_recipe_keys = {order.recipe_key for order in self.orders}
        if len(ordered_recipe_keys) == 1:
            return self.orders.pop(0)
        return None

    # ------------------------------------------------------------------
    # Main tick
    # ------------------------------------------------------------------

    def tick(self, dt: float) -> None:
        self.time += dt
        self.spawn_timer += dt
        self.order_spawn_timer += dt

        effective_spawn_interval = (
            ITEM_SPAWN_INTERVAL / DOUBLE_SPAWN_INTERVAL_DIVISOR
            if self.tech_tree.get("double_spawn", False)
            else ITEM_SPAWN_INTERVAL
        )
        commercial_cfg = COMMERCIALS.get(self.commercial_strategy, {})
        demand_multiplier = max(0.1, float(commercial_cfg.get("demand_multiplier", 1.0)))
        effective_order_spawn_interval = ORDER_SPAWN_INTERVAL / demand_multiplier
        if self.spawn_timer >= effective_spawn_interval:
            self.spawn_timer = 0.0
            self._spawn_item()

        if self.order_spawn_timer >= effective_order_spawn_interval:
            self.order_spawn_timer = 0.0
            self._spawn_order()

        # Hygiene fluctuation
        hygiene_recovery = HYGIENE_RECOVERY_RATE + (
            HYGIENE_TRAINING_RECOVERY_BONUS if self.tech_tree.get("hygiene_training", False) else 0.0
        )
        if self.time - self.last_hygiene_event > HYGIENE_EVENT_COOLDOWN and self.rng.random() < HYGIENE_EVENT_CHANCE:
            self.last_hygiene_event = self.time
            self.hygiene = clamp(self.hygiene - self.rng.uniform(8, 20), 0, 100)
        else:
            self.hygiene = clamp(self.hygiene + dt * hygiene_recovery, 0, 100)

        blocked = 0
        moved_items: List[Item] = []
        turbo = TURBO_BELT_BONUS if self.tech_tree.get("turbo_belts", False) else 0.0

        for item in self.items:
            tile = self.grid[item.y][item.x]
            speed = 1.0 + turbo
            if tile.kind in (MACHINE, PROCESSOR):
                speed = 0.5 + (self.hygiene / 220.0)
            elif tile.kind == OVEN:
                oven_bonus = TURBO_OVEN_SPEED_BONUS if self.tech_tree.get("turbo_oven", False) else 0.0
                speed = 0.35 + oven_bonus + (self.hygiene / 280.0)
            elif tile.kind == ASSEMBLY_TABLE:
                speed = ASSEMBLY_TABLE_SPEED
            item.progress += dt * speed

            if item.progress < 1.0:
                moved_items.append(item)
                continue

            item.progress = 0.0
            nx, ny = item.x, item.y

            if tile.kind in (CONVEYOR, SOURCE, MACHINE, PROCESSOR, OVEN, BOT_DOCK, ASSEMBLY_TABLE):
                flow = PROCESS_FLOW.get(tile.kind)
                if flow and item.stage == flow["from"]:
                    item.stage = flow["to"]
                    self.research_points += flow["research_gain"]
                    if "delivery_boost" in flow:
                        item.delivery_boost = flow["delivery_boost"]
                if tile.kind == ASSEMBLY_TABLE and self.orders and not item.recipe_key:
                    item.recipe_key = self.orders[0].recipe_key
                nx, ny = self._next_pos(item.x, item.y, tile.rot)
            elif tile.kind == EMPTY:
                blocked += 1

            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                continue

            ntile = self.grid[ny][nx]
            if ntile.kind == SINK and item.stage == "baked":
                if self.orders:
                    order = self._resolve_order_for_item(item)
                    if order is not None:
                        self._enqueue_delivery(order)
                        if item.delivery_boost > 0 and self.deliveries:
                            self.deliveries[-1].remaining = max(1.5, self.deliveries[-1].remaining - item.delivery_boost)
                            self.deliveries[-1].duration = self.deliveries[-1].remaining
                    else:
                        self.waste += 1
                        self._log_event("Order rejected: baked item recipe mismatch")
                else:
                    self.waste += 1
                    if self.tech_tree.get("precision_cooking", False) and RECIPES:
                        default_recipe = next(iter(RECIPES))
                        refund = int(RECIPES[default_recipe]["sell_price"] * PRECISION_COOKING_WASTE_REFUND)
                        self.money += refund
                        self.total_revenue += refund
                continue

            if ntile.kind == EMPTY:
                blocked += 1
                moved_items.append(item)
                continue

            if any(o.x == nx and o.y == ny for o in moved_items):
                blocked += 1
                moved_items.append(item)
                continue

            item.x, item.y = nx, ny
            moved_items.append(item)

        self.items = moved_items
        self.bottleneck = clamp((blocked / max(1, len(self.items))) * 100.0, 0, 100)
        self._process_research()

        # Auto-bot delivery acceleration
        docks = sum(1 for row in self.grid for tile in row if tile.kind == BOT_DOCK)
        if self.tech_tree.get("bots", False) and docks > 0:
            self.auto_bot_charge += dt * (BOT_AUTO_CHARGE_RATE * docks)
            while self.auto_bot_charge >= 1.0 and self.deliveries:
                target = max(self.deliveries, key=lambda d: d.remaining)
                target.remaining = max(0.4, target.remaining - BOT_AUTO_DELIVERY_REDUCTION)
                self.auto_bot_charge -= 1.0

        # Expansion tier progression
        expansion_delivery_mult = FRANCHISE_EXPANSION_BONUS if self.tech_tree.get("franchise_system", False) else 1.0
        self.expansion_progress += (dt * EXPANSION_PROGRESS_RATE) + (self.completed * EXPANSION_DELIVERY_BONUS * expansion_delivery_mult)
        needed = EXPANSION_BASE_NEEDED * self.expansion_level
        if self.expansion_progress >= needed:
            self.expansion_progress -= needed
            self.expansion_level += 1

        # Order SLA countdown
        next_orders: List[Order] = []
        for order in self.orders:
            order.remaining_sla -= dt
            if order.remaining_sla > 0:
                next_orders.append(order)
        self.orders = next_orders

        # Delivery completion
        late_penalty = (
            PRIORITY_DISPATCH_LATE_MULTIPLIER
            if self.tech_tree.get("priority_dispatch", False)
            else LATE_DELIVERY_PENALTY
        )
        next_deliveries: List[Delivery] = []
        for d in self.deliveries:
            d.elapsed += dt
            d.remaining -= dt
            if d.remaining <= 0:
                self.completed += 1
                if d.elapsed <= d.sla:
                    self.ontime += 1
                    self.money += d.reward
                    self.total_revenue += d.reward
                    self.reputation = clamp(self.reputation + REPUTATION_GAIN_ONTIME, 0.0, 100.0)
                else:
                    late_reward = int(d.reward * late_penalty)
                    self.money += late_reward
                    self.total_revenue += late_reward
                    self.reputation = clamp(self.reputation - REPUTATION_LOSS_LATE, 0.0, 100.0)
            else:
                next_deliveries.append(d)
        self.deliveries = next_deliveries

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def ontime_rate(self) -> float:
        return 100.0 if self.completed == 0 else (self.ontime / self.completed) * 100.0
