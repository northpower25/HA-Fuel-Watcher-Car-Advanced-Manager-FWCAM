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
    ATTR_ENTITY_DATA_SOURCE,
    ATTR_ENTITY_DEPENDENCIES,
    ATTR_ENTITY_DOCUMENTATION_URL,
    ATTR_ENTITY_PURPOSE,
    CONF_CHEAP_STATIONS_COUNT,
    CONF_CHEAP_STATIONS_RADIUS,
    CONF_CHEAP_NEAR_STATIONS_RADIUS,
    CONF_CONSUMPTION_MIN_DATA_POINTS,
    CONF_CONSUMPTION_PREDICTION_INTERVAL,
    CONF_MIN_TANK_LEVEL_FOR_ALERTS,
    CONF_PROXIMITY_ALERT_DISTANCE,
    CONF_UPDATE_INTERVAL,
    CONF_VEHICLE_NAME,
    DEFAULT_CHEAP_STATIONS_COUNT,
    DEFAULT_CHEAP_STATIONS_RADIUS,
    DEFAULT_CHEAP_NEAR_STATIONS_RADIUS,
    DEFAULT_CONSUMPTION_MIN_DATA_POINTS,
    DEFAULT_CONSUMPTION_PREDICTION_INTERVAL,
    DEFAULT_MIN_TANK_LEVEL_FOR_ALERTS,
    DEFAULT_PROXIMITY_ALERT_DISTANCE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_CHEAP_STATIONS_COUNT,
    MAX_CHEAP_STATIONS_RADIUS,
    MAX_CHEAP_NEAR_STATIONS_RADIUS,
    MAX_CONSUMPTION_MIN_DATA_POINTS,
    MAX_CONSUMPTION_PREDICTION_INTERVAL,
    MAX_PROXIMITY_ALERT_DISTANCE,
    MAX_UPDATE_INTERVAL,
    MIN_CHEAP_STATIONS_COUNT,
    MIN_CHEAP_STATIONS_RADIUS,
    MIN_CHEAP_NEAR_STATIONS_RADIUS,
    MIN_CONSUMPTION_MIN_DATA_POINTS,
    MIN_CONSUMPTION_PREDICTION_INTERVAL,
    MIN_PROXIMITY_ALERT_DISTANCE,
    MIN_UPDATE_INTERVAL,
)
from .entity_metadata import get_entity_metadata

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
        UpdateIntervalNumber(coordinator, config_entry, vehicle_name, hass),
        ConsumptionMinDataPointsNumber(coordinator, config_entry, vehicle_name, hass),
        ConsumptionPredictionIntervalNumber(coordinator, config_entry, vehicle_name, hass),
        ProximityAlertDistanceNumber(coordinator, config_entry, vehicle_name, hass),
        CheapStationsCountNumber(coordinator, config_entry, vehicle_name, hass),
        CheapStationsRadiusNumber(coordinator, config_entry, vehicle_name, hass),
        CheapNearStationsRadiusNumber(coordinator, config_entry, vehicle_name, hass),
        MinTankLevelForAlertsNumber(coordinator, config_entry, vehicle_name, hass),
    ]

    async_add_entities(numbers)


