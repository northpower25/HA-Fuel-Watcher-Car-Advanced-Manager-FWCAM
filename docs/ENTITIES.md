# FWCAM Entity Documentation

This document provides detailed information about all entities in the Fuel Watcher Car Advanced Manager (FWCAM) integration, including their update behavior, data sources, and manual triggers.

**For detailed update frequency information, see**: [Data Update Frequencies](./user_docs/DATA_UPDATE_FREQUENCIES_DE.md)

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

**Update Behavior**:
- **First Update**: Automatically after Home Assistant startup (when `homeassistant_started` event fires)
- **Update Interval**: Configurable via `number.[vehicle_name]_api_update_interval` 
  - Default: 15 minutes
  - Range: 1-60 minutes
  - Applied jitter: ±2% randomization to prevent simultaneous API calls
- **External Sources**: 
  - Fuel price API (e.g., Tankerkönig): Queried at each update interval
  - Vehicle/HA location: Read from configured entities at each update
- **Manual Triggers**:
  - `button.[vehicle_name]_fuel_price_refresh`: Immediate API query
  - `button.[vehicle_name]_test_api_connection`: Test connection with debug output
- **Configuration**: See [Data Update Frequencies](./user_docs/DATA_UPDATE_FREQUENCIES_DE.md) for detailed interval configuration

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

**Update Behavior**:
- **First Update**: Automatically after Home Assistant startup (when `homeassistant_started` event fires)
- **Update Interval**: Synchronized with coordinator updates
  - Default: 15 minutes (same as API update interval)
  - Configurable via `number.[vehicle_name]_api_update_interval`
- **External Sources**: 
  - Configured tank level entity: Read at each coordinator update
  - Range entity: Used for fallback estimation if tank level unavailable
- **Manual Triggers**:
  - `button.[vehicle_name]_refresh_vehicle_data`: Immediate refresh of all vehicle data
- **Configuration**: Follows main coordinator update interval

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

**Update Behavior**:
- **First Update**: Automatically after Home Assistant startup (when `homeassistant_started` event fires)
- **Update Interval**: Synchronized with coordinator updates
  - Default: 15 minutes (same as API update interval)
  - Configurable via `number.[vehicle_name]_api_update_interval`
- **External Sources**: 
  - Configured range entity: Read at each coordinator update
  - Tank level and consumption data: Used for fallback estimation if range unavailable
- **Manual Triggers**:
  - `button.[vehicle_name]_refresh_vehicle_data`: Immediate refresh of all vehicle data
- **Configuration**: Follows main coordinator update interval

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

**Update Behavior**:
- **First Update**: Automatically after Home Assistant startup (when `homeassistant_started` event fires)
- **Update Interval**: Synchronized with Fuel Price Sensor updates
  - Default: 15 minutes
  - Configurable via `number.[vehicle_name]_api_update_interval`
- **External Sources**: 
  - Same API data as Fuel Price Sensor (no additional API calls)
  - Vehicle position from configured entity
- **Manual Triggers**:
  - `button.[vehicle_name]_fuel_price_refresh`: Triggers update via coordinator
- **Configuration**: Follows Fuel Price Sensor configuration

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

**Update Behavior**:
- **First Update**: Automatically after Home Assistant startup (when `homeassistant_started` event fires)
- **Update Interval**: Synchronized with Fuel Price Sensor updates
  - Default: 15 minutes
  - Captures debug data from each API request
- **External Sources**: 
  - Debug information captured from provider API calls
  - No additional API calls (passive monitoring)
- **Manual Triggers**:
  - `button.[vehicle_name]_fuel_price_refresh`: Triggers new API call to capture fresh debug data
  - `button.[vehicle_name]_test_api_connection`: Provides detailed test output
- **Configuration**: Follows Fuel Price Sensor configuration

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

**Update Behavior**:
- **First Update**: Automatically after Home Assistant startup (when `homeassistant_started` event fires)
- **Update Interval**: Synchronized with coordinator updates
  - Default: 15 minutes
  - Captures vehicle data from each coordinator refresh
- **External Sources**: 
  - All configured vehicle entities (odometer, tank, range, position)
  - Entity states read from Home Assistant state machine
  - No external API calls (internal monitoring only)
