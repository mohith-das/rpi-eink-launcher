# RPi E-Ink Launcher

A touch-first, applet-based launcher for the Waveshare 2.13-inch Touch e-Paper HAT and Raspberry Pi Zero. It turns the small 250×122 display into a reusable device UI instead of a single-purpose status screen.

![MIT license](https://img.shields.io/badge/license-MIT-black)
![Python](https://img.shields.io/badge/python-3.10%2B-black)

## Included applets

- **Pi Info** preserves the original auto-scrolling clock, weather, system, Wi-Fi, IP, and SSH views. Tap a tab or let it rotate every 20 seconds.
- **Pomodoro** starts a countdown as soon as a preset or custom duration is tapped. Presets remain fixed at the top: 25-minute Focus, 5-minute Short Break, 15-minute Long Break, and 50-minute Deep Focus.
- Custom Pomodoro durations can be added from 1–180 minutes, selected, started, and deleted. They persist in `~/.config/rpi-eink-launcher/timers.json`.

Every screen uses the same bottom navigation rail: **Back** on the left and **Home** on the right. A running timer keeps time when you leave the applet and supports pause, resume, and timer selection.

## Hardware support

Target hardware: [Waveshare 2.13-inch Touch e-Paper HAT](https://www.waveshare.com/2.13inch-Touch-e-Paper-HAT-with-case.htm).

- Display: 250×122 black/white e-paper over SPI, including partial refresh.
- Touch: GT1151 capacitive controller over I²C at address `0x14`, reset on BCM GPIO 22 and interrupt on BCM GPIO 27.
- Backlight: **none**. E-paper is reflective and needs ambient light; there is no backlight to enable in software.

The launcher retries the touch controller automatically. If touch is disconnected, it shows the launcher briefly and then opens Pi Info so the display remains useful. Pressing Home works as soon as touch reconnects.

## Install

Enable SPI and I²C in `sudo raspi-config`, then reboot. On Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y python3-pil python3-gpiozero python3-spidev python3-smbus
git clone https://github.com/mohith-das/rpi-eink-launcher.git ~/rpi-eink-launcher
cd ~/rpi-eink-launcher
python3 launcher.py --touch-test
```

Install the boot service:

```bash
sudo cp systemd/rpi-eink-launcher.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rpi-eink-launcher.service
systemctl status rpi-eink-launcher.service
```

Useful diagnostics:

```bash
journalctl -u rpi-eink-launcher.service -n 100 --no-pager
python3 launcher.py --touch-test
python3 launcher.py --preview preview
```

If `--touch-test` reports `OSError: [Errno 5] Input/output error`, I²C is enabled but the controller is not answering. Power off the Pi and reseat the HAT so the 40-pin connector—especially physical pins 3 and 5—has firm contact. The display can still work because it uses different SPI pins.

## Add an applet

The launcher shell owns display refresh, touch mapping, Home, and Back. Applets own only their state and content.

1. Add a class under `rpi_eink_launcher/applets/` that implements `Applet` from `applets/base.py`.
2. Give it a unique `AppletMeta` id, title, and launcher subtitle.
3. Implement `render()`, `handle_touch()`, and optionally `tick()`, `back()`, and lifecycle hooks.
4. Register one instance in `build_registry()` in `shell.py`.

The shell discovers registered applets for launcher cards and automatically adds launcher pages after four applets, so its navigation code does not change as the collection grows.

## Refresh behavior

Screen transitions use a full refresh. Countdown seconds use partial refresh to avoid distracting full-screen flashes, followed by a full refresh every 60 partial updates to control ghosting and protect display quality.

## License

[MIT](LICENSE)
