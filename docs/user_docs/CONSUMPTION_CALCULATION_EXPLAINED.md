# Consumption Calculation - How It Works

## Understanding Sensor Attributes

### The `data_source` Attribute

When you look at consumption-related sensors like:
- `sensor.xxx_average_consumption_forecast`
- `sensor.xxx_average_consumption_history` 
- `sensor.xxx_days_until_refuel`

You may see an attribute called `data_source` with one of these values:

#### 1. `"historical_data"` ✅ **This is GOOD!**
- Your consumption predictions are based on **real data** from your vehicle
- The system has analyzed your refueling history and odometer readings
- This provides **accurate, personalized** consumption estimates
- **This is the expected and desired state** when you have enough data

#### 2. `"ml_enhanced"` ⭐ **This is EVEN BETTER!**
- Machine learning has been applied to your historical data
- Weekday driving patterns are recognized (e.g., more driving on workdays)
- Even more accurate predictions based on behavioral analysis
- Requires sufficient historical data to enable

#### 3. `"fallback_values"` ⚠️ **Needs More Data**
- Not enough historical data available yet
- System is using default/configured values as estimates
- To improve: add refueling events and drive more to build up history
- Import historical data using the import buttons if available

---

## How Consumption Calculations Work

### 1. Data Collection

The integration tracks:
- **Odometer readings** - from your vehicle's odometer sensor
- **Tank level changes** - from your tank fill level sensor
- **Refueling events** - detected automatically when tank level increases
- **Timestamps** - when each data point was recorded

### 2. Consumption History Calculation

Runs on **every coordinator update** (typically every 5 minutes):

```
For each time period (today, 7 days, 14 days, 30 days):
  1. Filter refueling events within that period
  2. Calculate distance driven between refueling events
  3. Calculate fuel consumed (from refueling amounts)
  4. Compute: consumption = (fuel_liters / distance_km) * 100
```

**Result**: Average L/100km for each time period

### 3. Consumption Prediction Calculation

Runs **periodically** (configurable interval, default: every few hours):

```
1. Check if enough historical data exists (minimum 5 data points)
2. Analyze driving patterns (daily km, weekday patterns)
3. Calculate average consumption rate
4. Predict days until refueling needed based on current tank level
5. Estimate when you'll need to refuel next
```

**Result**: Predictions with confidence scores

### 4. Consumption Forecast Calculation

Runs **after prediction** completes:

```
1. Take consumption prediction data
2. Apply weekday driving patterns (if ML-enhanced)
3. Calculate expected km driven for different periods
4. Estimate fuel needed and costs based on historical prices
```

**Result**: Cost forecasts for tomorrow, next week, etc.

---

## Understanding the Attributes

### Common Attributes on Consumption Sensors

| Attribute | Meaning | Example |
|-----------|---------|---------|
| `data_source` | Where prediction data comes from | `"historical_data"` |
| `data_points_used` | Number of data points analyzed | `957` |
| `data_points_required` | Minimum needed for predictions | `5` |
| `data_points_percentage` | How much data you have | `100` (means 100%+ available) |
| `last_prediction` | When prediction was last updated | `2024-01-15T10:30:00` |
| `confidence` | How reliable the prediction is | `0.85` (85% confidence) |

### What `data_points_percentage: 100` Means

This means you have **100% or more** of the required data points:
- Required: 5 data points minimum
- You have: 957 data points
- Percentage: (957 / 5) * 100 = **way over 100%** (capped at 100 in display)
- **Status**: Excellent data coverage ✅

---

## Using the Recalculate Button

### What Does `button.xxx_recalculate_trip_statistics` Do?

When you press this button:

1. **Recalculates trip statistics** from stored trip data
   - Total distance driven
   - Total fuel consumed
   - Trip category counts (business/private/commute)

2. **Forces consumption prediction update**
   - Resets the prediction interval timer
   - Causes predictions to be recalculated immediately on next update
   - Updates all consumption sensors with fresh data

3. **Triggers coordinator refresh**
   - Fetches latest vehicle data
   - Runs all calculations with new data
   - Updates all sensors

### When to Use the Recalculate Button

- After importing historical data
- After manually adding/editing refueling events
- When sensor values seem outdated
- After configuration changes

---

## Understanding the Import Buttons

### `button.xxx_import_historical_vehicle_data`

**What it imports**:
- Odometer readings from Home Assistant history
- Tank level changes from sensor history
- Detected refueling events

**When to use**:
- Initial setup to build historical database
- After fresh installation to get past data
- When you have existing sensor data but empty refueling log

**What it does NOT import**:
- GPS-based trip data (use the other button for that)

### `button.xxx_import_historical_trip_data`

**What it imports**:
- GPS position history from device tracker
- Detected trips based on location changes
- Trip start/end points and routes

**When to use**:
- When trip tracking feature is enabled
- To analyze historical driving patterns
- After enabling trip tracking to import past trips

**Requirements**:
- Trip tracking must be enabled in configuration
- Vehicle position entity must be configured

---

## Troubleshooting

### "Why do my sensors show `data_source: historical_data`?"

**Answer**: This is correct! It means your system is using real historical data from your vehicle.

### "Why doesn't recalculate button update immediately?"

**Answer**: 
- **Before this fix**: Predictions had interval throttling
- **After this fix**: Button forces immediate recalculation
- You may need to reload the integration or restart HA to get the updated button behavior

### "My predictions show low confidence"

**Possible causes**:
1. Not enough refueling events (need at least 2)
2. Irregular refueling patterns
3. Missing odometer readings
4. Recent data import needs time to process

**Solutions**:
- Continue driving and refueling normally
- Ensure vehicle sensors are properly configured
- Import historical data if available
- Wait for more data to accumulate

### "Consumption values seem wrong"

**Check**:
1. Tank capacity configured correctly
2. Odometer sensor reports in kilometers (not miles)
3. Tank level sensor reports percentage (0-100%)
4. Recent refueling events are logged correctly

---

## Data Requirements

### Minimum Data for Predictions

- **At least 2 refueling events** with odometer readings
- **At least 5 data points** total (configurable)
- Odometer values must increase between events
- Timestamps must be valid and in order

### Optimal Data for Best Predictions

- **30+ days** of driving history
- **Regular refueling** patterns (weekly or more frequent)
- **Accurate odometer** readings (no gaps or jumps)
- **Complete tank level** data
- **Position data** for location-based features (optional)

---

## Summary

✅ **`data_source: "historical_data"` is GOOD** - it means your system is working correctly

✅ **`data_points_used: 957` is EXCELLENT** - you have plenty of data

✅ **Use the recalculate button** to force immediate prediction updates

✅ **Import buttons** help build historical database from existing sensor data

❌ **Don't worry** if you see "historical_data" - it's not an error!
