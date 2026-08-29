"""Launcher shell, applet lifecycle, and shared navigation."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from PIL import Image, ImageDraw

from .applets import Applet, AppletRegistry, InfoApplet, PomodoroApplet
from .touch import GT1151Touch
from .ui import (
    BACK_RECT,
    BLACK,
    HOME_RECT,
    NAV_TOP,
    PAGE_NEXT_RECT,
    PAGE_PREV_RECT,
    Rect,
    canvas,
    draw_nav,
    fit_text,
    font,
)

LOGGER = logging.getLogger(__name__)


class LauncherShell:
    def __init__(self, registry: AppletRegistry, touch) -> None:
        self.registry = registry
        self.touch = touch
        self.active: Applet | None = None
        self.force_full = True
        self._last_touch_at = 0.0
        self._touch_was_available = bool(touch.available)
        self._started_at = time.monotonic()
        self._fallback_opened = False
        self.launcher_page = 0

    def mark_ready(self, now: float) -> None:
        """Start fallback timing after slow e-paper hardware initialization."""
        self._started_at = now

    @property
    def launcher_pages(self) -> int:
        return max(1, (len(self.registry.all()) + 3) // 4)

    def _visible_applets(self) -> tuple[Applet, ...]:
        self.launcher_page %= self.launcher_pages
        start = self.launcher_page * 4
        return self.registry.all()[start : start + 4]

    def render_launcher(self, now: float) -> Image.Image:
        image, draw = canvas()
        draw.text((5, 3), "RPi EINK", font=font("display", 16), fill=BLACK)
        touch_text = "TOUCH READY" if self.touch.available else "TOUCH OFFLINE"
        draw.text((174, 7), touch_text, font=font("mono", 6), fill=BLACK)
        draw.line((0, 23, 249, 23), fill=BLACK)

        for index, applet in enumerate(self._visible_applets()):
            column = index % 2
            row = index // 2
            rect = Rect(4 + column * 123, 29 + row * 31, 122 + column * 123, 56 + row * 31)
            draw.rectangle((rect.x0, rect.y0, rect.x1, rect.y1), fill=255, outline=BLACK)
            draw.text((rect.x0 + 6, rect.y0 + 4), applet.meta.title.upper(), font=font("bold", 10), fill=BLACK)
            status = fit_text(applet.launcher_status(now), 24)
            draw.text((rect.x0 + 6, rect.y0 + 17), status, font=font("body", 6), fill=BLACK)
            draw.text((rect.x1 - 13, rect.y0 + 8), ">", font=font("bold", 12), fill=BLACK)

        if not self.touch.available:
            draw.text((5, 90), "Info opens automatically", font=font("mono", 6), fill=BLACK)
        draw_nav(
            draw,
            can_go_back=False,
            at_home=True,
            launcher_page=(self.launcher_page + 1, self.launcher_pages),
        )
        return image

    def _launcher_card_at(self, x: int, y: int) -> Applet | None:
        for index, applet in enumerate(self._visible_applets()):
            column = index % 2
            row = index // 2
            rect = Rect(4 + column * 123, 29 + row * 31, 122 + column * 123, 56 + row * 31)
            if rect.contains(x, y):
                return applet
        return None

    def open_applet(self, applet: Applet, now: float) -> None:
        if self.active is not None:
            self.active.on_leave(now)
        self.active = applet
        applet.on_enter(now)
        self.force_full = True

    def go_home(self, now: float) -> None:
        if self.active is not None:
            self.active.on_leave(now)
        self.active = None
        self.force_full = True

    def handle_touch(self, x: int, y: int, now: float) -> bool:
        if now - self._last_touch_at < 0.25:
            return False
        self._last_touch_at = now
        LOGGER.info("Touch at logical (%d, %d)", x, y)
        if HOME_RECT.contains(x, y):
            self.go_home(now)
            return True
        if self.active is None and self.launcher_pages > 1:
            if PAGE_PREV_RECT.contains(x, y):
                self.launcher_page = (self.launcher_page - 1) % self.launcher_pages
                self.force_full = True
                return True
            if PAGE_NEXT_RECT.contains(x, y):
                self.launcher_page = (self.launcher_page + 1) % self.launcher_pages
                self.force_full = True
                return True
        if BACK_RECT.contains(x, y):
            if self.active is None:
                return False
            if not self.active.back(now):
                self.go_home(now)
            else:
                self.force_full = True
            return True
        if y >= NAV_TOP:
            return False
        if self.active is None:
            selected = self._launcher_card_at(x, y)
            if selected is not None:
                self.open_applet(selected, now)
                return True
            return False
        changed = self.active.handle_touch(x, y, now)
        if changed:
            self.force_full = True
        return changed

    def tick(self, now: float) -> bool:
        touch_available = bool(self.touch.available)
        if touch_available != self._touch_was_available:
            self._touch_was_available = touch_available
            LOGGER.info("Touch availability changed: %s", touch_available)
            return True
        if self.active is not None and self.active.tick(now):
            return True
        # Preserve the old status monitor when the touch hardware is disconnected.
        if not touch_available and not self._fallback_opened and now - self._started_at >= 5:
            self._fallback_opened = True
            self.open_applet(self.registry.get("info"), now)
            return True
        return False

    def render(self, now: float) -> Image.Image:
        if self.active is None:
            return self.render_launcher(now)
        image = self.active.render(now)
        draw_nav(ImageDraw.Draw(image), can_go_back=True, at_home=False)
        return image


def build_registry(config_dir: Path) -> AppletRegistry:
    registry = AppletRegistry()
    registry.register(InfoApplet())
    registry.register(PomodoroApplet(config_dir / "timers.json"))
    # Future applets only need to implement Applet and be registered here.
    return registry


def run(display, touch=None, config_dir: Path | None = None) -> None:
    config_dir = config_dir or Path.home() / ".config" / "rpi-eink-launcher"
    touch = touch or GT1151Touch()
    registry = build_registry(config_dir)
    shell = LauncherShell(registry, touch)
    display.initialize()
    touch.initialize()
    shell.mark_ready(time.monotonic())
    dirty = True
    try:
        while True:
            now = time.monotonic()
            point = touch.poll(now)
            if point is not None:
                dirty = shell.handle_touch(point.x, point.y, now) or dirty
            dirty = shell.tick(now) or dirty
            if dirty:
                display.show(shell.render(now), full=shell.force_full)
                shell.force_full = False
                dirty = False
            time.sleep(0.05)
    finally:
        touch.close()
        display.close()
