"""Switch platform for haFWCMA integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_PROXIMITY_ALERTS_ENABLED,
    CONF_TELEGRAM_CHAT_ID,
    CONF_TELEGRAM_METHOD,
    CONF_TELEGRAM_TOKEN,
    CONF_VEHICLE_NAME,
    DEFAULT_PROXIMITY_ALERTS_ENABLED,
    DOMAIN,
    TELEGRAM_METHOD_DIRECT_API,
    TELEGRAM_METHOD_INTEGRATION,
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
        ProximityAlertsSwitch(coordinator, config_entry, vehicle_name, hass),
    ]

    async_add_entities(switches)


class ProximityAlertsSwitch(SwitchEntity):
    """Switch to enable/disable proximity alerts for cheap stations."""
    
    _attr_icon = "mdi:bell-alert"
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the switch."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._hass = hass
        self._attr_name = "Proximity Alerts"
        self._attr_unique_id = f"{config_entry.entry_id}_proximity_alerts"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    @property
    def is_on(self) -> bool:
        """Return true if proximity alerts are enabled."""
        options = self._config_entry.options
        return options.get(CONF_PROXIMITY_ALERTS_ENABLED, DEFAULT_PROXIMITY_ALERTS_ENABLED)
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on proximity alerts."""
        _LOGGER.info("Enabling proximity alerts")
        new_options = dict(self._config_entry.options)
        new_options[CONF_PROXIMITY_ALERTS_ENABLED] = True
        self._hass.config_entries.async_update_entry(self._config_entry, options=new_options)
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off proximity alerts."""
        _LOGGER.info("Disabling proximity alerts")
        new_options = dict(self._config_entry.options)
        new_options[CONF_PROXIMITY_ALERTS_ENABLED] = False
        self._hass.config_entries.async_update_entry(self._config_entry, options=new_options)