- **Manual Triggers**:
  - `button.[vehicle_name]_refresh_vehicle_data`: Triggers immediate vehicle data fetch
- **Configuration**: Follows main coordinator update interval

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

**Update Behavior**:
- **First Update**: Automatically after Home Assistant startup (when `homeassistant_started` event fires)
- **Update Interval**: Separate configurable interval for consumption predictions
  - Default: 6 hours
  - Range: 0.5-24 hours
  - Configurable via `number.[vehicle_name]_consumption_prediction_interval`
- **External Sources**: 
  - Historical refueling data from storage (no external API)
  - Current vehicle data (tank level, range, odometer)
  - Trip data if trip tracking is enabled
- **Manual Triggers**:
  - `button.[vehicle_name]_consumption_prediction`: Forces immediate recalculation
  - Automatic recalculation after historical data import
- **Initial Data Requirements**:
  - Minimum data points configurable via `number.[vehicle_name]_consumption_min_data_points` (default: 5)
  - Until minimum reached, uses fallback values with lower confidence
  - Recommended: Use `button.[vehicle_name]_import_historical_data` for immediate predictions after setup
- **Configuration**: See [Data Update Frequencies](./user_docs/DATA_UPDATE_FREQUENCIES_DE.md)

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

**Update Behavior**:
- **First Update**: Automatically after Home Assistant startup (when `homeassistant_started` event fires)
- **Update Interval**: Recalculated at each coordinator update
  - Default: 15 minutes (same as API update interval)
  - Updates whenever new vehicle or refueling data is available
- **External Sources**: 
  - Historical refueling events from storage
  - Odometer readings from vehicle data
  - No external API calls (uses stored data)
- **Manual Triggers**:
  - Updates automatically when new refueling events are added
  - Recalculated after historical data import
  - No dedicated manual trigger (follows coordinator updates)
- **Data Requirements**:
  - Requires at least 2 refueling events within each time period for calculation
  - Shows "unavailable" or N/A if insufficient data for a period
- **Configuration**: Follows main coordinator update interval

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

**Update Behavior**:
- **First Update**: Automatically after Home Assistant startup (when `homeassistant_started` event fires)
- **Update Interval**: Synchronized with Consumption Prediction updates
  - Default: 6 hours (same as consumption prediction interval)
  - Configurable via `number.[vehicle_name]_consumption_prediction_interval`
- **External Sources**: 
  - Consumption History Sensor data
  - Current fuel prices from Fuel Price Sensor
  - Consumption Prediction Sensor patterns
  - No additional external API calls
- **Manual Triggers**:
  - `button.[vehicle_name]_consumption_prediction`: Triggers forecast recalculation
  - Updates automatically when consumption prediction updates
- **Data Requirements**:
  - Requires sufficient historical consumption data
  - Forecast accuracy improves with more historical data points
- **Configuration**: Follows consumption prediction interval

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

**Update Behavior**:
- **First Update**: Automatically after Home Assistant startup (when `homeassistant_started` event fires)
- **Update Interval**: Event-driven updates (no regular polling)
  - Updates immediately when new refueling events are added
  - Updates when refueling events are edited or deleted
  - Syncs with coordinator updates for attribute refresh
- **External Sources**: 
  - Storage system (`.storage/hafwcma_{entry_id}.json`)
  - Telegram bot submissions (if configured)
  - Manual service calls (`hafwcma.add_refuel_event`, `hafwcma.update_refuel_event`)
  - No external API queries
- **Manual Triggers**:
  - Add event: `hafwcma.add_refuel_event` service
  - Update event: `hafwcma.update_refuel_event` service  
  - Delete event: `hafwcma.delete_refuel_event` service
  - Import historical: `button.[vehicle_name]_import_historical_data`
- **Initial Data**:
  - Automatically imports historical refueling data on first setup (up to 90 days)
  - Import runs once automatically, can be re-run manually with force flag
- **Configuration**: No configurable intervals (event-driven)

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

**Update Behavior**:
- **First Update**: Automatically after Home Assistant startup (when `homeassistant_started` event fires)
- **Update Interval**: Synchronized with Fuel Price Sensor updates
  - Default: 15 minutes when position is static
  - More frequent when vehicle is moving (depends on position entity updates)
