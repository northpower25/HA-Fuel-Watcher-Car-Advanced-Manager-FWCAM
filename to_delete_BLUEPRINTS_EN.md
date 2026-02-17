# haFWCMA Blueprints - Complete Guide

Ready-to-use Home Assistant blueprints for the Fuel Watcher Car Advanced Manager (haFWCMA) integration.

---

## 🚀 Quick Import

### One-Click Import Links

Click the badge to import directly into Home Assistant:

#### Automation Blueprints

**Low Fuel Alert**
[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fnorthpower25%2FHA-Fuel-Watcher-Car-Advanced-Manager-FWCAM%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Flow_fuel_alert.yaml)

**Price Drop Notification**
[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fnorthpower25%2FHA-Fuel-Watcher-Car-Advanced-Manager-FWCAM%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fprice_drop_notification.yaml)

**Smart Refueling Reminder**
[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fnorthpower25%2FHA-Fuel-Watcher-Car-Advanced-Manager-FWCAM%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Frefueling_reminder.yaml)

**Trip Logging**
[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fnorthpower25%2FHA-Fuel-Watcher-Car-Advanced-Manager-FWCAM%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Ftrip_logging.yaml)

#### Script Blueprints

**Manual Refuel Entry**
[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fnorthpower25%2FHA-Fuel-Watcher-Car-Advanced-Manager-FWCAM%2Fblob%2Fmain%2Fblueprints%2Fscript%2Fmanual_refuel_entry.yaml)

**Trip Completion Handler**
[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fnorthpower25%2FHA-Fuel-Watcher-Car-Advanced-Manager-FWCAM%2Fblob%2Fmain%2Fblueprints%2Fscript%2Ftrip_completion.yaml)

**Fuel Price Query**
[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fnorthpower25%2FHA-Fuel-Watcher-Car-Advanced-Manager-FWCAM%2Fblob%2Fmain%2Fblueprints%2Fscript%2Ffuel_price_query.yaml)

---

## 📚 Blueprint Overview

### Automation Blueprints

#### 1. Low Fuel Alert
**Purpose**: Notify when tank level is low  
**Triggers**: Tank urgency level changes  
**Features**:
- Configurable urgency thresholds (critical, high, medium)
- Cooldown to prevent notification spam
- Smart messages based on urgency level
- Tank percentage and range information

**Example Notification**:
```
🚨 CRITICAL: Tank almost empty!
Your Car has only 5L (8%) remaining.
Range: approx. 40km
⛽ Please refuel IMMEDIATELY!
```

#### 2. Price Drop Notification
**Purpose**: Alert when fuel prices drop  
**Triggers**: Price falls below threshold  
**Features**:
- User-defined price threshold
- Optional station information
- Price trend analysis
- Savings calculation

**Example Notification**:
```
💰 Cheap Fuel Price!
Price dropped below 1.45€/L!

Current: 1.43€/L
Trend: falling

🏆 Cheapest Station:
Shell Main Street 123
Distance: 2.3km
Price: 1.41€/L
```

#### 3. Smart Refueling Reminder
**Purpose**: Daily reminder based on patterns  
**Triggers**: Time-based (configurable)  
**Features**:
- Combines tank level, price, and driving patterns
- Minimum urgency level filter
- Price status evaluation
- Recommended action included

**Example Notification**:
```
⛽ Refueling Reminder
💡 Refueling recommended in the next days

📊 Status:
• Tank: 32%
• Range: approx. 225km
• Days until empty: 3.5

💰 Price Info:
• Current: 1.48€/L
• Trend: rising
• ⏳ High price - wait if possible
```

#### 4. Trip Logging
**Purpose**: Automatic trip recording  
**Triggers**: Trip start/end detection  
**Features**:
- Optional notifications on trip events
- Pattern recognition integration
- Auto-categorization support
- Trip statistics in notifications

**Example Notification**:
```
🏁 Trip Completed
Trip: 25.5km in 32min
Purpose: work
Consumption: 7.2L/100km
Cost: 2.75€

📍 Pattern recognized: Home → Office
```

#### 5. Geolocation Proximity (Planned)
**Purpose**: Alert when near cheap station  
**Status**: Placeholder for future feature  
**Features**: Will notify when approaching stations with good prices

### Script Blueprints

#### 1. Manual Refuel Entry
**Purpose**: Quickly log a refueling event  
**Parameters**:
- Config Entry ID
- Liters refueled (required)
- Price per liter (optional)
- Odometer reading (optional)
- Station name (optional)
- Fuel type (diesel, e5, e10, super_plus)

**Usage Example**:
```yaml
alias: Quick Refuel Log
use_blueprint:
  path: manual_refuel_entry.yaml
  input:
    config_entry_id: "abc123"
    liters: 45.5
    price_per_liter: 1.599
    station_name: "Shell"
    fuel_type: diesel
```

