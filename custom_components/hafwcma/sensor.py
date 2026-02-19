"""Sensor platform for haFWCMA integration."""
from __future__ import annotations

import aiohttp
import heapq
import logging
import random
import sys
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_AVG_CONSUMPTION_RATE,
    ATTR_AVG_DAILY_KM,
    ATTR_CONFIDENCE,
    ATTR_DATA_POINTS_USED,
    ATTR_DATA_SOURCE,
    ATTR_DAYS_LEFT,
    ATTR_DISTANCE,
    ATTR_ENTITY_DATA_SOURCE,
    ATTR_ENTITY_DEPENDENCIES,
    ATTR_ENTITY_DOCUMENTATION_URL,
    ATTR_ENTITY_PURPOSE,
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
    CONF_CHEAP_NEAR_STATIONS_RADIUS,
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
    CONF_RANGE_ENTITY,
    CONF_TANK_CAPACITY,
    CONF_TANK_LEVEL_ENTITY,
    CONF_UPDATE_INTERVAL,
    CONF_VEHICLE_NAME,
    DEFAULT_CHEAP_STATIONS_COUNT,
    DEFAULT_CHEAP_STATIONS_RADIUS,
    DEFAULT_CHEAP_NEAR_STATIONS_RADIUS,
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
from .entity_metadata import get_entity_metadata
from .providers.tankerkonig import TankerkoenigProvider
from .utils.vehicle_data import async_get_vehicle_data, async_wait_for_entities
from .utils.vehicle_tracker import VehicleDataTracker
from .utils import storage
from .utils.storage import recalculate_trip_statistics
from .utils.consumption_prediction import predict_days_until_refuel, store_prediction_result
from .utils.prediction_engine import evaluate_refuel_strategy, get_prediction_summary
from .utils.price_engine import compute_price_trend, get_price_statistics
from .utils.price_statistics_engine import calculate_price_statistics
from .utils.statistics_engine import estimate_days_left
from .utils.geolocation import (
    ProximityTracker,
    enrich_station_data,
    find_nearest_cheap_station,
    format_alert_message,
    get_navigation_urls,
)
from .utils.refuel_recommendation_engine import (
    PositionTracker,
    compare_stations_by_radius,
    analyze_forecast_recommendation,
    DEFAULT_AVG_CONSUMPTION,
)

_LOGGER = logging.getLogger(__name__)

# Station recommendation constants
# Minimum savings in EUR required to recommend driving to a farther station
STATION_RECOMMENDATION_MIN_SAVINGS = 0.50  # EUR

# Constants for tank percentage validation
MIN_TANK_PERCENTAGE = 0.0
MAX_TANK_PERCENTAGE = 100.0

# Constants for historical import defaults
DEFAULT_HISTORICAL_IMPORT_TIMESTAMP = None
DEFAULT_HISTORICAL_IMPORT_TYPE = "none"

# State restoration and data staleness constants
DATA_STALENESS_THRESHOLD_HOURS = 1  # Hours before showing staleness warning
STATE_RESTORED_DATA_SOURCE = "restored_from_previous_state"  # Data source marker for restored state


