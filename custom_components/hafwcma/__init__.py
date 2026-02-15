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

# Historical data import configuration
HISTORICAL_IMPORT_STARTUP_DELAY_SECONDS = 10  # Delay before starting background import

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
        
        Returns:
            ServiceResponse dict with keys:
                - location_name (str): Extracted location name (e.g., "Brandenburg Gate")
                - address (str): Full formatted address (e.g., "Unter den Linden, 10117 Berlin")
                - success (bool): True if geocoding succeeded, False otherwise
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
                _LOGGER.debug("Reverse geocode result: name=%s, address=%s", 
                            result.get("location_name"), result.get("address"))
                return {
                    "location_name": result.get("location_name", ""),
                    "address": result.get("address", ""),
                    "success": True,
                }
            else:
                _LOGGER.warning("Reverse geocoding failed for (%.4f, %.4f)", latitude, longitude)
                # Return empty response with generic error
                # Note: Error structure duplicated in except block for clarity
                return {
                    "location_name": "",
                    "address": "",
                    "success": False,
                    "error": "Geocoding failed",
                }
        except Exception as err:
            _LOGGER.error("Error during reverse geocoding: %s", err)
            # Return empty response with specific error
            # Note: Error structure duplicated from else block for clarity in exception handling
            return {
                "location_name": "",
                "address": "",
                "success": False,
                "error": str(err),
            }

    
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
    from .const import CONF_TELEGRAM_CHAT_ID, CONF_TELEGRAM_TOKEN
    from .telegram_handler import TelegramEventHandler
    
    telegram_chat_id = entry.data.get(CONF_TELEGRAM_CHAT_ID)
    telegram_token = entry.data.get(CONF_TELEGRAM_TOKEN)
    
    if telegram_chat_id and telegram_token:
        telegram_handler = TelegramEventHandler(hass, entry, telegram_chat_id)
        await telegram_handler.async_setup()
        hass.data[DOMAIN][entry.entry_id]["telegram_handler"] = telegram_handler
        _LOGGER.info("Telegram event handler initialized for bidirectional communication")
    else:
        _LOGGER.debug("Telegram not configured, skipping event handler setup")
    
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
    Also imports trip history if trip tracking is enabled.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    try:
        from .utils.historical_data_import import import_historical_vehicle_data, import_historical_trip_data
        from .utils import storage
        
        _LOGGER.info("Starting background historical data import")
        
        # Wait to ensure coordinator is fully initialized
        import asyncio
        await asyncio.sleep(HISTORICAL_IMPORT_STARTUP_DELAY_SECONDS)
        
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
        
        # Import trip history if trip tracking is enabled
        data = await storage.load_data(hass, entry)
        trip_config = data.get("trip_tracking_config", {})
        trip_tracking_enabled = trip_config.get("enabled", False)
        
        if trip_tracking_enabled:
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
            _LOGGER.debug("Trip tracking not enabled, skipping trip history import")
            
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
    
    # Cleanup Telegram event handler
    telegram_handler = hass.data[DOMAIN][entry.entry_id].get("telegram_handler")
    if telegram_handler:
        await telegram_handler.async_unload()
    
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
