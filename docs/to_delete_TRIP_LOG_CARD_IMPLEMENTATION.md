# Trip Log Card Implementation Guide

## Overview

This document describes the implementation of the Trip Log functionality in the FWCAM Lovelace card.

## Backend Implementation (Completed)

### 1. Sensor Attributes Enhancement

The `TripLogSensor` has been enhanced with the following attributes:

- `config_entry_id`: Required for service calls
- `last_historical_import_timestamp`: Timestamp of last historical trip import
- `last_historical_import_type`: Type of import ("manual" or "automatic")
- `last_vehicle_data_refresh_timestamp`: Timestamp of last vehicle data refresh
- `last_vehicle_data_refresh_type`: Type of refresh ("manual" or "automatic")

**Location**: `custom_components/hafwcma/sensor.py` lines 2502-2588

### 2. Historical Trip Data Import

A new function `import_historical_trip_data()` has been added to detect and import historical trips from Home Assistant's recorder database.

**Features**:
- Checks if trip tracking is enabled before execution
- Queries historical odometer, tank level, and GPS data
- Detects trips based on odometer changes (minimum 0.5 km)
- Calculates trip metrics (distance, duration, fuel consumption)
- Uses long-term statistics for data older than 10 days
- Stores import metadata with timestamp and type

**Location**: `custom_components/hafwcma/utils/historical_data_import.py` lines 1085-1538

**Constants**:
```python
TRIP_DETECTION_MIN_DISTANCE_KM = 0.5
TRIP_MERGE_TIME_WINDOW_MINUTES = 5
TRIP_MAX_SPEED_KMH = 300
TRIP_MIN_DURATION_MINUTES = 1
```

### 3. Button Entity for Manual Import

A new button entity `ImportHistoricalTripDataButton` has been added for manual historical trip imports.

**Features**:
- Validates that trip tracking is enabled
- Triggers historical import with `force_reimport=True`
- Marks import as "manual" type
- Returns import statistics in entity attributes

**Location**: `custom_components/hafwcma/button.py` lines 345-431

## Frontend Implementation (Partial - In Progress)

### 1. Card Configuration

The card configuration has been updated to support trip log display:

```yaml
type: custom:fwcam-card
entity: sensor.your_car_refueling_log
show_trip_log: true  # New option
show_refueling_log: true
show_vehicle_info: true
show_controls: true
show_settings: true
```

### 2. Entity Detection

The `findEntities()` method has been updated to auto-detect trip-related entities:

```javascript
trip_log_sensor: `sensor.${baseName}_trip_log`,
current_trip: `sensor.${baseName}_current_trip`,
trip_tracking: `switch.${baseName}_trip_tracking`,
import_historical_trip_data: `button.${baseName}_import_historical_trip_data`,
```

### 3. Service Methods

New service methods have been added:

```javascript
editTrip(tripData) {
  return this.callService('hafwcma', 'edit_trip', tripData);
}

deleteTrip(tripId) {
  // Shows confirmation dialog in user's language
  if (confirm(message)) {
    this.callService('hafwcma', 'delete_trip', {
      config_entry_id: this.getConfigEntryId(),
      trip_id: tripId
    });
  }
}
```

## Trip Table Structure

The trip table displays the following columns:

| Column | Description | Sortable | Format |
|--------|-------------|----------|--------|
| Start Time | Trip start timestamp | Yes | Date/Time |
| End Time | Trip end timestamp | Yes | Date/Time |
| Distance (km) | Trip distance | Yes | Number (1 decimal) |
| Duration | Trip duration | Yes | HH:MM format |
| Category | Trip category (business/private/commute) | Yes | Badge |
| Fuel (L) | Fuel consumed | Yes | Number (2 decimals) |
| Actions | Edit/Delete buttons | No | Buttons |

## Filters

The trip table supports filtering by:

1. **Year**: Dropdown with all years from trip data
2. **Month**: Dropdown with all 12 months
3. **Category**: Dropdown with business/private/commute options

