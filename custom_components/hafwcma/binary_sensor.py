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
    ATTR_ENTITY_DATA_SOURCE,
    ATTR_ENTITY_DEPENDENCIES,
    ATTR_ENTITY_DOCUMENTATION_URL,
    ATTR_ENTITY_PURPOSE,
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
from .entity_metadata import get_entity_metadata

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
        OnTripSensor(coordinator, config_entry, vehicle_name),
    ]
    
    # Add Telegram Bot status sensor if configured
    from .const import CONF_TELEGRAM_CHAT_ID, CONF_TELEGRAM_TOKEN
    telegram_chat_id = config_entry.data.get(CONF_TELEGRAM_CHAT_ID)
    telegram_token = config_entry.data.get(CONF_TELEGRAM_TOKEN)
    
    if telegram_chat_id and telegram_token:
        entities.append(TelegramBotStatusSensor(hass, config_entry, vehicle_name))
    
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
        """Return additional state attributes.
        
        Attributes are ordered according to FWCAM standard structure:
        1. Core metadata (data_source)
        2. Station information (when near)
        3. Alert configuration
        4. Config & documentation
        """
        if not self.coordinator.data:
            return {
                "data_source": "geolocation",
                "station_name": "Keine günstige Tankstelle in der unmittelbaren Umgebung",
            }
        
        proximity_data = self.coordinator.data.get("proximity_alert")
        if not proximity_data or not proximity_data.get("is_near"):
            return {
                "data_source": "geolocation",
                "station_name": "Keine günstige Tankstelle in der unmittelbaren Umgebung",
            }
        
        station = proximity_data.get("station", {})
        
        # Build attributes in standard order
        # 1. Core metadata
        attributes = {
            "data_source": "geolocation",
        }
        
        # 2. Station information (current alert)
        attributes.update({
            ATTR_STATION_NAME: station.get("name"),
            ATTR_STATION_ADDRESS: station.get("address"),
            ATTR_DISTANCE: station.get("distance_km"),
            ATTR_PRICE: station.get("price"),
            ATTR_FUEL_TYPE: station.get("fuel_type"),
            ATTR_BRAND: station.get("brand"),
            ATTR_IS_OPEN: station.get("is_open"),
        })
        
        # 3. Alert configuration and message
        attributes.update({
            ATTR_PROXIMITY_THRESHOLD_KM: proximity_data.get("threshold_km"),
            ATTR_ALERT_MESSAGE: proximity_data.get("alert_message"),
            ATTR_NAVIGATION_URLS: station.get("navigation_urls", {}),
        })
        
        # 4. Configuration & documentation metadata
        attributes["config_entry_id"] = self._config_entry.entry_id
        
        metadata = get_entity_metadata("proximity_alert_binary_sensor")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        # Filter out None values
        return {k: v for k, v in attributes.items() if v is not None}
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class OnTripSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor indicating if vehicle is currently on a trip."""
    
    _attr_device_class = None
    _attr_has_entity_name = True
    _attr_icon = "mdi:car-connected"
    
    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
    ) -> None:
        """Initialize the on-trip sensor.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
        """
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_name = "On Trip"
        self._attr_unique_id = f"{config_entry.entry_id}_on_trip"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    @property
    def is_on(self) -> bool:
        """Return true if vehicle is on a trip."""
        if not self.coordinator.data:
            return False
        
        trip_state = self.coordinator.data.get("trip_tracking_state", {})
        return trip_state.get("on_trip", False)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return trip state attributes.
        
        Attributes are ordered according to FWCAM standard structure:
        1. Core metadata (data_source, trip_tracking_enabled)
        2. Current trip information (if on trip)
        3. Config & documentation
        """
        if not self.coordinator.data:
            return {
                "data_source": "trip_tracking",
                "trip_tracking_enabled": False,
            }
        
        trip_state = self.coordinator.data.get("trip_tracking_state", {})
        trip_config = self.coordinator.data.get("trip_tracking_config", {})
        current_trip = trip_state.get("current_trip", {})
        
        # Build attributes in standard order
        # 1. Core metadata
        attributes = {
            "data_source": "trip_tracking",
            "trip_tracking_enabled": trip_config.get("enabled", False),
        }
        
        # 2. Current trip information (if on trip)
        if trip_state.get("on_trip", False):
            attributes.update({
                "timestamp_start": current_trip.get("timestamp_start"),
                "distance_km": round(current_trip.get("distance_km", 0), 2),
                "duration": current_trip.get("duration"),
                "duration_minutes": round(current_trip.get("duration_minutes", 0), 1),
            })
        
        # 3. Configuration & documentation metadata
        attributes["config_entry_id"] = self._config_entry.entry_id
        
        metadata = get_entity_metadata("on_trip_binary_sensor")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class TelegramBotStatusSensor(BinarySensorEntity):
    """Binary sensor indicating Telegram Bot connectivity status."""
    
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True
    
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        vehicle_name: str,
    ) -> None:
        """Initialize the Telegram bot status sensor.
        
        Args:
            hass: Home Assistant instance
            config_entry: Config entry
            vehicle_name: Name of the vehicle
        """
        self._hass = hass
        self._config_entry = config_entry
        self._vehicle_name = vehicle_name
        self._attr_unique_id = f"{config_entry.entry_id}_telegram_bot_status"
        self._attr_name = "Telegram Bot"
        
        # Device info for grouping with other entities
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    @property
    def is_on(self) -> bool:
        """Return true if the Telegram bot is available."""
        # Check if telegram_bot integration is loaded
        if "telegram_bot" not in self._hass.config.components:
            return False
        
        # Check if our handlers are initialized
        telegram_handler = self._hass.data.get(DOMAIN, {}).get(
            self._config_entry.entry_id, {}
        ).get("telegram_handler")
        
        telegram_refueling_handler = self._hass.data.get(DOMAIN, {}).get(
            self._config_entry.entry_id, {}
        ).get("telegram_refueling_handler")
        
        return telegram_handler is not None and telegram_refueling_handler is not None
    
    @property
    def icon(self) -> str:
        """Return icon based on status."""
        return "mdi:message-check" if self.is_on else "mdi:message-cog"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        from .const import CONF_TELEGRAM_CHAT_ID, CONF_TELEGRAM_METHOD
        
        attrs = {}
        
        # Show configuration status
        attrs["telegram_bot_integration"] = "telegram_bot" in self._hass.config.components
        attrs["chat_id_configured"] = bool(self._config_entry.data.get(CONF_TELEGRAM_CHAT_ID))
        
        method = self._config_entry.data.get(CONF_TELEGRAM_METHOD, "integration")
        attrs["telegram_method"] = method
        
        # Show handler status
        handlers_data = self._hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id, {})
        attrs["telegram_handler_active"] = handlers_data.get("telegram_handler") is not None
        attrs["refueling_handler_active"] = handlers_data.get("telegram_refueling_handler") is not None
        
        # Show pending refuelings if handler exists
        refueling_handler = handlers_data.get("telegram_refueling_handler")
        if refueling_handler:
            attrs["pending_refuelings"] = len(refueling_handler._pending_refuelings)
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("telegram_bot_status_binary_sensor")
        if metadata:
            attrs[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attrs[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attrs[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attrs[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attrs
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return True  # Always available to show status
