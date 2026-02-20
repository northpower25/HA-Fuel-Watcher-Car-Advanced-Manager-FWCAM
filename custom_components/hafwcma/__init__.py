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
from homeassistant.core import CoreState, HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_call_later
import homeassistant.helpers.config_validation as cv

# ServiceResponse is available in HA 2023.7+, but return type annotation is optional
# The actual return value is a dict, so using dict as fallback for type checking is safe
try:
    from homeassistant.core import ServiceResponse
except ImportError:
    ServiceResponse = dict  # Type annotation only, actual return is always dict

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SWITCH, Platform.NUMBER]

# Frontend card configuration
CARD_FILENAME = "fwcam-card.js"
CARD_VERSION = "1.0.0"  # Update this when the card changes

# Dashboard panel configuration
PANEL_FILENAME = "fwcam-dashboard-panel.js"
PANEL_URL_PATH = "hafwcma"
PANEL_ELEMENT_NAME = "fwcam-dashboard-panel"

# Service schemas
SERVICE_ADD_REFUEL_EVENT = "add_refuel_event"
SERVICE_UPDATE_REFUEL_EVENT = "update_refuel_event"
SERVICE_DELETE_REFUEL_EVENT = "delete_refuel_event"
SERVICE_ADD_TRIP = "add_trip"
SERVICE_EDIT_TRIP = "edit_trip"
SERVICE_DELETE_TRIP = "delete_trip"
SERVICE_CREATE_PATTERN = "create_pattern"
SERVICE_EXPORT_TRIPS = "export_trips"
SERVICE_GET_ALL_TRIPS = "get_all_trips"
SERVICE_GET_ALL_REFUELINGS = "get_all_refuelings"
SERVICE_REVERSE_GEOCODE = "reverse_geocode"
SERVICE_GET_GEOCODING_CACHE_STATS = "get_geocoding_cache_stats"
SERVICE_SIMULATE_REFUELING_EVENT = "simulate_refueling_event"

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

SCHEMA_ADD_TRIP = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
    vol.Required("timestamp_start"): cv.string,
    vol.Required("timestamp_end"): cv.string,
    vol.Required("distance_km"): vol.Coerce(float),
    vol.Optional("category"): vol.In(["business", "private", "commute"]),
    vol.Optional("purpose"): cv.string,
    vol.Optional("fuel_consumed"): vol.Coerce(float),
    vol.Optional("additional_costs"): vol.Coerce(float),
    vol.Optional("odometer_start"): vol.Coerce(float),
    vol.Optional("odometer_end"): vol.Coerce(float),
    vol.Optional("start_latitude"): vol.Coerce(float),
    vol.Optional("start_longitude"): vol.Coerce(float),
    vol.Optional("end_latitude"): vol.Coerce(float),
    vol.Optional("end_longitude"): vol.Coerce(float),
    vol.Optional("start_name"): cv.string,
    vol.Optional("start_address"): cv.string,
    vol.Optional("end_name"): cv.string,
    vol.Optional("end_address"): cv.string,
    vol.Optional("data_quality"): cv.string,
    vol.Optional("confidence"): vol.Coerce(float),
})

SCHEMA_EDIT_TRIP = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
    vol.Required("trip_id"): vol.Coerce(int),
    vol.Optional("category"): vol.In(["business", "private", "commute"]),
    vol.Optional("purpose"): cv.string,
    vol.Optional("additional_costs"): vol.Coerce(float),
    vol.Optional("notes"): cv.string,
    vol.Optional("odometer_start"): vol.Coerce(float),
    vol.Optional("odometer_end"): vol.Coerce(float),
    vol.Optional("start_latitude"): vol.Coerce(float),
    vol.Optional("start_longitude"): vol.Coerce(float),
    vol.Optional("end_latitude"): vol.Coerce(float),
    vol.Optional("end_longitude"): vol.Coerce(float),
    vol.Optional("start_name"): cv.string,
    vol.Optional("start_address"): cv.string,
    vol.Optional("end_name"): cv.string,
    vol.Optional("end_address"): cv.string,
    vol.Optional("data_quality"): cv.string,
    vol.Optional("confidence"): vol.Coerce(float),
})

SCHEMA_DELETE_TRIP = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
    vol.Required("trip_id"): vol.Coerce(int),
})

SCHEMA_CREATE_PATTERN = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
    vol.Required("name"): cv.string,
    vol.Required("start_latitude"): vol.Coerce(float),
    vol.Required("start_longitude"): vol.Coerce(float),
    vol.Required("end_latitude"): vol.Coerce(float),
    vol.Required("end_longitude"): vol.Coerce(float),
    vol.Optional("category"): vol.In(["business", "private", "commute"]),
    vol.Optional("purpose"): cv.string,
    vol.Optional("is_anonymized"): cv.boolean,
})

SCHEMA_EXPORT_TRIPS = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
    vol.Optional("format"): vol.In(["csv", "json"]),
    vol.Optional("date_from"): cv.string,
    vol.Optional("date_to"): cv.string,
    vol.Optional("category"): vol.In(["all", "business", "private", "commute"]),
})

SCHEMA_GET_ALL_TRIPS = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
})

SCHEMA_GET_ALL_REFUELINGS = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
})

SCHEMA_REVERSE_GEOCODE = vol.Schema({
    vol.Required("latitude"): vol.Coerce(float),
    vol.Required("longitude"): vol.Coerce(float),
    vol.Optional("use_cache", default=True): cv.boolean,
})

