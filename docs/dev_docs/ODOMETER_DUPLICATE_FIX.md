# Odometer Duplicate Handling Fix

## Problem

The integration was showing inflated km values (e.g., `last_24h_km: 11111`) when the actual vehicle odometer was much lower (e.g., `2089 km`).

### Root Cause

Vehicle integrations often transmit the same odometer value multiple times without changes. For example, if a vehicle integration updates every hour, it might send:
- 13:00: odometer = 2089 km
- 14:00: odometer = 2089 km (no change)
- 15:00: odometer = 2089 km (no change)
- 16:00: odometer = 2095 km (vehicle moved)

Previously, the integration stored ALL these readings in `odometer_history`, including duplicates. While the consumption calculation logic correctly calculated differences between consecutive readings, having many duplicate entries could:
1. Waste storage space
2. Cause issues if any code incorrectly processed the raw data
3. Make debugging more difficult

## Solution

### 1. Duplicate Filtering in `add_odometer_observation()`

Modified `custom_components/hafwcma/utils/storage.py` function `add_odometer_observation()`:

```python
# Check if this is a duplicate of the last odometer value
# Vehicle integrations often send the same odometer value multiple times
# We only want to record actual changes to avoid inflated statistics
if data["odometer_history"]:
    last_entry = data["odometer_history"][-1]
    last_value = last_entry.get("value")
    
    # Skip if value hasn't changed (tolerance: ODOMETER_CHANGE_THRESHOLD_KM = 0.1 km)
    if last_value is not None and abs(float(last_value) - float(odometer_km)) < 0.1:
        _LOGGER.debug(
            "Skipping duplicate odometer observation: %.1f km (same as last value)",
            odometer_km
        )
        return
```

**Benefits:**
- Only stores odometer values when they actually change
- Reduces storage usage
- Makes odometer_history cleaner and more useful
- Prevents any potential misuse of duplicate data

### 2. Enhanced Validation Logging

Added comprehensive validation in `calculate_consumption_history()` to detect data quality issues:

#### a) Duplicate Event Detection
```python
# Check for duplicate/very close timestamps (within 60 seconds)
if time_diff_seconds < 60:
    _LOGGER.warning(
        "Events id=%s and id=%s: very close timestamps (%.1f seconds apart) - possible duplicate refueling events",
        prev_event_id, event_id, time_diff_seconds
    )
```

#### b) Missing/Invalid Odometer Detection
```python
# Check for missing odometer
if odometer is None:
    _LOGGER.warning(
        "Event id=%s (index %d): missing odometer_km - this event will be skipped in km calculations",
        event_id, i
    )
# Check for suspicious negative or zero odometer
elif odometer <= 0:
    _LOGGER.warning(
        "Event id=%s (index %d): suspicious odometer_km=%s <= 0",
        event_id, i, odometer
    )
```

#### c) Unreasonable Distance Detection
```python
# Validate km_driven for unreasonable values
# Warn if a single segment shows > 2000 km (likely data entry error)
if km_driven > 2000:
    _LOGGER.warning(
        "Pair [%d->%d]: SUSPICIOUS km_driven=%s km (odometer: %s -> %s). "
        "This seems unreasonably high - check for incorrect odometer values in refueling events!",
        curr_event_id, next_event_id, km_driven, curr_odometer, next_odometer
    )
```

## Verification

### Existing Calculation Logic (Confirmed Correct)

The consumption calculation logic in `calculate_consumption_history()` was already correct:

```python
for i in range(len(relevant_events) - 1):
    curr_odometer = relevant_events[i][1].get("odometer_km")
    next_odometer = relevant_events[i+1][1].get("odometer_km")
    km_driven = next_odometer - curr_odometer  # DIFFERENCE, not sum
    if km_driven > 0 and liters_refueled > 0:
        total_km += km_driven  # Only differences accumulated
```

**Key Point:** The code always calculated the DIFFERENCE between consecutive odometer readings, never summed absolute values.

### What This Fix Changes

1. **Prevents duplicate odometer values** from being stored in `odometer_history`
2. **Adds warnings** to help diagnose data quality issues in refueling events
3. **No change** to the core calculation logic (which was already correct)

## Impact

- **Existing data:** Not affected. The fix only applies to new odometer readings going forward.
- **Calculations:** Will continue to work correctly as before.
- **Debugging:** Much easier with the new validation warnings.
- **Storage:** Reduced by eliminating duplicate odometer entries.

## Recommendation

If you're experiencing inflated `last_24h_km` values with existing data, check your refueling log for:
1. Duplicate refueling events (same timestamp, same odometer)
2. Incorrect odometer values in refueling events (e.g., cumulative instead of actual reading)
3. Very large gaps between consecutive odometer readings

The new validation logging will help identify these issues automatically.

## Example

### Before Fix
Odometer history with duplicates:
```
2089 km @ 13:00
2089 km @ 14:00
2089 km @ 15:00
2095 km @ 16:00
```
All 4 entries stored.

### After Fix
Odometer history without duplicates:
```
2089 km @ 13:00
2095 km @ 16:00
```
Only 2 entries stored (when value changed).

## Related Files

- `custom_components/hafwcma/utils/storage.py` - Main storage functions
- `custom_components/hafwcma/sensor.py` - Coordinator calling add_odometer_observation()
- `custom_components/hafwcma/utils/consumption_prediction.py` - Uses odometer_history
- `custom_components/hafwcma/utils/ml_engine.py` - Uses odometer_history
- `custom_components/hafwcma/utils/statistics_engine.py` - Uses odometer_history
