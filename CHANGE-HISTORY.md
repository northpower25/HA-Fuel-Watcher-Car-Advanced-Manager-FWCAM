# Change History

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
