/**
 * FWCAM Trip Log Card (fwcam-trip-log-card)
 *
 * Standalone Lovelace card showing the trip log.
 *
 * YAML example:
 *   type: custom:fwcam-trip-log-card
 *   entity: sensor.my_car_refueling_log
 *   title: Reiseprotokoll
 *
 * @version 1.0.0
 * @author northpower25
 * @license MIT
 */

class FWCAMTripLogCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._innerCard = null;
    this._config = {};
  }

  setConfig(config) {
    if (!config.entity) throw new Error('fwcam-trip-log-card: "entity" is required');
    this._config = config;
    if (this._innerCard) {
      this._innerCard.setConfig(this._buildInnerConfig());
    }
  }

  _buildInnerConfig() {
    return {
      entity: this._config.entity,
      title: this._config.title || '🛣️ Reiseprotokoll',
      section_order: ['trip_log'],
      show_vehicle_info: false,
      show_refueling_log: false,
      show_trip_log: true,
      show_controls: false,
      show_settings: false,
      show_backup: false,
      show_price_chart: false,
      show_consumption_chart: false,
      show_cheapest_stations: false,
      show_top_destinations: false,
      show_map: false,
      show_route_planner: false,
    };
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._innerCard) {
      this._innerCard = document.createElement('fwcam-card');
      this.shadowRoot.appendChild(this._innerCard);
      this._innerCard.setConfig(this._buildInnerConfig());
    }
    this._innerCard.hass = hass;
  }

  getCardSize() { return 8; }

  static getStubConfig() {
    return { entity: 'sensor.my_car_refueling_log' };
  }
}

customElements.define('fwcam-trip-log-card', FWCAMTripLogCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'fwcam-trip-log-card',
  name: 'FWCAM Reiseprotokoll',
  description: 'Fuel Watcher Car Advanced Manager – Reiseprotokoll',
  preview: false,
});

console.info(
  '%c FWCAM-TRIP-LOG-CARD %c v1.0.0 ',
  'color: white; background: #039be5; font-weight: 700;',
  'color: #039be5; background: white; font-weight: 700;'
);
