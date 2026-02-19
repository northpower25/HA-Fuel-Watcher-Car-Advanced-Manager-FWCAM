# FWCAM Dashboard System - Benutzeranleitung / User Guide

## 🎯 Zusammenfassung / Summary

Dieses PR implementiert ein umfassendes Dashboard-System für die FWCAM-Integration mit vorgefertigten Vorlagen, Hilfesystem und ausführlicher Dokumentation.

This PR implements a comprehensive dashboard system for the FWCAM integration with ready-to-use templates, help system, and extensive documentation.

---

## 🚀 Was wurde implementiert / What Was Implemented

### 1. Dashboard-Vorlagen / Dashboard Templates

#### Übersichts-Dashboard / Overview Dashboard
📁 `dashboards/fwcam-overview-dashboard.yaml`

**Für mehrere Fahrzeuge / For multiple vehicles**
- 5 Ansichten: Übersicht, Kraftstoffpreise, Fahrten, Einstellungen, Debug
- 5 views: Overview, Fuel Prices, Trips, Settings, Debug
- Vergleich zwischen Fahrzeugen / Vehicle comparison
- Zentrale Konfiguration / Centralized configuration

#### Fahrzeug-Dashboard / Per-Vehicle Dashboard
📁 `dashboards/fwcam-vehicle-dashboard-template.yaml`

**Für detaillierte Fahrzeugverwaltung / For detailed vehicle management**
- 6 Ansichten: Übersicht, Tankprotokoll, Fahrtenbuch, Statistiken, Einstellungen, Debug
- 6 views: Overview, Refueling Log, Trip Log, Statistics, Settings, Debug
- FWCAM-Karte vollständig integriert / Full FWCAM card integration
- Erweiterte Statistiken / Advanced statistics

### 2. Hilfe-Module / Helper Modules

#### Hilfe-Inhalte / Help Content
📁 `custom_components/hafwcma/www/fwcam-card-help.js`

- Zweisprachig (Deutsch/Englisch) / Bilingual (German/English)
- Hilfe für alle Entitäten / Help for all entities
- Modal-Popups (keine neuen Tabs) / Modal popups (no new tabs)
- Links zur Dokumentation / Links to documentation

#### Hilfsfunktionen / Helper Functions
📁 `custom_components/hafwcma/www/fwcam-card-helpers.js`

- Wiederverwendbare UI-Komponenten / Reusable UI components
- Hilfe-Buttons / Help buttons
- Statistik-Karten / Statistics cards
- Ausklappbare Bereiche / Collapsible sections
- Fortschrittsbalken / Progress bars
- Formatierungsfunktionen / Formatting functions

### 3. Dokumentation / Documentation

#### Installationsanleitung / Installation Guide
📁 `dashboards/DASHBOARD_INSTALLATION_GUIDE.md`

- Schritt-für-Schritt-Anleitung / Step-by-step instructions
- Anpassungsbeispiele / Customization examples
- Fehlerbehebung / Troubleshooting
- Technische Limitierungen erklärt / Technical limitations explained

#### Weitere Dokumentation / Additional Documentation
- 📁 `dashboards/README.md` - Schnellstart / Quick start
- 📁 `custom_components/hafwcma/www/CARD_ENHANCEMENT_GUIDE.md` - Entwicklerhandbuch / Developer guide
- 📁 `DASHBOARD_SYSTEM_SUMMARY.md` - Technische Übersicht / Technical overview

---

## 📋 Installation - Schnellstart / Quick Start

### Option 1: Übersichts-Dashboard (Mehrere Fahrzeuge)

**5-Minuten-Installation:**

1. **Datei öffnen / Open file:**
   - `dashboards/fwcam-overview-dashboard.yaml`

2. **YAML kopieren / Copy YAML:**
   - Gesamten Inhalt kopieren / Copy entire content

3. **Dashboard erstellen / Create dashboard:**
   - Einstellungen → Dashboards
   - Settings → Dashboards
   - "+ DASHBOARD HINZUFÜGEN" / "+ ADD DASHBOARD"

4. **YAML einfügen / Paste YAML:**
   - Dashboard bearbeiten → Raw-Konfigurations-Editor
   - Edit Dashboard → Raw configuration editor
   - YAML einfügen / Paste YAML

