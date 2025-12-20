"""
Unit tests for YouTube API integration.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from youtube_service import YouTubeAPIService
from youtube_poller import YouTubePoller


class TestConfig(unittest.TestCase):
    """Test configuration management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = 'test_config.json'
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
    
    def test_default_config(self):
        """Test default configuration creation."""
        config = Config(self.test_config_file)
        self.assertIsNotNone(config.config)
        self.assertIn('youtube', config.config)
        self.assertIn('display', config.config)
    
    def test_get_config_value(self):
        """Test getting configuration values."""
        config = Config(self.test_config_file)
        
        # Test existing key
        self.assertEqual(config.get('youtube.enabled'), False)
        
        # Test non-existing key with default
        self.assertEqual(config.get('nonexistent.key', 'default'), 'default')
    
    def test_set_config_value(self):
        """Test setting configuration values."""
        config = Config(self.test_config_file)
        
        config.set('youtube.enabled', True)
        self.assertEqual(config.get('youtube.enabled'), True)
        
        config.set('youtube.api_key', 'test_key')
        self.assertEqual(config.get('youtube.api_key'), 'test_key')
    
    def test_config_from_environment(self):
        """Test configuration from environment variables."""
        os.environ['YOUTUBE_API_KEY'] = 'env_test_key'
        os.environ['YOUTUBE_CHANNEL_ID'] = 'env_test_channel'
        
        config = Config(self.test_config_file)
        
        self.assertEqual(config.get('youtube.api_key'), 'env_test_key')
        self.assertEqual(config.get('youtube.channel_id'), 'env_test_channel')
        
        # Clean up
        del os.environ['YOUTUBE_API_KEY']
        del os.environ['YOUTUBE_CHANNEL_ID']


