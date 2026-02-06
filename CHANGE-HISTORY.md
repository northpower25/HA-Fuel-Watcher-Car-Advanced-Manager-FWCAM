# Change History

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
