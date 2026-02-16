# Fuel Recommendation Optimization - Implementation Summary

## Overview
This implementation adds advanced fuel recommendation features to haFWCMA, addressing the issue of optimizing refueling recommendations based on driving behavior, historical price patterns, and intelligent position tracking.

## Features Implemented

### 1. Position Change Cooldown Mechanism

**Problem Solved:** 
Large price jumps when driving from a high-price region to a low-price region were causing misleading recommendations (e.g., "great price!" when entering a region where prices are actually not that good).

**Solution:**
- **PositionTracker** class monitors vehicle position changes
- Triggers cooldown when:
  - Vehicle moves ≥50km AND
  - Price changes by ≥€0.10/L
- During cooldown (30 minutes):
  - Recommendations are paused
  - User sees message: "⏸️ Moved XXkm with price change of €X.XXX/L. Recommendations paused temporarily."

**Constants (configurable in code):**
- `SIGNIFICANT_POSITION_CHANGE_KM = 50.0`
- `POSITION_CHANGE_COOLDOWN_MINUTES = 30`
- `PRICE_CHANGE_THRESHOLD_FOR_COOLDOWN = 0.10`

### 2. Multi-Radius Station Comparison (10km vs 20km)

**Problem Solved:**
Users want to know if it's worth driving further to a cheaper station, considering the additional fuel cost of the trip.

**Solution:**
- Compares cheapest stations within 10km and 20km radius
- Calculates **true savings** considering:
  - Fuel to purchase (tank capacity - current level)
  - Distance to station and back (round trip)
  - Fuel consumed during the trip (using average consumption)
  - Price difference per liter

**Example Output:**
```
station_comparison:
  10km:
    name: "Shell Frankfurt Hauptstraße"
    distance_km: 5.0
    price: 1.75
    total_cost: 71.22  # Includes fuel + trip cost
  20km:
    name: "Aral Offenbach Berliner Straße"
    distance_km: 15.0
    price: 1.65
    total_cost: 69.47
  savings: 1.76  # Euro
  savings_percent: 2.5
  comparison_recommendation: "💰 Save €1.76 by driving to Aral..."
```

**Recommendation Messages:**
- Savings > €2.00: "💰 Save €X.XX by driving to [20km station]..."
- Savings €0.50-2.00: "💡 Small savings of €X.XX possible at..."
- Savings ≈ €0: "≈ Similar cost..."
- Negative savings: "🏆 Best choice: [10km station]..."

### 3. Forecast Recommendation Based on Historical Prices

**Problem Solved:**
Users want to know if they should refuel now or wait, based on when they'll need to refuel and historical price patterns.

**Solution:**
- Analyzes historical prices by weekday
- Compares predicted refueling day with historically cheapest days
- Recommends early refueling if:
  - Predicted refueling day typically has higher prices AND
  - Current price is close to historical best

**Example Scenario:**
- Prediction: Need to refuel on Friday
- Historical data: Fridays average €1.74/L, Saturdays average €1.65/L
- Current price: €1.67/L
- **Recommendation:** "📊 Forecast: Current price (€1.67) is near historical best! Friday avg is €1.74. Consider refueling now."

**Attributes Added to sensor.{vehicle}_days_until_refuel:**
```yaml
forecast_trend: "favorable_now" | "favorable_earlier" | "stable"
forecast_should_refuel: true | false
forecast_urgency: "low" | "medium" | "high"
forecast_recommendation: "User-friendly message"
forecast_predicted_weekday: "Friday"
forecast_predicted_avg_price: 1.74
forecast_cheapest_weekday: "Saturday"
forecast_cheapest_avg_price: 1.65
forecast_price_difference: 0.09
```

## Technical Implementation

### New Module: `refuel_recommendation_engine.py`

**Classes:**
- `PositionTracker`: Tracks position changes and manages cooldowns
  - `update(lat, lon, price)` → returns cooldown status
  
**Functions:**
- `compare_stations_by_radius()`: Calculates 10km vs 20km comparison
- `analyze_forecast_recommendation()`: Analyzes historical prices for forecast
- `_format_savings_recommendation()`: Formats user-friendly messages
- `_format_forecast_recommendation()`: Formats forecast messages

### Integration Points

**In `sensor.py` → `HaFWCMACoordinator`:**
1. Added `_position_tracker` initialization
2. Modified `_async_update_data()`:
   - Calls `position_tracker.update()` when vehicle position available
   - Skips recommendations during cooldown
   - Calls `compare_stations_by_radius()` when nearby stations available
   - Adds `position_change_info` and `radius_comparison` to coordinator data

3. Modified `_update_consumption_prediction()`:
   - Calls `analyze_forecast_recommendation()` after prediction
   - Adds forecast recommendation to prediction data

