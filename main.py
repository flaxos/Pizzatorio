from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

from config import (
    ASSEMBLY_TABLE,
    BOT_DOCK,
    CELL,
    CONVEYOR,
    DIRS,
    EMPTY,
    GRID_H,
    GRID_W,
    MACHINE,
    OVEN,
    PROCESSOR,
    SAVE_FILE,
    SINK,
    SOURCE,
)
from game import FactorySim

try:
    import pygame  # type: ignore
except Exception:
    pygame = None


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
        self.section_defaults = {
            "Build": ["Belts", "Machines", "Utilities"],
            "Orders": ["Delivery", "Takeaway", "Eat-in"],
            "R&D": ["Cycle", "Unlock", "Clear"],
            "Commercials": ["Campaigns", "Promos", "Franchise"],
            "Info": ["KPIs", "Logs", "Economy"],
        }
        self.active_section = "Build"
        self.active_subsection = self._subsections_for(self.active_section)[0]
        self.order_channel = self.sim.order_channel
        self.commercial_strategy = self.sim.commercial_strategy
        self.toolbar_actions = [
            "1 Conveyor",
            "2 Processor",
            "3 Oven",
            "4 Bot Dock",
            "6 Assembly",
            "5 Delete",
            "Rot -",
            "Rot +",
            "C Cycle R&D",
            "U Unlock",
            "S Save",
            "L Load",
        ]

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
        self.active_subsection = self._subsections_for(section)[0]

    def _cycle_section(self) -> None:
        idx = self.main_sections.index(self.active_section)
        self._set_section(self.main_sections[(idx + 1) % len(self.main_sections)])

    def _rd_visible_targets(self) -> List[str]:
        targets = self.sim.available_research_targets()
        if self.sim.research_focus and self.sim.research_focus not in targets:
            targets.insert(0, self.sim.research_focus)
        return targets[:3]

    def _subsections_for(self, section: str) -> List[str]:
        if section != "R&D":
            return list(self.section_defaults.get(section, []))
        labels = list(self.section_defaults["R&D"])
        for tech in self._rd_visible_targets():
            labels.append(f"Focus: {tech}")
        return labels

    def _set_subsection(self, subsection: str) -> None:
        if subsection in self._subsections_for(self.active_section):
            self.active_subsection = subsection
            if self.active_section == "Orders":
                self.order_channel = subsection.lower().replace("-", "_")
                self.sim.set_order_channel(self.order_channel)
            elif self.active_section == "Commercials":
                strategy = subsection.lower()
                if self.sim.set_commercial_strategy(strategy):
                    self.commercial_strategy = self.sim.commercial_strategy
            elif self.active_section == "R&D":
                if subsection == "Cycle":
                    self.sim.cycle_research_focus()
                elif subsection == "Unlock":
                    self.sim.try_unlock_research_focus()
                elif subsection == "Clear":
                    self.sim.set_research_focus("")
                elif subsection.startswith("Focus: "):
                    self.sim.set_research_focus(subsection.split(": ", 1)[1])
                if self.sim.research_focus:
                    self.active_subsection = f"Focus: {self.sim.research_focus}"

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
        for subsection in self._subsections_for(self.active_section):
            rect = pygame.Rect(x, sub_y, 146, 28)
            subs.append((rect, subsection))
            x += 152

        return {"sections": sections, "subsections": subs}

    def _toolbar_rects(self) -> List[Tuple[pygame.Rect, str]]:
        y = self.grid_px_h + 78
        rects = []
        x = 10
        for label in self.toolbar_actions:
            w = max(86, len(label) * 8 + 20)
            rects.append((pygame.Rect(x, y, w, 30), label))
            x += w + 8
        return rects

    def _handle_toolbar_action(self, label: str) -> bool:
        if label == "1 Conveyor":
            self.selected = CONVEYOR
        elif label == "2 Processor":
            self.selected = PROCESSOR
        elif label == "3 Oven":
            self.selected = OVEN
        elif label == "4 Bot Dock":
            self.selected = BOT_DOCK
        elif label == "6 Assembly":
            self.selected = ASSEMBLY_TABLE
        elif label == "5 Delete":
            self.selected = EMPTY
        elif label == "Rot -":
            self.rotation = (self.rotation - 1) % 4
        elif label == "Rot +":
            self.rotation = (self.rotation + 1) % 4
        elif label == "C Cycle R&D":
            self.sim.cycle_research_focus()
        elif label == "U Unlock":
            self.sim.try_unlock_research_focus()
        elif label == "S Save":
            self.sim.save()
        elif label == "L Load" and SAVE_FILE.exists():
            self.sim = FactorySim.load()
            self.order_channel = self.sim.order_channel
            self.commercial_strategy = self.sim.commercial_strategy
        else:
            return False
        return True

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
        for rect, label in self._toolbar_rects():
            if rect.collidepoint(mx, my):
                return self._handle_toolbar_action(label)
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
                elif ev.key == pygame.K_6:
                    self.selected = ASSEMBLY_TABLE
                elif ev.key == pygame.K_5:
                    self.selected = EMPTY
                elif ev.key == pygame.K_r or ev.key == pygame.K_e:
                    self._handle_toolbar_action("Rot +")
                elif ev.key == pygame.K_q:
                    self._handle_toolbar_action("Rot -")
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
                    self._handle_toolbar_action("S Save")
                elif ev.key == pygame.K_c:
                    self._handle_toolbar_action("C Cycle R&D")
                elif ev.key == pygame.K_u:
                    self._handle_toolbar_action("U Unlock")
                elif ev.key == pygame.K_l:
                    self._handle_toolbar_action("L Load")
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
            ASSEMBLY_TABLE: (162, 110, 220),
            SOURCE: (88, 193, 112),
            SINK: (196, 98, 96),
        }
        return colors.get(kind, (100, 100, 100))

    def _draw_tile_icon(self, tile, rect: pygame.Rect) -> None:
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
        elif tile.kind == ASSEMBLY_TABLE:
            pygame.draw.rect(self.screen, icon, pygame.Rect(cx - 13, cy - 4, 26, 12), width=2, border_radius=3)
            pygame.draw.line(self.screen, icon, (cx - 9, cy + 8), (cx - 9, cy + 14), 2)
            pygame.draw.line(self.screen, icon, (cx + 9, cy + 8), (cx + 9, cy + 14), 2)
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
        fill_w = int(bar_bg.w * max(0.0, min(1.0, value / 100.0)))
        fill = pygame.Rect(bar_bg.x, bar_bg.y, fill_w, bar_bg.h)
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
            f"Commercial: {self.commercial_strategy}",
            f"R&D focus: {self.sim.research_focus or 'auto'}",
            f"R&D available: {len(self.sim.available_research_targets())}",
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

        if self.active_section == "Info":
            detail_y = card_y + 202
            if self.active_subsection == "Economy":
                net = self.sim.total_revenue - self.sim.total_spend
                details = [
                    f"Revenue: ${self.sim.total_revenue}",
                    f"Spend: ${self.sim.total_spend}",
                    f"Net: ${net}",
                    f"Waste items: {self.sim.waste}",
                ]
            elif self.active_subsection == "Logs":
                details = ["Recent events:"] + self.sim.event_log[-5:]
            else:
                details = [
                    f"Completed: {self.sim.completed}",
                    f"On-time: {self.sim.ontime}",
                    f"SLA rate: {self.sim.ontime_rate:0.1f}%",
                    f"Rep: {self.sim.reputation:0.1f}",
                ]
            for line in details:
                self.screen.blit(self.small.render(line, True, self.palette["muted"]), (self.grid_px_w + 14, detail_y))
                detail_y += 23

    def draw_tile(self, x: int, y: int, tile) -> None:
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
                or ("Assembly" in label and self.selected == ASSEMBLY_TABLE)
                or ("Delete" in label and self.selected == EMPTY)
            )
            self._draw_chip(rect, label, active)

        dtext = (
            f"Tool={self.selected.upper()} Rot={self.rotation} | Menu={self.active_section}/{self.active_subsection} "
            f"| Orders={len(self.sim.orders)} Deliveries={len(self.sim.deliveries)} Cash=${self.sim.money} "
            f"Rev=${self.sim.total_revenue} Spend=${self.sim.total_spend}"
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


def run_headless(ticks: int, dt: float, load_save: bool) -> None:
    sim = FactorySim.load() if (load_save and SAVE_FILE.exists()) else FactorySim()

    # Build a mid-game-like path automatically
    from config import BOT_DOCK, CONVEYOR, OVEN, PROCESSOR
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
