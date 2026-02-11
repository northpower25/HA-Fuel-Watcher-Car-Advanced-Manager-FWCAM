# Geolocation-Based Fuel Station Proximity - Quick Start

## 🎯 What is this?

This feature automatically finds the cheapest fuel stations near your vehicle and alerts you when you're driving close to one. Perfect for saving money while on the road!

## ✨ Features

- **📍 Smart Station Tracking**: Finds N cheapest stations within a configurable radius of your vehicle
- **🔔 Proximity Alerts**: Notifies you when you're near a cheap station
- **🚗 Vehicle Position Based**: Uses YOUR vehicle's GPS location (never uses home coordinates)
- **🧠 Anti-Spam**: Smart cooldown prevents notification overload
- **📱 Mobile Optimized**: Works great with Home Assistant Companion App, CarPlay, and Android Auto
- **🧭 Navigation Ready**: Includes Google Maps, Apple Maps, and Waze links

## 📋 Prerequisites

Before using this feature, you need:

1. **Vehicle Position Entity**: A `device_tracker` entity configured in the integration setup
   - Can be from HA Companion App, OwnTracks, or any device tracker
   - Must provide latitude/longitude attributes

2. **Tankerkönig API**: Already configured (part of base integration)

3. **Optional**: Tank level sensor for smart filtering

## 🚀 Quick Setup

### Step 1: Enable Proximity Alerts

Turn on the proximity alerts switch:

```yaml
# In Home Assistant UI or via service call
switch.my_car_proximity_alerts: on
```

Or via service:
```yaml
service: switch.turn_on
target:
  entity_id: switch.my_car_proximity_alerts
```

### Step 2: Configure Alert Settings (Optional)

Adjust these numbers to your preference:

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| Proximity Alert Distance | 1.5 km | 0.1-10 km | How close before alerting |
| Cheap Stations Count | 5 | 1-20 | How many cheap stations to track |
| Cheap Stations Radius | 15 km | 1-50 km | Search radius for cheap stations |
| Min Tank Level for Alerts | 30% | 0-100% | Only alert when tank below this |

### Step 3: Create Automation

Basic example for mobile notification:

```yaml
automation:
  - alias: "Alert: Near Cheap Station"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_near_cheap_station
        to: "on"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "⛽ Cheap Fuel Nearby!"
          message: >
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'alert_message') }}
          data:
            actions:
              - action: "NAVIGATE"
                title: "🧭 Navigate"
                uri: "{{ state_attr('binary_sensor.my_car_near_cheap_station', 'navigation_urls')['google_maps'] }}"
```

## 📊 Available Entities

### Sensors

**Binary Sensor: Near Cheap Station**
- `binary_sensor.{vehicle}_near_cheap_station`
- Shows `on` when you're within alert distance of a cheap station
- Includes all station details in attributes

**Sensor: Nearby Cheap Stations**
- `sensor.{vehicle}_nearby_cheap_stations`
- Shows number of cheap stations found
- Lists all stations with details in attributes

### Configuration

**Numbers:**
- `number.{vehicle}_proximity_alert_distance`
- `number.{vehicle}_cheap_stations_count`
- `number.{vehicle}_cheap_stations_radius`
- `number.{vehicle}_min_tank_level_for_alerts`

**Switch:**
- `switch.{vehicle}_proximity_alerts`

## 💡 Use Cases

### 1. CarPlay/Android Auto Alert

Get voice and visual alerts while driving:

```yaml
automation:
  - alias: "CarPlay Voice Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_near_cheap_station
        to: "on"
    action:
      # Visual notification
      - service: notify.mobile_app_iphone
        data:
          title: "⛽ Günstige Tankstelle"
          message: >
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'station_name') }}:
            €{{ state_attr('binary_sensor.my_car_near_cheap_station', 'price') }}/L
          data:
            importance: high
            actions:
              - action: "NAVIGATE"
                title: "Navigate"
      
      # Voice announcement
      - service: tts.google_say
        target:
          entity_id: media_player.car_audio
        data:
          message: >
            Günstige Tankstelle in der Nähe.
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'distance') | round(1) }} Kilometer entfernt.
```

### 2. Only Alert When Tank is Low

Smart alerts based on fuel level:

```yaml
automation:
  - alias: "Low Fuel + Cheap Station"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_near_cheap_station
        to: "on"
    condition:
      - condition: numeric_state
        entity_id: sensor.my_car_tank_level_percentage
        below: 25
    action:
      - service: notify.telegram
        data:
          message: "⚠️ Tank low and cheap station nearby! {{ state_attr('binary_sensor.my_car_near_cheap_station', 'alert_message') }}"
```

### 3. Show on Dashboard

