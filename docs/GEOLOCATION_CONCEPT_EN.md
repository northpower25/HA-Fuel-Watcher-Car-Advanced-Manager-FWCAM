# Geolocation-Based Fuel Station Proximity Notification - Concept

**Version:** 1.0  
**Date:** 2026-02-10  
**Status:** Concept / Planning

---

## Executive Summary

This document describes the concept for a geolocation-based feature that automatically finds the cheapest fuel stations near the vehicle and notifies the user when the vehicle approaches one of these stations.

---

## 1. Requirements

### 1.1 Functional Requirements

1. **Station Selection:**
   - Find the N cheapest fuel stations within a configurable radius of the current vehicle position
   - Configurable number of cheapest stations to track (e.g., Top 3, 5, or 10)
   - Configurable search radius for geolocation (e.g., 5-25 km)
   - Consider fuel type (E5, E10, Diesel)
   - Optional: Filter by opening hours (only open stations)

2. **Proximity Detection:**
   - Continuous monitoring of vehicle position
   - Detection when vehicle approaches a pre-selected cheap station
   - Configurable threshold for proximity detection (e.g., 500m, 1km, 2km)
   - Spam notification prevention (cooldown mechanism)

3. **Notification Function:**
   - Write warning/notification to a dedicated entity
   - Entity can be used for notify automations (Telegram, HA Companion App, etc.)
   - Provide useful information: Name, address, price, distance, navigation URLs

4. **Configurability:**
   - Number of cheap stations to track
   - Search radius for station selection
   - Proximity threshold for notifications
   - Update interval for position and station data
   - Optional: Only notify when tank is below a certain level

---

## 2. Technical Architecture

### 2.1 New Entities

#### 2.1.1 Sensor: Nearby Cheap Stations
- **Entity Type:** `sensor.{vehicle_name}_nearby_cheap_stations`
- **State:** Number of found cheap stations
- **Attributes:**
  - `stations`: List of N cheapest stations with full details:
    ```json
    [
      {
        "id": "station_uuid",
        "name": "Gas Station ABC",
        "brand": "Brand Name",
        "address": "Street 123, 12345 City",
        "latitude": 52.520008,
        "longitude": 13.404954,
        "distance_km": 3.2,
        "price": 1.589,
        "fuel_type": "e10",
        "is_open": true,
        "google_maps_url": "...",
        "apple_maps_url": "...",
        "waze_url": "..."
      }
    ]
    ```
  - `last_update`: Timestamp of last update
  - `search_radius_km`: Used search radius
  - `vehicle_latitude`: Current vehicle position (Lat)
  - `vehicle_longitude`: Current vehicle position (Lon)
  - `max_stations`: Configured number of stations to track

#### 2.1.2 Binary Sensor: Proximity Alert
- **Entity Type:** `binary_sensor.{vehicle_name}_near_cheap_station`
- **State:** `on` when near a cheap station, otherwise `off`
- **Device Class:** `presence` or `proximity`
- **Attributes:**
  - `station_name`: Name of nearby station
  - `station_address`: Address
  - `distance_km`: Current distance
  - `price`: Current price
  - `fuel_type`: Fuel type
  - `proximity_threshold_km`: Used threshold
  - `station_details`: Complete station details (as above)
  - `navigation_urls`: Object with Google Maps, Apple Maps, Waze URLs
  - `alert_message`: Ready-made message for notifications, e.g.:
    ```
    "🚗 Cheap gas station nearby!
    📍 Gas Station ABC (1.2 km away)
    💰 Price: €1.589/L (E10)
    🧭 Navigate: [Link]"
    ```

#### 2.1.3 Number: Proximity Threshold
- **Entity Type:** `number.{vehicle_name}_proximity_alert_distance`
- **Min:** 0.1 km
- **Max:** 10.0 km
- **Default:** 1.5 km
- **Step:** 0.1 km
- **Purpose:** Configurable distance for proximity alert

