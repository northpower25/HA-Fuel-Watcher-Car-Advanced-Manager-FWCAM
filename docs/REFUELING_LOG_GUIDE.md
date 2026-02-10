# Refueling Log - Display and Management Guide

## Overview

The `sensor.[car_name]_refueling_log` entity provides a comprehensive log of all refueling events for your vehicle. This guide explains how to display and manage this data in the Home Assistant GUI.

## Important: Not a Todo Domain Entity

The refueling log is a **sensor entity**, not a todo domain entity. This means:
- ✅ It can display refueling history and statistics
- ❌ It cannot be used with the ToDo List tile/card
- ✅ It can be edited through services and automations
- ✅ Multiple display options are available (see below)

### Why Not a Todo Entity?

Todo entities in Home Assistant are designed for task management (shopping lists, checklists, etc.). The refueling log is historical data with specific attributes (timestamp, odometer, liters, cost, etc.) that don't fit the todo domain model.

## Display Options

### Option 0: FWCAM Custom Card (RECOMMENDED - Most User-Friendly)

**The FWCAM Card is a custom Lovelace card that provides the best user experience for managing the Fuel Watcher Car Advanced Manager integration.**

#### Features
- ✅ **Vehicle Information**: Real-time display of fuel price, tank level, range, and nearest station
- ✅ **Control Panel**: Quick access buttons for all integration functions
- ✅ **Settings Management**: Inline editing of all integration settings
- ✅ **Refueling Log Table**: View, edit, and delete refueling events
- ✅ **Add Events**: Manually add new refueling events
- ✅ **Data Quality Indicators**: Color-coded quality and confidence scores
- ✅ **Responsive Design**: Works on desktop and mobile
- ✅ **Auto-Detection**: Automatically finds all related entities

#### Installation

**HACS Installation (Recommended):**
1. Open HACS in your Home Assistant
2. Go to "Frontend" section
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM`
6. Select category "Lovelace"
7. Click "Add"
8. Find "FWCAM Lovelace Card" in the list
9. Click "Download"
10. Restart Home Assistant
11. Clear your browser cache (Ctrl+Shift+R)

**Manual Installation:**
1. Copy `fwcam-card/dist/fwcam-card.js` from this repository to your Home Assistant `config/www/fwcam-card/` directory
2. Add the resource in your Lovelace configuration (Configuration → Dashboards → Resources):
   ```yaml
   url: /local/fwcam-card/fwcam-card.js
   type: module
   ```
3. Restart Home Assistant
4. Clear your browser cache (Ctrl+Shift+R)

#### Basic Usage

Add the following to your Lovelace dashboard:

```yaml
type: custom:fwcam-card
entity: sensor.my_car_refueling_log
```

#### Full Configuration

```yaml
type: custom:fwcam-card
entity: sensor.my_car_refueling_log
title: My Car Fuel Manager
show_refueling_log: true    # Show refueling log table
show_vehicle_info: true     # Show vehicle information
show_controls: true         # Show control buttons
show_settings: true         # Show settings inputs
rows_per_page: 10          # Number of events to display
```

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `entity` | string | **Required** | Your refueling log sensor (e.g., `sensor.my_car_refueling_log`) |
| `title` | string | `Fuel Watcher Car Advanced Manager` | Card title |
| `show_refueling_log` | boolean | `true` | Show/hide the refueling log table |
| `show_vehicle_info` | boolean | `true` | Show/hide vehicle information section |
| `show_controls` | boolean | `true` | Show/hide control buttons |
| `show_settings` | boolean | `true` | Show/hide settings section |
| `rows_per_page` | number | `10` | Number of refueling events to display |

#### What the Card Displays

**Vehicle Information Section:**
- Current fuel price (€/L)
- Tank level (%)
- Remaining range (km)
- Nearest/cheapest fuel station
- Predicted days until refueling needed

**Control Panel:**
- 🔄 Refresh Fuel Prices - Manually update fuel price data
- 📊 Update Prediction - Recalculate consumption prediction
- 🔌 Test Connection - Test API connection to fuel price provider
- 📥 Import History - Import historical refueling data

**Settings:**
- Station Search Radius (1-25 km)
- API Update Interval (1-60 minutes)
- Minimum Data Points for consumption calculation
- Prediction Calculation Interval (0.5-24 hours)

**Refueling Log Table:**
- Date/Time of refueling
- Odometer reading (km)
- Liters refueled
- Price per liter (€)
- Total cost (€)
- Station name
- Data quality indicator (Manual/Auto/Historical)
- Confidence score (0-100%)
- Edit/Delete buttons for each event

#### Developer Notes

**When adding new features to the FWCAM integration:**

1. **New Entities**: Add them to the `findEntities()` method in `fwcam-card.js`
   ```javascript
   // Example: Adding a new sensor
   new_sensor: `sensor.${baseName}_new_feature`,
   ```

2. **New UI Sections**: Create a new render method
   ```javascript
   renderNewSection() {
     // Your UI code here
   }
   ```

3. **New Services**: Add service call methods
   ```javascript
   callNewService(params) {
     this.callService('hafwcma', 'new_service', params);
   }
   ```

4. **Configuration Options**: Update `setConfig()` method and documentation

5. **Always update**:
   - `fwcam-card.js` - Main card code
   - `www/fwcam-card/README.md` - Card documentation
   - `REFUELING_LOG_GUIDE.md` - This file
   - `REFUELING_LOG_GUIDE_DE.md` - German version

#### Advantages of the Custom Card

- ✅ **All-in-one interface**: Central dashboard for the entire integration
- ✅ **User-friendly**: No need for complex YAML templates
- ✅ **Fully editable**: Direct manipulation of refueling events
- ✅ **Visual feedback**: Color-coded quality and confidence indicators
- ✅ **Responsive**: Works on all devices
- ✅ **Future-proof**: Easy to extend with new features

---

### Option 1: Attributes Card (Recommended)

Use the built-in Attributes card to display refueling events:

```yaml
type: attribute
entity: sensor.your_car_refueling_log
attribute: recent_events
```

This will show the 10 most recent refueling events with all details.

### Option 2: Markdown Card

Create a custom markdown card for better formatting:

```yaml
type: markdown
content: |
  ## Refueling Log for {{ state_attr('sensor.your_car_refueling_log', 'status') }}
  
  ### Last Refueling
  {% set last = state_attr('sensor.your_car_refueling_log', 'last_refueling') %}
  {% if last %}
  - **Date**: {{ last.timestamp | as_datetime | as_local }}
  - **Liters**: {{ last.liters }} L
  - **Cost**: {{ last.cost }} €
  - **Station**: {{ last.station }}
  {% else %}
  No refueling events recorded yet.
  {% endif %}
  
  ### Recent Events
  {% set events = state_attr('sensor.your_car_refueling_log', 'recent_events') %}
  {% if events %}
  {% for event in events %}
  #### Event #{{ event.id }} - {{ event.timestamp | as_datetime | as_local }}
  - **Odometer**: {{ event.odometer_km }} km
  - **Liters**: {{ event.liters_refueled }} L
  - **Price/L**: {{ event.price_per_liter }} €
  - **Total**: {{ event.total_cost }} €
  - **Station**: {{ event.station_name }}
  - **Quality**: {{ event.data_quality }} ({{ (event.confidence * 100) | round(0) }}% confidence)
  {% endfor %}
  {% else %}
  No events to display.
  {% endif %}
