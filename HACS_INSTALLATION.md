# HACS Installation Guide

This repository contains **two separate components** that can be installed via HACS:

1. **FWCAM Integration** - The backend Home Assistant integration
2. **FWCAM Lovelace Card** - The frontend card for the dashboard

Both can be installed from the same repository but are recognized as separate components by HACS.

## Prerequisites

- Home Assistant 2023.1.0 or later
- HACS (Home Assistant Community Store) installed

## Installing the Integration

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

Restart Home Assistant to load the new integration.

### Step 4: Configure the Integration

1. Go to **Settings → Devices & Services**
2. Click **"+ Add Integration"**
3. Search for **"Fuel Watcher Car Advanced Manager"**
4. Follow the configuration wizard

For detailed configuration options, see [INSTALLATION.md](docs/INSTALLATION.md).

## Installing the Lovelace Card

### Step 1: Add Custom Repository (if not already done)

1. Open HACS in your Home Assistant
2. Click on **"Frontend"**
3. Click the three dots menu (⋮) in the top right
4. Select **"Custom repositories"**
5. Enter the **same repository URL**:
   ```
   https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM
   ```
6. Select **"Lovelace"** as the category
7. Click **"Add"**

### Step 2: Install the Card

1. In HACS Frontend, search for **"FWCAM Lovelace Card"**
2. Click on the card
3. Click **"Download"**
4. Select the latest version
5. Wait for download to complete

### Step 3: Restart Home Assistant

Restart Home Assistant to load the card resources.

### Step 4: Clear Browser Cache

**Important**: After restart, clear your browser cache:
- Chrome/Edge: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
- Firefox: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
- Safari: `Cmd+Option+R`

### Step 5: Add Card to Dashboard

1. Edit your dashboard
2. Click **"+ Add Card"**
3. Search for **"FWCAM Card"** in the card picker
4. Configure the card:

```yaml
type: custom:fwcam-card
entity: sensor.my_car_refueling_log
```

Replace `my_car` with your vehicle name from the integration setup.

For detailed card configuration, see [fwcam-card/README.md](fwcam-card/README.md).

## Troubleshooting

### Integration Not Showing in HACS

- Ensure you selected **"Integration"** as the category
- Refresh HACS
- Check that the repository was added successfully

### Card Not Showing in HACS

- Ensure you selected **"Lovelace"** as the category when adding the repository
- Refresh HACS Frontend section
- Check that the repository was added successfully

### Card Not Loading in Dashboard

- Verify you restarted Home Assistant after installation
- Clear your browser cache (very important!)
- Check browser console for errors (F12)
- Verify the resource is loaded: **Settings → Dashboards → Resources**

### Card Shows "Custom element doesn't exist"

This usually means:
1. Browser cache wasn't cleared - clear it and refresh
2. Resource wasn't loaded - check Resources section
3. Wrong card type - ensure you're using `type: custom:fwcam-card`

## Version Compatibility

Both components (Integration and Card) should be kept at the same version for best compatibility.

When updating:
1. Update the Integration via HACS Integrations
2. Update the Card via HACS Frontend
3. Restart Home Assistant
4. Clear browser cache

## Support

For issues and questions:
- Check [Documentation](docs/)
- Read [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- Open an [Issue](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)

## Benefits of HACS Installation

- ✅ Easy installation and updates
- ✅ Automatic version management
- ✅ Integrated with Home Assistant
- ✅ Community support
- ✅ One-click updates

## Alternative: Manual Installation

If you prefer manual installation or HACS is not available, see:
- Integration: [INSTALLATION.md](docs/INSTALLATION.md#method-2-manual-installation)
- Card: [fwcam-card/README.md](fwcam-card/README.md#manual-installation)