#### 2.1.4 Number: Cheap Stations Count
- **Entity Type:** `number.{vehicle_name}_cheap_stations_count`
- **Min:** 1
- **Max:** 20
- **Default:** 5
- **Step:** 1
- **Purpose:** Number of cheap stations to track

#### 2.1.5 Number: Cheap Stations Radius
- **Entity Type:** `number.{vehicle_name}_cheap_stations_radius`
- **Min:** 1 km
- **Max:** 50 km
- **Default:** 15 km
- **Step:** 1 km
- **Purpose:** Search radius for cheap stations

#### 2.1.6 Switch: Enable Proximity Alerts
- **Entity Type:** `switch.{vehicle_name}_proximity_alerts`
- **Default:** `on`
- **Purpose:** Enable/disable proximity alerts

### 2.2 Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   Vehicle Position (GPS)                        │
│                  (device_tracker entity)                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Geolocation Service / Coordinator                  │
│  - Checks position every X seconds (e.g., 30-60s when moving) │
│  - Detects movement (speed > 5 km/h)                          │
└────────────┬───────────────────────────┬────────────────────────┘
             │                           │
             ▼                           ▼
┌────────────────────────┐  ┌───────────────────────────────────┐
│  Station Search        │  │   Proximity Check                 │
│  (every 5-10 min or    │  │   (every 30-60s)                  │
│   on position change)  │  │                                   │
│                        │  │ - Calculates distance to each     │
│ - API call to          │  │   cheap station                   │
│   Tankerkönig          │  │ - Checks against threshold        │
│ - Sort by price        │  │ - Triggers binary sensor          │
│ - Select top N         │  │ - Anti-spam logic                 │
└────────────┬───────────┘  └───────────┬───────────────────────┘
             │                           │
             ▼                           ▼
┌────────────────────────┐  ┌───────────────────────────────────┐
│ Sensor Update:         │  │ Binary Sensor Update:             │
│ nearby_cheap_stations  │  │ near_cheap_station                │
└────────────────────────┘  └───────────┬───────────────────────┘
                                        │
                                        ▼
                            ┌──────────────────────────────┐
                            │  Home Assistant Automation   │
                            │  - State Change Trigger      │
                            │  - Notify Service Call       │
                            └──────────────────────────────┘
