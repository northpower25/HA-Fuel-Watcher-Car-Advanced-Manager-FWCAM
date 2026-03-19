/**
 * FWCAM Routenplanung Card (fwcam-routenplanung-card)
 *
 * Standalone Lovelace card that exposes only the Route Planner section
 * of the Fuel Watcher Car Advanced Manager integration.
 *
 * Can be embedded in any Home Assistant dashboard independently of the
 * full fwcam-card. Configure it with the same `entity` option you use for
 * the main card (e.g. sensor.my_car_refueling_log).
 *
 * YAML example:
 *   type: custom:fwcam-routenplanung-card
 *   entity: sensor.my_car_refueling_log
 *   title: Routenplanung
 *
 * @version 1.0.0
 * @author northpower25
 * @license MIT
 */

class FWCAMRoutePlannerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = null;
    this._entities = {};
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Lovelace lifecycle
  // ──────────────────────────────────────────────────────────────────────────

  setConfig(config) {
    if (!config.entity) {
      throw new Error('fwcam-routenplanung-card: "entity" is required (e.g. sensor.my_car_refueling_log)');
    }
    this._config = {
      entity: config.entity,
      title: config.title || '🗺️ Routenplanung',
    };
  }

  set hass(hass) {
    this._hass = hass;
    this._entities = this._buildEntities();
    this._render();
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Entity helpers
  // ──────────────────────────────────────────────────────────────────────────

  /**
   * Derive the sensor base name from the configured entity and return a map
   * of all route-related entity IDs.
   */
  _buildEntities() {
    const entityId = this._config.entity || '';
    // Strip domain prefix and known suffixes to get the base name.
    // e.g. sensor.my_car_refueling_log → my_car
    let baseName = entityId.replace(/^[^.]+\./, '');
    const suffixes = [
      '_refueling_log', '_fuel_price', '_tank_level', '_range',
      '_nearest_station', '_cheapest_station', '_days_until_refuel',
      '_active_route', '_predicted_fuel_stop', '_corridor_best_station',
      '_corridor_stations',
    ];
    for (const s of suffixes) {
      if (baseName.endsWith(s)) {
        baseName = baseName.slice(0, -s.length);
        break;
      }
    }
    return {
      active_route: `sensor.${baseName}_active_route`,
      predicted_fuel_stop: `sensor.${baseName}_predicted_fuel_stop`,
      corridor_best_station: `sensor.${baseName}_corridor_best_station`,
      corridor_stations: `sensor.${baseName}_corridor_stations`,
    };
  }

  _getEntityState(entityId) {
    if (!this._hass || !entityId) return null;
    return this._hass.states[entityId] || null;
  }

  /**
   * Retrieve the config_entry_id from the configured entity's attributes.
   * Falls back to the entry_id attribute used in some card versions.
   */
  _getConfigEntryId() {
    const entity = this._getEntityState(this._config.entity);
    if (entity) {
      return entity.attributes.config_entry_id || entity.attributes.entry_id || '';
    }
    return '';
  }

  // ──────────────────────────────────────────────────────────────────────────
  // HTML escaping
  // ──────────────────────────────────────────────────────────────────────────

  _esc(val) {
    if (val == null) return '';
    return String(val)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Rendering
  // ──────────────────────────────────────────────────────────────────────────

  _render() {
    if (!this._hass) return;
    this.shadowRoot.innerHTML = `
      ${this._getStyles()}
      <ha-card>
        <div class="card-header">
          <span class="name">${this._esc(this._config.title)}</span>
        </div>
        <div class="card-content">
          ${this._renderRoutePlanner()}
        </div>
      </ha-card>
    `;
    this._attachListeners();
  }

  _renderRoutePlanner() {
    const activeRouteEntity = this._getEntityState(this._entities.active_route);
    const predictedFuelStopEntity = this._getEntityState(this._entities.predicted_fuel_stop);
    const corridorBestEntity = this._getEntityState(this._entities.corridor_best_station);
    const corridorStationsEntity = this._getEntityState(this._entities.corridor_stations);

    const isActive = activeRouteEntity && activeRouteEntity.state === 'active';
    const routeAttrs = activeRouteEntity ? (activeRouteEntity.attributes || {}) : {};
    const fuelStopAttrs = predictedFuelStopEntity ? (predictedFuelStopEntity.attributes || {}) : {};
    const bestAttrs = corridorBestEntity ? (corridorBestEntity.attributes || {}) : {};
    const corridorAttrs = corridorStationsEntity ? (corridorStationsEntity.attributes || {}) : {};
    const topStations = corridorAttrs.stations || [];

    const activeStatusHtml = isActive ? `
      <div class="info-grid" style="margin-top:0.5rem;">
        <div class="info-item">
          <span class="info-label">Ziel</span>
          <span class="info-value">${this._esc(routeAttrs.destination || '—')}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Distanz</span>
          <span class="info-value">${routeAttrs.total_distance_km != null ? routeAttrs.total_distance_km + ' km' : '—'}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Korridor-Breite</span>
          <span class="info-value">${routeAttrs.corridor_width_km != null ? routeAttrs.corridor_width_km + ' km' : '—'}</span>
        </div>
        ${predictedFuelStopEntity && predictedFuelStopEntity.state && predictedFuelStopEntity.state !== 'unknown' && predictedFuelStopEntity.state !== 'unavailable' ? `
        <div class="info-item">
          <span class="info-label">Vorhergesagter Tankstopp</span>
          <span class="info-value">~${this._esc(predictedFuelStopEntity.state)} km voraus</span>
        </div>` : ''}
      </div>
    ` : '';

    const bestStationHtml = (isActive && corridorBestEntity && corridorBestEntity.state && corridorBestEntity.state !== 'unknown' && corridorBestEntity.state !== 'unavailable') ? `
      <div style="margin-top:0.75rem;padding:0.5rem;background:var(--secondary-background-color,#f5f5f5);border-radius:6px;">
        <div style="font-weight:600;margin-bottom:0.25rem;">🏆 Beste Tankstelle im Korridor</div>
        <div class="info-grid" style="margin:0;">
          <div class="info-item">
            <span class="info-label">Tankstelle</span>
            <span class="info-value">${this._esc(bestAttrs.station_name || '—')}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Preis</span>
            <span class="info-value">${bestAttrs.price_per_litre != null ? bestAttrs.price_per_litre + ' €/l' : '—'}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Umweg</span>
            <span class="info-value">${bestAttrs.detour_km != null ? bestAttrs.detour_km + ' km' : '—'}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Effektivpreis</span>
            <span class="info-value">${bestAttrs.effective_price_eur_per_l != null ? bestAttrs.effective_price_eur_per_l + ' €/l' : '—'}</span>
          </div>
        </div>
        <div style="margin-top:0.4rem;display:flex;gap:0.5rem;flex-wrap:wrap;">
          ${bestAttrs.google_maps_url ? `<a href="${this._esc(bestAttrs.google_maps_url)}" target="_blank" rel="noopener" style="font-size:0.8rem;">🗺️ Google Maps</a>` : ''}
          ${bestAttrs.waze_url ? `<a href="${this._esc(bestAttrs.waze_url)}" target="_blank" rel="noopener" style="font-size:0.8rem;">🚗 Waze</a>` : ''}
          ${bestAttrs.apple_maps_url ? `<a href="${this._esc(bestAttrs.apple_maps_url)}" target="_blank" rel="noopener" style="font-size:0.8rem;">🍎 Apple Maps</a>` : ''}
        </div>
      </div>
    ` : '';

    const topStationsHtml = (isActive && topStations.length > 1) ? `
      <div style="margin-top:0.75rem;">
        <div style="font-weight:600;margin-bottom:0.25rem;">📋 Top Tankstellen im Korridor</div>
        <table style="width:100%;font-size:0.8rem;border-collapse:collapse;">
          <thead><tr style="text-align:left;border-bottom:1px solid var(--divider-color,#ccc);">
            <th style="padding:2px 4px;">#</th>
            <th style="padding:2px 4px;">Tankstelle</th>
            <th style="padding:2px 4px;">Preis</th>
            <th style="padding:2px 4px;">Umweg</th>
            <th style="padding:2px 4px;">Eff. Preis</th>
          </tr></thead>
          <tbody>
            ${topStations.slice(0, 3).map((st, i) => `
              <tr style="border-bottom:1px solid var(--divider-color,#eee);">
                <td style="padding:2px 4px;">${i + 1}</td>
                <td style="padding:2px 4px;">${this._esc(st.name || '—')}</td>
                <td style="padding:2px 4px;">${st.price != null ? st.price + ' €/l' : '—'}</td>
                <td style="padding:2px 4px;">${st.detour_km != null ? st.detour_km + ' km' : '—'}</td>
                <td style="padding:2px 4px;">${st.effective_price_eur_per_l != null ? st.effective_price_eur_per_l + ' €/l' : '—'}</td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>
    ` : '';

    return `
      <div class="section">
        <div style="display:flex;flex-direction:column;gap:0.5rem;">
          <label style="font-size:0.85rem;font-weight:500;">Zieladresse</label>
          <input id="rp-destination" type="text" class="setting-input"
            placeholder="z.B. München Hauptbahnhof"
            style="padding:0.4rem 0.6rem;border:1px solid var(--divider-color,#ccc);border-radius:4px;font-size:0.9rem;width:100%;box-sizing:border-box;">

          <label style="font-size:0.85rem;font-weight:500;">Zwischenstopps <small style="font-weight:normal;">(optional, kommagetrennt)</small></label>
          <input id="rp-waypoints" type="text" class="setting-input"
            placeholder="z.B. Augsburg, Ingolstadt"
            style="padding:0.4rem 0.6rem;border:1px solid var(--divider-color,#ccc);border-radius:4px;font-size:0.9rem;width:100%;box-sizing:border-box;">

          <div style="display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-end;">
            <div style="flex:1;min-width:120px;">
              <label style="font-size:0.85rem;font-weight:500;">Korridor-Breite (km)</label>
              <input id="rp-corridor" type="number" class="setting-input"
                min="1" max="50" step="1" value="5"
                style="padding:0.4rem 0.6rem;border:1px solid var(--divider-color,#ccc);border-radius:4px;font-size:0.9rem;width:100%;box-sizing:border-box;">
            </div>
            <div style="flex:1;min-width:140px;">
              <label style="font-size:0.85rem;font-weight:500;">Routing-Anbieter</label>
              <select id="rp-provider" class="setting-input"
                style="padding:0.4rem 0.6rem;border:1px solid var(--divider-color,#ccc);border-radius:4px;font-size:0.9rem;width:100%;box-sizing:border-box;">
                <option value="osrm" selected>OSRM (kostenlos)</option>
                <option value="openrouteservice">OpenRouteService</option>
                <option value="google">Google Maps</option>
              </select>
            </div>
          </div>

          <div id="rp-google-key-row" style="display:none;flex-direction:column;gap:0.25rem;">
            <label style="font-size:0.85rem;font-weight:500;">Google API Key</label>
            <input id="rp-google-key" type="text" class="setting-input"
              placeholder="Google Maps API-Schlüssel"
              style="padding:0.4rem 0.6rem;border:1px solid var(--divider-color,#ccc);border-radius:4px;font-size:0.9rem;width:100%;box-sizing:border-box;">
          </div>

          <div style="display:flex;gap:0.5rem;margin-top:0.25rem;">
            <button id="rp-start-btn" class="control-button" style="flex:1;justify-content:center;">
              <ha-icon icon="mdi:map-marker-path"></ha-icon>
              <span>Route starten</span>
            </button>
            ${isActive ? `
            <button id="rp-cancel-btn" class="control-button"
              style="flex:0 0 auto;background:var(--error-color,#d32f2f);color:white;">
              <ha-icon icon="mdi:close-circle"></ha-icon>
              <span>Abbrechen</span>
            </button>` : ''}
          </div>
        </div>

        ${isActive ? `<div style="margin-top:0.5rem;padding:0.4rem 0.6rem;background:var(--primary-color,#039be5);color:white;border-radius:4px;font-size:0.85rem;">
          ✅ Route aktiv
        </div>` : ''}
        ${activeStatusHtml}
        ${bestStationHtml}
        ${topStationsHtml}
      </div>
    `;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Event listeners
  // ──────────────────────────────────────────────────────────────────────────

  _attachListeners() {
    const startBtn = this.shadowRoot.getElementById('rp-start-btn');
    if (startBtn) {
      startBtn.addEventListener('click', () => this._handleRouteStart());
    }

    const cancelBtn = this.shadowRoot.getElementById('rp-cancel-btn');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => this._handleRouteCancel());
    }

    const providerSelect = this.shadowRoot.getElementById('rp-provider');
    const googleKeyRow = this.shadowRoot.getElementById('rp-google-key-row');
    if (providerSelect && googleKeyRow) {
      const updateVisibility = () => {
        googleKeyRow.style.display = providerSelect.value === 'google' ? 'flex' : 'none';
      };
      providerSelect.addEventListener('change', updateVisibility);
      updateVisibility();
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Service calls
  // ──────────────────────────────────────────────────────────────────────────

  async _handleRouteStart() {
    const destinationEl = this.shadowRoot.getElementById('rp-destination');
    const waypointsEl = this.shadowRoot.getElementById('rp-waypoints');
    const corridorEl = this.shadowRoot.getElementById('rp-corridor');
    const providerEl = this.shadowRoot.getElementById('rp-provider');
    const googleKeyEl = this.shadowRoot.getElementById('rp-google-key');

    const destination = destinationEl ? destinationEl.value.trim() : '';
    if (!destination) {
      alert('Bitte eine Zieladresse eingeben.');
      return;
    }

    const waypointsRaw = waypointsEl ? waypointsEl.value.trim() : '';
    const waypoints = waypointsRaw
      ? waypointsRaw.split(',').map(w => w.trim()).filter(Boolean)
      : [];
    const corridorWidth = corridorEl ? (parseFloat(corridorEl.value) || 5) : 5;
    const provider = providerEl ? providerEl.value : 'osrm';
    const googleApiKey = googleKeyEl ? googleKeyEl.value.trim() : '';

    const configEntryId = this._getConfigEntryId();

    const serviceData = {
      config_entry_id: configEntryId,
      destination,
      waypoints,
      corridor_width_km: corridorWidth,
      routing_provider: provider,
    };
    if (googleApiKey) {
      serviceData.google_api_key = googleApiKey;
    }

    try {
      await this._hass.callService('hafwcma', 'set_route', serviceData);
    } catch (err) {
      console.error('FWCAM Routenplanung: set_route failed', err);
      alert(`Route konnte nicht gestartet werden: ${err.message || err}`);
    }
  }

  async _handleRouteCancel() {
    const configEntryId = this._getConfigEntryId();
    try {
      await this._hass.callService('hafwcma', 'cancel_route', { config_entry_id: configEntryId });
    } catch (err) {
      console.error('FWCAM Routenplanung: cancel_route failed', err);
      alert(`Route konnte nicht abgebrochen werden: ${err.message || err}`);
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // CSS
  // ──────────────────────────────────────────────────────────────────────────

  _getStyles() {
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
          font-size: 20px;
          font-weight: 500;
          color: var(--primary-text-color);
        }
        .card-content {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .section {
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          padding: 16px;
          background: var(--card-background-color);
        }
        .info-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 8px;
        }
        .info-item {
          display: flex;
          flex-direction: column;
          padding: 6px 8px;
          background: var(--primary-background-color);
          border-radius: 4px;
        }
        .info-label {
          font-size: 0.75rem;
          font-weight: 500;
          color: var(--secondary-text-color);
        }
        .info-value {
          font-size: 0.9rem;
          font-weight: 600;
          color: var(--primary-text-color);
        }
        .control-button {
          display: flex;
          flex-direction: row;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          transition: opacity 0.2s;
          font-size: 0.9rem;
        }
        .control-button:hover {
          opacity: 0.88;
        }
        .control-button ha-icon {
          --mdc-icon-size: 20px;
        }
        .setting-input {
          background: var(--primary-background-color);
          color: var(--primary-text-color);
        }
      </style>
    `;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Card editor stub config
  // ──────────────────────────────────────────────────────────────────────────

  static getStubConfig() {
    return {
      entity: 'sensor.my_car_refueling_log',
      title: '🗺️ Routenplanung',
    };
  }
}

// Register the custom element
customElements.define('fwcam-routenplanung-card', FWCAMRoutePlannerCard);

// Register with Home Assistant card picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'fwcam-routenplanung-card',
  name: 'FWCAM Routenplanung',
  description: 'Fuel Watcher Car Advanced Manager – Routenplanung mit Korridorsuche',
  preview: false,
  documentationURL: 'https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/user_docs/ROUTENPLANUNG_ANLEITUNG_DE.md',
});

console.info(
  '%c FWCAM-ROUTENPLANUNG-CARD %c v1.0.0 ',
  'color: white; background: #039be5; font-weight: 700;',
  'color: #039be5; background: white; font-weight: 700;'
);
