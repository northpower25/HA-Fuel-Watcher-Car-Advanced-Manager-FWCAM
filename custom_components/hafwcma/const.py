"""Constants for the haFWCMA integration."""
from typing import Final

# Integration domain
DOMAIN: Final = "hafwcma"

# Configuration keys
CONF_API_KEY: Final = "api_key"
CONF_LATITUDE: Final = "latitude"
CONF_LONGITUDE: Final = "longitude"
CONF_RADIUS: Final = "radius"
CONF_FUEL_TYPE: Final = "fuel_type"
CONF_TANK_CAPACITY: Final = "tank_capacity"
CONF_VEHICLE_NAME: Final = "vehicle_name"
CONF_TELEGRAM_TOKEN: Final = "telegram_token"
CONF_TELEGRAM_CHAT_ID: Final = "telegram_chat_id"

# Vehicle entity configuration keys
CONF_ODOMETER_ENTITY: Final = "odometer_entity"
CONF_TANK_LEVEL_ENTITY: Final = "tank_level_entity"
CONF_RANGE_ENTITY: Final = "range_entity"
CONF_POSITION_ENTITY: Final = "position_entity"

# Defaults
DEFAULT_RADIUS: Final = 5.0  # km
DEFAULT_TANK_CAPACITY: Final = 50.0  # liters
DEFAULT_SCAN_INTERVAL: Final = 300  # seconds (5 minutes)

# Fuel types
FUEL_TYPE_E5: Final = "e5"
FUEL_TYPE_E10: Final = "e10"
FUEL_TYPE_DIESEL: Final = "diesel"

FUEL_TYPES: Final = [
    FUEL_TYPE_E5,
    FUEL_TYPE_E10,
    FUEL_TYPE_DIESEL,
]

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

# Events
EVENT_FUEL_PRICE_ALERT: Final = f"{DOMAIN}_fuel_price_alert"
EVENT_TANK_LOW: Final = f"{DOMAIN}_tank_low"
EVENT_REFUEL_RECOMMENDATION: Final = f"{DOMAIN}_refuel_recommendation"
