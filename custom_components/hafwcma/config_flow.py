"""Config flow for haFWCMA integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from telegram import Bot
from telegram.error import TelegramError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import AbortFlow, FlowResult
from homeassistant.helpers import entity_registry as er, selector
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_CHEAP_STATIONS_RADIUS,
    CONF_CRITICAL_FUEL_THRESHOLD,
    CONF_FALLBACK_DAILY_KM,
    CONF_FALLBACK_DAILY_KM_MONDAY,
    CONF_FALLBACK_DAILY_KM_TUESDAY,
    CONF_FALLBACK_DAILY_KM_WEDNESDAY,
    CONF_FALLBACK_DAILY_KM_THURSDAY,
    CONF_FALLBACK_DAILY_KM_FRIDAY,
    CONF_FALLBACK_DAILY_KM_SATURDAY,
    CONF_FALLBACK_DAILY_KM_SUNDAY,
    CONF_FUEL_TYPE,
    CONF_IMPORT_HISTORICAL_DATA,
    CONF_INITIAL_CONSUMPTION,
    CONF_LOW_FUEL_THRESHOLD,
    CONF_ODOMETER_ENTITY,
    CONF_POSITION_ENTITY,
    CONF_PRICE_DROP_ABSOLUTE_THRESHOLD,
    CONF_PRICE_DROP_PERCENT_THRESHOLD,
    CONF_PROVIDER,
    CONF_PROXIMITY_ALERTS_ENABLED,
    CONF_RANGE_ENTITY,
    CONF_TANK_CAPACITY,
    CONF_TANK_LEVEL_ENTITY,
    CONF_TELEGRAM_CHAT_ID,
    CONF_TELEGRAM_METHOD,
    CONF_TELEGRAM_TOKEN,
    CONF_TRIP_TRACKING_INITIAL_ENABLED,
    CONF_UPDATE_INTERVAL,
    CONF_VEHICLE_NAME,
    DEFAULT_CHEAP_STATIONS_RADIUS,
    DEFAULT_CRITICAL_FUEL_THRESHOLD,
    DEFAULT_FALLBACK_DAILY_KM,
    DEFAULT_LOW_FUEL_THRESHOLD,
    DEFAULT_PRICE_DROP_ABSOLUTE,
    DEFAULT_PRICE_DROP_PERCENT,
    DEFAULT_PROXIMITY_ALERTS_ENABLED,
    DEFAULT_TANK_CAPACITY,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    FUEL_TYPES,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    PROVIDER_NAMES,
    PROVIDER_TANKERKONIG,
    PROVIDERS,
    TELEGRAM_METHOD_DIRECT_API,
    TELEGRAM_METHOD_INTEGRATION,
)

_LOGGER = logging.getLogger(__name__)

# Timeout for API validation tests (in seconds)
API_TEST_TIMEOUT = 10



async def async_test_fuel_api(
    hass: HomeAssistant,
    provider: str,
    api_key: str,
    latitude: float,
    longitude: float,
    radius: float,
    fuel_type: str,
) -> list[dict[str, Any]]:
    """Test fuel price API connection and return station data.
    
    Args:
        hass: Home Assistant instance
        provider: Provider name (e.g., 'tankerkonig')
        api_key: API key for the provider
        latitude: Latitude for search
        longitude: Longitude for search
        radius: Search radius in km
        fuel_type: Type of fuel to search for
        
    Returns:
        List of station dictionaries with name, address, and prices
        
    Raises:
        Exception: If API test fails
    """
    from .providers.tankerkonig import TankerkoenigProvider
    from .providers import ProviderError
    
    # Create a temporary session for testing
    async with aiohttp.ClientSession() as session:
        # Currently only supports TankerKönig
        if provider == PROVIDER_TANKERKONIG:
            provider_instance = TankerkoenigProvider(api_key, session)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        try:
            # Get stations from API with timeout
            stations = await asyncio.wait_for(
                provider_instance.get_stations_nearby(
                    latitude=latitude,
                    longitude=longitude,
                    radius=radius,
                    fuel_type=fuel_type,
                ),
                timeout=API_TEST_TIMEOUT,
            )
            
            # Format station data for display (limit to top 5 stations)
            station_list = []
            for station in stations[:5]:
                station_dict = {
                    "name": station.name,
                    "brand": station.brand,
                    "address": station.address,
                    "distance": round(station.distance, 2),
                }
                
                # Add prices if available
                if station.price_e5 is not None:
                    station_dict["price_e5"] = round(station.price_e5, 3)
                if station.price_e10 is not None:
                    station_dict["price_e10"] = round(station.price_e10, 3)
                if station.price_diesel is not None:
                    station_dict["price_diesel"] = round(station.price_diesel, 3)
                    
                station_list.append(station_dict)
            
            _LOGGER.info("API test successful: Found %d stations", len(stations))
            return station_list
            
        except asyncio.TimeoutError as err:
            _LOGGER.error("API test timed out after %d seconds", API_TEST_TIMEOUT)
            raise Exception(f"API request timed out after {API_TEST_TIMEOUT} seconds") from err
        except ProviderError as err:
            _LOGGER.error("API test failed: %s", err)
            raise Exception(f"API Error: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error during API test: %s", err)
            raise


async def async_send_telegram_test_message(
    bot_token: str,
    chat_id: str,
) -> bool:
    """Send a test message via Telegram.
    
    This is a simple send-only test to verify the bot token and chat ID are valid.
    For bidirectional communication, users should configure Home Assistant's 
    telegram_bot integration separately.
    
    Args:
        bot_token: Telegram bot token
        chat_id: Chat ID to send message to
        
    Returns:
        True if message was sent successfully
        
    Raises:
        Exception: If sending fails
    """
    try:
        bot = Bot(token=bot_token)
        
        message_text = (
            "🚗 <b>FWCMA Test Message</b>\n\n"
            "✅ Success! Your Telegram configuration is working.\n\n"
            "haFWCMA can now send you notifications about:\n"
            "• Fuel price alerts\n"
            "• Refueling recommendations\n"
            "• Low tank warnings\n\n"
            "<i>Note: For bidirectional features (e.g., logging refueling via Telegram), "
            "please configure Home Assistant's telegram_bot integration.</i>"
        )
        
        await bot.send_message(
            chat_id=chat_id,
            text=message_text,
            parse_mode="HTML",
        )
        
        _LOGGER.info("Telegram test message sent successfully")
        return True
        
    except TelegramError as err:
        _LOGGER.error("Failed to send Telegram test message: %s", err)
        raise Exception(f"Telegram Error: {err}") from err
    except Exception as err:
        _LOGGER.error("Unexpected error sending Telegram message: %s", err)
        raise


def format_station_list_for_display(stations: list[dict[str, Any]]) -> str:
    """Format station list for display in config flow.
    
    Args:
        stations: List of station dictionaries
        
    Returns:
        Formatted string for display
    """
    if not stations:
        return "No stations found in the specified radius."
    
    lines = [f"✅ Found {len(stations)} station(s):\n"]
    
    for i, station in enumerate(stations, 1):
        lines.append(f"\n{i}. **{station['name']}** ({station['brand']})")
        lines.append(f"   📍 {station['address']}")
        lines.append(f"   📏 Distance: {station['distance']} km")
        
        # Add prices
        prices = []
        if "price_e5" in station:
            prices.append(f"E5: €{station['price_e5']:.3f}")
        if "price_e10" in station:
            prices.append(f"E10: €{station['price_e10']:.3f}")
        if "price_diesel" in station:
            prices.append(f"Diesel: €{station['price_diesel']:.3f}")
        
        if prices:
            lines.append(f"   💰 Prices: {' | '.join(prices)}")
    
    return "\n".join(lines)


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

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data: dict[str, Any] = {}
        self._import_task: asyncio.Task | None = None
        self._preflight_result: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - Provider and API configuration.
        
        Args:
            user_input: User provided configuration data
            
        Returns:
            Form to display or entry creation result
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if API key is provided
            if not user_input.get(CONF_API_KEY):
                errors["base"] = "invalid_api_key"
            else:
                # Store data and move to API validation
                self.data = user_input
                return await self.async_step_validate_api()

        # Show form for provider and API configuration
        data_schema = vol.Schema(
            {
                vol.Required(CONF_PROVIDER, default=PROVIDER_TANKERKONIG): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=provider, label=PROVIDER_NAMES[provider])
                            for provider in PROVIDERS
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_API_KEY): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD,
                    )
                ),
                vol.Optional(CONF_CHEAP_STATIONS_RADIUS, default=DEFAULT_CHEAP_STATIONS_RADIUS): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0,
                        max=50.0,
                        step=0.5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Required(CONF_FUEL_TYPE, default=FUEL_TYPES[0]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=FUEL_TYPES,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=DEFAULT_UPDATE_INTERVAL,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_UPDATE_INTERVAL,
                        max=MAX_UPDATE_INTERVAL,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="min",
                    )
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

    async def async_step_validate_api(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate fuel price API configuration.
        
        This step tests the API connection with the provided credentials
        and displays a list of found stations or an error message.
        
        Args:
            user_input: User action (continue or back)
            
        Returns:
            Form showing test results or next step
        """
        errors: dict[str, str] = {}
        
        # If no user input, this is the first time showing this step
        # We need to test the API
        if user_input is None:
            _LOGGER.debug("Testing API connection...")
            
            try:
                # Test API with home coordinates
                stations = await async_test_fuel_api(
                    hass=self.hass,
                    provider=self.data[CONF_PROVIDER],
                    api_key=self.data[CONF_API_KEY],
                    latitude=self.hass.config.latitude,
                    longitude=self.hass.config.longitude,
                    radius=self.data[CONF_CHEAP_STATIONS_RADIUS],
                    fuel_type=self.data[CONF_FUEL_TYPE],
                )
                
                # Format station list for display
                station_display = format_station_list_for_display(stations)
                
                # Show success with station list
                return self.async_show_form(
                    step_id="validate_api",
                    data_schema=vol.Schema({}),
                    description_placeholders={
                        "stations": station_display,
                        "error_details": "",  # Empty for success case
                    },
                )
                
            except Exception as err:
                # Show error message
                error_msg = str(err)
                _LOGGER.error("API validation failed: %s", error_msg)
                errors["base"] = "api_test_failed"
                
                # Store error in data for display
                self.data["_api_error"] = error_msg
                
                return self.async_show_form(
                    step_id="validate_api",
                    data_schema=vol.Schema({}),
                    errors=errors,
                    description_placeholders={
                        "stations": "",  # Empty for error case
                        "error_details": error_msg,
                    },
                )
        
        # User has clicked a button after seeing results
        # Check if there was an API error
        if "_api_error" in self.data:
            # Remove the temporary error flag
            del self.data["_api_error"]
            # Go back to API configuration with current data prepopulated
            return await self.async_step_user(self.data)
        
        # Success - continue to vehicle setup
        return await self.async_step_vehicle()

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
                vol.Required(CONF_TANK_CAPACITY): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10.0,
                        max=200.0,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="L",
                    )
                ),
                vol.Required(CONF_INITIAL_CONSUMPTION): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0,
                        max=50.0,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="L/100km",
                    )
                ),
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
            try:
                for key, entity_id in entity_ids.items():
                    if entity_id and not await async_validate_entity(self.hass, entity_id):
                        errors[key] = "invalid_entity"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Error validating entities")
                errors["base"] = "entity_validation_failed"
                    
            # Validate position entity is a device_tracker
            position_entity = entity_ids.get(CONF_POSITION_ENTITY, "")
            if position_entity and not position_entity.startswith("device_tracker."):
                errors[CONF_POSITION_ENTITY] = "not_device_tracker"
            
            if not errors:
                self.data.update(user_input)
                return await self.async_step_vehicle_features()

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

    async def async_step_vehicle_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle vehicle features configuration step.

        Asks the user whether to enable proximity alerts and trip tracking.

        Args:
            user_input: User provided feature toggles

        Returns:
            Form to display or next step
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_telegram()

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_PROXIMITY_ALERTS_ENABLED,
                    default=DEFAULT_PROXIMITY_ALERTS_ENABLED,
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_TRIP_TRACKING_INITIAL_ENABLED,
                    default=False,
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="vehicle_features",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_historical_import(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle historical data import configuration step.

        Asks the user whether to import historical vehicle data from HA's recorder.

        Args:
            user_input: User provided import preference

        Returns:
            Form to display or next step (progress or entry creation)
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            self.data.update(user_input)

            # Automatically add latitude and longitude from Home Assistant configuration
            self.data[CONF_LATITUDE] = self.hass.config.latitude
            self.data[CONF_LONGITUDE] = self.hass.config.longitude

            # Create the entry directly – the actual import runs in the background
            # after HA has fully started (_import_historical_data_background) and
            # the result is reported via a persistent notification.
            return self.async_create_entry(
                title=f"haFWCMA - {self.data.get(CONF_VEHICLE_NAME, 'Vehicle')}",
                data=self.data,
            )

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_IMPORT_HISTORICAL_DATA,
                    default=True,
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="historical_import",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_import_progress(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show a progress indicator while checking recorder availability.

        Runs a quick preflight query against HA's recorder to determine how
        much historical data is available for the configured vehicle entities.
        This gives the user visible feedback before the setup flow completes.
        The heavyweight import itself still runs in the background after startup.

        Args:
            user_input: Unused – called automatically by HA when the task finishes

        Returns:
            Progress form while the task is running, or entry creation when done
        """
        if self._import_task is None:
            self._import_task = self.hass.async_create_task(
                self._run_import_preflight()
            )

        if not self._import_task.done():
            return self.async_show_progress(
                step_id="import_progress",
                progress_action="importing",
                progress_task=self._import_task,
            )

        # Task completed – clean up and proceed to finish setup
        self._import_task = None
        return self.async_show_progress_done(next_step_id="finish_setup")

    async def async_step_finish_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Final step: show import summary and create the config entry.

        Args:
            user_input: Submitted by the user to confirm and finish

        Returns:
            Entry creation result or summary form
        """
        if user_input is not None:
            return self.async_create_entry(
                title=f"haFWCMA - {self.data.get(CONF_VEHICLE_NAME, 'Vehicle')}",
                data=self.data,
            )

        result = self._preflight_result
        odometer_pts = result.get("odometer_points", 0)
        tank_pts = result.get("tank_points", 0)
        date_range = result.get("date_range", "")
        recorder_ok = result.get("recorder_available", False)
        preflight_error = result.get("preflight_error", "")
        is_german = getattr(self.hass.config, "language", "en").startswith("de")

        summary = self._build_import_summary(
            is_german=is_german,
            recorder_ok=recorder_ok,
            odometer_pts=odometer_pts,
            tank_pts=tank_pts,
            date_range=date_range,
            preflight_error=preflight_error,
        )

        return self.async_show_form(
            step_id="finish_setup",
            data_schema=vol.Schema({}),
            description_placeholders={"import_summary": summary},
        )

    async def _run_import_preflight(self) -> None:
        """Query the recorder to estimate how much historical data is available.

        Stores the result in ``self._preflight_result`` so that
        ``async_step_finish_setup`` can display a meaningful summary.
        Each recorder query has a 25-second timeout to prevent the
        import_progress spinner from hanging indefinitely when the
        recorder is slow or busy.  A ``finally`` block guarantees that
        ``_preflight_result`` is always set, even on task cancellation.
        """
        result: dict[str, Any] = {
            "recorder_available": False,
            "odometer_points": 0,
            "tank_points": 0,
            "date_range": "",
        }

        odometer_entity = self.data.get(CONF_ODOMETER_ENTITY, "")
        tank_entity = self.data.get(CONF_TANK_LEVEL_ENTITY, "")

        try:
            from homeassistant.components.recorder import get_instance, history
            from homeassistant.util import dt as dt_util
            from datetime import timedelta

            recorder_instance = get_instance(self.hass)
            if not recorder_instance:
                return  # finally block ensures _preflight_result is set
            result["recorder_available"] = True

            end_time = dt_util.now()
            start_time = end_time - timedelta(days=90)

            if odometer_entity:
                try:
                    odo_states = await asyncio.wait_for(
                        recorder_instance.async_add_executor_job(
                            history.get_significant_states,
                            self.hass,
                            start_time,
                            end_time,
                            [odometer_entity],
                        ),
                        timeout=25.0,
                    )
                    result["odometer_points"] = len(
                        odo_states.get(odometer_entity, [])
                    )
                except asyncio.TimeoutError:
                    _LOGGER.warning(
                        "Import preflight: odometer query timed out for %s",
                        odometer_entity,
                    )
                    result["preflight_error"] = "Odometer recorder query timed out"

            if tank_entity:
                try:
                    tank_states = await asyncio.wait_for(
                        recorder_instance.async_add_executor_job(
                            history.get_significant_states,
                            self.hass,
                            start_time,
                            end_time,
                            [tank_entity],
                        ),
                        timeout=25.0,
                    )
                    result["tank_points"] = len(
                        tank_states.get(tank_entity, [])
                    )
                except asyncio.TimeoutError:
                    _LOGGER.warning(
                        "Import preflight: tank level query timed out for %s",
                        tank_entity,
                    )
                    if not result.get("preflight_error"):
                        result["preflight_error"] = "Tank level recorder query timed out"

            if result["odometer_points"] > 0 or result["tank_points"] > 0:
                result["date_range"] = (
                    f"{start_time.strftime('%Y-%m-%d')} – {end_time.strftime('%Y-%m-%d')}"
                )

        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Import preflight check failed: %s", err)
            result["preflight_error"] = str(err)
        finally:
            # Ensure _preflight_result is always set, even if the task is cancelled
            # (CancelledError is BaseException in Python 3.8+ and bypasses except Exception)
            self._preflight_result = result

    @staticmethod
    def _build_import_summary(
        is_german: bool,
        recorder_ok: bool,
        odometer_pts: int,
        tank_pts: int,
        date_range: str,
        preflight_error: str,
    ) -> str:
        """Build a localised import summary string for the finish_setup step."""
        if recorder_ok and odometer_pts > 0:
            if is_german:
                summary = (
                    f"✅ **Recorder-Daten gefunden!**\n\n"
                    f"• Kilometerzähler Datenpunkte: **{odometer_pts}**\n"
                    f"• Tankfüllstand Datenpunkte: **{tank_pts}**\n"
                )
                if date_range:
                    summary += f"• Zeitraum: {date_range}\n"
                summary += (
                    "\n📥 Historische Daten werden automatisch importiert, sobald Home Assistant "
                    "vollständig gestartet ist. Die Ergebnisse erscheinen als Home Assistant Benachrichtigung."
                )
            else:
                summary = (
                    f"✅ **Recorder data found!**\n\n"
                    f"• Odometer data points: **{odometer_pts}**\n"
                    f"• Tank level data points: **{tank_pts}**\n"
                )
                if date_range:
                    summary += f"• Date range: {date_range}\n"
                summary += (
                    "\n📥 Historical data will be imported automatically once Home Assistant "
                    "has fully started. Results will appear as a notification."
                )
        elif recorder_ok:
            summary = (
                "ℹ️ Recorder ist verfügbar, aber für die konfigurierten Fahrzeugentitäten "
                "wurden keine historischen Daten gefunden.\n\n"
                "Daten werden automatisch gesammelt, sobald Sie fahren."
                if is_german else
                "ℹ️ Recorder is available but no historical data was found for the "
                "configured vehicle entities.\n\n"
                "Data will accumulate automatically as you drive."
            )
        elif preflight_error:
            summary = (
                f"⚠️ Recorder konnte nicht abgefragt werden: {preflight_error}\n\n"
                "Historischer Import wird übersprungen. Daten werden automatisch gesammelt."
                if is_german else
                f"⚠️ Could not query the recorder: {preflight_error}\n\n"
                "Historical import will be skipped. Data will accumulate automatically."
            )
        else:
            summary = (
                "⚠️ Home Assistant Recorder ist nicht verfügbar oder konnte nicht abgefragt werden.\n\n"
                "Historischer Import wird übersprungen. Daten werden automatisch gesammelt."
                if is_german else
                "⚠️ Home Assistant recorder is not available or could not be queried.\n\n"
                "Historical import will be skipped. Data will accumulate automatically."
            )
        return summary

    async def async_step_telegram(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle Telegram notification configuration (optional).
        
        Detects if telegram_bot integration is available and provides appropriate options.
        
        Args:
            user_input: User provided Telegram configuration
            
        Returns:
            Form to display or next step
        """
        errors: dict[str, str] = {}
        
        # Check if telegram_bot integration is loaded
        telegram_bot_available = "telegram_bot" in self.hass.config.components

        if user_input is not None:
            # Merge all data
            self.data.update(user_input)
            
            # Store the method being used
            if telegram_bot_available:
                self.data[CONF_TELEGRAM_METHOD] = TELEGRAM_METHOD_INTEGRATION
            else:
                self.data[CONF_TELEGRAM_METHOD] = TELEGRAM_METHOD_DIRECT_API
            
            # If both Telegram token and chat ID are provided, validate them
            telegram_token = user_input.get(CONF_TELEGRAM_TOKEN, "")
            telegram_chat_id = user_input.get(CONF_TELEGRAM_CHAT_ID, "")
            
            if telegram_token and telegram_chat_id:
                # Move to Telegram validation
                return await self.async_step_validate_telegram()
            else:
                # Skip validation if Telegram is not configured
                # Move to prediction engine configuration
                return await self.async_step_prediction()

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_TELEGRAM_TOKEN): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD,
                    )
                ),
                vol.Optional(CONF_TELEGRAM_CHAT_ID): str,
            }
        )
        
        # Common setup instructions
        common_instructions = (
            "Optional: Configure Telegram for notifications\n\n"
            "To get your Telegram Bot Token:\n"
            "1. Open Telegram and search for @BotFather\n"
            "2. Send /newbot and follow instructions\n"
            "3. Copy the token provided\n\n"
            "To get your Chat ID:\n"
            "1. Search for @userinfobot in Telegram\n"
            "2. Start a chat and it will show your Chat ID\n\n"
        )
        
        # Build description based on whether telegram_bot is available
        if telegram_bot_available:
            telegram_info = (
                "✅ <b>Telegram Bot Integration Detected</b>\n\n"
                "The Home Assistant telegram_bot integration is available. "
                "This enables bidirectional communication (sending and receiving messages).\n\n"
                + common_instructions +
                "<i>💡 Tip: Use the same bot token in the telegram_bot integration for full features.</i>"
            )
        else:
            telegram_info = (
                "ℹ️ <b>Telegram Bot Integration Not Found</b>\n\n"
                "The telegram_bot integration is not configured. "
                "Only one-way notifications (sending messages) will be available.\n\n"
                + common_instructions +
                "<i>💡 Tip: Configure the telegram_bot integration for bidirectional features.</i>"
            )

        return self.async_show_form(
            step_id="telegram",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "telegram_info": telegram_info
            },
        )
    
    async def async_step_validate_telegram(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate Telegram API configuration with test message.
        
        This step:
        1. Sends a test message to the user
        2. Reports which method is being used (integration vs direct API)
        3. Displays success or error
        4. Allows continuation to next step
        
        Args:
            user_input: User action (continue, skip, or back)
            
        Returns:
            Form showing test results or next step
        """
        errors: dict[str, str] = {}
        
        # If no user input, this is the first time showing this step
        # Send the test message to verify configuration
        if user_input is None:
            _LOGGER.debug("Testing Telegram connection...")
            
            # Determine method being used
            telegram_bot_available = "telegram_bot" in self.hass.config.components
            method_used = TELEGRAM_METHOD_INTEGRATION if telegram_bot_available else TELEGRAM_METHOD_DIRECT_API
            
            try:
                # Send test message (no polling to avoid conflicts)
                await async_send_telegram_test_message(
                    bot_token=self.data[CONF_TELEGRAM_TOKEN],
                    chat_id=self.data[CONF_TELEGRAM_CHAT_ID],
                )
                
                # Build success message based on method
                if method_used == TELEGRAM_METHOD_INTEGRATION:
                    success_msg = (
                        "✅ Test message sent successfully!\n\n"
                        "Your Telegram configuration is working.\n\n"
                        "🔄 <b>Method:</b> Using Home Assistant's telegram_bot integration\n"
                        "✨ <b>Features:</b> Bidirectional communication is available!\n\n"
                        "<i>You can send commands to the bot and receive responses.</i>"
                    )
                else:
                    success_msg = (
                        "✅ Test message sent successfully!\n\n"
                        "Your Telegram configuration is working.\n\n"
                        "📤 <b>Method:</b> Using Direct Bot API\n"
                        "📝 <b>Features:</b> One-way notifications only\n\n"
                        "ℹ️ <b>For bidirectional communication:</b>\n"
                        "To enable advanced features like logging refueling via Telegram commands, "
                        "please configure Home Assistant's <i>telegram_bot</i> integration with the same bot token."
                    )
                
                # Success - show confirmation
                return self.async_show_form(
                    step_id="validate_telegram",
                    data_schema=vol.Schema({}),
                    description_placeholders={
                        "message": success_msg,
                        "error_details": "",
                        "waiting": "",
                    },
                )
                
            except Exception as err:
                # Show error message
                error_msg = str(err)
                _LOGGER.error("Telegram validation failed: %s", error_msg)
                errors["base"] = "telegram_test_failed"
                
                # Store error in data for display
                self.data["_telegram_error"] = error_msg
                
                return self.async_show_form(
                    step_id="validate_telegram",
                    data_schema=vol.Schema({}),
                    errors=errors,
                    description_placeholders={
                        "message": "",
                        "error_details": error_msg,
                        "waiting": "",
                    },
                )
        
        # User has clicked a button after seeing results
        # Check if there was a Telegram error
        if "_telegram_error" in self.data:
            # Remove the temporary error flag
            del self.data["_telegram_error"]
            # Go back to Telegram configuration with current data prepopulated
            return await self.async_step_telegram(self.data)
        
        # Success - continue to prediction setup
        return await self.async_step_prediction()
    
    async def async_step_prediction(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle prediction engine configuration (optional).
        
        Args:
            user_input: User provided prediction configuration
            
        Returns:
            Form to display or entry creation
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Merge all data
            self.data.update(user_input)

            # Continue to historical import configuration
            return await self.async_step_historical_import()

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_PRICE_DROP_PERCENT_THRESHOLD,
                    default=DEFAULT_PRICE_DROP_PERCENT,
                    description={"suggested_value": DEFAULT_PRICE_DROP_PERCENT},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=100.0,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="%",
                    )
                ),
                vol.Optional(
                    CONF_PRICE_DROP_ABSOLUTE_THRESHOLD,
                    default=DEFAULT_PRICE_DROP_ABSOLUTE,
                    description={"suggested_value": DEFAULT_PRICE_DROP_ABSOLUTE},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.01,
                        max=1.0,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="EUR",
                    )
                ),
                vol.Optional(
                    CONF_LOW_FUEL_THRESHOLD,
                    default=DEFAULT_LOW_FUEL_THRESHOLD,
                    description={"suggested_value": DEFAULT_LOW_FUEL_THRESHOLD},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0,
                        max=2000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_CRITICAL_FUEL_THRESHOLD,
                    default=DEFAULT_CRITICAL_FUEL_THRESHOLD,
                    description={"suggested_value": DEFAULT_CRITICAL_FUEL_THRESHOLD},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0,
                        max=500.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_DAILY_KM_MONDAY,
                    default=DEFAULT_FALLBACK_DAILY_KM,
                    description={"suggested_value": DEFAULT_FALLBACK_DAILY_KM},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_DAILY_KM_TUESDAY,
                    default=DEFAULT_FALLBACK_DAILY_KM,
                    description={"suggested_value": DEFAULT_FALLBACK_DAILY_KM},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_DAILY_KM_WEDNESDAY,
                    default=DEFAULT_FALLBACK_DAILY_KM,
                    description={"suggested_value": DEFAULT_FALLBACK_DAILY_KM},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_DAILY_KM_THURSDAY,
                    default=DEFAULT_FALLBACK_DAILY_KM,
                    description={"suggested_value": DEFAULT_FALLBACK_DAILY_KM},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_DAILY_KM_FRIDAY,
                    default=DEFAULT_FALLBACK_DAILY_KM,
                    description={"suggested_value": DEFAULT_FALLBACK_DAILY_KM},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_DAILY_KM_SATURDAY,
                    default=DEFAULT_FALLBACK_DAILY_KM,
                    description={"suggested_value": DEFAULT_FALLBACK_DAILY_KM},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_DAILY_KM_SUNDAY,
                    default=DEFAULT_FALLBACK_DAILY_KM,
                    description={"suggested_value": DEFAULT_FALLBACK_DAILY_KM},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="prediction",
            data_schema=data_schema,
            errors=errors,
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
        return HaFWCMAOptionsFlow()


class HaFWCMAOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for haFWCMA integration."""

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
            try:
                for key, entity_id in entity_ids.items():
                    if entity_id and not await async_validate_entity(self.hass, entity_id):
                        errors[key] = "invalid_entity"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Error validating entities")
                errors["base"] = "entity_validation_failed"
                    
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
        provider_value = current_options.get(CONF_PROVIDER)
        if not provider_value:
            provider_value = current_config.get(CONF_PROVIDER, PROVIDER_TANKERKONIG)
        # Ensure provider is valid
        if provider_value not in PROVIDERS:
            provider_value = PROVIDER_TANKERKONIG
            
        api_key_value = current_options.get(CONF_API_KEY, "")
        if not api_key_value:
            api_key_value = current_config.get(CONF_API_KEY, "")
            
        update_interval_value = current_options.get(CONF_UPDATE_INTERVAL)
        if update_interval_value is None or update_interval_value == "":
            update_interval_value = current_config.get(CONF_UPDATE_INTERVAL)
        if update_interval_value is None or update_interval_value == "":
            update_interval_value = DEFAULT_UPDATE_INTERVAL
            
        # Removed radius_value - now using cheap_stations_radius number entity instead
            
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
        
        initial_consumption_value = current_options.get(CONF_INITIAL_CONSUMPTION)
        if initial_consumption_value is None or initial_consumption_value == "":
            initial_consumption_value = current_config.get(CONF_INITIAL_CONSUMPTION)
            
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
        
        # Get prediction engine values
        price_drop_percent_value = current_options.get(CONF_PRICE_DROP_PERCENT_THRESHOLD)
        if price_drop_percent_value is None or price_drop_percent_value == "":
            price_drop_percent_value = current_config.get(CONF_PRICE_DROP_PERCENT_THRESHOLD)
        if price_drop_percent_value is None or price_drop_percent_value == "":
            price_drop_percent_value = DEFAULT_PRICE_DROP_PERCENT
        
        price_drop_absolute_value = current_options.get(CONF_PRICE_DROP_ABSOLUTE_THRESHOLD)
        if price_drop_absolute_value is None or price_drop_absolute_value == "":
            price_drop_absolute_value = current_config.get(CONF_PRICE_DROP_ABSOLUTE_THRESHOLD)
        if price_drop_absolute_value is None or price_drop_absolute_value == "":
            price_drop_absolute_value = DEFAULT_PRICE_DROP_ABSOLUTE
        
        low_fuel_value = current_options.get(CONF_LOW_FUEL_THRESHOLD)
        if low_fuel_value is None or low_fuel_value == "":
            low_fuel_value = current_config.get(CONF_LOW_FUEL_THRESHOLD)
        if low_fuel_value is None or low_fuel_value == "":
            low_fuel_value = DEFAULT_LOW_FUEL_THRESHOLD
        
        critical_fuel_value = current_options.get(CONF_CRITICAL_FUEL_THRESHOLD)
        if critical_fuel_value is None or critical_fuel_value == "":
            critical_fuel_value = current_config.get(CONF_CRITICAL_FUEL_THRESHOLD)
        if critical_fuel_value is None or critical_fuel_value == "":
            critical_fuel_value = DEFAULT_CRITICAL_FUEL_THRESHOLD
        
        # Get weekday-specific fallback values
        fallback_monday = current_options.get(CONF_FALLBACK_DAILY_KM_MONDAY)
        if fallback_monday is None or fallback_monday == "":
            fallback_monday = current_config.get(CONF_FALLBACK_DAILY_KM_MONDAY, DEFAULT_FALLBACK_DAILY_KM)
        
        fallback_tuesday = current_options.get(CONF_FALLBACK_DAILY_KM_TUESDAY)
        if fallback_tuesday is None or fallback_tuesday == "":
            fallback_tuesday = current_config.get(CONF_FALLBACK_DAILY_KM_TUESDAY, DEFAULT_FALLBACK_DAILY_KM)
        
        fallback_wednesday = current_options.get(CONF_FALLBACK_DAILY_KM_WEDNESDAY)
        if fallback_wednesday is None or fallback_wednesday == "":
            fallback_wednesday = current_config.get(CONF_FALLBACK_DAILY_KM_WEDNESDAY, DEFAULT_FALLBACK_DAILY_KM)
        
        fallback_thursday = current_options.get(CONF_FALLBACK_DAILY_KM_THURSDAY)
        if fallback_thursday is None or fallback_thursday == "":
            fallback_thursday = current_config.get(CONF_FALLBACK_DAILY_KM_THURSDAY, DEFAULT_FALLBACK_DAILY_KM)
        
        fallback_friday = current_options.get(CONF_FALLBACK_DAILY_KM_FRIDAY)
        if fallback_friday is None or fallback_friday == "":
            fallback_friday = current_config.get(CONF_FALLBACK_DAILY_KM_FRIDAY, DEFAULT_FALLBACK_DAILY_KM)
        
        fallback_saturday = current_options.get(CONF_FALLBACK_DAILY_KM_SATURDAY)
        if fallback_saturday is None or fallback_saturday == "":
            fallback_saturday = current_config.get(CONF_FALLBACK_DAILY_KM_SATURDAY, DEFAULT_FALLBACK_DAILY_KM)
        
        fallback_sunday = current_options.get(CONF_FALLBACK_DAILY_KM_SUNDAY)
        if fallback_sunday is None or fallback_sunday == "":
            fallback_sunday = current_config.get(CONF_FALLBACK_DAILY_KM_SUNDAY, DEFAULT_FALLBACK_DAILY_KM)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_PROVIDER,
                    default=provider_value,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=provider, label=PROVIDER_NAMES[provider])
                            for provider in PROVIDERS
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_API_KEY,
                    default=api_key_value,
                    description={"suggested_value": api_key_value},
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD,
                    )
                ),
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=update_interval_value,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_UPDATE_INTERVAL,
                        max=MAX_UPDATE_INTERVAL,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="min",
                    )
                ),
                vol.Optional(
                    CONF_FUEL_TYPE,
                    default=fuel_type_value,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=FUEL_TYPES,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_TANK_CAPACITY,
                    default=tank_capacity_value,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10.0,
                        max=200.0,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="L",
                    )
                ),
                vol.Optional(
                    CONF_INITIAL_CONSUMPTION,
                    description={"suggested_value": initial_consumption_value},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0,
                        max=50.0,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="L/100km",
                    )
                ),
                vol.Optional(
                    CONF_TELEGRAM_TOKEN,
                    default=telegram_token_value,
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD,
                    )
                ),
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
                vol.Optional(
                    CONF_PRICE_DROP_PERCENT_THRESHOLD,
                    default=price_drop_percent_value,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=100.0,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="%",
                    )
                ),
                vol.Optional(
                    CONF_PRICE_DROP_ABSOLUTE_THRESHOLD,
                    default=price_drop_absolute_value,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.01,
                        max=1.0,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="EUR",
                    )
                ),
                vol.Optional(
                    CONF_LOW_FUEL_THRESHOLD,
                    default=low_fuel_value,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0,
                        max=2000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_CRITICAL_FUEL_THRESHOLD,
                    default=critical_fuel_value,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0,
                        max=500.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_DAILY_KM_MONDAY,
                    default=fallback_monday,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_DAILY_KM_TUESDAY,
                    default=fallback_tuesday,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_DAILY_KM_WEDNESDAY,
                    default=fallback_wednesday,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_DAILY_KM_THURSDAY,
                    default=fallback_thursday,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_DAILY_KM_FRIDAY,
                    default=fallback_friday,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_DAILY_KM_SATURDAY,
                    default=fallback_saturday,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_DAILY_KM_SUNDAY,
                    default=fallback_sunday,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)
