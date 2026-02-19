# FWCAM Dashboard Installation Guide

This guide explains how to access and set up dashboards for the Fuel Watcher Car Advanced Manager (FWCAM) integration.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Dashboard Types](#dashboard-types)
4. [Installation Methods](#installation-methods)
5. [Customization Guide](#customization-guide)
6. [Troubleshooting](#troubleshooting)
7. [Technical Limitations](#technical-limitations)

---

## Overview

FWCAM provides two ways to access its dashboard:

1. **Automatic Sidebar Panel** *(recommended – zero configuration)*
   - Registers automatically when FWCAM is installed
   - Appears as **"Fuel Watcher"** in the Home Assistant sidebar
   - Auto-discovers all configured vehicles
   - No YAML needed

2. **YAML Dashboard Templates** *(advanced / fallback)*
   - `dashboards/fwcam-overview-dashboard.yaml` – multi-vehicle overview
   - `dashboards/fwcam-vehicle-dashboard-template.yaml` – per-vehicle detail view
   - Full control over layout and entities

## Prerequisites

### Required

- ✅ Home Assistant 2023.7 or newer
- ✅ FWCAM integration installed and configured
- ✅ At least one vehicle (config entry) set up in FWCAM

### Recommended (YAML templates only)

- ✅ Basic knowledge of YAML
- ✅ Access to Home Assistant UI (Settings → Dashboards)

## Dashboard Types

### Automatic Sidebar Panel

**Best for:**
- All users – no setup required
- Quick access from the sidebar
- Single and multi-vehicle setups

**Features:**
- Auto-detects all FWCAM vehicles
- Vehicle tab selector (multi-vehicle)
- Full FWCAM card embedded (refueling log, trip log, vehicle info, settings)
- Updates automatically when vehicles are added or removed

### Overview Dashboard (YAML)

**Best for:**
- Users who need a dedicated multi-vehicle Lovelace dashboard
- Custom layouts with additional HA cards
- Comparison between vehicles, centralized settings

**Features:**
- 5 views: Overview, Fuel Prices, Trips, Settings, Debug
- Grouped vehicle displays, fuel price comparison, combined trip log

### Per-Vehicle Dashboard (YAML)

**Best for:**
- Detailed vehicle management with custom layout
- Statistics and history graphs alongside other HA cards

**Features:**
- 6 views: Overview, Refueling Log, Trip Log, Statistics, Settings, Debug
- Full FWCAM card integration, consumption and price history graphs

## Installation Methods

### ⭐ Method 1: Automatic Sidebar Panel (Recommended)

**This is the easiest method.** No YAML, no manual steps.

1. **Install FWCAM** via Settings → Devices & Services → Add Integration → "Fuel Watcher Car Advanced Manager"
2. **Configure at least one vehicle** during the setup flow
3. **Done!** A **"Fuel Watcher"** entry appears automatically in your Home Assistant sidebar

The panel auto-discovers all your FWCAM vehicles and shows a tab for each one (if you have multiple vehicles). The full `fwcam-card` is embedded, giving you access to the refueling log, trip log, vehicle info, controls, and settings – all without any manual configuration.

> **Note:** If the sidebar entry does not appear, restart Home Assistant once after completing the FWCAM setup.

---

### Method 2: Manual YAML Dashboard

Use this if you want a dedicated Lovelace dashboard with a custom layout or additional cards.

#### Step-by-Step Instructions:

1. **Navigate to Dashboards**
   - Open Home Assistant
   - Go to **Settings** → **Dashboards**

2. **Create New Dashboard**
   - Click the **"+ ADD DASHBOARD"** button (bottom right)
   - Select **"New dashboard from scratch"**

3. **Configure Dashboard**
   - **Title**: Enter a name (e.g., "Fuel Watcher Overview" or "My Car Dashboard")
   - **Icon**: Choose an icon (e.g., `mdi:car` or `mdi:gas-station`)
   - **Sidebar**: Check "Show in sidebar" if you want quick access
   - Click **"CREATE"**

4. **Enter Edit Mode**
   - On your new dashboard, click the **three dots menu** (⋮) in the top right
   - Select **"Edit Dashboard"**

5. **Open Raw Configuration Editor**
   - Click the **three dots menu** (⋮) again
   - Select **"Raw configuration editor"**

6. **Paste Dashboard Configuration**
   - **For Overview Dashboard:**
     - Open `dashboards/fwcam-overview-dashboard.yaml`
     - Copy the entire content
     - Paste into the editor
   - **For Per-Vehicle Dashboard:**
     - Open `dashboards/fwcam-vehicle-dashboard-template.yaml`
     - Copy the entire content
     - Paste into the editor

7. **Customize Entity Names**
   - Press `Ctrl+F` (or `Cmd+F` on Mac) to find
   - Search for `YOUR_CAR_NAME`
   - Replace ALL instances with your actual vehicle name
     - Example: If your car is named "vw_golf", replace `YOUR_CAR_NAME` with `vw_golf`
     - This will change `sensor.YOUR_CAR_NAME_fuel_price` to `sensor.vw_golf_fuel_price`
   - **Important:** Make sure to replace ALL occurrences!

8. **Save Configuration**
   - Click **"SAVE"** button
   - If there are YAML errors, they will be highlighted
   - Fix any errors and save again

9. **Exit Edit Mode**
   - Click **"DONE"** to exit edit mode
   - Your new dashboard is now live! 🎉

### Method 3: UI-Based Dashboard Creation

For users who prefer a graphical interface without copy-pasting YAML:

1. **Create New Dashboard**
   - Go to **Settings** → **Dashboards**
   - Click **"+ ADD DASHBOARD"**
   - Select **"New dashboard from scratch"**

2. **Add Views Manually**
   - Click **"Edit Dashboard"**
   - Add views (tabs) using the UI
   - Add cards by clicking "+ ADD CARD"

3. **Add FWCAM Card**
   - Search for "FWCAM Card" in the card picker
   - Configure using the visual editor
   - Add entity IDs manually

4. **Add Other Cards**
   - Use entity cards, gauge cards, markdown cards, etc.
   - Reference the YAML templates for inspiration

**Note:** This method is more time-consuming but doesn't require YAML knowledge.

## Customization Guide

### Finding Your Vehicle Entity Names

Your vehicle entity names are derived from the vehicle name you entered during setup.

**Example:**
- Vehicle name in config: "My VW Golf"
- Entity prefix: `vw_golf`
- Entities will be: `sensor.vw_golf_fuel_price`, `sensor.vw_golf_tank_level`, etc.

**How to find your exact entity names:**

1. Go to **Developer Tools** → **States**
2. Search for `sensor.` and filter by your integration
3. Look for entities containing your vehicle name
4. Note the exact entity ID format

### Common Customizations

#### Changing Gauge Ranges

In the vehicle dashboard, gauges have min/max values. Adjust these for your vehicle:

```yaml
- type: gauge
  entity: sensor.YOUR_CAR_NAME_tank_level
  min: 0
  max: 100
  severity:
    green: 50
    yellow: 25
    red: 0
```

**Customizations:**
- `max: 100` - Maximum value (e.g., tank capacity in %)
- `green: 50` - Threshold for green color
- `yellow: 25` - Threshold for yellow color
- `red: 0` - Threshold for red color

#### Adjusting History Graph Time Ranges

```yaml
- type: history-graph
  title: Fuel Price History
  hours_to_show: 168  # Change this number
  entities:
    - entity: sensor.YOUR_CAR_NAME_fuel_price
```

**Common values:**
- `24` - Last 24 hours
- `168` - Last week (7 days)
- `720` - Last month (30 days)
- `8760` - Last year (365 days)

#### Adding Multiple Vehicles to Overview Dashboard

To add a second vehicle to the overview dashboard:

1. Find the "Vehicle 1 Section" in the YAML
2. Copy the entire `- type: vertical-stack` block
3. Paste it below the first vehicle section
4. Replace `YOUR_CAR_NAME` with your second vehicle's name
5. Update the title to "Vehicle 2"

#### Customizing FWCAM Card Display

The FWCAM custom card has many configuration options:

```yaml
- type: custom:fwcam-card
  entity: sensor.YOUR_CAR_NAME_refueling_log
  title: My Custom Title
  show_refueling_log: true    # Show/hide refueling section
  show_trip_log: true          # Show/hide trip section
  show_vehicle_info: true      # Show/hide vehicle info
  show_controls: true          # Show/hide control buttons
  show_settings: true          # Show/hide settings
  rows_per_page: 10            # Pagination size
  table_max_height: 400px      # Table height
  refresh_interval: 300        # Refresh throttle (seconds)
```

**Use cases:**
- **Refueling-only view**: Set only `show_refueling_log: true`
- **Trip-only view**: Set only `show_trip_log: true`
- **Settings-only view**: Set only `show_settings: true`

### Color Scheme Customization

To match your Home Assistant theme, modify the markdown cards and severity levels:

```yaml
severity:
  green: 50
  yellow: 25
  red: 0
```

Or use custom colors in conditional formatting:

```yaml
{% if urgency == 'critical' %}
🔴 **CRITICAL**
{% elif urgency == 'high' %}
🟠 **HIGH**
{% endif %}
```

## Troubleshooting

### Dashboard Shows "Entity not found"

**Problem:** Entities display as "unavailable" or "entity not found"

**Solutions:**
1. Verify entity names in **Developer Tools** → **States**
2. Check that you replaced ALL instances of `YOUR_CAR_NAME`
3. Ensure FWCAM integration is properly set up
4. Restart Home Assistant if entities were just created

### FWCAM Card Not Found

**Problem:** "Custom element doesn't exist: fwcam-card"

**Solutions:**
1. Verify `fwcam-card.js` is in `/config/www/` or `/config/custom_components/hafwcma/www/`
2. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
3. Check browser console for JavaScript errors
4. Verify the card is registered in Home Assistant resources

### YAML Errors When Saving

**Problem:** "Invalid YAML" or syntax errors when saving dashboard

**Solutions:**
1. Use a YAML validator (https://www.yamllint.com/)
2. Check indentation - YAML requires consistent spacing
3. Ensure no tabs are used (only spaces)
4. Verify all brackets and quotes are closed
5. Look for special characters that need escaping

### Graphs Not Showing Data

**Problem:** History graphs are empty

**Solutions:**
1. Wait for data to accumulate (entities need time to record history)
2. Verify Home Assistant Recorder is enabled
3. Check `hours_to_show` value - try smaller values first
4. Ensure entities are actually updating (check **Developer Tools** → **States**)

### Markdown Templates Not Rendering

**Problem:** `{% %}` visible in markdown cards instead of values

**Solutions:**
1. Verify Home Assistant version supports Jinja templates in markdown
2. Check entity availability
3. Use default filters: `| default('N/A')`
4. Test template in **Developer Tools** → **Template**

### Mobile Display Issues

**Problem:** Dashboard doesn't look good on mobile

**Solutions:**
1. Use `horizontal-stack` sparingly on mobile
2. Consider creating a mobile-specific view
3. Test on actual mobile device, not just browser responsive mode
4. Use Home Assistant Companion App settings to adjust

## Technical Limitations

### Why No Auto-Dashboard Creation?

**Important:** Home Assistant does **NOT** officially support programmatic dashboard creation from custom integrations.

**Reasons:**
1. **Security**: `.storage/lovelace` files are internal to HA core
2. **Stability**: Manual modification can cause data corruption
3. **Architecture**: Dashboards are user-managed, not integration-managed
4. **Updates**: Changes could break with HA version updates

**Our Approach:**
- ✅ Provide comprehensive YAML templates
- ✅ Detailed installation instructions
- ✅ Easy customization guides
- ✅ Example configurations
- ✅ Best practices following HA guidelines

This approach is used by professional integrations like:
- **Frigate NVR**
- **ESPHome**
- **Zigbee2MQTT**
- **Node-RED**

### Dashboard Import Limitations

Home Assistant currently does not support:
- ❌ Dashboard import from files via UI
- ❌ Blueprint-style dashboard templates
- ❌ Automatic dashboard creation on integration install
- ❌ Dashboard sharing marketplace

**Workarounds:**
- ✅ Manual copy-paste from YAML templates (this guide)
- ✅ Community sharing via GitHub/forums
- ✅ Documentation with screenshots and examples

## Additional Resources

### Documentation
- [FWCAM Entity Documentation](../docs/ENTITIES.md)
- [Refueling Log Guide](../docs/user_docs/REFUELING_LOG_GUIDE.md)
- [Home Assistant Dashboard Documentation](https://www.home-assistant.io/dashboards/)

### Support
- [GitHub Issues](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)
- [Home Assistant Community Forum](https://community.home-assistant.io/)

### Example Configurations
- See `dashboards/` directory for template files
- Check GitHub for community-shared configurations

---

## Quick Start Checklist

- [ ] Prerequisites met (HA 2023.7+, FWCAM installed)
- [ ] Vehicle configured in FWCAM
- [ ] Entity names identified
- [ ] Dashboard template selected (Overview or Per-Vehicle)
- [ ] New dashboard created in Home Assistant
- [ ] YAML template copied and pasted
- [ ] Entity names customized (replaced `YOUR_CAR_NAME`)
- [ ] Configuration saved successfully
- [ ] Dashboard tested and working
- [ ] Customizations applied (optional)
- [ ] Mobile view verified (optional)

---

**Need help?** Open an issue on GitHub or ask in the Home Assistant community forums!

**Want to share your dashboard?** Create a discussion on GitHub to share your customized configuration with the community!
