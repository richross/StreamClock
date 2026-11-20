import logging
import os
from datetime import datetime
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager

from dashboard_config import DashboardConfig, daily_message, load_config
from weather_service import CONDITIONS, WeatherService, WeatherState, night_palette, weather_status


Window.fullscreen = "auto"
logger = logging.getLogger(__name__)

DAY = {
    "background": (0.063, 0.110, 0.180, 1),
    "card": (0.102, 0.165, 0.251, 1),
    "text": (1, 0.961, 0.906, 1),
    "muted": (0.682, 0.745, 0.816, 1),
    "accent": (0.376, 0.851, 0.773, 1),
    "warning": (0.965, 0.784, 0.471, 1),
}
NIGHT = {
    "background": (0.043, 0.075, 0.125, 1),
    "card": (0.082, 0.133, 0.208, 1),
    "text": (0.765, 0.737, 0.686, 1),
    "muted": (0.639, 0.686, 0.749, 1),
    "accent": (0.506, 0.718, 0.682, 1),
    "warning": (0.820, 0.702, 0.522, 1),
}


class InfoCard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        with self.canvas.before:
            self.background_color = Color(*DAY["card"])
            self.background = RoundedRectangle(pos=self.pos, size=self.size, radius=[12])
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_args):
        self.background.pos = self.pos
        self.background.size = self.size