```

### Option 3: Custom Card with Filtering

Use a markdown card with filtering by data quality:

```yaml
type: markdown
content: |
  ## Refueling Log - Manual Review Needed
  
  {% set events = state_attr('sensor.your_car_refueling_log', 'recent_events') %}
  {% if events %}
  ### Low Confidence Events (Review Recommended)
  {% for event in events if event.confidence < 0.7 %}
  - **{{ event.timestamp | as_datetime | as_local }}**: {{ event.liters_refueled }}L at {{ event.odometer_km }}km
    - Quality: {{ event.data_quality }}, Confidence: {{ (event.confidence * 100) | round(0) }}%
    - Station: {{ event.station_name }}
  {% endfor %}
  
  ### High Confidence Events
  {% for event in events if event.confidence >= 0.7 %}
  - **{{ event.timestamp | as_datetime | as_local }}**: {{ event.liters_refueled }}L at {{ event.odometer_km }}km
  {% endfor %}
  {% endif %}
```

### Option 4: Entities Card

Display summary statistics:

```yaml
type: entities
title: Refueling Summary
entities:
  - entity: sensor.your_car_refueling_log
    name: Total Events
  - type: attribute
    entity: sensor.your_car_refueling_log
    attribute: status
    name: Status
  - type: attribute
    entity: sensor.your_car_refueling_log
    attribute: last_refueling
    name: Last Refueling
