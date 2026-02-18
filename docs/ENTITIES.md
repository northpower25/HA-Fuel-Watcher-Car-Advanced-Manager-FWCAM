# FWCAM Entity Documentation

This document provides detailed information about all entities in the Fuel Watcher Car Advanced Manager (FWCAM) integration.

## Table of Contents

- [Sensors](#sensors)
  - [Fuel Price Sensor](#fuel-price-sensor)
  - [Tank Level Sensor](#tank-level-sensor)
  - [Range Sensor](#range-sensor)
  - [Nearest Station Sensor](#nearest-station-sensor)
  - [Fuel Price API Debug Sensor](#fuel-price-api-debug-sensor)
  - [Car Data Debug Sensor](#car-data-debug-sensor)
  - [Consumption Prediction Sensor](#consumption-prediction-sensor)
  - [Consumption History Sensor](#consumption-history-sensor)
  - [Consumption Forecast Sensor](#consumption-forecast-sensor)
  - [Refueling Log Sensor](#refueling-log-sensor)
  - [Nearby Cheap Stations Sensor](#nearby-cheap-stations-sensor)
  - [Trip Log Sensor](#trip-log-sensor)
  - [Current Trip Sensor](#current-trip-sensor)
- [Binary Sensors](#binary-sensors)
  - [Proximity Alert Sensor](#proximity-alert-sensor)
  - [On Trip Sensor](#on-trip-sensor)
  - [Telegram Bot Status Sensor](#telegram-bot-status-sensor)
- [Switches](#switches)
  - [Proximity Alerts Switch](#proximity-alerts-switch)
  - [Trip Tracking Switch](#trip-tracking-switch)
- [Buttons](#buttons)
  - [Test Provider Connection Button](#test-provider-connection-button)
  - [Import Historical Data Button](#import-historical-data-button)
  - [Import Historical Trip Data Button](#import-historical-trip-data-button)
  - [Recalculate Trip Statistics Button](#recalculate-trip-statistics-button)
  - [Validate Refueling Events Button](#validate-refueling-events-button)
  - [Refresh Vehicle Data Button](#refresh-vehicle-data-button)
  - [Fuel Price Refresh Button](#fuel-price-refresh-button)
  - [Consumption Prediction Button](#consumption-prediction-button)
  - [Telegram Test Button](#telegram-test-button)
  - [Export Vehicle Data Button](#export-vehicle-data-button)

---

## Sensors

### Fuel Price Sensor

**Entity ID**: `sensor.[vehicle_name]_fuel_price`

**Purpose**: Displays the current fuel price (€/L) at the nearest/cheapest station within the configured search radius.

**Data Source**:
- Fuel price data from the selected provider API (e.g., Tankerkönig)
- Station location data from provider
- Vehicle location from configured position entity or Home Assistant location

**Dependencies**:
- Requires valid API key for fuel price provider
- Uses geolocation data (vehicle position or HA location)
- Referenced by: Refueling recommendations, price trend analysis

**Key Attributes**:
- `station_name`: Name of the cheapest station
- `station_address`: Address of the station
- `distance`: Distance from vehicle/home to station (km)
- `forecast_trend`: Price trend prediction (rising/falling/stable)
- `should_refuel`: Boolean recommendation to refuel now
- `urgency`: Urgency level (low/medium/high/critical)
- `recommendation`: Human-readable recommendation text
- `price_delta`: Price difference vs recent average
- `price_delta_percent`: Price change percentage

**See Also**: [Fuel Price Documentation](./FUEL_PRICE_MONITORING.md)

---

### Tank Level Sensor

**Entity ID**: `sensor.[vehicle_name]_tank_level`

**Purpose**: Displays the current fuel tank level as a percentage (0-100%).

**Data Source**:
- Tank level from configured vehicle entity (CONF_TANK_LEVEL_ENTITY)
- Falls back to estimation based on range if tank level entity is unavailable

**Dependencies**:
- Vehicle integration providing tank level data
- Referenced by: Refueling recommendations, consumption prediction, proximity alerts

**Key Attributes**:
- `liters`: Current fuel in liters (calculated from percentage)
- `tank_capacity`: Total tank capacity in liters
- `last_vehicle_data_refresh`: Timestamp of last vehicle data update
- `data_staleness_warning`: Warning if data is outdated

---

### Range Sensor

**Entity ID**: `sensor.[vehicle_name]_range`

**Purpose**: Displays the estimated remaining range in kilometers based on current fuel level.

**Data Source**:
- Range data from configured vehicle entity (CONF_RANGE_ENTITY)
- Falls back to estimation based on tank level and average consumption

**Dependencies**:
- Vehicle integration providing range data
- Referenced by: Refueling recommendations, trip planning, consumption prediction

**Key Attributes**:
- `days_left`: Estimated days until refueling needed (based on consumption patterns)
- `last_vehicle_data_refresh`: Timestamp of last vehicle data update
- `data_staleness_warning`: Warning if data is outdated

---

### Nearest Station Sensor

**Entity ID**: `sensor.[vehicle_name]_nearest_station`

**Purpose**: Displays the name of the nearest/cheapest fuel station.

**Data Source**:
- Station data from fuel price provider API
- Vehicle location from position entity

**Dependencies**:
- Fuel Price Sensor (uses same API data)
- Referenced by: Navigation helpers, station recommendations

**Key Attributes**:
- `station_address`: Full address of the station
- `distance`: Distance to station (km)
- `price`: Current fuel price at this station

---

### Fuel Price API Debug Sensor

**Entity ID**: `sensor.[vehicle_name]_fuel_price_api_debug`

**Purpose**: Provides debugging information about API requests and responses for fuel price data.

**Data Source**:
- API request parameters (URL, coordinates, radius, fuel type)
- API response data (station count, response structure)
- Error information if API calls fail

**Dependencies**:
- Fuel Price Sensor (monitors its API calls)
- For developers and troubleshooting

**Key Attributes**:
- `api_endpoint`: URL of the API being called
- `request_parameters`: Parameters sent to API
- `response_status`: HTTP status code
- `stations_count`: Number of stations returned
- `error_details`: Error messages if request failed

---

### Car Data Debug Sensor

**Entity ID**: `sensor.[vehicle_name]_car_data_debug`

**Purpose**: Provides debugging information about vehicle entity data retrieval.

**Data Source**:
- Vehicle entity states and attributes
- Data refresh timestamps
- Entity availability status

**Dependencies**:
- All configured vehicle entities
- For developers and troubleshooting

**Key Attributes**:
- `odometer_entity`: Configured odometer entity ID
- `tank_level_entity`: Configured tank level entity ID
- `range_entity`: Configured range entity ID
- `position_entity`: Configured position entity ID
- Entity state values and timestamps

---

### Consumption Prediction Sensor

**Entity ID**: `sensor.[vehicle_name]_consumption_prediction`

**Purpose**: Predicts the number of days until refueling is needed based on consumption patterns.

**Data Source**:
- Historical refueling data from storage
- Current vehicle data (range, tank level)
- Weekday consumption patterns
- Trip data if available

**Dependencies**:
- Refueling Log Sensor (historical data)
- Tank Level Sensor and/or Range Sensor
- Trip Log Sensor (optional, improves accuracy)

**Key Attributes**:
- `days_until_refuel`: Predicted days until refueling needed
- `confidence`: Prediction confidence level (0-100%)
- `data_source`: Method used for prediction (range/tank/consumption)
- `data_points_used`: Number of historical data points used
- `avg_consumption_rate`: Average fuel consumption (L/day)
- `avg_daily_km`: Average daily kilometers driven
- `predicted_refuel_date`: Estimated date when refueling will be needed

**See Also**: [Consumption Prediction Documentation](./dev_docs/REFUELING_PREDICTION_IMPROVEMENT.md)

---

### Consumption History Sensor

**Entity ID**: `sensor.[vehicle_name]_consumption_history`

**Purpose**: Displays historical consumption statistics over various time periods.

**Data Source**:
- Historical refueling data from storage
- Odometer readings over time

**Dependencies**:
- Refueling Log Sensor (data source)
- Referenced by: Charts, consumption trends, forecasting

**Key Attributes**:
- `consumption_today`: Today's consumption stats
- `consumption_7_days`: Last 7 days consumption
- `consumption_14_days`: Last 14 days consumption
- `consumption_30_days`: Last 30 days consumption
- Each period includes: liters, km, L/100km, cost

---

### Consumption Forecast Sensor

**Entity ID**: `sensor.[vehicle_name]_consumption_forecast`

**Purpose**: Forecasts future fuel costs and consumption based on usage patterns.

**Data Source**:
- Historical consumption data
- Current fuel prices
- Predicted consumption patterns

**Dependencies**:
- Consumption History Sensor
- Fuel Price Sensor
- Consumption Prediction Sensor

**Key Attributes**:
- `forecast_7_days`: 7-day forecast (cost, liters)
- `forecast_30_days`: 30-day forecast (cost, liters)
- `forecast_90_days`: 90-day forecast (cost, liters)
- Forecast confidence levels

---

### Refueling Log Sensor

**Entity ID**: `sensor.[vehicle_name]_refueling_log`

**Purpose**: Displays the complete history of refueling events.

**Data Source**:
- Refueling events from storage
- Telegram bot submissions (if configured)
- Manual entries via services

**Dependencies**:
- Storage system (SQLite database)
- Telegram Bot (optional, for automatic logging)
- Referenced by: Consumption calculations, statistics, trip correlation

**Key Attributes**:
- `refueling_events`: List of all refueling events
- Each event includes: timestamp, liters, price, station, odometer, fuel_type
- `total_refuelings`: Count of refueling events
- `last_refueling_date`: Date of most recent refueling

**See Also**: [Refueling Log Guide](./REFUELING_LOG_GUIDE.md)

---

### Nearby Cheap Stations Sensor

**Entity ID**: `sensor.[vehicle_name]_nearby_cheap_stations`

**Purpose**: Displays a list of nearby cheap stations sorted by price, for geolocation-based features.

**Data Source**:
- Fuel price provider API
- Vehicle real-time location (position entity)
- Configured search radius

**Dependencies**:
- Position entity (must provide GPS coordinates)
- Fuel Price Sensor (uses same provider)
- Referenced by: Proximity alerts, navigation

**Key Attributes**:
- `stations`: List of stations with name, address, distance, price
- `search_radius_km`: Current search radius
- `vehicle_latitude`: Current vehicle latitude
- `vehicle_longitude`: Current vehicle longitude
- `max_stations`: Maximum number of stations to track

**See Also**: [Geolocation Concept](./GEOLOCATION_CONCEPT_EN.md)

---

### Trip Log Sensor

**Entity ID**: `sensor.[vehicle_name]_trip_log`

**Purpose**: Displays the history of all tracked trips.

**Data Source**:
- Trip tracking system (when enabled)
- Odometer readings at trip start/end
- Trip timestamps and durations

**Dependencies**:
- Trip Tracking Switch (must be enabled)
- Odometer entity
- Referenced by: Consumption calculation, trip statistics

**Key Attributes**:
- `trips`: List of all trip events
- Each trip includes: start/end time, distance, duration, trip_type
- `total_trips`: Count of trips
- `last_trip_date`: Date of most recent trip

**See Also**: [Trip Tracking Documentation](./TRIP_TRACKING_README.md)

---

### Current Trip Sensor

**Entity ID**: `sensor.[vehicle_name]_current_trip`

**Purpose**: Displays information about the currently active trip (if any).

**Data Source**:
- Real-time trip tracking
- Current odometer reading
- Trip start timestamp

**Dependencies**:
- Trip Tracking Switch (must be enabled)
- On Trip Sensor (indicates if trip is active)
- Odometer entity

**Key Attributes**:
- `distance_km`: Current trip distance
- `duration`: Trip duration (time elapsed)
- `timestamp_start`: Trip start timestamp
- `current_odometer`: Current odometer reading

---

## Binary Sensors

### Proximity Alert Sensor

**Entity ID**: `binary_sensor.[vehicle_name]_proximity_alert`

**Purpose**: Indicates when the vehicle is near a cheap fuel station (within configured threshold).

**Data Source**:
- Vehicle GPS location (position entity)
- Nearby cheap stations data
- Configured proximity threshold

**Dependencies**:
- Proximity Alerts Switch (must be enabled)
- Position entity (GPS coordinates)
- Nearby Cheap Stations Sensor
- Tank Level Sensor (alerts only when tank below threshold)

**Key Attributes**:
- `station_name`: Name of the nearby cheap station
- `station_address`: Address of the station
- `distance`: Current distance to station (km)
- `price`: Fuel price at this station
- `proximity_threshold_km`: Alert threshold distance
- `navigation_urls`: Links to navigation apps
- `alert_message`: Human-readable alert text

**See Also**: [Geolocation Concept](./GEOLOCATION_CONCEPT_EN.md)

---

### On Trip Sensor

**Entity ID**: `binary_sensor.[vehicle_name]_on_trip`

**Purpose**: Indicates whether the vehicle is currently on a trip (moving).

**Data Source**:
- Trip tracking system
- Odometer changes
- Trip start/end events

**Dependencies**:
- Trip Tracking Switch (must be enabled)
- Odometer entity
- Referenced by: Trip Log Sensor, Current Trip Sensor

**Key Attributes**:
- `trip_tracking_enabled`: Whether trip tracking is active
- `timestamp_start`: When the current trip started
- `distance_km`: Distance traveled on current trip
- `duration`: Trip duration
- `duration_minutes`: Duration in minutes

---

### Telegram Bot Status Sensor

**Entity ID**: `binary_sensor.[vehicle_name]_telegram_bot_status`

**Purpose**: Indicates the connection status and health of the Telegram bot integration.

**Data Source**:
- Telegram bot connection test
- Integration availability check
- Handler initialization status

**Dependencies**:
- Telegram configuration (token and chat ID)
- Home Assistant's telegram_bot integration (if using integration method)

**Key Attributes**:
- `telegram_bot_integration`: Name of HA telegram_bot integration
- `chat_id_configured`: Whether chat ID is configured
- `telegram_method`: Method being used (integration/direct_api)
- `telegram_handler_active`: Whether handler is initialized
- `refueling_handler_active`: Whether refueling handler is active
- `pending_refuelings`: Number of pending refueling confirmations

**See Also**: [Telegram Setup](./TELEGRAM_SETUP.md)

---

## Switches

### Proximity Alerts Switch

**Entity ID**: `switch.[vehicle_name]_proximity_alerts`

**Purpose**: Enables or disables proximity alerts for nearby cheap fuel stations.

**Data Source**:
- Configuration entry options (persisted)

**Dependencies**:
- Position entity (GPS coordinates)
- Nearby Cheap Stations Sensor
- Referenced by: Proximity Alert Sensor

**Key Attributes**:
None (simple on/off switch)

**See Also**: [Geolocation Concept](./GEOLOCATION_CONCEPT_EN.md)

---

### Trip Tracking Switch

**Entity ID**: `switch.[vehicle_name]_trip_tracking`

**Purpose**: Enables or disables automatic trip tracking based on odometer changes.

**Data Source**:
- Configuration entry options (persisted)
- Trip tracking state and history

**Dependencies**:
- Odometer entity
- Referenced by: Trip Log Sensor, On Trip Sensor, Current Trip Sensor

**Key Attributes**:
- `privacy_notice_accepted`: Whether user accepted privacy notice
- `last_enabled_at`: Timestamp when last enabled
- `last_disabled_at`: Timestamp when last disabled
- `total_trips`: Total number of trips tracked
- `total_distance_km`: Total distance tracked
- `business_trips`: Count of business trips
- `private_trips`: Count of private trips
- `commute_trips`: Count of commute trips

**See Also**: [Trip Tracking Documentation](./TRIP_TRACKING_README.md)

---

## Buttons

### Test Provider Connection Button

**Entity ID**: `button.[vehicle_name]_test_provider_connection`

**Purpose**: Tests the connection to the fuel price provider API and displays results.

**Data Source**:
- API test request to provider
- Current configuration (API key, location, fuel type)

**Dependencies**:
- Configured API provider and API key

**Result Attributes** (temporary, in notification):
- Number of stations found
- Response time
- Error details if test fails

---

### Import Historical Data Button

**Entity ID**: `button.[vehicle_name]_import_historical_data`

**Purpose**: Imports historical fuel price data from the provider API for the past 30 days.

**Data Source**:
- Provider API historical data endpoint
- Storage system for persisting data

**Dependencies**:
- Fuel price provider with historical data support
- Storage system

**Result Attributes** (in logs):
- Number of data points imported
- Date range of imported data

---

### Import Historical Trip Data Button

**Entity ID**: `button.[vehicle_name]_import_historical_trip_data`

**Purpose**: Recalculates trip history from existing odometer observations.

**Data Source**:
- Historical odometer observations in storage
- Trip detection algorithm

**Dependencies**:
- Odometer entity with historical data
- Storage system

**Result Attributes** (in logs):
- Number of trips detected
- Date range processed

---

### Recalculate Trip Statistics Button

**Entity ID**: `button.[vehicle_name]_recalculate_trip_statistics`

**Purpose**: Recalculates aggregate trip statistics from the trip log.

**Data Source**:
- Trip log data
- Refueling event data (for correlation)

**Dependencies**:
- Trip Log Sensor

**Result Attributes** (in logs):
- Statistics updated
- Number of trips processed

---

### Validate Refueling Events Button

**Entity ID**: `button.[vehicle_name]_validate_refueling_events`

**Purpose**: Validates all refueling events and auto-detects test/invalid entries.

**Data Source**:
- Refueling log data
- Validation rules (timestamps, amounts, odometer progression)

**Dependencies**:
- Refueling Log Sensor
- Storage system

**Result Attributes** (in notification):
- Number of events validated
- Number of issues detected
- Events marked for exclusion

**See Also**: [Refueling Event Validation](./dev_docs/REFUELING_EVENT_VALIDATION.md)

---

### Refresh Vehicle Data Button

**Entity ID**: `button.[vehicle_name]_refresh_vehicle_data`

**Purpose**: Manually triggers a refresh of all vehicle entity data (odometer, tank level, range, position).

**Data Source**:
- Vehicle integration entities
- Vehicle data tracker

**Dependencies**:
- All configured vehicle entities

**Result Attributes** (temporary):
- Updated values for each entity
- Timestamp of refresh

---

### Fuel Price Refresh Button

**Entity ID**: `button.[vehicle_name]_fuel_price_refresh`

**Purpose**: Manually triggers a refresh of fuel price data from the provider API.

**Data Source**:
- Fuel price provider API

**Dependencies**:
- Fuel Price Sensor

**Result Attributes** (temporary):
- New price data
- Number of stations found

---

### Consumption Prediction Button

**Entity ID**: `button.[vehicle_name]_consumption_prediction`

**Purpose**: Manually triggers a recalculation of the consumption prediction.

**Data Source**:
- Historical refueling data
- Current vehicle data

**Dependencies**:
- Consumption Prediction Sensor
- Refueling Log Sensor

**Result Attributes** (temporary):
- New prediction values
- Confidence level

---

### Telegram Test Button

**Entity ID**: `button.[vehicle_name]_telegram_test`

**Purpose**: Sends a test message to Telegram to verify bot connectivity.

**Data Source**:
- Telegram configuration

**Dependencies**:
- Telegram Bot configuration
- Telegram Bot Status Sensor

**Result Attributes** (temporary):
- Test message sent status
- Response from Telegram API

**See Also**: [Telegram Setup](./TELEGRAM_SETUP.md)

---

### Export Vehicle Data Button

**Entity ID**: `button.[vehicle_name]_export_vehicle_data`

**Purpose**: Exports all vehicle data (refuelings, trips, statistics) to CSV file.

**Data Source**:
- Refueling log
- Trip log
- Consumption statistics
- Storage system

**Dependencies**:
- Storage system
- All data sensors

**Result Attributes** (in notification):
- Path to exported file
- Number of records exported
- File format details

---

## Integration Information

All entities in FWCAM share common characteristics:

### Device Information

All entities are grouped under a single device:
- **Device Name**: Vehicle name (configured during setup)
- **Device Manufacturer**: FWCAM Integration
- **Device Model**: Car Fuel Manager
- **Device Identifier**: Integration entry ID

### Entity Naming

Entities follow the pattern:
- `{platform}.{vehicle_name}_{entity_name}`

Example: `sensor.my_car_fuel_price`

### Update Intervals

- **Fuel Price Data**: Configurable, default 5 minutes
- **Vehicle Data**: On-demand when vehicle integration updates
- **Consumption Prediction**: Configurable, default every 6 hours
- **Geolocation**: 30 seconds when moving, 5 minutes when stationary

### Data Storage

Most entities rely on the integration's internal storage system:
- **Location**: `.storage/hafwcma_{entry_id}.json`
- **Format**: JSON
- **Backup**: Recommended to include in Home Assistant backups

---

## Documentation Links

- [Main Documentation](../README.md)
- [Installation Guide](../HACS_INSTALLATION.md)
- [Refueling Log Guide](./REFUELING_LOG_GUIDE.md)
- [Trip Tracking Guide](./TRIP_TRACKING_README.md)
- [Geolocation Concept](./GEOLOCATION_CONCEPT_EN.md)
- [Telegram Setup](./TELEGRAM_SETUP.md)
- [Developer Notes](../DEVELOPER_NOTES.md)
- [API Documentation](./dev_docs/API.md)

---

**Last Updated**: 2026-02-18
**Integration Version**: See [manifest.json](../custom_components/hafwcma/manifest.json)
