/**
 * FWCAM Routenplanung Card (fwcam-routenplanung-card)
 *
 * Standalone Lovelace card that exposes the full Route Planner section
 * of the Fuel Watcher Car Advanced Manager integration.
 *
 * Features:
 * - Start a route immediately (set_route service)
 * - Plan a future route (plan_route service) with departure date/time
 * - Manage all planned routes: view, edit, activate, delete
 * - Active route status with best corridor station and fuel stop prediction
 *
 * YAML example:
 *   type: custom:fwcam-routenplanung-card
 *   entity: sensor.my_car_refueling_log
 *   title: Routenplanung
 *
 * @version 2.0.0
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
    this._plannedRoutes = [];
    this._plannedRoutesLoaded = false;
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error('fwcam-routenplanung-card: "entity" is required (e.g. sensor.my_car_refueling_log)');
    }
    this._config = {
      entity: config.entity,
      title: config.title || '\ud83d\uddfa\ufe0f Routenplanung',
    };
  }

  set hass(hass) {
    this._hass = hass;
    this._entities = this._buildEntities();
    if (!this.shadowRoot.querySelector('ha-card')) {
      this._render();
    } else {
      this._updateStatus();
      this._syncPlannedRoutesFromEntity();
    }
  }

  _buildEntities() {
    const entityId = this._config.entity || '';
    let baseName = entityId.replace(/^[^.]+\./, '');
    const suffixes = [
      '_refueling_log', '_fuel_price', '_tank_level', '_range',
      '_nearest_station', '_cheapest_station', '_days_until_refuel',
      '_active_route', '_planned_routes', '_predicted_fuel_stop',
      '_corridor_best_station', '_corridor_stations',
    ];
    for (const s of suffixes) {
      if (baseName.endsWith(s)) {
        baseName = baseName.slice(0, -s.length);
        break;
      }
    }
    return {
      active_route: `sensor.${baseName}_active_route`,
      planned_routes: `sensor.${baseName}_planned_routes`,
      predicted_fuel_stop: `sensor.${baseName}_predicted_fuel_stop`,
      corridor_best_station: `sensor.${baseName}_corridor_best_station`,
      corridor_stations: `sensor.${baseName}_corridor_stations`,
    };
  }

  _getEntityState(entityId) {
    if (!this._hass || !entityId) return null;
    return this._hass.states[entityId] || null;
  }

  _getConfigEntryId() {
    const entity = this._getEntityState(this._config.entity);
    if (entity) return entity.attributes.config_entry_id || entity.attributes.entry_id || '';
    const planned = this._getEntityState(this._entities.planned_routes);
    if (planned) return planned.attributes.config_entry_id || '';
    return '';
  }

  _syncPlannedRoutesFromEntity() {
    const entity = this._getEntityState(this._entities.planned_routes);
    if (entity && Array.isArray(entity.attributes.routes)) {
      this._plannedRoutes = entity.attributes.routes;
      this._plannedRoutesLoaded = true;
      this._updatePlannedRoutesList();
    }
  }

  _esc(val) {
    if (val == null) return '';
    return String(val)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  _render() {
    if (!this._hass) return;
    this.shadowRoot.innerHTML = `
      ${this._getStyles()}
      <ha-card>
        <div class="card-header">
          <span class="name">${this._esc(this._config.title)}</span>
        </div>
        <div class="card-content">
          <div class="section">
            ${this._renderFormSection()}
            <div id="rp-status"></div>
          </div>
          <div class="section" id="rp-planned-routes-section">
            ${this._renderPlannedRoutesList()}
          </div>
        </div>
      </ha-card>
    `;
    this._attachListeners();
    this._updateStatus();
    this._syncPlannedRoutesFromEntity();
    if (!this._plannedRoutesLoaded) {
      this._fetchPlannedRoutes();
    }
  }

  _updateStatus() {
    const statusEl = this.shadowRoot.getElementById('rp-status');
    if (!statusEl) { this._render(); return; }
    statusEl.innerHTML = this._renderStatusSection();
    const cancelBtn = this.shadowRoot.getElementById('rp-cancel-btn');
    if (cancelBtn) cancelBtn.addEventListener('click', () => this._handleRouteCancel());
  }

  _updatePlannedRoutesList() {
    const el = this.shadowRoot.getElementById('rp-planned-routes-section');
    if (el) {
      el.innerHTML = this._renderPlannedRoutesList();
      this._attachPlannedRoutesListeners();
    }
  }

  _renderFormSection() {
    return `
      <div style="display:flex;flex-direction:column;gap:0.5rem;">
        <label style="font-size:0.85rem;font-weight:500;">Startadresse <small style="font-weight:normal;">(optional)</small></label>
        <input id="rp-origin" type="text" class="setting-input"
          placeholder="z.B. Berlin Hauptbahnhof (leer = Fahrzeugposition)"
          style="padding:0.4rem 0.6rem;border:1px solid var(--divider-color,#ccc);border-radius:4px;font-size:0.9rem;width:100%;box-sizing:border-box;">
        <label style="font-size:0.85rem;font-weight:500;">Zieladresse</label>
        <input id="rp-destination" type="text" class="setting-input"
          placeholder="z.B. M\u00fcnchen Hauptbahnhof"
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
            placeholder="Google Maps API-Schl\u00fcssel"
            style="padding:0.4rem 0.6rem;border:1px solid var(--divider-color,#ccc);border-radius:4px;font-size:0.9rem;width:100%;box-sizing:border-box;">
        </div>
        <div style="display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-end;">
          <div style="flex:1;min-width:140px;">
            <label style="font-size:0.85rem;font-weight:500;">Abfahrtsdatum <small style="font-weight:normal;">(optional)</small></label>
            <input id="rp-departure-date" type="date" class="setting-input"
              style="padding:0.4rem 0.6rem;border:1px solid var(--divider-color,#ccc);border-radius:4px;font-size:0.9rem;width:100%;box-sizing:border-box;">
          </div>
          <div style="flex:1;min-width:120px;">
            <label style="font-size:0.85rem;font-weight:500;">Abfahrtszeit <small style="font-weight:normal;">(24h)</small></label>
            <input id="rp-departure-time" type="time" class="setting-input"
              style="padding:0.4rem 0.6rem;border:1px solid var(--divider-color,#ccc);border-radius:4px;font-size:0.9rem;width:100%;box-sizing:border-box;">
          </div>
        </div>
        <div style="display:flex;gap:0.5rem;margin-top:0.25rem;flex-wrap:wrap;">
          <button id="rp-start-btn" class="control-button" style="flex:1;justify-content:center;">
            <ha-icon icon="mdi:map-marker-path"></ha-icon>
            <span>Route starten</span>
          </button>
          <button id="rp-plan-btn" class="control-button plan-button" style="flex:1;justify-content:center;">
            <ha-icon icon="mdi:calendar-plus"></ha-icon>
            <span>Route planen</span>
          </button>
        </div>
      </div>
    `;
  }

  _renderStatusSection() {
    const activeRouteEntity = this._getEntityState(this._entities.active_route);
    const predictedFuelStopEntity = this._getEntityState(this._entities.predicted_fuel_stop);
    const corridorBestEntity = this._getEntityState(this._entities.corridor_best_station);
    const corridorStationsEntity = this._getEntityState(this._entities.corridor_stations);
    const isActive = activeRouteEntity && activeRouteEntity.state === 'active';
    const routeAttrs = activeRouteEntity ? (activeRouteEntity.attributes || {}) : {};
    const bestAttrs = corridorBestEntity ? (corridorBestEntity.attributes || {}) : {};
    const corridorAttrs = corridorStationsEntity ? (corridorStationsEntity.attributes || {}) : {};
    const topStations = corridorAttrs.stations || [];
    const cancelBtnHtml = isActive ? `
      <div style="display:flex;gap:0.5rem;margin-top:0.25rem;">
        <button id="rp-cancel-btn" class="control-button cancel-button" style="flex:0 0 auto;">
          <ha-icon icon="mdi:close-circle"></ha-icon>
          <span>Abbrechen</span>
        </button>
      </div>` : '';
    const activeBannerHtml = isActive ? `
      <div style="margin-top:0.5rem;padding:0.4rem 0.6rem;background:var(--primary-color,#039be5);color:white;border-radius:4px;font-size:0.85rem;">
        \u2705 Route aktiv
      </div>` : '';
    const activeStatusHtml = isActive ? `
      <div class="info-grid" style="margin-top:0.5rem;">
        ${routeAttrs.origin ? `<div class="info-item"><span class="info-label">Start</span><span class="info-value">${this._esc(routeAttrs.origin)}</span></div>` : ''}
        <div class="info-item"><span class="info-label">Ziel</span><span class="info-value">${this._esc(routeAttrs.destination || '\u2014')}</span></div>
        <div class="info-item"><span class="info-label">Distanz</span><span class="info-value">${routeAttrs.total_distance_km != null ? routeAttrs.total_distance_km + ' km' : '\u2014'}</span></div>
        <div class="info-item"><span class="info-label">Korridor-Breite</span><span class="info-value">${routeAttrs.corridor_width_km != null ? routeAttrs.corridor_width_km + ' km' : '\u2014'}</span></div>
        ${predictedFuelStopEntity && predictedFuelStopEntity.state && predictedFuelStopEntity.state !== 'unknown' && predictedFuelStopEntity.state !== 'unavailable' ? `
        <div class="info-item"><span class="info-label">Vorhergesagter Tankstopp</span><span class="info-value">~${this._esc(predictedFuelStopEntity.state)} km voraus</span></div>` : ''}
      </div>` : '';
    const bestStationHtml = (isActive && corridorBestEntity && corridorBestEntity.state && corridorBestEntity.state !== 'unknown' && corridorBestEntity.state !== 'unavailable') ? `
      <div style="margin-top:0.75rem;padding:0.5rem;background:var(--secondary-background-color,#f5f5f5);border-radius:6px;">
        <div style="font-weight:600;margin-bottom:0.25rem;">\ud83c\udfc6 Beste Tankstelle im Korridor</div>
        <div class="info-grid" style="margin:0;">
          <div class="info-item"><span class="info-label">Tankstelle</span><span class="info-value">${this._esc(bestAttrs.station_name || '\u2014')}</span></div>
          <div class="info-item"><span class="info-label">Preis</span><span class="info-value">${bestAttrs.price_per_litre != null ? bestAttrs.price_per_litre + ' \u20ac/l' : '\u2014'}</span></div>
          <div class="info-item"><span class="info-label">Umweg</span><span class="info-value">${bestAttrs.detour_km != null ? bestAttrs.detour_km + ' km' : '\u2014'}</span></div>
          <div class="info-item"><span class="info-label">Effektivpreis</span><span class="info-value">${bestAttrs.effective_price_eur_per_l != null ? bestAttrs.effective_price_eur_per_l + ' \u20ac/l' : '\u2014'}</span></div>
        </div>
        <div style="margin-top:0.4rem;display:flex;gap:0.5rem;flex-wrap:wrap;">
          ${bestAttrs.google_maps_url ? `<a href="${this._esc(bestAttrs.google_maps_url)}" target="_blank" rel="noopener" style="font-size:0.8rem;">\ud83d\uddfa\ufe0f Google Maps</a>` : ''}
          ${bestAttrs.waze_url ? `<a href="${this._esc(bestAttrs.waze_url)}" target="_blank" rel="noopener" style="font-size:0.8rem;">\ud83d\ude97 Waze</a>` : ''}
          ${bestAttrs.apple_maps_url ? `<a href="${this._esc(bestAttrs.apple_maps_url)}" target="_blank" rel="noopener" style="font-size:0.8rem;">\ud83c\udf4e Apple Maps</a>` : ''}
        </div>
      </div>` : '';
    const topStationsHtml = (isActive && topStations.length > 1) ? `
      <div style="margin-top:0.75rem;">
        <div style="font-weight:600;margin-bottom:0.25rem;">\ud83d\udccb Top Tankstellen im Korridor</div>
        <table style="width:100%;font-size:0.8rem;border-collapse:collapse;">
          <thead><tr style="text-align:left;border-bottom:1px solid var(--divider-color,#ccc);">
            <th style="padding:2px 4px;">#</th><th style="padding:2px 4px;">Tankstelle</th><th style="padding:2px 4px;">Preis</th><th style="padding:2px 4px;">Umweg</th><th style="padding:2px 4px;">Eff. Preis</th>
          </tr></thead>
          <tbody>
            ${topStations.slice(0, 3).map((st, i) => `
              <tr style="border-bottom:1px solid var(--divider-color,#eee);">
                <td style="padding:2px 4px;">${i + 1}</td>
                <td style="padding:2px 4px;">${this._esc(st.name || '\u2014')}</td>
                <td style="padding:2px 4px;">${st.price != null ? st.price + ' \u20ac/l' : '\u2014'}</td>
                <td style="padding:2px 4px;">${st.detour_km != null ? st.detour_km + ' km' : '\u2014'}</td>
                <td style="padding:2px 4px;">${st.effective_price_eur_per_l != null ? st.effective_price_eur_per_l + ' \u20ac/l' : '\u2014'}</td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>` : '';
    return `${cancelBtnHtml}${activeBannerHtml}${activeStatusHtml}${bestStationHtml}${topStationsHtml}`;
  }

  _renderPlannedRoutesList() {
    const routes = this._plannedRoutes || [];
    if (!this._plannedRoutesLoaded) {
      return `<div style="font-size:0.85rem;color:var(--secondary-text-color,#888);">Geplante Routen werden geladen\u2026</div>`;
    }
    const rowsHtml = routes.length === 0
      ? `<div style="padding:0.5rem 0;font-size:0.85rem;color:var(--secondary-text-color,#888);">Keine geplanten Routen.</div>`
      : routes.map(r => {
          const waypointsStr = Array.isArray(r.waypoints) && r.waypoints.length ? r.waypoints.join(' \u2192 ') : (r.waypoints || '');
          const distanceStr = r.total_distance_km != null ? `${r.total_distance_km} km` : '\u2014';
          const createdStr = r.created_at ? r.created_at.replace('T', ' ').slice(0, 16) : '\u2014';
          const departureStr = r.departure_time ? r.departure_time.replace('T', ' ').slice(0, 16) : '\u2014';
          const routeJson = this._esc(JSON.stringify(r));
          const routeId = this._esc(String(r.route_id));
          return `<tr style="border-bottom:1px solid var(--divider-color,#eee);font-size:0.82rem;">
            <td style="padding:4px 6px;vertical-align:top;">
              <div style="font-weight:600;">${this._esc(r.destination || '\u2014')}</div>
              ${waypointsStr ? `<div style="font-size:0.78rem;color:var(--secondary-text-color,#888);">\u21aa ${this._esc(waypointsStr)}</div>` : ''}
              <div style="font-size:0.78rem;color:var(--secondary-text-color,#888);">Erstellt: ${createdStr}</div>
            </td>
            <td style="padding:4px 6px;white-space:nowrap;vertical-align:top;">${distanceStr}</td>
            <td style="padding:4px 6px;white-space:nowrap;vertical-align:top;">${departureStr}</td>
            <td style="padding:4px 6px;vertical-align:top;">
              <div style="display:flex;gap:4px;flex-wrap:wrap;">
                <button class="action-button" data-action="rp-route-edit" data-route-json="${routeJson}" title="In Formular laden" style="padding:2px 6px;font-size:0.78rem;">
                  <ha-icon icon="mdi:pencil" style="--mdi-icon-size:14px;"></ha-icon>
                </button>
                <button class="action-button activate-button" data-action="rp-route-activate" data-route-json="${routeJson}" title="Route jetzt starten" style="padding:2px 6px;font-size:0.78rem;">
                  <ha-icon icon="mdi:play" style="--mdi-icon-size:14px;"></ha-icon>
                </button>
                <button class="action-button delete-button" data-action="rp-route-delete" data-route-id="${routeId}" title="L\u00f6schen" style="padding:2px 6px;font-size:0.78rem;">
                  <ha-icon icon="mdi:delete" style="--mdi-icon-size:14px;"></ha-icon>
                </button>
              </div>
            </td>
          </tr>`;
        }).join('');
    return `
      <div style="font-weight:600;margin-bottom:0.4rem;">\ud83d\udccb Geplante Routen (${routes.length})</div>
      ${routes.length > 0 ? `
      <table style="width:100%;border-collapse:collapse;font-size:0.82rem;">
        <thead>
          <tr style="text-align:left;border-bottom:1px solid var(--divider-color,#ccc);font-size:0.78rem;color:var(--secondary-text-color,#888);">
            <th style="padding:2px 6px;">Ziel</th>
            <th style="padding:2px 6px;">Distanz</th>
            <th style="padding:2px 6px;">Abfahrt</th>
            <th style="padding:2px 6px;"></th>
          </tr>
        </thead>
        <tbody>${rowsHtml}</tbody>
      </table>` : rowsHtml}
    `;
  }

  _attachListeners() {
    const startBtn = this.shadowRoot.getElementById('rp-start-btn');
    if (startBtn) startBtn.addEventListener('click', () => this._handleRouteStart());
    const planBtn = this.shadowRoot.getElementById('rp-plan-btn');
    if (planBtn) planBtn.addEventListener('click', () => this._handleRoutePlan());
    const providerSelect = this.shadowRoot.getElementById('rp-provider');
    const googleKeyRow = this.shadowRoot.getElementById('rp-google-key-row');
    if (providerSelect && googleKeyRow) {
      const upd = () => { googleKeyRow.style.display = providerSelect.value === 'google' ? 'flex' : 'none'; };
      providerSelect.addEventListener('change', upd);
      upd();
    }
    this._attachPlannedRoutesListeners();
  }

  _attachPlannedRoutesListeners() {
    const section = this.shadowRoot.getElementById('rp-planned-routes-section');
    if (!section) return;
    // Remove old listener by cloning (simple dedup approach)
    const newSection = section.cloneNode(true);
    section.parentNode.replaceChild(newSection, section);
    newSection.id = 'rp-planned-routes-section';
    newSection.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      const action = btn.dataset.action;
      if (action === 'rp-route-edit') {
        try { this._editPlannedRoute(JSON.parse(btn.dataset.routeJson || '{}')); } catch (e) { console.error('FWCAM: edit route parse error', e); }
      } else if (action === 'rp-route-activate') {
        try { this._activatePlannedRoute(JSON.parse(btn.dataset.routeJson || '{}')); } catch (e) { console.error('FWCAM: activate route parse error', e); }
      } else if (action === 'rp-route-delete') {
        if (btn.dataset.routeId) this._deletePlannedRoute(btn.dataset.routeId);
      }
    });
  }

  _collectFormData() {
    const get = id => (this.shadowRoot.getElementById(id) || {}).value || '';
    const origin = get('rp-origin').trim();
    const destination = get('rp-destination').trim();
    const waypointsRaw = get('rp-waypoints').trim();
    const waypoints = waypointsRaw ? waypointsRaw.split(',').map(w => w.trim()).filter(Boolean) : [];
    const corridorWidth = parseFloat(get('rp-corridor')) || 5;
    const provider = get('rp-provider') || 'osrm';
    const googleApiKey = get('rp-google-key').trim();
    const departureDate = get('rp-departure-date');
    const departureTime = get('rp-departure-time');
    const departureTimeStr = (departureDate && departureTime) ? `${departureDate} ${departureTime}` : '';
    return { origin, destination, waypoints, corridorWidth, provider, googleApiKey, departureTimeStr };
  }

  async _handleRouteStart() {
    const fd = this._collectFormData();
    if (!fd.destination) { alert('Bitte eine Zieladresse eingeben.'); return; }
    const configEntryId = this._getConfigEntryId();
    const serviceData = { config_entry_id: configEntryId, destination: fd.destination, waypoints: fd.waypoints, corridor_width_km: fd.corridorWidth, routing_provider: fd.provider };
    if (fd.origin) serviceData.origin = fd.origin;
    if (fd.googleApiKey) serviceData.google_api_key = fd.googleApiKey;
    if (fd.departureTimeStr) serviceData.departure_time = fd.departureTimeStr;
    try {
      await this._hass.callService('hafwcma', 'set_route', serviceData);
      setTimeout(() => this._fetchPlannedRoutes(), 1500);
    } catch (err) {
      console.error('FWCAM Routenplanung: set_route failed', err);
      alert(`Route konnte nicht gestartet werden: ${err.message || err}`);
    }
  }

  async _handleRoutePlan() {
    const fd = this._collectFormData();
    if (!fd.destination) { alert('Bitte eine Zieladresse eingeben.'); return; }
    const configEntryId = this._getConfigEntryId();
    const serviceData = { config_entry_id: configEntryId, destination: fd.destination, waypoints: fd.waypoints, corridor_width_km: fd.corridorWidth, routing_provider: fd.provider };
    if (fd.origin) serviceData.origin = fd.origin;
    if (fd.googleApiKey) serviceData.google_api_key = fd.googleApiKey;
    if (fd.departureTimeStr) serviceData.departure_time = fd.departureTimeStr;
    try {
      await this._hass.callService('hafwcma', 'plan_route', serviceData);
      const destEl = this.shadowRoot.getElementById('rp-destination');
      if (destEl) destEl.value = '';
      setTimeout(() => this._fetchPlannedRoutes(), 1200);
    } catch (err) {
      console.error('FWCAM Routenplanung: plan_route failed', err);
      alert(`Route konnte nicht geplant werden: ${err.message || err}`);
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

  async _fetchPlannedRoutes() {
    const configEntryId = this._getConfigEntryId();
    if (!configEntryId) { this._plannedRoutesLoaded = true; this._updatePlannedRoutesList(); return; }
    try {
      const result = await this._hass.callService('hafwcma', 'get_saved_routes', { config_entry_id: configEntryId }, true);
      this._plannedRoutes = (result && Array.isArray(result.response?.routes)) ? result.response.routes : [];
    } catch (e) { console.error("FWCAM: get_saved_routes failed", e); this._plannedRoutes = []; }
    this._plannedRoutesLoaded = true;
    this._updatePlannedRoutesList();
  }

  async _deletePlannedRoute(routeId) {
    if (!confirm('Geplante Route wirklich l\u00f6schen?')) return;
    const configEntryId = this._getConfigEntryId();
    try {
      await this._hass.callService('hafwcma', 'delete_saved_route', { config_entry_id: configEntryId, route_id: routeId });
      await this._fetchPlannedRoutes();
    } catch (err) {
      console.error('FWCAM Routenplanung: delete_saved_route failed', err);
      alert(`Route konnte nicht gel\u00f6scht werden: ${err.message || err}`);
    }
  }

  _editPlannedRoute(route) {
    const set = (id, val) => { const el = this.shadowRoot.getElementById(id); if (el && val != null) el.value = val; };
    set('rp-destination', route.destination || '');
    set('rp-origin', route.origin || '');
    set('rp-waypoints', Array.isArray(route.waypoints) ? route.waypoints.join(', ') : (route.waypoints || ''));
    set('rp-corridor', route.corridor_width_km != null ? route.corridor_width_km : 5);
    const providerEl = this.shadowRoot.getElementById('rp-provider');
    if (providerEl && route.routing_provider) providerEl.value = route.routing_provider;
    if (route.departure_time) {
      const parts = route.departure_time.replace('T', ' ').split(' ');
      set('rp-departure-date', parts[0] || '');
      set('rp-departure-time', parts[1] ? parts[1].slice(0, 5) : '');
    }
    const formSection = this.shadowRoot.querySelector('.section');
    if (formSection) formSection.scrollIntoView({ behavior: 'smooth' });
  }

  async _activatePlannedRoute(route) {
    if (!confirm(`Route nach "${route.destination}" jetzt starten?`)) return;
    const configEntryId = this._getConfigEntryId();
    const serviceData = {
      config_entry_id: configEntryId,
      destination: route.destination || '',
      waypoints: Array.isArray(route.waypoints) ? route.waypoints : [],
      corridor_width_km: route.corridor_width_km || 5,
      routing_provider: route.routing_provider || 'osrm',
    };
    if (route.origin) serviceData.origin = route.origin;
    if (route.departure_time) serviceData.departure_time = route.departure_time;
    try {
      await this._hass.callService('hafwcma', 'set_route', serviceData);
    } catch (err) {
      console.error('FWCAM Routenplanung: activate planned route failed', err);
      alert(`Route konnte nicht gestartet werden: ${err.message || err}`);
    }
  }

  _getStyles() {
    return `<style>
      :host { display: block; }
      ha-card { padding: 16px; }
      .card-header { display:flex;justify-content:space-between;align-items:center;margin-bottom:16px; }
      .card-header .name { font-size:20px;font-weight:500;color:var(--primary-text-color); }
      .card-content { display:flex;flex-direction:column;gap:16px; }
      .section { border:1px solid var(--divider-color);border-radius:8px;padding:16px;background:var(--card-background-color); }
      .info-grid { display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px; }
      .info-item { display:flex;flex-direction:column;padding:6px 8px;background:var(--primary-background-color);border-radius:4px; }
      .info-label { font-size:0.75rem;font-weight:500;color:var(--secondary-text-color); }
      .info-value { font-size:0.9rem;font-weight:600;color:var(--primary-text-color); }
      .control-button { display:flex;flex-direction:row;align-items:center;gap:8px;padding:10px 16px;background:var(--primary-color);color:white;border:none;border-radius:8px;cursor:pointer;transition:opacity 0.2s;font-size:0.9rem; }
      .control-button:hover { opacity:0.88; }
      .control-button ha-icon { --mdc-icon-size:20px; }
      .plan-button { background:var(--success-color,#4caf50); }
      .cancel-button { background:var(--error-color,#d32f2f);color:white; }
      .action-button { background:var(--secondary-background-color,#f5f5f5);border:1px solid var(--divider-color,#ccc);border-radius:4px;cursor:pointer;color:var(--primary-text-color);display:flex;align-items:center;justify-content:center; }
      .action-button:hover { opacity:0.8; }
      .activate-button { color:var(--primary-color,#039be5); }
      .delete-button { color:var(--error-color,#d32f2f); }
      .setting-input { background:var(--primary-background-color);color:var(--primary-text-color); }
    </style>`;
  }

  static getStubConfig() {
    return { entity: 'sensor.my_car_refueling_log', title: '\ud83d\uddfa\ufe0f Routenplanung' };
  }
}

customElements.define('fwcam-routenplanung-card', FWCAMRoutePlannerCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'fwcam-routenplanung-card',
  name: 'FWCAM Routenplanung',
  description: 'Fuel Watcher Car Advanced Manager \u2013 Routenplanung mit Korridorsuche und Routenverwaltung',
  preview: false,
  documentationURL: 'https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/user_docs/ROUTENPLANUNG_ANLEITUNG_DE.md',
});
console.info(
  '%c FWCAM-ROUTENPLANUNG-CARD %c v2.0.0 ',
  'color: white; background: #039be5; font-weight: 700;',
  'color: #039be5; background: white; font-weight: 700;'
);
