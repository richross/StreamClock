# StreamClock YouTube Integration - Visual Guide

## Display Layout

### Full Widget Mode (Default)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                           │
│                                                                           │
│                          ┌────────────────────┐                          │
│                          │  ● LIVE            │                          │
│                          │  👥 1,234 viewers   │                          │
│                          │  ⏱️  01:45:30       │                          │
│                          │  💬 15.2 msg/min    │                          │
│                          │  📊 25,678 subs     │                          │
│                          └────────────────────┘                          │
│                                                                           │
│                         12:34:56                                          │
│                  Monday, December 20, 2025                                │
│                                                                           │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

**Widget Position:** Top-right corner (98% from left, 98% from top)
**Background:** Semi-transparent black (60% opacity)
**Font Size:** 14-16sp
**Live Indicator:** Red dot (● LIVE) when streaming, gray when offline

### Compact Mode

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                           │
│                           ● LIVE | 1,234👥 | 01:45⏱️                     │
│                                                                           │
│                                                                           │
│                         12:34:56                                          │
│                  Monday, December 20, 2025                                │
│                                                                           │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

**Widget Position:** Top-right corner
**Background:** Semi-transparent black (60% opacity)
**Font Size:** 14sp
**Format:** Single-line with pipe separators

### Offline State

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                           │
│                                                                           │
│                          ┌────────────────────┐                          │
│                          │  ● OFFLINE         │                          │
│                          │  📊 25,678 subs     │                          │
│                          └────────────────────┘                          │
│                                                                           │
│                         12:34:56                                          │
│                  Monday, December 20, 2025                                │
│                                                                           │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

**Offline Indicator:** Gray dot with "OFFLINE" text
**Displayed Info:** Only non-stream-specific stats (like subscriber count)

## Color Scheme

- **Live Status (Active):** Red (#ff3333) - `(1, 0.2, 0.2, 1)`
- **Offline Status:** Gray (#b3b3b3) - `(0.7, 0.7, 0.7, 1)`
- **Regular Text:** White - `(1, 1, 1, 1)`
- **Error Messages:** Light Red (#ff4d4d) - `(1, 0.3, 0.3, 1)`
- **Background:** Black with 60% opacity - `(0, 0, 0, 0.6)`

## Widget Behavior

### When Stream Starts
1. Widget updates from OFFLINE to LIVE within 30 seconds (or configured polling interval)
2. Red live indicator appears
3. Viewer count, duration, and chat stats become visible
4. Duration counter starts from stream start time

### When Stream Ends
1. Widget updates to OFFLINE state within polling interval
2. Live-specific stats disappear
3. Subscriber count remains visible (if enabled)
4. Gray offline indicator appears

### During Stream
- **Viewer count updates:** Every polling interval (default 30s)
- **Duration updates:** Every 1 second (calculated locally, not from API)
- **Chat activity:** Updated every polling interval with rolling average
- **Subscriber count:** Updated every polling interval

### Error States
- If API fails, error message appears at bottom of widget in red
- Example: "⚠️ API Error: 403..."
- Widget remains visible but shows stale data
- Clock continues functioning normally

## Display Options (Configurable)

### Features Toggle
Users can enable/disable individual features in `config.json`:

```json
"features": {
  "viewer_count": true,      // Show 👥 viewers
  "stream_duration": true,   // Show ⏱️ duration
  "chat_activity": true,     // Show 💬 msg/min
  "stream_status": true,     // Show ● LIVE/OFFLINE
  "subscriber_count": true,  // Show 📊 subscribers
  "stream_health": false     // Show health metrics (future)
}
```

### Display Modes

**Normal Mode (`compact_mode: false`):**
- Full widget with all stats in vertical layout
- ~200px width × ~200px height
- Best for larger displays

**Compact Mode (`compact_mode: true`):**
- Single-line horizontal layout
- Auto-width based on content
- Best for smaller displays or minimal distraction

### Widget Positioning

**Fixed Position:**
- Top-right corner by default
- `pos_hint: {'right': 0.98, 'top': 0.98}`
- 2% margin from edges
- Always visible over clock display
- Does not block main time/date display

## Integration with Clock Display

### Main Clock Elements
- **Time:** Center of screen, 120sp font, bold hours/minutes
- **Date:** Below time, 30sp font
- **Spacers:** 30% vertical space above and below for centering

### YouTube Widget Overlay
- Rendered on top of clock layout using FloatLayout
- Semi-transparent background ensures clock is visible
- Does not interfere with time display or exit button
- Updates independently on 1-second interval

### Exit Functionality
- Invisible full-screen button remains functional
- Tap anywhere (including widget area) to exit
- YouTube widget does not block exit button

## Performance Characteristics

### Resource Usage
- **CPU:** Minimal - updates every 1 second (display) and 30+ seconds (API)
- **Memory:** ~5-10MB additional for YouTube integration
- **Network:** API calls every 30 seconds (configurable)
  - Each API cycle: ~3-5 requests depending on features
  - Total data: <50KB per minute

### Threading Model
- **Main Thread:** Kivy UI and clock updates
- **Background Thread:** YouTube API polling (non-blocking)
- **Thread Safety:** Cache access protected by locks

### API Quota Impact
With default settings (30-second polling, all features enabled):
- ~2,880 API poll cycles per day
- ~8-12 quota units per cycle
- Total: ~25,000-35,000 units/day
- Daily limit: 10,000 units (default) - may need quota increase

## Responsive Behavior

### On API Failures
- Widget shows last known data
- Error message displayed in red
- Clock continues updating normally
- Automatic retry on next polling cycle

### On Configuration Changes
- Requires app restart to apply
- Widget recreated with new settings
- No data loss during transition

### On Network Issues
- Graceful timeout handling
- Error logged but not displayed prominently
- Continues using cached data
- Retries automatically

## Future Enhancements (Planned)

1. **Draggable Widget:** Allow user to reposition widget on screen
2. **Customizable Colors:** User-defined color schemes
3. **Alert Thresholds:** Notifications at viewer milestones
4. **Historical Graphs:** Mini charts of viewer trends
5. **Multi-Platform:** Support for Twitch, Facebook Live, etc.
6. **Stream Events:** Display subscriber notifications, raids, etc.
7. **Chat Overlay:** Show recent chat messages
8. **Advanced Health:** Detailed bitrate, dropped frames, connection quality

## Example Configurations

### Minimal Setup (Subscriber Count Only)
```json
{
  "youtube": {
    "enabled": true,
    "features": {
      "viewer_count": false,
      "stream_duration": false,
      "chat_activity": false,
      "stream_status": true,
      "subscriber_count": true
    }
  },
  "display": {
    "compact_mode": true
  }
}
```

Result: Small widget showing "● OFFLINE | 📊 25,678 subs"

### Full Featured Setup
```json
{
  "youtube": {
    "enabled": true,
    "polling_interval": 30,
    "features": {
      "viewer_count": true,
      "stream_duration": true,
      "chat_activity": true,
      "stream_status": true,
      "subscriber_count": true
    }
  },
  "display": {
    "compact_mode": false
  }
}
```

Result: Full widget with all statistics when live

### Battery Saver Setup (Raspberry Pi Zero)
```json
{
  "youtube": {
    "enabled": true,
    "polling_interval": 60,  // Slower updates
    "features": {
      "viewer_count": true,
      "stream_duration": true,
      "chat_activity": false,  // Disable expensive chat API
      "stream_status": true,
      "subscriber_count": false  // Disable non-essential
    }
  },
  "display": {
    "compact_mode": true  // Minimal rendering
  }
}
```

Result: Compact display, slower updates, reduced API usage