- **External Sources**: 
  - Same API data as Fuel Price Sensor (no additional API calls)
  - Vehicle position from configured GPS entity (real-time)
  - Filters and sorts existing station data by proximity
- **Manual Triggers**:
  - `button.[vehicle_name]_fuel_price_refresh`: Refreshes station data
  - Position entity changes trigger automatic updates
- **Configuration**: 
  - Search radius: Configurable via integration options
  - Station count: Configurable (default based on cheap_stations_count)
  - Follows Fuel Price Sensor update configuration

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

**Update Behavior**:
- **First Update**: Automatically after Home Assistant startup (when `homeassistant_started` event fires)
- **Update Interval**: Event-driven updates (no regular polling)
  - Updates when trip tracking switch is enabled
  - Updates when trips start or end (based on odometer changes)
  - Syncs with coordinator updates for attribute refresh
- **External Sources**: 
  - Odometer entity: Monitored for changes to detect trips
  - Storage system for trip persistence
  - No external API queries
- **Manual Triggers**:
  - Add trip: `hafwcma.add_trip` service
  - Edit trip: `hafwcma.edit_trip` service
  - Delete trip: `hafwcma.delete_trip` service
  - Import historical: `button.[vehicle_name]_import_historical_trip_data`
  - Recalculate: `button.[vehicle_name]_recalculate_trip_statistics`
- **Activation Requirements**:
  - Trip Tracking Switch must be enabled
  - Odometer entity must be configured and available
- **Initial Data**:
  - Can import historical trips from odometer data on first setup
  - Use `button.[vehicle_name]_import_historical_trip_data` for initial import
- **Configuration**: No configurable intervals (event-driven based on odometer changes)

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

**Update Behavior**:
- **First Update**: When a trip starts (triggered by odometer change)
- **Update Interval**: Real-time updates during active trip
  - Updates with each coordinator refresh (default: 15 minutes)
  - Updates when odometer changes
  - Clears when trip ends
- **External Sources**: 
  - Odometer entity: For current reading and distance calculation
  - Trip tracking system: For trip start/end detection
  - No external API queries
- **Manual Triggers**:
  - No manual triggers (automatic based on trip state)
  - Trip state controlled by Trip Tracking Switch
- **Activation Requirements**:
  - Trip Tracking Switch must be enabled
  - On Trip Sensor must indicate active trip
  - Odometer entity must be available
- **Configuration**: Follows coordinator update interval when trip is active

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

**Update Behavior**:
- **First Update**: When proximity alerts are enabled
- **Update Interval**: Real-time based on position changes
  - Updates when vehicle position changes
  - Evaluates proximity at each coordinator update (default: 15 minutes)
  - Faster updates when vehicle is moving
- **External Sources**: 
  - Position entity: GPS coordinates (read from vehicle integration)
  - Nearby Cheap Stations Sensor: Station list and prices
  - Tank Level Sensor: Current tank level for alert threshold
  - No additional external API calls
- **Manual Triggers**:
  - No manual triggers (automatic based on position)
  - Can be enabled/disabled via Proximity Alerts Switch
- **Activation Requirements**:
  - Proximity Alerts Switch must be enabled
  - Position entity must provide valid GPS coordinates
  - Tank level must be below configured threshold (default: 30%)
- **Alert Behavior**:
  - Cooldown period: 15 minutes between alerts for same station
  - Hysteresis: Requires 10% distance increase to reset alert
- **Configuration**: 
  - Alert distance: Configurable via integration options (default: 2 km)
  - Tank threshold: Configurable (default: 30%)

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

**Update Behavior**:
- **First Update**: When trip tracking is enabled and odometer changes detected
- **Update Interval**: Event-driven (no regular polling)
  - Updates immediately when trip starts (odometer increase detected)
  - Updates immediately when trip ends (odometer stable)
  - Syncs with coordinator updates during active trip
- **External Sources**: 
  - Odometer entity: Monitored for changes to detect movement
  - Trip tracking system: Internal state management
  - No external API queries
- **Manual Triggers**:
  - No manual triggers (automatic based on odometer changes)
  - Trip tracking enabled/disabled via Trip Tracking Switch
