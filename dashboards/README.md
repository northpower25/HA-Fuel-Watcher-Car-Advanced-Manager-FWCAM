# FWCAM Dashboard Templates

Welcome to the FWCAM dashboard templates directory! This directory contains ready-to-use Lovelace dashboard configurations for the Fuel Watcher Car Advanced Manager integration.

## 📁 Available Templates

### 1. Overview Dashboard (`fwcam-overview-dashboard.yaml`)

A multi-vehicle dashboard providing a comprehensive overview of all your vehicles.

**Features:**
- 📊 Overview page with all vehicles grouped
- ⛽ Fuel price comparison view
- 🗺️ Combined trip log view
- ⚙️ Centralized settings management
- 🐛 Debug information for troubleshooting

**Best for:**
- Users with multiple vehicles
- Quick comparison between vehicles
- Central configuration management

**Views:**
1. **Overview** - All vehicles at a glance
2. **Fuel Prices** - Price comparison and history
3. **Trip Logs** - All trip data
4. **Settings** - Integration configuration
5. **Debug** - Technical information

### 2. Per-Vehicle Dashboard (`fwcam-vehicle-dashboard-template.yaml`)

A detailed dashboard template for a single vehicle with the full FWCAM custom card.

**Features:**
- 🚗 Comprehensive vehicle overview with gauges
- ⛽ Full refueling log management via FWCAM card
- 🗺️ Trip log with categorization and geocoding
- 📈 Statistical analysis and trend graphs
- ⚙️ Complete settings and controls
- 🐛 Debug information

**Best for:**
- Single-vehicle detailed management
- Frequent refueling log editing
- Trip categorization for tax purposes
- Detailed consumption analysis

**Views:**
1. **Overview** - Key metrics and recommendations
2. **Refueling Log** - FWCAM card for refueling management
3. **Trip Log** - FWCAM card for trip management
4. **Statistics** - Graphs and analytics
5. **Settings** - Configuration and controls
6. **Debug** - Technical details

## 🚀 Quick Start

### Prerequisites

- ✅ Home Assistant 2023.7 or newer
- ✅ FWCAM integration installed and configured
- ✅ At least one vehicle set up

### Installation (5 minutes)

1. **Open the Installation Guide**
   - Read [DASHBOARD_INSTALLATION_GUIDE.md](./DASHBOARD_INSTALLATION_GUIDE.md) for detailed instructions

2. **Choose Your Template**
   - **Multiple vehicles?** → Use `fwcam-overview-dashboard.yaml`
   - **Single vehicle with details?** → Use `fwcam-vehicle-dashboard-template.yaml`
   - **Want both?** → Install both! 🎉

3. **Quick Installation**
   - Go to Settings → Dashboards in Home Assistant
   - Click "+ ADD DASHBOARD"
   - Select "New dashboard from scratch"
   - Edit Dashboard → Raw configuration editor
   - Copy & paste your chosen template
   - Replace `YOUR_CAR_NAME` with your vehicle name
   - Save and enjoy!

## 📖 Documentation

- **[Dashboard Installation Guide](./DASHBOARD_INSTALLATION_GUIDE.md)** - Detailed step-by-step instructions
- **[Entity Documentation](../docs/ENTITIES.md)** - All available entities explained
- **[Refueling Log Guide](../docs/user_docs/REFUELING_LOG_GUIDE.md)** - How to use the refueling log

## 🎨 Customization

All templates are fully customizable! Common customizations:

### Change Vehicle Names
```yaml
# Find and replace
YOUR_CAR_NAME → your_actual_car_name
```

### Adjust Gauge Ranges
```yaml
- type: gauge
  entity: sensor.car_tank_level
  min: 0
  max: 100  # Adjust to match your tank capacity
```

### Add More Vehicles
Copy the vehicle section and paste with different entity names.

### Change Colors and Icons
Modify severity thresholds and icon names to match your preferences.

## 🖼️ Screenshots

### Overview Dashboard
![Overview Dashboard](../docs/images/dashboard-overview.png)
*Multi-vehicle overview with key metrics*

