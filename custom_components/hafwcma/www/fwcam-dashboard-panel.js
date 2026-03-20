/**
 * FWCAM Dashboard Panel
 *
 * Registers as a Home Assistant sidebar panel (panel_custom).
 * Automatically discovers all FWCAM vehicles from hass.states and
 * renders the appropriate cards per vehicle tab and sub-tab.
 *
 * Features:
 * - Per-vehicle tabs
 * - Per-vehicle sub-tabs (Startseite, Routenplanung, Tankprotokoll, Reiseprotokoll, Wartung)
 * - User-configurable layout: add/remove/rename sub-tabs, add/remove/sort cards (drag & drop)
 * - Layout persisted per vehicle in localStorage
 *
 * @version 2.0.0
 * @author northpower25
 * @license MIT
 */

const PANEL_ELEMENT_NAME = "fwcam-dashboard-panel";
const REFUELING_LOG_SUFFIX = "_refueling_log";
const FWCAM_CARD_ELEMENT = "fwcam-card";
const NARROW_VIEWPORT_BREAKPOINT = 870;

// Available card types that can be placed on tabs
const AVAILABLE_CARDS = [
  { type: "fwcam-vehicle-info-card",       label: "🚗 Fahrzeuginformation",         defaultTitle: "Fahrzeuginformation" },
  { type: "fwcam-fuel-price-card",          label: "⛽ Kraftstoffpreisentwicklung",   defaultTitle: "Kraftstoffpreisentwicklung" },
  { type: "fwcam-consumption-card",         label: "📊 Kraftstoffverbrauch",          defaultTitle: "Kraftstoffverbrauch" },
  { type: "fwcam-cheapest-stations-card",   label: "🏆 Top 5 günstigste Tankstellen", defaultTitle: "Top 5 günstigste Tankstellen" },
  { type: "fwcam-map-card",                 label: "🗺️ Tankstellenkarte",            defaultTitle: "Tankstellenkarte" },
  { type: "fwcam-routenplanung-card",       label: "🗺️ Routenplanung",              defaultTitle: "Routenplanung" },
  { type: "fwcam-maintenance-card",         label: "🔧 Wartung",                     defaultTitle: "Wartung" },
  { type: "fwcam-refueling-log-card",       label: "📋 Tankprotokoll",              defaultTitle: "Tankprotokoll" },
  { type: "fwcam-trip-log-card",            label: "🛣️ Reiseprotokoll",             defaultTitle: "Reiseprotokoll" },
  { type: "fwcam-top-destinations-card",    label: "🏁 Top 20 Reiseziele",           defaultTitle: "Top 20 Reiseziele" },
];

const DEFAULT_TABS = [
  {
    id: "home",
    name: "Startseite",
    icon: "mdi:home",
    cards: [
      { type: "fwcam-fuel-price-card" },
      { type: "fwcam-map-card" },
      { type: "fwcam-top-destinations-card" },
      { type: "fwcam-vehicle-info-card" },
    ],
  },
  {
    id: "route",
    name: "Routenplanung",
    icon: "mdi:map-marker-path",
    cards: [{ type: "fwcam-routenplanung-card" }],
  },
  {
    id: "refuel",
    name: "Tankprotokoll",
    icon: "mdi:gas-station",
    cards: [{ type: "fwcam-refueling-log-card" }],
  },
  {
    id: "trips",
    name: "Reiseprotokoll",
    icon: "mdi:road",
    cards: [{ type: "fwcam-trip-log-card" }],
  },
  {
    id: "maintenance",
    name: "Wartung",
    icon: "mdi:wrench",
    cards: [{ type: "fwcam-maintenance-card" }],
  },
];

class FWCAMDashboardPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._panel = null;
    this._narrow = false;
    this._selectedVehicleEntityId = null;
    this._vehicles = [];
    this._lastVehicleKey = "";
    this._activeSubTabId = "home";
    // Map: vehicleEntityId → tabs config array
    this._vehicleLayouts = {};
    // Edit mode state
    this._editMode = false;
    this._editSelectedTabId = null;
    this._dragSrcTabId = null;
    this._dragSrcCardIndex = null;
    // Rendered card elements per tab slot
    this._cardElements = {};
    this._visibilityHandler = null;
  }

  connectedCallback() {
    this._visibilityHandler = () => {
      if (!document.hidden && this._hass) this._render();
    };
    document.addEventListener("visibilitychange", this._visibilityHandler);

    // Preload all standalone card modules
    const modules = [
      "fwcam-vehicle-info-card.js",
      "fwcam-fuel-price-card.js",
      "fwcam-consumption-card.js",
      "fwcam-cheapest-stations-card.js",
      "fwcam-map-card.js",
      "fwcam-routenplanung-card.js",
      "fwcam-maintenance-card.js",
      "fwcam-refueling-log-card.js",
      "fwcam-trip-log-card.js",
      "fwcam-top-destinations-card.js",
    ];
    modules.forEach((m) => {
      if (!customElements.get(m.replace(".js", ""))) {
        import(`/hafwcma_local/${m}`).catch((e) =>
          console.warn(`[FWCAM] Could not preload ${m}:`, e)
        );
      }
    });

    if (!this._narrow && typeof window !== "undefined" && window.innerWidth < NARROW_VIEWPORT_BREAKPOINT) {
      this._narrow = true;
    }

    if (this._hass && !this.shadowRoot.querySelector(".fwcam-panel-root")) {
      this._render();
    }
  }

  disconnectedCallback() {
    if (this._visibilityHandler) {
      document.removeEventListener("visibilitychange", this._visibilityHandler);
      this._visibilityHandler = null;
    }
  }

  set hass(hass) {
    this._hass = hass;
    const vehicles = this._discoverVehicles(hass);
    const vehicleKey = vehicles.map((v) => v.entityId).join(",");

    if (vehicleKey !== this._lastVehicleKey) {
      this._lastVehicleKey = vehicleKey;
      this._vehicles = vehicles;
      if (!this._selectedVehicleEntityId || !vehicles.find((v) => v.entityId === this._selectedVehicleEntityId)) {
        this._selectedVehicleEntityId = vehicles.length > 0 ? vehicles[0].entityId : null;
      }
      this._render();
    } else {
      this._updateCardsHass(hass);
    }
    const menuBtn = this.shadowRoot && this.shadowRoot.querySelector("ha-menu-button");
    this._applyMenuButtonState(menuBtn);
  }

  set panel(panel) { this._panel = panel; }

  set narrow(narrow) {
    this._narrow = narrow;
    const menuBtn = this.shadowRoot && this.shadowRoot.querySelector("ha-menu-button");
    this._applyMenuButtonState(menuBtn);
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Vehicle discovery & layout management
  // ──────────────────────────────────────────────────────────────────────────

  _discoverVehicles(hass) {
    const vehicles = [];
    for (const [entityId, state] of Object.entries(hass.states)) {
      if (entityId.startsWith("sensor.") && entityId.endsWith(REFUELING_LOG_SUFFIX)) {
        const rawName = entityId.replace(/^sensor\./, "").replace(new RegExp(`${REFUELING_LOG_SUFFIX}$`), "");
        let displayName = (state.attributes && state.attributes.friendly_name) || rawName;
        displayName = displayName.replace(/\s+Refueling Log\s*$/i, "").replace(/\s+Tankprotokoll\s*$/i, "").trim();
        vehicles.push({ entityId, rawName, displayName });
      }
    }
    return vehicles.sort((a, b) => a.displayName.localeCompare(b.displayName));
  }

  _getVehicleLayout(vehicleEntityId) {
    if (this._vehicleLayouts[vehicleEntityId]) return this._vehicleLayouts[vehicleEntityId];
    try {
      const stored = localStorage.getItem(`fwcam_dashboard_layout_${vehicleEntityId}`);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          this._vehicleLayouts[vehicleEntityId] = parsed;
          return parsed;
        }
      }
    } catch (_e) { /* ignore */ }
    // Deep-copy defaults
    const layout = JSON.parse(JSON.stringify(DEFAULT_TABS));
    this._vehicleLayouts[vehicleEntityId] = layout;
    return layout;
  }

  _saveVehicleLayout(vehicleEntityId) {
    try {
      localStorage.setItem(
        `fwcam_dashboard_layout_${vehicleEntityId}`,
        JSON.stringify(this._vehicleLayouts[vehicleEntityId])
      );
    } catch (_e) { /* ignore storage errors */ }
  }

  _getActiveTab() {
    if (!this._selectedVehicleEntityId) return null;
    const tabs = this._getVehicleLayout(this._selectedVehicleEntityId);
    return tabs.find((t) => t.id === this._activeSubTabId) || tabs[0] || null;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Helpers
  // ──────────────────────────────────────────────────────────────────────────

  _esc(str) {
    return String(str ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  _applyMenuButtonState(menuBtn) {
    if (!menuBtn) return;
    menuBtn.hass = this._hass;
    menuBtn.narrow = this._narrow;
    if (this._narrow) menuBtn.setAttribute("narrow", "");
    else menuBtn.removeAttribute("narrow");
  }

  _updateCardsHass(hass) {
    const content = this.shadowRoot.querySelector(".panel-content");
    if (!content) return;
    content.querySelectorAll("[data-fwcam-card]").forEach((el) => {
      if (el.hass !== undefined) el.hass = hass;
    });
    const menuBtn = this.shadowRoot.querySelector("ha-menu-button");
    this._applyMenuButtonState(menuBtn);
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Main render
  // ──────────────────────────────────────────────────────────────────────────

  _render() {
    if (!this._hass) return;

    const styles = this._getStyles();

    if (this._vehicles.length === 0) {
      this.shadowRoot.innerHTML = `
        <style>${styles}</style>
        <div class="fwcam-panel-root">
          <div class="panel-header">
            <ha-menu-button></ha-menu-button>
            <ha-icon class="panel-header-icon" icon="mdi:gas-station"></ha-icon>
            <h1>Fuel Watcher</h1>
          </div>
          <div class="empty-state">
            <div class="empty-icon">⛽</div>
            <h2>Kein FWCAM-Fahrzeug gefunden</h2>
            <p>Bitte die Fuel Watcher Car Advanced Manager Integration unter
              <strong>Einstellungen → Geräte &amp; Dienste</strong> konfigurieren.</p>
          </div>
        </div>`;
      this._applyMenuButtonState(this.shadowRoot.querySelector("ha-menu-button"));
      return;
    }

    const vehicleTabsHtml = this._vehicles.length > 1
      ? this._vehicles.map((v) => `
          <button class="vehicle-tab${this._selectedVehicleEntityId === v.entityId ? " selected" : ""}"
            data-vehicle-entity="${this._esc(v.entityId)}">${this._esc(v.displayName)}</button>`).join("")
      : "";

    const tabs = this._selectedVehicleEntityId ? this._getVehicleLayout(this._selectedVehicleEntityId) : [];
    const activeTab = this._getActiveTab();

    const subTabsHtml = tabs.map((tab) => `
      <button class="sub-tab${activeTab && activeTab.id === tab.id ? " selected" : ""}"
        data-sub-tab-id="${this._esc(tab.id)}">${this._esc(tab.name)}</button>`).join("");

    const contentHtml = this._renderTabContent(activeTab);
    const editPanelHtml = this._editMode ? this._renderEditPanel(tabs) : "";

    this.shadowRoot.innerHTML = `
      <style>${styles}</style>
      <div class="fwcam-panel-root">
        <div class="panel-header">
          <ha-menu-button></ha-menu-button>
          <ha-icon class="panel-header-icon" icon="mdi:gas-station"></ha-icon>
          <h1>Fuel Watcher${this._vehicles.length === 1 ? ` – ${this._esc(this._vehicles[0].displayName)}` : ""}</h1>
          ${this._selectedVehicleEntityId ? `
          <button class="edit-layout-btn${this._editMode ? " active" : ""}" data-action="toggle-edit">
            ${this._editMode ? "✅ Fertig" : "✏️ Layout bearbeiten"}
          </button>` : ""}
        </div>

        ${this._vehicles.length > 1 ? `<div class="vehicle-tabs">${vehicleTabsHtml}</div>` : ""}

        <div class="sub-tabs-bar">
          ${subTabsHtml}
        </div>

        ${this._editMode ? `<div class="edit-panel">${editPanelHtml}</div>` : ""}

        <div class="panel-content">
          ${contentHtml}
        </div>
      </div>`;

    this._applyMenuButtonState(this.shadowRoot.querySelector("ha-menu-button"));
    this._attachListeners();
    this._initCards();
  }

  _renderTabContent(activeTab) {
    if (!activeTab || !this._selectedVehicleEntityId) return "";
    return activeTab.cards.map((card, idx) => `
      <div class="card-slot" data-card-type="${this._esc(card.type)}" data-card-index="${idx}">
        <${this._esc(card.type)} data-fwcam-card="1"></${this._esc(card.type)}>
      </div>`).join("");
  }

  _renderEditPanel(tabs) {
    const activeTab = this._getActiveTab();
    const editTabId = this._editSelectedTabId || (activeTab ? activeTab.id : (tabs[0] ? tabs[0].id : null));
    const editTab = tabs.find((t) => t.id === editTabId) || tabs[0];

    // Tab list
    const tabListHtml = tabs.map((tab, idx) => `
      <div class="edit-tab-row${editTab && editTab.id === tab.id ? " selected" : ""}"
           draggable="true" data-drag-type="tab" data-tab-id="${this._esc(tab.id)}"
           data-tab-index="${idx}">
        <span class="drag-handle" title="Ziehen zum Sortieren">⠿</span>
        <span class="edit-tab-name" data-tab-id="${this._esc(tab.id)}">${this._esc(tab.name)}</span>
        <button class="edit-tab-select-btn" data-action="select-edit-tab" data-tab-id="${this._esc(tab.id)}" title="Karten bearbeiten">✏️</button>
        <button class="edit-tab-rename-btn" data-action="rename-tab" data-tab-id="${this._esc(tab.id)}" title="Umbenennen">📝</button>
        <button class="edit-tab-del-btn" data-action="delete-tab" data-tab-id="${this._esc(tab.id)}" title="Löschen">🗑️</button>
      </div>`).join("");

    // Card list for selected tab
    const cardListHtml = editTab ? editTab.cards.map((card, idx) => {
      const cardMeta = AVAILABLE_CARDS.find((c) => c.type === card.type) || { label: card.type };
      return `
        <div class="edit-card-row" draggable="true" data-drag-type="card"
             data-card-index="${idx}" data-tab-id="${this._esc(editTab.id)}">
          <span class="drag-handle" title="Ziehen zum Sortieren">⠿</span>
          <span class="edit-card-label">${this._esc(cardMeta.label)}</span>
          <button class="edit-card-del-btn" data-action="delete-card"
            data-tab-id="${this._esc(editTab.id)}" data-card-index="${idx}" title="Karte entfernen">🗑️</button>
        </div>`;
    }).join("") : "";

    // Available cards to add
    const currentCardTypes = editTab ? editTab.cards.map((c) => c.type) : [];
    const availableHtml = AVAILABLE_CARDS.map((card) => {
      const alreadyAdded = currentCardTypes.includes(card.type);
      return `
        <label class="available-card-item${alreadyAdded ? " added" : ""}">
          <input type="checkbox" data-action="toggle-card"
            data-tab-id="${editTab ? this._esc(editTab.id) : ""}"
            data-card-type="${this._esc(card.type)}"
            ${alreadyAdded ? "checked" : ""}>
          ${this._esc(card.label)}
        </label>`;
    }).join("");

    return `
      <div class="edit-panel-inner">
        <div class="edit-section">
          <h3>Reiter</h3>
          <div class="edit-tab-list" id="edit-tab-list">${tabListHtml}</div>
          <button class="edit-add-tab-btn" data-action="add-tab">+ Reiter hinzufügen</button>
        </div>
        <div class="edit-section">
          <h3>Karten für „${editTab ? this._esc(editTab.name) : "—"}"</h3>
          <div class="edit-card-list" id="edit-card-list">${cardListHtml}</div>
          <div class="available-cards-title">Verfügbare Karten:</div>
          <div class="available-cards">${availableHtml}</div>
        </div>
      </div>`;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Card initialization
  // ──────────────────────────────────────────────────────────────────────────

  _initCards() {
    const content = this.shadowRoot.querySelector(".panel-content");
    if (!content || !this._selectedVehicleEntityId) return;

    content.querySelectorAll("[data-fwcam-card]").forEach((cardEl) => {
      try {
        if (typeof cardEl.setConfig === "function") {
          cardEl.setConfig({ entity: this._selectedVehicleEntityId });
        }
        cardEl.hass = this._hass;
      } catch (e) {
        console.warn("[FWCAM Panel] Card init error:", cardEl.tagName, e);
      }
    });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Event listeners
  // ──────────────────────────────────────────────────────────────────────────

  _attachListeners() {
    const root = this.shadowRoot;

    // Vehicle tab clicks
    root.querySelectorAll(".vehicle-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        this._selectedVehicleEntityId = btn.dataset.vehicleEntity;
        this._activeSubTabId = this._getVehicleLayout(this._selectedVehicleEntityId)[0]?.id || "home";
        this._editMode = false;
        this._render();
      });
    });

    // Sub-tab clicks
    root.querySelectorAll(".sub-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        this._activeSubTabId = btn.dataset.subTabId;
        this._render();
      });
    });

    // Edit toggle
    const editBtn = root.querySelector("[data-action='toggle-edit']");
    if (editBtn) {
      editBtn.addEventListener("click", () => {
        this._editMode = !this._editMode;
        if (this._editMode) {
          const activeTab = this._getActiveTab();
          this._editSelectedTabId = activeTab ? activeTab.id : null;
        }
        this._render();
      });
    }

    if (!this._editMode) return;

    // Edit panel actions (delegated)
    const editPanel = root.querySelector(".edit-panel");
    if (!editPanel) return;

    editPanel.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-action]");
      if (!btn) return;
      const action = btn.dataset.action;

      if (action === "select-edit-tab") {
        this._editSelectedTabId = btn.dataset.tabId;
        this._render();
      } else if (action === "rename-tab") {
        const tabId = btn.dataset.tabId;
        const tabs = this._getVehicleLayout(this._selectedVehicleEntityId);
        const tab = tabs.find((t) => t.id === tabId);
        if (!tab) return;
        const newName = prompt("Neuer Name für den Reiter:", tab.name);
        if (newName && newName.trim()) {
          tab.name = newName.trim();
          this._saveVehicleLayout(this._selectedVehicleEntityId);
          this._render();
        }
      } else if (action === "delete-tab") {
        const tabId = btn.dataset.tabId;
        const tabs = this._getVehicleLayout(this._selectedVehicleEntityId);
        if (tabs.length <= 1) { alert("Mindestens ein Reiter ist erforderlich."); return; }
        if (!confirm("Diesen Reiter wirklich löschen?")) return;
        const idx = tabs.findIndex((t) => t.id === tabId);
        if (idx >= 0) tabs.splice(idx, 1);
        if (this._activeSubTabId === tabId) this._activeSubTabId = tabs[0]?.id || "home";
        if (this._editSelectedTabId === tabId) this._editSelectedTabId = tabs[0]?.id || null;
        this._saveVehicleLayout(this._selectedVehicleEntityId);
        this._render();
      } else if (action === "add-tab") {
        const name = prompt("Name des neuen Reiters:");
        if (!name || !name.trim()) return;
        const tabs = this._getVehicleLayout(this._selectedVehicleEntityId);
        const newId = `tab_${Date.now()}`;
        tabs.push({ id: newId, name: name.trim(), icon: "mdi:tab", cards: [] });
        this._editSelectedTabId = newId;
        this._saveVehicleLayout(this._selectedVehicleEntityId);
        this._render();
      } else if (action === "delete-card") {
        const tabId = btn.dataset.tabId;
        const cardIndex = parseInt(btn.dataset.cardIndex, 10);
        const tabs = this._getVehicleLayout(this._selectedVehicleEntityId);
        const tab = tabs.find((t) => t.id === tabId);
        if (tab && !isNaN(cardIndex)) {
          tab.cards.splice(cardIndex, 1);
          this._saveVehicleLayout(this._selectedVehicleEntityId);
          this._render();
        }
      }
    });

    // Checkbox toggles for adding/removing cards
    editPanel.addEventListener("change", (e) => {
      const cb = e.target.closest("input[data-action='toggle-card']");
      if (!cb) return;
      const tabId = cb.dataset.tabId;
      const cardType = cb.dataset.cardType;
      const tabs = this._getVehicleLayout(this._selectedVehicleEntityId);
      const tab = tabs.find((t) => t.id === tabId);
      if (!tab) return;
      if (cb.checked) {
        if (!tab.cards.find((c) => c.type === cardType)) {
          tab.cards.push({ type: cardType });
        }
      } else {
        const idx = tab.cards.findIndex((c) => c.type === cardType);
        if (idx >= 0) tab.cards.splice(idx, 1);
      }
      this._saveVehicleLayout(this._selectedVehicleEntityId);
      this._render();
    });

    // Drag & drop for tabs
    this._attachDragListeners(editPanel, "tab");
    // Drag & drop for cards
    this._attachDragListeners(editPanel, "card");
  }

  _attachDragListeners(container, dragType) {
    const selector = `[data-drag-type="${dragType}"]`;
    let dragSrc = null;

    container.querySelectorAll(selector).forEach((row) => {
      row.addEventListener("dragstart", (e) => {
        dragSrc = row;
        e.dataTransfer.effectAllowed = "move";
        row.classList.add("dragging");
      });
      row.addEventListener("dragend", () => {
        row.classList.remove("dragging");
        container.querySelectorAll(selector).forEach((r) => r.classList.remove("drag-over"));
        dragSrc = null;
      });
      row.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        if (row !== dragSrc) row.classList.add("drag-over");
      });
      row.addEventListener("dragleave", () => row.classList.remove("drag-over"));
      row.addEventListener("drop", (e) => {
        e.stopPropagation();
        row.classList.remove("drag-over");
        if (!dragSrc || dragSrc === row) return;

        const tabs = this._getVehicleLayout(this._selectedVehicleEntityId);

        if (dragType === "tab") {
          const srcId = dragSrc.dataset.tabId;
          const dstId = row.dataset.tabId;
          const srcIdx = tabs.findIndex((t) => t.id === srcId);
          const dstIdx = tabs.findIndex((t) => t.id === dstId);
          if (srcIdx >= 0 && dstIdx >= 0) {
            const [moved] = tabs.splice(srcIdx, 1);
            tabs.splice(dstIdx, 0, moved);
          }
        } else if (dragType === "card") {
          const tabId = dragSrc.dataset.tabId;
          const srcIdx = parseInt(dragSrc.dataset.cardIndex, 10);
          const dstIdx = parseInt(row.dataset.cardIndex, 10);
          const tab = tabs.find((t) => t.id === tabId);
          if (tab && !isNaN(srcIdx) && !isNaN(dstIdx)) {
            const [moved] = tab.cards.splice(srcIdx, 1);
            tab.cards.splice(dstIdx, 0, moved);
          }
        }

        this._saveVehicleLayout(this._selectedVehicleEntityId);
        this._render();
      });
    });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Styles
  // ──────────────────────────────────────────────────────────────────────────

  _getStyles() {
    return `
      :host { display: block; height: 100%; }
      * { box-sizing: border-box; }

      .fwcam-panel-root {
        display: flex;
        flex-direction: column;
        height: 100%;
        background-color: var(--primary-background-color);
        overflow-y: auto;
      }

      /* ── Header ── */
      .panel-header {
        display: flex;
        align-items: center;
        padding: 0 8px 0 0;
        background-color: var(--app-header-background-color, var(--primary-color));
        color: var(--app-header-text-color, #fff);
        min-height: 48px;
        gap: 4px;
        flex-shrink: 0;
      }
      .panel-header-icon { --mdc-icon-size: 24px; color: inherit; }
      .panel-header h1 {
        margin: 0; font-size: 1.1rem; font-weight: 500; flex: 1;
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      }
      .edit-layout-btn {
        padding: 5px 12px; border-radius: 16px; border: 1.5px solid rgba(255,255,255,0.7);
        background: transparent; color: white; cursor: pointer; font-size: 0.8rem;
        white-space: nowrap; transition: background 0.15s;
      }
      .edit-layout-btn:hover { background: rgba(255,255,255,0.15); }
      .edit-layout-btn.active { background: rgba(255,255,255,0.25); border-color: white; }

      /* ── Vehicle tabs ── */
      .vehicle-tabs {
        display: flex; flex-wrap: wrap; gap: 6px; padding: 8px 16px;
        background-color: var(--card-background-color, #fff);
        border-bottom: 1px solid var(--divider-color, #e0e0e0); flex-shrink: 0;
      }
      .vehicle-tab {
        padding: 5px 14px; border-radius: 16px; cursor: pointer; font-size: 0.85rem;
        font-family: inherit; background: var(--secondary-background-color, #f5f5f5);
        color: var(--primary-text-color); border: none; transition: background 0.15s;
      }
      .vehicle-tab:hover { background: var(--primary-color-light, #e3f2fd); }
      .vehicle-tab.selected { background: var(--primary-color); color: var(--text-primary-color, #fff); }

      /* ── Sub-tabs ── */
      .sub-tabs-bar {
        display: flex; flex-wrap: wrap; gap: 4px; padding: 6px 16px;
        background-color: var(--card-background-color, #fff);
        border-bottom: 1px solid var(--divider-color, #e0e0e0); flex-shrink: 0;
      }
      .sub-tab {
        padding: 5px 14px; border-radius: 16px; cursor: pointer; font-size: 0.85rem;
        font-family: inherit; background: var(--secondary-background-color, #f5f5f5);
        color: var(--primary-text-color); border: none; transition: background 0.15s;
      }
      .sub-tab:hover { background: var(--primary-color-light, #e3f2fd); }
      .sub-tab.selected {
        background: var(--primary-color); color: var(--text-primary-color, #fff);
        font-weight: 500;
      }

      /* ── Edit panel ── */
      .edit-panel {
        background: var(--secondary-background-color, #f5f5f5);
        border-bottom: 2px solid var(--primary-color); padding: 12px 16px; flex-shrink: 0;
      }
      .edit-panel-inner { display: flex; gap: 24px; flex-wrap: wrap; }
      .edit-section { flex: 1; min-width: 260px; }
      .edit-section h3 { margin: 0 0 8px; font-size: 0.95rem; font-weight: 600; }

      .edit-tab-list, .edit-card-list { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
      .edit-tab-row, .edit-card-row {
        display: flex; align-items: center; gap: 6px; padding: 6px 8px;
        background: var(--card-background-color, #fff); border-radius: 6px;
        border: 1px solid var(--divider-color, #ddd); cursor: default; user-select: none;
      }
      .edit-tab-row.selected { border-color: var(--primary-color); background: var(--primary-color-light, #e3f2fd); }
      .edit-tab-row.dragging, .edit-card-row.dragging { opacity: 0.4; }
      .edit-tab-row.drag-over, .edit-card-row.drag-over { border-color: var(--primary-color); background: var(--primary-color-light, #e3f2fd); }
      .drag-handle { cursor: grab; color: var(--secondary-text-color); font-size: 1.1rem; }
      .edit-tab-name, .edit-card-label { flex: 1; font-size: 0.88rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .edit-tab-select-btn, .edit-tab-rename-btn, .edit-tab-del-btn,
      .edit-card-del-btn {
        background: none; border: none; cursor: pointer; padding: 2px 4px; font-size: 0.85rem;
        border-radius: 4px; transition: background 0.1s; flex-shrink: 0;
      }
      .edit-tab-select-btn:hover, .edit-tab-rename-btn:hover { background: var(--primary-color-light, #e3f2fd); }
      .edit-tab-del-btn:hover, .edit-card-del-btn:hover { background: var(--error-color, #fde8e8); }

      .edit-add-tab-btn {
        padding: 5px 12px; border-radius: 6px; background: var(--primary-color);
        color: white; border: none; cursor: pointer; font-size: 0.85rem; margin-top: 4px;
      }
      .edit-add-tab-btn:hover { opacity: 0.88; }

      .available-cards-title { font-size: 0.85rem; font-weight: 600; margin: 8px 0 4px; }
      .available-cards { display: flex; flex-wrap: wrap; gap: 6px; }
      .available-card-item {
        display: flex; align-items: center; gap: 4px; padding: 4px 8px;
        background: var(--card-background-color, #fff); border-radius: 6px;
        border: 1px solid var(--divider-color, #ddd); cursor: pointer; font-size: 0.82rem;
        transition: border-color 0.1s;
      }
      .available-card-item.added { border-color: var(--primary-color); }
      .available-card-item input { margin: 0; cursor: pointer; }

      /* ── Content area ── */
      .panel-content {
        padding: 16px; max-width: 1400px; margin: 0 auto; width: 100%;
        display: flex; flex-direction: column; gap: 16px;
      }
      .card-slot { width: 100%; }

      /* ── Empty state ── */
      .empty-state {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; padding: 64px 16px; text-align: center;
        color: var(--secondary-text-color);
      }
      .empty-icon { font-size: 64px; margin-bottom: 16px; opacity: 0.4; }
      .empty-state h2 { margin: 0 0 8px; font-size: 1.25rem; font-weight: 500; color: var(--primary-text-color); }
      .empty-state p { margin: 0; font-size: 0.875rem; max-width: 400px; }
    `;
  }
}

customElements.define(PANEL_ELEMENT_NAME, FWCAMDashboardPanel);
