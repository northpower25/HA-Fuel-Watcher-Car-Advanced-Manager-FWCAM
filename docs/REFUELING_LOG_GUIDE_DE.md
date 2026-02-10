# Tankprotokoll - Anzeige- und Verwaltungshandbuch

## Übersicht

Die Entität `sensor.[car_name]_refueling_log` bietet ein umfassendes Protokoll aller Tankvorgänge für Ihr Fahrzeug. Dieses Handbuch erklärt, wie Sie diese Daten in der Home Assistant GUI anzeigen und verwalten können.

## Wichtig: Keine ToDo-Domain-Entität

Das Tankprotokoll ist eine **Sensor-Entität**, keine ToDo-Domain-Entität. Das bedeutet:
- ✅ Es kann Tankhistorie und Statistiken anzeigen
- ❌ Es kann nicht mit der ToDo-Listen-Kachel verwendet werden
- ✅ Es kann über Dienste und Automatisierungen bearbeitet werden
- ✅ Mehrere Anzeigeoptionen sind verfügbar (siehe unten)

### Warum keine ToDo-Entität?

ToDo-Entitäten in Home Assistant sind für Aufgabenverwaltung (Einkaufslisten, Checklisten usw.) konzipiert. Das Tankprotokoll sind historische Daten mit spezifischen Attributen (Zeitstempel, Kilometerstand, Liter, Kosten usw.), die nicht zum ToDo-Domain-Modell passen.

## Anzeigeoptionen

### Option 0: FWCAM Custom Card (EMPFOHLEN - Am Benutzerfreundlichsten)

**Die FWCAM Card ist eine benutzerdefinierte Lovelace-Karte, die die beste Benutzererfahrung für die Verwaltung der Fuel Watcher Car Advanced Manager Integration bietet.**

#### Funktionen
- ✅ **Fahrzeuginformationen**: Echtzeit-Anzeige von Kraftstoffpreis, Tankfüllstand, Reichweite und nächster Tankstelle
- ✅ **Bedienfeld**: Schnellzugriff-Buttons für alle Integrationsfunktionen
- ✅ **Einstellungsverwaltung**: Inline-Bearbeitung aller Integrationseinstellungen
- ✅ **Tankprotokoll-Tabelle**: Anzeigen, Bearbeiten und Löschen von Tankvorgängen
- ✅ **Ereignisse hinzufügen**: Manuelle Eingabe neuer Tankvorgänge
- ✅ **Datenqualitätsindikatoren**: Farbcodierte Qualitäts- und Vertrauens-Scores
- ✅ **Responsives Design**: Funktioniert auf Desktop und Mobile
- ✅ **Auto-Erkennung**: Findet automatisch alle zugehörigen Entitäten

#### Installation

**Manuelle Installation:**
1. Kopieren Sie `/www/fwcam-card/fwcam-card.js` aus diesem Repository in Ihr Home Assistant `config/www/fwcam-card/` Verzeichnis
2. Fügen Sie die Ressource in Ihrer Lovelace-Konfiguration hinzu (Konfiguration → Dashboards → Ressourcen):
   ```yaml
   url: /local/fwcam-card/fwcam-card.js
   type: module
   ```
3. Laden Sie Ihren Browser-Cache neu (Strg+F5)

**HACS Installation (Zukünftig):**
> Hinweis: HACS-Installation wird verfügbar sein, sobald diese Karte im HACS-Standard-Repository veröffentlicht ist.

#### Grundlegende Verwendung

Fügen Sie Folgendes zu Ihrem Lovelace-Dashboard hinzu:

```yaml
type: custom:fwcam-card
entity: sensor.my_car_refueling_log
```

#### Vollständige Konfiguration

```yaml
type: custom:fwcam-card
entity: sensor.my_car_refueling_log
title: Mein Auto Kraftstoff-Manager
show_refueling_log: true    # Tankprotokoll-Tabelle anzeigen
show_vehicle_info: true     # Fahrzeuginformationen anzeigen
show_controls: true         # Steuerungs-Buttons anzeigen
show_settings: true         # Einstellungen anzeigen
rows_per_page: 10          # Anzahl anzuzeigender Ereignisse
```

