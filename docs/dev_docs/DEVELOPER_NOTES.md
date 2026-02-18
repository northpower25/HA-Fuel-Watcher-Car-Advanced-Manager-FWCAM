# Developer Notes for FWCAM Integration

This document provides important notes for developers working on the Fuel Watcher Car Advanced Manager (FWCAM) integration.

## Custom Lovelace Card Integration

The FWCAM integration includes a custom Lovelace card (`www/fwcam-card/fwcam-card.js`) that serves as the central GUI for users.

### When Adding New Features

**IMPORTANT**: When you add new features to the integration, you MUST update the custom Lovelace card to support them.

#### 1. Adding New Entities

If you add a new entity (sensor, switch, number, button, etc.), update the `findEntities()` method in `www/fwcam-card/fwcam-card.js`:

```javascript
findEntities() {
  // ...existing code...
  
  // Add your new entity here
  your_new_entity: `sensor.${baseName}_your_feature`,
}
```

#### 2. Displaying New Entities

Add UI elements to display your new entities. You can either:
- Add to an existing section (e.g., `renderVehicleInfo()`, `renderControls()`, `renderSettings()`)
- Create a new render method for a new section

Example:
```javascript
renderYourNewSection() {
  const yourEntity = this.getEntityState(this._entities.your_new_entity);
  
  return `
    <div class="section">
      <h3>Your New Feature</h3>
      <!-- Your UI code here -->
    </div>
  `;
}
```

Then call it in the main `render()` method:
```javascript
render() {
  // ...existing code...
  ${this._config.show_your_feature ? this.renderYourNewSection() : ''}
}
```

#### 3. Adding New Services

If you add new services to the integration:

1. **Register the service** in `custom_components/hafwcma/__init__.py`:
   ```python
   hass.services.async_register(
       DOMAIN, 
       "your_service_name", 
       handle_your_service, 
       schema=YOUR_SERVICE_SCHEMA
   )
   ```

2. **Document the service** in `custom_components/hafwcma/services.yaml`:
   ```yaml
   your_service_name:
     name: Your Service Name
     description: Description of what the service does
     fields:
       # Define service parameters
   ```

3. **Add card methods** in `www/fwcam-card/fwcam-card.js`:
   ```javascript
   callYourService(params) {
     this.callService('hafwcma', 'your_service_name', params);
   }
   ```

4. **Add UI controls** (buttons, inputs, etc.) to trigger the service

#### 4. Adding Configuration Options

If you add new configuration options for the card:

1. Update the `setConfig()` method with default values
2. Add configuration fields to the card editor (if implementing one)
3. Update documentation in `www/fwcam-card/README.md`

#### 5. Required Documentation Updates

When adding features, update these files:
- `www/fwcam-card/fwcam-card.js` - Card implementation
- `www/fwcam-card/README.md` - Card documentation
- `docs/REFUELING_LOG_GUIDE.md` - English user guide
- `docs/REFUELING_LOG_GUIDE_DE.md` - German user guide
- `custom_components/hafwcma/strings.json` - Entity translations
- `custom_components/hafwcma/translations/en.json` - English translations
- `custom_components/hafwcma/translations/de.json` - German translations

### Code Quality Guidelines

#### Entity Naming Convention

Since we renamed entities for clarity, follow these guidelines for new entities:

**Before (Unclear)**:
- `switch.[car]_manual_refresh` - What is being refreshed?
- `number.[car]_search_radius` - Search for what?

**After (Clear)**:
- `switch.[car]_fuel_price_refresh` - Clearly refreshes fuel prices
- `number.[car]_station_search_radius` - Clearly for station search

**Guidelines**:
- Entity names should be self-explanatory
- Include what the entity controls/displays in the name
- Use consistent naming patterns across the integration

#### Translation Best Practices

Always provide translations for:
- Entity names (in `strings.json` and `translations/*.json`)
- Service descriptions (in `services.yaml`)
- UI text in the custom card

#### Entity Documentation Requirements

**IMPORTANT**: All new entities MUST include standardized documentation attributes.

When creating a new entity, you must:

1. **Add metadata to `entity_metadata.py`**:
   ```python
   "your_entity_type": {
       "data_source_info": "Where the data comes from",
       "dependencies_info": "What this depends on; what depends on this",
       "purpose_info": "What this entity is for",
       "documentation_url": "your-entity-anchor-in-entities-md",
   }
   ```

