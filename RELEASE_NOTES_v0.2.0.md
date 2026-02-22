# Release Notes – v0.2.0

> **Upgrade path:** v0.2.0 is a full release superseding all pre-releases from v0.1.1 through v0.1.66.  
> Users on v0.1.0 can upgrade directly. Please read the **⚠️ Breaking Changes** section before upgrading.

---

## 🚀 Highlights

v0.2.0 is a major step forward from the initial v0.1.0 release. The most significant improvements are:

- **Bidirectional Telegram integration** – log refueling events directly via chat
- **Automatic trip tracking** with GPS position quality and HA-restart recovery
- **Near-vs-far station cost comparison** with dedicated sensor entities
- **Historical data import** from the HA recorder for automatic bootstrapping
- **Zero-config sidebar dashboard panel** and rich Lovelace card
- **Advanced interactive charts** for prices and consumption (dashboard)
- **Self-learning consumption prediction** based on weekday driving patterns
- **Fully redesigned setup flow** with in-flow progress indicator

---

## ✨ New Features

### 🗺️ Trip Tracking
- Automatic trip start/stop detection based on odometer changes
- Persistent trip storage with start/end GPS coordinates, distance, duration, and fuel cost
- **Automatic trip recovery after HA restart** – trips in progress at the time of a restart are detected and backfilled from odometer history
- **Cross-session position backfill** – GPS coordinates are propagated across stored trips from adjacent odometer readings
- **Position quality tracking**: every trip is tagged `full`, `partial`, or `none` based on GPS availability
- Periodic background detection of missed trips from gaps in odometer history
- **New sensors**: `sensor.[car]_trip_log` (full trip history + top-20 destinations) and `sensor.[car]_current_trip` (live trip progress)
- **New switch**: `switch.[car]_trip_tracking` to enable/disable trip tracking at runtime
- **New buttons**: `Import Historical Trip Data`, `Recalculate Trip Statistics`

### ⛽ Near-vs-Far Station Comparison
- Compares the cheapest station in a **near radius** (default 10 km) against the **far radius** (default 20 km)
- Calculates actual total cost savings after accounting for the extra fuel consumed on the detour
- **Three dedicated station sensors**:
  - `sensor.[car]_cheapest_station` – best-value station from the comparison (was: old `nearest_station`)
  - `sensor.[car]_nearest_station` – physically closest open station
  - `sensor.[car]_far_station` – cheapest station in the outer radius
- **New number entities** for fine-grained radius control:
  - `number.[car]_cheap_stations_radius` (overall far radius, replaces old single search radius)
  - `number.[car]_cheap_near_stations_radius` (inner near-comparison radius)
  - `number.[car]_cheap_stations_count` (number of stations to consider)
- `costsaving_far_vs_near_station` attribute on the Fuel Price sensor shows total EUR savings from driving to the farther station

### 📱 Bidirectional Telegram Communication
- Log refueling events directly from Telegram with a multi-turn conversational dialog
- Smart parsing of free-text responses (liters, price, station name, odometer)
- Automatic total cost calculation from detected liters × price
- Explicit refuel-ID matching ensures the correct event is updated
- Inline result highlighting shows which fields were recognized automatically
- Enhanced Telegram notification formatting with proper HTML escaping

### 📊 Historical Data Import
- Imports odometer readings, tank level changes, and refueling events directly from the HA recorder database
- Triggered automatically on first setup (90-day look-back)
- Can be re-triggered at any time via the `Import Historical Car Data` button
- Live **import progress indicator** shown inside the setup flow spinner
- Per-query timeout prevents the setup UI from hanging indefinitely
- Imported events are tagged with `data_quality: historical_import` and a confidence score

### 🎨 Sidebar Panel & Dashboard
- **Zero-config sidebar panel**: after installation a "Fuel Watcher" entry appears automatically in the HA sidebar (via `panel_custom`)
- Auto-discovers all configured vehicles and renders a full dashboard for each
- URL path: `/hafwcma`
- Dashboard includes **interactive charts** (see below)

### 📈 Interactive Charts (Dashboard)
- **Daily fuel price line chart** – price evolution over the last 30 days
- **Weekday min/avg grouped bar chart** – best and average price per weekday
- **Cheapest station display** – best station prominently shown
- **TOP 5 cheapest stations** list with price, distance, and brand
- **TOP 20 trip destinations** aggregated from the full trip history
- **Consumption over time** chart

### 🧠 Improved Consumption Prediction
- Prediction now uses **consumption-based math** (km driven ÷ consumption rate) instead of simple refueling interval averaging
- **WLTP / known consumption field** added to setup – used as bootstrap value before enough history is available
- **Weekday driving pattern learning**: separate average daily km is tracked per weekday (`avg_monday` … `avg_sunday`)
- Attributes `last_24h_*`, `last_7_days_*`, `last_14_days_*`, `last_30_days_*` on the Consumption History sensor use explicit **rolling-window labels** (not calendar boundaries)
- **Recalculate button** (`Fuel Price Refresh` / `Consumption Prediction` switch) forces an immediate prediction update
- Refueling events are validated before use in calculations to exclude test data and physically impossible amounts
- `ConsumptionPredictionSensor` now restores its last state after HA restart

