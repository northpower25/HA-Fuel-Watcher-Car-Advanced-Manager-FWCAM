"""Sensor platform for haFWCMA integration."""
from __future__ import annotations

import aiohttp
import logging
import random
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
    ATTR_AVG_CONSUMPTION_RATE,
    ATTR_AVG_DAILY_KM,
    ATTR_CONFIDENCE,
    ATTR_DATA_POINTS_USED,
    ATTR_DATA_SOURCE,
    ATTR_DAYS_LEFT,
    ATTR_DISTANCE,
    ATTR_FORECAST_TREND,
    ATTR_LAST_PREDICTION,
    ATTR_PREDICTED_REFUEL_DATE,
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
    CONF_CHEAP_STATIONS_COUNT,
    CONF_CHEAP_STATIONS_RADIUS,
    CONF_CONSUMPTION_MIN_DATA_POINTS,
    CONF_CONSUMPTION_PREDICTION_INTERVAL,
    CONF_FUEL_TYPE,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MIN_TANK_LEVEL_FOR_ALERTS,
    CONF_ODOMETER_ENTITY,
    CONF_POSITION_ENTITY,
    CONF_PROVIDER,
    CONF_PROXIMITY_ALERT_DISTANCE,
    CONF_PROXIMITY_ALERTS_ENABLED,
    CONF_RADIUS,
    CONF_RANGE_ENTITY,
    CONF_TANK_CAPACITY,
    CONF_TANK_LEVEL_ENTITY,
    CONF_UPDATE_INTERVAL,
    CONF_VEHICLE_NAME,
    DEFAULT_CHEAP_STATIONS_COUNT,
    DEFAULT_CHEAP_STATIONS_RADIUS,
    DEFAULT_CONSUMPTION_MIN_DATA_POINTS,
    DEFAULT_CONSUMPTION_PREDICTION_INTERVAL,
    DEFAULT_MIN_TANK_LEVEL_FOR_ALERTS,
    DEFAULT_PROXIMITY_ALERT_DISTANCE,
    DEFAULT_PROXIMITY_ALERTS_ENABLED,
    DEFAULT_TANK_CAPACITY,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_JITTER_PERCENT,
    DOMAIN,
    GEOLOCATION_ALERT_COOLDOWN,
    GEOLOCATION_HYSTERESIS_FACTOR,
    PROVIDER_TANKERKONIG,
)
from .providers.tankerkonig import TankerkoenigProvider
from .utils.vehicle_data import async_get_vehicle_data
from .utils.vehicle_tracker import VehicleDataTracker
from .utils import storage
from .utils.consumption_prediction import predict_days_until_refuel, store_prediction_result
from .utils.prediction_engine import evaluate_refuel_strategy, get_prediction_summary
from .utils.price_engine import compute_price_trend, get_price_statistics
from .utils.statistics_engine import estimate_days_left
from .utils.geolocation import (
    ProximityTracker,
    enrich_station_data,
    find_nearest_cheap_station,
    format_alert_message,
    get_navigation_urls,
)

_LOGGER = logging.getLogger(__name__)

