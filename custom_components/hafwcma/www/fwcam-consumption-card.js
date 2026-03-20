/**
 * FWCAM Consumption Card (fwcam-consumption-card)
 *
 * Standalone Lovelace card showing consumption history chart.
 *
 * YAML example:
 *   type: custom:fwcam-consumption-card
 *   entity: sensor.my_car_refueling_log
 *   title: Kraftstoffverbrauch
 *
 * @version 1.0.0
 * @author northpower25
 * @license MIT
 */

class FWCAMConsumptionCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._innerCard = null;
    this._config = {};
  }

  setConfig(config) {
    if (!config.entity) throw new Error('fwcam-consumption-card: "entity" is required');
    this._config = config;
    if (this._innerCard) {
      this._innerCard.setConfig(this._buildInnerConfig());
    }
  }

  _buildInnerConfig() {
    return {
      entity: this._config.entity,
      title: this._config.title || '📊 Kraftstoffverbrauch',
      section_order: ['consumption_chart'],
      show_vehicle_info: false,
      show_refueling_log: false,
      show_trip_log: false,
      show_controls: false,
      show_settings: false,
      show_backup: false,
      show_price_chart: false,
      show_consumption_chart: true,
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

  getCardSize() { return 4; }

  static getStubConfig() {
    return { entity: 'sensor.my_car_refueling_log' };
  }
}

customElements.define('fwcam-consumption-card', FWCAMConsumptionCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'fwcam-consumption-card',
  name: 'FWCAM Kraftstoffverbrauch',
  description: 'Fuel Watcher Car Advanced Manager – Kraftstoffverbrauch',
  preview: false,
});

console.info(
  '%c FWCAM-CONSUMPTION-CARD %c v1.0.0 ',
  'color: white; background: #039be5; font-weight: 700;',
  'color: #039be5; background: white; font-weight: 700;'
);
