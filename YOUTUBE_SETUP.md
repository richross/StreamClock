# YouTube Live Streaming API Integration Guide

## Overview

StreamClock now supports YouTube Live Streaming API integration to display real-time stream statistics during your broadcasts. This guide will walk you through setting up and configuring the YouTube API integration.

## Features

- **Live Status Indicator**: Shows whether your channel is currently live
- **Viewer Count**: Real-time concurrent viewer count
- **Stream Duration**: Elapsed time since stream started
- **Chat Activity**: Messages per minute rate
- **Subscriber Count**: Current subscriber count with live updates
- **Stream Health Monitoring**: Connection quality and performance metrics
- **Graceful Degradation**: Clock continues working even if API is unavailable

## Prerequisites

- YouTube channel with streaming enabled
- Google Cloud Platform account
- Python 3.11+ with pip

## Setup Instructions

### 1. Create Google Cloud Project and Enable YouTube API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **YouTube Data API v3**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"

### 2. Create API Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "API Key"
3. Copy your API key (you'll need this later)
4. **Recommended**: Restrict your API key:
   - Click on the API key to edit it
   - Under "API restrictions", select "Restrict key"
   - Choose "YouTube Data API v3"
   - Under "Application restrictions", you can restrict by IP or HTTP referrer

### 3. Get Your YouTube Channel ID

You can find your channel ID in several ways:

**Method 1: YouTube Studio**
1. Go to [YouTube Studio](https://studio.youtube.com)
2. Click on "Settings" (bottom left)
3. Select "Channel" > "Advanced settings"
4. Your Channel ID is displayed at the bottom

**Method 2: From Your Channel URL**
- If your URL is `youtube.com/channel/CHANNEL_ID`, the ID is in the URL
- If your URL is `youtube.com/@username`, you'll need to use Method 1 or 3

**Method 3: Using YouTube API**
```bash
curl "https://www.googleapis.com/youtube/v3/channels?part=id&forUsername=YOUR_USERNAME&key=YOUR_API_KEY"
```

### 4. Install Required Dependencies

```bash
# Activate your virtual environment (if using one)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Configure StreamClock

1. Copy the example configuration file:
   ```bash
   cp config.json.example config.json
   ```

2. Edit `config.json` and add your credentials:
   ```json
   {
     "youtube": {
       "api_key": "YOUR_API_KEY_HERE",
       "channel_id": "YOUR_CHANNEL_ID_HERE",
       "enabled": true,
       "polling_interval": 30,
       "features": {
         "viewer_count": true,
         "stream_duration": true,
         "chat_activity": true,
         "stream_status": true,
         "subscriber_count": true,
         "stream_health": true
       }
     },
     "display": {
       "show_offline_message": true,
       "compact_mode": false
     }
   }
   ```

3. **Important**: Never commit `config.json` to version control (it's already in `.gitignore`)

### 6. Alternative: Use Environment Variables

Instead of `config.json`, you can set environment variables:

```bash
export YOUTUBE_API_KEY="your_api_key"
export YOUTUBE_CHANNEL_ID="your_channel_id"
```

Then set `"enabled": true` in your config file, or create a minimal config:
```json
{
  "youtube": {
    "enabled": true
  }
}
```

## Configuration Options

### YouTube Settings

- **`api_key`** (string): Your YouTube Data API v3 key
- **`channel_id`** (string): Your YouTube channel ID
- **`enabled`** (boolean): Enable/disable YouTube integration
- **`polling_interval`** (integer): Seconds between API polls (default: 30)
  - Minimum recommended: 30 seconds
  - Lower values increase API quota usage

### Feature Toggles

Enable or disable individual features in `youtube.features`:

- **`viewer_count`**: Show concurrent viewer count
- **`stream_duration`**: Show elapsed stream time
- **`chat_activity`**: Show chat messages per minute
- **`stream_status`**: Show live/offline indicator
- **`subscriber_count`**: Show subscriber count
- **`stream_health`**: Show connection quality metrics

### Display Settings

- **`show_offline_message`** (boolean): Show widget when offline
- **`compact_mode`** (boolean): Use compact single-line display instead of full widget

## Usage

Simply start the clock app as normal:

```bash
./start_clock.sh
# or
python3 clock_app.py
```

When configured correctly:
- The app will connect to YouTube API on startup
- Stream statistics will appear in the top-right corner
- Updates occur automatically based on `polling_interval`
- If you're not live, it will show "OFFLINE"
- When you go live, statistics will appear automatically

## API Quota and Rate Limiting

### Understanding YouTube API Quotas

YouTube Data API v3 has daily quota limits:
- Default quota: 10,000 units per day
- Each API call costs different amounts:
  - `liveBroadcasts.list`: 1 unit
  - `videos.list`: 1 unit
  - `channels.list`: 1 unit
  - `liveChatMessages.list`: 5 units

### Quota Usage Estimation

With default settings (30-second polling):
- ~2,880 polls per day
- ~8-12 units per poll (depending on enabled features)
- Total: ~25,000-35,000 units per day

**Recommendation**: Use a 30-60 second polling interval to stay within quota limits.

### Rate Limiting

The integration includes built-in rate limiting:
- Minimum 1 second between individual API calls
- Polling interval controls update frequency
- Caching reduces redundant API calls

## Troubleshooting

### "YouTube integration not available"

**Cause**: Required Python packages not installed

**Solution**:
```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

### "API Error: 403"

**Possible causes**:
1. Invalid API key
2. YouTube Data API v3 not enabled
3. API key restrictions blocking the request
4. Quota exceeded

**Solutions**:
1. Verify API key in config.json
2. Check that YouTube Data API v3 is enabled in Google Cloud Console
3. Review API key restrictions
4. Check quota usage in Google Cloud Console

### "No stream data showing"

**Possible causes**:
1. YouTube integration disabled in config
2. Not currently live streaming
3. Invalid channel ID
4. API errors (check logs)

**Solutions**:
1. Set `"enabled": true` in config
2. Start a live stream on YouTube
3. Verify channel ID is correct
4. Check console output for error messages

### Stream stats not updating

**Possible causes**:
1. Network connectivity issues
2. API quota exceeded
3. Polling interval too long

**Solutions**:
1. Check internet connection
2. Review quota usage in Google Cloud Console
3. Reduce `polling_interval` (but not below 30 seconds)

## Security Best Practices

1. **Never commit API keys**: The `config.json` file is in `.gitignore`
2. **Restrict API keys**: Use IP/referrer restrictions in Google Cloud Console
3. **Use environment variables**: For deployment, prefer environment variables over config files
4. **Rotate keys regularly**: Generate new API keys periodically
5. **Monitor usage**: Check Google Cloud Console for unexpected API usage

## Testing Without a Live Stream

To test the integration without actually going live:

1. Configure with valid API key and channel ID
2. Run the app - it should show "OFFLINE"
3. Check logs for any errors
4. When you go live, stats should appear automatically

## Advanced Configuration

### Custom Polling Intervals

Different features can benefit from different update rates:

```json
{
  "youtube": {
    "polling_interval": 30,  // Main interval for most features
    "chat_polling_interval": 10  // Faster updates for chat (not yet implemented)
  }
}
```

### Selective Feature Disabling

To reduce API quota usage, disable features you don't need:

```json
{
  "youtube": {
    "features": {
      "viewer_count": true,
      "stream_duration": true,
      "chat_activity": false,  // Disable to save quota
      "stream_status": true,
      "subscriber_count": false,  // Disable to save quota
      "stream_health": false  // Not yet fully implemented
    }
  }
}
```

## API Reference

For more details on the YouTube Data API v3, see:
- [YouTube Data API Documentation](https://developers.google.com/youtube/v3)
- [API Quota Calculator](https://developers.google.com/youtube/v3/determine_quota_cost)
- [API Reference](https://developers.google.com/youtube/v3/docs)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review application logs for error messages
3. Verify API quota usage in Google Cloud Console
4. Open an issue on the GitHub repository

## Future Enhancements

Planned features for future releases:
- OAuth authentication for private stream data
- Advanced stream health metrics
- Historical statistics tracking
- Multi-platform support (Twitch, etc.)
- Custom alert thresholds
- Stream event notifications
