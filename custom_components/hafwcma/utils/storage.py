"""
Storage Layer for haFWCMA
-------------------------
Implements persistent storage per config entry for:
- Price history
- Odometer history  
- Weekday consumption statistics
- Tank history (refueling events)
- Last decision (refuel recommendations)
- API data cache

Each ConfigEntry gets its own storage file:
- .storage/hafwcma_<entry_id>.json

Based on the fuel_watcher storage architecture.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.storage import Store

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY_TEMPLATE = f"{DOMAIN}_{{entry_id}}"

# Odometer observation thresholds
ODOMETER_CHANGE_THRESHOLD_KM = 0.1  # Minimum change to record new observation

# Tank level observation thresholds
TANK_LEVEL_CHANGE_THRESHOLD_L = 0.5  # Minimum change in liters to record new observation

# Consumption calculation validation thresholds
DUPLICATE_EVENT_THRESHOLD_SECONDS = 60  # Time gap to warn about possible duplicates
MAX_REASONABLE_DISTANCE_KM = 2000  # Max km between refuelings before warning

# Refueling event validation thresholds
CLOCK_SKEW_TOLERANCE_HOURS = 1  # Allow events up to 1 hour in future for clock skew
MAX_REALISTIC_FUEL_AMOUNT_L = 200  # Maximum realistic fuel amount in liters
MAX_REALISTIC_SPEED_KMH = 200  # Maximum realistic average speed between events
MAX_DISTANCE_PER_DAY_KM = 5000  # Maximum realistic distance in a single day
VEHICLE_ODOMETER_TOLERANCE_KM = 1000  # Tolerance for odometer vs current vehicle value


def _get_store(hass: HomeAssistant, entry: ConfigEntry) -> Store:
    """Return a Store instance for this config entry.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Store instance for this entry
    """
    key = STORAGE_KEY_TEMPLATE.format(entry_id=entry.entry_id)
    return Store(hass, STORAGE_VERSION, key)


async def load_data(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Load storage data for this entry.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Dictionary with stored data
    """
    store = _get_store(hass, entry)
    data = await store.async_load()
    if not data:
        data = {
            "version": STORAGE_VERSION,
            "price_history": [],  # List of {ts: str, price: float}
            "odometer_history": [],  # List of {ts: str, value: float}
            "tank_level_history": [],  # List of {ts: str, value: float, odometer_km: float}
            "weekday_consumption": {},  # {weekday: {km: float, count: int}}
            "tank_history": [],  # List of refueling events
            "last_price": None,  # float
            "last_price_timestamp": None,  # str timestamp of last price
            "last_station": None,  # dict with last station data
            "last_station_timestamp": None,  # str timestamp of last station
            "last_fuel_type": None,  # str with last used fuel type
            "last_decision": None,  # dict with decision data
            "last_api": None,  # dict with last API response
            "last_telegram": None,  # dict with last telegram message
            "last_error": None,  # str with last error
            "ml_models": {},  # ML model parameters
            "prediction_history": [],  # List of prediction results for accuracy tracking
            "next_refuel_id": 1,  # Counter for refueling event IDs
            "last_vehicle_data": None,  # dict with last successful vehicle data fetch
            "last_vehicle_data_refresh": None,  # {ts: str, type: "automatic"|"manual"}
            "last_historical_import": None,  # {ts: str, type: "automatic"|"manual"}
            # Trip Tracking
            "trips": [],  # List of Trip objects (as dicts)
            "trip_patterns": [],  # List of TripPattern objects
            "pois": [],  # List of POI objects
            "next_trip_id": 1,
            "next_pattern_id": 1,
            "next_poi_id": 1,
            "trip_tracking_config": {
                "enabled": False,
                "privacy_notice_accepted": False,
                "privacy_notice_accepted_at": None,
                "min_trip_distance_km": 0.5,
                "merge_time_window_seconds": 300,  # 5 minutes
                "retention_days": 365,
                "auto_geocode": True,
                "geocode_service": "nominatim",
                "anonymization_schedules": [],
                "tax_mileage_rate_default": 0.30,
                "tax_mileage_rate_above_20km": 0.38,
                "include_additional_costs": True,
            },
            "geocoding_cache": {},  # Cache for reverse geocoding: {key: {location_name, address, timestamp}}
            "trip_statistics": {
                "total_trips": 0,
                "total_distance_km": 0.0,
                "total_fuel_consumed": 0.0,
                "total_fuel_cost": 0.0,
                "total_additional_costs": 0.0,
                "business_trips": 0,
                "private_trips": 0,
                "commute_trips": 0,
            },
        }
    return data


async def save_data(hass: HomeAssistant, entry: ConfigEntry, data: dict[str, Any]) -> None:
    """Save storage data for this entry.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        data: Data to save
    """
    store = _get_store(hass, entry)
    await store.async_save(data)


# ---------------------------------------------------------------------------
# Price History
# ---------------------------------------------------------------------------

async def add_price_observation(
    hass: HomeAssistant,
    entry: ConfigEntry,
    price: float,
    timestamp: str,
    station_id: str | None = None,
    station_name: str | None = None,
    station_brand: str | None = None,
    station_city: str | None = None,
    station_street: str | None = None,
) -> None:
    """Add a price observation to history.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        price: Price in EUR per liter
        timestamp: ISO format timestamp
        station_id: Optional station ID
        station_name: Optional station name
        station_brand: Optional station brand
        station_city: Optional station city/place
        station_street: Optional station street
    """
    data = await load_data(hass, entry)
    observation = {
        "ts": timestamp,
        "price": price,
    }
    
    # Add station information if available
    if station_id:
        observation["station_id"] = station_id
    if station_name:
        observation["station_name"] = station_name
    if station_brand:
        observation["station_brand"] = station_brand
    if station_city:
        observation["station_city"] = station_city
    if station_street:
        observation["station_street"] = station_street
    
    data["price_history"].append(observation)
    
    # Keep only last 1000 entries
    if len(data["price_history"]) > 1000:
        data["price_history"] = data["price_history"][-1000:]
    
    await save_data(hass, entry, data)


