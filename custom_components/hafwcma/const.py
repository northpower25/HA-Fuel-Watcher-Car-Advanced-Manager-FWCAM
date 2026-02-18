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
DEFAULT_CHEAP_STATIONS_COUNT: Final = 5
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