- **Activation Requirements**:
  - Trip Tracking Switch must be enabled
  - Odometer entity must be available and updating
- **Trip Detection Logic**:
  - Trip starts: Odometer increase detected
  - Trip ends: Odometer stable for configured period
- **Configuration**: No configurable intervals (event-driven)

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

**Update Behavior**:
- **First Update**: At integration setup
- **Update Interval**: Event-driven status checks
  - Updates when Telegram configuration changes
  - Updates when handler status changes
  - Periodic health check every 5 minutes
- **External Sources**: 
  - Telegram Bot API (connection test)
  - Home Assistant telegram_bot integration (if using integration method)
  - Internal handler status monitoring
- **Manual Triggers**:
  - `button.[vehicle_name]_telegram_test`: Tests connection and updates status
  - Status updates automatically when configuration changes
- **Activation Requirements**:
  - Telegram token must be configured
  - Chat ID must be configured
  - For integration method: HA telegram_bot integration must be available
- **Configuration**: Telegram method and credentials configured during setup

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

**Update Behavior**:
- **First Update**: At integration setup (reads saved state)
- **Update Interval**: Event-driven (no regular updates)
  - State persisted immediately when toggled
  - Affects Proximity Alert Sensor behavior
- **External Sources**: 
  - Configuration entry options (persistent storage)
  - No external API queries
- **Manual Triggers**:
  - Toggle switch on/off to enable/disable proximity alerts
  - State change triggers immediate update to Proximity Alert Sensor
- **Configuration**: State persisted in integration configuration

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

**Update Behavior**:
- **First Update**: At integration setup (reads saved state)
- **Update Interval**: Event-driven (no regular updates)
  - State persisted immediately when toggled
  - Statistics update when trips are added/modified
- **External Sources**: 
  - Configuration entry options (persistent storage)
  - Trip log data for statistics
  - No external API queries
- **Manual Triggers**:
  - Toggle switch on/off to enable/disable trip tracking
  - State change triggers trip tracking activation/deactivation
- **Effects When Enabled**:
  - Enables On Trip Sensor
  - Activates automatic trip detection from odometer changes
  - Enables Trip Log and Current Trip sensors
- **Configuration**: State and statistics persisted in integration configuration

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

**Update Behavior**:
- **Trigger**: Manual press only
- **Operation**: One-time synchronous API test
  - Sends test request to configured fuel price API
  - Returns results immediately (typically < 5 seconds)
  - Updates Fuel Price API Debug Sensor with test results
- **External Sources**: 
  - Fuel price provider API (test query)
  - Uses configured API key, location, radius, and fuel type
- **When to Use**:
  - Initial setup to verify API credentials
  - Troubleshooting API connection issues
  - Testing after configuration changes
- **Effects**: No permanent data changes, only temporary test results

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

**Update Behavior**:
- **Trigger**: Manual press or automatic on first setup
- **Operation**: One-time asynchronous import (runs in background)
  - **Automatic**: Runs once on initial integration setup (10 seconds after HA start)
  - **Manual**: Can be triggered via button press
  - **Duration**: Typically 10-30 seconds for 90 days of data
- **External Sources**: 
  - Home Assistant Recorder database (historical entity states)
  - Reads odometer and tank level history (up to 90 days)
  - No external API calls
- **Import Process**:
  1. Queries recorder for historical vehicle entity states
  2. Processes odometer readings chronologically
  3. Detects refueling events from tank level changes (>5L increase)
  4. Calculates consumption between refuelings
  5. Stores processed data in integration storage
- **When to Use**:
  - **Initial Setup**: Automatic import provides immediate predictions
  - **After Entity Changes**: Re-import after changing vehicle entities
  - **Data Refresh**: Force re-import with `force_reimport=True`
  - **Missing Data**: If automatic import failed at startup
- **Effects**: 
  - Populates Refueling Log Sensor with historical events
  - Enables immediate consumption predictions
  - Updates Consumption History Sensor with historical data
- **Requirements**:
  - HA Recorder must be enabled
  - Vehicle entities must have historical data
  - Configured tank level and odometer entities

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

**Update Behavior**:
- **Trigger**: Manual press only
- **Operation**: One-time asynchronous analysis (runs in background)
  - Analyzes historical odometer data to reconstruct trips
  - Duration depends on data volume (typically 30-60 seconds)
