# Vehicle Entity Integration Guide

This guide explains how to configure vehicle entity integration in the Fuel Watcher Car Advanced Manager (haFWCMA) integration.

## Overview

The vehicle entity integration allows haFWCMA to use existing Home Assistant entities from your vehicle to:

- **Track real-time odometer readings** - Calculate accurate fuel consumption
- **Monitor tank fill level** - Automatically detect refueling events
- **Use remaining range** - Improve consumption predictions and refueling recommendations
- **Track vehicle position** - Find the nearest and cheapest gas station based on your current location

## Configuration

### Initial Setup

When adding the integration, you'll go through these steps:

1. **Tankerkönig API Configuration** - Enter your API credentials and default location
2. **Vehicle Configuration** - Enter vehicle name and tank capacity
3. **Vehicle Entities (Optional)** - Link existing Home Assistant vehicle entities
4. **Telegram Notifications (Optional)** - Configure notifications

### Vehicle Entities Step

In the "Configure Vehicle Entities" step, you can optionally link the following entities:

#### Odometer Sensor

- **Entity Type**: `sensor.*`
- **Purpose**: Track total distance traveled for fuel consumption calculations
- **Unit**: Kilometers (km)
- **Example Entities**: 
  - `sensor.my_car_odometer`
  - `sensor.bmw_mileage`
  - `sensor.vehicle_odometer_km`

#### Tank Fill Level Sensor

- **Entity Type**: `sensor.*`
- **Purpose**: Monitor fuel level and automatically detect refueling
- **Unit**: Liters (L) or Percentage (%)
- **Example Entities**:
  - `sensor.my_car_fuel_level`
  - `sensor.vehicle_fuel_tank_level`
  - `sensor.car_fuel_remaining`

**Note**: The integration supports both absolute (liters) and percentage-based tank level sensors.

#### Remaining Range Sensor

- **Entity Type**: `sensor.*`
- **Purpose**: Track estimated driving range for consumption analysis
- **Unit**: Kilometers (km)
- **Example Entities**:
  - `sensor.my_car_range`
  - `sensor.vehicle_remaining_range`
  - `sensor.car_distance_to_empty`

#### Vehicle Position (Device Tracker)

- **Entity Type**: `device_tracker.*` **only**
- **Purpose**: Use current vehicle location to find nearest gas stations
- **Example Entities**:
  - `device_tracker.my_car`
  - `device_tracker.iphone_of_driver`
  - `device_tracker.bmw_location`

**Important**: Only device_tracker entities are supported for position tracking.

### Entity Selection Methods

You can configure entities in two ways:

1. **Entity Selector** - Use the dropdown search to find and select existing entities
2. **Manual Entry** - Copy and paste the entity ID directly

Both methods validate that the entity exists in your Home Assistant instance.

### Special Notes for Device Trackers

Device trackers can report location in different ways:

- **Coordinates in Attributes** (Preferred): `latitude` and `longitude` in attributes
- **Zone Names in State**: "home", "work", "away" - coordinates extracted from attributes
- **Unavailable**: Falls back to configured default location

The integration automatically handles all these cases.

## Reconfiguration

You can update vehicle entity configuration at any time:

1. Go to **Settings** → **Devices & Services**
2. Find **Fuel Watcher Car Advanced Manager**
3. Click **Configure**
4. Update any entity IDs as needed

Changes take effect on the next update cycle (typically within 5 minutes).

## How It Works

### Fuel Consumption Tracking

When both **odometer** and **tank level** entities are configured:

1. Integration tracks changes in both values over time
2. Calculates consumption: `(fuel_used / distance_traveled) × 100` = L/100km
3. Excludes refueling events from consumption calculations
4. Provides average consumption data for analysis

### Refueling Detection

When a **tank level** entity is configured:

1. Integration monitors tank level changes
2. Detects significant increases (>5 units) as refueling
3. Logs refueling events with timestamp and amount
4. Can trigger automations via Home Assistant events

**Example**: Tank level jumps from 15L to 45L → Refueling detected (30L added)

### Dynamic Station Location

When a **position** entity is configured:

1. Integration uses real-time vehicle coordinates
2. Queries Tankerkönig API for nearby stations
3. Updates station list based on current location
4. Calculates accurate distances to stations

**Fallback**: If position unavailable, uses configured default location.

## Entity Requirements

### Optional vs Required

**All vehicle entities are optional**. The integration works with any combination:

- ✅ No entities configured (uses manual data entry)
- ✅ Only position configured (dynamic station search)
- ✅ Only tank level configured (refueling detection)
- ✅ All entities configured (full feature set)

