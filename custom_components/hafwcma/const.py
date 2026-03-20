"""Constants for the haFWCMA integration."""
from typing import Final

# Integration domain
DOMAIN: Final = "hafwcma"

# Configuration keys
CONF_API_KEY: Final = "api_key"
CONF_LATITUDE: Final = "latitude"
CONF_LONGITUDE: Final = "longitude"
CONF_FUEL_TYPE: Final = "fuel_type"
CONF_TANK_CAPACITY: Final = "tank_capacity"
CONF_INITIAL_CONSUMPTION: Final = "initial_consumption"  # WLTP / user-known average L/100km
CONF_VEHICLE_NAME: Final = "vehicle_name"
CONF_TELEGRAM_TOKEN: Final = "telegram_token"
CONF_TELEGRAM_CHAT_ID: Final = "telegram_chat_id"
CONF_TELEGRAM_METHOD: Final = "telegram_method"  # "integration" or "direct_api"
CONF_PROVIDER: Final = "provider"
CONF_UPDATE_INTERVAL: Final = "update_interval"

# Vehicle entity configuration keys
CONF_ODOMETER_ENTITY: Final = "odometer_entity"
CONF_TANK_LEVEL_ENTITY: Final = "tank_level_entity"
CONF_RANGE_ENTITY: Final = "range_entity"
CONF_POSITION_ENTITY: Final = "position_entity"

# Prediction engine configuration keys
CONF_PRICE_DROP_PERCENT_THRESHOLD: Final = "price_drop_percent_threshold"
CONF_PRICE_DROP_ABSOLUTE_THRESHOLD: Final = "price_drop_absolute_threshold"
CONF_LOW_FUEL_THRESHOLD: Final = "low_fuel_threshold"
CONF_CRITICAL_FUEL_THRESHOLD: Final = "critical_fuel_threshold"
CONF_FALLBACK_DAILY_KM: Final = "fallback_daily_km"
CONF_FALLBACK_DAILY_KM_MONDAY: Final = "fallback_daily_km_monday"
CONF_FALLBACK_DAILY_KM_TUESDAY: Final = "fallback_daily_km_tuesday"
CONF_FALLBACK_DAILY_KM_WEDNESDAY: Final = "fallback_daily_km_wednesday"
CONF_FALLBACK_DAILY_KM_THURSDAY: Final = "fallback_daily_km_thursday"
CONF_FALLBACK_DAILY_KM_FRIDAY: Final = "fallback_daily_km_friday"
CONF_FALLBACK_DAILY_KM_SATURDAY: Final = "fallback_daily_km_saturday"
CONF_FALLBACK_DAILY_KM_SUNDAY: Final = "fallback_daily_km_sunday"

# Consumption prediction configuration keys
CONF_CONSUMPTION_MIN_DATA_POINTS: Final = "consumption_min_data_points"
CONF_CONSUMPTION_PREDICTION_INTERVAL: Final = "consumption_prediction_interval"

# Defaults
DEFAULT_TANK_CAPACITY: Final = 50.0  # liters
DEFAULT_SCAN_INTERVAL: Final = 300  # seconds (5 minutes)
DEFAULT_UPDATE_INTERVAL: Final = 5  # minutes
MIN_UPDATE_INTERVAL: Final = 1  # minutes
MAX_UPDATE_INTERVAL: Final = 60  # minutes

# Update interval randomization
DEFAULT_UPDATE_INTERVAL_JITTER_PERCENT: Final = 2  # ±2% randomization to avoid simultaneous API calls
MIN_UPDATE_INTERVAL_JITTER_PERCENT: Final = 0  # 0% = no randomization
MAX_UPDATE_INTERVAL_JITTER_PERCENT: Final = 10  # Maximum 10% jitter

# Prediction engine defaults
DEFAULT_PRICE_DROP_PERCENT: Final = 2.0  # 2% price drop
DEFAULT_PRICE_DROP_ABSOLUTE: Final = 0.05  # 5 cents drop (EUR)
DEFAULT_LOW_FUEL_THRESHOLD: Final = 150.0  # 150 km remaining range
DEFAULT_CRITICAL_FUEL_THRESHOLD: Final = 50.0  # 50 km remaining range
DEFAULT_FALLBACK_DAILY_KM: Final = 40.0  # 40 km per day (used if weekday-specific not set)

