# Geolocation Feature - Visual Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HOME ASSISTANT                                    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     Vehicle Position Tracking                       │ │
│  │                                                                     │ │
│  │  📱 device_tracker.my_car                                          │ │
│  │     Lat: 50.000000, Lon: 10.000000                                 │ │
│  │     Speed: 45 km/h                                                 │ │
│  │     Update: every 30-60s (when moving)                             │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                  │                                       │
│                                  ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              Geolocation Coordinator                                │ │
│  │                                                                     │ │
│  │  🔄 Two-Tier Update Strategy:                                      │ │
│  │                                                                     │ │
│  │  ┌─────────────────────┐      ┌──────────────────────┐            │ │
│  │  │ API Update          │      │ Proximity Check       │            │ │
│  │  │ Every 10-15 min     │      │ Every 30-60s          │            │ │
│  │  │                     │      │                       │            │ │
│  │  │ • Fetch stations    │      │ • Calculate distance  │            │ │
│  │  │ • Sort by price     │      │ • Check threshold     │            │ │
│  │  │ • Select top N      │      │ • Anti-spam logic     │            │ │
│  │  │ • Cache in memory   │      │ • Trigger alerts      │            │ │
│  │  └─────────────────────┘      └──────────────────────┘            │ │
│  │           │                              │                         │ │
│  └───────────┼──────────────────────────────┼─────────────────────────┘ │
│              │                              │                           │
│              ▼                              ▼                           │
│  ┌──────────────────────────┐  ┌─────────────────────────────────────┐ │
│  │ 📊 Sensors               │  │ 🔔 Binary Sensors                   │ │
│  │                          │  │                                     │ │
│  │ nearby_cheap_stations    │  │ near_cheap_station                  │ │
│  │                          │  │                                     │ │
│  │ State: 5                 │  │ State: on                           │ │
│  │                          │  │                                     │ │
│  │ Attributes:              │  │ Attributes:                         │ │
│  │ • stations: [...]        │  │ • station_name: "Shell ABC"        │ │
│  │ • search_radius: 15 km   │  │ • distance_km: 1.2                 │ │
│  │ • vehicle_lat: 50.00     │  │ • price: 1.589                     │ │
│  │ • vehicle_lon: 10.00     │  │ • alert_message: "🚗 Cheap..."     │ │
│  └──────────────────────────┘  └─────────────────────────────────────┘ │
│                                              │                           │
│                                              ▼                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                        Automations                                │  │
│  │                                                                   │  │
│  │  Trigger: binary_sensor.near_cheap_station → "on"                │  │
│  │  Condition: tank_level < 30%                                     │  │
│  │  Action: notify.telegram / notify.mobile_app                     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                              │                           │
└──────────────────────────────────────────────┼───────────────────────────┘
                                               │
                                               ▼
                              ┌────────────────────────────┐
                              │  📱 User Notification       │
                              │                            │
                              │  🚗 Cheap station nearby!  │
                              │  📍 Shell ABC (1.2 km)     │
                              │  💰 €1.589/L (E10)         │
                              │  🧭 [Navigate]             │
                              └────────────────────────────┘
```

---

## Data Flow Timeline

```
Time    Vehicle Position    API Update           Proximity Check       Alert
────────────────────────────────────────────────────────────────────────────
00:00   Lat: 50.00, Lon: 10.00
        Speed: 0 km/h       Fetch stations       No close stations     -
                            (Radius: 15 km)
                            Found: 5 cheap
                            ┌─────────────┐
                            │ 1. Shell    │
                            │    1.589 €  │
                            │    5.2 km   │
                            │ 2. Aral     │
                            │    1.599 €  │
                            │    3.8 km   │
                            │ 3. Esso     │
                            │    1.609 €  │
                            │    7.1 km   │
                            └─────────────┘

00:30   Lat: 50.01, Lon: 10.01
        Speed: 45 km/h      (cached data)        Distance to Aral:     -
                                                  2.5 km
                                                  > threshold (1.5 km)

01:00   Lat: 50.015, Lon: 10.02
        Speed: 50 km/h      (cached data)        Distance to Aral:     -
                                                  1.8 km
                                                  > threshold

01:30   Lat: 50.018, Lon: 10.03
        Speed: 45 km/h      (cached data)        Distance to Aral:     🔔 ALERT!
                                                  1.3 km                Triggered
                                                  < threshold (1.5 km)  
                                                  
                                                  Cooldown: 30 min
                                                  started for Aral

