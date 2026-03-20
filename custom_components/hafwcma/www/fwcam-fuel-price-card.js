/**
 * FWCAM Fuel Price Development Card (fwcam-fuel-price-card)
 *
 * Standalone Lovelace card showing fuel price history charts.
 *
 * YAML example:
 *   type: custom:fwcam-fuel-price-card
 *   entity: sensor.my_car_refueling_log
 *   title: Kraftstoffpreisentwicklung
 *
 * @version 1.0.0
 * @author northpower25
 * @license MIT
 */

class FWCAMFuelPriceCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._innerCard = null;
    this._config = {};
  }

  setConfig(config) {
    if (!config.entity) throw new Error('fwcam-fuel-price-card: "entity" is required');
    this._config = config;
    if (this._innerCard) {
      this._innerCard.setConfig(this._buildInnerConfig());
    }
  }

  _buildInnerConfig() {
    return {
      entity: this._config.entity,
      title: this._config.title || '⛽ Kraftstoffpreisentwicklung',
      section_order: ['price_chart'],
      show_vehicle_info: false,
      show_refueling_log: false,
      show_trip_log: false,
      show_controls: false,
      show_settings: false,
      show_backup: false,
      show_price_chart: true,
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

  getCardSize() { return 5; }

  static getStubConfig() {
    return { entity: 'sensor.my_car_refueling_log' };
  }
}

customElements.define('fwcam-fuel-price-card', FWCAMFuelPriceCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'fwcam-fuel-price-card',
  name: 'FWCAM Kraftstoffpreisentwicklung',
  description: 'Fuel Watcher Car Advanced Manager – Kraftstoffpreisentwicklung',
  preview: false,
});

console.info(
  '%c FWCAM-FUEL-PRICE-CARD %c v1.0.0 ',
  'color: white; background: #039be5; font-weight: 700;',
  'color: #039be5; background: white; font-weight: 700;'
);