5. **Anpassen / Customize:**
   - `YOUR_CAR_NAME` durch Ihren Fahrzeugnamen ersetzen
   - Replace `YOUR_CAR_NAME` with your vehicle name
   - Speichern / Save

### Option 2: Fahrzeug-Dashboard (Ein Fahrzeug, detailliert)

**Gleicher Prozess mit:**
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
1. `fwcam-card.js` installiert? / Installed?
2. Browser-Cache leeren (Ctrl+Shift+R) / Clear cache
3. Ressourcen neu laden / Reload resources

### YAML-Fehler / YAML Errors

**Problem:** "Ungültiges YAML" beim Speichern

**Lösung / Solution:**
1. YAML-Validator verwenden / Use YAML validator
2. Einrückung prüfen (Leerzeichen, keine Tabs) / Check indentation
3. Anführungszeichen geschlossen? / Quotes closed?
4. Sonderzeichen maskiert? / Special chars escaped?

---

## ⚠️ Technische Limitierungen / Technical Limitations

### Warum keine automatische Dashboard-Erstellung?

**Wichtig / Important:**
Home Assistant unterstützt NICHT die automatische Dashboard-Erstellung durch Integrationen.

Home Assistant does NOT support automatic dashboard creation from integrations.

**Gründe / Reasons:**
1. Sicherheit / Security
2. Stabilität / Stability
3. Architektur / Architecture
4. Best Practices

**Unsere Lösung / Our Solution:**
- ✅ Vorgefertigte YAML-Vorlagen / Ready-made YAML templates
- ✅ Ausführliche Anleitungen / Detailed guides
- ✅ Einfache Anpassung / Easy customization
- ✅ Best Practices befolgt / Following best practices

**Dieser Ansatz wird auch verwendet von:**
This approach is also used by:
- Frigate NVR
- ESPHome
- Zigbee2MQTT
- Node-RED

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

### Vor der Installation / Before Installation
- [ ] Home Assistant 2023.7 oder neuer / or newer
- [ ] FWCAM-Integration installiert / installed
- [ ] Fahrzeug konfiguriert / Vehicle configured
- [ ] Entitätsnamen notiert / Entity names noted

### Installation / Installation
- [ ] Vorlage ausgewählt / Template selected
- [ ] YAML kopiert / YAML copied
- [ ] Dashboard erstellt / Dashboard created
- [ ] YAML eingefügt / YAML pasted
- [ ] Entitätsnamen angepasst / Entity names customized
- [ ] Gespeichert / Saved
- [ ] Getestet / Tested

### Nach der Installation / After Installation
- [ ] Dashboard funktioniert / Dashboard works
- [ ] Alle Entitäten angezeigt / All entities shown
- [ ] Mobilansicht geprüft / Mobile view checked
- [ ] Anpassungen vorgenommen / Customizations made
- [ ] Dokumentiert / Documented

---

## 🎉 Zusammenfassung / Summary

**Was Sie bekommen / What You Get:**
- 2 vorgefertigte Dashboard-Vorlagen / 2 ready-made templates
- Zweisprachiges Hilfesystem / Bilingual help system
- Wiederverwendbare UI-Komponenten / Reusable UI components
- Umfassende Dokumentation / Comprehensive documentation
- 5-Minuten-Installation / 5-minute installation
- Vollständig anpassbar / Fully customizable

**Warum dieser Ansatz? / Why This Approach?**
- ✅ Folgt HA Best Practices / Follows HA best practices
- ✅ Kein Risiko von Datenbeschädigung / No data corruption risk
- ✅ Funktioniert mit allen HA-Versionen / Works with all HA versions
- ✅ Von Benutzern anpassbar / Customizable by users
- ✅ Einfach zu warten / Easy to maintain
- ✅ Community kann teilen / Community can share

**Nächste Schritte / Next Steps:**
1. Vorlage auswählen / Choose template
2. Installationsanleitung folgen / Follow installation guide
3. Dashboard anpassen / Customize dashboard
4. Genießen! / Enjoy!

---

**Viel Erfolg! / Good luck!** 🚗💨

Bei Fragen oder Problemen öffnen Sie bitte ein Issue auf GitHub.

For questions or issues, please open an issue on GitHub.