SCHEMA_GET_GEOCODING_CACHE_STATS = vol.Schema({})

SCHEMA_SIMULATE_REFUELING_EVENT = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
    vol.Optional("include_missing_data", default=True): cv.boolean,
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


async def _register_dashboard_panel(hass: HomeAssistant) -> None:
    """Register the FWCAM dashboard as a sidebar panel (panel_custom).

    This adds a "Fuel Watcher" entry to the Home Assistant sidebar that
    opens the FWCAM dashboard panel.  The panel auto-discovers all
    configured vehicles so no manual YAML copy-paste is required.

    Uses homeassistant.components.panel_custom.async_register_panel which
    is the correct API for registering custom panels in Home Assistant.

    The static path for the panel JS is already served via the
    /{DOMAIN}_local/ prefix registered by _async_register_frontend_card.

    Args:
        hass: Home Assistant instance
    """
    try:
        from homeassistant.components.panel_custom import async_register_panel

        panel_url = f"/{DOMAIN}_local/{PANEL_FILENAME}?v={CARD_VERSION}"

        await async_register_panel(
            hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name=PANEL_ELEMENT_NAME,
            sidebar_title="Fuel Watcher",
            sidebar_icon="mdi:gas-station",
            module_url=panel_url,
            embed_iframe=False,
            trust_external=False,
            require_admin=False,
        )

        _LOGGER.info(
            "FWCAM dashboard panel registered at /%s (module: %s)",
            PANEL_URL_PATH,
            panel_url,
        )

    except Exception as err:
        _LOGGER.error(
            "Failed to register FWCAM dashboard panel: %s",
            err,
            exc_info=True,
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
    
    # Register the dashboard as a sidebar panel (panel_custom)
    await _register_dashboard_panel(hass)
    
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
        _LOGGER.info("Added refuel event with ID %s via service call", event_id)
        
        # Fire event for Telegram notification
        _LOGGER.info(
            "Firing %s_refueling_added event for service call (refuel_id: %s)",
            DOMAIN,
            event_id
        )
        hass.bus.async_fire(
            f"{DOMAIN}_refueling_added",
            {
                "config_entry_id": entry_id,
                "refuel_id": event_id,
                "refuel_data": event_data,
            }
        )
        
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
    
    async def handle_add_trip(call: ServiceCall) -> None:
        """Handle the add_trip service call."""
        from .utils.storage import add_trip
        from .utils.geocoding import cache_manual_location
        from homeassistant.util import dt as dt_util
        
        entry_id = call.data["config_entry_id"]
        entry = hass.config_entries.async_get_entry(entry_id)
        
        if not entry:
            _LOGGER.error("Config entry %s not found", entry_id)
            return
        
        trip_data = {
            "timestamp_start": call.data["timestamp_start"],
            "timestamp_end": call.data["timestamp_end"],
            "distance_km": call.data["distance_km"],
            "category": call.data.get("category", "private"),
            "purpose": call.data.get("purpose"),
            "fuel_consumed": call.data.get("fuel_consumed"),
            "additional_costs": call.data.get("additional_costs", 0.0),
            "odometer_start": call.data.get("odometer_start"),
            "odometer_end": call.data.get("odometer_end"),
            "start_latitude": call.data.get("start_latitude"),
            "start_longitude": call.data.get("start_longitude"),
            "end_latitude": call.data.get("end_latitude"),
            "end_longitude": call.data.get("end_longitude"),
            "start_name": call.data.get("start_name"),
            "start_address": call.data.get("start_address"),
            "end_name": call.data.get("end_name"),
            "end_address": call.data.get("end_address"),
            "data_quality": call.data.get("data_quality", "manual"),
            "confidence": call.data.get("confidence", 1.0),
            "is_manual": True,
        }
        
        trip_id = await add_trip(hass, entry, trip_data)
        _LOGGER.info("Added trip with ID %s", trip_id)
        
        # Cache manually entered location data for future auto-fill
        cache_manual_location(
            latitude=trip_data.get("start_latitude"),
            longitude=trip_data.get("start_longitude"),
            location_name=trip_data.get("start_name"),
            address=trip_data.get("start_address"),
        )
        cache_manual_location(
            latitude=trip_data.get("end_latitude"),
            longitude=trip_data.get("end_longitude"),
            location_name=trip_data.get("end_name"),
            address=trip_data.get("end_address"),
        )
        
        # Trigger coordinator refresh
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("coordinator")
        if coordinator:
            await coordinator.async_request_refresh()
    
    async def handle_edit_trip(call: ServiceCall) -> None:
        """Handle the edit_trip service call."""
        from .utils.storage import update_trip
        from .utils.geocoding import cache_manual_location
        
        entry_id = call.data["config_entry_id"]
        entry = hass.config_entries.async_get_entry(entry_id)
        
        if not entry:
            _LOGGER.error("Config entry %s not found", entry_id)
            return
        
        trip_id = call.data["trip_id"]
        updates = {
            k: v for k, v in call.data.items()
            if k not in ["config_entry_id", "trip_id"] and v is not None
        }
        
        success = await update_trip(hass, entry, trip_id, updates)
        if success:
            _LOGGER.info("Updated trip ID %s", trip_id)
            
            # Cache manually entered location data for future auto-fill
            # Start location
            start_lat = updates.get("start_latitude")
            start_lon = updates.get("start_longitude")
            if start_lat is not None and start_lon is not None:
                cache_manual_location(
                    latitude=start_lat,
                    longitude=start_lon,
                    location_name=updates.get("start_name"),
                    address=updates.get("start_address"),
                )
            # End location
            end_lat = updates.get("end_latitude")
            end_lon = updates.get("end_longitude")
            if end_lat is not None and end_lon is not None:
                cache_manual_location(
                    latitude=end_lat,
                    longitude=end_lon,
                    location_name=updates.get("end_name"),
                    address=updates.get("end_address"),
                )
        else:
            _LOGGER.error("Trip ID %s not found", trip_id)
        
        # Trigger coordinator refresh
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("coordinator")
        if coordinator:
            await coordinator.async_request_refresh()
    
    async def handle_delete_trip(call: ServiceCall) -> None:
        """Handle the delete_trip service call."""
        from .utils.storage import delete_trip
        
        entry_id = call.data["config_entry_id"]
        entry = hass.config_entries.async_get_entry(entry_id)
        
        if not entry:
            _LOGGER.error("Config entry %s not found", entry_id)
            return
        
        trip_id = call.data["trip_id"]
        success = await delete_trip(hass, entry, trip_id)
        if success:
            _LOGGER.info("Deleted trip ID %s", trip_id)
        else:
            _LOGGER.error("Trip ID %s not found", trip_id)
        
        # Trigger coordinator refresh
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("coordinator")
        if coordinator:
            await coordinator.async_request_refresh()
    
    async def handle_create_pattern(call: ServiceCall) -> None:
        """Handle the create_pattern service call."""
        from .utils.storage import add_trip_pattern
        from homeassistant.util import dt as dt_util
        
        entry_id = call.data["config_entry_id"]
        entry = hass.config_entries.async_get_entry(entry_id)
        
        if not entry:
            _LOGGER.error("Config entry %s not found", entry_id)
            return
        
        pattern_data = {
            "name": call.data["name"],
            "start_latitude": call.data["start_latitude"],
            "start_longitude": call.data["start_longitude"],
            "start_radius_m": 200.0,
            "end_latitude": call.data["end_latitude"],
            "end_longitude": call.data["end_longitude"],
            "end_radius_m": 200.0,
            "category": call.data.get("category", "private"),
            "purpose": call.data.get("purpose", ""),
            "is_anonymized": call.data.get("is_anonymized", False),
            "is_tax_relevant": False,
            "match_count": 0,
            "avg_distance_km": 0.0,
            "avg_duration_minutes": 0.0,
            "avg_fuel_consumption": 0.0,
        }
        
        pattern_id = await add_trip_pattern(hass, entry, pattern_data)
        _LOGGER.info("Created trip pattern with ID %s", pattern_id)
        
        # Trigger coordinator refresh
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("coordinator")
        if coordinator:
            await coordinator.async_request_refresh()
    
    async def handle_export_trips(call: ServiceCall) -> None:
        """Handle the export_trips service call."""
        from .utils.storage import get_trips
        import csv
        import json
        from pathlib import Path
        from homeassistant.util import dt as dt_util
        
        entry_id = call.data["config_entry_id"]
        entry = hass.config_entries.async_get_entry(entry_id)
        
        if not entry:
            _LOGGER.error("Config entry %s not found", entry_id)
            return
        
        # Get filters
        format_type = call.data.get("format", "csv")
        date_from = call.data.get("date_from")
        date_to = call.data.get("date_to")
        category = call.data.get("category", "all")
        
        # Get trips
        trips = await get_trips(hass, entry)
        
        # Apply filters
        if category != "all":
            trips = [t for t in trips if t.get("category") == category]
        
        if date_from or date_to:
            filtered_trips = []
            for trip in trips:
                try:
                    trip_date = dt_util.parse_datetime(trip.get("timestamp_end", ""))
                    if trip_date:
                        trip_date_str = trip_date.date().isoformat()
                        if date_from and trip_date_str < date_from:
                            continue
                        if date_to and trip_date_str > date_to:
                            continue
                    filtered_trips.append(trip)
                except (ValueError, TypeError):
                    filtered_trips.append(trip)
            trips = filtered_trips
        
        # Generate filename
        filename = f"trips_export_{dt_util.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
        filepath = Path(hass.config.path("www")) / filename
        
        # Ensure www directory exists
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
        except OSError as err:
            _LOGGER.error("Failed to create export directory: %s", err)
            return
        
        # Export
        try:
            if format_type == "csv":
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    if trips:
                        writer = csv.DictWriter(f, fieldnames=trips[0].keys())
                        writer.writeheader()
                        writer.writerows(trips)
            else:  # json
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(trips, f, indent=2, ensure_ascii=False)
            
            _LOGGER.info("Exported %d trips to %s", len(trips), filepath)
        except (IOError, OSError) as err:
            _LOGGER.error("Failed to export trips to %s: %s", filepath, err)
    
    async def handle_get_all_trips(call: ServiceCall) -> ServiceResponse:
        """Handle the get_all_trips service call.
        
        Returns all trips for a given config entry, sorted by end time (newest first).
        This service allows the frontend card to retrieve all trip data without
        exceeding the 16KB attribute limit.
        """
        from .utils.storage import get_trips
        
        entry_id = call.data["config_entry_id"]
        entry = hass.config_entries.async_get_entry(entry_id)
        
        if not entry:
            _LOGGER.error("Config entry %s not found", entry_id)
            return {"trips": [], "error": "Config entry not found"}
        
        # Get all trips
        trips = await get_trips(hass, entry)
        
        # Sort by end time (newest first)
        sorted_trips = sorted(trips, key=lambda x: x.get("timestamp_end", ""), reverse=True)
        
        _LOGGER.debug("Retrieved %d trips for config entry %s", len(sorted_trips), entry_id)
        
        return {"trips": sorted_trips}
    
    async def handle_get_all_refuelings(call: ServiceCall) -> ServiceResponse:
        """Handle the get_all_refuelings service call.
        
        Returns all refueling events for a given config entry, sorted by timestamp (newest first).
        This service allows the frontend card to retrieve all refueling data without
        exceeding the 16KB attribute limit.
        """
        from .utils.storage import get_refueling_log
        
        entry_id = call.data["config_entry_id"]
        entry = hass.config_entries.async_get_entry(entry_id)
        
        if not entry:
            _LOGGER.error("Config entry %s not found", entry_id)
            return {"refuelings": [], "error": "Config entry not found"}
        
        # Get all refueling events
        refueling_log = await get_refueling_log(hass, entry)
        
        # Sort by timestamp (newest first)
        sorted_refuelings = sorted(
            refueling_log,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        _LOGGER.debug("Retrieved %d refueling events for config entry %s", len(sorted_refuelings), entry_id)
        
        return {"refuelings": sorted_refuelings}
    
    async def handle_reverse_geocode(call: ServiceCall) -> ServiceResponse:
        """Handle the reverse_geocode service call.
        
        Reverse geocodes coordinates to location name and address.
        Uses cache by default to avoid unnecessary API calls.
        Returns success=True even when no data is found (fields remain empty).
        Only returns success=False on actual errors (exceptions).
        
        Returns:
            ServiceResponse dict with keys:
                - location_name (str): Extracted location name (e.g., "Brandenburg Gate")
                - address (str): Full formatted address (e.g., "Unter den Linden, 10117 Berlin")
                - success (bool): True if no error occurred, False on exceptions
                - from_cache (bool): True if data came from cache
                - error (str): Error message if success is False (optional)
        """
        from .utils.geocoding import geocode_trip_location
        
        latitude = call.data["latitude"]
        longitude = call.data["longitude"]
        use_cache = call.data.get("use_cache", True)
        
        _LOGGER.debug("Reverse geocoding request for (%.4f, %.4f), use_cache=%s", 
                     latitude, longitude, use_cache)
        
        try:
            result = await geocode_trip_location(latitude, longitude, use_cache=use_cache)
            
            if result:
                _LOGGER.debug("Reverse geocode result: name=%s, address=%s, from_cache=%s", 
                            result.get("location_name"), result.get("address"), result.get("from_cache"))
                return {
                    "location_name": result.get("location_name", ""),
                    "address": result.get("address", ""),
                    "success": True,
                    "from_cache": result.get("from_cache", False),
                }
            else:
                _LOGGER.debug("No geocoding data found for (%.4f, %.4f)", latitude, longitude)
                return {
                    "location_name": "",
                    "address": "",
                    "success": True,
                    "from_cache": False,
                }
        except Exception as err:
            _LOGGER.error("Error during reverse geocoding: %s", err)
            # Only actual exceptions are considered errors
            return {
                "location_name": "",
                "address": "",
                "success": False,
                "error": str(err),
            }
    
    async def handle_get_geocoding_cache_stats(call: ServiceCall) -> ServiceResponse:
        """Handle the get_geocoding_cache_stats service call.
        
        Returns statistics about the geocoding cache for debugging purposes.
        Shows the total number of cache entries and details about each entry.
        
        Returns:
            ServiceResponse dict with keys:
                - total_entries (int): Total number of cache entries
                - entries (list): List of cache entries with coordinates, names, addresses
        """
        from .utils.geocoding import get_geocoder
        
        try:
            geocoder = get_geocoder()
            stats = geocoder.get_cache_stats()
            
            _LOGGER.debug("Geocoding cache stats: %d entries", stats["total_entries"])
            return stats
            
        except Exception as err:
            _LOGGER.error("Error getting geocoding cache stats: %s", err)
            return {
                "total_entries": 0,
                "entries": [],
                "error": str(err),
            }

    async def handle_simulate_refueling_event(call: ServiceCall) -> None:
        """Handle the simulate_refueling_event service call.
        
        Creates a simulated refueling event for testing Telegram notification
        functionality. This is useful for testing the bidirectional data
        collection workflow without actually refueling.
        """
        from .utils.storage import add_refuel_event, get_last_fuel_type
        from datetime import datetime
        import random
        
        entry_id = call.data["config_entry_id"]
        include_missing_data = call.data.get("include_missing_data", True)
        entry = hass.config_entries.async_get_entry(entry_id)
        
        if not entry:
            _LOGGER.error("Config entry %s not found", entry_id)
            return
        
        # Get last used fuel type, or default to None to test fuel type suggestion
        last_fuel_type = await get_last_fuel_type(hass, entry)
        
        # Create a simulated refueling with some data missing
        timestamp = datetime.now().isoformat()
        
        if include_missing_data:
            # Create with intentionally missing data to test the collection workflow
            event_data = {
                "timestamp": timestamp,
                "liters_refueled": round(random.uniform(30.0, 55.0), 2),
                "data_quality": "simulated",
                "confidence": 0.8,
                # Intentionally omit: fuel_type, odometer_km, price_per_liter, total_cost, station_name, station_address
                # This allows testing of the last fuel type suggestion feature
            }
        else:
            # Create with complete data using last fuel type or default to e10
            liters = round(random.uniform(30.0, 55.0), 2)
            price = round(random.uniform(1.50, 1.90), 3)
            event_data = {
                "timestamp": timestamp,
                "liters_refueled": liters,
                "odometer_km": round(random.uniform(50000, 150000), 1),
                "price_per_liter": price,
                "total_cost": round(liters * price, 2),
                "station_name": random.choice(["Shell", "Aral", "Esso", "Total"]),
                "station_address": "Teststraße 123, 12345 Teststadt",
                "fuel_type": last_fuel_type or "e10",
                "data_quality": "simulated",
                "confidence": 1.0,
            }
        
        event_id = await add_refuel_event(hass, entry, event_data)
        _LOGGER.info("Simulated refuel event with ID %s (missing_data=%s)", event_id, include_missing_data)
        
        # Fire event for Telegram notification
        hass.bus.async_fire(
            f"{DOMAIN}_refueling_added",
            {
                "config_entry_id": entry_id,
                "refuel_id": event_id,
                "refuel_data": event_data,
            }
        )
        
        # Trigger coordinator refresh to update sensors immediately
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("coordinator")
        if coordinator:
            await coordinator.async_request_refresh()

    
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_REFUEL_EVENT, handle_add_refuel_event, schema=SCHEMA_ADD_REFUEL_EVENT
    )
    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE_REFUEL_EVENT, handle_update_refuel_event, schema=SCHEMA_UPDATE_REFUEL_EVENT
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_REFUEL_EVENT, handle_delete_refuel_event, schema=SCHEMA_DELETE_REFUEL_EVENT
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_TRIP, handle_add_trip, schema=SCHEMA_ADD_TRIP
    )
    hass.services.async_register(
        DOMAIN, SERVICE_EDIT_TRIP, handle_edit_trip, schema=SCHEMA_EDIT_TRIP
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_TRIP, handle_delete_trip, schema=SCHEMA_DELETE_TRIP
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CREATE_PATTERN, handle_create_pattern, schema=SCHEMA_CREATE_PATTERN
    )
    hass.services.async_register(
        DOMAIN, SERVICE_EXPORT_TRIPS, handle_export_trips, schema=SCHEMA_EXPORT_TRIPS
    )
    hass.services.async_register(
        DOMAIN, SERVICE_GET_ALL_TRIPS, handle_get_all_trips, schema=SCHEMA_GET_ALL_TRIPS, supports_response=True
    )
    hass.services.async_register(
        DOMAIN, SERVICE_GET_ALL_REFUELINGS, handle_get_all_refuelings, schema=SCHEMA_GET_ALL_REFUELINGS, supports_response=True
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REVERSE_GEOCODE, handle_reverse_geocode, schema=SCHEMA_REVERSE_GEOCODE, supports_response=True
    )
    hass.services.async_register(
        DOMAIN, SERVICE_GET_GEOCODING_CACHE_STATS, handle_get_geocoding_cache_stats, schema=SCHEMA_GET_GEOCODING_CACHE_STATS, supports_response=True
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SIMULATE_REFUELING_EVENT, handle_simulate_refueling_event, schema=SCHEMA_SIMULATE_REFUELING_EVENT
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
    
    # Initialize Telegram event handler for bidirectional communication
    # Defer initialization until Home Assistant is fully started to ensure telegram_bot is loaded
    from .const import CONF_TELEGRAM_CHAT_ID, CONF_TELEGRAM_TOKEN
    from .telegram_handler import TelegramEventHandler
    
    telegram_chat_id = entry.data.get(CONF_TELEGRAM_CHAT_ID)
    telegram_token = entry.data.get(CONF_TELEGRAM_TOKEN)
    
    if telegram_chat_id and telegram_token:
        _LOGGER.info(
            "Telegram credentials found (chat_id: %s). "
            "Will initialize Telegram handlers after Home Assistant startup completes.",
            telegram_chat_id
        )
        
        async def _initialize_telegram_handlers(event):
            """Initialize Telegram handlers after HA is fully started.
            
            This ensures telegram_bot integration is loaded before we try to use it.
            """
            _LOGGER.info("Home Assistant started - initializing Telegram handlers now...")
            
            # Check if telegram_bot is now available
            if "telegram_bot" not in hass.config.components:
                _LOGGER.warning(
                    "telegram_bot integration still not found after Home Assistant startup. "
                    "Telegram features will not be available. "
                    "Please configure the telegram_bot integration. "
                    "See: https://www.home-assistant.io/integrations/telegram_bot/"
                )
                return
            
            # Also check if the telegram_bot service is available
            if not hass.services.has_service("telegram_bot", "send_message"):
                _LOGGER.warning(
                    "telegram_bot integration loaded but send_message service not available. "
                    "This may indicate the integration is still initializing. "
                    "Telegram features may not work correctly."
                )
            else:
                _LOGGER.info("telegram_bot send_message service is available")
            
            telegram_handler = TelegramEventHandler(hass, entry, telegram_chat_id)
            await telegram_handler.async_setup()
            hass.data[DOMAIN][entry.entry_id]["telegram_handler"] = telegram_handler
            _LOGGER.info("Telegram event handler initialized for bidirectional communication")
            
            # Initialize Telegram refueling handler for bidirectional refueling tracking
            from .telegram_refueling_handler import TelegramRefuelingHandler
            
            _LOGGER.debug("Creating TelegramRefuelingHandler instance...")
            telegram_refueling_handler = TelegramRefuelingHandler(
                hass,
                entry,
                telegram_chat_id,
                telegram_handler
            )
            setup_result = await telegram_refueling_handler.async_setup()
            
            if setup_result:
                hass.data[DOMAIN][entry.entry_id]["telegram_refueling_handler"] = telegram_refueling_handler
                _LOGGER.info("✅ Telegram refueling handler successfully initialized and ready for notifications")
            else:
                _LOGGER.error(
                    "❌ Telegram refueling handler setup FAILED. "
                    "Refueling notifications will NOT be sent. "
                    "Check that telegram_bot integration is properly configured."
                )
        
        # Register to initialize telegram handlers after HA is fully started
        hass.bus.async_listen_once("homeassistant_started", _initialize_telegram_handlers)
        _LOGGER.debug("Registered telegram handler initialization for homeassistant_started event")
    else:
        _LOGGER.info(
            "Telegram not configured (chat_id: %s, token: %s), skipping event handler setup",
            "present" if telegram_chat_id else "missing",
            "present" if telegram_token else "missing"
        )
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Setup options update listener - use update handler instead of reload
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # Apply initial feature settings and then import historical data, sequentially,
    # after HA is fully started.  A single listener ensures trip-tracking is
    # persisted to storage *before* the historical import checks it.
    async def _on_homeassistant_started(event):
        """Run first-time setup tasks in order after HA has fully started."""
        await _apply_initial_feature_settings(hass, entry)
        await _import_historical_data_background(hass, entry)

    if hass.state is CoreState.running:
        # HA is already running (e.g. integration reloaded at runtime).
        # Schedule import 5 minutes from now so the integration can finish
        # loading before the heavyweight recorder queries start.
        _LOGGER.info(
            "HA already running – scheduling historical import in 5 minutes for %s",
            entry.entry_id,
        )

        async def _delayed_start(_now):
            await _apply_initial_feature_settings(hass, entry)
            await _import_historical_data_background(hass, entry)

        entry.async_on_unload(
            async_call_later(hass, 300, _delayed_start)
        )
    else:
        hass.bus.async_listen_once("homeassistant_started", _on_homeassistant_started)
    
    return True


async def _apply_initial_feature_settings(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Apply initial feature settings from config flow to storage and options.

    This runs once after first-time setup to apply trip_tracking_initial_enabled
    and proximity_alerts_enabled settings from the config entry data to the
    persistent storage and config entry options respectively.

    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    from .const import (
        CONF_PROXIMITY_ALERTS_ENABLED,
        CONF_TRIP_TRACKING_INITIAL_ENABLED,
    )
    from .utils import storage

    trip_tracking_initial = entry.data.get(CONF_TRIP_TRACKING_INITIAL_ENABLED, False)
    trip_tracking_saved = False

    try:
        if trip_tracking_initial:
            data = await storage.load_data(hass, entry)
            trip_config = data.get("trip_tracking_config", {})

            # Only apply initial setting if trip tracking hasn't been explicitly configured yet
            if trip_config.get("enabled") is None or not trip_config.get("privacy_notice_accepted"):
                from homeassistant.util import dt as dt_util
                trip_config["enabled"] = True
                trip_config["privacy_notice_accepted"] = True
                trip_config["privacy_notice_accepted_at"] = dt_util.now().isoformat()
                trip_config["last_enabled_at"] = dt_util.now().isoformat()
                data["trip_tracking_config"] = trip_config
                await storage.save_data(hass, entry, data)
                trip_tracking_saved = True
                _LOGGER.info("Applied initial trip tracking setting: enabled=True")

        # Migrate proximity_alerts_enabled from entry.data to entry.options so
        # that the ProximityAlertsSwitch entity reflects the value chosen during
        # the config flow (the switch reads exclusively from entry.options).
        proximity_initial = entry.data.get(CONF_PROXIMITY_ALERTS_ENABLED)
        if proximity_initial is not None and CONF_PROXIMITY_ALERTS_ENABLED not in entry.options:
            new_options = dict(entry.options)
            new_options[CONF_PROXIMITY_ALERTS_ENABLED] = proximity_initial
            hass.config_entries.async_update_entry(entry, options=new_options)
            _LOGGER.info(
                "Migrated initial proximity_alerts_enabled=%s to entry options",
                proximity_initial,
            )

        # Refresh the coordinator so that trip-tracking / proximity switches
        # immediately reflect the values we just persisted.
        if trip_tracking_saved:
            coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("coordinator")
            if coordinator is not None:
                await coordinator.async_request_refresh()

    except Exception as err:
        _LOGGER.error("Error applying initial feature settings: %s", err)


async def _import_historical_data_background(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Import historical data in the background.
    
    This runs after integration setup to avoid blocking startup.
    Imports historical vehicle data from Home Assistant's recorder
    to populate consumption history and enable predictions.
    Also imports trip history if trip tracking is enabled.
    Also rebuilds the geocoding cache from existing trip data.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    try:
        from .const import CONF_IMPORT_HISTORICAL_DATA
        from .utils.historical_data_import import import_historical_vehicle_data, import_historical_trip_data
        from .utils import storage
        from .utils.geocoding import rebuild_cache_from_trips
        from .utils.statistics_engine import recompute_weekday_stats

        # Check if the user opted out of historical import during setup
        import_requested = entry.data.get(CONF_IMPORT_HISTORICAL_DATA, True)
        if not import_requested:
            _LOGGER.info(
                "Historical data import skipped: user opted out during setup"
            )
            return

        # Signal that the import is now running
        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN][entry.entry_id]["historical_import_status"] = "running"
        
        _LOGGER.info("Starting background historical data import")
        
        # Import historical vehicle data (90 days lookback by default)
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
        
        # Import trip history if trip tracking is enabled.
        # This also runs when vehicle data import was already completed so that
        # a previous run that skipped trip import (e.g. due to the race condition
        # between initial-feature-settings and this function) can still import trips.
        data = await storage.load_data(hass, entry)
        trip_config = data.get("trip_tracking_config", {})
        trip_tracking_enabled = trip_config.get("enabled", False)

        trip_result = None
        if trip_tracking_enabled:
            # Check whether trip import has already been completed successfully.
            # import_historical_trip_data uses last_historical_import["imported"] to
            # guard against duplicate imports; vehicle data import does NOT set that
            # flag, so a prior vehicle-only run will not block a trip import here.
            last_trip_import = data.get("last_historical_import", {})
            trip_already_done = last_trip_import.get("imported", False)

            if not trip_already_done:
                _LOGGER.info("Trip tracking is enabled, importing historical trip data")
                trip_result = await import_historical_trip_data(
                    hass,
                    entry,
                    lookback_days=90,
                    force_reimport=False,
                    import_type="automatic",
                )
                
                if trip_result["imported"]:
                    _LOGGER.info(
                        "Historical trip import completed: %d trips detected",
                        trip_result["trips_detected"],
                    )
                else:
                    _LOGGER.info("Historical trip import skipped: %s", trip_result["reason"])
            else:
                _LOGGER.debug("Historical trip import already completed, skipping")
        else:
            _LOGGER.debug("Trip tracking not enabled, skipping trip history import")
        
        # Recompute weekday consumption stats from the freshly imported odometer history
        await recompute_weekday_stats(hass, entry)
        _LOGGER.info("Weekday consumption stats recomputed after historical import")

        # Ensure trip_statistics are consistent with the saved trips list.
        # This is a safety measure in case the batch-save in _import_trip_history
        # wrote trips but the statistics dict was not updated atomically.
        if trip_result is not None and trip_result.get("imported"):
            try:
                from .utils.storage import recalculate_trip_statistics
                await recalculate_trip_statistics(hass, entry)
                _LOGGER.info("Trip statistics recalculated after historical import")
            except Exception as stats_err:
                _LOGGER.warning("Error recalculating trip statistics: %s", stats_err)

        # Rebuild geocoding cache from existing trip data
        _LOGGER.info("Rebuilding geocoding cache from existing trip data")
        cache_count = await rebuild_cache_from_trips(hass, entry)
        _LOGGER.info("Geocoding cache rebuilt with %d entries", cache_count)

        # Mark import status as completed
        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN][entry.entry_id]["historical_import_status"] = "completed"

        # Trigger a coordinator refresh so sensors immediately show the imported data
        # without waiting for the next scheduled update cycle.
        try:
            coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("coordinator")
            if coordinator is not None:
                await coordinator.async_request_refresh()
                _LOGGER.debug("Coordinator refresh requested after historical import")
        except Exception as refresh_err:
            _LOGGER.warning("Error requesting coordinator refresh after import: %s", refresh_err)

        # Reload storage data to capture everything written during the import
        data = await storage.load_data(hass, entry)

        # ── Only send the first-install notification ONCE per vehicle ────────
        if data.get("first_install_notification_sent"):
            _LOGGER.debug(
                "First-install notification already sent for %s, skipping",
                entry.entry_id,
            )
            return

        # ── Gather statistics from storage ──────────────────────────────────
        vehicle_name = entry.data.get("vehicle_name", "Vehicle")
        is_german = getattr(hass.config, "language", "en").startswith("de")

        odometer_history = data.get("odometer_history", [])
        odo_count = len(odometer_history)
        last_odo = odometer_history[-1].get("value") if odometer_history else None

        tank_level_history = data.get("tank_level_history", [])
        tank_count = len(tank_level_history)
        last_tank = tank_level_history[-1].get("value") if tank_level_history else None

        refuel_events = len(data.get("refueling_log", []))

        trips = data.get("trips", [])
        # Count by position quality (new field) or derive from coordinates (legacy trips)
        trips_full_pos = sum(
            1 for t in trips
            if t.get("position_quality") == "full"
            or (
                "position_quality" not in t
                and t.get("start_latitude") is not None
                and t.get("end_latitude") is not None
            )
        )
        trips_partial_pos = sum(
            1 for t in trips
            if t.get("position_quality") == "partial"
            or (
                "position_quality" not in t
                and (t.get("start_latitude") is None) != (t.get("end_latitude") is None)
            )
        )
        trips_no_pos = len(trips) - trips_full_pos - trips_partial_pos

        # Weekday names and consumption pattern (0=Monday … 6=Sunday)
        weekday_names = (
            ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
            if is_german
            else ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        )
        weekday_consumption = data.get("weekday_consumption", {})

        # ── Build notification message ───────────────────────────────────────
        # ha_lines uses Markdown (** **) for HA persistent_notification.
        # tg_lines uses HTML (<b></b>) for Telegram (parse_mode="html").
        odo_str = f"{last_odo:.1f} km" if last_odo is not None else "0"
        tank_str = f"{last_tank:.1f}" if last_tank is not None else "0"

        weekday_pattern_lines: list[str] = []
        for day_idx, day_name in enumerate(weekday_names):
            day_data = weekday_consumption.get(str(day_idx), {})
            day_km = day_data.get("km", 0.0)
            day_count = day_data.get("count", 0)
            avg_km = round(day_km / day_count, 1) if day_count > 0 else 0
            weekday_pattern_lines.append(f"   - {day_name}: {avg_km} km")
        weekday_pattern_str = "\n".join(weekday_pattern_lines)

        if is_german:
            ha_message = (
                f"Nach der Erstinstallation für das Fahrzeug **{vehicle_name}** "
                f"wurden folgende Daten wie gewünscht importiert:\n\n"
                f"- Kilometerstand: {odo_str} / {odo_count} Datensätze\n"
                f"- Tanklevel: {tank_str} / {tank_count} Datensätze\n\n"
                "Nach dem Import wurde eine erste Analyse durchgeführt, "
                "dabei konnte folgendes ermittelt werden:\n\n"
                f"- Tankvorgänge: {refuel_events}\n"
                f"- Fahrtenbuch: {trips_full_pos} Trips mit vollständiger Position / "
                f"{trips_partial_pos} Trips mit partieller Position / "
                f"{trips_no_pos} Trips ohne Position\n\n"
                f"Historisches Verbrauchspattern:\n{weekday_pattern_str}\n\n"
                "Ab sofort ermittelt die Integration die Daten zur Laufzeit."
            )
            tg_message = (
                f"Nach der Erstinstallation für das Fahrzeug <b>{vehicle_name}</b> "
                f"wurden folgende Daten wie gewünscht importiert:\n\n"
                f"- Kilometerstand: {odo_str} / {odo_count} Datensätze\n"
                f"- Tanklevel: {tank_str} / {tank_count} Datensätze\n\n"
                "Nach dem Import wurde eine erste Analyse durchgeführt, "
                "dabei konnte folgendes ermittelt werden:\n\n"
                f"- Tankvorgänge: {refuel_events}\n"
                f"- Fahrtenbuch: {trips_full_pos} Trips mit vollständiger Position / "
                f"{trips_partial_pos} Trips mit partieller Position / "
                f"{trips_no_pos} Trips ohne Position\n\n"
                f"Historisches Verbrauchspattern:\n{weekday_pattern_str}\n\n"
                "Ab sofort ermittelt die Integration die Daten zur Laufzeit."
            )
            notification_title = f"haFWCMA – {vehicle_name} Erstinstallation abgeschlossen"
        else:
            ha_message = (
                f"After the initial installation for vehicle **{vehicle_name}** "
                f"the following data was imported as requested:\n\n"
                f"- Odometer: {odo_str} / {odo_count} records\n"
                f"- Tank level: {tank_str} / {tank_count} records\n\n"
                "A first analysis was performed after the import:\n\n"
                f"- Refueling events: {refuel_events}\n"
                f"- Trip log: {trips_full_pos} trips with full position / "
                f"{trips_partial_pos} trips with partial position / "
                f"{trips_no_pos} trips without position\n\n"
                f"Historical consumption pattern:\n{weekday_pattern_str}\n\n"
                "From now on the integration collects data at runtime."
            )
            tg_message = (
                f"After the initial installation for vehicle <b>{vehicle_name}</b> "
                f"the following data was imported as requested:\n\n"
                f"- Odometer: {odo_str} / {odo_count} records\n"
                f"- Tank level: {tank_str} / {tank_count} records\n\n"
                "A first analysis was performed after the import:\n\n"
                f"- Refueling events: {refuel_events}\n"
                f"- Trip log: {trips_full_pos} trips with full position / "
                f"{trips_partial_pos} trips with partial position / "
                f"{trips_no_pos} trips without position\n\n"
                f"Historical consumption pattern:\n{weekday_pattern_str}\n\n"
                "From now on the integration collects data at runtime."
            )
            notification_title = f"haFWCMA – {vehicle_name} first install complete"

        from homeassistant.components import persistent_notification
        persistent_notification.async_create(
            hass,
            ha_message,
            title=notification_title,
            notification_id=f"hafwcma_import_complete_{entry.entry_id}",
        )

        # ── Optional Telegram notification ──────────────────────────────────
        telegram_token = entry.data.get("telegram_token", "")
        telegram_chat_id = entry.data.get("telegram_chat_id", "")
        if telegram_token and telegram_chat_id:
            try:
                from .messaging.telegram import TelegramNotifier

                # Use HTML-formatted message for Telegram (parse_mode="html")
                await TelegramNotifier(
                    bot_token=telegram_token,
                    chat_id=telegram_chat_id,
                    hass=hass,
                ).send_message(tg_message)
                _LOGGER.info("Telegram first-install notification sent for %s", vehicle_name)
            except Exception as tg_err:
                _LOGGER.warning("Could not send Telegram first-install notification: %s", tg_err)

        # ── Mark notification as sent so it is never repeated ───────────────
        data["first_install_notification_sent"] = True
        await storage.save_data(hass, entry, data)
            
    except Exception as err:
        _LOGGER.error("Error during background historical data import: %s", err, exc_info=True)
        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN][entry.entry_id]["historical_import_status"] = "error"


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry to unload
        
    Returns:
        True if unload was successful
    """
    _LOGGER.info("Unloading haFWCMA config entry: %s", entry.entry_id)
    
    # Cleanup Telegram event handler
    telegram_handler = hass.data[DOMAIN][entry.entry_id].get("telegram_handler")
    if telegram_handler:
        await telegram_handler.async_unload()
    
    # Cleanup Telegram refueling handler
    telegram_refueling_handler = hass.data[DOMAIN][entry.entry_id].get("telegram_refueling_handler")
    if telegram_refueling_handler:
        await telegram_refueling_handler.async_unload()
    
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
