# FWCAM Card - Visual Guide

This guide provides visual examples and sample configurations for the FWCAM custom Lovelace card.

## Example Dashboard Configuration

### Full Featured Card

```yaml
type: custom:fwcam-card
entity: sensor.my_car_refueling_log
title: My BMW 320d Fuel Manager
show_refueling_log: true
show_vehicle_info: true
show_controls: true
show_settings: true
rows_per_page: 10
```

**What it shows**:
- Complete vehicle information dashboard
- All control buttons for integration
- All settings with inline editing
- Refueling log table with 10 most recent events
- Color-coded quality and confidence indicators

---

### Compact Card (Info Only)

```yaml
type: custom:fwcam-card
entity: sensor.my_car_refueling_log
title: Vehicle Status
show_refueling_log: false
show_vehicle_info: true
show_controls: false
show_settings: false
```

**What it shows**:
- Only vehicle information section
- Current fuel price, tank level, range
- Nearest station and days until refuel
- Perfect for at-a-glance dashboard

---

### Control Center Card

```yaml
type: custom:fwcam-card
entity: sensor.my_car_refueling_log
title: Fuel Manager Controls
show_refueling_log: false
show_vehicle_info: false
show_controls: true
show_settings: true
```

**What it shows**:
- Control buttons only
- Settings management
- No information display or refueling log
- Perfect for configuration dashboard

---

### Refueling Log Only Card

```yaml
type: custom:fwcam-card
entity: sensor.my_car_refueling_log
title: Refueling History
show_refueling_log: true
show_vehicle_info: false
show_controls: false
show_settings: false
rows_per_page: 20
```

**What it shows**:
- Refueling log table only
- 20 most recent events
- Edit and delete buttons for each entry
- Add new event button
- Perfect for dedicated refueling history view

---

## Card Sections Breakdown

### 1. Vehicle Information Section

**Displays**:
```
┌─────────────────────────────────────────┐
│ Vehicle Information                     │
├─────────────────────────────────────────┤
│ Fuel Price:              1.599 €/L      │
│ Tank Level:              65 %           │
│ Range:                   520 km         │
│ Nearest Station:         Shell Bahnhof  │
│ Days Until Refuel:       4.2            │
└─────────────────────────────────────────┘
```

**Auto-detects entities**:
- `sensor.[car]_fuel_price`
- `sensor.[car]_tank_level`
- `sensor.[car]_range`
- `sensor.[car]_nearest_station`
- `sensor.[car]_days_until_refuel`

---

### 2. Control Panel Section

**Displays**:
```
┌─────────────────────────────────────────┐
│ Controls                                │
├─────────────────────────────────────────┤
│  [🔄 Refresh Prices]  [📊 Update Pred] │
│  [🔌 Test Connect]    [📥 Import Hist] │
└─────────────────────────────────────────┘
```

**Controls**:
- Refresh Fuel Prices → Toggles `switch.[car]_fuel_price_refresh`
- Update Prediction → Toggles `switch.[car]_consumption_prediction`
- Test Connection → Presses `button.[car]_test_connection`
- Import History → Presses `button.[car]_import_historical_data`

---

### 3. Settings Section

**Displays**:
```
┌─────────────────────────────────────────┐
│ Settings                                │
├─────────────────────────────────────────┤
│ Station Search Radius (km):  [  5.0  ] │
│ API Update Interval (min):   [  5    ] │
│ Min Data Points:             [  10   ] │
│ Prediction Interval (h):     [  1.0  ] │
└─────────────────────────────────────────┘
```

**Controls**:
- All inputs update corresponding `number.*` entities in real-time
- Values are validated according to entity min/max
- Changes are immediately saved to Home Assistant

---

### 4. Refueling Log Section

**Displays**:
```
┌───────────────────────────────────────────────────────────────┐
│ Refueling Log                                                 │
├───────────────────────────────────────────────────────────────┤
│ Last Refueling: 2024-02-08 14:30 - 45.5L @ Shell Station    │
├───────────────────────────────────────────────────────────────┤
│ Date/Time    │Odometer│Liters│Price│Total│Station│Qual│Conf │
├──────────────┼────────┼──────┼─────┼─────┼───────┼────┼─────┤
│ 2024-02-08   │ 98,450 │ 45.5 │1.59 │72.70│ Shell │[M] │ 95% │
│ 14:30        │        │      │     │     │       │    │     │
│ [✏️ Edit] [🗑️ Delete]                                        │
├──────────────┼────────┼──────┼─────┼─────┼───────┼────┼─────┤
│ 2024-02-01   │ 98,120 │ 48.2 │1.62 │78.08│ Aral  │[A] │ 87% │
│ 09:15        │        │      │     │     │       │    │     │
│ [✏️ Edit] [🗑️ Delete]                                        │
└──────────────┴────────┴──────┴─────┴─────┴───────┴────┴─────┘
│                     [➕ Add Refueling Event]                  │
└───────────────────────────────────────────────────────────────┘
```

