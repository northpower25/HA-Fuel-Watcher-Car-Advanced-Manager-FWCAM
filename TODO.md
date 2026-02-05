# TODO List for haFWCMA

## High Priority

### Core Functionality
- [ ] Implement actual Tankerkönig API data fetching in sensor coordinator
- [x] Add real vehicle tank level tracking (integration with existing entities)
- [x] Connect vehicle entities for data monitoring (odometer, tank level, range, position)
- [ ] Connect Telegram notifier to sensor events
- [ ] Implement proper error handling and retry logic for API calls
- [ ] Add API rate limiting and caching

### Data Management
- [ ] Add persistent storage for price history
- [ ] Implement database for vehicle data and refuel history
- [x] Add vehicle data change detection (refueling detection)
- [x] Implement basic consumption tracking (L/100km calculation)
- [ ] Add data migration support for upgrades
- [ ] Create backup/restore functionality

### Forecasting
- [ ] Improve price forecasting algorithm (machine learning?)
- [ ] Add historical price analysis
- [ ] Implement predictive refueling recommendations
- [ ] Add support for external price trend APIs

## Medium Priority

### Features
- [ ] Support for multiple vehicles per integration instance
- [x] Add fuel consumption tracking (via odometer and tank level)
- [x] Implement refuel history logging (refueling event detection)
- [ ] Add cost savings calculator
- [ ] Create station favorites/blacklist feature
- [ ] Add route-based station recommendations
- [x] Support for car tracking integrations (device_tracker integration)
- [ ] Support for other fuel price providers (international)

### User Interface
- [ ] Add Lovelace card for dashboard display
- [ ] Create custom panel for detailed statistics
- [ ] Add graphical price trend visualization
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

---

**Note**: This is a living document. Items will be added, removed, or reprioritized based on user feedback and development progress.

Last updated: 2026-02-05
