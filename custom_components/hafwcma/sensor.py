"""Sensor platform for haFWCMA integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    ATTR_DISTANCE,
    ATTR_FORECAST_TREND,
    ATTR_PRICE,
    ATTR_RANGE_KM,
    ATTR_STATION_ADDRESS,
    ATTR_STATION_NAME,
    ATTR_TANK_LEVEL,
    CONF_FUEL_TYPE,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_RADIUS,
    CONF_VEHICLE_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up haFWCMA sensors from a config entry.
    
    Args:
        hass: Home Assistant instance
        config_entry: Config entry for this integration
        async_add_entities: Callback to add sensor entities
    """
    _LOGGER.info("Setting up haFWCMA sensors")

    # TODO: Initialize coordinator with actual data fetching
    coordinator = HaFWCMACoordinator(hass, config_entry)
    await coordinator.async_config_entry_first_refresh()

    vehicle_name = config_entry.data.get(CONF_VEHICLE_NAME, "Vehicle")

    sensors = [
        FuelPriceSensor(coordinator, config_entry, vehicle_name),
        TankLevelSensor(coordinator, config_entry, vehicle_name),
        RangeSensor(coordinator, config_entry, vehicle_name),
        NearestStationSensor(coordinator, config_entry, vehicle_name),
    ]

    async_add_entities(sensors)


class HaFWCMACoordinator(DataUpdateCoordinator):
    """Coordinator to manage data updates for haFWCMA."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator.
        
        Args:
            hass: Home Assistant instance
            config_entry: Config entry with user settings
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.config_entry = config_entry

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from providers.
        
        Returns:
            Dictionary with updated sensor data
            
        Raises:
            UpdateFailed: If update fails
        """
        try:
            # TODO: Fetch data from Tankerkönig provider
            # TODO: Update vehicle tank level
            # TODO: Generate forecast
            # TODO: Calculate recommendations

            # Placeholder data structure
            data = {
                "fuel_price": 1.649,  # EUR per liter
                "tank_level": 35.0,  # liters
                "tank_percentage": 70.0,  # percent
                "range": 450.0,  # km
                "nearest_station": {
                    "name": "Example Station",
                    "address": "Main Street 1",
                    "distance": 2.5,
                    "price": 1.649,
                },
                "forecast_trend": "stable",
            }

            return data

        except Exception as err:
            _LOGGER.error("Error updating haFWCMA data: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err


class FuelPriceSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing current fuel price at nearest station."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = f"{CURRENCY_EURO}/L"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: HaFWCMACoordinator,
        config_entry: ConfigEntry,
        vehicle_name: str,
    ) -> None:
        """Initialize the sensor.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
        """
        super().__init__(coordinator)
        self._attr_name = f"{vehicle_name} Fuel Price"
        self._attr_unique_id = f"{config_entry.entry_id}_fuel_price"
        self._config_entry = config_entry

    @property
    def native_value(self) -> float | None:
        """Return the current fuel price."""
        return self.coordinator.data.get("fuel_price")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        station = self.coordinator.data.get("nearest_station", {})
        return {
            ATTR_STATION_NAME: station.get("name"),
            ATTR_STATION_ADDRESS: station.get("address"),
            ATTR_DISTANCE: station.get("distance"),
            ATTR_FORECAST_TREND: self.coordinator.data.get("forecast_trend"),
        }


class TankLevelSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing current tank level."""

    _attr_native_unit_of_measurement = "L"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:gas-station"

    def __init__(
        self,
        coordinator: HaFWCMACoordinator,
        config_entry: ConfigEntry,
        vehicle_name: str,
    ) -> None:
        """Initialize the sensor.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
        """
        super().__init__(coordinator)
        self._attr_name = f"{vehicle_name} Tank Level"
        self._attr_unique_id = f"{config_entry.entry_id}_tank_level"

    @property
    def native_value(self) -> float | None:
        """Return the current tank level."""
        return self.coordinator.data.get("tank_level")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            "percentage": self.coordinator.data.get("tank_percentage"),
        }


class RangeSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing estimated range."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:map-marker-distance"

    def __init__(
        self,
        coordinator: HaFWCMACoordinator,
        config_entry: ConfigEntry,
        vehicle_name: str,
    ) -> None:
        """Initialize the sensor.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
        """
        super().__init__(coordinator)
        self._attr_name = f"{vehicle_name} Range"
        self._attr_unique_id = f"{config_entry.entry_id}_range"

    @property
    def native_value(self) -> float | None:
        """Return the estimated range."""
        return self.coordinator.data.get("range")


class NearestStationSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing nearest fuel station."""

    _attr_icon = "mdi:gas-station"

    def __init__(
        self,
        coordinator: HaFWCMACoordinator,
        config_entry: ConfigEntry,
        vehicle_name: str,
    ) -> None:
        """Initialize the sensor.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
        """
        super().__init__(coordinator)
        self._attr_name = f"{vehicle_name} Nearest Station"
        self._attr_unique_id = f"{config_entry.entry_id}_nearest_station"

    @property
    def native_value(self) -> str | None:
        """Return the name of nearest station."""
        station = self.coordinator.data.get("nearest_station", {})
        return station.get("name")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        station = self.coordinator.data.get("nearest_station", {})
        return {
            ATTR_STATION_ADDRESS: station.get("address"),
            ATTR_DISTANCE: station.get("distance"),
            ATTR_PRICE: station.get("price"),
        }
