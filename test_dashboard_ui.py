import unittest
from datetime import datetime, timedelta
from dataclasses import replace
from unittest.mock import Mock, patch

from kivy.base import EventLoop
from kivy.core.window import Window

from clock_app import ClockScreen
from dashboard_config import DashboardConfig
from test_dashboard import weather_response
from weather_service import WeatherState, parse_weather


class DashboardUiTests(unittest.TestCase):
    def setUp(self):
        Window.fullscreen = False
        Window.size = (800, 480)
        self.config = DashboardConfig(
            location_name="A configured location with a long name",
            latitude=0, longitude=0, timezone="UTC",
            messages=("Take a moment to notice something good, then make time for one small step forward today.",
                      "Tomorrow is a fresh start."),
        )
        self.screen = ClockScreen(config=self.config, size=Window.size)
        Window.add_widget(self.screen)
        self.addCleanup(self.cleanup)
        self.settle()

    def cleanup(self):
        self.screen.stop()
        Window.remove_widget(self.screen)

    def settle(self):
        for _ in range(6):
            EventLoop.idle()
        for label, _font_size, _role in self.screen._text_labels:
            label.texture_update()

    def test_landscape_layouts_keep_clock_and_long_content_inside_regions(self):
        self.screen.config = replace(self.config, messages=(self.config.messages[0],))
        now = datetime(2027, 9, 29, 23, 59, 59)
        snapshot = parse_weather(weather_response(now), self.config, now)
        for size in ((800, 480), (1280, 720)):
            with self.subTest(size=size):
                Window.size = size
                self.screen.size = size
                with patch("clock_app.datetime") as clock:
                    clock.now.return_value = now
                    self.screen._weather_updated(WeatherState(snapshot, failed=True))
                    self.screen.message_label.text = self.config.messages[0]
                    self.settle()
                self.assertEqual(self.screen.seconds_label.text, ":59")
                self.assertLessEqual(self.screen.time_row.width, self.screen.layout.width - 56 * min(size[0] / 800, size[1] / 480))
                for name in ("time_label", "seconds_label", "date_label",
                             "message_label", "temperature_label", "condition_label", "range_label",
                             "weather_status_label", "config_status"):
                    label = getattr(self.screen, name)
                    lines = label._label._cached_lines
                    self.assertLessEqual(sum(line.h for line in lines), label.height + 1, name)
                    self.assertTrue(all(line.w <= label.width + 1 for line in lines), name)
                self.assertLessEqual(len(self.screen.message_label._label._cached_lines), 3)
                self.assertEqual(self.screen.message_label.text, self.config.messages[0])
                self.assertLessEqual(self.screen.weather_card.right, self.screen.message_card.x)
                self.assertLessEqual(self.screen.cards.top, self.screen.date_label.y)
                words = "".join(word.text for line in self.screen.message_label._label._cached_lines
                                for word in line.words)
                self.assertEqual(words.replace(" ", ""), self.config.messages[0].replace(" ", ""))

    def test_overlong_rendered_message_is_explicitly_shortened(self):
        self.screen._message_source = "W" * 90
        with self.assertLogs("clock_app", level="WARNING"):
            self.screen._fit_message()
        self.settle()
        self.assertTrue(self.screen.message_label.text.endswith("..."))
        self.assertIn("shortened", self.screen.message_note.text)
        self.assertLessEqual(sum(line.h for line in self.screen.message_label._label._cached_lines),
                             self.screen.message_label.height)

    def test_negative_fahrenheit_and_stale_cache_status_fit(self):
        now = datetime.now()
        config = replace(self.config, temperature_unit="fahrenheit")
        self.screen.config = config
        snapshot = parse_weather(weather_response(now, "fahrenheit"), config, now)
        snapshot = replace(snapshot, temperature=-148,
                           fetched_at=(now - timedelta(days=1)).timestamp(),
                           observed_at=(now - timedelta(days=1)).timestamp())
        self.screen._weather_updated(WeatherState(snapshot, failed=True, cache_error=True))
        self.settle()
        for label in (self.screen.temperature_label, self.screen.weather_status_label):
            self.assertEqual(len(label._label._cached_lines), 1)
            self.assertLessEqual(label._label._cached_lines[0].h, label.height)
            self.assertFalse(label.is_shortened)

    def test_clock_changes_during_pending_weather_and_midnight_clears_yesterday_range(self):
        now = datetime(2026, 11, 20, 23, 59, 59)
        snapshot = parse_weather(weather_response(now), self.config, now)
        self.screen.weather_service = Mock()
        with patch("clock_app.datetime") as clock:
            clock.now.return_value = now
            self.screen._weather_updated(WeatherState(snapshot))
            old_message = self.screen.message_label.text
            clock.now.return_value = now + timedelta(seconds=1)
            self.screen.update_time(0.5)
        self.assertEqual(self.screen.time_label.text, "[b]00:00[/b]")
        self.assertEqual(self.screen.seconds_label.text, ":00")
        self.assertNotEqual(self.screen.message_label.text, old_message)
        self.assertEqual(self.screen.range_label.text, "Today's range unavailable")
        self.assertIn("Nov 20", self.screen.weather_status_label.text)
        self.assertTrue(self.screen._night)
        self.assertEqual(self.screen.weather_service.refresh.call_count, 1)

    def test_invalid_configuration_notice_and_shutdown_remain_visible(self):
        self.cleanup()
        self.screen = ClockScreen(config_error=True, size=Window.size)
        Window.add_widget(self.screen)
        self.settle()
        self.assertIn("Configuration error", self.screen.config_status.text)
        self.assertEqual(self.screen.weather_status_label.text, "Weather not configured")
        self.screen.stop()
        self.assertFalse(self.screen._clock_event.is_triggered)


if __name__ == "__main__":
    unittest.main()
