"""Persistent preset/custom Pomodoro countdown applet."""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

from PIL import Image

from .base import Applet, AppletMeta
from ..ui import BLACK, Rect, button, canvas, centered_text, draw_header, fit_text, font

PRESETS = (
    ("FOCUS", 25),
    ("SHORT", 5),
    ("LONG", 15),
    ("DEEP", 50),
)

PRESET_RECTS = (
    Rect(4, 27, 62, 52),
    Rect(65, 27, 123, 52),
    Rect(126, 27, 184, 52),
    Rect(187, 27, 245, 52),
)
CUSTOM_RECT = Rect(4, 62, 130, 91)
PREV_RECT = Rect(134, 62, 158, 91)
NEXT_RECT = Rect(161, 62, 185, 91)
ADD_RECT = Rect(189, 62, 216, 91)
DELETE_RECT = Rect(219, 62, 246, 91)

EDITOR_MINUS_5 = Rect(4, 38, 44, 69)
EDITOR_MINUS_1 = Rect(47, 38, 87, 69)
EDITOR_PLUS_1 = Rect(162, 38, 202, 69)
EDITOR_PLUS_5 = Rect(205, 38, 245, 69)
EDITOR_SAVE = Rect(74, 74, 176, 93)

RUN_PAUSE = Rect(4, 72, 119, 93)
RUN_RESET = Rect(130, 72, 245, 93)

DELETE_CANCEL = Rect(4, 68, 119, 92)
DELETE_CONFIRM = Rect(130, 68, 245, 92)


class TimerStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[int]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            values = data.get("custom_minutes", [])
            return [int(value) for value in values if 1 <= int(value) <= 180]
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return []

    def save(self, values: list[int]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"custom_minutes": values}, indent=2) + "\n"
        with tempfile.NamedTemporaryFile("w", dir=self.path.parent, delete=False, encoding="utf-8") as target:
            target.write(payload)
            temporary = Path(target.name)
        temporary.replace(self.path)