class TestYouTubeAPIService(unittest.TestCase):
    """Test YouTube API service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api_key = 'test_api_key'
        self.channel_id = 'test_channel_id'
    
    @patch('youtube_service.YOUTUBE_API_AVAILABLE', True)
    @patch('googleapiclient.discovery.build')
    def test_service_initialization(self, mock_build):
        """Test service initialization."""
        mock_youtube = Mock()
        mock_build.return_value = mock_youtube
        
        service = YouTubeAPIService(self.api_key, self.channel_id)
        
        self.assertEqual(service.api_key, self.api_key)
        self.assertEqual(service.channel_id, self.channel_id)
        self.assertIsNotNone(service.youtube)
        mock_build.assert_called_once_with('youtube', 'v3', developerKey=self.api_key)
    
    @patch('youtube_service.YOUTUBE_API_AVAILABLE', True)
    @patch('googleapiclient.discovery.build')
    def test_get_cached_data(self, mock_build):
        """Test getting cached data."""
        mock_youtube = Mock()
        mock_build.return_value = mock_youtube
        
        service = YouTubeAPIService(self.api_key, self.channel_id)
        data = service.get_cached_data()
        
        self.assertIsInstance(data, dict)
        self.assertIn('stream_status', data)
        self.assertIn('viewer_count', data)
        self.assertEqual(data['stream_status'], 'offline')
    
    @patch('youtube_service.YOUTUBE_API_AVAILABLE', True)
    @patch('googleapiclient.discovery.build')
    def test_is_live(self, mock_build):
        """Test live status check."""
        mock_youtube = Mock()
        mock_build.return_value = mock_youtube
        
        service = YouTubeAPIService(self.api_key, self.channel_id)
        
        # Initially should not be live
        self.assertFalse(service.is_live())
        
        # Set to live
        service._cache['stream_status'] = 'live'
        self.assertTrue(service.is_live())
    
    @patch('youtube_service.YOUTUBE_API_AVAILABLE', True)
    @patch('googleapiclient.discovery.build')
    def test_rate_limiting(self, mock_build):
        """Test API rate limiting."""
        mock_youtube = Mock()
        mock_build.return_value = mock_youtube
        
        service = YouTubeAPIService(self.api_key, self.channel_id)
        
        start_time = time.time()
        service._rate_limit()
        service._rate_limit()
        end_time = time.time()
        
        # Second call should be delayed by at least min_call_interval
        self.assertGreaterEqual(end_time - start_time, service._min_call_interval)
    
    @patch('youtube_service.YOUTUBE_API_AVAILABLE', True)
    @patch('googleapiclient.discovery.build')
    def test_get_live_broadcasts_no_items(self, mock_build):
        """Test getting live broadcasts when none exist."""
        mock_youtube = Mock()
        mock_broadcast_list = Mock()
        mock_request = Mock()
        
        mock_request.execute.return_value = {'items': []}
        mock_broadcast_list.list.return_value = mock_request
        mock_youtube.liveBroadcasts.return_value = mock_broadcast_list
        mock_build.return_value = mock_youtube
        
        service = YouTubeAPIService(self.api_key, self.channel_id)
        result = service.get_live_broadcasts()
        
        self.assertIsNone(result)
    
    @patch('youtube_service.YOUTUBE_API_AVAILABLE', True)
    @patch('googleapiclient.discovery.build')
    def test_get_live_broadcasts_with_broadcast(self, mock_build):
        """Test getting live broadcasts when one exists."""
        mock_youtube = Mock()
        mock_broadcast_list = Mock()
        mock_request = Mock()
        
        broadcast_data = {
            'id': 'test_broadcast_id',
            'snippet': {'title': 'Test Stream'},
            'status': {'lifeCycleStatus': 'live'}
        }
        mock_request.execute.return_value = {'items': [broadcast_data]}
        mock_broadcast_list.list.return_value = mock_request
        mock_youtube.liveBroadcasts.return_value = mock_broadcast_list
        mock_build.return_value = mock_youtube
        
        service = YouTubeAPIService(self.api_key, self.channel_id)
        result = service.get_live_broadcasts()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'test_broadcast_id')
    
    @patch('youtube_service.YOUTUBE_API_AVAILABLE', True)
    @patch('googleapiclient.discovery.build')
    def test_update_cache_offline(self, mock_build):
        """Test cache update when not live."""
        mock_youtube = Mock()
        mock_broadcast_list = Mock()
        mock_request = Mock()
        
        mock_request.execute.return_value = {'items': []}
        mock_broadcast_list.list.return_value = mock_request
        mock_youtube.liveBroadcasts.return_value = mock_broadcast_list
        mock_build.return_value = mock_youtube
        
        service = YouTubeAPIService(self.api_key, self.channel_id)
        service.update_cache()
        
        data = service.get_cached_data()
        self.assertEqual(data['stream_status'], 'offline')
        self.assertEqual(data['viewer_count'], 0)


class TestYouTubePoller(unittest.TestCase):
    """Test YouTube background poller."""
    
    @patch('youtube_service.YOUTUBE_API_AVAILABLE', True)
    @patch('googleapiclient.discovery.build')
    def test_poller_initialization(self, mock_build):
        """Test poller initialization."""
        mock_youtube = Mock()
        mock_build.return_value = mock_youtube
        
        service = YouTubeAPIService('test_key', 'test_channel')
        poller = YouTubePoller(service, interval=5)
        
        self.assertEqual(poller.interval, 5)
        self.assertIsNotNone(poller.youtube_service)
    
    @patch('youtube_service.YOUTUBE_API_AVAILABLE', True)
    @patch('googleapiclient.discovery.build')
    def test_poller_start_stop(self, mock_build):
        """Test starting and stopping poller."""
        mock_youtube = Mock()
        mock_build.return_value = mock_youtube
        
        service = YouTubeAPIService('test_key', 'test_channel')
        poller = YouTubePoller(service, interval=1)
        
        poller.start()
        self.assertIsNotNone(poller._thread)
        self.assertTrue(poller._thread.is_alive())
        
        poller.stop()
        self.assertFalse(poller._thread.is_alive())


if __name__ == '__main__':
    # Import time here to avoid issues with mocking
    import time
    unittest.main()
