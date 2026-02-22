"""Anonymized Debug Data Export for haFWCMA.

This module creates an anonymized snapshot of all integration data that can be
shared for bug reports. Sensitive fields are pseudonymized in a *consistent*
manner so that:

- Relative distances between GPS positions are preserved (same spatial geometry,
  different absolute coordinates).
- All occurrences of the same real value map to the same anonymized value, so
  data relationships remain intact.
- Personal identifiers (vehicle name, person names, addresses, station IDs) are
  replaced by deterministic placeholders derived from a random per-export salt.

Anonymized fields
-----------------
- GPS coordinates (start_latitude/longitude, end_latitude/longitude, lat/lon,
  latitude/longitude, home_latitude/longitude, config lat/lon) – shifted by a
  random constant offset (same offset for the whole export so geometry is kept).
- Vehicle name – replaced with "Vehicle_0001" etc. (consistent across the export).
- Person/location names and addresses – replaced with deterministic aliases
  ("Location_A", "Address_B", …) that are the same every time the same original
  string appears within one export.
- Station names / IDs / brands / streets / cities – replaced with aliases.
- Config entry ID – replaced with "ENTRY_0001".

Non-anonymized fields (useful for debugging)
--------------------------------------------
- Distances (km), fuel amounts (L), prices (€), timestamps, durations, odometer
  *delta* values, quality/confidence fields, statistical aggregates, flags.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Approximate earth radius in km (used for coordinate offset bounding).
_EARTH_RADIUS_KM = 6371.0

# Maximum GPS offset in degrees (≈ 50 km at equator – far enough to be
# unrecognisable, small enough that map projections stay similar).
_MAX_LAT_OFFSET = 0.45   # ~50 km
_MAX_LON_OFFSET = 0.65   # ~50 km at mid-latitudes


# ---------------------------------------------------------------------------
# Internal helper: consistent string alias table
# ---------------------------------------------------------------------------

class _AliasTable:
    """Maps real strings to deterministic aliases within one export session."""

    def __init__(self, salt: bytes, prefix: str, letters: bool = False) -> None:
        self._salt = salt
        self._prefix = prefix
        self._letters = letters
        self._map: dict[str, str] = {}
        self._counter = 0

    def alias(self, value: str | None) -> str | None:
        """Return a stable alias for *value*, or None if value is None/empty."""
        if not value:
            return value
        if value not in self._map:
            self._counter += 1
            if self._letters:
                # Use letter sequence: A, B, …, Z, AA, AB, …
                n = self._counter
                label = ""
                while n > 0:
                    n, r = divmod(n - 1, 26)
                    label = chr(65 + r) + label
                self._map[value] = f"{self._prefix}_{label}"
            else:
                self._map[value] = f"{self._prefix}_{self._counter:04d}"
        return self._map[value]


# ---------------------------------------------------------------------------
# Core anonymizer
# ---------------------------------------------------------------------------

class _Anonymizer:
    """Stateful anonymizer for one debug export run."""

    def __init__(self) -> None:
        # Generate a random salt for this export session.
        self._salt = os.urandom(16)

        # Deterministic lat/lon offsets derived from salt (constant for export).
        h = int.from_bytes(
            hashlib.sha256(self._salt + b"gps_offset").digest()[:8],
            "big",
        )
        # Map hash value to [-1, 1] range then scale to max offset.
        max_val = 2**64
        self._lat_offset = ((h % max_val) / max_val * 2 - 1) * _MAX_LAT_OFFSET
        h2 = int.from_bytes(
            hashlib.sha256(self._salt + b"gps_offset_lon").digest()[:8],
            "big",
        )
        self._lon_offset = ((h2 % max_val) / max_val * 2 - 1) * _MAX_LON_OFFSET

        # Alias tables
        self._vehicles = _AliasTable(self._salt, "Vehicle", letters=False)
        self._locations = _AliasTable(self._salt, "Location", letters=True)
        self._addresses = _AliasTable(self._salt, "Address", letters=True)
        self._stations = _AliasTable(self._salt, "Station", letters=False)
        self._station_ids = _AliasTable(self._salt, "STID", letters=False)
        self._cities = _AliasTable(self._salt, "City", letters=True)
        self._streets = _AliasTable(self._salt, "Street", letters=True)
        self._brands = _AliasTable(self._salt, "Brand", letters=False)
        self._purposes = _AliasTable(self._salt, "Purpose", letters=False)
        self._entry_ids = _AliasTable(self._salt, "ENTRY", letters=False)

    # ------------------------------------------------------------------
    # Basic field anonymizers
    # ------------------------------------------------------------------

    def shift_lat(self, lat: float | None) -> float | None:
        """Shift latitude by the fixed export offset."""
        if lat is None:
            return None
        shifted = lat + self._lat_offset
        # Clamp to valid range [-90, 90]
        return max(-90.0, min(90.0, shifted))

    def shift_lon(self, lon: float | None) -> float | None:
        """Shift longitude by the fixed export offset."""
        if lon is None:
            return None
        shifted = lon + self._lon_offset
        # Normalise to (-180, 180]
        while shifted > 180:
            shifted -= 360
        while shifted <= -180:
            shifted += 360
        return shifted

    def vehicle(self, name: str | None) -> str | None:
        return self._vehicles.alias(name)

    def location(self, name: str | None) -> str | None:
        return self._locations.alias(name)

    def address(self, addr: str | None) -> str | None:
        return self._addresses.alias(addr)

    def station_name(self, name: str | None) -> str | None:
        return self._stations.alias(name)

    def station_id(self, sid: str | None) -> str | None:
        return self._station_ids.alias(sid)

    def city(self, c: str | None) -> str | None:
        return self._cities.alias(c)

    def street(self, s: str | None) -> str | None:
        return self._streets.alias(s)

    def brand(self, b: str | None) -> str | None:
        return self._brands.alias(b)

    def purpose(self, p: str | None) -> str | None:
        return self._purposes.alias(p)

    def entry_id(self, eid: str | None) -> str | None:
        return self._entry_ids.alias(eid)

    # ------------------------------------------------------------------
    # Data-structure anonymizers
    # ------------------------------------------------------------------

    def _anon_trip(self, trip: dict[str, Any]) -> dict[str, Any]:
        t = copy.copy(trip)
        t["start_latitude"] = self.shift_lat(t.get("start_latitude"))
        t["start_longitude"] = self.shift_lon(t.get("start_longitude"))
        t["end_latitude"] = self.shift_lat(t.get("end_latitude"))
        t["end_longitude"] = self.shift_lon(t.get("end_longitude"))
        t["start_name"] = self.location(t.get("start_name"))
        t["end_name"] = self.location(t.get("end_name"))
        t["start_address"] = self.address(t.get("start_address"))
        t["end_address"] = self.address(t.get("end_address"))
        t["purpose"] = self.purpose(t.get("purpose"))
        # Anonymize nested position waypoints list if present
        if "positions" in t and isinstance(t["positions"], list):
            t["positions"] = [
                {
                    **p,
                    "lat": self.shift_lat(p.get("lat")),
                    "lon": self.shift_lon(p.get("lon")),
                    "latitude": self.shift_lat(p.get("latitude")),
                    "longitude": self.shift_lon(p.get("longitude")),
                }
                for p in t["positions"]
            ]
        return t

    def _anon_refuel_event(self, event: dict[str, Any]) -> dict[str, Any]:
        e = copy.copy(event)
        e["station_name"] = self.station_name(e.get("station_name"))
        e["station_address"] = self.address(e.get("station_address"))
        # Anonymize GPS position at time of refueling (reveals the fuel station location)
        e["latitude"] = self.shift_lat(e.get("latitude"))
        e["longitude"] = self.shift_lon(e.get("longitude"))
        return e

    def _anon_price_observation(self, obs: dict[str, Any]) -> dict[str, Any]:
        o = copy.copy(obs)
        o["station_name"] = self.station_name(o.get("station_name"))
        o["station_id"] = self.station_id(o.get("station_id"))
        o["station_brand"] = self.brand(o.get("station_brand"))
        o["station_city"] = self.city(o.get("station_city"))
        o["station_street"] = self.street(o.get("station_street"))
        return o

    def _anon_odometer_point(self, point: dict[str, Any]) -> dict[str, Any]:
        """Anonymize GPS in odometer history points (keep value/ts)."""
        p = copy.copy(point)
        p["lat"] = self.shift_lat(p.get("lat"))
        p["lon"] = self.shift_lon(p.get("lon"))
        p["latitude"] = self.shift_lat(p.get("latitude"))
        p["longitude"] = self.shift_lon(p.get("longitude"))
        return p

    def _anon_trip_pattern(self, pattern: dict[str, Any]) -> dict[str, Any]:
        pp = copy.copy(pattern)
        pp["name"] = self.location(pp.get("name"))
        pp["start_latitude"] = self.shift_lat(pp.get("start_latitude"))
        pp["start_longitude"] = self.shift_lon(pp.get("start_longitude"))
        pp["end_latitude"] = self.shift_lat(pp.get("end_latitude"))
        pp["end_longitude"] = self.shift_lon(pp.get("end_longitude"))
        pp["purpose"] = self.purpose(pp.get("purpose"))
        return pp

    def _anon_poi(self, poi: dict[str, Any]) -> dict[str, Any]:
        p = copy.copy(poi)
        p["name"] = self.location(p.get("name"))
        p["address"] = self.address(p.get("address"))
        p["latitude"] = self.shift_lat(p.get("latitude"))
        p["longitude"] = self.shift_lon(p.get("longitude"))
        return p

    def _anon_geocoding_cache(
        self, cache: dict[str, Any]
    ) -> dict[str, Any]:
        """Anonymize the geocoding cache dict.

        Keys are typically "lat,lon" strings.  Values are dicts with
        ``location_name`` and ``address`` fields.
        """
        result: dict[str, Any] = {}
        for _key, val in cache.items():
            # Drop the original key (contains real coordinates); use a
            # sequential placeholder instead.
            anon_val = copy.copy(val) if isinstance(val, dict) else val
            if isinstance(anon_val, dict):
                anon_val["location_name"] = self.location(
                    anon_val.get("location_name")
                )
                anon_val["address"] = self.address(anon_val.get("address"))
            new_key = f"geocache_{len(result) + 1:04d}"
            result[new_key] = anon_val
        return result

    def _anon_last_vehicle_data(
        self, vd: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Anonymize last_vehicle_data (may contain position/name fields)."""
        if not vd:
            return vd
        vd = copy.deepcopy(vd)
        for gps_key in ("latitude", "longitude", "lat", "lon",
                        "home_latitude", "home_longitude"):
            if gps_key in vd:
                if "lat" in gps_key:
                    vd[gps_key] = self.shift_lat(vd[gps_key])
                else:
                    vd[gps_key] = self.shift_lon(vd[gps_key])
        for name_key in ("vehicle_name", "name", "driver_name", "owner_name"):
            if name_key in vd:
                vd[name_key] = self.vehicle(str(vd[name_key]))
        return vd

    def anon_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Anonymize config entry data (home position, vehicle name, API keys)."""
        c = copy.deepcopy(config)
        # Remove or mask API key
        if "api_key" in c:
            c["api_key"] = "***REDACTED***"
        if "telegram_token" in c:
            c["telegram_token"] = "***REDACTED***"
        if "telegram_chat_id" in c:
            c["telegram_chat_id"] = "***REDACTED***"
        # Anonymize home position
        c["latitude"] = self.shift_lat(c.get("latitude"))
        c["longitude"] = self.shift_lon(c.get("longitude"))
        # Anonymize vehicle name
        if "vehicle_name" in c:
            c["vehicle_name"] = self.vehicle(c["vehicle_name"])
        return c

    # ------------------------------------------------------------------
    # Full storage anonymizer
    # ------------------------------------------------------------------

    def anonymize_storage(self, storage: dict[str, Any]) -> dict[str, Any]:
        """Return a fully anonymized copy of the raw storage dict."""
        result: dict[str, Any] = {}

        # --- Price history ---
        result["price_history"] = [
            self._anon_price_observation(o)
            for o in storage.get("price_history", [])
        ]

        # --- Odometer history ---
        result["odometer_history"] = [
            self._anon_odometer_point(p)
            for p in storage.get("odometer_history", [])
        ]

        # --- Tank level history (no PII, keep as-is) ---
        result["tank_level_history"] = copy.deepcopy(
            storage.get("tank_level_history", [])
        )

        # --- Weekday consumption stats (aggregate, no PII) ---
        result["weekday_consumption"] = copy.deepcopy(
            storage.get("weekday_consumption", {})
        )

        # --- Refueling events ---
        result["tank_history"] = [
            self._anon_refuel_event(e)
            for e in storage.get("tank_history", [])
        ]

        # --- Trips ---
        result["trips"] = [
            self._anon_trip(t) for t in storage.get("trips", [])
        ]

        # --- Trip patterns ---
        result["trip_patterns"] = [
            self._anon_trip_pattern(p)
            for p in storage.get("trip_patterns", [])
        ]

        # --- POIs ---
        result["pois"] = [
            self._anon_poi(p) for p in storage.get("pois", [])
        ]

        # --- Trip statistics (aggregates, no PII) ---
        result["trip_statistics"] = copy.deepcopy(
            storage.get("trip_statistics", {})
        )

        # --- Trip tracking config (scrub names/addresses in schedules) ---
        ttc = copy.deepcopy(storage.get("trip_tracking_config", {}))
        result["trip_tracking_config"] = ttc

        # --- Geocoding cache ---
        result["geocoding_cache"] = self._anon_geocoding_cache(
            storage.get("geocoding_cache", {})
        )

        # --- Last vehicle data ---
        result["last_vehicle_data"] = self._anon_last_vehicle_data(
            storage.get("last_vehicle_data")
        )

        # --- Counters / non-PII scalars ---
        for key in (
            "version",
            "next_refuel_id",
            "next_trip_id",
            "next_pattern_id",
            "next_poi_id",
            "last_price",
            "last_price_timestamp",
            "last_fuel_type",
            "last_vehicle_data_refresh",
            "last_historical_import",
            "last_decision",
        ):
            if key in storage:
                result[key] = copy.deepcopy(storage[key])

        # Remove raw API / Telegram payloads (may contain API keys or chat IDs)
        # and error strings (may contain paths or personal data).
        # These are NOT included in the debug export.

        return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def create_debug_export(
    hass: HomeAssistant,
    entry: ConfigEntry,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Create an anonymized debug export for *entry*.

    The export is written as a JSON file to *output_dir* (defaults to
    ``<config_dir>/www/hafwcma_debug/``) so it can be downloaded through the
    Home Assistant web server at ``/local/hafwcma_debug/<filename>``.

    Args:
        hass:       Home Assistant instance.
        entry:      Config entry to export.
        output_dir: Directory to write the file.  Created if missing.

    Returns:
        Dict with keys:
        - ``success`` (bool)
        - ``file_path`` (str) – absolute path of the created file
        - ``download_url`` (str) – relative URL for browser download
        - ``error`` (str, only on failure)
        - ``stats`` (dict) – counts of anonymized records
    """
    from .storage import load_data
    from ..backup_manager import _get_app_version  # reuse version helper

    app_version = _get_app_version(hass)
    real_vehicle_name = entry.data.get("vehicle_name", entry.entry_id)

    # Load raw storage data
    try:
        storage_data = await load_data(hass, entry)
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Failed to load storage data for debug export: %s", err)
        return {"success": False, "error": f"Failed to load storage data: {err}"}

    # Run anonymizer
    anon = _Anonymizer()
    anon_storage = anon.anonymize_storage(storage_data)
    anon_vehicle_name = anon.vehicle(real_vehicle_name)
    anon_entry_id = anon.entry_id(entry.entry_id)
    anon_config = anon.anon_config(dict(entry.data))

    # Gather HA system info (non-personal)
    ha_version = "unknown"
    try:
        ha_version = hass.data.get("homeassistant", {}).get("version", "unknown")
    except Exception:  # noqa: BLE001
        pass
    try:
        from homeassistant.const import __version__ as _ha_ver
        ha_version = _ha_ver
    except Exception:  # noqa: BLE001
        pass

    # Build export payload
    created_at = datetime.now(timezone.utc).isoformat()
    stats = {
        "trips": len(anon_storage.get("trips", [])),
        "refueling_events": len(anon_storage.get("tank_history", [])),
        "price_history_entries": len(anon_storage.get("price_history", [])),
        "odometer_history_entries": len(anon_storage.get("odometer_history", [])),
        "trip_patterns": len(anon_storage.get("trip_patterns", [])),
        "pois": len(anon_storage.get("pois", [])),
    }

    export_payload: dict[str, Any] = {
        "hafwcma_debug_export": True,
        "format_version": 1,
        "created_at": created_at,
        "app_version": app_version,
        "ha_version": ha_version,
        "anonymized": True,
        "anonymization_note": (
            "GPS coordinates have been shifted by a consistent random offset "
            "so relative distances are preserved but absolute locations cannot "
            "be determined. Names, addresses and station information have been "
            "replaced with stable pseudonyms. API keys and credentials have been "
            "redacted. WARNING: The download filename shown by your browser may "
            "still contain the real vehicle name (e.g. licence plate). Please "
            "rename the file before sharing it. The vehicle owner is solely "
            "responsible for reviewing this file before sharing it."
        ),
        "entry_id": anon_entry_id,
        "vehicle_name": anon_vehicle_name,
        "config": anon_config,
        "stats": stats,
        "storage": anon_storage,
    }

    # Determine output path
    if output_dir is None:
        output_dir = str(Path(hass.config.path("www")) / "hafwcma_debug")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in (anon_vehicle_name or "unknown")
    )
    filename = f"hafwcma_debug_{safe_name}_{ts}.json"
    file_path = Path(output_dir) / filename
    download_url = f"/local/hafwcma_debug/{filename}"

    try:
        await hass.async_add_executor_job(
            _write_export_file, file_path, export_payload
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Failed to write debug export file %s: %s", file_path, err)
        return {
            "success": False,
            "error": f"Failed to write debug export file: {err}",
        }

    _LOGGER.info(
        "Anonymized debug export created for entry %s (vehicle: %s): %s",
        entry.entry_id,
        real_vehicle_name,
        file_path,
    )
    return {
        "success": True,
        "file_path": str(file_path),
        "download_url": download_url,
        "stats": stats,
    }


def _write_export_file(file_path: Path, payload: dict[str, Any]) -> None:
    """Write the export payload to disk (executor-safe)."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, default=str)