class ClockScreen(Screen):
    def __init__(self, config=None, config_error=False, **kwargs):
        super().__init__(**kwargs)
        self.config = config or DashboardConfig()
        self.config_error = config_error
        self.weather_state = WeatherState()
        self.weather_service = None
        self._day = None
        self._night = None
        self._text_labels = []
        self._message_source = ""
        with self.canvas.before:
            self.background_color = Color(*DAY["background"])
            self.background = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw_background, size=self._redraw_background)

        root = FloatLayout()
        self.layout = BoxLayout(orientation="vertical", size_hint=(None, None),
                                pos_hint={"center_x": 0.5, "center_y": 0.5})
        root.add_widget(self.layout)
        self.header = BoxLayout(size_hint_y=None)
        self.heading = self._label("YOUR DAY, AT A GLANCE", 14, "muted")
        self.mode_label = self._label("", 12, "muted", halign="right")
        self.header.add_widget(self.heading)
        self.header.add_widget(self.mode_label)
        self.layout.add_widget(self.header)

        self.clock_area = BoxLayout(orientation="vertical", size_hint_y=None)
        self.time_anchor = AnchorLayout(anchor_x="center", anchor_y="bottom")
        self.time_row = BoxLayout(size_hint=(None, 1))
        self.time_label = self._label("", 116, "text", markup=True,
                                      size_hint_x=None, valign="bottom", natural_width=True)
        self.seconds_label = self._label("", 56, "accent", size_hint_x=None,
                                         valign="bottom", natural_width=True)
        self.time_label.bind(texture_size=self._size_time)
        self.seconds_label.bind(texture_size=self._size_time)
        self.time_row.add_widget(self.time_label)
        self.time_row.add_widget(self.seconds_label)
        self.time_anchor.add_widget(self.time_row)
        self.clock_area.add_widget(self.time_anchor)
        self.date_label = self._label("", 24, "muted", halign="center", size_hint_y=None)
        self.clock_area.add_widget(self.date_label)
        self.layout.add_widget(self.clock_area)

        self.cards = BoxLayout(size_hint_y=None)
        self.weather_card = InfoCard()
        self.message_card = InfoCard()
        self.cards.add_widget(self.weather_card)
        self.cards.add_widget(self.message_card)
        self.layout.add_widget(self.cards)

        title = "WEATHER"
        if self.config.location_name:
            title += " / " + self.config.location_name
        self.weather_title = self._label(title, 12, "muted", size_hint_y=None,
                                         shorten=True, shorten_from="right")
        self.weather_card.add_widget(self.weather_title)
        self.weather_content = BoxLayout()
        self.temperature_label = self._label("--", 36, "text", size_hint_x=0.43)
        self.conditions = BoxLayout(orientation="vertical", size_hint_x=0.57)
        self.condition_label = self._label("Not configured", 17, "text", max_lines=2)
        self.range_label = self._label("", 15, "muted")
        self.conditions.add_widget(self.condition_label)
        self.conditions.add_widget(self.range_label)
        self.weather_content.add_widget(self.temperature_label)
        self.weather_content.add_widget(self.conditions)
        self.weather_card.add_widget(self.weather_content)
        self.weather_status_label = self._label("", 12, "muted", size_hint_y=None,
                                                shorten=True, shorten_from="right")
        self.weather_card.add_widget(self.weather_status_label)

        self.message_title = self._label("TODAY'S MESSAGE", 12, "accent", size_hint_y=None)
        self.message_label = self._label("", 20, "text", max_lines=3)
        self.message_note = self._label("From your local collection", 12, "muted",
                                        size_hint_y=None)
        self._message_event = Clock.create_trigger(self._fit_message)
        self.message_label.bind(size=lambda instance, size: self._message_event())
        for label in (self.message_title, self.message_label, self.message_note):
            self.message_card.add_widget(label)

        self.footer = BoxLayout(size_hint_y=None)
        self.attribution = self._label("Weather data: Open-Meteo", 12, "muted")
        self.config_status = self._label(
            "Configuration error - see log" if config_error else "24-hour clock",
            12, "warning" if config_error else "muted", halign="right",
        )
        self.footer.add_widget(self.attribution)
        self.footer.add_widget(self.config_status)
        self.layout.add_widget(self.footer)

        exit_btn = Button(text="", background_color=(0, 0, 0, 0),
                          background_normal="", background_down="",
                          size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        exit_btn.bind(on_press=lambda instance: App.get_running_app().stop())
        root.add_widget(exit_btn)
        self.add_widget(root)
        self.bind(size=self._resize)
        self._resize()
        self.update_time(0)
        self._clock_event = Clock.schedule_interval(self.update_time, 0.5)

    def _label(self, text, font_size, role, natural_width=False, **kwargs):
        label = Label(text=text, font_size=font_size, halign=kwargs.pop("halign", "left"),
                      valign=kwargs.pop("valign", "middle"), **kwargs)
        label.bind(size=lambda instance, size: setattr(
            instance, "text_size", (None, size[1]) if natural_width else size))
        self._text_labels.append((label, font_size, role))
        return label

    def _redraw_background(self, *_args):
        self.background.pos = self.pos
        self.background.size = self.size

    def _resize(self, *_args):
        scale = min(self.width / 800, self.height / 480)
        self.layout.size = (800 * scale, 480 * scale)
        self.layout.padding = [28 * scale, 18 * scale]
        self.layout.spacing = 12 * scale
        self.header.height = 24 * scale
        self.clock_area.height = 214 * scale
        self.date_label.height = 48 * scale
        self.cards.height = 143 * scale
        self.cards.spacing = 16 * scale
        self.footer.height = 25 * scale
        self.time_row.spacing = 8 * scale
        for card in (self.weather_card, self.message_card):
            card.padding = [20 * scale, 10 * scale]
            card.spacing = 5 * scale
            card.background.radius = [12 * scale]
        for label in (self.weather_title, self.message_title):
            label.height = 20 * scale
        for label in (self.weather_status_label, self.message_note):
            label.height = 18 * scale
        for label, font_size, _role in self._text_labels:
            label.font_size = font_size * scale
        self._size_time()

    def _size_time(self, *_args):
        for label in (self.time_label, self.seconds_label):
            label.width = label.texture_size[0]
        self.time_row.width = self.time_label.width + self.seconds_label.width + self.time_row.spacing

    def _fit_message(self, *_args):
        if not self._message_source or self.message_label.width <= 0:
            return

        def fits(text):
            measurement = CoreLabel(text=text, font_name=self.message_label.font_name,
                                    font_size=self.message_label.font_size,
                                    text_size=(self.message_label.width, None))
            return measurement.render()[1] <= self.message_label.height

        if fits(self._message_source):
            self.message_label.text = self._message_source
            self.message_note.text = "From your local collection"
            return
        start, end = 0, len(self._message_source)
        while start < end:
            middle = (start + end + 1) // 2
            if fits(self._message_source[:middle].rstrip() + "..."):
                start = middle
            else:
                end = middle - 1
        self.message_label.text = self._message_source[:start].rstrip() + "..."
        if self.message_note.text != "Message shortened - edit config":
            logger.warning("Daily message does not fit; displaying an ellipsis")
        self.message_note.text = "Message shortened - edit config"

    def attach_weather(self, cache_path):
        if self.config.weather_enabled:
            self.weather_service = WeatherService(self.config, cache_path, self._weather_updated)
            self.weather_service.start()

    def _weather_updated(self, state):
        self.weather_state = state
        self.update_time(0)

    def update_time(self, _dt):
        now = datetime.now()
        time_text, seconds_text = now.strftime("[b]%H:%M[/b]"), now.strftime(":%S")
        if self.time_label.text != time_text:
            self.time_label.text = time_text
        if self.seconds_label.text != seconds_text:
            self.seconds_label.text = seconds_text
        if now.date() != self._day:
            self._day = now.date()
            self.date_label.text = now.strftime("%A, %B %d, %Y")
            self._message_source = daily_message(self.config, now.date())
            self.message_label.text = self._message_source
            self._message_event()
            if self.weather_service is not None:
                self.weather_service.refresh()
        self._update_weather(now)
        night = night_palette(self.config, now, self.weather_state)
        if night != self._night:
            self._night = night
            palette = NIGHT if night else DAY
            Window.clearcolor = palette["background"]
            self.background_color.rgba = palette["background"]
            for card in (self.weather_card, self.message_card):
                card.background_color.rgba = palette["card"]
            for label, _font_size, role in self._text_labels:
                label.color = palette[role]
            self.mode_label.text = "Night palette" if night else "Day palette"
        warning = self.weather_state.failed or self.weather_state.cache_error
        self.weather_status_label.color = (NIGHT if night else DAY)["warning" if warning else "muted"]

    def _update_weather(self, now):
        snapshot = self.weather_state.snapshot
        if not self.config.weather_enabled:
            self.weather_status_label.text = "Weather not configured"
            return
        self.weather_status_label.text = weather_status(self.weather_state, now)
        if snapshot is None:
            self.condition_label.text = "Unavailable" if self.weather_state.failed else "Loading..."
            return
        unit = "C" if self.config.temperature_unit == "celsius" else "F"
        self.temperature_label.text = f"{snapshot.temperature:.0f}\u00b0{unit}"
        self.condition_label.text = CONDITIONS[snapshot.weather_code]
        if snapshot.forecast_date == now.date().isoformat() and snapshot.high is not None and snapshot.low is not None:
            self.range_label.text = f"High {snapshot.high:.0f}\u00b0 / Low {snapshot.low:.0f}\u00b0"
        else:
            self.range_label.text = "Today's range unavailable"

    def stop(self):
        self._clock_event.cancel()
        self._message_event.cancel()
        if self.weather_service is not None:
            self.weather_service.stop()


class ClockApp(App):
    def build(self):
        config_path = Path(os.environ.get("STREAMCLOCK_CONFIG", Path(__file__).with_name("config.json")))
        config, config_error = DashboardConfig(), False
        try:
            if config_path.exists() or "STREAMCLOCK_CONFIG" in os.environ:
                config = load_config(config_path)
        except (OSError, ValueError, UnicodeError):
            logger.exception("Cannot load dashboard configuration: %s", config_path)
            config_error = True
        logger.info("Clock display dimensions: %s x %s", *Window.size)
        self.screen = ClockScreen(name="clock", config=config, config_error=config_error)
        manager = ScreenManager()
        manager.add_widget(self.screen)
        return manager

    def on_start(self):
        self.screen.attach_weather(Path(self.user_data_dir) / "weather-cache.json")

    def on_stop(self):
        self.screen.stop()


if __name__ == "__main__":
    ClockApp().run()
