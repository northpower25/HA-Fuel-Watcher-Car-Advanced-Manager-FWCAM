# TODO List for haFWCMA

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
- [ ] Create blueprint automations for common scenarios
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

- [ ] Create detailed API documentation
- [ ] Add troubleshooting guide
- [ ] Write FAQ section
- [ ] Create video tutorials
- [ ] Add code examples for advanced usage
- [ ] Document all configuration options
- [ ] Create developer guide for contributions

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
  - [ ] Image upload via Telegram or Home Assistant
  - [ ] OCR extraction of key data (station, amount, price, date/time)
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

Last updated: 2026-02-09
