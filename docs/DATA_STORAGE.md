# Data Storage Guidelines for haFWCMA

This document describes the data storage architecture and best practices for the Fuel Watcher Car Advanced Manager integration.

## Storage Architecture

### Home Assistant Store Class

All persistent data storage in haFWCMA **MUST** use Home Assistant's built-in `Store` class from `homeassistant.helpers.storage`. This ensures:

- **Thread-safe operations** at the storage layer level
- **Atomic file operations** preventing data corruption
- **Integration with Home Assistant's storage framework**
- **Compliance with Home Assistant development guidelines**
- **Protection against read/write conflicts** from concurrent operations

### Storage Location

Data is stored in Home Assistant's `.storage` directory:
- File pattern: `.storage/hafwcma_<entry_id>.json`
- One storage file per configuration entry
- Storage version: 1

## Data Structures

Each configuration entry stores the following data:

### Price History
- **Type**: List of observations
- **Structure**: `{ts: str, price: float}`
- **Retention**: Last 1000 entries
- **Purpose**: Price trend analysis, statistics

### Odometer History
- **Type**: List of observations
- **Structure**: `{ts: str, value: float}`
- **Retention**: Last 1000 entries
- **Purpose**: Consumption tracking, daily km calculation

### Weekday Consumption
- **Type**: Dictionary
- **Structure**: `{weekday: {km: float, count: int}}`
- **Purpose**: Pattern learning, prediction accuracy

### Tank History (Refueling Events)
- **Type**: List of events
- **Structure**: `{timestamp, fuel_added, odometer_km, consumption_rate, price_per_liter}`
- **Retention**: Last 100 events
- **Purpose**: Consumption rate tracking, refueling detection

### Last Successful Values
- **last_price**: Float - Last successfully retrieved fuel price
- **last_price_timestamp**: String (ISO) - When the price was fetched
- **last_station**: Dict - Last successfully retrieved station data
- **last_station_timestamp**: String (ISO) - When the station was fetched
- **Purpose**: Display stability when API fails

### Other Data
- **last_decision**: Refuel recommendation data
- **last_api**: API response cache
- **last_telegram**: Telegram message data
- **last_error**: Error message string

## Best Practices

### ✅ DO

1. **Always use the Storage API**
   ```python
   from .utils import storage
   
   # Load data
   data = await storage.load_data(hass, entry)
   
   # Save data
   await storage.save_data(hass, entry, data)
   ```

2. **Use provided helper functions**
   ```python
   # Add price observation
   await storage.add_price_observation(hass, entry, price, timestamp)
   
   # Get price history
   history = await storage.get_price_history(hass, entry)
   ```

3. **Store timestamps with data**
   ```python
   from datetime import datetime
   timestamp = datetime.now().isoformat()
   await storage.set_last_price(hass, entry, price, timestamp)
   ```

4. **Handle storage errors gracefully**
   ```python
   try:
       await storage.add_price_observation(hass, entry, price, timestamp)
   except Exception as err:
       _LOGGER.warning("Error storing price: %s", err)
       # Continue without failing the entire operation
   ```

5. **Keep data retention limits**
   - Use appropriate list slicing to limit history size
   - Implement automatic cleanup of old data
   - Document retention policies

### ❌ DON'T

1. **Never use direct file operations**
   ```python
   # ❌ WRONG - Do not use
   import json
   with open("data.json", "w") as f:
       json.dump(data, f)
   ```

2. **Never use JSON files for persistence**
   ```python
   # ❌ WRONG - Do not use
   import json
   data = json.loads(file_content)
   ```

3. **Never access .storage directory directly**
   ```python
   # ❌ WRONG - Do not use
   from pathlib import Path
   storage_path = Path(hass.config.path(".storage"))
   ```

4. **Never store sensitive data unencrypted**
   - API keys belong in ConfigEntry.data (encrypted by HA)
   - Passwords should never be stored in storage files

5. **Never block the event loop**
   ```python
   # ❌ WRONG - Use async versions
   import json
   with open("file.json") as f:
       data = json.load(f)
   
   # ✅ CORRECT - Use async Store
   data = await storage.load_data(hass, entry)
   ```

## Thread Safety

### Current Implementation

