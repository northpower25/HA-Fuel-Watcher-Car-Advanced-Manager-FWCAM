"""Config flow for haFWCMA integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_FUEL_TYPE,
    CONF_RADIUS,
    CONF_TANK_CAPACITY,
    CONF_TELEGRAM_CHAT_ID,
    CONF_TELEGRAM_TOKEN,
    CONF_VEHICLE_NAME,
    DEFAULT_RADIUS,
    DEFAULT_TANK_CAPACITY,
    DOMAIN,
    FUEL_TYPES,
)

_LOGGER = logging.getLogger(__name__)


class HaFWCMAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for haFWCMA."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - Tankerkönig API configuration.
        
        Args:
            user_input: User provided configuration data
            
        Returns:
            Form to display or entry creation result
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # TODO: Validate API key with Tankerkönig API
            # For now, just check if it's provided
            if not user_input.get(CONF_API_KEY):
                errors["base"] = "invalid_api_key"
            else:
                # Store data and move to vehicle setup
                self.data = user_input
                return await self.async_step_vehicle()

        # Show form for API configuration
        data_schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Required(
                    CONF_LATITUDE,
                    default=self.hass.config.latitude,
                ): cv.latitude,
                vol.Required(
                    CONF_LONGITUDE,
                    default=self.hass.config.longitude,
                ): cv.longitude,
                vol.Optional(CONF_RADIUS, default=DEFAULT_RADIUS): vol.Coerce(float),
                vol.Required(CONF_FUEL_TYPE, default=FUEL_TYPES[0]): vol.In(
                    FUEL_TYPES
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "api_info": "Get your API key from https://creativecommons.tankerkoenig.de"
            },
        )

    async def async_step_vehicle(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle vehicle configuration step.
        
        Args:
            user_input: User provided vehicle data
            
        Returns:
            Form to display or next step
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_telegram()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_VEHICLE_NAME, default="My Car"): str,
                vol.Required(CONF_TANK_CAPACITY, default=DEFAULT_TANK_CAPACITY): vol.Coerce(float),
            }
        )

        return self.async_show_form(
            step_id="vehicle",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_telegram(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle Telegram notification configuration (optional).
        
        Args:
            user_input: User provided Telegram configuration
            
        Returns:
            Form to display or entry creation
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Merge all data
            self.data.update(user_input)
            
            # Create the config entry
            return self.async_create_entry(
                title=f"haFWCMA - {self.data.get(CONF_VEHICLE_NAME, 'Vehicle')}",
                data=self.data,
            )

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_TELEGRAM_TOKEN): str,
                vol.Optional(CONF_TELEGRAM_CHAT_ID): str,
            }
        )

        return self.async_show_form(
            step_id="telegram",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "telegram_info": "Optional: Configure Telegram for notifications"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HaFWCMAOptionsFlow:
        """Get the options flow for this handler.
        
        Args:
            config_entry: The config entry to create options flow for
            
        Returns:
            Options flow handler
        """
        return HaFWCMAOptionsFlow(config_entry)


class HaFWCMAOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for haFWCMA integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow.
        
        Args:
            config_entry: The config entry to manage options for
        """
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options.
        
        Args:
            user_input: User provided option changes
            
        Returns:
            Form to display or options update
        """
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_config = self.config_entry.data
        current_options = self.config_entry.options

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_RADIUS,
                    default=current_options.get(
                        CONF_RADIUS, current_config.get(CONF_RADIUS, DEFAULT_RADIUS)
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_FUEL_TYPE,
                    default=current_options.get(
                        CONF_FUEL_TYPE, current_config.get(CONF_FUEL_TYPE, FUEL_TYPES[0])
                    ),
                ): vol.In(FUEL_TYPES),
                vol.Optional(
                    CONF_TANK_CAPACITY,
                    default=current_options.get(
                        CONF_TANK_CAPACITY,
                        current_config.get(CONF_TANK_CAPACITY, DEFAULT_TANK_CAPACITY),
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_TELEGRAM_TOKEN,
                    default=current_options.get(
                        CONF_TELEGRAM_TOKEN, current_config.get(CONF_TELEGRAM_TOKEN, "")
                    ),
                ): str,
                vol.Optional(
                    CONF_TELEGRAM_CHAT_ID,
                    default=current_options.get(
                        CONF_TELEGRAM_CHAT_ID, current_config.get(CONF_TELEGRAM_CHAT_ID, "")
                    ),
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
