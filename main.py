from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
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


@dataclass
class RuntimeLayout:
    viewport_w: int
    viewport_h: int
    safe_top: int
    safe_bottom: int
    top_strip_h: int
    bottom_sheet_h: int
    side_panel_w: int
    play_w: int
    play_h: int
    cell_size: int
    grid_px_w: int
    grid_px_h: int
    grid_x: int
    grid_y: int
    play_top: int
    play_bottom: int
    bottom_sheet_y: int


UI_SETTINGS_FILE = Path("ui_settings.json")


class GameUI:
    def __init__(self, sim: FactorySim):
        if pygame is None:
            raise RuntimeError("pygame is required for graphical mode")
        pygame.init()
        self.sim = sim

        self.display_mode = self._select_display_mode()
        self.touch_mode = self.display_mode == "mobile_fullscreen"
        self.layout: RuntimeLayout | None = None

        display = pygame.display.Info()
        self.physical_viewport = (display.current_w, display.current_h)

        if self.display_mode == "mobile_fullscreen":
            flags = pygame.FULLSCREEN
            if hasattr(pygame, "SCALED"):
                flags |= pygame.SCALED
            self.screen = pygame.display.set_mode((0, 0), flags)
        else:
            window_w = GRID_W * CELL + 340
            window_h = GRID_H * CELL + 190
            self.screen = pygame.display.set_mode((window_w, window_h), pygame.RESIZABLE)

        self.hud_state_cycle = ["hidden", "compact", "expanded"]
        self.bottom_sheet_state = "expanded"
        self.sidebar_visible = True
        self.show_top_kpis = True
        self.show_floating_dock = True
        self._load_ui_settings()

        self._reflow_layout(*self.screen.get_size())
        pygame.display.set_caption("Pizzatorio Factory")
        self.clock = pygame.time.Clock()
        self.touch_target_min_h = 56 if self.touch_mode else 34
        self.touch_horizontal_padding = 26 if self.touch_mode else 14
        self.hit_slop = 12 if self.touch_mode else 5
        self.font = pygame.font.SysFont("arial", 22)
        self.small = pygame.font.SysFont("arial", 17)
        self.chip_font = self.small
        self.running = True
        self.selected = CONVEYOR
        self.rotation = 0
        self.hud_toggle_rects: List[Tuple[pygame.Rect, str]] = []
        self.sidebar_toggle_rect: pygame.Rect | None = None

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
        self.build_toolbar_actions = {
            "Belts": ["1 Conveyor", "5 Delete", "Rot -", "Rot +"],
            "Machines": ["2 Processor", "3 Oven", "6 Assembly", "Rot -", "Rot +"],
            "Utilities": ["4 Bot Dock", "S Save", "L Load", "C Cycle R&D", "U Unlock"],
        }

        self.palette = {
            "bg": (12, 15, 24),
            "panel": (20, 25, 38),
            "panel_border": (46, 56, 80),
            "grid_line": (38, 45, 62),
            "text": (230, 236, 248),
            "muted": (161, 177, 205),
            "accent": (97, 167, 255),
            "chip": (30, 38, 55),
            "chip_active": (88, 140, 236),
            "chip_active_border": (180, 215, 255),
        }

    def _select_display_mode(self) -> str:
        is_android = (
            os.environ.get("ANDROID_ARGUMENT") is not None
            or os.environ.get("P4A_BOOTSTRAP") is not None
            or "pydroid" in os.environ.get("PYTHONHOME", "").lower()
            or "pydroid" in os.environ.get("TERMUX_VERSION", "").lower()
        )
        return "mobile_fullscreen" if is_android else "desktop_windowed"

    def _load_ui_settings(self) -> None:
        if not UI_SETTINGS_FILE.exists():
            return
        try:
            data = json.loads(UI_SETTINGS_FILE.read_text())
        except (OSError, json.JSONDecodeError):
            return
        if str(data.get("bottom_sheet_state", "")) in self.hud_state_cycle:
            self.bottom_sheet_state = str(data["bottom_sheet_state"])
        self.sidebar_visible = bool(data.get("sidebar_visible", self.sidebar_visible))
        self.show_top_kpis = bool(data.get("show_top_kpis", self.show_top_kpis))
        self.show_floating_dock = bool(data.get("show_floating_dock", self.show_floating_dock))

    def _save_ui_settings(self) -> None:
        payload = {
            "bottom_sheet_state": self.bottom_sheet_state,
            "sidebar_visible": self.sidebar_visible,
            "show_top_kpis": self.show_top_kpis,
            "show_floating_dock": self.show_floating_dock,
        }
        UI_SETTINGS_FILE.write_text(json.dumps(payload, indent=2))

    def _cycle_bottom_sheet_state(self) -> None:
        idx = self.hud_state_cycle.index(self.bottom_sheet_state)
        self.bottom_sheet_state = self.hud_state_cycle[(idx + 1) % len(self.hud_state_cycle)]
        self._save_ui_settings()
        self._reflow_layout()

    def _reflow_layout(self, viewport_w: int | None = None, viewport_h: int | None = None) -> None:
        if viewport_w is None or viewport_h is None:
            viewport_w, viewport_h = self.screen.get_size()

        landscape = viewport_w >= viewport_h
        mobile = self.display_mode == "mobile_fullscreen"
        safe_top = int(viewport_h * 0.02) if mobile else 0
        safe_bottom = int(viewport_h * 0.03) if mobile else 0

        top_strip_h = max(54, int(viewport_h * 0.1)) if self.show_top_kpis else 0
        sheet_heights = {
            "hidden": 0,
            "compact": max(64 if self.touch_mode else 56, int(viewport_h * 0.11)),
            "expanded": max(210 if self.touch_mode else 170, int(viewport_h * (0.38 if self.touch_mode else 0.3))),
        }
        bottom_sheet_h = sheet_heights.get(self.bottom_sheet_state, sheet_heights["expanded"])

        sidebar_ratio = 0.28 if landscape else 0.0
        side_panel_w = 0
        if landscape and self.sidebar_visible:
            side_panel_w = max(250, int(viewport_w * sidebar_ratio))

        play_w = max(320, viewport_w - side_panel_w)
        play_top = safe_top + top_strip_h
        play_bottom = viewport_h - safe_bottom - bottom_sheet_h
        play_h = max(220, play_bottom - play_top)

        cell_size = max(18, int(min(play_w / GRID_W, play_h / GRID_H)))
        grid_px_w = int(cell_size * GRID_W)
        grid_px_h = int(cell_size * GRID_H)
        grid_x = max(0, (play_w - grid_px_w) // 2)
        grid_y = play_top + max(0, (play_h - grid_px_h) // 2)

        self.layout = RuntimeLayout(
            viewport_w=viewport_w,
            viewport_h=viewport_h,
            safe_top=safe_top,
            safe_bottom=safe_bottom,
            top_strip_h=top_strip_h,
            bottom_sheet_h=bottom_sheet_h,
            side_panel_w=side_panel_w,
            play_w=play_w,
            play_h=play_h,
            cell_size=cell_size,
            grid_px_w=grid_px_w,
            grid_px_h=grid_px_h,
            grid_x=grid_x,
            grid_y=grid_y,
            play_top=play_top,
            play_bottom=play_bottom,
            bottom_sheet_y=viewport_h - safe_bottom - bottom_sheet_h,
        )

        self.landscape = landscape
        self.sidebar_w = side_panel_w
        self.window_w = viewport_w
        self.window_h = viewport_h
        self.grid_px_w = grid_px_w
        self.grid_px_h = grid_px_h

        chip_size = max(17, int(self.touch_target_min_h * 0.38))
        small_size = max(15, int(chip_size * 0.86))
        body_size = max(20, int(chip_size * 1.15))
        self.chip_font = pygame.font.SysFont("arial", chip_size)
        self.small = pygame.font.SysFont("arial", small_size)
        self.font = pygame.font.SysFont("arial", body_size)

    def _toolbar_button_label(self, label: str) -> str:
        if not self.touch_mode:
            return label
        if " " not in label:
            return label
        prefix, remainder = label.split(" ", 1)
        return remainder if len(prefix) == 1 and prefix.isalnum() else label

    def _layout_chip_rows(
        self,
        labels: List[str],
        start_y: int,
        min_width: int,
        min_height: int,
        gap_x: int,
        gap_y: int,
        label_fn=None,
    ) -> List[Tuple[pygame.Rect, str]]:
        assert self.layout is not None
        x = 10
        y = start_y
        max_x = self.layout.play_w - 10
        rects: List[Tuple[pygame.Rect, str]] = []
        render_label = label_fn or (lambda text: text)
        for value in labels:
            shown = render_label(value)
            text_w, text_h = self.chip_font.size(shown)
            width = max(min_width, text_w + self.touch_horizontal_padding * 2)
            height = max(min_height, text_h + 14)
            if x + width > max_x and x > 10:
                x = 10
                y += height + gap_y
            rects.append((pygame.Rect(x, y, width, height), value))
            x += width + gap_x
        return rects

    def _screen_to_grid(self, mx: int, my: int) -> Tuple[int, int] | None:
        assert self.layout is not None
        if not (
            self.layout.grid_x <= mx < self.layout.grid_x + self.layout.grid_px_w
            and self.layout.grid_y <= my < self.layout.grid_y + self.layout.grid_px_h
        ):
            return None
        gx = int((mx - self.layout.grid_x) // self.layout.cell_size)
        gy = int((my - self.layout.grid_y) // self.layout.cell_size)
        if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
            return gx, gy
        return None

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
        if section == "Orders":
            labels: List[str] = []
            for channel in self.section_defaults.get("Orders", []):
                key = channel.lower().replace("-", "_")
                if self.sim.order_channel_is_unlocked(key):
                    labels.append(channel)
                else:
                    min_rep = int(self.sim.order_channel_min_reputation(key))
                    labels.append(f"{channel} (Rep {min_rep})")
            return labels
        if section == "Commercials":
            labels: List[str] = []
            for strategy in self.section_defaults.get("Commercials", []):
                key = strategy.lower()
                if self.sim.commercial_strategy_is_unlocked(key):
                    labels.append(strategy)
                else:
                    required = str(self.simulation_commercials().get(key, {}).get("required_research", "")).strip()
                    labels.append(f"{strategy} ({required})" if required else strategy)
            return labels
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
                label = subsection.split(" (", 1)[0]
                requested_channel = label.lower().replace("-", "_")
                if self.sim.set_order_channel(requested_channel):
                    self.order_channel = requested_channel
                else:
                    selected_label = self.order_channel.replace("_", "-").title()
                    self.active_subsection = selected_label
            elif self.active_section == "Commercials":
                strategy = subsection.split(" (", 1)[0].lower()
                if self.sim.set_commercial_strategy(strategy):
                    self.commercial_strategy = self.sim.commercial_strategy
                else:
                    self.active_subsection = self.commercial_strategy.title()
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

    def simulation_commercials(self) -> Dict[str, Dict[str, str | int | float]]:
        from game.simulation import COMMERCIALS

        return COMMERCIALS

    def _ui_rects(self) -> Dict[str, List[Tuple[pygame.Rect, str]]]:
        assert self.layout is not None
        if self.layout.bottom_sheet_h <= 0 or self.bottom_sheet_state != "expanded":
            return {"sections": [], "subsections": []}
        top_y = self.layout.bottom_sheet_y + 8
        sections = self._layout_chip_rows(
            self.main_sections,
            start_y=top_y,
            min_width=120 if self.touch_mode else 104,
            min_height=self.touch_target_min_h,
            gap_x=10,
            gap_y=8,
        )

        sub_start = max(rect.bottom for rect, _ in sections) + 8 if sections else top_y
        subs = self._layout_chip_rows(
            self._subsections_for(self.active_section),
            start_y=sub_start,
            min_width=150 if self.touch_mode else 132,
            min_height=self.touch_target_min_h,
            gap_x=10,
            gap_y=8,
        )

        return {"sections": sections, "subsections": subs}

    def _toolbar_rects(self) -> List[Tuple[pygame.Rect, str]]:
        assert self.layout is not None
        if self.layout.bottom_sheet_h <= 0:
            return []
        if self.bottom_sheet_state == "compact":
            return self._layout_chip_rows(
                ["1 Conveyor", "2 Processor", "3 Oven", "5 Delete", "Rot +"],
                start_y=self.layout.bottom_sheet_y + 8,
                min_width=120 if self.touch_mode else 96,
                min_height=self.touch_target_min_h,
                gap_x=10,
                gap_y=8,
                label_fn=self._toolbar_button_label,
            )

        ui_rects = self._ui_rects()
        last_sub_bottom = max(rect.bottom for rect, _ in ui_rects["subsections"]) if ui_rects["subsections"] else self.layout.bottom_sheet_y + 8
        y = last_sub_bottom + 10
        actions = self._active_toolbar_actions()
        return self._layout_chip_rows(
            actions,
            start_y=y,
            min_width=156 if self.touch_mode else 94,
            min_height=self.touch_target_min_h,
            gap_x=10,
            gap_y=8,
            label_fn=self._toolbar_button_label,
        )

    def _expanded_hit_rect(self, rect: pygame.Rect) -> pygame.Rect:
        return rect.inflate(self.hit_slop * 2, self.hit_slop * 2)

    def _active_toolbar_actions(self) -> List[str]:
        if self.active_section == "Build":
            return list(self.build_toolbar_actions.get(self.active_subsection, self.toolbar_actions))
        return self.toolbar_actions

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
            self._save_ui_settings()
        elif label == "L Load" and SAVE_FILE.exists():
            self.sim = FactorySim.load()
            self.order_channel = self.sim.order_channel
            self.commercial_strategy = self.sim.commercial_strategy
            self._load_ui_settings()
            self._reflow_layout()
        else:
            return False
        return True

    def _handle_click(self, mx: int, my: int) -> bool:
        for rect, action in self.hud_toggle_rects:
            if self._expanded_hit_rect(rect).collidepoint(mx, my):
                if action == "sheet":
                    self._cycle_bottom_sheet_state()
                elif action == "kpis":
                    self.show_top_kpis = not self.show_top_kpis
                    self._save_ui_settings()
                    self._reflow_layout()
                elif action == "dock":
                    self.show_floating_dock = not self.show_floating_dock
                    self._save_ui_settings()
                elif action.startswith("tool:"):
                    return self._handle_toolbar_action(action.split(":", 1)[1])
                return True

        if self.sidebar_toggle_rect and self._expanded_hit_rect(self.sidebar_toggle_rect).collidepoint(mx, my):
            self.sidebar_visible = not self.sidebar_visible
            self._save_ui_settings()
            self._reflow_layout()
            return True

        ui_rects = self._ui_rects()
        for rect, section in ui_rects["sections"]:
            if self._expanded_hit_rect(rect).collidepoint(mx, my):
                self._set_section(section)
                return True
        for rect, subsection in ui_rects["subsections"]:
            if self._expanded_hit_rect(rect).collidepoint(mx, my):
                self._set_subsection(subsection)
                return True
        for rect, label in self._toolbar_rects():
            if self._expanded_hit_rect(rect).collidepoint(mx, my):
                return self._handle_toolbar_action(label)
        return False

    def handle_input(self) -> None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            if ev.type == pygame.VIDEORESIZE and self.display_mode == "desktop_windowed":
                self.screen = pygame.display.set_mode((ev.w, ev.h), pygame.RESIZABLE)
                self._reflow_layout(ev.w, ev.h)
            if hasattr(pygame, "WINDOWSIZECHANGED") and ev.type == pygame.WINDOWSIZECHANGED:
                self._reflow_layout(*self.screen.get_size())
            if ev.type == pygame.KEYDOWN:
                if self.touch_mode:
                    continue
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
                elif ev.key == pygame.K_h:
                    self._cycle_bottom_sheet_state()
                elif ev.key == pygame.K_F6:
                    self.show_top_kpis = not self.show_top_kpis
                    self._save_ui_settings()
                    self._reflow_layout()
                elif ev.key == pygame.K_F7:
                    self.sidebar_visible = not self.sidebar_visible
                    self._save_ui_settings()
                    self._reflow_layout()
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                x, y = pygame.mouse.get_pos()
                assert self.layout is not None
                in_sheet = self.layout.bottom_sheet_h > 0 and y >= self.layout.bottom_sheet_y
                if (in_sheet or self.layout.top_strip_h > 0 or self.sidebar_toggle_rect is not None) and self._handle_click(x, y):
                    continue
                pos = self._screen_to_grid(x, y)
                if pos is not None:
                    gx, gy = pos
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
        border = self.palette["chip_active_border"] if active else self.palette["panel_border"]
        label_color = (255, 255, 255) if active else self.palette["text"]
        radius = 14 if self.touch_mode else 9
        pygame.draw.rect(self.screen, bg, rect, border_radius=radius)
        pygame.draw.rect(self.screen, border, rect, width=2 if active else 1, border_radius=radius)
        shown = self._toolbar_button_label(label)
        text = self.chip_font.render(shown, True, label_color)
        text_rect = text.get_rect(center=rect.center)
        self.screen.blit(text, text_rect)

    def _draw_sidebar(self) -> None:
        assert self.layout is not None
        if not self.landscape:
            return

        toggle = pygame.Rect(self.layout.play_w - 24, 12, 22, 54)
        self.sidebar_toggle_rect = toggle
        self._draw_chip(toggle, ">" if not self.sidebar_visible else "<", self.sidebar_visible)

        if self.layout.side_panel_w <= 0:
            return

        panel = pygame.Rect(self.layout.play_w, 0, self.layout.side_panel_w, self.layout.viewport_h)
        pygame.draw.rect(self.screen, (16, 21, 33), panel)
        pygame.draw.line(
            self.screen,
            self.palette["panel_border"],
            (self.layout.play_w, 0),
            (self.layout.play_w, self.layout.viewport_h),
            2,
        )

        y = 14
        self.screen.blit(self.font.render("Operations", True, self.palette["text"]), (self.layout.play_w + 14, y))
        y += 34
        critical = [
            f"Cash: ${self.sim.money}",
            f"Orders due: {len(self.sim.orders)}",
            f"Throughput: {self.sim.ontime_rate:0.1f}%",
            f"Deliveries active: {len(self.sim.deliveries)}",
        ]
        for row in critical:
            self.screen.blit(self.small.render(row, True, self.palette["text"]), (self.layout.play_w + 14, y))
            y += 24

        card_y = y + 10
        card_w = self.layout.side_panel_w - 28
        self._draw_metric_card(self.layout.play_w + 14, card_y, card_w, "Bottleneck", self.sim.bottleneck, (242, 186, 88))
        self._draw_metric_card(self.layout.play_w + 14, card_y + 64, card_w, "Hygiene", self.sim.hygiene, (101, 189, 255))

        if self.active_section == "Info" and self.active_subsection == "Logs":
            detail_y = card_y + 138
            self.screen.blit(self.small.render("Verbose logs:", True, self.palette["muted"]), (self.layout.play_w + 14, detail_y))
            detail_y += 22
            for line in self.sim.event_log[-4:]:
                self.screen.blit(self.small.render(line, True, self.palette["muted"]), (self.layout.play_w + 14, detail_y))
                detail_y += 21

    def draw_tile(self, x: int, y: int, tile) -> None:
        assert self.layout is not None
        cell = self.layout.cell_size
        rect = pygame.Rect(
            self.layout.grid_x + x * cell + 1,
            self.layout.grid_y + y * cell + 1,
            cell - 2,
            cell - 2,
        )
        base = self._tile_base_color(tile.kind)
        lift = tuple(min(255, c + 25) for c in base)
        pygame.draw.rect(self.screen, base, rect, border_radius=10)
        shine = pygame.Rect(rect.x + 1, rect.y + 1, rect.w - 2, rect.h // 2)
        pygame.draw.rect(self.screen, lift, shine, border_top_left_radius=10, border_top_right_radius=10)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, width=1, border_radius=10)
        if tile.kind != EMPTY:
            self._draw_tile_icon(tile, rect)

    def draw(self) -> None:
        assert self.layout is not None
        cell = self.layout.cell_size
        self.screen.fill(self.palette["bg"])
        self.hud_toggle_rects = []
        self.sidebar_toggle_rect = None
        for y in range(GRID_H):
            for x in range(GRID_W):
                self.draw_tile(x, y, self.sim.grid[y][x])

        for x in range(GRID_W + 1):
            xpos = self.layout.grid_x + x * cell
            pygame.draw.line(
                self.screen,
                self.palette["grid_line"],
                (xpos, self.layout.grid_y),
                (xpos, self.layout.grid_y + self.grid_px_h),
                1,
            )
        for y in range(GRID_H + 1):
            ypos = self.layout.grid_y + y * cell
            pygame.draw.line(
                self.screen,
                self.palette["grid_line"],
                (self.layout.grid_x, ypos),
                (self.layout.grid_x + self.grid_px_w, ypos),
                1,
            )

        for item in self.sim.items:
            px = self.layout.grid_x + item.x * cell + cell // 2
            py = self.layout.grid_y + item.y * cell + cell // 2
            colors = {
                "raw": (219, 223, 235),
                "processed": (255, 214, 126),
                "baked": (255, 139, 94),
            }
            color = colors.get(item.stage, (255, 255, 255))
            pygame.draw.circle(self.screen, (30, 34, 45), (int(px), int(py)), max(5, cell // 4))
            pygame.draw.circle(self.screen, color, (int(px), int(py)), max(3, cell // 6))

        if self.layout.top_strip_h > 0:
            top = pygame.Rect(0, self.layout.safe_top, self.layout.play_w, self.layout.top_strip_h)
            pygame.draw.rect(self.screen, (18, 23, 35), top)
            metrics = [
                f"Cash ${self.sim.money}",
                f"Orders Due {len(self.sim.orders)}",
                f"Throughput {self.sim.ontime_rate:0.1f}%",
            ]
            x = 10
            for metric in metrics:
                label = self.small.render(metric, True, self.palette["text"])
                self.screen.blit(label, (x, top.y + 12))
                x += label.get_width() + 24
            toggle_labels = [
                (f"HUD {self.bottom_sheet_state.title()}", "sheet", True),
                (f"KPIs {'On' if self.show_top_kpis else 'Off'}", "kpis", self.show_top_kpis),
            ]
            if not self.landscape:
                toggle_labels.append((f"Dock {'On' if self.show_floating_dock else 'Off'}", "dock", self.show_floating_dock))
            tx = self.layout.play_w - 10
            for label, action, active in reversed(toggle_labels):
                tw, th = self.small.size(label)
                rect = pygame.Rect(tx - tw - 24, top.y + 8, tw + 16, top.height - 16)
                tx = rect.x - 8
                self._draw_chip(rect, label, active)
                self.hud_toggle_rects.append((rect, action))

        if self.layout.bottom_sheet_h > 0:
            panel = pygame.Rect(0, self.layout.bottom_sheet_y, self.layout.play_w, self.layout.bottom_sheet_h)
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

        if not self.landscape and self.show_floating_dock:
            dock_actions = ["1 Conveyor", "2 Processor", "5 Delete", "Rot +", "S Save"]
            dock_y = self.layout.play_bottom - 58
            dock_x = max(8, self.layout.play_w - 110)
            for idx, label in enumerate(dock_actions):
                rect = pygame.Rect(dock_x, dock_y - idx * 50, 100, 42)
                self._draw_chip(rect, self._toolbar_button_label(label), False)
                self.hud_toggle_rects.append((rect, f"tool:{label}"))

        dtext = f"Tool={self.selected.upper()} Rot={self.rotation}"
        self.screen.blit(self.small.render(dtext, True, (255, 236, 160)), (10, self.layout.play_bottom - 26))

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
