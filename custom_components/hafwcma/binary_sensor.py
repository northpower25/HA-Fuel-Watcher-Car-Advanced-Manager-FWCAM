"""Binary sensor platform for haFWCMA integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ALERT_MESSAGE,
    ATTR_BRAND,
    ATTR_DISTANCE,
    ATTR_FUEL_TYPE,
    ATTR_IS_OPEN,
    ATTR_NAVIGATION_URLS,
    ATTR_PRICE,
    ATTR_PROXIMITY_THRESHOLD_KM,
    ATTR_STATION_ADDRESS,
    ATTR_STATION_NAME,
    CONF_VEHICLE_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up haFWCMA binary sensors from a config entry.
    
    Args:
        hass: Home Assistant instance
        config_entry: Config entry for this integration
        async_add_entities: Callback to add binary sensor entities
    """
    _LOGGER.info("Setting up haFWCMA binary sensors")
    
    # Get the coordinator from hass.data
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    vehicle_name = config_entry.data.get(CONF_VEHICLE_NAME, "My Car")
    
    # Create binary sensors
    entities = [
        ProximityAlertSensor(coordinator, config_entry, vehicle_name),
    ]
    
    async_add_entities(entities, update_before_add=True)


class ProximityAlertSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for proximity alerts when near a cheap fuel station."""
    
    _attr_device_class = BinarySensorDeviceClass.PRESENCE
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
    ) -> None:
        """Initialize the proximity alert sensor.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
        """
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._vehicle_name = vehicle_name
        
        # Generate unique ID
        self._attr_unique_id = f"{config_entry.entry_id}_near_cheap_station"
        self._attr_name = "Near Cheap Station"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    @property
    def is_on(self) -> bool:
        """Return true if near a cheap station."""
        if not self.coordinator.data:
            return False
        
        proximity_data = self.coordinator.data.get("proximity_alert")
        if not proximity_data:
            return False
        
        return proximity_data.get("is_near", False)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {
                ATTR_STATION_NAME: "Keine günstige Tankstelle in der unmittelbaren Umgebung",
            }
        
        proximity_data = self.coordinator.data.get("proximity_alert")
        if not proximity_data or not proximity_data.get("is_near"):
            return {
                ATTR_STATION_NAME: "Keine günstige Tankstelle in der unmittelbaren Umgebung",
            }
        
        station = proximity_data.get("station", {})
        
        attributes = {
            ATTR_STATION_NAME: station.get("name"),
            ATTR_STATION_ADDRESS: station.get("address"),
            ATTR_DISTANCE: station.get("distance_km"),
            ATTR_PRICE: station.get("price"),
            ATTR_FUEL_TYPE: station.get("fuel_type"),
            ATTR_BRAND: station.get("brand"),
            ATTR_IS_OPEN: station.get("is_open"),
            ATTR_PROXIMITY_THRESHOLD_KM: proximity_data.get("threshold_km"),
            ATTR_NAVIGATION_URLS: station.get("navigation_urls", {}),
            ATTR_ALERT_MESSAGE: proximity_data.get("alert_message"),
        }
        
        # Filter out None values
        return {k: v for k, v in attributes.items() if v is not None}
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