async def get_price_history(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> list[dict[str, Any]]:
    """Get price history.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        List of price observations
    """
    data = await load_data(hass, entry)
    return data.get("price_history", [])


# ---------------------------------------------------------------------------
# Odometer History
# ---------------------------------------------------------------------------

async def add_odometer_observation(
    hass: HomeAssistant,
    entry: ConfigEntry,
    odometer_km: float,
    timestamp: str,
    latitude: float | None = None,
    longitude: float | None = None,
) -> None:
    """Add an odometer observation to history.
    
    Only adds the observation if the odometer value has changed from the last recorded value.
    This prevents duplicate entries when vehicle integrations send the same odometer reading multiple times.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        odometer_km: Odometer reading in kilometers
        timestamp: ISO format timestamp
        latitude: Optional GPS latitude at this odometer reading
        longitude: Optional GPS longitude at this odometer reading
    """
    data = await load_data(hass, entry)
    
    # Check if this is a duplicate of the last odometer value
    # Vehicle integrations often send the same odometer value multiple times
    # We only want to record actual changes to avoid inflated statistics
    if data["odometer_history"]:
        last_entry = data["odometer_history"][-1]
        last_value = last_entry.get("value")
        
        # Skip if value hasn't changed (within threshold)
        if last_value is not None and abs(float(last_value) - float(odometer_km)) < ODOMETER_CHANGE_THRESHOLD_KM:
            _LOGGER.debug(
                "Skipping odometer observation: %.1f km (changed by less than %.1f km from last value of %.1f km)",
                odometer_km, ODOMETER_CHANGE_THRESHOLD_KM, last_value
            )
            return
    
    observation: dict[str, Any] = {"ts": timestamp, "value": odometer_km}
    if latitude is not None:
        observation["lat"] = latitude
    if longitude is not None:
        observation["lon"] = longitude
    data["odometer_history"].append(observation)
    
    # Keep only last 1000 entries
    if len(data["odometer_history"]) > 1000:
        data["odometer_history"] = data["odometer_history"][-1000:]
    
    await save_data(hass, entry, data)


async def get_odometer_history(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> list[dict[str, Any]]:
    """Get odometer history.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        List of odometer observations
    """
    data = await load_data(hass, entry)
    return data.get("odometer_history", [])


async def add_tank_level_observation(
    hass: HomeAssistant,
    entry: ConfigEntry,
    tank_level_liters: float,
    odometer_km: float | None,
    timestamp: str,
) -> None:
    """Add a tank level observation to history.
    
    Only adds the observation if the tank level has changed significantly from the last recorded value.
    This prevents duplicate entries and tracks tank level changes for missed refueling detection.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        tank_level_liters: Tank level in liters
        odometer_km: Current odometer reading in kilometers (optional)
        timestamp: ISO format timestamp
    """
    data = await load_data(hass, entry)
    
    # Initialize tank_level_history if not present (for existing installations)
    if "tank_level_history" not in data:
        data["tank_level_history"] = []
    
    # Check if this is a duplicate of the last tank level value
    # Only record significant changes to avoid inflated statistics
    if data["tank_level_history"]:
        last_entry = data["tank_level_history"][-1]
        last_value = last_entry.get("value")
        
        # Skip if value hasn't changed significantly (within threshold)
        if last_value is not None and abs(float(last_value) - float(tank_level_liters)) < TANK_LEVEL_CHANGE_THRESHOLD_L:
            _LOGGER.debug(
                "Skipping tank level observation: %.1f L (changed by less than %.1f L from last value of %.1f L)",
                tank_level_liters, TANK_LEVEL_CHANGE_THRESHOLD_L, last_value
            )
            return
    
    data["tank_level_history"].append({
        "ts": timestamp,
        "value": tank_level_liters,
        "odometer_km": odometer_km,
    })
    
    # Keep only last 1000 entries
    if len(data["tank_level_history"]) > 1000:
        data["tank_level_history"] = data["tank_level_history"][-1000:]
    
    await save_data(hass, entry, data)


async def get_tank_level_history(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> list[dict[str, Any]]:
    """Get tank level history.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        List of tank level observations with timestamps
    """
    data = await load_data(hass, entry)
    return data.get("tank_level_history", [])


# ---------------------------------------------------------------------------
# Weekday Consumption
# ---------------------------------------------------------------------------

async def update_weekday_consumption(
    hass: HomeAssistant,
    entry: ConfigEntry,
    weekday: int,
    km: float,
) -> None:
    """Update weekday consumption statistics.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        weekday: Day of week (0=Monday, 6=Sunday)
        km: Kilometers driven on this day
    """
    data = await load_data(hass, entry)
    
    if "weekday_consumption" not in data:
        data["weekday_consumption"] = {}
    
    weekday_str = str(weekday)
    if weekday_str not in data["weekday_consumption"]:
        data["weekday_consumption"][weekday_str] = {"km": 0.0, "count": 0}
    
    data["weekday_consumption"][weekday_str]["km"] += km
    data["weekday_consumption"][weekday_str]["count"] += 1
    
    await save_data(hass, entry, data)


async def get_weekday_consumption(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[int, dict[str, Any]]:
    """Get weekday consumption statistics.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Dictionary mapping weekday to consumption stats
    """
    data = await load_data(hass, entry)
    weekday_data = data.get("weekday_consumption", {})
    
    # Convert string keys back to integers
    return {int(k): v for k, v in weekday_data.items()}


# ---------------------------------------------------------------------------
# Tank History (Refueling Events)
# ---------------------------------------------------------------------------

async def add_refuel_event(
    hass: HomeAssistant,
    entry: ConfigEntry,
    event_data: dict[str, Any],
) -> int:
    """Add a refueling event to tank history.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        event_data: Refueling event data (timestamp, amount, price, etc.)
        
    Returns:
        The ID of the newly created refueling event
    """
    data = await load_data(hass, entry)
    
    # Initialize refueling_log if not present
    if "refueling_log" not in data:
        data["refueling_log"] = []
    
    # Get next ID from counter (with fallback for old data)
    if "next_refuel_id" not in data:
        # Migrate old data - find highest existing ID and increment
        # Only consider events with valid (non-None) IDs
        existing_ids = [
            event.get("id") for event in data.get("refueling_log", [])
            if event.get("id") is not None
        ]
        # Use highest ID + 1, or start at 1 if no valid IDs exist
        data["next_refuel_id"] = (max(existing_ids) + 1) if existing_ids else 1
    
    next_id = data["next_refuel_id"]
    data["next_refuel_id"] = next_id + 1
    
    # Create complete refueling record with ID
    # Ensure timestamp is always stored as a string
    timestamp = event_data.get("timestamp")
    if timestamp is not None and isinstance(timestamp, datetime):
        # Convert datetime object to ISO format string
        timestamp = timestamp.isoformat()
    
    refuel_record = {
        "id": next_id,
        "timestamp": timestamp,
        "odometer_km": event_data.get("odometer_km"),
        "station_name": event_data.get("station_name"),
        "station_address": event_data.get("station_address"),
        "liters_refueled": event_data.get("liters_refueled"),
        "price_per_liter": event_data.get("price_per_liter"),
        "total_cost": event_data.get("total_cost"),
        "latitude": event_data.get("latitude"),
        "longitude": event_data.get("longitude"),
        "fuel_type": event_data.get("fuel_type"),
        "editable": True,
        # Data quality indicators for filtering and manual correction
        "data_quality": event_data.get("data_quality", "manual"),  # manual, auto_detected, historical_import
        "confidence": event_data.get("confidence", 1.0),  # 0.0-1.0, higher is better
        "excluded_from_calculation": event_data.get("excluded_from_calculation", False),  # Exclude test/invalid events
        "exclusion_reason": event_data.get("exclusion_reason"),  # Why event was excluded (optional)
        # Telegram response tracking for bidirectional communication
        "telegram_notification_sent": event_data.get("telegram_notification_sent", False),
        "telegram_notification_timestamp": event_data.get("telegram_notification_timestamp"),
        "telegram_response_received": event_data.get("telegram_response_received", False),
        "telegram_response_timestamp": event_data.get("telegram_response_timestamp"),
        "telegram_response_type": event_data.get("telegram_response_type"),  # text, photo, voice, callback
        "telegram_response_raw": event_data.get("telegram_response_raw"),  # Raw text/transcription
        "telegram_response_parsed": event_data.get("telegram_response_parsed"),  # AI-parsed structured data
        "telegram_photo_file_id": event_data.get("telegram_photo_file_id"),  # For photo responses
        "telegram_voice_file_id": event_data.get("telegram_voice_file_id"),  # For voice responses
        "telegram_message_id": event_data.get("telegram_message_id"),  # ID of the notification message for threading
    }
    
    data["refueling_log"].append(refuel_record)
    
    # Also add to legacy tank_history for backward compatibility
    data["tank_history"].append(event_data)
    
    # Track last fuel type if provided (skip simulated refuelings)
    fuel_type = event_data.get("fuel_type")
    data_quality = event_data.get("data_quality")
    if fuel_type and data_quality != "simulated":
        data["last_fuel_type"] = fuel_type
    
    # Keep only last 100 refueling events
    if len(data["tank_history"]) > 100:
        data["tank_history"] = data["tank_history"][-100:]
    if len(data["refueling_log"]) > 100:
        data["refueling_log"] = data["refueling_log"][-100:]
    
    await save_data(hass, entry, data)
    return next_id


async def get_tank_history(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> list[dict[str, Any]]:
    """Get tank history (refueling events).
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        List of refueling events
    """
    data = await load_data(hass, entry)
    return data.get("tank_history", [])


async def get_refueling_log(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> list[dict[str, Any]]:
    """Get complete refueling log with all records.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        List of refueling log records with full details
    """
    data = await load_data(hass, entry)
    return data.get("refueling_log", [])


async def get_refueling_record(
    hass: HomeAssistant,
    entry: ConfigEntry,
    refuel_id: int,
) -> dict[str, Any] | None:
    """Get a specific refueling record by ID.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        refuel_id: ID of the refueling record
        
    Returns:
        Refueling record or None if not found
    """
    log = await get_refueling_log(hass, entry)
    for record in log:
        if record.get("id") == refuel_id:
            return record
    return None


async def update_refueling_record(
    hass: HomeAssistant,
    entry: ConfigEntry,
    refuel_id: int,
    updates: dict[str, Any],
) -> bool:
    """Update a specific refueling record.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        refuel_id: ID of the refueling record to update
        updates: Dictionary with fields to update
        
    Returns:
        True if record was updated, False if not found
    """
    data = await load_data(hass, entry)
    
    if "refueling_log" not in data:
        return False
    
    for record in data["refueling_log"]:
        if record.get("id") == refuel_id:
            # Update allowed fields
            allowed_fields = [
                "timestamp", "odometer_km", "station_name", "station_address",
                "liters_refueled", "price_per_liter", "total_cost",
                "latitude", "longitude", "fuel_type", "data_quality", "confidence",
                "excluded_from_calculation", "exclusion_reason",
                # Telegram response tracking fields
                "telegram_notification_sent", "telegram_notification_timestamp",
                "telegram_response_received", "telegram_response_timestamp",
                "telegram_response_type", "telegram_response_raw", "telegram_response_parsed",
                "telegram_photo_file_id", "telegram_voice_file_id", "telegram_message_id"
            ]
            for field in allowed_fields:
                if field in updates:
                    record[field] = updates[field]
            
            # Track last fuel type if updated (skip simulated refuelings)
            if "fuel_type" in updates and updates["fuel_type"]:
                # Only track if this is not a simulated refueling
                data_quality = record.get("data_quality", updates.get("data_quality"))
                if data_quality != "simulated":
                    data["last_fuel_type"] = updates["fuel_type"]
            
            await save_data(hass, entry, data)
            return True
    
    return False


async def delete_refueling_record(
    hass: HomeAssistant,
    entry: ConfigEntry,
    refuel_id: int,
) -> bool:
    """Delete a specific refueling record.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        refuel_id: ID of the refueling record to delete
        
    Returns:
        True if record was deleted, False if not found
    """
    data = await load_data(hass, entry)
    
    if "refueling_log" not in data:
        return False
    
    original_length = len(data["refueling_log"])
    data["refueling_log"] = [
        record for record in data["refueling_log"]
        if record.get("id") != refuel_id
    ]
    
    if len(data["refueling_log"]) < original_length:
        await save_data(hass, entry, data)
        return True
    
    return False


async def get_last_fuel_type(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Get last used fuel type for this entry.
    
    Returns the fuel type from the most recent non-simulated refueling event.
    This ensures that test/simulated refuelings don't affect the fuel type suggestion.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Last fuel type from a real (non-simulated) refueling, or None
    """
    data = await load_data(hass, entry)
    refueling_log = data.get("refueling_log", [])
    
    # Filter out refuelings without timestamps and sort by timestamp (newest first)
    # ISO format timestamps sort correctly as strings (e.g., "2024-02-17T17:32:32")
    refuelings_with_timestamps = [r for r in refueling_log if r.get("timestamp") is not None]
    sorted_log = sorted(
        refuelings_with_timestamps,
        key=lambda x: x.get("timestamp", ""),
        reverse=True
    )
    
    for refuel in sorted_log:
        # Skip simulated refuelings
        if refuel.get("data_quality") == "simulated":
            continue
        # Return fuel type if it exists
        fuel_type = refuel.get("fuel_type")
        if fuel_type:
            return fuel_type
    
    # Fallback to stored last_fuel_type if no real refuelings found
    return data.get("last_fuel_type")


# ---------------------------------------------------------------------------
# Last Price
# ---------------------------------------------------------------------------

async def get_last_price(hass: HomeAssistant, entry: ConfigEntry) -> float | None:
    """Get last known price for this entry.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Last price or None
    """
    data = await load_data(hass, entry)
    return data.get("last_price")


async def set_last_price(hass: HomeAssistant, entry: ConfigEntry, price: float, timestamp: str | None = None) -> None:
    """Set last known price for this entry with timestamp.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        price: Price to store
        timestamp: Timestamp of the price (ISO format), defaults to now
    """
    from homeassistant.util import dt as dt_util
    
    if timestamp is None:
        timestamp = dt_util.now().isoformat()
    
    data = await load_data(hass, entry)
    data["last_price"] = price
    data["last_price_timestamp"] = timestamp
    await save_data(hass, entry, data)


async def get_last_price_timestamp(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Get timestamp of last known price.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Timestamp string or None
    """
    data = await load_data(hass, entry)
    return data.get("last_price_timestamp")


async def set_last_station(hass: HomeAssistant, entry: ConfigEntry, station: dict, timestamp: str | None = None) -> None:
    """Set last known station data with timestamp.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        station: Station data to store
        timestamp: Timestamp of the station data (ISO format), defaults to now
    """
    from homeassistant.util import dt as dt_util
    
    if timestamp is None:
        timestamp = dt_util.now().isoformat()
    
    data = await load_data(hass, entry)
    data["last_station"] = station
    data["last_station_timestamp"] = timestamp
    await save_data(hass, entry, data)


async def get_last_station(hass: HomeAssistant, entry: ConfigEntry) -> dict | None:
    """Get last known station data.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Last station data or None
    """
    data = await load_data(hass, entry)
    return data.get("last_station")


async def get_last_station_timestamp(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Get timestamp of last known station data.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Timestamp string or None
    """
    data = await load_data(hass, entry)
    return data.get("last_station_timestamp")


# ---------------------------------------------------------------------------
# Last Decision
# ---------------------------------------------------------------------------

async def get_last_decision(hass: HomeAssistant, entry: ConfigEntry) -> dict | None:
    """Get last refuel decision for this entry.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Last decision data or None
    """
    data = await load_data(hass, entry)
    return data.get("last_decision")


async def set_last_decision(hass: HomeAssistant, entry: ConfigEntry, decision: dict) -> None:
    """Set last refuel decision for this entry.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        decision: Decision data to store
    """
    data = await load_data(hass, entry)
    data["last_decision"] = decision
    await save_data(hass, entry, data)


# ---------------------------------------------------------------------------
# Last API Data
# ---------------------------------------------------------------------------

async def get_last_api(hass: HomeAssistant, entry: ConfigEntry) -> dict | None:
    """Get last API response for this entry.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Last API data or None
    """
    data = await load_data(hass, entry)
    return data.get("last_api")


async def set_last_api(hass: HomeAssistant, entry: ConfigEntry, api_data: dict) -> None:
    """Set last API response for this entry.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        api_data: API data to store
    """
    data = await load_data(hass, entry)
    data["last_api"] = api_data
    await save_data(hass, entry, data)


# ---------------------------------------------------------------------------
# Last Error
# ---------------------------------------------------------------------------

async def get_last_error(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Get last error message for this entry.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Last error message or None
    """
    data = await load_data(hass, entry)
    return data.get("last_error")


async def set_last_error(hass: HomeAssistant, entry: ConfigEntry, error: str) -> None:
    """Set last error message for this entry.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        error: Error message to store
    """
    data = await load_data(hass, entry)
    data["last_error"] = error
    await save_data(hass, entry, data)
    _LOGGER.error("haFWCMA [%s]: %s", entry.title, error)


# ---------------------------------------------------------------------------
# Consumption History Calculations
# ---------------------------------------------------------------------------

async def validate_refueling_event(
    hass: HomeAssistant,
    entry: ConfigEntry,
    event: dict[str, Any],
    vehicle_odometer: float | None = None,
) -> tuple[bool, str | None]:
    """Validate a refueling event for logical consistency.
    
    Checks if a refueling event is valid based on:
    - Odometer value vs other events
    - Timestamp vs other events
    - Reasonable fuel amounts
    - Data quality indicators
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        event: Refueling event to validate
        vehicle_odometer: Current vehicle odometer (optional)
        
    Returns:
        Tuple of (is_valid, reason_if_invalid)
    """
    from homeassistant.util import dt as dt_util
    
    event_id = event.get("id")
    odometer = event.get("odometer_km")
    timestamp_str = event.get("timestamp")
    liters = event.get("liters_refueled")
    station_name = event.get("station_name", "")
    
    # Parse timestamp
    try:
        if isinstance(timestamp_str, str):
            event_time = dt_util.parse_datetime(timestamp_str)
        elif isinstance(timestamp_str, datetime):
            event_time = timestamp_str
        else:
            return False, "Invalid timestamp format"
            
        if not event_time:
            return False, "Could not parse timestamp"
    except Exception as e:
        return False, f"Timestamp parsing error: {e}"
    
    # Check if event is from the future
    now = dt_util.now()
    if event_time > now:
        time_diff = (event_time - now).total_seconds() / 3600  # hours
        if time_diff > CLOCK_SKEW_TOLERANCE_HOURS:
            return False, f"Event is {time_diff:.1f} hours in the future"
    
    # Check for test indicators in station name
    test_indicators = ["test", "api test", "demo", "example", "xxxx", "1111", "9999"]
    station_lower = station_name.lower()
    for indicator in test_indicators:
        if indicator in station_lower:
            return False, f"Station name contains test indicator: '{indicator}'"
    
    # Check for unrealistic fuel amounts
    if liters is not None:
        if liters <= 0:
            return False, "Fuel amount must be positive"
        if liters > MAX_REALISTIC_FUEL_AMOUNT_L:
            return False, f"Fuel amount {liters}L exceeds realistic maximum ({MAX_REALISTIC_FUEL_AMOUNT_L}L)"
    
    # Check odometer value if available
    if odometer is not None:
        if odometer <= 0:
            return False, "Odometer must be positive"
        
        # Check against current vehicle odometer if provided
        if vehicle_odometer is not None and odometer > vehicle_odometer + VEHICLE_ODOMETER_TOLERANCE_KM:
            diff = odometer - vehicle_odometer
            return False, f"Odometer {odometer} km is {diff} km higher than current vehicle odometer"
        
        # Check against other events for logical ordering
        data = await load_data(hass, entry)
        refueling_log = data.get("refueling_log", [])
        
        for other_event in refueling_log:
            other_id = other_event.get("id")
            if other_id == event_id:
                continue  # Skip self
            
            if other_event.get("excluded_from_calculation", False):
                continue  # Skip already excluded events
            
            other_odometer = other_event.get("odometer_km")
            other_timestamp_str = other_event.get("timestamp")
            
            if other_odometer is None or other_timestamp_str is None:
                continue
            
            try:
                if isinstance(other_timestamp_str, str):
                    other_time = dt_util.parse_datetime(other_timestamp_str)
                elif isinstance(other_timestamp_str, datetime):
                    other_time = other_timestamp_str
                else:
                    continue
                    
                if not other_time:
                    continue
                    
                # Ensure timezone-aware for comparison
                if event_time.tzinfo is None:
                    event_time = dt_util.as_local(event_time)
                if other_time.tzinfo is None:
                    other_time = dt_util.as_local(other_time)
                
                # Check for odometer going backwards in time
                if event_time > other_time and odometer < other_odometer:
                    km_diff = other_odometer - odometer
                    time_diff_hours = (event_time - other_time).total_seconds() / 3600
                    return False, f"Odometer went backwards by {km_diff} km vs event #{other_id} ({time_diff_hours:.1f}h ago)"
                
                # Check for unrealistic odometer jump
                if event_time > other_time:
                    km_diff = odometer - other_odometer
                    time_diff_hours = (event_time - other_time).total_seconds() / 3600
                    if time_diff_hours > 0:
                        km_per_hour = km_diff / time_diff_hours
                        # Check for unrealistic average speed
                        if km_per_hour > MAX_REALISTIC_SPEED_KMH:
                            return False, f"Unrealistic speed: {km_per_hour:.0f} km/h average vs event #{other_id}"
                        # Check for unrealistic distance in short time
                        if time_diff_hours < 24 and km_diff > MAX_DISTANCE_PER_DAY_KM:
                            return False, f"Unrealistic distance: {km_diff} km in {time_diff_hours:.1f}h vs event #{other_id}"
                            
            except Exception:
                continue
    
    return True, None


async def auto_validate_refueling_events(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Automatically validate all refueling events and mark suspicious ones.
    
    Scans all refueling events and marks those that fail validation as excluded
    from calculation.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Dictionary with validation results:
        {
            "total_events": int,
            "validated": int,
            "newly_excluded": int,
            "already_excluded": int,
            "excluded_events": [list of excluded event IDs],
        }
    """
    data = await load_data(hass, entry)
    refueling_log = data.get("refueling_log", [])
    
    total_events = len(refueling_log)
    newly_excluded = 0
    already_excluded = 0
    excluded_event_ids = []
    
    for event in refueling_log:
        event_id = event.get("id")
        
        # Skip if already excluded
        if event.get("excluded_from_calculation", False):
            already_excluded += 1
            excluded_event_ids.append(event_id)
            continue
        
        # Validate event
        is_valid, reason = await validate_refueling_event(hass, entry, event)
        
        if not is_valid:
            # Mark event as excluded
            event["excluded_from_calculation"] = True
            event["exclusion_reason"] = f"Auto-validation: {reason}"
            newly_excluded += 1
            excluded_event_ids.append(event_id)
            _LOGGER.warning(
                "Refueling event #%s automatically excluded from calculations: %s",
                event_id, reason
            )
    
    if newly_excluded > 0:
        await save_data(hass, entry, data)
    
    validated = total_events - already_excluded
    
    _LOGGER.info(
        "Auto-validation complete: %d events validated, %d newly excluded, %d already excluded",
        validated, newly_excluded, already_excluded
    )
    
    return {
        "total_events": total_events,
        "validated": validated,
        "newly_excluded": newly_excluded,
        "already_excluded": already_excluded,
        "excluded_events": excluded_event_ids,
    }


async def calculate_consumption_history(
    hass: HomeAssistant,
    entry: ConfigEntry,
    days: int = 1,
) -> dict[str, Any]:
    """Calculate average consumption for a historical period.
    
    Calculates consumption based on refueling events and odometer changes.
    Events are filtered by timestamp, then sorted chronologically for consumption calculation.
    
    Implementation note: Filtered events are stored as (datetime, event) tuples
    to enable consistent chronological sorting regardless of original timestamp format.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        days: Number of days to look back (1, 7, 14, 30)
        
    Returns:
        Dictionary with consumption statistics
    """
    from datetime import timedelta
    from homeassistant.util import dt as dt_util
    
    data = await load_data(hass, entry)
    refueling_log = data.get("refueling_log", [])
    
    if not refueling_log:
        _LOGGER.debug("No refueling log data available for consumption calculation")
        return {
            "avg_consumption_l_per_100km": None,
            "total_liters": 0,
            "total_km": 0,
            "refuel_count": 0,
            "total_cost": 0.0,
        }
    
    # Calculate cutoff timestamp
    cutoff = dt_util.now() - timedelta(days=days)
    
    _LOGGER.debug(
        "calculate_consumption_history(%d days): cutoff=%s, now=%s",
        days, cutoff, dt_util.now()
    )
    
    # Filter events within period
    relevant_events = []
    excluded_count = 0
    for event in refueling_log:
        # Skip events explicitly excluded from calculation (e.g., test events)
        if event.get("excluded_from_calculation", False):
            excluded_count += 1
            _LOGGER.debug(
                "Event id=%s: EXCLUDED from calculation (reason: %s)",
                event.get("id"),
                event.get("exclusion_reason", "manually excluded")
            )
            continue
        
        timestamp_value = event.get("timestamp", "")
        event_time = None
        
        try:
            # Handle both string and datetime objects
            # While timestamps should always be stored as strings (see add_refuel_event),
            # we handle datetime objects here for robustness in case of:
            # - Legacy data from older versions
            # - Direct data manipulation/import
            # - Race conditions during updates
            if isinstance(timestamp_value, str):
                event_time = dt_util.parse_datetime(timestamp_value)
            elif isinstance(timestamp_value, datetime):  # It's already a datetime object
                event_time = timestamp_value
                _LOGGER.debug(
                    "Event id=%s: timestamp is already a datetime object: %s",
                    event.get("id"),
                    event_time
                )
            else:
                _LOGGER.debug(
                    "Event id=%s: timestamp has unexpected type %s: %s",
                    event.get("id"),
                    type(timestamp_value),
                    timestamp_value
                )
                continue
            
            if not event_time:
                _LOGGER.debug(
                    "Event id=%s timestamp=%s -> parse returned None",
                    event.get("id"),
                    timestamp_value
                )
                continue
        except (ValueError, TypeError) as e:
            _LOGGER.debug(
                "Event id=%s timestamp=%s -> parse failed: %s",
                event.get("id"),
                timestamp_value,
                e
            )
            continue
        
        # Ensure event_time is timezone-aware for proper comparison (outside try-except)
        try:
            if event_time.tzinfo is None:
                # If event_time is naive, make it aware using the default timezone
                event_time = dt_util.as_local(event_time)
                _LOGGER.debug(
                    "Event id=%s: converted naive datetime to timezone-aware: %s",
                    event.get("id"),
                    event_time
                )
        except (ValueError, TypeError) as e:
            _LOGGER.debug(
                "Event id=%s: timezone conversion failed: %s",
                event.get("id"),
                e
            )
            continue
        
        # Now do the comparison
        try:
            should_include = event_time >= cutoff
            _LOGGER.debug(
                "Event id=%s timestamp=%s -> parsed=%s -> included=%s (cutoff=%s)",
                event.get("id"),
                timestamp_value,
                event_time,
                should_include,
                cutoff
            )
            
            if should_include:
                # Store as tuple (datetime, event) for chronological sorting
                relevant_events.append((event_time, event))
        except TypeError as e:
            _LOGGER.error(
                "Event id=%s: Comparison failed between event_time=%s (tzinfo=%s) and cutoff=%s (tzinfo=%s): %s",
                event.get("id"),
                event_time,
                event_time.tzinfo,
                cutoff,
                cutoff.tzinfo,
                e
            )
            continue
    
    _LOGGER.debug(
        "calculate_consumption_history(%d days): found %d/%d events in period (%d excluded from calculation)",
        days, len(relevant_events), len(refueling_log), excluded_count
    )
    
    if len(relevant_events) < 2:
        # Need at least 2 refueling events for refueling-based consumption calculation.
        # Fall back to trip data for the period when available.
        trips_in_period = []
        for trip in data.get("trips", []):
            trip_end_str = trip.get("timestamp_end")
            if not trip_end_str:
                continue
            try:
                if isinstance(trip_end_str, str):
                    trip_end = dt_util.parse_datetime(trip_end_str)
                elif isinstance(trip_end_str, datetime):
                    trip_end = trip_end_str
                else:
                    continue
                if trip_end is None:
                    continue
                if trip_end.tzinfo is None:
                    trip_end = dt_util.as_local(trip_end)
                if trip_end >= cutoff:
                    trips_in_period.append(trip)
            except (ValueError, TypeError):
                continue

        if trips_in_period:
            trip_total_km = sum(t.get("distance_km") or 0.0 for t in trips_in_period)
            # Sum fuel_consumed only for trips where it was measured (not None)
            trips_with_fuel = [t for t in trips_in_period if t.get("fuel_consumed") is not None]
            trip_total_liters = sum(t.get("fuel_consumed") or 0.0 for t in trips_with_fuel)

            # For trips missing fuel data, estimate using average rate from trips that have it
            trips_without_fuel_km = sum(
                t.get("distance_km") or 0.0
                for t in trips_in_period
                if t.get("fuel_consumed") is None
            )
            if trips_without_fuel_km > 0 and trips_with_fuel:
                known_km = sum(t.get("distance_km") or 0.0 for t in trips_with_fuel)
                if known_km > 0:
                    estimated_rate = trip_total_liters / known_km  # L/km
                    trip_total_liters += estimated_rate * trips_without_fuel_km

            avg_consumption = (trip_total_liters / trip_total_km) * 100 if trip_total_km > 0 and trip_total_liters > 0 else None

            # Cost from any refueling events in the period
            total_cost = 0.0
            for _event_time, event in relevant_events:
                price_per_liter = event.get("price_per_liter")
                liters_refueled = event.get("liters_refueled")
                if price_per_liter is not None and liters_refueled is not None:
                    total_cost += price_per_liter * liters_refueled

            # If no refueling in period, estimate cost from last known price × consumed liters
            if total_cost == 0.0 and trip_total_liters > 0:
                sorted_log = sorted(
                    [e for e in refueling_log if e.get("price_per_liter") is not None],
                    key=lambda x: x.get("timestamp", ""),
                    reverse=True,
                )
                last_price = sorted_log[0].get("price_per_liter") if sorted_log else None
                if last_price is not None:
                    total_cost = trip_total_liters * last_price

            _LOGGER.debug(
                "calculate_consumption_history(%d days): used trip data "
                "(%d trips) total_km=%.1f total_liters=%.2f avg_consumption=%s",
                days, len(trips_in_period), trip_total_km, trip_total_liters, avg_consumption
            )

            return {
                "avg_consumption_l_per_100km": avg_consumption,
                "total_liters": round(trip_total_liters, 2),
                "total_km": round(trip_total_km, 2),
                "refuel_count": len(relevant_events),
                "total_cost": round(total_cost, 2) if total_cost > 0 else 0.0,
            }

        # No trip data available either - return cost from any refueling events in period
        total_cost = 0.0
        for _event_time, event in relevant_events:
            price_per_liter = event.get("price_per_liter")
            liters_refueled = event.get("liters_refueled")
            if price_per_liter is not None and liters_refueled is not None:
                total_cost += price_per_liter * liters_refueled

        return {
            "avg_consumption_l_per_100km": None,
            "total_liters": 0,
            "total_km": 0,
            "refuel_count": len(relevant_events),
            "total_cost": round(total_cost, 2) if total_cost > 0 else 0.0,
        }
    
    # Sort by normalized timestamp (first element of tuple)
    relevant_events.sort(key=lambda x: x[0])
    
    _LOGGER.debug(
        "calculate_consumption_history(%d days): sorted %d events for consumption calc",
        days, len(relevant_events)
    )
    
    # Validate event data for potential issues
    for i, (event_time, event) in enumerate(relevant_events):
        event_id = event.get("id")
        odometer = event.get("odometer_km")
        
        # Check for missing odometer
        if odometer is None:
            _LOGGER.warning(
                "Event id=%s (index %d): missing odometer_km - this event will be skipped in km calculations",
                event_id, i
            )
        # Check for suspicious negative or zero odometer
        elif odometer <= 0:
            _LOGGER.warning(
                "Event id=%s (index %d): suspicious odometer_km=%s <= 0",
                event_id, i, odometer
            )
        
        # Check for duplicate/very close timestamps (within 60 seconds)
        if i > 0:
            prev_time = relevant_events[i-1][0]
            time_diff_seconds = abs((event_time - prev_time).total_seconds())
            if time_diff_seconds < DUPLICATE_EVENT_THRESHOLD_SECONDS:
                _LOGGER.warning(
                    "Events id=%s and id=%s: very close timestamps (%.1f seconds apart) - possible duplicate refueling events",
                    relevant_events[i-1][1].get("id"), event_id, time_diff_seconds
                )
    
    # Calculate total distance and fuel consumed
    # Logic: Fuel from refueling event i is consumed between event i and event i+1
    total_km = 0
    total_liters = 0
    
    for i in range(len(relevant_events) - 1):
        curr_time, curr_event = relevant_events[i]
        next_time, next_event = relevant_events[i + 1]
        
        curr_odometer = curr_event.get("odometer_km")
        next_odometer = next_event.get("odometer_km")
        liters_refueled = curr_event.get("liters_refueled")
        
        _LOGGER.debug(
            "Pair [%d->%d]: curr_odo=%s next_odo=%s liters=%s",
            curr_event.get("id"), next_event.get("id"),
            curr_odometer, next_odometer, liters_refueled
        )
        
        # Fuel from current refueling was consumed to reach next refueling
        # Use explicit None checks to handle 0 values correctly
        if (curr_odometer is not None and next_odometer is not None 
            and liters_refueled is not None):
            km_driven = next_odometer - curr_odometer
            
            # Validate km_driven for unreasonable values
            # Warn if a single segment shows > MAX_REASONABLE_DISTANCE_KM (likely data entry error)
            if km_driven > MAX_REASONABLE_DISTANCE_KM:
                _LOGGER.warning(
                    "Pair [%d->%d]: SUSPICIOUS km_driven=%s km (odometer: %s -> %s). "
                    "This seems unreasonably high - check for incorrect odometer values in refueling events!",
                    curr_event.get("id"), next_event.get("id"),
                    km_driven, curr_odometer, next_odometer
                )
            
            # Only count if positive distance and fuel was actually consumed
            if km_driven > 0 and liters_refueled > 0:
                total_km += km_driven
                total_liters += liters_refueled
                _LOGGER.debug(
                    "Pair [%d->%d]: km_driven=%s consumed=%s L (running totals: %s km, %s L)",
                    curr_event.get("id"), next_event.get("id"),
                    km_driven, liters_refueled, total_km, total_liters
                )
            else:
                _LOGGER.debug(
                    "Pair [%d->%d]: SKIPPED (km_driven=%s <= 0 or liters=%s <= 0)",
                    curr_event.get("id"), next_event.get("id"),
                    km_driven, liters_refueled
                )
        else:
            _LOGGER.debug(
                "Pair [%d->%d]: SKIPPED (missing odometer or liters data)",
                curr_event.get("id"), next_event.get("id")
            )
    
    # Calculate average consumption
    avg_consumption = None
    if total_km > 0:
        avg_consumption = (total_liters / total_km) * 100
    
    _LOGGER.debug(
        "calculate_consumption_history(%d days): RESULT total_km=%s, total_liters=%s, avg_consumption=%s L/100km",
        days, total_km, total_liters, avg_consumption
    )
    
    # Validate results for suspicious data patterns
    # This helps detect data quality issues that need user attention
    if total_km > 0 and days > 0:
        avg_km_per_day = total_km / days
        # Warn if average exceeds 1000 km/day (unrealistic for normal usage)
        if avg_km_per_day > 1000:
            _LOGGER.warning(
                "calculate_consumption_history(%d days): SUSPICIOUS DATA - Average %.1f km/day (total: %d km). "
                "This suggests refueling events may have incorrect timestamps or odometer values. "
                "Refuel count: %d. Check your refueling log for data quality issues.",
                days, avg_km_per_day, total_km, len(relevant_events)
            )
            # Log the event details to help diagnose
            _LOGGER.warning("Refueling events in this period:")
            for i, (event_time, event) in enumerate(relevant_events):
                _LOGGER.warning(
                    "  Event %d: timestamp=%s, odometer=%s km, liters=%s",
                    i + 1,
                    event_time.isoformat(),
                    event.get("odometer_km"),
                    event.get("liters_refueled")
                )
    
    # Calculate total cost from refueling events in this period
    total_cost = 0.0
    for event_time, event in relevant_events:
        price_per_liter = event.get("price_per_liter")
        liters_refueled = event.get("liters_refueled")
        if price_per_liter is not None and liters_refueled is not None:
            total_cost += price_per_liter * liters_refueled
    
    return {
        "avg_consumption_l_per_100km": avg_consumption,
        "total_liters": total_liters,
        "total_km": total_km,
        "refuel_count": len(relevant_events),
        "total_cost": round(total_cost, 2) if total_cost > 0 else 0.0,
    }


async def get_last_refuel_price(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> float | None:
    """Get the price per liter from the most recent refueling event.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Price per liter from last refueling or None if not available
    """
    data = await load_data(hass, entry)
    refueling_log = data.get("refueling_log", [])
    
    if not refueling_log:
        return None
    
    # Sort by timestamp to get the most recent
    sorted_log = sorted(
        refueling_log,
        key=lambda x: x.get("timestamp", ""),
        reverse=True
    )
    
    # Return price from most recent refueling
    return sorted_log[0].get("price_per_liter")


async def calculate_average_price(
    hass: HomeAssistant,
    entry: ConfigEntry,
    days: int = 7,
) -> float | None:
    """Calculate average price per liter over a period.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        days: Number of days to look back
        
    Returns:
        Average price per liter or None if not available
    """
    from datetime import timedelta
    from homeassistant.util import dt as dt_util
    
    data = await load_data(hass, entry)
    refueling_log = data.get("refueling_log", [])
    
    if not refueling_log:
        return None
    
    # Calculate cutoff timestamp
    cutoff = dt_util.now() - timedelta(days=days)
    
    # Filter events within period and collect prices
    prices = []
    for event in refueling_log:
        try:
            event_time = dt_util.parse_datetime(event.get("timestamp", ""))
            price_per_liter = event.get("price_per_liter")
            if event_time and event_time >= cutoff and price_per_liter is not None:
                prices.append(price_per_liter)
        except (ValueError, TypeError):
            continue
    
    if not prices:
        return None
    
    return sum(prices) / len(prices)


# ---------------------------------------------------------------------------
# Trip Tracking Storage
# ---------------------------------------------------------------------------

def _derive_position_quality(trip: dict[str, Any]) -> str:
    """Return the position quality string for a trip based on its coordinates.
    
    Args:
        trip: Trip dictionary containing optional start_latitude/longitude
              and end_latitude/longitude fields.
    
    Returns:
        "full" if both start and end coordinates are present,
        "partial" if only one side has coordinates,
        "none" if neither side has coordinates.
    """
    has_start = (
        trip.get("start_latitude") is not None
        and trip.get("start_longitude") is not None
    )
    has_end = (
        trip.get("end_latitude") is not None
        and trip.get("end_longitude") is not None
    )
    if has_start and has_end:
        return "full"
    if has_start or has_end:
        return "partial"
    return "none"


def _derive_quality_level(trip: dict[str, Any]) -> str:
    """Derive GoBD quality level for a trip.

    Quality levels:
        A – Complete: odometer start+end, timestamps, GPS both sides, fuel data, driver
        B – Mostly complete: odometer + timestamps; missing GPS or fuel or driver
        C – Partial: odometer present but multiple fields missing
        D – Odometer-only: only odometer change recorded, almost everything else missing

    Args:
        trip: Trip dictionary

    Returns:
        Quality level string: "A", "B", "C", or "D"
    """
    has_odometer_start = trip.get("odometer_start") is not None
    has_odometer_end = trip.get("odometer_end") is not None
    has_time_start = bool(trip.get("timestamp_start"))
    has_time_end = bool(trip.get("timestamp_end"))
    has_gps = _derive_position_quality(trip) == "full"
    has_fuel = trip.get("fuel_consumed") is not None or trip.get("fuel_level_start") is not None
    has_driver = bool(trip.get("driver"))

    if (has_odometer_start and has_odometer_end and has_time_start and has_time_end
            and has_gps and has_fuel and has_driver):
        return "A"
    if has_odometer_start and has_odometer_end and has_time_start and has_time_end:
        return "B"
    if has_odometer_start and has_odometer_end:
        return "C"
    return "D"


def _derive_consumption_source(trip: dict[str, Any]) -> str | None:
    """Derive how the consumption value was determined.

    Returns:
        "direct"     – measured from both odometer change and tank-level delta
        "historical" – inferred from adjacent trip tank levels
        "estimated"  – calculated from average consumption and distance
        None         – no consumption data available
    """
    fuel_consumed = trip.get("fuel_consumed")
    if fuel_consumed is None:
        return None
    source = trip.get("consumption_source")
    if source in ("direct", "historical", "estimated"):
        return source
    # Heuristic: if we have fuel levels on both sides the value is direct
    if trip.get("fuel_level_start") is not None and trip.get("fuel_level_end") is not None:
        return "direct"
    # Otherwise treat as estimated
    return "estimated"


PLAUSIBILITY_THRESHOLD_PCT = 5.0  # Max % deviation from avg consumption before flagging


def _check_consumption_plausibility(
    trip: dict[str, Any],
    avg_consumption_l_per_100km: float | None,
) -> dict[str, Any]:
    """Check fuel consumption for plausibility against the fleet average.

    If the average consumption is known and the trip's consumption deviates
    more than 5 % from it the trip is flagged with a deviation note.

    Args:
        trip: Trip dictionary (may include distance_km and fuel_consumed)
        avg_consumption_l_per_100km: Fleet/history average in L/100 km

    Returns:
        Dict with keys:
            plausible (bool | None): True/False/None when unknown
            deviation_pct (float | None): % deviation from average
    """
    result: dict[str, Any] = {"plausible": None, "deviation_pct": None}
    distance_km = trip.get("distance_km") or 0.0
    fuel_consumed = trip.get("fuel_consumed")
    if fuel_consumed is None or distance_km <= 0 or not avg_consumption_l_per_100km:
        return result
    trip_rate = (fuel_consumed / distance_km) * 100  # L/100 km
    deviation_pct = ((trip_rate - avg_consumption_l_per_100km) / avg_consumption_l_per_100km) * 100
    result["deviation_pct"] = round(deviation_pct, 1)
    result["plausible"] = abs(deviation_pct) <= PLAUSIBILITY_THRESHOLD_PCT
    return result


def _append_change_log(
    trip: dict[str, Any],
    changed_by: str,
    changes: dict[str, Any],
    action: str = "update",
) -> None:
    """Append an immutable audit entry to the trip's change_log list.

    This implements the GoBD requirement for a revision-safe audit trail
    that records who changed what and when.

    Args:
        trip: Trip dictionary to mutate in-place
        changed_by: User / system actor performing the change
        changes: Dict of field name → new value pairs that were changed
        action: Human-readable action label (e.g. "update", "finalize", "delete_gap_fill")
    """
    from homeassistant.util import dt as dt_util
    if "change_log" not in trip:
        trip["change_log"] = []
    entry = {
        "ts": dt_util.now().isoformat(),
        "by": changed_by,
        "action": action,
        "fields": changes,
    }
    trip["change_log"].append(entry)


async def add_trip(
    hass: HomeAssistant,
    entry: ConfigEntry,
    trip_data: dict[str, Any],
) -> int:
    """Add a new trip to storage.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        trip_data: Trip data dictionary
        
    Returns:
        Trip ID of the newly created trip
    """
    from homeassistant.util import dt as dt_util
    
    data = await load_data(hass, entry)
    
    # Initialize trips list if not present
    if "trips" not in data:
        data["trips"] = []
    
    # Initialize trip_statistics if not present
    if "trip_statistics" not in data:
        data["trip_statistics"] = {
            "total_trips": 0,
            "total_distance_km": 0.0,
            "total_fuel_consumed": 0.0,
            "total_fuel_cost": 0.0,
            "total_additional_costs": 0.0,
            "business_trips": 0,
            "private_trips": 0,
            "commute_trips": 0,
        }
    
    # Get next trip ID
    next_id = data.get("next_trip_id", 1)
    trip_data["trip_id"] = next_id
    data["next_trip_id"] = next_id + 1
    
    # Add timestamps
    now = dt_util.now().isoformat()
    trip_data.setdefault("created_at", now)
    trip_data.setdefault("updated_at", now)
    
    # Ensure position_quality is set based on coordinate availability.
    if "position_quality" not in trip_data:
        trip_data["position_quality"] = _derive_position_quality(trip_data)

    # Derive GoBD quality level (A/B/C/D)
    if "quality_level" not in trip_data:
        trip_data["quality_level"] = _derive_quality_level(trip_data)

    # Derive consumption source label
    if "consumption_source" not in trip_data:
        trip_data["consumption_source"] = _derive_consumption_source(trip_data)

    # Initialize GoBD finalization fields
    trip_data.setdefault("finalized", False)
    trip_data.setdefault("finalized_by", None)
    trip_data.setdefault("finalized_at", None)

    # Initialize driver field (required for GoBD)
    trip_data.setdefault("driver", None)

    # Initialize append-only audit/change log
    trip_data.setdefault("change_log", [])

    # Add trip to storage
    data["trips"].append(trip_data)
    
    # Update statistics
    stats = data["trip_statistics"]
    stats["total_trips"] = (stats.get("total_trips") or 0) + 1
    stats["total_distance_km"] = (stats.get("total_distance_km") or 0.0) + (trip_data.get("distance_km") or 0.0)
    stats["total_fuel_consumed"] = (stats.get("total_fuel_consumed") or 0.0) + (trip_data.get("fuel_consumed") or 0.0)
    stats["total_fuel_cost"] = (stats.get("total_fuel_cost") or 0.0) + (trip_data.get("fuel_cost") or 0.0)
    stats["total_additional_costs"] = (stats.get("total_additional_costs") or 0.0) + (trip_data.get("additional_costs") or 0.0)
    
    # Update category counters
    category = trip_data.get("category", "private")
    category_key = f"{category}_trips"
    stats[category_key] = (stats.get(category_key) or 0) + 1
    
    await save_data(hass, entry, data)
    return next_id


async def get_trips(
    hass: HomeAssistant,
    entry: ConfigEntry,
    limit: int | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Get trips from storage.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        limit: Maximum number of trips to return (newest first)
        category: Filter by category (business, private, commute)
        
    Returns:
        List of trip dictionaries
    """
    data = await load_data(hass, entry)
    trips = data.get("trips", [])
    
    # Filter by category if specified
    if category:
        trips = [t for t in trips if t.get("category") == category]
    
    # Sort by timestamp_end (newest first)
    trips = sorted(trips, key=lambda x: x.get("timestamp_end", ""), reverse=True)
    
    # Apply limit if specified
    if limit:
        trips = trips[:limit]
    
    return trips


async def update_trip(
    hass: HomeAssistant,
    entry: ConfigEntry,
    trip_id: int,
    updates: dict[str, Any],
    changed_by: str = "system",
) -> bool:
    """Update an existing trip.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        trip_id: ID of the trip to update
        updates: Dictionary of fields to update
        changed_by: User or system actor performing the update (for audit log)
        
    Returns:
        True if trip was found and updated, False otherwise
    """
    from homeassistant.util import dt as dt_util
    
    data = await load_data(hass, entry)
    trips = data.get("trips", [])
    
    for trip in trips:
        if trip.get("trip_id") == trip_id:
            # Update timestamp
            trip["updated_at"] = dt_util.now().isoformat()

            # Record which fields are actually changing for the audit log
            changed_fields = {k: v for k, v in updates.items() if trip.get(k) != v}

            # Apply updates (guard finalized trips from further odometer changes)
            if trip.get("finalized"):
                # Odometer fields are locked on finalized trips to protect the km history
                odometer_fields = {"odometer_start", "odometer_end", "distance_km"}
                updates = {k: v for k, v in updates.items() if k not in odometer_fields}
                # Mark that this finalized trip was modified afterwards
                if updates:
                    trip["modified_after_finalization"] = True

            trip.update(updates)
            
            # Refresh derived fields
            coord_fields = {"start_latitude", "start_longitude", "end_latitude", "end_longitude"}
            if coord_fields.intersection(updates.keys()):
                trip["position_quality"] = _derive_position_quality(trip)

            # Refresh quality level whenever any data field changes
            trip["quality_level"] = _derive_quality_level(trip)

            # Refresh consumption_source if relevant fields changed
            consumption_fields = {"fuel_consumed", "fuel_level_start", "fuel_level_end", "consumption_source"}
            if consumption_fields.intersection(updates.keys()):
                if "consumption_source" not in updates:
                    trip["consumption_source"] = _derive_consumption_source(trip)

            # Append audit entry if anything actually changed
            if changed_fields:
                _append_change_log(trip, changed_by, changed_fields, action="update")
            
            await save_data(hass, entry, data)
            return True
    
    return False


async def finalize_trip(
    hass: HomeAssistant,
    entry: ConfigEntry,
    trip_id: int,
    finalized_by: str,
) -> bool:
    """Mark a trip as finalized (GoBD-compliant immutable confirmation).

    Once finalized, odometer fields cannot be changed via update_trip.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        trip_id: ID of the trip to finalize
        finalized_by: User performing the finalization

    Returns:
        True if trip was found and finalized, False otherwise
    """
    from homeassistant.util import dt as dt_util

    data = await load_data(hass, entry)
    trips = data.get("trips", [])

    for trip in trips:
        if trip.get("trip_id") == trip_id:
            now = dt_util.now().isoformat()
            trip["finalized"] = True
            trip["finalized_by"] = finalized_by
            trip["finalized_at"] = now
            trip["updated_at"] = now
            _append_change_log(trip, finalized_by, {}, action="finalize")
            await save_data(hass, entry, data)
            _LOGGER.info("Trip #%d finalized by %s", trip_id, finalized_by)
            return True

    return False


async def delete_trip(
    hass: HomeAssistant,
    entry: ConfigEntry,
    trip_id: int,
) -> bool:
    """Delete a trip from storage.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        trip_id: ID of the trip to delete
        
    Returns:
        True if trip was found and deleted, False otherwise
    """
    data = await load_data(hass, entry)
    trips = data.get("trips", [])
    
    # Initialize trip_statistics if not present
    if "trip_statistics" not in data:
        data["trip_statistics"] = {
            "total_trips": 0,
            "total_distance_km": 0.0,
            "total_fuel_consumed": 0.0,
            "total_fuel_cost": 0.0,
            "total_additional_costs": 0.0,
            "business_trips": 0,
            "private_trips": 0,
            "commute_trips": 0,
        }
    
    # Find and remove the trip
    for i, trip in enumerate(trips):
        if trip.get("trip_id") == trip_id:
            removed_trip = trips.pop(i)
            
            # Update statistics
            stats = data["trip_statistics"]
            stats["total_trips"] = max(0, (stats.get("total_trips") or 0) - 1)
            stats["total_distance_km"] = max(0.0, (stats.get("total_distance_km") or 0.0) - (removed_trip.get("distance_km") or 0.0))
            stats["total_fuel_consumed"] = max(0.0, (stats.get("total_fuel_consumed") or 0.0) - (removed_trip.get("fuel_consumed") or 0.0))
            stats["total_fuel_cost"] = max(0.0, (stats.get("total_fuel_cost") or 0.0) - (removed_trip.get("fuel_cost") or 0.0))
            stats["total_additional_costs"] = max(0.0, (stats.get("total_additional_costs") or 0.0) - (removed_trip.get("additional_costs") or 0.0))
            
            # Update category counters
            category = removed_trip.get("category", "private")
            category_key = f"{category}_trips"
            stats[category_key] = max(0, (stats.get(category_key) or 0) - 1)

            # ---------------------------------------------------------------
            # GoBD odometer continuity: if the deleted trip had valid odometer
            # data AND the neighbouring trips leave a gap, insert a placeholder
            # trip to keep the km history unbroken.
            # ---------------------------------------------------------------
            odo_start = removed_trip.get("odometer_start")
            odo_end = removed_trip.get("odometer_end")
            if odo_start is not None and odo_end is not None and odo_end > odo_start:
                # Check whether any remaining trip already covers this interval
                gap_covered = any(
                    (t.get("odometer_start") is not None
                     and t.get("odometer_end") is not None
                     and t["odometer_start"] <= odo_start
                     and t["odometer_end"] >= odo_end)
                    for t in data["trips"]
                )
                if not gap_covered:
                    from homeassistant.util import dt as dt_util
                    now_str = dt_util.now().isoformat()
                    gap_id = data.get("next_trip_id", 1)
                    data["next_trip_id"] = gap_id + 1
                    gap_trip: dict[str, Any] = {
                        "trip_id": gap_id,
                        "odometer_start": odo_start,
                        "odometer_end": odo_end,
                        "distance_km": round(odo_end - odo_start, 2),
                        "timestamp_start": removed_trip.get("timestamp_start"),
                        "timestamp_end": removed_trip.get("timestamp_end"),
                        "category": "private",
                        "data_quality": "gap_fill",
                        "quality_level": "D",
                        "finalized": False,
                        "finalized_by": None,
                        "finalized_at": None,
                        "driver": None,
                        "fuel_consumed": None,
                        "consumption_source": None,
                        "position_quality": "none",
                        "created_at": now_str,
                        "updated_at": now_str,
                        "notes": (
                            f"Auto-generated gap-fill after trip #{trip_id} was deleted. "
                            "Odometer continuity preserved (GoBD)."
                        ),
                        "change_log": [{
                            "ts": now_str,
                            "by": "system",
                            "action": "gap_fill",
                            "fields": {"deleted_trip_id": trip_id},
                        }],
                    }
                    data["trips"].append(gap_trip)
                    stats["total_trips"] = (stats.get("total_trips") or 0) + 1
                    stats["total_distance_km"] = (
                        (stats.get("total_distance_km") or 0.0) + gap_trip["distance_km"]
                    )
                    stats["private_trips"] = (stats.get("private_trips") or 0) + 1
                    _LOGGER.info(
                        "Inserted gap-fill trip #%d (%.1f km, odo %.1f→%.1f) "
                        "after deleting trip #%d to preserve odometer continuity.",
                        gap_id,
                        gap_trip["distance_km"],
                        odo_start,
                        odo_end,
                        trip_id,
                    )
            
            await save_data(hass, entry, data)
            return True
    
    return False


async def merge_trips(
    hass: HomeAssistant,
    entry: ConfigEntry,
    trip_id_1: int,
    trip_id_2: int,
    merged_by: str = "ha_user",
) -> int | None:
    """Merge two trips into one combined trip.

    The earlier trip's start and the later trip's end form the merged trip.
    Distance and fuel are summed. The earlier trip is replaced by the merged
    trip; the later trip is removed.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        trip_id_1: ID of the first trip
        trip_id_2: ID of the second trip
        merged_by: User performing the merge

    Returns:
        New trip ID of the merged trip, or None if one/both trips were not found
    """
    from homeassistant.util import dt as dt_util

    data = await load_data(hass, entry)
    trips = data.get("trips", [])

    t1 = next((t for t in trips if t.get("trip_id") == trip_id_1), None)
    t2 = next((t for t in trips if t.get("trip_id") == trip_id_2), None)

    if t1 is None or t2 is None:
        return None

    # Determine chronological order
    ts1 = t1.get("timestamp_start") or t1.get("timestamp_end") or ""
    ts2 = t2.get("timestamp_start") or t2.get("timestamp_end") or ""
    earlier, later = (t1, t2) if ts1 <= ts2 else (t2, t1)

    now_str = dt_util.now().isoformat()
    next_id = data.get("next_trip_id", 1)
    data["next_trip_id"] = next_id + 1

    merged_distance = (earlier.get("distance_km") or 0.0) + (later.get("distance_km") or 0.0)
    merged_fuel = None
    if earlier.get("fuel_consumed") is not None or later.get("fuel_consumed") is not None:
        merged_fuel = (earlier.get("fuel_consumed") or 0.0) + (later.get("fuel_consumed") or 0.0)

    merged_trip: dict[str, Any] = {
        "trip_id": next_id,
        "timestamp_start": earlier.get("timestamp_start"),
        "timestamp_end": later.get("timestamp_end"),
        "distance_km": round(merged_distance, 2),
        "category": earlier.get("category") or later.get("category") or "private",
        "purpose": earlier.get("purpose") or later.get("purpose"),
        "driver": earlier.get("driver") or later.get("driver"),
        "fuel_consumed": merged_fuel,
        "additional_costs": (earlier.get("additional_costs") or 0.0) + (later.get("additional_costs") or 0.0),
        "odometer_start": earlier.get("odometer_start"),
        "odometer_end": later.get("odometer_end"),
        "start_latitude": earlier.get("start_latitude"),
        "start_longitude": earlier.get("start_longitude"),
        "start_name": earlier.get("start_name"),
        "start_address": earlier.get("start_address"),
        "end_latitude": later.get("end_latitude"),
        "end_longitude": later.get("end_longitude"),
        "end_name": later.get("end_name"),
        "end_address": later.get("end_address"),
        "data_quality": "manual",
        "finalized": False,
        "finalized_by": None,
        "finalized_at": None,
        "created_at": now_str,
        "updated_at": now_str,
        "notes": f"Merged from trips #{earlier['trip_id']} and #{later['trip_id']}",
        "change_log": [{
            "ts": now_str,
            "by": merged_by,
            "action": "merge",
            "fields": {"source_trip_ids": [earlier["trip_id"], later["trip_id"]]},
        }],
    }
    merged_trip["position_quality"] = _derive_position_quality(merged_trip)
    merged_trip["quality_level"] = _derive_quality_level(merged_trip)
    merged_trip["consumption_source"] = _derive_consumption_source(merged_trip)

    # Remove both source trips and add merged trip
    data["trips"] = [t for t in trips if t.get("trip_id") not in (trip_id_1, trip_id_2)]
    data["trips"].append(merged_trip)

    # Update statistics: subtract both, add merged
    stats = data.setdefault("trip_statistics", {
        "total_trips": 0, "total_distance_km": 0.0, "total_fuel_consumed": 0.0,
        "total_fuel_cost": 0.0, "total_additional_costs": 0.0,
        "business_trips": 0, "private_trips": 0, "commute_trips": 0,
    })
    for removed in (earlier, later):
        stats["total_trips"] = max(0, (stats.get("total_trips") or 0) - 1)
        stats["total_distance_km"] = max(0.0, (stats.get("total_distance_km") or 0.0) - (removed.get("distance_km") or 0.0))
        stats["total_fuel_consumed"] = max(0.0, (stats.get("total_fuel_consumed") or 0.0) - (removed.get("fuel_consumed") or 0.0))
        cat_key = f"{removed.get('category', 'private')}_trips"
        stats[cat_key] = max(0, (stats.get(cat_key) or 0) - 1)

    stats["total_trips"] = (stats.get("total_trips") or 0) + 1
    stats["total_distance_km"] = (stats.get("total_distance_km") or 0.0) + merged_trip["distance_km"]
    if merged_fuel:
        stats["total_fuel_consumed"] = (stats.get("total_fuel_consumed") or 0.0) + merged_fuel
    cat_key = f"{merged_trip['category']}_trips"
    stats[cat_key] = (stats.get(cat_key) or 0) + 1

    await save_data(hass, entry, data)
    _LOGGER.info("Merged trips #%d and #%d into new trip #%d", trip_id_1, trip_id_2, next_id)
    return next_id


async def split_trip(
    hass: HomeAssistant,
    entry: ConfigEntry,
    trip_id: int,
    split_distance_km: float,
    split_by: str = "ha_user",
) -> tuple[int, int] | None:
    """Split a trip into two trips at a given distance.

    The first trip covers split_distance_km; the second covers the remainder.
    Odometer values are recalculated if available.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        trip_id: ID of the trip to split
        split_distance_km: Distance for the first part in km (must be > 0 and < total distance)
        split_by: User performing the split

    Returns:
        Tuple of (trip_id_part1, trip_id_part2), or None if trip not found or split invalid
    """
    from homeassistant.util import dt as dt_util
    import datetime

    data = await load_data(hass, entry)
    trips = data.get("trips", [])

    original = next((t for t in trips if t.get("trip_id") == trip_id), None)
    if original is None:
        return None

    total_distance = original.get("distance_km") or 0.0
    if split_distance_km <= 0 or split_distance_km >= total_distance:
        return None

    remainder_km = round(total_distance - split_distance_km, 2)
    split_distance_km = round(split_distance_km, 2)
    ratio = split_distance_km / total_distance

    # Estimate split timestamp proportionally between start and end
    split_ts: str | None = None
    try:
        ts_start = datetime.datetime.fromisoformat(original["timestamp_start"])
        ts_end = datetime.datetime.fromisoformat(original["timestamp_end"])
        delta = ts_end - ts_start
        split_ts = (ts_start + datetime.timedelta(seconds=delta.total_seconds() * ratio)).isoformat()
    except Exception:
        split_ts = original.get("timestamp_start")

    now_str = dt_util.now().isoformat()
    id1 = data.get("next_trip_id", 1)
    id2 = id1 + 1
    data["next_trip_id"] = id2 + 1

    odo_start = original.get("odometer_start")
    odo_end = original.get("odometer_end")
    odo_mid = round(odo_start + split_distance_km, 2) if odo_start is not None else None

    fuel_total = original.get("fuel_consumed")
    fuel1 = round(fuel_total * ratio, 4) if fuel_total is not None else None
    fuel2 = round(fuel_total - fuel1, 4) if fuel_total is not None else None

    base = {
        "category": original.get("category", "private"),
        "purpose": original.get("purpose"),
        "driver": original.get("driver"),
        "data_quality": "manual",
        "finalized": False,
        "finalized_by": None,
        "finalized_at": None,
        "created_at": now_str,
        "updated_at": now_str,
    }

    part1: dict[str, Any] = {
        **base,
        "trip_id": id1,
        "timestamp_start": original.get("timestamp_start"),
        "timestamp_end": split_ts,
        "distance_km": split_distance_km,
        "odometer_start": odo_start,
        "odometer_end": odo_mid,
        "start_latitude": original.get("start_latitude"),
        "start_longitude": original.get("start_longitude"),
        "start_name": original.get("start_name"),
        "start_address": original.get("start_address"),
        "end_latitude": None,
        "end_longitude": None,
        "end_name": None,
        "end_address": None,
        "fuel_consumed": fuel1,
        "additional_costs": round((original.get("additional_costs") or 0.0) * ratio, 4),
        "notes": f"Part 1 of 2 – split from trip #{trip_id}",
        "change_log": [{
            "ts": now_str, "by": split_by, "action": "split",
            "fields": {"source_trip_id": trip_id, "part": 1},
        }],
    }
    part2: dict[str, Any] = {
        **base,
        "trip_id": id2,
        "timestamp_start": split_ts,
        "timestamp_end": original.get("timestamp_end"),
        "distance_km": remainder_km,
        "odometer_start": odo_mid,
        "odometer_end": odo_end,
        "start_latitude": None,
        "start_longitude": None,
        "start_name": None,
        "start_address": None,
        "end_latitude": original.get("end_latitude"),
        "end_longitude": original.get("end_longitude"),
        "end_name": original.get("end_name"),
        "end_address": original.get("end_address"),
        "fuel_consumed": fuel2,
        "additional_costs": round((original.get("additional_costs") or 0.0) * (1 - ratio), 4),
        "notes": f"Part 2 of 2 – split from trip #{trip_id}",
        "change_log": [{
            "ts": now_str, "by": split_by, "action": "split",
            "fields": {"source_trip_id": trip_id, "part": 2},
        }],
    }

    for part in (part1, part2):
        part["position_quality"] = _derive_position_quality(part)
        part["quality_level"] = _derive_quality_level(part)
        part["consumption_source"] = _derive_consumption_source(part)

    # Remove original trip and add two new ones
    data["trips"] = [t for t in trips if t.get("trip_id") != trip_id]
    data["trips"].extend([part1, part2])

    # Update statistics: subtract original, add both parts
    stats = data.setdefault("trip_statistics", {
        "total_trips": 0, "total_distance_km": 0.0, "total_fuel_consumed": 0.0,
        "total_fuel_cost": 0.0, "total_additional_costs": 0.0,
        "business_trips": 0, "private_trips": 0, "commute_trips": 0,
    })
    stats["total_trips"] = max(0, (stats.get("total_trips") or 0) - 1)
    stats["total_distance_km"] = max(0.0, (stats.get("total_distance_km") or 0.0) - (original.get("distance_km") or 0.0))
    if original.get("fuel_consumed"):
        stats["total_fuel_consumed"] = max(0.0, (stats.get("total_fuel_consumed") or 0.0) - original["fuel_consumed"])
    orig_cat_key = f"{original.get('category', 'private')}_trips"
    stats[orig_cat_key] = max(0, (stats.get(orig_cat_key) or 0) - 1)

    for part in (part1, part2):
        stats["total_trips"] = (stats.get("total_trips") or 0) + 1
        stats["total_distance_km"] = (stats.get("total_distance_km") or 0.0) + part["distance_km"]
        if part.get("fuel_consumed"):
            stats["total_fuel_consumed"] = (stats.get("total_fuel_consumed") or 0.0) + part["fuel_consumed"]
        cat_key = f"{part['category']}_trips"
        stats[cat_key] = (stats.get(cat_key) or 0) + 1

    await save_data(hass, entry, data)
    _LOGGER.info("Split trip #%d into #%d (%.1f km) and #%d (%.1f km)", trip_id, id1, split_distance_km, id2, remainder_km)
    return (id1, id2)


async def get_trip_patterns(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> list[dict[str, Any]]:
    """Get all trip patterns from storage.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        List of trip pattern dictionaries
    """
    data = await load_data(hass, entry)
    return data.get("trip_patterns", [])


async def get_pending_trips(
    hass: HomeAssistant,
    entry: ConfigEntry,
    older_than_hours: int = 24,
) -> list[dict[str, Any]]:
    """Return unfinalized trips that are older than *older_than_hours*.

    These are the trips that need manual review and finalization to meet
    GoBD requirements.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        older_than_hours: Age threshold in hours (default 24)

    Returns:
        List of trip dicts sorted by timestamp_end ascending (oldest first)
    """
    from datetime import timedelta
    from homeassistant.util import dt as dt_util

    data = await load_data(hass, entry)
    now = dt_util.now()
    cutoff = now - timedelta(hours=older_than_hours)
    pending = []
    for trip in data.get("trips", []):
        if trip.get("finalized"):
            continue
        ts_end_str = trip.get("timestamp_end")
        if not ts_end_str:
            # No end time recorded – treat as pending
            pending.append(trip)
            continue
        try:
            ts_end = dt_util.parse_datetime(ts_end_str)
            if ts_end is None:
                pending.append(trip)
                continue
            if ts_end.tzinfo is None:
                ts_end = dt_util.as_local(ts_end)
            if ts_end <= cutoff:
                pending.append(trip)
        except Exception:
            pending.append(trip)

    # Sort oldest first so the user sees the oldest unresolved trip at the top
    pending.sort(key=lambda t: t.get("timestamp_end", ""))
    return pending


async def add_trip_pattern(
    hass: HomeAssistant,
    entry: ConfigEntry,
    pattern_data: dict[str, Any],
) -> int:
    """Add a new trip pattern to storage.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        pattern_data: Pattern data dictionary
        
    Returns:
        Pattern ID of the newly created pattern
    """
    from homeassistant.util import dt as dt_util
    
    data = await load_data(hass, entry)
    
    # Initialize trip_patterns list if not present
    if "trip_patterns" not in data:
        data["trip_patterns"] = []
    
    # Get next pattern ID
    next_id = data.get("next_pattern_id", 1)
    pattern_data["pattern_id"] = next_id
    data["next_pattern_id"] = next_id + 1
    
    # Add timestamps
    now = dt_util.now().isoformat()
    pattern_data.setdefault("created_at", now)
    pattern_data.setdefault("updated_at", now)
    
    # Add pattern to storage
    data["trip_patterns"].append(pattern_data)
    
    await save_data(hass, entry, data)
    return next_id


async def get_pois(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> list[dict[str, Any]]:
    """Get all POIs from storage.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        List of POI dictionaries
    """
    data = await load_data(hass, entry)
    return data.get("pois", [])


async def add_poi(
    hass: HomeAssistant,
    entry: ConfigEntry,
    poi_data: dict[str, Any],
) -> int:
    """Add a new POI to storage.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        poi_data: POI data dictionary
        
    Returns:
        POI ID of the newly created POI
    """
    from homeassistant.util import dt as dt_util
    
    data = await load_data(hass, entry)
    
    # Initialize pois list if not present
    if "pois" not in data:
        data["pois"] = []
    
    # Get next POI ID
    next_id = data.get("next_poi_id", 1)
    poi_data["poi_id"] = next_id
    data["next_poi_id"] = next_id + 1
    
    # Add timestamps
    now = dt_util.now().isoformat()
    poi_data.setdefault("created_at", now)
    poi_data.setdefault("updated_at", now)
    
    # Add POI to storage
    data["pois"].append(poi_data)
    
    await save_data(hass, entry, data)
    return next_id


async def get_trip_tracking_config(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Get trip tracking configuration.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Trip tracking configuration dictionary
    """
    data = await load_data(hass, entry)
    return data.get("trip_tracking_config", {})


async def recalculate_trip_statistics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Recalculate trip statistics from existing trips.
    
    This function recalculates all statistics from scratch based on the trips
    stored in the database. Useful for fixing inconsistencies or initializing
    statistics after trips have been imported.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Updated trip statistics dictionary
    """
    _LOGGER.info("Recalculating trip statistics from existing trips")
    
    data = await load_data(hass, entry)
    trips = data.get("trips", [])
    
    # Initialize statistics
    stats = {
        "total_trips": 0,
        "total_distance_km": 0.0,
        "total_fuel_consumed": 0.0,
        "total_fuel_cost": 0.0,
        "total_additional_costs": 0.0,
        "business_trips": 0,
        "private_trips": 0,
        "commute_trips": 0,
    }
    
    # Calculate from all trips
    for trip in trips:
        stats["total_trips"] += 1
        stats["total_distance_km"] += (trip.get("distance_km") or 0.0)
        stats["total_fuel_consumed"] += (trip.get("fuel_consumed") or 0.0)
        stats["total_fuel_cost"] += (trip.get("fuel_cost") or 0.0)
        stats["total_additional_costs"] += (trip.get("additional_costs") or 0.0)
        
        # Update category counters
        category = trip.get("category", "private")
        category_key = f"{category}_trips"
        if category_key in stats:
            stats[category_key] += 1
    
    # Update storage
    data["trip_statistics"] = stats
    await save_data(hass, entry, data)
    
    _LOGGER.info(
        "Trip statistics recalculated: %d trips, %.1f km, %.1f L fuel",
        stats["total_trips"],
        stats["total_distance_km"],
        stats["total_fuel_consumed"],
    )
    
    return stats


async def save_last_vehicle_data(
    hass: HomeAssistant,
    entry: ConfigEntry,
    vehicle_data: dict[str, Any],
) -> None:
    """Save the last successful vehicle data fetch to storage.
    
    This ensures vehicle data persists across HA restarts.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        vehicle_data: Dictionary with vehicle data (odometer_km, tank_level, range_km, etc.)
    """
    from homeassistant.util import dt as dt_util
    
    data = await load_data(hass, entry)
    
    # Store vehicle data with timestamp
    data["last_vehicle_data"] = {
        "data": vehicle_data.copy(),
        "timestamp": dt_util.now().isoformat(),
    }
    
    await save_data(hass, entry, data)
    _LOGGER.debug("Saved last vehicle data to storage: %s", vehicle_data)


async def get_last_vehicle_data(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any] | None:
    """Get the last successful vehicle data from storage.
    
    Used to restore vehicle data after HA restart when entities haven't loaded yet.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Dictionary with vehicle data or None if not available
    """
    data = await load_data(hass, entry)
    last_vehicle = data.get("last_vehicle_data")
    
    if last_vehicle:
        _LOGGER.debug(
            "Retrieved last vehicle data from storage (timestamp: %s): %s",
            last_vehicle.get("timestamp"),
            last_vehicle.get("data")
        )
        return last_vehicle.get("data")
    
    return None
