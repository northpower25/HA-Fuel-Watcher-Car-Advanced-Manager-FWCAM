# Consumption Prediction Engine - Implementation Summary

## Overview

This implementation adds an advanced consumption prediction engine to the haFWCMA (Home Assistant Fuel Watcher Car Advanced Manager) integration. The engine analyzes historical vehicle data to predict when refueling will be needed, providing users with accurate forecasts based on their driving patterns.

## German Requirements Translation

The original requirements (in German) asked for:

1. **Build a consumption prediction engine** that uses:
   - Current mileage and tank level
   - Historical changes in mileage and tank level
   - Changes over time in both metrics

2. **Make configurable** (via separate entities/sensors):
   - Amount of historical data required for valid prediction
   - Prediction calculation interval

3. **Data handling**:
   - Check if sufficient vehicle data is available
   - If not, use fallback values from configuration

4. **Output as a sensor showing days until refueling**, with attributes:
   - Whether data was calculated from historical values or fallback configuration
   - Last prediction calculation timestamp
   - Predicted date/time when refueling is needed

## Implementation Details

### 1. New Files

#### `custom_components/hafwcma/utils/consumption_prediction.py`

This is the core prediction engine module containing:

- **`check_data_sufficiency()`**: Validates if enough historical data exists for reliable predictions
  - Checks odometer history points
  - Checks refueling events with consumption data
  - Returns sufficiency status and reason

- **`calculate_historical_consumption()`**: Analyzes historical data to calculate:
  - Average daily kilometers driven
  - Average fuel consumption rate (L/100km)
  - Consumption trend (increasing/decreasing/stable)
  - Confidence score based on data availability

- **`predict_days_until_refuel()`**: Main prediction function that:
  - Determines if historical or fallback data should be used
  - Calculates days until refueling needed
  - Provides predicted refuel date
  - Returns comprehensive prediction data with confidence

- **`store_prediction_result()`**: Stores prediction history for accuracy tracking

### 2. Modified Files

#### `custom_components/hafwcma/const.py`

Added new configuration constants:
- `CONF_CONSUMPTION_MIN_DATA_POINTS`: Minimum data points for predictions
- `CONF_CONSUMPTION_PREDICTION_INTERVAL`: Interval between predictions
- New attribute constants for sensor data
- Default values for all new settings

#### `custom_components/hafwcma/number.py`

Added two new number entities:
- **ConsumptionMinDataPointsNumber**: Configure minimum data points (2-50, default 5)
- **ConsumptionPredictionIntervalNumber**: Configure prediction interval (0.5-24h, default 6h)

Both entities allow runtime configuration via Home Assistant UI.

#### `custom_components/hafwcma/sensor.py`

Major additions:
- **ConsumptionPredictionSensor**: New sensor entity displaying days until refuel
  - Shows prediction value
  - Exposes comprehensive attributes (data source, confidence, consumption rates, etc.)

- **Coordinator updates**:
  - `_last_consumption_prediction`: Tracks last prediction time
  - `_update_consumption_prediction()`: Manages prediction lifecycle
  - Integrated prediction into main update cycle

### 3. Configuration

#### Default Values

```python
DEFAULT_CONSUMPTION_MIN_DATA_POINTS = 5  # Minimum historical data points
DEFAULT_CONSUMPTION_PREDICTION_INTERVAL = 6.0  # Hours between predictions
MIN_CONSUMPTION_MIN_DATA_POINTS = 2  # Absolute minimum
MAX_CONSUMPTION_MIN_DATA_POINTS = 50  # Maximum configurable
MIN_CONSUMPTION_PREDICTION_INTERVAL = 0.5  # 30 minutes
MAX_CONSUMPTION_PREDICTION_INTERVAL = 24.0  # 24 hours
```

#### User-Configurable Settings

Users can adjust these via number entities in Home Assistant:
1. **Consumption Min Data Points** (2-50): How many historical data points are needed for reliable predictions
2. **Consumption Prediction Interval** (0.5-24 hours): How often to recalculate predictions

### 4. Sensor Attributes

The "Days Until Refuel" sensor provides:

| Attribute | Description |
|-----------|-------------|
| `data_source` | `"historical_data"` or `"fallback_values"` |
| `confidence` | 0.0-1.0 confidence score |
| `avg_daily_km` | Average kilometers driven per day |
| `avg_consumption_rate` | Average fuel consumption (L/100km) |
| `data_points_used` | Number of historical data points used |
| `last_prediction` | ISO timestamp of last calculation |
| `predicted_refuel_date` | ISO timestamp when refueling is predicted |

