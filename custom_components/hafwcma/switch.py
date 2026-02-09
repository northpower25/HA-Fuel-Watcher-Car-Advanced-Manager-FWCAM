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
        ManualPredictionSwitch(coordinator, config_entry, vehicle_name),
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


class ManualPredictionSwitch(SwitchEntity):
    """Switch to manually trigger range/consumption prediction calculation."""

    _attr_icon = "mdi:chart-line"

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
        self._attr_name = f"{vehicle_name} Manual Prediction"
        self._attr_unique_id = f"{config_entry.entry_id}_manual_prediction"
        self._attr_is_on = False
        self._last_prediction_time = None
        self._last_prediction_result = None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch - trigger manual prediction."""
        _LOGGER.info("Manual prediction triggered")
        self._attr_is_on = True
        self.async_write_ha_state()
        
        # Force a consumption prediction update
        if self._coordinator:
            try:
                from datetime import datetime
                from .utils.consumption_prediction import predict_days_until_refuel, store_prediction_result
                from .utils.statistics_engine import get_average_consumption_rate
                from .const import (
                    CONF_CONSUMPTION_MIN_DATA_POINTS,
                    CONF_FALLBACK_DAILY_KM,
                    CONF_TANK_CAPACITY,
                    DEFAULT_CONSUMPTION_MIN_DATA_POINTS,
                    DEFAULT_FALLBACK_DAILY_KM,
                    DEFAULT_TANK_CAPACITY,
                )
                
                # Get current data
                vehicle_data = self._coordinator.data.get("vehicle_data", {})
                options = self._config_entry.options
                config = self._config_entry.data
                
                range_km = vehicle_data.get("range_km")
                tank_level = vehicle_data.get("tank_level")
                tank_capacity = options.get(CONF_TANK_CAPACITY) or config.get(CONF_TANK_CAPACITY, DEFAULT_TANK_CAPACITY)
                fallback_daily_km = options.get(CONF_FALLBACK_DAILY_KM) or config.get(CONF_FALLBACK_DAILY_KM, DEFAULT_FALLBACK_DAILY_KM)
                min_data_points = options.get(CONF_CONSUMPTION_MIN_DATA_POINTS) or config.get(CONF_CONSUMPTION_MIN_DATA_POINTS, DEFAULT_CONSUMPTION_MIN_DATA_POINTS)
                
                # Get average consumption rate
                fallback_consumption_rate = await get_average_consumption_rate(
                    self._coordinator.hass,
                    self._config_entry,
                    fallback=7.0,
                )
                
                # Run prediction
                prediction = await predict_days_until_refuel(
                    self._coordinator.hass,
                    self._config_entry,
                    current_range_km=range_km,
                    current_tank_level=tank_level,
                    tank_capacity=tank_capacity,
                    fallback_daily_km=fallback_daily_km,
                    fallback_consumption_rate=fallback_consumption_rate,
                    min_data_points=int(min_data_points),
                )
                
                # Store result
                await store_prediction_result(self._coordinator.hass, self._config_entry, prediction)
                
                self._last_prediction_time = datetime.now().isoformat()
                self._last_prediction_result = prediction
                
                _LOGGER.info("Manual prediction completed: %s", prediction)
                
                # Request coordinator refresh to update sensors
                await self._coordinator.async_request_refresh()
                
            except Exception as err:
                _LOGGER.error("Error during manual prediction: %s", err, exc_info=True)
                self._last_prediction_result = {"error": str(err)}
        
        # Auto turn off after prediction
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch - does nothing as it auto-turns off."""
        self._attr_is_on = False
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = {}
        if self._last_prediction_time:
            attrs["last_prediction_time"] = self._last_prediction_time
        if self._last_prediction_result:
            attrs["last_prediction_result"] = self._last_prediction_result
        return attrs
