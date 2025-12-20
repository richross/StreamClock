# YouTube Toggle Button - Visual Mockup

## Button Appearance

### When YouTube Integration is DISABLED (Red):
```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                           │
│                          ┌────────────────────┐                          │
│                          │  ● OFFLINE         │  (YouTube widget)        │
│                          │  📊 25,678 subs     │                          │
│                          └────────────────────┘                          │
│                                                                           │
│                         12:34:56                                          │
│                  Monday, December 20, 2025                                │
│                                                                           │
│                                                      ┌──────┐             │
│                                                      │YT ✗ │ (Red)        │
│                                                      └──────┘             │
└─────────────────────────────────────────────────────────────────────────┘
```

### When YouTube Integration is ENABLED (Green):
```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                           │
│                          ┌────────────────────┐                          │
│                          │  ● LIVE            │  (YouTube widget)        │
│                          │  👥 1,234 viewers   │                          │
│                          │  ⏱️  01:45:30       │                          │
│                          └────────────────────┘                          │
│                                                                           │
│                         12:34:56                                          │
│                  Monday, December 20, 2025                                │
│                                                                           │
│                                                      ┌──────┐             │
│                                                      │YT ✓ │ (Green)      │
│                                                      └──────┘             │
└─────────────────────────────────────────────────────────────────────────┘
```

## Button Specifications

**Position:** Lower right corner
- `pos_hint={'right': 0.98, 'y': 0.02}`
- 2% margin from bottom and right edges

**Size:** 50sp × 50sp (small button)

**Colors:**
- **Disabled State:** Red background `(0.8, 0.2, 0.2, 0.8)` with text "YT ✗"
- **Enabled State:** Green background `(0.2, 0.8, 0.2, 0.8)` with text "YT ✓"
- **Text Color:** White `(1, 1, 1, 1)`

**Behavior:**
- Clicking the button toggles YouTube integration on/off
- State is saved to config.json immediately
- YouTube widget appears/disappears dynamically
- No app restart needed

## Runtime Behavior

### Initial State (App Startup)
1. Button appears in lower right corner
2. Button color reflects current config.json setting
3. If enabled=true in config, button is green and widget is visible
4. If enabled=false in config, button is red and widget is hidden

### Toggle to Enable
1. User clicks red "YT ✗" button
2. Button changes to green "YT ✓"
3. YouTube service initializes
4. YouTube widget appears in top-right corner
5. Background polling starts
6. config.json updated with `"enabled": true`
7. Change persists across app restarts

### Toggle to Disable
1. User clicks green "YT ✓" button
2. Button changes to red "YT ✗"
3. Background polling stops
4. YouTube widget disappears from screen
5. YouTube service cleaned up
6. config.json updated with `"enabled": false`
7. Change persists across app restarts

## Configuration File Updates

The button modifies the config.json file in real-time:

**Before toggle (disabled):**
```json
{
  "youtube": {
    "enabled": false,
    ...
  }
}
```

**After toggle (enabled):**
```json
{
  "youtube": {
    "enabled": true,
    ...
  }
}
```

## Technical Details

### Dynamic Loading
- Config is read at startup
- Button toggles the `youtube.enabled` value
- Changes are saved to disk immediately using `config.save()`
- YouTube service starts/stops dynamically without app restart

### Widget Management
- When enabled: Widget is added to root FloatLayout
- When disabled: Widget is removed from root FloatLayout
- No memory leaks - proper cleanup of threads and services

### Thread Safety
- Background polling thread starts when enabled
- Thread properly stopped and cleaned up when disabled
- No orphaned threads or processes

## User Experience

**Advantages:**
- No need to edit config.json manually
- No need to restart the app
- Instant feedback (button color change)
- Persists across restarts
- Simple one-click toggle

**Use Cases:**
1. Quick disable during non-streaming hours (saves API quota)
2. Troubleshooting API issues (disable/enable to reset connection)
3. Testing without YouTube integration
4. Battery saving on Raspberry Pi (stop background polling)
