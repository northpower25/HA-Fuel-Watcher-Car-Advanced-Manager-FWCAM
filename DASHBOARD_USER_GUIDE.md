# FWCAM Dashboard System - Benutzeranleitung / User Guide

## 🎯 Zusammenfassung / Summary

Dieses System implementiert ein umfassendes Dashboard für die FWCAM-Integration mit automatischem Sidebar-Panel, vorgefertigten YAML-Vorlagen und ausführlicher Dokumentation.

This system implements a comprehensive dashboard for the FWCAM integration with an automatic sidebar panel, ready-to-use YAML templates, and extensive documentation.

---

## 🚀 Was wurde implementiert / What Was Implemented

### 1. Automatisches Sidebar-Panel / Automatic Sidebar Panel (NEU / NEW)

✅ **Zero-Konfiguration – kein YAML erforderlich / Zero-configuration – no YAML required**

Nach der Installation erscheint **"Fuel Watcher"** automatisch in der Seitenleiste.
After installation, **"Fuel Watcher"** appears automatically in the sidebar.

- Erkennt alle FWCAM-Fahrzeuge automatisch / Auto-discovers all FWCAM vehicles
- Fahrzeug-Tabs bei mehreren Fahrzeugen / Vehicle tabs for multiple vehicles
- Vollständige `fwcam-card` eingebettet / Full `fwcam-card` embedded

### 2. Dashboard-Vorlagen / Dashboard Templates (Fallback)

#### Übersichts-Dashboard / Overview Dashboard
📁 `dashboards/fwcam-overview-dashboard.yaml`

**Für mehrere Fahrzeuge / For multiple vehicles**
- 5 Ansichten: Übersicht, Kraftstoffpreise, Fahrten, Einstellungen, Debug
- 5 views: Overview, Fuel Prices, Trips, Settings, Debug

#### Fahrzeug-Dashboard / Per-Vehicle Dashboard
📁 `dashboards/fwcam-vehicle-dashboard-template.yaml`

**Für detaillierte Fahrzeugverwaltung / For detailed vehicle management**
- 6 Ansichten: Übersicht, Tankprotokoll, Fahrtenbuch, Statistiken, Einstellungen, Debug
- 6 views: Overview, Refueling Log, Trip Log, Statistics, Settings, Debug

### 3. Hilfe-Module / Helper Modules

#### Hilfe-Inhalte / Help Content
📁 `custom_components/hafwcma/www/fwcam-card-help.js`

- Zweisprachig (Deutsch/Englisch) / Bilingual (German/English)
- Hilfe für alle Entitäten / Help for all entities

#### Hilfsfunktionen / Helper Functions
📁 `custom_components/hafwcma/www/fwcam-card-helpers.js`

- Wiederverwendbare UI-Komponenten / Reusable UI components
- Formatierungsfunktionen / Formatting functions

### 4. Dokumentation / Documentation

📁 `dashboards/DASHBOARD_INSTALLATION_GUIDE.md` – Installationsanleitung / Installation guide

---

## 📋 Installation - Schnellstart / Quick Start

### ⭐ Option 1: Automatisches Sidebar-Panel (Empfohlen / Recommended)

**Keine Schritte erforderlich! / No steps required!**

1. FWCAM-Integration installieren / Install FWCAM integration
2. Mindestens ein Fahrzeug konfigurieren / Configure at least one vehicle
3. ✅ **"Fuel Watcher" erscheint automatisch in der Seitenleiste / appears automatically in the sidebar**

---

### Option 2: Übersichts-Dashboard (Mehrere Fahrzeuge / Multiple Vehicles)

**YAML-Fallback:**

1. **Datei öffnen / Open file:**
   - `dashboards/fwcam-overview-dashboard.yaml`

2. **YAML kopieren / Copy YAML:**
   - Gesamten Inhalt kopieren / Copy entire content

3. **Dashboard erstellen / Create dashboard:**
   - Einstellungen → Dashboards / Settings → Dashboards
   - "+ DASHBOARD HINZUFÜGEN" / "+ ADD DASHBOARD"

4. **YAML einfügen / Paste YAML:**
   - Dashboard bearbeiten → Raw-Konfigurations-Editor
   - Edit Dashboard → Raw configuration editor
   - YAML einfügen / Paste YAML

5. **Anpassen / Customize:**
   - `YOUR_CAR_NAME` durch Ihren Fahrzeugnamen ersetzen
   - Replace `YOUR_CAR_NAME` with your vehicle name
   - Speichern / Save

### Option 3: Fahrzeug-Dashboard (Ein Fahrzeug, detailliert)

**Gleicher Prozess mit / Same process with:**
- `dashboards/fwcam-vehicle-dashboard-template.yaml`

---

## ⚙️ Anpassung / Customization

### Fahrzeugnamen finden / Find Vehicle Names