**Quality Badges**:
- `[M]` = Manual (Green) - Manually entered, highest confidence
- `[A]` = Auto Detected (Blue) - Automatically detected
- `[H]` = Historical Import (Orange) - Imported from history

**Confidence Badges**:
- 70-100% = High (Green)
- 40-69% = Medium (Orange)
- 0-39% = Low (Red)

---

## Multi-Card Dashboard Layout

### Recommended Setup

**Top Row** - Vehicle Status:
```yaml
- type: custom:fwcam-card
  entity: sensor.my_car_refueling_log
  title: Vehicle Status
  show_refueling_log: false
  show_vehicle_info: true
  show_controls: true
  show_settings: false
```

**Bottom Row** - Refueling Log:
```yaml
- type: custom:fwcam-card
  entity: sensor.my_car_refueling_log
  title: Refueling History
  show_refueling_log: true
  show_vehicle_info: false
  show_controls: false
  show_settings: false
  rows_per_page: 15
```

**Separate Tab** - Settings:
```yaml
- type: custom:fwcam-card
  entity: sensor.my_car_refueling_log
  title: Fuel Manager Settings
  show_refueling_log: false
  show_vehicle_info: false
  show_controls: false
  show_settings: true
```

---

## Color Scheme

The card uses Home Assistant's theme variables for automatic dark/light mode support:

**Light Mode**:
- Background: White (#FFFFFF)
- Primary: Blue (#03A9F4)
- Text: Dark Gray (#212121)
- Borders: Light Gray (#E0E0E0)

**Dark Mode**:
- Background: Dark (#111111)
- Primary: Light Blue (#039BE5)
- Text: Light Gray (#E1E1E1)
- Borders: Dark Gray (#424242)

**Status Colors** (both modes):
- Success/High: Green (#4CAF50)
- Warning/Medium: Orange (#FF9800)
- Error/Low: Red (#F44336)
- Info: Blue (#2196F3)

---

## Responsive Design

The card adapts to different screen sizes:

**Desktop (>1024px)**:
- Info grid: 2-3 columns
- Control buttons: 4 columns
- Settings: 2 columns
- Table: Full width with scroll

**Tablet (768px-1024px)**:
- Info grid: 2 columns
- Control buttons: 2 columns
- Settings: 1-2 columns
- Table: Horizontal scroll

**Mobile (<768px)**:
- Info grid: 1 column
- Control buttons: 2 columns
- Settings: 1 column
- Table: Horizontal scroll

---

## Tips for Best Visual Results

### 1. Card Size
The card works best with:
- Minimum width: 400px
- Recommended width: 600-800px
- Can span full width on large screens

### 2. Grid Layout
Use Home Assistant's grid layout for optimal positioning:
```yaml
type: grid
columns: 2
cards:
  - type: custom:fwcam-card
    # ... config ...
  - type: custom:fwcam-card
    # ... config ...
```

### 3. Stacking
For mobile, use vertical stacking:
```yaml
type: vertical-stack
cards:
  - type: custom:fwcam-card
    # Vehicle info
  - type: custom:fwcam-card
    # Refueling log
```

### 4. Badges
Consider adding badges above the card:
```yaml
type: vertical-stack
cards:
  - type: entity
    entity: sensor.my_car_fuel_price
    name: Current Price
  - type: custom:fwcam-card
    # ... config ...
```

---

## Common Configurations

### Configuration 1: Complete Dashboard
**Use case**: Main vehicle dashboard  
**Sections**: All enabled  
**Rows**: 10

### Configuration 2: Status Only
**Use case**: At-a-glance view  
**Sections**: Vehicle info only  
**Rows**: N/A

### Configuration 3: Log Manager
**Use case**: Refueling history management  
**Sections**: Log only  
**Rows**: 20+

### Configuration 4: Quick Controls
**Use case**: Control panel  
**Sections**: Controls + Settings  
**Rows**: N/A

---

## Screenshots

> **Note**: Actual screenshots can be added here once the card is installed and tested in a live Home Assistant environment.

**To take screenshots**:
1. Install the card following REFUELING_LOG_GUIDE.md
2. Configure as shown in examples above
3. Take screenshots in both light and dark mode
4. Add to this file or create separate screenshots directory

**Recommended screenshots**:
- Full card (all sections)
- Vehicle info section only
- Refueling log table
- Mobile view
- Dark mode vs light mode
- Different quality/confidence indicators

---

## Troubleshooting Visual Issues

### Card Not Displaying
- Check browser console for errors
- Verify resource is loaded in Lovelace resources
- Clear browser cache (Ctrl+F5)

### Incorrect Entity Detection
- Verify sensor entity exists and has correct naming
- Check entity state in Developer Tools → States
- Ensure integration is properly configured

### Styling Issues
- Card uses CSS variables from HA theme
- Custom themes may affect appearance
- Test with default HA theme first

### Mobile Display Issues
- Card is responsive but may require horizontal scroll for table
- Consider using vertical stack on mobile
- Test in mobile view (browser dev tools)

---

**For more information**: See REFUELING_LOG_GUIDE.md and www/fwcam-card/README.md
