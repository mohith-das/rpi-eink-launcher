from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rpi_eink_launcher.applets import AppletMeta, AppletRegistry, InfoApplet, PomodoroApplet
from rpi_eink_launcher.shell import LauncherShell
from rpi_eink_launcher.touch import NullTouch, map_raw_touch
from rpi_eink_launcher.ui import HOME_RECT, PAGE_NEXT_RECT, SCREEN_HEIGHT, SCREEN_WIDTH


class TouchMappingTests(unittest.TestCase):
    def test_maps_portrait_touch_to_rotated_landscape(self) -> None:
        self.assertEqual((map_raw_touch(121, 0).x, map_raw_touch(121, 0).y), (0, 0))
        self.assertEqual((map_raw_touch(0, 249).x, map_raw_touch(0, 249).y), (249, 121))

    def test_clamps_out_of_range_values(self) -> None:
        point = map_raw_touch(-20, 999)
        self.assertEqual((point.x, point.y), (SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1))


class PomodoroTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "timers.json"
        self.applet = PomodoroApplet(self.path)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_preset_touch_starts_countdown_immediately(self) -> None:
        self.assertTrue(self.applet.handle_touch(30, 40, 100.0))
        self.assertEqual(self.applet.view, "timer")
        self.assertEqual(self.applet.timer_minutes, 25)
        self.assertEqual(self.applet.remaining_seconds(101.0), 1499)

    def test_pause_and_resume_preserve_remaining_time(self) -> None:
        self.applet.start_timer("Focus", 25, 100.0)
        self.applet.handle_touch(50, 80, 110.0)
        paused = self.applet.remaining_seconds(200.0)
        self.assertEqual(paused, 1490)
        self.applet.handle_touch(50, 80, 200.0)
        self.assertEqual(self.applet.remaining_seconds(205.0), 1485)

    def test_custom_timer_is_persisted_and_can_be_deleted(self) -> None:
        self.applet.handle_touch(200, 75, 100.0)  # Add.
        self.applet.edit_minutes = 42
        self.applet.handle_touch(100, 82, 100.0)  # Save.
        self.assertEqual(PomodoroApplet(self.path).custom_minutes, [42])
        self.applet.handle_touch(232, 75, 100.0)  # Delete prompt.
        self.applet.handle_touch(180, 80, 100.0)  # Confirm.
        self.assertEqual(PomodoroApplet(self.path).custom_minutes, [])

    def test_all_views_render_at_panel_resolution(self) -> None:
        for view in ("select", "editor"):
            self.applet.view = view
            self.assertEqual(self.applet.render(100.0).size, (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.applet.start_timer("Focus", 25, 100.0)
        self.assertEqual(self.applet.render(100.0).size, (SCREEN_WIDTH, SCREEN_HEIGHT))


class ShellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        registry = AppletRegistry()
        self.info = registry.register(InfoApplet())
        registry.register(PomodoroApplet(Path(self.temporary.name) / "timers.json"))
        self.shell = LauncherShell(registry, NullTouch())

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_launcher_card_opens_registered_applet(self) -> None:
        self.assertTrue(self.shell.handle_touch(20, 40, 10.0))
        self.assertIs(self.shell.active, self.info)

    def test_home_button_always_returns_to_launcher(self) -> None:
        self.shell.open_applet(self.info, 10.0)
        self.shell.handle_touch(HOME_RECT.x0 + 2, HOME_RECT.y0 + 2, 11.0)
        self.assertIsNone(self.shell.active)

    def test_registry_automatically_paginates_after_four_applets(self) -> None:
        registry = AppletRegistry()
        applets = []
        for index in range(5):
            applet = InfoApplet()
            applet.meta = AppletMeta(f"app-{index}", f"App {index}", "Test")
            applets.append(registry.register(applet))
        shell = LauncherShell(registry, NullTouch())
        self.assertEqual(shell.launcher_pages, 2)
        shell.handle_touch(PAGE_NEXT_RECT.x0 + 2, PAGE_NEXT_RECT.y0 + 2, 10.0)
        self.assertEqual(shell.launcher_page, 1)
        shell.handle_touch(20, 40, 11.0)
        self.assertIs(shell.active, applets[4])


if __name__ == "__main__":
    unittest.main()
