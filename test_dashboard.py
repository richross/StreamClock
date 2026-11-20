import copy
import json
import tempfile
import unittest
from contextlib import nullcontext
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from dashboard_config import DashboardConfig, daily_message, load_config, scheduled_night
from weather_service import (
    REFRESH_SECONDS, RETRY_SECONDS, WeatherService, WeatherState,
    night_palette, parse_weather, read_cache, weather_status, write_cache,
)


def weather_response(now, unit="celsius"):
    degree = "\u00b0C" if unit == "celsius" else "\u00b0F"
    return {
        "utc_offset_seconds": now.astimezone().utcoffset().total_seconds(),
        "current_units": {"temperature_2m": degree},
        "daily_units": {"temperature_2m_max": degree, "temperature_2m_min": degree},
        "current": {"time": now.timestamp(), "temperature_2m": 18, "weather_code": 2},
        "daily": {
            "time": [now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()],
            "temperature_2m_max": [20], "temperature_2m_min": [12],
            "sunrise": [now.replace(hour=6, minute=30, second=0, microsecond=0).timestamp()],
            "sunset": [now.replace(hour=18, minute=0, second=0, microsecond=0).timestamp()],
        },
    }


class ConfigurationTests(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return load_config(path)

    def test_weather_requires_location_pair_and_explicit_timezone(self):
        for data in ({"latitude": 12}, {"longitude": 20},
                     {"latitude": 12, "longitude": 20},
                     {"latitude": True, "longitude": 20, "timezone": "UTC"},
                     {"latitude": 91, "longitude": 20, "timezone": "UTC"},
                     {"latitude": 12, "longitude": float("nan"), "timezone": "UTC"}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.load(data)
        config = self.load({"latitude": 0, "longitude": 0, "timezone": "UTC"})
        self.assertTrue(config.weather_enabled)

    def test_invalid_messages_units_and_schedule_are_rejected(self):
        for data in ({"messages": []}, {"messages": [" "]},
                     {"messages": ["x" * 91]}, {"messages": ["one\ntwo"]},
                     {"temperature_unit": "kelvin"}, {"night_start": "24:00"},
                     {"night_end": "7:00"}, {"night_end": "21:00"},
                     {"unexpected_setting": True}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.load(data)

    def test_message_selection_is_stable_and_changes_on_next_day(self):
        config = self.load({"messages": ["first", "second", "third"]})
        day = datetime(2026, 11, 20).date()
        self.assertEqual(daily_message(config, day), daily_message(config, day))
        self.assertNotEqual(daily_message(config, day), daily_message(config, day + timedelta(days=1)))
        self.assertEqual(daily_message(config, day), daily_message(config, day + timedelta(days=3)))

    def test_schedule_handles_overnight_and_nonovernight_boundaries(self):
        config = DashboardConfig()
        for hour, minute, expected in ((20, 59, False), (21, 0, True),
                                       (0, 0, True), (6, 59, True), (7, 0, False)):
            with self.subTest(hour=hour, minute=minute):
                self.assertEqual(scheduled_night(config, datetime(2026, 11, 20, hour, minute)), expected)
        daytime = replace(config, night_start=600, night_end=720)
        self.assertTrue(scheduled_night(daytime, datetime(2026, 11, 20, 10)))
        self.assertFalse(scheduled_night(daytime, datetime(2026, 11, 20, 12)))


class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 20, 14, 5)
        self.config = DashboardConfig(latitude=0, longitude=0, timezone="UTC")
        self.response = weather_response(self.now)
        self.snapshot = parse_weather(self.response, self.config, self.now)

    def test_temperature_units_and_timezone_must_match(self):
        fahrenheit = replace(self.config, temperature_unit="fahrenheit")
        self.assertEqual(parse_weather(weather_response(self.now, "fahrenheit"),
                                       fahrenheit, self.now).temperature, 18)
        with self.assertRaises(ValueError):
            parse_weather(self.response, fahrenheit, self.now)
        self.response["utc_offset_seconds"] += 3600
        with self.assertRaises(ValueError):
            parse_weather(self.response, self.config, self.now)

    def test_bad_missing_outdated_and_past_day_data_are_rejected(self):
        cases = [
            {"current": {"time": self.now.timestamp(), "temperature_2m": None, "weather_code": 0}},
            {"current": {"time": self.now.timestamp(), "temperature_2m": float("nan"), "weather_code": 0}},
            {"current": {"time": self.now.timestamp(), "temperature_2m": 18, "weather_code": True}},
            {"current": {"time": (self.now - timedelta(hours=2)).timestamp(),
                         "temperature_2m": 18, "weather_code": 0}},
            {"daily": {}}, {"current_units": {}},
        ]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_weather({**self.response, **changes}, self.config, self.now)
        with self.assertRaises(ValueError):
            parse_weather(self.response, self.config, self.now + timedelta(days=1))

    def test_invalid_or_missing_sun_times_keep_weather_and_fall_back(self):
        for sunrise, sunset in ((None, None), ("bad", 12), (100, 50)):
            data = copy.deepcopy(self.response)
            data["daily"]["sunrise"] = [sunrise]
            data["daily"]["sunset"] = [sunset]
            with self.subTest(sunrise=sunrise), (
                self.assertLogs("weather_service", level="WARNING")
                if sunrise is not None else nullcontext()
            ):
                snapshot = parse_weather(data, self.config, self.now)
            self.assertEqual(snapshot.temperature, 18)
            self.assertFalse(night_palette(self.config, self.now, WeatherState(snapshot)))
            self.assertTrue(night_palette(self.config, self.now.replace(hour=22), WeatherState(snapshot)))
        del self.response["daily"]["sunrise"]
        with self.assertLogs("weather_service", level="WARNING"):
            snapshot = parse_weather(self.response, self.config, self.now)
        self.assertIsNone(snapshot.sunrise)
        self.assertEqual(snapshot.temperature, 18)

    def test_sun_boundaries_and_next_day_schedule_fallback(self):
        state = WeatherState(self.snapshot, failed=True)
        self.assertTrue(night_palette(self.config, self.now.replace(hour=6, minute=29), state))
        self.assertFalse(night_palette(self.config, self.now.replace(hour=6, minute=30), state))
        self.assertFalse(night_palette(self.config, self.now.replace(hour=17, minute=59), state))
        self.assertTrue(night_palette(self.config, self.now.replace(hour=18, minute=0), state))
        self.assertFalse(night_palette(self.config, self.now + timedelta(days=1), state))

    def test_cache_roundtrip_mismatch_corruption_and_future_timestamps(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "weather-cache.json"
            write_cache(path, self.config, self.snapshot)
            self.assertEqual(read_cache(path, self.config, self.now), self.snapshot)
            self.assertIsNone(read_cache(path, replace(self.config, longitude=1), self.now))
            self.assertIsNone(read_cache(path, replace(self.config, temperature_unit="fahrenheit"), self.now))
            self.assertFalse(path.with_suffix(".tmp").exists())
            with self.assertRaises(ValueError):
                read_cache(path, self.config, self.now - timedelta(hours=1))
            path.write_text("{bad", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_cache(path, self.config, self.now)

    def test_status_identifies_stale_last_known_and_prior_day_readings(self):
        self.assertEqual(weather_status(WeatherState(loading=True), self.now), "Loading weather")
        self.assertEqual(weather_status(WeatherState(failed=True), self.now), "Weather unavailable")
        self.assertIn("Last known", weather_status(WeatherState(self.snapshot, failed=True), self.now))
        self.assertIn("Stale", weather_status(WeatherState(self.snapshot), self.now + timedelta(minutes=30)))
        tomorrow = weather_status(WeatherState(self.snapshot), self.now + timedelta(days=1))
        self.assertIn("Nov 20", tomorrow)


class FakeEvent:
    def __init__(self, callback, delay):
        self.callback, self.delay, self.cancelled = callback, delay, False

    def cancel(self):
        self.cancelled = True


class FakeScheduler:
    def __init__(self):
        self.events = []

    def schedule_once(self, callback, delay):
        event = FakeEvent(callback, delay)
        self.events.append(event)
        return event


class FakeRequest:
    def __init__(self, url, **kwargs):
        self.url, self.callbacks, self.cancelled = url, kwargs, False

    def cancel(self):
        self.cancelled = True


class WeatherLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config = DashboardConfig(latitude=0, longitude=0, timezone="UTC")
        self.path = Path(self.directory.name) / "cache.json"
        self.scheduler = FakeScheduler()
        self.requests, self.updates = [], []

        def request_factory(url, **kwargs):
            request = FakeRequest(url, **kwargs)
            self.requests.append(request)
            return request

        self.service = WeatherService(self.config, self.path, self.updates.append,
                                      scheduler=self.scheduler, request_factory=request_factory)
        self.addCleanup(self.service.stop)

    def succeed(self):
        request = self.requests[-1]
        request.callbacks["on_success"](request, weather_response(datetime.now()))

    def fail(self):
        request = self.requests[-1]
        with self.assertLogs("weather_service", level="WARNING"):
            request.callbacks["on_error"](request, OSError("connection unavailable"))

    def test_single_request_bounded_retries_and_recovery(self):
        self.service.start()
        self.service.refresh()
        self.assertEqual(len(self.requests), 1)
        self.assertIn("forecast_days=1", self.requests[0].url)
        self.succeed()
        snapshot = self.service.state.snapshot
        self.assertEqual(self.scheduler.events[-1].delay, REFRESH_SECONDS)
        self.service.refresh()
        self.fail()
        self.assertEqual(self.scheduler.events[-1].delay, RETRY_SECONDS)
        self.assertEqual(self.service.state.snapshot, snapshot)
        self.service.refresh()
        self.succeed()
        self.assertFalse(self.service.state.failed)

    def test_stop_cancels_request_and_ignores_late_callbacks(self):
        self.service.start()
        request = self.requests[0]
        update_count = len(self.updates)
        self.service.stop()
        self.assertTrue(request.cancelled)
        self.succeed()
        self.assertEqual(len(self.updates), update_count)
        self.assertFalse(self.path.exists())
        self.assertFalse(self.scheduler.events)

    def test_cache_write_error_preserves_live_reading_and_reports_problem(self):
        self.service.start()
        with patch("weather_service.write_cache", side_effect=OSError("read-only disk")), \
                self.assertLogs("weather_service", level="ERROR"):
            self.succeed()
        self.assertIsNotNone(self.service.state.snapshot)
        self.assertTrue(self.service.state.cache_error)
        self.assertFalse(self.service.state.failed)

    def test_corrupt_cache_and_malformed_response_are_visible_not_fatal(self):
        self.path.write_text("{bad", encoding="utf-8")
        with self.assertLogs("weather_service", level="ERROR"):
            self.service.start()
        self.assertTrue(self.service.state.cache_error)
        request = self.requests[0]
        with self.assertLogs("weather_service", level="WARNING"):
            request.callbacks["on_success"](request, {"current": None})
        self.assertTrue(self.service.state.failed)
        self.assertIsNone(self.service.state.snapshot)
        self.assertEqual(self.scheduler.events[-1].delay, RETRY_SECONDS)


if __name__ == "__main__":
    unittest.main()