Display when alert is active:

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
    
    💰 €{{ state_attr('binary_sensor.my_car_near_cheap_station', 'price') }}/L
    📏 {{ state_attr('binary_sensor.my_car_near_cheap_station', 'distance') }} km
    
    [Navigate]({{ state_attr('binary_sensor.my_car_near_cheap_station', 'navigation_urls')['google_maps'] }})
```

## 🔧 How It Works

### Two-Tier Update Strategy

The integration uses a smart update strategy to balance responsiveness and API rate limits:

1. **API Updates** (every 10-15 minutes):
   - Fetches fresh station list and prices
   - Uses configured `cheap_stations_radius`

2. **Proximity Checks** (every 30-60 seconds):
   - Only calculates distance to already-fetched stations
   - Very fast, no API calls needed

### Anti-Spam Mechanism

Prevents notification fatigue:

1. **Cooldown**: 30 minutes between alerts for the same station
2. **Hysteresis**: Must move 30% farther away to reset alert

Example: If alert distance is 1.5 km:
- Alert triggers at ≤ 1.5 km
- Alert resets only after moving > 1.95 km away (1.5 × 1.3)

### Vehicle Position Only

⚠️ **Important**: This feature **ONLY** uses your vehicle's position entity. It **NEVER** uses Home Assistant's home coordinates. If vehicle position is unavailable, geolocation features are disabled.

## 🎨 CarPlay & Android Auto Tips

For best experience in your car:

1. **Use High Priority Notifications**:
   ```yaml
   data:
     importance: high
     priority: high
     ttl: 0
   ```

2. **Keep Messages Concise**: CarPlay/Android Auto have limited screen space

3. **Add Clear Actions**: Make navigation buttons obvious
   ```yaml
   actions:
     - action: "NAVIGATE"
       title: "🧭 Navigate"
   ```

4. **Consider Voice**: Add TTS announcements for safety
   ```yaml
   service: tts.google_translate_say
   target:
     entity_id: media_player.car_audio
   ```

5. **Test While Parked**: Always test notifications before driving

## 🐛 Troubleshooting

### No Alerts Triggering?

1. ✅ Check `switch.my_car_proximity_alerts` is ON
2. ✅ Verify vehicle position entity is updating (check attributes)
3. ✅ Ensure tank level < configured threshold
4. ✅ Check you're within proximity alert distance

### Too Many Alerts?

- Increase `number.my_car_proximity_alert_distance`
- Increase `number.my_car_min_tank_level_for_alerts`
- Check automation conditions

### Vehicle Position Not Working?

1. Verify device_tracker entity exists
2. Check it has `latitude` and `longitude` attributes
3. Ensure it's updating regularly (check state change history)

### No Nearby Cheap Stations Found?

- Increase `number.my_car_cheap_stations_radius`
- Check you're in an area covered by Tankerkönig (Germany only)
- Verify API is working (check main fuel price sensor)

## 📚 Advanced Configuration

See [GEOLOCATION_AUTOMATION_EXAMPLES.md](GEOLOCATION_AUTOMATION_EXAMPLES.md) for:
- Advanced automation examples
- Telegram integration
- Multi-condition alerts
- Custom dashboard cards

## ❓ FAQ

**Q: Does this work when I'm not at home?**  
A: Yes! It uses your vehicle's actual GPS position, not your home location.

**Q: Will I get spammed with alerts?**  
A: No. The anti-spam mechanism prevents repeated alerts for the same station.

**Q: Can I use this outside Germany?**  
A: Currently only works with Tankerkönig API (Germany). Future versions may support other providers.

**Q: Does this drain my phone battery?**  
A: Minimal impact. The integration uses efficient distance calculations and doesn't poll your phone directly.

**Q: Can I get alerts even when tank is full?**  
A: Yes, set `number.my_car_min_tank_level_for_alerts` to 0.

**Q: How accurate is the distance?**  
A: Very accurate. Uses Haversine formula for GPS distance calculation (typically within 5-10 meters).

## 🔐 Privacy

- All processing is **local** on your Home Assistant instance
- Vehicle position is **never** sent to external servers
- Only Tankerkönig API receives your search coordinates (required for station lookup)
- No tracking, no cloud storage, no data sharing

## 📖 Further Reading

- [GEOLOCATION_CONCEPT.md](GEOLOCATION_CONCEPT.md) - Detailed technical concept
- [GEOLOCATION_ARCHITECTURE.md](GEOLOCATION_ARCHITECTURE.md) - System architecture
- [GEOLOCATION_AUTOMATION_EXAMPLES.md](GEOLOCATION_AUTOMATION_EXAMPLES.md) - More examples
- [VEHICLE_ENTITIES.md](VEHICLE_ENTITIES.md) - Vehicle entity setup guide

---

**Ready to save money on fuel? Enable proximity alerts and hit the road! 🚗⛽**
