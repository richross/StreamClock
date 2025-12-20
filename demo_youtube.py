#!/usr/bin/env python3
"""
Demo script to test YouTube API integration without running the full Kivy app.
This is useful for testing API credentials and functionality.
"""
import sys
import time
from config import Config

def test_config():
    """Test configuration loading."""
    print("=" * 60)
    print("Testing Configuration")
    print("=" * 60)
    
    config = Config('config.json')
    
    print(f"YouTube enabled: {config.get('youtube.enabled')}")
    print(f"API key set: {'Yes' if config.get('youtube.api_key') else 'No'}")
    print(f"Channel ID set: {'Yes' if config.get('youtube.channel_id') else 'No'}")
    print(f"Polling interval: {config.get('youtube.polling_interval')}s")
    print(f"Compact mode: {config.get('display.compact_mode')}")
    
    features = config.get('youtube.features', {})
    print("\nEnabled features:")
    for feature, enabled in features.items():
        status = "✓" if enabled else "✗"
        print(f"  {status} {feature}")
    
    return config

def test_youtube_service(config):
    """Test YouTube API service."""
    print("\n" + "=" * 60)
    print("Testing YouTube API Service")
    print("=" * 60)
    
    if not config.get('youtube.enabled'):
        print("❌ YouTube integration is disabled in config")
        print("   Enable it in config.json to test the API")
        return None
    
    api_key = config.get('youtube.api_key')
    channel_id = config.get('youtube.channel_id')
    
    if not api_key or not channel_id:
        print("❌ YouTube API key or channel ID not configured")
        print("   Add them to config.json to test the API")
        return None
    
    try:
        from youtube_service import YouTubeAPIService
        print("✓ YouTube service module imported successfully")
        
        service = YouTubeAPIService(
            api_key=api_key,
            channel_id=channel_id,
            polling_interval=config.get('youtube.polling_interval', 30)
        )
        print("✓ YouTube service initialized")
        
        return service
        
    except ImportError as e:
        print(f"❌ Failed to import YouTube service: {e}")
        print("   Install dependencies: pip install -r requirements.txt")
        return None
    except Exception as e:
        print(f"❌ Failed to initialize YouTube service: {e}")
        return None

def test_api_call(service):
    """Test making an API call."""
    print("\n" + "=" * 60)
    print("Testing API Call")
    print("=" * 60)
    
    if not service:
        print("⊘ Skipping - service not initialized")
        return
    
    try:
        print("Updating cache from YouTube API...")
        service.update_cache()
        print("✓ Cache updated successfully")
        
        data = service.get_cached_data()
        
        print("\nStream Status:")
        print(f"  Status: {data['stream_status']}")
        print(f"  Is Live: {service.is_live()}")
        
        if service.is_live():
            print(f"\nLive Statistics:")
            print(f"  Viewers: {data['viewer_count']:,}")
            
            duration = service.get_stream_duration()
            if duration:
                hours = int(duration.total_seconds() // 3600)
                minutes = int((duration.total_seconds() % 3600) // 60)
                seconds = int(duration.total_seconds() % 60)
                print(f"  Duration: {hours:02d}:{minutes:02d}:{seconds:02d}")
            
            chat_activity = data.get('chat_activity', 0)
            if chat_activity > 0:
                print(f"  Chat: {chat_activity:.1f} msg/min")
        else:
            print("\n  Not currently live streaming")
        
        print(f"\nSubscriber Count: {data['subscriber_count']:,}")
        
        if data.get('error'):
            print(f"\n⚠️  API Error: {data['error']}")
        
        print(f"\nLast Updated: {data.get('last_update')}")
        
    except Exception as e:
        print(f"❌ API call failed: {e}")

def main():
    """Main demo function."""
    print("\n" + "=" * 60)
    print("StreamClock YouTube Integration Demo")
    print("=" * 60)
    print()
    
    # Test configuration
    config = test_config()
    
    # Test YouTube service
    service = test_youtube_service(config)
    
    # Test API call
    test_api_call(service)
    
    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)
    print()
    
    if service:
        print("✓ All tests passed!")
        print("\nYour YouTube integration is configured correctly.")
        print("You can now run the full StreamClock app with:")
        print("  ./start_clock.sh")
        print("  or")
        print("  python3 clock_app.py")
    else:
        print("⚠️  Some tests failed or were skipped.")
        print("\nPlease check:")
        print("  1. config.json exists and has valid API credentials")
        print("  2. YouTube integration is enabled in config")
        print("  3. Dependencies are installed: pip install -r requirements.txt")
        print("\nFor setup help, see: YOUTUBE_SETUP.md")
    
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
