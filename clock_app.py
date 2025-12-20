from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.window import Window
from datetime import datetime
import logging

# YouTube integration imports
try:
    from config import Config
    from youtube_service import YouTubeAPIService
    from youtube_poller import YouTubePoller
    from youtube_widgets import StreamStatsWidget, CompactStreamStatsWidget
    YOUTUBE_INTEGRATION_AVAILABLE = True
except ImportError as e:
    logging.warning(f"YouTube integration not available: {e}")
    YOUTUBE_INTEGRATION_AVAILABLE = False

logging.basicConfig(level=logging.INFO)

#Set Window Fullscreen
Window.fullscreen = 'auto'

class ClockScreen(Screen):
    def __init__(self, **kwargs):
        super(ClockScreen, self).__init__(**kwargs)
        
        # Initialize configuration
        self.config = None
        self.youtube_service = None
        self.youtube_poller = None
        self.stream_widget = None
        
        if YOUTUBE_INTEGRATION_AVAILABLE:
            try:
                self.config = Config()
                self._setup_youtube_integration()
            except Exception as e:
                logging.error(f"Failed to setup YouTube integration: {e}")
        
        # Use FloatLayout as base to allow overlay
        root_layout = FloatLayout()
        
        # Create BoxLayout for clock display
        layout = BoxLayout(orientation='vertical')

        #Clock Label
        self.time_label = Label(
            font_size='120sp',
            markup=True
        )

        #Date Label
        self.date_label = Label(
            font_size='30sp'
        )

        #Add Widgets to layout
        layout.add_widget(Label(size_hint=(1, 0.3))) # Spacer
        layout.add_widget(self.time_label)
        layout.add_widget(self.date_label)
        layout.add_widget(Label(size_hint=(1, 0.3))) # Spacer

        # Add clock layout to root
        root_layout.add_widget(layout)
        
        # Add YouTube stats widget if enabled
        if self.stream_widget:
            root_layout.add_widget(self.stream_widget)
        
        #invisible Exit button (overlaid on top)
        exit_btn = Button(
            text="",
            background_color=(0,0,0,0),
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        exit_btn.bind(on_press=lambda instance: App.get_running_app().stop())
        root_layout.add_widget(exit_btn)

        self.add_widget(root_layout)
        Clock.schedule_interval(self.update_time, 0.5)
        
        # Schedule YouTube widget updates if enabled
        if self.stream_widget:
            Clock.schedule_interval(self.update_youtube_display, 1.0)
    
    def _setup_youtube_integration(self):
        """Setup YouTube API integration."""
        if not self.config.get('youtube.enabled'):
            logging.info("YouTube integration is disabled in config")
            return
        
        api_key = self.config.get('youtube.api_key')
        channel_id = self.config.get('youtube.channel_id')
        
        if not api_key or not channel_id:
            logging.warning("YouTube API key or channel ID not configured")
            return
        
        try:
            # Initialize YouTube service
            polling_interval = self.config.get('youtube.polling_interval', 30)
            self.youtube_service = YouTubeAPIService(
                api_key=api_key,
                channel_id=channel_id,
                polling_interval=polling_interval
            )
            
            # Create widget based on display mode
            compact_mode = self.config.get('display.compact_mode', False)
            if compact_mode:
                self.stream_widget = CompactStreamStatsWidget()
            else:
                self.stream_widget = StreamStatsWidget()
            
            # Start background poller
            self.youtube_poller = YouTubePoller(
                self.youtube_service,
                interval=polling_interval
            )
            self.youtube_poller.start()
            
            logging.info("YouTube integration initialized successfully")
        except Exception as e:
            logging.error(f"Error setting up YouTube integration: {e}")
            self.youtube_service = None
            self.stream_widget = None
    
    def update_youtube_display(self, dt):
        """Update YouTube statistics display."""
        if not self.youtube_service or not self.stream_widget:
            return
        
        try:
            data = self.youtube_service.get_cached_data()
            features = self.config.get('youtube.features', {})
            self.stream_widget.update(data, features)
        except Exception as e:
            logging.error(f"Error updating YouTube display: {e}")

    def update_time(self, dt):
        now = datetime.now()
        time_text = now.strftime("[b]%H:%M[/b]:%S")
        date_text = now.strftime("%A, %B %d, %Y")
        self.time_label.text = time_text
        self.date_label.text = date_text
    
    def on_stop(self):
        """Cleanup when screen is stopped."""
        if self.youtube_poller:
            self.youtube_poller.stop()

class ClockApp(App):
    def build(self):
        sm = ScreenManager()
        self.clock_screen = ClockScreen(name='clock')
        sm.add_widget(self.clock_screen)
        return sm
    
    def on_stop(self):
        """Cleanup on app exit."""
        if hasattr(self, 'clock_screen'):
            self.clock_screen.on_stop()
        return True

if __name__ == '__main__':
    ClockApp().run()