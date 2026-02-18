# Entity Documentation Standardization - Implementation Summary

## Overview

This implementation adds standardized inline documentation attributes to all 28 entities in the FWCAM (Fuel Watcher Car Advanced Manager) integration. Each entity now exposes metadata attributes that provide users and developers with immediate access to:

1. **Purpose** - What the entity is for
2. **Data Source** - Where the data comes from or what data is required
3. **Dependencies** - What this entity depends on and what depends on it
4. **Documentation URL** - Direct link to detailed documentation

## Implementation Details

### Files Created

1. **`custom_components/hafwcma/entity_metadata.py`**
   - Central repository for all entity metadata
   - Contains standardized information for all 28 entities
   - Automatically generates documentation URLs

2. **`docs/ENTITIES.md`**
   - Comprehensive entity documentation
   - Detailed information about all sensors, binary sensors, switches, and buttons
   - Includes data sources, dependencies, attributes, and usage examples
   - GitHub markdown anchors for deep linking

### Files Modified

1. **`custom_components/hafwcma/const.py`**
   - Added 4 new attribute constants:
     - `ATTR_ENTITY_PURPOSE`
     - `ATTR_ENTITY_DATA_SOURCE`
     - `ATTR_ENTITY_DEPENDENCIES`
     - `ATTR_ENTITY_DOCUMENTATION_URL`

2. **`custom_components/hafwcma/sensor.py`**
   - Updated imports to include new constants and `get_entity_metadata()`
   - Added metadata to all 13 sensor entities:
     - FuelPriceSensor
     - TankLevelSensor
     - RangeSensor
     - NearestStationSensor
     - FuelPriceApiDebugSensor
     - CarDataDebugSensor
     - ConsumptionPredictionSensor
     - ConsumptionHistorySensor
     - ConsumptionForecastSensor
     - RefuelingLogSensor
     - NearbyCheapStationsSensor
     - TripLogSensor
     - CurrentTripSensor

3. **`custom_components/hafwcma/binary_sensor.py`**
   - Updated imports to include new constants and `get_entity_metadata()`
   - Added metadata to all 3 binary sensor entities:
     - ProximityAlertSensor
     - OnTripSensor
     - TelegramBotStatusSensor

4. **`custom_components/hafwcma/switch.py`**
   - Updated imports to include new constants and `get_entity_metadata()`
   - Added metadata to all 2 switch entities:
     - ProximityAlertsSwitch
     - TripTrackingSwitch

5. **`custom_components/hafwcma/button.py`**
   - Updated imports to include new constants and `get_entity_metadata()`
   - Added metadata to all 10 button entities:
     - TestProviderConnectionButton
     - ImportHistoricalDataButton
     - ImportHistoricalTripDataButton
     - RecalculateTripStatisticsButton
     - ValidateRefuelingEventsButton
     - RefreshVehicleDataButton
     - FuelPriceRefreshButton
     - ConsumptionPredictionButton
     - TelegramTestButton
     - ExportVehicleDataButton

6. **`docs/dev_docs/DEVELOPER_NOTES.md`**
   - Added comprehensive "Entity Documentation Requirements" section
   - Provides step-by-step guide for adding metadata to new entities
   - Updated testing checklist to include entity metadata verification

7. **`DOCUMENTATION_INDEX.md`**
   - Added link to `docs/ENTITIES.md` in multiple locations
   - Added "What is..." section entry for understanding entities

## Technical Implementation

### Pattern Used

Each entity's `extra_state_attributes` method now includes:

```python
@property
def extra_state_attributes(self) -> dict[str, Any]:
    """Return additional attributes."""
    attributes = {}
    
    # ... existing attributes ...
    
    # Add standardized entity metadata for inline documentation
    metadata = get_entity_metadata("entity_type_key")
    if metadata:
        attributes[ATTR_ENTITY_PURPOSE] = metadata.get("purpose_info")
        attributes[ATTR_ENTITY_DATA_SOURCE] = metadata.get("data_source_info")
        attributes[ATTR_ENTITY_DEPENDENCIES] = metadata.get("dependencies_info")
        attributes[ATTR_ENTITY_DOCUMENTATION_URL] = metadata.get("documentation_url")
    
    return attributes
```

