"""Shared monochrome UI primitives and touch targets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

SCREEN_WIDTH = 250
SCREEN_HEIGHT = 122
NAV_TOP = 98
CONTENT_HEIGHT = NAV_TOP

WHITE = 255
BLACK = 0


@dataclass(frozen=True)
class Rect:
    x0: int
    y0: int
    x1: int
    y1: int

    def contains(self, x: int, y: int) -> bool:
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1


BACK_RECT = Rect(0, NAV_TOP, 68, SCREEN_HEIGHT - 1)
HOME_RECT = Rect(181, NAV_TOP, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1)
PAGE_PREV_RECT = Rect(72, NAV_TOP + 2, 101, SCREEN_HEIGHT - 3)
PAGE_NEXT_RECT = Rect(149, NAV_TOP + 2, 178, SCREEN_HEIGHT - 3)


def _font_path(name: str) -> str | None:
    candidates = {
        "display": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf",
        ],
        "body": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ],
        "bold": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ],
        "mono": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/System/Library/Fonts/Supplemental/Courier New.ttf",
        ],
    }
    for candidate in candidates[name]:
        if Path(candidate).exists():
            return candidate
    return None


def font(role: str = "body", size: int = 10):
    path = _font_path(role)
    return ImageFont.truetype(path, size) if path else ImageFont.load_default()


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("1", (SCREEN_WIDTH, SCREEN_HEIGHT), WHITE)
    return image, ImageDraw.Draw(image)


def text_size(draw: ImageDraw.ImageDraw, text: str, selected_font) -> Tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=selected_font)
    return box[2] - box[0], box[3] - box[1]


def centered_text(
    draw: ImageDraw.ImageDraw,
    rect: Rect,
    text: str,
    selected_font,
    fill: int = BLACK,
) -> None:
    width, height = text_size(draw, text, selected_font)
    x = rect.x0 + ((rect.x1 - rect.x0 + 1) - width) // 2
    y = rect.y0 + ((rect.y1 - rect.y0 + 1) - height) // 2 - 1
    draw.text((x, y), text, font=selected_font, fill=fill)


def button(
    draw: ImageDraw.ImageDraw,
    rect: Rect,
    label: str,
    *,
    selected: bool = False,
    disabled: bool = False,
    selected_font=None,
) -> None:
    selected_font = selected_font or font("bold", 9)
    background = BLACK if selected else WHITE
    foreground = WHITE if selected else BLACK
    draw.rectangle((rect.x0, rect.y0, rect.x1, rect.y1), fill=background, outline=BLACK)
    centered_text(draw, rect, label, selected_font, foreground)


def draw_header(draw: ImageDraw.ImageDraw, title: str, eyebrow: str = "") -> None:
    if eyebrow:
        draw.text((4, 1), eyebrow.upper(), font=font("mono", 6), fill=BLACK)
    draw.text((4, 8 if eyebrow else 3), title.upper(), font=font("display", 12), fill=BLACK)
    draw.line((0, 22, SCREEN_WIDTH - 1, 22), fill=BLACK)


def draw_nav(
    draw: ImageDraw.ImageDraw,
    *,
    can_go_back: bool,
    at_home: bool,
    launcher_page: tuple[int, int] | None = None,
) -> None:
    """A fixed bottom rail: spatially stable on every screen."""
    draw.rectangle((0, NAV_TOP, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1), fill=WHITE, outline=BLACK)
    button(draw, BACK_RECT, "< BACK", disabled=not can_go_back, selected_font=font("bold", 9))
    if launcher_page and launcher_page[1] > 1:
        page, pages = launcher_page
        button(draw, PAGE_PREV_RECT, "<", selected_font=font("bold", 11))
        centered_text(draw, Rect(103, NAV_TOP, 147, SCREEN_HEIGHT - 1), f"{page}/{pages}", font("mono", 7))
        button(draw, PAGE_NEXT_RECT, ">", selected_font=font("bold", 11))
    else:
        draw.text((78, 104), "RPi / EINK", font=font("mono", 7), fill=BLACK)
    button(draw, HOME_RECT, "HOME", selected=at_home, selected_font=font("bold", 9))


def fit_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max(1, max_chars - 1)] + "…"
