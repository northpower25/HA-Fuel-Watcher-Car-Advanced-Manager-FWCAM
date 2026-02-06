# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Fuel Watcher Car Advanced Manager integration.

## Debug Features

The integration now includes comprehensive debug capabilities to help identify API and configuration issues.

### API Debug Sensor

A new sensor entity `sensor.[vehicle_name]_api_debug` provides detailed information about API requests:

**State**: Shows the API response status (`Success`, `Error`, or `Unknown`)

**Attributes** (available when API requests are made):
- `timestamp`: ISO timestamp of the last API request
- `location_source`: Indicates if using vehicle position or fallback coordinates
  - Example: `"vehicle (device_tracker.my_car)"` or `"fallback (configured)"`
- `latitude`: Latitude used for the API request
- `longitude`: Longitude used for the API request
- `radius_km`: Search radius in kilometers
- `fuel_type`: Type of fuel requested (e5, e10, diesel)
- `provider`: Fuel price provider name (tankerkonig)
- `api_response_status`: Result of API call (`success` or `error`)
- `stations_found`: Number of stations returned by API
- `stations_with_price_and_open`: Number of stations that are open and have valid prices
- `warning`: Any warning messages from the API call
- `error`: Error message if request failed
- `error_type`: Type of error exception

### Test API Connection Button

The `button.[vehicle_name]_test_api_connection` entity allows manual testing of the API connection.

**How to use**:
1. Navigate to the entity in Home Assistant
2. Press the button
3. Check the entity's attributes for detailed debug information

**Attributes after button press**:
- `success`: Boolean indicating if the test succeeded
- `message`: Human-readable result message
- `timestamp`: When the test was performed
- `location_source`: Data source for coordinates
- `latitude`, `longitude`: Coordinates used
- `radius_km`: Search radius used
- `fuel_type`: Fuel type requested
- `provider`: Provider being tested
- `api_url`: The API endpoint called
- `api_params`: Parameters sent (API key masked)
- `stations_total`: Total stations found
- `stations_with_price_and_open`: Stations that are open with valid prices
- `nearest_station`: Name of nearest station
- `nearest_price`: Price at nearest station
- `nearest_distance`: Distance to nearest station (km)
- `cheapest_station`: Name of cheapest open station
- `cheapest_price`: Price at cheapest station
- `cheapest_distance`: Distance to cheapest station (km)

### Configurable Search Radius

A new number entity `number.[vehicle_name]_search_radius` allows you to adjust the search radius dynamically:

**Range**: 1.0 to 25.0 km
**Step**: 0.5 km
**Unit**: Kilometers

**How to use**:
1. Go to the entity in Home Assistant UI
2. Adjust the value using the input box
3. The integration will automatically update and use the new radius

## Common Issues

### Issue: "No station found" even though stations exist nearby

**Symptoms**: 
- `sensor.[vehicle_name]_cheapest_station` shows "No station found"
- `sensor.[vehicle_name]_fuel_price` shows "Unknown" or no value

**Troubleshooting steps**:

1. **Check API Debug Sensor**:
   - Look at `sensor.[vehicle_name]_api_debug` attributes
   - Check `api_response_status` - should be "success"
   - Check `stations_found` - should be > 0
   - Check `stations_with_price_and_open` - this is the critical number

2. **Press Test Connection Button**:
   - Use `button.[vehicle_name]_test_api_connection`
   - Review all attributes for detailed diagnostics
   - Check if `api_url` and `api_params` look correct

3. **Verify Coordinates**:
   - Check `latitude` and `longitude` in debug attributes
   - Ensure coordinates are in Germany (Tankerkönig only covers Germany)
   - Check `location_source` to see if using vehicle or fallback
   - If using vehicle position, ensure the device tracker is working

4. **Increase Search Radius**:
   - Use `number.[vehicle_name]_search_radius` to increase radius
   - Try values like 10, 15, or even 25 km
   - Check if `stations_found` increases

5. **Check Fuel Type**:
   - Verify the configured fuel type matches what stations offer
   - Some stations may not have all fuel types available
   - Check configuration via Configuration > Integrations

6. **Station Filtering**:
   - Stations must be **both** open **and** have valid prices
   - Closed stations are filtered out even if they report prices
   - Stations without prices for your fuel type are filtered out
   - Check `stations_found` vs `stations_with_price_and_open` difference

### Issue: Invalid API Key

**Symptoms**:
- Test connection button shows "Invalid API key"
- API debug sensor shows error status

**Solution**:
1. Verify your Tankerkönig API key at https://creativecommons.tankerkoenig.de
2. Reconfigure the integration with correct API key
3. Test again using the button

### Issue: Using wrong location (home instead of car position)

**Symptoms**:
- Stations found are near home, not car
- `location_source` shows "fallback (configured)"

**Solution**:
1. Configure a position entity in integration options
2. Ensure the device tracker entity is working correctly
3. Check that device tracker has `latitude` and `longitude` attributes
4. After configuration, verify `location_source` shows vehicle entity name

### Issue: Automatic updates not working

**Symptoms**:
- Manual button test works
- Automatic sensor updates show old data
- Timestamp doesn't update

**Troubleshooting**:
1. Check `timestamp` in `api_debug` sensor - should update regularly
2. Verify update interval in integration options
3. Check Home Assistant logs for errors
4. Restart Home Assistant if needed

## Debugging Best Practices

1. **Start with the Test Button**: Always press `button.[vehicle_name]_test_api_connection` first
2. **Check Debug Sensor**: Review `sensor.[vehicle_name]_api_debug` for ongoing issues
3. **Enable Debug Logging**: Add to `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.hafwcma: debug
   ```
4. **Increase Radius Temporarily**: Use the number entity to test with larger radius
5. **Monitor Over Time**: Check if `timestamp` updates regularly in api_debug sensor

## Getting Help

If you still have issues after following this guide:

1. Collect debug information:
   - Screenshot of `button.[vehicle_name]_test_api_connection` attributes
   - Screenshot of `sensor.[vehicle_name]_api_debug` attributes
   - Relevant Home Assistant logs (with debug logging enabled)

2. Open an issue at: https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues

3. Include:
   - Debug information collected above
   - Your configuration (without API keys)
   - Description of expected vs actual behavior
   - Location (region/city) to verify API coverage

## API Rate Limiting

Tankerkönig API has rate limits:
- Do not set update interval below 5 minutes
- Excessive API calls may result in temporary blocking
- Use the configurable update interval wisely

## Data Privacy

Debug information includes:
- Exact coordinates (latitude/longitude)
- This data is only stored in Home Assistant
- API key is masked in button attributes
- No data is sent to external services except the configured fuel price provider
