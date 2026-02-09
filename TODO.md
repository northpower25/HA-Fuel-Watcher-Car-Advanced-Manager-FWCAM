# TODO List for haFWCMA

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
- [ ] Add support for external price trend APIs
- [ ] Add machine learning for advanced predictions
- [ ] Implement seasonal consumption pattern learning
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
- [ ] Add Lovelace card for dashboard display
- [ ] Create custom panel for detailed statistics
- [ ] Add graphical price trend visualization
- [ ] Add consumption prediction accuracy visualization
- [ ] Create prediction confidence indicator in UI
- [ ] Implement interactive station map

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

---

**Note**: This is a living document. Items will be added, removed, or reprioritized based on user feedback and development progress.

Last updated: 2026-02-09
