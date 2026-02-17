# State Restoration Feature for External Data Sources

## Problem Statement

After a Home Assistant restart, sensors depending on external APIs (vehicle data, fuel price API) would show `unavailable` for up to 15 minutes because:

1. Sensors started in `unavailable` state
2. First data refresh waited for `homeassistant_started` event (delayed startup)
3. External APIs might take time to respond
4. No state restoration was implemented - previous values were lost

This caused issues for users relying on these sensors for automations and calculations, especially when external APIs were temporarily unreachable.

## Solution

Implemented state restoration using Home Assistant's `RestoreEntity` helper class for all sensors that depend on external data sources.

### Affected Sensors

The following sensors now support state restoration:

1. **FuelPriceSensor** (`sensor.{vehicle_name}_fuel_price`)
   - Restores last known fuel price
   - Restores station information (name, address, distance)
   - Restores price statistics and recommendations

2. **TankLevelSensor** (`sensor.{vehicle_name}_tank_level`)
   - Restores last known tank level percentage
   - Restores liters value
   - Restores tank capacity

3. **RangeSensor** (`sensor.{vehicle_name}_range`)
   - Restores last known range in kilometers
   - Restores days_left calculation

4. **NearestStationSensor** (`sensor.{vehicle_name}_cheapest_station`)
   - Restores last known cheapest station name
   - Restores station details (address, distance, price)
   - Restores navigation URLs

### How It Works

1. **On Shutdown**: Home Assistant automatically saves the current state and attributes of all entities

2. **On Startup**: 
   - Sensors initialize immediately with `RestoreEntity` capability
   - `async_added_to_hass()` is called, which restores the last known state
   - Sensors display restored values with `data_source: restored_from_previous_state` attribute
   - Restored values are shown immediately (no 15-minute wait)

3. **After First Coordinator Update**:
   - When coordinator successfully fetches fresh data, sensors update to show current values
   - The `data_source` attribute is removed (or updated) to indicate live data
   - If fresh data is identical to restored data, users see seamless continuity

4. **Data Staleness Tracking**:
   - Sensors check the age of the last successful data fetch
   - If data is older than 1 hour, a `data_staleness_warning` attribute appears
   - Warning message format: `"{data_type} is {hours:.1f} hours old"`

### Implementation Details

#### RestoreEntity Integration

Each sensor now:
- Inherits from `RestoreEntity` in addition to `CoordinatorEntity` and `SensorEntity`
- Stores `_restored_value` and `_restored_attributes` during initialization
- Implements `async_added_to_hass()` to restore previous state
- Falls back to restored values when coordinator data is unavailable

```python
class TankLevelSensor(CoordinatorEntity, RestoreEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, vehicle_name):
        super().__init__(coordinator)
        self._restored_value = None
        self._restored_attributes = {}
        # ... other initialization

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            self._restored_value = float(last_state.state)
            self._restored_attributes = dict(last_state.attributes)

    @property
    def native_value(self):
        # Try coordinator data first
        if self.coordinator.data is not None:
            value = self.coordinator.data.get("tank_percentage")
            if value is not None:
                return value
        # Fall back to restored value
        return self._restored_value
```

#### Staleness Detection

Data staleness is checked in `extra_state_attributes`:

```python
if last_update:
    age = dt_util.now() - last_update
    if age > timedelta(hours=1):
        attributes["data_staleness_warning"] = f"Vehicle data is {age.total_seconds() / 3600:.1f} hours old"
```

### Benefits

1. **Immediate Availability**: Sensors show values immediately after HA restart
2. **Graceful Degradation**: Temporary API unavailability doesn't cause `unavailable` states
3. **Automation Continuity**: Automations relying on these sensors continue to work
4. **User Awareness**: Staleness warnings inform users when data might be outdated
5. **Seamless Experience**: Users see consistent values across restarts

### User Experience

#### Before State Restoration
```
Time 0:00 - HA restarts
Time 0:00 - Sensors show: unavailable
Time 0:15 - First coordinator update completes
Time 0:15 - Sensors show: 65% (tank level)
```

#### After State Restoration
```
Time 0:00 - HA restarts
Time 0:00 - Sensors show: 65% (tank level) [data_source: restored_from_previous_state]
Time 0:15 - First coordinator update completes
Time 0:15 - Sensors show: 64% (tank level) [updated with fresh data]
```

### Attributes Added

- `data_source`: Set to `"restored_from_previous_state"` when showing restored values
- `data_staleness_warning`: Appears when data is older than 1 hour (e.g., `"Vehicle data is 2.3 hours old"`)

### Coordinator Integration

The coordinator already handles API failures gracefully:
- Stores timestamps for last successful data fetches
- Falls back to last successful values when APIs fail
- Maintains cached vehicle data for resilience

State restoration complements this by making cached values available immediately on restart.

### Testing

To test state restoration:

1. **Setup**: Ensure sensors have valid values
2. **Restart**: Restart Home Assistant
3. **Verify**: Check that sensors show values immediately (not `unavailable`)
4. **Check Attributes**: Verify `data_source: restored_from_previous_state` is present
5. **Wait**: Wait for first coordinator update (check logs)
6. **Verify Update**: Confirm sensors update with fresh data and `data_source` attribute is removed

### Future Enhancements

Possible improvements:
1. Add configurable staleness threshold (currently hardcoded to 1 hour)
2. Add visual indicator in Lovelace card for restored vs. live data
3. Persist more complex state (e.g., full recommendation objects)
4. Add metrics for state restoration success rate

## Technical Notes

- State restoration uses HA's built-in `.storage` mechanism (no custom storage needed)
- Restored values are cleared when coordinator provides fresh data
- Only numeric/string sensor states are restored (not all attributes)
- State restoration is automatic - no user configuration required