### 5. Prediction Logic

#### Data Sufficiency Check

The system checks:
1. Number of odometer history points
2. Number of refueling events with consumption data
3. Requires: `odometer_points >= min_data_points` AND `consumption_events >= min_data_points/2`

#### Historical vs Fallback

**Historical data is used when:**
- Sufficient data points exist
- Average daily km > 0
- Consumption calculations are valid

**Fallback is used when:**
- Insufficient historical data
- Missing vehicle data
- Calculation errors

#### Confidence Scoring

Confidence is calculated based on data points:
- 10+ data points: 1.0 (100% confidence)
- 5-9 data points: 0.7 (70% confidence)
- 2-4 data points: 0.4 (40% confidence)
- <2 data points or fallback: 0.3 or lower

#### Consumption Trend Analysis

For 4+ consumption events, the system:
1. Splits data into first and second halves
2. Compares average consumption
3. Determines trend: increasing (>5%), decreasing (<-5%), or stable

### 6. Prediction Interval Management

The coordinator:
1. Checks time since last prediction
2. Only recalculates if interval has passed
3. Returns previous prediction if interval not elapsed
4. Stores predictions for history tracking

### 7. Integration with Existing System

The prediction engine integrates seamlessly:
- Uses existing storage infrastructure
- Leverages vehicle data tracking
- Complements refuel recommendation engine
- Works with existing coordinator update cycle

## Usage Examples

### Basic Automation

```yaml
automation:
  - alias: "Low Days Until Refuel Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_car_days_until_refuel
        below: 2
    condition:
      - condition: template
        value_template: "{{ state_attr('sensor.my_car_days_until_refuel', 'confidence') | float > 0.5 }}"
    action:
      - service: notify.telegram
        data:
          message: >
            Warning: Only {{ states('sensor.my_car_days_until_refuel') }} days of fuel left!
            Predicted refuel date: {{ state_attr('sensor.my_car_days_until_refuel', 'predicted_refuel_date') }}
```

### Dashboard Card

```yaml
type: entities
title: Fuel Prediction
entities:
  - entity: sensor.my_car_days_until_refuel
    name: Days Until Refuel
  - type: attribute
    entity: sensor.my_car_days_until_refuel
    attribute: confidence
    name: Confidence
  - type: attribute
    entity: sensor.my_car_days_until_refuel
    attribute: data_source
    name: Data Source
  - entity: number.my_car_consumption_min_data_points
    name: Min Data Points
  - entity: number.my_car_consumption_prediction_interval
    name: Update Interval
```

## Benefits

1. **Accurate Predictions**: Based on actual driving patterns, not assumptions
2. **Configurable**: Users can tune sensitivity and update frequency
3. **Transparent**: Clear indication of data source and confidence
4. **Intelligent Fallback**: Gracefully handles insufficient data
5. **History Tracking**: Stores predictions for future accuracy analysis
6. **Efficient**: Configurable intervals prevent excessive calculations

## Future Enhancements

Potential improvements documented in TODO.md:
- Seasonal consumption pattern learning
- Weather-based consumption adjustments
- Route-based consumption prediction
- Prediction accuracy analysis and reporting
- Machine learning for advanced predictions

## Testing Recommendations

1. **Test with no historical data**: Should use fallback values with low confidence
2. **Test with minimal data (2-4 points)**: Should use historical data with medium confidence
3. **Test with sufficient data (5+ points)**: Should use historical data with high confidence
4. **Test interval configuration**: Change interval and verify prediction updates respect it
5. **Test min data points configuration**: Change threshold and verify behavior changes

## Security

- Code passed CodeQL security scan with 0 alerts
- No vulnerabilities introduced
- Safe handling of missing/invalid data
- Proper error handling throughout

## Documentation

Updated:
- **README.md**: Added feature descriptions, usage examples, sensor documentation
- **TODO.md**: Marked completed items, added future enhancements
- **Code comments**: Comprehensive docstrings in all new functions

## Conclusion

This implementation successfully adds a robust, configurable consumption prediction engine that meets all requirements from the original German specification. The system intelligently uses historical data when available, falls back gracefully when needed, and provides users with transparent, actionable predictions about their vehicle's fuel needs.