#### Konfigurationsoptionen

| Option | Typ | Standard | Beschreibung |
|--------|-----|----------|--------------|
| `entity` | string | **Erforderlich** | Ihr Tankprotokoll-Sensor (z.B. `sensor.my_car_refueling_log`) |
| `title` | string | `Fuel Watcher Car Advanced Manager` | Kartentitel |
| `show_refueling_log` | boolean | `true` | Tankprotokoll-Tabelle anzeigen/ausblenden |
| `show_vehicle_info` | boolean | `true` | Fahrzeuginformationen anzeigen/ausblenden |
| `show_controls` | boolean | `true` | Steuerungs-Buttons anzeigen/ausblenden |
| `show_settings` | boolean | `true` | Einstellungen anzeigen/ausblenden |
| `rows_per_page` | number | `10` | Anzahl anzuzeigender Tankvorgänge |

#### Was die Karte anzeigt

**Fahrzeuginformationen-Bereich:**
- Aktueller Kraftstoffpreis (€/L)
- Tankfüllstand (%)
- Verbleibende Reichweite (km)
- Nächste/günstigste Tankstelle
- Vorhergesagte Tage bis zum nächsten Tanken

**Bedienfeld:**
- 🔄 Kraftstoffpreise aktualisieren - Kraftstoffpreisdaten manuell aktualisieren
- 📊 Vorhersage aktualisieren - Verbrauchsvorhersage neu berechnen
- 🔌 Verbindung testen - API-Verbindung zum Kraftstoffpreisanbieter testen
- 📥 Historie importieren - Historische Tankdaten importieren

**Einstellungen:**
- Tankstellen-Suchradius (1-25 km)
- API-Aktualisierungsintervall (1-60 Minuten)
- Minimale Datenpunkte für Verbrauchsberechnung
- Vorhersage-Berechnungsintervall (0,5-24 Stunden)

**Tankprotokoll-Tabelle:**
- Datum/Uhrzeit des Tankvorgangs
- Kilometerstand (km)
- Getankte Liter
- Preis pro Liter (€)
- Gesamtkosten (€)
- Tankstellenname
- Datenqualitätsindikator (Manuell/Auto/Historisch)
- Vertrauens-Score (0-100%)
- Bearbeiten/Löschen-Buttons für jedes Ereignis

#### Entwicklerhinweise

**Beim Hinzufügen neuer Funktionen zur FWCAM-Integration:**

1. **Neue Entitäten**: Fügen Sie sie zur `findEntities()`-Methode in `fwcam-card.js` hinzu
   ```javascript
   // Beispiel: Hinzufügen eines neuen Sensors
   new_sensor: `sensor.${baseName}_new_feature`,
   ```

2. **Neue UI-Bereiche**: Erstellen Sie eine neue Render-Methode
   ```javascript
   renderNewSection() {
     // Ihr UI-Code hier
   }
   ```

3. **Neue Dienste**: Fügen Sie Dienstaufruf-Methoden hinzu
   ```javascript
   callNewService(params) {
     this.callService('hafwcma', 'new_service', params);
   }
   ```

4. **Konfigurationsoptionen**: Aktualisieren Sie die `setConfig()`-Methode und Dokumentation

5. **Immer aktualisieren**:
   - `fwcam-card.js` - Haupt-Kartencode
   - `www/fwcam-card/README.md` - Karten-Dokumentation
   - `REFUELING_LOG_GUIDE.md` - Englische Version
   - `REFUELING_LOG_GUIDE_DE.md` - Diese Datei

#### Vorteile der benutzerdefinierten Karte

- ✅ **All-in-One-Interface**: Zentrale Übersicht für die gesamte Integration
- ✅ **Benutzerfreundlich**: Keine komplexen YAML-Templates erforderlich
- ✅ **Voll editierbar**: Direkte Manipulation von Tankvorgängen
- ✅ **Visuelles Feedback**: Farbcodierte Qualitäts- und Vertrauensindikatoren
- ✅ **Responsiv**: Funktioniert auf allen Geräten
- ✅ **Zukunftssicher**: Einfach mit neuen Funktionen erweiterbar

