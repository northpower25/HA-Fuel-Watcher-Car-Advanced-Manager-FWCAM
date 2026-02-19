/**
 * FWCAM Dashboard Panel
 *
 * Registers as a Home Assistant sidebar panel (panel_custom).
 * Automatically discovers all FWCAM vehicles from hass.states and
 * renders the fwcam-card for each vehicle.
 *
 * This file is served from /hafwcma_local/ and registered via
 * homeassistant.components.frontend.async_register_panel() in __init__.py.
 *
 * @version 1.0.0
 * @author northpower25
 * @license MIT
 */

const PANEL_ELEMENT_NAME = "fwcam-dashboard-panel";
const REFUELING_LOG_SUFFIX = "_refueling_log";
const FWCAM_CARD_ELEMENT = "fwcam-card";

class FWCAMDashboardPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._panel = null;
    this._selectedEntityId = null;
    this._vehicles = [];
    this._card = null;
    this._lastVehicleKey = "";
  }

  /**
   * Called by HA when the hass object is updated.
   * Discovers vehicles and re-renders if the vehicle list changed.
   */
  set hass(hass) {
    this._hass = hass;

    const vehicles = this._discoverVehicles(hass);
    const vehicleKey = vehicles.map((v) => v.entityId).join(",");

    if (vehicleKey !== this._lastVehicleKey) {
      this._lastVehicleKey = vehicleKey;
      this._vehicles = vehicles;

      // Keep selected vehicle if it still exists, otherwise pick first
      if (
        !this._selectedEntityId ||
        !vehicles.find((v) => v.entityId === this._selectedEntityId)
      ) {
        this._selectedEntityId = vehicles.length > 0 ? vehicles[0].entityId : null;
      }

      this._render();
    } else {
      // Just pass hass to the existing card
      this._updateCardHass(hass);
    }
  }

  set panel(panel) {
    this._panel = panel;
  }

  /**
   * Scan hass.states for sensor.*_refueling_log entities created by FWCAM.
   */
  _discoverVehicles(hass) {
    const vehicles = [];
    for (const [entityId, state] of Object.entries(hass.states)) {
      if (
        entityId.startsWith("sensor.") &&
        entityId.endsWith(REFUELING_LOG_SUFFIX)
      ) {
        const rawName = entityId
          .replace(/^sensor\./, "")
          .replace(new RegExp(`${REFUELING_LOG_SUFFIX}$`), "");

        // Use friendly_name from attributes, strip trailing " Refueling Log" / " Tankprotokoll"
        let displayName =
          (state.attributes && state.attributes.friendly_name) || rawName;
        displayName = displayName
          .replace(/\s+Refueling Log\s*$/i, "")
          .replace(/\s+Tankprotokoll\s*$/i, "")
          .trim();

        vehicles.push({ entityId, rawName, displayName });
      }
    }
    return vehicles.sort((a, b) =>
      a.displayName.localeCompare(b.displayName)
    );
  }

  _updateCardHass(hass) {
    if (this._card) {
      this._card.hass = hass;
    }
  }

  _selectVehicle(entityId) {
    if (this._selectedEntityId === entityId) return;
    this._selectedEntityId = entityId;
    this._render();
  }

  _escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  _render() {
    if (!this._hass) return;

    const styles = `
      :host {
        display: block;
        height: 100%;
        background-color: var(--primary-background-color);
        overflow-y: auto;
        box-sizing: border-box;
      }
      .panel-header {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        background-color: var(--app-header-background-color, var(--primary-color));
        color: var(--app-header-text-color, #fff);
      }
      .panel-header-icon {
        margin-right: 10px;
        --mdc-icon-size: 24px;
        color: inherit;
      }
      .panel-header h1 {
        margin: 0;
        font-size: 1.2rem;
        font-weight: 500;
        line-height: 1;
      }
      .vehicle-tabs {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        padding: 8px 16px;
        background-color: var(--card-background-color, #fff);
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
      }
      .vehicle-tab {
        padding: 6px 18px;
        border-radius: 20px;
        cursor: pointer;
        font-size: 0.875rem;
        font-family: inherit;
        background-color: var(--secondary-background-color, #f5f5f5);
        color: var(--primary-text-color, #212121);
        border: none;
        transition: background-color 0.15s, color 0.15s;
        outline: none;
      }
      .vehicle-tab:hover {
        background-color: var(--primary-color-light, #e3f2fd);
      }
      .vehicle-tab.selected {
        background-color: var(--primary-color, #03a9f4);
        color: var(--text-primary-color, #fff);
      }
      .panel-content {
        padding: 16px;
        max-width: 1400px;
        margin: 0 auto;
      }
      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 64px 16px;
        text-align: center;
        color: var(--secondary-text-color, #757575);
      }
      .empty-state .empty-icon {
        font-size: 64px;
        margin-bottom: 16px;
        opacity: 0.4;
      }
      .empty-state h2 {
        margin: 0 0 8px;
        font-size: 1.25rem;
        font-weight: 500;
        color: var(--primary-text-color, #212121);
      }
      .empty-state p {
        margin: 0;
        font-size: 0.875rem;
        max-width: 400px;
      }
    `;

    // --- Empty state ---
    if (this._vehicles.length === 0) {
      this.shadowRoot.innerHTML = `
        <style>${styles}</style>
        <div class="panel-header">
          <ha-icon class="panel-header-icon" icon="mdi:gas-station"></ha-icon>
          <h1>Fuel Watcher</h1>
        </div>
        <div class="empty-state">
          <div class="empty-icon">⛽</div>
          <h2>No FWCAM vehicles found</h2>
          <p>
            Please configure the Fuel Watcher Car Advanced Manager integration
            in <strong>Settings → Devices &amp; Services</strong>.
          </p>
        </div>
      `;
      this._card = null;
      return;
    }

    // --- Vehicle tabs (only when more than one vehicle) ---
    const tabsHtml =
      this._vehicles.length > 1
        ? `<div class="vehicle-tabs">
            ${this._vehicles
              .map(
                (v) => `
                <button
                  class="vehicle-tab${this._selectedEntityId === v.entityId ? " selected" : ""}"
                  data-entity-id="${this._escapeHtml(v.entityId)}"
                >${this._escapeHtml(v.displayName)}</button>
              `
              )
              .join("")}
           </div>`
        : "";

    this.shadowRoot.innerHTML = `
      <style>${styles}</style>
      <div class="panel-header">
        <ha-icon class="panel-header-icon" icon="mdi:gas-station"></ha-icon>
        <h1>Fuel Watcher</h1>
      </div>
      ${tabsHtml}
      <div class="panel-content">
        <${FWCAM_CARD_ELEMENT}></${FWCAM_CARD_ELEMENT}>
      </div>
    `;

    // --- Attach tab click listeners ---
    this.shadowRoot.querySelectorAll(".vehicle-tab").forEach((tab) => {
      tab.addEventListener("click", () =>
        this._selectVehicle(tab.dataset.entityId)
      );
    });

    // --- Configure the fwcam-card ---
    this._card = this.shadowRoot.querySelector(FWCAM_CARD_ELEMENT);
    if (this._card) {
      const vehicle =
        this._vehicles.find((v) => v.entityId === this._selectedEntityId) ||
        this._vehicles[0];
      try {
        this._card.setConfig({
          entity: vehicle.entityId,
          title: vehicle.displayName,
        });
      } catch (err) {
        // fwcam-card may not be defined yet (race condition on first load).
        // hass setter will retry via _updateCardHass on next update.
        console.warn("[FWCAM] fwcam-card not ready yet, will retry on next hass update:", err);
        this._card = null;
        return;
      }
      this._card.hass = this._hass;
    }
  }
}

customElements.define(PANEL_ELEMENT_NAME, FWCAMDashboardPanel);
