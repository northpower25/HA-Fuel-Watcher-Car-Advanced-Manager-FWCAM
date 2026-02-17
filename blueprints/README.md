# haFWCMA Blueprints

This directory contains Home Assistant Blueprints for easy integration of haFWCMA features into your automations and scripts.

## 📁 Structure

```
blueprints/
├── automation/          # Automation blueprints
│   ├── low_fuel_alert.yaml
│   ├── price_drop_notification.yaml
│   ├── refueling_reminder.yaml
│   ├── trip_logging.yaml
│   └── geolocation_proximity.yaml (planned)
└── script/             # Script blueprints
    ├── manual_refuel_entry.yaml
    ├── trip_completion.yaml
    └── fuel_price_query.yaml
```

## 🚀 Quick Start

### Import a Blueprint

1. Go to **Settings** → **Automations & Scenes** in Home Assistant
2. Click on **Blueprints** tab
3. Click **Import Blueprint** (bottom right)
4. Paste the blueprint URL
5. Click **Preview** and then **Import**

### Blueprint URLs

All blueprints are available at:
```
https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/blueprints/[type]/[name].yaml
```

Example:
```
https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/blueprints/automation/low_fuel_alert.yaml
```

## 📖 Documentation

For detailed documentation in German, see: [BLUEPRINTS_DE.md](../BLUEPRINTS_DE.md)

For English documentation, see the main [README.md](../README.md)

## 🤖 Available Blueprints

### Automations

- **Low Fuel Alert** - Warns when fuel level is low
- **Price Drop Notification** - Notifies when fuel price drops below threshold
- **Refueling Reminder** - Smart daily reminder based on patterns
- **Trip Logging** - Automatic trip recording with notifications
- **Geolocation Proximity** - Alerts near cheap stations (planned)

### Scripts

- **Manual Refuel Entry** - Add refueling event manually
- **Trip Completion** - Edit and categorize completed trips
- **Fuel Price Query** - Get current prices and station info

## 🔧 Requirements

- Home Assistant 2023.9 or later
- haFWCMA integration installed and configured
- Notification service configured (for most blueprints)

## 📝 License

MIT License - See [LICENSE](../LICENSE)
