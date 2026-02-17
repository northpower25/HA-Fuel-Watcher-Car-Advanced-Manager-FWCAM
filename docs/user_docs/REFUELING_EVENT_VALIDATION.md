# Refueling Event Validation and Filtering

## Problem

Test refueling events (created for testing APIs or input forms) can pollute consumption calculations, leading to unrealistic values and user confusion. Similarly, incorrectly entered data (wrong odometer values, dates, etc.) can cause the same issues.

## Solution

The integration now includes an automatic validation system that:
1. Detects suspicious/invalid refueling events
2. Excludes them from consumption calculations
3. Provides UI controls to manage event validation
4. Maintains data integrity while allowing manual override

## How It Works

### 1. Event Validation

Each refueling event is validated against multiple criteria:

#### Timestamp Validation
- **Future events**: Events more than 1 hour in the future are flagged
- **Purpose**: Prevents accidentally entered future dates

#### Station Name Validation
- **Test indicators**: Station names containing "test", "api test", "demo", "example", "xxxx", "1111", "9999" are flagged
- **Purpose**: Automatically detects test/demo events

#### Fuel Amount Validation
- **Negative/zero**: Fuel amount must be positive
- **Unrealistic maximum**: More than 200L is flagged as unrealistic
- **Purpose**: Catches data entry errors

#### Odometer Validation
- **Positive values**: Odometer must be positive
- **Future odometer**: Odometer significantly higher than current vehicle odometer is flagged
- **Backwards progression**: Odometer decreasing over time is flagged
- **Unrealistic jumps**: 
  - More than 200 km/h average speed between events
  - More than 5000 km in less than 24 hours
- **Purpose**: Ensures logical progression of odometer values

### 2. Automatic Exclusion

When validation detects an issue:
1. The event's `excluded_from_calculation` field is set to `True`
2. The `exclusion_reason` field explains why it was excluded
3. The event remains in the log but doesn't affect calculations
4. Users can manually include/exclude events as needed

### 3. Calculation Filtering

The `calculate_consumption_history()` function now:
1. Skips events where `excluded_from_calculation` is `True`
2. Logs excluded events for debugging
3. Reports exclusion count in debug logs

Example log output:
```
calculate_consumption_history(7 days): found 5/8 events in period (3 excluded from calculation)
Event id=123: EXCLUDED from calculation (reason: Auto-validation: Station name contains test indicator: 'test')
```

## Using the System

### Automatic Validation Button

**Location**: Device page → "Validate Refueling Events" button

**What it does**:
1. Scans all refueling events
2. Validates each against logical criteria
3. Excludes suspicious events automatically
4. Forces consumption recalculation

**Button Attributes**:
- `success`: Whether validation completed successfully
- `timestamp`: When validation was run
- `total_events`: Total number of events
- `validated`: Events checked (not already excluded)
- `newly_excluded`: Events newly flagged as invalid
- `already_excluded`: Events already excluded
- `excluded_event_ids`: List of all excluded event IDs

**When to use**:
- After importing historical data
- After manual data entry
- When consumption values seem unrealistic
- Periodically for data hygiene

### Manual Include/Exclude

Events can be manually managed through the Lovelace card:

1. **View exclusion status**: 
   - Refueling Log Sensor shows `excluded_from_calculation` field
   - Recent events include `exclusion_reason`

2. **Manual override**:
   - Edit event through Lovelace card
   - Set `excluded_from_calculation` to `true` or `false`
   - Optionally add custom `exclusion_reason`

### Viewing Exclusion Information

**Refueling Log Sensor Attributes**:
```yaml
total_events: 10
total_excluded: 2
total_active: 8
status: "10 refueling events recorded (2 excluded from calculations)"

recent_events:
  - id: 123
    excluded_from_calculation: true
    exclusion_reason: "Auto-validation: Station name contains test indicator: 'test'"
    # ... other fields
  - id: 124
    excluded_from_calculation: false
    exclusion_reason: null
    # ... other fields
```

## Validation Criteria Details

### Test Event Detection

