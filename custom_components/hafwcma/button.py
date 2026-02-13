"""Button platform for haFWCMA integration."""
from __future__ import annotations

import aiohttp
import logging
from datetime import datetime
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_API_KEY,
    CONF_FUEL_TYPE,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_POSITION_ENTITY,
    CONF_PROVIDER,
    CONF_RADIUS,
    CONF_VEHICLE_NAME,
    DOMAIN,
    PROVIDER_TANKERKONIG,
)
from .providers.tankerkonig import TankerkoenigProvider

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up haFWCMA button entities from a config entry.
    
    Args:
        hass: Home Assistant instance
        config_entry: Config entry for this integration
        async_add_entities: Callback to add button entities
    """
    _LOGGER.info("Setting up haFWCMA buttons")

    vehicle_name = config_entry.data.get(CONF_VEHICLE_NAME, "Vehicle")
    
    # Get coordinator from hass.data
    coordinator = hass.data[DOMAIN][config_entry.entry_id].get("coordinator")

    buttons = [
        TestProviderConnectionButton(coordinator, config_entry, vehicle_name, hass),
        ImportHistoricalDataButton(coordinator, config_entry, vehicle_name, hass),
        ImportHistoricalTripDataButton(coordinator, config_entry, vehicle_name, hass),
        RefreshVehicleDataButton(coordinator, config_entry, vehicle_name, hass),
        FuelPriceRefreshButton(coordinator, config_entry, vehicle_name),
        ConsumptionPredictionButton(coordinator, config_entry, vehicle_name),
    ]
    
    # Add TelegramTestButton if telegram is configured
    from .const import CONF_TELEGRAM_CHAT_ID, CONF_TELEGRAM_TOKEN
    telegram_token = config_entry.data.get(CONF_TELEGRAM_TOKEN)
    telegram_chat_id = config_entry.data.get(CONF_TELEGRAM_CHAT_ID)
    if telegram_token and telegram_chat_id:
        buttons.append(TelegramTestButton(coordinator, config_entry, vehicle_name, hass))

    async_add_entities(buttons)


class TestProviderConnectionButton(ButtonEntity):
    """Button to test provider API connection and display results."""

    _attr_icon = "mdi:api"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the button.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
            hass: Home Assistant instance
        """
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._hass = hass
        self._attr_name = "Test API Connection"
        self._attr_unique_id = f"{config_entry.entry_id}_test_connection"
        self._last_result: dict[str, Any] = {}
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    async def async_press(self) -> None:
        """Handle button press - test API connection."""
        _LOGGER.info("Testing provider API connection")
        
        # Get configuration
        config = self._config_entry.data
        options = self._config_entry.options
        
        provider = options.get(CONF_PROVIDER) or config.get(CONF_PROVIDER, PROVIDER_TANKERKONIG)
        api_key = config.get(CONF_API_KEY)
        latitude = config.get(CONF_LATITUDE)
        longitude = config.get(CONF_LONGITUDE)
        radius = options.get(CONF_RADIUS) or config.get(CONF_RADIUS, 5.0)
        fuel_type = options.get(CONF_FUEL_TYPE) or config.get(CONF_FUEL_TYPE, "e5")
        position_entity = options.get(CONF_POSITION_ENTITY) or config.get(CONF_POSITION_ENTITY)
        
        # Track the data source for debugging
        location_source = "fallback (configured)"
        
        # Use vehicle position if available
        if position_entity:
            state = self._hass.states.get(position_entity)
            if state and state.attributes:
                vehicle_lat = state.attributes.get("latitude")
                vehicle_lon = state.attributes.get("longitude")
                if vehicle_lat is not None and vehicle_lon is not None:
                    latitude = vehicle_lat
                    longitude = vehicle_lon
                    location_source = f"vehicle ({position_entity})"
        
        # Build the debug data
        timestamp = dt_util.now().isoformat()
        
        try:
            # Test API connection based on provider
            if provider == PROVIDER_TANKERKONIG:
                # Reuse coordinator's session if available, otherwise create temporary one
                session = None
                own_session = False
                
                if self._coordinator and hasattr(self._coordinator, '_session') and self._coordinator._session:
                    session = self._coordinator._session
                else:
                    # Create session with timeout configuration
                    timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
                    session = aiohttp.ClientSession(timeout=timeout)
                    own_session = True
                
                try:
                    provider_instance = TankerkoenigProvider(api_key, session)
                    
                    # Build the API request URL for debugging
                    api_url = f"https://creativecommons.tankerkoenig.de/json/list.php"
                    # Safely mask API key for debug output
                    masked_key = api_key[:min(8, len(api_key))] + "..." if api_key else None
                    api_params = {
                        "lat": latitude,
                        "lng": longitude,
                        "rad": radius,
                        "type": fuel_type,
                        "apikey": masked_key,
                        "sort": "price",
                    }
                    
                    # Validate API key
                    is_valid = await provider_instance.validate_api_key(api_key)
                    
                    if is_valid:
                        # Fetch stations
                        stations = await provider_instance.get_stations_nearby(
                            latitude, longitude, radius, fuel_type
                        )
                        
                        # Filter open stations with prices
                        stations_with_price = [
                            s for s in stations 
                            if s.get_price(fuel_type) is not None and s.is_open
                        ]
                        
                        self._last_result = {
                            "success": True,
                            "message": f"Connection successful! Found {len(stations)} stations, {len(stations_with_price)} with valid prices and open.",
                            "timestamp": timestamp,
                            "location_source": location_source,
                            "latitude": latitude,
                            "longitude": longitude,
                            "radius_km": radius,
                            "fuel_type": fuel_type,
                            "provider": provider,
                            "api_url": api_url,
                            "api_params": api_params,
                            "stations_total": len(stations),
                            "stations_with_price_and_open": len(stations_with_price),
                            "nearest_station": stations[0].name if stations else None,
                            "nearest_price": stations[0].get_price(fuel_type) if stations else None,
                            "nearest_distance": stations[0].distance if stations else None,
                            "nearest_is_open": stations[0].is_open if stations else None,
                            "cheapest_station": stations_with_price[0].name if stations_with_price else None,
                            "cheapest_price": stations_with_price[0].get_price(fuel_type) if stations_with_price else None,
                            "cheapest_distance": stations_with_price[0].distance if stations_with_price else None,
                        }
                        _LOGGER.info("API test successful: %s", self._last_result)
                    else:
                        self._last_result = {
                            "success": False,
                            "message": "Invalid API key",
                            "timestamp": timestamp,
                            "location_source": location_source,
                            "latitude": latitude,
                            "longitude": longitude,
                            "radius_km": radius,
                            "fuel_type": fuel_type,
                            "provider": provider,
                            "api_url": api_url,
                            "api_params": api_params,
                        }
                        _LOGGER.warning("API test failed: Invalid API key")
                finally:
                    # Only close session if we created it
                    if own_session:
                        await session.close()
            else:
                self._last_result = {
                    "success": False,
                    "message": f"Provider '{provider}' not yet implemented",
                    "timestamp": timestamp,
                    "provider": provider,
                }
                _LOGGER.warning("Provider not implemented: %s", provider)
                
        except Exception as err:
            self._last_result = {
                "success": False,
                "message": f"Error: {str(err)}",
                "timestamp": timestamp,
                "location_source": location_source,
                "latitude": latitude,
                "longitude": longitude,
                "radius_km": radius,
                "fuel_type": fuel_type,
                "provider": provider,
                "error_type": type(err).__name__,
                "error_details": str(err),
            }
            _LOGGER.error("Error testing API connection: %s", err, exc_info=True)
        
        # Trigger coordinator update to reflect test results
        if self._coordinator:
            await self._coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with test results."""
        return self._last_result


class ImportHistoricalDataButton(ButtonEntity):
    """Button to import historical vehicle data from recorder."""

    _attr_icon = "mdi:database-import"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the button.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
            hass: Home Assistant instance
        """
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._hass = hass
        self._attr_name = "Import Historical Data"
        self._attr_unique_id = f"{config_entry.entry_id}_import_historical_data"
        self._last_result: dict[str, Any] = {}
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    async def async_press(self) -> None:
        """Handle button press - import historical data."""
        _LOGGER.info("Manual historical data import triggered")
        
        try:
            from .utils.historical_data_import import import_historical_vehicle_data
            
            # Import with force_reimport=True to allow re-importing and mark as manual
            result = await import_historical_vehicle_data(
                self._hass,
                self._config_entry,
                lookback_days=90,
                force_reimport=True,
                import_type="manual",
            )
            
            self._last_result = result
            
            if result["imported"]:
                _LOGGER.info(
                    "Historical import successful: %d odometer points, %d refuel events",
                    result["odometer_points_imported"],
                    result["refuel_events_detected"],
                )
            else:
                _LOGGER.warning("Historical import skipped: %s", result["reason"])
                
        except Exception as err:
            self._last_result = {
                "imported": False,
                "reason": f"Error: {str(err)}",
                "error_type": type(err).__name__,
                "error_details": str(err),
            }
            _LOGGER.error("Error importing historical data: %s", err, exc_info=True)
        
        # Trigger coordinator update to recalculate predictions with new data
        if self._coordinator:
            await self._coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with import results."""
        return self._last_result


class ImportHistoricalTripDataButton(ButtonEntity):
    """Button to import historical trip data from recorder."""

    _attr_icon = "mdi:database-import-outline"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the button.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
            hass: Home Assistant instance
        """
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._hass = hass
        self._attr_name = "Import Historical Trip Data"
        self._attr_unique_id = f"{config_entry.entry_id}_import_historical_trip_data"
        self._last_result: dict[str, Any] = {}
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    async def async_press(self) -> None:
        """Handle button press - import historical trip data."""
        _LOGGER.info("Manual historical trip data import triggered")
        
        try:
            from .utils.historical_data_import import import_historical_trip_data
            
            # Check if trip tracking is enabled
            trip_tracking_enabled = self._config_entry.data.get("trip_tracking_enabled", False)
            if not trip_tracking_enabled:
                self._last_result = {
                    "imported": False,
                    "reason": "Trip tracking is not enabled. Please enable trip tracking first.",
                    "trips_detected": 0,
                }
                _LOGGER.warning("Historical trip import skipped: Trip tracking not enabled")
                return
            
            # Import with force_reimport=True to allow re-importing and mark as manual
            result = await import_historical_trip_data(
                self._hass,
                self._config_entry,
                lookback_days=90,
                force_reimport=True,
                import_type="manual",
            )
            
            self._last_result = result
            
            if result["imported"]:
                _LOGGER.info(
                    "Historical trip import successful: %d trips detected",
                    result["trips_detected"],
                )
            else:
                _LOGGER.warning("Historical trip import skipped: %s", result["reason"])
                
        except Exception as err:
            self._last_result = {
                "imported": False,
                "reason": f"Error: {str(err)}",
                "error_type": type(err).__name__,
                "error_details": str(err),
            }
            _LOGGER.error("Error importing historical trip data: %s", err, exc_info=True)
        
        # Trigger coordinator update to refresh trip statistics
        if self._coordinator:
            await self._coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with import results."""
        return self._last_result


class RefreshVehicleDataButton(ButtonEntity):
    """Button to manually refresh vehicle data from source entities."""

    _attr_icon = "mdi:car-sync"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the button.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
            hass: Home Assistant instance
        """
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._hass = hass
        self._attr_name = "Refresh Vehicle Data"
        self._attr_unique_id = f"{config_entry.entry_id}_refresh_vehicle_data"
        self._last_refresh_time: str | None = None
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    async def async_press(self) -> None:
        """Handle button press - refresh vehicle data."""
        _LOGGER.info("Manual vehicle data refresh triggered")
        
        # Request coordinator to refresh data (which includes fetching vehicle data)
        if self._coordinator:
            await self._coordinator.async_request_refresh()
            timestamp = dt_util.now().isoformat()
            self._last_refresh_time = timestamp
            
            # Store refresh metadata in storage
            try:
                from .utils.storage import load_data, save_data
                data = await load_data(self._hass, self._config_entry)
                data["last_vehicle_data_refresh"] = {
                    "timestamp": timestamp,
                    "type": "manual",
                }
                await save_data(self._hass, self._config_entry, data)
            except Exception as err:
                _LOGGER.warning("Failed to store refresh metadata: %s", err)
            
            _LOGGER.info("Vehicle data refresh completed")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = {}
        if self._last_refresh_time:
            # Keep old attribute name for backward compatibility
            attrs["last_refresh_time"] = self._last_refresh_time
            # Add new attribute name for consistency
            attrs["last_refresh_timestamp"] = self._last_refresh_time
            attrs["last_refresh_type"] = "manual"
        if self._coordinator and hasattr(self._coordinator, "last_update_success"):
            attrs["last_update_success"] = self._coordinator.last_update_success
        return attrs


