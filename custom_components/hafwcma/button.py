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
    ]

    async_add_entities(buttons)


class TestProviderConnectionButton(ButtonEntity):
    """Button to test provider API connection and display results."""

    _attr_icon = "mdi:api"

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
        self._attr_name = f"{vehicle_name} Test API Connection"
        self._attr_unique_id = f"{config_entry.entry_id}_test_connection"
        self._last_result: dict[str, Any] = {}

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
        timestamp = datetime.now().isoformat()
        
        try:
            # Test API connection based on provider
            if provider == PROVIDER_TANKERKONIG:
                # Reuse coordinator's session if available, otherwise create temporary one
                session = None
                own_session = False
                
                if self._coordinator and hasattr(self._coordinator, '_session') and self._coordinator._session:
                    session = self._coordinator._session
                else:
                    session = aiohttp.ClientSession()
                    own_session = True
                
                try:
                    provider_instance = TankerkoenigProvider(api_key, session)
                    
                    # Build the API request URL for debugging
                    api_url = f"https://creativecommons.tankerkoenig.de/json/list.php"
                    api_params = {
                        "lat": latitude,
                        "lng": longitude,
                        "rad": radius,
                        "type": fuel_type,
                        "apikey": api_key[:8] + "..." if api_key else None,  # Mask API key
                        "sort": "dist",
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
