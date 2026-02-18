# Refueling Prediction Improvement

## Problem Statement

The previous implementation of Method 3 in `predict_days_until_refuel()` used `_calculate_avg_days_between_refuelings()` which simply averaged the time intervals between past refueling events. This approach had several issues:

1. **Ignored actual consumption patterns** - It only looked at when refuelings happened, not how much fuel was consumed
2. **Required historical refueling events** - Didn't work well for new vehicles or after data resets
3. **Didn't account for driving patterns** - Ignored weekday vs weekend differences in driving behavior
4. **Redundant logic** - We already had better data available:
   - Average consumption rate (L/100km)
   - Consumption forecast by weekday (weekday_pattern from ML)
   - Current tank level and capacity
   - Average daily kilometers driven

## Example of the Problem

**Old Method 3 Logic:**
- User refuels every 7 days on average
- Prediction: "You'll need to refuel in 7 days"
- Reality: Tank is nearly empty, needs refuel in 2 days

**Why it failed:**
The old method didn't know or care about the current tank level, consumption rate, or whether the user drove more/less this week.

## Solution

Replaced Method 3 with an **intelligent consumption-based fallback** that:

1. **Uses weekday patterns when available**
   - Calculates estimated range from assumed tank level (50% if unknown)
   - Applies weekday-aware consumption pattern via `_calculate_days_until_refuel_with_weekday_pattern()`
   - Accounts for different driving distances on weekdays vs weekends

2. **Falls back to simple consumption calculation**
   - If weekday pattern isn't available: `days = (estimated_range_km) / avg_daily_km`
   - Still uses actual consumption data, not refueling intervals

3. **Conservative estimation**
   - When tank level is unknown, assumes 50% capacity
   - Provides a safer prediction than historical intervals

## Code Changes

### Before (Old Method 3)
```python
# Method 3: Use average refueling interval from history
if days_until_refuel is None and use_historical:
    avg_refuel_interval = await _calculate_avg_days_between_refuelings(hass, entry)
    if avg_refuel_interval is not None:
        days_until_refuel = avg_refuel_interval
```

### After (New Method 3)
```python
# Method 3: Intelligent fallback using consumption forecast with weekday pattern
if days_until_refuel is None and use_historical and avg_daily_km > 0 and avg_consumption_rate > 0:
    # Use weekday pattern if available for more accurate prediction
    if weekday_pattern and tank_capacity is not None:
        estimated_tank_level = tank_capacity * 0.5
        estimated_range_km = (estimated_tank_level / avg_consumption_rate) * 100
        days_until_refuel = _calculate_days_until_refuel_with_weekday_pattern(
            estimated_range_km, weekday_pattern, now
        )
    
    # Fallback to simple calculation if weekday pattern didn't work
    if days_until_refuel is None and tank_capacity is not None:
        estimated_tank_level = tank_capacity * 0.5
        estimated_range_km = (estimated_tank_level / avg_consumption_rate) * 100
        days_until_refuel = estimated_range_km / avg_daily_km
```

## Benefits

1. **More accurate predictions** - Uses actual consumption data and driving patterns
2. **No dependency on refueling events** - Works even without historical refuelings
3. **Weekday-aware** - Accounts for different driving patterns throughout the week
4. **Consistent with other methods** - Methods 1, 2, and 3 now all use consumption-based logic
5. **Better fallback** - When exact tank data is unavailable, makes a smarter estimate

## Backward Compatibility

- `_calculate_avg_days_between_refuelings()` is kept but marked as deprecated
- No breaking changes to the API
- Prediction quality improves, especially for:
  - New vehicles without refueling history
  - Users with irregular refueling patterns
  - Scenarios where tank level sensor is temporarily unavailable

## Related Sensors

The improved prediction leverages data from:
- `sensor.{car}_average_consumption_forecast` - Weekday consumption patterns
- `sensor.{car}_tank_level` - Current fuel level
- Tank capacity (from entity attributes)
- `sensor.{car}_fuel_price` - Can be used for future price prediction enhancements

## Future Enhancements

Potential improvements that could build on this change:
1. Add fuel price trend analysis to suggest optimal refueling timing
2. Account for planned long trips (calendar integration)
3. Learn from user's refueling behavior (e.g., prefers to refuel at 25% vs 10%)
4. Seasonal consumption adjustments (winter vs summer)