- **External Sources**: 
  - Home Assistant Recorder database (historical odometer states)
  - No external API calls
- **Import Process**:
  1. Queries recorder for historical odometer readings
  2. Analyzes patterns to detect trip start/end
  3. Calculates trip distances and durations
  4. Stores detected trips in trip log
- **When to Use**:
  - Initial setup to populate trip history
  - After enabling trip tracking for the first time
  - To recover trips from odometer data
- **Effects**: 
  - Populates Trip Log Sensor with historical trips
  - Updates trip statistics
  - Improves consumption predictions (if trips correlate with refuelings)
- **Requirements**:
  - Trip Tracking Switch must be enabled
  - Odometer entity must have historical data in recorder
  - Sufficient historical data for pattern detection

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

**Update Behavior**:
- **Trigger**: Manual press only
- **Operation**: Synchronous calculation (immediate)
  - Recalculates aggregate statistics from trip log
  - Typically completes in < 1 second
- **External Sources**: 
  - Trip log data from storage
  - Refueling log for trip-refueling correlation
  - No external API calls
- **Calculation Process**:
  - Aggregates total distance, trips by category
  - Calculates average trip duration and distance
  - Updates Trip Tracking Switch attributes
- **When to Use**:
  - After manual trip data corrections
  - After importing historical trip data
  - If statistics appear inconsistent
- **Effects**: Updates trip statistics in Trip Tracking Switch attributes

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

**Update Behavior**:
- **Trigger**: Manual press only
- **Operation**: Synchronous validation (immediate)
  - Validates all refueling events in storage
  - Typically completes in < 2 seconds
- **External Sources**: 
  - Refueling log data from storage
  - No external API calls
- **Validation Rules**:
  - Chronological timestamp ordering
  - Reasonable fuel amounts (0 < liters ≤ tank capacity)
  - Odometer progression (increasing values)
  - Price reasonableness (if configured)
- **When to Use**:
  - After bulk data import
  - If suspicious refueling events exist
  - Periodic data quality checks
- **Effects**: 
  - Marks invalid events with data quality flags
  - Updates Refueling Log Sensor
  - May affect consumption calculations if events excluded

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

**Update Behavior**:
- **Trigger**: Manual press only
- **Operation**: Synchronous entity state read (immediate)
  - Reads current state from all configured vehicle entities
  - Typically completes in < 1 second
- **External Sources**: 
  - Odometer, tank level, range, and position entities
  - Reads from Home Assistant state machine (no new vehicle API calls)
  - No external API queries
- **When to Use**:
  - Immediate update without waiting for next interval
  - After refueling to detect event sooner
  - Testing entity configuration
  - When data appears stale
- **Effects**: 
  - Updates all vehicle-data-dependent sensors
  - Triggers refueling detection if applicable
  - Updates coordinator cache
- **Note**: Does not force vehicle integration to query the vehicle; only reads current HA entity states

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

**Update Behavior**:
- **Trigger**: Manual press only
- **Operation**: Asynchronous API query (runs in background)
  - Queries fuel price provider API
  - Typically completes in 2-5 seconds
- **External Sources**: 
  - Fuel price provider API (e.g., Tankerkönig)
  - Uses configured API key, location, radius, fuel type
- **When to Use**:
  - Immediate price update without waiting for next interval
  - Before planning a refueling stop
  - After receiving a price drop notification
- **Effects**: 
  - Updates Fuel Price Sensor
  - Updates Nearest Station Sensor
  - Updates Nearby Cheap Stations Sensor
  - Updates Fuel Price API Debug Sensor
  - Triggers coordinator data update
- **Note**: Counts toward API rate limits; avoid excessive manual refreshes

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

**Update Behavior**:
- **Trigger**: Manual press only
- **Operation**: Synchronous calculation (immediate)
  - Recalculates consumption prediction from stored data
  - Typically completes in < 1 second
- **External Sources**: 
  - Historical refueling data from storage
  - Current vehicle data (tank, range, odometer)
  - Trip data if available
  - No external API calls
- **When to Use**:
  - Force prediction update without waiting for interval
  - After adding/editing refueling events
  - After importing historical data
  - Testing prediction accuracy
