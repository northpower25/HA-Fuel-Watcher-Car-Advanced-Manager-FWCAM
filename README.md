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
- **NEW: Configurable API polling interval** (1-60 minutes)
- **NEW: Automatic randomization** to prevent simultaneous API calls and rate limiting

### 📈 Smart Forecasting & Prediction Engine
- **Self-learning consumption tracking** based on your driving patterns
- **Machine learning for advanced predictions** with weekday/weekend pattern recognition
- **Intelligent refueling recommendations** with urgency levels
- **Advanced consumption prediction engine** with confidence scoring
- **Manual prediction trigger** via switch entity for on-demand calculations
- **Configurable prediction intervals** and data requirements
- Fuel price trend prediction (rising/falling/stable)
- Price drop detection with configurable thresholds
- Days until refuel estimation based on learned daily kilometers
- Historical price analysis and statistics
- Weekday consumption pattern learning
- Best time to refuel suggestions
- Price vs. distance optimization
- Automatic fallback to configuration values when insufficient historical data
- **Stable fuel price display** - sensors retain last successful values with timestamps

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
   - **Step 5**: (Optional) Configure prediction engine thresholds

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
- **Prediction Engine Settings**:
  - Price drop percent threshold (trigger refuel recommendation)
  - Price drop absolute threshold (in EUR)
  - Low fuel alert threshold (% of tank)
  - Critical fuel alert threshold (% of tank)
  - Fallback daily kilometers (for range estimation)
- **Telegram Settings**: Bot token and chat ID
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
- **Days Until Refuel**: Predicted days until refueling needed (consumption prediction)
- **Average Consumption History**: Historical average consumption with attributes for today, last week, last 14 days, and last month
- **Average Consumption Forecast**: Forecasted average consumption with attributes for tomorrow, next week, next 14 days, and next month
- **API Debug**: API request/response debug information for troubleshooting

### Controls

- **Test API Connection Button**: Manually test the fuel price API connection with detailed results
- **Manual Prediction Switch**: Trigger immediate consumption/range prediction calculation on demand
- **Search Radius Number**: Adjust the search radius (1-25 km) dynamically from the UI
- **API Update Interval Number**: Configure how often the API is polled (1-60 minutes). Each update is automatically randomized by ±20% to prevent rate limiting when multiple instances access the API simultaneously.
- **Consumption Min Data Points Number**: Configure minimum historical data points required for reliable predictions (2-50, default: 5)
- **Consumption Prediction Interval Number**: Configure how often consumption predictions are recalculated (0.5-24 hours, default: 6)

### Attributes

Each sensor provides additional attributes:

#### Fuel Price Sensor
- `station_name`: Name of the station
- `station_address`: Street address
- `distance`: Distance to station in km
- `last_update_timestamp`: When this price was last successfully fetched (ISO format)
- `forecast_trend`: Price trend (rising/falling/stable)
- `should_refuel`: Boolean recommendation to refuel now
- `urgency`: Urgency level (low/medium/high/critical)
- `recommendation`: User-friendly recommendation text
- `price_delta`: Absolute price change from last known price (EUR)
- `price_delta_percent`: Percentage price change

#### Range Sensor
- `days_left`: Estimated days until refuel needed (based on learned patterns)

#### Tank Level Sensor
- `percentage`: Tank fill percentage

#### Days Until Refuel Sensor (Consumption Prediction)
- `data_source`: Whether prediction uses `ml_enhanced`, `historical_data` or `fallback_values`
- `confidence`: Confidence level of prediction (0-1)
- `avg_daily_km`: Average daily kilometers driven
- `avg_consumption_rate`: Average fuel consumption rate (L/100km)
- `data_points_used`: Number of historical data points used
- `last_prediction`: Timestamp of last prediction calculation
- `predicted_refuel_date`: Predicted date/time when refueling will be needed
- `ml_prediction`: ML-enhanced prediction data (weekday patterns, trends) if available

#### Average Consumption History Sensor
- `today_consumption`: Average consumption for today (L/100km)
- `today_km`: Total kilometers driven today
- `today_liters`: Total liters consumed today
- `today_refuel_count`: Number of refueling events today
- `last_week_consumption`: Average consumption for last 7 days (L/100km)
- `last_week_km`: Total kilometers driven in last 7 days
- `last_week_liters`: Total liters consumed in last 7 days
- `last_week_refuel_count`: Number of refueling events in last 7 days
- `last_14_days_consumption`: Average consumption for last 14 days (L/100km)
- `last_14_days_km`: Total kilometers driven in last 14 days
- `last_14_days_liters`: Total liters consumed in last 14 days
- `last_14_days_refuel_count`: Number of refueling events in last 14 days
- `last_month_consumption`: Average consumption for last 30 days (L/100km)
- `last_month_km`: Total kilometers driven in last 30 days
- `last_month_liters`: Total liters consumed in last 30 days
- `last_month_refuel_count`: Number of refueling events in last 30 days

#### Average Consumption Forecast Sensor
- `tomorrow_consumption`: Forecasted consumption for tomorrow (L/100km)
- `tomorrow_confidence`: Confidence level of tomorrow's forecast (0-1)
- `tomorrow_data_source`: Data source for forecast (`ml_enhanced`, `historical_data`, or `fallback_values`)
- `next_week_consumption`: Forecasted consumption for next 7 days (L/100km)
- `next_week_confidence`: Confidence level of next week's forecast (0-1)
- `next_week_data_source`: Data source for forecast
- `next_14_days_consumption`: Forecasted consumption for next 14 days (L/100km)
- `next_14_days_confidence`: Confidence level of forecast (0-1)
- `next_14_days_data_source`: Data source for forecast
- `next_month_consumption`: Forecasted consumption for next 30 days (L/100km)
- `next_month_confidence`: Confidence level of forecast (0-1)
- `next_month_data_source`: Data source for forecast