2. **Add metadata to entity's `extra_state_attributes` method**:
   ```python
   @property
   def extra_state_attributes(self) -> dict[str, Any]:
       """Return additional attributes."""
       attributes = {}
       
       # ... your existing attributes ...
       
       # Add standardized entity metadata for inline documentation
       metadata = get_entity_metadata("your_entity_type")
       if metadata:
           attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
           attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
           attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
           attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
       
       return attributes
   ```

3. **Import required constants and functions**:
   ```python
   from .const import (
       # ... other imports ...
       ATTR_ENTITY_DATA_SOURCE,
       ATTR_ENTITY_DEPENDENCIES,
       ATTR_ENTITY_DOCUMENTATION_URL,
       ATTR_ENTITY_PURPOSE,
   )
   from .entity_metadata import get_entity_metadata
   ```

4. **Add detailed documentation to `docs/ENTITIES.md`**:
   - Create a new section with anchor matching your `documentation_url`
   - Include: Purpose, Data Source, Dependencies, Key Attributes
   - Add link in the Table of Contents

**Why This Matters**:
- Users can understand entities directly in Home Assistant UI
- Developers can quickly see dependencies and data flow
- Reduces confusion and support requests
- Provides direct links to detailed documentation

**Example**:
See `FuelPriceSensor` in `sensor.py` for a complete implementation example.

#### Code Comments

Add developer notes in your code:
```python
# DEVELOPER NOTE: This function is called by the custom Lovelace card
# If you change the return format, update www/fwcam-card/fwcam-card.js
```

### Testing Checklist

When you add new features, test:

- [ ] Entity creation and initialization
- [ ] Entity state updates
- [ ] Service calls work correctly
- [ ] Custom card displays the entity correctly
- [ ] Custom card can control the entity (if applicable)
- [ ] Translations are correct in both languages
- [ ] **Entity metadata is included and displays correctly**
- [ ] **Documentation is added to docs/ENTITIES.md**
- [ ] Documentation is updated
- [ ] No breaking changes to existing functionality

### Custom Card Architecture

The FWCAM card uses a component-based architecture:

```
fwcam-card.js
├── Core Methods
│   ├── setConfig() - Card configuration
│   ├── set hass() - Home Assistant state updates
│   └── render() - Main rendering
│
├── Entity Detection
│   └── findEntities() - Auto-detect related entities
│
├── Render Sections
│   ├── renderVehicleInfo() - Vehicle stats
│   ├── renderControls() - Action buttons
│   ├── renderSettings() - Configuration inputs
│   └── renderRefuelingLog() - Refueling table
│
├── Service Calls
│   ├── toggleSwitch() - Switch entities
│   ├── setNumberValue() - Number entities
│   ├── pressButton() - Button entities
│   ├── addRefuelingEvent() - Add log entry
│   ├── updateRefuelingEvent() - Update log entry
│   └── deleteRefuelingEvent() - Delete log entry
│
└── Utilities
    ├── formatDateTime() - Date formatting
    ├── formatNumber() - Number formatting
    └── getEntityState() - Get entity state
```

### Future Enhancements

Planned improvements for the card:
- [ ] Card editor for visual configuration
- [ ] Pagination for refueling log
- [ ] Advanced filtering and sorting
- [ ] Charts and graphs for consumption trends
- [ ] Export refueling log to CSV/PDF
- [ ] Import refueling log from CSV
- [ ] Comparison with other vehicles (multi-car support)

### Support and Contributing

- For bugs: Open an issue with the `bug` label
- For features: Open an issue with the `enhancement` label
- Always include:
  - Home Assistant version
  - Integration version
  - Browser (for card issues)
  - Error logs if applicable

### Resources

