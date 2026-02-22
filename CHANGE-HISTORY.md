# Change History

## Version 0.2.0 (2026-02-22) - Major Feature Release

### Highlights
This release consolidates all pre-release improvements from v0.1.1 through v0.1.66 into a single stable release.

### Added
- **Backup & Restore**
  - New button: `Create Backup` – creates a versioned JSON backup of all user data
    (refueling events, trips, odometer history, price history, ML models, geocoding cache, etc.)
    and saves it to `<config>/www/hafwcma_backups/` for easy download.
  - New service: `hafwcma.create_backup` – programmatic backup creation, returns file path.
  - New service: `hafwcma.restore_backup` – restores data from a backup file with automatic
    compatibility checking; blocks the restore if breaking changes prevent safe migration and
    warns the user about any version differences.
  - Backup files include `app_version`, `data_model_version`, and `created_at` metadata so
    that compatibility can be verified at restore time even after a fresh installation.

- **Automatic Trip Tracking**
  - Start/stop detection based on odometer changes, with GPS position quality (`full`/`partial`/`none`)
  - Trip recovery after HA restart via history backfill
  - Cross-session trip position backfill from adjacent odometer readings
  - Periodic background detection of missed trips
  - New sensors: `Trip Log` and `Current Trip`
  - New switch: `Trip Tracking`
  - New buttons: `Import Historical Trip Data`, `Recalculate Trip Statistics`

- **Near-vs-Far Station Cost Comparison**
  - Compares cheapest near-radius station (default 10 km) with cheapest far-radius station (default 20 km)
  - Accounts for extra fuel cost of the detour when computing savings
  - Three dedicated station sensors: `Cheapest Station`, `Nearest Station`, `Far Station`
  - New number entities: `Cheap Stations Radius`, `Cheap Near Stations Radius`, `Cheap Stations Count`
  - `costsaving_far_vs_near_station` attribute on the Fuel Price sensor

- **Bidirectional Telegram Communication**
  - Multi-turn conversational dialog for logging refueling events via Telegram
  - Smart parsing: liters, price per liter, station name, odometer
  - Explicit refuel-ID matching; HTML-safe output

- **Historical Data Import**
  - Imports odometer history, tank level changes, and refueling events from the HA recorder
  - Live progress indicator in the setup flow spinner; per-query timeout
  - New button: `Import Historical Car Data`

- **Zero-Config Sidebar Dashboard Panel**
  - Registered via `panel_custom`; appears automatically after installation
  - URL path `/hafwcma`; auto-discovers all configured vehicles

- **Interactive Dashboard Charts**
  - Daily fuel price line chart, weekday min/avg grouped bar chart
  - TOP 5 cheapest stations, TOP 20 trip destinations
  - Cheapest station display

- **Weekday Driving Pattern Learning**
  - Separate average daily km tracked per weekday (`avg_monday` … `avg_sunday`)

- **WLTP / Initial Consumption Field**
  - Required in the setup flow; used as bootstrap prediction value and trip import fuel fallback

- **Additional Controls**
  - New switches: `Proximity Alerts`, `Trip Tracking`
  - New buttons: `Validate Refueling Events`, `Recalculate Trip Statistics`, `Import Historical Trip Data`
  - New number entities: `Cheap Stations Radius`, `Cheap Near Stations Radius`, `Cheap Stations Count`, `Proximity Alert Distance`, `Min Tank Level For Alerts`

### Changed
- **Setup flow** expanded to include: vehicle features step, historical import step, finish-setup summary step
- **Consumption prediction** now uses consumption-based math (km ÷ L/100km) instead of refueling interval averaging
- **Rolling-window period labels** renamed: `today_*` → `last_24h_*`, `last_week_*` → `last_7_days_*`, `last_month_*` → `last_30_days_*`
- **Sensor naming**: old `nearest_station` renamed to `cheapest_station`; new `nearest_station` is the physically closest station
- **Radius configuration**: single `station_search_radius` replaced by `cheap_stations_radius`, `cheap_near_stations_radius`, and `cheap_stations_count`
- `ConsumptionPredictionSensor` and `days_until_refuel` sensor now restore their last state after HA restart
- Cost-saving calculation uses learned or WLTP consumption rate instead of hardcoded 7.0 L/100km

