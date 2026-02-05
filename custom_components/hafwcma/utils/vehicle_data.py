"""Utility functions for reading vehicle entity data."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant, State
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    STATE_HOME,
    STATE_NOT_HOME,
    STATE_UNKNOWN,
    STATE_UNAVAILABLE,
)

_LOGGER = logging.getLogger(__name__)


async def async_get_entity_state(
    hass: HomeAssistant, entity_id: str | None
) -> State | None:
    """Get the state of an entity.
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to get state for
        
    Returns:
        State object or None if entity doesn't exist or is not provided
    """
    if not entity_id:
        return None
        
    state = hass.states.get(entity_id)
    if not state:
        _LOGGER.warning("Entity %s not found", entity_id)
        return None
        
    return state


async def async_get_numeric_state(
    hass: HomeAssistant, entity_id: str | None, default: float | None = None
) -> float | None:
    """Get numeric state value from an entity.
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to read
        default: Default value if entity unavailable or invalid
        
    Returns:
        Numeric value or default
    """
    state = await async_get_entity_state(hass, entity_id)
    
    if not state:
        return default
        
    if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        _LOGGER.debug("Entity %s has invalid state: %s", entity_id, state.state)
        return default
        
    try:
        return float(state.state)
    except (ValueError, TypeError):
        _LOGGER.warning(
            "Could not convert state of %s to float: %s", entity_id, state.state
        )
        return default


async def async_get_device_tracker_coordinates(
    hass: HomeAssistant, entity_id: str | None
) -> tuple[float, float] | None:
    """Get coordinates from a device_tracker entity.
    
    Handles both cases:
    - State contains coordinates (latitude, longitude)
    - State contains zone name (home, away, etc.) - use attributes
    
    Args:
        hass: Home Assistant instance
        entity_id: Device tracker entity ID
        
    Returns:
        Tuple of (latitude, longitude) or None if unavailable
    """
    state = await async_get_entity_state(hass, entity_id)
    
    if not state:
        return None
        
    if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        _LOGGER.debug("Device tracker %s has invalid state: %s", entity_id, state.state)
        return None
    
    # Try to get coordinates from attributes first (most reliable)
    latitude = state.attributes.get(ATTR_LATITUDE)
    longitude = state.attributes.get(ATTR_LONGITUDE)
    
    if latitude is not None and longitude is not None:
        try:
            return (float(latitude), float(longitude))
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Could not convert coordinates from attributes of %s: lat=%s, lon=%s",
                entity_id,
                latitude,
                longitude,
            )
            return None
    
    # If state is a zone name (home, away, not_home, etc.), we can't use it
    # without zone lookup, so return None
    state_lower = state.state.lower()
    if state_lower in ("home", "not_home", "away"):
        _LOGGER.debug(
            "Device tracker %s is in zone '%s' but no coordinates in attributes",
            entity_id,
            state.state,
        )
        return None
    
    # Try to parse state as coordinates (some device trackers put lat,lon in state)
    # This is rare but handle it for completeness
    try:
        parts = state.state.split(",")
        if len(parts) == 2:
            return (float(parts[0].strip()), float(parts[1].strip()))
    except (ValueError, AttributeError):
        pass
    
    _LOGGER.debug(
        "Could not extract coordinates from device tracker %s (state: %s)",
        entity_id,
        state.state,
    )
    return None


async def async_get_odometer(
    hass: HomeAssistant, entity_id: str | None
) -> float | None:
    """Get odometer reading in kilometers.
    
    Args:
        hass: Home Assistant instance
        entity_id: Odometer sensor entity ID
        
    Returns:
        Odometer reading in km or None
    """
    return await async_get_numeric_state(hass, entity_id)


async def async_get_tank_level(
    hass: HomeAssistant, entity_id: str | None
) -> float | None:
    """Get tank fill level.
    
    Can be in liters or percentage depending on the sensor.
    The caller should check the unit_of_measurement attribute.
    
    Args:
        hass: Home Assistant instance
        entity_id: Tank level sensor entity ID
        
    Returns:
        Tank level value or None
    """
    return await async_get_numeric_state(hass, entity_id)


async def async_get_range(
    hass: HomeAssistant, entity_id: str | None
) -> float | None:
    """Get remaining range in kilometers.
    
    Args:
        hass: Home Assistant instance
        entity_id: Range sensor entity ID
        
    Returns:
        Range in km or None
    """
    return await async_get_numeric_state(hass, entity_id)


async def async_get_vehicle_data(
    hass: HomeAssistant,
    odometer_entity: str | None,
    tank_level_entity: str | None,
    range_entity: str | None,
    position_entity: str | None,
) -> dict[str, Any]:
    """Get all vehicle data from configured entities.
    
    Args:
        hass: Home Assistant instance
        odometer_entity: Odometer entity ID
        tank_level_entity: Tank level entity ID
        range_entity: Range entity ID
        position_entity: Position device_tracker entity ID
        
    Returns:
        Dictionary with vehicle data (None for unavailable values)
    """
    odometer = await async_get_odometer(hass, odometer_entity)
    tank_level = await async_get_tank_level(hass, tank_level_entity)
    range_km = await async_get_range(hass, range_entity)
    coordinates = await async_get_device_tracker_coordinates(hass, position_entity)
    
    # Get tank level unit to know if it's percentage or liters
    tank_level_unit = None
    if tank_level_entity:
        state = await async_get_entity_state(hass, tank_level_entity)
        if state:
            tank_level_unit = state.attributes.get("unit_of_measurement")
    
    return {
        "odometer_km": odometer,
        "tank_level": tank_level,
        "tank_level_unit": tank_level_unit,
        "range_km": range_km,
        "latitude": coordinates[0] if coordinates else None,
        "longitude": coordinates[1] if coordinates else None,
    }
