"""
Fuel Watcher Car Advanced Manager (haFWCMA) Integration for Home Assistant.

This integration provides:
- Fuel price monitoring via Tankerkönig API
- Vehicle tank level tracking and forecasting
- Telegram notifications for optimal refueling times
- Advanced car management features
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SWITCH, Platform.NUMBER]

# Frontend card configuration
CARD_FILENAME = "fwcam-card.js"
CARD_VERSION = "1.0.0"  # Update this when the card changes

# Historical data import configuration
HISTORICAL_IMPORT_STARTUP_DELAY_SECONDS = 10  # Delay before starting background import

# Service schemas
SERVICE_ADD_REFUEL_EVENT = "add_refuel_event"
SERVICE_UPDATE_REFUEL_EVENT = "update_refuel_event"
SERVICE_DELETE_REFUEL_EVENT = "delete_refuel_event"

SCHEMA_ADD_REFUEL_EVENT = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
    vol.Required("timestamp"): cv.string,
    vol.Required("liters_refueled"): vol.Coerce(float),
    vol.Optional("odometer_km"): vol.Coerce(float),
    vol.Optional("price_per_liter"): vol.Coerce(float),
    vol.Optional("total_cost"): vol.Coerce(float),
    vol.Optional("station_name"): cv.string,
    vol.Optional("station_address"): cv.string,
    vol.Optional("fuel_type"): cv.string,
    vol.Optional("data_quality"): cv.string,
    vol.Optional("confidence"): vol.Coerce(float),
})

SCHEMA_UPDATE_REFUEL_EVENT = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
    vol.Required("event_id"): vol.Coerce(int),
    vol.Optional("timestamp"): cv.string,
    vol.Optional("liters_refueled"): vol.Coerce(float),
    vol.Optional("odometer_km"): vol.Coerce(float),
    vol.Optional("price_per_liter"): vol.Coerce(float),
    vol.Optional("total_cost"): vol.Coerce(float),
    vol.Optional("station_name"): cv.string,
    vol.Optional("station_address"): cv.string,
    vol.Optional("fuel_type"): cv.string,
    vol.Optional("data_quality"): cv.string,
    vol.Optional("confidence"): vol.Coerce(float),
})

SCHEMA_DELETE_REFUEL_EVENT = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
    vol.Required("event_id"): vol.Coerce(int),
})


async def _async_register_frontend_card(hass: HomeAssistant) -> None:
    """Register the FWCAM frontend card.
    
    This makes the custom card available in the Lovelace UI.
    The card is served from the integration's www directory and
    automatically registered when the integration loads.
    
    Args:
        hass: Home Assistant instance
    """
    try:
        # Get the path to our card JS file
        card_dir = Path(__file__).parent / "www"
        card_path = card_dir / CARD_FILENAME
        
        # Verify the card file exists
        if not card_path.exists():
            _LOGGER.warning(
                "FWCAM card file not found at %s. Card will not be available.",
                card_path
            )
            return
        
        # Register static path for serving the card
        # This makes the card available at /hafwcma_local/fwcam-card.js
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                url_path=f"/{DOMAIN}_local",
                path=str(card_dir),
                cache_headers=False,
            )
        ])
        
        # Register the card as a frontend module
        # This adds it to the list of available resources
        card_url = f"/{DOMAIN}_local/{CARD_FILENAME}?v={CARD_VERSION}"
        
        # Add to frontend extra module URLs
        # This is equivalent to manually adding the resource in the UI
        hass.data.setdefault("frontend_extra_module_url", set()).add(card_url)
        
        _LOGGER.info(
            "FWCAM frontend card registered at %s",
            card_url
        )
        
    except Exception as err:
        _LOGGER.error(
            "Failed to register FWCAM frontend card: %s",
            err,
            exc_info=True
        )


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the haFWCMA component from YAML configuration.
    
    Args:
        hass: Home Assistant instance
        config: Configuration dictionary
        
    Returns:
        True if setup was successful
    """
    _LOGGER.info("Setting up haFWCMA integration")
    hass.data.setdefault(DOMAIN, {})
    
    # Register the frontend card resource
    await _async_register_frontend_card(hass)
    
    # Register services
    async def handle_add_refuel_event(call: ServiceCall) -> None:
        """Handle the add_refuel_event service call."""
        from .utils.storage import add_refuel_event
        
        entry_id = call.data["config_entry_id"]
        entry = hass.config_entries.async_get_entry(entry_id)
        
        if not entry:
            _LOGGER.error("Config entry %s not found", entry_id)
            return
        
        event_data = {
            "timestamp": call.data["timestamp"],
            "liters_refueled": call.data["liters_refueled"],
            "odometer_km": call.data.get("odometer_km"),
            "price_per_liter": call.data.get("price_per_liter"),
            "total_cost": call.data.get("total_cost"),
            "station_name": call.data.get("station_name"),
            "station_address": call.data.get("station_address"),
            "fuel_type": call.data.get("fuel_type"),
            "data_quality": call.data.get("data_quality", "manual"),
            "confidence": call.data.get("confidence", 1.0),
        }
        
        event_id = await add_refuel_event(hass, entry, event_data)
        _LOGGER.info("Added refuel event with ID %s", event_id)
        
        # Trigger coordinator refresh to update sensors immediately
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("coordinator")
        if coordinator:
            await coordinator.async_request_refresh()
        else:
            _LOGGER.warning("Coordinator not found for entry %s, UI may not update immediately", entry_id)
    
    async def handle_update_refuel_event(call: ServiceCall) -> None:
        """Handle the update_refuel_event service call."""
        from .utils.storage import update_refueling_record
        
        entry_id = call.data["config_entry_id"]
        entry = hass.config_entries.async_get_entry(entry_id)
        
        if not entry:
            _LOGGER.error("Config entry %s not found", entry_id)
            return
        
        event_id = call.data["event_id"]
        
        # Build updates dictionary with only valid fields
        valid_fields = [
            "timestamp", "liters_refueled", "odometer_km", "price_per_liter",
            "total_cost", "station_name", "station_address", "fuel_type",
            "data_quality", "confidence"
        ]
        updates = {k: v for k, v in call.data.items() if k in valid_fields}
        
        await update_refueling_record(hass, entry, event_id, updates)
        _LOGGER.info("Updated refuel event ID %s", event_id)
        
        # Trigger coordinator refresh to update sensors immediately
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("coordinator")
        if coordinator:
            await coordinator.async_request_refresh()
        else:
            _LOGGER.warning("Coordinator not found for entry %s, UI may not update immediately", entry_id)
    
    async def handle_delete_refuel_event(call: ServiceCall) -> None:
        """Handle the delete_refuel_event service call."""
        from .utils.storage import delete_refueling_record
        
        entry_id = call.data["config_entry_id"]
        entry = hass.config_entries.async_get_entry(entry_id)
        
        if not entry:
            _LOGGER.error("Config entry %s not found", entry_id)
            return
        
        event_id = call.data["event_id"]
        await delete_refueling_record(hass, entry, event_id)
        _LOGGER.info("Deleted refuel event ID %s", event_id)
        
        # Trigger coordinator refresh to update sensors immediately
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("coordinator")
        if coordinator:
            await coordinator.async_request_refresh()
        else:
            _LOGGER.warning("Coordinator not found for entry %s, UI may not update immediately", entry_id)
    
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_REFUEL_EVENT, handle_add_refuel_event, schema=SCHEMA_ADD_REFUEL_EVENT
    )
    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE_REFUEL_EVENT, handle_update_refuel_event, schema=SCHEMA_UPDATE_REFUEL_EVENT
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_REFUEL_EVENT, handle_delete_refuel_event, schema=SCHEMA_DELETE_REFUEL_EVENT
    )
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up haFWCMA from a config entry.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry containing user configuration
        
    Returns:
        True if setup was successful
        
    Raises:
        ConfigEntryNotReady: If setup cannot be completed
    """
    _LOGGER.info("Setting up haFWCMA config entry: %s", entry.entry_id)
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "options": entry.options,
    }
    
    # TODO: Initialize providers (Tankerkönig, etc.)
    # TODO: Initialize messaging (Telegram)
    # TODO: Initialize forecast engine
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Setup options update listener - use update handler instead of reload
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    
    # Import historical data in the background (non-blocking)
    # This runs asynchronously after setup is complete
    hass.async_create_task(_import_historical_data_background(hass, entry))
    
    return True


async def _import_historical_data_background(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Import historical data in the background.
    
    This runs after integration setup to avoid blocking startup.
    Imports historical vehicle data from Home Assistant's recorder
    to populate consumption history and enable predictions.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    try:
        from .utils.historical_data_import import import_historical_vehicle_data
        
        _LOGGER.info("Starting background historical data import")
        
        # Wait to ensure coordinator is fully initialized
        import asyncio
        await asyncio.sleep(HISTORICAL_IMPORT_STARTUP_DELAY_SECONDS)
        
        # Import historical data (90 days lookback by default)
        result = await import_historical_vehicle_data(
            hass,
            entry,
            lookback_days=90,
            force_reimport=False,
        )
        
        if result["imported"]:
            _LOGGER.info(
                "Historical data import completed: %d odometer points, %d refuel events",
                result["odometer_points_imported"],
                result["refuel_events_detected"],
            )
        else:
            _LOGGER.info("Historical data import skipped: %s", result["reason"])
            
    except Exception as err:
        _LOGGER.error("Error during background historical data import: %s", err, exc_info=True)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry to unload
        
    Returns:
        True if unload was successful
    """
    _LOGGER.info("Unloading haFWCMA config entry: %s", entry.entry_id)
    
    # Cleanup coordinator
    coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
    if coordinator and hasattr(coordinator, "async_shutdown"):
        await coordinator.async_shutdown()
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options without reloading the integration.
    
    This updates the coordinator and entities in-place to avoid entities
    becoming unavailable during the update process.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry with updated options
    """
    _LOGGER.info("Updating options for haFWCMA config entry: %s", entry.entry_id)
    
    # Update stored options
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN][entry.entry_id]["options"] = entry.options
        
        # Get the coordinator and update it with new settings
        coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
        if coordinator and hasattr(coordinator, "async_update_config"):
            await coordinator.async_update_config(entry)
        
        # Trigger a refresh to apply new settings
        if coordinator:
            await coordinator.async_request_refresh()
    
    _LOGGER.info("Options updated successfully without reloading")


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change.
    
    This function is kept for compatibility but should not be used
    as the update listener. Use async_update_options instead.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry to reload
    """
    _LOGGER.info("Reloading haFWCMA config entry: %s", entry.entry_id)
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
