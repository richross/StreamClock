# StreamClock

A fullscreen, clock-first Kivy dashboard for Raspberry Pi 3B+. It shows a
24-hour clock with seconds, the full date, modeled weather from Open-Meteo,
and one locally configured message per day. The navy/teal palette dims at
sunset and brightens at sunrise; an offline schedule is available as fallback.
Tap or click anywhere to exit, as in the original clock.

## Run on the Pi

Use the existing Python 3.11 virtual environment and launch script:

```bash
source venv/bin/activate
python3 -m pip install -r requirements.txt
bash start_clock.sh
```

`start_clock.sh` retains its existing `/home/richross/clock_project` working
directory. If your checkout is elsewhere, activate its environment and run
`python3 clock_app.py` from that checkout instead. This app requires a graphical
desktop/display; existing autostart configuration does not need to change.

## Configure the dashboard

Copy `config.example.json` to `config.json` beside `clock_app.py`. The local
configuration is ignored by Git. Alternatively, set `STREAMCLOCK_CONFIG` to
the path of a JSON configuration file.

- Set `latitude` and `longitude` together, plus an explicit IANA `timezone`
  matching the Pi's system timezone, such as `Europe/London`. Coordinates
  are sent only to the weather provider; location is not inferred from IP.
- Give the weather card a short `location_name` (at most 40 characters).
- Set `temperature_unit` to `celsius` (default) or `fahrenheit`.
- Edit `messages`, a nonempty list of messages up to 90 characters each.
  One is selected deterministically per local calendar day, so restarting
  does not change today's selection. Messages wrap to at most three lines.
  Unusually wide text that cannot fit is visibly shortened with an ellipsis
  and an "edit config" notice, rather than silently clipped.
- Set `night_start` and `night_end` in `HH:MM` format for the fallback schedule,
  initially `21:00` and `07:00`. Sunrise/sunset for today's configured location
  take precedence, including cached sun times when offline. Past-day or
  invalid sun times use the fallback. This changes the rendered colors,
  **not the physical display backlight**.

With no configuration file, the clock, default messages and fallback dimming
work immediately; weather says "Weather not configured". Leave both coordinates
and timezone `null` for offline-only operation. Invalid configuration is logged,
shows "Configuration error - see log", and retains a usable default clock rather
than pretending the invalid settings were applied.

On the Pi, check the system timezone with `timedatectl`. Weather is rejected
with a logged error if the provider's UTC offset differs from the system clock.
Daily messages and date changes use the system's local calendar.

## Weather and offline behavior

Weather uses asynchronous Kivy requests, not the clock's update callback.
It requests current temperature/condition and today's high/low/sun times,
refreshes every 15 minutes after success, and retries after 5 minutes on failure.
Requests have a 10-second timeout and never overlap. The clock still updates
every 0.5 seconds.

- Before the first result: "Loading weather"; failed with no cache:
  "Weather unavailable".
- After failure with retained data: "Last known", with an update timestamp.
  Data is also marked "Stale" after 30 minutes, based on both fetch and
  observation time. A provider failure is not assumed to prove the network
  itself is offline.
- Prior-day readings include their date; prior-day high/low are never shown
  as today's forecast. A fresh request is triggered at local midnight.
- Validated readings are cached atomically in Kivy's writable `user_data_dir`
  as `weather-cache.json`. The cache is not reused for different coordinates,
  units or timezone. Cache read/write failures are logged and visible; a write
  failure does not discard a good live reading.

Weather data: [Open-Meteo](https://open-meteo.com/). Read the
[API documentation](https://open-meteo.com/en/docs) and
[terms](https://open-meteo.com/en/terms). The free endpoint is intended for
eligible non-commercial use; check licensing/subscription requirements for
monetized streaming or other commercial deployment. These are modeled weather
conditions, not readings from a local sensor.

## Display and checks

The layout is designed for 800 x 480 landscape and scales to larger landscape
displays, including 1280 x 720. The startup log records Kivy's actual window
dimensions. The original repository did not specify the physical resolution;
confirm it in the Pi's display settings. Fonts use window-relative pixel sizing
so display density does not independently enlarge the text beyond its region.

Run focused logic tests without opening a window:

```bash
source venv/bin/activate
python3 -m unittest test_dashboard
```

With a graphical display and Kivy available, exercise the real widget layouts
and clock/date transitions:

```bash
python3 -m unittest test_dashboard_ui
```

`test_kivy.py` remains the graphical installation smoke test. On the physical
Pi, check both palettes and display sizes, long labels/messages, degree symbols,
tap-to-exit, midnight and sun boundaries, slow/offline requests and recovery.
Compare CPU/memory with the original clock and perform an extended run before
relying on this as a kiosk. A desktop preview cannot establish Pi performance.
