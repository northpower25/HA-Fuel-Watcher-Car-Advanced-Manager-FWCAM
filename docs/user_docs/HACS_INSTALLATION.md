# HACS Installation Guide

This repository contains the **Fuel Watcher Car Advanced Manager** integration which includes a built-in frontend card for your dashboard.

## What's Included

When you install this integration via HACS, you get:
1. **FWCAM Integration** - The backend Home Assistant integration
2. **FWCAM Card** - The frontend card (automatically registered)

**Important**: You only need to install the integration. The Lovelace card is automatically bundled with the integration and will be available after installation.

## Prerequisites

- Home Assistant 2023.1.0 or later
- HACS (Home Assistant Community Store) installed

## Installation Steps

### Step 1: Add Custom Repository

1. Open HACS in your Home Assistant
2. Click on **"Integrations"**
3. Click the three dots menu (⋮) in the top right
4. Select **"Custom repositories"**
5. Enter the repository URL:
   ```
   https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM
   ```
6. Select **"Integration"** as the category
7. Click **"Add"**

### Step 2: Install the Integration

1. In HACS Integrations, search for **"Fuel Watcher Car Advanced Manager"**
2. Click on the integration
3. Click **"Download"**
4. Select the latest version
5. Wait for download to complete

### Step 3: Restart Home Assistant

Restart Home Assistant to load the new integration and its frontend card.

### Step 4: Configure the Integration

1. Go to **Settings → Devices & Services**
2. Click **"+ Add Integration"**
3. Search for **"Fuel Watcher Car Advanced Manager"**
4. Follow the configuration wizard

For detailed configuration options, see [INSTALLATION.md](INSTALLATION.md).

### Step 5: Clear Browser Cache

**Important**: After restart, clear your browser cache to ensure the card loads:
- Chrome/Edge: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
- Firefox: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
- Safari: `Cmd+Option+R`

### Step 6: Add Card to Dashboard

The FWCAM card is now automatically available in your Lovelace dashboard:

1. Edit your dashboard
2. Click **"+ Add Card"**
3. Search for **"FWCAM Card"** in the card picker
4. Configure the card:

```yaml
type: custom:fwcam-card
entity: sensor.my_car_refueling_log
```

Replace `my_car` with your vehicle name from the integration setup.

For detailed card configuration, see [Card Configuration](#card-configuration) below.

## Card Configuration

The FWCAM card supports the following configuration options:

```yaml
type: custom:fwcam-card
entity: sensor.my_car_refueling_log  # Required: Your refueling log sensor
title: "My Car Fuel History"          # Optional: Custom title
show_statistics: true                  # Optional: Show statistics panel
max_entries: 10                        # Optional: Maximum entries to display
```

## Troubleshooting

### Card Not Appearing in Card Picker

1. Ensure you restarted Home Assistant after installation
2. Clear your browser cache (hard refresh)
3. Check browser console for errors (F12 → Console)
4. Verify the integration is loaded: Settings → System → Logs

### "Custom element doesn't exist: fwcam-card"

This error means the card JavaScript hasn't loaded:
1. Clear browser cache completely
2. Restart Home Assistant
3. Try a different browser to rule out cache issues
4. Check that the integration is properly installed

### Updates

To update the integration (and card):
1. Go to HACS → Integrations
2. Find "Fuel Watcher Car Advanced Manager"
3. Click "Update" if available
4. Restart Home Assistant
5. Clear browser cache

## Migration from Separate Card Installation

If you previously installed the card separately (using the old dual-repository method):

1. Remove the old card from HACS Frontend (if installed)
2. Remove any manual `frontend.extra_module_url` entries from configuration.yaml
3. Install/update the integration as described above
4. Restart Home Assistant
5. The card will now be provided by the integration

## Support

For issues, feature requests, or questions:
- [GitHub Issues](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)
- [Documentation](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM)
