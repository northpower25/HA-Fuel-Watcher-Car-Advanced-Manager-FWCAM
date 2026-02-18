# Entity Attributes Structure Guidelines

This document defines the standardized structure for entity attributes in the FWCAM integration.

## Home Assistant Official Guidelines

According to Home Assistant developer documentation:
- **Attribute naming**: Use lowercase snake_case
- **Attributes vs Entities**: Use attributes for supplementary/metadata information. Create separate entities for values that should be monitored or automated independently.
- **Performance**: Entity property getters must not perform I/O - return values from memory only
- **Size limits**: Keep total attribute size under 16KB to avoid performance issues

References:
- [Entity | Home Assistant Developer Docs](https://developers.home-assistant.io/docs/core/entity/)
- [Devices & Services Architecture](https://developers.home-assistant.io/docs/architecture/devices-and-services/)

## FWCAM Attribute Ordering Standard

All entities MUST follow this consistent ordering to provide users with a predictable structure:

### 1. **Top Section: Core Measurement Metadata**
```python
attributes = {
    # State class (for sensors with statistics)
    "state_class": "measurement",  # or "total", "total_increasing"
    
    # Data source identification
    "data_source": "vehicle_integration",  # or "api", "calculated", "user_input", etc.
    "data_source_info": "...",  # From entity_metadata.py
}
```

### 2. **Update & Timing Information**
```python
attributes = {
    # General entity update timestamps
    "last_update": "2026-02-18T10:30:00+00:00",
    "last_successful_update": "2026-02-18T10:30:00+00:00",
    "last_data_refresh": "2026-02-18T10:29:45+00:00",
}
```

### 3. **AI/ML Confidence & Patterns** (if applicable)
```python
attributes = {
    # Confidence values for AI-detected data
    "ai_confidence": 0.95,
    "prediction_confidence": "high",  # or "medium", "low"
    
    # AI/ML patterns
    "weekday_pattern": {
        "monday": {"avg_km": 50, "refuel_probability": 0.2},
        # ...
    },
}
```

### 4. **Last Event Summaries** (not full mass data)
```python
attributes = {
    # Summary of most recent event - NOT the full event object
    "last_refueling": {
        "timestamp": "2026-02-18T08:00:00+00:00",
        "liters": 45.5,
        "cost": 68.25,
        "station": "Shell Station",
    },
    "last_trip": {
        "timestamp": "2026-02-17T18:00:00+00:00",
        "distance_km": 120,
        "duration_minutes": 90,
    },
}
```

### 5. **Recommendations** (if applicable)
```python
attributes = {
    # User-facing recommendations
    "refuel_recommendation": "Refuel in next 2 days",
    "recommended_refuel_date": "2026-02-20",
    "optimal_station": "Station Name",
}
```

### 6. **Counter/Accumulator Attributes**
```python
attributes = {
    # Timestamp ABOVE related counters (if applicable)
    "counters_last_reset": "2026-01-01T00:00:00+00:00",
    
    # Counter values
    "total_events": 150,
    "total_refuelings": 45,
    "total_trips": 105,
    "total_distance_km": 5420,
    "total_fuel_consumed_liters": 450.5,
    "total_cost_eur": 720.50,
    
    # Excluded/filtered counts
    "total_excluded": 5,
    "total_active": 145,
}
```

### 7. **Time-based Statistics** (if not directly related to counters above)
```python
attributes = {
    # Various time-based stats
    "average_consumption_7d": 6.5,
    "average_consumption_30d": 6.8,
    "average_price_last_week": 1.589,
    "average_price_last_month": 1.605,
}
```

### 8. **Configuration & Documentation** (ALWAYS at the end, before mass data)
```python
attributes = {
    # Config entry reference
    "config_entry_id": "abc123...",
    
    # Standardized metadata from entity_metadata.py
    "purpose_info": "Current fuel price (€/L) at nearest/cheapest station",
    "dependencies_info": "API key, geolocation data; used by refueling recommendations",
    "documentation_url": "https://github.com/.../docs/ENTITIES.md#fuel-price-sensor",
}
```

### 9. **Mass Data Arrays** (ALWAYS last, LIMITED to 5 events)
```python
attributes = {
    # Mass data for debugging/error analysis ONLY
    # MUST be limited to last 5 events maximum
    # Components should use database services (get_all_refuelings, get_all_trips) instead
    "recent_events": [
        # Last 5 events only (sorted newest first)
        {...},  # Event 1
        {...},  # Event 2
        {...},  # Event 3
        {...},  # Event 4
        {...},  # Event 5
    ],
}
```

## Mass Data Best Practices

### ❌ **DO NOT** use attributes for mass data access:
```python
# BAD - Don't do this
def process_all_trips():
    trips = trip_sensor.attributes["recent_trips"]  # Only has 5-10 events!
    for trip in trips:
        # ... missing most historical data
```

### ✅ **DO** use database services:
```python
# GOOD - Use this instead
async def process_all_trips(hass):
    trips = await hass.services.async_call(
        "hafwcma",
        "get_all_trips",
        return_response=True
    )
    for trip in trips:
        # ... has complete historical data
```

### Why Limit Mass Data in Attributes?

1. **Performance**: Home Assistant has a 16KB attribute size limit. Large arrays cause:
   - State update failures
   - Database bloat
   - UI freezing
   - Memory issues

2. **Separation of Concerns**: 
   - **Attributes**: Current state metadata and debugging info
   - **Database**: Complete historical data storage

3. **Component Architecture**:
   - **Lovelace Card**: Uses `get_all_refuelings`, `get_all_trips` services
   - **Telegram Bot**: Uses direct storage access
   - **Attributes**: Fallback and debugging only

### Mass Data Array Limits

| Array Type | Previous Limit | New Limit | Reason |
|------------|---------------|-----------|--------|
| `recent_events` | 10 | **5** | Debugging only; card uses service |
| `recent_trips` | 10 | **5** | Debugging only; card uses service |
| `stations` | unlimited | **5** | Top 5 cheapest; detailed search via service |
| `top_stations` (in nested objects) | 3 | **3** | Keep as-is; reasonable for comparisons |

## Implementation Checklist

When creating or updating an entity's `extra_state_attributes`:

- [ ] Follow the 9-section ordering above
- [ ] Limit mass data arrays to 5 items maximum
- [ ] Add descriptive comments for each section
- [ ] Include all metadata from `get_entity_metadata()`
- [ ] Use ISO 8601 format for all timestamps
- [ ] Ensure no I/O operations in the property getter
- [ ] Document any component dependencies on these attributes

## Example: Complete Attribute Structure

```python
@property
def extra_state_attributes(self) -> dict[str, Any]:
    """Return entity attributes following FWCAM standard ordering."""
    
    # 1. Core measurement metadata
    attributes = {
        "state_class": "measurement",
        "data_source": "vehicle_integration",
    }
    
    # 2. Update timestamps
    attributes.update({
        "last_update": self._last_update.isoformat(),
        "last_successful_update": self._last_successful.isoformat(),
    })
    
    # 3. AI/ML confidence & patterns
    if self._weekday_pattern:
        attributes["weekday_pattern"] = self._weekday_pattern
        attributes["pattern_confidence"] = self._pattern_confidence
    
    # 4. Last event summary
    if self._last_event:
        attributes["last_event"] = {
            "timestamp": self._last_event["timestamp"],
            "key_value": self._last_event["value"],
        }
    
    # 5. Recommendations
    if self._recommendation:
        attributes["recommendation"] = self._recommendation
    
    # 6. Counters
    attributes.update({
        "total_events": self._total_count,
        "total_active": self._active_count,
    })
    
    # 7. Time statistics
    attributes.update({
        "average_7d": self._avg_7d,
        "average_30d": self._avg_30d,
    })
    
    # 8. Configuration & documentation
    attributes["config_entry_id"] = self._config_entry.entry_id
    
    metadata = get_entity_metadata("your_entity_type")
    attributes.update({
        "purpose_info": metadata.get("purpose_info"),
        "dependencies_info": metadata.get("dependencies_info"),
        "data_source_info": metadata.get("data_source_info"),
        "documentation_url": metadata.get("documentation_url"),
    })
    
    # 9. Mass data (LIMITED to 5 items for debugging)
    if self._events:
        # Sort newest first, take only last 5
        sorted_events = sorted(
            self._events, 
            key=lambda x: x["timestamp"], 
            reverse=True
        )
        attributes["recent_events"] = sorted_events[:5]
    
    return attributes
```

## Migration Notes

### When Updating Existing Entities:

1. **Preserve existing attribute names** - Don't rename unless necessary
2. **Only reorder** - Move attributes to match the standard sections
3. **Add missing sections** - Include timestamps, metadata if missing
4. **Limit arrays** - Reduce from 10 to 5 items
5. **Document changes** - Update entity documentation in `docs/ENTITIES.md`

### Testing After Changes:

1. Check state size: `< 16KB` per entity
2. Verify attribute order matches standard
3. Test Lovelace card functionality (should use services)
4. Verify Telegram bot works (should use storage)
5. Check developer tools > States for readability

## Further Reading

- [ENTITIES.md](../ENTITIES.md) - Complete entity documentation
- [DEVELOPER_NOTES.md](./DEVELOPER_NOTES.md) - General development guidelines
- [entity_metadata.py](../../custom_components/hafwcma/entity_metadata.py) - Metadata definitions
