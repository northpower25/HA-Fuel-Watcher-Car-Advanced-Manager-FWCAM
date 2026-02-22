"""Backup and Restore Manager for haFWCMA.

This module handles creating and restoring data backups for the integration.
The backup includes all user data (refueling events, trips, odometer history, etc.)
along with version metadata to ensure compatibility is checked before restore.

=== DEVELOPER GUIDE: Handling Breaking Changes ===

If you make changes to the storage data model that are NOT backward-compatible
(i.e. an older backup CANNOT be safely restored into the new version), you MUST:

1. Increment ``CURRENT_DATA_MODEL_VERSION`` in this file.

2. Add an entry to ``BREAKING_CHANGES_REGISTRY``:

   .. code-block:: python

       BREAKING_CHANGES_REGISTRY["X.Y.Z"] = {
           "data_model_version": <new CURRENT_DATA_MODEL_VERSION>,
           "description": "Brief user-facing description of what changed.",
           "migration_hint": (
               "What the user can do to migrate an older backup, e.g. "
               "'Export trips via the export_trips service before updating, "
               "then re-import them manually after restore.'"
           ),
       }

   where ``"X.Y.Z"`` is the **app version string** (from ``manifest.json``)
   in which the breaking change was introduced.

A breaking change is any modification to ``utils/storage.py`` where:
- A stored field is **renamed** or **removed**.
- The **type or format** of a stored field changes incompatibly.
- New **required** fields are added that cannot be derived from existing data.
- The **semantics** of an existing field change incompatibly.

NON-breaking changes (no entry needed):
- Adding new optional fields with sensible defaults.
- Adding new data structures alongside existing ones.
- Bug fixes that do not change the storage format.
- Changes to derived/cached data (``trip_statistics``, ``geocoding_cache``,
  ``weekday_consumption``) that are re-computable from raw records.

=== END DEVELOPER GUIDE ===
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Version constants
# ---------------------------------------------------------------------------

# Version of the backup-file envelope itself.
# Increment ONLY when the top-level backup structure changes (not when the
# internal data model changes – use CURRENT_DATA_MODEL_VERSION for that).
BACKUP_FORMAT_VERSION: int = 1

# Current version of the storage data model.
# Increment whenever a breaking change is made to utils/storage.py.
# See the developer guide in this module's docstring for details.
CURRENT_DATA_MODEL_VERSION: int = 1

# ---------------------------------------------------------------------------
# Breaking-changes registry
# ---------------------------------------------------------------------------
# Maps the app version string in which each breaking change was introduced to
# a description and the new data_model_version.
#
# Example (uncomment and adapt when a breaking change is introduced):
#
# BREAKING_CHANGES_REGISTRY: dict[str, dict[str, Any]] = {
#     "0.3.0": {
#         "data_model_version": 2,
#         "description": (
#             "Refueling event structure changed: 'liters_refueled' field "
#             "renamed to 'volume_liters' and 'timestamp' is now stored in UTC."
#         ),
#         "migration_hint": (
#             "Backups created before version 0.3.0 cannot be restored directly. "
#             "Export your refueling events via the 'export_trips' service before "
#             "updating, then re-import them manually after reinstalling."
#         ),
#     },
# }
BREAKING_CHANGES_REGISTRY: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Keys that contain user data and should be included in a backup.
# Keys that are only caches or runtime state are excluded.
# ---------------------------------------------------------------------------
_BACKUP_DATA_KEYS: tuple[str, ...] = (
    # Core fuel data
    "tank_history",
    "refueling_log",
    "odometer_history",
    "tank_level_history",
    "price_history",
    "weekday_consumption",
    "next_refuel_id",
    # Trip log
    "trips",
    "trip_patterns",
    "pois",
    "next_trip_id",
    "next_pattern_id",
    "next_poi_id",
    "trip_tracking_config",
    "trip_statistics",
    # ML / prediction history (user-accumulated, worth preserving)
    "ml_models",
    "prediction_history",
    # Misc state that improves UX after restore
    "last_price",
    "last_price_timestamp",
    "last_fuel_type",
    "last_vehicle_data",
    "last_vehicle_data_refresh",
    "last_historical_import",
    # Geocoding cache (speeds up address display after restore)
    "geocoding_cache",
)


def _get_app_version(hass: HomeAssistant) -> str:
    """Return the current integration version from manifest.json."""
    try:
        manifest_path = Path(__file__).parent.parent / "manifest.json"
        with manifest_path.open(encoding="utf-8") as fh:
            manifest = json.load(fh)
        return manifest.get("version", "unknown")
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Could not read manifest version: %s", err)
        return "unknown"


def _parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a semantic-version string into a comparable tuple.

    Returns (0, 0, 0) for unparsable strings so comparisons are safe.
    """
    try:
        return tuple(int(x) for x in version_str.split(".")[:3])
    except (ValueError, AttributeError):
        return (0, 0, 0)