### 🔍 Debug & Diagnostics
- **Car Data Debug sensor** (`sensor.[car]_car_data_debug`) – shows vehicle data collection status, historical import metadata, odometer history size, and refueling event count
- **Fuel Price API Debug sensor** updated with near-radius attributes and clearer field labels
- All entities expose standardized **inline documentation attributes** (`entity_purpose`, `entity_data_source`, `entity_dependencies`, `entity_documentation_url`)

### 🗂️ Redesigned Setup Flow
The setup wizard now has the following steps:
1. **API & Location** – Tankerkönig API key and fixed home coordinates
2. *(auto)* API connection validation
3. **Vehicle** – name, tank capacity, fuel type, and WLTP consumption (new)
4. **Vehicle Entities** *(optional)* – link odometer, tank level, range, and position sensors
5. **Vehicle Features** *(optional)* – enable trip tracking and proximity alerts
6. **Telegram** *(optional)* – bot token and chat ID
7. **Prediction** – urgency thresholds and fallback daily km
8. **Historical Import** – one-time data import from the recorder with live progress
9. **Finish Setup** – post-install summary and next-step hints

### 📍 Proximity Alerts
- New `switch.[car]_proximity_alerts` and `number.[car]_proximity_alert_distance` for configurable distance-based alerts when driving near cheap stations

### 🔔 Other Improvements
- `sensor.[car]_nearby_cheap_stations` – lists up to 5 cheapest stations near the current vehicle position
- `button.[car]_validate_refueling_events` – re-runs data quality checks on all stored refueling events
- `button.[car]_refresh_vehicle_data` – forces an immediate vehicle entity state read
- Comma decimal separator supported in config flow number fields (e.g. `1,5` = `1.5`)
- Adaptive render throttling in the Lovelace card: 15-second refresh during startup/unavailable states, then configured interval
- `days_until_refuel` sensor and `ConsumptionPredictionSensor` now survive HA restarts without showing "Unknown"

---

## ⚠️ Breaking Changes

### Sensor Rename (since v0.1.0)

The former `sensor.[car]_nearest_station` has been **renamed** to `sensor.[car]_cheapest_station`. A new `sensor.[car]_nearest_station` now represents the *physically closest* open station.

| Old Entity ID | New Entity ID | Change |
|---|---|---|
| `sensor.[car]_nearest_station` | `sensor.[car]_cheapest_station` | Now tracks the best-value station |
| *(new)* | `sensor.[car]_nearest_station` | Physically closest open station |
| *(new)* | `sensor.[car]_far_station` | Cheapest station in the outer radius |

**Action required:** Update any dashboards, automations, or scripts that reference `sensor.[car]_nearest_station` to use `sensor.[car]_cheapest_station`.

### Consumption History Attribute Rename (since v0.1.0)

Rolling-window period attributes on `sensor.[car]_average_consumption_history` have been renamed for clarity:

| Old Attribute | New Attribute |
|---|---|
| `today_consumption` / `today_km` / … | `last_24h_consumption` / `last_24h_km` / … |
| `last_week_consumption` / `last_week_km` / … | `last_7_days_consumption` / `last_7_days_km` / … |
| `last_month_consumption` / `last_month_km` / … | `last_30_days_consumption` / `last_30_days_km` / … |

The same rolling-window labels apply to the `sensor.[car]_fuel_price` period statistics attributes (`last_7_days_price`, `last_14_days_price`, `last_30_days_price`).

**Action required:** Update any templates or automations that use the old attribute names.

### Radius Configuration Consolidation (since v0.1.0)

The old single `number.[car]_station_search_radius` entity has been replaced by three dedicated radius entities:

| Old | New |
|---|---|
| `number.[car]_station_search_radius` | `number.[car]_cheap_stations_radius` (far radius) |
| *(new)* | `number.[car]_cheap_near_stations_radius` (near comparison radius) |
| *(new)* | `number.[car]_cheap_stations_count` |

---

## 🐛 Notable Bug Fixes

- Startup errors (`AttributeError`, `NameError`, timezone-naive/aware mismatches) resolved across all major code paths
- Refueling detection: unit mismatch, impossible amounts, merge-window logic, and trip-stats refresh all corrected
- Trip recovery after HA restart: trips no longer silently disappear on restart
- Station cost-saving calculation: previously always used a hardcoded 7.0 L/100km; now uses the vehicle's learned or WLTP consumption rate
- `days_until_refuel` sensor no longer stays "Unknown" after HA restart or manual prediction trigger
- Config flow infinite loading / spinner hang resolved with per-query timeout and guaranteed preflight result
- Lovelace card N/A values after browser refresh or HA restart fixed with adaptive render throttling and race-condition mitigation

---

## 📚 Documentation

- Restructured `docs/` into `user_docs/` and `dev_docs/` hierarchies
- New user guides: HACS Installation (EN/DE), Telegram Setup (EN/DE), Vehicle Entities, Refueling Log, Blueprints (EN/DE), Data Update Frequencies, Troubleshooting
- All entities now include inline documentation attributes (`entity_purpose`, `entity_data_source`, etc.) visible directly in the HA developer tools

---

**Full pre-release changelog:** https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/compare/v0.1.0...v0.1.66