Ihre Entitäts-IDs basieren auf Ihrem Fahrzeugnamen:

Your entity IDs are based on your vehicle name:

**Beispiel / Example:**
- Fahrzeugname / Vehicle name: "Mein VW Golf" → `vw_golf`
- Entitäten / Entities: `sensor.vw_golf_fuel_price`, `sensor.vw_golf_tank_level`

**So finden Sie sie / How to find them:**
1. Entwicklerwerkzeuge → Zustände / Developer Tools → States
2. Suchen nach / Search for: `sensor.` + Ihr Fahrzeugname
3. Notieren Sie das exakte Format / Note the exact format

### Häufige Anpassungen / Common Customizations

#### Messbereiche anpassen / Adjust Gauge Ranges
```yaml
- type: gauge
  entity: sensor.vw_golf_tank_level
  min: 0
  max: 100  # An Ihren Tank anpassen / Adjust to your tank
```

#### Weitere Fahrzeuge hinzufügen / Add More Vehicles
- Fahrzeug-Abschnitt kopieren / Copy vehicle section
- Entitätsnamen ändern / Change entity names
- Titel aktualisieren / Update title

#### Verlaufs-Zeiträume ändern / Change History Time Ranges
```yaml
hours_to_show: 168  # Ändern Sie diese Zahl / Change this number
# 24 = 1 Tag / day
# 168 = 1 Woche / week
# 720 = 1 Monat / month
```

---

## 🎨 Funktionen / Features

### Sidebar-Panel Features

**Fahrzeugübersicht / Vehicle Overview:**
- Automatische Fahrzeugerkennung / Automatic vehicle detection
- Tab-Navigation bei mehreren Fahrzeugen / Tab navigation for multiple vehicles
- Vollständige fwcam-card eingebettet / Full fwcam-card embedded

### Übersichts-Dashboard Features

**Übersichts-Ansicht / Overview View:**
- Alle Fahrzeuge auf einen Blick / All vehicles at a glance
- Tankempfehlungen / Refueling recommendations
- Tankfüllstände / Tank levels
- Aktuelle Preise / Current prices

**Kraftstoffpreis-Ansicht / Fuel Price View:**
- Preisvergleich / Price comparison
- Verlaufsdiagramme / History graphs
- Günstige Tankstellen / Cheap stations

**Fahrten-Ansicht / Trip View:**
- Fahrtenstatistiken / Trip statistics
- Alle Fahrzeuge / All vehicles

**Einstellungen-Ansicht / Settings View:**
- Zentrale Konfiguration / Central configuration
- Alle Einstellungen pro Fahrzeug / All settings per vehicle

**Debug-Ansicht / Debug View:**
- Technische Informationen / Technical information
- Fehlerbehebung / Troubleshooting

### Fahrzeug-Dashboard Features

**Übersichts-Ansicht / Overview View:**
- Tankfüllstand-Anzeigen / Tank level gauges
- Verbrauchsanzeigen / Consumption gauges
- Reichweitenanzeige / Range display
- Tankempfehlungen mit Dringlichkeit / Refueling recommendations with urgency
- Günstige Tankstellen in der Nähe / Nearby cheap stations

**Tankprotokoll-Ansicht / Refueling Log View:**
- FWCAM-Karte mit voller CRUD-Funktionalität / FWCAM card with full CRUD
- Tankhistorie bearbeiten / Edit refueling history
- Telegram-Integration / Telegram integration
- Statistiken / Statistics

**Fahrtenbuch-Ansicht / Trip Log View:**
- FWCAM-Karte für Fahrten / FWCAM card for trips
- Kategorisierung (Geschäftlich/Privat/Pendeln) / Categorization
- Geocodierung / Geocoding
- Kartenvorschau / Map preview

**Statistik-Ansicht / Statistics View:**
- Verbrauchsverlauf / Consumption history
- Preisverlauf / Price history
- Tankfüllstandsverlauf / Tank level history
- Verbrauchsprognose / Consumption forecast

**Einstellungen-Ansicht / Settings View:**
- Alle Zahlen-Entitäten / All number entities
- Schalter / Switches
- Schaltflächen / Buttons
- Inline-Bearbeitung / Inline editing

**Debug-Ansicht / Debug View:**
- API-Debug-Informationen / API debug information
- Fahrzeugdaten-Debug / Car data debug
- Telegram-Bot-Status / Telegram bot status

---

## 🆘 Fehlerbehebung / Troubleshooting

### Sidebar-Panel nicht sichtbar / Sidebar panel not visible

**Problem:** "Fuel Watcher" fehlt in der Seitenleiste / missing from sidebar

**Lösung / Solution:**
1. Home Assistant neu starten / Restart Home Assistant
2. FWCAM korrekt installiert und konfiguriert? / FWCAM installed and configured?
3. Browser-Cache leeren (Ctrl+Shift+R) / Clear browser cache

