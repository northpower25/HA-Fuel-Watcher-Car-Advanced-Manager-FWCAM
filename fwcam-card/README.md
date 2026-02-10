# FWCAM Card - Fuel Watcher Car Advanced Manager Card

A custom Lovelace card for the Fuel Watcher Car Advanced Manager (FWCAM) Home Assistant integration.

## Features

- **Vehicle Information Display**: Shows current fuel price, tank level, range, nearest station, and refueling prediction
- **Control Panel**: Quick access buttons for refreshing fuel prices, updating predictions, testing connection, and importing historical data
- **Settings Management**: Inline editing of integration settings (search radius, update interval, etc.)
- **Refueling Log**: 
  - View all refueling events in a table format
  - Color-coded data quality and confidence indicators
  - Inline editing capabilities (edit and delete events)
  - Add new refueling events manually
- **Responsive Design**: Adapts to different screen sizes
- **Material Design**: Follows Home Assistant's design language

## Installation

### HACS Installation (Recommended)

1. Open HACS in your Home Assistant
2. Go to "Frontend" section
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM`
6. Select category "Lovelace"
7. Click "Add"
8. Find "FWCAM Lovelace Card" in the list
9. Click "Download"
10. Restart Home Assistant
11. Clear your browser cache
12. Add the card to your dashboard

### Manual Installation

1. Download `fwcam-card.js` from the `dist/` directory
2. Copy it to your `config/www/fwcam-card/` directory
3. Add the resource in your Lovelace configuration:

```yaml
resources:
  - url: /local/fwcam-card/fwcam-card.js
    type: module
```

4. Restart Home Assistant
5. Clear your browser cache
6. Add the card to your dashboard

## Configuration

### Basic Configuration

```yaml
type: custom:fwcam-card
entity: sensor.my_car_refueling_log
```

### Full Configuration

```yaml
type: custom:fwcam-card
entity: sensor.my_car_refueling_log
title: My Car Fuel Manager
show_refueling_log: true
show_vehicle_info: true
show_controls: true
show_settings: true
rows_per_page: 10
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `entity` | string | **Required** | The refueling log sensor entity (e.g., `sensor.my_car_refueling_log`) |
| `title` | string | `Fuel Watcher Car Advanced Manager` | Card title |
| `show_refueling_log` | boolean | `true` | Show/hide the refueling log table |
| `show_vehicle_info` | boolean | `true` | Show/hide vehicle information section |
| `show_controls` | boolean | `true` | Show/hide control buttons |
| `show_settings` | boolean | `true` | Show/hide settings section |
| `rows_per_page` | number | `10` | Number of refueling events to display |

## Entity Auto-Detection

The card automatically detects all related entities based on the refueling log sensor name. For example, if you configure:

```yaml
entity: sensor.my_car_refueling_log
```

The card will automatically find and use:
- `sensor.my_car_fuel_price`
- `sensor.my_car_tank_level`
- `sensor.my_car_range`
- `switch.my_car_fuel_price_refresh`
- `switch.my_car_consumption_prediction`
- `number.my_car_station_search_radius`
- And all other related entities

## Features in Detail

### Refueling Log Table

The refueling log shows:
- **Date/Time**: When the refueling occurred
- **Odometer**: Vehicle odometer reading in km
- **Liters**: Amount of fuel added
- **Price/L**: Price per liter in €
- **Total**: Total cost in €
- **Station**: Name of the fuel station
- **Quality**: Data quality indicator (manual, auto_detected, historical_import)
- **Confidence**: Confidence score of the detection (0-100%)
- **Actions**: Edit and delete buttons

**Note on Editing**: The current version uses service calls for editing. Click the edit or add button to see instructions for using the `hafwcma.add_refuel_event` and `hafwcma.update_refuel_event` services. A visual dialog interface for editing will be added in a future update.

### Data Quality Indicators

- **Manual** (Green): Manually entered data - highest quality
- **Auto Detected** (Blue): Automatically detected during normal operation
- **Historical Import** (Orange): Imported from historical data

### Confidence Scores

- **High (Green)**: 70-100% confidence
- **Medium (Orange)**: 40-69% confidence
- **Low (Red)**: 0-39% confidence

### Inline Editing

Click the edit button (✏️) to modify a refueling event. Click the delete button (🗑️) to remove an event.

## Services Required

The card uses the following services (these should be provided by the FWCAM integration):

- `hafwcma.add_refuel_event` - Add a new refueling event
- `hafwcma.update_refuel_event` - Update an existing event
- `hafwcma.delete_refuel_event` - Delete an event

## Browser Compatibility

- Chrome/Edge: ✅ Fully supported
- Firefox: ✅ Fully supported
- Safari: ✅ Fully supported
- Mobile browsers: ✅ Responsive design

## Development

### Adding New Features

When adding new features to the FWCAM integration:

1. **Add new entities** to the `findEntities()` method in `fwcam-card.js`
2. **Update UI sections** to display new entities
3. **Add service calls** if new backend functionality is added
4. **Update configuration** if new options are needed
5. **Update documentation** in the integration's documentation

### Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and feature requests:
1. Check the [Documentation](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM)
2. Open an issue on [GitHub](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)

## License

MIT License - See LICENSE file for details

## Credits

Developed by northpower25 for the FWCAM Home Assistant integration.
