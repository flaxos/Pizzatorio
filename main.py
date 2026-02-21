from __future__ import annotations
import argparse
import json
import math
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from recipe_catalog import load_recipe_catalog

try:
    import pygame  # type: ignore
except Exception:
    pygame = None

GRID_W = 20
GRID_H = 15
CELL = 48
SAVE_FILE = Path("midgame_save.json")
RECIPES_FILE = Path("data/recipes.json")

EMPTY = "empty"
CONVEYOR = "conveyor"
MACHINE = "machine"
PROCESSOR = "processor"
OVEN = "oven"
BOT_DOCK = "bot_dock"
SOURCE = "source"
SINK = "sink"

DIRS = {
    0: (1, 0),
    1: (0, 1),
    2: (-1, 0),
    3: (0, -1),
}

ITEM_STAGE_ORDER = ["raw", "processed", "baked"]
PROCESS_FLOW = {
    PROCESSOR: {"from": "raw", "to": "processed", "research_gain": 0.12},
    OVEN: {"from": "processed", "to": "baked", "research_gain": 0.25},
    BOT_DOCK: {"from": "baked", "to": "baked", "research_gain": 0.06, "delivery_boost": 1.2},
}

RECIPES = load_recipe_catalog(RECIPES_FILE)


@dataclass
class Tile:
    kind: str = EMPTY
    rot: int = 0
    hygiene_penalty: int = 0


@dataclass
class Item:
    x: int
    y: int
    progress: float = 0.0
    stage: str = "raw"
    delivery_boost: float = 0.0


@dataclass
class Delivery:
    mode: str
    remaining: float
    sla: float
    duration: float
    recipe_key: str
    reward: int
    elapsed: float = 0.0