02:00   Lat: 50.020, Lon: 10.04
        Speed: 50 km/h      (cached data)        Distance to Aral:     -
                                                  2.1 km                (cooldown)
                                                  > threshold * 1.3
                                                  
                                                  Alert deactivated

10:00   (new API update)    Fetch stations       -                     -
                            (prices changed)
                            Found: 5 cheap
                            (new sorting)
```

---

## Configuration UI

```
┌──────────────────────────────────────────────────────────────┐
│  Geolocation Settings                                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ☑ Enable Geolocation Features                              │
│                                                               │
│  Number of cheap stations to track:                          │
│  ┌────┐                                                       │
│  │ 5  │ ◄──────────────── (1-20)                            │
│  └────┘                                                       │
│                                                               │
│  Search radius for cheap stations:                           │
│  ┌────┐ km                                                    │
│  │ 15 │ ◄──────────────── (1-50 km)                         │
│  └────┘                                                       │
│                                                               │
│  Proximity alert distance:                                   │
│  ┌────┐ km                                                    │
│  │1.5 │ ◄──────────────── (0.1-10 km)                       │
│  └────┘                                                       │
│                                                               │
│  Only alert when tank below:                                 │
│  ┌────┐ %                                                     │
│  │ 30 │ ◄──────────────── (0-100%)                          │
│  └────┘                                                       │
│                                                               │
│  [ Save ]  [ Cancel ]                                        │
└──────────────────────────────────────────────────────────────┘
```

---

## Entity Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  sensor.my_car_nearby_cheap_stations                            │
├─────────────────────────────────────────────────────────────────┤
│  State: 5                                                       │
│                                                                 │
│  Attributes:                                                    │
│  {                                                              │
│    "stations": [                                                │
│      {                                                          │
│        "id": "abc123",                                          │
│        "name": "Shell Tankstelle",                             │
│        "brand": "Shell",                                        │
│        "address": "Hauptstraße 123, 12345 Berlin",             │
│        "latitude": 50.000000,                                   │
│        "longitude": 10.000000,                                  │
│        "distance_km": 3.2,                                      │
│        "price": 1.589,                                          │
│        "fuel_type": "e10",                                      │
│        "is_open": true,                                         │
│        "google_maps_url": "https://maps.google.com/?q=...",    │
│        "apple_maps_url": "http://maps.apple.com/?q=...",       │
│        "waze_url": "https://waze.com/ul?q=..."                 │
│      },                                                         │
│      { ... 4 more stations ... }                               │
│    ],                                                           │
│    "last_update": "2026-02-10T21:47:12Z",                      │
│    "search_radius_km": 15,                                      │
│    "vehicle_latitude": 50.01,                                   │
│    "vehicle_longitude": 10.00,                                  │
│    "max_stations": 5                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  binary_sensor.my_car_near_cheap_station                        │
├─────────────────────────────────────────────────────────────────┤
│  State: on                                                      │
│                                                                 │
│  Attributes:                                                    │
│  {                                                              │
│    "station_name": "Shell Tankstelle",                         │
│    "station_address": "Hauptstraße 123, 12345 Berlin",         │
│    "distance_km": 1.2,                                          │
│    "price": 1.589,                                              │
│    "fuel_type": "e10",                                          │
│    "proximity_threshold_km": 1.5,                               │
│    "station_details": { ... full station object ... },         │
│    "navigation_urls": {                                         │
│      "google_maps": "https://maps.google.com/?q=...",          │
│      "apple_maps": "http://maps.apple.com/?q=...",             │
│      "waze": "https://waze.com/ul?q=..."                       │
│    },                                                           │
│    "alert_message": "🚗 Günstige Tankstelle in der Nähe!\n    │
│                      📍 Shell Tankstelle (1.2 km entfernt)\n   │
│                      💰 Preis: €1.589/L (E10)\n                │
│                      🧭 Navigation: [Link]"                     │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Performance Characteristics

```
┌──────────────────────────────────────────────────────────────────┐
│  Performance Metrics                                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  API Calls:                                                       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Frequency:  1 call per 10-15 minutes                       │  │
│  │ Rate:       ~6 calls/hour, 144 calls/day                   │  │
│  │ Limit:      ~10 calls/minute (Tankerkönig)                 │  │
│  │ Status:     ✅ Well within limits                           │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  Proximity Checks:                                                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Frequency:  Every 30-60s (when moving)                     │  │
│  │             Every 5 min (when stationary)                  │  │
│  │ Calculation: Haversine distance for N stations             │  │
│  │ Time:       < 1ms for 10 stations                          │  │
│  │ Status:     ✅ Negligible CPU impact                        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  Memory Usage:                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Cached stations: ~1 KB per station                         │  │
│  │ Total (10 stations): ~10 KB                                │  │
│  │ Alert history: ~0.5 KB per entry                           │  │
│  │ Total: ~15-20 KB                                           │  │
│  │ Status:     ✅ Minimal memory footprint                     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  Battery Impact (smartphone GPS):                                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Updates:    30-60s intervals (HA Companion App default)    │  │
│  │ Impact:     Moderate (normal for navigation)               │  │
│  │ Mitigation: Adaptive updates (slower when stationary)      │  │
│  │ Status:     ⚠️  User should be aware, opt-in recommended   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Example Scenario Walkthrough

