# FWCAM Card Troubleshooting Guide

## Trip Log Not Displaying

If your trip log is showing "No trips recorded yet" even though you have trip data in the sensor, follow these debugging steps:

### 1. Check Browser Console

Open your browser's developer console (F12) and look for FWCAM Card debug messages:

```
[FWCAM Card] Trip Log Entity: sensor.test_car_trip_log
[FWCAM Card] Trip Log Entity State: {...}
[FWCAM Card] Recent Trips: [...]
```

### 2. Verify Entity Naming

The card auto-detects the trip log sensor based on your main entity name:

**Configuration:**
```yaml
entity: sensor.test_car_refueling_log
```

**Expected trip log entity:**
```
sensor.test_car_trip_log
```

The card removes `_refueling_log` and adds `_trip_log` to find the trip sensor.

### 3. Verify Sensor Data

Check your trip log sensor in Developer Tools → States:

1. Look for `sensor.[your_car]_trip_log`
2. Check attributes for `recent_trips` array
3. Verify `recent_trips` has data

Example:
```yaml
attributes:
  recent_trips:
    - timestamp_start: "2026-02-14T19:21:03"
      timestamp_end: "2026-02-14T19:34:15"
      distance_km: 1
      category: private
      # ... more fields
```

### 4. Configuration Solutions

If auto-detection isn't working, explicitly specify the trip log entity:

```yaml
type: custom:fwcam-card
entity: sensor.test_car_refueling_log
trip_log_entity: sensor.test_car_trip_log  # Explicitly specify
show_trip_log: true
```

### 5. Common Issues

**Issue: All sections showing when only one requested**

Before v0.0.86:
```yaml
type: custom:fwcam-card
entity: sensor.test_car_refueling_log
show_trip_log: true
# This showed ALL sections (bug)
```

After v0.0.86:
```yaml
type: custom:fwcam-card
entity: sensor.test_car_refueling_log
show_trip_log: true
# This shows ONLY trip log (fixed)
```

**Issue: Browser cache**

After updating the integration:
1. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
2. Hard refresh the page
3. Close and reopen browser
4. Check Home Assistant logs for card loading messages

**Issue: Entity not found**

If you see "Entity not found" errors:
1. Ensure trip tracking is enabled in integration settings
2. Verify the trip log sensor exists in Developer Tools → States
3. Check integration logs for errors
4. Try importing historical trip data using the button

### 6. Enable Debug Logging

The card automatically logs debug information when `show_trip_log: true` is set. Check the browser console for:

- Entity ID being used
- Entity state object
- Recent trips data

### 7. Report Issues

If problems persist, report with:
1. Your card configuration (YAML)
2. Browser console logs
3. Screenshot of Developer Tools → States showing your trip_log sensor
4. Home Assistant version and integration version