class FuelPriceRefreshButton(ButtonEntity):
    """Button to manually trigger fuel price data refresh."""

    _attr_icon = "mdi:refresh"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
    ) -> None:
        """Initialize the button.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
        """
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._attr_name = "Fuel Price Refresh"
        self._attr_unique_id = f"{config_entry.entry_id}_fuel_price_refresh"
        self._last_manual_refresh: str | None = None
        self._last_automatic_refresh: str | None = None
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    async def async_press(self) -> None:
        """Handle button press - trigger manual refresh."""
        _LOGGER.info("Manual fuel price refresh triggered")
        
        # Request coordinator to refresh data
        if self._coordinator:
            await self._coordinator.async_request_refresh()
            timestamp = dt_util.now().isoformat()
            self._last_manual_refresh = timestamp
            _LOGGER.info("Fuel price refresh completed")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = {}
        if self._last_manual_refresh:
            attrs["last_manual_refresh"] = self._last_manual_refresh
        
        # Track automatic refreshes from coordinator
        if self._coordinator and hasattr(self._coordinator, "last_update_time"):
            attrs["last_automatic_refresh"] = self._coordinator.last_update_time
        
        if self._coordinator and hasattr(self._coordinator, "last_update_success"):
            attrs["last_update_success"] = self._coordinator.last_update_success
        return attrs