```

---

## 3. Data Source Analysis

### 3.1 Vehicle Position (Latitude/Longitude)

**Current Implementation:**
- Position read from `device_tracker` entity (see `utils/vehicle_data.py`)
- Function: `async_get_device_tracker_coordinates()`
- Source: `CONF_POSITION_ENTITY` from configuration

**Suitability for Geolocation:**
✅ **Suitable**
- Position obtained directly from HA device_tracker
- Supports various trackers (e.g., HA Companion App, OwnTracks, etc.)
- Accuracy: GPS-based, typically 5-30m, sufficient for station search

**Timing & Updates:**
- Update frequency depends on device_tracker
- HA Companion App: Typically 30-60s when moving, longer when stationary
- OwnTracks: Configurable, can be very frequent (5-30s)
- For driving scenario: Usually 30-60s updates, **sufficient** for station proximity

**Recommendation:**
- ✅ No change to data source required
- ⚠️ Cache last position for offline robustness
- ⚠️ Calculate speed to detect movement/standstill
- ⚠️ Adaptive update strategy: Check more frequently when moving, less when stationary

### 3.2 Station Data (Tankerkönig API)

**Current Implementation:**
- API client: `providers/tankerkonig.py`
- Method: `async_fetch_stations()` - Searches stations in radius
- Update interval: Configurable via `CONF_UPDATE_INTERVAL` (1-60 min)
- Caching: Yes, via Coordinator update mechanism

**Suitability for Geolocation:**
✅ **Suitable with adjustments**
- API provides list of all stations in radius with prices and coordinates
- Data already contains: Name, address, Lat/Lon, price, status (open/closed)
- Haversine distance calculation already implemented

**Timing & Updates:**
- Current standard: 5-60 min (note: API rate limits!)
- **For geolocation:**
  - Cheap stations: Update every 10-15 min sufficient (prices don't change constantly)
  - Distance calculation: Should be more frequent (every 30-60s), but **only distance calc**, no API call!

**Recommendation:**
- ✅ Reuse existing API data
- ✅ **Two-tier approach:**
  1. **Slow API update** (every 10-15 min): Fetches list of cheap stations
  2. **Fast proximity check** (every 30-60s): Only calculates distance to known stations
- ✅ Cache top-N stations in memory/storage
- ⚠️ Respect API rate limits (Tankerkönig typically allows 1 request/min per IP)

### 3.3 Tank Level (Optional Filter)

**Current Implementation:**
- `CONF_TANK_LEVEL_ENTITY` provides current tank level
- Already used for refueling detection

**Suitability:**
✅ **Optionally usable**
- Could serve as filter: Only notify when tank < 30%
- Prevents unnecessary alerts with full tank

---

## 4. Accuracy vs. Speed

### 4.1 Driving Requirements

**Scenario:** Driver approaches cheap station at 50 km/h (≈ 14 m/s)

| Update Interval | Distance Traveled | Suitability          |
|-----------------|-------------------|----------------------|
| 10 seconds      | ~140 meters       | ⚠️ Might be too late |
| 30 seconds      | ~420 meters       | ✅ Acceptable        |
| 60 seconds      | ~840 meters       | ⚠️ Borderline        |
| 120 seconds     | ~1.68 km          | ❌ Too slow          |

**Recommendation:**
- **Proximity check:** Every 30-60 seconds
- **Advance warning:** With threshold of 1-2 km, driver has ~1-2 minutes reaction time
- **Dynamic adjustment:** Check more frequently at higher speeds (> 80 km/h)

### 4.2 Accuracy Requirements

**GPS Accuracy:**
- Typical: 5-30 meters (smartphone GPS)
- Sufficient for: Yes! Gas stations are large enough (50-100m access area)

**Distance Calculation:**
- Haversine formula: Accurate enough for < 50 km distances
- Already implemented in `providers/tankerkonig.py`

**Threshold Recommendation:**
- Minimum: 500 meters (urban)
- Recommended: 1.5 km (country road/highway)
- Maximum: 5 km (very high speed or rural area)

### 4.3 Performance Optimization

**Memory vs. Computation:**
1. **Caching:**
   - Store top-N cheap stations in memory
   - Only coordinates and critical data
   - Memory requirement: Minimal (< 10 KB for 10 stations)

2. **Distance Calculation:**
   - Haversine for N stations: Very fast (< 1ms for 10 stations)
   - Can easily run every 30s

3. **API Calls:**
   - Should NOT be more frequent than every 5-10 min
   - Respect rate limiting!

**Proposed Update Strategy:**
```python
# Pseudo-code
API_UPDATE_INTERVAL = 10 * 60  # 10 minutes
PROXIMITY_CHECK_INTERVAL_MOVING = 30  # 30 seconds when driving
PROXIMITY_CHECK_INTERVAL_STATIONARY = 300  # 5 minutes when stationary
MOVEMENT_THRESHOLD = 5  # km/h

if vehicle_speed > MOVEMENT_THRESHOLD:
    # Moving: Frequent proximity checks
    check_proximity_every(30 seconds)
else:
    # Stationary: Infrequent checks
    check_proximity_every(5 minutes)

# API calls independent of movement status
fetch_cheap_stations_every(10 minutes)
```

---

## 5. Implementation Proposal

### 5.1 New Components

#### 5.1.1 Geolocation Service (`utils/geolocation_service.py`)
```python
class GeolocationService:
    """Service for geolocation-based fuel station features."""
    
    async def find_cheap_stations(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        count: int,
        fuel_type: str
    ) -> list[FuelStation]:
        """Find the N cheapest stations in radius."""
        
    async def calculate_proximity(
        self,
        vehicle_lat: float,
        vehicle_lon: float,
        stations: list[FuelStation],
        threshold_km: float
    ) -> FuelStation | None:
        """Check if vehicle is near a station."""
        
    def is_vehicle_moving(
        self,
        previous_position: tuple,
        current_position: tuple,
        time_delta: float
    ) -> bool:
        """Detect if vehicle is moving."""
