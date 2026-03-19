# TODO List for haFWCMA

## 🎯 New: Trip Tracking (Fahrtenbuch) Feature

### Implementation Status ✅
**Status**: ✅ Implemented (Phases 1-6, 8)  
**Priority**: High  
**Implementation Date**: 2026-02-13  
**Documentation**: See `docs/TRIP_TRACKING_README.md`, `docs/TRIP_TRACKING_CONCEPT.md`

#### Completed Features ✅
- [x] **Phase 1: Basic Trip Detection & Recording**
  - [x] Trip, TripPattern, and POI data models
  - [x] Extended storage schema with trip data structures
  - [x] Trip detection logic in vehicle_tracker.py
  - [x] TripTracker class with automatic trip detection
  - [x] Trip tracking switch entity
  - [x] Trip log sensor and current trip sensor
  - [x] On-trip binary sensor

- [x] **Phase 2: Cost Calculation**
  - [x] Fuel consumption calculation for trips
  - [x] German tax mileage rate configuration
  - [x] Cost comparison logic (real costs vs. tax rates)
  - [x] Fuel cost calculation based on current price
  - [x] Support for additional costs (tolls, parking)

- [x] **Phase 3: Geocoding Integration**
  - [x] OpenStreetMap Nominatim API client
  - [x] Reverse geocoding for start/end addresses
  - [x] Geocoding cache to reduce API calls
  - [x] Rate limiting (1 request/second)
  - [x] Configurable auto-geocoding

- [x] **Phase 4: Pattern Recognition**
  - [x] Pattern matching algorithm
  - [x] Automatic pattern detection from trip history
  - [x] Match quality scoring
  - [x] Pattern statistics tracking
  - [x] Integration into trip workflow

- [x] **Phase 5: POI Management**
  - [x] POI detection logic
  - [x] Home/Work auto-detection
  - [x] Gas station POI integration
  - [x] POI visit counting
  - [x] POI suggestion functions

- [x] **Phase 6: Anonymization Features**
  - [x] Time-based anonymization rules
  - [x] Anonymization application logic
  - [x] Pattern-based anonymization
  - [x] Data retention policy
  - [x] Privacy configuration options
  - [x] Privacy notice and summary generation

- [x] **Phase 8: Services & Automations**
  - [x] `hafwcma.add_trip` service
  - [x] `hafwcma.edit_trip` service
  - [x] `hafwcma.delete_trip` service
  - [x] `hafwcma.create_pattern` service
  - [x] `hafwcma.export_trips` service (CSV/JSON)
  - [x] Complete service documentation in services.yaml

#### Future Enhancements (Phase 7 - Optional)
- [ ] **Lovelace Card Extension**
  - [ ] Trip Log tab in FWCAM card
  - [ ] Trip table with sorting/filtering
  - [ ] Trip edit dialog
  - [ ] Pattern management dialog
  - [ ] POI management dialog
  - [ ] CSV export in UI

#### Key Features
- **Automatic Trip Detection**: Based on odometer and GPS data
- **Privacy First**: Opt-in, local storage, time-based anonymization
- **Cost Analysis**: Real costs vs. German tax mileage rates
- **Pattern Recognition**: Automatic detection of recurring routes
- **POI Management**: Home, Work, and favorite gas stations
- **GDPR Compliant**: All required privacy rights supported
- **Service Integration**: Full API for automations and scripts

---

## 🔧 Temporary Debug Features

### Export Vehicle Data Button ✅
**Status**: ✅ Implemented (Temporary)  
**Implementation Date**: 2026-02-14  
**Purpose**: Export raw vehicle entity data for test dataset generation

#### Features
- [x] Button entity: "Export Vehicle Data (Debug)"
- [x] Exports data for all configured vehicle entities:
  - [x] Odometer entity (history + statistics)
  - [x] Tank level entity (history + statistics)
  - [x] Range entity (history + statistics)
  - [x] Position entity (history + statistics)
