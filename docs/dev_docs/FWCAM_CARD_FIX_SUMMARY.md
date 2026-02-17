# FWCAM Card Configuration Fix - User Guide

## Problem Summary

The user reported several issues with the FWCAM Lovelace card:

1. Trip log data exists in sensor attributes but shows "No trips recorded yet"
2. When configuring only `show_trip_log: true`, all other sections were still displayed
3. Request for more intuitive configuration with separate entities per section

## Solutions Implemented

### 1. Fixed Configuration Behavior

**Old Behavior (v0.0.85 and earlier):**
```yaml
type: custom:fwcam-card
entity: sensor.test_car_refueling_log
show_trip_log: true
# Problem: This showed ALL sections, not just trip log
```

**New Behavior (v0.0.86+):**
```yaml
type: custom:fwcam-card
entity: sensor.test_car_refueling_log
show_trip_log: true
# ✅ Now shows ONLY trip log, all others hidden
```

### 2. Smart Default Behavior

The card now has intelligent defaults:

- **No show_* options specified** → All sections visible (backward compatibility)
- **Any show_* option specified** → Only explicitly enabled sections visible

Examples:

**Show everything (default):**
```yaml
type: custom:fwcam-card
entity: sensor.test_car_refueling_log
# All sections shown
```

**Show only specific sections:**
```yaml
type: custom:fwcam-card
entity: sensor.test_car_refueling_log
show_refueling_log: true
show_trip_log: true
# Only refueling and trip logs shown
```

### 3. Separate Entity Configuration

You can now specify different entities for each section:

```yaml
type: custom:fwcam-card
entity: sensor.test_car_refueling_log
trip_log_entity: sensor.test_car_trip_log
refueling_log_entity: sensor.test_car_refueling_log
show_trip_log: true
show_refueling_log: true
```

### 4. Enhanced Debugging

The card now provides detailed console logging when `show_trip_log: true`:

Open Browser Console (F12) to see:
```
[FWCAM Card] Trip Log Debugging:
  - Expected Entity ID: sensor.test_car_trip_log
  - Entity Found: Yes
  - Entity State: 83
  - Has recent_trips: Yes
  - Recent Trips Count: 10
  - Recent Trips Data: [...]
```

## How to Use Your Card

Based on your configuration, here's what you should do:

### Configuration 1: Show Only Trip Log
```yaml
type: custom:fwcam-card
entity: sensor.test_car_refueling_log
show_trip_log: true
```

This will now show ONLY the trip log section.

### Configuration 2: Show Only Trip Log with Explicit Entity
```yaml
type: custom:fwcam-card
entity: sensor.test_car_refueling_log
trip_log_entity: sensor.test_car_trip_log
show_trip_log: true
```

This explicitly tells the card which entity to use for trip data.

## Troubleshooting

If you still see "No trips recorded yet":

1. **Clear Browser Cache**
   - Press Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
   - Or close and reopen browser completely

2. **Check Console Logs**
   - Open browser console (F12)
   - Look for `[FWCAM Card] Trip Log Debugging` messages
   - Verify entity is found and has data

3. **Verify Sensor**
   - Go to Developer Tools → States
   - Search for `sensor.test_car_trip_log`
   - Check `recent_trips` attribute has data

4. **Check Integration**
   - Ensure trip tracking is enabled
   - Try the "Import Historical Trip Data" button
   - Check integration logs for errors

## What Changed in the Code

### Main Changes in `fwcam-card.js`

1. **Configuration Logic** (lines 48-88)
   - Added `hasExplicitShowOptions` detection
   - Changed default behavior based on explicit configuration
   - Added support for separate entity configuration

2. **Render Method** (lines 467-497)
   - Support for `trip_log_entity` configuration
   - Enhanced debug logging
   - Better entity detection

3. **Safety Improvements**
   - Use `Object.prototype.hasOwnProperty.call()` for property checks
   - Safer handling of missing entities

## Testing

All configuration scenarios have been tested and pass:
- ✅ Default behavior (all sections visible)
- ✅ Single section explicit (only that section visible)
- ✅ Multiple sections explicit (only specified sections visible)
- ✅ Separate entity configuration (entity override works)

## Next Steps for Users

1. Update your Home Assistant integration to include these changes
2. Clear browser cache
3. Refresh your Lovelace dashboard
4. Check browser console for debug messages
5. Verify trip log displays correctly

If issues persist, refer to `docs/FWCAM_CARD_TROUBLESHOOTING.md` for detailed troubleshooting steps.
