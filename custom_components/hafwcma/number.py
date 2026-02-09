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
    CONF_CONSUMPTION_MIN_DATA_POINTS,
    CONF_CONSUMPTION_PREDICTION_INTERVAL,
    CONF_RADIUS,
    CONF_UPDATE_INTERVAL,
    CONF_VEHICLE_NAME,
    DEFAULT_CONSUMPTION_MIN_DATA_POINTS,
    DEFAULT_CONSUMPTION_PREDICTION_INTERVAL,
    DEFAULT_RADIUS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_CONSUMPTION_MIN_DATA_POINTS,
    MAX_CONSUMPTION_PREDICTION_INTERVAL,
    MAX_UPDATE_INTERVAL,
    MIN_CONSUMPTION_MIN_DATA_POINTS,
    MIN_CONSUMPTION_PREDICTION_INTERVAL,
    MIN_UPDATE_INTERVAL,
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
        UpdateIntervalNumber(coordinator, config_entry, vehicle_name, hass),
        ConsumptionMinDataPointsNumber(coordinator, config_entry, vehicle_name, hass),
        ConsumptionPredictionIntervalNumber(coordinator, config_entry, vehicle_name, hass),
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
        
        # Update entry - this will trigger the update listener (async_update_options)
        # which will update the coordinator and refresh entities
        self._hass.config_entries.async_update_entry(
            self._config_entry,
            options=new_options,
        )
        
        # Schedule state update to reflect new value immediately
        self.async_schedule_update_ha_state()


class UpdateIntervalNumber(NumberEntity):
    """Number entity for configurable API update interval."""

    _attr_icon = "mdi:timer-outline"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = float(MIN_UPDATE_INTERVAL)
    _attr_native_max_value = float(MAX_UPDATE_INTERVAL)
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = "min"

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
        self._attr_name = f"{vehicle_name} API Update Interval"
        self._attr_unique_id = f"{config_entry.entry_id}_update_interval"

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
        # which will update the coordinator with new interval
        self._hass.config_entries.async_update_entry(
            self._config_entry,
            options=new_options,
        )
        
        # Schedule state update to reflect new value immediately
        self.async_schedule_update_ha_state()


class ConsumptionMinDataPointsNumber(NumberEntity):
    """Number entity for minimum data points required for consumption prediction."""

    _attr_icon = "mdi:database"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = float(MIN_CONSUMPTION_MIN_DATA_POINTS)
    _attr_native_max_value = float(MAX_CONSUMPTION_MIN_DATA_POINTS)
    _attr_native_step = 1.0

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
        self._attr_name = f"{vehicle_name} Consumption Min Data Points"
        self._attr_unique_id = f"{config_entry.entry_id}_consumption_min_data_points"

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
        self._hass.config_entries.async_update_entry(
            self._config_entry,
            options=new_options,
        )
        
        # Schedule state update to reflect new value immediately
        self.async_schedule_update_ha_state()


class ConsumptionPredictionIntervalNumber(NumberEntity):
    """Number entity for consumption prediction calculation interval."""

    _attr_icon = "mdi:clock-time-eight-outline"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_CONSUMPTION_PREDICTION_INTERVAL
    _attr_native_max_value = MAX_CONSUMPTION_PREDICTION_INTERVAL
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = "h"

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
        self._attr_name = f"{vehicle_name} Consumption Prediction Interval"
        self._attr_unique_id = f"{config_entry.entry_id}_consumption_prediction_interval"

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
        self._hass.config_entries.async_update_entry(
            self._config_entry,
            options=new_options,
        )
        
        # Schedule state update to reflect new value immediately
        self.async_schedule_update_ha_state()

