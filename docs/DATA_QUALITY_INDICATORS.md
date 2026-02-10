# Data Quality Indicators - Implementation Summary

## Overview

This document describes the implementation of data quality indicators for the refueling log feature in the haFWCMA integration.

## Problem Addressed

Users reported several issues with the refueling log:
1. Inability to use the refueling log sensor with ToDo List cards in the GUI
2. Duplicate timestamps in historical refueling events
3. No way to identify automatically detected events that might need manual review

## Solution

### 1. Data Quality Fields

Two new fields have been added to each refueling event record:

#### `data_quality` (string)
Indicates the source of the refueling event:
- **`manual`**: Manually entered by the user (highest quality)
- **`auto_detected`**: Automatically detected during normal operation
- **`historical_import`**: Detected from historical data import

#### `confidence` (float, 0.0-1.0)
A numerical score indicating the quality/reliability of the event data:
- **1.0**: Perfect confidence (all data available, values are reasonable)
- **0.7-0.9**: High confidence (most data available)
- **0.4-0.6**: Medium confidence (some data missing)
- **0.0-0.3**: Low confidence (limited data, manual review recommended)

### 2. Confidence Score Calculation

The confidence score is calculated based on three factors:

1. **Odometer Data Availability** (40% weight)
   - Full points (0.4) if odometer reading was successfully matched
   - Zero points if odometer data is missing or invalid

2. **Price Data Availability** (30% weight)
   - Full points (0.3) if fuel price was found in historical data
   - Zero points if price data is missing

3. **Reasonable Refueling Amount** (30% weight)
   - Full points (0.3) if refueled amount is 10-100% of tank capacity
   - Partial points (0.15) if refueled amount exceeds 100% (suggests measurement error but refueling was detected)
   - Partial points (0.15) if tank capacity is unknown

**Example Calculations:**

```python
# Perfect event: all data available, reasonable amount
odometer = ✓ (0.4)
price = ✓ (0.3)
amount = 45L / 50L tank = 90% ✓ (0.3)
confidence = 1.0

# Good event: missing price data
odometer = ✓ (0.4)
price = ✗ (0.0)
amount = 40L / 50L tank = 80% ✓ (0.3)
confidence = 0.7

# Uncertain event: missing odometer and price
odometer = ✗ (0.0)
price = ✗ (0.0)
amount = 55L / 50L tank = 110% (0.15)
confidence = 0.15  # Needs manual review
```

### 3. Duplicate Detection

Historical data import now checks for duplicate refueling events:
- Compares new events against existing events within a 24-hour window
- Prevents reimporting the same refueling event multiple times
- Logs skipped duplicates at debug level

**Configuration:**
```python
DUPLICATE_DETECTION_WINDOW_HOURS = 24  # Adjustable in historical_data_import.py
```

### 4. GUI Display Options

Since the refueling log is a sensor (not a todo domain entity), several display options are documented:

#### Option 1: Attributes Card
```yaml
type: attribute
entity: sensor.your_car_refueling_log
attribute: recent_events
```

#### Option 2: Markdown Card with Filtering
```yaml
type: markdown
content: |
  {% set events = state_attr('sensor.your_car_refueling_log', 'recent_events') %}
  {% for event in events if event.confidence < 0.7 %}
  ⚠️ {{ event.timestamp }}: {{ event.liters_refueled }}L
  (Confidence: {{ (event.confidence * 100) | round(0) }}%)
  {% endfor %}
```

See [Refueling Log Guide](REFUELING_LOG_GUIDE.md) for complete examples.

## Usage Guide

### Reviewing Historical Imports

After running historical data import:

1. Check the refueling log sensor attributes
2. Filter events by `data_quality: historical_import`
3. Focus on events with `confidence < 0.7`
4. Review and correct as needed:
   - Verify timestamps match actual refueling dates
   - Check odometer readings
   - Update missing price information
   - Delete false positives

### Filtering Examples

**Get all low-confidence events:**
```yaml
{% set events = state_attr('sensor.car_refueling_log', 'recent_events') %}
{% set low_conf = events | selectattr('confidence', '<', 0.7) | list %}
```

**Get historical imports needing review:**
```yaml
{% set events = state_attr('sensor.car_refueling_log', 'recent_events') %}
{% set needs_review = events | 
  selectattr('data_quality', 'eq', 'historical_import') |
  selectattr('confidence', '<', 0.7) | list %}
```

**Count events by quality:**
```yaml
{% set events = state_attr('sensor.car_refueling_log', 'recent_events') %}
Manual: {{ events | selectattr('data_quality', 'eq', 'manual') | list | count }}
Auto: {{ events | selectattr('data_quality', 'eq', 'auto_detected') | list | count }}
Historical: {{ events | selectattr('data_quality', 'eq', 'historical_import') | list | count }}
```

## Technical Details

### Storage Structure

Each refueling event is stored with the following structure:

```json
{
  "id": 1,
  "timestamp": "2026-02-09T13:13:44.434888+00:00",
  "odometer_km": 1798.5,
  "liters_refueled": 45.2,
  "price_per_liter": 1.759,
  "total_cost": 79.51,
  "station_name": "Historical Import",
  "fuel_type": "e5",
  "latitude": null,
  "longitude": null,
  "editable": true,
  "data_quality": "historical_import",
  "confidence": 0.7
}
```

### Code Changes

**Files Modified:**
- `custom_components/hafwcma/utils/storage.py`
  - Added `data_quality` and `confidence` fields to refuel_record
  - Default values: `data_quality="manual"`, `confidence=1.0`

- `custom_components/hafwcma/utils/historical_data_import.py`
  - Added duplicate detection logic
  - Implemented `_calculate_confidence()` function
  - Added `DUPLICATE_DETECTION_WINDOW_HOURS` constant
  - Added `PERCENTAGE_MULTIPLIER` constant
  - Improved logging (debug for individual events, info for summary)

- `custom_components/hafwcma/sensor.py`
  - Updated `RefuelingLogSensor.extra_state_attributes()`
  - Exposed `data_quality` and `confidence` in recent_events

**Files Created:**
- `docs/REFUELING_LOG_GUIDE.md` - English documentation
- `docs/REFUELING_LOG_GUIDE_DE.md` - German documentation
- `docs/DATA_QUALITY_INDICATORS.md` - This file

### Backward Compatibility

The implementation is fully backward compatible:
- Existing refueling events without quality fields will default to `data_quality="manual"` and `confidence=1.0`
- No database migration required
- Existing functionality remains unchanged

## Future Enhancements

Potential improvements for future versions:

1. **Machine Learning Confidence**
   - Use ML to improve confidence scoring based on patterns
   - Learn from user corrections to improve future detections

2. **User Feedback Loop**
   - Allow users to mark events as correct/incorrect
   - Use feedback to improve detection algorithms

3. **Configurable Confidence Weights**
   - Make the 40/30/30 weights configurable
   - Allow users to prioritize different factors

4. **Enhanced Duplicate Detection**
   - Fuzzy matching based on odometer and amount
   - Smarter duplicate detection for rapid consecutive refuelings

5. **Bulk Operations**
   - Bulk delete low-confidence events
   - Bulk update events with missing data

## Support

For questions or issues:
- See [Refueling Log Guide](REFUELING_LOG_GUIDE.md) for detailed usage
- Check [Troubleshooting Guide](TROUBLESHOOTING.md) for common problems
- Open an issue on GitHub with logs and configuration

## References

- [Refueling Log Guide](REFUELING_LOG_GUIDE.md)
- [Refueling Log Guide (German)](REFUELING_LOG_GUIDE_DE.md)
- [Data Storage Architecture](DATA_STORAGE.md)
- [Data Update Frequencies](DATA_UPDATE_FREQUENCIES.md)