```

#### 5.1.2 Geolocation Coordinator (`geolocation_coordinator.py`)
```python
class GeolocationCoordinator(DataUpdateCoordinator):
    """Coordinator for geolocation updates."""
    
    def __init__(self, ...):
        # Two update intervals:
        # - API update: 10 min (fetches cheap stations)
        # - Proximity check: 30-60s (checks distance)
        
    async def _async_update_data(self):
        """Performs updates based on timing."""
        # Distinguishes between API update and proximity check
```

#### 5.1.3 New Sensors
- `GeolocationCheapStationsSensor`: List of cheap stations
- `GeolocationProximityBinarySensor`: Proximity alert
- Corresponding Number/Switch entities for configuration

### 5.2 Configuration

**Config Flow Extension:**
- New step: "Geolocation Settings" (optional)
- Fields:
  - Enable Geolocation Features (Boolean)
  - Number of cheap stations to track (1-20, default: 5)
  - Search radius for cheap stations (1-50 km, default: 15)
  - Proximity alert distance (0.1-10 km, default: 1.5)
  - Only alert when tank below % (0-100, default: 30)

**Options Flow Extension:**
- All above settings should be changeable
- Plus: Enable/Disable Geolocation

### 5.3 Anti-Spam Mechanism

**Problem:** Avoiding spam notifications
- Driver passes station → Alert
- Drives away → Alert off
- Drives back → Alert (Spam!)

**Solution: Cooldown + Hysteresis**
```python
ALERT_COOLDOWN = 30 * 60  # 30 minutes
HYSTERESIS_FACTOR = 1.3  # 30% more distance to deactivate

if distance < threshold:
    if not alerted_recently(station_id, ALERT_COOLDOWN):
        trigger_alert()
elif distance > threshold * HYSTERESIS_FACTOR:
    deactivate_alert()
```

**Additionally:**
- Track per station when last alerted
- Persistent storage in Storage
- Optional: Automatically reset all alerts after refueling

### 5.4 Automation Examples

**Example 1: Telegram Notification**
```yaml
automation:
  - alias: "Notify about nearby cheap station"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_near_cheap_station
        to: "on"
    condition:
      - condition: numeric_state
        entity_id: sensor.my_car_tank_level
        below: 30  # Only when tank below 30%
    action:
      - service: notify.telegram
        data:
          message: >
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'alert_message') }}
```

**Example 2: HA Companion App Notification with Action**
```yaml
automation:
  - alias: "Cheap station proximity alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_near_cheap_station
        to: "on"
    action:
      - service: notify.mobile_app_smartphone
        data:
          title: "Cheap gas station nearby!"
          message: >
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'station_name') }}
            - {{ state_attr('binary_sensor.my_car_near_cheap_station', 'distance_km') }} km
            - €{{ state_attr('binary_sensor.my_car_near_cheap_station', 'price') }}/L
          data:
            actions:
              - action: "NAVIGATE"
                title: "Start Navigation"
                uri: >
                  {{ state_attr('binary_sensor.my_car_near_cheap_station', 'navigation_urls').google_maps }}
              - action: "IGNORE"
                title: "Ignore"