#### 2. Trip Completion Handler
**Purpose**: Edit and categorize completed trips  
**Parameters**:
- Config Entry ID
- Trip ID
- Purpose (private, work, business, other)
- Notes (optional)
- Additional costs (optional)

**Usage Example**:
```yaml
alias: Mark Trip as Business
use_blueprint:
  path: trip_completion.yaml
  input:
    config_entry_id: "abc123"
    trip_id: "trip_20240115_080000"
    purpose: business
    notes: "Client visit in Munich"
    additional_costs: 5.50
```

#### 3. Fuel Price Query
**Purpose**: Get current prices on demand  
**Parameters**:
- Fuel price sensor
- Nearest station sensor
- Cheapest station sensor
- Notification service (optional)
- Include navigation links (optional)

**Result Example**:
```
⛽ Current Fuel Prices
💰 Current Price: 1.48€/L (diesel)
📈 Trend: rising

📍 Nearest Station:
Shell Main Street 123
Distance: 1.2km
Price: 1.48€/L

💎 Cheapest Station:
Aral Station Street 45
Distance: 3.5km
Price: 1.43€/L
💰 Savings: 0.05€/L (2.3km extra)
```

---

## 🔧 Configuration Guide

### Finding Your Config Entry ID

1. Go to **Developer Tools** → **States**
2. Search for a haFWCMA sensor (e.g., `sensor.my_car_fuel_price`)
3. Click on the sensor
4. Look for `config_entry_id` in attributes
5. Copy the value (e.g., `abc123def456`)

### Setting Up Notification Services

Blueprints use Home Assistant notification services. Common examples:

**Mobile App**:
```yaml
notify_service: notify.mobile_app_iphone
```

**Telegram**:
```yaml
notify_service: notify.telegram
```

**Multiple Services**:
```yaml
notify_service:
  - notify.mobile_app_iphone
  - notify.telegram
```

### Entity Filters

Blueprints automatically filter to show only haFWCMA entities using:
```yaml
selector:
  entity:
    filter:
      - integration: hafwcma
        domain: sensor
```

---

## 💡 Advanced Usage

### Combining Multiple Blueprints

Create a comprehensive fuel management automation system:

1. **Low Fuel Alert** - Know when to refuel
2. **Price Drop Notification** - Know when prices are good
3. **Smart Refueling Reminder** - Daily check at 6 PM
4. **Trip Logging** - Track all drives automatically

### Custom Modifications

Blueprints can be customized after import:

1. Import the blueprint
2. Create automation from blueprint
3. Switch to YAML mode
4. Modify conditions, actions, or triggers
5. Save as regular automation

### Dashboard Integration

Add buttons to trigger script blueprints:

```yaml
type: button
name: Log Refueling
icon: mdi:gas-station
tap_action:
  action: call-service
  service: script.manual_refuel_entry
```

### Voice Assistant Integration

Create Alexa/Google Assistant routines:

```yaml
intent_script:
  CheckFuelPrice:
    speech:
      text: "Current price is {{ states('sensor.my_car_fuel_price') }} euros per liter"
    action:
      service: script.fuel_price_query
```

---

## 🐛 Troubleshooting

### "Blueprint could not be imported"
- Check the URL for typos
- Ensure internet connection
- Try downloading manually and adding to `/config/blueprints/`

### "Entity not found"
- Verify haFWCMA integration is installed
- Check entity IDs in **Developer Tools** → **States**
- Adjust entity IDs to match your installation

### "Service not available"
- Ensure notification service is configured
- For Telegram: `telegram_bot` integration must be set up
- Test service in **Developer Tools** → **Services**

### "Config Entry ID invalid"
- Must be exact ID from sensor attributes
- Format: Usually alphanumeric string like `abc123def456`
- Don't confuse with entity_id

---

## 📖 Documentation

- **German Blueprint Guide**: [BLUEPRINTS_DE.md](../BLUEPRINTS_DE.md)
- **Main Documentation**: [README.md](../README.md)
- **German Full Documentation**: [DOKUMENTATION_DE.md](../DOKUMENTATION_DE.md)
- **Documentation Index**: [DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md)

---

## 🤝 Contributing

Have a useful blueprint? Share it!

1. Fork the repository
2. Add your blueprint to `blueprints/automation/` or `blueprints/script/`
3. Create a pull request
4. Include documentation

### Blueprint Guidelines

- Follow Home Assistant blueprint schema
- Include clear descriptions
- Use meaningful default values
- Add usage examples
- Test before submitting

---

## 📝 License

MIT License - See [LICENSE](../LICENSE)

---

**Version**: 1.0.0  
**Last Updated**: 2024-02-17  
**Home Assistant**: 2023.9+  
**Integration**: haFWCMA