**Triggers exclusion when station name contains**:
- "test" (case-insensitive)
- "api test"
- "demo"
- "example"
- "xxxx"
- "1111"
- "9999"

**Examples that would be flagged**:
- "Test Station"
- "API Test Refueling"
- "Demo Event XXXX"

### Odometer Logic Validation

**Backwards progression example**:
```
Event #100: 2026-02-10, 2000 km ✓
Event #101: 2026-02-12, 1800 km ✗ (went backwards by 200 km)
```

**Unrealistic jump example**:
```
Event #100: 2026-02-10 10:00, 2000 km ✓
Event #101: 2026-02-10 11:00, 2300 km ✗ (300 km in 1 hour = 300 km/h average)
```

**Validation allows**:
- Normal driving patterns (up to 200 km/h average)
- Up to 5000 km per day (for edge cases like long trips)
- Clock skew up to 1 hour for future events

### Confidence-Based Filtering

Events already have a `confidence` field (0.0-1.0):
- `1.0`: Manual entry or high-quality auto-detection
- `0.5-0.9`: Auto-detected with some uncertainty
- `< 0.5`: Low confidence detection

**Current behavior**: All confidence levels are included in calculations if not explicitly excluded

**Future enhancement**: Could add minimum confidence threshold configuration

## Integration with Existing Features

### Data Quality Warnings

Works together with the data quality warning system:
1. **Warnings detect** suspicious patterns in results
2. **Validation prevents** suspicious events from affecting results

**Workflow**:
1. User sees data quality warning: "Today shows 11111 km driven"
2. User presses "Validate Refueling Events" button
3. System excludes test events automatically
4. Consumption recalculates with valid data only
5. Warning disappears

### Historical Import

During historical data import:
1. Events are created with timestamps from historical data
2. Auto-validation can be run afterwards to clean up any issues
3. Imported events with low confidence might need manual review

### Recalculation

The existing "Recalculate Trip Statistics" button:
1. Forces consumption prediction update
2. Works with validated data (excluded events are skipped)
3. Complementary to validation button

**Recommended workflow**:
1. Validate events first
2. Then recalculate statistics

## Examples

### Example 1: Test Event After API Testing

**Scenario**: Developer tests Telegram API by creating fake refueling event

**Before validation**:
```yaml
Event #50:
  station_name: "Test API Event"
  odometer_km: 5000
  liters_refueled: 40
  excluded_from_calculation: false
```

**Consumption calculation**: Includes this test event, causing unrealistic values

**After pressing "Validate Refueling Events"**:
```yaml
Event #50:
  station_name: "Test API Event"
  odometer_km: 5000
  liters_refueled: 40
  excluded_from_calculation: true
  exclusion_reason: "Auto-validation: Station name contains test indicator: 'test'"
```

**Consumption calculation**: Skips this event, shows realistic values

### Example 2: Incorrect Odometer Entry

**Scenario**: User accidentally enters 12000 instead of 1200 for odometer

**Before validation**:
```yaml
Event #45: 2026-02-10, odometer: 1150 km ✓
Event #46: 2026-02-12, odometer: 12000 km (typo - should be 1200)
Event #47: 2026-02-14, odometer: 1250 km ✓
```

**Consumption shows**: Unrealistic 10850 km in 2 days

**After validation**:
```yaml
Event #46:
  excluded_from_calculation: true
  exclusion_reason: "Auto-validation: Unrealistic distance: 10850 km in 48.0h vs event #45"
```

**User action**: 
1. Sees event #46 is excluded
2. Edits odometer to correct value (1200)
3. Sets `excluded_from_calculation` back to `false`
4. Recalculates

### Example 3: Manual Override

**Scenario**: User intentionally creates test event for learning, wants it excluded

**Action**:
1. Create refueling event through Lovelace card
2. Edit event, set `excluded_from_calculation: true`
3. Set `exclusion_reason: "Training/demo event"`
4. Event remains in log but doesn't affect calculations

## Technical Details

### New Fields in Refueling Events

```python
{
    "id": 123,
    "timestamp": "2026-02-17T10:00:00+01:00",
    "odometer_km": 2000,
    # ... other fields ...
    "excluded_from_calculation": False,  # NEW: Exclude from calculations
    "exclusion_reason": None,  # NEW: Why excluded (optional)
}
```