# Constants for tank percentage validation
MIN_TANK_PERCENTAGE = 0.0
MAX_TANK_PERCENTAGE = 100.0


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
        ConsumptionPredictionSensor(coordinator, config_entry, vehicle_name),
        ConsumptionHistorySensor(coordinator, config_entry, vehicle_name),
        ConsumptionForecastSensor(coordinator, config_entry, vehicle_name),
        RefuelingLogSensor(coordinator, config_entry, vehicle_name),
        NearbyCheapStationsSensor(coordinator, config_entry, vehicle_name),
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
        
        # Initialize with randomized interval to prevent simultaneous API calls
        # Calculate jitter range with reduced randomization to avoid "shaky" sensor updates
        jitter_percent = DEFAULT_UPDATE_INTERVAL_JITTER_PERCENT / 100.0
        jitter_minutes = update_interval_minutes * jitter_percent
        random_offset = random.uniform(-jitter_minutes, jitter_minutes)
        randomized_minutes = max(1.0, update_interval_minutes + random_offset)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=randomized_minutes),
        )
        self.config_entry = config_entry
        self.vehicle_tracker = VehicleDataTracker()
        self._provider = None
        self._session = None
        self._api_debug_info = None  # Store debug info about API requests/responses
        self._last_consumption_prediction = None  # Store last consumption prediction time
        self._proximity_tracker = ProximityTracker(
            cooldown_seconds=GEOLOCATION_ALERT_COOLDOWN,
            hysteresis_factor=GEOLOCATION_HYSTERESIS_FACTOR,
        )  # Track proximity alerts
        
        _LOGGER.info(
            "Coordinator initialized with randomized update interval: %.1f minutes (base: %d, jitter: ±%.1f)",
            randomized_minutes,
            update_interval_minutes,
            jitter_minutes,
        )

    def _capture_provider_debug_info(self) -> None:
        """Capture API request and response from provider for debugging.
        
        This method safely extracts debug information from the provider
        (if available) and stores it in self._api_debug_info dictionary.
        It's used both on successful API calls and when errors occur.
        """
        if self._api_debug_info and self._provider:
            if hasattr(self._provider, 'last_api_request'):
                self._api_debug_info["last_api_request"] = self._provider.last_api_request
            if hasattr(self._provider, 'last_api_response'):
                self._api_debug_info["last_api_response"] = self._provider.last_api_response

    def _get_randomized_interval(self, base_minutes: int) -> timedelta:
        """Calculate a randomized update interval to avoid simultaneous API calls.
        
        Applies a small random jitter (±2% by default) to distribute API calls over time.
        This helps prevent rate limiting when multiple instances hit the API simultaneously
        while keeping sensor updates stable and non-"shaky".
        
        Args:
            base_minutes: Base update interval in minutes
            
        Returns:
            Randomized timedelta for next update
        """
        # Calculate jitter range with reduced randomization
        jitter_percent = DEFAULT_UPDATE_INTERVAL_JITTER_PERCENT / 100.0
        jitter_minutes = base_minutes * jitter_percent
        
        # Apply random offset within jitter range
        random_offset = random.uniform(-jitter_minutes, jitter_minutes)
        randomized_minutes = base_minutes + random_offset
        
        # Ensure we don't go below 1 minute
        randomized_minutes = max(1.0, randomized_minutes)
        
        _LOGGER.debug(
            "Randomized update interval: base=%.1f min, jitter=±%.1f min, result=%.1f min",
            base_minutes,
            jitter_minutes,
            randomized_minutes,
        )
        
        return timedelta(minutes=randomized_minutes)

    async def async_set_update_interval(self, minutes: int) -> None:
        """Dynamically update the coordinator's update interval.
        
        This allows the update interval to be changed at runtime through
        the number entity without reloading the integration.
        
        Args:
            minutes: New update interval in minutes
        """
        _LOGGER.info("Setting new update interval: %d minutes (with randomization)", minutes)
        
        # Update the coordinator's update interval with randomization
        self.update_interval = self._get_randomized_interval(minutes)
        
        # Request a refresh with the new interval
        await self.async_request_refresh()

    async def async_update_config(self, config_entry: ConfigEntry) -> None:
        """Update coordinator configuration from config entry.
        
        This allows configuration changes without reloading the entire integration.
        
        Args:
            config_entry: Updated config entry
        """
        _LOGGER.info("Updating coordinator configuration")
        self.config_entry = config_entry
        
        # Update update interval if it changed
        options = config_entry.options
        config = config_entry.data
        update_interval_minutes = options.get(CONF_UPDATE_INTERVAL) or config.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        
        # Update interval with randomization
        self.update_interval = self._get_randomized_interval(update_interval_minutes)
        
        _LOGGER.info("Coordinator configuration updated successfully")

    async def _update_consumption_prediction(
        self,
        range_km: float | None,
        tank_level: float | None,
        tank_capacity: float,
    ) -> dict[str, Any] | None:
        """Update consumption prediction if interval has passed.
        
        Args:
            range_km: Current range in km
            tank_level: Current tank level in liters
            tank_capacity: Tank capacity in liters
            
        Returns:
            Prediction dictionary or None if not updated
        """
        from homeassistant.util import dt as dt_util
        from .const import (
            CONF_CONSUMPTION_MIN_DATA_POINTS,
            CONF_CONSUMPTION_PREDICTION_INTERVAL,
            CONF_FALLBACK_DAILY_KM,
            DEFAULT_CONSUMPTION_MIN_DATA_POINTS,
            DEFAULT_CONSUMPTION_PREDICTION_INTERVAL,
            DEFAULT_FALLBACK_DAILY_KM,
        )
        from .utils.statistics_engine import get_average_consumption_rate
        
        # Get configuration
        options = self.config_entry.options
        config = self.config_entry.data
        
        prediction_interval_hours = options.get(CONF_CONSUMPTION_PREDICTION_INTERVAL) or config.get(
            CONF_CONSUMPTION_PREDICTION_INTERVAL, DEFAULT_CONSUMPTION_PREDICTION_INTERVAL
        )
        min_data_points = options.get(CONF_CONSUMPTION_MIN_DATA_POINTS) or config.get(
            CONF_CONSUMPTION_MIN_DATA_POINTS, DEFAULT_CONSUMPTION_MIN_DATA_POINTS
        )
        fallback_daily_km = options.get(CONF_FALLBACK_DAILY_KM) or config.get(
            CONF_FALLBACK_DAILY_KM, DEFAULT_FALLBACK_DAILY_KM
        )
        
        # Check if we should run prediction (based on interval)
        now = dt_util.now()
        if self._last_consumption_prediction:
            time_since_last = (now - self._last_consumption_prediction).total_seconds() / 3600
            if time_since_last < prediction_interval_hours:
                # Return None to keep existing prediction
                return None
        
        # Update last prediction time
        self._last_consumption_prediction = now
        
        # Get average consumption rate from history
        fallback_consumption_rate = await get_average_consumption_rate(
            self.hass,
            self.config_entry,
            fallback=7.0,
        )
        
        # Run prediction
        prediction = await predict_days_until_refuel(
            self.hass,
            self.config_entry,
            current_range_km=range_km,
            current_tank_level=tank_level,
            tank_capacity=tank_capacity,
            fallback_daily_km=fallback_daily_km,
            fallback_consumption_rate=fallback_consumption_rate,
            min_data_points=int(min_data_points),
        )
        
        # Store prediction result for accuracy tracking
        await store_prediction_result(self.hass, self.config_entry, prediction)
        
        _LOGGER.info(
            "Consumption prediction updated: %.1f days until refuel (source: %s, confidence: %.2f)",
            prediction.get("days_until_refuel") or 0,
            prediction.get("data_source"),
            prediction.get("confidence") or 0,
        )
        
        return prediction

    async def _calculate_consumption_history(self) -> dict[str, Any]:
        """Calculate consumption history for different time periods.
        
        Returns:
            Dictionary with consumption statistics for today, last week, last 14 days, last month
        """
        from .utils.storage import calculate_consumption_history
        
        # Calculate for different time periods
        today = await calculate_consumption_history(self.hass, self.config_entry, days=1)
        last_week = await calculate_consumption_history(self.hass, self.config_entry, days=7)
        last_14_days = await calculate_consumption_history(self.hass, self.config_entry, days=14)
        last_month = await calculate_consumption_history(self.hass, self.config_entry, days=30)
        
        return {
            "today": today,
            "last_week": last_week,
            "last_14_days": last_14_days,
            "last_month": last_month,
        }
    
    async def _calculate_consumption_forecast(
        self,
        consumption_prediction: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Calculate consumption forecast for different time periods.
        
        Uses ML prediction engine to forecast consumption patterns. Currently returns
        the same average consumption rate for all periods. Future enhancements will add
        time-specific forecasting with weekday/weekend patterns, seasonal variations,
        and historical trends.
        
        Args:
            consumption_prediction: Current consumption prediction data
            
        Returns:
            Dictionary with consumption forecasts for tomorrow, next week, next 14 days, next month
        """
        if not consumption_prediction:
            periods = ["tomorrow", "next_week", "next_14_days", "next_month"]
            return {period: None for period in periods}
        
        # Get average consumption rate and confidence from prediction
        avg_consumption_rate = consumption_prediction.get("avg_consumption_rate")
        confidence = consumption_prediction.get("confidence", 0.0)
        data_source = consumption_prediction.get("data_source", "unknown")
        
        # Create forecast with current average consumption rate
        forecast_base = {
            "avg_consumption_l_per_100km": avg_consumption_rate,
            "confidence": confidence,
            "data_source": data_source,
        }
        
        # Return same forecast for all periods (future: time-specific forecasting)
        periods = ["tomorrow", "next_week", "next_14_days", "next_month"]
        return {
            period: forecast_base.copy() if avg_consumption_rate else None
            for period in periods
        }

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
                from homeassistant.util import dt as dt_util
                await storage.add_odometer_observation(
                    self.hass,
                    self.config_entry,
                    odometer,
                    dt_util.now().isoformat(),
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
            from homeassistant.util import dt as dt_util
            timestamp = dt_util.now().isoformat()
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
                            # Create session with timeout configuration
                            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
                            self._session = aiohttp.ClientSession(timeout=timeout)
                        self._provider = TankerkoenigProvider(api_key, self._session)
                    
                    # Fetch stations near current position
                    stations = await self._provider.get_stations_nearby(
                        latitude, longitude, radius, fuel_type
                    )
                    
                    # Capture API request and response from provider
                    self._capture_provider_debug_info()
                    
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
                    self._capture_provider_debug_info()
                    
                    self._api_debug_info["api_response_status"] = "error"
                    self._api_debug_info["error"] = str(err)
                    self._api_debug_info["error_type"] = type(err).__name__
                    _LOGGER.error("Error fetching data from provider: %s", err, exc_info=True)
                    # Continue with cached/placeholder data
            
            # Process geolocation-based features (nearby cheap stations & proximity alerts)
            nearby_cheap_stations_data = None
            proximity_alert_data = None
            
            # Only process geolocation if vehicle position is available
            vehicle_lat = vehicle_data.get("latitude")
            vehicle_lon = vehicle_data.get("longitude")
            
            if vehicle_lat is not None and vehicle_lon is not None and position_entity:
                try:
                    # Get geolocation configuration
                    proximity_enabled = options.get(CONF_PROXIMITY_ALERTS_ENABLED, DEFAULT_PROXIMITY_ALERTS_ENABLED)
                    cheap_stations_count = options.get(CONF_CHEAP_STATIONS_COUNT, DEFAULT_CHEAP_STATIONS_COUNT)
                    cheap_stations_radius = options.get(CONF_CHEAP_STATIONS_RADIUS, DEFAULT_CHEAP_STATIONS_RADIUS)
                    proximity_distance = options.get(CONF_PROXIMITY_ALERT_DISTANCE, DEFAULT_PROXIMITY_ALERT_DISTANCE)
                    min_tank_level = options.get(CONF_MIN_TANK_LEVEL_FOR_ALERTS, DEFAULT_MIN_TANK_LEVEL_FOR_ALERTS)
                    
                    # Fetch stations for geolocation (using larger radius for cheap stations search)
                    if self._provider and provider == PROVIDER_TANKERKONIG:
                        try:
                            geo_stations = await self._provider.get_stations_nearby(
                                vehicle_lat, vehicle_lon, cheap_stations_radius, fuel_type
                            )
                            
                            if geo_stations:
                                # Filter open stations with valid prices
                                geo_stations_valid = [
                                    s for s in geo_stations
                                    if s.get_price(fuel_type) is not None and s.is_open
                                ]
                                
                                if geo_stations_valid:
                                    # Sort by price
                                    geo_stations_valid.sort(key=lambda s: s.get_price(fuel_type))
                                    
                                    # Get N cheapest stations
                                    cheapest_stations = geo_stations_valid[:cheap_stations_count]
                                    
                                    # Convert to dict format with enriched data
                                    stations_list = []
                                    for station in cheapest_stations:
                                        station_dict = {
                                            "id": station.station_id,
                                            "name": station.name,
                                            "brand": station.brand,
                                            "address": f"{station.address}, {station.city}",
                                            "lat": station.latitude,
                                            "latitude": station.latitude,
                                            "lng": station.longitude,
                                            "longitude": station.longitude,
                                            "price": station.get_price(fuel_type),
                                            "fuel_type": fuel_type,
                                            "is_open": station.is_open,
                                        }
                                        # Enrich with distance and navigation
                                        enriched = enrich_station_data(station_dict, vehicle_lat, vehicle_lon)
                                        stations_list.append(enriched)
                                    
                                    nearby_cheap_stations_data = {
                                        "count": len(stations_list),
                                        "stations": stations_list,
                                        "search_radius_km": cheap_stations_radius,
                                        "vehicle_latitude": vehicle_lat,
                                        "vehicle_longitude": vehicle_lon,
                                        "max_stations": cheap_stations_count,
                                    }
                                    
                                    _LOGGER.info(
                                        "Found %d cheap stations within %.1f km of vehicle",
                                        len(stations_list),
                                        cheap_stations_radius,
                                    )
                                    
                                    # Check for proximity alerts (only if enabled)
                                    if proximity_enabled and stations_list:
                                        # Check tank level condition
                                        should_alert_tank = True
                                        if tank_percentage is not None and min_tank_level > 0:
                                            should_alert_tank = tank_percentage < min_tank_level
                                        
                                        if should_alert_tank:
                                            # Find nearest station within proximity threshold
                                            nearest_cheap = find_nearest_cheap_station(
                                                stations_list,
                                                vehicle_lat,
                                                vehicle_lon,
                                                proximity_distance,
                                            )
                                            
                                            if nearest_cheap:
                                                # Check if we should alert for this station
                                                station_id = nearest_cheap.get("id")
                                                distance = nearest_cheap.get("distance_km", 999)
                                                
                                                if self._proximity_tracker.should_alert(
                                                    station_id, distance, proximity_distance
                                                ):
                                                    # Generate alert
                                                    nav_urls = nearest_cheap.get("navigation_urls", {})
                                                    alert_msg = format_alert_message(
                                                        station_name=nearest_cheap.get("name", ""),
                                                        distance_km=distance,
                                                        price=nearest_cheap.get("price", 0),
                                                        fuel_type=fuel_type,
                                                        address=nearest_cheap.get("address", ""),
                                                        navigation_url=nav_urls.get("google_maps", ""),
                                                    )
                                                    
                                                    proximity_alert_data = {
                                                        "is_near": True,
                                                        "station": nearest_cheap,
                                                        "threshold_km": proximity_distance,
                                                        "alert_message": alert_msg,
                                                    }
                                                    
                                                    _LOGGER.info(
                                                        "Proximity alert: Near cheap station %s (%.1f km)",
                                                        nearest_cheap.get("name"),
                                                        distance,
                                                    )
                                                else:
                                                    # Within threshold but cooldown/hysteresis preventing alert
                                                    proximity_alert_data = {"is_near": False}
                                            else:
                                                # No cheap station within proximity threshold
                                                proximity_alert_data = {"is_near": False}
                                        else:
                                            # Tank level too high for alerts
                                            proximity_alert_data = {"is_near": False}
                                            _LOGGER.debug(
                                                "Proximity alerts disabled: tank level %.1f%% >= %.1f%%",
                                                tank_percentage or 0,
                                                min_tank_level,
                                            )
                                    else:
                                        # Proximity alerts disabled
                                        proximity_alert_data = {"is_near": False}
                                else:
                                    _LOGGER.debug("No valid stations found for geolocation features")
                            else:
                                _LOGGER.debug("No stations found within geolocation radius %.1f km", cheap_stations_radius)
                        except Exception as err:
                            _LOGGER.warning("Error fetching geolocation data: %s", err)
                except Exception as err:
                    _LOGGER.warning("Error processing geolocation features: %s", err)
            else:
                _LOGGER.debug("Geolocation features disabled: vehicle position not available")
                    
        except Exception as err:
            if self._api_debug_info:
                # Capture API request and response from provider even on error
                self._capture_provider_debug_info()
                
                self._api_debug_info["api_response_status"] = "error"
                self._api_debug_info["error"] = str(err)
                self._api_debug_info["error_type"] = type(err).__name__
            _LOGGER.error("Error in station lookup: %s", err, exc_info=True)
            # Continue with cached/placeholder data
        
        # Handle storing and retrieving last successful price and station
        from homeassistant.util import dt as dt_util
        timestamp_now = dt_util.now().isoformat()
        
        try:
            # If we successfully got a price, store it with timestamp
            if fuel_price is not None and nearest_station:
                await storage.set_last_price(
                    self.hass,
                    self.config_entry,
                    fuel_price,
                    timestamp_now,
                )
                await storage.set_last_station(
                    self.hass,
                    self.config_entry,
                    nearest_station,
                    timestamp_now,
                )
                # Also store price history
                await storage.add_price_observation(
                    self.hass,
                    self.config_entry,
                    fuel_price,
                    timestamp_now,
                )
            else:
                # No current data - use last successful values
                _LOGGER.info("No current price/station data, using last successful values")
                last_price = await storage.get_last_price(self.hass, self.config_entry)
                last_price_timestamp = await storage.get_last_price_timestamp(self.hass, self.config_entry)
                last_station = await storage.get_last_station(self.hass, self.config_entry)
                last_station_timestamp = await storage.get_last_station_timestamp(self.hass, self.config_entry)
                
                if last_price is not None:
                    fuel_price = last_price
                    _LOGGER.info("Using last successful price: €%.3f from %s", last_price, last_price_timestamp)
                
                if last_station is not None:
                    nearest_station = last_station
                    _LOGGER.info("Using last successful station: %s from %s", last_station.get("name"), last_station_timestamp)
        except Exception as err:
            _LOGGER.warning("Error handling price/station persistence: %s", err)
        
        try:
            # Handle refueling detection
            if tracking_result.get("refueling_detected"):
                _LOGGER.info("Refueling detected!")
                from homeassistant.util import dt as dt_util
                
                # Get current fuel type from config
                fuel_type = options.get(CONF_FUEL_TYPE) or config.get(CONF_FUEL_TYPE, "e5")
                
                # Get fuel added amount
                fuel_added = tracking_result.get("fuel_added")
                
                # Calculate total cost only if both price and amount are available and positive
                total_cost = None
                if (fuel_price is not None and fuel_added is not None 
                    and fuel_price > 0 and fuel_added > 0):
                    total_cost = fuel_added * fuel_price
                
                # Create comprehensive refueling event with all available data
                refuel_event = {
                    "timestamp": tracking_result.get("refuel_timestamp", dt_util.now().isoformat()),
                    "odometer_km": tracking_result.get("refuel_odometer_km") or odometer,
                    "liters_refueled": fuel_added,
                    "price_per_liter": fuel_price,
                    "total_cost": total_cost,
                    "station_name": nearest_station.get("name") if nearest_station else None,
                    "latitude": tracking_result.get("refuel_latitude"),
                    "longitude": tracking_result.get("refuel_longitude"),
                    "fuel_type": fuel_type,
                }
                
                # Store in new refueling log with ID
                refuel_id = await storage.add_refuel_event(self.hass, self.config_entry, refuel_event)
                
                # Format log message with safe handling of None values
                log_msg = f"Stored refueling event #{refuel_id}: "
                if fuel_added is not None:
                    log_msg += f"{fuel_added:.1f} L "
                else:
                    log_msg += "Unknown L "
                
                station_name = refuel_event.get("station_name") or "Unknown"
                log_msg += f"at {station_name} "
                if fuel_price is not None:
                    log_msg += f"(€{fuel_price:.3f}/L"
                    if total_cost is not None:
                        log_msg += f", total: €{total_cost:.2f}"
                    log_msg += ")"
                
                _LOGGER.info(log_msg)
        except Exception as err:
            _LOGGER.warning("Error handling refueling detection: %s", err)
        
        # Build data structure
        # Calculate tank percentage and liters from vehicle data
        tank_percentage = None
        tank_level_liters = None
        tank_level = vehicle_data.get("tank_level")
        tank_level_unit = vehicle_data.get("tank_level_unit")
        tank_capacity = options.get(CONF_TANK_CAPACITY) or config.get(CONF_TANK_CAPACITY, 50.0)
        
        if tank_level is not None:
            # Check if tank level is already a percentage or in liters
            if tank_level_unit and tank_level_unit.lower() in ("%", "percent", "percentage"):
                # Tank level is already a percentage, use it directly
                tank_percentage = tank_level
                # Calculate liters from percentage if we have tank capacity
                if tank_capacity and tank_capacity > 0:
                    tank_level_liters = (tank_level / 100.0) * tank_capacity
            else:
                # Tank level is in liters, use it directly
                tank_level_liters = tank_level
                # Convert to percentage if we have tank capacity
                if tank_capacity and tank_capacity > 0:
                    tank_percentage = (tank_level / tank_capacity) * 100
            
            # Clamp tank percentage to valid range (0-100%)
            if tank_percentage is not None:
                tank_percentage = max(MIN_TANK_PERCENTAGE, min(MAX_TANK_PERCENTAGE, tank_percentage))
        
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
        
        # Run consumption prediction if interval has passed
        consumption_prediction = None
        try:
            consumption_prediction = await self._update_consumption_prediction(
                range_km=range_km,
                tank_level=tank_level,
                tank_capacity=options.get(CONF_TANK_CAPACITY) or config.get(CONF_TANK_CAPACITY, 50.0),
            )
            # If no new prediction (interval not passed), keep existing prediction from previous data
            if consumption_prediction is None and self.data:
                consumption_prediction = self.data.get("consumption_prediction")
        except Exception as err:
            _LOGGER.warning("Error updating consumption prediction: %s", err)
            # Keep existing prediction on error
            if self.data:
                consumption_prediction = self.data.get("consumption_prediction")
        
        # Get timestamps for last successful data
        last_price_timestamp = await storage.get_last_price_timestamp(self.hass, self.config_entry)
        last_station_timestamp = await storage.get_last_station_timestamp(self.hass, self.config_entry)
        
        # Calculate consumption history
        consumption_history = None
        try:
            consumption_history = await self._calculate_consumption_history()
        except Exception as err:
            _LOGGER.warning("Error calculating consumption history: %s", err)
        
        # Calculate consumption forecast
        consumption_forecast = None
        try:
            consumption_forecast = await self._calculate_consumption_forecast(consumption_prediction)
        except Exception as err:
            _LOGGER.warning("Error calculating consumption forecast: %s", err)
        
        # Get refueling log for the refueling log sensor
        refueling_log = None
        try:
            refueling_log = await storage.get_refueling_log(self.hass, self.config_entry)
        except Exception as err:
            _LOGGER.warning("Error getting refueling log: %s", err)
        
        data = {
            "fuel_price": fuel_price,
            "last_price_timestamp": last_price_timestamp,
            "tank_level": tank_level_liters,  # Always in liters for consistency
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
            "last_station_timestamp": last_station_timestamp,
            "forecast_trend": price_trend,
            "vehicle_data": vehicle_data,
            "tracking": tracking_result,
            "recommendation": recommendation,
            "days_left": days_left,
            "api_debug": self._api_debug_info,  # Add debug information
            "consumption_prediction": consumption_prediction,  # Add consumption prediction
            "consumption_history": consumption_history,  # Add consumption history
            "consumption_forecast": consumption_forecast,  # Add consumption forecast
            "refueling_log": refueling_log,  # Add refueling log
            "nearby_cheap_stations": nearby_cheap_stations_data,  # Add geolocation data
            "proximity_alert": proximity_alert_data,  # Add proximity alert data
        }
        
        # Apply randomization for next update interval
        # Get current base interval from config
        current_base_interval = options.get(CONF_UPDATE_INTERVAL) or config.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        self.update_interval = self._get_randomized_interval(current_base_interval)

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
    _attr_has_entity_name = True

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
        self._attr_name = "Fuel Price"
        self._attr_unique_id = f"{config_entry.entry_id}_fuel_price"
        self._config_entry = config_entry
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

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
        
        # Add timestamp of last successful price fetch
        last_price_timestamp = self.coordinator.data.get("last_price_timestamp")
        if last_price_timestamp:
            attributes["last_update_timestamp"] = last_price_timestamp
        
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
    _attr_has_entity_name = True

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
        self._attr_name = "Tank Level"
        self._attr_unique_id = f"{config_entry.entry_id}_tank_level"
        self._config_entry = config_entry
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

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
        
        # Include tank capacity from config for use in Lovelace card validation
        options = self._config_entry.options
        config = self._config_entry.data
        tank_capacity = options.get(CONF_TANK_CAPACITY) or config.get(CONF_TANK_CAPACITY, DEFAULT_TANK_CAPACITY)
        attributes["tank_capacity"] = tank_capacity
        
        return attributes


class RangeSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing estimated range."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:map-marker-distance"
    _attr_has_entity_name = True

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
        self._attr_name = "Range"
        self._attr_unique_id = f"{config_entry.entry_id}_range"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

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
    _attr_has_entity_name = True

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
        self._attr_name = "Cheapest Station"
        self._attr_unique_id = f"{config_entry.entry_id}_nearest_station"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

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
        
        # Add timestamp of last successful station fetch
        last_station_timestamp = self.coordinator.data.get("last_station_timestamp")
        if last_station_timestamp:
            attributes["last_update_timestamp"] = last_station_timestamp
        
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
    _attr_has_entity_name = True

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
        self._attr_name = "API Debug"
        self._attr_unique_id = f"{config_entry.entry_id}_api_debug"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

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


class ConsumptionPredictionSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing days until refueling is needed based on consumption prediction."""

    _attr_icon = "mdi:fuel"
    _attr_native_unit_of_measurement = "days"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

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
        self._config_entry = config_entry
        self._attr_name = "Days Until Refuel"
        self._attr_unique_id = f"{config_entry.entry_id}_days_until_refuel"
        self._last_prediction_update = None
        self._last_known_value = None
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    @property
    def native_value(self) -> float | None:
        """Return the days until refueling is needed."""
        prediction = self.coordinator.data.get("consumption_prediction")
        if prediction:
            days = prediction.get("days_until_refuel")
            if days is not None:
                self._last_known_value = days
                return days
        # Fallback to last known value if current value is None
        return self._last_known_value
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional prediction attributes."""
        prediction = self.coordinator.data.get("consumption_prediction")
        if not prediction:
            return {
                ATTR_DATA_SOURCE: "no_data",
                "status": "Waiting for initial prediction",
            }
        
        # Get min data points configuration
        from .const import CONF_CONSUMPTION_MIN_DATA_POINTS, DEFAULT_CONSUMPTION_MIN_DATA_POINTS
        options = self._config_entry.options
        config = self._config_entry.data
        min_data_points = options.get(CONF_CONSUMPTION_MIN_DATA_POINTS) or config.get(
            CONF_CONSUMPTION_MIN_DATA_POINTS, DEFAULT_CONSUMPTION_MIN_DATA_POINTS
        )
        
        attributes = {
            ATTR_DATA_SOURCE: prediction.get("data_source", "unknown"),
            ATTR_CONFIDENCE: prediction.get("confidence", 0.0),
            ATTR_AVG_DAILY_KM: prediction.get("avg_daily_km", 0.0),
            ATTR_AVG_CONSUMPTION_RATE: prediction.get("avg_consumption_rate", 0.0),
            ATTR_DATA_POINTS_USED: prediction.get("data_points_used", 0),
        }
        
        # Calculate and add data points percentage
        data_points_used = prediction.get("data_points_used", 0)
        if min_data_points > 0:
            data_points_percentage = min(100.0, (data_points_used / min_data_points) * 100)
            attributes["data_points_percentage"] = round(data_points_percentage, 1)
            attributes["data_points_required"] = min_data_points
        else:
            attributes["data_points_percentage"] = 0.0
            attributes["data_points_required"] = min_data_points
        
        # Add last prediction time
        if prediction.get("last_prediction_time"):
            attributes[ATTR_LAST_PREDICTION] = prediction["last_prediction_time"].isoformat()
        
        # Add predicted refuel date
        if prediction.get("predicted_refuel_date"):
            attributes[ATTR_PREDICTED_REFUEL_DATE] = prediction["predicted_refuel_date"].isoformat()
        
        return attributes


class ConsumptionHistorySensor(CoordinatorEntity, SensorEntity):
    """Sensor showing average consumption based on historical data."""

    _attr_icon = "mdi:chart-line"
    _attr_native_unit_of_measurement = "L/100km"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = None
    _attr_has_entity_name = True

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
        self._config_entry = config_entry
        self._attr_name = "Average Consumption History"
        self._attr_unique_id = f"{config_entry.entry_id}_consumption_history"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    @property
    def native_value(self) -> float | None:
        """Return the overall average consumption based on available historical data.
        
        Prioritizes longer time periods for more accurate overall average:
        1. Last month (if available)
        2. Last 14 days (if available)
        3. Last week (if available)
        4. Today (as fallback)
        """
        history = self.coordinator.data.get("consumption_history")
        if not history:
            return None
        
        # Try to get the most comprehensive average, prioritizing longer periods
        # Use a loop to eliminate duplication
        for period_key in ["last_month", "last_14_days", "last_week", "today"]:
            period_data = history.get(period_key)
            if period_data:
                consumption = period_data.get("avg_consumption_l_per_100km")
                if consumption is not None:
                    return round(consumption, 2)
        
        return None
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return consumption statistics for different time periods."""
        history = self.coordinator.data.get("consumption_history")
        if not history:
            return {
                "today": None,
                "last_week": None,
                "last_14_days": None,
                "last_month": None,
                "status": "Waiting for refueling data",
            }
        
        attributes = {}
        
        # Today's consumption
        if history.get("today"):
            today = history["today"]
            attributes["today_consumption"] = today.get("avg_consumption_l_per_100km")
            attributes["today_km"] = today.get("total_km", 0)
            attributes["today_liters"] = today.get("total_liters", 0)
            attributes["today_refuel_count"] = today.get("refuel_count", 0)
        
        # Last week
        if history.get("last_week"):
            week = history["last_week"]
            attributes["last_week_consumption"] = week.get("avg_consumption_l_per_100km")
            attributes["last_week_km"] = week.get("total_km", 0)
            attributes["last_week_liters"] = week.get("total_liters", 0)
            attributes["last_week_refuel_count"] = week.get("refuel_count", 0)
        
        # Last 14 days
        if history.get("last_14_days"):
            two_weeks = history["last_14_days"]
            attributes["last_14_days_consumption"] = two_weeks.get("avg_consumption_l_per_100km")
            attributes["last_14_days_km"] = two_weeks.get("total_km", 0)
            attributes["last_14_days_liters"] = two_weeks.get("total_liters", 0)
            attributes["last_14_days_refuel_count"] = two_weeks.get("refuel_count", 0)
        
        # Last month
        if history.get("last_month"):
            month = history["last_month"]
            attributes["last_month_consumption"] = month.get("avg_consumption_l_per_100km")
            attributes["last_month_km"] = month.get("total_km", 0)
            attributes["last_month_liters"] = month.get("total_liters", 0)
            attributes["last_month_refuel_count"] = month.get("refuel_count", 0)
        
        return attributes


class ConsumptionForecastSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing forecasted average consumption based on prediction engine."""

    _attr_icon = "mdi:chart-timeline-variant"
    _attr_native_unit_of_measurement = "L/100km"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = None
    _attr_has_entity_name = True

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
        self._config_entry = config_entry
        self._attr_name = "Average Consumption Forecast"
        self._attr_unique_id = f"{config_entry.entry_id}_consumption_forecast"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    @property
    def native_value(self) -> float | None:
        """Return the forecasted consumption for tomorrow."""
        forecast = self.coordinator.data.get("consumption_forecast")
        if forecast and forecast.get("tomorrow"):
            return forecast["tomorrow"].get("avg_consumption_l_per_100km")
        return None
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return forecasted consumption for different time periods."""
        forecast = self.coordinator.data.get("consumption_forecast")
        if not forecast:
            return {
                "tomorrow": None,
                "next_week": None,
                "next_14_days": None,
                "next_month": None,
                "status": "Waiting for prediction data",
            }
        
        attributes = {}
        
        # Tomorrow's forecast
        if forecast.get("tomorrow"):
            tomorrow = forecast["tomorrow"]
            attributes["tomorrow_consumption"] = tomorrow.get("avg_consumption_l_per_100km")
            attributes["tomorrow_confidence"] = tomorrow.get("confidence", 0.0)
            attributes["tomorrow_data_source"] = tomorrow.get("data_source", "unknown")
        
        # Next week
        if forecast.get("next_week"):
            week = forecast["next_week"]
            attributes["next_week_consumption"] = week.get("avg_consumption_l_per_100km")
            attributes["next_week_confidence"] = week.get("confidence", 0.0)
            attributes["next_week_data_source"] = week.get("data_source", "unknown")
        
        # Next 14 days
        if forecast.get("next_14_days"):
            two_weeks = forecast["next_14_days"]
            attributes["next_14_days_consumption"] = two_weeks.get("avg_consumption_l_per_100km")
            attributes["next_14_days_confidence"] = two_weeks.get("confidence", 0.0)
            attributes["next_14_days_data_source"] = two_weeks.get("data_source", "unknown")
        
        # Next month
        if forecast.get("next_month"):
            month = forecast["next_month"]
            attributes["next_month_consumption"] = month.get("avg_consumption_l_per_100km")
            attributes["next_month_confidence"] = month.get("confidence", 0.0)
            attributes["next_month_data_source"] = month.get("data_source", "unknown")
        
        return attributes


class RefuelingLogSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing refueling events log with detailed information.
    
    Displays the total number of refueling events as the state and provides
    detailed information about each refueling event in the attributes.
    This allows users to review and track their refueling history.
    """

    _attr_icon = "mdi:gas-station"
    _attr_state_class = None
    _attr_device_class = None
    _attr_has_entity_name = True

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
        self._config_entry = config_entry
        self._attr_name = "Refueling Log"
        self._attr_unique_id = f"{config_entry.entry_id}_refueling_log"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    @property
    def native_value(self) -> int:
        """Return the total number of refueling events."""
        refueling_log = self.coordinator.data.get("refueling_log")
        return len(refueling_log) if refueling_log else 0
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed refueling events as attributes.
        
        Returns the last 10 refueling events with all details to allow
        users to review and verify detected refuelings.
        """
        refueling_log = self.coordinator.data.get("refueling_log")
        
        if not refueling_log:
            return {
                "config_entry_id": self._config_entry.entry_id,
                "total_events": 0,
                "last_refueling": None,
                "recent_events": [],
                "status": "No refueling events recorded",
            }
        
        # Filter out events without timestamps and sort by timestamp (newest first)
        # Use a sentinel value that sorts to the beginning (will be at end after reverse)
        events_with_timestamps = [e for e in refueling_log if e.get("timestamp")]
        sorted_log = sorted(
            events_with_timestamps,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        # Get the last 10 events for display
        recent_events = []
        for event in sorted_log[:10]:
            event_info = {
                "id": event.get("id"),
                "timestamp": event.get("timestamp"),
                "odometer_km": event.get("odometer_km"),
                "liters_refueled": event.get("liters_refueled"),
                "price_per_liter": event.get("price_per_liter"),
                "total_cost": event.get("total_cost"),
                "station_name": event.get("station_name"),
                "station_address": event.get("station_address"),
                "fuel_type": event.get("fuel_type"),
                "data_quality": event.get("data_quality", "manual"),
                "confidence": event.get("confidence", 1.0),
            }
            recent_events.append(event_info)
        
        # Get the most recent refueling
        last_refueling = None
        if sorted_log:
            last_event = sorted_log[0]
            last_refueling = {
                "timestamp": last_event.get("timestamp"),
                "liters": last_event.get("liters_refueled"),
                "cost": last_event.get("total_cost"),
                "station": last_event.get("station_name"),
            }
        
        return {
            "config_entry_id": self._config_entry.entry_id,
            "total_events": len(refueling_log),
            "last_refueling": last_refueling,
            "recent_events": recent_events,
            "status": f"{len(refueling_log)} refueling events recorded",
        }


class NearbyCheapStationsSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing nearby cheap fuel stations based on vehicle location."""
    
    _attr_icon = "mdi:map-marker-multiple"
    _attr_state_class = None
    _attr_device_class = None
    _attr_has_entity_name = True
    
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
        self._config_entry = config_entry
        self._vehicle_name = vehicle_name
        
        # Generate unique ID
        self._attr_unique_id = f"{config_entry.entry_id}_nearby_cheap_stations"
        self._attr_name = "Nearby Cheap Stations"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    @property
    def native_value(self) -> int | None:
        """Return the number of nearby cheap stations."""
        if not self.coordinator.data:
            return None
        
        nearby_data = self.coordinator.data.get("nearby_cheap_stations")
        if not nearby_data:
            return 0
        
        return nearby_data.get("count", 0)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}
        
        nearby_data = self.coordinator.data.get("nearby_cheap_stations")
        if not nearby_data:
            return {
                "stations": [],
                "search_radius_km": None,
                "vehicle_latitude": None,
                "vehicle_longitude": None,
                "max_stations": None,
            }
        
        return {
            "stations": nearby_data.get("stations", []),
            "search_radius_km": nearby_data.get("search_radius_km"),
            "vehicle_latitude": nearby_data.get("vehicle_latitude"),
            "vehicle_longitude": nearby_data.get("vehicle_longitude"),
            "max_stations": nearby_data.get("max_stations"),
        }
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