class PomodoroApplet(Applet):
    meta = AppletMeta("pomodoro", "Pomodoro", "Focus and break timers")

    def __init__(self, config_path: Path) -> None:
        self.store = TimerStore(config_path)
        self.custom_minutes = self.store.load()
        self.custom_index = 0
        self.view = "select"
        self.edit_minutes = 30
        self.timer_label = ""
        self.timer_minutes = 0
        self.ends_at: float | None = None
        self.paused_remaining: float | None = None
        self.last_visible_second: int | None = None

    @property
    def running(self) -> bool:
        return self.ends_at is not None or self.paused_remaining is not None

    def remaining_seconds(self, now: float) -> int:
        if self.paused_remaining is not None:
            return max(0, math.ceil(self.paused_remaining))
        if self.ends_at is None:
            return 0
        return max(0, math.ceil(self.ends_at - now))

    def start_timer(self, label: str, minutes: int, now: float) -> None:
        self.timer_label = label
        self.timer_minutes = minutes
        self.ends_at = now + minutes * 60
        self.paused_remaining = None
        self.last_visible_second = None
        self.view = "timer"

    def tick(self, now: float) -> bool:
        if self.view != "timer" or not self.running:
            return False
        second = self.remaining_seconds(now)
        changed = second != self.last_visible_second
        self.last_visible_second = second
        return changed

    def launcher_status(self, now: float) -> str:
        if not self.running:
            return self.meta.subtitle
        remaining = self.remaining_seconds(now)
        return f"{self.timer_label} {remaining // 60:02d}:{remaining % 60:02d}"

    def _render_select(self, now: float) -> Image.Image:
        image, draw = canvas()
        status = self.launcher_status(now) if self.running else "TAP A TIMER TO START"
        draw_header(draw, "Pomodoro", status)
        for rect, (label, minutes) in zip(PRESET_RECTS, PRESETS):
            draw.rectangle((rect.x0, rect.y0, rect.x1, rect.y1), fill=255, outline=BLACK)
            centered_text(draw, Rect(rect.x0, rect.y0 + 1, rect.x1, rect.y0 + 13), f"{minutes}m", font("display", 11))
            centered_text(draw, Rect(rect.x0, rect.y0 + 13, rect.x1, rect.y1), label, font("mono", 6))

        if self.custom_minutes:
            self.custom_index %= len(self.custom_minutes)
            value = self.custom_minutes[self.custom_index]
            label = f"CUSTOM {self.custom_index + 1}/{len(self.custom_minutes)}  {value} MIN"
            button(draw, CUSTOM_RECT, label, selected_font=font("bold", 8))
        else:
            button(draw, CUSTOM_RECT, "NO CUSTOM TIMERS", disabled=True, selected_font=font("body", 7))
        button(draw, PREV_RECT, "<", disabled=not self.custom_minutes, selected_font=font("bold", 13))
        button(draw, NEXT_RECT, ">", disabled=not self.custom_minutes, selected_font=font("bold", 13))
        button(draw, ADD_RECT, "+", selected_font=font("bold", 14))
        button(draw, DELETE_RECT, "X", disabled=not self.custom_minutes, selected_font=font("bold", 11))
        return image

    def _render_editor(self) -> Image.Image:
        image, draw = canvas()
        draw_header(draw, "New custom", "SET DURATION IN MINUTES")
        button(draw, EDITOR_MINUS_5, "-5", selected_font=font("bold", 10))
        button(draw, EDITOR_MINUS_1, "-1", selected_font=font("bold", 10))
        centered_text(draw, Rect(90, 32, 159, 73), str(self.edit_minutes), font("display", 24))
        button(draw, EDITOR_PLUS_1, "+1", selected_font=font("bold", 10))
        button(draw, EDITOR_PLUS_5, "+5", selected_font=font("bold", 10))
        button(draw, EDITOR_SAVE, "SAVE TIMER", selected=True, selected_font=font("bold", 8))
        return image

    def _render_timer(self, now: float) -> Image.Image:
        image, draw = canvas()
        remaining = self.remaining_seconds(now)
        state = "PAUSED" if self.paused_remaining is not None else ("COMPLETE" if remaining == 0 else "COUNTING DOWN")
        draw_header(draw, fit_text(self.timer_label, 18), state)
        time_text = f"{remaining // 60:02d}:{remaining % 60:02d}"
        centered_text(draw, Rect(4, 25, 245, 61), time_text, font("mono", 27))
        total = max(1, self.timer_minutes * 60)
        elapsed_ratio = 1 - (remaining / total)
        draw.rectangle((5, 63, 244, 68), outline=BLACK, fill=255)
        draw.rectangle((6, 64, 6 + int(237 * elapsed_ratio), 67), fill=BLACK)
        pause_label = "RESUME" if self.paused_remaining is not None else "PAUSE"
        if remaining == 0:
            pause_label = "DONE"
        button(draw, RUN_PAUSE, pause_label, selected=remaining == 0, selected_font=font("bold", 9))
        button(draw, RUN_RESET, "CHOOSE TIMER", selected_font=font("bold", 8))
        return image

    def _render_delete(self) -> Image.Image:
        image, draw = canvas()
        value = self.custom_minutes[self.custom_index]
        draw_header(draw, "Delete timer?", "CUSTOM TIMER")
        centered_text(draw, Rect(4, 28, 245, 62), f"{value} MINUTES", font("display", 19))
        button(draw, DELETE_CANCEL, "KEEP", selected_font=font("bold", 9))
        button(draw, DELETE_CONFIRM, "DELETE", selected=True, selected_font=font("bold", 9))
        return image

    def render(self, now: float) -> Image.Image:
        if self.view == "editor":
            return self._render_editor()
        if self.view == "timer":
            return self._render_timer(now)
        if self.view == "delete":
            return self._render_delete()
        return self._render_select(now)

    def _adjust_editor(self, delta: int) -> None:
        self.edit_minutes = max(1, min(180, self.edit_minutes + delta))

    def handle_touch(self, x: int, y: int, now: float) -> bool:
        if self.view == "select":
            for rect, (label, minutes) in zip(PRESET_RECTS, PRESETS):
                if rect.contains(x, y):
                    self.start_timer(label.title(), minutes, now)
                    return True
            if CUSTOM_RECT.contains(x, y) and self.custom_minutes:
                value = self.custom_minutes[self.custom_index]
                self.start_timer(f"Custom {value}m", value, now)
                return True
            if PREV_RECT.contains(x, y) and self.custom_minutes:
                self.custom_index = (self.custom_index - 1) % len(self.custom_minutes)
                return True
            if NEXT_RECT.contains(x, y) and self.custom_minutes:
                self.custom_index = (self.custom_index + 1) % len(self.custom_minutes)
                return True
            if ADD_RECT.contains(x, y):
                self.edit_minutes = 30
                self.view = "editor"
                return True
            if DELETE_RECT.contains(x, y) and self.custom_minutes:
                self.view = "delete"
                return True
            return False

        if self.view == "editor":
            for rect, delta in (
                (EDITOR_MINUS_5, -5),
                (EDITOR_MINUS_1, -1),
                (EDITOR_PLUS_1, 1),
                (EDITOR_PLUS_5, 5),
            ):
                if rect.contains(x, y):
                    self._adjust_editor(delta)
                    return True
            if EDITOR_SAVE.contains(x, y):
                self.custom_minutes.append(self.edit_minutes)
                self.custom_index = len(self.custom_minutes) - 1
                self.store.save(self.custom_minutes)
                self.view = "select"
                return True
            return False

        if self.view == "delete":
            if DELETE_CANCEL.contains(x, y):
                self.view = "select"
                return True
            if DELETE_CONFIRM.contains(x, y):
                del self.custom_minutes[self.custom_index]
                self.custom_index = max(0, min(self.custom_index, len(self.custom_minutes) - 1))
                self.store.save(self.custom_minutes)
                self.view = "select"
                return True
            return False

        if self.view == "timer":
            if RUN_RESET.contains(x, y):
                self.view = "select"
                return True
            if RUN_PAUSE.contains(x, y):
                remaining = self.remaining_seconds(now)
                if remaining == 0:
                    self.ends_at = None
                    self.paused_remaining = None
                    self.view = "select"
                elif self.paused_remaining is None:
                    self.paused_remaining = float(remaining)
                    self.ends_at = None
                else:
                    self.ends_at = now + self.paused_remaining
                    self.paused_remaining = None
                return True
        return False

    def back(self, now: float) -> bool:
        if self.view == "select":
            return False
        self.view = "select"
        return True