### Metadata Structure

Each entity in `entity_metadata.py` has:

```python
"entity_type_key": {
    "data_source_info": "Where the data comes from",
    "dependencies_info": "What this depends on; what depends on this",
    "purpose_info": "What this entity is for",
    "documentation_url": "anchor-in-entities-md",
}
```

The `get_entity_metadata()` function automatically converts the anchor to a full GitHub URL.

## Benefits

### For Users

1. **Inline Documentation**: Entity information is directly visible in Home Assistant UI
2. **Quick Understanding**: Users can immediately see what each entity does
3. **Troubleshooting**: Dependencies are clear, helping diagnose issues
4. **Direct Links**: One click to detailed documentation

### For Developers

1. **Clear Data Flow**: Easy to see what depends on what
2. **Reduced Errors**: Understanding dependencies prevents integration issues
3. **Maintenance**: Easy to update documentation in one place
4. **Consistency**: All entities follow the same pattern

### For Support

1. **Reduced Questions**: Users can answer their own questions
2. **Better Bug Reports**: Users understand what each entity does
3. **Faster Resolution**: Dependencies are clearly documented

## Validation

### Code Quality

- ✅ All Python files compile successfully
- ✅ No syntax errors
- ✅ Code review completed
- ✅ CodeQL security scan passed (0 alerts)

### Documentation Quality

- ✅ All 28 entities have complete metadata
- ✅ All documentation URLs validated
- ✅ All anchors exist in ENTITIES.md
- ✅ Metadata module tested and working

### Coverage

- ✅ 13 Sensors
- ✅ 3 Binary Sensors
- ✅ 2 Switches
- ✅ 10 Buttons
- **Total: 28 entities with standardized documentation**

## Example Usage

When a user views the attributes of the Fuel Price sensor in Home Assistant, they will see:

```yaml
purpose_info: "Current fuel price (€/L) at nearest/cheapest station"
data_source_info: "Fuel price provider API (e.g., Tankerkönig), vehicle/HA location"
dependencies_info: "API key, geolocation data; used by refueling recommendations, price trends"
documentation_url: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#fuel-price-sensor"
```

Clicking the documentation URL takes them directly to the detailed documentation for that entity.

## Future Maintenance

### Adding a New Entity

When creating a new entity, developers must:

1. Add metadata to `entity_metadata.py`
2. Add metadata retrieval to entity's `extra_state_attributes`
3. Add imports for constants and `get_entity_metadata()`
4. Add detailed documentation to `docs/ENTITIES.md`
5. Add link in Table of Contents

See the "Entity Documentation Requirements" section in `docs/dev_docs/DEVELOPER_NOTES.md` for complete instructions.

### Updating Entity Information

To update entity documentation:

1. Update metadata in `entity_metadata.py` (for inline docs)
2. Update detailed section in `docs/ENTITIES.md` (for full docs)

Both sources should be kept in sync.

## Testing in Home Assistant

To test the implementation:

1. Install the integration in Home Assistant
2. Navigate to Developer Tools → States
3. Select any FWCAM entity
4. View the attributes section
5. Verify that `purpose_info`, `data_source_info`, `dependencies_info`, and `documentation_url` are present
6. Click the documentation URL to verify it links to the correct section

## Conclusion

This implementation provides a comprehensive, standardized approach to entity documentation in the FWCAM integration. All 28 entities now have inline documentation accessible directly in Home Assistant, with deep links to detailed documentation. The pattern is well-documented and easy to follow for future entity additions.

---

**Implementation Date**: 2026-02-18
**Total Entities Updated**: 28 (13 sensors + 3 binary sensors + 2 switches + 10 buttons)
**Files Created**: 2
**Files Modified**: 7
**Security Issues**: 0
**Code Review Issues**: 0 (1 minor note acknowledged as intended behavior)
