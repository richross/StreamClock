"""
Configuration management for StreamClock YouTube API integration.
"""
import os
import json
from pathlib import Path


class Config:
    """Configuration manager for StreamClock."""
    
    def __init__(self, config_file='config.json'):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file (default: config.json)
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file or create default."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config file: {e}")
                return self._default_config()
        else:
            return self._default_config()
    
    def _default_config(self):
        """Return default configuration."""
        return {
            'youtube': {
                'api_key': os.environ.get('YOUTUBE_API_KEY', ''),
                'channel_id': os.environ.get('YOUTUBE_CHANNEL_ID', ''),
                'enabled': False,
                'polling_interval': 30,  # seconds
                'features': {
                    'viewer_count': True,
                    'stream_duration': True,
                    'chat_activity': True,
                    'stream_status': True,
                    'subscriber_count': True,
                    'stream_health': True
                }
            },
            'display': {
                'show_offline_message': True,
                'compact_mode': False
            }
        }
    
    def save(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except IOError as e:
            print(f"Error saving config file: {e}")
    
    def get(self, key_path, default=None):
        """
        Get configuration value by dot-separated key path.
        
        Args:
            key_path: Dot-separated path (e.g., 'youtube.api_key')
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path, value):
        """
        Set configuration value by dot-separated key path.
        
        Args:
            key_path: Dot-separated path (e.g., 'youtube.api_key')
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