@dataclass
class Order:
    recipe_key: str
    remaining_sla: float
    total_sla: float
    reward: int


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class FactorySim:
    def __init__(self, seed: int = 7):
        self.rng = random.Random(seed)
        self.grid: List[List[Tile]] = [[Tile() for _ in range(GRID_W)] for _ in range(GRID_H)]
        self.items: List[Item] = []
        self.deliveries: List[Delivery] = []
        self.orders: List[Order] = []
        self.time = 0.0
        self.spawn_timer = 0.0
        self.order_spawn_timer = 0.0
        self.hygiene = 100.0
        self.bottleneck = 0.0
        self.expansion_level = 1
        self.expansion_progress = 0.0
        self.research_points = 0.0
        self.tech_tree: Dict[str, bool] = {
            "ovens": False,
            "bots": False,
            "turbo_belts": False,
        }
        self.auto_bot_charge = 0.0
        self.completed = 0
        self.ontime = 0
        self.money = 0
        self.waste = 0
        self.last_hygiene_event = 0.0

        self.place_static_world()

    def place_static_world(self) -> None:
        self.grid[7][1] = Tile(SOURCE, rot=0)
        self.grid[7][18] = Tile(SINK, rot=0)
        for x in range(2, 18):
            self.grid[7][x] = Tile(CONVEYOR, rot=0)
        self.grid[7][7] = Tile(PROCESSOR, rot=0)
        self.grid[7][12] = Tile(OVEN, rot=0)
        self.grid[6][12] = Tile(BOT_DOCK, rot=1)

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
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "FactorySim":
        sim = cls()
        raw_grid = data.get("grid")
        if isinstance(raw_grid, list) and len(raw_grid) == GRID_H and all(isinstance(row, list) and len(row) == GRID_W for row in raw_grid):
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
        sim.time = data.get("time", 0.0)
        sim.spawn_timer = data.get("spawn_timer", 0.0)
        sim.order_spawn_timer = data.get("order_spawn_timer", 0.0)
        sim.hygiene = data.get("hygiene", 100.0)
        sim.bottleneck = data.get("bottleneck", 0.0)
        sim.expansion_level = data.get("expansion_level", 1)
        sim.expansion_progress = data.get("expansion_progress", 0.0)
        sim.research_points = data.get("research_points", 0.0)
        sim.tech_tree = data.get(
            "tech_tree",
            {
                "ovens": False,
                "bots": False,
                "turbo_belts": False,
            },
        )
        sim.auto_bot_charge = data.get("auto_bot_charge", 0.0)
        sim.completed = data.get("completed", 0)
        sim.ontime = data.get("ontime", 0)
        sim.money = data.get("money", 0)
        sim.waste = data.get("waste", 0)
        sim.last_hygiene_event = data.get("last_hygiene_event", 0.0)
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
        return {
            "x": int(item.get("x", 0)),
            "y": int(item.get("y", 0)),
            "progress": float(item.get("progress", 0.0)),
            "stage": str(item.get("stage", "raw")),
            "delivery_boost": float(item.get("delivery_boost", 0.0)),
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

    def save(self, path: Path = SAVE_FILE) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path = SAVE_FILE) -> "FactorySim":
        return cls.from_dict(json.loads(path.read_text()))

    def place_tile(self, x: int, y: int, kind: str, rot: int) -> None:
        if not (0 <= x < GRID_W and 0 <= y < GRID_H):
            return
        if self.grid[y][x].kind in (SOURCE, SINK):
            return
        if kind == EMPTY:
            self.grid[y][x] = Tile()
        else:
            if kind == OVEN and not self.tech_tree.get("ovens", False):
                return
            if kind == BOT_DOCK and not self.tech_tree.get("bots", False):
                return
            self.grid[y][x] = Tile(kind=kind, rot=rot % 4)

    def _process_research(self) -> None:
        unlocks = [
            ("ovens", 12.0),
            ("bots", 28.0),
            ("turbo_belts", 55.0),
        ]
        for tech, cost in unlocks:
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

    def _enqueue_delivery(self, order: Order) -> None:
        mode = self.rng.choice(["drone", "scooter"])
        travel = self.rng.uniform(3.5, 7.5) if mode == "drone" else self.rng.uniform(5.0, 10.0)
        self.deliveries.append(
            Delivery(
                mode=mode,
                remaining=travel,
                elapsed=0.0,
                sla=max(2.5, order.remaining_sla),
                duration=travel,
                recipe_key=order.recipe_key,
                reward=order.reward,
            )
        )

    def tick(self, dt: float) -> None:
        self.time += dt
        self.spawn_timer += dt
        self.order_spawn_timer += dt

        if self.spawn_timer >= 1.8:
            self.spawn_timer = 0.0
            self.items.append(Item(1, 7, 0.0, stage="raw"))

        if self.order_spawn_timer >= 5.5:
            self.order_spawn_timer = 0.0
            self._spawn_order()

        # hygiene events
        if self.time - self.last_hygiene_event > 14 and self.rng.random() < 0.015:
            self.last_hygiene_event = self.time
            self.hygiene = clamp(self.hygiene - self.rng.uniform(8, 20), 0, 100)
        else:
            self.hygiene = clamp(self.hygiene + dt * 0.35, 0, 100)

        blocked = 0
        moved_items: List[Item] = []
        turbo = 0.25 if self.tech_tree.get("turbo_belts", False) else 0.0
        for item in self.items:
            tile = self.grid[item.y][item.x]
            speed = 1.0 + turbo
            if tile.kind in (MACHINE, PROCESSOR):
                speed = 0.5 + (self.hygiene / 220.0)
            elif tile.kind == OVEN:
                speed = 0.35 + (self.hygiene / 280.0)
            item.progress += dt * speed

            if item.progress < 1.0:
                moved_items.append(item)
                continue

            item.progress = 0.0
            nx, ny = item.x, item.y

            if tile.kind in (CONVEYOR, SOURCE, MACHINE, PROCESSOR, OVEN, BOT_DOCK):
                flow = PROCESS_FLOW.get(tile.kind)
                if flow and item.stage == flow["from"]:
                    item.stage = flow["to"]
                    self.research_points += flow["research_gain"]
                    if "delivery_boost" in flow:
                        item.delivery_boost = flow["delivery_boost"]
                nx, ny = self._next_pos(item.x, item.y, tile.rot)
            elif tile.kind == EMPTY:
                blocked += 1

            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                continue

            ntile = self.grid[ny][nx]
            if ntile.kind == SINK and item.stage == "baked":
                if self.orders:
                    order = self.orders.pop(0)
                    self._enqueue_delivery(order)
                    if item.delivery_boost > 0:
                        self.deliveries[-1].remaining = max(1.5, self.deliveries[-1].remaining - item.delivery_boost)
                        self.deliveries[-1].duration = self.deliveries[-1].remaining
                else:
                    self.waste += 1
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

        docks = sum(1 for row in self.grid for tile in row if tile.kind == BOT_DOCK)
        if self.tech_tree.get("bots", False) and docks > 0:
            self.auto_bot_charge += dt * (0.18 * docks)
            while self.auto_bot_charge >= 1.0 and self.deliveries:
                target = max(self.deliveries, key=lambda d: d.remaining)
                target.remaining = max(0.4, target.remaining - 0.8)
                self.auto_bot_charge -= 1.0

        self.expansion_progress += (dt * 0.35) + (self.completed * 0.002)
        needed = 24.0 * self.expansion_level
        if self.expansion_progress >= needed:
            self.expansion_progress -= needed
            self.expansion_level += 1

        # Deliveries & SLA
        next_orders: List[Order] = []
        for order in self.orders:
            order.remaining_sla -= dt
            if order.remaining_sla > 0:
                next_orders.append(order)
        self.orders = next_orders

        next_deliveries: List[Delivery] = []
        for d in self.deliveries:
            d.elapsed += dt
            d.remaining -= dt
            if d.remaining <= 0:
                self.completed += 1
                if d.elapsed <= d.sla:
                    self.ontime += 1
                    self.money += d.reward
                else:
                    self.money += int(d.reward * 0.5)
            else:
                next_deliveries.append(d)
        self.deliveries = next_deliveries

    @property
    def ontime_rate(self) -> float:
        return 100.0 if self.completed == 0 else (self.ontime / self.completed) * 100.0


