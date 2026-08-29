#!/usr/bin/env python3
"""RPi E-Ink Launcher entry point."""

from __future__ import annotations

import argparse
import logging
import signal
import time
from pathlib import Path

from rpi_eink_launcher.applets import InfoApplet, PomodoroApplet
from rpi_eink_launcher.display import EInkDisplay, PreviewDisplay
from rpi_eink_launcher.shell import LauncherShell, build_registry, run
from rpi_eink_launcher.touch import GT1151Touch, NullTouch
from rpi_eink_launcher.ui import draw_nav


def render_previews(output_dir: Path) -> None:
    display = PreviewDisplay(output_dir)
    display.initialize()
    now = time.monotonic()
    registry = build_registry(output_dir / "config")
    shell = LauncherShell(registry, NullTouch())
    display.show(shell.render_launcher(now), name="01-launcher.png")

    info = registry.get("info")
    for index in range(3):
        info.tab = index
        image = info.render(now)
        from PIL import ImageDraw
        draw_nav(ImageDraw.Draw(image), can_go_back=True, at_home=False)
        display.show(image, name=f"02-info-{index + 1}.png")

    pomodoro = registry.get("pomodoro")
    image = pomodoro.render(now)
    from PIL import ImageDraw
    draw_nav(ImageDraw.Draw(image), can_go_back=True, at_home=False)
    display.show(image, name="03-pomodoro-select.png")
    pomodoro.view = "editor"
    image = pomodoro.render(now)
    draw_nav(ImageDraw.Draw(image), can_go_back=True, at_home=False)
    display.show(image, name="04-pomodoro-custom.png")
    pomodoro.start_timer("Focus", 25, now)
    image = pomodoro.render(now + 61)
    draw_nav(ImageDraw.Draw(image), can_go_back=True, at_home=False)
    display.show(image, name="05-pomodoro-running.png")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path, help="render all screens to PNG files and exit")
    parser.add_argument("--touch-test", action="store_true", help="initialize the GT1151 and print its status")
    parser.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.preview:
        render_previews(args.preview)
        return 0
    if args.touch_test:
        touch = GT1151Touch()
        ready = touch.initialize()
        print(f"ready={ready} version={touch.version!r} error={touch.last_error!r}")
        touch.close()
        return 0 if ready else 1
    def request_stop(_signum, _frame) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    try:
        run(EInkDisplay())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Launcher stopped cleanly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