- [x] Creates CSV files in `/config/www/export/`
- [x] Exports short-term history (limited by Home Assistant's recorder retention, typically 10 days)
- [x] Exports long-term statistics (up to 365 days of hourly aggregated data)
- [x] Each entity gets two CSV files: `{entity}_history_{timestamp}.csv` and `{entity}_statistics_{timestamp}.csv`
- [x] Processing done in 7-day chunks to avoid memory issues (exports full requested range)
- [x] Status and results available in button attributes

#### CSV File Format
**History CSV**: `timestamp, state, attributes`
**Statistics CSV**: `timestamp, mean, min, max, state, sum`

#### Usage
1. Click the "Export Vehicle Data (Debug)" button in Home Assistant
2. Wait for export to complete (check button attributes for status)
3. Find CSV files in `/config/www/export/`
4. Access via browser at `http://your-ha-ip:8123/local/export/`

#### Removal Plan
⚠️ **NOTE**: This is a temporary debugging feature and will be removed once trip detection issues are resolved. Target removal: Next major version update.

---

## 🎯 Neu: Routen-Korridor Tankstellensuche / New: Route Corridor Station Search (In Planung / In Planning)

### Konzept erstellt / Concept Created ✅
- [x] **Routenfunktion mit Tankstellensuche entlang eines Korridors** – Umfassendes bilinguales Konzeptdokument erstellt
  - Siehe / See `docs/dev_docs/ROUTE_CORRIDOR_STATION_SEARCH_CONCEPT.md` (DE/EN)
  - **Status:** Konzept – keine Umsetzung gestartet / Concept – awaiting review before implementation
  - **Aufwand / Effort:** ~60-80 Stunden für MVP (Phase 1-3)
  - **Geplante Funktionen / Features planned:**
    - Routeneingabe mit Ziel + Zwischenzielen über Dashboard, Telegram-Bot oder HA-Automation
    - Korridor-Polygon-Berechnung um die Route (konfigurierbare Breite, Standard 5 km)
    - Tankstopp-Prognose (Tankstand + Verbrauch → Stopppunkt auf der Route)
    - Tankstellen-Filterung nach Korridor + Ranking nach effektivem Preis (Listenpreis + Umwegkosten)
    - Telegram-Benachrichtigungen: Routenstart-Tankplan, günstigere Station im Korridor, Reichweitenwarnung
    - Proaktive Preis-Überwachung während der Fahrt (konfigurierbar alle 5 Minuten)
    - Mehrfach-Tankstopp-Planung für lange Routen
    - Preisvorhersage-Integration
    - Öffnungszeiten-Bewusstsein

---

## 🎯 New: Geolocation Feature (In Planning)

### Konzept erstellt / Concept Created ✅
- [x] **Geolocation-basierte Tankstellen-Näherungserkennung** - Comprehensive concept documents created
  - See `docs/GEOLOCATION_CONCEPT.md` (German)
  - See `docs/GEOLOCATION_CONCEPT_EN.md` (English)
  - See `docs/GEOLOCATION_SUMMARY.md` (Quick summary)
  - **Status:** Awaiting review and approval before implementation
  - **Effort:** ~20-30 hours for MVP (Phase 1)
  - **Features planned:**
    - Sensor for N cheapest stations in configurable radius
    - Binary sensor for proximity alerts (when near cheap station)
    - Configurable thresholds (count, radius, distance)
    - Anti-spam mechanism with cooldown
    - Integration with existing vehicle position tracking
    - Automation examples for Telegram/HA Companion App

---

## ✅ Completed: API Testing in Config Flow
**Status**: ✅ Implemented (MVP + Basic)  
**Priority**: Medium  
**Actual Effort**: ~8-10 hours  
**Documentation**: See `docs/FEATURE_API_TESTING_CONFIG_FLOW.md` (DE) and `docs/FEATURE_API_TESTING_CONFIG_FLOW_EN.md` (EN)

**Implementation Date**: 2026-02-11

#### Implemented Features ✅
- [x] **Fuel Price API Validation during Config Flow**
  - [x] Implement `async_step_validate_api` in config_flow.py
  - [x] Test API connection with home coordinates
  - [x] Display list of found stations on success
    - [x] Station name, address, prices (e5, e10, diesel)
    - [x] Distance to each station
  - [x] Show detailed error message on failure
  - [x] Add "Back" button to retry on errors
  - [x] Timeout handling (10 seconds)

- [x] **Telegram API Validation during Config Flow**
  - [x] Implement `async_step_validate_telegram` in config_flow.py
  - [x] Send test message with title and instructions
  - [x] Display success/error screen
  - [x] Add "Back" button to retry on errors
  - [x] Skip validation if Telegram not configured

#### Technical Implementation ✅
- [x] State management for multi-step validation flows
- [x] Async API call handling during config flow
- [x] Error handling for various API error scenarios
- [x] Timeout management for API calls
- [x] Translations for all new UI strings (DE/EN)

#### Future Enhancements (Phase 3 - Optional)
- [x] Implement response waiting mechanism for Telegram
  - [x] Polling-based response handling (implemented 2026-02-11)
  - [x] Display waiting screen with instructions
  - [x] Process received response and display confirmation
  - [x] Timeout handling (120 seconds)
- [ ] Advanced retry mechanisms
- [ ] Skip options for advanced users
- [ ] Enhanced loading indicators

---

## 🎯 New: Diagnostic Data Export Feature

### Konzept / Concept ✅
**Status**: 📝 Concept Created (Awaiting Implementation)  
**Priority**: High  
**Created**: 2026-02-14  
**Target**: Future PR

#### Problem Statement
Users experiencing issues need an easy way to export all relevant diagnostic data for troubleshooting and bug reporting. Currently, gathering this data requires manual extraction from multiple sources, which is error-prone and time-consuming.

#### Solution: One-Click Diagnostic Export
A button entity that generates a downloadable ZIP file containing all relevant diagnostic information.

#### Implementation Plan

##### Phase 1: Core Export Functionality
- [ ] **Button Entity**: "Export Diagnostic Data"
  - [ ] Create new button entity in `button.py`
  - [ ] Generates timestamped ZIP file in `/config/hafwcma_diagnostics/`
  - [ ] Shows status in button attributes (last export time, file path, file size)
  
- [ ] **Service**: `hafwcma.export_diagnostics`
  - [ ] Callable from automations/scripts
  - [ ] Optional parameters: `include_history_days`, `anonymize_gps`, `anonymize_stations`
  - [ ] Returns file path and download URL
  
- [ ] **Data Collection Module**: `utils/diagnostics_export.py`
  - [ ] Centralized export logic
  - [ ] Privacy controls (anonymization options)
  - [ ] Error handling and logging

##### Phase 2: Data to Include in Export

**Integration Configuration** (anonymized)
- [ ] Config entry data (IDs, entity mappings)
- [ ] Options flow settings
- [ ] Trip tracking configuration
- [ ] Anonymization rules
- [ ] Feature flags and toggles

**Storage Data** (limited retention)
- [ ] Last 100 trips with full details
- [ ] Last 50 refueling events
- [ ] Trip patterns (anonymized GPS if enabled)
- [ ] POI list (anonymized if enabled)
- [ ] Last 90 days of odometer history
- [ ] Price observations (last 100)
- [ ] Geocoding cache entries (last 50, anonymized)

**Entity States & Attributes**
- [ ] All hafwcma sensor states and attributes
- [ ] Connected vehicle entity states (odometer, tank, range, position)
- [ ] Entity availability status
- [ ] Last update timestamps

**API Status & Responses** (sanitized)
- [ ] Last API debug sensor data
- [ ] API connection test results
- [ ] Rate limiting status
- [ ] Last API error messages (sanitized)
- [ ] Sample API responses (anonymized station data)

**Error Logs & Diagnostics**
- [ ] Last 200 haFWCMA log entries (from Home Assistant logs)
- [ ] Error tracebacks (sanitized of personal data)
- [ ] Warning messages
- [ ] Import history (historical data import status)

**System Information**
- [ ] Home Assistant version
- [ ] Integration version
- [ ] Python version
- [ ] Recorder configuration (history retention settings)
- [ ] Entity registry entries for configured entities
- [ ] Timezone and locale settings

**Test Datasets** (if feature enabled)
- [ ] Export format matching `docs/test_datasets/`
- [ ] Odometer history CSV (last 100 points)
- [ ] Tank level history CSV (last 100 points)
- [ ] Range history CSV (last 100 points)
- [ ] Anonymized position history (if GPS configured)

##### Phase 3: Privacy & Security

**Anonymization Options**
- [ ] **GPS Coordinates**: Round to 2-3 decimal places or replace with "ANONYMIZED"
- [ ] **Station Names/Addresses**: Replace with generic "Station A", "Station B"
- [ ] **Personal Names**: Detect and redact from trip notes/descriptions
- [ ] **API Keys**: Always redact (replace with "REDACTED_API_KEY")
- [ ] **Home/Work Addresses**: Option to exclude or anonymize POIs

**User Controls**
- [ ] Checkbox in export dialog: "Anonymize GPS coordinates"
- [ ] Checkbox: "Anonymize station names and addresses"
- [ ] Checkbox: "Include full error logs"
- [ ] Number input: "Days of history to include" (default: 30, max: 90)

**File Security**
- [ ] ZIP files stored in protected directory
- [ ] Automatic cleanup after 24 hours
- [ ] File size limits (max 10 MB)
- [ ] Validate ZIP contents before generation

##### Phase 4: User Experience

**Export Dialog** (if UI implementation)
- [ ] Show estimated file size before export
- [ ] Privacy options with explanations
- [ ] Progress indicator during generation
- [ ] Download link with auto-expiry notice

**Notifications**
- [ ] Success notification with download link
- [ ] Error notification if export fails
- [ ] File size warning if >5 MB
- [ ] Cleanup notification (24h expiry)

**Documentation**
- [ ] User guide for using diagnostic export
- [ ] Privacy explanation (what data is included)
- [ ] Instructions for attaching to bug reports
- [ ] How to interpret diagnostic data (for advanced users)

#### File Structure Example
```
hafwcma_diagnostics_20260214_142500.zip
├── README.txt (export info, privacy notice)
├── config/
│   ├── config_entry.json
│   ├── options.json
│   └── trip_tracking_config.json
├── storage/
│   ├── trips.json (last 100)
│   ├── refueling_events.json (last 50)
│   ├── patterns.json
│   ├── pois.json (anonymized)
│   ├── odometer_history.json
│   └── price_history.json
├── entities/
│   ├── sensor_states.json
│   ├── vehicle_entities.json
│   └── entity_attributes.json
├── api/
│   ├── last_api_response.json (anonymized)
│   ├── api_status.json
│   └── connection_test_results.json
├── logs/
│   ├── error_log.txt
│   ├── warning_log.txt
│   └── import_history.json
├── system/
│   ├── system_info.json
│   └── recorder_config.json
└── test_datasets/ (optional)
    ├── odometer_history.csv
    ├── tank_level_history.csv
    └── range_history.csv
```

#### Technical Implementation Notes

**ZIP Generation**
- Use Python's `zipfile` module
- Stream writing for memory efficiency
- Atomic file creation (write to temp, then move)

**Data Serialization**
- JSON for structured data (pretty-printed for readability)
- CSV for time-series data
- Plain text for logs

**Performance Considerations**
- Async/await for all I/O operations
- Background executor for ZIP generation
- Timeout protection (max 30 seconds)
- Chunk-based data retrieval from storage

**Error Handling**
- Graceful degradation (partial export if some data unavailable)
- Detailed error messages in export metadata
- Fallback to minimal export on critical errors

#### Future Enhancements (Phase 5)
- [ ] Automatic upload to GitHub issue (with user consent)
- [ ] Integration with Home Assistant Cloud for easy sharing
- [ ] Diff comparison between two diagnostic exports
- [ ] Scheduled periodic exports for issue tracking
- [ ] Email/Telegram notification with download link
- [ ] Web-based diagnostic analyzer tool

#### Success Metrics
- ✅ One-click export reduces troubleshooting time by 80%
- ✅ Users can attach diagnostic data to bug reports
- ✅ Developers can reproduce issues faster
- ✅ Privacy controls ensure user data safety
- ✅ Export generation completes in <10 seconds

---

## 🔄 Deferred Features (Future Enhancements)

## High Priority

### Core Functionality
- [x] Implement actual Tankerkönig API data fetching in sensor coordinator
- [x] Add real vehicle tank level tracking (integration with existing entities)
- [x] Connect vehicle entities for data monitoring (odometer, tank level, range, position)
- [ ] Connect Telegram notifier to sensor events
- [x] Implement proper error handling and retry logic for API calls
- [x] Add API rate limiting and caching (via update interval configuration)
- [x] Add manual refresh capability (switch entity)
- [x] Add API connection test functionality (button entity)

### Data Management
- [x] Add persistent storage for price history
- [x] Implement database for vehicle data and refuel history
- [x] Add vehicle data change detection (refueling detection)
- [x] Implement basic consumption tracking (L/100km calculation)
- [x] Add prediction history for accuracy tracking
- [x] **NEW: Enhanced refueling log with ID, editable fields, and comprehensive data**
- [x] **NEW: CRUD operations for refueling records (add, get, update, delete)**
- [x] **NEW: Historical consumption calculation utilities**
- [ ] Add data migration support for upgrades
- [ ] Create backup/restore functionality
- [ ] Implement prediction accuracy analysis and reporting
- [ ] Add data export functionality (CSV, JSON)

### Forecasting
- [x] Improve price forecasting algorithm (statistical analysis)
- [x] Add historical price analysis
- [x] Implement predictive refueling recommendations
- [x] Implement consumption prediction engine with historical data analysis
- [x] Add configurable prediction intervals and data requirements
- [x] Create days-until-refuel sensor with confidence scoring
- [x] **NEW: Average consumption history sensor (today, week, 14 days, month)**
- [x] **NEW: Average consumption forecast sensor (tomorrow, week, 14 days, month)**
- [ ] Add support for external price trend APIs
- [x] Add machine learning for advanced predictions
- [x] Implement seasonal consumption pattern learning
- [ ] Add weather-based consumption adjustments (requires weather integration)
- [ ] Add route-based consumption prediction (requires route planning integration)

## Medium Priority

### Features
- [x] Support for multiple fuel price providers (framework in place)
- [x] Provider selection via config and options flow (dropdown)
- [x] Configurable update interval for automatic data fetching
- [ ] Support for multiple vehicles per integration instance
- [x] Add fuel consumption tracking (via odometer and tank level)
- [x] Implement refuel history logging (refueling event detection)
- [ ] Add cost savings calculator
- [ ] Create station favorites/blacklist feature
- [ ] Add route-based station recommendations
- [x] Support for car tracking integrations (device_tracker integration)
- [x] Support for other fuel price providers (international) - framework ready

### User Interface
- [x] Manual data refresh via switch entity
- [x] API connection test via button entity with result attributes
- [x] Configurable number entities for prediction settings (min data points, prediction interval)
- [x] Add Lovelace card for dashboard display
- [x] **HACS-compatible Lovelace card distribution structure**
- [x] **NEW: Refueling log table with sorting and filtering in Lovelace card**
- [x] **NEW: Add/Edit/Delete refueling events via dialogs**
- [x] **NEW: Immediate UI refresh after CRUD operations via coordinator**
- [x] **NEW: Smart station autocomplete with case-insensitive search**
- [x] **NEW: Auto-calculated total cost field**
- [x] **NEW: Tank capacity validation for liters**
- [x] **NEW: Intelligent odometer suggestions based on history**
- [x] **NEW: Last fuel type pre-selection**
- [x] **NEW: Dynamic odometer recalculation on timestamp change**
- [ ] Create custom panel for detailed statistics
- [ ] Add graphical price trend visualization
- [ ] Add consumption prediction accuracy visualization
- [ ] Create prediction confidence indicator in UI
- [ ] Implement interactive station map
- [ ] **FUTURE: Make tank capacity configurable in UI (currently uses constant)**
- [ ] **FUTURE: Make default daily distance configurable in UI**
- [ ] **FUTURE: Add station favorites list management**
- [ ] **FUTURE: Improve autocomplete with fuzzy matching**
- [ ] **FUTURE: Add bulk import/export of refueling data**

### Automations
- [x] **NEW: Create blueprint automations for common scenarios** (blueprints/automation/)
  - [x] Low fuel alert
  - [x] Price drop notification
  - [x] Smart refueling reminder
  - [x] Trip logging automation
  - [x] Geolocation proximity (placeholder for future feature)
- [x] **NEW: Create script blueprints** (blueprints/script/)
  - [x] Manual refuel entry
  - [x] Trip completion handler
  - [x] Fuel price query
- [ ] Add automation suggestions based on usage patterns
- [ ] Implement smart scheduling for notifications

## Low Priority

### Integrations
- [ ] Add support for other messaging platforms (WhatsApp, Discord, etc.)
- [ ] Integration with Google Maps for navigation
- [x] Support for car tracking integrations (device_tracker entities)
- [ ] Direct integration with vehicle APIs (e.g., BMW ConnectedDrive, Tesla API)
- [ ] Connect with fuel card/loyalty programs

### Analytics
- [ ] Generate monthly fuel cost reports
- [ ] Add comparison with regional averages
- [ ] Implement fuel efficiency tracking
- [ ] Create driving pattern analysis

### Advanced Features
- [ ] Multi-currency support
- [ ] Electric vehicle charging station support
- [ ] Add diesel exhaust fluid (AdBlue) tracking
- [ ] Support for hybrid vehicles (dual fuel types)

## Technical Debt

- [ ] Add comprehensive unit tests
- [ ] Add integration tests
- [ ] Improve code documentation
- [ ] Add type hints everywhere
- [ ] Set up CI/CD pipeline
- [ ] Add pre-commit hooks
- [ ] Improve error messages and user feedback
- [ ] Add logging configuration options
- [ ] Performance optimization for large datasets

## Documentation

- [x] **NEW: Comprehensive German Documentation** (DOKUMENTATION_DE.md)
  - [x] Grundlagen (Fundamentals)
  - [x] Setup und Konfiguration
  - [x] Fahrzeug-Integrationen
  - [x] Tankpreis-API Anbindung
  - [x] Telegram-Integration
  - [x] Funktionsübersicht (Trip, Refueling, Price, Statistics)
  - [x] Erweiterte Funktionen
  - [x] Fehlerbehebung
- [x] **NEW: Blueprint Library** (blueprints/)
  - [x] 5 Automation Blueprints (alerts, notifications, logging)
  - [x] 3 Script Blueprints (manual entry, queries)
  - [x] Complete Blueprint Documentation (BLUEPRINTS_DE.md)
  - [x] Import-ready URLs for Home Assistant
- [x] Create detailed API documentation (docs/API.md exists)
- [x] Add troubleshooting guide (docs/TROUBLESHOOTING.md, TELEGRAM_TROUBLESHOOTING_DE.md)
- [ ] Write FAQ section
- [ ] Create video tutorials
- [x] Add code examples for advanced usage (in blueprints and docs)
- [x] Document all configuration options (DOKUMENTATION_DE.md)
- [ ] Create developer guide for contributions
- [ ] Create English version of DOKUMENTATION_DE.md

## Community

- [ ] Set up discussion forum
- [ ] Create feature request template
- [ ] Add bug report template
- [ ] Establish contributing guidelines
- [ ] Set up sponsorship/donation options
- [ ] Create showcase of user installations

## Future Ideas

- [ ] Mobile app for quick fuel price checks
- [ ] Voice assistant integration (Alexa, Google Assistant)
- [ ] Gamification (achievements, badges for fuel savings)
- [ ] Community price reporting
- [ ] Social features (share good deals with friends)
- [ ] Predictive maintenance reminders based on fuel consumption
- [ ] Integration with financial tracking apps
- [ ] Smart zone-based position tracking (use home zone coordinates when at home)
- [ ] Vehicle entity auto-discovery (suggest entities based on naming patterns)
- [ ] Support for percentage-based tank level sensors
- [ ] Historical consumption analytics and trends
- [x] Display navigation links (Google Maps, Apple Maps, Waze) in station attributes
- [ ] Add station price comparison in sensor attributes (cheapest vs current)
- [ ] Provider API key validation during setup flow
- [ ] Cache station data to reduce API calls
- [ ] Add sensor for second-nearest station for comparison
- [ ] Implement geo-fencing to auto-update search location when vehicle moves significantly
- [ ] Add automation triggers for "good price found" events
- [ ] Support for CNG (compressed natural gas) stations
- [ ] Add station opening hours to sensor attributes
- [ ] **Enhanced fuel station recommendation**: Calculate if driving to a farther station with lower price is economically justified based on fuel consumption and distance. Consider factors like:
  - Current fuel price at nearest station vs. farther station
  - Distance to each station
  - Vehicle fuel consumption rate
  - Additional fuel cost for the extra distance
  - Potential savings after accounting for extra fuel used

## Automatic Fuel Log / Refueling Book Features

### Core Features (Implemented)
- [x] Refueling event detection based on tank level changes
- [x] Automatic storage of refueling events with comprehensive data
- [x] Refueling log with unique IDs and editable fields
- [x] Pre-fill station name from recommended station at time of refueling
- [x] Pre-fill price from current fuel price at time of refueling
- [x] Calculate total cost based on liters and price
- [x] Store location data (GPS coordinates) for each refueling event
- [x] CRUD operations (Create, Read, Update, Delete) for refueling records

### Future Enhancements
- [ ] **Table entity for Home Assistant UI**: Create a table entity to display and edit refueling records directly in the Home Assistant GUI
- [ ] **Home Assistant services**: Expose services for managing refueling records
  - [ ] `hafwcma.add_refueling_event` - Manually add a refueling event
  - [ ] `hafwcma.update_refueling_event` - Update an existing refueling event
  - [ ] `hafwcma.delete_refueling_event` - Delete a refueling event
  - [ ] `hafwcma.get_refueling_log` - Retrieve refueling log data
- [ ] **Telegram chat integration**: Complete refueling records via chat message
  - [ ] AI-powered text parsing to extract refueling details from user messages
  - [ ] Automatically map extracted data to correct fields
  - [ ] Confirmation and editing workflow via chat
- [ ] **Receipt OCR/AI analysis**: Scan fuel receipts using AI
  - [ ] Image/PDF upload via Telegram or FuelLog edit dialog (drag & drop / file picker)
  - [ ] Backup & restore support for uploaded receipt files
  - [ ] OCR extraction of key data (station, amount, price, date/time, litre quantity)
  - [ ] Document quality assessment + per-field confidence scoring
  - [ ] Raw OCR output + parsed result stored per refueling record
  - [ ] Pre-fill FuelLog edit form with recognised values (similar to Telegram dialog)
  - [ ] Receipt preview window in UI
  - [ ] **Local OCR engines** (preferred, open-source, no cloud dependency):
    - PaddleOCR (Apache 2.0) — best choice, layout & table recognition, Python API, runs on RPi/x86
    - DocTR (Apache 2.0) — Transformer-OCR, excellent layout recognition
    - EasyOCR (Apache 2.0) — simpler fallback option
    - See `docs/dev_docs/OCR_RECEIPT_SCANNING.md` for detailed comparison & setup guide
  - [ ] **Cloud OCR engines** (configurable via API key in Config/Options Flow):
    - Google Cloud Vision / Document AI
    - Microsoft Azure Cognitive Services (Receipt API)
    - AWS Textract
    - See `docs/dev_docs/OCR_RECEIPT_SCANNING.md` for API key setup instructions
  - [ ] Config/Options Flow: add OCR engine selector + API key fields for cloud services
  - [ ] AI validation and correction of extracted data
  - [ ] Automatic population of refueling record
- [ ] **Statistics and reporting**:
  - [ ] Monthly fuel cost summaries
  - [ ] Average price paid per liter over time
  - [ ] Fuel cost trends and comparisons
  - [ ] Most frequented stations
  - [ ] Cost per kilometer calculations
- [ ] **Refueling reminders**: Smart reminders based on historical patterns
- [ ] **Loyalty card integration**: Track loyalty points and discounts
- [ ] **Multi-vehicle support**: Separate refueling logs for each vehicle
- [ ] **Export/Import**: CSV or JSON export for external analysis or backup

---

**Note**: This is a living document. Items will be added, removed, or reprioritized based on user feedback and development progress.

Last updated: 2026-02-11

## 💡 Concept: AI-Powered Vehicle Lookup in Setup Flow

**Status**: 📋 Concept / Future Enhancement  
**Priority**: Low  
**Source**: User feedback (2026-02-20)

### Idea
Allow the user to type in their vehicle type during setup, and use an AI service (e.g. Copilot/ChatGPT) to automatically retrieve and pre-fill:
- Maximum tank capacity (L)
- Average WLTP consumption (L/100km)

### Proposed Interaction Flow
1. User enters vehicle model (e.g., "Skoda Superb")
2. System asks for year (e.g., "2025")
3. System asks for engine/trim (e.g., "Sportline 4x4 TFSI")
4. AI returns: "Your vehicle has a tank volume of 69.5 L and an average WLTP consumption of 7.6–7.8 L/100km. Is this correct?"
5. User confirms → values are automatically filled in the setup form

### Implementation Considerations
- Requires integration with an AI/LLM API (OpenAI, Copilot, or similar)
- Could use a public vehicle database API as an alternative
- Optional feature, falls back to manual entry if unavailable
- Privacy: vehicle model data sent to third-party API; needs user consent
