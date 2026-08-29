"""GT1151 capacitive touch controller support."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from .ui import SCREEN_HEIGHT, SCREEN_WIDTH

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TouchPoint:
    x: int
    y: int
    size: int = 0


def map_raw_touch(raw_x: int, raw_y: int) -> TouchPoint:
    """Map the HAT's portrait coordinates to the launcher's rotated landscape UI."""
    logical_x = max(0, min(SCREEN_WIDTH - 1, raw_y))
    logical_y = max(0, min(SCREEN_HEIGHT - 1, SCREEN_HEIGHT - 1 - raw_x))
    return TouchPoint(logical_x, logical_y)


class GT1151Touch:
    ADDRESS = 0x14
    STATUS_REGISTER = 0x814E
    POINTS_REGISTER = 0x814F
    VERSION_REGISTER = 0x8140

    def __init__(self, retry_seconds: float = 10.0) -> None:
        self.retry_seconds = retry_seconds
        self.available = False
        self.last_error = "not initialized"
        self.version = ""
        self._bus = None
        self._reset = None
        self._interrupt = None
        self._retry_at = 0.0

    def _write_register_pointer(self, register: int) -> None:
        self._bus.write_byte_data(self.ADDRESS, (register >> 8) & 0xFF, register & 0xFF)

    def _read(self, register: int, length: int) -> list[int]:
        self._write_register_pointer(register)
        return [int(self._bus.read_byte(self.ADDRESS)) for _ in range(length)]

    def _write(self, register: int, value: int) -> None:
        packed = (register & 0xFF) | ((value & 0xFF) << 8)
        self._bus.write_word_data(self.ADDRESS, (register >> 8) & 0xFF, packed)

    def initialize(self) -> bool:
        self.close()
        try:
            from gpiozero import InputDevice, OutputDevice
            from smbus import SMBus

            # InputDevice avoids gpiozero's event-monitor thread; polling is a
            # better fit for the launcher's single event loop and clean retries.
            self._reset = OutputDevice(22, active_high=True, initial_value=False)
            self._interrupt = InputDevice(27, pull_up=False)
            self._bus = SMBus(1)
            self._reset.on()
            time.sleep(0.1)
            self._reset.off()
            time.sleep(0.1)
            self._reset.on()
            time.sleep(0.1)
            raw_version = self._read(self.VERSION_REGISTER, 4)
            self.version = bytes(raw_version).decode("ascii", errors="replace")
            self.available = True
            self.last_error = ""
            LOGGER.info("GT1151 touch ready (version %r)", self.version)
            return True
        except Exception as exc:  # Hardware/library errors vary by Pi OS release.
            self.last_error = f"{type(exc).__name__}: {exc}"
            LOGGER.warning("Touch unavailable: %s", self.last_error)
            self.close()
            self._retry_at = time.monotonic() + self.retry_seconds
            return False

    def poll(self, now: float | None = None) -> TouchPoint | None:
        now = time.monotonic() if now is None else now
        if not self.available:
            if now >= self._retry_at:
                self.initialize()
            return None
        try:
            if self._interrupt is not None and self._interrupt.value != 0:
                return None
            status = self._read(self.STATUS_REGISTER, 1)[0]
            if not status & 0x80:
                return None
            count = status & 0x0F
            if count < 1 or count > 5:
                self._write(self.STATUS_REGISTER, 0)
                return None
            point = self._read(self.POINTS_REGISTER, count * 8)
            self._write(self.STATUS_REGISTER, 0)
            raw_x = (point[2] << 8) | point[1]
            raw_y = (point[4] << 8) | point[3]
            size = (point[6] << 8) | point[5]
            mapped = map_raw_touch(raw_x, raw_y)
            return TouchPoint(mapped.x, mapped.y, size)
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            LOGGER.warning("Touch read failed: %s", self.last_error)
            self.close()
            self._retry_at = now + self.retry_seconds
            return None

    def close(self) -> None:
        self.available = False
        for device in (self._interrupt, self._reset):
            if device is not None:
                try:
                    device.close()
                except Exception:
                    pass
        if self._bus is not None:
            try:
                self._bus.close()
            except Exception:
                pass
        self._interrupt = self._reset = self._bus = None


class NullTouch:
    available = False
    last_error = "preview mode"

    def initialize(self) -> bool:
        return False

    def poll(self, now: float | None = None) -> TouchPoint | None:
        return None

    def close(self) -> None:
        pass