def run_headless(ticks: int, dt: float, load_save: bool) -> None:
    sim = FactorySim.load() if (load_save and SAVE_FILE.exists()) else FactorySim()

    # Build a mid-game-like path automatically
    for x in range(2, 18):
        sim.place_tile(x, 7, CONVEYOR, 0)
    sim.place_tile(7, 7, PROCESSOR, 0)
    sim.tech_tree["ovens"] = True
    sim.tech_tree["bots"] = True
    sim.place_tile(12, 7, OVEN, 0)
    sim.place_tile(14, 7, BOT_DOCK, 0)

    for _ in range(ticks):
        sim.tick(dt)

    sim.save()
    print(
        f"headless_done t={sim.time:.1f} items={len(sim.items)} "
        f"orders={len(sim.orders)} delivering={len(sim.deliveries)} "
        f"kpi[hyg={sim.hygiene:.1f},btl={sim.bottleneck:.1f},sla={sim.ontime_rate:.1f}]"
        f" progression[xp={sim.research_points:.1f},tier={sim.expansion_level}]"
        f" economy[cash=${sim.money},waste={sim.waste}]"
    )


class GameUI:
    def __init__(self, sim: FactorySim):
        if pygame is None:
            raise RuntimeError("pygame is required for graphical mode")
        pygame.init()
        self.sim = sim
        self.grid_px_w = GRID_W * CELL
        self.grid_px_h = GRID_H * CELL
        self.panel_h = 190

        display = pygame.display.Info()
        self.landscape = display.current_w >= display.current_h
        self.sidebar_w = 340 if self.landscape else 0
        self.window_w = self.grid_px_w + self.sidebar_w
        self.window_h = self.grid_px_h + self.panel_h

        self.screen = pygame.display.set_mode((self.window_w, self.window_h))
        pygame.display.set_caption("Pizzatorio Factory")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22)
        self.small = pygame.font.SysFont("arial", 17)
        self.running = True
        self.selected = CONVEYOR
        self.rotation = 0

        self.main_sections = ["Build", "Orders", "R&D", "Commercials", "Info"]
        self.subsections = {
            "Build": ["Belts", "Machines", "Utilities"],
            "Orders": ["Delivery", "Takeaway", "Eat-in"],
            "R&D": ["Tech tree", "Queued", "Upgrades"],
            "Commercials": ["Campaigns", "Promos", "Franchise"],
            "Info": ["KPIs", "Logs", "Economy"],
        }
        self.active_section = "Build"
        self.active_subsection = self.subsections[self.active_section][0]
        self.order_channel = "delivery"

        self.palette = {
            "bg": (12, 15, 24),
            "panel": (20, 25, 38),
            "panel_border": (46, 56, 80),
            "grid_line": (38, 45, 62),
            "text": (230, 236, 248),
            "muted": (161, 177, 205),
            "accent": (97, 167, 255),
            "chip": (30, 38, 55),
            "chip_active": (59, 93, 156),
        }

    def _set_section(self, section: str) -> None:
        if section not in self.main_sections:
            return
        self.active_section = section
        self.active_subsection = self.subsections[section][0]

    def _cycle_section(self) -> None:
        idx = self.main_sections.index(self.active_section)
        self._set_section(self.main_sections[(idx + 1) % len(self.main_sections)])

    def _set_subsection(self, subsection: str) -> None:
        if subsection in self.subsections.get(self.active_section, []):
            self.active_subsection = subsection
            if self.active_section == "Orders":
                self.order_channel = subsection.lower()

    def _ui_rects(self) -> Dict[str, List[Tuple[pygame.Rect, str]]]:
        top_y = self.grid_px_h + 8
        x = 10
        sections: List[Tuple[pygame.Rect, str]] = []
        for section in self.main_sections:
            rect = pygame.Rect(x, top_y, 112, 30)
            sections.append((rect, section))
            x += 118

        sub_y = top_y + 38
        x = 10
        subs: List[Tuple[pygame.Rect, str]] = []
        for subsection in self.subsections[self.active_section]:
            rect = pygame.Rect(x, sub_y, 146, 28)
            subs.append((rect, subsection))
            x += 152

        return {"sections": sections, "subsections": subs}

    def _toolbar_rects(self) -> List[Tuple[pygame.Rect, str]]:
        y = self.grid_px_h + 78
        labels = ["1 Conveyor", "2 Processor", "3 Oven", "4 Bot Dock", "5 Delete", "R Rotate", "Q/E Rot ±"]
        rects = []
        x = 10
        for label in labels:
            w = max(86, len(label) * 8 + 20)
            rects.append((pygame.Rect(x, y, w, 30), label))
            x += w + 8
        return rects

    def _handle_click(self, mx: int, my: int) -> bool:
        ui_rects = self._ui_rects()
        for rect, section in ui_rects["sections"]:
            if rect.collidepoint(mx, my):
                self._set_section(section)
                return True
        for rect, subsection in ui_rects["subsections"]:
            if rect.collidepoint(mx, my):
                self._set_subsection(subsection)
                return True
        return False

    def handle_input(self) -> None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_1:
                    self.selected = CONVEYOR
                elif ev.key == pygame.K_2:
                    self.selected = PROCESSOR
                elif ev.key == pygame.K_3:
                    self.selected = OVEN
                elif ev.key == pygame.K_4:
                    self.selected = BOT_DOCK
                elif ev.key == pygame.K_5:
                    self.selected = EMPTY
                elif ev.key == pygame.K_r or ev.key == pygame.K_e:
                    self.rotation = (self.rotation + 1) % 4
                elif ev.key == pygame.K_q:
                    self.rotation = (self.rotation - 1) % 4
                elif ev.key == pygame.K_TAB:
                    self._cycle_section()
                elif ev.key == pygame.K_F1:
                    self._set_section("Build")
                elif ev.key == pygame.K_F2:
                    self._set_section("Orders")
                elif ev.key == pygame.K_F3:
                    self._set_section("R&D")
                elif ev.key == pygame.K_F4:
                    self._set_section("Commercials")
                elif ev.key == pygame.K_F5:
                    self._set_section("Info")
                elif ev.key == pygame.K_s:
                    self.sim.save()
                elif ev.key == pygame.K_l and SAVE_FILE.exists():
                    self.sim = FactorySim.load()
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                x, y = pygame.mouse.get_pos()
                if y >= self.grid_px_h and self._handle_click(x, y):
                    continue
                if x < self.grid_px_w and y < self.grid_px_h:
                    gx, gy = x // CELL, y // CELL
                    self.sim.place_tile(gx, gy, self.selected, self.rotation)

    def _tile_base_color(self, kind: str) -> Tuple[int, int, int]:
        colors = {
            EMPTY: (40, 44, 58),
            CONVEYOR: (74, 126, 230),
            MACHINE: (208, 158, 80),
            PROCESSOR: (230, 190, 102),
            OVEN: (232, 102, 61),
            BOT_DOCK: (98, 211, 222),
            SOURCE: (88, 193, 112),
            SINK: (196, 98, 96),
        }
        return colors[kind]

    def _draw_tile_icon(self, tile: Tile, rect: pygame.Rect) -> None:
        cx, cy = rect.center
        icon = (242, 246, 255)
        if tile.kind in (CONVEYOR, SOURCE):
            dx, dy = DIRS[tile.rot]
            tip = (cx + dx * 14, cy + dy * 14)
            side = (dy * 9, -dx * 9)
            base = (cx - dx * 8, cy - dy * 8)
            points = [tip, (base[0] + side[0], base[1] + side[1]), (base[0] - side[0], base[1] - side[1])]
            pygame.draw.polygon(self.screen, icon, points)
        elif tile.kind == PROCESSOR:
            chip = pygame.Rect(0, 0, 19, 19)
            chip.center = (cx, cy)
            pygame.draw.rect(self.screen, icon, chip, width=2, border_radius=4)
            for off in (-7, -3, 1, 5):
                pygame.draw.line(self.screen, icon, (chip.left - 4, cy + off), (chip.left, cy + off), 2)
                pygame.draw.line(self.screen, icon, (chip.right, cy + off), (chip.right + 4, cy + off), 2)
        elif tile.kind == OVEN:
            pygame.draw.circle(self.screen, icon, (cx, cy + 5), 10, width=2)
            flame = [(cx, cy - 8), (cx - 7, cy + 3), (cx, cy + 0), (cx + 7, cy + 3)]
            pygame.draw.polygon(self.screen, icon, flame)
        elif tile.kind == BOT_DOCK:
            pygame.draw.circle(self.screen, icon, (cx, cy - 3), 9, width=2)
            pygame.draw.circle(self.screen, icon, (cx - 3, cy - 4), 1)
            pygame.draw.circle(self.screen, icon, (cx + 3, cy - 4), 1)
            pygame.draw.rect(self.screen, icon, (cx - 10, cy + 8, 20, 3), border_radius=2)
        elif tile.kind == SINK:
            pygame.draw.circle(self.screen, icon, (cx, cy), 11, width=2)
            pygame.draw.circle(self.screen, icon, (cx, cy), 4)

    def _draw_metric_card(self, x: int, y: int, w: int, title: str, value: float, hue: Tuple[int, int, int]) -> None:
        card = pygame.Rect(x, y, w, 54)
        pygame.draw.rect(self.screen, (27, 34, 48), card, border_radius=10)
        pygame.draw.rect(self.screen, (56, 68, 94), card, width=1, border_radius=10)
        self.screen.blit(self.small.render(title, True, self.palette["muted"]), (x + 10, y + 8))
        self.screen.blit(self.font.render(f"{value:5.1f}%", True, self.palette["text"]), (x + 10, y + 23))
        bar_bg = pygame.Rect(x + 96, y + 25, w - 108, 16)
        pygame.draw.rect(self.screen, (43, 49, 63), bar_bg, border_radius=8)
        fill = pygame.Rect(bar_bg.x, bar_bg.y, int(bar_bg.w * clamp(value / 100.0, 0.0, 1.0)), bar_bg.h)
        pygame.draw.rect(self.screen, hue, fill, border_radius=8)

    def _draw_chip(self, rect: pygame.Rect, label: str, active: bool) -> None:
        bg = self.palette["chip_active"] if active else self.palette["chip"]
        pygame.draw.rect(self.screen, bg, rect, border_radius=8)
        pygame.draw.rect(self.screen, self.palette["panel_border"], rect, width=1, border_radius=8)
        self.screen.blit(self.small.render(label, True, self.palette["text"]), (rect.x + 8, rect.y + 6))

    def _draw_sidebar(self) -> None:
        if self.sidebar_w <= 0:
            return
        panel = pygame.Rect(self.grid_px_w, 0, self.sidebar_w, self.window_h)
        pygame.draw.rect(self.screen, (16, 21, 33), panel)
        pygame.draw.line(self.screen, self.palette["panel_border"], (self.grid_px_w, 0), (self.grid_px_w, self.window_h), 2)

        y = 14
        self.screen.blit(self.font.render("Landscape Ops", True, self.palette["text"]), (self.grid_px_w + 14, y))
        y += 34
        rows = [
            f"Menu: {self.active_section}",
            f"Sub-menu: {self.active_subsection}",
            f"Order channel: {self.order_channel}",
            f"Selected tool: {self.selected}",
            f"Rotation: {self.rotation}",
            f"Orders pending: {len(self.sim.orders)}",
            f"Deliveries active: {len(self.sim.deliveries)}",
        ]
        for row in rows:
            self.screen.blit(self.small.render(row, True, self.palette["muted"]), (self.grid_px_w + 14, y))
            y += 25

        card_y = y + 8
        card_w = self.sidebar_w - 28
        self._draw_metric_card(self.grid_px_w + 14, card_y, card_w, "On-time Throughput", self.sim.ontime_rate, (106, 212, 148))
        self._draw_metric_card(self.grid_px_w + 14, card_y + 64, card_w, "Bottleneck", self.sim.bottleneck, (242, 186, 88))
        self._draw_metric_card(self.grid_px_w + 14, card_y + 128, card_w, "Hygiene", self.sim.hygiene, (101, 189, 255))

    def draw_tile(self, x: int, y: int, tile: Tile) -> None:
        rect = pygame.Rect(x * CELL + 1, y * CELL + 1, CELL - 2, CELL - 2)
        base = self._tile_base_color(tile.kind)
        lift = tuple(min(255, c + 25) for c in base)
        pygame.draw.rect(self.screen, base, rect, border_radius=10)
        shine = pygame.Rect(rect.x + 1, rect.y + 1, rect.w - 2, rect.h // 2)
        pygame.draw.rect(self.screen, lift, shine, border_top_left_radius=10, border_top_right_radius=10)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, width=1, border_radius=10)
        if tile.kind != EMPTY:
            self._draw_tile_icon(tile, rect)

    def draw(self) -> None:
        self.screen.fill(self.palette["bg"])
        for y in range(GRID_H):
            for x in range(GRID_W):
                self.draw_tile(x, y, self.sim.grid[y][x])

        for x in range(GRID_W + 1):
            pygame.draw.line(self.screen, self.palette["grid_line"], (x * CELL, 0), (x * CELL, self.grid_px_h), 1)
        for y in range(GRID_H + 1):
            pygame.draw.line(self.screen, self.palette["grid_line"], (0, y * CELL), (self.grid_px_w, y * CELL), 1)

        for item in self.sim.items:
            px = item.x * CELL + CELL // 2
            py = item.y * CELL + CELL // 2
            colors = {
                "raw": (219, 223, 235),
                "processed": (255, 214, 126),
                "baked": (255, 139, 94),
            }
            color = colors.get(item.stage, (255, 255, 255))
            pygame.draw.circle(self.screen, (30, 34, 45), (int(px), int(py)), 10)
            pygame.draw.circle(self.screen, color, (int(px), int(py)), 7)

        panel = pygame.Rect(0, self.grid_px_h, self.grid_px_w, self.panel_h)
        pygame.draw.rect(self.screen, self.palette["panel"], panel)
        pygame.draw.line(self.screen, self.palette["panel_border"], panel.topleft, panel.topright, 2)

        ui_rects = self._ui_rects()
        for rect, section in ui_rects["sections"]:
            self._draw_chip(rect, section, section == self.active_section)
        for rect, subsection in ui_rects["subsections"]:
            self._draw_chip(rect, subsection, subsection == self.active_subsection)

        for rect, label in self._toolbar_rects():
            active = (
                ("Conveyor" in label and self.selected == CONVEYOR)
                or ("Processor" in label and self.selected == PROCESSOR)
                or ("Oven" in label and self.selected == OVEN)
                or ("Bot Dock" in label and self.selected == BOT_DOCK)
                or ("Delete" in label and self.selected == EMPTY)
            )
            self._draw_chip(rect, label, active)

        dtext = (
            f"Tool={self.selected.upper()} Rot={self.rotation} | Menu={self.active_section}/{self.active_subsection} "
            f"| Orders={len(self.sim.orders)} Deliveries={len(self.sim.deliveries)} Cash=${self.sim.money}"
        )
        self.screen.blit(self.small.render(dtext, True, (255, 236, 160)), (10, self.grid_px_h + 150))

        self._draw_sidebar()
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_input()
            self.sim.tick(dt)
            self.draw()
        pygame.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Pizzatorio factory prototype")
    parser.add_argument("--headless", action="store_true", help="run simulation without graphics")
    parser.add_argument("--ticks", type=int, default=600, help="headless ticks to run")
    parser.add_argument("--dt", type=float, default=0.1, help="headless timestep")
    parser.add_argument("--load", action="store_true", help="load midgame save")
    args = parser.parse_args()

    if args.headless:
        run_headless(args.ticks, args.dt, args.load)
        return

    sim = FactorySim.load() if (args.load and SAVE_FILE.exists()) else FactorySim()
    GameUI(sim).run()


if __name__ == "__main__":
    main()
