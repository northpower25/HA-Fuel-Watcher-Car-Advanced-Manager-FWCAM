"""Switch platform for haFWCMA integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ENTITY_DATA_SOURCE,
    ATTR_ENTITY_DEPENDENCIES,
    ATTR_ENTITY_DOCUMENTATION_URL,
    ATTR_ENTITY_PURPOSE,
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
from .entity_metadata import get_entity_metadata

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
        TripTrackingSwitch(coordinator, config_entry, vehicle_name, hass),
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
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attributes = {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("proximity_alerts_switch")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes
    
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


class TripTrackingSwitch(SwitchEntity):
    """Switch to enable/disable trip tracking (Fahrtenbuch)."""
    
    _attr_icon = "mdi:book-open-variant"
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
        self._attr_name = "Trip Tracking"
        self._attr_unique_id = f"{config_entry.entry_id}_trip_tracking"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    def _has_coordinator_data(self) -> bool:
        """Check if coordinator and its data are available."""
        return (
            self._coordinator is not None
            and hasattr(self._coordinator, "data")
            and self._coordinator.data is not None
        )
    
    @property
    def is_on(self) -> bool:
        """Return true if trip tracking is enabled."""
        if self._has_coordinator_data():
            config = self._coordinator.data.get("trip_tracking_config", {})
            return config.get("enabled", False)
        return False
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attributes = {}
        
        if self._has_coordinator_data():
            config = self._coordinator.data.get("trip_tracking_config", {})
            stats = self._coordinator.data.get("trip_statistics", {})
            
            attributes.update({
                "privacy_notice_accepted": config.get("privacy_notice_accepted", False),
                "last_enabled_at": config.get("last_enabled_at"),
                "last_disabled_at": config.get("last_disabled_at"),
                "total_trips": stats.get("total_trips", 0),
                "total_distance_km": round(stats.get("total_distance_km", 0.0), 2),
                "business_trips": stats.get("business_trips", 0),
                "private_trips": stats.get("private_trips", 0),
                "commute_trips": stats.get("commute_trips", 0),
            })
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("trip_tracking_switch")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on trip tracking."""
        from .utils import storage
        
        _LOGGER.info("Enabling trip tracking")
        
        # Load storage data
        data = await storage.load_data(self._hass, self._config_entry)
        
        # Update config
        config = data.get("trip_tracking_config", {})
        config["enabled"] = True
        config["last_enabled_at"] = dt_util.now().isoformat()
        
        # Accept privacy notice on first enable
        if not config.get("privacy_notice_accepted"):
            config["privacy_notice_accepted"] = True
            config["privacy_notice_accepted_at"] = dt_util.now().isoformat()
            _LOGGER.info("Privacy notice accepted for trip tracking")
        
        data["trip_tracking_config"] = config
        
        # Save to storage
        await storage.save_data(self._hass, self._config_entry, data)
        
        # Update coordinator data
        if self._has_coordinator_data():
            self._coordinator.data["trip_tracking_config"] = config
            self._coordinator.async_update_listeners()
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off trip tracking."""
        from .utils import storage
        
        _LOGGER.info("Disabling trip tracking")
        
        # Load storage data
        data = await storage.load_data(self._hass, self._config_entry)
        
        # Update config
        config = data.get("trip_tracking_config", {})
        config["enabled"] = False
        config["last_disabled_at"] = dt_util.now().isoformat()
        data["trip_tracking_config"] = config
        
        # Save to storage
        await storage.save_data(self._hass, self._config_entry, data)
        
        # Update coordinator data
        if self._has_coordinator_data():
            self._coordinator.data["trip_tracking_config"] = config
            self._coordinator.async_update_listeners()