def check_data_staleness(timestamp: str | datetime | None, data_type: str) -> str | None:
    """Check if data timestamp indicates stale data and return warning message.
    
    The function accepts timestamps in any format that Home Assistant's dt_util.parse_datetime
    can handle, including ISO 8601 formats (e.g., '2024-01-15T10:30:00+00:00'), or datetime objects.
    
    Args:
        timestamp: Datetime string (ISO 8601 or other standard formats),
                  datetime object (used directly without parsing), or None
        data_type: Description of the data type (e.g., "Vehicle data", "Fuel price data")
        
    Returns:
        Warning message if data is stale (older than threshold), None otherwise
    """
    if not timestamp:
        return None
        
    try:
        if isinstance(timestamp, str):
            last_update = dt_util.parse_datetime(timestamp)
        else:
            last_update = timestamp
        
        if last_update:
            age = dt_util.now() - last_update
            if age > timedelta(hours=DATA_STALENESS_THRESHOLD_HOURS):
                hours_old = age.total_seconds() / 3600
                return f"{data_type} is {hours_old:.1f} hours old"
    except (ValueError, TypeError, AttributeError) as err:
        _LOGGER.debug("Could not calculate data age for %s: %s", data_type, err)
    
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up haFWCMA sensors from a config entry.
    
    This function follows Home Assistant best practices:
    - Returns immediately without blocking HA startup
    - Sensors start in unavailable state
    - First data refresh happens after HA is fully started
    
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

    vehicle_name = config_entry.data.get(CONF_VEHICLE_NAME, "Vehicle")

    sensors = [
        FuelPriceSensor(coordinator, config_entry, vehicle_name),
        TankLevelSensor(coordinator, config_entry, vehicle_name),
        RangeSensor(coordinator, config_entry, vehicle_name),
        NearestStationSensor(coordinator, config_entry, vehicle_name),
        FuelPriceApiDebugSensor(coordinator, config_entry, vehicle_name),
        CarDataDebugSensor(coordinator, config_entry, vehicle_name),
        ConsumptionPredictionSensor(coordinator, config_entry, vehicle_name),
        ConsumptionHistorySensor(coordinator, config_entry, vehicle_name),
        ConsumptionForecastSensor(coordinator, config_entry, vehicle_name),
        RefuelingLogSensor(coordinator, config_entry, vehicle_name),
        NearbyCheapStationsSensor(coordinator, config_entry, vehicle_name),
        TripLogSensor(coordinator, config_entry, vehicle_name),
        CurrentTripSensor(coordinator, config_entry, vehicle_name),
    ]

    # Add entities immediately - they will start in unavailable state
    async_add_entities(sensors)
    
    # Schedule first refresh after HA is fully started to avoid blocking startup
    async def _first_refresh_when_started(event):
        """Perform first data refresh after HA is fully started."""
        _LOGGER.info("Home Assistant started - performing first data refresh for %s", vehicle_name)
        try:
            await coordinator.async_refresh()
        except Exception as err:
            _LOGGER.error("Error during first refresh for %s: %s", vehicle_name, err, exc_info=True)
    
    # Listen for HA startup completion event
    hass.bus.async_listen_once("homeassistant_started", _first_refresh_when_started)
    
    _LOGGER.info("haFWCMA sensors registered successfully - first refresh will occur after HA startup")



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
        
        # Get tank capacity from config for percentage-based refueling detection
        tank_capacity = options.get(CONF_TANK_CAPACITY) or config.get(
            CONF_TANK_CAPACITY, DEFAULT_TANK_CAPACITY
        )
        self.vehicle_tracker = VehicleDataTracker(tank_capacity=tank_capacity)
        self.trip_tracker = None  # Will be initialized when trip tracking is enabled
        
        self._provider = None
        self._session = None
        self._api_debug_info = None  # Store debug info about API requests/responses
        self._last_consumption_prediction = None  # Store last consumption prediction time
        self._last_missed_trip_check = None  # Track when we last checked for missed trips
        self._last_missed_refueling_check = None  # Track when we last checked for missed refuelings
        self._proximity_tracker = ProximityTracker(
            cooldown_seconds=GEOLOCATION_ALERT_COOLDOWN,
            hysteresis_factor=GEOLOCATION_HYSTERESIS_FACTOR,
        )  # Track proximity alerts
        self._position_tracker = PositionTracker()  # Track position changes for recommendation cooldown
        
        # Entity availability and caching
        self._cached_vehicle_data = {}  # Cache last known vehicle data
        self._cached_consumption_prediction = None  # Cache last known prediction
        self._entities_available = False  # Track if vehicle entities are available
        self._first_successful_fetch = False  # Track if we've had a successful vehicle data fetch
        
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

    def force_consumption_prediction_update(self) -> None:
        """Force consumption prediction to be recalculated on next coordinator update.
        
        This resets the prediction interval timer, causing predictions to be
        recalculated immediately on the next coordinator update cycle.
        Used by the recalculate button to force fresh predictions.
        """
        _LOGGER.info("Forcing consumption prediction update on next coordinator refresh")
        self._last_consumption_prediction = None

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

    async def _check_vehicle_entities_available(self) -> None:
        """Check if vehicle entities are available without blocking.
        
        This method checks if the configured vehicle entities exist.
        It does not wait or retry - just checks once and updates the flag.
        """
        if self._entities_available:
            # Already checked and found entities
            return
        
        config = self.config_entry.data
        options = self.config_entry.options
        
        # Get entity IDs from options first, then config
        odometer_entity = options.get(CONF_ODOMETER_ENTITY) or config.get(CONF_ODOMETER_ENTITY)
        tank_level_entity = options.get(CONF_TANK_LEVEL_ENTITY) or config.get(CONF_TANK_LEVEL_ENTITY)
        range_entity = options.get(CONF_RANGE_ENTITY) or config.get(CONF_RANGE_ENTITY)
        position_entity = options.get(CONF_POSITION_ENTITY) or config.get(CONF_POSITION_ENTITY)
        
        # Filter out None/empty entity IDs
        entity_ids = [e for e in [odometer_entity, tank_level_entity, range_entity, position_entity] if e]
        
        if not entity_ids:
            _LOGGER.debug("No vehicle entities configured")
            self._entities_available = True  # No entities to wait for
            return
        
        # Check if at least one entity exists
        found_any = False
        for entity_id in entity_ids:
            if self.hass.states.get(entity_id) is not None:
                found_any = True
                break
        
        if found_any:
            _LOGGER.info("Vehicle entities are now available")
            self._entities_available = True
        else:
            _LOGGER.debug("Vehicle entities not yet available - sensors will remain unavailable until entities exist")

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
        
        # Don't run prediction until we've successfully fetched vehicle data at least once
        if not self._first_successful_fetch:
            _LOGGER.debug(
                "Skipping consumption prediction - waiting for first successful vehicle data fetch"
            )
            return self._cached_consumption_prediction
        
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
        
        # Debug logging before calling prediction
        _LOGGER.debug(
            "Calling predict_days_until_refuel with: range_km=%.2f, tank_level=%.2f, tank_capacity=%.2f, "
            "fallback_daily_km=%.2f, fallback_consumption_rate=%.2f",
            range_km if range_km is not None else -1,
            tank_level if tank_level is not None else -1,
            tank_capacity,
            fallback_daily_km,
            fallback_consumption_rate
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
        
        # Cache the prediction for startup delay usage
        self._cached_consumption_prediction = prediction
        
        # Store prediction result for accuracy tracking
        await store_prediction_result(self.hass, self.config_entry, prediction)
        
        # Calculate forecast recommendation based on predicted refuel date
        forecast_recommendation = None
        predicted_refuel_date = prediction.get("predicted_refuel_date")
        fuel_price = self.data.get("fuel_price") if self.data else None
        
        if predicted_refuel_date and fuel_price:
            try:
                forecast_recommendation = await analyze_forecast_recommendation(
                    self.hass,
                    self.config_entry,
                    predicted_refuel_date,
                    fuel_price,
                )
                _LOGGER.debug("Forecast recommendation: %s", forecast_recommendation)
            except Exception as forecast_err:
                _LOGGER.warning("Error calculating forecast recommendation: %s", forecast_err)
        
        # Add forecast recommendation to prediction
        if forecast_recommendation:
            prediction["forecast_recommendation"] = forecast_recommendation
        
        _LOGGER.info(
            "Consumption prediction updated: %.1f days until refuel (source: %s, confidence: %.2f)",
            prediction.get("days_until_refuel") or 0,
            prediction.get("data_source"),
            prediction.get("confidence") or 0,
        )
        
        # Debug log the full prediction result
        _LOGGER.debug("Full prediction result: %s", prediction)
        
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
        
        Uses ML prediction engine to forecast consumption patterns. Includes cost forecasts
        based on historical price data and expected consumption. Uses weekday driving patterns
        to provide more accurate forecasts for different time periods.
        
        Args:
            consumption_prediction: Current consumption prediction data
            
        Returns:
            Dictionary with consumption forecasts for tomorrow, next week, next 14 days, next month
        """
        from datetime import timedelta
        from .utils.storage import get_last_refuel_price, calculate_average_price
        from homeassistant.util import dt as dt_util
        
        if not consumption_prediction:
            periods = ["tomorrow", "next_week", "next_14_days", "next_month"]
            return {period: None for period in periods}
        
        # Get average consumption rate and confidence from prediction
        avg_consumption_rate = consumption_prediction.get("avg_consumption_rate")
        avg_daily_km = consumption_prediction.get("avg_daily_km", 0.0)
        confidence = consumption_prediction.get("confidence", 0.0)
        data_source = consumption_prediction.get("data_source", "unknown")
        weekday_pattern = consumption_prediction.get("weekday_pattern", {})
        
        if not avg_consumption_rate:
            periods = ["tomorrow", "next_week", "next_14_days", "next_month"]
            return {period: None for period in periods}
        
        # Get price data for cost forecasting
        last_price = await get_last_refuel_price(self.hass, self.config_entry)
        avg_price_7d = await calculate_average_price(self.hass, self.config_entry, days=7)
        avg_price_14d = await calculate_average_price(self.hass, self.config_entry, days=14)
        avg_price_30d = await calculate_average_price(self.hass, self.config_entry, days=30)
        
        # Helper function to calculate expected km for a specific weekday
        def get_weekday_km(weekday_idx: int) -> float:
            """Get expected km for a specific weekday."""
            if weekday_pattern and weekday_idx in weekday_pattern:
                return weekday_pattern[weekday_idx]
            return avg_daily_km  # Fallback to average
        
        # Helper function to calculate weighted km for a period
        def calculate_period_km(days: int, start_weekday: int) -> float:
            """Calculate weighted average km for a period based on weekday patterns."""
            if not weekday_pattern:
                # No pattern available, use simple average
                return avg_daily_km * days
            
            # Use modulo arithmetic to calculate weekdays efficiently
            total_km = 0.0
            for day_offset in range(days):
                weekday = (start_weekday + day_offset) % 7
                total_km += get_weekday_km(weekday)
            
            return total_km
        
        # Tomorrow (1 day) - use tomorrow's specific weekday pattern
        now = dt_util.now()
        tomorrow = now + timedelta(days=1)
        tomorrow_weekday = tomorrow.weekday()
        tomorrow_km = get_weekday_km(tomorrow_weekday)
        
        tomorrow_forecast = {
            "avg_consumption_l_per_100km": avg_consumption_rate,
            "confidence": confidence,
            "data_source": data_source,
        }
        if last_price and tomorrow_km > 0:
            liters_needed = (tomorrow_km * avg_consumption_rate) / 100
            tomorrow_forecast["forecast_cost"] = round(liters_needed * last_price, 2)
        
        # Next week (7 days) - use weighted average based on actual weekdays
        next_week_km = calculate_period_km(7, now.weekday())
        next_week_forecast = {
            "avg_consumption_l_per_100km": avg_consumption_rate,
            "confidence": confidence,
            "data_source": data_source,
        }
        if avg_price_7d and next_week_km > 0:
            liters_needed = (next_week_km * avg_consumption_rate) / 100
            next_week_forecast["forecast_cost"] = round(liters_needed * avg_price_7d, 2)
        
        # Next 14 days - use weighted average based on actual weekdays
        next_14_days_km = calculate_period_km(14, now.weekday())
        next_14_days_forecast = {
            "avg_consumption_l_per_100km": avg_consumption_rate,
            "confidence": confidence,
            "data_source": data_source,
        }
        if avg_price_14d and next_14_days_km > 0:
            liters_needed = (next_14_days_km * avg_consumption_rate) / 100
            next_14_days_forecast["forecast_cost"] = round(liters_needed * avg_price_14d, 2)
        
        # Next month (30 days) - use weighted average based on actual weekdays
        next_month_km = calculate_period_km(30, now.weekday())
        next_month_forecast = {
            "avg_consumption_l_per_100km": avg_consumption_rate,
            "confidence": confidence,
            "data_source": data_source,
        }
        if avg_price_30d and next_month_km > 0:
            liters_needed = (next_month_km * avg_consumption_rate) / 100
            next_month_forecast["forecast_cost"] = round(liters_needed * avg_price_30d, 2)
        
        return {
            "tomorrow": tomorrow_forecast,
            "next_week": next_week_forecast,
            "next_14_days": next_14_days_forecast,
            "next_month": next_month_forecast,
        }

    async def _check_for_missed_trips(self) -> None:
        """Periodically check for missed trips in odometer history.
        
        This method checks for trips that may have been missed due to gaps in tracking.
        It's called periodically during updates to catch trips that weren't detected in real-time.
        The check runs at most once per hour to avoid excessive processing.
        """
        from homeassistant.util import dt as dt_util
        
        # Only check if trip tracking is enabled
        if self.trip_tracker is None:
            return
        
        # Check at most once per hour to avoid excessive processing
        now = dt_util.now()
        if self._last_missed_trip_check is not None:
            time_since_last_check = (now - self._last_missed_trip_check).total_seconds() / 3600  # hours
            if time_since_last_check < 1.0:
                _LOGGER.debug("Skipping missed trip check - last check was %.1f minutes ago", time_since_last_check * 60)
                return
        
        try:
            _LOGGER.debug("Checking for missed trips in odometer history")
            
            # Load data
            data = await storage.load_data(self.hass, self.config_entry)
            trip_config = data.get("trip_tracking_config", {})
            
            if not trip_config.get("enabled", False):
                return
            
            odometer_history = data.get("odometer_history", [])
            existing_trips = data.get("trips", [])
            
            # Build set of existing trip timestamps
            existing_timestamps = set()
            for trip in existing_trips:
                if trip.get("timestamp_start"):
                    try:
                        ts = dt_util.parse_datetime(trip["timestamp_start"])
                        if ts:
                            if ts.tzinfo is None:
                                ts = dt_util.as_local(ts)
                            existing_timestamps.add(ts)
                    except Exception as err:
                        _LOGGER.debug(
                            "Failed to parse trip timestamp '%s': %s",
                            trip.get("timestamp_start"),
                            err,
                        )
            
            # Detect missed trips from recent history
            from .utils.vehicle_tracker import detect_missed_trips_from_history
            min_distance = trip_config.get("min_trip_distance_km", 0.5)
            lookback_hours = trip_config.get("missed_trip_lookback_hours", 24)
            
            missed_trips = detect_missed_trips_from_history(
                odometer_history=odometer_history,
                existing_trip_timestamps=existing_timestamps,
                min_trip_distance_km=min_distance,
                lookback_hours=lookback_hours,
            )
            
            if missed_trips:
                _LOGGER.info(
                    "Found %d missed trip(s) in odometer history - recovering",
                    len(missed_trips),
                )
                
                # Initialize trips list if not present
                if "trips" not in data:
                    data["trips"] = []
                
                # Get next trip ID
                next_id = data.get("next_trip_id", 1)
                now_str = now.isoformat()
                
                for trip_data_item in missed_trips:
                    try:
                        # Assign trip ID
                        trip_data_item["trip_id"] = next_id
                        next_id += 1
                        
                        # Add timestamps
                        trip_data_item.setdefault("created_at", now_str)
                        trip_data_item.setdefault("updated_at", now_str)
                        
                        # Add note about recovery
                        if "notes" not in trip_data_item:
                            trip_data_item["notes"] = "Auto-recovered from odometer history during periodic check"
                        
                        # Add trip to storage
                        data["trips"].append(trip_data_item)
                        
                        _LOGGER.info(
                            "Recovered trip #%d: %.1f km (%.1f → %.1f km) at %s",
                            trip_data_item["trip_id"],
                            trip_data_item.get("distance_km", 0),
                            trip_data_item.get("odometer_start", 0),
                            trip_data_item.get("odometer_end", 0),
                            trip_data_item.get("timestamp_start", "unknown"),
                        )
                    except Exception as err:
                        _LOGGER.warning("Error saving recovered trip: %s", err)
                
                # Update next trip ID
                data["next_trip_id"] = next_id
                
                # Save the new trips to storage first
                await storage.save_data(self.hass, self.config_entry, data)
                
                # Recalculate trip statistics to include new trips
                # This will update trip_statistics in storage
                await recalculate_trip_statistics(self.hass, self.config_entry)
                
                _LOGGER.info(
                    "Saved %d recovered trip(s) to storage. Will be reflected in current update cycle.",
                    len(missed_trips)
                )
            else:
                _LOGGER.debug("No missed trips found in odometer history")
            
            # Update last check timestamp
            self._last_missed_trip_check = now
            
        except Exception as err:
            _LOGGER.warning("Error checking for missed trips: %s", err)

    async def _check_for_missed_refuelings(self) -> None:
        """Periodically check for missed refuelings in tank level history.
        
        This method checks for refueling events that may have been missed due to gaps in tracking.
        It's called periodically during updates to catch refuelings that weren't detected in real-time.
        The check runs at most once per hour to avoid excessive processing.
        """
        from homeassistant.util import dt as dt_util
        
        # Check at most once per hour to avoid excessive processing
        now = dt_util.now()
        if self._last_missed_refueling_check is not None:
            time_since_last_check = (now - self._last_missed_refueling_check).total_seconds() / 3600  # hours
            if time_since_last_check < 1.0:
                _LOGGER.debug("Skipping missed refueling check - last check was %.1f minutes ago", time_since_last_check * 60)
                return
        
        try:
            _LOGGER.debug("Checking for missed refuelings in tank level history")
            
            # Load data
            data = await storage.load_data(self.hass, self.config_entry)
            
            # Get tank level history
            tank_level_history = data.get("tank_level_history", [])
            
            if not tank_level_history or len(tank_level_history) < 2:
                _LOGGER.debug("Not enough tank level history for missed refueling detection")
                return
            
            # Get existing refueling events
            refueling_log = data.get("refueling_log", [])
            
            # Build set of existing refueling timestamps
            existing_timestamps = set()
            for refuel in refueling_log:
                if refuel.get("timestamp"):
                    try:
                        ts = dt_util.parse_datetime(refuel["timestamp"])
                        if ts:
                            if ts.tzinfo is None:
                                ts = dt_util.as_local(ts)
                            existing_timestamps.add(ts)
                    except Exception as err:
                        _LOGGER.debug(
                            "Failed to parse refueling timestamp '%s': %s",
                            refuel.get("timestamp"),
                            err,
                        )
            
            # Get tank capacity from config
            options = self.config_entry.options
            config = self.config_entry.data
            tank_capacity = options.get(CONF_TANK_CAPACITY) or config.get(CONF_TANK_CAPACITY, DEFAULT_TANK_CAPACITY)
            
            # Detect missed refuelings from recent history
            from .utils.vehicle_tracker import detect_missed_refuelings_from_history, DEFAULT_MISSED_REFUELING_LOOKBACK_HOURS
            
            missed_refuelings = detect_missed_refuelings_from_history(
                tank_level_history=tank_level_history,
                existing_refuel_timestamps=existing_timestamps,
                tank_capacity=tank_capacity,
                min_refuel_threshold_percent=3.5,  # Same as VehicleDataTracker
                lookback_hours=DEFAULT_MISSED_REFUELING_LOOKBACK_HOURS,
            )
            
            if missed_refuelings:
                _LOGGER.info(
                    "Found %d missed refueling(s) in tank level history - recovering",
                    len(missed_refuelings),
                )
                
                # Get default fuel type from config
                fuel_type = options.get(CONF_FUEL_TYPE) or config.get(CONF_FUEL_TYPE, "e5")
                
                for refuel_event in missed_refuelings:
                    try:
                        # Set fuel type from config if not set
                        if not refuel_event.get("fuel_type"):
                            refuel_event["fuel_type"] = fuel_type
                        
                        # Add note about recovery
                        refuel_event["notes"] = "Auto-recovered from tank level history during periodic check"
                        
                        # Store refueling event
                        refuel_id = await storage.add_refuel_event(
                            self.hass,
                            self.config_entry,
                            refuel_event,
                        )
                        
                        _LOGGER.info(
                            "Recovered refueling event #%d: %.1f L at %s (odometer: %s km)",
                            refuel_id,
                            refuel_event.get("liters_refueled", 0),
                            refuel_event.get("timestamp", "unknown"),
                            f"{refuel_event.get('odometer_km'):.1f}" if refuel_event.get("odometer_km") else "unknown",
                        )
                    except Exception as err:
                        _LOGGER.warning("Error saving recovered refueling: %s", err)
                
                _LOGGER.info(
                    "Saved %d recovered refueling(s) to storage. Will be reflected in current update cycle.",
                    len(missed_refuelings)
                )
            else:
                _LOGGER.debug("No missed refuelings found in tank level history")
            
            # Update last check timestamp
            self._last_missed_refueling_check = now
            
        except Exception as err:
            _LOGGER.warning("Error checking for missed refuelings: %s", err)

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
        radius = options.get(CONF_CHEAP_STATIONS_RADIUS, DEFAULT_CHEAP_STATIONS_RADIUS)
        
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
            # Check if vehicle entities are available (non-blocking)
            await self._check_vehicle_entities_available()
            
            # Fetch vehicle data from configured entities
            # Use silent mode if entities aren't available yet to avoid spam
            silent_mode = not self._entities_available
            
            vehicle_data = await async_get_vehicle_data(
                self.hass,
                odometer_entity,
                tank_level_entity,
                range_entity,
                position_entity,
                silent=silent_mode,
            )
            
            # Mark first successful fetch if we got any actual data
            # async_get_vehicle_data always returns a dict, check if any value is not None
            if any(v is not None for v in vehicle_data.values()):
                if not self._first_successful_fetch:
                    _LOGGER.info("First successful vehicle data fetch completed")
                    self._first_successful_fetch = True
            
            # Cache the data (defensive check, vehicle_data is always a dict but may be empty)
            if vehicle_data:
                self._cached_vehicle_data = vehicle_data.copy()
            
            _LOGGER.debug("Vehicle data: %s", vehicle_data)
            
            # Calculate tank percentage early for use in geolocation features
            # This needs to be done before proximity alert processing in the geolocation features section
            tank_percentage = None
            tank_level = vehicle_data.get("tank_level")
            tank_level_unit = vehicle_data.get("tank_level_unit")
            # Use explicit None checks to handle edge case where tank_capacity could be 0
            tank_capacity = options.get(CONF_TANK_CAPACITY)
            if tank_capacity is None:
                tank_capacity = config.get(CONF_TANK_CAPACITY)
            if tank_capacity is None:
                tank_capacity = DEFAULT_TANK_CAPACITY
            
            if tank_level is not None:
                # Check if tank level is already a percentage or in liters
                if tank_level_unit and tank_level_unit.lower() in ("%", "percent", "percentage"):
                    # Tank level is already a percentage, use it directly
                    tank_percentage = tank_level
                else:
                    # Tank level is in liters, convert to percentage if we have tank capacity
                    if tank_capacity and tank_capacity > 0:
                        tank_percentage = (tank_level / tank_capacity) * 100
                
                # Clamp tank percentage to valid range (0-100%)
                if tank_percentage is not None:
                    tank_percentage = max(MIN_TANK_PERCENTAGE, min(MAX_TANK_PERCENTAGE, tank_percentage))
            
            # Track vehicle data changes and detect events
            tracking_result = self.vehicle_tracker.update(vehicle_data)
            _LOGGER.debug("Tracking result: %s", tracking_result)
            
            # Store odometer history if available
            odometer = vehicle_data.get("odometer_km")
            if odometer is not None:
                from homeassistant.util import dt as dt_util
                timestamp = dt_util.now().isoformat()
                await storage.add_odometer_observation(
                    self.hass,
                    self.config_entry,
                    odometer,
                    timestamp,
                )
                
                # Track automatic vehicle data refresh
                data = await storage.load_data(self.hass, self.config_entry)
                data["last_vehicle_data_refresh"] = {
                    "timestamp": timestamp,
                    "type": "automatic",
                }
                await storage.save_data(self.hass, self.config_entry, data)
            
            # Store tank level history if available (for missed refueling detection)
            # Record tank level even without odometer - odometer is only supplementary info
            tank_level = vehicle_data.get("tank_level")
            if tank_level is not None:
                from homeassistant.util import dt as dt_util
                timestamp = dt_util.now().isoformat()
                await storage.add_tank_level_observation(
                    self.hass,
                    self.config_entry,
                    tank_level,
                    odometer,  # May be None, which is acceptable
                    timestamp,
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
                                "address": cheapest.address,
                                "city": cheapest.city,
                                "street": cheapest.street,
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
            
            _LOGGER.debug(
                "Geolocation data - lat: %s, lon: %s, position_entity: %s",
                vehicle_lat,
                vehicle_lon,
                position_entity,
            )
            
            if vehicle_lat is not None and vehicle_lon is not None and position_entity:
                try:
                    # Get geolocation configuration
                    proximity_enabled = options.get(CONF_PROXIMITY_ALERTS_ENABLED, DEFAULT_PROXIMITY_ALERTS_ENABLED)
                    cheap_stations_count = options.get(CONF_CHEAP_STATIONS_COUNT, DEFAULT_CHEAP_STATIONS_COUNT)
                    cheap_stations_radius = options.get(CONF_CHEAP_STATIONS_RADIUS, DEFAULT_CHEAP_STATIONS_RADIUS)
                    cheap_near_stations_radius = options.get(CONF_CHEAP_NEAR_STATIONS_RADIUS, DEFAULT_CHEAP_NEAR_STATIONS_RADIUS)
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
                                            "address": station.address,
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
                # Also store price history with station information
                await storage.add_price_observation(
                    self.hass,
                    self.config_entry,
                    fuel_price,
                    timestamp_now,
                    station_id=nearest_station.get("id"),
                    station_name=nearest_station.get("name"),
                    station_brand=nearest_station.get("brand"),
                    station_city=nearest_station.get("city"),
                    station_street=nearest_station.get("street"),
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
        
        # Handle trip tracking
        try:
            # Load trip tracking configuration
            data = await storage.load_data(self.hass, self.config_entry)
            trip_config = data.get("trip_tracking_config", {})
            
            if trip_config.get("enabled", False):
                # Initialize trip tracker if not already done
                if self.trip_tracker is None:
                    from .utils.vehicle_tracker import TripTracker, detect_missed_trips_from_history
                    min_distance = trip_config.get("min_trip_distance_km", 0.5)
                    merge_window = trip_config.get("merge_time_window_seconds", 300)
                    self.trip_tracker = TripTracker(
                        min_trip_distance_km=min_distance,
                        merge_time_window_seconds=merge_window,
                    )
                    _LOGGER.info("Trip tracker initialized")
                    
                    # Check for missed trips in recent odometer history
                    # This handles trips that were missed due to HA restart or integration reload
                    try:
                        odometer_history = data.get("odometer_history", [])
                        existing_trips = data.get("trips", [])
                        
                        # Build set of existing trip timestamps
                        from homeassistant.util import dt as dt_util
                        existing_timestamps = set()
                        for trip in existing_trips:
                            if trip.get("timestamp_start"):
                                try:
                                    ts = dt_util.parse_datetime(trip["timestamp_start"])
                                    if ts:
                                        if ts.tzinfo is None:
                                            ts = dt_util.as_local(ts)
                                        existing_timestamps.add(ts)
                                except Exception as err:
                                    _LOGGER.debug(
                                        "Failed to parse trip timestamp '%s': %s",
                                        trip.get("timestamp_start"),
                                        err,
                                    )
                        
                        # Detect missed trips from recent history
                        # Use configured lookback hours or default to 24
                        lookback_hours = trip_config.get("missed_trip_lookback_hours", 24)
                        missed_trips = detect_missed_trips_from_history(
                            odometer_history=odometer_history,
                            existing_trip_timestamps=existing_timestamps,
                            min_trip_distance_km=min_distance,
                            lookback_hours=lookback_hours,
                        )
                        
                        if missed_trips:
                            _LOGGER.info(
                                "Recovered %d missed trip(s) from recent odometer history",
                                len(missed_trips),
                            )
                            
                            # Save missed trips to storage
                            from .utils.storage import save_data
                            
                            # Initialize trips list if not present
                            if "trips" not in data:
                                data["trips"] = []
                            
                            # Get next trip ID
                            next_id = data.get("next_trip_id", 1)
                            now = dt_util.now().isoformat()
                            
                            for trip_data_item in missed_trips:
                                try:
                                    # Assign trip ID
                                    trip_data_item["trip_id"] = next_id
                                    next_id += 1
                                    
                                    # Add timestamps
                                    trip_data_item.setdefault("created_at", now)
                                    trip_data_item.setdefault("updated_at", now)
                                    
                                    # Add note about recovery
                                    if "notes" not in trip_data_item:
                                        trip_data_item["notes"] = "Auto-recovered from odometer history after system restart"
                                    
                                    # Add trip to storage
                                    data["trips"].append(trip_data_item)
                                    
                                    _LOGGER.debug(
                                        "Saved recovered trip #%d: %.1f km",
                                        trip_data_item["trip_id"],
                                        trip_data_item.get("distance_km", 0),
                                    )
                                except Exception as err:
                                    _LOGGER.warning("Error saving recovered trip: %s", err)
                            
                            # Update next trip ID
                            data["next_trip_id"] = next_id
                            
                            # Save data
                            await save_data(self.hass, self.config_entry, data)
                            
                    except Exception as err:
                        _LOGGER.warning("Error checking for missed trips: %s", err)
                
                # Create snapshot for trip tracking
                from .utils.vehicle_tracker import VehicleSnapshot
                from homeassistant.util import dt as dt_util
                snapshot = VehicleSnapshot(
                    timestamp=dt_util.now(),
                    odometer_km=vehicle_data.get("odometer_km"),
                    tank_level=vehicle_data.get("tank_level"),
                    range_km=vehicle_data.get("range_km"),
                    latitude=vehicle_data.get("latitude"),
                    longitude=vehicle_data.get("longitude"),
                )
                
                # Update trip tracker
                trip_result = self.trip_tracker.update(snapshot)
                
                # Handle trip end - save to storage
                if trip_result.get("trip_ended") and trip_result.get("trip_data"):
                    trip_data = trip_result["trip_data"]
                    
                    # Check if trip should be anonymized based on time
                    from .utils.trip_anonymization import should_anonymize_trip, anonymize_trip_data
                    trip_start_str = trip_data.get("timestamp_start")
                    should_anonymize = False
                    
                    if trip_start_str:
                        try:
                            trip_start_dt = dt_util.parse_datetime(trip_start_str)
                            if trip_start_dt:
                                anonymization_schedules = trip_config.get("anonymization_schedules", [])
                                should_anonymize = should_anonymize_trip(trip_start_dt, anonymization_schedules)
                        except (ValueError, TypeError):
                            pass
                    
                    # Calculate costs
                    fuel_consumed = trip_data.get("fuel_consumed")
                    distance_km = trip_data.get("distance_km", 0)
                    
                    # Calculate fuel cost
                    fuel_cost = 0.0
                    if fuel_consumed and fuel_consumed > 0 and fuel_price:
                        fuel_cost = fuel_consumed * fuel_price
                    
                    # Calculate tax mileage amount
                    tax_rate_default = trip_config.get("tax_mileage_rate_default", 0.30)
                    tax_rate_above_20 = trip_config.get("tax_mileage_rate_above_20km", 0.38)
                    
                    if distance_km <= 20:
                        tax_mileage_amount = distance_km * tax_rate_default
                        tax_rate_used = tax_rate_default
                    else:
                        # First 20 km at default rate, rest at higher rate
                        tax_mileage_amount = (20 * tax_rate_default) + ((distance_km - 20) * tax_rate_above_20)
                        tax_rate_used = tax_rate_default  # Store base rate
                    
                    # Update trip data with costs
                    trip_data.update({
                        "fuel_price_avg": fuel_price,
                        "fuel_cost": fuel_cost,
                        "additional_costs": 0.0,
                        "total_cost": fuel_cost,
                        "tax_mileage_rate": tax_rate_used,
                        "tax_mileage_amount": tax_mileage_amount,
                        "cost_difference": fuel_cost - tax_mileage_amount,
                        "category": "private",  # Default category
                        "is_manual": False,
                    })
                    
                    # Geocode addresses if enabled and coordinates available
                    if trip_config.get("auto_geocode", True):
                        from .utils.geocoding import geocode_trip_location
                        
                        start_lat = trip_data.get("start_latitude")
                        start_lon = trip_data.get("start_longitude")
                        end_lat = trip_data.get("end_latitude")
                        end_lon = trip_data.get("end_longitude")
                        
                        try:
                            if start_lat and start_lon:
                                start_geo = await geocode_trip_location(start_lat, start_lon)
                                if start_geo:
                                    if start_geo.get("location_name"):
                                        trip_data["start_name"] = start_geo["location_name"]
                                    if start_geo.get("address"):
                                        trip_data["start_address"] = start_geo["address"]
                                    _LOGGER.debug("Geocoded start: name=%s, address=%s", 
                                                start_geo.get("location_name"), 
                                                start_geo.get("address"))
                        except Exception as geo_err:
                            _LOGGER.warning("Error geocoding start location: %s", geo_err)
                        
                        try:
                            if end_lat and end_lon:
                                end_geo = await geocode_trip_location(end_lat, end_lon)
                                if end_geo:
                                    if end_geo.get("location_name"):
                                        trip_data["end_name"] = end_geo["location_name"]
                                    if end_geo.get("address"):
                                        trip_data["end_address"] = end_geo["address"]
                                    _LOGGER.debug("Geocoded end: name=%s, address=%s", 
                                                end_geo.get("location_name"), 
                                                end_geo.get("address"))
                        except Exception as geo_err:
                            _LOGGER.warning("Error geocoding end location: %s", geo_err)
                    
                    # Pattern matching
                    try:
                        from homeassistant.util import dt as dt_util
                        from .utils.trip_patterns import find_matching_patterns
                        patterns = data.get("trip_patterns", [])
                        
                        if patterns:
                            matching_patterns = find_matching_patterns(trip_data, patterns)
                            if matching_patterns:
                                # Use the best matching pattern
                                best_pattern = matching_patterns[0]
                                trip_data["pattern_id"] = best_pattern.get("pattern_id")
                                trip_data["category"] = best_pattern.get("category", "private")
                                trip_data["purpose"] = best_pattern.get("purpose")
                                
                                # Apply anonymization if pattern requires it OR time-based rule applies
                                if best_pattern.get("is_anonymized", False) or should_anonymize:
                                    should_anonymize = True
                                
                                # Update pattern statistics
                                for pattern in patterns:
                                    if pattern.get("pattern_id") == best_pattern.get("pattern_id"):
                                        pattern["match_count"] = pattern.get("match_count", 0) + 1
                                        pattern["last_matched"] = dt_util.now().isoformat()
                                        break
                                
                                data["trip_patterns"] = patterns
                                await storage.save_data(self.hass, self.config_entry, data)
                                
                                _LOGGER.info(
                                    "Trip matched pattern: %s (ID: %d)",
                                    best_pattern.get("name"),
                                    best_pattern.get("pattern_id"),
                                )
                    except Exception as pattern_err:
                        _LOGGER.warning("Error matching trip patterns: %s", pattern_err)
                    
                    # Apply anonymization if needed
                    if should_anonymize:
                        trip_data = anonymize_trip_data(trip_data)
                        _LOGGER.info("Trip anonymized based on privacy settings")
                    
                    # Save trip to storage
                    trip_id = await storage.add_trip(self.hass, self.config_entry, trip_data)
                    _LOGGER.info(
                        "Trip #%d saved: %.2f km, duration: %s, fuel: %.2fL, cost: €%.2f, from: %s to: %s",
                        trip_id,
                        distance_km,
                        trip_data.get("duration", "unknown"),
                        fuel_consumed or 0,
                        fuel_cost,
                        trip_data.get("start_address", "Unknown"),
                        trip_data.get("end_address", "Unknown"),
                    )
                    
                # Store trip tracking state in coordinator data
                data["trip_tracking_state"] = {
                    "on_trip": trip_result.get("on_trip", False),
                    "current_trip": self.trip_tracker.get_current_trip_data() if self.trip_tracker else None,
                }
                await storage.save_data(self.hass, self.config_entry, data)
            else:
                # Trip tracking disabled - reset tracker
                if self.trip_tracker is not None:
                    self.trip_tracker = None
                    _LOGGER.debug("Trip tracker disabled")
        except Exception as err:
            _LOGGER.warning("Error handling trip tracking: %s", err)
        
        # Periodically check for missed trips in odometer history
        # This catches trips that weren't detected in real-time due to gaps in tracking
        try:
            await self._check_for_missed_trips()
        except Exception as err:
            _LOGGER.warning("Error in periodic missed trip check: %s", err)
        
        # Periodically check for missed refuelings in tank level history
        # This catches refuelings that weren't detected in real-time due to gaps in tracking
        try:
            await self._check_for_missed_refuelings()
        except Exception as err:
            _LOGGER.warning("Error in periodic missed refueling check: %s", err)
        
        # Build data structure
        # Calculate tank_level_liters from vehicle data
        # Note: tank_percentage was already calculated earlier (after line 722) for use in geolocation
        tank_level_liters = None
        
        if tank_level is not None:
            # Check if tank level is already a percentage or in liters
            if tank_level_unit and tank_level_unit.lower() in ("%", "percent", "percentage"):
                # Tank level is already a percentage
                # Calculate liters from percentage if we have tank capacity
                if tank_capacity and tank_capacity > 0:
                    tank_level_liters = (tank_level / 100.0) * tank_capacity
            else:
                # Tank level is in liters, use it directly
                tank_level_liters = tank_level
        
        # Get price trend and statistics
        price_trend = None
        try:
            price_trend = await compute_price_trend(self.hass, self.config_entry, window=5)
        except Exception as err:
            _LOGGER.warning("Error computing price trend: %s", err)
        
        # Calculate consumption history early as it's needed for radius comparison
        consumption_history = None
        try:
            consumption_history = await self._calculate_consumption_history()
        except Exception as err:
            _LOGGER.warning("Error calculating consumption history: %s", err)
        
        # Get refuel recommendation if we have price and tank info
        recommendation = None
        position_change_info = None
        radius_comparison = None
        
        if fuel_price is not None and tank_percentage is not None:
            try:
                # Track position changes and check cooldown status
                if vehicle_lat is not None and vehicle_lon is not None:
                    position_change_info = self._position_tracker.update(
                        vehicle_lat, vehicle_lon, fuel_price
                    )
                    _LOGGER.debug("Position change info: %s", position_change_info)
                
                # Only generate recommendation if not in cooldown
                if not position_change_info or not position_change_info.get("in_cooldown", False):
                    recommendation = await evaluate_refuel_strategy(
                        self.hass,
                        self.config_entry,
                        current_price=fuel_price,
                        tank_percentage=tank_percentage,
                        range_km=vehicle_data.get("range_km"),
                        station_name=nearest_station.get("name") if nearest_station else None,
                    )
                    _LOGGER.debug("Refuel recommendation: %s", recommendation)
                else:
                    # In cooldown - provide modified recommendation
                    cooldown_reason = position_change_info.get("cooldown_reason", "Position change cooldown")
                    recommendation = {
                        "should_refuel": False,
                        "reason": "position_change_cooldown",
                        "urgency": "low",
                        "price_delta": 0.0,
                        "price_delta_percent": 0.0,
                        "days_left": None,
                        "recommendation": f"⏸️ {cooldown_reason}. Recommendations paused temporarily.",
                        "in_cooldown": True,
                        "cooldown_remaining_minutes": position_change_info.get("cooldown_remaining_minutes"),
                    }
                    _LOGGER.info("Recommendation in cooldown: %s", cooldown_reason)
                
                # Compare stations by radius if we have nearby stations data
                if nearby_cheap_stations_data and tank_level_liters is not None:
                    stations_list = nearby_cheap_stations_data.get("stations", [])
                    if stations_list and vehicle_lat and vehicle_lon:
                        # Get average consumption from consumption history
                        avg_consumption = DEFAULT_AVG_CONSUMPTION  # Default from shared constant
                        if consumption_history:
                            history_consumption = consumption_history.get("avg_consumption")
                            if history_consumption and history_consumption > 0:
                                avg_consumption = history_consumption
                        
                        try:
                            radius_comparison = await compare_stations_by_radius(
                                self.hass,
                                self.config_entry,
                                stations_list,
                                vehicle_lat,
                                vehicle_lon,
                                tank_level_liters,
                                tank_capacity,
                                avg_consumption,
                                near_radius=cheap_near_stations_radius,
                                far_radius=cheap_stations_radius,
                            )
                            _LOGGER.debug("Radius comparison: %s", radius_comparison)
                        except Exception as comp_err:
                            _LOGGER.warning("Error comparing stations by radius: %s", comp_err)
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
                tank_level=tank_level_liters,  # Use tank level in liters for consistency
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
        
        # Calculate consumption forecast
        consumption_forecast = None
        try:
            consumption_forecast = await self._calculate_consumption_forecast(consumption_prediction)
        except Exception as err:
            _LOGGER.warning("Error calculating consumption forecast: %s", err)
        
        # Calculate price statistics
        price_statistics = None
        try:
            price_statistics = await calculate_price_statistics(self.hass, self.config_entry)
        except Exception as err:
            _LOGGER.warning("Error calculating price statistics: %s", err)
        
        # Get refueling log and retrieval metadata from storage (single load operation)
        refueling_log = None
        last_vehicle_data_refresh = None
        last_historical_import = None
        trip_tracking_config = {}
        trips = []
        trip_statistics = {}
        storage_statistics = {}
        try:
            stored_data = await storage.load_data(self.hass, self.config_entry)
            refueling_log = stored_data.get("refueling_log", [])
            last_vehicle_data_refresh = stored_data.get("last_vehicle_data_refresh")
            last_historical_import = stored_data.get("last_historical_import")
            trip_tracking_config = stored_data.get("trip_tracking_config", {})
            trips = stored_data.get("trips", [])
            trip_statistics = stored_data.get("trip_statistics", {})
            
            # Calculate storage statistics for debug sensor
            odometer_history = stored_data.get("odometer_history", [])
            tank_history = stored_data.get("tank_history", [])
            
            storage_statistics = {
                "odometer_good": len(odometer_history),
                "odometer_error": 0,
                "tank_good": sum(1 for event in tank_history if event.get("liters_refueled") is not None),
                "tank_error": 0,
                "range_good": 0,  # Range is not stored historically
                "range_error": 0,
                "position_good": sum(1 for trip in trips if trip.get("start_location") is not None),
                "position_error": 0,
                "refueling_count": len(tank_history),
                "trip_count": len(trips),
            }
        except Exception as err:
            _LOGGER.warning("Error getting refueling log and metadata: %s", err)
        
        data = {
            "fuel_price": fuel_price,
            "last_price_timestamp": last_price_timestamp,
            "tank_level": tank_level_liters,  # Always in liters for consistency
            "tank_percentage": tank_percentage,
            "range": range_km,
            "odometer": vehicle_data.get("odometer_km"),
            "latitude": latitude,
            "longitude": longitude,
            "location_source": location_source,  # Add location source for position data
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
            "price_statistics": price_statistics,  # Add price statistics
            "refueling_log": refueling_log,  # Add refueling log
            "nearby_cheap_stations": nearby_cheap_stations_data,  # Add geolocation data
            "proximity_alert": proximity_alert_data,  # Add proximity alert data
            "last_vehicle_data_refresh": last_vehicle_data_refresh,  # Add retrieval metadata
            "last_historical_import": last_historical_import,  # Add import metadata
            "trip_tracking_config": trip_tracking_config,  # Add trip tracking config
            "trips": trips,  # Add trips list
            "trip_statistics": trip_statistics,  # Add trip statistics
            "position_change_info": position_change_info,  # Add position change tracking
            "radius_comparison": radius_comparison,  # Add 10km vs 20km comparison
            "storage_statistics": storage_statistics,  # Add storage statistics for debug sensor
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


def add_prediction_metadata_to_attributes(
    attributes: dict[str, Any],
    consumption_prediction: dict[str, Any] | None,
    config_entry: ConfigEntry,
) -> None:
    """Add prediction metadata attributes to a sensor's attributes dict.
    
    This is a utility function to avoid code duplication between sensors.
    
    Args:
        attributes: Dictionary to add attributes to (modified in place)
        consumption_prediction: Consumption prediction data
        config_entry: Config entry for accessing configuration
    """
    if not consumption_prediction:
        return
    
    from .const import CONF_CONSUMPTION_MIN_DATA_POINTS, DEFAULT_CONSUMPTION_MIN_DATA_POINTS
    options = config_entry.options
    config = config_entry.data
    min_data_points = options.get(CONF_CONSUMPTION_MIN_DATA_POINTS) or config.get(
        CONF_CONSUMPTION_MIN_DATA_POINTS, DEFAULT_CONSUMPTION_MIN_DATA_POINTS
    )
    
    data_points_used = consumption_prediction.get("data_points_used", 0)
    attributes["data_source"] = consumption_prediction.get("data_source", "unknown")
    attributes["data_points_used"] = data_points_used
    
    # Calculate and add data points percentage
    if min_data_points > 0:
        data_points_percentage = min(100.0, (data_points_used / min_data_points) * 100)
        attributes["data_points_percentage"] = round(data_points_percentage, 1)
    else:
        attributes["data_points_percentage"] = 0.0
    attributes["data_points_required"] = min_data_points
    
    # Add last prediction time
    if consumption_prediction.get("last_prediction_time"):
        last_pred_time = consumption_prediction["last_prediction_time"]
        if isinstance(last_pred_time, str):
            attributes["last_prediction"] = last_pred_time
        else:
            attributes["last_prediction"] = last_pred_time.isoformat()


def format_weekday_pattern(
    weekday_pattern: dict[int, float] | None,
) -> dict[str, str] | None:
    """Convert weekday pattern from numeric keys to named keys with units.
    
    Args:
        weekday_pattern: Dictionary with weekday numbers (0-6) as keys and km values
        
    Returns:
        Dictionary with weekday names as keys and formatted km values with units, or None if input is None
    """
    if not weekday_pattern:
        return None
    
    # Convert weekday numbers to names for better readability
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    formatted_pattern = {}
    for weekday, km in weekday_pattern.items():
        if isinstance(weekday, int) and 0 <= weekday < 7:
            formatted_pattern[weekday_names[weekday]] = f"{round(km, 1)} km"
    
    return formatted_pattern if formatted_pattern else None


class FuelPriceSensor(CoordinatorEntity, RestoreEntity, SensorEntity):
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
        # State restoration variables
        self._restored_value = None  # Last known sensor value from previous HA session
        self._restored_attributes = {}  # Last known attributes dict from previous HA session
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    async def async_added_to_hass(self) -> None:
        """Restore last known state when added to hass."""
        await super().async_added_to_hass()
        
        # Restore last state
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._restored_value = float(last_state.state)
                self._restored_attributes = dict(last_state.attributes)
                _LOGGER.info(
                    "Restored %s with value %s from previous state",
                    self.entity_id,
                    self._restored_value,
                )
            except (ValueError, TypeError) as err:
                _LOGGER.warning(
                    "Could not restore %s state: %s",
                    self.entity_id,
                    err,
                )

    @property
    def native_value(self) -> float | None:
        """Return the current fuel price."""
        # If coordinator has fresh data, use it
        if self.coordinator.data is not None:
            value = self.coordinator.data.get("fuel_price")
            if value is not None:
                return value
        
        # Fall back to restored value if coordinator data not yet available
        return self._restored_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes following FWCAM standardized ordering."""
        # If coordinator has fresh data, use it
        if self.coordinator.data is not None:
            station = self.coordinator.data.get("nearest_station", {})
            recommendation = self.coordinator.data.get("recommendation", {})
            radius_comparison = self.coordinator.data.get("radius_comparison")
            
            # Determine which station to display as primary
            # If we have a comparison and a clear recommendation, show the recommended station
            display_station = station  # Default to nearest by price
            
            if radius_comparison and radius_comparison.get("has_comparison"):
                comparison_rec = radius_comparison.get("recommendation", "")
                savings = radius_comparison.get("savings", 0)
                
                # If the farther station actually saves money (positive savings),
                # or if the recommendation suggests it's better, show the 20km station
                # Otherwise (negative savings or similar cost), show the 10km station
                if "20km" in comparison_rec or savings > STATION_RECOMMENDATION_MIN_SAVINGS:
                    station_20km = radius_comparison.get("station_20km", {})
                    if station_20km:
                        # Build station data from 20km comparison data
                        # Note: Station address is not available in comparison data as it only
                        # contains essential fields (name, distance, price) for cost calculation.
                        # The address would require an additional lookup from the full station list.
                        display_station = {
                            "name": station_20km.get("name"),
                            "distance": station_20km.get("distance_km"),
                        }
                else:
                    # Show 10km station as recommended
                    station_10km = radius_comparison.get("station_10km", {})
                    if station_10km:
                        display_station = {
                            "name": station_10km.get("name"),
                            "distance": station_10km.get("distance_km"),
                        }
            
            # 1. Core metadata
            attributes = {
                ATTR_STATION_NAME: display_station.get("name"),
                ATTR_STATION_ADDRESS: display_station.get("address"),
                ATTR_DISTANCE: display_station.get("distance"),
            }
            
            # Add data source (API-based)
            attributes[ATTR_DATA_SOURCE] = "api"
            
            # Add location source information
            location_source = self.coordinator.data.get("location_source")
            if location_source:
                attributes["location_source"] = location_source
            
            # 2. Update timestamps
            last_price_timestamp = self.coordinator.data.get("last_price_timestamp")
            if last_price_timestamp:
                attributes["last_update_timestamp"] = last_price_timestamp
                
                # Check if data is stale (> 1 hour old)
                staleness_warning = check_data_staleness(last_price_timestamp, "Fuel price data")
                if staleness_warning:
                    attributes["data_staleness_warning"] = staleness_warning
        else:
            # Fall back to restored attributes if coordinator data not yet available
            attributes = self._restored_attributes.copy() if self._restored_attributes else {}
            
            # Mark as restored state using constant
            if self._restored_value is not None:
                attributes[ATTR_DATA_SOURCE] = STATE_RESTORED_DATA_SOURCE
        
        # Add supplementary attributes from coordinator data if available
        if self.coordinator.data is not None:
            # 3. AI/ML patterns (history price pattern - weekday patterns)
            price_statistics = self.coordinator.data.get("price_statistics")
            if price_statistics:
                weekday_patterns = price_statistics.get("weekday_patterns")
                if weekday_patterns:
                    attributes["history_price_pattern"] = weekday_patterns
            
            # 4. Last event summary - NOT applicable for this sensor
            
            # 5. Recommendations
            recommendation = self.coordinator.data.get("recommendation", {})
            if recommendation:
                attributes[ATTR_SHOULD_REFUEL] = recommendation.get("should_refuel", False)
                attributes[ATTR_URGENCY] = recommendation.get("urgency", "low")
                attributes[ATTR_RECOMMENDATION] = recommendation.get("recommendation", "")
                attributes[ATTR_PRICE_DELTA] = recommendation.get("price_delta")
                attributes[ATTR_PRICE_DELTA_PERCENT] = recommendation.get("price_delta_percent")
            
            # Add cost savings comparison (part of recommendations)
            radius_comparison = self.coordinator.data.get("radius_comparison")
            if radius_comparison and radius_comparison.get("has_comparison"):
                comparison_type = radius_comparison.get("comparison_type", "10km_vs_20km")
                savings_value = radius_comparison.get("savings")
                
                if savings_value is not None:
                    if comparison_type == "near_vs_far_radius":
                        near_radius_label = radius_comparison.get("near_radius_label", "near station")
                        far_radius_label = radius_comparison.get("far_radius_label", "farther station")
                        
                        if savings_value >= 0:
                            attributes["costsaving_far_vs_near_station"] = f"+{savings_value:.2f} € (save by driving to {far_radius_label})"
                        else:
                            attributes["costsaving_far_vs_near_station"] = f"{savings_value:.2f} € (costs more, stay within {near_radius_label})"
                    elif comparison_type == "nearest_vs_cheapest":
                        if savings_value >= 0:
                            attributes["costsaving_far_vs_near_station"] = f"+{savings_value:.2f} € (save by driving to cheapest)"
                        else:
                            attributes["costsaving_far_vs_near_station"] = f"{savings_value:.2f} € (costs more to drive to cheapest, stay near)"
                    else:
                        if savings_value >= 0:
                            attributes["costsaving_far_vs_near_station"] = f"+{savings_value:.2f} € (save by driving farther)"
                        else:
                            attributes["costsaving_far_vs_near_station"] = f"{savings_value:.2f} € (cost more by driving farther)"
                else:
                    attributes["costsaving_far_vs_near_station"] = "Waiting for more data"
            elif radius_comparison:
                reason = radius_comparison.get("reason", "Unknown")
                if reason == "No stations available":
                    attributes["costsaving_far_vs_near_station"] = "Waiting for station data"
                elif reason == "Tank is full":
                    attributes["costsaving_far_vs_near_station"] = "Tank is full - no savings calculation"
                elif reason == "No different stations to compare":
                    attributes["costsaving_far_vs_near_station"] = "Not applicable - only one station available"
                elif reason == "Only one station available":
                    attributes["costsaving_far_vs_near_station"] = "Not applicable - only one station available"
                elif reason == "Nearest and cheapest stations are the same":
                    attributes["costsaving_far_vs_near_station"] = "Not applicable - nearest is also cheapest"
                else:
                    attributes["costsaving_far_vs_near_station"] = f"Not available ({reason})"
            else:
                attributes["costsaving_far_vs_near_station"] = "Waiting for more data"
            
            # Add cooldown information if present (part of recommendations)
            if recommendation and recommendation.get("in_cooldown"):
                attributes["in_cooldown"] = True
                attributes["cooldown_remaining_minutes"] = recommendation.get("cooldown_remaining_minutes")
            
            # 6. Counters - NOT applicable for this sensor
            
            # 7. Time-based statistics
            attributes[ATTR_FORECAST_TREND] = self.coordinator.data.get("forecast_trend")
            
            # Add period statistics
            if price_statistics:
                last_week = price_statistics.get("last_week")
                if last_week:
                    attributes["last_week_price"] = last_week.get("avg_price")
                    attributes["last_week_trend"] = last_week.get("trend", "Waiting for more data")
                    attributes["last_week_top_stations"] = last_week.get("top_stations", [])
                else:
                    attributes["last_week_trend"] = "Waiting for more data"
                    attributes["last_week_top_stations"] = [
                        {"name": "Waiting for more data", "avg_price": "Waiting for more data"},
                        {"name": "Waiting for more data", "avg_price": "Waiting for more data"},
                        {"name": "Waiting for more data", "avg_price": "Waiting for more data"},
                    ]
                
                last_14_days = price_statistics.get("last_14_days")
                if last_14_days:
                    attributes["last_14_days_price"] = last_14_days.get("avg_price")
                    attributes["last_14_days_trend"] = last_14_days.get("trend", "Waiting for more data")
                    attributes["last_14_days_top_stations"] = last_14_days.get("top_stations", [])
                else:
                    attributes["last_14_days_trend"] = "Waiting for more data"
                    attributes["last_14_days_top_stations"] = [
                        {"name": "Waiting for more data", "avg_price": "Waiting for more data"},
                        {"name": "Waiting for more data", "avg_price": "Waiting for more data"},
                        {"name": "Waiting for more data", "avg_price": "Waiting for more data"},
                    ]
                
                last_month = price_statistics.get("last_month")
                if last_month:
                    attributes["last_month_price"] = last_month.get("avg_price")
                    attributes["last_month_trend"] = last_month.get("trend", "Waiting for more data")
                    attributes["last_month_top_stations"] = last_month.get("top_stations", [])
                else:
                    attributes["last_month_trend"] = "Waiting for more data"
                    attributes["last_month_top_stations"] = [
                        {"name": "Waiting for more data", "avg_price": "Waiting for more data"},
                        {"name": "Waiting for more data", "avg_price": "Waiting for more data"},
                        {"name": "Waiting for more data", "avg_price": "Waiting for more data"},
                    ]
        
        # 8. Configuration & documentation
        attributes["config_entry_id"] = self._config_entry.entry_id
        
        metadata = get_entity_metadata("fuel_price_sensor")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        # 9. Mass data - station_comparison object (keep as is, but move to end)
        if self.coordinator.data is not None:
            radius_comparison = self.coordinator.data.get("radius_comparison")
            if radius_comparison and radius_comparison.get("has_comparison"):
                comparison_type = radius_comparison.get("comparison_type", "10km_vs_20km")
                
                if comparison_type == "near_vs_far_radius":
                    near_radius = radius_comparison.get("near_radius_km")
                    far_radius = radius_comparison.get("far_radius_km")
                    near_radius_label = radius_comparison.get("near_radius_label", "near")
                    far_radius_label = radius_comparison.get("far_radius_label", "farther")
                    attributes["station_comparison"] = {
                        "near": radius_comparison.get("station_near"),
                        "far": radius_comparison.get("station_far"),
                        "near_radius_km": near_radius,
                        "far_radius_km": far_radius,
                        "near_radius_label": near_radius_label,
                        "far_radius_label": far_radius_label,
                        "savings": radius_comparison.get("savings"),
                        "savings_percent": radius_comparison.get("savings_percent"),
                        "comparison_recommendation": radius_comparison.get("recommendation"),
                        "fuel_to_purchase": radius_comparison.get("fuel_to_purchase"),
                        "comparison_type": "near_vs_far_radius",
                    }
                elif comparison_type == "nearest_vs_cheapest":
                    attributes["station_comparison"] = {
                        "nearest": radius_comparison.get("nearest_station"),
                        "cheapest": radius_comparison.get("cheapest_station"),
                        "savings": radius_comparison.get("savings"),
                        "savings_percent": radius_comparison.get("savings_percent"),
                        "comparison_recommendation": radius_comparison.get("recommendation"),
                        "fuel_to_purchase": radius_comparison.get("fuel_to_purchase"),
                        "comparison_type": "nearest_vs_cheapest",
                    }
                else:
                    attributes["station_comparison"] = {
                        "10km": radius_comparison.get("station_10km"),
                        "20km": radius_comparison.get("station_20km"),
                        "savings": radius_comparison.get("savings"),
                        "savings_percent": radius_comparison.get("savings_percent"),
                        "comparison_recommendation": radius_comparison.get("recommendation"),
                        "fuel_to_purchase": radius_comparison.get("fuel_to_purchase"),
                        "comparison_type": "10km_vs_20km",
                    }
        
        return attributes


class TankLevelSensor(CoordinatorEntity, RestoreEntity, SensorEntity):
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
        # State restoration variables
        self._restored_value = None  # Last known sensor value from previous HA session
        self._restored_attributes = {}  # Last known attributes dict from previous HA session
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    async def async_added_to_hass(self) -> None:
        """Restore last known state when added to hass."""
        await super().async_added_to_hass()
        
        # Restore last state
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._restored_value = float(last_state.state)
                self._restored_attributes = dict(last_state.attributes)
                _LOGGER.info(
                    "Restored %s with value %s from previous state",
                    self.entity_id,
                    self._restored_value,
                )
            except (ValueError, TypeError) as err:
                _LOGGER.warning(
                    "Could not restore %s state: %s",
                    self.entity_id,
                    err,
                )

    @property
    def native_value(self) -> float | None:
        """Return the current tank level as percentage."""
        # If coordinator has fresh data, use it
        if self.coordinator.data is not None:
            value = self.coordinator.data.get("tank_percentage")
            if value is not None:
                return value
        
        # Fall back to restored value if coordinator data not yet available
        return self._restored_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        # If coordinator has fresh data, use it
        if self.coordinator.data is not None:
            tank_level_liters = self.coordinator.data.get("tank_level")
            attributes = {}
            
            if tank_level_liters is not None:
                attributes["liters"] = tank_level_liters
            
            # Include tank capacity from config for use in Lovelace card validation
            options = self._config_entry.options
            config = self._config_entry.data
            tank_capacity = options.get(CONF_TANK_CAPACITY) or config.get(CONF_TANK_CAPACITY, DEFAULT_TANK_CAPACITY)
            attributes["tank_capacity"] = tank_capacity
            
            # Add last vehicle data refresh timestamp and check staleness
            last_vehicle_data_refresh = self.coordinator.data.get("last_vehicle_data_refresh")
            if last_vehicle_data_refresh:
                attributes["last_vehicle_data_refresh"] = last_vehicle_data_refresh.get("timestamp")
                attributes["last_vehicle_data_refresh_type"] = last_vehicle_data_refresh.get("type")
                
                # Check if data is stale (> 1 hour old)
                staleness_warning = check_data_staleness(
                    last_vehicle_data_refresh.get("timestamp"),
                    "Vehicle data"
                )
                if staleness_warning:
                    attributes["data_staleness_warning"] = staleness_warning
            
            return attributes
        
        # Fall back to restored attributes if coordinator data not yet available
        attributes = self._restored_attributes.copy() if self._restored_attributes else {}
        
        # Mark as restored state
        if self._restored_value is not None:
            attributes["data_source"] = STATE_RESTORED_DATA_SOURCE
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("tank_level_sensor")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class RangeSensor(CoordinatorEntity, RestoreEntity, SensorEntity):
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
        # State restoration variables
        self._restored_value = None  # Last known sensor value from previous HA session
        self._restored_attributes = {}  # Last known attributes dict from previous HA session
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    async def async_added_to_hass(self) -> None:
        """Restore last known state when added to hass."""
        await super().async_added_to_hass()
        
        # Restore last state
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._restored_value = float(last_state.state)
                self._restored_attributes = dict(last_state.attributes)
                _LOGGER.info(
                    "Restored %s with value %s from previous state",
                    self.entity_id,
                    self._restored_value,
                )
            except (ValueError, TypeError) as err:
                _LOGGER.warning(
                    "Could not restore %s state: %s",
                    self.entity_id,
                    err,
                )

    @property
    def native_value(self) -> float | None:
        """Return the estimated range."""
        # If coordinator has fresh data, use it
        if self.coordinator.data is not None:
            value = self.coordinator.data.get("range")
            if value is not None:
                return value
        
        # Fall back to restored value if coordinator data not yet available
        return self._restored_value
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        # If coordinator has fresh data, use it
        if self.coordinator.data is not None:
            days_left = self.coordinator.data.get("days_left")
            attributes = {}
            if days_left is not None:
                attributes[ATTR_DAYS_LEFT] = days_left
            
            # Add last vehicle data refresh timestamp and check staleness
            last_vehicle_data_refresh = self.coordinator.data.get("last_vehicle_data_refresh")
            if last_vehicle_data_refresh:
                attributes["last_vehicle_data_refresh"] = last_vehicle_data_refresh.get("timestamp")
                attributes["last_vehicle_data_refresh_type"] = last_vehicle_data_refresh.get("type")
                
                # Check if data is stale (> 1 hour old)
                staleness_warning = check_data_staleness(
                    last_vehicle_data_refresh.get("timestamp"),
                    "Vehicle data"
                )
                if staleness_warning:
                    attributes["data_staleness_warning"] = staleness_warning
            
            return attributes
        
        # Fall back to restored attributes if coordinator data not yet available
        attributes = self._restored_attributes.copy() if self._restored_attributes else {}
        
        # Mark as restored state
        if self._restored_value is not None:
            attributes["data_source"] = STATE_RESTORED_DATA_SOURCE
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("range_sensor")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class NearestStationSensor(CoordinatorEntity, RestoreEntity, SensorEntity):
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
        # State restoration variables
        self._restored_value = None  # Last known sensor value from previous HA session
        self._restored_attributes = {}  # Last known attributes dict from previous HA session
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    async def async_added_to_hass(self) -> None:
        """Restore last known state when added to hass."""
        await super().async_added_to_hass()
        
        # Restore last state
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            self._restored_value = last_state.state
            self._restored_attributes = dict(last_state.attributes)
            _LOGGER.info(
                "Restored %s with value %s from previous state",
                self.entity_id,
                self._restored_value,
            )

    @property
    def native_value(self) -> str | None:
        """Return the name of cheapest station."""
        # If coordinator has fresh data, use it
        if self.coordinator.data is not None:
            station = self.coordinator.data.get("nearest_station", {})
            value = station.get("name")
            if value is not None:
                return value
        
        # Fall back to restored value if coordinator data not yet available
        return self._restored_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        # If coordinator has fresh data, use it
        if self.coordinator.data is not None:
            station = self.coordinator.data.get("nearest_station", {})
            attributes = {
                ATTR_STATION_ADDRESS: station.get("address"),
                ATTR_DISTANCE: station.get("distance"),
                ATTR_PRICE: station.get("price"),
            }
            
            # Add timestamp of last successful station fetch and check staleness
            last_station_timestamp = self.coordinator.data.get("last_station_timestamp")
            if last_station_timestamp:
                attributes["last_update_timestamp"] = last_station_timestamp
                
                # Check if data is stale (> 1 hour old)
                staleness_warning = check_data_staleness(last_station_timestamp, "Station data")
                if staleness_warning:
                    attributes["data_staleness_warning"] = staleness_warning
            
            # Add navigation links if station has coordinates
            lat = station.get("latitude")
            lon = station.get("longitude")
            if lat and lon:
                attributes["google_maps_url"] = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                attributes["apple_maps_url"] = f"https://maps.apple.com/?q={lat},{lon}"
                attributes["waze_url"] = f"https://waze.com/ul?ll={lat},{lon}&navigate=yes"
            
            return attributes
        
        # Fall back to restored attributes if coordinator data not yet available
        attributes = self._restored_attributes.copy() if self._restored_attributes else {}
        
        # Mark as restored state
        if self._restored_value is not None:
            attributes["data_source"] = STATE_RESTORED_DATA_SOURCE
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("nearest_station_sensor")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class FuelPriceApiDebugSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing fuel price API debug information."""

    _attr_icon = "mdi:api"
    _attr_has_entity_name = True
    
    # Constants for API debug attribute filtering
    MAX_SUMMARY_KEYS = 10  # Maximum number of keys to include in response summary
    MAX_STRING_LENGTH = 200  # Maximum length for truncated strings

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
        self._attr_name = "Fuel Price API Debug"
        self._attr_unique_id = f"{config_entry.entry_id}_fuel_price_api_debug"
        
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
        if self.coordinator.data is None:
            return None
        api_debug = self.coordinator.data.get("api_debug", {})
        if not api_debug:
            return "Unknown"
        
        status = api_debug.get("api_response_status", "unknown")
        return status.title()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return API debug information as attributes (summarized to avoid size issues)."""
        if self.coordinator.data is None:
            return {}
        api_debug = self.coordinator.data.get("api_debug", {})
        if not api_debug:
            return {"status": "No API request made yet"}
        
        # Create a copy without the potentially large response data
        filtered_debug = {}
        
        for key, value in api_debug.items():
            # Skip or summarize large fields
            if key == "last_api_response":
                # Include detailed summary info about the response
                if isinstance(value, dict):
                    response_summary = {
                        "keys": list(value.keys())[:self.MAX_SUMMARY_KEYS],  # First N keys only
                        "size_bytes": sys.getsizeof(value),
                    }
                    
                    # Add more details about the response structure
                    if "status" in value:
                        response_summary["status"] = value["status"]
                    if "data" in value:
                        data = value["data"]
                        if isinstance(data, dict):
                            response_summary["data_keys"] = list(data.keys())
                            # Check for nested data structure (v4 API format)
                            if "data" in data and isinstance(data["data"], dict):
                                response_summary["nested_data_keys"] = list(data["data"].keys())
                                # Check for stations in nested data
                                if "stations" in data["data"]:
                                    stations = data["data"]["stations"]
                                    response_summary["stations_count"] = len(stations) if isinstance(stations, list) else 0
                                    # Include sample station if available
                                    if isinstance(stations, list) and len(stations) > 0:
                                        sample = stations[0]
                                        if isinstance(sample, dict):
                                            response_summary["sample_station_keys"] = list(sample.keys())
                            # Check for stations at top level (legacy format)
                            elif "stations" in data:
                                stations = data["stations"]
                                response_summary["stations_count"] = len(stations) if isinstance(stations, list) else 0
                                # Include sample station if available
                                if isinstance(stations, list) and len(stations) > 0:
                                    sample = stations[0]
                                    if isinstance(sample, dict):
                                        response_summary["sample_station_keys"] = list(sample.keys())
                            # Add other top-level data info
                            if "ok" in data:
                                response_summary["api_ok"] = data["ok"]
                            if "message" in data:
                                response_summary["api_message"] = data["message"]
                    if "error" in value:
                        response_summary["error"] = value["error"]
                    if "error_type" in value:
                        response_summary["error_type"] = value["error_type"]
                    
                    filtered_debug["api_response_summary"] = response_summary
                elif isinstance(value, list):
                    filtered_debug["api_response_summary"] = {
                        "items_count": len(value),
                        "size_bytes": sys.getsizeof(value),
                    }
                else:
                    filtered_debug["api_response_summary"] = {
                        "type": type(value).__name__,
                        "size_bytes": sys.getsizeof(value),
                    }
            elif key == "last_api_request":
                # Include complete request info with full URL (params masked)
                if isinstance(value, dict):
                    request_summary = {
                        k: v for k, v in value.items() 
                        if k in ["url", "method", "timestamp"]
                    }
                    
                    # Build complete URL with query parameters (API key already masked in params)
                    if "url" in value and "params" in value:
                        base_url = value["url"]
                        params = value["params"]
                        if isinstance(params, dict) and params:
                            # Build properly URL-encoded query string from parameters
                            query_string = urlencode(params)
                            request_summary["url"] = f"{base_url}?{query_string}"
                        
                        # Also include parameters separately for easier reading
                        # (URL encoding can make some values harder to read at a glance)
                        request_summary["params"] = params
                    
                    filtered_debug["api_request_summary"] = request_summary
                else:
                    filtered_debug["api_request_summary"] = str(value)[:self.MAX_STRING_LENGTH]  # Truncate long strings
            else:
                # Include other fields as-is (they should be small)
                filtered_debug[key] = value
        
        # Add station count and price analysis at different radius ranges
        nearby_cheap_stations_data = self.coordinator.data.get("nearby_cheap_stations")
        if nearby_cheap_stations_data:
            stations_list = nearby_cheap_stations_data.get("stations", [])
            search_radius_km = nearby_cheap_stations_data.get("search_radius_km")
            
            # Get configured radius values from options
            options = self._config_entry.options
            cheap_stations_radius = options.get(CONF_CHEAP_STATIONS_RADIUS, DEFAULT_CHEAP_STATIONS_RADIUS)
            cheap_near_stations_radius = options.get(CONF_CHEAP_NEAR_STATIONS_RADIUS, DEFAULT_CHEAP_NEAR_STATIONS_RADIUS)
            
            if stations_list:
                # Helper function to get valid prices from station list
                def get_lowest_price(stations):
                    """Extract lowest valid price from station list."""
                    prices = [s.get("price") for s in stations if s.get("price") is not None]
                    return round(min(prices), 3) if prices else None
                
                # Stations within configured full search radius (cheap_stations_radius)
                filtered_debug["count_stations_cheap_stations_radius_range"] = len(stations_list)
                filtered_debug["configured_cheap_stations_radius_km"] = cheap_stations_radius
                filtered_debug["lowest_price_cheap_stations_radius_range"] = get_lowest_price(stations_list)
                
                # Stations within configured near radius (cheap_near_stations_radius)
                stations_near = [s for s in stations_list if s.get("distance_km", float('inf')) <= cheap_near_stations_radius]
                filtered_debug["count_stations_cheap_near_stations_radius_range"] = len(stations_near)
                filtered_debug["configured_cheap_near_stations_radius_km"] = cheap_near_stations_radius
                filtered_debug["lowest_price_cheap_near_stations_radius_range"] = get_lowest_price(stations_near)
                
                # Stations within 10km
                stations_10km = [s for s in stations_list if s.get("distance_km", float('inf')) <= 10]
                filtered_debug["count_stations_10km_range"] = len(stations_10km)
                filtered_debug["lowest_price_10km_range"] = get_lowest_price(stations_10km)
                
                # Stations within 20km
                stations_20km = [s for s in stations_list if s.get("distance_km", float('inf')) <= 20]
                filtered_debug["count_stations_20km_range"] = len(stations_20km)
                filtered_debug["lowest_price_20km_range"] = get_lowest_price(stations_20km)
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("fuel_price_api_debug_sensor")
        if metadata:
            filtered_debug[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            filtered_debug[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            filtered_debug[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            filtered_debug[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return filtered_debug


class CarDataDebugSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing vehicle data debug information.
    
    This sensor tracks vehicle data retrieval status and provides insights into:
    - When odometer, tank level, range, and position data was last retrieved
    - Quality of data points (good vs error counts)
    - Whether sufficient data exists for various calculations
    """

    _attr_icon = "mdi:car-info"
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
        self._attr_name = "Car Data Debug"
        self._attr_unique_id = f"{config_entry.entry_id}_car_data_debug"
        self._config_entry = config_entry
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    @property
    def native_value(self) -> str | None:
        """Return the overall data status."""
        if self.coordinator.data is None:
            return "No Data"
        
        vehicle_data = self.coordinator.data.get("vehicle_data", {})
        
        # Count how many data types are available
        data_available = 0
        for key in ["odometer_km", "tank_level", "range_km", "latitude"]:
            if vehicle_data.get(key) is not None:
                data_available += 1
        
        if data_available == 0:
            return "No Vehicle Data"
        elif data_available < 3:
            return "Partial Data"
        else:
            return "Data Available"

    async def _get_storage_statistics(self) -> dict[str, Any]:
        """Get statistics from storage about data points."""
        data = await storage.load_data(self.hass, self._config_entry)
        
        # Count odometer observations
        odometer_history = data.get("odometer_history", [])
        odometer_good = len(odometer_history)
        
        # Count tank level observations from refueling events
        tank_history = data.get("tank_history", [])
        tank_good = sum(1 for event in tank_history if event.get("liters_refueled") is not None)
        
        # Count range observations (not directly stored, use current value availability)
        # Count position observations from trips
        trips = data.get("trips", [])
        position_good = sum(1 for trip in trips if trip.get("start_location") is not None)
        
        # Get refueling count
        refueling_count = len(tank_history)
        
        # Get trip count
        trip_count = len(trips)
        
        return {
            "odometer_good": odometer_good,
            "odometer_error": 0,  # We don't track errors separately for now
            "tank_good": tank_good,
            "tank_error": 0,
            "range_good": 0,  # Range is not stored historically
            "range_error": 0,
            "position_good": position_good,
            "position_error": 0,
            "refueling_count": refueling_count,
            "trip_count": trip_count,
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return vehicle data debug information as attributes."""
        if self.coordinator.data is None:
            return {"status": "No coordinator data"}
        
        vehicle_data = self.coordinator.data.get("vehicle_data", {})
        consumption_prediction = self.coordinator.data.get("consumption_prediction") or {}
        
        from homeassistant.util import dt as dt_util
        from datetime import datetime
        
        attributes = {}
        
        # Get current timestamp for display
        current_time = dt_util.now()
        
        # Last retrieved data with timestamps
        if vehicle_data.get("odometer_km") is not None:
            attributes["odometer_last_value"] = vehicle_data["odometer_km"]
            attributes["odometer_last_timestamp"] = current_time.isoformat()
        else:
            attributes["odometer_last_value"] = None
            attributes["odometer_last_timestamp"] = None
        
        if vehicle_data.get("tank_level") is not None:
            attributes["tank_level_last_value"] = vehicle_data["tank_level"]
            attributes["tank_level_last_timestamp"] = current_time.isoformat()
            attributes["tank_level_unit"] = vehicle_data.get("tank_level_unit", "unknown")
        else:
            attributes["tank_level_last_value"] = None
            attributes["tank_level_last_timestamp"] = None
            attributes["tank_level_unit"] = None
        
        if vehicle_data.get("range_km") is not None:
            attributes["range_last_value"] = vehicle_data["range_km"]
            attributes["range_last_timestamp"] = current_time.isoformat()
        else:
            attributes["range_last_value"] = None
            attributes["range_last_timestamp"] = None
        
        if vehicle_data.get("latitude") is not None and vehicle_data.get("longitude") is not None:
            attributes["position_last_value"] = f"{vehicle_data['latitude']}/{vehicle_data['longitude']}"
            attributes["position_last_timestamp"] = current_time.isoformat()
        else:
            attributes["position_last_value"] = None
            attributes["position_last_timestamp"] = None
        
        # Get storage statistics from coordinator data
        storage_stats = self.coordinator.data.get("storage_statistics", {})
        data_points_used = consumption_prediction.get("data_points_used", 0)
        data_points_required = consumption_prediction.get("data_points_required", 5)
        
        attributes["odometer_good_count"] = storage_stats.get("odometer_good", 0)
        attributes["odometer_error_count"] = storage_stats.get("odometer_error", 0)
        attributes["tank_good_count"] = storage_stats.get("tank_good", 0)
        attributes["tank_error_count"] = storage_stats.get("tank_error", 0)
        attributes["range_good_count"] = 1 if vehicle_data.get("range_km") is not None else 0
        attributes["range_error_count"] = 0
        attributes["position_good_count"] = 1 if vehicle_data.get("latitude") is not None else 0
        attributes["position_error_count"] = 0
        
        # Calculation sufficiency status
        # Check if enough data for each sensor type
        
        # Trip log: needs position data
        trip_log_sufficient = vehicle_data.get("latitude") is not None
        attributes["trip_log_data_count"] = 1 if trip_log_sufficient else 0
        attributes["trip_log_sufficient"] = trip_log_sufficient
        
        # Refueling log: always available (stored events)
        attributes["refueling_log_data_count"] = data_points_used
        attributes["refueling_log_sufficient"] = True
        
        # Average consumption history: needs refueling data
        attributes["average_consumption_history_data_count"] = data_points_used
        attributes["average_consumption_history_sufficient"] = data_points_used >= 2
        
        # Days until refuel: needs range or tank level + consumption data
        has_vehicle_data = vehicle_data.get("range_km") is not None or vehicle_data.get("tank_level") is not None
        days_until_refuel_sufficient = has_vehicle_data and data_points_used >= data_points_required
        attributes["days_until_refuel_data_count"] = data_points_used
        attributes["days_until_refuel_sufficient"] = days_until_refuel_sufficient
        
        # Tank level sensor: needs tank level data
        tank_level_sufficient = vehicle_data.get("tank_level") is not None
        attributes["tank_level_data_count"] = 1 if tank_level_sufficient else 0
        attributes["tank_level_sufficient"] = tank_level_sufficient
        
        # Add data source from consumption prediction
        data_source = consumption_prediction.get("data_source", "unknown")
        attributes["consumption_data_source"] = data_source
        
        # Add missed trip check information
        if hasattr(self.coordinator, '_last_missed_trip_check') and self.coordinator._last_missed_trip_check:
            attributes["last_missed_trip_check_timestamp"] = self.coordinator._last_missed_trip_check.isoformat()
            time_since_last_check = (current_time - self.coordinator._last_missed_trip_check).total_seconds() / 3600  # hours
            attributes["hours_since_last_missed_trip_check"] = round(time_since_last_check, 2)
        else:
            attributes["last_missed_trip_check_timestamp"] = None
            attributes["hours_since_last_missed_trip_check"] = None
        
        # Add recommendations
        recommendations = []
        if not has_vehicle_data:
            recommendations.append("Configure vehicle entities (tank level or range sensor)")
        if data_points_used < data_points_required:
            recommendations.append(f"Need {data_points_required - data_points_used} more refueling events for predictions")
        if vehicle_data.get("latitude") is None:
            recommendations.append("Configure position entity for trip tracking")
        
        if recommendations:
            attributes["recommendations"] = "; ".join(recommendations)
        else:
            attributes["recommendations"] = "All data sources configured properly"
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("car_data_debug_sensor")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class ConsumptionPredictionSensor(CoordinatorEntity, RestoreEntity, SensorEntity):
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
        # State restoration variables
        self._restored_value = None  # Last known sensor value from previous HA session
        self._restored_attributes = {}  # Last known attributes dict from previous HA session
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    async def async_added_to_hass(self) -> None:
        """Restore last known state when added to hass."""
        await super().async_added_to_hass()
        
        # Restore last state
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._restored_value = float(last_state.state)
                self._restored_attributes = dict(last_state.attributes)
                _LOGGER.info(
                    "Restored %s with value %s from previous state",
                    self.entity_id,
                    self._restored_value,
                )
            except (ValueError, TypeError) as err:
                _LOGGER.warning(
                    "Could not restore %s state: %s",
                    self.entity_id,
                    err,
                )

    @property
    def native_value(self) -> float | None:
        """Return the days until refueling is needed."""
        # If coordinator has fresh data, use it
        if self.coordinator.data is not None:
            prediction = self.coordinator.data.get("consumption_prediction")
            if prediction:
                days = prediction.get("days_until_refuel")
                if days is not None:
                    self._last_known_value = days
                    return days
        
        # Fall back to restored value if coordinator data not yet available
        if self._restored_value is not None:
            return self._restored_value
        
        # Finally fall back to in-memory last known value
        return self._last_known_value
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional prediction attributes.
        
        Attributes are ordered according to FWCAM standard structure:
        1. Core metadata (state_class, data_source, confidence)
        2. Update timestamps (last_prediction)
        3. AI/ML patterns (weekday_driving_pattern)
        4. Recommendations (forecast_recommendation, forecast details)
        5. Counters (data_points_used, data_points_percentage)
        6. Statistics (avg_daily_km, avg_consumption_rate)
        7. Config & documentation
        """
        # If coordinator has fresh data, use it
        if self.coordinator.data is not None:
            prediction = self.coordinator.data.get("consumption_prediction")
            if not prediction:
                return {
                    "data_source": "no_data",
                    "status": "Waiting for initial prediction",
                }
            
            # Get min data points configuration
            from .const import CONF_CONSUMPTION_MIN_DATA_POINTS, DEFAULT_CONSUMPTION_MIN_DATA_POINTS
            options = self._config_entry.options
            config = self._config_entry.data
            min_data_points = options.get(CONF_CONSUMPTION_MIN_DATA_POINTS) or config.get(
                CONF_CONSUMPTION_MIN_DATA_POINTS, DEFAULT_CONSUMPTION_MIN_DATA_POINTS
            )
            
            # Build attributes in standard order
            # 1. Core metadata
            attributes = {
                "state_class": "measurement",
                "data_source": prediction.get("data_source", "unknown"),
                "confidence": prediction.get("confidence", 0.0),
            }
            
            # 2. Update timestamps
            if prediction.get("last_prediction_time"):
                last_pred_time = prediction["last_prediction_time"]
                if isinstance(last_pred_time, str):
                    attributes["last_prediction"] = last_pred_time
                else:
                    attributes["last_prediction"] = last_pred_time.isoformat()
            
            # Also add predicted refuel date here as it's a key timestamp
            if prediction.get("predicted_refuel_date"):
                pred_refuel_date = prediction["predicted_refuel_date"]
                if isinstance(pred_refuel_date, str):
                    attributes["predicted_refuel_date"] = pred_refuel_date
                else:
                    attributes["predicted_refuel_date"] = pred_refuel_date.isoformat()
            
            # 3. AI/ML patterns - weekday driving pattern
            weekday_pattern = prediction.get("weekday_pattern")
            if weekday_pattern:
                # Convert weekday numbers to names for better readability
                weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                formatted_pattern = {}
                for weekday, km in weekday_pattern.items():
                    if isinstance(weekday, int) and 0 <= weekday < 7:
                        formatted_pattern[weekday_names[weekday]] = round(km, 1)
                
                if formatted_pattern:
                    attributes["weekday_driving_pattern (km)"] = formatted_pattern
            
            # 4. Recommendations - forecast recommendation
            if prediction.get("forecast_recommendation"):
                forecast = prediction["forecast_recommendation"]
                attributes["forecast_recommendation"] = forecast.get("recommendation", "Not enough data for price forecast") or "Not enough data for price forecast"
                attributes["forecast_should_refuel"] = forecast.get("should_refuel", False)
                attributes["forecast_urgency"] = forecast.get("urgency", "low")
                attributes["forecast_trend"] = forecast.get("forecast_trend", "stable")
                
                # Add detailed forecast data
                if forecast.get("has_forecast"):
                    attributes["forecast_predicted_weekday"] = forecast.get("predicted_weekday")
                    attributes["forecast_predicted_avg_price"] = forecast.get("predicted_avg_price")
                    attributes["forecast_cheapest_weekday"] = forecast.get("cheapest_weekday")
                    attributes["forecast_cheapest_avg_price"] = forecast.get("cheapest_avg_price")
                    attributes["forecast_price_difference"] = forecast.get("price_difference")
            else:
                # No forecast recommendation data available
                attributes["forecast_recommendation"] = "Waiting for consumption prediction and price history data"
            
            # 5. Counters
            data_points_used = prediction.get("data_points_used", 0)
            attributes["data_points_used"] = data_points_used
            
            # Calculate and add data points percentage
            if min_data_points > 0:
                data_points_percentage = min(100.0, (data_points_used / min_data_points) * 100)
                attributes["data_points_percentage"] = round(data_points_percentage, 1)
                attributes["data_points_required"] = min_data_points
            else:
                attributes["data_points_percentage"] = 0.0
                attributes["data_points_required"] = min_data_points
            
            # 6. Statistics
            attributes["avg_daily_km"] = prediction.get("avg_daily_km", 0.0)
            attributes["avg_consumption_rate"] = prediction.get("avg_consumption_rate", 0.0)
            
            # 7. Configuration & documentation metadata
            attributes["config_entry_id"] = self._config_entry.entry_id
            
            metadata = get_entity_metadata("consumption_prediction_sensor")
            if metadata:
                attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
                attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
                attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
                attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
            
            return attributes
        
        # Fall back to restored attributes if coordinator data not yet available
        attributes = self._restored_attributes.copy() if self._restored_attributes else {}
        
        # Mark as restored state
        if self._restored_value is not None:
            attributes["data_source"] = STATE_RESTORED_DATA_SOURCE
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("consumption_prediction_sensor")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
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
    
    def _add_prediction_metadata(
        self,
        attributes: dict[str, Any],
        consumption_prediction: dict[str, Any] | None,
    ) -> None:
        """Add prediction metadata attributes (data_points, percentage, etc).
        
        Args:
            attributes: Dictionary to add attributes to
            consumption_prediction: Consumption prediction data
        """
        add_prediction_metadata_to_attributes(attributes, consumption_prediction, self._config_entry)

    @property
    def native_value(self) -> float | None:
        """Return the overall average consumption based on available historical data.
        
        Prioritizes longer time periods for more accurate overall average:
        1. Last month (if available)
        2. Last 14 days (if available)
        3. Last week (if available)
        4. Today (as fallback)
        """
        if self.coordinator.data is None:
            return None
        history = self.coordinator.data.get("consumption_history")
        if not history:
            _LOGGER.debug("ConsumptionHistorySensor: No consumption_history data available")
            return None
        
        # Try to get the most comprehensive average, prioritizing longer periods
        # Use a loop to eliminate duplication
        for period_key in ["last_month", "last_14_days", "last_week", "today"]:
            period_data = history.get(period_key)
            if period_data:
                consumption = period_data.get("avg_consumption_l_per_100km")
                if consumption is not None:
                    _LOGGER.debug(
                        "ConsumptionHistorySensor: Using %s consumption: %.2f L/100km",
                        period_key, consumption
                    )
                    return round(consumption, 2)
        
        _LOGGER.warning(
            "ConsumptionHistorySensor: No consumption data available in any period. "
            "This may indicate insufficient refueling events. Need at least 2 refueling "
            "events with odometer readings in a period to calculate consumption."
        )
        return None
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return consumption statistics for different time periods."""
        if self.coordinator.data is None:
            return {}
        history = self.coordinator.data.get("consumption_history")
        consumption_prediction = self.coordinator.data.get("consumption_prediction")
        
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
            attributes["today_cost"] = today.get("total_cost", 0.0)
            
            # Add data quality warning if daily km seems unrealistic
            total_km = today.get("total_km", 0)
            if total_km > 1000:  # More than 1000 km in one day is suspicious
                attributes["data_quality_warning"] = (
                    f"Today shows {total_km} km driven, which is unusually high. "
                    "This may indicate incorrect timestamps or odometer values in your refueling events. "
                    "Check your refueling log or use the recalculation button to fix data issues."
                )
        
        # Last week
        if history.get("last_week"):
            week = history["last_week"]
            attributes["last_week_consumption"] = week.get("avg_consumption_l_per_100km")
            attributes["last_week_km"] = week.get("total_km", 0)
            attributes["last_week_liters"] = week.get("total_liters", 0)
            attributes["last_week_refuel_count"] = week.get("refuel_count", 0)
            attributes["last_week_cost"] = week.get("total_cost", 0.0)
            
            # Detect if weekly data is suspiciously similar to daily data
            if history.get("today"):
                today_km = history["today"].get("total_km", 0)
                week_km = week.get("total_km", 0)
                # If they're exactly the same or very close (within 1%), it's suspicious
                if today_km > 0 and week_km > 0 and abs(week_km - today_km) / today_km < 0.01:
                    if "data_quality_warning" not in attributes:
                        attributes["data_quality_warning"] = ""
                    else:
                        attributes["data_quality_warning"] += " "
                    attributes["data_quality_warning"] += (
                        f"Last week and today show nearly identical km ({week_km} vs {today_km}). "
                        "This suggests all refueling events may have the same or very recent timestamps. "
                        "Check if historical data was imported correctly or if refueling events need to be updated."
                    )
        
        # Last 14 days
        if history.get("last_14_days"):
            two_weeks = history["last_14_days"]
            attributes["last_14_days_consumption"] = two_weeks.get("avg_consumption_l_per_100km")
            attributes["last_14_days_km"] = two_weeks.get("total_km", 0)
            attributes["last_14_days_liters"] = two_weeks.get("total_liters", 0)
            attributes["last_14_days_refuel_count"] = two_weeks.get("refuel_count", 0)
            attributes["last_14_days_cost"] = two_weeks.get("total_cost", 0.0)
        
        # Last month
        if history.get("last_month"):
            month = history["last_month"]
            attributes["last_month_consumption"] = month.get("avg_consumption_l_per_100km")
            attributes["last_month_km"] = month.get("total_km", 0)
            attributes["last_month_liters"] = month.get("total_liters", 0)
            attributes["last_month_refuel_count"] = month.get("refuel_count", 0)
            attributes["last_month_cost"] = month.get("total_cost", 0.0)
        
        # Add weekday driving pattern if available in consumption_prediction
        if consumption_prediction:
            weekday_pattern = consumption_prediction.get("weekday_pattern")
            formatted_pattern = format_weekday_pattern(weekday_pattern)
            if formatted_pattern:
                attributes["weekday_driving_pattern"] = formatted_pattern
        
        # Add metadata from consumption_prediction if available
        self._add_prediction_metadata(attributes, consumption_prediction)
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("consumption_history_sensor")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class ConsumptionForecastSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing forecasted average consumption based on prediction engine."""

    _attr_icon = "mdi:chart-timeline-variant"
    _attr_native_unit_of_measurement = "L/100km"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = None
    _attr_has_entity_name = True
    _attr_suggested_display_precision = 2  # Limit to 2 decimal places in history

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
    
    def _add_prediction_metadata(
        self,
        attributes: dict[str, Any],
        consumption_prediction: dict[str, Any] | None,
    ) -> None:
        """Add prediction metadata attributes (data_points, percentage, etc).
        
        Args:
            attributes: Dictionary to add attributes to
            consumption_prediction: Consumption prediction data
        """
        add_prediction_metadata_to_attributes(attributes, consumption_prediction, self._config_entry)

    @property
    def native_value(self) -> float | None:
        """Return the forecasted consumption for tomorrow."""
        if self.coordinator.data is None:
            return None
        forecast = self.coordinator.data.get("consumption_forecast")
        if forecast and forecast.get("tomorrow"):
            return forecast["tomorrow"].get("avg_consumption_l_per_100km")
        return None
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return forecasted consumption for different time periods."""
        if self.coordinator.data is None:
            return {}
        forecast = self.coordinator.data.get("consumption_forecast")
        consumption_prediction = self.coordinator.data.get("consumption_prediction")
        
        # Initialize attributes with default null values for all forecast periods
        attributes = {
            "tomorrow_consumption": None,  # L/100km
            "tomorrow_confidence": None,
            "tomorrow_data_source": None,
            "next_week_consumption": None,  # L/100km
            "next_week_confidence": None,
            "next_week_data_source": None,
            "next_14_days_consumption": None,  # L/100km
            "next_14_days_confidence": None,
            "next_14_days_data_source": None,
            "next_month_consumption": None,  # L/100km
            "next_month_confidence": None,
            "next_month_data_source": None,
        }
        
        if not forecast:
            attributes["status"] = "Waiting for prediction data"
            # Still add metadata even if forecast is missing
            self._add_prediction_metadata(attributes, consumption_prediction)
            return attributes
        
        # Tomorrow's forecast
        if forecast.get("tomorrow"):
            tomorrow = forecast["tomorrow"]
            attributes["tomorrow_consumption"] = tomorrow.get("avg_consumption_l_per_100km")
            attributes["tomorrow_confidence"] = tomorrow.get("confidence", 0.0)
            attributes["tomorrow_data_source"] = tomorrow.get("data_source", "unknown")
            # Include cost forecast if calculated by coordinator
            if tomorrow.get("forecast_cost") is not None:
                attributes["tomorrow_cost"] = tomorrow.get("forecast_cost")
        
        # Next week
        if forecast.get("next_week"):
            week = forecast["next_week"]
            attributes["next_week_consumption"] = week.get("avg_consumption_l_per_100km")
            attributes["next_week_confidence"] = week.get("confidence", 0.0)
            attributes["next_week_data_source"] = week.get("data_source", "unknown")
            # Include cost forecast if calculated by coordinator
            if week.get("forecast_cost") is not None:
                attributes["next_week_cost"] = week.get("forecast_cost")
        
        # Next 14 days
        if forecast.get("next_14_days"):
            two_weeks = forecast["next_14_days"]
            attributes["next_14_days_consumption"] = two_weeks.get("avg_consumption_l_per_100km")
            attributes["next_14_days_confidence"] = two_weeks.get("confidence", 0.0)
            attributes["next_14_days_data_source"] = two_weeks.get("data_source", "unknown")
            # Include cost forecast if calculated by coordinator
            if two_weeks.get("forecast_cost") is not None:
                attributes["next_14_days_cost"] = two_weeks.get("forecast_cost")
        
        # Next month
        if forecast.get("next_month"):
            month = forecast["next_month"]
            attributes["next_month_consumption"] = month.get("avg_consumption_l_per_100km")
            attributes["next_month_confidence"] = month.get("confidence", 0.0)
            attributes["next_month_data_source"] = month.get("data_source", "unknown")
            # Include cost forecast if calculated by coordinator
            if month.get("forecast_cost") is not None:
                attributes["next_month_cost"] = month.get("forecast_cost")
        
        # Add weekday driving pattern if available in consumption_prediction
        if consumption_prediction:
            weekday_pattern = consumption_prediction.get("weekday_pattern")
            formatted_pattern = format_weekday_pattern(weekday_pattern)
            if formatted_pattern:
                attributes["weekday_driving_pattern (km)"] = formatted_pattern
        
        # Add metadata from consumption_prediction if available
        self._add_prediction_metadata(attributes, consumption_prediction)
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("consumption_forecast_sensor")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
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
        if self.coordinator.data is None:
            return 0
        refueling_log = self.coordinator.data.get("refueling_log")
        return len(refueling_log) if refueling_log else 0
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed refueling events as attributes.
        
        Returns the last 5 refueling events with all details for debugging.
        Use get_all_refuelings service to access complete history.
        
        Attributes are ordered according to FWCAM standard structure:
        1. Core metadata (data_source)
        2. Update timestamps
        3. Last event summary
        4. Counters
        5. Config & documentation
        6. Mass data (limited to 5 events for debugging only)
        """
        if self.coordinator.data is None:
            return {}
        refueling_log = self.coordinator.data.get("refueling_log")
        
        if not refueling_log:
            return {
                "data_source": "storage",
                "status": "No refueling events recorded",
                "total_events": 0,
                "last_refueling": None,
                "config_entry_id": self._config_entry.entry_id,
                "recent_events": [],
            }
        
        # Filter out events without timestamps and sort by timestamp (newest first)
        events_with_timestamps = [e for e in refueling_log if e.get("timestamp")]
        sorted_log = sorted(
            events_with_timestamps,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        # Get the most recent refueling (summary only, not full event)
        last_refueling = None
        if sorted_log:
            last_event = sorted_log[0]
            last_refueling = {
                "timestamp": last_event.get("timestamp"),
                "liters": last_event.get("liters_refueled"),
                "cost": last_event.get("total_cost"),
                "station": last_event.get("station_name"),
            }
        
        # Count total excluded events in the entire log
        total_excluded = sum(1 for e in refueling_log if e.get("excluded_from_calculation", False))
        
        # Build attributes in standard order
        # 1. Core metadata
        attrs = {
            "data_source": "storage",
        }
        
        # 2. Update timestamps
        last_historical_import = self.coordinator.data.get("last_historical_import")
        if last_historical_import:
            attrs["last_historical_import_timestamp"] = last_historical_import.get("timestamp")
            attrs["last_historical_import_type"] = last_historical_import.get("type")
        
        last_vehicle_refresh = self.coordinator.data.get("last_vehicle_data_refresh")
        if last_vehicle_refresh:
            attrs["last_vehicle_data_refresh_timestamp"] = last_vehicle_refresh.get("timestamp")
            attrs["last_vehicle_data_refresh_type"] = last_vehicle_refresh.get("type")
        
        # 3. Last event summary
        attrs["last_refueling"] = last_refueling
        
        # 4. Counters
        attrs.update({
            "total_events": len(refueling_log),
            "total_excluded": total_excluded,
            "total_active": len(refueling_log) - total_excluded,
        })
        
        # 5. Status
        attrs["status"] = f"{len(refueling_log)} refueling events recorded ({total_excluded} excluded from calculations)"
        
        # 6. Configuration & documentation metadata
        attrs["config_entry_id"] = self._config_entry.entry_id
        
        metadata = get_entity_metadata("refueling_log_sensor")
        if metadata:
            attrs[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attrs[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attrs[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attrs[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        # 7. Mass data (LIMITED to 5 events for debugging only)
        # NOTE: Components should use get_all_refuelings service for complete history
        recent_events = []
        for event in sorted_log[:5]:  # Reduced from 10 to 5
            is_excluded = event.get("excluded_from_calculation", False)
            
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
                "excluded_from_calculation": is_excluded,
                "exclusion_reason": event.get("exclusion_reason") if is_excluded else None,
                "telegram_response_received": event.get("telegram_response_received", False),
                "telegram_response_timestamp": event.get("telegram_response_timestamp"),
                "telegram_response_type": event.get("telegram_response_type"),
                "telegram_response_raw": event.get("telegram_response_raw"),
                "telegram_response_parsed": event.get("telegram_response_parsed"),
            }
            recent_events.append(event_info)
        
        attrs["recent_events"] = recent_events
        
        return attrs


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
        """Return additional state attributes.
        
        Returns top 5 cheapest stations for debugging.
        Use geolocation features or services for complete station list.
        
        Attributes are ordered according to FWCAM standard structure:
        1. Core metadata (data_source, location info)
        2. Configuration (radius, max stations)
        3. Config & documentation
        4. Mass data (limited to 5 stations)
        """
        if not self.coordinator.data:
            return {}
        
        nearby_data = self.coordinator.data.get("nearby_cheap_stations")
        if not nearby_data:
            return {
                "data_source": "api",
                "stations": [],
                "search_radius_km": None,
                "vehicle_latitude": None,
                "vehicle_longitude": None,
                "max_stations": None,
                "location_source": None,
            }
        
        # Build attributes in standard order
        # 1. Core metadata
        attributes = {
            "data_source": "api",
            "location_source": self.coordinator.data.get("location_source"),
        }
        
        # 2. Configuration
        attributes.update({
            "search_radius_km": nearby_data.get("search_radius_km"),
            "max_stations": nearby_data.get("max_stations"),
            "vehicle_latitude": nearby_data.get("vehicle_latitude"),
            "vehicle_longitude": nearby_data.get("vehicle_longitude"),
        })
        
        # 3. Configuration & documentation metadata
        attributes["config_entry_id"] = self._config_entry.entry_id
        
        metadata = get_entity_metadata("nearby_cheap_stations_sensor")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        # 4. Mass data (LIMITED to 5 stations)
        # Get top 5 cheapest stations only for debugging
        all_stations = nearby_data.get("stations", [])
        # Use heapq for efficient top-N selection without full sort
        if len(all_stations) <= 5:
            attributes["stations"] = sorted(all_stations, key=lambda x: x.get("price", float('inf')))
        else:
            attributes["stations"] = heapq.nsmallest(5, all_stations, key=lambda x: x.get("price", float('inf')))
        
        return attributes
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class TripLogSensor(CoordinatorEntity, SensorEntity):
    """Sensor displaying trip log with history and statistics."""
    
    _attr_icon = "mdi:book-open-variant"
    _attr_has_entity_name = True
    _attr_state_class = None
    
    def __init__(
        self,
        coordinator: HaFWCMACoordinator,
        config_entry: ConfigEntry,
        vehicle_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_name = "Trip Log"
        self._attr_unique_id = f"{config_entry.entry_id}_trip_log"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    @property
    def native_value(self) -> int:
        """Return the total number of trips."""
        if not self.coordinator.data:
            return 0
        
        stats = self.coordinator.data.get("trip_statistics", {})
        return stats.get("total_trips", 0)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return trip statistics and recent trips.
        
        Returns the last 5 trips for debugging only.
        Use get_all_trips service to access complete history.
        
        Attributes are ordered according to FWCAM standard structure:
        1. Core metadata (data_source, trip tracking enabled)
        2. Update timestamps
        3. Counters (trip counts, totals)
        4. Config & documentation
        5. Mass data (limited to 5 trips for debugging only)
        """
        if not self.coordinator.data:
            return {
                "data_source": "storage",
                "trip_tracking_enabled": False,
                "last_historical_import_timestamp": DEFAULT_HISTORICAL_IMPORT_TIMESTAMP,
                "last_historical_import_type": DEFAULT_HISTORICAL_IMPORT_TYPE,
            }
        
        stats = self.coordinator.data.get("trip_statistics", {})
        trips = self.coordinator.data.get("trips", [])
        
        # Sort all trips by end time (newest first)
        sorted_trips = sorted(trips, key=lambda x: x.get("timestamp_end", ""), reverse=True)
        
        # Build attributes in standard order
        # 1. Core metadata
        attrs = {
            "data_source": "storage",
            "trip_tracking_enabled": self.coordinator.data.get("trip_tracking_config", {}).get("enabled", False),
        }
        
        # 2. Update timestamps
        last_historical_import = self.coordinator.data.get("last_historical_import")
        if last_historical_import:
            attrs["last_historical_import_timestamp"] = last_historical_import.get("timestamp", DEFAULT_HISTORICAL_IMPORT_TIMESTAMP)
            attrs["last_historical_import_type"] = last_historical_import.get("type", DEFAULT_HISTORICAL_IMPORT_TYPE)
            attrs["last_historical_import_completed_timestamp"] = last_historical_import.get("completion_timestamp")
            attrs["last_historical_import_trips_detected"] = last_historical_import.get("trips_detected", 0)
            attrs["last_historical_import_odometer_points"] = last_historical_import.get("odometer_points_available", 0)
        else:
            # If no historical import has been done, set default values
            attrs["last_historical_import_timestamp"] = DEFAULT_HISTORICAL_IMPORT_TIMESTAMP
            attrs["last_historical_import_type"] = DEFAULT_HISTORICAL_IMPORT_TYPE
            attrs["last_historical_import_completed_timestamp"] = None
            attrs["last_historical_import_trips_detected"] = 0
            attrs["last_historical_import_odometer_points"] = 0
        
        last_vehicle_refresh = self.coordinator.data.get("last_vehicle_data_refresh")
        if last_vehicle_refresh:
            attrs["last_vehicle_data_refresh_timestamp"] = last_vehicle_refresh.get("timestamp")
            attrs["last_vehicle_data_refresh_type"] = last_vehicle_refresh.get("type")
        
        # 3. Counters and statistics
        attrs.update({
            "total_trips": stats.get("total_trips", 0),
            "business_trips": stats.get("business_trips", 0),
            "private_trips": stats.get("private_trips", 0),
            "commute_trips": stats.get("commute_trips", 0),
            "total_distance_km": round(stats.get("total_distance_km", 0.0), 2),
            "total_fuel_consumed": round(stats.get("total_fuel_consumed", 0.0), 2),
            "total_fuel_cost": round(stats.get("total_fuel_cost", 0.0), 2),
            "total_additional_costs": round(stats.get("total_additional_costs", 0.0), 2),
        })
        
        # 4. Configuration & documentation metadata
        attrs["config_entry_id"] = self._config_entry.entry_id
        
        metadata = get_entity_metadata("trip_log_sensor")
        if metadata:
            attrs[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attrs[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attrs[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attrs[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        # 5. Mass data (LIMITED to 5 trips for debugging only)
        # NOTE: Components should use get_all_trips service for complete history
        attrs["recent_trips"] = sorted_trips[:5]  # Reduced from 10 to 5
        
        return attrs
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class CurrentTripSensor(CoordinatorEntity, SensorEntity):
    """Sensor displaying current trip in progress."""
    
    _attr_icon = "mdi:map-marker-path"
    _attr_has_entity_name = True
    _attr_state_class = None
    
    def __init__(
        self,
        coordinator: HaFWCMACoordinator,
        config_entry: ConfigEntry,
        vehicle_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Current Trip"
        self._attr_unique_id = f"{config_entry.entry_id}_current_trip"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    @property
    def native_value(self) -> str:
        """Return the state of the current trip."""
        if not self.coordinator.data:
            return "No trip"
        
        trip_state = self.coordinator.data.get("trip_tracking_state", {})
        
        if trip_state.get("on_trip", False):
            current_trip = trip_state.get("current_trip")
            if current_trip:
                distance = current_trip.get("distance_km", 0)
                return f"{distance:.1f} km"
        
        return "No trip"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return current trip details."""
        if not self.coordinator.data:
            return {"on_trip": False}
        
        trip_state = self.coordinator.data.get("trip_tracking_state", {})
        on_trip = trip_state.get("on_trip", False)
        
        if not on_trip:
            attributes = {
                "on_trip": False,
                "trip_tracking_enabled": self.coordinator.data.get("trip_tracking_config", {}).get("enabled", False),
            }
        else:
            current_trip = trip_state.get("current_trip", {})
            
            attributes = {
                "on_trip": True,
                "timestamp_start": current_trip.get("timestamp_start"),
                "distance_km": round(current_trip.get("distance_km", 0), 2),
                "odometer_start": current_trip.get("odometer_start"),
                "start_latitude": current_trip.get("start_latitude"),
                "start_longitude": current_trip.get("start_longitude"),
                "duration": current_trip.get("duration"),
                "duration_minutes": round(current_trip.get("duration_minutes", 0), 1),
                "trip_tracking_enabled": self.coordinator.data.get("trip_tracking_config", {}).get("enabled", False),
            }
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("current_trip_sensor")
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