### Data Availability

Entities must:
- Exist in Home Assistant
- Have valid state (not `unavailable` or `unknown`)
- Report numeric values (for sensors)
- Report coordinates or zone (for device trackers)

Missing or unavailable data is handled gracefully - features requiring that data simply won't activate.

## Examples

### Example 1: BMW ConnectedDrive Integration

```yaml
# BMW ConnectedDrive provides these entities:
odometer_entity: sensor.bmw_330e_mileage
tank_level_entity: sensor.bmw_330e_remaining_fuel
range_entity: sensor.bmw_330e_remaining_range_electric
position_entity: device_tracker.bmw_330e
```

### Example 2: Tesla Integration

```yaml
# Tesla integration provides:
odometer_entity: sensor.tesla_model_3_odometer
tank_level_entity: sensor.tesla_model_3_battery_level
range_entity: sensor.tesla_model_3_range
position_entity: device_tracker.tesla_model_3_location
```

### Example 3: Manual Tracking with Phone GPS

```yaml
# Using phone GPS for location, manual sensors for vehicle data:
odometer_entity: sensor.my_car_odometer_manual
tank_level_entity: sensor.my_car_fuel_level_manual
range_entity: # Leave empty
position_entity: device_tracker.my_iphone
```

### Example 4: Basic Setup (No Vehicle Integration)

```yaml
# Minimum setup - all entities empty
# Uses default location from initial setup
# Manual tank level tracking via input_number helpers
```

## Troubleshooting

### Entity Not Found Error

**Problem**: "Entity does not exist in Home Assistant"

**Solutions**:
1. Check entity ID spelling (case-sensitive)
2. Verify entity exists: **Developer Tools** → **States**
3. Ensure integration providing entity is loaded
4. Try using entity selector instead of manual entry

### Device Tracker Not Accepted

**Problem**: "Position entity must be a device_tracker"

**Solution**: Only `device_tracker.*` entities are valid for position. If you're using a sensor, you may need to:
1. Create a device tracker from your sensor data
2. Use templates to convert sensor to device_tracker
3. Leave position empty and use default location

### No Coordinates from Device Tracker

**Problem**: Device tracker shows "home" but no fuel stations found

**Explanation**: Some device trackers report zone names without coordinates in attributes.

**Solutions**:
1. Check if coordinates exist: **Developer Tools** → **States** → Check attributes
2. Use a GPS-based device tracker (phone app, car integration)
3. Fall back to default configured location

### Inaccurate Consumption Calculation

**Problem**: Consumption values seem wrong

**Possible Causes**:
1. Odometer reports in miles instead of kilometers
2. Tank level sensor is percentage, not liters
3. Not enough data collected yet (need 2+ updates)
4. Refueling was not properly detected

**Solutions**:
1. Verify entity units in **Developer Tools** → **States**
2. Ensure entities update regularly (check last_updated)
3. Wait for more data to accumulate
4. Check logs for tracking information

## Best Practices

### 1. Use Vehicle Integration When Available

Most modern car integrations (BMW, Tesla, Ford, etc.) provide all needed entities. Use these official integrations for best results.

### 2. Keep Entities Updated

Ensure your vehicle entities update regularly:
- Car integrations: Usually every 5-15 minutes
- Phone GPS: Every few minutes when moving
- Manual sensors: Update after each trip

### 3. Consistent Units

Use consistent units across your setup:
- **Recommended**: km for distance, L for fuel
- Avoid mixing miles/km or gallons/liters

### 4. Test Configuration

After setup:
1. Check entity states in Developer Tools
2. Wait for one update cycle (5 minutes)
3. Verify sensors show correct data
4. Test position by moving vehicle (if configured)

### 5. Combine with Automations

Create automations based on vehicle data:
- Low fuel alert when tank < 20%
- Refueling reminder when prices are low
- Consumption tracking for monthly reports

## Future Enhancements

Planned improvements for vehicle entity integration:

- [ ] Automatic unit conversion (miles → km, gallons → L)
- [ ] Multiple vehicle support
- [ ] Historical consumption trends
- [ ] Fuel efficiency comparisons
- [ ] Smart learning from driving patterns
- [ ] Integration with more vehicle platforms

## Support

For issues or questions:
- **GitHub Issues**: [Report problems](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)
- **Discussions**: [Ask questions](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/discussions)
- **Documentation**: [Main README](../../README.md)

---

*Last Updated: 2026-02-05*
