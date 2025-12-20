"""
YouTube API service wrapper for StreamClock.
Handles authentication, API requests, and data retrieval.
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YouTubeAPIService:
    """Service class for YouTube Data API v3 integration."""
    
    def __init__(self, api_key: str, channel_id: str, polling_interval: int = 30):
        """
        Initialize YouTube API service.
        
        Args:
            api_key: YouTube Data API v3 key
            channel_id: YouTube channel ID to monitor
            polling_interval: Seconds between API polls (default: 30)
        """
        if not YOUTUBE_API_AVAILABLE:
            raise ImportError("google-api-python-client not installed")
        
        self.api_key = api_key
        self.channel_id = channel_id
        self.polling_interval = polling_interval
        self.youtube = None
        self._lock = threading.Lock()
        
        # Cached data
        self._cache = {
            'live_broadcast': None,
            'viewer_count': 0,
            'chat_messages_count': 0,
            'subscriber_count': 0,
            'stream_start_time': None,
            'stream_status': 'offline',
            'stream_health': {},
            'last_update': None,
            'last_chat_check': None,
            'error': None
        }
        
        # Rate limiting
        self._last_api_call = 0
        self._min_call_interval = 1  # Minimum 1 second between API calls
        
        self._initialize_api()
    
    def _initialize_api(self):
        """Initialize YouTube API client."""
        try:
            self.youtube = build('youtube', 'v3', developerKey=self.api_key)
            logger.info("YouTube API initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize YouTube API: {e}")
            self._cache['error'] = str(e)
    
    def _rate_limit(self):
        """Enforce rate limiting between API calls."""
        now = time.time()
        elapsed = now - self._last_api_call
        if elapsed < self._min_call_interval:
            time.sleep(self._min_call_interval - elapsed)
        self._last_api_call = time.time()
    
    def get_live_broadcasts(self) -> Optional[Dict[str, Any]]:
        """
        Get current live broadcasts for the channel.
        
        Returns:
            Live broadcast data or None if not live
        """
        if not self.youtube:
            return None
        
        try:
            self._rate_limit()
            request = self.youtube.liveBroadcasts().list(
                part='snippet,status,contentDetails',
                broadcastStatus='active',
                broadcastType='all'
            )
            response = request.execute()
            
            if response.get('items'):
                return response['items'][0]
            return None
        except HttpError as e:
            logger.error(f"HTTP error getting live broadcasts: {e}")
            self._cache['error'] = f"API Error: {e.resp.status}"
            return None
        except Exception as e:
            logger.error(f"Error getting live broadcasts: {e}")
            self._cache['error'] = str(e)
            return None
    
    def get_live_stream_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed statistics for a live stream.
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Stream statistics or None on error
        """
        if not self.youtube:
            return None
        
        try:
            self._rate_limit()
            request = self.youtube.videos().list(
                part='liveStreamingDetails,statistics',
                id=video_id
            )
            response = request.execute()
            
            if response.get('items'):
                return response['items'][0]
            return None
        except HttpError as e:
            logger.error(f"HTTP error getting stream details: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting stream details: {e}")
            return None
    
    def get_chat_messages_count(self, live_chat_id: str) -> int:
        """
        Get count of recent chat messages.
        
        Args:
            live_chat_id: Live chat ID
        
        Returns:
            Number of recent messages
        """
        if not self.youtube:
            return 0
        
        try:
            self._rate_limit()
            request = self.youtube.liveChatMessages().list(
                liveChatId=live_chat_id,
                part='snippet',
                maxResults=100
            )
            response = request.execute()
            return len(response.get('items', []))
        except HttpError as e:
            logger.error(f"HTTP error getting chat messages: {e}")
            return 0
        except Exception as e:
            logger.error(f"Error getting chat messages: {e}")
            return 0
    
    def get_subscriber_count(self) -> int:
        """
        Get current subscriber count for the channel.
        
        Returns:
            Subscriber count or 0 on error
        """
        if not self.youtube or not self.channel_id:
            return 0
        
        try:
            self._rate_limit()
            request = self.youtube.channels().list(
                part='statistics',
                id=self.channel_id
            )
            response = request.execute()
            
            if response.get('items'):
                stats = response['items'][0].get('statistics', {})
                return int(stats.get('subscriberCount', 0))
            return 0
        except HttpError as e:
            logger.error(f"HTTP error getting subscriber count: {e}")
            return 0
        except Exception as e:
            logger.error(f"Error getting subscriber count: {e}")
            return 0
    
    def update_cache(self):
        """Update cached stream data from YouTube API."""
        with self._lock:
            try:
                # Get live broadcast
                broadcast = self.get_live_broadcasts()
                
                if broadcast:
                    video_id = broadcast['id']
                    self._cache['live_broadcast'] = broadcast
                    self._cache['stream_status'] = 'live'
                    
                    # Get detailed stream info
                    details = self.get_live_stream_details(video_id)
                    if details:
                        # Extract viewer count
                        live_details = details.get('liveStreamingDetails', {})
                        stats = details.get('statistics', {})
                        
                        self._cache['viewer_count'] = int(live_details.get('concurrentViewers', 0))
                        
                        # Parse stream start time
                        start_time_str = live_details.get('actualStartTime')
                        if start_time_str:
                            self._cache['stream_start_time'] = datetime.fromisoformat(
                                start_time_str.replace('Z', '+00:00')
                            )
                        
                        # Get chat ID and messages
                        chat_id = live_details.get('activeLiveChatId')
                        if chat_id:
                            chat_count = self.get_chat_messages_count(chat_id)
                            
                            # Calculate messages per minute
                            now = datetime.now()
                            if self._cache['last_chat_check']:
                                time_diff = (now - self._cache['last_chat_check']).total_seconds()
                                if time_diff > 0:
                                    msg_diff = chat_count - self._cache['chat_messages_count']
                                    self._cache['chat_activity'] = (msg_diff / time_diff) * 60
                            
                            self._cache['chat_messages_count'] = chat_count
                            self._cache['last_chat_check'] = now
                else:
                    # No live broadcast
                    self._cache['stream_status'] = 'offline'
                    self._cache['viewer_count'] = 0
                    self._cache['stream_start_time'] = None
                    self._cache['live_broadcast'] = None
                
                # Get subscriber count
                self._cache['subscriber_count'] = self.get_subscriber_count()
                
                self._cache['last_update'] = datetime.now()
                self._cache['error'] = None
                
            except Exception as e:
                logger.error(f"Error updating cache: {e}")
                self._cache['error'] = str(e)
    
    def get_cached_data(self) -> Dict[str, Any]:
        """
        Get cached stream data.
        
        Returns:
            Dictionary with cached stream information
        """
        with self._lock:
            return self._cache.copy()
    
    def get_stream_duration(self) -> Optional[timedelta]:
        """
        Calculate current stream duration.
        
        Returns:
            Stream duration or None if not streaming
        """
        with self._lock:
            if self._cache['stream_start_time'] and self._cache['stream_status'] == 'live':
                return datetime.now() - self._cache['stream_start_time'].replace(tzinfo=None)
            return None
    
    def is_live(self) -> bool:
        """
        Check if channel is currently live.
        
        Returns:
            True if live, False otherwise
        """
        with self._lock:
            return self._cache['stream_status'] == 'live'
