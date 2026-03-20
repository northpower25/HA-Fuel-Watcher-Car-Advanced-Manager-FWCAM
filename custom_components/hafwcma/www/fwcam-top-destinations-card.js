/**
 * FWCAM Top 20 Trip Destinations Card (fwcam-top-destinations-card)
 *
 * Standalone Lovelace card showing the top 20 trip destinations.
 *
 * YAML example:
 *   type: custom:fwcam-top-destinations-card
 *   entity: sensor.my_car_refueling_log
 *   title: Top 20 Reiseziele
 *
 * @version 1.0.0
 * @author northpower25
 * @license MIT
 */

class FWCAMTopDestinationsCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._innerCard = null;
    this._config = {};
  }

  setConfig(config) {
    if (!config.entity) throw new Error('fwcam-top-destinations-card: "entity" is required');
    this._config = config;
    if (this._innerCard) {
      this._innerCard.setConfig(this._buildInnerConfig());
    }
  }

  _buildInnerConfig() {
    return {
      entity: this._config.entity,
      title: this._config.title || '🏁 Top 20 Reiseziele',
      section_order: ['top_destinations'],
      show_vehicle_info: false,
      show_refueling_log: false,
      show_trip_log: false,
      show_controls: false,
      show_settings: false,
      show_backup: false,
      show_price_chart: false,
      show_consumption_chart: false,
      show_cheapest_stations: false,
      show_top_destinations: true,
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

customElements.define('fwcam-top-destinations-card', FWCAMTopDestinationsCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'fwcam-top-destinations-card',
  name: 'FWCAM Top 20 Reiseziele',
  description: 'Fuel Watcher Car Advanced Manager – Top 20 Reiseziele',
  preview: false,
});

console.info(
  '%c FWCAM-TOP-DESTINATIONS-CARD %c v1.0.0 ',
  'color: white; background: #039be5; font-weight: 700;',
  'color: #039be5; background: white; font-weight: 700;'
);
