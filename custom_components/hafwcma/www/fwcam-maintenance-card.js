/**
 * FWCAM Maintenance Card (fwcam-maintenance-card)
 *
 * Standalone Lovelace card with Controls, Settings, and Backup sections.
 *
 * YAML example:
 *   type: custom:fwcam-maintenance-card
 *   entity: sensor.my_car_refueling_log
 *   title: Wartung
 *
 * @version 1.0.0
 * @author northpower25
 * @license MIT
 */

class FWCAMMaintenanceCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._innerCard = null;
    this._config = {};
  }

  setConfig(config) {
    if (!config.entity) throw new Error('fwcam-maintenance-card: "entity" is required');
    this._config = config;
    if (this._innerCard) {
      this._innerCard.setConfig(this._buildInnerConfig());
    }
  }

  _buildInnerConfig() {
    return {
      entity: this._config.entity,
      title: this._config.title || '🔧 Wartung',
      section_order: ['controls', 'settings', 'backup'],
      show_vehicle_info: false,
      show_refueling_log: false,
      show_trip_log: false,
      show_controls: true,
      show_settings: true,
      show_backup: true,
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

customElements.define('fwcam-maintenance-card', FWCAMMaintenanceCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'fwcam-maintenance-card',
  name: 'FWCAM Wartung',
  description: 'Fuel Watcher Car Advanced Manager – Wartung (Steuerung, Einstellungen, Backup)',
  preview: false,
});

console.info(
  '%c FWCAM-MAINTENANCE-CARD %c v1.0.0 ',
  'color: white; background: #039be5; font-weight: 700;',
  'color: #039be5; background: white; font-weight: 700;'
);