def get_breaking_changes_between(
    from_version: str, to_version: str
) -> list[dict[str, Any]]:
    """Return breaking changes introduced strictly between *from_version* and *to_version*.

    Args:
        from_version: The app version that created the backup (inclusive lower bound).
        to_version:   The app version that will restore the backup (exclusive upper bound).

    Returns:
        List of breaking-change dicts (may be empty if none exist).
    """
    from_t = _parse_version(from_version)
    to_t = _parse_version(to_version)
    result = []
    for ver, info in BREAKING_CHANGES_REGISTRY.items():
        ver_t = _parse_version(ver)
        # Include changes introduced *after* the backup was made and *up to* the
        # current version (i.e. from_t < ver_t <= to_t).
        if from_t < ver_t <= to_t:
            result.append({"version": ver, **info})
    # Sort chronologically
    result.sort(key=lambda x: _parse_version(x["version"]))
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def create_backup(
    hass: HomeAssistant,
    entry: ConfigEntry,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Create a backup of all user data for a config entry.

    The backup is written as a JSON file to *output_dir* (defaults to
    ``<config_dir>/www/hafwcma_backups/``).

    Args:
        hass:       Home Assistant instance.
        entry:      Config entry whose data should be backed up.
        output_dir: Directory to write the backup file.  Created if missing.

    Returns:
        Dict with keys:
        - ``success`` (bool)
        - ``file_path`` (str) – absolute path of the created file
        - ``backup_data`` (dict) – the full backup payload
        - ``error`` (str, only on failure)
    """
    from .storage import load_data

    app_version = _get_app_version(hass)
    vehicle_name = entry.data.get("vehicle_name", entry.entry_id)

    # Load storage data
    try:
        storage_data = await load_data(hass, entry)
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Failed to load storage data for backup: %s", err)
        return {"success": False, "error": f"Failed to load storage data: {err}"}

    # Extract only user-data keys (skip runtime/cache-only keys that are absent)
    data_snapshot: dict[str, Any] = {}
    for key in _BACKUP_DATA_KEYS:
        if key in storage_data:
            data_snapshot[key] = storage_data[key]

    # Assemble the backup envelope
    created_at = datetime.now(timezone.utc).isoformat()
    backup_payload: dict[str, Any] = {
        "fwcam_backup_format_version": BACKUP_FORMAT_VERSION,
        "data_model_version": CURRENT_DATA_MODEL_VERSION,
        "app_version": app_version,
        "created_at": created_at,
        "entry_id": entry.entry_id,
        "vehicle_name": vehicle_name,
        "data": data_snapshot,
    }

    # Determine output path
    if output_dir is None:
        output_dir = str(Path(hass.config.path("www")) / "hafwcma_backups")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in vehicle_name)
    filename = f"hafwcma_backup_{safe_name}_{ts}.json"
    file_path = Path(output_dir) / filename

    try:
        await hass.async_add_executor_job(
            _write_backup_file, file_path, backup_payload
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Failed to write backup file %s: %s", file_path, err)
        return {
            "success": False,
            "error": f"Failed to write backup file: {err}",
            "backup_data": backup_payload,
        }

    _LOGGER.info(
        "Backup created for entry %s (vehicle: %s, app_version: %s, data_model_version: %d): %s",
        entry.entry_id,
        vehicle_name,
        app_version,
        CURRENT_DATA_MODEL_VERSION,
        file_path,
    )
    return {
        "success": True,
        "file_path": str(file_path),
        "backup_data": backup_payload,
    }


def _write_backup_file(file_path: Path, payload: dict[str, Any]) -> None:
    """Write the backup payload to disk (executor-safe)."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, default=str)


def check_restore_compatibility(
    backup_data: dict[str, Any],
    current_app_version: str,
) -> dict[str, Any]:
    """Check whether *backup_data* can safely be restored to *current_app_version*.

    Args:
        backup_data:          The parsed backup payload (top-level dict).
        current_app_version:  The currently installed app version string.

    Returns:
        Dict with keys:
        - ``compatible`` (bool) – False if hard incompatibility detected.
        - ``has_warnings`` (bool) – True if soft warnings exist.
        - ``breaking_changes`` (list[dict]) – Breaking changes between versions.
        - ``warnings`` (list[str]) – Human-readable warning messages.
        - ``errors`` (list[str]) – Human-readable error messages.
        - ``backup_app_version`` (str)
        - ``backup_data_model_version`` (int)
        - ``current_data_model_version`` (int)
    """
    errors: list[str] = []
    warnings: list[str] = []

    # --- Validate envelope format ---
    fmt_ver = backup_data.get("fwcam_backup_format_version")
    if fmt_ver is None:
        errors.append(
            "This file does not appear to be a valid haFWCMA backup "
            "(missing 'fwcam_backup_format_version')."
        )
        return {
            "compatible": False,
            "has_warnings": False,
            "breaking_changes": [],
            "warnings": warnings,
            "errors": errors,
            "backup_app_version": "unknown",
            "backup_data_model_version": 0,
            "current_data_model_version": CURRENT_DATA_MODEL_VERSION,
        }

    if fmt_ver > BACKUP_FORMAT_VERSION:
        errors.append(
            f"The backup was created with a newer backup format (v{fmt_ver}) "
            f"than this installation supports (v{BACKUP_FORMAT_VERSION}). "
            "Please update haFWCMA before restoring."
        )

    backup_app_version: str = backup_data.get("app_version", "unknown")
    backup_dm_version: int = backup_data.get("data_model_version", 1)

    # --- Check data model version ---
    if backup_dm_version > CURRENT_DATA_MODEL_VERSION:
        errors.append(
            f"The backup was created with a newer data model (v{backup_dm_version}) "
            f"than this installation supports (v{CURRENT_DATA_MODEL_VERSION}). "
            "Please update haFWCMA to the latest version before restoring."
        )

    # --- Check for breaking changes between versions ---
    breaking = get_breaking_changes_between(backup_app_version, current_app_version)

    for change in breaking:
        msg = (
            f"Breaking change in v{change['version']}: {change['description']} "
            f"— {change.get('migration_hint', 'Manual data migration may be required.')}"
        )
        if backup_dm_version < change.get("data_model_version", CURRENT_DATA_MODEL_VERSION):
            errors.append(msg)
        else:
            warnings.append(msg)

    # --- Soft warning: backup is from a different (but older) version ---
    if (
        backup_app_version not in ("unknown", current_app_version)
        and _parse_version(backup_app_version) < _parse_version(current_app_version)
        and not breaking
    ):
        warnings.append(
            f"The backup was created with v{backup_app_version}; "
            f"the current installation is v{current_app_version}. "
            "No breaking changes were detected – restore should work correctly."
        )

    compatible = len(errors) == 0
    return {
        "compatible": compatible,
        "has_warnings": len(warnings) > 0,
        "breaking_changes": breaking,
        "warnings": warnings,
        "errors": errors,
        "backup_app_version": backup_app_version,
        "backup_data_model_version": backup_dm_version,
        "current_data_model_version": CURRENT_DATA_MODEL_VERSION,
    }


async def restore_backup(
    hass: HomeAssistant,
    entry: ConfigEntry,
    backup_file_path: str,
    force: bool = False,
) -> dict[str, Any]:
    """Restore user data from a backup file.

    Args:
        hass:             Home Assistant instance.
        entry:            Config entry to restore data into.
        backup_file_path: Absolute path to the backup JSON file.
        force:            If True, restore even when compatibility warnings exist
                          (but NOT when hard errors are detected).

    Returns:
        Dict with keys:
        - ``success`` (bool)
        - ``compatibility`` (dict) – result of :func:`check_restore_compatibility`
        - ``restored_keys`` (list[str]) – keys that were written to storage
        - ``error`` (str, only on failure)
    """
    from .storage import load_data, save_data

    app_version = _get_app_version(hass)

    # --- Load backup file ---
    try:
        backup_data = await hass.async_add_executor_job(
            _read_backup_file, backup_file_path
        )
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"Backup file not found: {backup_file_path}",
            "compatibility": {},
        }
    except Exception as err:  # noqa: BLE001
        return {
            "success": False,
            "error": f"Failed to read backup file: {err}",
            "compatibility": {},
        }

    # --- Compatibility check ---
    compat = check_restore_compatibility(backup_data, app_version)

    if not compat["compatible"]:
        _LOGGER.error(
            "Backup restore aborted due to compatibility errors: %s",
            compat["errors"],
        )
        return {
            "success": False,
            "error": "Incompatible backup: " + "; ".join(compat["errors"]),
            "compatibility": compat,
        }

    if compat["has_warnings"] and not force:
        _LOGGER.warning(
            "Backup restore proceeding with warnings (force=False): %s",
            compat["warnings"],
        )
        # Soft warnings do NOT block the restore – we proceed but log them.

    # --- Merge backup data into current storage ---
    try:
        current_data = await load_data(hass, entry)
    except Exception as err:  # noqa: BLE001
        return {
            "success": False,
            "error": f"Failed to load current storage data: {err}",
            "compatibility": compat,
        }

    backup_snapshot: dict[str, Any] = backup_data.get("data", {})
    restored_keys: list[str] = []

    for key in _BACKUP_DATA_KEYS:
        if key in backup_snapshot:
            current_data[key] = backup_snapshot[key]
            restored_keys.append(key)

    # Backward-compatibility: backups created before refueling_log was added to
    # _BACKUP_DATA_KEYS only contain tank_history.  Rebuild a minimal refueling_log
    # from tank_history so the FuelLog is not empty after restore.
    if "refueling_log" not in backup_snapshot and current_data.get("tank_history"):
        tank_history: list[dict[str, Any]] = current_data["tank_history"]
        rebuilt: list[dict[str, Any]] = []
        for idx, event in enumerate(tank_history, start=1):
            rebuilt.append(
                {
                    "id": event.get("id", idx),
                    "timestamp": event.get("timestamp"),
                    "odometer_km": event.get("odometer_km"),
                    "station_name": event.get("station_name"),
                    "station_address": event.get("station_address"),
                    "liters_refueled": event.get("liters_refueled"),
                    "price_per_liter": event.get("price_per_liter"),
                    "total_cost": event.get("total_cost"),
                    "latitude": event.get("latitude"),
                    "longitude": event.get("longitude"),
                    "fuel_type": event.get("fuel_type"),
                    "editable": True,
                    "data_quality": event.get("data_quality", "manual"),
                    "confidence": event.get("confidence", 1.0),
                    "excluded_from_calculation": event.get(
                        "excluded_from_calculation", False
                    ),
                    "exclusion_reason": event.get("exclusion_reason"),
                    "telegram_notification_sent": event.get(
                        "telegram_notification_sent", False
                    ),
                    "telegram_notification_timestamp": event.get(
                        "telegram_notification_timestamp"
                    ),
                    "telegram_response_received": event.get(
                        "telegram_response_received", False
                    ),
                    "telegram_response_timestamp": event.get(
                        "telegram_response_timestamp"
                    ),
                    "telegram_response_type": event.get("telegram_response_type"),
                    "telegram_response_raw": event.get("telegram_response_raw"),
                    "telegram_response_parsed": event.get("telegram_response_parsed"),
                    "telegram_photo_file_id": event.get("telegram_photo_file_id"),
                    "telegram_voice_file_id": event.get("telegram_voice_file_id"),
                    "telegram_message_id": event.get("telegram_message_id"),
                }
            )
        current_data["refueling_log"] = rebuilt
        # Ensure next_refuel_id is at least one beyond the highest rebuilt ID
        current_data["next_refuel_id"] = max(
            current_data.get("next_refuel_id", 1), len(rebuilt) + 1
        )
        restored_keys.append("refueling_log")
        _LOGGER.info(
            "Rebuilt refueling_log from tank_history for entry %s (%d entries)",
            entry.entry_id,
            len(rebuilt),
        )

    # Stamp the restore event in the data so it's auditable
    current_data["last_backup_restore"] = {
        "restored_at": datetime.now(timezone.utc).isoformat(),
        "backup_app_version": compat["backup_app_version"],
        "backup_data_model_version": compat["backup_data_model_version"],
        "restored_by_app_version": app_version,
        "backup_file": backup_file_path,
    }

    try:
        await save_data(hass, entry, current_data)
    except Exception as err:  # noqa: BLE001
        return {
            "success": False,
            "error": f"Failed to save restored data: {err}",
            "compatibility": compat,
        }

    _LOGGER.info(
        "Backup restored for entry %s from backup created with v%s. Keys restored: %s",
        entry.entry_id,
        compat["backup_app_version"],
        restored_keys,
    )
    return {
        "success": True,
        "compatibility": compat,
        "restored_keys": restored_keys,
    }


