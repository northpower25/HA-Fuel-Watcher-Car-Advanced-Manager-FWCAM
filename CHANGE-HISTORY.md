# Change History

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