---

### Option 1: Attribute-Karte (Empfohlen)

Verwenden Sie die integrierte Attribute-Karte zur Anzeige der Tankvorgänge:

```yaml
type: attribute
entity: sensor.your_car_refueling_log
attribute: recent_events
```

Dies zeigt die 10 neuesten Tankvorgänge mit allen Details an.

### Option 2: Markdown-Karte

Erstellen Sie eine benutzerdefinierte Markdown-Karte für bessere Formatierung:

```yaml
type: markdown
content: |
  ## Tankprotokoll für {{ state_attr('sensor.your_car_refueling_log', 'status') }}
  
  ### Letzter Tankvorgang
  {% set last = state_attr('sensor.your_car_refueling_log', 'last_refueling') %}
  {% if last %}
  - **Datum**: {{ last.timestamp | as_datetime | as_local }}
  - **Liter**: {{ last.liters }} L
  - **Kosten**: {{ last.cost }} €
  - **Tankstelle**: {{ last.station }}
  {% else %}
  Noch keine Tankvorgänge erfasst.
  {% endif %}
  
  ### Letzte Ereignisse
  {% set events = state_attr('sensor.your_car_refueling_log', 'recent_events') %}
  {% if events %}
  {% for event in events %}
  #### Ereignis #{{ event.id }} - {{ event.timestamp | as_datetime | as_local }}
  - **Kilometerstand**: {{ event.odometer_km }} km
  - **Liter**: {{ event.liters_refueled }} L
  - **Preis/L**: {{ event.price_per_liter }} €
  - **Gesamt**: {{ event.total_cost }} €
  - **Tankstelle**: {{ event.station_name }}
  - **Qualität**: {{ event.data_quality }} ({{ (event.confidence * 100) | round(0) }}% Vertrauen)
  {% endfor %}
  {% else %}
  Keine Ereignisse anzuzeigen.
  {% endif %}
```

### Option 3: Benutzerdefinierte Karte mit Filterung

Verwenden Sie eine Markdown-Karte mit Filterung nach Datenqualität:

```yaml
type: markdown
content: |
  ## Tankprotokoll - Manuelle Überprüfung erforderlich
  
  {% set events = state_attr('sensor.your_car_refueling_log', 'recent_events') %}
  {% if events %}
  ### Ereignisse mit geringem Vertrauen (Überprüfung empfohlen)
  {% for event in events if event.confidence < 0.7 %}
  - **{{ event.timestamp | as_datetime | as_local }}**: {{ event.liters_refueled }}L bei {{ event.odometer_km }}km
    - Qualität: {{ event.data_quality }}, Vertrauen: {{ (event.confidence * 100) | round(0) }}%
    - Tankstelle: {{ event.station_name }}
  {% endfor %}
  
  ### Ereignisse mit hohem Vertrauen
  {% for event in events if event.confidence >= 0.7 %}
  - **{{ event.timestamp | as_datetime | as_local }}**: {{ event.liters_refueled }}L bei {{ event.odometer_km }}km
  {% endfor %}
  {% endif %}
```

### Option 4: Entitäten-Karte

Zusammenfassende Statistiken anzeigen:

```yaml
type: entities
title: Tank-Zusammenfassung
entities:
  - entity: sensor.your_car_refueling_log
    name: Gesamte Ereignisse
  - type: attribute
    entity: sensor.your_car_refueling_log
    attribute: status
    name: Status
  - type: attribute
    entity: sensor.your_car_refueling_log
    attribute: last_refueling
    name: Letzter Tankvorgang
```

## Datenqualitätsindikatoren

Jeder Tankvorgang enthält Qualitätsindikatoren, die Ihnen helfen, Ereignisse zu identifizieren, die möglicherweise manuell korrigiert werden müssen:

### Datenqualitätsfeld

- **`manual`**: Manuell eingetragener Tankvorgang (höchste Qualität)
- **`auto_detected`**: Automatisch während des normalen Betriebs erkannt
- **`historical_import`**: Aus historischem Datenimport erkannt

### Vertrauens-Score

