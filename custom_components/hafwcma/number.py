"""Number platform for haFWCMA integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_RADIUS,
    CONF_VEHICLE_NAME,
    DEFAULT_RADIUS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up haFWCMA number entities from a config entry.
    
    Args:
        hass: Home Assistant instance
        config_entry: Config entry for this integration
        async_add_entities: Callback to add number entities
    """
    _LOGGER.info("Setting up haFWCMA number entities")

    vehicle_name = config_entry.data.get(CONF_VEHICLE_NAME, "Vehicle")
    
    # Get coordinator from hass.data
    coordinator = hass.data[DOMAIN][config_entry.entry_id].get("coordinator")

    numbers = [
        SearchRadiusNumber(coordinator, config_entry, vehicle_name, hass),
    ]

    async_add_entities(numbers)


class SearchRadiusNumber(NumberEntity):
    """Number entity for configurable search radius."""

    _attr_icon = "mdi:radius"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 1.0
    _attr_native_max_value = 25.0
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS

    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the number entity.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
            hass: Home Assistant instance
        """
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._hass = hass
        self._attr_name = f"{vehicle_name} Search Radius"
        self._attr_unique_id = f"{config_entry.entry_id}_search_radius"

    @property
    def native_value(self) -> float:
        """Return the current search radius."""
        options = self._config_entry.options
        config = self._config_entry.data
        return options.get(CONF_RADIUS) or config.get(CONF_RADIUS, DEFAULT_RADIUS)

    async def async_set_native_value(self, value: float) -> None:
        """Update the search radius."""
        _LOGGER.info("Updating search radius to %.1f km", value)
        
        # Update the config entry options
        new_options = dict(self._config_entry.options)
        new_options[CONF_RADIUS] = value
        
        self._hass.config_entries.async_update_entry(
            self._config_entry,
            options=new_options,
        )
        
        # Trigger coordinator refresh to use new radius
        if self._coordinator:
            await self._coordinator.async_request_refresh()
