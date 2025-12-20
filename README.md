# StreamClock

A fullscreen Kivy clock application designed for Raspberry Pi with YouTube Live Streaming API integration. Perfect for content creators who want to display time and live stream statistics during broadcasts.

## Features

### Core Clock Display
- **Fullscreen Time Display**: Large, easy-to-read digital clock
- **Formatted Date**: Current date with day of week
- **Bold Hours/Minutes**: Visual hierarchy with seconds in regular weight
- **0.5s Refresh Rate**: Smooth updates with minimal drift
- **Invisible Exit**: Tap anywhere on the screen to close

### YouTube Live Streaming Integration
- **Live Status Indicator**: Shows when your channel is live
- **Real-time Viewer Count**: Display concurrent viewers during stream
- **Stream Duration**: Elapsed time tracker (HH:MM:SS format)
- **Chat Activity Monitor**: Messages per minute indicator
- **Subscriber Count**: Live subscriber count updates
- **Stream Health Monitoring**: Connection quality metrics (basic implementation)
- **Configurable Features**: Enable/disable individual stat displays
- **Compact Mode**: Minimal single-line display option
- **Toggle Button**: One-click enable/disable button in lower right corner (no restart needed)
- **Graceful Degradation**: Clock works even when API is unavailable

## Screenshots

*Coming soon - Screenshots of the clock display and YouTube integration*

## Requirements

- Python 3.11+
- Raspberry Pi (or any Linux system with display)
- YouTube Data API v3 key (optional, for streaming features)

## Installation

### Basic Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/richross/StreamClock.git
   cd StreamClock
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### YouTube Integration Setup

For YouTube streaming features, follow the detailed guide in [YOUTUBE_SETUP.md](YOUTUBE_SETUP.md).

Quick setup:
1. Get a YouTube Data API v3 key from Google Cloud Console
2. Copy `config.json.example` to `config.json`
3. Add your API key and channel ID
4. Set `"enabled": true` in the config

## Usage

### Running the Clock

**Using the start script (recommended):**
```bash
./start_clock.sh
```

**Or run directly:**
```bash
source venv/bin/activate
python3 clock_app.py
```

### Configuration

Edit `config.json` to customize settings:

```json
{
  "youtube": {
    "api_key": "YOUR_API_KEY",
    "channel_id": "YOUR_CHANNEL_ID",
    "enabled": true,
    "polling_interval": 30,
    "features": {
      "viewer_count": true,
      "stream_duration": true,
      "chat_activity": true,
      "stream_status": true,
      "subscriber_count": true,
      "stream_health": false
    }
  },
  "display": {
    "show_offline_message": true,
    "compact_mode": false
  }
}
```

#### Configuration Options

- **`youtube.enabled`**: Turn YouTube integration on/off
- **`youtube.polling_interval`**: Seconds between API updates (30-60 recommended)
- **`youtube.features.*`**: Toggle individual stat displays
- **`display.compact_mode`**: Use minimal single-line display

### Toggle Button (Runtime Control)

A **YouTube toggle button** appears in the lower right corner when YouTube integration is available:

- **Red "YT ✗" button**: YouTube integration is disabled
- **Green "YT ✓" button**: YouTube integration is enabled
- **Click to toggle**: Enable/disable YouTube features without restarting the app
- **Persistent**: State is saved to config.json and persists across restarts

**Benefits:**
- Quick disable during non-streaming hours (saves API quota)
- Instant feedback without editing config files
- No app restart required
- Perfect for troubleshooting or battery saving

See [TOGGLE_BUTTON_GUIDE.md](TOGGLE_BUTTON_GUIDE.md) for visual mockups and detailed behavior.

### Environment Variables

Alternatively, set API credentials via environment:
```bash
export YOUTUBE_API_KEY="your_api_key"
export YOUTUBE_CHANNEL_ID="your_channel_id"
```

## Autostart on Raspberry Pi

To launch StreamClock automatically on boot:

1. Create systemd service:
   ```bash
   sudo nano /etc/systemd/system/clock.service
   ```

2. Add service configuration:
   ```ini
   [Unit]
   Description=Fullscreen Clock Display
   After=graphical.target

   [Service]
   Environment=DISPLAY=:0
   User=your_username
   WorkingDirectory=/path/to/StreamClock
   ExecStart=/path/to/StreamClock/start_clock.sh
   Restart=on-failure

   [Install]
   WantedBy=graphical.target
   ```

3. Enable and start:
   ```bash
   sudo systemctl enable clock.service
   sudo systemctl start clock.service
   ```

## Development

### Project Structure

```
StreamClock/
├── clock_app.py              # Main Kivy application
├── config.py                 # Configuration management
├── youtube_service.py        # YouTube API wrapper
├── youtube_poller.py         # Background API polling
├── youtube_widgets.py        # Kivy display widgets
├── test_youtube_integration.py  # Unit tests
├── config.json.example       # Example configuration
├── requirements.txt          # Python dependencies
├── start_clock.sh           # Launch script
├── YOUTUBE_SETUP.md         # Detailed YouTube setup guide
└── README.md                # This file
```

### Running Tests

```bash
python3 test_youtube_integration.py
```

### Code Conventions

- **Event Handling**: Lambda bindings for simple callbacks
- **UI Layout**: BoxLayout with FloatLayout overlay for widgets
- **Timing**: Kivy Clock (not asyncio/threading) for UI updates
- **Background Tasks**: Threading for API calls (non-blocking)
- **Error Handling**: Graceful degradation with user feedback

## API Quota Considerations

YouTube Data API v3 has daily quota limits (10,000 units default). With 30-second polling:
- ~2,880 polls per day
- ~8-12 units per poll
- Total: ~25,000-35,000 units/day

**Recommendation**: Use 30-60 second intervals. Disable unused features to reduce quota usage.

See [YOUTUBE_SETUP.md](YOUTUBE_SETUP.md) for detailed quota information.

## Troubleshooting

### Clock won't start
- Check that virtual environment is activated
- Verify Kivy installation: `python3 -c "import kivy"`
- Check for error messages in terminal

### YouTube stats not showing
- Verify API key and channel ID in config.json
- Check that `"enabled": true` in config
- Ensure you're currently live streaming
- Review logs for API errors

### API quota exceeded
- Increase `polling_interval` to 60+ seconds
- Disable unused features in config
- Check quota usage in Google Cloud Console

For more troubleshooting, see [YOUTUBE_SETUP.md](YOUTUBE_SETUP.md).

## Future Enhancements

Planned features:
- [ ] OAuth authentication for private stream data
- [ ] Advanced stream health metrics (bitrate, dropped frames)
- [ ] Historical statistics tracking
- [ ] Multi-platform support (Twitch, etc.)
- [ ] Custom alert thresholds and notifications
- [ ] Stream event notifications (new subscriber, raid, etc.)
- [ ] Chat message display overlay
- [ ] Customizable widget positioning

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

*License information to be added*

## Acknowledgments

- Built with [Kivy](https://kivy.org/) framework
- Uses [Google YouTube Data API v3](https://developers.google.com/youtube/v3)
- Designed for Raspberry Pi but works on any Linux system with display

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review [YOUTUBE_SETUP.md](YOUTUBE_SETUP.md) for YouTube-specific issues
3. Open an issue on GitHub with detailed error messages

---

**Note**: This project is designed for personal use by content creators. Always protect your API keys and never commit them to version control.
