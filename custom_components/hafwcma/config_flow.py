"""Config flow for haFWCMA integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry as er, selector
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_FUEL_TYPE,
    CONF_ODOMETER_ENTITY,
    CONF_POSITION_ENTITY,
    CONF_RADIUS,
    CONF_RANGE_ENTITY,
    CONF_TANK_CAPACITY,
    CONF_TANK_LEVEL_ENTITY,
    CONF_TELEGRAM_CHAT_ID,
    CONF_TELEGRAM_TOKEN,
    CONF_VEHICLE_NAME,
    DEFAULT_RADIUS,
    DEFAULT_TANK_CAPACITY,
    DOMAIN,
    FUEL_TYPES,
)

_LOGGER = logging.getLogger(__name__)


async def async_validate_entity(hass: HomeAssistant, entity_id: str) -> bool:
    """Validate that an entity exists in Home Assistant.
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to validate
        
    Returns:
        True if entity exists, False otherwise
    """
    if not entity_id:
        return True  # Empty is valid (optional field)
    
    entity_registry = er.async_get(hass)
    
    # Check if entity is in registry
    entity_entry = entity_registry.async_get(entity_id)
    if entity_entry:
        return True
    
    # Check if entity exists in current states
    state = hass.states.get(entity_id)
    if state:
        return True
        
    return False


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
            return await self.async_step_vehicle_entities()

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

    async def async_step_vehicle_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle vehicle entities configuration step.
        
        Args:
            user_input: User provided entity IDs
            
        Returns:
            Form to display or next step
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate entities
            entity_ids = {
                CONF_ODOMETER_ENTITY: user_input.get(CONF_ODOMETER_ENTITY, ""),
                CONF_TANK_LEVEL_ENTITY: user_input.get(CONF_TANK_LEVEL_ENTITY, ""),
                CONF_RANGE_ENTITY: user_input.get(CONF_RANGE_ENTITY, ""),
                CONF_POSITION_ENTITY: user_input.get(CONF_POSITION_ENTITY, ""),
            }
            
            # Validate each entity if provided
            for key, entity_id in entity_ids.items():
                if entity_id and not await async_validate_entity(self.hass, entity_id):
                    errors[key] = "invalid_entity"
                    
            # Validate position entity is a device_tracker
            position_entity = entity_ids.get(CONF_POSITION_ENTITY, "")
            if position_entity and not position_entity.startswith("device_tracker."):
                errors[CONF_POSITION_ENTITY] = "not_device_tracker"
            
            if not errors:
                self.data.update(user_input)
                return await self.async_step_telegram()

        # Use entity selector for easy selection
        data_schema = vol.Schema(
            {
                vol.Optional(CONF_ODOMETER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"],
                        multiple=False,
                    )
                ),
                vol.Optional(CONF_TANK_LEVEL_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"],
                        multiple=False,
                    )
                ),
                vol.Optional(CONF_RANGE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"],
                        multiple=False,
                    )
                ),
                vol.Optional(CONF_POSITION_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["device_tracker"],
                        multiple=False,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="vehicle_entities",
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
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # Validate entities if changed
            entity_ids = {
                CONF_ODOMETER_ENTITY: user_input.get(CONF_ODOMETER_ENTITY, ""),
                CONF_TANK_LEVEL_ENTITY: user_input.get(CONF_TANK_LEVEL_ENTITY, ""),
                CONF_RANGE_ENTITY: user_input.get(CONF_RANGE_ENTITY, ""),
                CONF_POSITION_ENTITY: user_input.get(CONF_POSITION_ENTITY, ""),
            }
            
            # Validate each entity if provided
            for key, entity_id in entity_ids.items():
                if entity_id and not await async_validate_entity(self.hass, entity_id):
                    errors[key] = "invalid_entity"
                    
            # Validate position entity is a device_tracker
            position_entity = entity_ids.get(CONF_POSITION_ENTITY, "")
            if position_entity and not position_entity.startswith("device_tracker."):
                errors[CONF_POSITION_ENTITY] = "not_device_tracker"
            
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        current_config = self.config_entry.data
        current_options = self.config_entry.options

        # Get current values with proper fallbacks for empty/invalid values
        # Use explicit None checks to allow 0 values but reject None/empty strings
        radius_value = current_options.get(CONF_RADIUS)
        if radius_value is None or radius_value == "":
            radius_value = current_config.get(CONF_RADIUS)
        if radius_value is None or radius_value == "":
            radius_value = DEFAULT_RADIUS
            
        fuel_type_value = current_options.get(CONF_FUEL_TYPE)
        if not fuel_type_value:
            fuel_type_value = current_config.get(CONF_FUEL_TYPE)
        if not fuel_type_value:
            fuel_type_value = FUEL_TYPES[0]
        # Ensure fuel type is valid
        if fuel_type_value not in FUEL_TYPES:
            fuel_type_value = FUEL_TYPES[0]
            
        tank_capacity_value = current_options.get(CONF_TANK_CAPACITY)
        if tank_capacity_value is None or tank_capacity_value == "":
            tank_capacity_value = current_config.get(CONF_TANK_CAPACITY)
        if tank_capacity_value is None or tank_capacity_value == "":
            tank_capacity_value = DEFAULT_TANK_CAPACITY
            
        telegram_token_value = current_options.get(CONF_TELEGRAM_TOKEN, "")
        if not telegram_token_value:
            telegram_token_value = current_config.get(CONF_TELEGRAM_TOKEN, "")
            
        telegram_chat_id_value = current_options.get(CONF_TELEGRAM_CHAT_ID, "")
        if not telegram_chat_id_value:
            telegram_chat_id_value = current_config.get(CONF_TELEGRAM_CHAT_ID, "")
            
        # Get vehicle entity values
        odometer_value = current_options.get(CONF_ODOMETER_ENTITY, "")
        if not odometer_value:
            odometer_value = current_config.get(CONF_ODOMETER_ENTITY, "")
            
        tank_level_value = current_options.get(CONF_TANK_LEVEL_ENTITY, "")
        if not tank_level_value:
            tank_level_value = current_config.get(CONF_TANK_LEVEL_ENTITY, "")
            
        range_value = current_options.get(CONF_RANGE_ENTITY, "")
        if not range_value:
            range_value = current_config.get(CONF_RANGE_ENTITY, "")
            
        position_value = current_options.get(CONF_POSITION_ENTITY, "")
        if not position_value:
            position_value = current_config.get(CONF_POSITION_ENTITY, "")

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_RADIUS,
                    default=radius_value,
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_FUEL_TYPE,
                    default=fuel_type_value,
                ): vol.In(FUEL_TYPES),
                vol.Optional(
                    CONF_TANK_CAPACITY,
                    default=tank_capacity_value,
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_TELEGRAM_TOKEN,
                    default=telegram_token_value,
                ): str,
                vol.Optional(
                    CONF_TELEGRAM_CHAT_ID,
                    default=telegram_chat_id_value,
                ): str,
                vol.Optional(
                    CONF_ODOMETER_ENTITY,
                    description={"suggested_value": odometer_value},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"],
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_TANK_LEVEL_ENTITY,
                    description={"suggested_value": tank_level_value},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"],
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_RANGE_ENTITY,
                    description={"suggested_value": range_value},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"],
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_POSITION_ENTITY,
                    description={"suggested_value": position_value},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["device_tracker"],
                        multiple=False,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)
