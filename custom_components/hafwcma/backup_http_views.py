"""HTTP views for haFWCMA backup operations.

Provides an authenticated REST endpoint that the Lovelace card uses to upload
backup files from the user's local browser to the HA server so they can be
restored via the ``restore_backup`` service.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Maximum size of an uploaded backup file (50 MB)
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class BackupUploadView(HomeAssistantView):
    """Authenticated HTTP endpoint for uploading haFWCMA backup files.

    Accepts a ``multipart/form-data`` POST with a ``file`` field containing
    the backup JSON.  Validates the file, stores it in the standard backup
    directory, and returns the server-side path so the card can trigger
    ``restore_backup``.

    URL:  POST /api/hafwcma/upload_backup
    Auth: Long-lived access token / HA session cookie (``requires_auth=True``)
    """

    url = "/api/hafwcma/upload_backup"
    name = "api:hafwcma:upload_backup"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Handle backup file upload."""
        hass: HomeAssistant = request.app["hass"]

        try:
            reader = await request.multipart()
        except Exception as err:  # noqa: BLE001
            return self.json_message(f"Failed to parse multipart request: {err}", 400)

        try:
            field = await reader.next()
        except Exception as err:  # noqa: BLE001
            return self.json_message(f"Failed to read multipart field: {err}", 400)

        if field is None or field.name != "file":
            return self.json_message(
                "Request must contain a 'file' field in multipart/form-data", 400
            )

        # Stream the file content with a hard size cap
        chunks: list[bytes] = []
        total = 0
        try:
            while True:
                chunk = await field.read_chunk(size=65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_UPLOAD_BYTES:
                    return self.json_message(
                        f"File too large (max {_MAX_UPLOAD_BYTES // 1024 // 1024} MB)",
                        413,
                    )
                chunks.append(chunk)
        except Exception as err:  # noqa: BLE001
            return self.json_message(f"Failed to read uploaded file: {err}", 400)

        content = b"".join(chunks)

        # --- Validate: must be parseable JSON ---
        try:
            backup_data: dict[str, Any] = json.loads(content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as err:
            return self.json_message(f"File is not valid UTF-8 JSON: {err}", 400)

        # --- Validate: must look like a haFWCMA backup ---
        if "fwcam_backup_format_version" not in backup_data:
            return self.json_message(
                "Not a valid haFWCMA backup file (missing 'fwcam_backup_format_version')",
                400,
            )

        # --- Determine a safe filename ---
        original_name: str = getattr(field, "filename", None) or ""
        if original_name:
            safe_name = "".join(
                c if c.isalnum() or c in "-_." else "_" for c in original_name
            )
        else:
            from datetime import datetime, timezone

            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            vehicle = backup_data.get("vehicle_name", "unknown")
            safe_vehicle = "".join(c if c.isalnum() or c in "-_" else "_" for c in vehicle)
            safe_name = f"hafwcma_backup_{safe_vehicle}_{ts}.json"

        if not safe_name.lower().endswith(".json"):
            safe_name += ".json"

        # --- Persist to the standard backup directory ---
        backup_dir = Path(hass.config.path("www")) / "hafwcma_backups"

        def _write() -> str:
            backup_dir.mkdir(parents=True, exist_ok=True)
            target = backup_dir / safe_name
            target.write_bytes(content)
            return str(target)

        try:
            file_path = await hass.async_add_executor_job(_write)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed to write uploaded backup to %s: %s", backup_dir / safe_name, err)
            return self.json_message(f"Failed to save backup file: {err}", 500)

        _LOGGER.info(
            "Backup file uploaded and saved: %s (%d bytes)", file_path, len(content)
        )
        return self.json(
            {
                "success": True,
                "file_path": file_path,
                "filename": safe_name,
                "download_url": f"/local/hafwcma_backups/{safe_name}",
            }
        )
