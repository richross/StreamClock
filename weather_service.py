import json
import logging
import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from dashboard_config import DashboardConfig, scheduled_night


logger = logging.getLogger(__name__)
REFRESH_SECONDS = 15 * 60
RETRY_SECONDS = 5 * 60
STALE_SECONDS = 30 * 60
REQUEST_TIMEOUT = 10

CONDITIONS = {
    0: "Clear sky", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Freezing fog", 51: "Light drizzle", 53: "Drizzle",
    55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain",
    67: "Freezing rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow",
    77: "Snow grains", 80: "Light showers", 81: "Rain showers",
    82: "Heavy showers", 85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Storm with hail", 99: "Storm with hail",
}


@dataclass(frozen=True)
class WeatherSnapshot:
    fetched_at: float
    observed_at: float
    temperature: float
    weather_code: int
    forecast_date: str
    high: float | None
    low: float | None
    sunrise: float | None
    sunset: float | None


@dataclass(frozen=True)
class WeatherState:
    snapshot: WeatherSnapshot | None = None
    loading: bool = False
    failed: bool = False
    cache_error: bool = False


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Invalid weather {name}")
    return float(value)


def _timestamp(value, name):
    number = _number(value, name)
    try:
        datetime.fromtimestamp(number)
    except (ValueError, OverflowError, OSError) as error:
        raise ValueError(f"Invalid weather {name}") from error
    if number <= 0:
        raise ValueError(f"Invalid weather {name}")
    return number


def _optional_number(value, name):
    return None if value is None else _number(value, name)


def parse_weather(data, config: DashboardConfig, now: datetime) -> WeatherSnapshot:
    if not isinstance(data, dict):
        raise ValueError("Weather response is not an object")
    current, daily = data.get("current"), data.get("daily")
    units = data.get("current_units")
    daily_units = data.get("daily_units")
    if not all(isinstance(item, dict) for item in (current, daily, units, daily_units)):
        raise ValueError("Weather response is missing current/daily data or units")
    expected_unit = "\u00b0C" if config.temperature_unit == "celsius" else "\u00b0F"
    if (units.get("temperature_2m") != expected_unit
            or any(daily_units.get(key) != expected_unit
                   for key in ("temperature_2m_max", "temperature_2m_min"))):
        raise ValueError("Weather units do not match configuration")
    offset = now.astimezone().utcoffset().total_seconds()
    if _number(data.get("utc_offset_seconds"), "timezone offset") != offset:
        raise ValueError("Weather timezone does not match the system clock")
    observed = _timestamp(current.get("time"), "observation time")
    if observed > now.timestamp() + REQUEST_TIMEOUT or now.timestamp() - observed > STALE_SECONDS:
        raise ValueError("Weather observation is outdated or in the future")
    code = current.get("weather_code")
    if isinstance(code, bool) or not isinstance(code, int) or code not in CONDITIONS:
        raise ValueError("Unrecognized weather condition code")
    keys = ("time", "temperature_2m_max", "temperature_2m_min", "sunrise", "sunset")
    arrays = [daily.get(key) for key in keys[:3]]
    if any(not isinstance(array, list) or len(array) != 1 for array in arrays):
        raise ValueError("Expected exactly one daily forecast")
    forecast_day = datetime.fromtimestamp(_timestamp(arrays[0][0], "forecast date")).date()
    if forecast_day != now.date():
        raise ValueError("Weather forecast is not for the current local day")
    high, low = (_optional_number(arrays[index][0], keys[index]) for index in (1, 2))
    if high is not None and low is not None and high < low:
        raise ValueError("Weather high is lower than low")
    try:
        for key in keys[3:]:
            array = daily.get(key)
            if not isinstance(array, list) or len(array) != 1:
                raise ValueError(f"Missing or invalid {key}")
            arrays.append(array)
        sunrise, sunset = (
            None if arrays[index][0] is None else _timestamp(arrays[index][0], keys[index])
            for index in (3, 4)
        )
        if sunrise is not None and sunset is not None and (
            sunrise >= sunset or any(datetime.fromtimestamp(value).date() != now.date()
                                     for value in (sunrise, sunset))
        ):
            raise ValueError("Sun times do not describe the current local day")
    except ValueError:
        logger.warning("Invalid sun times; using the scheduled night palette", exc_info=True)
        sunrise = sunset = None
    return WeatherSnapshot(now.timestamp(), observed,
                           _number(current.get("temperature_2m"), "temperature"),
                           code, forecast_day.isoformat(), high, low, sunrise, sunset)


def night_palette(config: DashboardConfig, now: datetime, state: WeatherState) -> bool:
    snapshot = state.snapshot
    if (snapshot is not None and snapshot.forecast_date == now.date().isoformat()
            and snapshot.sunrise is not None and snapshot.sunset is not None):
        return now.timestamp() < snapshot.sunrise or now.timestamp() >= snapshot.sunset
    return scheduled_night(config, now)


def weather_status(state: WeatherState, now: datetime) -> str:
    snapshot = state.snapshot
    if snapshot is None:
        return "Weather unavailable" if state.failed else "Loading weather"
    updated = datetime.fromtimestamp(snapshot.fetched_at)
    timestamp = updated.strftime("%H:%M" if updated.date() == now.date() else "%b %d %H:%M")
    stale = (now.timestamp() - min(snapshot.fetched_at, snapshot.observed_at) >= STALE_SECONDS
             or snapshot.fetched_at > now.timestamp() + REQUEST_TIMEOUT)
    prefix = "Last known / " if state.failed else ""
    prefix += "Stale / " if stale else ""
    if state.cache_error:
        prefix += "Cache error / "
    return f"{prefix}updated {timestamp}"


