# Testing Guide - Fuel Recommendation Optimization

## Quick Start

After installing this update, the new features will automatically activate. No configuration changes are needed!

## What to Look For

### 1. Position Change Cooldown

**How to Test:**
1. Drive >50km from one region to another where prices are significantly different (>€0.10/L change)
2. Check the `sensor.{your_vehicle}_fuel_price` entity
3. Look for these attributes:
   ```yaml
   in_cooldown: true
   cooldown_remaining_minutes: 28.5
   recommendation: "⏸️ Moved 230km with price change of €0.150/L. Recommendations paused temporarily."
   ```
4. Wait 30 minutes - cooldown should end and normal recommendations resume

**Example Scenario:**
- Start in Munich: €1.80/L
- Drive to Stuttgart: €1.65/L
- Distance: 230km, Price change: €0.15
- **Expected:** Cooldown activates, recommendations paused for 30 minutes

### 2. Station Comparison (10km vs 20km)

**How to Test:**
1. Ensure you have vehicle position configured (GPS entity)
2. Check `sensor.{your_vehicle}_fuel_price` attributes
3. Look for `station_comparison` attribute:
   ```yaml
   station_comparison:
     10km:
       name: "Shell Frankfurt Hauptstraße"
       distance_km: 5.0
       price: 1.75
       total_cost: 71.22
     20km:
       name: "Aral Offenbach Berliner Straße"
       distance_km: 15.0
       price: 1.65
       total_cost: 69.47
     savings: 1.76
     savings_percent: 2.5
     comparison_recommendation: "💡 Small savings of €1.76 possible..."
   ```

**When It Shows:**
- You have GPS position configured
- Multiple stations available in 10-20km radius
- Tank is not full

### 3. Forecast Recommendation

**How to Test:**
1. Wait for consumption prediction to run (usually within 24 hours of setup)
2. Check `sensor.{your_vehicle}_days_until_refuel` attributes
3. Look for forecast attributes:
   ```yaml
   forecast_trend: "favorable_now"
   forecast_should_refuel: true
   forecast_urgency: "medium"
   forecast_recommendation: "📊 Forecast: Current price (€1.67) is near historical best! Friday avg is €1.74. Consider refueling now."
   forecast_predicted_weekday: "Friday"
   forecast_predicted_avg_price: 1.74
   forecast_cheapest_weekday: "Saturday"
   forecast_cheapest_avg_price: 1.65
   ```

**Requirements:**
- At least 10 historical price observations
- Consumption prediction active (days_until_refuel sensor has a value)

## Troubleshooting

### "No forecast attributes"
- **Cause:** Not enough historical data yet
- **Solution:** Wait for more price observations to accumulate (runs every update cycle)

### "No station_comparison attribute"
- **Cause:** Vehicle position not available or no nearby stations
- **Solution:** 
  - Check GPS entity is configured and reporting position
  - Ensure stations exist within 20km radius
  - Check `nearby_cheap_stations` sensor for available stations

### "Recommendations always in cooldown"
- **Cause:** Frequently driving long distances with price changes
- **Solution:** This is expected behavior - cooldown will expire after 30 minutes of staying in one location

## Understanding the Recommendations

### Position Cooldown Messages
- `⏸️ Moved XXkm with price change...` - Recently entered new price region, recommendations paused

### Station Comparison Messages
- `💰 Save €X.XX by driving to...` - Significant savings (>€2.00)
- `💡 Small savings of €X.XX...` - Minor savings (€0.50-2.00)
- `≈ Similar cost...` - Negligible difference
- `🏆 Best choice...` - Closer station is actually better

### Forecast Messages
- `📊 Forecast: Current price is near historical best!` - Good time to refuel now
- `📊 Forecast: Prices typically cheaper on...` - Consider waiting or refueling earlier
- `📊 Forecast: Prices stable...` - No significant advantage to timing

## Technical Details

### Configurable Constants (in code)
Located in `custom_components/hafwcma/utils/refuel_recommendation_engine.py`:

```python
SIGNIFICANT_POSITION_CHANGE_KM = 50.0  # Distance triggering cooldown
POSITION_CHANGE_COOLDOWN_MINUTES = 30  # Cooldown duration
PRICE_CHANGE_THRESHOLD_FOR_COOLDOWN = 0.10  # Price change triggering cooldown (EUR)

DEFAULT_AVG_CONSUMPTION = 7.0  # Default consumption for savings calculation (L/100km)

FORECAST_MIN_HISTORY_POINTS = 10  # Min price observations for forecast
FORECAST_SIGNIFICANT_PRICE_DIFFERENCE = 0.05  # Threshold for significant day differences
FORECAST_NEAR_BEST_PRICE_MARGIN = 0.03  # Margin for "close to cheapest"
FORECAST_NEAR_HISTORICAL_BEST_MARGIN = 0.02  # Margin for "near best"
```

### Data Flow

```
Vehicle Position → PositionTracker → Cooldown Check
                                         ↓
                                    Recommendations
                                         ↓
                       ┌─────────────────┼─────────────────┐
                       ↓                 ↓                 ↓
              Station Comparison    Price Trend    Forecast Analysis
                   (10km/20km)       (Current)      (Historical)
```

## Providing Feedback

When testing, please note:
- Which features work as expected
- Which features don't work or behave unexpectedly
- Any error messages in Home Assistant logs
- Suggestions for improvement

Check logs with:
```
Settings → System → Logs → Filter: "hafwcma"
```

Look for messages starting with:
- `Position change cooldown activated`
- `Radius comparison`
- `Forecast recommendation`

## Example Test Session

1. **Day 1:** Install update, observe initial behavior
2. **Day 2-7:** Let price history accumulate
3. **Day 8:** Check for forecast recommendations
4. **Test Drive:** Drive >50km between cities, verify cooldown
5. **Station Check:** Review station comparison when tank <50%

## Success Criteria

✓ Position cooldown activates after long drives with price changes
✓ Station comparison shows realistic savings calculations
✓ Forecast recommendations are actionable and sensible
✓ All sensor attributes populate correctly
✓ No errors in Home Assistant logs

---

**Need Help?**
Create an issue with:
- Your sensor attributes (sanitize any personal data)
- Relevant log entries
- Description of unexpected behavior
