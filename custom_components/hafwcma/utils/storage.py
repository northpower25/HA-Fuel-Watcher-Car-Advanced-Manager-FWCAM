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
) -> None:
    """Add a refueling event to tank history.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        event_data: Refueling event data (timestamp, amount, price, etc.)
    """
    data = await load_data(hass, entry)
    data["tank_history"].append(event_data)
    
    # Keep only last 100 refueling events
    if len(data["tank_history"]) > 100:
        data["tank_history"] = data["tank_history"][-100:]
    
    await save_data(hass, entry, data)


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
    from datetime import datetime
    
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
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
    from datetime import datetime
    
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
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
