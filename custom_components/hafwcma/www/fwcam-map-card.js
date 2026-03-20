/**
 * FWCAM Fuelstation Map Card (fwcam-map-card)
 *
 * Standalone Lovelace card showing the interactive fuel station map.
 *
 * YAML example:
 *   type: custom:fwcam-map-card
 *   entity: sensor.my_car_refueling_log
 *   title: Tankstellenkarte
 *
 * @version 1.0.0
 * @author northpower25
 * @license MIT
 */

class FWCAMMapCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._innerCard = null;
    this._config = {};
  }

  setConfig(config) {
    if (!config.entity) throw new Error('fwcam-map-card: "entity" is required');
    this._config = config;
    if (this._innerCard) {
      this._innerCard.setConfig(this._buildInnerConfig());
    }
  }

  _buildInnerConfig() {
    return {
      entity: this._config.entity,
      title: this._config.title || '🗺️ Tankstellenkarte',
      section_order: ['map'],
      show_vehicle_info: false,
      show_refueling_log: false,
      show_trip_log: false,
      show_controls: false,
      show_settings: false,
      show_backup: false,
      show_price_chart: false,
      show_consumption_chart: false,
      show_cheapest_stations: false,
      show_top_destinations: false,
      show_map: true,
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

  getCardSize() { return 6; }

  static getStubConfig() {
    return { entity: 'sensor.my_car_refueling_log' };
  }
}

customElements.define('fwcam-map-card', FWCAMMapCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'fwcam-map-card',
  name: 'FWCAM Tankstellenkarte',
  description: 'Fuel Watcher Car Advanced Manager – Interaktive Tankstellenkarte',
  preview: false,
});

console.info(
  '%c FWCAM-MAP-CARD %c v1.0.0 ',
  'color: white; background: #039be5; font-weight: 700;',
  'color: #039be5; background: white; font-weight: 700;'
);
