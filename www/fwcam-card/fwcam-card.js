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

class FWCAMCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = null;
    this._entities = {};
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
      show_vehicle_info: config.show_vehicle_info !== false,
      show_controls: config.show_controls !== false,
      show_settings: config.show_settings !== false,
      rows_per_page: config.rows_per_page || 10,
      ...config
    };
    this.findEntities();
    this.render();
  }

  /**
   * Set Home Assistant instance
   */
  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  /**
   * Get card size for layout
   */
  getCardSize() {
    return 10;
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
      // Switches
      fuel_price_refresh: `switch.${baseName}_fuel_price_refresh`,
      consumption_prediction: `switch.${baseName}_consumption_prediction`,
      // Numbers
      station_search_radius: `number.${baseName}_station_search_radius`,
      update_interval: `number.${baseName}_update_interval`,
      consumption_min_data_points: `number.${baseName}_consumption_min_data_points`,
      consumption_prediction_interval: `number.${baseName}_consumption_prediction_interval`,
      // Buttons
      test_connection: `button.${baseName}_test_connection`,
      import_historical_data: `button.${baseName}_import_historical_data`,
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
    if (!this._hass) return;
    this._hass.callService(domain, service, serviceData);
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
    this.callService('hafwcma', 'add_refuel_event', {
      config_entry_id: this.getConfigEntryId(),
      ...eventData
    });
  }

  /**
   * Update an existing refueling event
   */
  updateRefuelingEvent(eventId, eventData) {
    this.callService('hafwcma', 'update_refuel_event', {
      config_entry_id: this.getConfigEntryId(),
      event_id: eventId,
      ...eventData
    });
  }

  /**
   * Delete a refueling event
   */
  deleteRefuelingEvent(eventId) {
    if (confirm('Are you sure you want to delete this refueling event?')) {
      this.callService('hafwcma', 'delete_refuel_event', {
        config_entry_id: this.getConfigEntryId(),
        event_id: eventId
      });
    }
  }

  /**
   * Get config entry ID from entity
   */
  getConfigEntryId() {
    const entity = this.getEntityState(this._config.entity);
    if (!entity || !entity.attributes.config_entry_id) {
      console.error('Cannot find config_entry_id');
      return null;
    }
    return entity.attributes.config_entry_id;
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
        </div>
      </ha-card>
    `;

    this.attachEventListeners();
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
   * Render refueling log section with inline editing
   */
  renderRefuelingLog(events, lastRefueling) {
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

        <div class="table-container">
          <table class="refueling-table">
            <thead>
              <tr>
                <th>Date/Time</th>
                <th>Odometer (km)</th>
                <th>Liters</th>
                <th>Price/L (€)</th>
                <th>Total (€)</th>
                <th>Station</th>
                <th>Quality</th>
                <th>Confidence</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${events.length === 0 ? `
                <tr>
                  <td colspan="9" class="no-data">No refueling events recorded</td>
                </tr>
              ` : events.slice(0, this._config.rows_per_page).map(event => `
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

    // Refueling log action buttons
    this.shadowRoot.querySelectorAll('.action-button').forEach(button => {
      button.addEventListener('click', (e) => {
        const action = e.currentTarget.dataset.action;
        const eventId = e.currentTarget.dataset.eventId;
        
        if (action === 'edit') {
          this.showEditDialog(eventId);
        } else if (action === 'delete') {
          this.deleteRefuelingEvent(eventId);
        }
      });
    });

    // Add event button
    const addButton = this.shadowRoot.querySelector('.add-event-button');
    if (addButton) {
      addButton.addEventListener('click', () => {
        this.showAddDialog();
      });
    }
  }

  /**
   * Show dialog to add a new refueling event
   */
  showAddDialog() {
    // TODO: Implement dialog for adding refueling events
    // For now, show a simple alert
    alert('Add refueling event dialog - To be implemented with a proper dialog component');
  }

  /**
   * Show dialog to edit an existing refueling event
   */
  showEditDialog(eventId) {
    // TODO: Implement dialog for editing refueling events
    // For now, show a simple alert
    alert(`Edit refueling event ${eventId} - To be implemented with a proper dialog component`);
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
