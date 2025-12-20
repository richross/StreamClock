"""
Background poller for YouTube API updates.
Runs in a separate thread to avoid blocking the UI.
"""
import threading
import time
import logging

logger = logging.getLogger(__name__)


class YouTubePoller:
    """Background thread that polls YouTube API at regular intervals."""
    
    def __init__(self, youtube_service, interval: int = 30):
        """
        Initialize poller.
        
        Args:
            youtube_service: YouTubeAPIService instance
            interval: Polling interval in seconds
        """
        self.youtube_service = youtube_service
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread = None
    
    def start(self):
        """Start the background polling thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Poller already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info(f"YouTube poller started with {self.interval}s interval")
    
    def stop(self):
        """Stop the background polling thread."""
        if not self._thread:
            return
        
        self._stop_event.set()
        self._thread.join(timeout=5)
        logger.info("YouTube poller stopped")
    
    def _poll_loop(self):
        """Main polling loop."""
        while not self._stop_event.is_set():
            try:
                self.youtube_service.update_cache()
            except Exception as e:
                logger.error(f"Error in poll loop: {e}")
            
            # Wait for next interval or stop event
            self._stop_event.wait(self.interval)
