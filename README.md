# Fuel Watcher Car Advanced Manager (haFWCMA)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive Home Assistant integration for monitoring fuel prices, managing vehicle fuel levels, and receiving intelligent refueling recommendations.

## Features

### 🚗 Vehicle Management
- Track tank fuel levels and capacity
- Monitor estimated driving range
- Automatic tank level recognition
- **NEW: Integration with existing vehicle entities** (odometer, tank level, range, position)
- **NEW: Automatic refueling detection**
- **NEW: Real-time fuel consumption tracking**
- Support for multiple vehicles

### ⛽ Fuel Price Monitoring
- Real-time fuel prices via Tankerkönig API (Germany)
- Search for stations within configurable radius
- Support for E5, E10, and Diesel fuel types
- Distance-based station sorting

### 📈 Smart Forecasting
- Fuel price trend prediction
- Intelligent refueling recommendations
- Best time to refuel suggestions
- Price vs. distance optimization

### 📱 Telegram Notifications
- Price alerts for favorite stations
- Low fuel level warnings
- Refueling recommendations
- Customizable notification triggers

### 🎯 Home Assistant Integration
- Config Flow UI for easy setup
- Options Flow for runtime configuration
- Multiple sensor entities
- Event-based automations
- HACS compatible

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM`
6. Select category "Integration"
7. Click "Add"
8. Find "Fuel Watcher Car Advanced Manager" in the integration list
9. Click "Download"
10. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/hafwcma` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

### Prerequisites

- **Tankerkönig API Key**: Get your free API key from [Tankerkönig](https://creativecommons.tankerkoenig.de)
- **Telegram Bot** (Optional): Create a bot via [@BotFather](https://t.me/botfather) on Telegram

### Setup via UI

1. Go to Configuration > Integrations
2. Click the "+ Add Integration" button
3. Search for "Fuel Watcher Car Advanced Manager"
4. Follow the configuration steps:
   - **Step 1**: Enter Tankerkönig API credentials and location
   - **Step 2**: Configure vehicle details (name, tank capacity)
   - **Step 3**: (Optional) Link existing vehicle entities (odometer, tank level, range, position)
   - **Step 4**: (Optional) Configure Telegram notifications

For detailed information about vehicle entity integration, see [Vehicle Entity Integration Guide](docs/VEHICLE_ENTITIES.md).

### Configuration Options

After initial setup, you can modify these options:

- **Search Radius**: Area to search for fuel stations (in km)
- **Fuel Type**: E5, E10, or Diesel
- **Tank Capacity**: Vehicle tank capacity in liters
- **Vehicle Entities**: Link to existing Home Assistant vehicle entities
  - Odometer sensor (for consumption tracking)
  - Tank level sensor (for refueling detection)
  - Range sensor (for consumption analysis)
  - Position device tracker (for dynamic station search)
- **Telegram Settings**: Bot token and chat ID

## Usage

### Sensors

The integration creates the following sensors for each configured vehicle:

- **Fuel Price**: Current fuel price at nearest station
- **Tank Level**: Current fuel level in liters
- **Range**: Estimated driving range in kilometers
- **Nearest Station**: Name and details of closest station

### Attributes

Each sensor provides additional attributes:

#### Fuel Price Sensor
- `station_name`: Name of the station
- `station_address`: Street address
- `distance`: Distance to station in km
- `forecast_trend`: Price trend (rising/falling/stable)

#### Tank Level Sensor
- `percentage`: Tank fill percentage

#### Nearest Station Sensor
- `station_address`: Full address
- `distance`: Distance in km
- `price`: Current fuel price

### Automations

Example automation for low fuel alert:

```yaml
automation:
  - alias: "Low Fuel Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_car_tank_level
        below: 10
    action:
      - service: notify.telegram
        data:
          message: "Your car fuel level is low! Only {{ states('sensor.my_car_tank_level') }}L remaining."
```

Example automation for good refuel time:

```yaml
automation:
  - alias: "Good Time to Refuel"
    trigger:
      - platform: state
        entity_id: sensor.my_car_fuel_price
        attribute: forecast_trend
        to: "falling"
    condition:
      - condition: numeric_state
        entity_id: sensor.my_car_tank_level
        below: 25
    action:
      - service: notify.telegram
        data:
          message: "Good time to refuel! Prices are falling and tank is at {{ state_attr('sensor.my_car_tank_level', 'percentage') }}%"
```

## Development Status

This is an MVP (Minimum Viable Product) release. The following features are implemented:

- ✅ Config Flow and Options Flow
- ✅ Tankerkönig API integration
- ✅ Basic fuel price sensors
- ✅ Tank level tracking (stub)
- ✅ **Vehicle entity integration** (odometer, tank level, range, position)
- ✅ **Automatic refueling detection**
- ✅ **Real-time consumption tracking (L/100km)**
- ✅ **Dynamic position-based station search**
- ✅ Telegram notification system
- ✅ Price trend forecasting (basic)
- ✅ Multi-language support (EN/DE)

### Planned Features

See [TODO.md](TODO.md) for the complete roadmap.

## Support

- **Issues**: [GitHub Issues](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)
- **Documentation**: [docs/](docs/)

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](docs/CONTRIBUTING.md) first.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

- Fuel price data provided by [Tankerkönig](https://creativecommons.tankerkoenig.de)
- Built for [Home Assistant](https://www.home-assistant.io/)
- Compatible with [HACS](https://hacs.xyz/)

## Disclaimer

This integration is not affiliated with or endorsed by Tankerkönig. Please respect their API usage terms and rate limits.