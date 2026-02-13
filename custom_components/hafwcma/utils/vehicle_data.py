"""Utility functions for reading vehicle entity data."""
from __future__ import annotations

import asyncio
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
    hass: HomeAssistant, entity_id: str | None, silent: bool = False
) -> State | None:
    """Get the state of an entity.
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to get state for
        silent: If True, suppress warning logs when entity not found
        
    Returns:
        State object or None if entity doesn't exist or is not provided
    """
    if not entity_id:
        return None
        
    state = hass.states.get(entity_id)
    if not state:
        if not silent:
            _LOGGER.warning("Entity %s not found", entity_id)
        else:
            _LOGGER.debug("Entity %s not found (silent mode)", entity_id)
        return None
        
    return state


async def async_get_numeric_state(
    hass: HomeAssistant, entity_id: str | None, default: float | None = None, silent: bool = False
) -> float | None:
    """Get numeric state value from an entity.
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to read
        default: Default value if entity unavailable or invalid
        silent: If True, suppress warning logs when entity not found
        
    Returns:
        Numeric value or default
    """
    state = await async_get_entity_state(hass, entity_id, silent=silent)
    
    if not state:
        return default
        
    if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        _LOGGER.debug("Entity %s has invalid state: %s", entity_id, state.state)
        return default
        
    try:
        return float(state.state)
    except (ValueError, TypeError):
        if not silent:
            _LOGGER.warning(
                "Could not convert state of %s to float: %s", entity_id, state.state
            )
        return default


async def async_get_device_tracker_coordinates(
    hass: HomeAssistant, entity_id: str | None, silent: bool = False
) -> tuple[float, float] | None:
    """Get coordinates from a device_tracker entity.
    
    Handles both cases:
    - State contains coordinates (latitude, longitude)
    - State contains zone name (home, away, etc.) - use attributes
    
    Args:
        hass: Home Assistant instance
        entity_id: Device tracker entity ID
        silent: If True, suppress warning logs when entity not found
        
    Returns:
        Tuple of (latitude, longitude) or None if unavailable
    """
    state = await async_get_entity_state(hass, entity_id, silent=silent)
    
    if not state:
        return None
        
    if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        _LOGGER.debug("Device tracker %s has invalid state: %s", entity_id, state.state)
        return None
    
    # Try to get coordinates from attributes first (most reliable)
    latitude = state.attributes.get(ATTR_LATITUDE)
    longitude = state.attributes.get(ATTR_LONGITUDE)
    
    _LOGGER.debug(
        "Device tracker %s: state=%s, lat=%s, lon=%s, attributes=%s",
        entity_id,
        state.state,
        latitude,
        longitude,
        state.attributes.keys() if state.attributes else None,
    )
    
    if latitude is not None and longitude is not None:
        try:
            return (float(latitude), float(longitude))
        except (ValueError, TypeError):
            if not silent:
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
    hass: HomeAssistant, entity_id: str | None, silent: bool = False
) -> float | None:
    """Get odometer reading in kilometers.
    
    Args:
        hass: Home Assistant instance
        entity_id: Odometer sensor entity ID
        silent: If True, suppress warning logs when entity not found
        
    Returns:
        Odometer reading in km or None
    """
    return await async_get_numeric_state(hass, entity_id, silent=silent)


async def async_get_tank_level(
    hass: HomeAssistant, entity_id: str | None, silent: bool = False
) -> float | None:
    """Get tank fill level.
    
    Can be in liters or percentage depending on the sensor.
    The caller should check the unit_of_measurement attribute.
    
    Args:
        hass: Home Assistant instance
        entity_id: Tank level sensor entity ID
        silent: If True, suppress warning logs when entity not found
        
    Returns:
        Tank level value or None
    """
    return await async_get_numeric_state(hass, entity_id, silent=silent)


async def async_get_range(
    hass: HomeAssistant, entity_id: str | None, silent: bool = False
) -> float | None:
    """Get remaining range in kilometers.
    
    Args:
        hass: Home Assistant instance
        entity_id: Range sensor entity ID
        silent: If True, suppress warning logs when entity not found
        
    Returns:
        Range in km or None
    """
    return await async_get_numeric_state(hass, entity_id, silent=silent)


async def async_get_vehicle_data(
    hass: HomeAssistant,
    odometer_entity: str | None,
    tank_level_entity: str | None,
    range_entity: str | None,
    position_entity: str | None,
    silent: bool = False,
) -> dict[str, Any]:
    """Get all vehicle data from configured entities.
    
    Args:
        hass: Home Assistant instance
        odometer_entity: Odometer entity ID
        tank_level_entity: Tank level entity ID
        range_entity: Range entity ID
        position_entity: Position device_tracker entity ID
        silent: If True, suppress warning logs when entities not found
        
    Returns:
        Dictionary with vehicle data (None for unavailable values)
    """
    odometer = await async_get_odometer(hass, odometer_entity, silent=silent)
    tank_level = await async_get_tank_level(hass, tank_level_entity, silent=silent)
    range_km = await async_get_range(hass, range_entity, silent=silent)
    coordinates = await async_get_device_tracker_coordinates(hass, position_entity, silent=silent)
    
    # Get tank level unit to know if it's percentage or liters
    tank_level_unit = None
    if tank_level_entity:
        state = await async_get_entity_state(hass, tank_level_entity, silent=silent)
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


async def async_wait_for_entities(
    hass: HomeAssistant,
    entity_ids: list[str],
    max_retries: int = 6,
    retry_delay: int = 30,
) -> bool:
    """Wait for vehicle entities to become available with retries.
    
    This function will check if at least one of the provided entities exists
    and retry if none are found. This is useful during Home Assistant startup
    when vehicle integrations may load after this integration.
    
    Args:
        hass: Home Assistant instance
        entity_ids: List of entity IDs to check (empty strings/None will be filtered out)
        max_retries: Maximum number of retries (default: 6)
        retry_delay: Seconds to wait between retries (default: 30)
        
    Returns:
        True if at least one entity is found, False if all retries exhausted
    """
    # Filter out None and empty strings
    entities_to_check = [e for e in entity_ids if e]
    
    if not entities_to_check:
        _LOGGER.debug("No vehicle entities configured to wait for")
        return True  # No entities configured is not an error
    
    for attempt in range(max_retries):
        # Check if at least one entity exists
        found_entities = []
        for entity_id in entities_to_check:
            state = hass.states.get(entity_id)
            if state is not None:
                found_entities.append(entity_id)
        
        if found_entities:
            _LOGGER.info(
                "Vehicle entities available after %d attempts (%.1f seconds): %s",
                attempt + 1,
                attempt * retry_delay,
                ", ".join(found_entities)
            )
            return True
        
        # Log the retry attempt
        if attempt < max_retries - 1:
            _LOGGER.info(
                "Waiting for vehicle entities to become available (attempt %d/%d, retrying in %d seconds)...",
                attempt + 1,
                max_retries,
                retry_delay
            )
            await asyncio.sleep(retry_delay)
        else:
            _LOGGER.warning(
                "Vehicle entities not found after %d attempts (%.1f seconds). "
                "Integration will continue but vehicle data may be unavailable. "
                "Entities checked: %s",
                max_retries,
                (max_retries - 1) * retry_delay,
                ", ".join(entities_to_check)
            )
    
    return False
