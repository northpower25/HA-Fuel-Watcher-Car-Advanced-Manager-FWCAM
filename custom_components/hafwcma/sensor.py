"""Sensor platform for haFWCMA integration."""
from __future__ import annotations

import aiohttp
import logging
from datetime import datetime, timedelta
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
    ATTR_AVG_DAILY_KM,
    ATTR_DAYS_LEFT,
    ATTR_DISTANCE,
    ATTR_FORECAST_TREND,
    ATTR_PRICE,
    ATTR_PRICE_DELTA,
    ATTR_PRICE_DELTA_PERCENT,
    ATTR_RANGE_KM,
    ATTR_RECOMMENDATION,
    ATTR_SHOULD_REFUEL,
    ATTR_STATION_ADDRESS,
    ATTR_STATION_NAME,
    ATTR_TANK_LEVEL,
    ATTR_URGENCY,
    CONF_API_KEY,
    CONF_FUEL_TYPE,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_ODOMETER_ENTITY,
    CONF_POSITION_ENTITY,
    CONF_PROVIDER,
    CONF_RADIUS,
    CONF_RANGE_ENTITY,
    CONF_TANK_CAPACITY,
    CONF_TANK_LEVEL_ENTITY,
    CONF_UPDATE_INTERVAL,
    CONF_VEHICLE_NAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    PROVIDER_TANKERKONIG,
)
from .providers.tankerkonig import TankerkoenigProvider
from .utils.vehicle_data import async_get_vehicle_data
from .utils.vehicle_tracker import VehicleDataTracker
from .utils import storage
from .utils.prediction_engine import evaluate_refuel_strategy, get_prediction_summary
from .utils.price_engine import compute_price_trend, get_price_statistics
from .utils.statistics_engine import estimate_days_left

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
        ApiDebugSensor(coordinator, config_entry, vehicle_name),
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
        self._api_debug_info = None  # Store debug info about API requests/responses

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from providers.
        
        Returns:
            Dictionary with updated sensor data. Always returns data even if API fails,
            to ensure last_update_success is true and sensors maintain their state.
            
        Raises:
            UpdateFailed: Only if there's a critical configuration error
        """
        # Get configuration - check both data and options with proper fallback
        config = self.config_entry.data
        options = self.config_entry.options
        
        # Get provider configuration
        provider = options.get(CONF_PROVIDER) or config.get(CONF_PROVIDER, PROVIDER_TANKERKONIG)
        api_key = config.get(CONF_API_KEY)
        fuel_type = options.get(CONF_FUEL_TYPE) or config.get(CONF_FUEL_TYPE, "e5")
        radius = options.get(CONF_RADIUS) or config.get(CONF_RADIUS, 5.0)
        
        # Validate critical configuration
        if not api_key:
            raise UpdateFailed("API key not configured")
        
        # Get entity IDs from options first, then config
        odometer_entity = options.get(CONF_ODOMETER_ENTITY) or config.get(CONF_ODOMETER_ENTITY)
        tank_level_entity = options.get(CONF_TANK_LEVEL_ENTITY) or config.get(CONF_TANK_LEVEL_ENTITY)
        range_entity = options.get(CONF_RANGE_ENTITY) or config.get(CONF_RANGE_ENTITY)
        position_entity = options.get(CONF_POSITION_ENTITY) or config.get(CONF_POSITION_ENTITY)
        
        # Initialize default values
        fuel_price = None
        nearest_station = None
        vehicle_data = {}
        tracking_result = {}
        odometer = None
        
        try:
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
            
            # Store odometer history if available
            odometer = vehicle_data.get("odometer_km")
            if odometer is not None:
                await storage.add_odometer_observation(
                    self.hass,
                    self.config_entry,
                    odometer,
                    datetime.now().isoformat(),
                )
        except Exception as err:
            _LOGGER.warning("Error fetching vehicle data: %s", err)
            # Continue with empty vehicle data
        
        try:
            # Use vehicle position if available, otherwise use configured lat/lon
            latitude = vehicle_data.get("latitude")
            longitude = vehicle_data.get("longitude")
            # Default to fallback; will be updated if vehicle position is used
            location_source = "fallback (configured)"
            
            if latitude is None or longitude is None:
                latitude = config.get(CONF_LATITUDE)
                longitude = config.get(CONF_LONGITUDE)
            else:
                # Only set vehicle source if position_entity is configured
                position_entity = options.get(CONF_POSITION_ENTITY) or config.get(CONF_POSITION_ENTITY)
                if position_entity:
                    location_source = f"vehicle ({position_entity})"
            
            # Store debug info
            timestamp = datetime.now().isoformat()
            self._api_debug_info = {
                "timestamp": timestamp,
                "location_source": location_source,
                "latitude": latitude,
                "longitude": longitude,
                "radius_km": radius,
                "fuel_type": fuel_type,
                "provider": provider,
                "last_api_request": None,  # Will be populated from provider
                "last_api_response": None,  # Will be populated from provider
            }
            
            # Fetch data from provider
            if provider == PROVIDER_TANKERKONIG and api_key:
                try:
                    # Initialize provider and session if needed
                    if self._provider is None:
                        if self._session is None:
                            self._session = aiohttp.ClientSession()
                        self._provider = TankerkoenigProvider(api_key, self._session)
                    
                    # Fetch stations near current position
                    stations = await self._provider.get_stations_nearby(
                        latitude, longitude, radius, fuel_type
                    )
                    
                    # Capture API request and response from provider
                    if hasattr(self._provider, 'last_api_request'):
                        self._api_debug_info["last_api_request"] = self._provider.last_api_request
                    if hasattr(self._provider, 'last_api_response'):
                        self._api_debug_info["last_api_response"] = self._provider.last_api_response
                    
                    # Update debug info with response
                    self._api_debug_info["api_response_status"] = "success"
                    self._api_debug_info["stations_found"] = len(stations)
                    
                    if stations:
                        # Sort stations by price first (cheapest), then by distance
                        # Filter out closed stations AND stations without valid prices
                        # Note: Closed stations may still report prices but can't serve customers
                        
                        # Count stations by their status for better debugging
                        closed_count = sum(1 for s in stations if not s.is_open)
                        no_price_count = sum(1 for s in stations if s.get_price(fuel_type) is None)
                        
                        # Log each station's status for detailed debugging
                        for station in stations:
                            station_price = station.get_price(fuel_type)
                            _LOGGER.debug(
                                "Station '%s': is_open=%s, %s_price=%s, passes_filter=%s",
                                station.name,
                                station.is_open,
                                fuel_type,
                                station_price,
                                station_price is not None and station.is_open
                            )
                        
                        stations_with_price = [
                            s for s in stations 
                            if s.get_price(fuel_type) is not None and s.is_open
                        ]
                        
                        self._api_debug_info["stations_with_price_and_open"] = len(stations_with_price)
                        self._api_debug_info["stations_closed"] = closed_count
                        self._api_debug_info["stations_no_price"] = no_price_count
                        
                        if stations_with_price:
                            # Sort by price (ascending), then by distance (ascending)
                            # Note: All stations in this list have valid prices (filtered above)
                            stations_with_price.sort(key=lambda s: (s.get_price(fuel_type), s.distance))
                            cheapest = stations_with_price[0]
                            
                            fuel_price = cheapest.get_price(fuel_type)
                            nearest_station = {
                                "id": cheapest.station_id,
                                "name": cheapest.name,
                                "brand": cheapest.brand,
                                "address": f"{cheapest.address}, {cheapest.city}",
                                "distance": round(cheapest.distance, 2),
                                "price": fuel_price,
                                "latitude": cheapest.latitude,
                                "longitude": cheapest.longitude,
                                "is_open": cheapest.is_open,
                            }
                            _LOGGER.info(
                                "Found cheapest station: %s at %.2f km, price: €%.3f",
                                cheapest.name,
                                cheapest.distance,
                                fuel_price,
                            )
                        else:
                            # No stations with valid prices found - provide detailed reason
                            self._api_debug_info["warning"] = f"Found {len(stations)} stations but none are both open and have valid prices for {fuel_type}"
                            _LOGGER.warning(
                                "Found %d stations but none are both open and have valid prices for %s. Details: %d closed, %d without %s price",
                                len(stations),
                                fuel_type,
                                closed_count,
                                no_price_count,
                                fuel_type,
                            )
                    else:
                        self._api_debug_info["warning"] = f"No stations found within {radius} km"
                        _LOGGER.warning("No stations found within %.1f km", radius)
                        
                except Exception as err:
                    # Capture API request and response from provider even on error
                    if hasattr(self._provider, 'last_api_request'):
                        self._api_debug_info["last_api_request"] = self._provider.last_api_request
                    if hasattr(self._provider, 'last_api_response'):
                        self._api_debug_info["last_api_response"] = self._provider.last_api_response
                    
                    self._api_debug_info["api_response_status"] = "error"
                    self._api_debug_info["error"] = str(err)
                    self._api_debug_info["error_type"] = type(err).__name__
                    _LOGGER.error("Error fetching data from provider: %s", err, exc_info=True)
                    # Continue with cached/placeholder data
                    
        except Exception as err:
            if self._api_debug_info:
                # Capture API request and response from provider even on error
                if self._provider and hasattr(self._provider, 'last_api_request'):
                    self._api_debug_info["last_api_request"] = self._provider.last_api_request
                if self._provider and hasattr(self._provider, 'last_api_response'):
                    self._api_debug_info["last_api_response"] = self._provider.last_api_response
                
                self._api_debug_info["api_response_status"] = "error"
                self._api_debug_info["error"] = str(err)
                self._api_debug_info["error_type"] = type(err).__name__
            _LOGGER.error("Error in station lookup: %s", err, exc_info=True)
            # Continue with cached/placeholder data
        
        try:
            # Store price history if we have a price
            if fuel_price is not None:
                await storage.add_price_observation(
                    self.hass,
                    self.config_entry,
                    fuel_price,
                    datetime.now().isoformat(),
                )
        except Exception as err:
            _LOGGER.warning("Error storing price observation: %s", err)
        
        try:
            # Handle refueling detection
            if tracking_result.get("refueling_detected"):
                _LOGGER.info("Refueling detected!")
                # Store refueling event with current price if available
                refuel_event = {
                    "timestamp": datetime.now().isoformat(),
                    "fuel_added": tracking_result.get("fuel_added"),
                    "odometer_km": odometer,
                    "consumption_rate": tracking_result.get("average_consumption"),
                    "price_per_liter": fuel_price,  # Include price for better prediction
                }
                await storage.add_refuel_event(self.hass, self.config_entry, refuel_event)
        except Exception as err:
            _LOGGER.warning("Error handling refueling detection: %s", err)
        
        # Build data structure
        # Calculate tank percentage if we have both level and capacity
        tank_percentage = None
        tank_level = vehicle_data.get("tank_level")
        if tank_level is not None:
            tank_capacity = options.get(CONF_TANK_CAPACITY) or config.get(CONF_TANK_CAPACITY, 50.0)
            if tank_capacity and tank_capacity > 0:
                tank_percentage = (tank_level / tank_capacity) * 100
        
        # Get price trend and statistics
        price_trend = None
        try:
            price_trend = await compute_price_trend(self.hass, self.config_entry, window=5)
        except Exception as err:
            _LOGGER.warning("Error computing price trend: %s", err)
        
        # Get refuel recommendation if we have price and tank info
        recommendation = None
        if fuel_price is not None and tank_percentage is not None:
            try:
                recommendation = await evaluate_refuel_strategy(
                    self.hass,
                    self.config_entry,
                    current_price=fuel_price,
                    tank_percentage=tank_percentage,
                    range_km=vehicle_data.get("range_km"),
                    station_name=nearest_station.get("name") if nearest_station else None,
                )
                _LOGGER.debug("Refuel recommendation: %s", recommendation)
            except Exception as err:
                _LOGGER.warning("Error evaluating refuel strategy: %s", err)
        
        # Estimate days left
        days_left = None
        range_km = vehicle_data.get("range_km")
        if range_km:
            try:
                days_left = await estimate_days_left(
                    self.hass,
                    self.config_entry,
                    km_left=range_km,
                    fallback_daily_km=40.0,
                )
            except Exception as err:
                _LOGGER.warning("Error estimating days left: %s", err)
        
        data = {
            "fuel_price": fuel_price,
            "tank_level": tank_level,
            "tank_percentage": tank_percentage,
            "range": range_km,
            "odometer": vehicle_data.get("odometer_km"),
            "latitude": latitude,
            "longitude": longitude,
            "nearest_station": nearest_station or {
                "name": "No station found",
                "address": "",
                "distance": 0.0,
                "price": None,
            },
            "forecast_trend": price_trend,
            "vehicle_data": vehicle_data,
            "tracking": tracking_result,
            "recommendation": recommendation,
            "days_left": days_left,
            "api_debug": self._api_debug_info,  # Add debug information
        }

        return data
    
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
        recommendation = self.coordinator.data.get("recommendation", {})
        
        attributes = {
            ATTR_STATION_NAME: station.get("name"),
            ATTR_STATION_ADDRESS: station.get("address"),
            ATTR_DISTANCE: station.get("distance"),
            ATTR_FORECAST_TREND: self.coordinator.data.get("forecast_trend"),
        }
        
        # Add prediction attributes if available
        if recommendation:
            attributes[ATTR_SHOULD_REFUEL] = recommendation.get("should_refuel", False)
            attributes[ATTR_URGENCY] = recommendation.get("urgency", "low")
            attributes[ATTR_RECOMMENDATION] = recommendation.get("recommendation", "")
            attributes[ATTR_PRICE_DELTA] = recommendation.get("price_delta")
            attributes[ATTR_PRICE_DELTA_PERCENT] = recommendation.get("price_delta_percent")
        
        return attributes


class TankLevelSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing current tank level."""

    _attr_native_unit_of_measurement = "%"
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
        self._config_entry = config_entry

    @property
    def native_value(self) -> float | None:
        """Return the current tank level as percentage."""
        return self.coordinator.data.get("tank_percentage")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        tank_level_liters = self.coordinator.data.get("tank_level")
        attributes = {}
        
        if tank_level_liters is not None:
            attributes["liters"] = tank_level_liters
        
        return attributes


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
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        days_left = self.coordinator.data.get("days_left")
        if days_left is not None:
            return {
                ATTR_DAYS_LEFT: days_left,
            }
        return {}


class NearestStationSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing cheapest fuel station within radius."""

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
        self._attr_name = f"{vehicle_name} Cheapest Station"
        self._attr_unique_id = f"{config_entry.entry_id}_nearest_station"

    @property
    def native_value(self) -> str | None:
        """Return the name of cheapest station."""
        station = self.coordinator.data.get("nearest_station", {})
        return station.get("name")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        station = self.coordinator.data.get("nearest_station", {})
        attributes = {
            ATTR_STATION_ADDRESS: station.get("address"),
            ATTR_DISTANCE: station.get("distance"),
            ATTR_PRICE: station.get("price"),
        }
        
        # Add navigation links if station has coordinates
        lat = station.get("latitude")
        lon = station.get("longitude")
        if lat and lon:
            attributes["google_maps_url"] = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            attributes["apple_maps_url"] = f"https://maps.apple.com/?q={lat},{lon}"
            attributes["waze_url"] = f"https://waze.com/ul?ll={lat},{lon}&navigate=yes"
        
        return attributes


class ApiDebugSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing API debug information."""

    _attr_icon = "mdi:api"

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
        self._attr_name = f"{vehicle_name} API Debug"
        self._attr_unique_id = f"{config_entry.entry_id}_api_debug"

    @property
    def native_value(self) -> str | None:
        """Return the API status."""
        api_debug = self.coordinator.data.get("api_debug", {})
        if not api_debug:
            return "Unknown"
        
        status = api_debug.get("api_response_status", "unknown")
        return status.title()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return all API debug information as attributes."""
        api_debug = self.coordinator.data.get("api_debug", {})
        if not api_debug:
            return {"status": "No API request made yet"}
        
        return api_debug