### Fixed
- Startup `AttributeError` / `NameError` / timezone-naive/aware comparison errors
- Refueling detection: unit mismatch, impossible amounts, merge-window logic
- Trip loss on HA restart: trips are now recovered from odometer history
- Config flow spinner hang: resolved with per-query timeout and guaranteed preflight result
- Lovelace card N/A values after browser refresh or HA restart

### Breaking Changes
- `sensor.[car]_nearest_station` → renamed to `sensor.[car]_cheapest_station`
- Consumption history attributes: `today_*` / `last_week_*` / `last_month_*` → `last_24h_*` / `last_7_days_*` / `last_30_days_*`
- `number.[car]_station_search_radius` → `number.[car]_cheap_stations_radius`

See [RELEASE_NOTES_v0.2.0.md](RELEASE_NOTES_v0.2.0.md) for the full migration guide.

---

## Version 0.0.95 (2026-02-15) - Bug Fix: Services.yaml Validation Error

### Fixed
- **Lovelace Card Not Displaying Data** (Issue after PR #96)
  - Fixed services.yaml parsing error that prevented integration from loading properly
  - Changed latitude/longitude `step` values from `0.00001` to `step: any` for GPS coordinate fields
  - Affected services: `add_trip` and `edit_trip` (8 coordinate fields total)
  - Error message resolved: "not a valid value for dictionary value @ data['add_trip']['fields']['start_latitude']['selector']['step']"
  - Lovelace card now correctly displays refueling events and trip data again

### Technical Details
- Home Assistant's service YAML validator requires `step: any` for GPS coordinates to allow arbitrary decimal precision
- Using numeric step values like `0.00001` can cause validation errors in some HA versions
- Aligned coordinate field definitions with existing `create_pattern` service which already used `step: any`
- No Python code changes required - issue was purely in the services.yaml UI configuration

## Version 0.0.25 (2026-02-09) - Bug Fix: Manual Prediction

### Fixed
- **Days Until Refuel Sensor Showing Unknown** (#issue)
  - Fixed issue where `sensor.[car name]_days_until_refuel` remained "unknown" after manual prediction trigger
  - Manual prediction switch now directly updates coordinator data for immediate sensor update
  - Coordinator now preserves existing prediction values between update intervals
  - Affects: `switch.[car name]_manual_prediction` and `sensor.[car name]_days_until_refuel`
  - Root cause: Synchronization issue between manual switch and coordinator refresh cycle
  - Sensor now correctly displays prediction values immediately after manual trigger

### Technical Details
- Updated `switch.py`: Direct update of `coordinator.data["consumption_prediction"]` after prediction completes
- Updated `sensor.py`: Preserve existing prediction when interval check returns None
- No breaking changes - all existing functionality preserved

## Version 0.3.1 (2026-02-09) - UI Improvements

### Fixed
- **Number Entity UI Shaking/Wobbling** (#issue)
  - Fixed visual "shaking" or "wobbling" effect when adjusting number entities
  - Removed redundant `async_schedule_update_ha_state()` calls that caused duplicate updates
  - Affects: `api_update_interval`, `consumption_min_data_points`, `consumption_prediction_interval`, `search_radius`
  - Entities now update smoothly through the config entry update listener mechanism
  - No functional changes - all values still update correctly in the UI

### Documentation
- Added troubleshooting section for number input field shaking/wobbling issue
- Documented the technical resolution in TROUBLESHOOTING.md

## Version 0.3.0 (2026-02-06) - Prediction Engine

### Added
- **Prediction Engine** (`utils/prediction_engine.py`)
  - Intelligent refueling recommendations based on multiple factors
  - Configurable price drop thresholds (absolute and percentage)
  - Configurable fuel level thresholds (low and critical)
  - Urgency level calculation (low, medium, high, critical)
  - Integration of price trends and tank levels for smart recommendations
  - Days until refuel estimation based on driving patterns
- **Storage Layer** (`utils/storage.py`)
  - Persistent storage per config entry using Home Assistant's Store API
  - Price history tracking with automatic pruning (last 1000 entries)
  - Odometer history tracking for consumption analysis
  - Weekday consumption statistics for driving pattern learning
  - Tank history (refueling events) with consumption rates
  - Last price, decision, API data, and error tracking
- **Statistics Engine** (`utils/statistics_engine.py`)
  - Self-learning consumption and range logic
  - Odometer history evaluation
  - Daily kilometers calculation
  - Weekday average consumption tracking
  - Average daily kilometers calculation with fallback
  - Range estimation in days based on learned patterns
  - Fuel consumption rate calculation (L/100km)
- **Price Engine** (`utils/price_engine.py`)
  - Price delta calculation (absolute in EUR)
  - Price delta percentage calculation
  - Price spike detection with configurable threshold
  - Price trend analysis (rising, falling, stable)
  - Price statistics (min, max, avg over period)
  - Smart last known price retrieval (prioritizes actual refuel prices)
- **Config Flow Enhancement**
  - New "Prediction" configuration step added
  - Price drop percent threshold (default: 2%, range: 0-20%)
  - Price drop absolute threshold (default: 0.05 EUR, range: 0-0.5 EUR)
  - Low fuel alert threshold (default: 30%, range: 10-50%)
  - Critical fuel alert threshold (default: 15%, range: 5-25%)
  - Fallback daily kilometers (default: 40 km, range: 10-500 km)
- **Options Flow Enhancement**
  - All prediction thresholds configurable at runtime
  - Prediction settings integrated into existing options UI
- **Sensor Enhancements**
  - Fuel Price Sensor now includes:
    - `should_refuel` attribute (boolean recommendation)
    - `urgency` attribute (low/medium/high/critical)
    - `recommendation` attribute (user-friendly text)
    - `price_delta` attribute (absolute price change in EUR)
    - `price_delta_percent` attribute (percentage price change)
    - `forecast_trend` attribute (rising/falling/stable)
  - Range Sensor now includes:
    - `days_left` attribute (estimated days until refuel needed)
  - Automatic storage of price observations on each update
  - Automatic storage of odometer readings when available
  - Automatic detection and storage of refueling events

### Changed
- Sensor coordinator now uses storage layer for persistent data
- Coordinator integrates prediction engine for real-time recommendations
- Config flow now has 5 steps (added prediction step)
- Fuel price sensor attributes extended with prediction data
- Range sensor enhanced with days-left estimation

### Technical Details
- Storage uses versioned JSON files (`.storage/hafwcma_<entry_id>.json`)
- All engines use async/await patterns for Home Assistant compatibility
- Prediction engine combines price analysis, statistics, and tank levels
- Automatic data pruning to prevent storage bloat
- Comprehensive logging for debugging and monitoring
- Type hints throughout all new modules

### Translation Updates
- Added German translations for all new configuration options
- Added English translations for all new configuration options
- Prediction step labels in config flow
- All new option field labels in both languages

## Version 0.2.0 (2026-02-05) - Vehicle Entity Integration

### Added
- **Vehicle Entity Integration**
  - New config flow step for linking existing Home Assistant vehicle entities
  - Support for odometer sensor (for consumption tracking)
  - Support for tank level sensor (for automatic refueling detection)
  - Support for range sensor (for consumption analysis)
  - Support for position device_tracker (for dynamic station search based on current location)
  - Entity validation ensures selected entities exist in Home Assistant
  - Entity selector with search functionality and manual entry support
  - Domain filtering (device_tracker only for position entities)
- **Vehicle Data Utilities** (`utils/vehicle_data.py`)
  - Functions to read entity states from Home Assistant
  - Device tracker coordinate extraction with fallback handling
  - Handles device trackers that show zones (home, away) vs coordinates
  - Extracts coordinates from attributes when state contains zone name
  - Support for numeric sensors (odometer, tank level, range)
- **Vehicle Data Tracking** (`utils/vehicle_tracker.py`)
  - VehicleDataTracker class for change detection
  - Automatic refueling detection (tank level increase >5 units)
  - Fuel consumption calculation (L/100km)
  - Distance traveled tracking between refueling
  - Historical snapshot comparison
- **Sensor Coordinator Updates**
  - Integration with vehicle entity data
  - Real-time vehicle data fetching from configured entities
  - Dynamic position-based Tankerkönig API queries (when position entity configured)
  - Fallback to default location when vehicle position unavailable
  - Consumption tracking and refueling event logging
- **Options Flow Enhancement**
  - Added vehicle entity configuration to options
  - Users can update entity IDs after initial setup
  - Entity validation in options flow
  - Suggested values for existing configurations

### Changed
- Config flow now has 4 steps instead of 3 (added vehicle_entities step)
- Options flow includes vehicle entity fields
- Sensor coordinator now reads from vehicle entities when configured
- Position for API queries can come from vehicle device_tracker instead of fixed location

### Documentation
- Added comprehensive Vehicle Entity Integration Guide (`docs/VEHICLE_ENTITIES.md`)
- Updated README with new features
- Updated TODO.md with completed items
- Added translation strings for German and English

### Technical Details
- Backward compatible with existing configurations (all vehicle entities optional)
- Entity registry and state checks for validation
- Async entity state reading
- Proper error handling for unavailable entities
- Supports both percentage and liter-based tank level sensors
- Device tracker handles GPS coordinates and zone names

## Version 0.1.2 (2026-02-05) - Options Flow Fix

### Fixed
- Fixed options flow 500 Internal Server Error
  - Refactored `HaFWCMAOptionsFlow.async_step_init` to properly handle empty/invalid config values
  - Added explicit validation for numeric fields (radius, tank capacity) to handle empty strings
  - Added fuel type validation to ensure default value is in allowed list
  - Options flow can now be opened without errors even if config contains empty or invalid values
  - Resolves: "Der Konfigurationsfluss konnte nicht geladen werden: 500 Internal Server Error"

## Version 0.1.1 (2026-02-05) - Bug Fixes

### Fixed
- Fixed FuelPriceSensor state class incompatibility with monetary device class
  - Removed `SensorStateClass.MEASUREMENT` from FuelPriceSensor
  - Monetary device class sensors should not use MEASUREMENT state class per HA guidelines
  - Resolves logger warning: "Entity is using state class 'measurement' which is impossible considering device class ('monetary')"
- Fixed config flow 404/500 errors
  - Added missing `strings.json` file required by Home Assistant for config flow UI
  - Config flow can now be opened without errors

## Version 0.1.0 (2026-02-05) - Initial MVP Release

### Added
- Initial project structure and scaffolding
- Home Assistant integration framework
  - `manifest.json` with HACS compatibility
  - Config Flow for guided setup
  - Options Flow for runtime configuration
- Core modules:
  - `models/` - Data models for stations, vehicles, forecasts
  - `providers/` - Fuel price provider interface
  - `sensors/` - Sensor platform implementation
  - `messaging/` - Notification system interface
  - `utils/` - Utility functions and helpers
- Tankerkönig API integration
  - Station search by location and radius
  - Real-time fuel price fetching
  - Support for E5, E10, and Diesel
- Sensor entities:
  - Fuel Price sensor
  - Tank Level sensor
  - Range sensor
  - Nearest Station sensor
- Telegram notification system
  - Price alerts
  - Refueling recommendations
  - Low tank warnings
- Basic price forecasting
  - Trend detection (rising/falling/stable)
  - Simple refueling recommendations
- Multi-language support
  - English (en)
  - German (de)
- Documentation
  - README with features and installation guide
  - TODO list for future development
  - HACS configuration
  - MIT License

### Technical Details
- Python 3.11+ compatible
- Home Assistant 2023.1.0+ required
- Async/await architecture
- DataUpdateCoordinator for efficient polling
- Type hints and docstrings throughout

### Known Limitations
- Tank level tracking is stub implementation (requires manual integration)
- Forecast algorithm is basic (simple trend analysis)
- Single vehicle per integration instance
- Germany-only (Tankerkönig API limitation)
- No persistent storage for price history
- No graphical user interface components

### Notes
This is an MVP (Minimum Viable Product) release. All core features are implemented as stubs with proper interfaces and documentation. The integration is functional but requires further development for production use. See TODO.md for planned improvements.

---

## Future Releases

### Planned for 0.2.0
- Actual tank level integration
- Enhanced forecasting algorithms
- Price history persistence
- Multiple vehicle support

### Planned for 0.3.0
- Lovelace dashboard cards
- Blueprint automations
- Additional fuel price providers

---

**Legend:**
- Added: New features
- Changed: Changes in existing functionality
- Deprecated: Soon-to-be removed features
- Removed: Removed features
- Fixed: Bug fixes
- Security: Security fixes

---

## Developer Guide: Handling Breaking Changes for Backup/Restore Compatibility

> **Read this before making any changes to `utils/storage.py`.**

The backup/restore system tracks a `data_model_version` integer and a
`BREAKING_CHANGES_REGISTRY` dict (both in `utils/backup_manager.py`).  
Users may run backups from **any** past version and restore to the current
version after a fresh installation. You must ensure they are informed
when this is unsafe.

### What counts as a breaking change?

A breaking change is any modification to `utils/storage.py` where:

| Situation | Breaking? |
|---|---|
| Stored field **renamed or removed** | ✅ Yes |
| Field **type or format** changes incompatibly (e.g. `str` → `dict`) | ✅ Yes |
| New **required** fields added that cannot be derived from old data | ✅ Yes |
| **Semantics** of an existing field change incompatibly | ✅ Yes |
| New **optional** fields added with sensible defaults | ❌ No |
| New data structures added **alongside** existing ones | ❌ No |
| Bug fixes that don't alter the storage format | ❌ No |
| Derived/cached data recalculated from raw records (`trip_statistics`, `geocoding_cache`, `weekday_consumption`) | ❌ No |

### Steps when introducing a breaking change

1. **Increment `CURRENT_DATA_MODEL_VERSION`** in `utils/backup_manager.py`.

2. **Add an entry to `BREAKING_CHANGES_REGISTRY`**:

   ```python
   BREAKING_CHANGES_REGISTRY["X.Y.Z"] = {
       "data_model_version": <new CURRENT_DATA_MODEL_VERSION>,
       "description": "Brief user-facing description of what changed.",
       "migration_hint": (
           "Concrete advice for affected users, e.g.: "
           "'Export your trips via the export_trips service BEFORE updating, "
           "then re-import them manually after the fresh installation.'"
       ),
   }
   ```

   where `"X.Y.Z"` is the **app version** (from `manifest.json`) in which the
   breaking change is introduced.

3. **Update `manifest.json`** with the new version number.

4. **Document the change** in this file under the relevant version section.

### How the system uses this information

When a user calls `hafwcma.restore_backup` (or presses the *Create Backup* button
and then later restores), the system:

- Compares `backup.app_version` with the currently installed version.
- Looks up every `BREAKING_CHANGES_REGISTRY` entry whose version is **strictly
  between** the backup version and the current version.
- If any entry's `data_model_version` exceeds the backup's `data_model_version`,
  the restore is **blocked** with a clear error message listing the breaking
  changes and their `migration_hint` values.
- Soft differences (same data model version, different app version) produce a
  **warning** but do not block the restore.

### Advice for users running older versions

Users who have an older version installed and want to update should be advised to:

1. Press the **Create Backup** button (or call `hafwcma.create_backup`) while
   still on the old version.
2. Check the HA notification for the download path.
3. Download the backup file from `/local/hafwcma_backups/<filename>`.
4. Update haFWCMA (or reinstall from scratch).
5. Call `hafwcma.restore_backup` with the file path.

If breaking changes exist between the old and new version, the restore will
display an error explaining what changed and what migration steps are needed.
Users can then follow the `migration_hint` to recover their data manually.