class ConsumptionPredictionButton(ButtonEntity):
    """Button to manually trigger range/consumption prediction calculation."""

    _attr_icon = "mdi:chart-line"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
    ) -> None:
        """Initialize the button.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
        """
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._attr_name = "Consumption Prediction"
        self._attr_unique_id = f"{config_entry.entry_id}_consumption_prediction"
        self._last_manual_start: str | None = None
        self._last_automatic_start: str | None = None
        self._last_prediction_result = None
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    async def async_press(self) -> None:
        """Handle button press - trigger manual prediction."""
        _LOGGER.info("Manual consumption prediction triggered")
        
        # Force a consumption prediction update
        if self._coordinator:
            try:
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
                
                timestamp = dt_util.now().isoformat()
                self._last_manual_start = timestamp
                self._last_prediction_result = prediction
                
                _LOGGER.info("Manual prediction completed: %s", prediction)
                
                # Directly update coordinator data with the new prediction
                if self._coordinator.data:
                    self._coordinator.data["consumption_prediction"] = prediction
                
                # Request coordinator refresh to update sensors
                await self._coordinator.async_request_refresh()
                
            except Exception as err:
                _LOGGER.error("Error during manual prediction: %s", err, exc_info=True)
                self._last_prediction_result = {"error": str(err)}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = {}
        if self._last_manual_start:
            attrs["last_manual_start"] = self._last_manual_start
        
        # Track automatic starts from coordinator
        if self._coordinator and hasattr(self._coordinator, "_last_consumption_prediction"):
            if self._coordinator._last_consumption_prediction:
                attrs["last_automatic_start"] = self._coordinator._last_consumption_prediction.isoformat()
        
        if self._last_prediction_result:
            attrs["last_prediction_result"] = self._last_prediction_result
        return attrs


