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
    // State for table sorting and filtering
    this._sortColumn = 'timestamp';
    this._sortDirection = 'desc';
    this._filterYear = '';
    this._filterMonth = '';
  }

  /**
   * Set configuration for the card
   */
  setConfig(config) {
    if (!config.entity) {
      throw new Error('You need to define an entity (refueling_log sensor)');
    }
    this._config = {
      entity: config.entity,
      title: config.title || 'Fuel Watcher Car Advanced Manager',
      show_refueling_log: config.show_refueling_log !== false,
      show_trip_log: config.show_trip_log !== false,
      show_vehicle_info: config.show_vehicle_info !== false,
      show_controls: config.show_controls !== false,
      show_settings: config.show_settings !== false,
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
      station_search_radius: `number.${baseName}_station_search_radius`,
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
   * Call a Home Assistant service
   */
  callService(domain, service, serviceData = {}) {
    if (!this._hass) return Promise.reject(new Error('Home Assistant not available'));
    
    return this._hass.callService(domain, service, serviceData).then(() => {
      // Force render after service calls to show immediate feedback
      setTimeout(() => this.forceRender(), SERVICE_CALL_REFRESH_DELAY_MS);
    });
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
    if (value === null || value === undefined) return 'N/A';
    return `${parseFloat(value).toFixed(decimals)}${unit ? ' ' + unit : ''}`;
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

    const recentEvents = entity.attributes.recent_events || [];
    const lastRefueling = entity.attributes.last_refueling || null;
    
    // Get trip log data if trip log sensor exists
    const tripLogEntity = this.getEntityState(this._entities.trip_log_sensor);
    const recentTrips = tripLogEntity?.attributes?.recent_trips || [];
    
    // Store events for dialog access
    this._recentEvents = recentEvents;
    this._recentTrips = recentTrips;

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
          ${this._config.show_refueling_log ? this.renderRefuelingLog(recentEvents, lastRefueling) : ''}
          ${this._config.show_trip_log ? this.renderTripLog(recentTrips) : ''}
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
    const nearestStation = this.getEntityState(this._entities.nearest_station);
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
            <span class="value">${nearestStation ? nearestStation.state : 'N/A'}</span>
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
    const searchRadius = this.getEntityState(this._entities.station_search_radius);
    const updateInterval = this.getEntityState(this._entities.update_interval);
    const minDataPoints = this.getEntityState(this._entities.consumption_min_data_points);
    const predictionInterval = this.getEntityState(this._entities.consumption_prediction_interval);

    return `
      <div class="section">
        <h3>Settings</h3>
        <div class="settings-grid">
          <div class="setting-item">
            <label>Station Search Radius (km):</label>
            <input type="number" 
                   class="setting-input" 
                   data-entity="${this._entities.station_search_radius}"
                   value="${searchRadius ? searchRadius.state : ''}"
                   min="1" max="25" step="0.5">
          </div>
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

    // Filter dropdowns (refueling and trips)
    this.shadowRoot.querySelectorAll('.filter-select').forEach(select => {
      select.addEventListener('change', (e) => {
        const filterType = e.target.dataset.filter;
        const value = e.target.value;
        if (filterType === 'trip-category') {
          this.handleTripFilterChange(value);
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
   * Render trip log section with filtering, sorting, and editing
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

    // Apply filtering by category if needed
    const filteredTrips = this._tripCategoryFilter 
      ? trips.filter(t => t.category === this._tripCategoryFilter)
      : trips;

    // Apply sorting
    const sortColumn = this._tripSortColumn || 'timestamp_end';
    const sortDirection = this._tripSortDirection || 'desc';
    const sortedTrips = [...filteredTrips].sort((a, b) => {
      let aVal = a[sortColumn];
      let bVal = b[sortColumn];
      
      // Handle null/undefined values
      if (aVal == null) aVal = '';
      if (bVal == null) bVal = '';
      
      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    const categories = [
      { value: '', label: 'All Categories' },
      { value: 'business', label: 'Business' },
      { value: 'private', label: 'Private' },
      { value: 'commute', label: 'Commute' }
    ];

    return `
      <div class="section">
        <h3>Trip Log</h3>
        
        <div class="filter-controls">
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
          ${this._tripCategoryFilter ? `
            <button class="clear-filters-button" data-action="clear-trip-filters">
              <ha-icon icon="mdi:filter-remove"></ha-icon>
              <span>Clear Filter</span>
            </button>
          ` : ''}
          <div class="filter-info">
            Showing ${sortedTrips.length} of ${trips.length} trips
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
                <th class="sortable ${sortColumn === 'fuel_consumed' ? 'sorted-' + sortDirection : ''}" 
                    data-sort-column="fuel_consumed" data-sort-type="trip">
                  Fuel (L)
                  ${this.renderTripSortIcon('fuel_consumed')}
                </th>
                <th class="sortable ${sortColumn === 'fuel_cost' ? 'sorted-' + sortDirection : ''}" 
                    data-sort-column="fuel_cost" data-sort-type="trip">
                  Fuel Cost (€)
                  ${this.renderTripSortIcon('fuel_cost')}
                </th>
                <th>Additional Costs (€)</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${sortedTrips.length === 0 ? `
                <tr>
                  <td colspan="8" class="no-data">No trips match the current filter</td>
                </tr>
              ` : sortedTrips.slice(0, this._config.rows_per_page || 10).map(trip => `
                <tr data-trip-id="${trip.trip_id}">
                  <td>${this.formatDateTime(trip.timestamp_end)}</td>
                  <td>${this.formatNumber(trip.distance_km, 1)}</td>
                  <td>
                    <span class="category-badge category-${trip.category || 'private'}">
                      ${(trip.category || 'private').charAt(0).toUpperCase() + (trip.category || 'private').slice(1)}
                    </span>
                  </td>
                  <td>${trip.purpose || '-'}</td>
                  <td>${trip.fuel_consumed ? this.formatNumber(trip.fuel_consumed, 2) : '-'}</td>
                  <td>${trip.fuel_cost ? this.formatNumber(trip.fuel_cost, 2) : '-'}</td>
                  <td>${trip.additional_costs ? this.formatNumber(trip.additional_costs, 2) : '0.00'}</td>
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
              <div class="form-group">
                <label for="trip-start-time">Start Time:</label>
                <input type="datetime-local" id="trip-start-time" name="timestamp_start" required>
              </div>
              
              <div class="form-group">
                <label for="trip-end-time">End Time:</label>
                <input type="datetime-local" id="trip-end-time" name="timestamp_end" required>
              </div>
              
              <div class="form-group">
                <label for="trip-distance">Distance (km):</label>
                <input type="number" id="trip-distance" name="distance_km" step="0.1" min="0" required>
              </div>
              
              <div class="form-group">
                <label for="trip-category">Category:</label>
                <select id="trip-category" name="category">
                  <option value="private">Private</option>
                  <option value="business">Business</option>
                  <option value="commute">Commute</option>
                </select>
              </div>
              
              <div class="form-group">
                <label for="trip-purpose">Purpose:</label>
                <input type="text" id="trip-purpose" name="purpose" placeholder="Optional">
              </div>
              
              <div class="form-group">
                <label for="trip-fuel-consumed">Fuel Consumed (L):</label>
                <input type="number" id="trip-fuel-consumed" name="fuel_consumed" step="0.01" min="0" placeholder="Optional">
              </div>
              
              <div class="form-group">
                <label for="trip-additional-costs">Additional Costs (€):</label>
                <input type="number" id="trip-additional-costs" name="additional_costs" step="0.01" min="0" placeholder="Optional" value="0">
              </div>
              
              <div class="form-group">
                <label for="trip-notes">Notes:</label>
                <textarea id="trip-notes" name="notes" rows="3" placeholder="Optional"></textarea>
              </div>
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
                  </select>
                </label>
                <label for="confidence">
                  Confidence (0-1)
                  <input type="number" id="confidence" name="confidence" 
                         min="0" max="1" step="0.1" value="1.0">
                </label>
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
    
    // Find event in stored events
    const event = this._recentEvents ? this._recentEvents.find(e => e.id === parseInt(eventId)) : null;
    
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
    
    // Find trip in stored trips
    const trip = this._recentTrips ? this._recentTrips.find(t => t.trip_id === parseInt(tripId)) : null;
    
    if (!trip) {
      alert(`Trip with ID ${tripId} not found`);
      return;
    }
    
    // Set title
    dialogTitle.textContent = `Edit Trip #${tripId}`;
    
    // Store trip ID for submission
    form.dataset.tripId = tripId;
    
    // Populate form with trip data
    const tzOffset = new Date().getTimezoneOffset() * 60000;
    
    if (trip.timestamp_start) {
      const startDate = new Date(trip.timestamp_start);
      const localStart = new Date(startDate - tzOffset).toISOString().slice(0, 16);
      this.shadowRoot.getElementById('trip-start-time').value = localStart;
    }
    
    if (trip.timestamp_end) {
      const endDate = new Date(trip.timestamp_end);
      const localEnd = new Date(endDate - tzOffset).toISOString().slice(0, 16);
      this.shadowRoot.getElementById('trip-end-time').value = localEnd;
    }
    
    this.shadowRoot.getElementById('trip-distance').value = trip.distance_km || '';
    this.shadowRoot.getElementById('trip-category').value = trip.category || 'private';
    this.shadowRoot.getElementById('trip-purpose').value = trip.purpose || '';
    this.shadowRoot.getElementById('trip-fuel-consumed').value = trip.fuel_consumed || '';
    this.shadowRoot.getElementById('trip-additional-costs').value = trip.additional_costs || 0;
    this.shadowRoot.getElementById('trip-notes').value = trip.notes || '';
    
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
      timestamp_start: formData.get('timestamp_start'),
      timestamp_end: formData.get('timestamp_end'),
      distance_km: parseFloat(formData.get('distance_km')),
      category: formData.get('category') || 'private'
    };
    
    // Add optional fields if provided
    if (formData.get('purpose')) {
      serviceData.purpose = formData.get('purpose');
    }
    if (formData.get('fuel_consumed')) {
      serviceData.fuel_consumed = parseFloat(formData.get('fuel_consumed'));
    }
    if (formData.get('additional_costs')) {
      serviceData.additional_costs = parseFloat(formData.get('additional_costs'));
    }
    if (formData.get('notes')) {
      serviceData.notes = formData.get('notes');
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
      alert('Failed to save trip. Please try again.');
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
      liters_refueled: parseFloat(formData.get('liters_refueled'))
    };
    
    // Add optional fields if provided
    if (formData.get('odometer_km')) {
      serviceData.odometer_km = parseInt(formData.get('odometer_km'));
    }
    if (formData.get('price_per_liter')) {
      serviceData.price_per_liter = parseFloat(formData.get('price_per_liter'));
    }
    if (formData.get('total_cost')) {
      serviceData.total_cost = parseFloat(formData.get('total_cost'));
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
      serviceData.confidence = parseFloat(formData.get('confidence'));
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
        .form-row select {
          padding: 10px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font-size: 14px;
        }

        .form-row input:focus,
        .form-row select:focus {
          outline: none;
          border-color: var(--primary-color);
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
