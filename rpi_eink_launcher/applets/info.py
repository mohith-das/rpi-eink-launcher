"""The original scrolling status display, packaged as a launcher applet."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import urllib.parse
import urllib.request
from PIL import Image

from .base import Applet, AppletMeta
from ..ui import BLACK, CONTENT_HEIGHT, Rect, button, canvas, fit_text, font


def _command(args: list[str], timeout: float = 4) -> str:
    try:
        return subprocess.check_output(args, text=True, timeout=timeout, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _cpu_temp() -> str:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", encoding="utf-8") as source:
            return f"{float(source.read()) / 1000:.1f}C"
    except (OSError, ValueError):
        return "N/A"


def _memory() -> str:
    values = _command(["free", "-m"]).splitlines()
    try:
        fields = values[1].split()
        return f"{fields[2]}/{fields[1]} MB"
    except (IndexError, ValueError):
        return "N/A"


def _disk() -> str:
    values = _command(["df", "-h", "/"]).splitlines()
    try:
        fields = values[1].split()
        return f"{fields[2]}/{fields[1]} ({fields[4]})"
    except IndexError:
        return "N/A"


def _load_average() -> str:
    try:
        with open("/proc/loadavg", encoding="utf-8") as source:
            return " ".join(source.read().split()[:3])
    except OSError:
        return "N/A"


def _ip_address() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "No IP"
    finally:
        sock.close()


def _weather() -> str:
    location = os.getenv("EINK_WEATHER_LOCATION", "Buffalo")
    encoded = urllib.parse.quote(location)
    try:
        with urllib.request.urlopen(f"https://wttr.in/{encoded}?format=j1", timeout=4) as response:
            current = json.loads(response.read().decode())["current_condition"][0]
        condition = current["weatherDesc"][0]["value"]
        return f"{location}: {current['temp_F']}F {condition}"
    except (OSError, KeyError, IndexError, json.JSONDecodeError):
        return f"{location}: weather unavailable"


class InfoApplet(Applet):
    meta = AppletMeta("info", "Pi Info", "Clock, system, network")
    tabs = ("CLOCK", "SYSTEM", "NETWORK")

    def __init__(self, tab_seconds: int = 20) -> None:
        self.tab = 0
        self.tab_seconds = tab_seconds
        self.next_tab_at = 0.0
        self._weather_value = "Loading weather…"
        self._weather_updated_at = 0.0

    def on_enter(self, now: float) -> None:
        self.next_tab_at = now + self.tab_seconds

    def tick(self, now: float) -> bool:
        if now >= self.next_tab_at:
            self.tab = (self.tab + 1) % len(self.tabs)
            self.next_tab_at = now + self.tab_seconds
            return True
        return False

    def _refresh_weather(self, now: float) -> None:
        if now - self._weather_updated_at > 900:
            self._weather_value = _weather()
            self._weather_updated_at = now

    def render(self, now: float) -> Image.Image:
        image, draw = canvas()
        tab_width = 250 // len(self.tabs)
        for index, name in enumerate(self.tabs):
            rect = Rect(index * tab_width, 0, (index + 1) * tab_width - 1, 18)
            button(draw, rect, name, selected=index == self.tab, selected_font=font("bold", 7))

        if self.tab == 0:
            self._refresh_weather(now)
            draw.text((6, 23), time.strftime("%H:%M"), font=font("display", 28), fill=BLACK)
            draw.text((106, 26), time.strftime("%A"), font=font("bold", 11), fill=BLACK)
            draw.text((106, 42), time.strftime("%b %d, %Y"), font=font("body", 9), fill=BLACK)
            draw.line((5, 59, 244, 59), fill=BLACK)
            draw.text((6, 64), fit_text(self._weather_value, 40), font=font("body", 9), fill=BLACK)
            draw.text((6, 80), time.strftime("%Z  UTC%z"), font=font("mono", 8), fill=BLACK)
        elif self.tab == 1:
            uptime = _command(["uptime", "-p"]) or "N/A"
            rows = [
                ("TEMP", _cpu_temp()),
                ("MEM", _memory()),
                ("DISK", _disk()),
                ("LOAD", _load_average()),
                ("UP", uptime.removeprefix("up ")),
            ]
            for index, (label, value) in enumerate(rows):
                y = 23 + index * 14
                draw.text((6, y), label, font=font("mono", 8), fill=BLACK)
                draw.text((49, y), fit_text(value, 31), font=font("body", 9), fill=BLACK)
        else:
            wifi = _command(["iwgetid", "-r"]) or "Not connected"
            sessions = [line for line in _command(["who"]).splitlines() if line]
            draw.text((6, 25), "WIFI", font=font("mono", 8), fill=BLACK)
            draw.text((49, 24), fit_text(wifi, 26), font=font("bold", 10), fill=BLACK)
            draw.text((6, 42), "IP", font=font("mono", 8), fill=BLACK)
            draw.text((49, 41), _ip_address(), font=font("body", 10), fill=BLACK)
            draw.line((5, 57, 244, 57), fill=BLACK)
            draw.text((6, 62), "SSH", font=font("mono", 8), fill=BLACK)
            if sessions:
                for index, session in enumerate(sessions[:2]):
                    draw.text((49, 61 + index * 13), fit_text(session, 29), font=font("body", 8), fill=BLACK)
            else:
                draw.text((49, 61), "No active sessions", font=font("body", 8), fill=BLACK)
        return image

    def handle_touch(self, x: int, y: int, now: float) -> bool:
        if y <= 20:
            new_tab = min(len(self.tabs) - 1, x // (250 // len(self.tabs)))
            if new_tab != self.tab:
                self.tab = new_tab
                self.next_tab_at = now + self.tab_seconds
                return True
        return False