**In `FuelPriceSensor`:**
- Added `station_comparison` attribute with 10km/20km data
- Added `in_cooldown` and `cooldown_remaining_minutes` attributes

**In `ConsumptionPredictionSensor`:**
- Added forecast attributes:
  - `forecast_trend`
  - `forecast_should_refuel`
  - `forecast_urgency`
  - `forecast_recommendation`
  - Plus detailed forecast data (weekdays, prices, differences)

## Data Flow

```
Coordinator Update
    ↓
1. Get vehicle position & price
    ↓
2. PositionTracker.update()
    ↓
3. If cooldown → skip recommendations
   If not cooldown → generate recommendations
    ↓
4. If nearby_stations available → compare_stations_by_radius()
    ↓
5. If consumption_prediction → analyze_forecast_recommendation()
    ↓
6. Return data with:
   - position_change_info
   - radius_comparison
   - forecast_recommendation
    ↓
Sensors display attributes
```

## Usage Examples

### Position Change Cooldown in Action

**Scenario:** User drives from Munich (€1.80/L) to Stuttgart (€1.65/L)

1. Vehicle position: Munich (48.1351°, 11.5820°)
2. Price: €1.80/L
3. *Drive 230km*
4. Vehicle position: Stuttgart (48.7758°, 9.1829°)
5. Price: €1.65/L
6. **Cooldown activated:**
   - Distance: 230km > 50km ✓
   - Price change: €0.15 > €0.10 ✓
7. **Recommendation:** "⏸️ Moved 230km with price change of €0.150/L. Recommendations paused temporarily."
8. After 30 minutes → Normal recommendations resume

### Station Comparison Example

**Scenario:** Tank at 20%, capacity 50L, consumption 7L/100km

**10km Station:**
- Distance: 5km
- Price: €1.75/L
- Fuel to buy: 40L
- Round trip: 10km
- Fuel consumed: 0.7L
- Total cost: €70.00 (fuel) + €1.22 (trip) = €71.22

**20km Station:**
- Distance: 15km
- Price: €1.65/L
- Fuel to buy: 40L
- Round trip: 30km
- Fuel consumed: 2.1L
- Total cost: €66.00 (fuel) + €3.47 (trip) = €69.47

**Savings: €1.75** → "💡 Small savings of €1.75 possible at..."

### Forecast Recommendation Example

**Scenario:** Today is Wednesday, prediction says you'll need fuel on Friday

**Historical Analysis:**
- Monday-Thursday: €1.70-1.74/L average
- Friday: €1.74/L average
- Saturday: €1.65/L average (cheapest)
- Sunday: €1.66/L average

**Current Price:** €1.67/L

**Recommendation:** "📊 Forecast: Current price (€1.67) is near historical best! Friday avg is €1.74. Consider refueling now."

## Configuration

No additional configuration required. The new features use existing:
- `tank_capacity`: For calculating fuel to purchase
- `consumption_min_data_points`: For consumption history (used in avg consumption)
- Price history storage: For historical analysis
- Nearby cheap stations data: For radius comparison

## Performance Considerations

- **Position tracking:** Minimal overhead, simple distance calculation
- **Radius comparison:** Only runs when nearby_cheap_stations data available
- **Forecast analysis:** Only runs during consumption prediction updates (configurable interval)
- **Storage:** No additional storage required, uses existing price_history

## Validation

Validation tests confirm:
- ✓ Position tracking correctly identifies significant movements
- ✓ Cooldown triggers only when both distance and price thresholds met
- ✓ Savings calculation accurately accounts for trip costs
- ✓ Forecast logic correctly identifies cheapest days
- ✓ Recommendations formatted user-friendly

## Future Enhancements

Potential improvements:
1. Make cooldown parameters configurable via UI
2. Add "time of day" analysis to forecast (not just weekday)
3. Consider traffic conditions in trip cost calculations
4. Add user preference: "I don't mind driving X km for Y cent savings"
5. Historical analysis: "You usually refuel on Saturdays at 2pm"

## Files Modified

1. `custom_components/hafwcma/sensor.py`
   - Added PositionTracker initialization
   - Modified coordinator update logic
   - Enhanced sensor attributes

2. `custom_components/hafwcma/utils/refuel_recommendation_engine.py` (NEW)
   - Complete implementation of new features

## Testing Recommendations

For users to test:
1. Drive >50km between regions with different prices → verify cooldown
2. Check `station_comparison` attribute on fuel_price sensor
3. Check forecast attributes on days_until_refuel sensor
4. Verify recommendations are sensible and actionable
5. Monitor logs for any errors or warnings

## Conclusion

This implementation provides users with:
- **Smarter recommendations** that don't react to temporary price changes when moving
- **Financial transparency** showing actual savings considering trip costs
- **Predictive insights** based on historical price patterns
- **Actionable information** to optimize refueling timing

All features integrate seamlessly with existing haFWCMA functionality.
