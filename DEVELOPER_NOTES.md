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

---

**Last Updated**: 2024-02-10
**Maintainer**: @northpower25