The storage layer uses Home Assistant's `Store` class which provides thread-safe file operations. However, the integration uses a **load-modify-save pattern** which can have race conditions:

```python
# Potential race condition
data = await storage.load_data(hass, entry)  # Read
data["price_history"].append(new_price)       # Modify
await storage.save_data(hass, entry, data)    # Write
```

### Recommendations

1. **Minimize concurrent modifications**
   - Most updates happen in the coordinator's update cycle (sequential)
   - Manual operations (switches, buttons) are user-triggered (infrequent)

2. **Use atomic operations**
   - The provided helper functions (e.g., `add_price_observation`) are designed to minimize race windows
   - Each helper function does load-modify-save atomically

3. **Consider entry-level locks for critical sections** (future enhancement)
   ```python
   # Future enhancement example
   async with storage.get_lock(hass, entry):
       data = await storage.load_data(hass, entry)
       data["price_history"].append(new_price)
       await storage.save_data(hass, entry, data)
   ```

## Data Migration

When updating data structures:

1. **Increment STORAGE_VERSION** in `storage.py`
2. **Implement migration logic** in `load_data()`
   ```python
   data = await store.async_load()
   if data and data.get("version") < STORAGE_VERSION:
       data = await _migrate_data(data)
   ```
3. **Preserve backward compatibility** when possible
4. **Test migration with real data** before release

## Performance Considerations

1. **Limit data retention**
   - Price history: 1000 entries (~166 hours at 10-minute intervals)
   - Odometer history: 1000 entries
   - Tank history: 100 refueling events

2. **Avoid loading data in hot paths**
   - Cache frequently accessed data in coordinator
   - Only load from storage when necessary

3. **Batch operations when possible**
   ```python
   # ✅ Good - Single load/save cycle
   data = await storage.load_data(hass, entry)
   data["price_history"].append(price1)
   data["odometer_history"].append(odo1)
   await storage.save_data(hass, entry, data)
   
   # ❌ Avoid - Multiple load/save cycles
   await storage.add_price_observation(hass, entry, price1, ts1)
   await storage.add_odometer_observation(hass, entry, odo1, ts1)
   ```

## Future Development

When adding new features:

1. **Review storage needs first**
   - What data needs to be persisted?
   - What is the retention policy?
   - How often will it be accessed?

2. **Add to storage schema**
   - Update `load_data()` default structure
   - Add helper functions to `storage.py`
   - Document the new data structure here

3. **Test with edge cases**
   - Empty storage
   - Corrupted data
   - Storage errors
   - Concurrent access

4. **Update retention limits**
   - Review if new data needs size limits
   - Implement cleanup in helper functions

## Examples

### Adding New Persistent Data

```python
# 1. Update load_data() in storage.py
async def load_data(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    store = _get_store(hass, entry)
    data = await store.async_load()
    if not data:
        data = {
            "version": STORAGE_VERSION,
            # ... existing fields ...
            "my_new_data": [],  # Add new field with default
        }
    return data

# 2. Add helper functions
async def add_my_observation(
    hass: HomeAssistant,
    entry: ConfigEntry,
    value: float,
    timestamp: str,
) -> None:
    """Add observation to my_new_data."""
    data = await load_data(hass, entry)
    data["my_new_data"].append({"ts": timestamp, "value": value})
    
    # Apply retention limit
    if len(data["my_new_data"]) > 1000:
        data["my_new_data"] = data["my_new_data"][-1000:]
    
    await save_data(hass, entry, data)

async def get_my_observations(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> list[dict[str, Any]]:
    """Get my_new_data observations."""
    data = await load_data(hass, entry)
    return data.get("my_new_data", [])

# 3. Use in coordinator or sensors
await add_my_observation(self.hass, self.config_entry, 42.0, timestamp)
observations = await get_my_observations(self.hass, self.config_entry)
```

## Summary

- ✅ **Always use Home Assistant Store class**
- ✅ **Never use direct JSON file operations**
- ✅ **Store timestamps with all data**
- ✅ **Handle errors gracefully**
- ✅ **Respect retention limits**
- ✅ **Use async operations**
- ✅ **Document all data structures**

Following these guidelines ensures data integrity, performance, and compliance with Home Assistant best practices.