def _cache_identity(config):
    return {"latitude": config.latitude, "longitude": config.longitude,
            "timezone": config.timezone, "unit": config.temperature_unit}


def read_cache(path: Path, config: DashboardConfig, now: datetime) -> WeatherSnapshot | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Weather cache is not an object")
    if data.get("identity") != _cache_identity(config):
        logger.info("Ignoring weather cache for a different location, timezone or unit")
        return None
    raw = data.get("snapshot")
    if not isinstance(raw, dict) or set(raw) != set(WeatherSnapshot.__dataclass_fields__):
        raise ValueError("Invalid weather cache fields")
    fetched = _timestamp(raw["fetched_at"], "cached fetch time")
    observed = _timestamp(raw["observed_at"], "cached observation time")
    if fetched > now.timestamp() + REQUEST_TIMEOUT or observed > fetched + REQUEST_TIMEOUT:
        raise ValueError("Weather cache timestamps are in the future")
    code = raw["weather_code"]
    if isinstance(code, bool) or not isinstance(code, int) or code not in CONDITIONS:
        raise ValueError("Invalid cached weather code")
    try:
        day = datetime.strptime(raw["forecast_date"], "%Y-%m-%d").date()
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid cached forecast date") from error
    if day != datetime.fromtimestamp(fetched).date():
        raise ValueError("Cached forecast date does not match fetch date")
    high = _optional_number(raw["high"], "cached high")
    low = _optional_number(raw["low"], "cached low")
    if high is not None and low is not None and high < low:
        raise ValueError("Invalid cached forecast range")
    sunrise, sunset = (
        None if raw[key] is None else _timestamp(raw[key], f"cached {key}")
        for key in ("sunrise", "sunset")
    )
    if sunrise is not None and sunset is not None and (
        sunrise >= sunset or any(datetime.fromtimestamp(value).date() != day
                                 for value in (sunrise, sunset))
    ):
        raise ValueError("Invalid cached sun times")
    return WeatherSnapshot(fetched, observed, _number(raw["temperature"], "cached temperature"),
                           code, day.isoformat(), high, low, sunrise, sunset)


def write_cache(path: Path, config: DashboardConfig, snapshot: WeatherSnapshot):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    try:
        temporary.write_text(json.dumps({"identity": _cache_identity(config),
                                         "snapshot": asdict(snapshot)}), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class WeatherService:
    def __init__(self, config, cache_path, on_update, *, scheduler=None, request_factory=None):
        if scheduler is None:
            from kivy.clock import Clock
            scheduler = Clock
        if request_factory is None:
            from kivy.network.urlrequest import UrlRequest
            request_factory = UrlRequest
        self.config = config
        self.cache_path = cache_path
        self.on_update = on_update
        self.scheduler = scheduler
        self.request_factory = request_factory
        self.state = WeatherState()
        self.running = False
        self._active = False
        self._request = None
        self._event = None

    def start(self):
        if self.running or not self.config.weather_enabled:
            return
        self.running = True
        try:
            snapshot = read_cache(self.cache_path, self.config, datetime.now())
            self.state = WeatherState(snapshot=snapshot, loading=True)
        except (OSError, ValueError, UnicodeError):
            logger.exception("Cannot read weather cache")
            self.state = WeatherState(loading=True, cache_error=True)
        self.on_update(self.state)
        self.refresh()

    def refresh(self, _dt=0):
        if not self.running or self._active:
            return
        if self._event is not None:
            self._event.cancel()
            self._event = None
        self._active = True
        query = urlencode({
            "latitude": self.config.latitude, "longitude": self.config.longitude,
            "timezone": self.config.timezone, "temperature_unit": self.config.temperature_unit,
            "timeformat": "unixtime", "forecast_days": 1,
            "current": "temperature_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,sunrise,sunset",
        })
        try:
            request = self.request_factory(
                f"https://api.open-meteo.com/v1/forecast?{query}",
                on_success=self._success, on_failure=self._failure, on_error=self._failure,
                timeout=REQUEST_TIMEOUT, decode=True,
            )
            if self._active:
                self._request = request
        except (OSError, ValueError):
            logger.exception("Cannot start weather request")
            self._failure(None, "request startup error")

    def _success(self, request, result):
        if not self.running:
            return
        try:
            snapshot = parse_weather(result, self.config, datetime.now())
        except ValueError:
            logger.exception("Invalid weather response")
            self._failure(request, "invalid response")
            return
        cache_error = False
        try:
            write_cache(self.cache_path, self.config, snapshot)
        except OSError:
            logger.exception("Cannot write weather cache")
            cache_error = True
        self.state = WeatherState(snapshot=snapshot, cache_error=cache_error)
        self._finish(REFRESH_SECONDS)

    def _failure(self, request, error):
        if not self.running:
            return
        logger.warning("Weather request failed: %s", error)
        self.state = WeatherState(snapshot=self.state.snapshot, failed=True,
                                  cache_error=self.state.cache_error)
        self._finish(RETRY_SECONDS)

    def _finish(self, delay):
        self._active = False
        self._request = None
        if self.running:
            self._event = self.scheduler.schedule_once(self.refresh, delay)
        self.on_update(self.state)

    def stop(self):
        self.running = False
        if self._event is not None:
            self._event.cancel()
            self._event = None
        if self._request is not None:
            self._request.cancel()
            self._request = None
        self._active = False
