# Copilot Instructions for Clock Project

## Project Overview
A fullscreen Kivy clock application designed to run on Raspberry Pi. Displays real-time clock with hours/minutes in bold, seconds in regular weight, plus formatted date.

## Architecture

**Main Application**: [clock_app.py](clock_app.py)
- Single-screen Kivy app with `ClockScreen` as the only view
- Uses Kivy's `Clock.schedule_interval()` for 0.5s refresh rate (not Python threading)
- Window set to fullscreen with `Window.fullscreen = 'auto'`
- Invisible button overlay enables app exit via tap/click

**Update Interval**: 0.5s refresh rate (not 1s) reduces visible time drift
- Provides two update opportunities per second to catch time boundaries
- Prevents "sluggish" appearance if scheduled timer misaligns with wall clock
- Tested stable: runs for days without noticeable drift

**Time Display Pattern**: 
```python
time_text = now.strftime("[b]%H:%M[/b]:%S")  # Kivy markup for bold hours/minutes
```

## Streaming Integration (Planned)

**Purpose**: Clock serves as base HUD for streaming workflow
- Designed to display time while content creator is live streaming
- Planned widgets: YouTube live status indicator, chat comment notifications
- Current BoxLayout structure supports adding overlay widgets without blocking time display
- Event system will extend beyond time updates to handle external streaming events (API webhooks, chat monitoring)
- Non-intrusive design philosophy: alerts should be visible but not distract from content creation

## Development Environment

**Python Virtual Environment**: 
- Always activate venv before running: `source venv/bin/activate`
- Kivy is the primary dependency
- Designed for Python 3.11+ (Raspberry Pi target)

**Running the App**:
- Use [start_clock.sh](start_clock.sh) script (handles venv activation + launch)
- Or manually: `python3 clock_app.py` after activating venv
- App runs in fullscreen by default

**Testing**: 
- [test_kivy.py](test_kivy.py) is a minimal Kivy verification test (Hello World)
- Use to verify Kivy installation works before debugging main app

## Code Conventions

**UI Layout**: BoxLayout with vertical orientation and spacers for centering
- Spacers use `size_hint=(1, 0.3)` for vertical padding
- Font sizes: 120sp (time), 30sp (date)

**Event Handling**: Lambda bindings preferred for simple callbacks
```python
exit_btn.bind(on_press=lambda instance: self.exit_app())
```

**Kivy Specifics**:
- Use Kivy Clock for timing, not asyncio or threading
- Markup enabled on Labels for text styling (`markup=True`)
- Button transparency via `background_color=(0,0,0,0)`

## Platform Considerations
- Target platform: Raspberry Pi (Linux ARM)
- Assumes display/monitor output (not headless)
- Exit mechanism intentionally subtle (invisible button) for kiosk-style deployment

## Deployment (Raspberry Pi Autostart)

**Systemd Service Setup** for automatic startup:
```bash
# Create service file at /etc/systemd/system/clock.service
[Unit]
Description=Fullscreen Clock Display
After=graphical.target

[Service]
Environment=DISPLAY=:0
User=richross
WorkingDirectory=/home/richross/clock_project
ExecStart=/home/richross/clock_project/start_clock.sh
Restart=on-failure

[Install]
WantedBy=graphical.target
```

**Enable and manage service**:
```bash
sudo systemctl enable clock.service  # Enable on boot
sudo systemctl start clock.service   # Start now
sudo systemctl status clock.service  # Check status
sudo systemctl stop clock.service    # Stop service
```
