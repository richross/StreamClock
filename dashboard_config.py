import json
import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


DEFAULT_MESSAGES = (
    "Make room for one good thing today.",
    "Small steps still move you forward.",
    "Take a moment to notice something good.",
)


@dataclass(frozen=True)
class DashboardConfig:
    location_name: str = ""
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    temperature_unit: str = "celsius"
    messages: tuple[str, ...] = DEFAULT_MESSAGES
    night_start: int = 21 * 60
    night_end: int = 7 * 60

    @property
    def weather_enabled(self):
        return self.latitude is not None and self.longitude is not None


def _coordinate(value, name, limit):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(value) or not -limit <= value <= limit:
        raise ValueError(f"{name} must be between {-limit} and {limit}")
    return float(value)


def _minute(value, name):
    if not isinstance(value, str):
        raise ValueError(f"{name} must use HH:MM")
    parts = value.split(":")
    if len(parts) != 2 or any(len(part) != 2 or not part.isascii()
                              or not part.isdigit() for part in parts):
        raise ValueError(f"{name} must use HH:MM")
    hour, minute = map(int, parts)
    if hour > 23 or minute > 59:
        raise ValueError(f"{name} must be a valid time")
    return hour * 60 + minute


def load_config(path: Path) -> DashboardConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a JSON object")
    allowed = {"location_name", "latitude", "longitude", "timezone",
               "temperature_unit", "messages", "night_start", "night_end"}
    if data.keys() - allowed:
        raise ValueError(f"Unknown configuration keys: {', '.join(sorted(data.keys() - allowed))}")
    latitude, longitude = data.get("latitude"), data.get("longitude")
    if (latitude is None) != (longitude is None):
        raise ValueError("Set both latitude and longitude, or leave both null")
    if latitude is not None:
        latitude = _coordinate(latitude, "latitude", 90)
        longitude = _coordinate(longitude, "longitude", 180)
    timezone = data.get("timezone")
    if timezone is not None and (
        not isinstance(timezone, str) or not timezone.strip() or len(timezone) > 80
    ):
        raise ValueError("timezone must be a nonempty IANA timezone name")
    if latitude is not None and timezone is None:
        raise ValueError("Configured weather requires an explicit timezone matching the Pi")
    location_name = data.get("location_name", "")
    if not isinstance(location_name, str) or len(location_name) > 40:
        raise ValueError("location_name must be text of at most 40 characters")
    unit = data.get("temperature_unit", "celsius")
    if unit not in ("celsius", "fahrenheit"):
        raise ValueError("temperature_unit must be celsius or fahrenheit")
    messages = data.get("messages", list(DEFAULT_MESSAGES))
    if not isinstance(messages, list) or not messages or any(
        not isinstance(message, str) or not message.strip() or len(message) > 90
        or "\n" in message or "\r" in message
        for message in messages
    ):
        raise ValueError("messages must contain nonempty single-line strings of at most 90 characters")
    start = _minute(data.get("night_start", "21:00"), "night_start")
    end = _minute(data.get("night_end", "07:00"), "night_end")
    if start == end:
        raise ValueError("night_start and night_end must be different")
    return DashboardConfig(location_name.strip(), latitude, longitude, timezone,
                           unit, tuple(message.strip() for message in messages), start, end)


def daily_message(config: DashboardConfig, day: date) -> str:
    return config.messages[day.toordinal() % len(config.messages)]


def scheduled_night(config: DashboardConfig, now: datetime) -> bool:
    minute = now.hour * 60 + now.minute
    if config.night_start > config.night_end:
        return minute >= config.night_start or minute < config.night_end
    return config.night_start <= minute < config.night_end
