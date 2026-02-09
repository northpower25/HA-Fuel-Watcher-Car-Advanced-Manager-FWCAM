# Data Update Frequencies and Configuration

This document explains when and how often different types of data are automatically collected, calculated, or updated in the haFWCMA integration, along with configuration options and important warnings.

## Table of Contents

1. [Data Update Overview](#data-update-overview)
2. [Automatic Updates](#automatic-updates)
3. [Manual Updates](#manual-updates)
4. [Configuration Options](#configuration-options)
5. [Important Warnings](#important-warnings)
6. [Historical Data Import](#historical-data-import)

---

## Data Update Overview

The integration collects and processes data from multiple sources:

- **Fuel Price API** (Tankerkönig): Current fuel prices from nearby stations
- **Vehicle Entities**: Odometer, tank level, range, and position from your vehicle integration
- **Calculated Predictions**: Consumption forecasts and refueling recommendations
- **Historical Statistics**: Average consumption over various time periods

Each data source has its own update frequency to balance accuracy with system performance and API rate limits.

---

## Automatic Updates

### 1. Fuel Price API Updates

**Default Frequency:** Every 15 minutes  
**Configurable Range:** 1-60 minutes  
**Configuration Entity:** `number.[car_name]_api_update_interval`

The integration queries the Tankerkönig API for current fuel prices at the configured interval. To prevent rate limiting when multiple Home Assistant instances access the API simultaneously, each update is automatically randomized by ±2% of the configured interval.

**What gets updated:**
- Current fuel prices at nearby stations
- Station information (name, address, distance)
- Open/closed status of stations
- Price trends and forecasts

**Update triggers:**
- Time-based: Every X minutes (configured interval)
- Manual: Via `switch.[car_name]_manual_refresh`
- Manual: Via `button.[car_name]_test_api_connection`

### 2. Vehicle Data Updates

**Frequency:** Same as Fuel Price API updates  
**Default:** Every 15 minutes  
**Configuration Entity:** `number.[car_name]_api_update_interval`

Vehicle data from your configured entities (odometer, tank level, range, position) is fetched at the same interval as the fuel price API. This data is used to:
- Detect refueling events
- Track consumption patterns
- Calculate driving statistics

**What gets updated:**
- Current odometer reading
- Current tank level (liters or percentage)
- Current estimated range
- Current vehicle position (if configured)

**Update triggers:**
- Time-based: Every X minutes (same as API interval)
- Manual: Via `button.[car_name]_refresh_vehicle_data`
- Manual: Via `switch.[car_name]_manual_refresh`

**Data storage:**
- Odometer readings are stored in history (up to 1000 entries)
- Refueling events are automatically detected and logged (up to 100 events)
- All data is persisted in `.storage/hafwcma_<entry_id>.json`

### 3. Consumption Prediction Updates

**Default Frequency:** Every 6 hours  
**Configurable Range:** 0.5-24 hours  
**Configuration Entity:** `number.[car_name]_consumption_prediction_interval`

The consumption prediction engine analyzes historical driving data to calculate:
- Days until refueling is needed
- Average daily kilometers driven
- Average fuel consumption rate (L/100km)
- Confidence level of predictions

**What gets calculated:**
- `sensor.[car_name]_days_until_refuel` and its attributes
- Prediction data source (fallback_values, historical_data, or ml_enhanced)
- Confidence score (0-1 scale)

**Update triggers:**
- Time-based: Every X hours (configured interval)
- Manual: Via `switch.[car_name]_manual_prediction`

**Data requirements:**
The prediction engine requires a minimum number of data points before switching from fallback values to historical data predictions. This is configured via `number.[car_name]_consumption_min_data_points` (default: 5).

**Prediction modes:**
1. **Fallback Values** (data_points_used < minimum):
   - Uses configured default values
   - Low confidence (typically 0.3-0.5)
   - Attribute `data_points_percentage` shows progress toward minimum

2. **Historical Data** (sufficient data points):
   - Uses actual driving patterns
   - Higher confidence (0.6-0.8)
   - Based on your real consumption data

3. **ML Enhanced** (with pattern recognition):
   - Includes weekday/weekend patterns
   - Highest confidence (0.7-0.9)
   - Considers trends and seasonal variations

### 4. Consumption History Calculation

**Frequency:** Every coordinator update  
**Default:** Every 15 minutes (with API/vehicle data)

Historical consumption statistics are recalculated each time new vehicle data is fetched. This provides real-time updates to:
- `sensor.[car_name]_average_consumption_history` and its attributes

**Time periods calculated:**
- **Today**: Current day's consumption (midnight to now)
- **Last Week**: Rolling 7-day period
- **Last 14 Days**: Rolling 14-day period
- **Last Month**: Rolling 30-day period

**Data source:**
Calculations are based on detected refueling events. At least 2 refueling events are required within each time period to calculate consumption (fuel consumed between refuelings divided by distance traveled).

### 5. Consumption Forecast

**Frequency:** Every consumption prediction update  
**Default:** Every 6 hours

The forecast sensor provides predictions for future consumption based on learned patterns. Currently returns the same average consumption rate for all periods, with future enhancements planned for time-specific forecasting.

**What gets forecasted:**
- Tomorrow's expected consumption
- Next week's average consumption
- Next 14 days average consumption
- Next month average consumption

---

## Manual Updates

### Buttons

#### 1. Test API Connection
**Entity:** `button.[car_name]_test_api_connection`

Tests the Tankerkönig API connection and displays detailed results including:
- API response status
- Number of stations found
- Nearest and cheapest station information
- Request/response debugging information

**Use when:**
- Testing API key validity
- Debugging API connectivity issues
- Verifying station search configuration

#### 2. Import Historical Data
**Entity:** `button.[car_name]_import_historical_data`

Imports historical vehicle data from Home Assistant's recorder database. This backfills:
- Odometer history (up to 90 days)
- Detected refueling events from tank level changes
- Consumption calculations from historical data

**Use when:**
- First time setup to get immediate predictions
- After changing vehicle entities
- To reprocess historical data after configuration changes

**Note:** Import runs automatically on integration startup but can be re-triggered manually with `force_reimport=True`.

#### 3. Refresh Vehicle Data
**Entity:** `button.[car_name]_refresh_vehicle_data`

Immediately fetches current data from configured vehicle entities and updates all sensors.

**Use when:**
- You want instant update without waiting for next interval
- After refueling to immediate detect the event
- Testing entity configuration

### Switches

#### 1. Manual Refresh Switch
**Entity:** `switch.[car_name]_manual_refresh`

Triggers a full data refresh including:
- Fuel price API call
- Vehicle data fetch
- All sensor updates

The switch automatically turns off after completing the refresh.

#### 2. Manual Prediction Switch
**Entity:** `switch.[car_name]_manual_prediction`

Triggers immediate consumption prediction calculation using current data. Useful for:
- Testing prediction accuracy
- Forcing prediction update after configuration changes
- Getting immediate forecast after importing historical data

---

## Configuration Options

### Update Intervals

#### API Update Interval
**Entity:** `number.[car_name]_api_update_interval`  
**Range:** 1-60 minutes  
**Default:** 15 minutes

Controls how often the fuel price API is called and vehicle data is fetched.

**Considerations:**
- Lower values (1-5 min): More up-to-date prices but higher API usage
- Higher values (30-60 min): Reduced API calls but less frequent updates
- Recommended: 10-20 minutes for normal use

#### Consumption Prediction Interval
**Entity:** `number.[car_name]_consumption_prediction_interval`  
**Range:** 0.5-24 hours  
**Default:** 6 hours

Controls how often the prediction engine recalculates forecasts.

**Considerations:**
- Lower values (0.5-2 hours): More responsive to changes but higher CPU usage
- Higher values (12-24 hours): Less frequent updates but lower system load
- Recommended: 6-12 hours for most users

### Data Requirements

#### Minimum Data Points
**Entity:** `number.[car_name]_consumption_min_data_points`  
**Range:** 2-50 points  
**Default:** 5 points

Minimum number of historical odometer readings required before switching from fallback values to historical data predictions.

**Considerations:**
- Lower values (2-3): Faster switch to historical mode but less accurate
- Higher values (10-20): More reliable predictions but longer wait time
- Recommended: 5-10 points for balanced accuracy

---

## Important Warnings

### API Rate Limiting

**Tankerkönig API Limits:**
- The Tankerkönig API has rate limits to prevent abuse
- Excessive API calls may result in temporary IP blocking
- The integration includes automatic randomization (±2%) to distribute load

**Best Practices:**
- Don't set update interval below 5 minutes unless necessary
- Avoid rapid manual refreshes
- One instance per location is sufficient

**Signs of rate limiting:**
- API requests start failing with HTTP 429 errors
- Empty station lists despite valid configuration
- Temporary inability to fetch prices

**What to do:**
- Increase the update interval
- Wait 15-30 minutes before retrying
- Check API usage in `sensor.[car_name]_api_debug`

### System Load

**CPU and Memory Usage:**
The integration performs various calculations that consume system resources:

**Light operations (frequent):**
- Fetching vehicle entity states: Minimal impact
- Storing odometer readings: Very low impact
- Price comparisons: Low impact

**Medium operations (periodic):**
- Refueling detection: Low-medium impact
- Consumption history calculation: Medium impact (iterates through events)
- API requests: Medium impact (network I/O)

**Heavy operations (infrequent):**
- Historical data import: High impact initially (database queries)
- ML-enhanced predictions: Medium-high impact (pattern analysis)
- Weekday statistics recalculation: Medium impact

**Recommendations:**
- Keep default intervals for normal use
- Avoid running manual import repeatedly
- Monitor system resources if running on low-power devices (Raspberry Pi)

### Database Growth

**Storage considerations:**
- Each vehicle entry stores up to 1000 odometer readings
- Up to 100 refueling events per vehicle
- Price history limited to 1000 entries
- Prediction history for accuracy tracking

**Estimated storage:**
- Typical usage: 100-500 KB per vehicle
- With full history: Up to 2-5 MB per vehicle
- Storage location: `.storage/hafwcma_<entry_id>.json`

**Automatic cleanup:**
Oldest entries are automatically removed when limits are reached (FIFO - First In, First Out).

### Data Accuracy

**Prediction accuracy depends on:**
1. **Data quality**: Accurate vehicle entities are essential
2. **Driving consistency**: Regular patterns improve predictions
3. **Time horizon**: Predictions are more accurate for near term
4. **Refueling detection**: Tank level sensor must have sufficient resolution

**Common accuracy issues:**
- Inaccurate odometer readings → Wrong consumption calculations
- Missing refueling events → Gaps in consumption history
- Irregular driving patterns → Lower prediction confidence
- Tank level sensor with large steps → Missed refuelings

**Improving accuracy:**
- Ensure vehicle entities update regularly
- Use high-resolution tank level sensors (continuous values better than steps)
- Allow time for data collection (minimum 2-3 refuelings)
- Check `data_points_percentage` attribute to track progress

---

## Historical Data Import

### Automatic Import

On first startup, the integration automatically imports historical data from Home Assistant's recorder:

**What gets imported:**
- Odometer readings from the past 90 days
- Tank level changes to detect past refuelings
- Calculated consumption between detected refuelings

**Requirements:**
- Home Assistant recorder must be enabled
- Vehicle entities must have historical data
- Odometer and tank level entities must be configured

**Import process:**
1. Waits 10 seconds after integration startup
2. Queries recorder for historical states
3. Processes states in chronological order
4. Detects refueling events (tank level increases > 5L)
5. Calculates consumption between refuelings
6. Stores processed data in integration storage

**Import results:**
Check `button.[car_name]_import_historical_data` attributes after startup:
- `odometer_points_imported`: Number of historical odometer readings
- `refuel_events_detected`: Number of refuelings found
- `date_range`: Time period imported
- `imported`: Success status

### Manual Import

Force re-import of historical data:

1. Press `button.[car_name]_import_historical_data`
2. Wait for completion (typically 10-30 seconds)
3. Check button attributes for results
4. Predictions will update at next prediction interval

**Use cases for manual import:**
- After changing vehicle entity configuration
- If automatic import failed during startup
- To reprocess data after fixing entity issues
- Testing with different lookback periods

### Import Performance

**Time required:**
- 10-30 seconds for 90 days of data
- Depends on database size and history volume
- Non-blocking operation (runs in background)

**Impact:**
- Initial import: Medium database load
- Subsequent operations: Minimal impact
- Import is skipped if already completed (unless forced)

### Troubleshooting Import

**No data imported:**
1. Check that recorder is enabled in Home Assistant
2. Verify vehicle entities have historical data
3. Check entity IDs are correctly configured
4. Review Home Assistant logs for errors

**Fewer events than expected:**
- Tank level sensor may not have sufficient resolution
- Refueling threshold (5L) may be too high for your vehicle
- Check for gaps in historical data

**Incorrect consumption calculations:**
- Verify odometer readings are accurate
- Check that tank capacity is configured correctly
- Ensure refueling events have odometer readings
- Review refueling log for data quality

---

## Summary

**Default Configuration (Recommended for most users):**
- API/Vehicle updates: Every 15 minutes
- Prediction updates: Every 6 hours
- Minimum data points: 5
- Historical import: Automatic on startup (90 days)

**Aggressive Configuration (More frequent updates):**
- API/Vehicle updates: Every 5-10 minutes
- Prediction updates: Every 2-4 hours
- Minimum data points: 3
- ⚠️ Higher API usage and system load

**Conservative Configuration (Minimal system impact):**
- API/Vehicle updates: Every 30-60 minutes
- Prediction updates: Every 12-24 hours
- Minimum data points: 10
- ⚠️ Less responsive to changes

**Monitor your setup:**
- Check `sensor.[car_name]_api_debug` for API status
- Review `data_points_percentage` in prediction sensor
- Watch `data_points_used` to track learning progress
- Use `sensor.[car_name]_average_consumption_history` to verify calculations

**Questions or Issues?**
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common problems
- Check [GitHub Issues](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)
