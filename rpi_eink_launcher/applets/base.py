"""Applet contract used by the launcher registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image


@dataclass(frozen=True)
class AppletMeta:
    applet_id: str
    title: str
    subtitle: str


class Applet(ABC):
    meta: AppletMeta

    def on_enter(self, now: float) -> None:
        pass

    def on_leave(self, now: float) -> None:
        pass

    def tick(self, now: float) -> bool:
        """Update internal state and return True when the visible screen changed."""
        return False

    @abstractmethod
    def render(self, now: float) -> Image.Image:
        raise NotImplementedError

    @abstractmethod
    def handle_touch(self, x: int, y: int, now: float) -> bool:
        """Handle a content-area touch and return True when a redraw is needed."""
        raise NotImplementedError

    def back(self, now: float) -> bool:
        """Return True if handled internally; False asks the shell to close the applet."""
        return False

    def launcher_status(self, now: float) -> str:
        return self.meta.subtitle


class AppletRegistry:
    """Ordered applet registry; add future applets without changing shell logic."""

    def __init__(self) -> None:
        self._applets: list[Applet] = []

    def register(self, applet: Applet) -> Applet:
        if any(existing.meta.applet_id == applet.meta.applet_id for existing in self._applets):
            raise ValueError(f"Duplicate applet id: {applet.meta.applet_id}")
        self._applets.append(applet)
        return applet

    def all(self) -> tuple[Applet, ...]:
        return tuple(self._applets)

    def get(self, applet_id: str) -> Applet:
        for applet in self._applets:
            if applet.meta.applet_id == applet_id:
                return applet
        raise KeyError(applet_id)
