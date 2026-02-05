# Installation Guide

## Prerequisites

Before installing haFWCMA, ensure you have:

1. **Home Assistant** version 2023.1.0 or later
2. **HACS** (Home Assistant Community Store) installed (recommended)
3. **Tankerkönig API Key** - [Get it here](https://creativecommons.tankerkoenig.de)
4. **(Optional) Telegram Bot** - Create via [@BotFather](https://t.me/botfather)

## Method 1: HACS Installation (Recommended)

### Step 1: Add Custom Repository

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots menu (⋮) in the top right
4. Select "Custom repositories"
5. Enter the repository URL:
   ```
   https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM
   ```
6. Select "Integration" as the category
7. Click "Add"

### Step 2: Install Integration

1. Search for "Fuel Watcher Car Advanced Manager" in HACS
2. Click on the integration
3. Click "Download"
4. Select the latest version
5. Wait for the download to complete

### Step 3: Restart Home Assistant

1. Go to Settings → System → Restart
2. Wait for Home Assistant to restart

## Method 2: Manual Installation

### Step 1: Download Files

1. Download the latest release from GitHub
2. Extract the archive

### Step 2: Copy Files

1. Copy the `custom_components/hafwcma` directory to your Home Assistant `custom_components` directory:
   ```
   /config/custom_components/hafwcma/
   ```

2. Your directory structure should look like:
   ```
   custom_components/
   └── hafwcma/
       ├── __init__.py
       ├── manifest.json
       ├── config_flow.py
       ├── const.py
       ├── sensor.py
       ├── models/
       ├── providers/
       ├── sensors/
       ├── messaging/
       ├── utils/
       └── translations/
   ```

### Step 3: Restart Home Assistant

Restart Home Assistant to load the new integration.

## Configuration

### Step 1: Add Integration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Fuel Watcher Car Advanced Manager"
4. Click to start setup

### Step 2: Tankerkönig API Configuration

Enter your Tankerkönig credentials:

- **API Key**: Your Tankerkönig API key
- **Latitude**: Your location latitude (defaults to Home Assistant location)
- **Longitude**: Your location longitude (defaults to Home Assistant location)
- **Search Radius**: Radius to search for stations in km (default: 5)
- **Fuel Type**: Select E5, E10, or Diesel

### Step 3: Vehicle Configuration

Configure your vehicle:

- **Vehicle Name**: A friendly name (e.g., "My Car", "Tesla")
- **Tank Capacity**: Total tank capacity in liters

### Step 4: Telegram Configuration (Optional)

For notifications:

- **Bot Token**: Your Telegram bot token from @BotFather
- **Chat ID**: Your Telegram chat ID

To find your chat ID:
1. Start a chat with your bot
2. Send a message
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for "chat":{"id": YOUR_CHAT_ID

### Step 5: Complete Setup

Click "Submit" to create the integration.

## Verification

After setup, you should see new sensor entities:

- `sensor.<vehicle_name>_fuel_price`
- `sensor.<vehicle_name>_tank_level`
- `sensor.<vehicle_name>_range`
- `sensor.<vehicle_name>_nearest_station`

## Troubleshooting

### Integration Not Found

- Ensure you've restarted Home Assistant after installation
- Check that files are in the correct directory
- Check Home Assistant logs for errors

### API Connection Errors

- Verify your Tankerkönig API key is correct
- Check internet connectivity
- Ensure you're not exceeding API rate limits

### No Stations Found

- Increase search radius
- Verify latitude/longitude are correct
- Check if there are stations in your area

### Telegram Not Working

- Verify bot token is correct
- Ensure chat ID is correct
- Check that you've started a chat with the bot

## Next Steps

- Configure [automations](AUTOMATIONS.md)
- Customize your dashboard
- Set up notifications
- Explore advanced features

## Support

If you encounter issues:

1. Check the [FAQ](FAQ.md)
2. Search [existing issues](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)
3. Create a new issue with:
   - Home Assistant version
   - Integration version
   - Error logs
   - Steps to reproduce