```

---

## 6. Additional Ideas and Features

### 6.1 Route-based Optimization
**Idea:** Consider not only current position but planned route
- Integration with navigation (Google Maps, Apple Maps)
- Search stations along route
- Prioritize by: Price + detour in minutes

**Challenge:**
- Requires route data (not standard in HA)
- Complex calculation
- Possibly external API (Google Directions, OSRM)

**Assessment:** 🔶 Medium-term feature, not for MVP

### 6.2 Station Preferences
**Idea:** User can prefer or exclude station brands
- Favorites list (e.g., "Only Shell and Esso")
- Blacklist (e.g., "Never station XY")

**Implementation:**
- New configuration option
- Filtering in `find_cheap_stations()`

**Assessment:** ✅ Easy to implement, useful for loyalty programs

### 6.3 Time-based Optimization
**Idea:** Learn price patterns and recommend best refueling time
- "Station X is usually 5 cents cheaper in evening"
- ML-based prediction

**Implementation:**
- Extension of existing ML engine
- Historical price data per station

**Assessment:** 🔶 Interesting but complex. Long-term feature.

### 6.4 Integration with Tank Size and Range
**Idea:** Intelligent alerts based on range
- "You have 150km range, cheap station in 20km"
- Calculate if station is reachable

**Implementation:**
- Use existing range data
- Simple comparison logic

**Assessment:** ✅ Useful and simple! Should be in MVP.

### 6.5 Price History and Trends per Station
**Idea:** Show price history of cheap stations
- "This station was 8 cents more expensive last week"
- Trend arrows (↗️ ↘️ →)

**Implementation:**
- Extend storage with price history per station
- New sensor attributes

**Assessment:** ✅ Useful, moderate complexity. Good-to-have for MVP.

---

## 7. Risks and Challenges

### 7.1 API Rate Limits
**Problem:** Tankerkönig API has limits
- Max ~10 requests/minute
- With many users, integration could get blocked

**Solution:**
- Use caching (already implemented)
- Update interval not below 5 minutes
- Exponential backoff on errors

### 7.2 Battery Consumption
**Problem:** Frequent GPS checks consume battery
- Especially with smartphone as device_tracker

**Solution:**
- Adaptive update strategy (slower when stationary)
- Optional: Only activate when navigation active
- Use HA Companion App settings (app already optimizes)

### 7.3 Offline Situations
**Problem:** No internet while driving
- No API updates possible
- GPS might still work

**Solution:**
- Fallback to last known data
- Offline mode: Use cache
- Status indicator in sensor attributes

### 7.4 Privacy
**Problem:** Tracking vehicle position
- Sensitive data

**Solution:**
- Everything local in HA (no cloud)
- Opt-in feature
- Documentation about data usage

---

## 8. MVP (Minimum Viable Product) Definition

### Phase 1: Core Functionality ✅
**Must-Have:**
1. ✅ Sensor for cheap stations (Top N)
2. ✅ Binary sensor for proximity alert
3. ✅ Number entities for configuration (count, radius, threshold)
4. ✅ Basic proximity logic (distance calculation)
5. ✅ Anti-spam mechanism (cooldown)
6. ✅ Documentation and example automations

**Not in MVP:**
- ❌ Route-based optimization
- ❌ ML-based time predictions
- ❌ Complex geofencing

### Phase 2: Enhancements 🔶
**Nice-to-Have:**
1. 🔶 Station preferences (favorites/blacklist)
2. 🔶 Range integration (only refuel when necessary)
3. 🔶 Price trends per station
4. 🔶 Adaptive update strategy (based on speed)

### Phase 3: Advanced Features 🔮
**Future:**
1. 🔮 Route-based optimization
2. 🔮 ML price predictions per station
3. 🔮 Geofencing / zones
4. 🔮 Integration with other providers (international)

---

## 9. Timeline & Effort (Estimate)

### Phase 1 (MVP)
**Effort:** ~20-30 hours
- Geolocation Service: 4h
- Coordinator: 4h
- Sensor Entities: 6h
- Number/Switch Entities: 2h
- Anti-Spam Logic: 3h
- Tests: 4h
- Documentation: 4h
- Config/Options Flow: 3h

### Phase 2 (Enhancements)
**Effort:** ~15-20 hours
- Preferences: 4h
- Range Integration: 3h
- Price Trends: 5h
- Adaptive Updates: 3h
- Tests & Docs: 5h

---

## 10. Decision Matrix

| Feature                        | Complexity | Value  | Priority | MVP |
|--------------------------------|------------|--------|----------|-----|
| Cheap Stations Sensor          | Low        | High   | 1        | ✅  |
| Proximity Binary Sensor        | Low        | High   | 1        | ✅  |
| Configurable Thresholds        | Low        | High   | 1        | ✅  |
| Anti-Spam Mechanism            | Medium     | High   | 1        | ✅  |
| Station Preferences            | Low        | Medium | 2        | 🔶  |
| Range-based Filtering          | Low        | High   | 2        | 🔶  |
| Price Trends per Station       | Medium     | Medium | 2        | 🔶  |
| Adaptive Update Strategy       | Medium     | Medium | 2        | 🔶  |
| Route-based Optimization       | High       | High   | 3        | 🔮  |
| ML Time Predictions            | High       | Medium | 3        | 🔮  |
| Geofencing                     | High       | Low    | 3        | 🔮  |

---

## 11. Recommended Starting Point

### Option A: Full Integration (Recommended ✅)
**Start with Phase 1 (MVP)**
- Implement all core features
- Well tested and documented
- Users can use immediately

**Advantages:**
- Complete functionality
- Professional release
- Good foundation for future enhancements

**Disadvantages:**
- More development time
- Larger testing effort

### Option B: Minimal Start
**Only critical features**
- Only cheap stations sensor
- No proximity alert (user creates automation themselves)

**Advantages:**
- Faster release
- Less complexity

**Disadvantages:**
- Incomplete
- User must configure more themselves
- Less intuitive

### ⭐ Recommendation: Option A
Development of Phase 1 (MVP) is manageable (~20-30h) and delivers a complete, professional solution. The added value over Option B justifies the additional effort.

---

## 12. Next Steps

1. ✅ **Review and approve this concept**
2. ⬜ **Create technical design**
   - Detailed class diagrams
   - API specifications
   - Database schema
3. ⬜ **Develop prototype**
   - Geolocation Service
   - Basic Coordinator
4. ⬜ **Implement MVP**
   - All Phase 1 features
5. ⬜ **Test and document**
   - Unit tests
   - Integration tests
   - User documentation
6. ⬜ **Prepare release**
   - CHANGELOG
   - Migration guide
   - Example configurations

---

## 13. Open Questions

1. **Should geolocation be enabled by default?**
   - Suggestion: Opt-in (privacy and battery reasons)

2. **What default values for thresholds?**
   - Suggestion: 
     - Number of stations: 5
     - Search radius: 15 km
     - Proximity threshold: 1.5 km

3. **Should the feature be configurable in Config Flow or only Options Flow?**
   - Suggestion: Optional in Config Flow, fully adjustable in Options Flow

4. **Do we need a separate documentation page?**
   - Suggestion: Yes, `docs/GEOLOCATION_GUIDE.md` and `docs/GEOLOCATION_GUIDE_DE.md`

5. **Integration in Custom Card?**
   - Suggestion: Phase 2 - Show cheap stations + map in card

---

## 14. Summary

### ✅ Feasibility
The geolocation feature is **technically feasible** and integrates well into the existing architecture.

### ✅ Data Sources
Both GPS position and station data are **sufficiently accurate and current** for this purpose.

### ✅ Performance
Through **intelligent caching strategy** (API calls every 10 min, proximity checks every 30-60s), performance is not an issue.

### ✅ Usability
Through **sensible defaults** and **optional configuration**, the feature is easy to use without being overwhelming.

### ⚠️ Challenges
- API rate limits (solved by caching)
- Battery consumption (solved by adaptive updates)
- Anti-spam (solved by cooldown + hysteresis)

### 🎯 Recommendation
**Start with Phase 1 (MVP)** - delivers complete, professional solution with all core features.

---

**End of Concept Document**

*Feedback and suggestions welcome!*
