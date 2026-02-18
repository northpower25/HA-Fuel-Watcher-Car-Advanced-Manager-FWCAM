# Entity Metadata Display Example

This document shows how the standardized entity metadata appears in Home Assistant.

## Example: Fuel Price Sensor

When viewing the `sensor.my_car_fuel_price` entity in Home Assistant Developer Tools → States, users will see attributes like:

### Standard Sensor Attributes
```yaml
# Regular sensor data
state: 1.679
unit_of_measurement: €/L
device_class: monetary
station_name: "ARAL Tankstelle"
station_address: "Hauptstraße 123, 12345 Berlin"
distance: 2.3
forecast_trend: "stable"
should_refuel: false
urgency: "low"
recommendation: "Prices are stable. No urgent need to refuel."
```

### Entity Metadata Attributes (NEW)
```yaml
# Inline documentation - visible in Home Assistant UI
purpose_info: "Current fuel price (€/L) at nearest/cheapest station"
data_source_info: "Fuel price provider API (e.g., Tankerkönig), vehicle/HA location"
dependencies_info: "API key, geolocation data; used by refueling recommendations, price trends"
documentation_url: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#fuel-price-sensor"
```

## How Users See This

### In Developer Tools → States

1. User opens Developer Tools → States
2. Selects `sensor.my_car_fuel_price`
3. Scrolls to Attributes section
4. Sees the metadata attributes with clear descriptions
5. Can click the `documentation_url` to open detailed documentation

### In Home Assistant UI Cards

When creating cards or automations, users can:
- See what the entity does (`purpose_info`)
- Understand where data comes from (`data_source_info`)
- Know what else depends on it (`dependencies_info`)
- Access detailed docs with one click (`documentation_url`)

## Example: Trip Tracking Switch

```yaml
# Entity: switch.my_car_trip_tracking

# Regular switch data
state: "on"
friendly_name: "Trip Tracking"
icon: "mdi:map-marker-path"

# Trip statistics (existing attributes)
privacy_notice_accepted: true
last_enabled_at: "2026-02-18T10:30:00+00:00"
total_trips: 42
total_distance_km: 1234.5
business_trips: 15
private_trips: 20
commute_trips: 7

# Entity metadata (NEW)
purpose_info: "Enables/disables automatic trip tracking"
data_source_info: "Configuration entry options (persisted), trip tracking state"
dependencies_info: "Odometer entity; used by Trip Log, On Trip, Current Trip sensors"
documentation_url: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#trip-tracking-switch"
```

## Example: Test Provider Connection Button

```yaml
# Entity: button.my_car_test_provider_connection

# Regular button data
state: "2026-02-18T14:30:00+00:00"
friendly_name: "Test Provider Connection"
icon: "mdi:api"

# Test results (existing attributes, shown after pressing button)
test_success: true
stations_found: 15
response_time_ms: 234
message: "API connection successful"

# Entity metadata (NEW)
purpose_info: "Tests connection to fuel price provider API"
data_source_info: "API test request to fuel price provider"
dependencies_info: "Configured API provider and API key"
documentation_url: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#test-provider-connection-button"
```

## Benefits Illustrated

### Before (Without Metadata)
User sees: `sensor.my_car_consumption_prediction`

Questions:
- What is this sensor for?
- Where does it get its data?
- What else uses this data?
- Where can I learn more?

User must:
- Search documentation
- Read code
- Ask for help

### After (With Metadata)
User sees: `sensor.my_car_consumption_prediction`

Answers in attributes:
- **Purpose**: "Predicted days until refueling needed based on consumption patterns"
- **Data Source**: "Historical refueling data, current vehicle data, trip data, weekday patterns"
- **Dependencies**: "Refueling Log, Tank/Range sensors, Trip Log (optional); used by refueling recommendations"
- **Documentation**: "https://github.com/.../ENTITIES.md#consumption-prediction-sensor" [Click to open]

User:
- Understands immediately
- Can dive deeper if needed
- Self-sufficient

## Visual Representation

```
┌─────────────────────────────────────────────────────────────┐
│ Home Assistant Developer Tools → States                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Entity: sensor.my_car_fuel_price                           │
│                                                              │
│ State: 1.679 €/L                                            │
│                                                              │
│ Attributes:                                                  │
│ ┌─────────────────────────────────────────────────────┐    │
│ │ station_name: ARAL Tankstelle                        │    │
│ │ distance: 2.3                                        │    │
│ │ recommendation: Prices are stable...                │    │
│ │                                                       │    │
│ │ ╔═══════════════════════════════════════════════╗  │    │
│ │ ║ Entity Documentation (Inline)                 ║  │    │
│ │ ║                                                ║  │    │
│ │ ║ purpose_info:                                  ║  │    │
│ │ ║   Current fuel price (€/L) at nearest/...     ║  │    │
│ │ ║                                                ║  │    │
│ │ ║ data_source_info:                              ║  │    │
│ │ ║   Fuel price provider API (e.g., Tankerkö...  ║  │    │
│ │ ║                                                ║  │    │
│ │ ║ dependencies_info:                             ║  │    │
│ │ ║   API key, geolocation data; used by refue... ║  │    │
│ │ ║                                                ║  │    │
│ │ ║ documentation_url:                             ║  │    │
│ │ ║   https://github.com/.../ENTITIES.md#fuel-...  ║  │    │
│ │ ║   [Click to open detailed documentation]      ║  │    │
│ │ ╚═══════════════════════════════════════════════╝  │    │
│ └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Integration with Automations

When creating automations, users can quickly understand entities:

```yaml
# Before: User sees entity, must guess what it does
automation:
  trigger:
    - platform: state
      entity_id: binary_sensor.my_car_proximity_alert

# After: User checks attributes, immediately understands
# purpose_info: "Alerts when vehicle is near a cheap fuel station"
# dependencies_info: "Proximity Alerts Switch (enabled), Position entity, ..."

automation:
  trigger:
    - platform: state
      entity_id: binary_sensor.my_car_proximity_alert
      to: "on"
  action:
    - service: notify.mobile_app
      data:
        message: "Cheap fuel station nearby!"
```

## Conclusion

The entity metadata implementation provides:
1. **Immediate context** - No need to search documentation
2. **Better UX** - Users understand what they're configuring
3. **Faster troubleshooting** - Dependencies are clear
4. **One-click help** - Direct link to detailed docs

All without leaving the Home Assistant UI.

---

**Note**: The exact appearance in Home Assistant may vary depending on the UI theme and version, but the attributes will always be accessible in Developer Tools → States and in automation/script editors.