class TelegramTestButton(ButtonEntity):
    """Button to test Telegram API connection and method."""
    
    _attr_icon = "mdi:telegram"
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the button.
        
        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            vehicle_name: Name of the vehicle
            hass: Home Assistant instance
        """
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._hass = hass
        self._attr_name = "Telegram API Test"
        self._attr_unique_id = f"{config_entry.entry_id}_telegram_test"
        
        # Test result attributes
        self._last_manual_test: str | None = None
        self._last_automatic_test: str | None = None
        self._method_used = None
        self._supports_bidirectional = False
        self._last_send_result = None
        self._last_receive_result = None
        self._last_received_message = None
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
        
        # Determine method on initialization
        self._update_method_info()
    
    def _update_method_info(self) -> None:
        """Update information about which Telegram method is being used."""
        from .const import TELEGRAM_METHOD_INTEGRATION, TELEGRAM_METHOD_DIRECT_API
        
        # Check if telegram_bot integration is loaded
        if "telegram_bot" in self._hass.config.components:
            self._method_used = TELEGRAM_METHOD_INTEGRATION
            self._supports_bidirectional = True
        else:
            self._method_used = TELEGRAM_METHOD_DIRECT_API
            self._supports_bidirectional = False
    
    async def async_press(self) -> None:
        """Handle button press - trigger Telegram API test."""
        from telegram import Bot
        from telegram.error import TelegramError
        from .const import (
            CONF_TELEGRAM_TOKEN,
            CONF_TELEGRAM_CHAT_ID,
            TELEGRAM_METHOD_INTEGRATION,
        )
        
        _LOGGER.info("Telegram API test triggered")
        
        # Update method info
        self._update_method_info()
        timestamp = dt_util.now().isoformat()
        self._last_manual_test = timestamp
        
        # Get configuration
        telegram_token = self._config_entry.data.get(CONF_TELEGRAM_TOKEN)
        telegram_chat_id = self._config_entry.data.get(CONF_TELEGRAM_CHAT_ID)
        
        if not telegram_token or not telegram_chat_id:
            _LOGGER.error("Telegram not configured")
            self._last_send_result = "error_not_configured"
            return
        
        # Test sending message
        try:
            test_message = (
                "🧪 <b>Telegram API Test</b>\n\n"
                f"Method: <code>{self._method_used}</code>\n"
                f"Timestamp: {timestamp}\n\n"
                "✅ Send test successful!"
            )
            
            if self._method_used == TELEGRAM_METHOD_INTEGRATION:
                # Use Home Assistant's telegram_bot service
                await self._hass.services.async_call(
                    "telegram_bot",
                    "send_message",
                    {
                        "target": telegram_chat_id,
                        "message": test_message,
                        "parse_mode": "HTML",
                    },
                    blocking=True,
                )
                _LOGGER.info("Test message sent via telegram_bot integration")
            else:
                # Use direct Bot API
                bot = Bot(token=telegram_token)
                await bot.send_message(
                    chat_id=telegram_chat_id,
                    text=test_message,
                    parse_mode="HTML",
                )
                _LOGGER.info("Test message sent via direct Bot API")
            
            self._last_send_result = "success"
            
            # For bidirectional test, we would need to set up a listener
            if self._supports_bidirectional:
                self._last_receive_result = "supported_not_tested"
                _LOGGER.info("Bidirectional communication is supported via telegram_bot integration")
            else:
                self._last_receive_result = "not_supported"
                _LOGGER.info("Bidirectional communication not supported with direct API")
            
        except TelegramError as err:
            _LOGGER.error("Telegram API test failed: %s", err)
            self._last_send_result = f"error: {err}"
            self._last_receive_result = "not_tested"
        except Exception as err:
            _LOGGER.error("Unexpected error during Telegram test: %s", err)
            self._last_send_result = f"error: {err}"
            self._last_receive_result = "not_tested"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes about the test results."""
        attrs = {
            "method_used": self._method_used or "not_determined",
            "supports_bidirectional": self._supports_bidirectional,
        }
        
        if self._last_manual_test:
            attrs["last_manual_test"] = self._last_manual_test
        
        if self._last_automatic_test:
            attrs["last_automatic_test"] = self._last_automatic_test
        
        if self._last_send_result:
            attrs["last_send_result"] = self._last_send_result
        
        if self._last_receive_result:
            attrs["last_receive_result"] = self._last_receive_result
        
        if self._last_received_message:
            attrs["last_received_message"] = self._last_received_message
        
        return attrs