class UpdateIntervalNumber(NumberEntity):
    """Number entity for configurable API update interval."""

    _attr_icon = "mdi:timer-outline"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = float(MIN_UPDATE_INTERVAL)
    _attr_native_max_value = float(MAX_UPDATE_INTERVAL)
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = "min"
    _attr_has_entity_name = True

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
        self._attr_name = "API Update Interval"
        self._attr_unique_id = f"{config_entry.entry_id}_update_interval"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    @property
    def native_value(self) -> float:
        """Return the current update interval in minutes."""
        options = self._config_entry.options
        config = self._config_entry.data
        return float(
            options.get(CONF_UPDATE_INTERVAL)
            or config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the API update interval."""
        _LOGGER.info("Updating API update interval to %.0f minutes", value)
        
        # Update the config entry options
        new_options = dict(self._config_entry.options)
        new_options[CONF_UPDATE_INTERVAL] = int(value)
        
        # Update entry - this will trigger the update listener (async_update_options)
        # which will update the coordinator with new interval automatically
        self._hass.config_entries.async_update_entry(
            self._config_entry,
            options=new_options,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with entity metadata."""
        attributes = {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("api_update_interval_number")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class ConsumptionMinDataPointsNumber(NumberEntity):
    """Number entity for minimum data points required for consumption prediction."""

    _attr_icon = "mdi:database"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = float(MIN_CONSUMPTION_MIN_DATA_POINTS)
    _attr_native_max_value = float(MAX_CONSUMPTION_MIN_DATA_POINTS)
    _attr_native_step = 1.0
    _attr_has_entity_name = True

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
        self._attr_name = "Consumption Min Data Points"
        self._attr_unique_id = f"{config_entry.entry_id}_consumption_min_data_points"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    @property
    def native_value(self) -> float:
        """Return the current minimum data points setting."""
        options = self._config_entry.options
        config = self._config_entry.data
        return float(
            options.get(CONF_CONSUMPTION_MIN_DATA_POINTS)
            or config.get(CONF_CONSUMPTION_MIN_DATA_POINTS, DEFAULT_CONSUMPTION_MIN_DATA_POINTS)
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the minimum data points setting."""
        _LOGGER.info("Updating consumption min data points to %d", int(value))
        
        # Update the config entry options
        new_options = dict(self._config_entry.options)
        new_options[CONF_CONSUMPTION_MIN_DATA_POINTS] = int(value)
        
        # Update entry - this will trigger the update listener (async_update_options)
        # which will refresh entities automatically
        self._hass.config_entries.async_update_entry(
            self._config_entry,
            options=new_options,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with entity metadata."""
        attributes = {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("consumption_min_data_points_number")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class ConsumptionPredictionIntervalNumber(NumberEntity):
    """Number entity for consumption prediction calculation interval."""

    _attr_icon = "mdi:clock-time-eight-outline"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_CONSUMPTION_PREDICTION_INTERVAL
    _attr_native_max_value = MAX_CONSUMPTION_PREDICTION_INTERVAL
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = "h"
    _attr_has_entity_name = True

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
        self._attr_name = "Consumption Prediction Interval"
        self._attr_unique_id = f"{config_entry.entry_id}_consumption_prediction_interval"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    @property
    def native_value(self) -> float:
        """Return the current prediction interval in hours."""
        options = self._config_entry.options
        config = self._config_entry.data
        return float(
            options.get(CONF_CONSUMPTION_PREDICTION_INTERVAL)
            or config.get(CONF_CONSUMPTION_PREDICTION_INTERVAL, DEFAULT_CONSUMPTION_PREDICTION_INTERVAL)
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the prediction interval."""
        _LOGGER.info("Updating consumption prediction interval to %.1f hours", value)
        
        # Update the config entry options
        new_options = dict(self._config_entry.options)
        new_options[CONF_CONSUMPTION_PREDICTION_INTERVAL] = value
        
        # Update entry - this will trigger the update listener (async_update_options)
        # which will refresh entities automatically
        self._hass.config_entries.async_update_entry(
            self._config_entry,
            options=new_options,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with entity metadata."""
        attributes = {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("consumption_prediction_interval_number")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes



class ProximityAlertDistanceNumber(NumberEntity):
    """Number entity for proximity alert distance threshold."""
    
    _attr_icon = "mdi:map-marker-distance"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_PROXIMITY_ALERT_DISTANCE
    _attr_native_max_value = MAX_PROXIMITY_ALERT_DISTANCE
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the number entity."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._hass = hass
        self._attr_name = "Proximity Alert Distance"
        self._attr_unique_id = f"{config_entry.entry_id}_proximity_alert_distance"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    @property
    def native_value(self) -> float:
        """Return the current proximity alert distance."""
        options = self._config_entry.options
        return float(options.get(CONF_PROXIMITY_ALERT_DISTANCE, DEFAULT_PROXIMITY_ALERT_DISTANCE))
    
    async def async_set_native_value(self, value: float) -> None:
        """Update the proximity alert distance."""
        _LOGGER.info("Updating proximity alert distance to %.1f km", value)
        new_options = dict(self._config_entry.options)
        new_options[CONF_PROXIMITY_ALERT_DISTANCE] = value
        self._hass.config_entries.async_update_entry(self._config_entry, options=new_options)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with entity metadata."""
        attributes = {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("proximity_alert_distance_number")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class CheapStationsCountNumber(NumberEntity):
    """Number entity for number of cheap stations to track."""
    
    _attr_icon = "mdi:counter"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = float(MIN_CHEAP_STATIONS_COUNT)
    _attr_native_max_value = float(MAX_CHEAP_STATIONS_COUNT)
    _attr_native_step = 1.0
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the number entity."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._hass = hass
        self._attr_name = "Cheap Stations Count"
        self._attr_unique_id = f"{config_entry.entry_id}_cheap_stations_count"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    @property
    def native_value(self) -> float:
        """Return the current cheap stations count."""
        options = self._config_entry.options
        return float(options.get(CONF_CHEAP_STATIONS_COUNT, DEFAULT_CHEAP_STATIONS_COUNT))
    
    async def async_set_native_value(self, value: float) -> None:
        """Update the cheap stations count."""
        _LOGGER.info("Updating cheap stations count to %d", int(value))
        new_options = dict(self._config_entry.options)
        new_options[CONF_CHEAP_STATIONS_COUNT] = int(value)
        self._hass.config_entries.async_update_entry(self._config_entry, options=new_options)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with entity metadata."""
        attributes = {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("cheap_stations_count_number")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class CheapStationsRadiusNumber(NumberEntity):
    """Number entity for cheap stations search radius."""
    
    _attr_icon = "mdi:radius-outline"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_CHEAP_STATIONS_RADIUS
    _attr_native_max_value = MAX_CHEAP_STATIONS_RADIUS
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the number entity."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._hass = hass
        self._attr_name = "Cheap Stations Radius"
        self._attr_unique_id = f"{config_entry.entry_id}_cheap_stations_radius"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    @property
    def native_value(self) -> float:
        """Return the current cheap stations radius."""
        options = self._config_entry.options
        return float(options.get(CONF_CHEAP_STATIONS_RADIUS, DEFAULT_CHEAP_STATIONS_RADIUS))
    
    async def async_set_native_value(self, value: float) -> None:
        """Update the cheap stations radius."""
        _LOGGER.info("Updating cheap stations radius to %.1f km", value)
        new_options = dict(self._config_entry.options)
        new_options[CONF_CHEAP_STATIONS_RADIUS] = value
        self._hass.config_entries.async_update_entry(self._config_entry, options=new_options)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with entity metadata."""
        attributes = {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("cheap_stations_radius_number")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class CheapNearStationsRadiusNumber(NumberEntity):
    """Number entity for cheap near stations search radius (for near vs far comparison)."""
    
    _attr_icon = "mdi:map-marker-radius"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_CHEAP_NEAR_STATIONS_RADIUS
    _attr_native_max_value = MAX_CHEAP_NEAR_STATIONS_RADIUS
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the number entity."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._hass = hass
        self._attr_name = "Cheap Near Stations Radius"
        self._attr_unique_id = f"{config_entry.entry_id}_cheap_near_stations_radius"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    @property
    def native_value(self) -> float:
        """Return the current cheap near stations radius."""
        options = self._config_entry.options
        return float(options.get(CONF_CHEAP_NEAR_STATIONS_RADIUS, DEFAULT_CHEAP_NEAR_STATIONS_RADIUS))
    
    async def async_set_native_value(self, value: float) -> None:
        """Update the cheap near stations radius."""
        _LOGGER.info("Updating cheap near stations radius to %.1f km", value)
        new_options = dict(self._config_entry.options)
        new_options[CONF_CHEAP_NEAR_STATIONS_RADIUS] = value
        self._hass.config_entries.async_update_entry(self._config_entry, options=new_options)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with entity metadata."""
        attributes = {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("cheap_near_stations_radius_number")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class MinTankLevelForAlertsNumber(NumberEntity):
    """Number entity for minimum tank level threshold for proximity alerts."""
    
    _attr_icon = "mdi:gauge-empty"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 5.0
    _attr_native_unit_of_measurement = "%"
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the number entity."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._hass = hass
        self._attr_name = "Min Tank Level For Alerts"
        self._attr_unique_id = f"{config_entry.entry_id}_min_tank_level_for_alerts"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    @property
    def native_value(self) -> float:
        """Return the current minimum tank level for alerts."""
        options = self._config_entry.options
        return float(options.get(CONF_MIN_TANK_LEVEL_FOR_ALERTS, DEFAULT_MIN_TANK_LEVEL_FOR_ALERTS))
    
    async def async_set_native_value(self, value: float) -> None:
        """Update the minimum tank level for alerts."""
        _LOGGER.info("Updating min tank level for alerts to %.0f%%", value)
        new_options = dict(self._config_entry.options)
        new_options[CONF_MIN_TANK_LEVEL_FOR_ALERTS] = value
        self._hass.config_entries.async_update_entry(self._config_entry, options=new_options)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with entity metadata."""
        attributes = {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("min_tank_level_for_alerts_number")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes
