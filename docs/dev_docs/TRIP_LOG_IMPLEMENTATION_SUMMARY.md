# Trip Tracking Lovelace Card Implementation - Summary

## Überblick (Overview)

Diese Implementierung fügt die Fahrtenbuch (Trip Log) Funktionalität zur FWCAM Integration hinzu, wie in Phase 7 des [TRIP_TRACKING_IMPLEMENTATION_SUMMARY_DE.md](TRIP_TRACKING_IMPLEMENTATION_SUMMARY_DE.md) beschrieben.

This implementation adds Trip Log functionality to the FWCAM integration as described in Phase 7 of the [TRIP_TRACKING_IMPLEMENTATION_SUMMARY_DE.md](TRIP_TRACKING_IMPLEMENTATION_SUMMARY_DE.md).

## Was wurde implementiert? (What has been implemented?)

### 1. Backend - Trip Log Sensor Attribute (✅ Fertig/Complete)

**Datei**: `custom_components/hafwcma/sensor.py`

Der `TripLogSensor` wurde um folgende Attribute erweitert:

```python
attrs["config_entry_id"] = self._config_entry.entry_id
attrs["last_historical_import_timestamp"] = ...
attrs["last_historical_import_type"] = "manual" | "automatic"
attrs["last_vehicle_data_refresh_timestamp"] = ...
attrs["last_vehicle_data_refresh_type"] = "manual" | "automatic"
```

Diese Attribute ermöglichen:
- Service-Aufrufe von der Lovelace-Karte (config_entry_id)
- Tracking des letzten historischen Imports
- Tracking der letzten Fahrzeugdaten-Aktualisierung

### 2. Backend - Historische Fahrtdaten Import (✅ Fertig/Complete)

**Datei**: `custom_components/hafwcma/utils/historical_data_import.py`

Neue Funktion `import_historical_trip_data()`:

**Funktionen**:
- ✅ Prüft ob switch.{car}_trip_tracking aktiviert ist
- ✅ Lädt historische Daten aus dem Home Assistant Recorder
- ✅ Nutzt Langzeitspeicher-Statistiken für Daten älter als 10 Tage
- ✅ Erkennt Fahrten anhand von Kilometerstand-Änderungen
- ✅ Berechnet Fahrt-Metriken (Distanz, Dauer, Kraftstoffverbrauch)
- ✅ Speichert Import-Metadaten mit Zeitstempel und Typ

**Konstanten**:
```python
TRIP_DETECTION_MIN_DISTANCE_KM = 0.5  # Minimale Distanz für Fahrt
TRIP_MERGE_TIME_WINDOW_MINUTES = 5    # Zeitfenster für Zusammenführung
TRIP_MAX_SPEED_KMH = 300               # Maximale plausible Geschwindigkeit
TRIP_MIN_DURATION_MINUTES = 1          # Minimale Fahrtdauer
```

**Helper-Funktionen**:
- `_import_trip_history()` - Hauptlogik für Fahrterkennung
- `_fetch_entity_history()` - Lädt Entitäts-Historie
- `_find_closest_tank_level()` - Findet nächsten Tankstand
- `_find_closest_location()` - Findet nächste GPS-Position
- `_calculate_trip_confidence()` - Berechnet Vertrauenswert

### 3. Backend - Button für manuellen Import (✅ Fertig/Complete)

**Datei**: `custom_components/hafwcma/button.py`

Neue Button-Entität `ImportHistoricalTripDataButton`:

```python
class ImportHistoricalTripDataButton(ButtonEntity):
    """Button to import historical trip data from recorder."""
    
    _attr_icon = "mdi:database-import-outline"
    _attr_name = "Import Historical Trip Data"
```

**Funktionen**:
- ✅ Validiert dass Trip-Tracking aktiviert ist
- ✅ Trigger historischen Import mit `force_reimport=True`
- ✅ Markiert Import als "manual"
- ✅ Gibt Import-Statistiken in Entitäts-Attributen zurück
- ✅ Aktualisiert Coordinator nach erfolgreichem Import

### 4. Frontend - Lovelace Card Konfiguration (✅ Teilweise/Partial)

**Datei**: `fwcam-card/dist/fwcam-card.js`

**Implementiert**:
- ✅ `show_trip_log` Konfigurationsoption
- ✅ Automatische Entitätserkennung für Trip-Sensoren
- ✅ Service-Methoden `editTrip()` und `deleteTrip()`
- ✅ Render-Aufruf für Trip-Log in `render()` Methode

**Entitätserkennung**:
```javascript
trip_log_sensor: `sensor.${baseName}_trip_log`,
current_trip: `sensor.${baseName}_current_trip`,
trip_tracking: `switch.${baseName}_trip_tracking`,
import_historical_trip_data: `button.${baseName}_import_historical_trip_data`,
```

### 5. Frontend - Trip Log Methoden (📄 Dokumentiert/Documented)

**Datei**: `docs/TRIP_LOG_CARD_METHODS.js`

Vollständige Implementierung folgender Methoden dokumentiert:

**Render-Methoden**:
- `renderTripLog(trips)` - Rendert Fahrtenbuch-Tabelle mit Filtern
- `renderTripDialog()` - Rendert Bearbeitungs-Dialog

**Filter & Sort-Methoden**:
- `filterTrips(trips)` - Filtert nach Jahr, Monat, Kategorie
- `sortTrips(trips)` - Sortiert nach Spalte und Richtung
- `getUniqueTripYears(trips)` - Extrahiert einzigartige Jahre
- `renderTripSortIcon(column)` - Rendert Sort-Icon

**Format-Methoden**:
- `formatDuration(minutes)` - Formatiert Minuten zu HH:MM
- `capitalizeFirst(str)` - Kapitalisiert ersten Buchstaben

**Dialog-Methoden**:
- `showEditTripDialog(tripId)` - Öffnet Bearbeitungs-Dialog
- `closeTripDialog()` - Schließt Dialog
- `handleTripFormSubmit()` - Verarbeitet Formular-Submission

**Event-Handler**:
- Filter-Änderungen (Jahr, Monat, Kategorie)
- Tabellen-Sortierung
- Edit/Delete Buttons
- Dialog-Aktionen

## Fahrtenbuch-Tabelle (Trip Table)

### Spalten (Columns)

| Spalte | Beschreibung | Sortierbar | Format |
|--------|--------------|------------|--------|
| Start Time | Fahrtbeginn | Ja | Datum/Zeit |
| End Time | Fahrtende | Ja | Datum/Zeit |
| Distance (km) | Fahrtdistanz | Ja | Zahl (1 Dezimale) |
| Duration | Fahrtdauer | Ja | HH:MM Format |
| Category | Kategorie | Ja | Badge |
| Fuel (L) | Verbrauch | Ja | Zahl (2 Dezimalen) |
| Actions | Aktionen | Nein | Buttons |

### Filter (Filters)

1. **Jahr (Year)**: Dropdown mit allen Jahren aus Fahrtdaten
2. **Monat (Month)**: Dropdown mit allen 12 Monaten
3. **Kategorie (Category)**: Dropdown mit Geschäftlich/Privat/Pendeln

### Kategorie-Badges (Category Badges)

- **Business (Geschäftlich)**: Blauer Badge
- **Private (Privat)**: Grauer Badge
- **Commute (Pendeln)**: Grüner Badge

## Bearbeitungs-Dialog (Edit Dialog)

### Read-Only Felder:
- Start Time (Startzeit)
- End Time (Endzeit)
- Distance (Distanz)
- Duration (Dauer)
- Fuel Consumed (Kraftstoffverbrauch)

### Bearbeitbare Felder (Editable Fields):
- **Category**: Dropdown (Geschäftlich/Privat/Pendeln)
- **Purpose**: Textfeld für Fahrt-Beschreibung
- **Additional Costs**: Zahlenfeld für Maut, Parkgebühren, etc.
- **Notes**: Textbereich für zusätzliche Notizen

## Service-Aufrufe (Service Calls)

### Fahrt bearbeiten (Edit Trip)

```yaml
service: hafwcma.edit_trip
data:
  config_entry_id: "abc123def456"
  trip_id: 42
  category: "business"
  purpose: "Kundentermin in München"
  additional_costs: 5.50
  notes: "Autobahn-Umleitung wegen Baustelle"
```

### Fahrt löschen (Delete Trip)

```yaml
service: hafwcma.delete_trip
data:
  config_entry_id: "abc123def456"
  trip_id: 42
```

### Historische Fahrten importieren (Import Historical Trips)

```yaml
service: button.press
target:
  entity_id: button.mein_auto_import_historical_trip_data
```

## Integration in fwcam-card.js

Um die Trip-Log-Funktionalität zu aktivieren, müssen die Methoden aus `docs/TRIP_LOG_CARD_METHODS.js` in `fwcam-card/dist/fwcam-card.js` integriert werden:

### Schritt 1: Konstruktor erweitern

```javascript
// In constructor() um Zeile 43 hinzufügen:
this._filterTripYear = '';
this._filterTripMonth = '';
this._filterTripCategory = '';
this._sortTripColumn = 'timestamp_start';
this._sortTripDirection = 'desc';
```

### Schritt 2: Render-Methoden hinzufügen

Nach `renderRefuelingLog()` (um Zeile 770) folgende Methoden hinzufügen:
- `renderTripLog(trips)`
- `renderTripDialog()`

### Schritt 3: Filter & Sort-Methoden hinzufügen

Nach den bestehenden Filter/Sort-Methoden (um Zeile 850) hinzufügen:
- `filterTrips(trips)`
- `sortTrips(trips)`
- `getUniqueTripYears(trips)`
- `renderTripSortIcon(column)`

### Schritt 4: Format-Methoden hinzufügen

Nach den bestehenden Format-Methoden (um Zeile 400) hinzufügen:
- `formatDuration(minutes)`
- `capitalizeFirst(str)`

### Schritt 5: Event-Handler hinzufügen

In `attachEventListeners()` (um Zeile 920) die Event-Handler aus der Dokumentation hinzufügen.

### Schritt 6: Dialog-Methoden hinzufügen

Nach den bestehenden Dialog-Methoden (um Zeile 1100) hinzufügen:
- `showEditTripDialog(tripId)`
- `closeTripDialog()`
- `handleTripFormSubmit()`

### Schritt 7: CSS-Styles hinzufügen

In `getStyles()` (um Zeile 1550) die CSS-Styles aus der Dokumentation hinzufügen.

## Verwendung (Usage)

### Lovelace-Karten-Konfiguration

```yaml
type: custom:fwcam-card
entity: sensor.mein_auto_refueling_log
title: Mein Auto Manager
show_trip_log: true           # Aktiviert Fahrtenbuch
show_refueling_log: true
show_vehicle_info: true
show_controls: true
show_settings: true
rows_per_page: 10
```

### Historische Fahrten importieren

1. Aktiviere Trip-Tracking: `switch.mein_auto_trip_tracking`
2. Klicke Button: `button.mein_auto_import_historical_trip_data`
3. Warte auf Import (kann einige Minuten dauern)
4. Prüfe Import-Ergebnis in Button-Attributen

### Fahrten bearbeiten

1. Öffne Lovelace-Karte
2. Navigiere zum "Trip Log" Abschnitt
3. Klicke auf Edit-Button (Stift-Icon) neben einer Fahrt
4. Bearbeite Kategorie, Zweck, Zusatzkosten, Notizen
5. Klicke "Save Changes"

### Fahrten filtern