- [Home Assistant Custom Cards Guide](https://developers.home-assistant.io/docs/frontend/custom-ui/lovelace-custom-card/)
- [LitElement Documentation](https://lit.dev/)
- [Web Components](https://developer.mozilla.org/en-US/docs/Web/Web_Components)
- [HACS Documentation](https://hacs.xyz/)

## Entity Migration Notes

### Entity Renaming (v0.0.33)

The following entities were renamed for clarity:

| Old Name | New Name | Reason |
|----------|----------|--------|
| `switch.[car]_manual_refresh` | `switch.[car]_fuel_price_refresh` | Clarifies what is being refreshed |
| `switch.[car]_manual_prediction` | `switch.[car]_consumption_prediction` | Clarifies what prediction is calculated |
| `number.[car]_search_radius` | `number.[car]_station_search_radius` | Clarifies what is being searched |

**Note**: Existing users will see new entities. The old entity IDs will become unavailable. Users should update their automations and dashboards.

### Backward Compatibility

To maintain backward compatibility in future versions:
1. Document all breaking changes in CHANGELOG.md
2. Provide migration scripts if possible
3. Show warnings in logs for deprecated features
4. Keep deprecated features for at least 2 major versions before removal

## Device Tracker and Geolocation Handling

### Latitude/Longitude Attribute Handling

**Issue**: Many car device_tracker entities store GPS coordinates as attributes rather than in the state value. The state often contains a zone name like "home", "work", or "not_home".

**Example**:
```
device_tracker.my_car_location
  state: "home"
  attributes:
    latitude: 50.00
    longitude: 10.00
    gps_accuracy: 0
```

### Solution Implementation

The integration handles this pattern in `custom_components/hafwcma/utils/vehicle_data.py` in the `async_get_device_tracker_coordinates()` function:

1. **Primary Method**: Extract coordinates from attributes
   ```python
   latitude = state.attributes.get(ATTR_LATITUDE)
   longitude = state.attributes.get(ATTR_LONGITUDE)
   ```

2. **Fallback Method**: Parse state value if it contains coordinates (rare)
   ```python
   parts = state.state.split(",")
   if len(parts) == 2:
       return (float(parts[0].strip()), float(parts[1].strip()))
   ```

3. **Zone Handling**: If state contains a zone name and no attributes, return None
   - The integration cannot automatically resolve zone names to coordinates
   - This is intentional to avoid incorrect location data

### Debug Logging

When troubleshooting geolocation issues, check the logs for:

```
Device tracker device_tracker.my_car: state=home, lat=50.00, lon=10.00, attributes=dict_keys([...])
Geolocation data - lat: 50.00, lon: 10.00, position_entity: device_tracker.my_car
```

If coordinates show as `None`, verify:
1. The device_tracker entity has `latitude` and `longitude` attributes
2. The attribute names match Home Assistant standards (`latitude`/`longitude`, not `lat`/`lon`)
3. The entity is not in an `unknown` or `unavailable` state

### Best Practices for Future Development

When adding geolocation features:

1. **Always check attributes first** for coordinates
2. **Handle None values gracefully** - not all trackers provide coordinates
3. **Add debug logging** to help users troubleshoot
4. **Document coordinate requirements** in the configuration flow

### Common Car Integration Patterns

Different car integrations handle location differently:

| Integration | State Value | Coordinates Location |
|-------------|-------------|---------------------|
| Tesla | Zone name | `latitude`/`longitude` attributes |
| BMW Connected Drive | Zone name | `latitude`/`longitude` attributes |
| Volkswagen We Connect | Zone name | `latitude`/`longitude` attributes |
| Generic GPS Tracker | Coordinates | `latitude`/`longitude` attributes |
| OwnTracks | Zone name | `latitude`/`longitude` attributes |

**Recommendation**: Always use attributes for maximum compatibility.

## Config Flow Architecture and Testing Patterns

### Current Config Flow Structure

The integration uses a multi-step config flow for initial setup:

```
async_step_user (API Configuration)
  ↓
async_step_vehicle (Vehicle Settings)
  ↓
async_step_vehicle_entities (Entity Selection)
  ↓
async_step_telegram (Optional Notifications)
  ↓
async_step_prediction (Prediction Settings)
  ↓
async_create_entry (Complete Setup)
```

### API Validation Considerations

**Current State**: The config flow has a TODO comment for API validation (line 108-109 in config_flow.py):

```python
# TODO: Validate API key with selected provider
# For now, just check if it's provided
```

### Deferred Feature: API Testing in Config Flow

A comprehensive API testing feature has been **deferred** for future implementation. See `docs/FEATURE_API_TESTING_CONFIG_FLOW.md` for full details.

**Why Deferred:**
1. High complexity for marginal benefit
2. Users can test manually after setup via test buttons
3. Requires complex async state management
4. Other features have higher priority

**If Implementing in the Future:**

#### Design Patterns for Async Validation

When adding API validation to config flows:

1. **Keep validation optional** - Don't block setup on temporary API issues
2. **Use separate validation steps** - Don't mix validation with data entry
3. **Provide clear feedback** - Show loading states, success, and detailed errors
4. **Allow retry/skip** - Users should be able to retry or skip validation
5. **Manage state carefully** - Use instance variables for cross-step data

#### Example Pattern for API Validation

```python
async def async_step_validate_api(
    self, user_input: dict[str, Any] | None = None
) -> FlowResult:
    """Validate API configuration (optional step)."""
    
    if user_input is None:
        # First time showing this step - perform validation
        errors = {}
        result_message = ""
        
        try:
            # Test API with stored configuration
            test_result = await self._test_api_connection()
            result_message = self._format_success_message(test_result)
        except Exception as err:
            errors["base"] = "api_test_failed"
            result_message = str(err)
        
        # Show result with option to continue or go back
        return self.async_show_form(
            step_id="validate_api",
            data_schema=vol.Schema({
                vol.Optional("skip_validation", default=False): bool,
            }),
            errors=errors,
            description_placeholders={
                "test_result": result_message,
            },
        )
    else:
        # User clicked next - continue regardless of validation result
        return await self.async_step_vehicle()

async def _test_api_connection(self) -> dict:
    """Test API connection with current configuration."""
    from .providers.tankerkonig import TankerkoenigProvider
    
    provider = TankerkoenigProvider(
        api_key=self.data[CONF_API_KEY],
        hass=self.hass,
    )
    
    # Use home coordinates for test
    stations = await provider.get_stations_nearby(
        latitude=self.hass.config.latitude,
        longitude=self.hass.config.longitude,
        radius=self.data.get(CONF_RADIUS, 5.0),
        fuel_type=self.data.get(CONF_FUEL_TYPE, "e5"),
    )
    
    return {
        "station_count": len(stations),
        "stations": stations[:3],  # Top 3 for display
    }
```

#### Telegram Validation Challenges

Telegram validation is particularly complex:

1. **Async Response Waiting**: Need to wait for user reply
2. **Timeout Handling**: Must handle cases where user doesn't reply
3. **State Persistence**: Must store state between config flow steps
4. **Webhook Setup**: Ideally use webhooks, but polling is simpler
5. **Cleanup**: Must clean up listeners/webhooks on abort

**Recommended Approach** (if implementing):
- Use simple polling for MVP (check for message every 5s for 2 minutes)
- Store test message ID in instance variable
- Implement timeout with clear user feedback
- Provide "Skip Test" option for advanced users

#### Config Flow Best Practices

1. **Progressive Disclosure**: Start with essential fields, add advanced options later
2. **Validation**: Validate on form submission, show errors inline
3. **Error Messages**: Provide actionable error messages
4. **Help Text**: Use `description_placeholders` for contextual help
5. **Defaults**: Provide sensible defaults for all optional fields
6. **Entity Selection**: Use `selector.EntitySelector` for entity picking
7. **Translations**: All strings must have translations in `strings.json`

#### Testing Config Flows

**Manual Testing Checklist:**
- [ ] All steps can be completed successfully
- [ ] Back/forward navigation works correctly
- [ ] Errors are shown and clearable
- [ ] Required fields are validated
- [ ] Optional fields can be skipped
- [ ] Entity selectors filter correctly
- [ ] Translations are correct (DE/EN)
- [ ] Abort scenarios clean up properly
- [ ] Multiple instances can be created
- [ ] Options flow works for reconfiguration

**Automated Testing** (when test infrastructure exists):
- Mock all external dependencies (APIs, Home Assistant)
- Test happy path and error scenarios
- Test state persistence between steps
- Test abort/cleanup scenarios

### State Management in Config Flows

**Instance Variables for Cross-Step Data:**

```python
class HaFWCMAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    
    def __init__(self):
        """Initialize config flow."""
        self.data = {}  # Accumulate data across steps
        self._test_results = None  # Store validation results
        self._telegram_message_id = None  # For Telegram testing
```

**Best Practices:**
- Use `self.data` to accumulate configuration across steps
- Use separate instance variables for temporary state
- Clean up temporary state in `async_create_entry()`
- Handle missing state gracefully (users might navigate back)

### Resources

- [Config Flow Handler Documentation](https://developers.home-assistant.io/docs/config_entries_config_flow_handler)
- [Config Flow Options Documentation](https://developers.home-assistant.io/docs/config_entries_options_flow_handler)
- [Selector Documentation](https://developers.home-assistant.io/docs/data_entry_flow_index/#selectors)

---

**Last Updated**: 2026-02-11
**Maintainer**: @northpower25
