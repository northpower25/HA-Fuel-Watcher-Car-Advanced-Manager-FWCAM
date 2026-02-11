# Geolocation Feature - Automation Examples

This document provides example automations for using the geolocation-based fuel station proximity features.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Basic Proximity Alert](#basic-proximity-alert)
3. [Telegram Notification](#telegram-notification)
4. [Home Assistant Companion App Notification](#home-assistant-companion-app-notification)
5. [CarPlay/Android Auto Optimized Notification](#carplayandroid-auto-optimized-notification)
6. [Advanced: Combined with Tank Level](#advanced-combined-with-tank-level)
7. [Using the Entities](#using-the-entities)

---

## Prerequisites

1. **Vehicle Position Entity**: You must have configured a `device_tracker` entity for your vehicle in the setup flow. This can be from:
   - Home Assistant Companion App (mobile)
   - OwnTracks
   - Any other device tracker integration

2. **Enable Proximity Alerts**: Turn on the proximity alerts switch:
   ```yaml
   switch.my_car_proximity_alerts: on
   ```

3. **Configure Alert Settings** (optional, defaults are shown):
   - `number.my_car_proximity_alert_distance`: 1.5 km
   - `number.my_car_cheap_stations_count`: 5
   - `number.my_car_cheap_stations_radius`: 15 km
   - `number.my_car_min_tank_level_for_alerts`: 30%

---

## Basic Proximity Alert

Simple automation that triggers when you're near a cheap station:

```yaml
automation:
  - alias: "Notify When Near Cheap Station"
    description: "Basic proximity alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_near_cheap_station
        to: "on"
    action:
      - service: persistent_notification.create
        data:
          title: "⛽ Cheap Fuel Station Nearby"
          message: >
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'alert_message') }}
```

---

## Telegram Notification

Send a notification to Telegram with station details:

```yaml
automation:
  - alias: "Telegram: Cheap Station Nearby"
    description: "Send Telegram notification when near cheap station"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_near_cheap_station
        to: "on"
    condition:
      # Only notify if tank is below 30%
      - condition: numeric_state
        entity_id: sensor.my_car_tank_level
        below: 30
    action:
      - service: notify.telegram
        data:
          message: >
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'alert_message') }}
```

**Enhanced Telegram with inline keyboard:**

```yaml
automation:
  - alias: "Telegram: Enhanced Cheap Station Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_near_cheap_station
        to: "on"
    action:
      - service: notify.telegram
        data:
          message: >
            🚗 Günstige Tankstelle in der Nähe!
            
            📍 {{ state_attr('binary_sensor.my_car_near_cheap_station', 'station_name') }}
            💰 Preis: €{{ state_attr('binary_sensor.my_car_near_cheap_station', 'price') }}/L
            📏 Entfernung: {{ state_attr('binary_sensor.my_car_near_cheap_station', 'distance') }} km
            📫 {{ state_attr('binary_sensor.my_car_near_cheap_station', 'station_address') }}
          data:
            inline_keyboard:
              - "Navigate:{{ state_attr('binary_sensor.my_car_near_cheap_station', 'navigation_urls')['google_maps'] }}"
```

---

## Home Assistant Companion App Notification

Optimized for mobile devices:

```yaml
automation:
  - alias: "Mobile: Cheap Station Nearby"
    description: "Send mobile notification with navigation action"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_near_cheap_station
        to: "on"
    action:
      - service: notify.mobile_app_<your_device>
        data:
          title: "⛽ Cheap Fuel Nearby"
          message: >
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'station_name') }}
            €{{ state_attr('binary_sensor.my_car_near_cheap_station', 'price') }}/L
            ({{ state_attr('binary_sensor.my_car_near_cheap_station', 'distance') }} km)
          data:
            actions:
              - action: "navigate_to_station"
                title: "Navigate"
                uri: "{{ state_attr('binary_sensor.my_car_near_cheap_station', 'navigation_urls')['google_maps'] }}"
            tag: "cheap_fuel_alert"
            group: "fuel_alerts"
            importance: high
            ttl: 0
            priority: high
```

---

## CarPlay/Android Auto Optimized Notification

For visibility in CarPlay/Android Auto, use actionable notifications with voice announcements:

```yaml
automation:
  - alias: "CarPlay: Voice + Visual Alert"
    description: "Announce cheap station via TTS and show notification"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_near_cheap_station
        to: "on"
    condition:
      # Only when driving (optional)
      - condition: template
        value_template: >
          {{ states('sensor.my_car_speed') | float(0) > 5 }}
    action:
      # Visual notification
      - service: notify.mobile_app_<your_device>
        data:
          title: "⛽ Günstige Tankstelle"
          message: >
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'station_name') }}:
            €{{ state_attr('binary_sensor.my_car_near_cheap_station', 'price') }}/L,
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'distance') }} km
          data:
            # Makes notification visible in CarPlay/Android Auto
            importance: high
            channel: "fuel_alerts"
            ttl: 0
            priority: high
            # Action to navigate
            actions:
              - action: "NAVIGATE"
                title: "🧭 Navigieren"
                uri: "{{ state_attr('binary_sensor.my_car_near_cheap_station', 'navigation_urls')['google_maps'] }}"
      
      # Voice announcement (if TTS is configured)
      - service: tts.google_translate_say
        data:
          entity_id: media_player.car_audio  # or your car's media player
          message: >
            Günstige Tankstelle in der Nähe.
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'station_name') }},
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'distance') | round(1) }} Kilometer entfernt,
            Preis {{ state_attr('binary_sensor.my_car_near_cheap_station', 'price') }} Euro pro Liter.
```

**Note**: For CarPlay/Android Auto:
- Use `importance: high` and `priority: high`
- Keep messages concise
- Use clear action buttons
- Consider voice announcements for safety

---

## Advanced: Combined with Tank Level

Only alert when tank is low and you're near a cheap station:

```yaml
automation:
  - alias: "Smart Fuel Alert"
    description: "Alert only when tank is low AND near cheap station"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_near_cheap_station
        to: "on"
    condition:
      - condition: or
        conditions:
          # Tank below 25%
          - condition: numeric_state
            entity_id: sensor.my_car_tank_level_percentage
            below: 25
          # Range below 100 km
          - condition: numeric_state
            entity_id: sensor.my_car_range
            below: 100
    action:
      - service: notify.mobile_app_<your_device>
        data:
          title: "⚠️ Tank Low - Cheap Station Nearby!"
          message: >
            Tank: {{ states('sensor.my_car_tank_level_percentage') }}%
            ({{ states('sensor.my_car_range') }} km)
            
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'alert_message') }}
          data:
            importance: high
            tag: "low_fuel_cheap_station"
            actions:
              - action: "NAVIGATE"
                title: "Navigate Now"
                uri: "{{ state_attr('binary_sensor.my_car_near_cheap_station', 'navigation_urls')['google_maps'] }}"
```

---

## Using the Entities

### Available Sensors

**Binary Sensor: Proximity Alert**
- `binary_sensor.{vehicle_name}_near_cheap_station`
- State: `on` when near a cheap station, `off` otherwise
- Attributes:
  - `station_name`: Name of the station
  - `station_address`: Full address
  - `distance`: Distance in km
  - `price`: Fuel price per liter
  - `fuel_type`: Type of fuel (e5, e10, diesel)
  - `brand`: Station brand
  - `is_open`: Whether station is currently open
  - `proximity_threshold_km`: Configured threshold
  - `navigation_urls`: Dict with Google Maps, Apple Maps, Waze links
  - `alert_message`: Pre-formatted alert message

**Sensor: Nearby Cheap Stations**
- `sensor.{vehicle_name}_nearby_cheap_stations`
- State: Number of cheap stations found
- Attributes:
  - `stations`: List of N cheapest stations with details
  - `search_radius_km`: Search radius used
  - `vehicle_latitude`: Current vehicle latitude
  - `vehicle_longitude`: Current vehicle longitude
  - `max_stations`: Maximum stations to track

### Configuration Entities

**Numbers:**
- `number.{vehicle_name}_proximity_alert_distance` (0.1-10 km, default: 1.5)
- `number.{vehicle_name}_cheap_stations_count` (1-20, default: 5)
- `number.{vehicle_name}_cheap_stations_radius` (1-50 km, default: 15)
- `number.{vehicle_name}_min_tank_level_for_alerts` (0-100%, default: 30)

**Switch:**
- `switch.{vehicle_name}_proximity_alerts` (Enable/disable proximity alerts)

---

## Dashboard Card Example

Display nearby cheap stations in Lovelace:

```yaml
type: entities
title: Nearby Cheap Stations
entities:
  - entity: sensor.my_car_nearby_cheap_stations
    name: Stations Found
  - entity: binary_sensor.my_car_near_cheap_station
    name: Near Cheap Station
  - entity: switch.my_car_proximity_alerts
    name: Enable Alerts
  - type: divider
  - entity: number.my_car_proximity_alert_distance
    name: Alert Distance
  - entity: number.my_car_cheap_stations_count
    name: Stations to Track
  - entity: number.my_car_cheap_stations_radius
    name: Search Radius
  - entity: number.my_car_min_tank_level_for_alerts
    name: Min Tank Level
```

**Conditional Card for Active Alert:**

```yaml
type: conditional
conditions:
  - entity: binary_sensor.my_car_near_cheap_station
    state: "on"
card:
  type: markdown
  content: |
    ## ⛽ Cheap Station Nearby!
    
    **{{ state_attr('binary_sensor.my_car_near_cheap_station', 'station_name') }}**
    
    💰 Price: €{{ state_attr('binary_sensor.my_car_near_cheap_station', 'price') }}/L
    📏 Distance: {{ state_attr('binary_sensor.my_car_near_cheap_station', 'distance') }} km
    📫 {{ state_attr('binary_sensor.my_car_near_cheap_station', 'station_address') }}
    
    [🧭 Navigate]({{ state_attr('binary_sensor.my_car_near_cheap_station', 'navigation_urls')['google_maps'] }})
```

---

## Important Notes

### Vehicle Position Requirement

⚠️ **The integration ONLY uses your vehicle's position entity** (configured in setup). It **NEVER** uses Home Assistant's local coordinates as a fallback. If your vehicle's position is not available:
- Geolocation features will be disabled
- No proximity alerts will trigger
- The nearby cheap stations sensor will show 0 stations

Make sure your vehicle's device_tracker is properly configured and updating.

### Anti-Spam Mechanism

The integration includes built-in anti-spam to prevent notification overload:

1. **Cooldown Period**: 30 minutes between alerts for the same station
2. **Hysteresis**: Must move 30% farther away (beyond threshold × 1.3) to reset alert state

This means if you drive past a station and don't stop, you won't get repeated alerts for it.

### Tank Level Filter

By default, proximity alerts only trigger when your tank is below 30%. You can adjust this with `number.my_car_min_tank_level_for_alerts` or set it to 0 to always alert regardless of tank level.

---

## Troubleshooting

**No alerts triggering?**
1. Check `switch.my_car_proximity_alerts` is `on`
2. Verify vehicle position entity is updating
3. Check tank level is below configured threshold
4. Ensure you're within the proximity alert distance

**Too many alerts?**
1. Increase `number.my_car_proximity_alert_distance` to reduce sensitivity
2. Increase `number.my_car_min_tank_level_for_alerts` to only alert when tank is lower

**Want more stations?**
1. Increase `number.my_car_cheap_stations_count` (up to 20)
2. Increase `number.my_car_cheap_stations_radius` (up to 50 km)

---

## See Also

- [GEOLOCATION_CONCEPT.md](GEOLOCATION_CONCEPT.md) - Full technical concept
- [GEOLOCATION_ARCHITECTURE.md](GEOLOCATION_ARCHITECTURE.md) - Architecture diagrams
- [VEHICLE_ENTITIES.md](VEHICLE_ENTITIES.md) - Vehicle entity setup
