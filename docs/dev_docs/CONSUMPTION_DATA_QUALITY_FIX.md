# Consumption Data Quality Fix

## Issue

After PR #140, consumption sensors may show incorrect or suspicious values such as:
- Very high daily km (e.g., 11,111 km in one day)
- Identical values for different time periods (today and last week showing the same data)
- Unrealistically low or high consumption rates

## Root Cause

These issues typically occur when:
1. **Refueling events have incorrect timestamps** - All events may have been assigned the same recent timestamp instead of their historical dates
2. **Odometer values are incorrect** - Manual entries or import errors may have created unrealistic odometer readings
3. **Historical data import issues** - Odometer history was imported without corresponding tank level history, preventing proper refueling event detection

## How the Fix Works

### 1. Validation Warnings in Logs

The system now adds validation checks in `calculate_consumption_history()` that detect suspicious patterns:

```python
# Warning if average exceeds 1000 km/day (unrealistic for normal usage)
if avg_km_per_day > 1000:
    _LOGGER.warning(
        "SUSPICIOUS DATA - Average %.1f km/day (total: %d km). "
        "Check your refueling log for data quality issues.",
        avg_km_per_day, total_km
    )
```

Check your Home Assistant logs for these warnings to identify problematic data.

### 2. Sensor Attribute Warnings

The `ConsumptionHistorySensor` now includes a `data_quality_warning` attribute when suspicious data is detected:

- **High daily km warning**: "Today shows 11111 km driven, which is unusually high..."
- **Identical period warning**: "Last week and today show nearly identical km..."

These warnings guide users to:
1. Check the refueling log for incorrect data
2. Use the recalculation button to refresh predictions
3. Re-import historical data if needed

### 3. How Consumption Forecast Works (Expected Behavior)

It's **normal and correct** for all forecast periods to show the same consumption rate (L/100km):

```
tomorrow_consumption: 1.69
next_week_consumption: 1.69  ← This is CORRECT!
next_14_days_consumption: 1.69
next_month_consumption: 1.69
```

**Why?** Consumption rate (L/100km) is your vehicle's efficiency, which doesn't change day-to-day. What DOES change is:
- Expected km driven (based on weekday patterns)
- Expected fuel cost (tomorrow_cost, next_week_cost, etc.)

The forecast uses the same consumption rate but applies it to different expected distances.

## How to Fix Data Issues

### Option 1: Recalculate Button (Recommended)

1. Go to your vehicle device in Home Assistant
2. Press the **"Recalculate Trip Statistics"** button
3. This forces a fresh consumption prediction calculation
4. Wait for the next coordinator update (typically 5 minutes)
5. Check if the warnings are resolved

### Option 2: Re-Import Historical Data

If refueling events have incorrect timestamps:

1. Go to your vehicle device
2. Press the **"Import Historical Vehicle Data"** button
3. The system will:
   - Import odometer history from recorder
   - Import tank level history from recorder
   - Detect refueling events from tank level increases
   - Match odometer readings to refueling events by timestamp
4. Wait for the import to complete
5. Check the import results in the button's attributes

**Important**: This requires BOTH odometer AND tank level sensor history in Home Assistant's recorder database.

### Option 3: Manual Correction

If specific refueling events have wrong data:

1. Open the **Refueling Log Sensor** attributes
2. Identify events with suspicious odometer values or timestamps
3. Edit or delete those events through the Lovelace card
4. Use the recalculation button to refresh predictions

## Prevention

To avoid future data quality issues:

1. **Ensure proper sensor configuration**: Configure both odometer and tank level sensors
2. **Verify historical imports**: Check that tank level history is available before importing
3. **Monitor warnings**: Check sensor attributes regularly for data quality warnings
4. **Use auto-detection**: Let the system detect refueling from tank level changes rather than manual entry when possible

## Technical Details

### Consumption History Calculation

For each time period (today, last week, 14 days, 30 days):

1. Filter refueling events by timestamp cutoff
2. Sort events chronologically
3. For each consecutive pair of events:
   - Calculate km driven: `next_odometer - current_odometer`
   - Get fuel consumed: `liters_refueled` from current event
4. Sum totals: `total_km`, `total_liters`
5. Calculate average: `(total_liters / total_km) * 100`

**Key insight**: If all refueling events have the same timestamp, they all fall in the "today" bucket, making today and last week show identical values.

### Validation Thresholds

- **Daily km warning**: > 1000 km/day average
- **Period similarity**: < 1% difference between today and weekly totals

These thresholds are conservative to avoid false positives while catching obvious data errors.

## Example Scenario

**Problem**: After historical import, sensor shows:
```
last_24h_km: 11111
last_7_days_km: 11111
```

**Diagnosis**: 
- Check logs: "SUSPICIOUS DATA - Average 11111.0 km/day"
- Check attributes: `data_quality_warning` appears
- Check refueling log: All events have timestamp "2026-02-17T16:00:00"

**Solution**:
- Events were imported with current timestamp instead of historical dates
- Re-import with proper tank level history to get correct timestamps
- OR manually update event timestamps in the refueling log
- Press recalculation button to refresh

## Related Documentation

- [VERBRAUCHSBERECHNUNG_ERKLAERT_DE.md](VERBRAUCHSBERECHNUNG_ERKLAERT_DE.md) - How consumption calculation works (German)
- [CONSUMPTION_CALCULATION_EXPLAINED.md](CONSUMPTION_CALCULATION_EXPLAINED.md) - Consumption calculation details (English)