```

## Data Quality Indicators

Each refueling event includes quality indicators to help you identify events that may need manual correction:

### Data Quality Field

- **`manual`**: Manually entered refueling event (highest quality)
- **`auto_detected`**: Automatically detected during normal operation
- **`historical_import`**: Detected from historical data import

### Confidence Score

A value from 0.0 to 1.0 indicating confidence in the detection:
- **1.0**: Perfect confidence (all data available, reasonable values)
- **0.7-0.9**: High confidence (most data available)
- **0.4-0.6**: Medium confidence (some data missing)
- **0.0-0.3**: Low confidence (limited data, may need review)

### Confidence Calculation

The confidence score is calculated based on:
1. **Odometer Data Available** (40% weight): Whether odometer reading was found
2. **Price Data Available** (30% weight): Whether fuel price was found
3. **Reasonable Refueling Amount** (30% weight): Whether refueled amount is between 10-100% of tank capacity

### Filtering by Quality

You can filter events by quality in automations or templates:

```yaml
# Get only high-confidence events
{% set events = state_attr('sensor.your_car_refueling_log', 'recent_events') %}
{% set high_confidence = events | selectattr('confidence', '>=', 0.7) | list %}
```

```yaml
# Get historical import events that need review
{% set events = state_attr('sensor.your_car_refueling_log', 'recent_events') %}
{% set needs_review = events | selectattr('data_quality', 'eq', 'historical_import') | selectattr('confidence', '<', 0.7) | list %}
```

## Editing Refueling Events

While there's no built-in GUI for editing individual refueling events, you can use the following approaches:

### Method 1: Delete and Re-add

1. Use the `hafwcma.delete_refuel_event` service to remove incorrect events
2. Use the `hafwcma.add_refuel_event` service to add corrected events

### Method 2: Update via Service Call

Use the `hafwcma.update_refuel_event` service (if available) to modify specific fields.

### Method 3: Storage File Edit (Advanced)

For advanced users, you can edit the storage file directly:
1. Stop Home Assistant
2. Edit `.storage/hafwcma_[entry_id].json`
3. Modify the `refueling_log` array
4. Restart Home Assistant

**Warning**: Direct file editing can cause issues if done incorrectly. Always backup first!

## Best Practices

### Review Historical Imports

After historical data import:
1. Check events with `data_quality: historical_import`
2. Focus on events with `confidence < 0.7`
3. Verify timestamps match actual refueling dates
4. Correct or delete obvious false positives

### Regular Monitoring

- Review new events weekly
- Check for duplicate detections
- Verify odometer readings
- Update missing price data

### Prevent Duplicates

The integration automatically prevents duplicate detection within 24 hours of the same timestamp. If you see duplicates:
1. They may be from different import runs
2. Delete duplicates manually
3. Check logs for import errors

## Troubleshooting

### "Specify an entity from within the todo domain" Error

This error appears when trying to use the refueling log sensor with a ToDo List card. The refueling log is a sensor, not a todo entity. Use one of the display options above instead.

### Missing Timestamps

If refueling events show as "Unknown" or missing timestamps:
- Check that your tank level sensor has proper historical data
- Verify recorder is enabled and retaining data
- Review integration logs for import errors

### Duplicate Events

If you see duplicate refueling events:
- Check `data_quality` field to identify source
- Historical imports should skip existing events
- Delete duplicates using services or storage file edit

### Incorrect Timestamps

If timestamps don't match actual refueling dates:
- Verify your tank level sensor updates correctly
- Check that sensor timestamps are accurate
- Review confidence scores - low confidence may indicate timestamp uncertainty
- Historical import uses the tank level change timestamp

## Examples

### Complete Dashboard Card

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Refueling Overview
    entities:
      - entity: sensor.your_car_refueling_log
        name: Total Events
      - type: attribute
        entity: sensor.your_car_refueling_log
        attribute: status
        name: Status
  
  - type: markdown
    content: |
      ### Last Refueling
      {% set last = state_attr('sensor.your_car_refueling_log', 'last_refueling') %}
      {% if last %}
      **{{ last.timestamp | as_datetime | as_local }}**
      - {{ last.liters }} L @ {{ last.station }}
      - Cost: {{ last.cost }} €
      {% endif %}
  
  - type: markdown
    title: Recent Events (High Confidence)
    content: |
      {% set events = state_attr('sensor.your_car_refueling_log', 'recent_events') %}
      {% for event in events if event.confidence >= 0.7 %}
      **{{ event.timestamp | as_datetime | as_local }}**
      - {{ event.liters_refueled }} L at {{ event.odometer_km }} km
      - {{ event.total_cost }} € ({{ event.price_per_liter }} €/L)
      {% endfor %}
  
  - type: markdown
    title: Events Needing Review
    content: |
      {% set events = state_attr('sensor.your_car_refueling_log', 'recent_events') %}
      {% set low_conf = events | selectattr('confidence', '<', 0.7) | list %}
      {% if low_conf %}
      {% for event in low_conf %}
      ⚠️ **{{ event.timestamp | as_datetime | as_local }}** ({{ (event.confidence * 100) | round(0) }}%)
      - {{ event.liters_refueled }} L at {{ event.odometer_km or 'Unknown' }} km
      - Quality: {{ event.data_quality }}
      {% endfor %}
      {% else %}
      ✅ All events have high confidence
      {% endif %}
```

## Related Documentation

- [Data Storage](DATA_STORAGE.md) - Storage architecture
- [Data Update Frequencies](DATA_UPDATE_FREQUENCIES.md) - Update intervals
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues

## Support

For issues or questions:
1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review Home Assistant logs
3. Open an issue on GitHub with logs and configuration
