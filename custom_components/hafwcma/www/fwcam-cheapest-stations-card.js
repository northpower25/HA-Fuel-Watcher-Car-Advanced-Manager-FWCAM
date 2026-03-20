/**
 * FWCAM Cheapest Stations Card (fwcam-cheapest-stations-card)
 *
 * Standalone Lovelace card showing top 5 cheapest fuel stations.
 *
 * YAML example:
 *   type: custom:fwcam-cheapest-stations-card
 *   entity: sensor.my_car_refueling_log
 *   title: Top 5 günstigste Tankstellen
 *
 * @version 1.0.0
 * @author northpower25
 * @license MIT
 */

class FWCAMCheapestStationsCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._innerCard = null;
    this._config = {};
  }

  setConfig(config) {
    if (!config.entity) throw new Error('fwcam-cheapest-stations-card: "entity" is required');
    this._config = config;
    if (this._innerCard) {
      this._innerCard.setConfig(this._buildInnerConfig());
    }
  }

  _buildInnerConfig() {
    return {
      entity: this._config.entity,
      title: this._config.title || '🏆 Top 5 günstigste Tankstellen',
      section_order: ['cheapest_stations'],
      show_vehicle_info: false,
      show_refueling_log: false,
      show_trip_log: false,
      show_controls: false,
      show_settings: false,
      show_backup: false,
      show_price_chart: false,
      show_consumption_chart: false,
      show_cheapest_stations: true,
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

customElements.define('fwcam-cheapest-stations-card', FWCAMCheapestStationsCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'fwcam-cheapest-stations-card',
  name: 'FWCAM Top 5 günstigste Tankstellen',
  description: 'Fuel Watcher Car Advanced Manager – Top 5 günstigste Tankstellen',
  preview: false,
});

console.info(
  '%c FWCAM-CHEAPEST-STATIONS-CARD %c v1.0.0 ',
  'color: white; background: #039be5; font-weight: 700;',
  'color: #039be5; background: white; font-weight: 700;'
);
