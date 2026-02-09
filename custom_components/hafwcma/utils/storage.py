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
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.storage import Store

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY_TEMPLATE = f"{DOMAIN}_{{entry_id}}"


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
            "weekday_consumption": {},  # {weekday: {km: float, count: int}}
            "tank_history": [],  # List of refueling events
            "last_price": None,  # float
            "last_price_timestamp": None,  # str timestamp of last price
            "last_station": None,  # dict with last station data
            "last_station_timestamp": None,  # str timestamp of last station
            "last_decision": None,  # dict with decision data
            "last_api": None,  # dict with last API response
            "last_telegram": None,  # dict with last telegram message
            "last_error": None,  # str with last error
            "ml_models": {},  # ML model parameters
            "prediction_history": [],  # List of prediction results for accuracy tracking
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
) -> None:
    """Add a price observation to history.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        price: Price in EUR per liter
        timestamp: ISO format timestamp
    """
    data = await load_data(hass, entry)
    data["price_history"].append({"ts": timestamp, "price": price})
    
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
) -> None:
    """Add an odometer observation to history.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        odometer_km: Odometer reading in kilometers
        timestamp: ISO format timestamp
    """
    data = await load_data(hass, entry)
    data["odometer_history"].append({"ts": timestamp, "value": odometer_km})
    
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
    
    # Get next ID
    next_id = 1
    if data["refueling_log"]:
        next_id = max(event.get("id", 0) for event in data["refueling_log"]) + 1
    
    # Create complete refueling record with ID
    refuel_record = {
        "id": next_id,
        "timestamp": event_data.get("timestamp"),
        "odometer_km": event_data.get("odometer_km"),
        "station_name": event_data.get("station_name"),
        "liters_refueled": event_data.get("liters_refueled"),
        "price_per_liter": event_data.get("price_per_liter"),
        "total_cost": event_data.get("total_cost"),
        "latitude": event_data.get("latitude"),
        "longitude": event_data.get("longitude"),
        "fuel_type": event_data.get("fuel_type"),
        "editable": True,
    }
    
    data["refueling_log"].append(refuel_record)
    
    # Also add to legacy tank_history for backward compatibility
    data["tank_history"].append(event_data)
    
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
                "timestamp", "odometer_km", "station_name",
                "liters_refueled", "price_per_liter", "total_cost",
                "latitude", "longitude", "fuel_type"
            ]
            for field in allowed_fields:
                if field in updates:
                    record[field] = updates[field]
            
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

async def calculate_consumption_history(
    hass: HomeAssistant,
    entry: ConfigEntry,
    days: int = 1,
) -> dict[str, Any]:
    """Calculate average consumption for a historical period.
    
    Calculates consumption based on refueling events and odometer changes.
    
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
        return {
            "avg_consumption_l_per_100km": None,
            "total_liters": 0,
            "total_km": 0,
            "refuel_count": 0,
        }
    
    # Calculate cutoff timestamp
    cutoff = dt_util.now() - timedelta(days=days)
    
    # Filter events within period
    relevant_events = []
    for event in refueling_log:
        try:
            event_time = dt_util.parse_datetime(event.get("timestamp", ""))
            if event_time and event_time >= cutoff:
                relevant_events.append(event)
        except (ValueError, TypeError):
            continue
    
    if len(relevant_events) < 2:
        # Need at least 2 refueling events to calculate consumption
        return {
            "avg_consumption_l_per_100km": None,
            "total_liters": 0,
            "total_km": 0,
            "refuel_count": len(relevant_events),
        }
    
    # Sort by timestamp
    relevant_events.sort(key=lambda x: x.get("timestamp", ""))
    
    # Calculate total distance and fuel consumed
    total_km = 0
    total_liters = 0
    
    for i in range(1, len(relevant_events)):
        prev_event = relevant_events[i - 1]
        curr_event = relevant_events[i]
        
        prev_odometer = prev_event.get("odometer_km")
        curr_odometer = curr_event.get("odometer_km")
        liters_refueled = prev_event.get("liters_refueled")
        
        if prev_odometer and curr_odometer and liters_refueled:
            km_driven = curr_odometer - prev_odometer
            if km_driven > 0:
                total_km += km_driven
                total_liters += liters_refueled
    
    # Calculate average consumption
    avg_consumption = None
    if total_km > 0:
        avg_consumption = (total_liters / total_km) * 100
    
    return {
        "avg_consumption_l_per_100km": avg_consumption,
        "total_liters": total_liters,
        "total_km": total_km,
        "refuel_count": len(relevant_events),
    }