1. Wähle Jahr aus Dropdown
2. Wähle Monat aus Dropdown (optional)
3. Wähle Kategorie aus Dropdown (optional)
4. Tabelle wird automatisch gefiltert
5. Klicke "Clear Filters" um Filter zurückzusetzen

### Fahrten sortieren

1. Klicke auf Tabellen-Header
2. Erste Klick: Sortierung absteigend
3. Zweite Klick: Sortierung aufsteigend
4. Dritte Klick: Zurück zu Standard-Sortierung

## Testing

### Backend-Tests

```bash
# Trip-Tracking aktivieren
service: switch.turn_on
target:
  entity_id: switch.test_car_trip_tracking

# Historischen Import triggern
service: button.press
target:
  entity_id: button.test_car_import_historical_trip_data

# Prüfe Import-Ergebnis
# Attribute von button.test_car_import_historical_trip_data ansehen

# Prüfe Trip-Log-Sensor
# State und Attribute von sensor.test_car_trip_log ansehen
```

### Frontend-Tests

1. **Tabelle rendern**: Prüfe dass Fahrten angezeigt werden
2. **Sortierung**: Klicke auf verschiedene Spalten-Header
3. **Filterung**: Teste Jahr/Monat/Kategorie-Filter
4. **Edit-Dialog**: Öffne Dialog, prüfe dass Felder gefüllt sind
5. **Edit-Service**: Speichere Änderungen, prüfe dass aktualisiert wurde
6. **Delete-Dialog**: Teste Bestätigungs-Dialog
7. **Delete-Service**: Lösche Fahrt, prüfe dass entfernt wurde
8. **Keine Daten**: Teste Anzeige wenn keine Fahrten vorhanden

## Bekannte Einschränkungen (Known Limitations)

1. **Frontend-Integration**: Methoden sind dokumentiert, aber noch nicht in Haupt-Datei integriert
2. **End-to-End-Tests**: Noch nicht durchgeführt
3. **Minimierte Version**: `fwcam-card.min.js` muss nach Integration neu gebaut werden
4. **Pagination**: Aktuell nur `rows_per_page` Limit, keine echte Pagination
5. **Export**: Kein CSV/JSON Export implementiert

## Nächste Schritte (Next Steps)

1. **Integration**: Integriere Methoden aus `docs/TRIP_LOG_CARD_METHODS.js` in `fwcam-card/dist/fwcam-card.js`
2. **Testing**: Führe End-to-End-Tests durch
3. **Build**: Baue minimierte Version neu (`fwcam-card.min.js`)
4. **Dokumentation**: Aktualisiere README mit Trip-Tracking-Features
5. **Release**: Erstelle Release mit neuen Features

## Dateien (Files)

### Geändert (Modified)
- `custom_components/hafwcma/sensor.py` - Trip Log Sensor Attribute
- `custom_components/hafwcma/button.py` - Historischer Import Button
- `custom_components/hafwcma/utils/historical_data_import.py` - Import-Funktion
- `fwcam-card/dist/fwcam-card.js` - Karten-Konfiguration (teilweise)

### Neu (New)
- `docs/TRIP_LOG_CARD_IMPLEMENTATION.md` - Implementierungs-Dokumentation
- `docs/TRIP_LOG_CARD_METHODS.js` - JavaScript-Methoden-Dokumentation
- `docs/TRIP_LOG_IMPLEMENTATION_SUMMARY.md` - Dieses Dokument

## Support & Fragen (Support & Questions)

Bei Fragen oder Problemen:
1. Prüfe die Dokumentation in `docs/` Verzeichnis
2. Prüfe Service-Definitionen in `custom_components/hafwcma/services.yaml`
3. Prüfe Logs in Home Assistant für Fehler
4. Öffne Issue auf GitHub mit detaillierter Beschreibung

---

**Version**: 1.0.0  
**Datum**: 2026-02-13  
**Autor**: GitHub Copilot Agent  
**Lizenz**: MIT
