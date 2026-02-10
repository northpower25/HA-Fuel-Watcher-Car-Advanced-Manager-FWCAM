# FWCAM Card - Fuel Watcher Car Advanced Manager Card

Eine benutzerdefinierte Lovelace-Karte für die Fuel Watcher Car Advanced Manager (FWCAM) Home Assistant Integration.

## Funktionen

- **Fahrzeuginformationsanzeige**: Zeigt aktuellen Kraftstoffpreis, Tankfüllstand, Reichweite, nächste Tankstelle und Tankvorhersage
- **Bedienfeld**: Schnellzugriff-Schaltflächen zum Aktualisieren von Kraftstoffpreisen, Aktualisieren von Vorhersagen, Testen der Verbindung und Importieren historischer Daten
- **Einstellungsverwaltung**: Inline-Bearbeitung von Integrationseinstellungen (Suchradius, Aktualisierungsintervall usw.)
- **Tankbuch**: 
  - Anzeige aller Tankvorgänge im Tabellenformat
  - Farbcodierte Datenqualitäts- und Vertrauensindikatoren
  - Inline-Bearbeitungsfunktionen (Bearbeiten und Löschen von Einträgen)
  - Manuelles Hinzufügen neuer Tankvorgänge
- **Responsives Design**: Passt sich verschiedenen Bildschirmgrößen an
- **Material Design**: Folgt der Design-Sprache von Home Assistant

## Installation

### HACS Installation (Empfohlen)

1. Öffnen Sie HACS in Ihrem Home Assistant
2. Gehen Sie zum Abschnitt "Frontend"
3. Klicken Sie auf die drei Punkte oben rechts
4. Wählen Sie "Benutzerdefinierte Repositories"
5. Fügen Sie diese Repository-URL hinzu: `https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM`
6. Wählen Sie die Kategorie "Lovelace"
7. Klicken Sie auf "Hinzufügen"
8. Suchen Sie "FWCAM Lovelace Card" in der Liste
9. Klicken Sie auf "Herunterladen"
10. Starten Sie Home Assistant neu
11. Leeren Sie Ihren Browser-Cache
12. Fügen Sie die Karte Ihrem Dashboard hinzu

### Manuelle Installation

1. Laden Sie `fwcam-card.js` aus dem `dist/` Verzeichnis herunter
2. Kopieren Sie es in Ihr `config/www/fwcam-card/` Verzeichnis
3. Fügen Sie die Ressource in Ihrer Lovelace-Konfiguration hinzu:

```yaml
resources:
  - url: /local/fwcam-card/fwcam-card.js
    type: module
```

4. Starten Sie Home Assistant neu
5. Leeren Sie Ihren Browser-Cache
6. Fügen Sie die Karte Ihrem Dashboard hinzu

## Konfiguration

### Basis-Konfiguration

```yaml
type: custom:fwcam-card
entity: sensor.mein_auto_refueling_log
```

### Vollständige Konfiguration

```yaml
type: custom:fwcam-card
entity: sensor.mein_auto_refueling_log
title: Mein Auto Tankmanager
show_refueling_log: true
show_vehicle_info: true
show_controls: true
show_settings: true
rows_per_page: 10
```

### Konfigurationsoptionen

| Option | Typ | Standard | Beschreibung |
|--------|-----|----------|--------------|
| `entity` | string | **Erforderlich** | Die Tankbuch-Sensor-Entität (z.B. `sensor.mein_auto_refueling_log`) |
| `title` | string | `Fuel Watcher Car Advanced Manager` | Kartentitel |
| `show_refueling_log` | boolean | `true` | Tankbuch-Tabelle anzeigen/ausblenden |
| `show_vehicle_info` | boolean | `true` | Fahrzeuginformationsbereich anzeigen/ausblenden |
| `show_controls` | boolean | `true` | Steuerungsschaltflächen anzeigen/ausblenden |
| `show_settings` | boolean | `true` | Einstellungsbereich anzeigen/ausblenden |
| `rows_per_page` | number | `10` | Anzahl der anzuzeigenden Tankvorgänge |

## Automatische Entitätserkennung

Die Karte erkennt automatisch alle zugehörigen Entitäten basierend auf dem Namen des Tankbuch-Sensors. Zum Beispiel, wenn Sie konfigurieren:

