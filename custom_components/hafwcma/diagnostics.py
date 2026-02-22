"""Diagnostics support for Fuel Watcher Car Advanced Manager (haFWCMA).

Implements the Home Assistant standard diagnostics platform so that users can
download anonymized debug data directly from the device page in the HA UI
(Settings → Devices & Services → [Integration] → device → Download Diagnostics).

The exported data is anonymized using the same ``_Anonymizer`` class that backs
the existing ``export_debug_data`` service, so GPS coordinates are shifted by a
constant random offset and all names / addresses / station IDs are replaced with
stable pseudonyms.  API keys and Telegram credentials are fully redacted.
"""
from __future__ import annotations

import copy
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return anonymized diagnostics for a config entry (all vehicles).

    Called by HA when the user clicks "Download Diagnostics" on the integration
    card in Settings → Devices & Services.
    """
    return await _build_diagnostics(hass, entry)


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device: DeviceEntry,
) -> dict[str, Any]:
    """Return anonymized diagnostics for a specific device (vehicle).

    Called by HA when the user clicks "Download Diagnostics" on a device page.
    Because each config entry maps to exactly one vehicle, this delegates to the
    config-entry level function.
    """
    return await _build_diagnostics(hass, entry)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _build_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Build the anonymized diagnostics payload for *entry*."""
    from .utils.debug_export import _Anonymizer
    from .utils.storage import load_data

    # Resolve app version (reuse the same helper as the service)
    app_version: str = "unknown"
    try:
        from .utils.backup_manager import _get_app_version  # noqa: PLC0415
        app_version = _get_app_version(hass)
    except Exception:  # noqa: BLE001
        pass

    # Resolve HA version
    ha_version: str = "unknown"
    try:
        from homeassistant.const import __version__ as _ha_ver  # noqa: PLC0415
        ha_version = _ha_ver
    except Exception:  # noqa: BLE001
        pass

    # Load raw storage
    try:
        storage_data = await load_data(hass, entry)
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Failed to load storage data for diagnostics: %s", err)
        return {"error": f"Failed to load storage data: {err}"}

    # Anonymize
    anon = _Anonymizer()
    anon_storage = anon.anonymize_storage(storage_data)
    anon_vehicle_name = anon.vehicle(entry.data.get("vehicle_name", entry.entry_id))
    anon_entry_id = anon.entry_id(entry.entry_id)
    anon_config = anon.anon_config(dict(entry.data))

    stats = {
        "trips": len(anon_storage.get("trips", [])),
        "refueling_events": len(anon_storage.get("tank_history", [])),
        "price_history_entries": len(anon_storage.get("price_history", [])),
        "odometer_history_entries": len(anon_storage.get("odometer_history", [])),
        "trip_patterns": len(anon_storage.get("trip_patterns", [])),
        "pois": len(anon_storage.get("pois", [])),
    }

    # Include live coordinator data if available (non-personal, useful for debugging)
    coordinator_snapshot: dict[str, Any] = {}
    try:
        coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
        if coordinator and coordinator.data:
            coordinator_snapshot = _scrub_coordinator_data(coordinator.data)
    except Exception:  # noqa: BLE001
        pass

    return {
        "hafwcma_diagnostics": True,
        "format_version": 1,
        "app_version": app_version,
        "ha_version": ha_version,
        "anonymized": True,
        "anonymization_note": (
            "GPS coordinates have been shifted by a consistent random offset so "
            "relative distances are preserved but absolute locations cannot be "
            "determined. Names, addresses and station information have been "
            "replaced with stable pseudonyms. API keys and credentials have been "
            "redacted. The vehicle owner is solely responsible for reviewing this "
            "file before sharing it."
        ),
        "entry_id": anon_entry_id,
        "vehicle_name": anon_vehicle_name,
        "config": anon_config,
        "stats": stats,
        "storage": anon_storage,
        "coordinator_data": coordinator_snapshot,
    }


def _scrub_coordinator_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of coordinator data with sensitive fields removed.

    Coordinator data contains pre-computed sensor values (prices, distances,
    fuel amounts, timestamps) that are useful for debugging but may include
    station names and addresses.  We keep numeric/boolean/timestamp fields and
    drop free-text name/address fields as a precaution.
    """
    _SENSITIVE_KEYS = frozenset({
        "name", "address", "station_name", "station_address",
        "station_street", "station_city", "station_brand",
        "start_name", "end_name", "start_address", "end_address",
        "location_name",
    })

    def _scrub(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: ("***" if k in _SENSITIVE_KEYS else _scrub(v))
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_scrub(item) for item in obj]
        return obj

    return _scrub(copy.deepcopy(data))