# Consumption prediction defaults
DEFAULT_CONSUMPTION_MIN_DATA_POINTS: Final = 5  # Minimum historical data points for reliable prediction
MIN_CONSUMPTION_MIN_DATA_POINTS: Final = 2  # Absolute minimum
MAX_CONSUMPTION_MIN_DATA_POINTS: Final = 50  # Maximum configurable
DEFAULT_CONSUMPTION_PREDICTION_INTERVAL: Final = 6.0  # Hours between prediction calculations
MIN_CONSUMPTION_PREDICTION_INTERVAL: Final = 0.5  # Minimum 30 minutes
MAX_CONSUMPTION_PREDICTION_INTERVAL: Final = 24.0  # Maximum 24 hours

# Startup delay configuration (DEPRECATED - no longer used)
# These constants are kept for backward compatibility but are no longer used
# The integration now uses event-based startup (homeassistant_started) instead of delays
STARTUP_DELAY_VEHICLE_DATA_SECONDS: Final = 120  # DEPRECATED: Use event-based waiting
STARTUP_DELAY_CONSUMPTION_PREDICTION_SECONDS: Final = 120  # DEPRECATED: Use event-based waiting

# Entity availability wait configuration (DEPRECATED - no longer used)
# The integration now checks availability without blocking retries
ENTITY_WAIT_MAX_RETRIES: Final = 6  # DEPRECATED: Non-blocking check used instead
ENTITY_WAIT_RETRY_DELAY_SECONDS: Final = 30  # DEPRECATED: Non-blocking check used instead

# Fuel types
FUEL_TYPE_E5: Final = "e5"
FUEL_TYPE_E10: Final = "e10"
FUEL_TYPE_DIESEL: Final = "diesel"

FUEL_TYPES: Final = [
    FUEL_TYPE_E5,
    FUEL_TYPE_E10,
    FUEL_TYPE_DIESEL,
]

# Telegram method types
TELEGRAM_METHOD_INTEGRATION: Final = "integration"  # Use Home Assistant's telegram_bot integration
TELEGRAM_METHOD_DIRECT_API: Final = "direct_api"  # Use direct Telegram Bot API

TELEGRAM_METHODS: Final = [
    TELEGRAM_METHOD_INTEGRATION,
    TELEGRAM_METHOD_DIRECT_API,
]

# Provider types
PROVIDER_TANKERKONIG: Final = "tankerkonig"
# Future providers can be added here
# PROVIDER_GASBUDDY: Final = "gasbuddy"
# PROVIDER_AUTOTRAVELER: Final = "autotraveler"

PROVIDERS: Final = [
    PROVIDER_TANKERKONIG,
    # Add more providers as they become available
]

PROVIDER_NAMES: Final = {
    PROVIDER_TANKERKONIG: "Tankerkönig (Germany)",
    # Add more provider display names here
}

# API endpoints
TANKERKONIG_API_URL: Final = "https://creativecommons.tankerkoenig.de/json"

# Attributes
ATTR_STATION_NAME: Final = "station_name"
ATTR_STATION_ADDRESS: Final = "station_address"
ATTR_DISTANCE: Final = "distance"
ATTR_PRICE: Final = "price"
ATTR_FORECAST_TREND: Final = "forecast_trend"
ATTR_TANK_LEVEL: Final = "tank_level"
ATTR_RANGE_KM: Final = "range_km"
ATTR_LAST_UPDATED: Final = "last_updated"
ATTR_PRICE_DELTA: Final = "price_delta"
ATTR_PRICE_DELTA_PERCENT: Final = "price_delta_percent"
ATTR_SHOULD_REFUEL: Final = "should_refuel"
ATTR_URGENCY: Final = "urgency"
ATTR_RECOMMENDATION: Final = "recommendation"
ATTR_DAYS_LEFT: Final = "days_left"
ATTR_AVG_DAILY_KM: Final = "avg_daily_km"
ATTR_DATA_SOURCE: Final = "data_source"
ATTR_LAST_PREDICTION: Final = "last_prediction"
ATTR_PREDICTED_REFUEL_DATE: Final = "predicted_refuel_date"
ATTR_CONFIDENCE: Final = "confidence"
ATTR_AVG_CONSUMPTION_RATE: Final = "avg_consumption_rate"
ATTR_DATA_POINTS_USED: Final = "data_points_used"

