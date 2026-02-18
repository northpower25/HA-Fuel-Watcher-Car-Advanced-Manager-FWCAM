"""Entity metadata helper for standardized entity documentation."""
from __future__ import annotations

from typing import Final

# Base URL for entity documentation (GitHub repository)
ENTITY_DOCS_BASE_URL: Final = "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md"


def get_entity_metadata(entity_type: str) -> dict[str, str]:
    """
    Get standardized metadata attributes for an entity.
    
    This provides inline documentation for each entity, including:
    - Data source information
    - Dependencies
    - Purpose
    - Documentation link
    
    Args:
        entity_type: The type of entity (e.g., "fuel_price_sensor", "tank_level_sensor")
        
    Returns:
        Dictionary with metadata attributes
    """
    metadata = ENTITY_METADATA.get(entity_type, {})
    
    # Add documentation URL anchor
    if "documentation_url" in metadata:
        metadata["documentation_url"] = f"{ENTITY_DOCS_BASE_URL}#{metadata['documentation_url']}"
    
    return metadata


# Entity metadata definitions
# Each entity includes:
# - data_source_info: Where the data comes from
# - dependencies_info: What other entities/systems this depends on
# - purpose_info: What this entity is for
# - documentation_url: Anchor to detailed documentation
ENTITY_METADATA: Final = {
    "fuel_price_sensor": {
        "data_source_info": "Fuel price provider API (e.g., Tankerkönig), vehicle/HA location",
        "dependencies_info": "API key, geolocation data; used by refueling recommendations, price trends",
        "purpose_info": "Current fuel price (€/L) at nearest/cheapest station",
        "documentation_url": "fuel-price-sensor",
    },
    "tank_level_sensor": {
        "data_source_info": "Vehicle integration tank level entity, fallback estimation from range",
        "dependencies_info": "Vehicle entity; used by refueling recommendations, consumption prediction, proximity alerts",
        "purpose_info": "Current fuel tank level as percentage (0-100%)",
        "documentation_url": "tank-level-sensor",
    },
    "range_sensor": {
        "data_source_info": "Vehicle integration range entity, fallback estimation from tank level",
        "dependencies_info": "Vehicle entity; used by refueling recommendations, trip planning, consumption prediction",
        "purpose_info": "Estimated remaining range in kilometers",
        "documentation_url": "range-sensor",
    },
    "nearest_station_sensor": {
        "data_source_info": "Fuel price provider API station data, vehicle location",
        "dependencies_info": "Fuel Price Sensor; used by navigation helpers, station recommendations",
        "purpose_info": "Name of nearest/cheapest fuel station",
        "documentation_url": "nearest-station-sensor",
    },
    "fuel_price_api_debug_sensor": {
        "data_source_info": "API request/response logging from fuel price provider calls",
        "dependencies_info": "Fuel Price Sensor; for developers and troubleshooting",
        "purpose_info": "Debugging information for API requests and responses",
        "documentation_url": "fuel-price-api-debug-sensor",
    },
    "car_data_debug_sensor": {
        "data_source_info": "Vehicle entity states, attributes, and availability status",
        "dependencies_info": "All configured vehicle entities; for developers and troubleshooting",
        "purpose_info": "Debugging information for vehicle data retrieval",
        "documentation_url": "car-data-debug-sensor",
    },
    "consumption_prediction_sensor": {
        "data_source_info": "Historical refueling data, current vehicle data, trip data, weekday patterns",
        "dependencies_info": "Refueling Log, Tank/Range sensors, Trip Log (optional); used by refueling recommendations",
        "purpose_info": "Predicted days until refueling needed based on consumption patterns",
        "documentation_url": "consumption-prediction-sensor",
    },
    "consumption_history_sensor": {
        "data_source_info": "Historical refueling data, odometer readings over time",
        "dependencies_info": "Refueling Log; used by charts, consumption trends, forecasting",
        "purpose_info": "Historical consumption statistics over various time periods",
        "documentation_url": "consumption-history-sensor",
    },
    "consumption_forecast_sensor": {
        "data_source_info": "Historical consumption data, current fuel prices, predicted patterns",
        "dependencies_info": "Consumption History, Fuel Price, Consumption Prediction sensors",
        "purpose_info": "Forecasted future fuel costs and consumption",
        "documentation_url": "consumption-forecast-sensor",
    },
    "refueling_log_sensor": {
        "data_source_info": "Storage system, Telegram bot submissions, manual service entries",
        "dependencies_info": "Storage, Telegram Bot (optional); used by consumption calculations, statistics, trip correlation",
        "purpose_info": "Complete history of refueling events",
        "documentation_url": "refueling-log-sensor",
    },
    "nearby_cheap_stations_sensor": {
        "data_source_info": "Fuel price provider API, vehicle real-time GPS location",
        "dependencies_info": "Position entity (GPS), Fuel Price Sensor; used by proximity alerts, navigation",
        "purpose_info": "List of nearby cheap stations sorted by price for geolocation features",
        "documentation_url": "nearby-cheap-stations-sensor",
    },
    "trip_log_sensor": {
        "data_source_info": "Trip tracking system, odometer readings, trip timestamps",
        "dependencies_info": "Trip Tracking Switch (enabled), Odometer entity; used by consumption calculation, trip statistics",
        "purpose_info": "History of all tracked trips",
        "documentation_url": "trip-log-sensor",
    },
    "current_trip_sensor": {
        "data_source_info": "Real-time trip tracking, current odometer, trip start timestamp",
        "dependencies_info": "Trip Tracking Switch (enabled), On Trip Sensor, Odometer entity",
        "purpose_info": "Information about currently active trip (if any)",
        "documentation_url": "current-trip-sensor",
    },
    "proximity_alert_binary_sensor": {
        "data_source_info": "Vehicle GPS location, nearby stations data, proximity threshold",
        "dependencies_info": "Proximity Alerts Switch (enabled), Position entity, Nearby Cheap Stations, Tank Level sensors",
        "purpose_info": "Alerts when vehicle is near a cheap fuel station",
        "documentation_url": "proximity-alert-sensor",
    },
    "on_trip_binary_sensor": {
        "data_source_info": "Trip tracking system, odometer changes, trip events",
        "dependencies_info": "Trip Tracking Switch (enabled), Odometer entity; used by Trip Log, Current Trip sensors",
        "purpose_info": "Indicates whether vehicle is currently on a trip",
        "documentation_url": "on-trip-sensor",
    },
    "telegram_bot_status_binary_sensor": {
        "data_source_info": "Telegram bot connection test, integration availability, handler status",
        "dependencies_info": "Telegram configuration (token, chat ID), HA telegram_bot integration (if using)",
        "purpose_info": "Connection status and health of Telegram bot integration",
        "documentation_url": "telegram-bot-status-sensor",
    },
    "proximity_alerts_switch": {
        "data_source_info": "Configuration entry options (persisted)",
        "dependencies_info": "Position entity, Nearby Cheap Stations sensor; used by Proximity Alert sensor",
        "purpose_info": "Enables/disables proximity alerts for nearby cheap stations",
        "documentation_url": "proximity-alerts-switch",
    },
    "trip_tracking_switch": {
        "data_source_info": "Configuration entry options (persisted), trip tracking state",
        "dependencies_info": "Odometer entity; used by Trip Log, On Trip, Current Trip sensors",
        "purpose_info": "Enables/disables automatic trip tracking",
        "documentation_url": "trip-tracking-switch",
    },
    "test_provider_connection_button": {
        "data_source_info": "API test request to fuel price provider",
        "dependencies_info": "Configured API provider and API key",
        "purpose_info": "Tests connection to fuel price provider API",
        "documentation_url": "test-provider-connection-button",
    },
    "import_historical_data_button": {
        "data_source_info": "Provider API historical data endpoint, storage system",
        "dependencies_info": "Fuel price provider with historical support, storage system",
        "purpose_info": "Imports historical fuel price data (past 30 days)",
        "documentation_url": "import-historical-data-button",
    },
    "import_historical_trip_data_button": {
        "data_source_info": "Historical odometer observations, trip detection algorithm",
        "dependencies_info": "Odometer entity with history, storage system",
        "purpose_info": "Recalculates trip history from odometer observations",
        "documentation_url": "import-historical-trip-data-button",
    },
    "recalculate_trip_statistics_button": {
        "data_source_info": "Trip log data, refueling event data",
        "dependencies_info": "Trip Log Sensor",
        "purpose_info": "Recalculates aggregate trip statistics",
        "documentation_url": "recalculate-trip-statistics-button",
    },
    "validate_refueling_events_button": {
        "data_source_info": "Refueling log data, validation rules",
        "dependencies_info": "Refueling Log Sensor, storage system",
        "purpose_info": "Validates refueling events and auto-detects test/invalid entries",
        "documentation_url": "validate-refueling-events-button",
    },
    "refresh_vehicle_data_button": {
        "data_source_info": "Vehicle integration entities, vehicle data tracker",
        "dependencies_info": "All configured vehicle entities",
        "purpose_info": "Manually triggers refresh of all vehicle entity data",
        "documentation_url": "refresh-vehicle-data-button",
    },
    "fuel_price_refresh_button": {
        "data_source_info": "Fuel price provider API",
        "dependencies_info": "Fuel Price Sensor",
        "purpose_info": "Manually triggers refresh of fuel price data",
        "documentation_url": "fuel-price-refresh-button",
    },
    "consumption_prediction_button": {
        "data_source_info": "Historical refueling data, current vehicle data",
        "dependencies_info": "Consumption Prediction Sensor, Refueling Log Sensor",
        "purpose_info": "Manually triggers recalculation of consumption prediction",
        "documentation_url": "consumption-prediction-button",
    },
    "telegram_test_button": {
        "data_source_info": "Telegram configuration",
        "dependencies_info": "Telegram Bot configuration, Telegram Bot Status Sensor",
        "purpose_info": "Sends test message to verify Telegram bot connectivity",
        "documentation_url": "telegram-test-button",
    },
    "export_vehicle_data_button": {
        "data_source_info": "Refueling log, trip log, consumption statistics, storage",
        "dependencies_info": "Storage system, all data sensors",
        "purpose_info": "Exports all vehicle data to CSV file",
        "documentation_url": "export-vehicle-data-button",
    },
}