### "Entität nicht gefunden" / "Entity not found"

**Problem:** Entitäten werden als "nicht verfügbar" angezeigt

**Lösung / Solution:**
1. Entitätsnamen überprüfen / Verify entity names
2. ALLE `YOUR_CAR_NAME` ersetzt? / Replaced ALL `YOUR_CAR_NAME`?
3. FWCAM-Integration korrekt eingerichtet? / FWCAM setup correct?
4. Home Assistant neu starten / Restart Home Assistant

### "FWCAM-Karte nicht gefunden" / "FWCAM card not found"

**Problem:** "Custom element doesn't exist: fwcam-card"

**Lösung / Solution:**
1. Browser-Cache leeren (Ctrl+Shift+R) / Clear cache
2. Home Assistant neu starten / Restart Home Assistant

### YAML-Fehler / YAML Errors

**Problem:** "Ungültiges YAML" beim Speichern

**Lösung / Solution:**
1. YAML-Validator verwenden / Use YAML validator
2. Einrückung prüfen (Leerzeichen, keine Tabs) / Check indentation

---

## ⚠️ Technische Limitierungen / Technical Limitations

### Automatisches Sidebar-Panel / Automatic Sidebar Panel

**Seit PR #167 / Since PR #167:**
FWCAM registriert automatisch ein Sidebar-Panel – kein YAML-Kopieren erforderlich.

FWCAM automatically registers a sidebar panel – no YAML copy-pasting needed.

- ✅ Sidebar-Panel (`panel_custom`) wird beim Integrationsstart registriert
- ✅ Sidebar panel (`panel_custom`) registered on integration start
- ✅ Fahrzeuge werden automatisch erkannt / Vehicles discovered automatically
- ✅ `fwcam-card` vollständig eingebettet / `fwcam-card` fully embedded

**Fallback: YAML-Vorlagen / Fallback: YAML Templates**
Für benutzerdefinierte Layouts und zusätzliche HA-Karten stehen weiterhin YAML-Vorlagen bereit.
For custom layouts and additional HA cards, YAML templates are still available.

---

## 📚 Weitere Ressourcen / Additional Resources

### Dokumentation / Documentation
- 📖 [Dashboard-Installationsanleitung](dashboards/DASHBOARD_INSTALLATION_GUIDE.md)
- 📖 [Dashboard-README](dashboards/README.md)
- 📖 [Karten-Erweiterungshandbuch](custom_components/hafwcma/www/CARD_ENHANCEMENT_GUIDE.md)
- 📖 [System-Zusammenfassung](DASHBOARD_SYSTEM_SUMMARY.md)
- 📖 [Entitäten-Dokumentation](docs/ENTITIES.md)

### Support / Unterstützung
- 🐛 [GitHub Issues](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)
- 💬 [Home Assistant Community](https://community.home-assistant.io/)

### Beitragen / Contributing
- Eigene Dashboards teilen / Share your dashboards
- Verbesserungen vorschlagen / Suggest improvements
- Hilfe-Inhalte erweitern / Extend help content

---

## ✅ Checkliste / Checklist

### Automatisches Sidebar-Panel / Automatic Sidebar Panel
- [ ] Home Assistant 2023.7 oder neuer / or newer
- [ ] FWCAM-Integration installiert / installed
- [ ] Fahrzeug konfiguriert / Vehicle configured
- [x] ✅ "Fuel Watcher" erscheint automatisch in der Seitenleiste / appears automatically in the sidebar

### YAML-Vorlage (optional / optional)
- [ ] Vorlage ausgewählt / Template selected
- [ ] YAML kopiert / YAML copied
- [ ] Dashboard erstellt / Dashboard created
- [ ] YAML eingefügt / YAML pasted
- [ ] Entitätsnamen angepasst / Entity names customized
- [ ] Gespeichert / Saved
- [ ] Getestet / Tested

---

## 🎉 Zusammenfassung / Summary

**Was Sie bekommen / What You Get:**
- ✅ Automatisches Sidebar-Panel – kein YAML erforderlich / Automatic sidebar panel – no YAML required
- 2 vorgefertigte YAML-Vorlagen für benutzerdefinierte Layouts / 2 YAML templates for custom layouts
- Zweisprachiges Hilfesystem / Bilingual help system
- Wiederverwendbare UI-Komponenten / Reusable UI components
- Umfassende Dokumentation / Comprehensive documentation

**Empfehlung / Recommendation:**
- ⭐ Sidebar-Panel nutzen / Use sidebar panel (zero setup, auto-discovers vehicles)
- 📋 YAML-Vorlagen als Fallback / YAML templates as fallback (custom layouts)

---

**Viel Erfolg! / Good luck!** 🚗💨

Bei Fragen oder Problemen öffnen Sie bitte ein Issue auf GitHub.

For questions or issues, please open an issue on GitHub.