## Trip Edit Dialog

The trip edit dialog allows editing of:

- **Category**: Dropdown (business/private/commute)
- **Purpose**: Text field for trip description
- **Additional Costs**: Number field for tolls, parking, etc.
- **Notes**: Text area for additional notes

**Read-only fields**:
- Timestamps (start/end)
- Distance
- Duration
- Fuel consumed

## Service Call Structure

### Edit Trip

```javascript
{
  config_entry_id: string,
  trip_id: integer,
  category: string (optional),
  purpose: string (optional),
  additional_costs: float (optional),
  notes: string (optional)
}
```

### Delete Trip

```javascript
{
  config_entry_id: string,
  trip_id: integer
}
```

## CSS Classes

New CSS classes for trip styling:

```css
.trip-table { /* Trip table styles */ }
.trip-table th { /* Table header styles */ }
.trip-table td { /* Table cell styles */ }
.category-badge { /* Category badge base styles */ }
.category-business { /* Business trip badge */ }
.category-private { /* Private trip badge */ }
.category-commute { /* Commute trip badge */ }
```

## Helper Methods

### Trip Filtering

```javascript
filterTrips(trips) {
  // Filter by year, month, and category
  // Returns filtered trip array
}
```

### Trip Sorting

```javascript
sortTrips(trips) {
  // Sort by selected column and direction
  // Returns sorted trip array
}
```

### Duration Formatting

```javascript
formatDuration(minutes) {
  // Convert minutes to HH:MM format
  // Example: 125 minutes -> "02:05"
}
```

### Year Extraction

```javascript
getUniqueTripYears(trips) {
  // Extract unique years from trip timestamps
  // Returns array of years
}
```

## Testing Checklist

- [ ] Trip table renders correctly
- [ ] Sorting works for all columns
- [ ] Filtering works for year/month/category
- [ ] Edit button opens dialog with trip data
- [ ] Dialog fields are pre-filled correctly
- [ ] Edit service call updates trip
- [ ] Delete button shows confirmation
- [ ] Delete service call removes trip
- [ ] Table refreshes after edit/delete
- [ ] Category badges display correctly
- [ ] Duration formatting is correct
- [ ] No data message shows when no trips
- [ ] Filter info shows correct counts

## Future Enhancements

1. **Pagination**: Add pagination controls for large trip lists
2. **Export**: Add export button for CSV/JSON trip data
3. **Charts**: Add trip statistics visualization
4. **Map View**: Add map visualization of trip routes (if GPS data available)
5. **Pattern Detection**: Highlight trips matching recognized patterns
6. **Cost Calculation**: Show real costs vs. tax mileage rates

## Related Files

- Backend: `custom_components/hafwcma/sensor.py`
- Backend: `custom_components/hafwcma/utils/historical_data_import.py`
- Backend: `custom_components/hafwcma/button.py`
- Backend: `custom_components/hafwcma/__init__.py` (service handlers)
- Backend: `custom_components/hafwcma/services.yaml` (service definitions)
- Frontend: `fwcam-card/dist/fwcam-card.js`

## Usage Example

```yaml
# Lovelace card configuration
type: custom:fwcam-card
entity: sensor.my_car_refueling_log
title: My Car Manager
show_trip_log: true
show_refueling_log: true
rows_per_page: 10
```

## Service Call Examples

### Edit a Trip

```yaml
service: hafwcma.edit_trip
data:
  config_entry_id: "abc123def456"
  trip_id: 42
  category: "business"
  purpose: "Client meeting in Munich"
  additional_costs: 5.50
  notes: "Highway construction detour"
```

### Delete a Trip

```yaml
service: hafwcma.delete_trip
data:
  config_entry_id: "abc123def456"
  trip_id: 42
```

### Import Historical Trips

```yaml
# This is done via the button entity
service: button.press
target:
  entity_id: button.my_car_import_historical_trip_data
```
