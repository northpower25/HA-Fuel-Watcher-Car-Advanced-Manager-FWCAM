"""Switch platform for haFWCMA integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_PROXIMITY_ALERTS_ENABLED,
    CONF_TELEGRAM_CHAT_ID,
    CONF_TELEGRAM_METHOD,
    CONF_TELEGRAM_TOKEN,
    CONF_VEHICLE_NAME,
    DEFAULT_PROXIMITY_ALERTS_ENABLED,
    DOMAIN,
    TELEGRAM_METHOD_DIRECT_API,
    TELEGRAM_METHOD_INTEGRATION,
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
        ProximityAlertsSwitch(coordinator, config_entry, vehicle_name, hass),
    ]
    
    # Add TelegramTestSwitch if telegram is configured
    telegram_token = config_entry.data.get(CONF_TELEGRAM_TOKEN)
    telegram_chat_id = config_entry.data.get(CONF_TELEGRAM_CHAT_ID)
    if telegram_token and telegram_chat_id:
        switches.append(TelegramTestSwitch(coordinator, config_entry, vehicle_name, hass))

    async_add_entities(switches)


class ManualRefreshSwitch(SwitchEntity):
    """Switch to manually trigger fuel price data refresh."""

    _attr_icon = "mdi:refresh"
    _attr_has_entity_name = True

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
        self._attr_name = "Fuel Price Refresh"
        self._attr_unique_id = f"{config_entry.entry_id}_fuel_price_refresh"
        self._attr_is_on = False
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

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
    _attr_has_entity_name = True

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
        self._attr_name = "Consumption Prediction"
        self._attr_unique_id = f"{config_entry.entry_id}_consumption_prediction"
        self._attr_is_on = False
        self._last_prediction_time = None
        self._last_prediction_result = None
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch - trigger manual prediction."""
        _LOGGER.info("Manual prediction triggered")
        self._attr_is_on = True
        self.async_write_ha_state()
        
        # Force a consumption prediction update
        if self._coordinator:
            try:
                from homeassistant.util import dt as dt_util
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
                
                self._last_prediction_time = dt_util.now().isoformat()
                self._last_prediction_result = prediction
                
                _LOGGER.info("Manual prediction completed: %s", prediction)
                
                # Directly update coordinator data with the new prediction
                # This ensures the sensor gets updated immediately without waiting for the next interval
                if self._coordinator.data:
                    self._coordinator.data["consumption_prediction"] = prediction
                
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


class ProximityAlertsSwitch(SwitchEntity):
    """Switch to enable/disable proximity alerts for cheap stations."""
    
    _attr_icon = "mdi:bell-alert"
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the switch."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._hass = hass
        self._attr_name = "Proximity Alerts"
        self._attr_unique_id = f"{config_entry.entry_id}_proximity_alerts"
        
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": vehicle_name,
            "manufacturer": "haFWCMA",
            "model": "Fuel Watcher Car Advanced Manager",
        }
    
    @property
    def is_on(self) -> bool:
        """Return true if proximity alerts are enabled."""
        options = self._config_entry.options
        return options.get(CONF_PROXIMITY_ALERTS_ENABLED, DEFAULT_PROXIMITY_ALERTS_ENABLED)
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on proximity alerts."""
        _LOGGER.info("Enabling proximity alerts")
        new_options = dict(self._config_entry.options)
        new_options[CONF_PROXIMITY_ALERTS_ENABLED] = True
        self._hass.config_entries.async_update_entry(self._config_entry, options=new_options)
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off proximity alerts."""
        _LOGGER.info("Disabling proximity alerts")
        new_options = dict(self._config_entry.options)
        new_options[CONF_PROXIMITY_ALERTS_ENABLED] = False
        self._hass.config_entries.async_update_entry(self._config_entry, options=new_options)


class TelegramTestSwitch(SwitchEntity):
    """Switch to test Telegram API connection and method."""
    
    _attr_icon = "mdi:telegram"
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: Any,
        config_entry: ConfigEntry,
        vehicle_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the switch.
        
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
        self._attr_is_on = False
        
        # Test result attributes
        self._last_test_timestamp = None
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
        # Check if telegram_bot integration is loaded
        if "telegram_bot" in self._hass.config.components:
            self._method_used = TELEGRAM_METHOD_INTEGRATION
            self._supports_bidirectional = True
        else:
            self._method_used = TELEGRAM_METHOD_DIRECT_API
            self._supports_bidirectional = False
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch - trigger Telegram API test."""
        from homeassistant.util import dt as dt_util
        from telegram import Bot
        from telegram.error import TelegramError
        
        _LOGGER.info("Telegram API test triggered")
        self._attr_is_on = True
        self.async_write_ha_state()
        
        # Update method info
        self._update_method_info()
        self._last_test_timestamp = dt_util.now().isoformat()
        
        # Get configuration
        telegram_token = self._config_entry.data.get(CONF_TELEGRAM_TOKEN)
        telegram_chat_id = self._config_entry.data.get(CONF_TELEGRAM_CHAT_ID)
        
        if not telegram_token or not telegram_chat_id:
            _LOGGER.error("Telegram not configured")
            self._last_send_result = "error_not_configured"
            self._attr_is_on = False
            self.async_write_ha_state()
            return
        
        # Test sending message
        try:
            test_message = (
                "🧪 <b>Telegram API Test</b>\n\n"
                f"Method: <code>{self._method_used}</code>\n"
                f"Timestamp: {self._last_test_timestamp}\n\n"
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
            # This is simplified for now - actual implementation would require
            # listening for telegram_text events if using integration
            if self._supports_bidirectional:
                # Note: Actual receive test would require event listener setup
                # For now, we just indicate it's supported
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
        
        # Auto turn off after test
        self._attr_is_on = False
        self.async_write_ha_state()
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch - does nothing as it auto-turns off."""
        self._attr_is_on = False
        self.async_write_ha_state()
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes about the test results."""
        attrs = {
            "method_used": self._method_used or "not_determined",
            "supports_bidirectional": self._supports_bidirectional,
        }
        
        if self._last_test_timestamp:
            attrs["last_test_timestamp"] = self._last_test_timestamp
        
        if self._last_send_result:
            attrs["last_send_result"] = self._last_send_result
        
        if self._last_receive_result:
            attrs["last_receive_result"] = self._last_receive_result
        
        if self._last_received_message:
            attrs["last_received_message"] = self._last_received_message
        
        return attrs

