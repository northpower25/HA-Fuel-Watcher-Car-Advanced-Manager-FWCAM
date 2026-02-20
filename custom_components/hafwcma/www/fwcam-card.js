/**
 * FWCAM (Fuel Watcher Car Advanced Manager) Card
 * 
 * A custom Lovelace card for displaying and managing the Fuel Watcher Car Advanced Manager integration.
 * This card provides a central GUI for:
 * - Viewing and editing refueling log entries
 * - Displaying fuel price and vehicle information
 * - Controlling integration switches and number entities
 * - Managing integration settings
 * 
 * @version 1.0.0
 * @author northpower25
 * @license MIT
 * 
 * IMPORTANT FOR DEVELOPERS:
 * When adding new features to the FWCAM integration:
 * 1. Add new entities to the entity detection logic (findEntities method)
 * 2. Update the UI sections to display new entities
 * 3. Add new service calls if backend functionality is added
 * 4. Update the card editor if new configuration options are needed
 * 5. Update documentation in REFUELING_LOG_GUIDE.md
 */

// Constants
const SERVICE_CALL_REFRESH_DELAY_MS = 1000;
const DEFAULT_TANK_CAPACITY_LITERS = 99.99;
const DEFAULT_DAILY_DISTANCE_KM = 40.0;
const MAX_AUTOCOMPLETE_SUGGESTIONS = 10;

class FWCAMCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = null;
    this._entities = {};
    this._lastRender = 0;
    // State for refueling table sorting and filtering
    this._sortColumn = 'timestamp';
    this._sortDirection = 'desc';
    this._filterYear = '';
    this._filterMonth = '';
    // State for trip table sorting, filtering, and pagination
    this._tripSortColumn = 'timestamp_end';
    this._tripSortDirection = 'desc';
    this._tripCategoryFilter = '';
    this._tripFilterYear = '';
    this._tripFilterMonth = '';
    this._tripFilterDateFrom = '';
    this._tripFilterDateTo = '';
    this._tripCurrentPage = 1;
    // State for async data fetching
    this._allTripsFetched = false;
    this._allRefuelingsFetched = false;
    this._allTrips = [];
    this._allRefuelings = [];
    // Rate limiting for Nominatim API (1 request per second)
    this._lastNominatimRequest = 0;
  }

  /**
   * Set configuration for the card
   */
  setConfig(config) {
    if (!config.entity) {
      throw new Error('You need to define an entity (refueling_log sensor)');
    }
    
    // Check if any show_* options are explicitly set
    // Use Object.prototype.hasOwnProperty for safety
    const hasExplicitShowOptions = 
      Object.prototype.hasOwnProperty.call(config, 'show_refueling_log') ||
      Object.prototype.hasOwnProperty.call(config, 'show_trip_log') ||
      Object.prototype.hasOwnProperty.call(config, 'show_vehicle_info') ||
      Object.prototype.hasOwnProperty.call(config, 'show_controls') ||
      Object.prototype.hasOwnProperty.call(config, 'show_settings');
    
    // If any show_* option is explicitly set, only show those explicitly enabled
    // If no show_* options are set, default all to true (backward compatibility)
    const defaultShowValue = !hasExplicitShowOptions;
    
    this._config = {
      entity: config.entity,
      // Support for separate entity configuration per section
      refueling_log_entity: config.refueling_log_entity || config.entity,
      trip_log_entity: config.trip_log_entity || null,
      vehicle_info_entity: config.vehicle_info_entity || null,
      title: config.title || 'Fuel Watcher Car Advanced Manager',
      show_refueling_log: Object.prototype.hasOwnProperty.call(config, 'show_refueling_log') ? config.show_refueling_log : defaultShowValue,
      show_trip_log: Object.prototype.hasOwnProperty.call(config, 'show_trip_log') ? config.show_trip_log : defaultShowValue,
      show_vehicle_info: Object.prototype.hasOwnProperty.call(config, 'show_vehicle_info') ? config.show_vehicle_info : defaultShowValue,
      show_controls: Object.prototype.hasOwnProperty.call(config, 'show_controls') ? config.show_controls : defaultShowValue,
      show_settings: Object.prototype.hasOwnProperty.call(config, 'show_settings') ? config.show_settings : defaultShowValue,
      rows_per_page: config.rows_per_page || 10,
      refresh_interval: config.refresh_interval || 300,
      table_max_height: this.sanitizeCSSValue(config.table_max_height, '400px'),
      table_min_width: this.sanitizeCSSValue(config.table_min_width, '100%'),
      ...config
    };
    // Ensure first render happens immediately
    this._lastRender = 0;
    this.findEntities();
    this.render();
  }

  /**
   * Set Home Assistant instance
   */
  set hass(hass) {
    // Always store the hass instance
    this._hass = hass;
    
    // Skip throttling check if config not yet initialized
    if (!this._config || !this._config.refresh_interval) {
      return;
    }
    
    // Throttle rendering based on refresh_interval (in seconds)
    const now = Date.now();
    const intervalMs = this._config.refresh_interval * 1000;
    
    if (now - this._lastRender >= intervalMs) {
      this.render();
    }
  }

  /**
   * Get card size for layout
   */
  getCardSize() {
    return 10;
  }

  /**
   * Sanitize CSS value to prevent injection
   * Only allows positive numbers with safe CSS units
   */
  sanitizeCSSValue(value, defaultValue) {
    if (!value) return defaultValue;
    
    // Allow only safe CSS units: px, %, em, rem, vh, vw
    // Only positive numbers (negative/zero not useful for dimensions)
    const cssUnitPattern = /^(?:[1-9]\d*(?:\.\d+)?|0?\.\d+)(?:px|%|em|rem|vh|vw)$/;
    const trimmedValue = String(value).trim();
    
    if (cssUnitPattern.test(trimmedValue)) {
      return trimmedValue;
    }
    
    console.warn(`Invalid CSS value '${value}', using default '${defaultValue}'`);
    return defaultValue;
  }

  /**
   * Find all related entities for this integration instance
   * 
   * DEVELOPER NOTE: When adding new entity types to the integration,
   * update this method to detect and include them.
   */
  findEntities() {
    if (!this._hass) return;

    const configEntity = this._config.entity;
    const baseName = configEntity.replace('sensor.', '').replace('_refueling_log', '');
    
    // Auto-detect all related entities
    this._entities = {
      refueling_log: configEntity,
      // Sensors
      fuel_price: `sensor.${baseName}_fuel_price`,
      tank_level: `sensor.${baseName}_tank_level`,
      range: `sensor.${baseName}_range`,
      nearest_station: `sensor.${baseName}_nearest_station`,
      api_debug: `sensor.${baseName}_api_debug`,
      days_until_refuel: `sensor.${baseName}_days_until_refuel`,
      consumption_history: `sensor.${baseName}_consumption_history`,
      consumption_forecast: `sensor.${baseName}_consumption_forecast`,
      trip_log_sensor: `sensor.${baseName}_trip_log`,
      current_trip: `sensor.${baseName}_current_trip`,
      // Switches
      fuel_price_refresh: `switch.${baseName}_fuel_price_refresh`,
      consumption_prediction: `switch.${baseName}_consumption_prediction`,
      trip_tracking: `switch.${baseName}_trip_tracking`,
      // Numbers
      update_interval: `number.${baseName}_update_interval`,
      consumption_min_data_points: `number.${baseName}_consumption_min_data_points`,
      consumption_prediction_interval: `number.${baseName}_consumption_prediction_interval`,
      // Buttons
      test_connection: `button.${baseName}_test_connection`,
      import_historical_data: `button.${baseName}_import_historical_data`,
      import_historical_trip_data: `button.${baseName}_import_historical_trip_data`,
      refresh_vehicle_data: `button.${baseName}_refresh_vehicle_data`
    };
  }

  /**
   * Get state of an entity
   */
  getEntityState(entityId) {
    if (!this._hass || !entityId) return null;
    return this._hass.states[entityId];
  }

  /**
   * Get state value of an entity, returning null for unavailable/unknown states
   */
  getEntityStateValue(entityId) {
    const entity = this.getEntityState(entityId);
    if (!entity) return null;
    if (entity.state === 'unavailable' || entity.state === 'unknown') return null;
    return entity.state;
  }

  /**
   * Call a Home Assistant service
   */
  callService(domain, service, serviceData = {}) {
    if (!this._hass) return Promise.reject(new Error('Home Assistant not available'));
    
    return this._hass.callService(domain, service, serviceData).then(() => {
      // Reset fetch flags for data-modifying services to ensure fresh data on next render
      if (service.includes('trip') || service.includes('refuel')) {
        this._invalidateDataCache();
      }
      // Force render after service calls to show immediate feedback
      setTimeout(() => this.forceRender(), SERVICE_CALL_REFRESH_DELAY_MS);
    });
  }

  /**
   * Invalidate cached data flags to force re-fetching on next render
   */
  _invalidateDataCache() {
    this._allTripsFetched = false;
    this._allRefuelingsFetched = false;
  }

  /**
   * Toggle a switch entity
   */
  toggleSwitch(entityId) {
    const state = this.getEntityState(entityId);
    if (!state) return;
    
    const service = state.state === 'on' ? 'turn_off' : 'turn_on';
    this.callService('switch', service, { entity_id: entityId });
  }

  /**
   * Set value of a number entity
   */
  setNumberValue(entityId, value) {
    this.callService('number', 'set_value', {
      entity_id: entityId,
      value: parseFloat(value)
    });
  }

  /**
   * Press a button entity
   */
  pressButton(entityId) {
    this.callService('button', 'press', { entity_id: entityId });
  }

  /**
   * Fetch all trips for the current config entry
   * @returns {Promise<Array>} Array of all trips
   */
  async fetchAllTrips() {
    if (!this._hass) {
      console.warn('[FWCAM Card] Cannot fetch all trips: hass not available');
      return [];
    }
    
    try {
      const configEntryId = this.getConfigEntryId();
      const result = await this._hass.callService(
        'hafwcma',
        'get_all_trips',
        { config_entry_id: configEntryId },
        {},     // target
        true,   // notifyOnError
        true    // returnResponse
      );
      // Service response is wrapped in result.response
      return result?.response?.trips || [];
    } catch (error) {
      console.error('[FWCAM Card] Error fetching all trips:', error);
      // Fallback to recent_trips from sensor attributes
      const tripLogEntityId = this._config.trip_log_entity || this._entities.trip_log_sensor;
      const tripLogEntity = tripLogEntityId ? this.getEntityState(tripLogEntityId) : null;
      return tripLogEntity?.attributes?.recent_trips || [];
    }
  }

  /**
   * Fetch all refueling events for the current config entry
   * @returns {Promise<Array>} Array of all refueling events
   */
  async fetchAllRefuelings() {
    if (!this._hass) {
      console.warn('[FWCAM Card] Cannot fetch all refuelings: hass not available');
      return [];
    }
    
    try {
      const configEntryId = this.getConfigEntryId();
      const result = await this._hass.callService(
        'hafwcma',
        'get_all_refuelings',
        { config_entry_id: configEntryId },
        {},     // target
        true,   // notifyOnError
        true    // returnResponse
      );
      // Service response is wrapped in result.response
      return result?.response?.refuelings || [];
    } catch (error) {
      console.error('[FWCAM Card] Error fetching all refuelings:', error);
      // Fallback to recent_events from sensor attributes
      const refuelingLogEntityId = this._config.refueling_log_entity || this._entities.refueling_log_sensor;
      const refuelingLogEntity = refuelingLogEntityId ? this.getEntityState(refuelingLogEntityId) : null;
      return refuelingLogEntity?.attributes?.recent_events || [];
    }
  }

  /**
   * Fetch all trips asynchronously and update the card when done
   */
  async _fetchAllTripsAsync() {
    if (this._allTripsFetched) {
      console.log('[FWCAM Card] Skipping async trip fetch - already fetched');
      return; // Already fetched
    }
    
    console.log('[FWCAM Card] Starting async fetch of all trips...');
    try {
      const trips = await this.fetchAllTrips();
      this._allTrips = trips;
      this._allTripsFetched = true;
      console.log(`[FWCAM Card] ✓ Fetched ${trips.length} trips asynchronously`);
      // Re-render to show all trips
      this.forceRender();
    } catch (error) {
      console.error('[FWCAM Card] ✗ Error in async trip fetch:', error);
    }
  }

  /**
   * Fetch all refuelings asynchronously and update the card when done
   */
  async _fetchAllRefuelingsAsync() {
    if (this._allRefuelingsFetched) return; // Already fetched
    
    try {
      const refuelings = await this.fetchAllRefuelings();
      this._allRefuelings = refuelings;
      // Also update _recentEvents with the latest data for immediate use by edit dialog
      this._recentEvents = refuelings.slice(0, 10);
      this._allRefuelingsFetched = true;
      console.log(`[FWCAM Card] Fetched ${refuelings.length} refuelings asynchronously`);
      // Re-render to show all refuelings
      this.forceRender();
    } catch (error) {
      console.error('[FWCAM Card] Error in async refueling fetch:', error);
    }
  }

  /**
   * Add a new refueling event
   */
  addRefuelingEvent(eventData) {
    return this.callService('hafwcma', 'add_refuel_event', eventData);
  }

  /**
   * Update an existing refueling event
   */
  updateRefuelingEvent(eventData) {
    return this.callService('hafwcma', 'update_refuel_event', eventData);
  }

  /**
   * Get user's preferred language
   */
  getUserLanguage() {
    return this._hass?.language || 'en';
  }

  /**
   * Delete a refueling event
   */
  deleteRefuelingEvent(eventId) {
    const lang = this.getUserLanguage();
    const confirmMessages = {
      de: 'Sind Sie sicher, dass Sie diesen Tankvorgang löschen möchten?',
      en: 'Are you sure you want to delete this refueling event?'
    };
    const message = confirmMessages[lang] || confirmMessages['en'];
    
    if (confirm(message)) {
      this.callService('hafwcma', 'delete_refuel_event', {
        config_entry_id: this.getConfigEntryId(),
        event_id: eventId
      });
    }
  }

  /**
   * Edit a trip
   */
  editTrip(tripData) {
    return this.callService('hafwcma', 'edit_trip', tripData);
  }

  /**
   * Delete a trip
   */
  deleteTrip(tripId) {
    const lang = this.getUserLanguage();
    const confirmMessages = {
      de: 'Sind Sie sicher, dass Sie diese Fahrt löschen möchten?',
      en: 'Are you sure you want to delete this trip?'
    };
    const message = confirmMessages[lang] || confirmMessages['en'];
    
    if (confirm(message)) {
      this.callService('hafwcma', 'delete_trip', {
        config_entry_id: this.getConfigEntryId(),
        trip_id: tripId
      });
    }
  }

  /**
   * Get tank capacity from config
   */
  getTankCapacity() {
    // Try to get from various sources
    const entity = this.getEntityState(this._config.entity);
    
    // Check if tank capacity is in any related sensor attributes
    const tankSensor = this.getEntityState(this._entities.tank_level);
    if (tankSensor && tankSensor.attributes && tankSensor.attributes.tank_capacity) {
      return parseFloat(tankSensor.attributes.tank_capacity);
    }
    
    // Default fallback - configurable via constant
    return DEFAULT_TANK_CAPACITY_LITERS;
  }

  /**
   * Build unique station list from recent events
   */
  getUniqueStations() {
    if (!this._recentEvents) return [];
    
    const stations = new Map();
    
    for (const event of this._recentEvents) {
      if (event.station_name) {
        const key = `${event.station_name}|${event.station_address || ''}`;
        if (!stations.has(key)) {
          stations.set(key, {
            name: event.station_name,
            address: event.station_address || '',
            // Parse address components if available
            city: this._extractCity(event.station_address),
            street: this._extractStreet(event.station_address)
          });
        }
      }
    }
    
    return Array.from(stations.values());
  }

  /**
   * Extract city from address (simple heuristic)
   */
  _extractCity(address) {
    if (!address) return '';
    // Common German address format: "Street Number, PLZ City"
    const parts = address.split(',');
    if (parts.length >= 2) {
      const cityPart = parts[parts.length - 1].trim();
      // Remove PLZ (postal code) if present
      return cityPart.replace(/^\d{5}\s*/, '').trim();
    }
    return address;
  }

  /**
   * Extract street from address (simple heuristic)
   */
  _extractStreet(address) {
    if (!address) return '';
    const parts = address.split(',');
    return parts[0].trim();
  }

  /**
   * Filter stations by search query
   */
  filterStations(query, stations) {
    if (!query) return stations;
    
    const lowerQuery = query.toLowerCase();
    const queryParts = lowerQuery.split(/\s+/);
    
    return stations.filter(station => {
      const searchText = `${station.name} ${station.city} ${station.street}`.toLowerCase();
      // All query parts must be found in the search text
      return queryParts.every(part => searchText.includes(part));
    });
  }

  /**
   * Get last fuel type from recent events
   */
  getLastFuelType() {
    if (!this._recentEvents || this._recentEvents.length === 0) return '';
    
    // Events are already sorted by timestamp (newest first)
    for (const event of this._recentEvents) {
      if (event.fuel_type) {
        return event.fuel_type;
      }
    }
    
    return '';
  }

  /**
   * Estimate odometer reading based on last refueling and average consumption
   */
  estimateOdometer(targetDate) {
    if (!this._recentEvents || this._recentEvents.length === 0) return null;
    
    // Find the last event with an odometer reading
    const lastEvent = this._recentEvents.find(e => e.odometer_km);
    if (!lastEvent) return null;
    
    const lastOdometer = lastEvent.odometer_km;
    const lastDate = new Date(lastEvent.timestamp);
    const targetDateTime = new Date(targetDate);
    
    // Calculate days elapsed
    const daysElapsed = (targetDateTime - lastDate) / (1000 * 60 * 60 * 24);
    
    // Get average daily km from consumption history sensor
    const consumptionHistory = this.getEntityState(this._entities.consumption_history);
    let dailyKm = DEFAULT_DAILY_DISTANCE_KM; // Configurable fallback
    
    if (consumptionHistory && consumptionHistory.attributes) {
      // Try to get average daily distance
      if (consumptionHistory.attributes.avg_daily_distance_km) {
        dailyKm = consumptionHistory.attributes.avg_daily_distance_km;
      }
    }
    
    // Estimate new odometer
    const estimatedKm = Math.round(lastOdometer + (daysElapsed * dailyKm));
    return Math.max(lastOdometer, estimatedKm); // Never go backwards
  }

  /**
   * Format date/time for display
   */
  formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
  }

  /**
   * Format number with unit
   */
  formatNumber(value, decimals = 1, unit = '') {
    if (value === null || value === undefined || value === 'unavailable' || value === 'unknown') return 'N/A';
    const num = parseFloat(value);
    if (isNaN(num)) return 'N/A';
    return `${num.toFixed(decimals)}${unit ? ' ' + unit : ''}`;
  }

  /**
   * Force an immediate render (bypasses throttling)
   * Used after user interactions to provide immediate feedback
   * Note: _lastRender will be updated by render() after successful completion
   */
  forceRender() {
    this.render();
  }

  /**
   * Render the card
   */
  render() {
    if (!this._hass || !this._config.entity) return;

    const entity = this.getEntityState(this._config.entity);
    if (!entity) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div class="card-content">
            <p class="error">Entity ${this._config.entity} not found</p>
          </div>
        </ha-card>
      `;
      return;
    }

    // Get refueling log data from configured entity or default
    const refuelingEntity = this._config.refueling_log_entity 
      ? this.getEntityState(this._config.refueling_log_entity)
      : entity;
    const recentEvents = refuelingEntity?.attributes?.recent_events || [];
    const lastRefueling = refuelingEntity?.attributes?.last_refueling || null;
    
    // Store events for dialog access (use recent for now, fetch all when needed)
    this._recentEvents = recentEvents;
    // Only reset _allRefuelings if we haven't fetched all refuelings yet
    if (!this._allRefuelingsFetched) {
      this._allRefuelings = recentEvents;
    }
    
    // Trigger async fetch of all refuelings if we haven't fetched them yet
    if (!this._allRefuelingsFetched && this._config.show_refueling_log) {
      this._fetchAllRefuelingsAsync();
    }
    
    // Get trip log data from configured entity or auto-detected entity
    const tripLogEntityId = this._config.trip_log_entity || this._entities.trip_log_sensor;
    const tripLogEntity = tripLogEntityId ? this.getEntityState(tripLogEntityId) : null;
    // Use recent_trips from attributes (limited to last 10 to avoid 16KB limit)
    const recentTrips = tripLogEntity?.attributes?.recent_trips || [];
    
    // Debug logging for trip data
    if (this._config.show_trip_log) {
      console.log('[FWCAM Card] Trip Log Debugging:');
      console.log('  - Expected Entity ID:', tripLogEntityId);
      console.log('  - Entity Found:', tripLogEntity ? 'Yes' : 'No');
      if (tripLogEntity) {
        console.log('  - Entity State:', tripLogEntity.state);
        console.log('  - Has recent_trips:', tripLogEntity.attributes?.recent_trips ? 'Yes' : 'No');
        console.log('  - Recent Trips Count:', recentTrips.length);
      } else {
        console.warn('[FWCAM Card] Trip log entity not found! Available entities:', Object.keys(this._hass.states).filter(e => e.includes('trip')));
      }
    }
    
    // Store events and trips for dialog access
    // For initial display, use recent items. All items will be fetched async when needed
    // Only reset _allTrips if we haven't fetched all trips yet
    if (!this._allTripsFetched) {
      this._allTrips = recentTrips;
    }
    // Trigger async fetch of all trips if we haven't fetched them yet
    if (!this._allTripsFetched && (this._config.show_trip_log || this._config.show_vehicle_info)) {
      this._fetchAllTripsAsync();
    }

    this.shadowRoot.innerHTML = `
      ${this.getStyles()}
      <ha-card>
        <div class="card-header">
          <div class="name">${this._config.title}</div>
        </div>
        
        <div class="card-content">
          ${this._config.show_vehicle_info ? this.renderVehicleInfo() : ''}
          ${this._config.show_controls ? this.renderControls() : ''}
          ${this._config.show_settings ? this.renderSettings() : ''}
          ${this._config.show_refueling_log ? this.renderRefuelingLog(this._allRefuelings || [], lastRefueling) : ''}
          ${this._config.show_trip_log ? this.renderTripLog(this._allTrips || []) : ''}
        </div>
      </ha-card>
      ${this.renderDialog()}
      ${this.renderTripDialog()}
    `;


    this.attachEventListeners();
    
    // Update last render timestamp only after successful render
    this._lastRender = Date.now();
  }

  /**
   * Render vehicle information section
   */
  renderVehicleInfo() {
    const fuelPrice = this.getEntityState(this._entities.fuel_price);
    const tankLevel = this.getEntityState(this._entities.tank_level);
    const range = this.getEntityState(this._entities.range);
    const nearestStation = this.getEntityStateValue(this._entities.nearest_station);
    const daysUntilRefuel = this.getEntityState(this._entities.days_until_refuel);

    return `
      <div class="section">
        <h3>Vehicle Information</h3>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">Fuel Price:</span>
            <span class="value">${fuelPrice ? this.formatNumber(fuelPrice.state, 3, '€/L') : 'N/A'}</span>
          </div>
          <div class="info-item">
            <span class="label">Tank Level:</span>
            <span class="value">${tankLevel ? this.formatNumber(tankLevel.state, 0, '%') : 'N/A'}</span>
          </div>
          <div class="info-item">
            <span class="label">Range:</span>
            <span class="value">${range ? this.formatNumber(range.state, 0, 'km') : 'N/A'}</span>
          </div>
          <div class="info-item">
            <span class="label">Nearest Station:</span>
            <span class="value">${nearestStation || 'N/A'}</span>
          </div>
          <div class="info-item">
            <span class="label">Days Until Refuel:</span>
            <span class="value">${daysUntilRefuel ? this.formatNumber(daysUntilRefuel.state, 1) : 'N/A'}</span>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Render control buttons section
   */
  renderControls() {
    const fuelPriceRefresh = this.getEntityState(this._entities.fuel_price_refresh);
    const consumptionPrediction = this.getEntityState(this._entities.consumption_prediction);

    return `
      <div class="section">
        <h3>Controls</h3>
        <div class="controls-grid">
          <button class="control-button" data-action="toggle-switch" data-entity="${this._entities.fuel_price_refresh}">
            <ha-icon icon="mdi:refresh"></ha-icon>
            <span>Refresh Fuel Prices</span>
          </button>
          <button class="control-button" data-action="toggle-switch" data-entity="${this._entities.consumption_prediction}">
            <ha-icon icon="mdi:chart-line"></ha-icon>
            <span>Update Prediction</span>
          </button>
          <button class="control-button" data-action="press-button" data-entity="${this._entities.test_connection}">
            <ha-icon icon="mdi:connection"></ha-icon>
            <span>Test Connection</span>
          </button>
          <button class="control-button" data-action="press-button" data-entity="${this._entities.import_historical_data}">
            <ha-icon icon="mdi:database-import"></ha-icon>
            <span>Import History</span>
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Render settings section
   */
  renderSettings() {
    const updateInterval = this.getEntityState(this._entities.update_interval);
    const minDataPoints = this.getEntityState(this._entities.consumption_min_data_points);
    const predictionInterval = this.getEntityState(this._entities.consumption_prediction_interval);

    return `
      <div class="section">
        <h3>Settings</h3>
        <div class="settings-grid">
          <div class="setting-item">
            <label>API Update Interval (min):</label>
            <input type="number" 
                   class="setting-input" 
                   data-entity="${this._entities.update_interval}"
                   value="${updateInterval ? updateInterval.state : ''}"
                   min="1" max="60" step="1">
          </div>
          <div class="setting-item">
            <label>Min Data Points:</label>
            <input type="number" 
                   class="setting-input" 
                   data-entity="${this._entities.consumption_min_data_points}"
                   value="${minDataPoints ? minDataPoints.state : ''}"
                   min="2" max="50" step="1">
          </div>
          <div class="setting-item">
            <label>Prediction Interval (h):</label>
            <input type="number" 
                   class="setting-input" 
                   data-entity="${this._entities.consumption_prediction_interval}"
                   value="${predictionInterval ? predictionInterval.state : ''}"
                   min="0.5" max="24" step="0.5">
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Render refueling log section with inline editing, sorting, and filtering
   */
  renderRefuelingLog(events, lastRefueling) {
    // Apply filtering
    const filteredEvents = this.filterEvents(events);
    
    // Apply sorting
    const sortedEvents = this.sortEvents(filteredEvents);
    
    // Get unique years and months for filter dropdowns
    const years = this.getUniqueYears(events);
    const months = [
      { value: '', label: 'All Months' },
      { value: '01', label: 'January' },
      { value: '02', label: 'February' },
      { value: '03', label: 'March' },
      { value: '04', label: 'April' },
      { value: '05', label: 'May' },
      { value: '06', label: 'June' },
      { value: '07', label: 'July' },
      { value: '08', label: 'August' },
      { value: '09', label: 'September' },
      { value: '10', label: 'October' },
      { value: '11', label: 'November' },
      { value: '12', label: 'December' }
    ];
    
    return `
      <div class="section">
        <h3>Refueling Log</h3>
        
        ${lastRefueling ? `
          <div class="last-refueling">
            <strong>Last Refueling:</strong> 
            ${this.formatDateTime(lastRefueling.timestamp)} - 
            ${this.formatNumber(lastRefueling.liters, 2, 'L')} @ 
            ${lastRefueling.station || 'Unknown Station'}
          </div>
        ` : ''}

        <div class="filter-controls">
          <label>
            Year:
            <select class="filter-select" data-filter="year">
              <option value="">All Years</option>
              ${years.map(year => `
                <option value="${year}" ${this._filterYear === year ? 'selected' : ''}>${year}</option>
              `).join('')}
            </select>
          </label>
          <label>
            Month:
            <select class="filter-select" data-filter="month">
              ${months.map(month => `
                <option value="${month.value}" ${this._filterMonth === month.value ? 'selected' : ''}>${month.label}</option>
              `).join('')}
            </select>
          </label>
          ${(this._filterYear || this._filterMonth) ? `
            <button class="clear-filters-button" data-action="clear-filters">
              <ha-icon icon="mdi:filter-remove"></ha-icon>
              <span>Clear Filters</span>
            </button>
          ` : ''}
          <div class="filter-info">
            Showing ${sortedEvents.length} of ${events.length} events
          </div>
        </div>

        <div class="table-container">
          <table class="refueling-table">
            <thead>
              <tr>
                <th class="sortable ${this._sortColumn === 'timestamp' ? 'sorted-' + this._sortDirection : ''}" 
                    data-sort-column="timestamp">
                  Date/Time
                  ${this.renderSortIcon('timestamp')}
                </th>
                <th class="sortable ${this._sortColumn === 'odometer_km' ? 'sorted-' + this._sortDirection : ''}" 
                    data-sort-column="odometer_km">
                  Odometer (km)
                  ${this.renderSortIcon('odometer_km')}
                </th>
                <th class="sortable ${this._sortColumn === 'liters_refueled' ? 'sorted-' + this._sortDirection : ''}" 
                    data-sort-column="liters_refueled">
                  Liters
                  ${this.renderSortIcon('liters_refueled')}
                </th>
                <th class="sortable ${this._sortColumn === 'price_per_liter' ? 'sorted-' + this._sortDirection : ''}" 
                    data-sort-column="price_per_liter">
                  Price/L (€)
                  ${this.renderSortIcon('price_per_liter')}
                </th>
                <th class="sortable ${this._sortColumn === 'total_cost' ? 'sorted-' + this._sortDirection : ''}" 
                    data-sort-column="total_cost">
                  Total (€)
                  ${this.renderSortIcon('total_cost')}
                </th>
                <th class="sortable ${this._sortColumn === 'station_name' ? 'sorted-' + this._sortDirection : ''}" 
                    data-sort-column="station_name">
                  Station
                  ${this.renderSortIcon('station_name')}
                </th>
                <th>Quality</th>
                <th>Confidence</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${sortedEvents.length === 0 ? `
                <tr>
                  <td colspan="9" class="no-data">No refueling events match the current filters</td>
                </tr>
              ` : sortedEvents.slice(0, this._config.rows_per_page).map(event => `
                <tr data-event-id="${event.id}">
                  <td>${this.formatDateTime(event.timestamp)}</td>
                  <td>${event.odometer_km || 'N/A'}</td>
                  <td>${this.formatNumber(event.liters_refueled, 2)}</td>
                  <td>${this.formatNumber(event.price_per_liter, 3)}</td>
                  <td>${this.formatNumber(event.total_cost, 2)}</td>
                  <td>${event.station_name || 'Unknown'}</td>
                  <td>
                    <span class="quality-badge quality-${event.data_quality}">
                      ${event.data_quality}
                    </span>
                  </td>
                  <td>
                    <span class="confidence-badge confidence-${this.getConfidenceLevel(event.confidence)}">
                      ${Math.round(event.confidence * 100)}%
                    </span>
                  </td>
                  <td class="actions">
                    <button class="action-button edit-button" 
                            data-action="edit" 
                            data-event-id="${event.id}"
                            title="Edit">
                      <ha-icon icon="mdi:pencil"></ha-icon>
                    </button>
                    <button class="action-button delete-button" 
                            data-action="delete" 
                            data-event-id="${event.id}"
                            title="Delete">
                      <ha-icon icon="mdi:delete"></ha-icon>
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>

        <button class="add-event-button" data-action="add-event">
          <ha-icon icon="mdi:plus"></ha-icon>
          <span>Add Refueling Event</span>
        </button>
      </div>
    `;
  }

  /**
   * Get confidence level category
   */
  getConfidenceLevel(confidence) {
    if (confidence >= 0.7) return 'high';
    if (confidence >= 0.4) return 'medium';
    return 'low';
  }

  /**
   * Render sort icon for table headers
   */
  renderSortIcon(column) {
    if (this._sortColumn !== column) {
      return '<ha-icon icon="mdi:unfold-more-horizontal" class="sort-icon inactive"></ha-icon>';
    }
    const icon = this._sortDirection === 'asc' ? 'mdi:arrow-up' : 'mdi:arrow-down';
    return `<ha-icon icon="${icon}" class="sort-icon active"></ha-icon>`;
  }

  /**
   * Filter events by year and month
   */
  filterEvents(events) {
    if (!events || events.length === 0) return [];
    
    return events.filter(event => {
      if (!event.timestamp) return false;
      
      const eventDate = new Date(event.timestamp);
      const eventYear = eventDate.getFullYear().toString();
      const eventMonth = (eventDate.getMonth() + 1).toString().padStart(2, '0');
      
      // Apply year filter
      if (this._filterYear && eventYear !== this._filterYear) {
        return false;
      }
      
      // Apply month filter
      if (this._filterMonth && eventMonth !== this._filterMonth) {
        return false;
      }
      
      return true;
    });
  }

  /**
   * Sort events by column and direction
   */
  sortEvents(events) {
    if (!events || events.length === 0) return [];
    
    const sorted = [...events].sort((a, b) => {
      let aVal = a[this._sortColumn];
      let bVal = b[this._sortColumn];
      
      // Handle null/undefined values
      if (aVal === null || aVal === undefined) aVal = '';
      if (bVal === null || bVal === undefined) bVal = '';
      
      // Convert to comparable types
      if (this._sortColumn === 'timestamp') {
        aVal = new Date(aVal).getTime();
        bVal = new Date(bVal).getTime();
      } else if (['odometer_km', 'liters_refueled', 'price_per_liter', 'total_cost'].includes(this._sortColumn)) {
        aVal = parseFloat(aVal) || 0;
        bVal = parseFloat(bVal) || 0;
      } else {
        // String comparison for station_name
        aVal = String(aVal).toLowerCase();
        bVal = String(bVal).toLowerCase();
      }
      
      if (aVal < bVal) return this._sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return this._sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
    
    return sorted;
  }

  /**
   * Get unique years from events for filter dropdown
   */
  getUniqueYears(events) {
    if (!events || events.length === 0) return [];
    
    const years = new Set();
    events.forEach(event => {
      if (event.timestamp) {
        const year = new Date(event.timestamp).getFullYear();
        years.add(year.toString());
      }
    });
    
    return Array.from(years).sort((a, b) => b - a); // Sort descending (newest first)
  }

  /**
   * Handle sort column click
   */
  handleSort(column) {
    if (this._sortColumn === column) {
      // Toggle direction if clicking same column
      this._sortDirection = this._sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      // Set new column with default direction
      this._sortColumn = column;
      this._sortDirection = column === 'timestamp' ? 'desc' : 'asc';
    }
    this.render();
  }

  /**
   * Handle filter change
   */
  handleFilterChange(filterType, value) {
    if (filterType === 'year') {
      this._filterYear = value;
    } else if (filterType === 'month') {
      this._filterMonth = value;
    }
    this.render();
  }

  /**
   * Clear all filters
   */
  clearFilters() {
    this._filterYear = '';
    this._filterMonth = '';
    this.render();
  }

  /**
   * Handle trip table sorting
   */
  handleTripSort(column) {
    if (this._tripSortColumn === column) {
      // Toggle direction if clicking same column
      this._tripSortDirection = this._tripSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      // Set new column with default direction
      this._tripSortColumn = column;
      this._tripSortDirection = column === 'timestamp_end' ? 'desc' : 'asc';
    }
    this.render();
  }

  /**
   * Handle trip filter change
   */
  handleTripFilterChange(category) {
    this._tripCategoryFilter = category;
    this.render();
  }

  /**
   * Clear trip filters
   */
  clearTripFilters() {
    this._tripCategoryFilter = '';
    this._tripFilterYear = '';
    this._tripFilterMonth = '';
    this._tripFilterDateFrom = '';
    this._tripFilterDateTo = '';
    this._tripCurrentPage = 1;
    this.render();
  }
  
  /**
   * Filter trips by date, category, and date range
   */
  filterTrips(trips) {
    if (!trips || trips.length === 0) return [];
    
    return trips.filter(trip => {
      if (!trip.timestamp_end) return false;
      
      const tripDate = new Date(trip.timestamp_end);
      const tripYear = tripDate.getFullYear().toString();
      const tripMonth = (tripDate.getMonth() + 1).toString().padStart(2, '0');
      const tripDateStr = tripDate.toISOString().split('T')[0]; // YYYY-MM-DD
      
      // Apply year filter
      if (this._tripFilterYear && tripYear !== this._tripFilterYear) {
        return false;
      }
      
      // Apply month filter
      if (this._tripFilterMonth && tripMonth !== this._tripFilterMonth) {
        return false;
      }
      
      // Apply category filter
      if (this._tripCategoryFilter && trip.category !== this._tripCategoryFilter) {
        return false;
      }
      
      // Apply date from filter
      if (this._tripFilterDateFrom && tripDateStr < this._tripFilterDateFrom) {
        return false;
      }
      
      // Apply date to filter
      if (this._tripFilterDateTo && tripDateStr > this._tripFilterDateTo) {
        return false;
      }
      
      return true;
    });
  }
  
  /**
   * Sort trips by column and direction
   */
  sortTrips(trips) {
    if (!trips || trips.length === 0) return [];
    
    const sortColumn = this._tripSortColumn || 'timestamp_end';
    const sortDirection = this._tripSortDirection || 'desc';
    
    const sorted = [...trips].sort((a, b) => {
      let aVal = a[sortColumn];
      let bVal = b[sortColumn];
      
      // Handle null/undefined values
      if (aVal === null || aVal === undefined) aVal = '';
      if (bVal === null || bVal === undefined) bVal = '';
      
      // Convert to comparable types
      if (sortColumn === 'timestamp_end' || sortColumn === 'timestamp_start') {
        aVal = new Date(aVal).getTime();
        bVal = new Date(bVal).getTime();
      } else if (['distance_km', 'fuel_consumed', 'fuel_cost', 'additional_costs'].includes(sortColumn)) {
        aVal = parseFloat(aVal) || 0;
        bVal = parseFloat(bVal) || 0;
      } else {
        // String comparison for category, purpose
        aVal = String(aVal).toLowerCase();
        bVal = String(bVal).toLowerCase();
      }
      
      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
    
    return sorted;
  }
  
  /**
   * Get unique years from trips for filter dropdown
   */
  getUniqueTripYears(trips) {
    if (!trips || trips.length === 0) return [];
    
    const years = new Set();
    trips.forEach(trip => {
      if (trip.timestamp_end) {
        const year = new Date(trip.timestamp_end).getFullYear();
        years.add(year.toString());
      }
    });
    
    return Array.from(years).sort((a, b) => b - a); // Sort descending (newest first)
  }
  
  /**
   * Handle trip filter change (all types)
   */
  handleTripFilterChange(filterType, value) {
    if (filterType === 'trip-year') {
      this._tripFilterYear = value;
    } else if (filterType === 'trip-month') {
      this._tripFilterMonth = value;
    } else if (filterType === 'trip-category') {
      this._tripCategoryFilter = value;
    } else if (filterType === 'trip-date-from') {
      this._tripFilterDateFrom = value;
    } else if (filterType === 'trip-date-to') {
      this._tripFilterDateTo = value;
    }
    this._tripCurrentPage = 1; // Reset to first page when filter changes
    this.render();
  }
  
  /**
   * Handle trip pagination
   */
  handleTripPagination(direction) {
    if (direction === 'next') {
      this._tripCurrentPage++;
    } else if (direction === 'prev') {
      this._tripCurrentPage = Math.max(1, this._tripCurrentPage - 1);
    }
    this.render();
  }

  /**
   * Attach event listeners to interactive elements
   */
  attachEventListeners() {
    // Control buttons
    this.shadowRoot.querySelectorAll('.control-button').forEach(button => {
      button.addEventListener('click', (e) => {
        const action = e.currentTarget.dataset.action;
        const entity = e.currentTarget.dataset.entity;
        
        if (action === 'toggle-switch') {
          this.toggleSwitch(entity);
        } else if (action === 'press-button') {
          this.pressButton(entity);
        }
      });
    });

    // Settings inputs
    this.shadowRoot.querySelectorAll('.setting-input').forEach(input => {
      input.addEventListener('change', (e) => {
        const entity = e.target.dataset.entity;
        const value = e.target.value;
        this.setNumberValue(entity, value);
      });
    });

    // Refueling log and trip log action buttons
    this.shadowRoot.querySelectorAll('.action-button').forEach(button => {
      button.addEventListener('click', (e) => {
        const action = e.currentTarget.dataset.action;
        const eventId = e.currentTarget.dataset.eventId;
        const tripId = e.currentTarget.dataset.tripId;
        
        if (action === 'edit') {
          this.showEditDialog(eventId);
        } else if (action === 'delete') {
          this.deleteRefuelingEvent(eventId);
        } else if (action === 'edit-trip') {
          this.showEditTripDialog(tripId);
        } else if (action === 'delete-trip') {
          this.deleteTrip(tripId);
        }
      });
    });

    // Add event button (refueling and trips)
    const addButton = this.shadowRoot.querySelector('[data-action="add-event"]');
    if (addButton) {
      addButton.addEventListener('click', () => {
        this.showAddDialog();
      });
    }

    const addTripButton = this.shadowRoot.querySelector('[data-action="add-trip"]');
    if (addTripButton) {
      addTripButton.addEventListener('click', () => {
        this.showAddTripDialog();
      });
    }

    // Sort column headers (refueling and trips)
    this.shadowRoot.querySelectorAll('.sortable').forEach(header => {
      header.addEventListener('click', (e) => {
        const column = e.currentTarget.dataset.sortColumn;
        const sortType = e.currentTarget.dataset.sortType; // 'trip' or undefined for refueling
        if (sortType === 'trip') {
          this.handleTripSort(column);
        } else {
          this.handleSort(column);
        }
      });
    });

    // Filter dropdowns and date inputs (refueling and trips)
    this.shadowRoot.querySelectorAll('.filter-select, .filter-date').forEach(input => {
      input.addEventListener('change', (e) => {
        const filterType = e.target.dataset.filter;
        const value = e.target.value;
        if (filterType && filterType.startsWith('trip-')) {
          this.handleTripFilterChange(filterType, value);
        } else {
          this.handleFilterChange(filterType, value);
        }
      });
    });

    // Clear filters button (refueling and trips)
    const clearFiltersButton = this.shadowRoot.querySelector('[data-action="clear-filters"]');
    if (clearFiltersButton) {
      clearFiltersButton.addEventListener('click', () => {
        this.clearFilters();
      });
    }

    const clearTripFiltersButton = this.shadowRoot.querySelector('[data-action="clear-trip-filters"]');
    if (clearTripFiltersButton) {
      clearTripFiltersButton.addEventListener('click', () => {
        this.clearTripFilters();
      });
    }

    // Trip pagination buttons
    const tripPrevButton = this.shadowRoot.querySelector('[data-action="trip-prev-page"]');
    if (tripPrevButton) {
      tripPrevButton.addEventListener('click', () => {
        this.handleTripPagination('prev');
      });
    }

    const tripNextButton = this.shadowRoot.querySelector('[data-action="trip-next-page"]');
    if (tripNextButton) {
      tripNextButton.addEventListener('click', () => {
        this.handleTripPagination('next');
      });
    }

    // Dialog close buttons
    this.shadowRoot.querySelectorAll('[data-action="close-dialog"]').forEach(button => {
      button.addEventListener('click', () => {
        this.closeDialog();
      });
    });

    // Dialog form submission
    const refuelForm = this.shadowRoot.getElementById('refuel-form');
    if (refuelForm) {
      refuelForm.addEventListener('submit', (e) => {
        this.handleFormSubmit(e);
      });
    }

    // Close dialog on background click
    const dialogOverlay = this.shadowRoot.getElementById('refuel-dialog');
    if (dialogOverlay) {
      dialogOverlay.addEventListener('click', (e) => {
        if (e.target === dialogOverlay) {
          this.closeDialog();
        }
      });
    }

    // Reverse geocoding buttons
    this.shadowRoot.querySelectorAll('[data-action="reverse-geocode-start"], [data-action="reverse-geocode-end"]').forEach(button => {
      button.addEventListener('click', async (e) => {
        const action = e.currentTarget.dataset.action;
        const isStart = action === 'reverse-geocode-start';
        await this.handleReverseGeocode(isStart);
      });
    });

    // Trip dialog close buttons
    this.shadowRoot.querySelectorAll('[data-action="close-trip-dialog"]').forEach(button => {
      button.addEventListener('click', () => {
        this.closeTripDialog();
      });
    });

    // Trip dialog form submission
    const tripForm = this.shadowRoot.getElementById('trip-form');
    if (tripForm) {
      const submitButton = this.shadowRoot.querySelector('[data-action="submit-trip"]');
      if (submitButton) {
        submitButton.addEventListener('click', (e) => {
          e.preventDefault();
          this.handleTripFormSubmit();
        });
      }
    }

    // Close trip dialog on background click
    const tripDialogOverlay = this.shadowRoot.getElementById('trip-dialog');
    if (tripDialogOverlay) {
      tripDialogOverlay.addEventListener('click', (e) => {
        if (e.target === tripDialogOverlay) {
          this.closeTripDialog();
        }
      });
    }
  }

  /**
   * Render trip log section with filtering, sorting, pagination, and editing
   */
  renderTripLog(trips) {
    if (!trips || trips.length === 0) {
      return `
        <div class="section">
          <h3>Trip Log</h3>
          <div class="no-data">
            <p>No trips recorded yet.</p>
            <p style="font-size: 14px; color: var(--secondary-text-color);">
              Trips will appear here once trip tracking is enabled and trips are detected.
            </p>
          </div>
        </div>
      `;
    }

    // Apply date filtering
    const filteredTrips = this.filterTrips(trips);
    
    // Apply sorting
    const sortedTrips = this.sortTrips(filteredTrips);
    
    // Calculate pagination
    const rowsPerPage = this._config.rows_per_page || 10;
    const totalPages = Math.ceil(sortedTrips.length / rowsPerPage);
    const currentPage = Math.min(this._tripCurrentPage, Math.max(1, totalPages));
    this._tripCurrentPage = currentPage; // Ensure page is within bounds
    
    const startIndex = (currentPage - 1) * rowsPerPage;
    const endIndex = startIndex + rowsPerPage;
    const paginatedTrips = sortedTrips.slice(startIndex, endIndex);
    
    // Get unique years from trips for filter dropdown
    const years = this.getUniqueTripYears(trips);
    const months = [
      { value: '', label: 'All Months' },
      { value: '01', label: 'January' },
      { value: '02', label: 'February' },
      { value: '03', label: 'March' },
      { value: '04', label: 'April' },
      { value: '05', label: 'May' },
      { value: '06', label: 'June' },
      { value: '07', label: 'July' },
      { value: '08', label: 'August' },
      { value: '09', label: 'September' },
      { value: '10', label: 'October' },
      { value: '11', label: 'November' },
      { value: '12', label: 'December' }
    ];
    
    const categories = [
      { value: '', label: 'All Categories' },
      { value: 'business', label: 'Business' },
      { value: 'private', label: 'Private' },
      { value: 'commute', label: 'Commute' }
    ];
    
    const sortColumn = this._tripSortColumn || 'timestamp_end';
    const sortDirection = this._tripSortDirection || 'desc';
    
    const hasActiveFilters = this._tripCategoryFilter || this._tripFilterYear || 
                             this._tripFilterMonth || this._tripFilterDateFrom || this._tripFilterDateTo;

    return `
      <div class="section">
        <h3>Trip Log</h3>
        
        <div class="filter-controls">
          <label>
            Year:
            <select class="filter-select" data-filter="trip-year">
              <option value="">All Years</option>
              ${years.map(year => `
                <option value="${year}" ${this._tripFilterYear === year ? 'selected' : ''}>${year}</option>
              `).join('')}
            </select>
          </label>
          <label>
            Month:
            <select class="filter-select" data-filter="trip-month">
              ${months.map(month => `
                <option value="${month.value}" ${this._tripFilterMonth === month.value ? 'selected' : ''}>${month.label}</option>
              `).join('')}
            </select>
          </label>
          <label>
            Category:
            <select class="filter-select" data-filter="trip-category">
              ${categories.map(cat => `
                <option value="${cat.value}" ${this._tripCategoryFilter === cat.value ? 'selected' : ''}>
                  ${cat.label}
                </option>
              `).join('')}
            </select>
          </label>
        </div>
        
        <div class="filter-controls" style="margin-top: 8px;">
          <label>
            From:
            <input type="date" class="filter-date" data-filter="trip-date-from" 
                   value="${this._tripFilterDateFrom || ''}" 
                   placeholder="Start date">
          </label>
          <label>
            To:
            <input type="date" class="filter-date" data-filter="trip-date-to" 
                   value="${this._tripFilterDateTo || ''}" 
                   placeholder="End date">
          </label>
          ${hasActiveFilters ? `
            <button class="clear-filters-button" data-action="clear-trip-filters">
              <ha-icon icon="mdi:filter-remove"></ha-icon>
              <span>Clear Filters</span>
            </button>
          ` : ''}
          <div class="filter-info">
            Showing ${Math.min(endIndex, sortedTrips.length)} of ${sortedTrips.length} trips
            ${sortedTrips.length !== trips.length ? ` (filtered from ${trips.length} total)` : ''}
            ${!this._allTripsFetched ? ` <span style="color: var(--secondary-text-color); font-size: 12px;">(loading all trips...)</span>` : ''}
          </div>
        </div>

        <div class="table-container">
          <table class="refueling-table">
            <thead>
              <tr>
                <th class="sortable ${sortColumn === 'timestamp_end' ? 'sorted-' + sortDirection : ''}" 
                    data-sort-column="timestamp_end" data-sort-type="trip">
                  End Date/Time
                  ${this.renderTripSortIcon('timestamp_end')}
                </th>
                <th class="sortable ${sortColumn === 'distance_km' ? 'sorted-' + sortDirection : ''}" 
                    data-sort-column="distance_km" data-sort-type="trip">
                  Distance (km)
                  ${this.renderTripSortIcon('distance_km')}
                </th>
                <th class="sortable ${sortColumn === 'category' ? 'sorted-' + sortDirection : ''}" 
                    data-sort-column="category" data-sort-type="trip">
                  Category
                  ${this.renderTripSortIcon('category')}
                </th>
                <th>Purpose</th>
                <th>Quality</th>
                <th class="sortable ${sortColumn === 'fuel_consumed' ? 'sorted-' + sortDirection : ''}" 
                    data-sort-column="fuel_consumed" data-sort-type="trip">
                  Fuel (L)
                  ${this.renderTripSortIcon('fuel_consumed')}
                </th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${paginatedTrips.length === 0 ? `
                <tr>
                  <td colspan="7" class="no-data">No trips match the current filters</td>
                </tr>
              ` : paginatedTrips.map(trip => `
                <tr data-trip-id="${trip.trip_id}">
                  <td>${this.formatDateTime(trip.timestamp_end)}</td>
                  <td>${this.formatNumber(trip.distance_km, 1)}</td>
                  <td>
                    <span class="category-badge category-${trip.category || 'private'}">
                      ${(trip.category || 'private').charAt(0).toUpperCase() + (trip.category || 'private').slice(1)}
                    </span>
                  </td>
                  <td>${trip.purpose || '-'}</td>
                  <td>
                    <span class="quality-badge quality-${trip.data_quality || 'manual'}">
                      ${trip.data_quality || 'manual'}
                    </span>
                    <br>
                    <span class="confidence-badge confidence-${this.getConfidenceLevel(trip.confidence !== undefined ? trip.confidence : 1.0)}">
                      ${Math.round((trip.confidence !== undefined ? trip.confidence : 1.0) * 100)}%
                    </span>
                    <br>
                    ${(() => {
                      const pq = trip.position_quality ||
                        (trip.start_latitude != null && trip.end_latitude != null ? 'full' :
                         (trip.start_latitude != null || trip.end_latitude != null) ? 'partial' : 'none');
                      const icon = pq === 'full' ? 'mdi:map-marker' : pq === 'partial' ? 'mdi:map-marker-alert' : 'mdi:map-marker-off';
                      const label = pq === 'full' ? 'GPS: full' : pq === 'partial' ? 'GPS: partial' : 'GPS: none';
                      return `<span class="position-quality-badge position-quality-${pq}" title="${label}"><ha-icon icon="${icon}"></ha-icon> ${pq}</span>`;
                    })()}
                  </td>
                  <td>${trip.fuel_consumed ? this.formatNumber(trip.fuel_consumed, 2) : '-'}</td>
                  <td class="actions">
                    <button class="action-button edit-button" 
                            data-action="edit-trip" 
                            data-trip-id="${trip.trip_id}"
                            title="Edit">
                      <ha-icon icon="mdi:pencil"></ha-icon>
                    </button>
                    <button class="action-button delete-button" 
                            data-action="delete-trip" 
                            data-trip-id="${trip.trip_id}"
                            title="Delete">
                      <ha-icon icon="mdi:delete"></ha-icon>
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
        
        ${totalPages > 1 ? `
          <div class="pagination-controls">
            <button class="pagination-button" 
                    data-action="trip-prev-page" 
                    ${currentPage === 1 ? 'disabled' : ''}>
              <ha-icon icon="mdi:chevron-left"></ha-icon>
              Previous
            </button>
            <span class="pagination-info">
              Page ${currentPage} of ${totalPages} (${startIndex + 1}-${Math.min(endIndex, sortedTrips.length)} of ${sortedTrips.length})
            </span>
            <button class="pagination-button" 
                    data-action="trip-next-page" 
                    ${currentPage === totalPages ? 'disabled' : ''}>
              Next
              <ha-icon icon="mdi:chevron-right"></ha-icon>
            </button>
          </div>
        ` : ''}

        <button class="add-event-button" data-action="add-trip">
          <ha-icon icon="mdi:plus"></ha-icon>
          <span>Add Trip</span>
        </button>
      </div>
    `;
  }

  /**
   * Render sort icon for trip table headers
   */
  renderTripSortIcon(column) {
    const sortColumn = this._tripSortColumn || 'timestamp_end';
    if (sortColumn !== column) {
      return '<ha-icon icon="mdi:unfold-more-horizontal" class="sort-icon inactive"></ha-icon>';
    }
    const sortDirection = this._tripSortDirection || 'desc';
    const icon = sortDirection === 'asc' ? 'mdi:arrow-up' : 'mdi:arrow-down';
    return `<ha-icon icon="${icon}" class="sort-icon active"></ha-icon>`;
  }

  /**
   * Render dialog for adding/editing trips
   */
  renderTripDialog() {
    return `
      <div id="trip-dialog" class="dialog-overlay" style="display: none;">
        <div class="dialog-content">
          <div class="dialog-header">
            <h2 id="trip-dialog-title">Add Trip</h2>
            <button class="dialog-close" data-action="close-trip-dialog">
              <ha-icon icon="mdi:close"></ha-icon>
            </button>
          </div>
          <div class="dialog-body">
            <form id="trip-form">
              <input type="hidden" id="trip-id" name="trip_id" value="">
              
              <div class="form-section">
                <h4>Trip Timing</h4>
                <div class="form-row">
                  <label for="trip-start-time">
                    Start Time *
                    <input type="datetime-local" id="trip-start-time" name="timestamp_start" required>
                  </label>
                  <label for="trip-end-time">
                    End Time *
                    <input type="datetime-local" id="trip-end-time" name="timestamp_end" required>
                  </label>
                </div>
              </div>
              
              <div class="form-section">
                <h4>Distance & Odometer</h4>
                <div class="form-row">
                  <label for="trip-odometer-start">
                    Odometer Start (km)
                    <input type="number" id="trip-odometer-start" name="odometer_start" 
                           step="0.1" min="0" max="1000000" placeholder="Optional">
                  </label>
                  <label for="trip-odometer-end">
                    Odometer End (km)
                    <input type="number" id="trip-odometer-end" name="odometer_end" 
                           step="0.1" min="0" max="1000000" placeholder="Optional">
                  </label>
                </div>
                <div class="form-row full-width">
                  <label for="trip-distance">
                    Distance (km) * <small id="distance-calc-info"></small>
                    <input type="number" id="trip-distance" name="distance_km" 
                           step="0.1" min="0" required>
                  </label>
                </div>
              </div>
              
              <div class="form-section">
                <h4>Start Location</h4>
                <div class="form-row">
                  <label for="trip-start-name">
                    Location Name
                    <input type="text" id="trip-start-name" name="start_name" 
                           placeholder="e.g., Home, Office" list="start-location-suggestions">
                  </label>
                  <label for="trip-start-address">
                    Address
                    <input type="text" id="trip-start-address" name="start_address" 
                           placeholder="Optional">
                  </label>
                </div>
                <div class="form-row">
                  <label for="trip-start-latitude">
                    Latitude
                    <input type="text" id="trip-start-latitude" name="start_latitude" 
                           inputmode="decimal" placeholder="Optional" 
                           title="Enter latitude (e.g., 50.000000 or 50,000000)">
                  </label>
                  <label for="trip-start-longitude">
                    Longitude
                    <input type="text" id="trip-start-longitude" name="start_longitude" 
                           inputmode="decimal" placeholder="Optional" 
                           title="Enter longitude (e.g., 10.000000 or 10,000000)">
                  </label>
                </div>
                <div class="form-row" style="margin-top: 8px;">
                  <button type="button" class="secondary-button" data-action="reverse-geocode-start" 
                          aria-label="Automatically fill location name and address from coordinates using reverse geocoding"
                          style="display: flex; align-items: center; gap: 4px;">
                    <ha-icon icon="mdi:map-marker-check"></ha-icon>
                    <span>Auto-fill Name & Address</span>
                  </button>
                </div>
                <div id="start-location-map-preview" style="display: none; margin-top: 8px; position: relative; width: 100%; aspect-ratio: 1;">
                  <img id="start-map-img" style="width: 100%; height: 100%; border-radius: 4px; cursor: pointer; object-fit: cover;" 
                       alt="Map preview of trip start location" title="Click to open in Google Maps">
                  <svg id="start-map-marker" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;">
                    <circle id="start-marker-outer" cx="50%" cy="50%" r="8" fill="red" stroke="white" stroke-width="2" opacity="0.9"/>
                    <circle id="start-marker-inner" cx="50%" cy="50%" r="3" fill="white" opacity="0.9"/>
                  </svg>
                </div>
              </div>
              
              <div class="form-section">
                <h4>End Location</h4>
                <div class="form-row">
                  <label for="trip-end-name">
                    Location Name
                    <input type="text" id="trip-end-name" name="end_name" 
                           placeholder="e.g., Client Office" list="end-location-suggestions">
                  </label>
                  <label for="trip-end-address">
                    Address
                    <input type="text" id="trip-end-address" name="end_address" 
                           placeholder="Optional">
                  </label>
                </div>
                <div class="form-row">
                  <label for="trip-end-latitude">
                    Latitude
                    <input type="text" id="trip-end-latitude" name="end_latitude" 
                           inputmode="decimal" placeholder="Optional" 
                           title="Enter latitude (e.g., 51.000000 or 51,000000)">
                  </label>
                  <label for="trip-end-longitude">
                    Longitude
                    <input type="text" id="trip-end-longitude" name="end_longitude" 
                           inputmode="decimal" placeholder="Optional" 
                           title="Enter longitude (e.g., 11.000000 or 11,000000)">
                  </label>
                </div>
                <div class="form-row" style="margin-top: 8px;">
                  <button type="button" class="secondary-button" data-action="reverse-geocode-end" 
                          aria-label="Automatically fill location name and address from coordinates using reverse geocoding"
                          style="display: flex; align-items: center; gap: 4px;">
                    <ha-icon icon="mdi:map-marker-check"></ha-icon>
                    <span>Auto-fill Name & Address</span>
                  </button>
                </div>
                <div id="end-location-map-preview" style="display: none; margin-top: 8px; position: relative; width: 100%; aspect-ratio: 1;">
                  <img id="end-map-img" style="width: 100%; height: 100%; border-radius: 4px; cursor: pointer; object-fit: cover;" 
                       alt="Map preview of trip end location" title="Click to open in Google Maps">
                  <svg id="end-map-marker" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;">
                    <circle id="end-marker-outer" cx="50%" cy="50%" r="8" fill="red" stroke="white" stroke-width="2" opacity="0.9"/>
                    <circle id="end-marker-inner" cx="50%" cy="50%" r="3" fill="white" opacity="0.9"/>
                  </svg>
                </div>
                <div id="trip-map-links" style="display: none; margin-top: 8px;">
                  <a id="start-map-link" href="#" target="_blank" style="margin-right: 12px;">
                    <ha-icon icon="mdi:map-marker"></ha-icon> View Start on Map
                  </a>
                  <a id="end-map-link" href="#" target="_blank">
                    <ha-icon icon="mdi:map-marker"></ha-icon> View End on Map
                  </a>
                </div>
              </div>
              
              <div class="form-section">
                <h4>Trip Details</h4>
                <div class="form-row">
                  <label for="trip-category">
                    Category *
                    <select id="trip-category" name="category">
                      <option value="private">Private</option>
                      <option value="business">Business</option>
                      <option value="commute">Commute</option>
                    </select>
                  </label>
                  <label for="trip-purpose">
                    Purpose
                    <input type="text" id="trip-purpose" name="purpose" 
                           placeholder="Optional" list="purpose-suggestions">
                  </label>
                </div>
                
                <div class="form-row">
                  <label for="trip-fuel-consumed">
                    Fuel Consumed (L)
                    <input type="number" id="trip-fuel-consumed" name="fuel_consumed" 
                           step="0.01" min="0" placeholder="Optional">
                  </label>
                  <label for="trip-additional-costs">
                    Additional Costs (€)
                    <input type="number" id="trip-additional-costs" name="additional_costs" 
                           step="0.01" min="0" placeholder="Tolls, parking, etc." value="0">
                  </label>
                </div>
                
                <div class="form-row full-width">
                  <label for="trip-notes">
                    Notes
                    <textarea id="trip-notes" name="notes" rows="3" 
                              placeholder="Optional notes about this trip"></textarea>
                  </label>
                </div>
                
                <div class="form-row">
                  <label for="trip-data-quality">
                    Data Quality
                    <select id="trip-data-quality" name="data_quality">
                      <option value="manual">Manual</option>
                      <option value="historical_import">Historical Import</option>
                      <option value="auto_detected">Auto Detected</option>
                    </select>
                  </label>
                  <label for="trip-confidence">
                    Confidence (0.0 - 1.0)
                    <input type="number" id="trip-confidence" name="confidence" 
                           step="0.01" min="0" max="1" value="1.0">
                  </label>
                </div>
              </div>
              
              <datalist id="purpose-suggestions"></datalist>
              <datalist id="start-location-suggestions"></datalist>
              <datalist id="end-location-suggestions"></datalist>
            </form>
          </div>
          <div class="dialog-footer">
            <button class="cancel-button" data-action="close-trip-dialog">Cancel</button>
            <button class="submit-button" data-action="submit-trip">Save</button>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Render dialog for adding/editing refueling events
   */
  renderDialog() {
    return `
      <div id="refuel-dialog" class="dialog-overlay" style="display: none;">
        <div class="dialog-content">
          <div class="dialog-header">
            <h2 id="dialog-title">Add Refueling Event</h2>
            <button class="dialog-close" data-action="close-dialog">
              <ha-icon icon="mdi:close"></ha-icon>
            </button>
          </div>
          <div class="dialog-body">
            <form id="refuel-form">
              <input type="hidden" id="event-id" name="event_id" value="">
              
              <div class="form-row full-width">
                <label for="timestamp">
                  Date & Time *
                  <input type="datetime-local" id="timestamp" name="timestamp" required>
                </label>
              </div>

              <div class="form-row">
                <label for="liters_refueled">
                  Liters Refueled *
                  <input type="number" id="liters_refueled" name="liters_refueled" 
                         min="0" step="0.001" required>
                </label>
                <label for="odometer_km">
                  Odometer (km)
                  <input type="number" id="odometer_km" name="odometer_km" 
                         min="0" max="1000000" step="1">
                </label>
              </div>

              <div class="form-row">
                <label for="price_per_liter">
                  Price per Liter (€)
                  <input type="number" id="price_per_liter" name="price_per_liter" 
                         min="0" max="10" step="0.001">
                </label>
                <label for="total_cost">
                  Total Cost (€) <small>(auto-calculated)</small>
                  <input type="number" id="total_cost" name="total_cost" 
                         min="0" max="500" step="0.01" readonly>
                </label>
              </div>

              <div class="form-row full-width">
                <label for="station_name">
                  Station Name
                  <input type="text" id="station_name" name="station_name">
                </label>
              </div>

              <div class="form-row full-width">
                <label for="station_address">
                  Station Address
                  <input type="text" id="station_address" name="station_address">
                </label>
              </div>

              <div class="form-row full-width">
                <label for="fuel_type">
                  Fuel Type
                  <input type="text" id="fuel_type" name="fuel_type" placeholder="e.g., diesel, e5, e10">
                </label>
              </div>

              <div class="form-row">
                <label for="data_quality">
                  Data Quality
                  <select id="data_quality" name="data_quality">
                    <option value="manual">Manual</option>
                    <option value="auto_detected">Auto Detected</option>
                    <option value="historical_import">Historical Import</option>
                    <option value="ai_processed">AI Processed</option>
                  </select>
                </label>
                <label for="confidence">
                  Confidence (0-1)
                  <input type="number" id="confidence" name="confidence" 
                         min="0" max="1" step="0.1" value="1.0">
                </label>
              </div>

              <!-- Telegram Response Section (shown only if available) -->
              <div id="telegram-response-section" class="form-section" style="display: none;">
                <h3 style="margin-top: 20px; margin-bottom: 10px; border-top: 2px solid var(--primary-color); padding-top: 15px;">
                  📱 Telegram Response
                </h3>
                <div class="form-row">
                  <label for="telegram_response_raw" style="flex: 1;">
                    User Message
                    <textarea id="telegram_response_raw" name="telegram_response_raw" 
                              rows="4" readonly 
                              style="background-color: var(--disabled-color, #f5f5f5); resize: vertical;"></textarea>
                  </label>
                  <label for="telegram_response_parsed_display" style="flex: 1; margin-left: 10px;">
                    AI Recognized Data
                    <textarea id="telegram_response_parsed_display" 
                              rows="4" readonly 
                              style="background-color: var(--disabled-color, #f5f5f5); resize: vertical;"></textarea>
                  </label>
                </div>
                <div class="form-row">
                  <small style="color: var(--secondary-text-color); font-style: italic;">
                    Response Type: <span id="telegram_response_type">-</span> | 
                    Received: <span id="telegram_response_timestamp">-</span>
                  </small>
                </div>
              </div>

              <div class="dialog-footer">
                <button type="button" class="cancel-button" data-action="close-dialog">Cancel</button>
                <button type="submit" class="submit-button">Save</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Show dialog to add a new refueling event
   */
  showAddDialog() {
    const dialog = this.shadowRoot.getElementById('refuel-dialog');
    const dialogTitle = this.shadowRoot.getElementById('dialog-title');
    const form = this.shadowRoot.getElementById('refuel-form');
    
    // Set title
    dialogTitle.textContent = 'Add Refueling Event';
    
    // Clear form
    form.reset();
    this.shadowRoot.getElementById('event-id').value = '';
    
    // Set default timestamp to now
    const now = new Date();
    const tzOffset = now.getTimezoneOffset() * 60000;
    const localISOTime = new Date(now - tzOffset).toISOString().slice(0, 16);
    this.shadowRoot.getElementById('timestamp').value = localISOTime;
    
    // Set max liters based on tank capacity
    const tankCapacity = this.getTankCapacity();
    const litersInput = this.shadowRoot.getElementById('liters_refueled');
    litersInput.setAttribute('max', tankCapacity);
    
    // Pre-fill last fuel type
    const lastFuelType = this.getLastFuelType();
    if (lastFuelType) {
      this.shadowRoot.getElementById('fuel_type').value = lastFuelType;
    }
    
    // Estimate and suggest odometer reading
    const estimatedOdometer = this.estimateOdometer(localISOTime);
    if (estimatedOdometer) {
      this.shadowRoot.getElementById('odometer_km').value = estimatedOdometer;
      this.shadowRoot.getElementById('odometer_km').setAttribute('placeholder', `Suggested: ${estimatedOdometer} km`);
    }
    
    // Setup auto-calculation for total cost
    this._setupCostCalculation();
    
    // Setup station autocomplete
    this._setupStationAutocomplete();
    
    // Setup timestamp change listener to recalculate odometer
    this._setupOdometerRecalculation();
    
    // Show dialog
    dialog.style.display = 'flex';
  }

  /**
   * Show dialog to edit an existing refueling event
   */
  showEditDialog(eventId) {
    const dialog = this.shadowRoot.getElementById('refuel-dialog');
    const dialogTitle = this.shadowRoot.getElementById('dialog-title');
    const form = this.shadowRoot.getElementById('refuel-form');
    
    // Find event in stored events - prefer _allRefuelings for most up-to-date data
    // (includes telegram-updated values), fallback to _recentEvents
    let event = null;
    if (this._allRefuelings && this._allRefuelings.length > 0) {
      event = this._allRefuelings.find(e => e.id === parseInt(eventId));
    }
    if (!event && this._recentEvents) {
      event = this._recentEvents.find(e => e.id === parseInt(eventId));
    }
    
    if (!event) {
      alert(`Event with ID ${eventId} not found`);
      return;
    }
    
    // Set title
    dialogTitle.textContent = `Edit Refueling Event #${eventId}`;
    
    // Populate form with event data
    this.shadowRoot.getElementById('event-id').value = eventId;
    
    // Convert timestamp to local datetime-local format
    const eventDate = new Date(event.timestamp);
    const tzOffset = eventDate.getTimezoneOffset() * 60000;
    const localISOTime = new Date(eventDate - tzOffset).toISOString().slice(0, 16);
    this.shadowRoot.getElementById('timestamp').value = localISOTime;
    
    // Set max liters based on tank capacity
    const tankCapacity = this.getTankCapacity();
    const litersInput = this.shadowRoot.getElementById('liters_refueled');
    litersInput.setAttribute('max', tankCapacity);
    
    this.shadowRoot.getElementById('liters_refueled').value = event.liters_refueled || '';
    this.shadowRoot.getElementById('odometer_km').value = event.odometer_km || '';
    this.shadowRoot.getElementById('price_per_liter').value = event.price_per_liter || '';
    this.shadowRoot.getElementById('total_cost').value = event.total_cost || '';
    this.shadowRoot.getElementById('station_name').value = event.station_name || '';
    this.shadowRoot.getElementById('station_address').value = event.station_address || '';
    this.shadowRoot.getElementById('fuel_type').value = event.fuel_type || '';
    this.shadowRoot.getElementById('data_quality').value = event.data_quality || 'manual';
    this.shadowRoot.getElementById('confidence').value = event.confidence !== undefined ? event.confidence : 1.0;
    
    // Populate Telegram response fields if available
    const telegramSection = this.shadowRoot.getElementById('telegram-response-section');
    if (event.telegram_response_received && event.telegram_response_raw) {
      telegramSection.style.display = 'block';
      
      // Set raw message
      this.shadowRoot.getElementById('telegram_response_raw').value = event.telegram_response_raw || '';
      
      // Format parsed data for display
      let parsedDisplay = '';
      if (event.telegram_response_parsed && typeof event.telegram_response_parsed === 'object') {
        parsedDisplay = JSON.stringify(event.telegram_response_parsed, null, 2);
      } else if (event.telegram_response_parsed) {
        parsedDisplay = String(event.telegram_response_parsed);
      } else {
        parsedDisplay = 'No structured data parsed';
      }
      this.shadowRoot.getElementById('telegram_response_parsed_display').value = parsedDisplay;
      
      // Set metadata
      this.shadowRoot.getElementById('telegram_response_type').textContent = 
        event.telegram_response_type || 'unknown';
      
      if (event.telegram_response_timestamp) {
        try {
          const responseDate = new Date(event.telegram_response_timestamp);
          this.shadowRoot.getElementById('telegram_response_timestamp').textContent = 
            responseDate.toLocaleString();
        } catch (e) {
          this.shadowRoot.getElementById('telegram_response_timestamp').textContent = 
            event.telegram_response_timestamp;
        }
      }
    } else {
      telegramSection.style.display = 'none';
    }
    
    // Setup auto-calculation for total cost
    this._setupCostCalculation();
    
    // Setup station autocomplete
    this._setupStationAutocomplete();
    
    // Show dialog
    dialog.style.display = 'flex';
  }

  /**
   * Setup auto-calculation for total cost
   */
  _setupCostCalculation() {
    const litersInput = this.shadowRoot.getElementById('liters_refueled');
    const priceInput = this.shadowRoot.getElementById('price_per_liter');
    const totalInput = this.shadowRoot.getElementById('total_cost');
    
    // Remove any existing listeners
    const newLitersInput = litersInput.cloneNode(true);
    const newPriceInput = priceInput.cloneNode(true);
    litersInput.parentNode.replaceChild(newLitersInput, litersInput);
    priceInput.parentNode.replaceChild(newPriceInput, priceInput);
    
    const calculateTotal = () => {
      const liters = parseFloat(newLitersInput.value) || 0;
      const price = parseFloat(newPriceInput.value) || 0;
      
      if (liters > 0 && price > 0) {
        const total = (liters * price).toFixed(2);
        totalInput.value = total;
      }
    };
    
    newLitersInput.addEventListener('input', calculateTotal);
    newPriceInput.addEventListener('input', calculateTotal);
  }

  /**
   * Setup station autocomplete with smart search
   */
  _setupStationAutocomplete() {
    const stationInput = this.shadowRoot.getElementById('station_name');
    const addressInput = this.shadowRoot.getElementById('station_address');
    
    // Remove existing datalist if present
    let datalist = this.shadowRoot.getElementById('station-suggestions');
    if (datalist) {
      datalist.remove();
    }
    
    // Create new datalist
    datalist = document.createElement('datalist');
    datalist.id = 'station-suggestions';
    
    // Get unique stations
    const stations = this.getUniqueStations();
    
    // Add options to datalist
    for (const station of stations) {
      const option = document.createElement('option');
      option.value = `${station.name}${station.city ? ' ' + station.city : ''}${station.street ? ' ' + station.street : ''}`;
      option.dataset.address = station.address;
      datalist.appendChild(option);
    }
    
    // Append datalist to shadow root
    stationInput.parentNode.appendChild(datalist);
    stationInput.setAttribute('list', 'station-suggestions');
    
    // Auto-fill address when station is selected
    // Remove any existing listener
    const newStationInput = stationInput.cloneNode(true);
    newStationInput.setAttribute('list', 'station-suggestions');
    stationInput.parentNode.replaceChild(newStationInput, stationInput);
    
    newStationInput.addEventListener('change', () => {
      const selectedValue = newStationInput.value;
      
      // Find matching station
      for (const station of stations) {
        const displayValue = `${station.name}${station.city ? ' ' + station.city : ''}${station.street ? ' ' + station.street : ''}`;
        if (displayValue === selectedValue || selectedValue.toLowerCase().includes(station.name.toLowerCase())) {
          addressInput.value = station.address;
          break;
        }
      }
    });
    
    // Also support incremental filtering via input event
    newStationInput.addEventListener('input', () => {
      const query = newStationInput.value;
      const filteredStations = this.filterStations(query, stations);
      
      // Update datalist
      datalist.innerHTML = '';
      for (const station of filteredStations.slice(0, MAX_AUTOCOMPLETE_SUGGESTIONS)) {
        const option = document.createElement('option');
        option.value = `${station.name}${station.city ? ' ' + station.city : ''}${station.street ? ' ' + station.street : ''}`;
        option.dataset.address = station.address;
        datalist.appendChild(option);
      }
    });
  }

  /**
   * Setup odometer recalculation when timestamp changes (Add dialog only)
   */
  _setupOdometerRecalculation() {
    const timestampInput = this.shadowRoot.getElementById('timestamp');
    const odometerInput = this.shadowRoot.getElementById('odometer_km');
    const eventIdInput = this.shadowRoot.getElementById('event-id');
    
    // Only for Add dialog (not Edit)
    if (eventIdInput.value) {
      return; // This is Edit dialog, skip
    }
    
    // Remove existing listener
    const newTimestampInput = timestampInput.cloneNode(true);
    timestampInput.parentNode.replaceChild(newTimestampInput, timestampInput);
    
    newTimestampInput.addEventListener('change', () => {
      const newTimestamp = newTimestampInput.value;
      const estimatedOdometer = this.estimateOdometer(newTimestamp);
      
      if (estimatedOdometer) {
        odometerInput.value = estimatedOdometer;
        odometerInput.setAttribute('placeholder', `Suggested: ${estimatedOdometer} km`);
      }
    });
  }

  /**
   * Close the dialog
   */
  closeDialog() {
    const dialog = this.shadowRoot.getElementById('refuel-dialog');
    dialog.style.display = 'none';
  }

  /**
   * Show dialog to add a new trip
   */
  showAddTripDialog() {
    const dialog = this.shadowRoot.getElementById('trip-dialog');
    const dialogTitle = this.shadowRoot.getElementById('trip-dialog-title');
    const form = this.shadowRoot.getElementById('trip-form');
    
    if (!dialog || !dialogTitle || !form) {
      console.error('Trip dialog elements not found');
      return;
    }
    
    // Set title
    dialogTitle.textContent = 'Add Trip';
    
    // Clear form
    form.reset();
    form.dataset.tripId = '';
    
    // Set default timestamps
    const now = new Date();
    const tzOffset = now.getTimezoneOffset() * 60000;
    const localISOTime = new Date(now - tzOffset).toISOString().slice(0, 16);
    this.shadowRoot.getElementById('trip-end-time').value = localISOTime;
    
    // Set start time to 1 hour ago
    const oneHourAgo = new Date(now - 3600000);
    const localISOTimeStart = new Date(oneHourAgo - tzOffset).toISOString().slice(0, 16);
    this.shadowRoot.getElementById('trip-start-time').value = localISOTimeStart;
    
    // Set default category
    this.shadowRoot.getElementById('trip-category').value = 'private';
    
    // Set default data quality and confidence
    this.shadowRoot.getElementById('trip-data-quality').value = 'manual';
    this.shadowRoot.getElementById('trip-confidence').value = 1.0;
    
    // Populate autocomplete suggestions
    this.populateTripAutocomplete();
    
    // Set up odometer change listeners
    this.setupOdometerCalculation();
    
    // Set up coordinate map link handlers
    this.setupMapLinks();
    
    // Show dialog
    dialog.style.display = 'flex';
  }

  /**
   * Show dialog to edit an existing trip
   */
  showEditTripDialog(tripId) {
    const dialog = this.shadowRoot.getElementById('trip-dialog');
    const dialogTitle = this.shadowRoot.getElementById('trip-dialog-title');
    const form = this.shadowRoot.getElementById('trip-form');
    
    if (!dialog || !dialogTitle || !form) {
      console.error('Trip dialog elements not found');
      return;
    }
    
    // Find trip in stored trips (use all_trips instead of recent_trips)
    const trip = this._allTrips ? this._allTrips.find(t => t.trip_id === parseInt(tripId)) : null;
    
    if (!trip) {
      const lang = this.getUserLanguage();
      const errorMessages = {
        de: `Fahrt mit ID ${tripId} wurde nicht gefunden. Bitte aktualisieren Sie die Seite.`,
        en: `Trip with ID ${tripId} not found. Please refresh the page.`
      };
      const message = errorMessages[lang] || errorMessages['en'];
      alert(message);
      return;
    }
    
    // Set title
    dialogTitle.textContent = `Edit Trip #${tripId}`;
    
    // Store trip ID for submission
    form.dataset.tripId = tripId;
    
    // Populate form with trip data
    // Convert timestamps to local datetime-local format
    if (trip.timestamp_start) {
      try {
        const startDate = new Date(trip.timestamp_start);
        const tzOffset = startDate.getTimezoneOffset() * 60000;
        const localStart = new Date(startDate.getTime() - tzOffset).toISOString().slice(0, 16);
        this.shadowRoot.getElementById('trip-start-time').value = localStart;
      } catch (err) {
        console.error('Error parsing trip start time:', err);
      }
    }
    
    if (trip.timestamp_end) {
      try {
        const endDate = new Date(trip.timestamp_end);
        const tzOffset = endDate.getTimezoneOffset() * 60000;
        const localEnd = new Date(endDate.getTime() - tzOffset).toISOString().slice(0, 16);
        this.shadowRoot.getElementById('trip-end-time').value = localEnd;
      } catch (err) {
        console.error('Error parsing trip end time:', err);
      }
    }
    
    // Basic trip fields
    this.shadowRoot.getElementById('trip-distance').value = trip.distance_km || '';
    this.shadowRoot.getElementById('trip-category').value = trip.category || 'private';
    this.shadowRoot.getElementById('trip-purpose').value = trip.purpose || '';
    this.shadowRoot.getElementById('trip-fuel-consumed').value = trip.fuel_consumed || '';
    this.shadowRoot.getElementById('trip-additional-costs').value = trip.additional_costs || 0;
    this.shadowRoot.getElementById('trip-notes').value = trip.notes || '';
    
    // Odometer fields
    this.shadowRoot.getElementById('trip-odometer-start').value = trip.odometer_start || '';
    this.shadowRoot.getElementById('trip-odometer-end').value = trip.odometer_end || '';
    
    // Start location fields
    this.shadowRoot.getElementById('trip-start-name').value = trip.start_name || '';
    this.shadowRoot.getElementById('trip-start-address').value = trip.start_address || '';
    this.shadowRoot.getElementById('trip-start-latitude').value = trip.start_latitude || '';
    this.shadowRoot.getElementById('trip-start-longitude').value = trip.start_longitude || '';
    
    // End location fields
    this.shadowRoot.getElementById('trip-end-name').value = trip.end_name || '';
    this.shadowRoot.getElementById('trip-end-address').value = trip.end_address || '';
    this.shadowRoot.getElementById('trip-end-latitude').value = trip.end_latitude || '';
    this.shadowRoot.getElementById('trip-end-longitude').value = trip.end_longitude || '';
    
    // Data quality and confidence fields
    this.shadowRoot.getElementById('trip-data-quality').value = trip.data_quality || 'manual';
    this.shadowRoot.getElementById('trip-confidence').value = trip.confidence !== undefined ? trip.confidence : 1.0;
    
    // Populate autocomplete suggestions
    this.populateTripAutocomplete();
    
    // Set up odometer change listeners
    this.setupOdometerCalculation();
    
    // Set up coordinate map link handlers
    this.setupMapLinks();
    
    // Update map links if coordinates exist
    this.updateMapLinks();
    
    // Show dialog
    dialog.style.display = 'flex';
  }

  /**
   * Close trip dialog
   */
  closeTripDialog() {
    const dialog = this.shadowRoot.getElementById('trip-dialog');
    if (dialog) {
      dialog.style.display = 'none';
    }
  }

  /**
   * Handle trip form submission
   */
  async handleTripFormSubmit() {
    const form = this.shadowRoot.getElementById('trip-form');
    if (!form) return;
    
    const tripId = form.dataset.tripId;
    const formData = new FormData(form);
    
    // Build service data
    const serviceData = {
      config_entry_id: this.getConfigEntryId(),
      category: formData.get('category') || 'private'
    };
    
    // Only include timestamp and distance fields for new trips (add_trip service)
    // These fields are not allowed in edit_trip service
    if (!tripId) {
      serviceData.timestamp_start = formData.get('timestamp_start');
      serviceData.timestamp_end = formData.get('timestamp_end');
      // Normalize decimal separator for proper parsing
      serviceData.distance_km = parseFloat((formData.get('distance_km') || '').replace(',', '.'));
      
      // fuel_consumed is only allowed in add_trip, not edit_trip
      if (formData.get('fuel_consumed')) {
        // Normalize decimal separator for proper parsing
        serviceData.fuel_consumed = parseFloat((formData.get('fuel_consumed') || '').replace(',', '.'));
      }
    }
    
    // Add optional fields if provided
    if (formData.get('purpose')) {
      serviceData.purpose = formData.get('purpose');
    }
    if (formData.get('additional_costs')) {
      // Normalize decimal separator for proper parsing
      serviceData.additional_costs = parseFloat((formData.get('additional_costs') || '').replace(',', '.'));
    }
    if (formData.get('notes')) {
      serviceData.notes = formData.get('notes');
    }
    
    // Add odometer fields
    if (formData.get('odometer_start')) {
      // Normalize decimal separator for proper parsing
      serviceData.odometer_start = parseFloat((formData.get('odometer_start') || '').replace(',', '.'));
    }
    if (formData.get('odometer_end')) {
      // Normalize decimal separator for proper parsing
      serviceData.odometer_end = parseFloat((formData.get('odometer_end') || '').replace(',', '.'));
    }
    
    // Add start location fields
    if (formData.get('start_latitude')) {
      // Normalize decimal separator: replace comma with dot for proper parsing
      serviceData.start_latitude = parseFloat((formData.get('start_latitude') || '').replace(',', '.'));
    }
    if (formData.get('start_longitude')) {
      // Normalize decimal separator: replace comma with dot for proper parsing
      serviceData.start_longitude = parseFloat((formData.get('start_longitude') || '').replace(',', '.'));
    }
    if (formData.get('start_name')) {
      serviceData.start_name = formData.get('start_name');
    }
    if (formData.get('start_address')) {
      serviceData.start_address = formData.get('start_address');
    }
    
    // Add end location fields
    if (formData.get('end_latitude')) {
      // Normalize decimal separator: replace comma with dot for proper parsing
      serviceData.end_latitude = parseFloat((formData.get('end_latitude') || '').replace(',', '.'));
    }
    if (formData.get('end_longitude')) {
      // Normalize decimal separator: replace comma with dot for proper parsing
      serviceData.end_longitude = parseFloat((formData.get('end_longitude') || '').replace(',', '.'));
    }
    if (formData.get('end_name')) {
      serviceData.end_name = formData.get('end_name');
    }
    if (formData.get('end_address')) {
      serviceData.end_address = formData.get('end_address');
    }
    
    // Add data quality and confidence fields
    if (formData.get('data_quality')) {
      serviceData.data_quality = formData.get('data_quality');
    }
    if (formData.get('confidence')) {
      // Normalize decimal separator for proper parsing
      serviceData.confidence = parseFloat((formData.get('confidence') || '').replace(',', '.'));
    }
    
    try {
      if (tripId) {
        // Update existing trip
        serviceData.trip_id = parseInt(tripId);
        await this.editTrip(serviceData);
      } else {
        // Add new trip
        await this.callService('hafwcma', 'add_trip', serviceData);
      }
      
      // Close dialog
      this.closeTripDialog();
      
      // Refresh the card after a short delay
      setTimeout(() => {
        this.render();
      }, SERVICE_CALL_REFRESH_DELAY_MS);
    } catch (error) {
      console.error('Error submitting trip:', error);
      const lang = this.getUserLanguage();
      const errorMessages = {
        de: `Fehler beim Speichern der Fahrt: ${error.message || error}`,
        en: `Failed to save trip: ${error.message || error}`
      };
      const message = errorMessages[lang] || errorMessages['en'];
      alert(message);
    }
  }

  /**
   * Handle form submission
   */
  async handleFormSubmit(e) {
    e.preventDefault();
    
    const form = this.shadowRoot.getElementById('refuel-form');
    const formData = new FormData(form);
    const eventId = formData.get('event_id');
    
    // Build service data
    const serviceData = {
      config_entry_id: this.getConfigEntryId(),
      timestamp: formData.get('timestamp'),
      // Normalize decimal separator for proper parsing
      liters_refueled: parseFloat((formData.get('liters_refueled') || '').replace(',', '.'))
    };
    
    // Add optional fields if provided
    if (formData.get('odometer_km')) {
      serviceData.odometer_km = parseInt(formData.get('odometer_km'));
    }
    if (formData.get('price_per_liter')) {
      // Normalize decimal separator for proper parsing
      serviceData.price_per_liter = parseFloat((formData.get('price_per_liter') || '').replace(',', '.'));
    }
    if (formData.get('total_cost')) {
      // Normalize decimal separator for proper parsing
      serviceData.total_cost = parseFloat((formData.get('total_cost') || '').replace(',', '.'));
    }
    if (formData.get('station_name')) {
      serviceData.station_name = formData.get('station_name');
    }
    if (formData.get('station_address')) {
      serviceData.station_address = formData.get('station_address');
    }
    if (formData.get('fuel_type')) {
      serviceData.fuel_type = formData.get('fuel_type');
    }
    if (formData.get('data_quality')) {
      serviceData.data_quality = formData.get('data_quality');
    }
    if (formData.get('confidence')) {
      // Normalize decimal separator for proper parsing
      serviceData.confidence = parseFloat((formData.get('confidence') || '').replace(',', '.'));
    }
    
    try {
      if (eventId) {
        // Update existing event
        serviceData.event_id = parseInt(eventId);
        await this.updateRefuelingEvent(serviceData);
      } else {
        // Add new event
        await this.addRefuelingEvent(serviceData);
      }
      
      // Close dialog
      this.closeDialog();
      
      // Refresh the card after a short delay
      setTimeout(() => {
        this._lastRender = 0; // Force re-render
        if (this._hass) {
          this.render();
        }
      }, SERVICE_CALL_REFRESH_DELAY_MS);
      
    } catch (error) {
      alert(`Error saving refueling event: ${error.message}`);
    }
  }

  /**
   * Get config entry ID from entity
   */
  getConfigEntryId() {
    // Get config_entry_id from the entity attributes
    const entity = this.getEntityState(this._config.entity);
    if (entity && entity.attributes.config_entry_id) {
      return entity.attributes.config_entry_id;
    }
    
    // Fallback: show error with troubleshooting tips
    throw new Error('Config entry ID not found. Please ensure:\n1. The integration is properly configured\n2. The sensor entity exists and is available\n3. Home Assistant has been restarted after installation\n4. The entity is: ' + this._config.entity);
  }

  /**
   * Setup odometer calculation for trip dialog
   */
  setupOdometerCalculation() {
    const odometerStart = this.shadowRoot.getElementById('trip-odometer-start');
    const odometerEnd = this.shadowRoot.getElementById('trip-odometer-end');
    const distanceField = this.shadowRoot.getElementById('trip-distance');
    const distanceCalcInfo = this.shadowRoot.getElementById('distance-calc-info');
    
    if (!odometerStart || !odometerEnd || !distanceField) return;
    
    const calculateDistance = () => {
      const start = parseFloat(odometerStart.value);
      const end = parseFloat(odometerEnd.value);
      
      if (start && end && end > start) {
        const distance = (end - start).toFixed(1);
        distanceField.value = distance;
        distanceField.readOnly = true;
        if (distanceCalcInfo) {
          distanceCalcInfo.textContent = '(auto-calculated from odometer)';
        }
      } else {
        distanceField.readOnly = false;
        if (distanceCalcInfo) {
          distanceCalcInfo.textContent = '';
        }
      }
    };
    
    odometerStart.removeEventListener('input', calculateDistance);
    odometerEnd.removeEventListener('input', calculateDistance);
    odometerStart.addEventListener('input', calculateDistance);
    odometerEnd.addEventListener('input', calculateDistance);
    
    // Run once on setup
    calculateDistance();
  }

  /**
   * Setup map links for trip coordinates
   */
  setupMapLinks() {
    const startLat = this.shadowRoot.getElementById('trip-start-latitude');
    const startLon = this.shadowRoot.getElementById('trip-start-longitude');
    const endLat = this.shadowRoot.getElementById('trip-end-latitude');
    const endLon = this.shadowRoot.getElementById('trip-end-longitude');
    
    if (!startLat || !startLon || !endLat || !endLon) return;
    
    const updateLinks = () => {
      this.updateMapLinks();
    };
    
    [startLat, startLon, endLat, endLon].forEach(field => {
      field.removeEventListener('input', updateLinks);
      field.addEventListener('input', updateLinks);
    });
    
    // Set up location name change handlers for address auto-fill
    this.setupLocationNameHandlers();
  }
  
  /**
   * Set up handlers to auto-fill addresses when location names are selected
   */
  setupLocationNameHandlers() {
    const startName = this.shadowRoot.getElementById('trip-start-name');
    const endName = this.shadowRoot.getElementById('trip-end-name');
    
    if (startName) {
      startName.removeEventListener('change', this._startNameChangeHandler);
      this._startNameChangeHandler = () => this.handleLocationNameChange('start');
      startName.addEventListener('change', this._startNameChangeHandler);
    }
    
    if (endName) {
      endName.removeEventListener('change', this._endNameChangeHandler);
      this._endNameChangeHandler = () => this.handleLocationNameChange('end');
      endName.addEventListener('change', this._endNameChangeHandler);
    }
  }
  
  /**
   * Handle location name change to auto-fill address from previous trips
   */
  handleLocationNameChange(locationType) {
    const nameField = this.shadowRoot.getElementById(`trip-${locationType}-name`);
    const addressField = this.shadowRoot.getElementById(`trip-${locationType}-address`);
    const latField = this.shadowRoot.getElementById(`trip-${locationType}-latitude`);
    const lonField = this.shadowRoot.getElementById(`trip-${locationType}-longitude`);
    
    if (!nameField || !addressField) return;
    
    const locationName = nameField.value.trim();
    if (!locationName) return;
    
    // Don't overwrite if address is already filled
    if (addressField.value && addressField.value.trim()) return;
    
    // Find a matching trip with this location name
    if (!this._allTrips || this._allTrips.length === 0) return;
    
    for (const trip of this._allTrips) {
      const tripName = locationType === 'start' ? trip.start_name : trip.end_name;
      const tripAddress = locationType === 'start' ? trip.start_address : trip.end_address;
      const tripLat = locationType === 'start' ? trip.start_latitude : trip.end_latitude;
      const tripLon = locationType === 'start' ? trip.start_longitude : trip.end_longitude;
      
      // Match by name (case-insensitive)
      if (tripName && tripName.toLowerCase() === locationName.toLowerCase()) {
        // Auto-fill address if available
        if (tripAddress) {
          addressField.value = tripAddress;
        }
        
        // Auto-fill coordinates if available and not already set
        if (tripLat && tripLon && !latField.value && !lonField.value) {
          latField.value = tripLat;
          lonField.value = tripLon;
          this.updateMapLinks();
        }
        
        break; // Use first match
      }
    }
  }

  /**
   * Generate Google Maps URL for coordinates
   */
  getMapUrl(lat, lon) {
    // Validate coordinate bounds
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      console.warn('[FWCAM Card] Invalid coordinates for map URL:', { lat, lon });
      return '#';
    }
    return `https://www.google.com/maps?q=${encodeURIComponent(lat)},${encodeURIComponent(lon)}`;
  }
  
  /**
   * Generate static map image using OSM tiles directly
   * Returns the OSM tile URL that contains the coordinates
   * More reliable than staticmap.openstreetmap.de which is often down
   */
  getStaticMapUrl(lat, lon) {
    // Validate coordinate bounds
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      console.warn('[FWCAM Card] Invalid coordinates for static map:', { lat, lon });
      return '';
    }
    
    const zoom = 15;
    const MAX_MERCATOR_LAT = 85.05112878; // Web Mercator projection valid range
    
    // Clamp latitude to Web Mercator valid range to prevent Infinity/NaN
    const clampedLat = Math.max(-MAX_MERCATOR_LAT, Math.min(MAX_MERCATOR_LAT, lat));
    
    // Helper function: Convert latitude to Web Mercator Y coordinate
    const latToMercatorY = (latitude) => 
      (1 - Math.log(Math.tan(latitude * Math.PI / 180) + 1 / Math.cos(latitude * Math.PI / 180)) / Math.PI) / 2;
    
    // Calculate tile coordinates
    const n = Math.pow(2, zoom);
    const xtile = Math.floor((lon + 180) / 360 * n);
    const ytile = Math.floor(latToMercatorY(clampedLat) * n);
    
    // Validate tile coordinates are within valid range for the zoom level
    const maxTile = n - 1;
    if (xtile < 0 || xtile > maxTile || ytile < 0 || ytile > maxTile) {
      console.warn('[FWCAM Card] Invalid tile coordinates:', { xtile, ytile, maxTile });
      return '';
    }
    
    console.log('[FWCAM Card] Generating static map:', { lat, lon, clampedLat, zoom, xtile, ytile });
    
    // Return direct OSM tile URL (PR #101 implementation)
    return `https://tile.openstreetmap.org/${zoom}/${xtile}/${ytile}.png`;
  }
  
  /**
   * Calculate marker position for overlay (PR #102 implementation)
   * Returns the percentage position within the tile where the marker should be placed
   */
  getMapMarkerPosition(lat, lon) {
    const zoom = 15;
    const MAX_MERCATOR_LAT = 85.05112878;
    
    // Clamp latitude to Web Mercator valid range
    const clampedLat = Math.max(-MAX_MERCATOR_LAT, Math.min(MAX_MERCATOR_LAT, lat));
    
    // Helper function: Convert latitude to Web Mercator Y coordinate
    const latToMercatorY = (latitude) => 
      (1 - Math.log(Math.tan(latitude * Math.PI / 180) + 1 / Math.cos(latitude * Math.PI / 180)) / Math.PI) / 2;
    
    // Calculate tile coordinates
    const n = Math.pow(2, zoom);
    const xtile = Math.floor((lon + 180) / 360 * n);
    const ytile = Math.floor(latToMercatorY(clampedLat) * n);
    
    // Calculate the exact position within the tile (0-1 as percentage)
    const exactX = ((lon + 180) / 360 * n) - xtile;
    const exactY = (latToMercatorY(clampedLat) * n) - ytile;
    
    // Validate coordinates are finite numbers
    if (!isFinite(exactX) || !isFinite(exactY)) {
      console.warn('[FWCAM Card] Invalid marker position:', { exactX, exactY });
      return { x: 50, y: 50 }; // Return center as fallback
    }
    
    // Convert to percentage (0-100)
    const percentX = exactX * 100;
    const percentY = exactY * 100;
    
    console.log('[FWCAM Card] Marker position:', { lat, lon, percentX, percentY });
    
    return { x: percentX, y: percentY };
  }
  
  /**
   * Update map links based on coordinates
   */
  updateMapLinks() {
    // Normalize decimal separator: replace comma with dot for proper parsing
    const startLat = parseFloat((this.shadowRoot.getElementById('trip-start-latitude')?.value || '').replace(',', '.'));
    const startLon = parseFloat((this.shadowRoot.getElementById('trip-start-longitude')?.value || '').replace(',', '.'));
    const endLat = parseFloat((this.shadowRoot.getElementById('trip-end-latitude')?.value || '').replace(',', '.'));
    const endLon = parseFloat((this.shadowRoot.getElementById('trip-end-longitude')?.value || '').replace(',', '.'));
    
    const mapLinks = this.shadowRoot.getElementById('trip-map-links');
    const startMapLink = this.shadowRoot.getElementById('start-map-link');
    const endMapLink = this.shadowRoot.getElementById('end-map-link');
    
    // Map preview elements
    const startMapPreview = this.shadowRoot.getElementById('start-location-map-preview');
    const endMapPreview = this.shadowRoot.getElementById('end-location-map-preview');
    const startMapImg = this.shadowRoot.getElementById('start-map-img');
    const endMapImg = this.shadowRoot.getElementById('end-map-img');
    
    if (!mapLinks || !startMapLink || !endMapLink) return;
    
    const hasStart = !isNaN(startLat) && !isNaN(startLon);
    const hasEnd = !isNaN(endLat) && !isNaN(endLon);
    
    if (hasStart || hasEnd) {
      mapLinks.style.display = 'block';
      
      if (hasStart) {
        const startUrl = this.getMapUrl(startLat, startLon);
        startMapLink.href = startUrl;
        startMapLink.style.display = 'inline-flex';
        
        // Show inline map preview
        if (startMapPreview && startMapImg) {
          const mapUrl = this.getStaticMapUrl(startLat, startLon);
          console.log('[FWCAM Card] Setting start map preview URL:', mapUrl);
          startMapImg.src = mapUrl;
          startMapImg.onerror = (e) => {
            console.error('[FWCAM Card] Error loading start map preview:', e);
            startMapPreview.style.display = 'none';
          };
          startMapImg.onload = () => {
            console.log('[FWCAM Card] Start map preview loaded successfully');
          };
          startMapImg.onclick = () => window.open(startUrl, '_blank');
          
          // Update marker position (PR #102 overlay implementation)
          const markerPos = this.getMapMarkerPosition(startLat, startLon);
          const startMarkerOuter = this.shadowRoot.getElementById('start-marker-outer');
          const startMarkerInner = this.shadowRoot.getElementById('start-marker-inner');
          if (startMarkerOuter && startMarkerInner) {
            startMarkerOuter.setAttribute('cx', `${markerPos.x}%`);
            startMarkerOuter.setAttribute('cy', `${markerPos.y}%`);
            startMarkerInner.setAttribute('cx', `${markerPos.x}%`);
            startMarkerInner.setAttribute('cy', `${markerPos.y}%`);
          }
          
          startMapPreview.style.display = 'block';
        }
      } else {
        startMapLink.style.display = 'none';
        if (startMapPreview) startMapPreview.style.display = 'none';
      }
      
      if (hasEnd) {
        const endUrl = this.getMapUrl(endLat, endLon);
        endMapLink.href = endUrl;
        endMapLink.style.display = 'inline-flex';
        
        // Show inline map preview
        if (endMapPreview && endMapImg) {
          const mapUrl = this.getStaticMapUrl(endLat, endLon);
          console.log('[FWCAM Card] Setting end map preview URL:', mapUrl);
          endMapImg.src = mapUrl;
          endMapImg.onerror = (e) => {
            console.error('[FWCAM Card] Error loading end map preview:', e);
            endMapPreview.style.display = 'none';
          };
          endMapImg.onload = () => {
            console.log('[FWCAM Card] End map preview loaded successfully');
          };
          endMapImg.onclick = () => window.open(endUrl, '_blank');
          
          // Update marker position (PR #102 overlay implementation)
          const markerPos = this.getMapMarkerPosition(endLat, endLon);
          const endMarkerOuter = this.shadowRoot.getElementById('end-marker-outer');
          const endMarkerInner = this.shadowRoot.getElementById('end-marker-inner');
          if (endMarkerOuter && endMarkerInner) {
            endMarkerOuter.setAttribute('cx', `${markerPos.x}%`);
            endMarkerOuter.setAttribute('cy', `${markerPos.y}%`);
            endMarkerInner.setAttribute('cx', `${markerPos.x}%`);
            endMarkerInner.setAttribute('cy', `${markerPos.y}%`);
          }
          
          endMapPreview.style.display = 'block';
        }
      } else {
        endMapLink.style.display = 'none';
        if (endMapPreview) endMapPreview.style.display = 'none';
      }
    } else {
      mapLinks.style.display = 'none';
      if (startMapPreview) startMapPreview.style.display = 'none';
      if (endMapPreview) endMapPreview.style.display = 'none';
    }
  }

  /**
   * Handle reverse geocoding to auto-fill location name and address
   */
  async handleReverseGeocode(isStart) {
    const latField = this.shadowRoot.getElementById(isStart ? 'trip-start-latitude' : 'trip-end-latitude');
    const lonField = this.shadowRoot.getElementById(isStart ? 'trip-start-longitude' : 'trip-end-longitude');
    const nameField = this.shadowRoot.getElementById(isStart ? 'trip-start-name' : 'trip-end-name');
    const addressField = this.shadowRoot.getElementById(isStart ? 'trip-start-address' : 'trip-end-address');
    
    // Get raw values and normalize decimal separator
    // This handles locale-specific input (e.g., German: 50,000000 -> 50.000000)
    const latRaw = latField?.value || '';
    const lonRaw = lonField?.value || '';
    const lat = parseFloat(latRaw.replace(',', '.'));
    const lon = parseFloat(lonRaw.replace(',', '.'));
    
    console.log('[FWCAM Card] Reverse geocoding:', { 
      raw: `${latRaw}, ${lonRaw}`, 
      parsed: `${lat}, ${lon}`,
      isStart 
    });
    
    // Validate coordinates
    if (isNaN(lat) || isNaN(lon)) {
      const lang = this.getUserLanguage();
      const messages = {
        de: 'Bitte geben Sie Latitude und Longitude ein.',
        en: 'Please enter latitude and longitude first.'
      };
      alert(messages[lang] || messages['en']);
      return;
    }
    
    // Validate coordinate bounds
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      const lang = this.getUserLanguage();
      const messages = {
        de: 'Ungültige Koordinaten. Latitude muss zwischen -90 und 90 liegen, Longitude zwischen -180 und 180.',
        en: 'Invalid coordinates. Latitude must be between -90 and 90, longitude between -180 and 180.'
      };
      alert(messages[lang] || messages['en']);
      return;
    }
    
    try {
      // Call the backend service which checks cache first, then calls Nominatim if needed
      // The backend handles rate limiting and caching automatically
      const result = await this._hass.callService(
        'hafwcma',
        'reverse_geocode',
        {
          latitude: lat,
          longitude: lon,
          use_cache: true
        },
        {},     // target
        true,   // notifyOnError
        true    // returnResponse
      );
      
      if (result && result.response) {
        if (result.response.success) {
          const locationName = result.response.location_name || '';
          const address = result.response.address || '';
          
          // Fill in the fields if data is available
          if (locationName && nameField) {
            nameField.value = locationName;
          }
          if (address && addressField) {
            addressField.value = address;
          }
          
          // Log the result
          if (locationName || address) {
            console.log('[FWCAM Card] Reverse geocoding result:', {
              name: locationName,
              address: address,
              fromCache: result.response.from_cache
            });
          } else {
            console.log('[FWCAM Card] No location data found for coordinates, fields remain empty');
          }
        } else {
          // Only show error on actual exceptions (success=false)
          throw new Error(result.response.error || 'Geocoding error occurred');
        }
      }
    } catch (error) {
      // Only show error message on actual exceptions, not when data is simply not found
      console.error('[FWCAM Card] Error during reverse geocoding:', error);
      const lang = this.getUserLanguage();
      const messages = {
        de: 'Fehler beim Abrufen der Standortinformationen. Bitte versuchen Sie es später erneut.',
        en: 'Error fetching location information. Please try again later.'
      };
      alert(messages[lang] || messages['en']);
    }
  }

  /**
   * Populate trip autocomplete suggestions
   */
  populateTripAutocomplete() {
    if (!this._allTrips || this._allTrips.length === 0) return;
    
    // Get unique purposes
    const purposes = new Set();
    const startNames = new Set();
    const endNames = new Set();
    
    this._allTrips.forEach(trip => {
      if (trip.purpose) purposes.add(trip.purpose);
      if (trip.start_name) startNames.add(trip.start_name);
      if (trip.end_name) endNames.add(trip.end_name);
    });
    
    // Populate purpose datalist
    const purposeList = this.shadowRoot.getElementById('purpose-suggestions');
    if (purposeList) {
      purposeList.innerHTML = Array.from(purposes).map(p => `<option value="${p}"></option>`).join('');
    }
    
    // Populate start location datalist
    const startList = this.shadowRoot.getElementById('start-location-suggestions');
    if (startList) {
      startList.innerHTML = Array.from(startNames).map(n => `<option value="${n}"></option>`).join('');
    }
    
    // Populate end location datalist
    const endList = this.shadowRoot.getElementById('end-location-suggestions');
    if (endList) {
      endList.innerHTML = Array.from(endNames).map(n => `<option value="${n}"></option>`).join('');
    }
  }

  /**
   * Get CSS styles for the card
   */
  getStyles() {
    return `
      <style>
        :host {
          display: block;
        }

        ha-card {
          padding: 16px;
        }

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .card-header .name {
          font-size: 24px;
          font-weight: 500;
          color: var(--primary-text-color);
        }

        .card-content {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        .section {
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          padding: 16px;
          background: var(--card-background-color);
        }

        .section h3 {
          margin: 0 0 12px 0;
          font-size: 18px;
          font-weight: 500;
          color: var(--primary-text-color);
        }

        .info-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 12px;
        }

        .info-item {
          display: flex;
          justify-content: space-between;
          padding: 8px;
          background: var(--primary-background-color);
          border-radius: 4px;
        }

        .info-item .label {
          font-weight: 500;
          color: var(--secondary-text-color);
        }

        .info-item .value {
          font-weight: 600;
          color: var(--primary-text-color);
        }

        .controls-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 12px;
        }

        .control-button {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          padding: 16px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          transition: background 0.2s;
        }

        .control-button:hover {
          background: var(--primary-color-dark, var(--primary-color));
          opacity: 0.9;
        }

        .control-button ha-icon {
          --mdc-icon-size: 24px;
        }

        .settings-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 16px;
        }

        .setting-item {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .setting-item label {
          font-weight: 500;
          color: var(--primary-text-color);
        }

        .setting-input {
          padding: 8px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          background: var(--primary-background-color);
          color: var(--primary-text-color);
          font-size: 14px;
        }

        .last-refueling {
          padding: 12px;
          background: var(--primary-background-color);
          border-left: 4px solid var(--primary-color);
          border-radius: 4px;
          margin-bottom: 16px;
        }

        .table-container {
          overflow-x: auto;
          overflow-y: auto;
          max-height: ${this._config.table_max_height};
          min-width: ${this._config.table_min_width};
        }

        .refueling-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 14px;
        }

        .refueling-table th {
          background: var(--primary-background-color);
          padding: 12px 8px;
          text-align: left;
          font-weight: 600;
          color: var(--primary-text-color);
          border-bottom: 2px solid var(--divider-color);
        }

        .refueling-table td {
          padding: 10px 8px;
          border-bottom: 1px solid var(--divider-color);
          color: var(--primary-text-color);
        }

        .refueling-table tbody tr:hover {
          background: var(--primary-background-color);
        }

        .no-data {
          text-align: center;
          color: var(--secondary-text-color);
          font-style: italic;
        }

        .quality-badge {
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
        }

        .quality-manual {
          background: #4caf50;
          color: white;
        }

        .quality-auto_detected {
          background: #2196f3;
          color: white;
        }

        .quality-historical_import {
          background: #ff9800;
          color: white;
        }

        .confidence-badge {
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
        }

        .confidence-high {
          background: #4caf50;
          color: white;
        }

        .confidence-medium {
          background: #ff9800;
          color: white;
        }

        .confidence-low {
          background: #f44336;
          color: white;
        }

        .category-badge {
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
          text-transform: capitalize;
        }

        .category-business {
          background: #2196f3;
          color: white;
        }

        .category-private {
          background: #4caf50;
          color: white;
        }

        .category-commute {
          background: #ff9800;
          color: white;
        }

        .position-quality-badge {
          display: inline-flex;
          align-items: center;
          gap: 3px;
          padding: 3px 6px;
          border-radius: 4px;
          font-size: 10px;
          font-weight: 600;
          text-transform: uppercase;
        }

        .position-quality-full {
          background: #4caf50;
          color: white;
        }

        .position-quality-partial {
          background: #ff9800;
          color: white;
        }

        .position-quality-none {
          background: #9e9e9e;
          color: white;
        }

        .actions {
          display: flex;
          gap: 8px;
        }

        .action-button {
          padding: 6px;
          background: transparent;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          cursor: pointer;
          color: var(--primary-text-color);
          transition: all 0.2s;
        }

        .action-button:hover {
          background: var(--primary-background-color);
        }

        .edit-button:hover {
          border-color: var(--primary-color);
          color: var(--primary-color);
        }

        .delete-button:hover {
          border-color: #f44336;
          color: #f44336;
        }

        .action-button ha-icon {
          --mdc-icon-size: 18px;
        }

        .add-event-button {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 12px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          margin-top: 16px;
          transition: background 0.2s;
        }

        .add-event-button:hover {
          background: var(--primary-color-dark, var(--primary-color));
          opacity: 0.9;
        }

        .add-event-button ha-icon {
          --mdc-icon-size: 20px;
        }

        /* Sorting Styles */
        .sortable {
          cursor: pointer;
          user-select: none;
          position: relative;
        }

        .sortable:hover {
          background: var(--secondary-background-color);
        }

        .sort-icon {
          --mdc-icon-size: 16px;
          vertical-align: middle;
          margin-left: 4px;
        }

        .sort-icon.inactive {
          opacity: 0.3;
        }

        .sort-icon.active {
          opacity: 1;
          color: var(--primary-color);
        }

        .sorted-asc,
        .sorted-desc {
          background: var(--secondary-background-color);
        }

        /* Filter Styles */
        .filter-controls {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 16px;
          margin-bottom: 16px;
          padding: 12px;
          background: var(--secondary-background-color);
          border-radius: 8px;
        }

        .filter-controls label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          color: var(--primary-text-color);
        }

        .filter-select {
          padding: 6px 10px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font-size: 14px;
          cursor: pointer;
        }

        .filter-select:focus {
          outline: none;
          border-color: var(--primary-color);
        }

        .clear-filters-button {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          background: transparent;
          color: var(--primary-color);
          border: 1px solid var(--primary-color);
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.2s;
        }

        .clear-filters-button:hover {
          background: var(--primary-color);
          color: white;
        }

        .clear-filters-button ha-icon {
          --mdc-icon-size: 16px;
        }

        .filter-info {
          margin-left: auto;
          font-size: 13px;
          color: var(--secondary-text-color);
        }

        /* Pagination Styles */
        .pagination-controls {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 16px;
          margin-top: 16px;
          padding: 12px;
          background: var(--primary-background-color);
          border-radius: 8px;
        }

        .pagination-button {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 8px 16px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.2s;
        }

        .pagination-button:hover:not(:disabled) {
          background: var(--primary-color-dark, var(--primary-color));
          opacity: 0.9;
          transform: translateY(-1px);
        }

        .pagination-button:disabled {
          background: var(--disabled-text-color);
          cursor: not-allowed;
          opacity: 0.5;
        }

        .pagination-button ha-icon {
          --mdc-icon-size: 18px;
        }

        .pagination-info {
          font-size: 14px;
          font-weight: 500;
          color: var(--primary-text-color);
          min-width: 200px;
          text-align: center;
        }

        /* Date filter input styles */
        .filter-date {
          padding: 6px 10px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font-size: 14px;
          font-family: inherit;
        }

        .filter-date:focus {
          outline: none;
          border-color: var(--primary-color);
        }

        /* Dialog Styles */
        .dialog-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          backdrop-filter: blur(2px);
        }

        .dialog-content {
          background: var(--card-background-color);
          border-radius: 8px;
          max-width: 600px;
          width: 90%;
          max-height: 90vh;
          overflow-y: auto;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .dialog-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px;
          border-bottom: 1px solid var(--divider-color);
        }

        .dialog-header h2 {
          margin: 0;
          font-size: 20px;
          color: var(--primary-text-color);
        }

        .dialog-close {
          background: transparent;
          border: none;
          cursor: pointer;
          padding: 4px;
          color: var(--secondary-text-color);
          transition: color 0.2s;
        }

        .dialog-close:hover {
          color: var(--primary-text-color);
        }

        .dialog-close ha-icon {
          --mdc-icon-size: 24px;
        }

        .dialog-body {
          padding: 20px;
        }

        .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          margin-bottom: 16px;
        }

        .form-row.full-width {
          grid-template-columns: 1fr;
        }

        .form-row label {
          display: flex;
          flex-direction: column;
          gap: 6px;
          font-size: 14px;
          color: var(--primary-text-color);
          font-weight: 500;
        }

        .form-row input,
        .form-row select,
        .form-row textarea {
          padding: 10px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font-size: 14px;
          font-family: inherit;
        }

        .form-row textarea {
          resize: vertical;
          min-height: 80px;
        }

        .form-row input:focus,
        .form-row select:focus,
        .form-row textarea:focus {
          outline: none;
          border-color: var(--primary-color);
        }
        
        .form-row input:read-only {
          background: var(--disabled-color, #eee);
          color: var(--disabled-text-color);
        }
        
        .form-row label small {
          font-size: 12px;
          font-weight: normal;
          color: var(--secondary-text-color);
        }
        
        .form-section {
          margin-bottom: 24px;
          padding-bottom: 16px;
          border-bottom: 1px solid var(--divider-color);
        }
        
        .form-section:last-of-type {
          border-bottom: none;
        }
        
        .form-section h4 {
          margin: 0 0 12px 0;
          font-size: 15px;
          font-weight: 600;
          color: var(--primary-text-color);
        }
        
        #trip-map-links a {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          color: var(--primary-color);
          text-decoration: none;
          font-size: 13px;
        }
        
        #trip-map-links a:hover {
          text-decoration: underline;
        }
        
        #trip-map-links ha-icon {
          --mdc-icon-size: 16px;
        }

        .dialog-footer {
          display: flex;
          justify-content: flex-end;
          gap: 12px;
          margin-top: 24px;
          padding-top: 16px;
          border-top: 1px solid var(--divider-color);
        }

        .cancel-button,
        .submit-button {
          padding: 10px 20px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.2s;
        }

        .cancel-button {
          background: transparent;
          color: var(--secondary-text-color);
          border: 1px solid var(--divider-color);
        }

        .cancel-button:hover {
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
        }

        .submit-button {
          background: var(--primary-color);
          color: white;
        }

        .submit-button:hover {
          background: var(--primary-color-dark, var(--primary-color));
          opacity: 0.9;
        }

        .error {
          color: #f44336;
          padding: 16px;
          text-align: center;
        }
      </style>
    `;
  }

  /**
   * Static method to get a stub config for the card editor
   */
  static getStubConfig() {
    return {
      entity: 'sensor.my_car_refueling_log',
      title: 'Fuel Watcher Car Advanced Manager',
      show_refueling_log: true,
      show_vehicle_info: true,
      show_controls: true,
      show_settings: true,
      rows_per_page: 10
    };
  }
}

// Register the custom card
customElements.define('fwcam-card', FWCAMCard);

// Register the card with Home Assistant
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'fwcam-card',
  name: 'FWCAM Card',
  description: 'Fuel Watcher Car Advanced Manager Card',
  preview: false,
  documentationURL: 'https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/REFUELING_LOG_GUIDE.md'
});

console.info(
  '%c FWCAM-CARD %c v1.0.0 ',
  'color: white; background: #039be5; font-weight: 700;',
  'color: #039be5; background: white; font-weight: 700;'
);