- **Effects**: 
  - Updates Consumption Prediction Sensor immediately
  - Updates predicted refuel date
  - Recalculates confidence level
  - May trigger Consumption Forecast Sensor update
- **Note**: Prediction quality depends on available historical data points

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

**Update Behavior**:
- **Trigger**: Manual press only
- **Operation**: Asynchronous API test (runs in background)
  - Sends test message to configured Telegram chat
  - Typically completes in 1-3 seconds
- **External Sources**: 
  - Telegram Bot API (sendMessage endpoint)
  - Uses configured token and chat ID
- **When to Use**:
  - Initial Telegram setup verification
  - After changing Telegram configuration
  - Troubleshooting Telegram connectivity
  - Periodic connection health check
- **Effects**: 
  - Sends test message to Telegram chat
  - Updates Telegram Bot Status Sensor
  - Logs connection status
- **Requirements**:
  - Valid Telegram bot token
  - Valid chat ID
  - Network connectivity to Telegram servers

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

**Update Behavior**:
- **Trigger**: Manual press only
- **Operation**: Synchronous data export (immediate)
  - Exports data to CSV file
  - Typically completes in < 2 seconds
- **External Sources**: 
  - Refueling log from storage
  - Trip log from storage
  - Consumption statistics from storage
  - No external API calls
- **Export Contents**:
  - Refueling events (timestamp, liters, price, station, odometer)
  - Trip data (start/end, distance, duration, category)
  - Consumption statistics (periods, L/100km, costs)
  - Configuration summary
- **Export Location**: 
  - Default: `/config/www/fwcam_export_{vehicle_name}_{timestamp}.csv`
  - Accessible via Home Assistant frontend
- **When to Use**:
  - Backup before major changes
  - Data analysis in external tools (Excel, etc.)
  - Sharing data with tax software (for business trips)
  - Migration to another system
- **Effects**: Creates CSV file; no changes to integration data

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

### Update Intervals Summary

The integration uses different update strategies for different types of data:

#### Coordinator-Based Updates (Regular Intervals)
- **Fuel Price & Vehicle Data**: Synchronized updates via main coordinator
  - Default: 15 minutes
  - Range: 1-60 minutes
  - Configurable via: `number.[vehicle_name]_api_update_interval`
  - Jitter: ±2% randomization to prevent simultaneous API calls
  - Affects: Fuel Price, Tank Level, Range, Nearest Station, Nearby Cheap Stations, API Debug, Car Data Debug sensors

#### Consumption Prediction Updates (Separate Interval)
- **Consumption Calculations**: Independent prediction interval
  - Default: 6 hours
  - Range: 0.5-24 hours
  - Configurable via: `number.[vehicle_name]_consumption_prediction_interval`
  - Affects: Consumption Prediction, Consumption Forecast sensors

#### Real-Time Updates (Event-Driven)
- **Consumption History**: Recalculated at each coordinator update (15 min default)
- **Refueling Log**: Event-driven (updates when events added/modified)
- **Trip Sensors**: Event-driven (updates on odometer changes when trip tracking enabled)
- **Proximity Alerts**: Position-based (updates when vehicle location changes)
- **Telegram Status**: Periodic health check every 5 minutes + event-driven

#### Manual Updates Available
All entities can be manually updated via button entities or coordinator refresh. See individual entity documentation above for specific manual trigger buttons.

#### Initial Updates
- **First Update**: All sensors perform initial update after Home Assistant startup (when `homeassistant_started` event fires)
- **Historical Data Import**: Automatic on first setup (can be manually triggered)
  - Imports up to 90 days of vehicle data from HA Recorder
  - Detects historical refueling events
  - Enables immediate consumption predictions

#### Configuration Options
- **API Update Interval**: `number.[vehicle_name]_api_update_interval` (1-60 minutes, default: 15)
- **Consumption Prediction Interval**: `number.[vehicle_name]_consumption_prediction_interval` (0.5-24 hours, default: 6)
- **Minimum Data Points**: `number.[vehicle_name]_consumption_min_data_points` (2-50 points, default: 5)

For detailed update frequency documentation, see: [Data Update Frequencies](./user_docs/DATA_UPDATE_FREQUENCIES_DE.md)

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