def _read_backup_file(file_path: str) -> dict[str, Any]:
    """Read and parse a backup JSON file (executor-safe)."""
    with open(file_path, encoding="utf-8") as fh:
        return json.load(fh)


async def delete_backup(
    hass: HomeAssistant,
    file_path: str,
    backup_dir: str | None = None,
) -> dict[str, Any]:
    """Delete a backup file from the backup directory.

    Only files that reside inside the standard backup directory (or the
    *backup_dir* override) and match the ``hafwcma_backup_*.json`` naming
    pattern can be deleted.  Attempts to delete files outside that directory
    are rejected to prevent path-traversal attacks.

    Args:
        hass:       Home Assistant instance.
        file_path:  Absolute path to the backup file to delete.
        backup_dir: Override for the backup directory.  Defaults to
                    ``<config_dir>/www/hafwcma_backups/``.

    Returns:
        Dict with keys:
        - ``success`` (bool)
        - ``filename`` (str) – name of the deleted file
        - ``error`` (str, only on failure)
    """
    if backup_dir is None:
        backup_dir = str(Path(hass.config.path("www")) / "hafwcma_backups")

    target = Path(file_path).resolve()
    allowed_dir = Path(backup_dir).resolve()

    # Security: ensure the target is inside the allowed directory
    try:
        target.relative_to(allowed_dir)
    except ValueError:
        return {
            "success": False,
            "error": f"File is not inside the backup directory: {file_path}",
        }

    # Security: only allow files matching the expected naming pattern
    if not target.name.startswith("hafwcma_backup_") or not target.name.endswith(".json"):
        return {
            "success": False,
            "error": "Only hafwcma_backup_*.json files can be deleted via this service.",
        }

    def _delete() -> None:
        target.unlink()

    try:
        await hass.async_add_executor_job(_delete)
    except FileNotFoundError:
        return {"success": False, "error": f"File not found: {file_path}"}
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Failed to delete backup file %s: %s", target, err)
        return {"success": False, "error": f"Failed to delete backup file {target.name}: {err}"}

    _LOGGER.info("Backup file deleted: %s", target)
    return {"success": True, "filename": target.name}


