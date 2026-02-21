import argparse
import json
import math
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import pygame  # type: ignore
except Exception:
    pygame = None

GRID_W = 20
GRID_H = 15
CELL = 36
SAVE_FILE = Path("midgame_save.json")

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
    stage: int = 0
    delivery_boost: float = 0.0


@dataclass
class Delivery:
    mode: str
    remaining: float
    sla: float
    duration: float


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class FactorySim:
    def __init__(self, seed: int = 7):
        self.rng = random.Random(seed)
        self.grid: List[List[Tile]] = [[Tile() for _ in range(GRID_W)] for _ in range(GRID_H)]
        self.items: List[Item] = []
        self.deliveries: List[Delivery] = []
        self.time = 0.0
        self.spawn_timer = 0.0
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
            "time": self.time,
            "spawn_timer": self.spawn_timer,
            "hygiene": self.hygiene,
            "bottleneck": self.bottleneck,
            "expansion_level": self.expansion_level,
            "expansion_progress": self.expansion_progress,
            "research_points": self.research_points,
            "tech_tree": self.tech_tree,
            "auto_bot_charge": self.auto_bot_charge,
            "completed": self.completed,
            "ontime": self.ontime,
            "last_hygiene_event": self.last_hygiene_event,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "FactorySim":
        sim = cls()
        sim.grid = [[Tile(**tile) for tile in row] for row in data["grid"]]
        sim.items = [Item(**i) for i in data.get("items", [])]
        sim.deliveries = [Delivery(**d) for d in data.get("deliveries", [])]
        sim.time = data.get("time", 0.0)
        sim.spawn_timer = data.get("spawn_timer", 0.0)
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
        sim.last_hygiene_event = data.get("last_hygiene_event", 0.0)
        return sim

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

    def _enqueue_delivery(self) -> None:
        mode = self.rng.choice(["drone", "scooter"])
        travel = self.rng.uniform(3.5, 7.5) if mode == "drone" else self.rng.uniform(5.0, 10.0)
        sla = 8.0 if mode == "drone" else 11.0
        self.deliveries.append(Delivery(mode=mode, remaining=travel, sla=sla, duration=travel))

    def tick(self, dt: float) -> None:
        self.time += dt
        self.spawn_timer += dt

        if self.spawn_timer >= 1.8:
            self.spawn_timer = 0.0
            self.items.append(Item(1, 7, 0.0, stage=0))

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
                if tile.kind in (MACHINE, PROCESSOR) and item.stage == 0:
                    item.stage = 1
                    self.research_points += 0.12
                elif tile.kind == OVEN and item.stage == 1:
                    item.stage = 2
                    self.research_points += 0.25
                elif tile.kind == BOT_DOCK and item.stage >= 2:
                    item.delivery_boost = 1.2
                    self.research_points += 0.06
                nx, ny = self._next_pos(item.x, item.y, tile.rot)
            elif tile.kind == EMPTY:
                blocked += 1

            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                continue

            ntile = self.grid[ny][nx]
            if ntile.kind == SINK and item.stage >= 2:
                self._enqueue_delivery()
                if item.delivery_boost > 0:
                    self.deliveries[-1].remaining = max(1.5, self.deliveries[-1].remaining - item.delivery_boost)
                    self.deliveries[-1].duration = self.deliveries[-1].remaining
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
        next_deliveries: List[Delivery] = []
        for d in self.deliveries:
            d.remaining -= dt
            if d.remaining <= 0:
                self.completed += 1
                if d.duration <= d.sla:
                    self.ontime += 1
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
        f"delivering={len(sim.deliveries)} kpi[hyg={sim.hygiene:.1f},btl={sim.bottleneck:.1f},sla={sim.ontime_rate:.1f}]"
        f" progression[xp={sim.research_points:.1f},tier={sim.expansion_level}]"
    )


class GameUI:
    def __init__(self, sim: FactorySim):
        if pygame is None:
            raise RuntimeError("pygame is required for graphical mode")
        pygame.init()
        self.sim = sim
        self.screen = pygame.display.set_mode((GRID_W * CELL, GRID_H * CELL + 110))
        pygame.display.set_caption("Pizzatorio Factory")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 20)
        self.small = pygame.font.SysFont("arial", 16)
        self.running = True
        self.selected = CONVEYOR
        self.rotation = 0

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
                elif ev.key == pygame.K_r:
                    self.rotation = (self.rotation + 1) % 4
                elif ev.key == pygame.K_s:
                    self.sim.save()
                elif ev.key == pygame.K_l and SAVE_FILE.exists():
                    self.sim = FactorySim.load()
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                x, y = pygame.mouse.get_pos()
                gx, gy = x // CELL, y // CELL
                if gy < GRID_H:
                    self.sim.place_tile(gx, gy, self.selected, self.rotation)

    def draw_tile(self, x: int, y: int, tile: Tile) -> None:
        rect = pygame.Rect(x * CELL, y * CELL, CELL - 1, CELL - 1)
        colors = {
            EMPTY: (35, 35, 40),
            CONVEYOR: (90, 130, 210),
            MACHINE: (210, 160, 70),
            PROCESSOR: (220, 180, 85),
            OVEN: (235, 95, 55),
            BOT_DOCK: (110, 220, 220),
            SOURCE: (80, 180, 80),
            SINK: (180, 80, 80),
        }
        pygame.draw.rect(self.screen, colors[tile.kind], rect)
        if tile.kind in (CONVEYOR, MACHINE, PROCESSOR, OVEN, BOT_DOCK, SOURCE):
            cx = x * CELL + CELL // 2
            cy = y * CELL + CELL // 2
            dx, dy = DIRS[tile.rot]
            pygame.draw.line(self.screen, (250, 250, 250), (cx, cy), (cx + dx * 11, cy + dy * 11), 3)

    def draw(self) -> None:
        self.screen.fill((15, 16, 20))
        for y in range(GRID_H):
            for x in range(GRID_W):
                self.draw_tile(x, y, self.sim.grid[y][x])

        for item in self.sim.items:
            px = item.x * CELL + CELL // 2
            py = item.y * CELL + CELL // 2
            colors = {
                0: (210, 210, 230),
                1: (255, 210, 120),
                2: (255, 130, 90),
            }
            color = colors.get(item.stage, (255, 255, 255))
            pygame.draw.circle(self.screen, color, (int(px), int(py)), 6)

        panel_y = GRID_H * CELL + 8
        text = (
            f"Tool: {'DEL' if self.selected == EMPTY else self.selected.upper()} | Rot: {self.rotation} "
            f"(1 conveyor, 2 processor, 3 oven, 4 bot dock, 5 delete, R rotate, S save, L load)"
        )
        self.screen.blit(self.small.render(text, True, (220, 220, 220)), (8, panel_y))

        kpi = (
            f"KPI Throughput(ontime): {self.sim.ontime_rate:5.1f}%   "
            f"Bottleneck: {self.sim.bottleneck:5.1f}%   Hygiene: {self.sim.hygiene:5.1f}%"
        )
        self.screen.blit(self.font.render(kpi, True, (120, 255, 170)), (8, panel_y + 30))

        dtext = (
            f"Deliveries: {len(self.sim.deliveries)} | Tech: ovens={int(self.sim.tech_tree['ovens'])} "
            f"bots={int(self.sim.tech_tree['bots'])} turbo={int(self.sim.tech_tree['turbo_belts'])} "
            f"| XP: {self.sim.research_points:4.1f} | Expansion Tier: {self.sim.expansion_level}"
        )
        self.screen.blit(self.small.render(dtext, True, (255, 255, 180)), (8, panel_y + 66))

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
