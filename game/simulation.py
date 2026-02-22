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
from recipe_catalog import load_recipe_catalog

RECIPES_FILE = Path("data/recipes.json")
RECIPES = load_recipe_catalog(RECIPES_FILE)


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
        self.last_hygiene_event: float = 0.0
        self.reputation: float = REPUTATION_STARTING

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
            "last_hygiene_event": self.last_hygiene_event,
            "reputation": self.reputation,
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
        sim.last_hygiene_event = float(data.get("last_hygiene_event", 0.0))
        sim.reputation = float(data.get("reputation", REPUTATION_STARTING))
        return sim

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
        return {
            "recipe_key": recipe_key,
            "remaining_sla": float(order.get("remaining_sla", total_sla)),
            "total_sla": total_sla,
            "reward": reward,
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
        self.grid[y][x] = Tile(kind=kind, rot=rot % 4)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_research(self) -> None:
        for tech, cost in TECH_UNLOCK_COSTS.items():
            if not self.tech_tree.get(tech, False) and self.research_points >= cost:
                self.tech_tree[tech] = True

    def _next_pos(self, x: int, y: int, rot: int) -> Tuple[int, int]:
        dx, dy = DIRS[rot % 4]
        return x + dx, y + dy

    def _available_recipes(self) -> List[str]:
        return [
            key
            for key, recipe in RECIPES.items()
            if recipe.get("unlock_tier", 0) <= (self.expansion_level - 1)
        ]

    def _spawn_order(self) -> None:
        available = self._available_recipes()
        if not available:
            return
        weights = [max(0.01, float(RECIPES[key].get("demand_weight", 1.0))) for key in available]
        key = self.rng.choices(available, weights=weights, k=1)[0]
        recipe = RECIPES[key]
        self.orders.append(
            Order(
                recipe_key=key,
                remaining_sla=recipe["sla"],
                total_sla=recipe["sla"],
                reward=recipe["sell_price"],
            )
        )

    def _spawn_item(self) -> None:
        """Spawn a new ingredient item at the source tile with a weighted random type."""
        all_types = list(INGREDIENT_SPAWN_WEIGHTS.keys())
        weights = [INGREDIENT_SPAWN_WEIGHTS[t] for t in all_types]
        ingredient_type = self.rng.choices(all_types, weights=weights, k=1)[0]
        self.items.append(Item(1, 7, 0.0, stage="raw", ingredient_type=ingredient_type))

    def _enqueue_delivery(self, order: Order) -> None:
        mode = self.rng.choice(["drone", "scooter"])
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
        if self.spawn_timer >= effective_spawn_interval:
            self.spawn_timer = 0.0
            self._spawn_item()

        if self.order_spawn_timer >= ORDER_SPAWN_INTERVAL:
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
                    if item.recipe_key:
                        order_idx = next(
                            (i for i, o in enumerate(self.orders) if o.recipe_key == item.recipe_key),
                            0,
                        )
                    else:
                        order_idx = 0
                    order = self.orders.pop(order_idx)
                    self._enqueue_delivery(order)
                    if item.delivery_boost > 0:
                        self.deliveries[-1].remaining = max(1.5, self.deliveries[-1].remaining - item.delivery_boost)
                        self.deliveries[-1].duration = self.deliveries[-1].remaining
                else:
                    self.waste += 1
                    if self.tech_tree.get("precision_cooking", False) and RECIPES:
                        default_recipe = next(iter(RECIPES))
                        refund = int(RECIPES[default_recipe]["sell_price"] * PRECISION_COOKING_WASTE_REFUND)
                        self.money += refund
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
                    self.reputation = clamp(self.reputation + REPUTATION_GAIN_ONTIME, 0.0, 100.0)
                else:
                    self.money += int(d.reward * late_penalty)
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