### Per-Vehicle Dashboard
![Vehicle Dashboard](../docs/images/dashboard-vehicle.png)
*Detailed vehicle view with FWCAM card*

### Refueling Log
![Refueling Log](../docs/images/dashboard-refueling.png)
*Comprehensive refueling log management*

### Trip Log
![Trip Log](../docs/images/dashboard-trips.png)
*Trip log with geocoding and maps*

## 🛠️ Troubleshooting

### Common Issues

**"Entity not found"**
- Verify your vehicle entity names in Developer Tools → States
- Make sure you replaced ALL instances of `YOUR_CAR_NAME`

**"Custom element doesn't exist: fwcam-card"**
- Verify `fwcam-card.js` is installed
- Clear browser cache (Ctrl+Shift+R)

**"Invalid YAML"**
- Check indentation (use spaces, not tabs)
- Verify all quotes and brackets are properly closed
- Use a YAML validator online

For more troubleshooting, see the [Installation Guide](./DASHBOARD_INSTALLATION_GUIDE.md#troubleshooting).

## ⚠️ Technical Limitations

**Why no auto-install?**

Home Assistant does NOT support automatic dashboard creation from integrations for security and stability reasons. This is an architectural decision by the Home Assistant team.

**Our solution:**
- ✅ Comprehensive YAML templates (this directory)
- ✅ Detailed installation guides
- ✅ Easy customization
- ✅ Following Home Assistant best practices

This approach is used by professional integrations like Frigate, ESPHome, and Zigbee2MQTT.

## 🤝 Contributing

### Share Your Dashboard

Created an awesome customized dashboard? Share it with the community!

1. Fork the repository
2. Add your dashboard to `dashboards/community/`
3. Include screenshots
4. Submit a pull request

### Suggest Improvements

Have ideas for better dashboard layouts? [Open an issue](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)!

## 📝 Template Comparison

| Feature | Overview Dashboard | Per-Vehicle Dashboard |
|---------|-------------------|---------------------|
| Multiple vehicles | ✅ Yes | ❌ No (single vehicle) |
| FWCAM custom card | ❌ No | ✅ Yes (full integration) |
| Refueling management | 👁️ View only | ✅ Full CRUD |
| Trip management | 👁️ View only | ✅ Full CRUD + geocoding |
| Statistics graphs | Basic | ✅ Advanced |
| Price comparison | ✅ Yes | Single vehicle |
| Central settings | ✅ Yes | Single vehicle |
| Best for | Overview, multiple cars | Detailed single car management |
| Complexity | Medium | High |
| Setup time | 5-10 minutes | 5-10 minutes |

## 🎯 Recommended Setup

### For Single Vehicle Users
1. Install **Per-Vehicle Dashboard**
2. Customize to your preferences
3. Enjoy full FWCAM functionality!

### For Multiple Vehicle Users
1. Install **Overview Dashboard** for quick comparison
2. Install **Per-Vehicle Dashboard** for each vehicle you want to manage in detail
3. Use sidebar navigation to switch between dashboards

### For Power Users
1. Install both templates
2. Customize each extensively
3. Create custom views for specific use cases
4. Share your configurations with the community!

## 📚 Additional Resources

- [Home Assistant Dashboard Documentation](https://www.home-assistant.io/dashboards/)
- [Lovelace Card Reference](https://www.home-assistant.io/lovelace/)
- [FWCAM Integration Documentation](../README.md)
- [GitHub Discussions](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/discussions)

## 📄 Files in This Directory

```
dashboards/
├── README.md                               # This file
├── DASHBOARD_INSTALLATION_GUIDE.md         # Detailed installation guide
├── fwcam-overview-dashboard.yaml           # Multi-vehicle overview template
├── fwcam-vehicle-dashboard-template.yaml   # Single-vehicle detailed template
└── community/                              # Community-contributed dashboards (future)
```

---

**Happy dashboard building!** 🚗💨

Need help? Check the [Installation Guide](./DASHBOARD_INSTALLATION_GUIDE.md) or [open an issue](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)!