```yaml
entity: sensor.mein_auto_refueling_log
```

Findet und verwendet die Karte automatisch:
- `sensor.mein_auto_fuel_price`
- `sensor.mein_auto_tank_level`
- `sensor.mein_auto_range`
- `switch.mein_auto_fuel_price_refresh`
- `switch.mein_auto_consumption_prediction`
- `number.mein_auto_station_search_radius`
- Und alle anderen zugehörigen Entitäten

## Funktionen im Detail

### Tankbuch-Tabelle

Das Tankbuch zeigt:
- **Datum/Uhrzeit**: Wann der Tankvorgang stattfand
- **Kilometerstand**: Fahrzeug-Kilometerstand in km
- **Liter**: Menge des getankten Kraftstoffs
- **Preis/L**: Preis pro Liter in €
- **Gesamt**: Gesamtkosten in €
- **Tankstelle**: Name der Tankstelle
- **Qualität**: Datenqualitätsindikator (manual, auto_detected, historical_import)
- **Vertrauen**: Vertrauensbewertung der Erkennung (0-100%)
- **Aktionen**: Bearbeiten und Löschen Schaltflächen

**Hinweis zur Bearbeitung**: Die aktuelle Version verwendet Service-Aufrufe zur Bearbeitung. Klicken Sie auf die Bearbeiten- oder Hinzufügen-Schaltfläche, um Anweisungen zur Verwendung der Services `hafwcma.add_refuel_event` und `hafwcma.update_refuel_event` zu erhalten. Eine visuelle Dialog-Schnittstelle zur Bearbeitung wird in einem zukünftigen Update hinzugefügt.

### Datenqualitätsindikatoren

- **Manual** (Grün): Manuell eingegebene Daten - höchste Qualität
- **Auto Detected** (Blau): Automatisch während des normalen Betriebs erkannt
- **Historical Import** (Orange): Aus historischen Daten importiert

### Vertrauensbewertungen

- **Hoch (Grün)**: 70-100% Vertrauen
- **Mittel (Orange)**: 40-69% Vertrauen
- **Niedrig (Rot)**: 0-39% Vertrauen

### Inline-Bearbeitung

Klicken Sie auf die Bearbeiten-Schaltfläche (✏️), um einen Tankvorgang zu ändern. Klicken Sie auf die Löschen-Schaltfläche (🗑️), um einen Eintrag zu entfernen.

## Erforderliche Services

Die Karte verwendet die folgenden Services (diese sollten von der FWCAM-Integration bereitgestellt werden):

- `hafwcma.add_refuel_event` - Neuen Tankvorgang hinzufügen
- `hafwcma.update_refuel_event` - Bestehenden Eintrag aktualisieren
- `hafwcma.delete_refuel_event` - Eintrag löschen

## Browser-Kompatibilität

- Chrome/Edge: ✅ Vollständig unterstützt
- Firefox: ✅ Vollständig unterstützt
- Safari: ✅ Vollständig unterstützt
- Mobile Browser: ✅ Responsives Design

## Entwicklung

### Neue Funktionen hinzufügen

Beim Hinzufügen neuer Funktionen zur FWCAM-Integration:

1. **Neue Entitäten hinzufügen** zur `findEntities()` Methode in `fwcam-card.js`
2. **UI-Bereiche aktualisieren**, um neue Entitäten anzuzeigen
3. **Service-Aufrufe hinzufügen**, wenn neue Backend-Funktionalität hinzugefügt wird
4. **Konfiguration aktualisieren**, wenn neue Optionen benötigt werden
5. **Dokumentation aktualisieren** in der Integrationsdokumentation

### Beitragen

Beiträge sind willkommen! Bitte:
1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch
3. Machen Sie Ihre Änderungen
4. Senden Sie einen Pull-Request

## Support

Für Probleme und Feature-Anfragen:
1. Prüfen Sie die [Dokumentation](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM)
2. Öffnen Sie ein Issue auf [GitHub](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)

## Lizenz

MIT-Lizenz - Siehe LICENSE-Datei für Details

## Credits

Entwickelt von northpower25 für die FWCAM Home Assistant Integration.
