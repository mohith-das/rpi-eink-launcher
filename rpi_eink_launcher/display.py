"""Physical and preview display adapters."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

LOGGER = logging.getLogger(__name__)


class EInkDisplay:
    """Waveshare V3 display with ghosting-safe periodic full refreshes."""

    def __init__(self, full_refresh_every: int = 60) -> None:
        self.full_refresh_every = full_refresh_every
        self.partial_count = 0
        self.epd = None

    def initialize(self) -> None:
        from waveshare_epd import epd2in13_V3

        self._module = epd2in13_V3
        self.epd = epd2in13_V3.EPD()
        self.epd.init()
        self.epd.Clear()

    @staticmethod
    def orient(image: Image.Image) -> Image.Image:
        # Matches the original project's case/stand orientation.
        return image.rotate(180)

    def show(self, image: Image.Image, *, full: bool = False) -> None:
        if self.epd is None:
            raise RuntimeError("Display is not initialized")
        buffer = self.epd.getbuffer(self.orient(image))
        if full or self.partial_count >= self.full_refresh_every:
            self.epd.init()
            self.epd.displayPartBaseImage(buffer)
            self.partial_count = 0
        else:
            self.epd.displayPartial(buffer)
            self.partial_count += 1

    def close(self) -> None:
        if self.epd is None:
            return
        try:
            self.epd.sleep()
        finally:
            self._module.epdconfig.module_exit()


class PreviewDisplay:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.frames: list[Path] = []

    def initialize(self) -> None:
        pass

    def show(self, image: Image.Image, *, full: bool = False, name: str | None = None) -> None:
        path = self.output_dir / (name or f"frame-{len(self.frames):02d}.png")
        image.save(path)
        self.frames.append(path)

    def close(self) -> None:
        pass
