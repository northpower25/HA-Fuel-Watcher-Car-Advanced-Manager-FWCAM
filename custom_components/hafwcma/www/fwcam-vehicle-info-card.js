/**
 * FWCAM Vehicle Information Card (fwcam-vehicle-info-card)
 *
 * Standalone Lovelace card showing vehicle information only.
 * Wraps the main fwcam-card with vehicle_info section enabled.
 *
 * YAML example:
 *   type: custom:fwcam-vehicle-info-card
 *   entity: sensor.my_car_refueling_log
 *   title: Fahrzeuginformation
 *
 * @version 1.0.0
 * @author northpower25
 * @license MIT
 */

class FWCAMVehicleInfoCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._innerCard = null;
    this._config = {};
  }

  setConfig(config) {
    if (!config.entity) throw new Error('fwcam-vehicle-info-card: "entity" is required');
    this._config = config;
    if (this._innerCard) {
      this._innerCard.setConfig(this._buildInnerConfig());
    }
  }

  _buildInnerConfig() {
    return {
      entity: this._config.entity,
      title: this._config.title || '🚗 Fahrzeuginformation',
      section_order: ['vehicle_info'],
      show_vehicle_info: true,
      show_refueling_log: false,
      show_trip_log: false,
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

  getCardSize() { return 3; }

  static getStubConfig() {
    return { entity: 'sensor.my_car_refueling_log' };
  }
}

customElements.define('fwcam-vehicle-info-card', FWCAMVehicleInfoCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'fwcam-vehicle-info-card',
  name: 'FWCAM Fahrzeuginformation',
  description: 'Fuel Watcher Car Advanced Manager – Fahrzeuginformation',
  preview: false,
});

console.info(
  '%c FWCAM-VEHICLE-INFO-CARD %c v1.0.0 ',
  'color: white; background: #039be5; font-weight: 700;',
  'color: #039be5; background: white; font-weight: 700;'
);
