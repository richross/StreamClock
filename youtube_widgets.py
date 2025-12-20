"""
Kivy widgets for displaying YouTube stream information.
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from datetime import datetime, timedelta


class StreamStatsWidget(BoxLayout):
    """Widget displaying YouTube stream statistics."""
    
    def __init__(self, **kwargs):
        super(StreamStatsWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (0.3, 0.4)
        self.pos_hint = {'right': 0.98, 'top': 0.98}
        self.padding = [10, 10, 10, 10]
        self.spacing = 5
        
        # Add semi-transparent background
        with self.canvas.before:
            Color(0, 0, 0, 0.6)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        # Status indicator
        self.status_label = Label(
            text='[b]● OFFLINE[/b]',
            markup=True,
            font_size='16sp',
            size_hint_y=None,
            height='30sp',
            color=(0.7, 0.7, 0.7, 1)
        )
        self.add_widget(self.status_label)
        
        # Viewer count
        self.viewer_label = Label(
            text='',
            font_size='14sp',
            size_hint_y=None,
            height='25sp'
        )
        self.add_widget(self.viewer_label)
        
        # Stream duration
        self.duration_label = Label(
            text='',
            font_size='14sp',
            size_hint_y=None,
            height='25sp'
        )
        self.add_widget(self.duration_label)
        
        # Chat activity
        self.chat_label = Label(
            text='',
            font_size='14sp',
            size_hint_y=None,
            height='25sp'
        )
        self.add_widget(self.chat_label)
        
        # Subscriber count
        self.subscriber_label = Label(
            text='',
            font_size='14sp',
            size_hint_y=None,
            height='25sp'
        )
        self.add_widget(self.subscriber_label)
        
        # Error message
        self.error_label = Label(
            text='',
            font_size='12sp',
            size_hint_y=None,
            height='20sp',
            color=(1, 0.3, 0.3, 1)
        )
        self.add_widget(self.error_label)
    
    def _update_bg(self, *args):
        """Update background rectangle position and size."""
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
    
    def update(self, data: dict, features: dict):
        """
        Update widget with stream data.
        
        Args:
            data: Dictionary with stream data from YouTube API
            features: Dictionary indicating which features are enabled
        """
        is_live = data.get('stream_status') == 'live'
        
        # Update status
        if is_live:
            self.status_label.text = '[b]● LIVE[/b]'
            self.status_label.color = (1, 0.2, 0.2, 1)  # Red for live
        else:
            self.status_label.text = '[b]● OFFLINE[/b]'
            self.status_label.color = (0.7, 0.7, 0.7, 1)  # Gray for offline
        
        # Update viewer count
        if features.get('viewer_count') and is_live:
            viewers = data.get('viewer_count', 0)
            self.viewer_label.text = f'👥 {viewers:,} viewers'
        else:
            self.viewer_label.text = ''
        
        # Update stream duration
        if features.get('stream_duration') and is_live:
            start_time = data.get('stream_start_time')
            if start_time:
                duration = datetime.now() - start_time.replace(tzinfo=None)
                hours = int(duration.total_seconds() // 3600)
                minutes = int((duration.total_seconds() % 3600) // 60)
                seconds = int(duration.total_seconds() % 60)
                self.duration_label.text = f'⏱️  {hours:02d}:{minutes:02d}:{seconds:02d}'
            else:
                self.duration_label.text = ''
        else:
            self.duration_label.text = ''
        
        # Update chat activity
        if features.get('chat_activity') and is_live:
            chat_rate = data.get('chat_activity', 0)
            if chat_rate > 0:
                self.chat_label.text = f'💬 {chat_rate:.1f} msg/min'
            else:
                self.chat_label.text = ''
        else:
            self.chat_label.text = ''
        
        # Update subscriber count
        if features.get('subscriber_count'):
            subs = data.get('subscriber_count', 0)
            if subs > 0:
                self.subscriber_label.text = f'📊 {subs:,} subscribers'
            else:
                self.subscriber_label.text = ''
        else:
            self.subscriber_label.text = ''
        
        # Update error message
        error = data.get('error')
        if error:
            self.error_label.text = f'⚠️  {error[:30]}...'
        else:
            self.error_label.text = ''
    
    def hide(self):
        """Hide the widget."""
        self.opacity = 0
        self.disabled = True
    
    def show(self):
        """Show the widget."""
        self.opacity = 1
        self.disabled = False


class CompactStreamStatsWidget(Label):
    """Compact single-line stream stats widget."""
    
    def __init__(self, **kwargs):
        super(CompactStreamStatsWidget, self).__init__(**kwargs)
        self.markup = True
        self.font_size = '14sp'
        self.size_hint = (None, None)
        self.height = '30sp'
        self.pos_hint = {'right': 0.98, 'top': 0.98}
        self.padding = [10, 5]
        
        # Add semi-transparent background
        with self.canvas.before:
            Color(0, 0, 0, 0.6)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg, texture_size=self._update_size)
    
    def _update_bg(self, *args):
        """Update background rectangle."""
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
    
    def _update_size(self, *args):
        """Update widget size based on text."""
        self.width = self.texture_size[0] + 20
    
    def update(self, data: dict, features: dict):
        """
        Update widget with stream data.
        
        Args:
            data: Dictionary with stream data from YouTube API
            features: Dictionary indicating which features are enabled
        """
        is_live = data.get('stream_status') == 'live'
        
        if not is_live:
            self.text = '[b]● OFFLINE[/b]'
            self.color = (0.7, 0.7, 0.7, 1)
            return
        
        # Build compact status line
        parts = ['[b][color=ff3333]● LIVE[/color][/b]']
        
        if features.get('viewer_count'):
            viewers = data.get('viewer_count', 0)
            parts.append(f'{viewers:,}👥')
        
        if features.get('stream_duration'):
            start_time = data.get('stream_start_time')
            if start_time:
                duration = datetime.now() - start_time.replace(tzinfo=None)
                hours = int(duration.total_seconds() // 3600)
                minutes = int((duration.total_seconds() % 3600) // 60)
                parts.append(f'{hours:02d}:{minutes:02d}⏱️')
        
        self.text = ' | '.join(parts)
        self.color = (1, 1, 1, 1)
