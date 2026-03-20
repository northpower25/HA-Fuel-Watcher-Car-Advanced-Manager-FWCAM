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
const ROUTENPLANUNG_ELEMENT = "fwcam-routenplanung-card";
const VIEW_VEHICLE = "vehicle";
const VIEW_ROUTENPLANUNG = "routenplanung";
// Viewport width (px) below which the panel is considered narrow (matches HA's breakpoint)
const NARROW_VIEWPORT_BREAKPOINT = 870;

class FWCAMDashboardPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._panel = null;
    this._narrow = false;
    this._selectedEntityId = null;
    this._vehicles = [];
    this._card = null;
    this._activeView = VIEW_VEHICLE;
    this._lastVehicleKey = "";
    this._visibilityHandler = null;
  }

  /**
   * Called when the element is added to the DOM.
   * Registers the Page Visibility listener so the panel can recover
   * from a blank/black state when the user switches back to this tab.
   * Also proactively imports the routenplanung card module so the custom
   * element is registered before the user clicks the Routenplanung tab.
   */
  connectedCallback() {
    this._visibilityHandler = () => {
      if (!document.hidden && this._hass) {
        this._recoverIfBlank();
      }
    };
    document.addEventListener("visibilitychange", this._visibilityHandler);

    // Proactively load the routenplanung card module so that the custom
    // element is registered even when the panel module is the only entry
    // point (e.g. the first navigation after a hard-refresh).
    if (!customElements.get(ROUTENPLANUNG_ELEMENT)) {
      import("/hafwcma_local/fwcam-routenplanung-card.js").catch((e) => {
        console.warn("[FWCAM] Could not preload routenplanung card module:", e);
      });
    }

    // Fallback for the HA Companion App: if HA has not yet called the narrow
    // setter (or never will because of how the app bridges the panel element),
    // treat the viewport as narrow when its width is below HA's standard
    // breakpoint.  This ensures the hamburger menu button is always
    // visible on mobile/tablet devices regardless of how the app sets the flag.
    if (!this._narrow && typeof window !== "undefined" && window.innerWidth < NARROW_VIEWPORT_BREAKPOINT) {
      this._narrow = true;
    }

    // If hass was already set before we were connected, ensure the panel
    // is rendered (handles re-attachment to the DOM after a navigation).
    if (this._hass && !this.shadowRoot.querySelector(FWCAM_CARD_ELEMENT) &&
        !this.shadowRoot.querySelector(ROUTENPLANUNG_ELEMENT)) {
      this._render();
    }
  }

  /**
   * Called when the element is removed from the DOM.
   * Cleans up the Page Visibility listener to avoid memory leaks.
   */
  disconnectedCallback() {
    if (this._visibilityHandler) {
      document.removeEventListener("visibilitychange", this._visibilityHandler);
      this._visibilityHandler = null;
    }
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
   * HA sets `narrow` on panel_custom elements to indicate mobile/narrow mode.
   * Forwarding it to ha-menu-button makes the hamburger icon visible and
   * functional in the HA Companion App.
   *
   * We also set the attribute (in addition to the property) because
   * ha-menu-button's internal CSS relies on :host([narrow]) to toggle
   * visibility, and some Companion App WebView builds do not reflect
   * the property back to the attribute automatically.
   */
  set narrow(narrow) {
    this._narrow = narrow;
    const menuBtn = this.shadowRoot && this.shadowRoot.querySelector("ha-menu-button");
    this._applyMenuButtonState(menuBtn);
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
    // Use isConnected to detect a stale reference caused by shadow DOM replacement
    // (e.g. after tab switching, page hide/show, or navigation in the Companion App).
    if (this._card && this._card.isConnected) {
      this._card.hass = hass;
    } else if (
      (this._activeView === VIEW_VEHICLE && customElements.get(FWCAM_CARD_ELEMENT)) ||
      (this._activeView === VIEW_ROUTENPLANUNG && customElements.get(ROUTENPLANUNG_ELEMENT))
    ) {
      // The active card element is now registered (was not yet when _render() first ran),
      // or the card element was lost – re-render to restore the panel.
      this._render();
      return;
    }
    // Keep ha-menu-button in sync with latest hass so it can toggle sidebar
    const menuBtn = this.shadowRoot && this.shadowRoot.querySelector("ha-menu-button");
    this._applyMenuButtonState(menuBtn);
  }

  /**
   * Recover from a blank/black panel state that can occur when the user
   * switches browser tabs or the Companion App goes to the background.
   * Checks whether the shadow DOM still contains meaningful content and
   * forces a full re-render when the panel appears empty.
   */
  _recoverIfBlank() {
    const activeElement = this._activeView === VIEW_ROUTENPLANUNG
      ? this.shadowRoot && this.shadowRoot.querySelector(ROUTENPLANUNG_ELEMENT)
      : this.shadowRoot && this.shadowRoot.querySelector(FWCAM_CARD_ELEMENT);
    const cardConnected = activeElement && activeElement.isConnected;
    if (!cardConnected) {
      this._card = null;
      this._render();
    } else if (this._card && !this._card.isConnected) {
      this._card = null;
      this._render();
    }
  }

  _selectVehicle(entityId) {
    if (this._activeView === VIEW_VEHICLE && this._selectedEntityId === entityId) return;
    this._activeView = VIEW_VEHICLE;
    this._selectedEntityId = entityId;
    this._render();
  }

  _selectRoutenplanung() {
    if (this._activeView === VIEW_ROUTENPLANUNG) return;
    this._activeView = VIEW_ROUTENPLANUNG;
    this._render();
  }

  _escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /**
   * Apply the current hass object and narrow state to an ha-menu-button element.
   * Sets both the property AND the attribute so that the component's internal
   * :host([narrow]) CSS selector activates in all environments including the
   * HA Companion App WebView.
   */
  _applyMenuButtonState(menuBtn) {
    if (!menuBtn) return;
    menuBtn.hass = this._hass;
    menuBtn.narrow = this._narrow;
    if (this._narrow) {
      menuBtn.setAttribute("narrow", "");
    } else {
      menuBtn.removeAttribute("narrow");
    }
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
        padding: 0 4px 0 0;
        background-color: var(--app-header-background-color, var(--primary-color));
        color: var(--app-header-text-color, #fff);
        min-height: 48px;
      }
      .panel-header-icon {
        margin-right: 8px;
        --mdc-icon-size: 24px;
        color: inherit;
      }
      .panel-header h1 {
        margin: 0;
        font-size: 1.2rem;
        font-weight: 500;
        line-height: 1;
        flex: 1;
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
      .routenplanung-tab {
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
        margin-left: auto;
      }
      .routenplanung-tab:hover {
        background-color: var(--primary-color-light, #e3f2fd);
      }
      .routenplanung-tab.selected {
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
          <ha-menu-button></ha-menu-button>
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
      // Attach hass to menu button
      const menuBtn = this.shadowRoot.querySelector('ha-menu-button');
      this._applyMenuButtonState(menuBtn);
      this._card = null;
      return;
    }

    // --- Vehicle tabs (vehicle selection + Routenplanung tab) ---
    const vehicleTabsHtml = this._vehicles.length > 1
      ? this._vehicles
          .map(
            (v) => `
            <button
              class="vehicle-tab${this._activeView === VIEW_VEHICLE && this._selectedEntityId === v.entityId ? " selected" : ""}"
              data-entity-id="${this._escapeHtml(v.entityId)}"
            >${this._escapeHtml(v.displayName)}</button>
          `
          )
          .join("")
      : "";

    const tabsHtml = `
      <div class="vehicle-tabs">
        ${vehicleTabsHtml}
        <button
          class="routenplanung-tab${this._activeView === VIEW_ROUTENPLANUNG ? " selected" : ""}"
          data-view="routenplanung"
        >🗺️ Routenplanung</button>
      </div>`;

    // --- Determine which card element to render ---
    const cardElementTag = this._activeView === VIEW_ROUTENPLANUNG
      ? ROUTENPLANUNG_ELEMENT
      : FWCAM_CARD_ELEMENT;

    this.shadowRoot.innerHTML = `
      <style>${styles}</style>
      <div class="panel-header">
        <ha-menu-button></ha-menu-button>
        <ha-icon class="panel-header-icon" icon="mdi:gas-station"></ha-icon>
        <h1>Fuel Watcher</h1>
      </div>
      ${tabsHtml}
      <div class="panel-content">
        <${cardElementTag}></${cardElementTag}>
      </div>
    `;

    // Attach hass to the ha-menu-button so it can toggle the sidebar
    const menuBtn = this.shadowRoot.querySelector('ha-menu-button');
    this._applyMenuButtonState(menuBtn);

    // --- Attach vehicle tab click listeners ---
    this.shadowRoot.querySelectorAll(".vehicle-tab").forEach((tab) => {
      tab.addEventListener("click", () =>
        this._selectVehicle(tab.dataset.entityId)
      );
    });

    // --- Attach Routenplanung tab click listener ---
    const routenplanungBtn = this.shadowRoot.querySelector(".routenplanung-tab");
    if (routenplanungBtn) {
      routenplanungBtn.addEventListener("click", () => this._selectRoutenplanung());
    }

    // --- Configure the active card ---
    this._card = this.shadowRoot.querySelector(cardElementTag);
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
        // Card may not be defined yet (race condition on first load).
        // hass setter will retry via _updateCardHass on next update.
        console.warn(`[FWCAM] ${cardElementTag} not ready yet, will retry on next hass update:`, err);
        this._card = null;
        return;
      }
      this._card.hass = this._hass;
    }
  }
}

customElements.define(PANEL_ELEMENT_NAME, FWCAMDashboardPanel);
