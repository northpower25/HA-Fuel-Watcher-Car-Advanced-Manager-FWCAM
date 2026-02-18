"""Button platform for haFWCMA integration."""
from __future__ import annotations

import aiohttp
import csv
import logging
import os
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ENTITY_DATA_SOURCE,
    ATTR_ENTITY_DEPENDENCIES,
    ATTR_ENTITY_DOCUMENTATION_URL,
    ATTR_ENTITY_PURPOSE,
    CONF_API_KEY,
    CONF_CHEAP_STATIONS_RADIUS,
    CONF_FUEL_TYPE,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_POSITION_ENTITY,
    CONF_PROVIDER,
    CONF_VEHICLE_NAME,
    DEFAULT_CHEAP_STATIONS_RADIUS,
    DOMAIN,
    PROVIDER_TANKERKONIG,
)
from .entity_metadata import get_entity_metadata
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
        RecalculateTripStatisticsButton(coordinator, config_entry, vehicle_name, hass),
        ValidateRefuelingEventsButton(coordinator, config_entry, vehicle_name, hass),
        RefreshVehicleDataButton(coordinator, config_entry, vehicle_name, hass),
        FuelPriceRefreshButton(coordinator, config_entry, vehicle_name),
        ConsumptionPredictionButton(coordinator, config_entry, vehicle_name),
        ExportVehicleDataButton(coordinator, config_entry, vehicle_name, hass),
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
        radius = options.get(CONF_CHEAP_STATIONS_RADIUS, DEFAULT_CHEAP_STATIONS_RADIUS)
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
        attributes = self._last_result.copy() if isinstance(self._last_result, dict) else {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("test_provider_connection_button")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class ImportHistoricalDataButton(ButtonEntity):
    """Button to import historical vehicle data (odometer & refueling) from recorder."""

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
        self._attr_name = "Import Historical Vehicle Data"
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
        """Handle button press - import historical vehicle data (odometer & refueling events)."""
        _LOGGER.info("Manual historical vehicle data import triggered (odometer & refueling)")
        
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
                    "Historical vehicle data import successful: %d odometer points, %d refuel events",
                    result["odometer_points_imported"],
                    result["refuel_events_detected"],
                )
            else:
                _LOGGER.warning("Historical vehicle data import skipped: %s", result["reason"])
                
        except Exception as err:
            self._last_result = {
                "imported": False,
                "reason": f"Error: {str(err)}",
                "error_type": type(err).__name__,
                "error_details": str(err),
            }
            _LOGGER.error("Error importing historical vehicle data: %s", err, exc_info=True)
        
        # Trigger coordinator update to recalculate predictions with new data
        if self._coordinator:
            await self._coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with import results."""
        attributes = self._last_result.copy() if isinstance(self._last_result, dict) else {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("import_historical_data_button")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class ImportHistoricalTripDataButton(ButtonEntity):
    """Button to import historical trip data (GPS-based trips) from recorder."""

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
        """Handle button press - import historical trip data (GPS-based trips)."""
        _LOGGER.info("Manual historical trip data import triggered (GPS-based trips)")
        
        try:
            from .utils.historical_data_import import import_historical_trip_data
            from .utils import storage
            
            # Check if trip tracking is enabled from storage
            data = await storage.load_data(self._hass, self._config_entry)
            trip_config = data.get("trip_tracking_config", {})
            trip_tracking_enabled = trip_config.get("enabled", False)
            
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
                    "Historical trip data import successful: %d trips detected",
                    result["trips_detected"],
                )
            else:
                _LOGGER.warning("Historical trip data import skipped: %s", result["reason"])
                
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
        attributes = self._last_result.copy() if isinstance(self._last_result, dict) else {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("import_historical_trip_data_button")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class RecalculateTripStatisticsButton(ButtonEntity):
    """Button to recalculate trip statistics from existing trips."""

    _attr_icon = "mdi:calculator"
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
        self._attr_name = "Recalculate Trip Statistics"
        self._attr_unique_id = f"{config_entry.entry_id}_recalculate_trip_statistics"
        self._last_result: dict[str, Any] = {}
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    async def async_press(self) -> None:
        """Handle button press - recalculate trip statistics and force consumption prediction update."""
        _LOGGER.info("Manual trip statistics recalculation triggered")
        
        try:
            from .utils.storage import recalculate_trip_statistics
            
            # Recalculate statistics
            stats = await recalculate_trip_statistics(self._hass, self._config_entry)
            
            self._last_result = {
                "success": True,
                "total_trips": stats.get("total_trips", 0),
                "total_distance_km": round(stats.get("total_distance_km", 0.0), 2),
                "total_fuel_consumed": round(stats.get("total_fuel_consumed", 0.0), 2),
                "business_trips": stats.get("business_trips", 0),
                "private_trips": stats.get("private_trips", 0),
                "commute_trips": stats.get("commute_trips", 0),
            }
            
            _LOGGER.info(
                "Trip statistics recalculated: %d trips, %.1f km",
                stats["total_trips"],
                stats["total_distance_km"],
            )
            
            # Force consumption prediction update by calling coordinator's public method
            # This ensures the next coordinator update will recalculate consumption predictions
            if self._coordinator:
                self._coordinator.force_consumption_prediction_update()
                
        except Exception as err:
            self._last_result = {
                "success": False,
                "error": str(err),
                "error_type": type(err).__name__,
            }
            _LOGGER.error("Error recalculating trip statistics: %s", err, exc_info=True)
        
        # Trigger coordinator update to refresh sensors and recalculate consumption predictions
        if self._coordinator:
            await self._coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with recalculation results."""
        attributes = self._last_result.copy() if isinstance(self._last_result, dict) else {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("recalculate_trip_statistics_button")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class ValidateRefuelingEventsButton(ButtonEntity):
    """Button to validate refueling events and exclude suspicious ones from calculations."""

    _attr_icon = "mdi:check-circle-outline"
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
        self._attr_name = "Validate Refueling Events"
        self._attr_unique_id = f"{config_entry.entry_id}_validate_refueling_events"
        self._last_result: dict[str, Any] = {}
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    async def async_press(self) -> None:
        """Handle button press - validate all refueling events."""
        _LOGGER.info("Manual refueling events validation triggered")
        
        try:
            from .utils.storage import auto_validate_refueling_events
            
            # Run auto-validation
            result = await auto_validate_refueling_events(self._hass, self._config_entry)
            
            self._last_result = {
                "success": True,
                "timestamp": dt_util.now().isoformat(),
                "total_events": result["total_events"],
                "validated": result["validated"],
                "newly_excluded": result["newly_excluded"],
                "already_excluded": result["already_excluded"],
                "excluded_event_ids": result["excluded_events"],
            }
            
            _LOGGER.info(
                "Refueling events validation completed: %d total, %d validated, %d newly excluded, %d already excluded",
                result["total_events"],
                result["validated"],
                result["newly_excluded"],
                result["already_excluded"],
            )
            
            # Force consumption prediction update to recalculate with validated data
            if self._coordinator:
                self._coordinator.force_consumption_prediction_update()
                
        except Exception as err:
            self._last_result = {
                "success": False,
                "timestamp": dt_util.now().isoformat(),
                "error": str(err),
                "error_type": type(err).__name__,
            }
            _LOGGER.error("Error validating refueling events: %s", err, exc_info=True)
        
        # Trigger coordinator update to refresh sensors with validated data
        if self._coordinator:
            await self._coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with validation results."""
        attributes = self._last_result.copy() if isinstance(self._last_result, dict) else {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("validate_refueling_events_button")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes


class RefreshVehicleDataButton(ButtonEntity):
    """Button to manually refresh vehicle data from source entities."""

    _attr_icon = "mdi:car-info"
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
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("refresh_vehicle_data_button")
        if metadata:
            attrs[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attrs[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attrs[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attrs[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
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
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("fuel_price_refresh_button")
        if metadata:
            attrs[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attrs[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attrs[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attrs[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
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
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("consumption_prediction_button")
        if metadata:
            attrs[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attrs[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attrs[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attrs[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attrs


class TelegramTestButton(ButtonEntity):
    """Button to test Telegram API connection and bidirectional refueling flow."""
    
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
        
        # Refueling test flow attributes
        self._test_refuel_id: int | None = None
        self._test_refuel_created_at: str | None = None
        self._test_refuel_response_at: str | None = None
        self._test_refuel_response_raw: str | None = None
        self._test_refuel_response_parsed: dict | None = None
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
        
        # Determine method on initialization
        self._update_method_info()
        
        # Listen for refueling response events
        self._setup_event_listener()
    
    def _setup_event_listener(self) -> None:
        """Set up event listener for refueling responses."""
        from homeassistant.core import callback
        
        @callback
        def _handle_refueling_response(event):
            """Handle refueling response event."""
            # Check if this is a response to our test refueling
            refuel_id = event.data.get("refuel_id")
            if refuel_id == self._test_refuel_id:
                self._test_refuel_response_at = dt_util.now().isoformat()
                self._test_refuel_response_raw = event.data.get("telegram_response_raw")
                self._test_refuel_response_parsed = event.data.get("telegram_response_parsed")
                self._last_receive_result = "response_received"
                self.async_write_ha_state()
        
        # Listen for refueling update events
        self._hass.bus.async_listen(
            f"{DOMAIN}_refueling_updated",
            _handle_refueling_response
        )
    
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
        """Handle button press - trigger Telegram API test with refueling flow."""
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
            # If bidirectional is supported, create a real test refueling
            if self._supports_bidirectional:
                await self._test_bidirectional_flow(timestamp)
            else:
                # Just send a simple test message
                await self._test_unidirectional_flow(timestamp, telegram_token, telegram_chat_id)
            
            self._last_send_result = "success"
            
        except TelegramError as err:
            _LOGGER.error("Telegram API test failed: %s", err)
            self._last_send_result = f"error: {err}"
            self._last_receive_result = "not_tested"
        except Exception as err:
            _LOGGER.error("Unexpected error during Telegram test: %s", err)
            self._last_send_result = f"error: {err}"
            self._last_receive_result = "not_tested"
    
    async def _test_bidirectional_flow(self, timestamp: str) -> None:
        """Test the bidirectional flow by creating a real refueling event.
        
        Args:
            timestamp: Test timestamp
        """
        from .utils.storage import add_refuel_event
        import random
        
        _LOGGER.info("Testing bidirectional Telegram flow with real refueling event")
        
        # Create a test refueling with missing data
        liters = round(random.uniform(30.0, 55.0), 2)
        event_data = {
            "timestamp": timestamp,
            "liters_refueled": liters,
            "fuel_type": "e10",
            "data_quality": "manual",  # Will be changed to ai_processed when user responds
            "confidence": 0.8,
            "notes": "🧪 TEST - Created by Telegram Test Button",
            # Intentionally omit: odometer_km, price_per_liter, total_cost, station_name
        }
        
        # Add the refueling event
        event_id = await add_refuel_event(self._hass, self._config_entry, event_data)
        self._test_refuel_id = event_id
        self._test_refuel_created_at = timestamp
        self._test_refuel_response_at = None
        self._test_refuel_response_raw = None
        self._test_refuel_response_parsed = None
        
        _LOGGER.info("Test refueling created with ID %s", event_id)
        
        # Fire event for Telegram notification (this will trigger the notification)
        _LOGGER.info(
            "Firing %s_refueling_added event (config_entry_id: %s, refuel_id: %s)",
            DOMAIN,
            self._config_entry.entry_id,
            event_id
        )
        self._hass.bus.async_fire(
            f"{DOMAIN}_refueling_added",
            {
                "config_entry_id": self._config_entry.entry_id,
                "refuel_id": event_id,
                "refuel_data": event_data,
            }
        )
        _LOGGER.info("Event fired successfully. Notification should be sent shortly.")
        
        # Update status
        self._last_receive_result = "waiting_for_response"
        
        # Trigger coordinator refresh to update sensors immediately
        if self._coordinator:
            await self._coordinator.async_request_refresh()
    
    async def _test_unidirectional_flow(
        self,
        timestamp: str,
        telegram_token: str,
        telegram_chat_id: str
    ) -> None:
        """Test unidirectional flow (direct API without telegram_bot integration).
        
        Args:
            timestamp: Test timestamp
            telegram_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
        """
        from telegram import Bot
        from .const import TELEGRAM_METHOD_INTEGRATION
        
        test_message = (
            "🧪 <b>Telegram API Test</b>\n\n"
            f"Method: <code>{self._method_used}</code>\n"
            f"Timestamp: {timestamp}\n\n"
            "✅ Send test successful!\n\n"
            "⚠️ <b>Note:</b> Bidirectional communication requires the "
            "<code>telegram_bot</code> integration to be installed and configured."
        )
        
        if self._method_used == TELEGRAM_METHOD_INTEGRATION:
            # Use Home Assistant's telegram_bot service
            await self._hass.services.async_call(
                "telegram_bot",
                "send_message",
                {
                    "target": telegram_chat_id,
                    "message": test_message,
                    "parse_mode": "html",
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
        
        self._last_receive_result = "not_supported"
    
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
        
        # Add refueling test flow attributes
        if self._test_refuel_id:
            attrs["test_refuel_id"] = self._test_refuel_id
        
        if self._test_refuel_created_at:
            attrs["test_refuel_created_at"] = self._test_refuel_created_at
        
        if self._test_refuel_response_at:
            attrs["test_refuel_response_at"] = self._test_refuel_response_at
            # Calculate response time
            try:
                from datetime import datetime
                created = datetime.fromisoformat(self._test_refuel_created_at)
                responded = datetime.fromisoformat(self._test_refuel_response_at)
                response_time_seconds = (responded - created).total_seconds()
                attrs["test_response_time_seconds"] = round(response_time_seconds, 2)
            except:
                pass
        
        if self._test_refuel_response_raw:
            attrs["test_refuel_response_raw"] = self._test_refuel_response_raw
        
        if self._test_refuel_response_parsed:
            attrs["test_refuel_response_parsed"] = self._test_refuel_response_parsed
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("telegram_test_button")
        if metadata:
            attrs[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attrs[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attrs[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attrs[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attrs


class ExportVehicleDataButton(ButtonEntity):
    """TEMPORARY Button to export vehicle entity data to CSV for test data generation.
    
    This button exports all available historical data and long-term statistics
    for configured vehicle entities (odometer, tank level, position, range) to 
    CSV files in /config/www/export/ for test dataset creation.
    
    NOTE: This is a temporary debug feature and will be removed in a future version.
    """
    
    _attr_icon = "mdi:database-export"
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
        self._attr_name = "Export Vehicle Data (Debug)"
        self._attr_unique_id = f"{config_entry.entry_id}_export_vehicle_data"
        self._last_result: dict[str, Any] = {}
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    async def async_press(self) -> None:
        """Handle button press - export vehicle entity data to CSV files."""
        _LOGGER.info("Manual vehicle data export triggered (TEMPORARY DEBUG FEATURE)")
        
        try:
            from .const import (
                CONF_ODOMETER_ENTITY,
                CONF_TANK_LEVEL_ENTITY,
                CONF_RANGE_ENTITY,
                CONF_POSITION_ENTITY,
            )
            from homeassistant.components.recorder import get_instance, history
            from homeassistant.components.recorder.statistics import statistics_during_period
            
            # Get entity IDs from config
            config = self._config_entry.data
            options = self._config_entry.options
            
            entities = {
                "odometer": options.get(CONF_ODOMETER_ENTITY) or config.get(CONF_ODOMETER_ENTITY),
                "tank_level": options.get(CONF_TANK_LEVEL_ENTITY) or config.get(CONF_TANK_LEVEL_ENTITY),
                "range": options.get(CONF_RANGE_ENTITY) or config.get(CONF_RANGE_ENTITY),
                "position": options.get(CONF_POSITION_ENTITY) or config.get(CONF_POSITION_ENTITY),
            }
            
            # Filter out None values
            entities = {k: v for k, v in entities.items() if v is not None}
            
            if not entities:
                self._last_result = {
                    "success": False,
                    "error": "No vehicle entities configured",
                    "timestamp": dt_util.now().isoformat(),
                }
                _LOGGER.warning("No vehicle entities configured for export")
                return
            
            # Create export directory
            export_dir = "/config/www/export"
            await self._hass.async_add_executor_job(os.makedirs, export_dir, 0o755, True)
            
            # Check if recorder is available
            try:
                recorder_instance = await self._hass.async_add_executor_job(get_instance, self._hass)
                if not recorder_instance:
                    self._last_result = {
                        "success": False,
                        "error": "Recorder not available",
                        "timestamp": dt_util.now().isoformat(),
                    }
                    _LOGGER.warning("Recorder not available for data export")
                    return
            except Exception as err:
                self._last_result = {
                    "success": False,
                    "error": f"Error checking recorder: {err}",
                    "timestamp": dt_util.now().isoformat(),
                }
                _LOGGER.error("Error checking recorder availability: %s", err)
                return
            
            # Calculate time range - export all available data
            end_time = dt_util.now()
            # Try to get 365 days of data
            start_time = end_time - timedelta(days=365)
            
            result = {
                "success": True,
                "exported_entities": {},
                "export_path": export_dir,
                "timestamp": dt_util.now().isoformat(),
                "date_range_start": start_time.isoformat(),
                "date_range_end": end_time.isoformat(),
            }
            
            # Export each entity
            for entity_name, entity_id in entities.items():
                try:
                    _LOGGER.info("Exporting data for %s (%s)", entity_name, entity_id)
                    
                    stats = await self._export_entity_data(
                        entity_id,
                        entity_name,
                        start_time,
                        end_time,
                        export_dir,
                        recorder_instance,
                    )
                    
                    result["exported_entities"][entity_name] = stats
                    _LOGGER.info(
                        "Exported %s: %d history points, %d statistics points",
                        entity_name,
                        stats["history_points"],
                        stats["statistics_points"],
                    )
                    
                except Exception as err:
                    _LOGGER.error("Error exporting %s: %s", entity_name, err, exc_info=True)
                    result["exported_entities"][entity_name] = {
                        "error": str(err),
                        "history_points": 0,
                        "statistics_points": 0,
                    }
            
            self._last_result = result
            _LOGGER.info(
                "Vehicle data export completed: %d entities exported to %s",
                len([e for e in result["exported_entities"].values() if "error" not in e]),
                export_dir,
            )
            
        except Exception as err:
            self._last_result = {
                "success": False,
                "error": str(err),
                "error_type": type(err).__name__,
                "timestamp": dt_util.now().isoformat(),
            }
            _LOGGER.error("Error during vehicle data export: %s", err, exc_info=True)
    
    async def _export_entity_data(
        self,
        entity_id: str,
        entity_name: str,
        start_time: datetime,
        end_time: datetime,
        export_dir: str,
        recorder_instance: Any,
    ) -> dict[str, Any]:
        """Export data for a single entity to CSV files.
        
        Args:
            entity_id: Entity ID to export
            entity_name: Name for the CSV file
            start_time: Start of time range
            end_time: End of time range
            export_dir: Directory to export to
            recorder_instance: Recorder instance
            
        Returns:
            Statistics about exported data
        """
        timestamp_str = dt_util.now().strftime("%Y%m%d_%H%M%S")
        
        # Export history (short-term)
        history_file = os.path.join(export_dir, f"{entity_name}_history_{timestamp_str}.csv")
        history_count = await self._export_history(
            entity_id,
            start_time,
            end_time,
            history_file,
            recorder_instance,
        )
        
        # Export statistics (long-term)
        statistics_file = os.path.join(export_dir, f"{entity_name}_statistics_{timestamp_str}.csv")
        statistics_count = await self._export_statistics(
            entity_id,
            start_time,
            end_time,
            statistics_file,
            recorder_instance,
        )
        
        return {
            "entity_id": entity_id,
            "history_file": history_file,
            "history_points": history_count,
            "statistics_file": statistics_file,
            "statistics_points": statistics_count,
        }
    
    async def _export_history(
        self,
        entity_id: str,
        start_time: datetime,
        end_time: datetime,
        output_file: str,
        recorder_instance: Any,
    ) -> int:
        """Export short-term history to CSV.
        
        Args:
            entity_id: Entity ID to export
            start_time: Start of time range
            end_time: End of time range
            output_file: Output CSV file path
            recorder_instance: Recorder instance
            
        Returns:
            Number of data points exported
        """
        from homeassistant.components.recorder import history
        
        count = 0
        
        try:
            # Query history in chunks to avoid memory issues
            chunk_days = 7
            current_start = start_time
            all_states = []
            
            while current_start < end_time:
                current_end = min(current_start + timedelta(days=chunk_days), end_time)
                
                chunk_states = await recorder_instance.async_add_executor_job(
                    history.state_changes_during_period,
                    self._hass,
                    current_start,
                    current_end,
                    entity_id,
                )
                
                if chunk_states and entity_id in chunk_states:
                    all_states.extend(chunk_states[entity_id])
                
                current_start = current_end
            
            if not all_states:
                _LOGGER.debug("No history found for %s", entity_id)
                # Create empty file
                await self._hass.async_add_executor_job(
                    self._write_csv,
                    output_file,
                    ["timestamp", "state", "attributes"],
                    [],
                )
                return 0
            
            # Prepare data for CSV
            rows = []
            for state in all_states:
                # Get attributes as a string representation
                attrs_str = str(state.attributes) if state.attributes else ""
                
                rows.append({
                    "timestamp": state.last_changed.isoformat() if state.last_changed else "",
                    "state": state.state if state.state is not None else "",
                    "attributes": attrs_str,
                })
            
            # Write to CSV
            await self._hass.async_add_executor_job(
                self._write_csv,
                output_file,
                ["timestamp", "state", "attributes"],
                rows,
            )
            
            count = len(rows)
            _LOGGER.debug("Exported %d history points for %s to %s", count, entity_id, output_file)
            
        except Exception as err:
            _LOGGER.error("Error exporting history for %s: %s", entity_id, err, exc_info=True)
            raise
        
        return count
    
    async def _export_statistics(
        self,
        entity_id: str,
        start_time: datetime,
        end_time: datetime,
        output_file: str,
        recorder_instance: Any,
    ) -> int:
        """Export long-term statistics to CSV.
        
        Args:
            entity_id: Entity ID to export
            start_time: Start of time range
            end_time: End of time range
            output_file: Output CSV file path
            recorder_instance: Recorder instance
            
        Returns:
            Number of data points exported
        """
        from homeassistant.components.recorder.statistics import statistics_during_period
        
        count = 0
        
        try:
            # Fetch statistics
            stats = await recorder_instance.async_add_executor_job(
                statistics_during_period,
                self._hass,
                start_time,
                end_time,
                {entity_id},
                "hour",
                None,
                {"mean", "min", "max", "state", "sum"},
            )
            
            if not stats or entity_id not in stats:
                _LOGGER.debug("No statistics found for %s", entity_id)
                # Create empty file
                await self._hass.async_add_executor_job(
                    self._write_csv,
                    output_file,
                    ["timestamp", "mean", "min", "max", "state", "sum"],
                    [],
                )
                return 0
            
            # Prepare data for CSV
            rows = []
            for stat in stats[entity_id]:
                timestamp = stat.get("start")
                if isinstance(timestamp, (int, float)):
                    timestamp = dt_util.utc_from_timestamp(timestamp)
                
                rows.append({
                    "timestamp": timestamp.isoformat() if timestamp else "",
                    "mean": stat.get("mean", ""),
                    "min": stat.get("min", ""),
                    "max": stat.get("max", ""),
                    "state": stat.get("state", ""),
                    "sum": stat.get("sum", ""),
                })
            
            # Write to CSV
            await self._hass.async_add_executor_job(
                self._write_csv,
                output_file,
                ["timestamp", "mean", "min", "max", "state", "sum"],
                rows,
            )
            
            count = len(rows)
            _LOGGER.debug("Exported %d statistics points for %s to %s", count, entity_id, output_file)
            
        except Exception as err:
            _LOGGER.error("Error exporting statistics for %s: %s", entity_id, err, exc_info=True)
            raise
        
        return count
    
    def _write_csv(self, filename: str, headers: list[str], rows: list[dict[str, Any]]) -> None:
        """Write data to CSV file.
        
        Args:
            filename: Output filename
            headers: CSV column headers
            rows: List of dictionaries containing row data
        """
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with export results."""
        attributes = self._last_result.copy() if isinstance(self._last_result, dict) else {}
        
        # Add standardized entity metadata for inline documentation
        metadata = get_entity_metadata("export_vehicle_data_button")
        if metadata:
            attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
            attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
            attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
            attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
        
        return attributes