async def list_backups(
    hass: HomeAssistant,
    backup_dir: str | None = None,
) -> list[dict[str, Any]]:
    """List all available backup files in the backup directory.

    Args:
        hass:       Home Assistant instance.
        backup_dir: Directory to scan.  Defaults to the standard backup dir.

    Returns:
        List of dicts with keys:
        - ``filename``       (str)
        - ``file_path``      (str) – absolute path on the server
        - ``download_url``   (str) – relative URL for HA web server
        - ``size_bytes``     (int)
        - ``created_at``     (str) – ISO timestamp from backup metadata
        - ``vehicle_name``   (str)
        - ``app_version``    (str)
        - ``entry_id``       (str)
        - ``data_model_version`` (int)

        Sorted newest-first by ``created_at``.
    """
    if backup_dir is None:
        backup_dir = str(Path(hass.config.path("www")) / "hafwcma_backups")

    def _scan_dir() -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        backup_path = Path(backup_dir)
        if not backup_path.exists():
            return result

        for f in backup_path.glob("hafwcma_backup_*.json"):
            try:
                stat = f.stat()
                try:
                    with f.open(encoding="utf-8") as fh:
                        data = json.load(fh)
                    metadata: dict[str, Any] = {
                        "vehicle_name": data.get("vehicle_name", ""),
                        "app_version": data.get("app_version", ""),
                        "entry_id": data.get("entry_id", ""),
                        "created_at": data.get("created_at", ""),
                        "data_model_version": int(data.get("data_model_version", 1)),
                    }
                except Exception:  # noqa: BLE001
                    metadata = {
                        "vehicle_name": "",
                        "app_version": "",
                        "entry_id": "",
                        "created_at": "",
                        "data_model_version": 1,
                    }

                result.append(
                    {
                        "filename": f.name,
                        "file_path": str(f),
                        "download_url": f"/local/hafwcma_backups/{f.name}",
                        "size_bytes": stat.st_size,
                        **metadata,
                    }
                )
            except Exception:  # noqa: BLE001
                pass

        # Sort newest-first (ISO timestamps compare correctly as strings)
        result.sort(
            key=lambda x: x.get("created_at") or x["filename"], reverse=True
        )
        return result

    return await hass.async_add_executor_job(_scan_dir)