#### Nearest Station Sensor
- `station_address`: Full address
- `distance`: Distance in km
- `price`: Current fuel price
- `last_update_timestamp`: When this station was last successfully fetched (ISO format)
- `google_maps_url`: Navigation link for Google Maps
- `apple_maps_url`: Navigation link for Apple Maps
- `waze_url`: Navigation link for Waze

#### API Debug Sensor
- `timestamp`: When the last API request was made
- `location_source`: Whether using vehicle or fallback coordinates
- `latitude`, `longitude`: Coordinates used for API request
- `radius_km`: Search radius used
- `fuel_type`: Fuel type requested
- `api_response_status`: Success or error status
- `stations_found`: Number of stations returned
- `stations_with_price_and_open`: Number of open stations with valid prices
- `last_api_request`: Complete details of the last API request sent (URL, parameters, timestamp)
- `last_api_response`: Complete API response data (status, data payload, timestamp)

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

Example automation using prediction engine recommendations:

```yaml
automation:
  - alias: "Smart Refuel Alert"
    trigger:
      - platform: state
        entity_id: sensor.my_car_fuel_price
        attribute: should_refuel
        to: true
    action:
      - service: notify.telegram
        data:
          message: >
            {{ state_attr('sensor.my_car_fuel_price', 'recommendation') }}
            
            Price: €{{ states('sensor.my_car_fuel_price') }}/L
            Urgency: {{ state_attr('sensor.my_car_fuel_price', 'urgency') }}
            Days of fuel left: {{ state_attr('sensor.my_car_range', 'days_left') }}
```

Example automation using consumption prediction:

```yaml
automation:
  - alias: "Low Days Until Refuel Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_car_days_until_refuel
        below: 2
    condition:
      - condition: template
        value_template: "{{ state_attr('sensor.my_car_days_until_refuel', 'confidence') | float > 0.5 }}"
    action:
      - service: notify.telegram
        data:
          message: >
            Warning: Only {{ states('sensor.my_car_days_until_refuel') }} days of fuel left!
            
            Predicted refuel date: {{ state_attr('sensor.my_car_days_until_refuel', 'predicted_refuel_date') }}
            Data source: {{ state_attr('sensor.my_car_days_until_refuel', 'data_source') }}
            Confidence: {{ (state_attr('sensor.my_car_days_until_refuel', 'confidence') | float * 100) | round(0) }}%
```

## Automatic Fuel Log

The integration includes an **automatic fuel log** feature that tracks all your refueling events with comprehensive details:

### Refueling Detection

The system automatically detects refueling events when the tank level increases by more than 5 liters/percent. When a refueling is detected, the following information is automatically recorded:

- **Refueling ID**: Unique sequential ID for each refueling event
- **Timestamp**: Date and time of the refueling (editable)
- **Odometer Reading**: Mileage at the time of refueling (editable)
- **Station Name**: Automatically pre-filled with the recommended station at that time (editable)
- **Liters Refueled**: Calculated from tank level change (editable)
- **Price per Liter**: Pre-filled with the current fuel price (editable)
- **Total Cost**: Automatically calculated from liters × price per liter
- **Location**: GPS coordinates of the refueling event
- **Fuel Type**: Type of fuel (E5, E10, Diesel)

### Data Storage

All refueling events are stored persistently in the integration's database with full CRUD (Create, Read, Update, Delete) support. The refueling log maintains up to 100 refueling events per vehicle.

### Future Enhancements

Planned features for the automatic fuel log include:
- Table entity for viewing and editing refueling records in the Home Assistant UI
- Telegram chat integration for completing/editing refueling records via chat
- AI-powered receipt scanning for automatic data extraction
- Monthly fuel cost reports and statistics
- Export functionality (CSV, JSON)

See [TODO.md](TODO.md) for the complete roadmap of fuel log features.

## Development Status

This is an MVP (Minimum Viable Product) release. The following features are implemented:

- ✅ Config Flow and Options Flow
- ✅ Tankerkönig API integration
- ✅ Fuel price sensors with prediction attributes
- ✅ **Vehicle entity integration** (odometer, tank level, range, position)
- ✅ **Automatic refueling detection**
- ✅ **Real-time consumption tracking (L/100km)**
- ✅ **Dynamic position-based station search**
- ✅ **Prediction Engine with intelligent refuel recommendations**
- ✅ **Machine learning for advanced predictions**
- ✅ **Manual prediction trigger switch**
- ✅ **Advanced consumption prediction engine** with confidence scoring
- ✅ **Configurable prediction intervals and data requirements**
- ✅ **Persistent storage for price and vehicle history**
- ✅ **Self-learning driving pattern analysis**
- ✅ **Price trend analysis and statistics**
- ✅ **Configurable thresholds for personalized recommendations**
- ✅ **Automatic fuel log with comprehensive refueling tracking**
- ✅ **Average consumption history sensor** (today, week, 14 days, month)
- ✅ **Average consumption forecast sensor** (tomorrow, week, 14 days, month)
- ✅ Telegram notification system
- ✅ Multi-language support (EN/DE)

### Planned Features

See [TODO.md](TODO.md) for the complete roadmap.

## Support

- **Issues**: [GitHub Issues](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)
- **Troubleshooting**: [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
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