```
📍 Scenario: Commute to Work
──────────────────────────────────────────────────────────────────

07:00 - Start of Day
├─ Vehicle: At home, Tank: 25%
├─ Geolocation: Enabled
└─ System: Fetches 5 cheapest stations within 15 km
   ┌────────────────────────────────────┐
   │ 1. Esso (8.2 km)    - €1.589/L    │
   │ 2. Shell (5.1 km)   - €1.599/L    │
   │ 3. Aral (12.3 km)   - €1.609/L    │
   │ 4. Total (9.8 km)   - €1.619/L    │
   │ 5. Jet (14.5 km)    - €1.629/L    │
   └────────────────────────────────────┘

07:15 - Driving to Work
├─ Position: Moving at 50 km/h
├─ Proximity: Checking every 30s
└─ Distance to Shell: 3.2 km (no alert, > 1.5 km)

07:22 - Approaching Shell Station
├─ Position: Still moving
├─ Distance to Shell: 1.3 km
└─ 🔔 ALERT TRIGGERED!
   📱 Notification sent:
   "🚗 Günstige Tankstelle in der Nähe!
    📍 Shell (1.3 km entfernt)
    💰 Preis: €1.599/L (E10)
    🧭 [Navigation starten]"

07:23 - User Decision
├─ Option 1: Tap "Navigation" → Google Maps opens
├─ Option 2: Tap "Ignore" → Cooldown activated (30 min)
└─ User chooses: Ignore (in a hurry)

07:25 - Passed Station
├─ Distance to Shell: 2.5 km (moved away)
├─ Alert deactivated (distance > threshold * 1.3)
└─ Cooldown: Still active for Shell (28 min remaining)

17:00 - Return from Work
├─ Same route
├─ Distance to Shell: 1.1 km
└─ ⏸️  NO ALERT (cooldown still active from morning)

17:30 - Cooldown Expired
├─ System: Shell cooldown cleared
└─ Ready for new alerts

Next Day 08:00 - New Commute
├─ Distance to Shell: 1.2 km
└─ 🔔 NEW ALERT (cooldown expired)
   User decides to refuel this time!
```

---

## Success Criteria

```
✅ Feature is successful when:

1. Accuracy
   ├─ Finds cheapest stations within configured radius (100% accuracy)
   ├─ Distance calculations accurate within ±50 meters
   └─ Alerts trigger at correct threshold (±100 meters)

2. Performance
   ├─ API calls respect rate limits (< 10/min)
   ├─ Proximity checks complete in < 100ms
   └─ Memory usage < 50 KB

3. Usability
   ├─ No spam notifications (cooldown works)
   ├─ Alerts are timely (1-2 min reaction time at 50 km/h)
   └─ Configuration is intuitive (sensible defaults)

4. Reliability
   ├─ Works offline (uses cached data)
   ├─ Handles missing GPS data gracefully
   └─ Recovers from API errors automatically

5. Integration
   ├─ Works with existing automations
   ├─ Compatible with Telegram, HA Companion App
   └─ Can be disabled without affecting other features
```

---

**See full concept documents for detailed specifications!**
- `docs/GEOLOCATION_CONCEPT.md` (German)
- `docs/GEOLOCATION_CONCEPT_EN.md` (English)
- `docs/GEOLOCATION_SUMMARY.md` (Quick Summary)