# Initial setup configuration keys (stored in config entry data)
CONF_TRIP_TRACKING_INITIAL_ENABLED: Final = "trip_tracking_initial_enabled"
CONF_IMPORT_HISTORICAL_DATA: Final = "import_historical_data"

# Geolocation configuration keys
CONF_PROXIMITY_ALERT_DISTANCE: Final = "proximity_alert_distance"
CONF_CHEAP_STATIONS_COUNT: Final = "cheap_stations_count"
CONF_CHEAP_STATIONS_RADIUS: Final = "cheap_stations_radius"
CONF_CHEAP_NEAR_STATIONS_RADIUS: Final = "cheap_near_stations_radius"
CONF_PROXIMITY_ALERTS_ENABLED: Final = "proximity_alerts_enabled"
CONF_MIN_TANK_LEVEL_FOR_ALERTS: Final = "min_tank_level_for_alerts"

# Geolocation defaults
DEFAULT_PROXIMITY_ALERT_DISTANCE: Final = 1.5  # km
MIN_PROXIMITY_ALERT_DISTANCE: Final = 0.1  # km
MAX_PROXIMITY_ALERT_DISTANCE: Final = 10.0  # km
DEFAULT_CHEAP_STATIONS_COUNT: Final = 10
MIN_CHEAP_STATIONS_COUNT: Final = 1
MAX_CHEAP_STATIONS_COUNT: Final = 20
DEFAULT_CHEAP_STATIONS_RADIUS: Final = 15.0  # km
MIN_CHEAP_STATIONS_RADIUS: Final = 1.0  # km
MAX_CHEAP_STATIONS_RADIUS: Final = 50.0  # km
DEFAULT_CHEAP_NEAR_STATIONS_RADIUS: Final = 10.0  # km - for near vs far comparison
MIN_CHEAP_NEAR_STATIONS_RADIUS: Final = 1.0  # km
MAX_CHEAP_NEAR_STATIONS_RADIUS: Final = 30.0  # km
DEFAULT_MIN_TANK_LEVEL_FOR_ALERTS: Final = 30.0  # percentage
DEFAULT_PROXIMITY_ALERTS_ENABLED: Final = False  # opt-in

# Geolocation update intervals
GEOLOCATION_API_UPDATE_INTERVAL: Final = 600  # 10 minutes in seconds
GEOLOCATION_PROXIMITY_CHECK_INTERVAL: Final = 30  # 30 seconds
GEOLOCATION_PROXIMITY_CHECK_STATIONARY: Final = 300  # 5 minutes when stationary
GEOLOCATION_ALERT_COOLDOWN: Final = 1800  # 30 minutes in seconds
GEOLOCATION_HYSTERESIS_FACTOR: Final = 1.3  # 30% more distance to reset

# Additional attributes for geolocation
ATTR_STATIONS: Final = "stations"
ATTR_SEARCH_RADIUS_KM: Final = "search_radius_km"
ATTR_VEHICLE_LATITUDE: Final = "vehicle_latitude"
ATTR_VEHICLE_LONGITUDE: Final = "vehicle_longitude"
ATTR_MAX_STATIONS: Final = "max_stations"
ATTR_PROXIMITY_THRESHOLD_KM: Final = "proximity_threshold_km"
ATTR_NAVIGATION_URLS: Final = "navigation_urls"
ATTR_ALERT_MESSAGE: Final = "alert_message"
ATTR_IS_OPEN: Final = "is_open"
ATTR_BRAND: Final = "brand"
ATTR_FUEL_TYPE: Final = "fuel_type"

# Entity metadata attributes (for inline documentation)
ATTR_ENTITY_DATA_SOURCE: Final = "data_source_info"
ATTR_ENTITY_DEPENDENCIES: Final = "dependencies_info"
ATTR_ENTITY_PURPOSE: Final = "purpose_info"
ATTR_ENTITY_DOCUMENTATION_URL: Final = "documentation_url"

