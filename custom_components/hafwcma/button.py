"""Button platform for haFWCMA integration."""
from __future__ import annotations

import logging
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
        
        # Use vehicle position if available
        if position_entity:
            state = self._hass.states.get(position_entity)
            if state and state.attributes:
                vehicle_lat = state.attributes.get("latitude")
                vehicle_lon = state.attributes.get("longitude")
                if vehicle_lat is not None and vehicle_lon is not None:
                    latitude = vehicle_lat
                    longitude = vehicle_lon
        
        try:
            # Test API connection based on provider
            if provider == PROVIDER_TANKERKONIG:
                from .providers.tankerkonig import TankerkoenigProvider
                import aiohttp
                
                session = aiohttp.ClientSession()
                try:
                    provider_instance = TankerkoenigProvider(api_key, session)
                    
                    # Validate API key
                    is_valid = await provider_instance.validate_api_key(api_key)
                    
                    if is_valid:
                        # Fetch stations
                        stations = await provider_instance.get_stations_nearby(
                            latitude, longitude, radius, fuel_type
                        )
                        
                        self._last_result = {
                            "success": True,
                            "message": f"Connection successful! Found {len(stations)} stations.",
                            "stations_count": len(stations),
                            "nearest_station": stations[0].name if stations else None,
                            "nearest_price": stations[0].get_price(fuel_type) if stations else None,
                            "nearest_distance": stations[0].distance if stations else None,
                        }
                        _LOGGER.info("API test successful: %s", self._last_result)
                    else:
                        self._last_result = {
                            "success": False,
                            "message": "Invalid API key",
                        }
                        _LOGGER.warning("API test failed: Invalid API key")
                finally:
                    await session.close()
            else:
                self._last_result = {
                    "success": False,
                    "message": f"Provider '{provider}' not yet implemented",
                }
                _LOGGER.warning("Provider not implemented: %s", provider)
                
        except Exception as err:
            self._last_result = {
                "success": False,
                "message": f"Error: {str(err)}",
            }
            _LOGGER.error("Error testing API connection: %s", err)
        
        # Trigger coordinator update to reflect test results
        if self._coordinator:
            await self._coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes with test results."""
        return self._last_result
