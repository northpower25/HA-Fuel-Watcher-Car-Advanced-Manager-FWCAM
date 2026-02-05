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
    CONF_API_KEY,
    CONF_FUEL_TYPE,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_ODOMETER_ENTITY,
    CONF_POSITION_ENTITY,
    CONF_PROVIDER,
    CONF_RADIUS,
    CONF_RANGE_ENTITY,
    CONF_TANK_LEVEL_ENTITY,
    CONF_UPDATE_INTERVAL,
    CONF_VEHICLE_NAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    PROVIDER_TANKERKONIG,
)
from .utils.vehicle_data import async_get_vehicle_data
from .utils.vehicle_tracker import VehicleDataTracker

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

    # Initialize coordinator with actual data fetching
    coordinator = HaFWCMACoordinator(hass, config_entry)
    
    # Store coordinator in hass.data for button/switch access
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if config_entry.entry_id not in hass.data[DOMAIN]:
        hass.data[DOMAIN][config_entry.entry_id] = {}
    hass.data[DOMAIN][config_entry.entry_id]["coordinator"] = coordinator
    
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
        # Get update interval from config
        config = config_entry.data
        options = config_entry.options
        update_interval_minutes = options.get(CONF_UPDATE_INTERVAL) or config.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self.config_entry = config_entry
        self.vehicle_tracker = VehicleDataTracker()
        self._provider = None
        self._session = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from providers.
        
        Returns:
            Dictionary with updated sensor data
            
        Raises:
            UpdateFailed: If update fails
        """
        try:
            # Get configuration - check both data and options with proper fallback
            config = self.config_entry.data
            options = self.config_entry.options
            
            # Get provider configuration
            provider = options.get(CONF_PROVIDER) or config.get(CONF_PROVIDER, PROVIDER_TANKERKONIG)
            api_key = config.get(CONF_API_KEY)
            fuel_type = options.get(CONF_FUEL_TYPE) or config.get(CONF_FUEL_TYPE, "e5")
            radius = options.get(CONF_RADIUS) or config.get(CONF_RADIUS, 5.0)
            
            # Get entity IDs from options first, then config
            odometer_entity = options.get(CONF_ODOMETER_ENTITY) or config.get(CONF_ODOMETER_ENTITY)
            tank_level_entity = options.get(CONF_TANK_LEVEL_ENTITY) or config.get(CONF_TANK_LEVEL_ENTITY)
            range_entity = options.get(CONF_RANGE_ENTITY) or config.get(CONF_RANGE_ENTITY)
            position_entity = options.get(CONF_POSITION_ENTITY) or config.get(CONF_POSITION_ENTITY)
            
            # Fetch vehicle data from configured entities
            vehicle_data = await async_get_vehicle_data(
                self.hass,
                odometer_entity,
                tank_level_entity,
                range_entity,
                position_entity,
            )
            
            _LOGGER.debug("Vehicle data: %s", vehicle_data)
            
            # Track vehicle data changes and detect events
            tracking_result = self.vehicle_tracker.update(vehicle_data)
            _LOGGER.debug("Tracking result: %s", tracking_result)
            
            # Use vehicle position if available, otherwise use configured lat/lon
            latitude = vehicle_data.get("latitude")
            longitude = vehicle_data.get("longitude")
            
            if latitude is None or longitude is None:
                latitude = config.get(CONF_LATITUDE)
                longitude = config.get(CONF_LONGITUDE)
            
            # Fetch data from provider
            nearest_station = None
            fuel_price = None
            
            if provider == PROVIDER_TANKERKONIG and api_key:
                try:
                    # Initialize provider if needed
                    if self._provider is None or self._session is None:
                        import aiohttp
                        from .providers.tankerkonig import TankerkoenigProvider
                        
                        self._session = aiohttp.ClientSession()
                        self._provider = TankerkoenigProvider(api_key, self._session)
                    
                    # Fetch stations near current position
                    stations = await self._provider.get_stations_nearby(
                        latitude, longitude, radius, fuel_type
                    )
                    
                    if stations:
                        # Get nearest station
                        nearest = stations[0]
                        fuel_price = nearest.get_price(fuel_type)
                        nearest_station = {
                            "id": nearest.station_id,
                            "name": nearest.name,
                            "brand": nearest.brand,
                            "address": f"{nearest.address}, {nearest.city}",
                            "distance": round(nearest.distance, 2),
                            "price": fuel_price,
                            "latitude": nearest.latitude,
                            "longitude": nearest.longitude,
                            "is_open": nearest.is_open,
                        }
                        _LOGGER.info(
                            "Found nearest station: %s at %.2f km, price: €%.3f",
                            nearest.name,
                            nearest.distance,
                            fuel_price if fuel_price else 0,
                        )
                    else:
                        _LOGGER.warning("No stations found within %.1f km", radius)
                        
                except Exception as err:
                    _LOGGER.error("Error fetching data from provider: %s", err)
                    # Continue with cached/placeholder data
            
            # Build data structure
            data = {
                "fuel_price": fuel_price,
                "tank_level": vehicle_data.get("tank_level"),
                "tank_percentage": 70.0,  # TODO: Calculate from tank_level and capacity
                "range": vehicle_data.get("range_km"),
                "odometer": vehicle_data.get("odometer_km"),
                "latitude": latitude,
                "longitude": longitude,
                "nearest_station": nearest_station or {
                    "name": "No station found",
                    "address": "",
                    "distance": 0.0,
                    "price": None,
                },
                "forecast_trend": "stable",  # TODO: Implement forecasting
                "vehicle_data": vehicle_data,
                "tracking": tracking_result,
            }

            return data

        except Exception as err:
            _LOGGER.error("Error updating haFWCMA data: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err
    
    async def async_shutdown(self) -> None:
        """Shutdown coordinator and cleanup resources."""
        if self._session:
            await self._session.close()
            self._session = None
        self._provider = None


class FuelPriceSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing current fuel price at nearest station."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = f"{CURRENCY_EURO}/L"

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
