# FWCAM Card - Fuel Watcher Car Advanced Manager Card

A custom Lovelace card for the Fuel Watcher Car Advanced Manager (FWCAM) Home Assistant integration.

> **📦 NEW: The card is now bundled with the integration!**  
> When you install the FWCAM integration via HACS, the card is automatically included and registered.  
> You no longer need to install it separately. See [Installation](#installation) below.

## Features

- **Vehicle Information Display**: Shows current fuel price, tank level, range, nearest station, and refueling prediction
- **Control Panel**: Quick access buttons for refreshing fuel prices, updating predictions, testing connection, and importing historical data
- **Settings Management**: Inline editing of integration settings (search radius, update interval, etc.)
- **Refueling Log**: 
  - View all refueling events in a sortable table format
  - **Sortable columns**: Click headers to sort by Date, Odometer, Liters, Price, Total, or Station
  - **Filtering**: Filter events by year and month
  - **Add/Edit dialogs**: Full-featured dialogs for adding and editing refueling events
  - Color-coded data quality and confidence indicators
  - Edit and delete buttons for each event
- **Responsive Design**: Adapts to different screen sizes
- **Material Design**: Follows Home Assistant's design language

## Installation

### Automatic Installation (Recommended)

**The card is now bundled with the integration!**

1. Install the FWCAM integration via HACS (see [main README](../README.md))
2. Restart Home Assistant
3. Clear your browser cache (Ctrl+Shift+R)
4. The card is automatically available in your dashboard!

No separate installation needed!

### Manual Installation (Legacy)

If you're installing the integration manually, the card is already included in `custom_components/hafwcma/www/`.

Alternatively, for standalone use:

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
refresh_interval: 300
table_max_height: 400px
table_min_width: 100%
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
| `refresh_interval` | number | `300` | Refresh interval in seconds (default: 5 minutes) |
| `table_max_height` | string | `400px` | Maximum height of refueling log table (enables vertical scrolling) |
| `table_min_width` | string | `100%` | Minimum width of table (reduces horizontal scrolling) |

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