### Validation Function

```python
async def validate_refueling_event(
    hass: HomeAssistant,
    entry: ConfigEntry,
    event: dict[str, Any],
    vehicle_odometer: float | None = None,
) -> tuple[bool, str | None]:
    """Validate a refueling event.
    
    Returns:
        (is_valid, reason_if_invalid)
    """
```

**Checks performed**:
1. Timestamp parsing and future check
2. Test indicator detection
3. Fuel amount validation
4. Odometer logical progression
5. Speed/distance reasonableness

### Auto-Validation Function

```python
async def auto_validate_refueling_events(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Validate all events and mark suspicious ones.
    
    Returns:
        {
            "total_events": int,
            "validated": int,
            "newly_excluded": int,
            "already_excluded": int,
            "excluded_events": [list of IDs],
        }
    """
```

### Filtering in Calculations

```python
# In calculate_consumption_history()
for event in refueling_log:
    # Skip excluded events
    if event.get("excluded_from_calculation", False):
        excluded_count += 1
        continue
    # ... process event
```

## Best Practices

### For End Users

1. **Run validation after import**: Always validate after importing historical data
2. **Check exclusions**: Review excluded events in Refueling Log Sensor
3. **Manual corrections**: Fix typos in original data rather than leaving them excluded
4. **Keep test events**: Don't delete test events, just exclude them for future reference

### For Developers/Testers

1. **Use test indicators**: Name test stations with "Test" or "Demo" prefix
2. **Run validation**: Clean up test data with validation button
3. **Manual exclusion**: For persistent test events, manually exclude them
4. **Data quality**: Keep test data separate from production data when possible

### For Integration Maintainers

1. **Preserve excluded events**: Don't remove excluded events from storage
2. **Log exclusions**: Always log why events are excluded
3. **Allow override**: Let users manually include/exclude as needed
4. **Conservative thresholds**: Validation thresholds should minimize false positives

## Troubleshooting

### Valid Events Being Excluded

**Symptom**: Legitimate refueling events are marked as excluded

**Causes**:
- Station name happens to contain "test" (e.g., "Test Station GmbH")
- Unusual driving pattern (very long trip, very high speed average)

**Solution**:
1. Check `exclusion_reason` in event attributes
2. Manually set `excluded_from_calculation: false`
3. Optionally report threshold adjustments needed

### Test Events Not Being Excluded

**Symptom**: Test events still included in calculations after validation

**Causes**:
- Station name doesn't contain test indicators
- Event passes all validation checks

**Solution**:
1. Manually edit event
2. Set `excluded_from_calculation: true`
3. Set `exclusion_reason: "Manual - test event"`

### Consumption Still Wrong After Validation

**Symptom**: Values still unrealistic after running validation

**Possible causes**:
1. **Multiple issues**: More than one problematic event
2. **Data entry errors**: Incorrect values that pass validation
3. **Missing data**: Insufficient valid events for calculation

**Debug steps**:
1. Check Refueling Log Sensor attributes
2. Review `total_excluded` vs `total_active`
3. Check logs for "SUSPICIOUS DATA" warnings
4. Manually review each event's values

## Future Enhancements

Potential improvements for future versions:

1. **Configurable thresholds**: Allow users to adjust validation thresholds
2. **Confidence filtering**: Option to exclude low-confidence events
3. **Bulk operations**: UI to include/exclude multiple events at once
4. **Validation on entry**: Validate events immediately when created
5. **Undo exclusions**: Track exclusion history for easy undo
6. **Smart suggestions**: Suggest corrections for invalid values
7. **Pattern learning**: Learn user's normal patterns to improve validation

## Related Documentation

- [CONSUMPTION_DATA_QUALITY_FIX.md](CONSUMPTION_DATA_QUALITY_FIX.md) - Data quality warning system
- [VERBRAUCHSBERECHNUNG_ERKLAERT_DE.md](VERBRAUCHSBERECHNUNG_ERKLAERT_DE.md) - How consumption calculation works
