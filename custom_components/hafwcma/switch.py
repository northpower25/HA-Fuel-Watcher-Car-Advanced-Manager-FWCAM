"""Switch platform for haFWCMA integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_VEHICLE_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up haFWCMA switch entities from a config entry.
    
    Args:
        hass: Home Assistant instance
        config_entry: Config entry for this integration
        async_add_entities: Callback to add switch entities
    """
    _LOGGER.info("Setting up haFWCMA switches")

    vehicle_name = config_entry.data.get(CONF_VEHICLE_NAME, "Vehicle")
    
    # Get coordinator from hass.data
    coordinator = hass.data[DOMAIN][config_entry.entry_id].get("coordinator")

    switches = [
        ManualRefreshSwitch(coordinator, config_entry, vehicle_name),
    ]

    async_add_entities(switches)


class ManualRefreshSwitch(SwitchEntity):
    """Switch to manually trigger fuel price data refresh."""

    _attr_icon = "mdi:refresh"

    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
    ) -> None:
        """Initialize the switch.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
        """
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._attr_name = f"{vehicle_name} Manual Refresh"
        self._attr_unique_id = f"{config_entry.entry_id}_manual_refresh"
        self._attr_is_on = False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch - trigger manual refresh."""
        _LOGGER.info("Manual refresh triggered")
        self._attr_is_on = True
        self.async_write_ha_state()
        
        # Request coordinator to refresh data
        if self._coordinator:
            await self._coordinator.async_request_refresh()
        
        # Auto turn off after refresh
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch - does nothing as it auto-turns off."""
        self._attr_is_on = False
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self._coordinator and hasattr(self._coordinator, "last_update_success"):
            attrs = {
                "last_update_success": self._coordinator.last_update_success,
            }
            # Add last update time if coordinator has the data
            if hasattr(self._coordinator, "last_update_time"):
                attrs["last_update_time"] = self._coordinator.last_update_time
            return attrs
        return {}