Ein Wert von 0.0 bis 1.0, der das Vertrauen in die Erkennung angibt:
- **1.0**: Perfektes Vertrauen (alle Daten verfügbar, vernünftige Werte)
- **0.7-0.9**: Hohes Vertrauen (meiste Daten verfügbar)
- **0.4-0.6**: Mittleres Vertrauen (einige Daten fehlen)
- **0.0-0.3**: Geringes Vertrauen (begrenzte Daten, möglicherweise Überprüfung erforderlich)

### Vertrauens-Berechnung

Der Vertrauens-Score wird basierend auf folgenden Kriterien berechnet:
1. **Kilometerdaten verfügbar** (40% Gewichtung): Ob Kilometerstand gefunden wurde
2. **Preisdaten verfügbar** (30% Gewichtung): Ob Kraftstoffpreis gefunden wurde
3. **Vernünftige Tankmenge** (30% Gewichtung): Ob die getankte Menge zwischen 10-100% der Tankkapazität liegt

### Filterung nach Qualität

Sie können Ereignisse nach Qualität in Automatisierungen oder Templates filtern:

```yaml
# Nur Ereignisse mit hohem Vertrauen abrufen
{% set events = state_attr('sensor.your_car_refueling_log', 'recent_events') %}
{% set high_confidence = events | selectattr('confidence', '>=', 0.7) | list %}
```

```yaml
# Historische Import-Ereignisse abrufen, die überprüft werden müssen
{% set events = state_attr('sensor.your_car_refueling_log', 'recent_events') %}
{% set needs_review = events | selectattr('data_quality', 'eq', 'historical_import') | selectattr('confidence', '<', 0.7) | list %}
```

## Bearbeiten von Tankvorgängen

Obwohl es keine integrierte GUI zum Bearbeiten einzelner Tankvorgänge gibt, können Sie die folgenden Ansätze verwenden:

### Methode 1: Löschen und neu hinzufügen

1. Verwenden Sie den Dienst `hafwcma.delete_refuel_event`, um falsche Ereignisse zu entfernen
2. Verwenden Sie den Dienst `hafwcma.add_refuel_event`, um korrigierte Ereignisse hinzuzufügen

### Methode 2: Aktualisierung über Dienstaufruf

Verwenden Sie den Dienst `hafwcma.update_refuel_event` (falls verfügbar), um bestimmte Felder zu ändern.

### Methode 3: Speicherdatei-Bearbeitung (Fortgeschritten)

Für fortgeschrittene Benutzer können Sie die Speicherdatei direkt bearbeiten:
1. Home Assistant stoppen
2. `.storage/hafwcma_[entry_id].json` bearbeiten
3. Das `refueling_log`-Array ändern
4. Home Assistant neu starten

**Warnung**: Direkte Dateibearbeitung kann Probleme verursachen, wenn sie falsch durchgeführt wird. Erstellen Sie immer zuerst ein Backup!

## Best Practices

### Historische Importe überprüfen

Nach dem historischen Datenimport:
1. Überprüfen Sie Ereignisse mit `data_quality: historical_import`
2. Konzentrieren Sie sich auf Ereignisse mit `confidence < 0.7`
3. Überprüfen Sie, ob Zeitstempel mit tatsächlichen Tankterminen übereinstimmen
4. Korrigieren oder löschen Sie offensichtliche Fehlerkennungen

### Regelmäßige Überwachung

- Überprüfen Sie neue Ereignisse wöchentlich
- Achten Sie auf Duplikaterkennungen
- Überprüfen Sie Kilometerstände
- Aktualisieren Sie fehlende Preisdaten

### Duplikate verhindern

Die Integration verhindert automatisch Duplikaterkennung innerhalb von 24 Stunden des gleichen Zeitstempels. Wenn Sie Duplikate sehen:
1. Sie stammen möglicherweise aus verschiedenen Import-Durchläufen
2. Löschen Sie Duplikate manuell
3. Überprüfen Sie die Protokolle auf Import-Fehler

## Fehlerbehebung

### Fehler "Specify an entity from within the todo domain"

