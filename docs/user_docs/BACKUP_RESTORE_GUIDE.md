# Backup & Restore Guide

This guide explains how to back up and restore your haFWCMA vehicle data.

---

## Overview

haFWCMA stores all your vehicle data (refueling events, trip log, odometer history,
ML models, etc.) in Home Assistant's internal storage. The integration provides two
services to protect this data:

| Service | Purpose |
|---------|---------|
| `hafwcma.create_backup` | Export a snapshot of all data to a JSON file |
| `hafwcma.restore_backup` | Import a previously created snapshot back into the integration |

There is also a **button entity** (`button.<vehicle>_create_backup`) that triggers
`create_backup` with one click from your dashboard or the entity view.

---

## What Is Included in a Backup?

A backup contains all **user-generated data** for one vehicle entry:

- Refueling events and odometer history
- Trip log (trips, patterns, POIs)
- Price history and last-known fuel data
- ML/prediction models
- Geocoding cache (for faster address display after restore)

Runtime caches and sensor state that can be re-computed are **not** included.

---

## Creating a Backup

### Option A – Button entity (easiest)

1. Open Home Assistant → **Entities**.
2. Find `button.<vehicle_name>_create_backup` and press **Activate**.
3. A notification appears in Home Assistant with the download URL, e.g.:
   ```
   /local/hafwcma_backups/hafwcma_backup_MyCar_20260101_120000.json
   ```
4. Open that URL in your browser (`http://homeassistant.local:8123/local/hafwcma_backups/…`)
   to download the file.

### Option B – Service call

1. Go to **Developer Tools → Services**.
2. Select service: `hafwcma.create_backup`.
3. Fill in `config_entry_id` (see [Finding your config_entry_id](#finding-your-config_entry_id)).
4. Click **Call Service**.
5. The HA notification shows the file path and download URL.

The backup file is saved to:
```
/config/www/hafwcma_backups/hafwcma_backup_<vehicle>_<timestamp>.json
```

> 💡 **Tip:** Store backup files outside Home Assistant (e.g. on your PC or cloud
> storage). The `/config/www/hafwcma_backups/` folder is accessible via the HA web
> server but is **not** included in Home Assistant's own backup system.

---

## Restoring a Backup

### Prerequisites

- The backup file must be accessible on the **Home Assistant server** (not just on
  your local PC).
- If you are restoring after a fresh installation, complete the integration setup
  first so that the target `config_entry_id` exists.

### Step-by-step

1. **Upload the backup file to your HA server.**

   Copy the file to `/config/www/hafwcma_backups/` using one of these methods:
   - **File Editor add-on** – upload via the built-in browser
   - **Samba / Network Share** – mount `/config` and copy the file
   - **SSH / Terminal add-on** – `scp` or copy manually

2. **Note the absolute file path**, e.g.:
   ```
   /config/www/hafwcma_backups/hafwcma_backup_MyCar_20260101_120000.json
   ```

3. **Call the restore service.**

   Go to **Developer Tools → Services**, select `hafwcma.restore_backup`, and provide:

   | Field | Value |
   |-------|-------|
   | `config_entry_id` | The entry ID of the vehicle to restore into (see below) |
   | `backup_file_path` | Absolute path to the backup file on the HA server |
   | `force` | `false` (default) – set to `true` only to bypass soft warnings |

4. **Wait for the notification.**

   On success you will see:
   > ✅ Backup restored for **My Car**.
   > Please reload the integration (or restart Home Assistant) to apply the restored data.

5. **Reload the integration.**

   Go to **Settings → Devices & Services**, find haFWCMA, and click **Reload**.
   Alternatively, restart Home Assistant.

---

## Frequently Asked Questions

### Does the restore happen during setup (Config Flow) or later?

Restore happens **after** setup, via the `hafwcma.restore_backup` service. You first
complete the normal setup (Config Flow) so that an entry exists, then call the
restore service to repopulate it with your backed-up data.

### How does the integration know which vehicle to restore data to?

The `config_entry_id` parameter identifies the target vehicle entry. You provide it
when calling the service. The backup file contains the vehicle name and the original
entry ID as metadata, but this is informational only — the restore always writes into
the entry you specify.

### Can I restore into an existing installation with existing data?

Yes. The restore **overwrites** all keys that are present in the backup. Existing data
for those keys is replaced. There is **no deduplication** — if the same refueling
event exists in both the current data and the backup, it will appear only once after
the restore (because the backup data replaces the current data entirely for that key).

### What happens if I reinstall the integration?

After reinstalling haFWCMA:
1. Complete the Config Flow to create a new entry for your vehicle.
2. Copy your backup file to `/config/www/hafwcma_backups/` on the HA server.
3. Call `hafwcma.restore_backup` with the **new** `config_entry_id`.

The integration will restore all your historical data into the new entry.

### What about compatibility between versions?

The backup file includes the haFWCMA version it was created with. When restoring,
the integration automatically checks compatibility:

- **Compatible (possibly with warnings)** – restore proceeds. A warning is shown if
  the backup is from an older version, but no breaking changes were detected.
- **Incompatible (hard error)** – restore is blocked. This happens when a breaking
  change was introduced between the backup version and the current version. The error
  message explains what changed and what you can do.

Set `force: true` only to bypass **soft warnings** (not hard errors).

---

## Finding Your `config_entry_id`

The `config_entry_id` is the unique identifier of your haFWCMA instance for a
specific vehicle. To find it:

1. Go to **Settings → Devices & Services → Integrations**.
2. Click on your haFWCMA integration instance.
3. In the URL bar you will see something like:
   ```
   /config/integrations/integration/hafwcma?config_entry=abc123def456
   ```
   The value after `config_entry=` is your `config_entry_id`.

Alternatively, use the `hafwcma.create_backup` service response — it includes the
`entry_id` field.

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| "Backup file not found" | Check that the file path is correct and that the file is on the **HA server**, not just your local PC. |
| "Incompatible backup" error | Update haFWCMA to the latest version, or follow the migration hint shown in the error. |
| Data not updated after restore | Reload the integration (**Settings → Devices & Services → Reload**) or restart HA. |
| Button entity not visible | Ensure the vehicle entry is loaded. Go to **Settings → Devices & Services** and confirm haFWCMA is running without errors. |

---

## Related

- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Data Storage Documentation](DATA_STORAGE.md)