# Events
EVENT_FUEL_PRICE_ALERT: Final = f"{DOMAIN}_fuel_price_alert"
EVENT_TANK_LOW: Final = f"{DOMAIN}_tank_low"
EVENT_REFUEL_RECOMMENDATION: Final = f"{DOMAIN}_refuel_recommendation"
EVENT_NEAR_CHEAP_STATION: Final = f"{DOMAIN}_near_cheap_station"

# Route Corridor Station Search configuration keys
CONF_ROUTE_CORRIDOR_WIDTH_KM: Final      = "route_corridor_width_km"
CONF_ROUTE_FUEL_SAFETY_BUFFER_PCT: Final = "route_fuel_safety_buffer_pct"
CONF_ROUTE_PRICE_ALERT_DELTA: Final      = "route_price_alert_delta"
CONF_ROUTE_NOTIFY_INTERVAL_MIN: Final    = "route_notify_interval_min"
CONF_ROUTE_SEARCH_WINDOW_KM: Final       = "route_search_window_km"
CONF_ROUTE_TOP_N_STATIONS: Final         = "route_top_n_stations"
CONF_ROUTE_ROUTING_PROVIDER: Final       = "route_routing_provider"
CONF_ROUTE_AVOID_TOLLS: Final            = "route_avoid_tolls"
CONF_GOOGLE_MAPS_API_KEY: Final          = "google_maps_api_key"

# Route corridor defaults
DEFAULT_ROUTE_CORRIDOR_WIDTH_KM: Final      = 5
DEFAULT_ROUTE_FUEL_SAFETY_BUFFER_PCT: Final = 15
DEFAULT_ROUTE_PRICE_ALERT_DELTA: Final      = 0.03
DEFAULT_ROUTE_NOTIFY_INTERVAL_MIN: Final    = 5
DEFAULT_ROUTE_SEARCH_WINDOW_KM: Final       = 20
DEFAULT_ROUTE_TOP_N_STATIONS: Final         = 3

# Route routing provider options
ROUTE_PROVIDER_GOOGLE: Final        = "google"
ROUTE_PROVIDER_APPLE: Final         = "apple"
ROUTE_PROVIDER_WAZE: Final          = "waze"
ROUTE_PROVIDER_VEHICLE: Final       = "vehicle"
ROUTE_PROVIDER_OSRM: Final          = "osrm"
ROUTE_PROVIDER_ORS: Final           = "openrouteservice"
DEFAULT_ROUTE_PROVIDER: Final        = ROUTE_PROVIDER_OSRM

# Route corridor sensor attributes
ATTR_ROUTE_DESTINATION: Final        = "destination"
ATTR_ROUTE_WAYPOINTS: Final          = "waypoints"
ATTR_ROUTE_TOTAL_DISTANCE_KM: Final  = "total_distance_km"
ATTR_ROUTE_POLYLINE: Final           = "route_polyline"
ATTR_ROUTE_CORRIDOR_WIDTH_KM: Final  = "corridor_width_km"
ATTR_PREDICTED_STOP_LAT: Final       = "predicted_position_lat"
ATTR_PREDICTED_STOP_LON: Final       = "predicted_position_lon"
ATTR_PREDICTED_STOP_ADDR: Final      = "predicted_position_address"
ATTR_KM_REMAINING_TO_STOP: Final     = "km_remaining_to_stop"
ATTR_TIME_REMAINING_TO_STOP: Final   = "time_remaining_to_stop"
ATTR_SAFETY_BUFFER_PCT: Final        = "safety_buffer_pct"
ATTR_EFFECTIVE_TOTAL_COST: Final     = "effective_total_cost_eur"
ATTR_DETOUR_KM: Final                = "detour_km"
ATTR_PRICE_PER_LITRE: Final          = "price_per_litre"
ATTR_EFFECTIVE_PRICE: Final          = "effective_price_eur_per_l"
ATTR_SEARCH_WINDOW_KM: Final         = "search_window_km"

# Route-specific events
EVENT_ROUTE_STARTED: Final         = f"{DOMAIN}_route_started"
EVENT_ROUTE_CANCELLED: Final       = f"{DOMAIN}_route_cancelled"
EVENT_CHEAPER_STATION_FOUND: Final = f"{DOMAIN}_cheaper_station_found"
EVENT_RANGE_WARNING: Final         = f"{DOMAIN}_range_warning"