Dieser Fehler erscheint beim Versuch, den Tankprotokoll-Sensor mit einer ToDo-Listen-Karte zu verwenden. Das Tankprotokoll ist ein Sensor, keine ToDo-Entität. Verwenden Sie stattdessen eine der oben genannten Anzeigeoptionen.

### Fehlende Zeitstempel

Wenn Tankvorgänge als "Unbekannt" angezeigt werden oder Zeitstempel fehlen:
- Überprüfen Sie, ob Ihr Tankfüllstand-Sensor ordnungsgemäße historische Daten hat
- Stellen Sie sicher, dass Recorder aktiviert ist und Daten aufbewahrt
- Überprüfen Sie die Integrationsprotokolle auf Import-Fehler

### Doppelte Ereignisse

Wenn Sie doppelte Tankvorgänge sehen:
- Überprüfen Sie das `data_quality`-Feld, um die Quelle zu identifizieren
- Historische Importe sollten vorhandene Ereignisse überspringen
- Löschen Sie Duplikate über Dienste oder Speicherdatei-Bearbeitung

### Falsche Zeitstempel

Wenn Zeitstempel nicht mit tatsächlichen Tankterminen übereinstimmen:
- Überprüfen Sie, ob Ihr Tankfüllstand-Sensor korrekt aktualisiert wird
- Stellen Sie sicher, dass Sensor-Zeitstempel genau sind
- Überprüfen Sie Vertrauens-Scores - geringes Vertrauen kann auf Zeitstempel-Unsicherheit hinweisen
- Historischer Import verwendet den Zeitstempel der Tankfüllstandsänderung

## Beispiele

### Vollständige Dashboard-Karte

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Tankübersicht
    entities:
      - entity: sensor.your_car_refueling_log
        name: Gesamte Ereignisse
      - type: attribute
        entity: sensor.your_car_refueling_log
        attribute: status
        name: Status
  
  - type: markdown
    content: |
      ### Letzter Tankvorgang
      {% set last = state_attr('sensor.your_car_refueling_log', 'last_refueling') %}
      {% if last %}
      **{{ last.timestamp | as_datetime | as_local }}**
      - {{ last.liters }} L @ {{ last.station }}
      - Kosten: {{ last.cost }} €
      {% endif %}
  
  - type: markdown
    title: Letzte Ereignisse (Hohes Vertrauen)
    content: |
      {% set events = state_attr('sensor.your_car_refueling_log', 'recent_events') %}
      {% for event in events if event.confidence >= 0.7 %}
      **{{ event.timestamp | as_datetime | as_local }}**
      - {{ event.liters_refueled }} L bei {{ event.odometer_km }} km
      - {{ event.total_cost }} € ({{ event.price_per_liter }} €/L)
      {% endfor %}
  
  - type: markdown
    title: Ereignisse zur Überprüfung
    content: |
      {% set events = state_attr('sensor.your_car_refueling_log', 'recent_events') %}
      {% set low_conf = events | selectattr('confidence', '<', 0.7) | list %}
      {% if low_conf %}
      {% for event in low_conf %}
      ⚠️ **{{ event.timestamp | as_datetime | as_local }}** ({{ (event.confidence * 100) | round(0) }}%)
      - {{ event.liters_refueled }} L bei {{ event.odometer_km or 'Unbekannt' }} km
      - Qualität: {{ event.data_quality }}
      {% endfor %}
      {% else %}
      ✅ Alle Ereignisse haben hohes Vertrauen
      {% endif %}
```

## Verwandte Dokumentation

- [Datenspeicherung](DATA_STORAGE.md) - Speicher-Architektur
- [Datenaktualisierungsfrequenzen](DATA_UPDATE_FREQUENCIES_DE.md) - Aktualisierungsintervalle
- [Fehlerbehebung](TROUBLESHOOTING.md) - Häufige Probleme

## Unterstützung

Bei Problemen oder Fragen:
1. Überprüfen Sie den [Fehlerbehebungsleitfaden](TROUBLESHOOTING.md)
2. Überprüfen Sie die Home Assistant-Protokolle
3. Öffnen Sie ein Issue auf GitHub mit Protokollen und Konfiguration
