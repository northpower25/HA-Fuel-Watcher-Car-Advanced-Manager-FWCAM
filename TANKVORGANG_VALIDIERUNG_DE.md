# Validierung und Filterung von Tankvorgängen

## Problem

Test-Tankvorgänge (erstellt zum Testen von APIs oder Eingabeformularen) können Verbrauchsberechnungen verfälschen und zu unrealistischen Werten und Verwirrung führen. Ähnlich können falsch eingegebene Daten (falsche Kilometerstände, Daten usw.) dieselben Probleme verursachen.

## Lösung

Die Integration enthält jetzt ein automatisches Validierungssystem, das:
1. Verdächtige/ungültige Tankvorgänge erkennt
2. Diese von Verbrauchsberechnungen ausschließt
3. UI-Steuerelemente zur Verwaltung der Event-Validierung bereitstellt
4. Datenintegrität wahrt und gleichzeitig manuelle Überschreibung erlaubt

## Funktionsweise

### 1. Event-Validierung

Jeder Tankvorgang wird anhand mehrerer Kriterien validiert:

#### Zeitstempel-Validierung
- **Zukünftige Events**: Events mehr als 1 Stunde in der Zukunft werden markiert
- **Zweck**: Verhindert versehentlich eingegebene zukünftige Daten

#### Tankstellenname-Validierung
- **Test-Indikatoren**: Tankstellennamen mit "test", "api test", "demo", "example", "xxxx", "1111", "9999" werden markiert
- **Zweck**: Erkennt automatisch Test-/Demo-Events

#### Kraftstoffmenge-Validierung
- **Negativ/Null**: Kraftstoffmenge muss positiv sein
- **Unrealistisches Maximum**: Mehr als 200L wird als unrealistisch markiert
- **Zweck**: Fängt Dateneingabefehler ab

#### Kilometerstand-Validierung
- **Positive Werte**: Kilometerstand muss positiv sein
- **Zukünftiger Kilometerstand**: Kilometerstand deutlich höher als aktueller Fahrzeugkilometerstand wird markiert
- **Rückwärts-Progression**: Abnehmender Kilometerstand über Zeit wird markiert
- **Unrealistische Sprünge**:
  - Mehr als 200 km/h Durchschnittsgeschwindigkeit zwischen Events
  - Mehr als 5000 km in weniger als 24 Stunden
- **Zweck**: Stellt logische Progression der Kilometerstände sicher

### 2. Automatischer Ausschluss

Wenn die Validierung ein Problem erkennt:
1. Das Feld `excluded_from_calculation` des Events wird auf `True` gesetzt
2. Das Feld `exclusion_reason` erklärt, warum es ausgeschlossen wurde
3. Das Event bleibt im Protokoll, beeinflusst aber keine Berechnungen
4. Benutzer können Events manuell einschließen/ausschließen

### 3. Berechnungsfilterung

Die Funktion `calculate_consumption_history()` jetzt:
1. Überspringt Events wo `excluded_from_calculation` `True` ist
2. Protokolliert ausgeschlossene Events für Debugging
3. Meldet Ausschlusszahl in Debug-Logs

Beispiel Log-Ausgabe:
```
calculate_consumption_history(7 days): found 5/8 events in period (3 excluded from calculation)
Event id=123: EXCLUDED from calculation (reason: Auto-validation: Station name contains test indicator: 'test')
```

## Systemnutzung

### Automatischer Validierungs-Button

**Ort**: Device-Seite → "Validate Refueling Events" Button

**Funktion**:
1. Scannt alle Tankvorgänge
2. Validiert jeden anhand logischer Kriterien
3. Schließt verdächtige Events automatisch aus
4. Erzwingt Verbrauchsneuberechnung

**Button-Attribute**:
- `success`: Ob Validierung erfolgreich abgeschlossen
- `timestamp`: Wann Validierung durchgeführt wurde
- `total_events`: Gesamtzahl der Events
- `validated`: Geprüfte Events (nicht bereits ausgeschlossen)
- `newly_excluded`: Neu als ungültig markierte Events
- `already_excluded`: Bereits ausgeschlossene Events
- `excluded_event_ids`: Liste aller ausgeschlossenen Event-IDs

**Wann zu verwenden**:
- Nach Import historischer Daten
- Nach manueller Dateneingabe
- Wenn Verbrauchswerte unrealistisch erscheinen
- Periodisch zur Datenhygiene

### Manuelles Ein-/Ausschließen

Events können manuell über die Lovelace-Card verwaltet werden:

1. **Ausschlussstatus ansehen**:
   - Refueling Log Sensor zeigt `excluded_from_calculation` Feld
   - Aktuelle Events enthalten `exclusion_reason`

2. **Manuelle Überschreibung**:
   - Event über Lovelace-Card bearbeiten
   - `excluded_from_calculation` auf `true` oder `false` setzen
   - Optional benutzerdefinierten `exclusion_reason` hinzufügen

### Ausschlussinformationen anzeigen

**Refueling Log Sensor Attribute**:
```yaml
total_events: 10
total_excluded: 2
total_active: 8
status: "10 refueling events recorded (2 excluded from calculations)"

recent_events:
  - id: 123
    excluded_from_calculation: true
    exclusion_reason: "Auto-validation: Station name contains test indicator: 'test'"
    # ... weitere Felder
  - id: 124
    excluded_from_calculation: false
    exclusion_reason: null
    # ... weitere Felder
```

## Detaillierte Validierungskriterien

### Test-Event-Erkennung

**Löst Ausschluss aus wenn Tankstellenname enthält**:
- "test" (Groß-/Kleinschreibung ignoriert)
- "api test"
- "demo"
- "example"
- "xxxx"
- "1111"
- "9999"

**Beispiele die markiert würden**:
- "Test Tankstelle"
- "API Test Tankung"
- "Demo Event XXXX"

### Kilometerstand-Logik-Validierung

**Rückwärts-Progression Beispiel**:
```
Event #100: 2026-02-10, 2000 km ✓
Event #101: 2026-02-12, 1800 km ✗ (ging 200 km rückwärts)
```

**Unrealistischer Sprung Beispiel**:
```
Event #100: 2026-02-10 10:00, 2000 km ✓
Event #101: 2026-02-10 11:00, 2300 km ✗ (300 km in 1 Stunde = 300 km/h Durchschnitt)
```

**Validierung erlaubt**:
- Normale Fahrmuster (bis zu 200 km/h Durchschnitt)
- Bis zu 5000 km pro Tag (für Grenzfälle wie lange Reisen)
- Zeitabweichung bis zu 1 Stunde für zukünftige Events

## Integration mit bestehenden Features

### Datenqualitäts-Warnungen

Arbeitet zusammen mit dem Datenqualitäts-Warnsystem:
1. **Warnungen erkennen** verdächtige Muster in Ergebnissen
2. **Validierung verhindert** dass verdächtige Events Ergebnisse beeinflussen

**Workflow**:
1. Benutzer sieht Datenqualitätswarnung: "Heute zeigt 11111 km gefahren"
2. Benutzer drückt "Validate Refueling Events" Button
3. System schließt Test-Events automatisch aus
4. Verbrauch wird nur mit gültigen Daten neu berechnet
5. Warnung verschwindet

### Historischer Import

Während des historischen Datenimports:
1. Events werden mit Zeitstempeln aus historischen Daten erstellt
2. Auto-Validierung kann danach ausgeführt werden um Probleme zu bereinigen
3. Importierte Events mit niedriger Konfidenz benötigen möglicherweise manuelle Überprüfung

### Neuberechnung

Der bestehende "Recalculate Trip Statistics" Button:
1. Erzwingt Verbrauchsprognose-Update
2. Arbeitet mit validierten Daten (ausgeschlossene Events werden übersprungen)
3. Ergänzend zum Validierungs-Button

**Empfohlener Workflow**:
1. Zuerst Events validieren
2. Dann Statistiken neu berechnen

## Beispiele

### Beispiel 1: Test-Event nach API-Test

**Szenario**: Entwickler testet Telegram API durch Erstellen eines gefälschten Tankvorgangs

**Vor Validierung**:
```yaml
Event #50:
  station_name: "Test API Event"
  odometer_km: 5000
  liters_refueled: 40
  excluded_from_calculation: false
```

**Verbrauchsberechnung**: Schließt dieses Test-Event ein, verursacht unrealistische Werte

**Nach Drücken von "Validate Refueling Events"**:
```yaml
Event #50:
  station_name: "Test API Event"
  odometer_km: 5000
  liters_refueled: 40
  excluded_from_calculation: true
  exclusion_reason: "Auto-validation: Station name contains test indicator: 'test'"
```

**Verbrauchsberechnung**: Überspringt dieses Event, zeigt realistische Werte

### Beispiel 2: Falsche Kilometerstand-Eingabe

**Szenario**: Benutzer gibt versehentlich 12000 statt 1200 für Kilometerstand ein

**Vor Validierung**:
```yaml
Event #45: 2026-02-10, odometer: 1150 km ✓
Event #46: 2026-02-12, odometer: 12000 km (Tippfehler - sollte 1200 sein)
Event #47: 2026-02-14, odometer: 1250 km ✓
```

**Verbrauch zeigt**: Unrealistische 10850 km in 2 Tagen

**Nach Validierung**:
```yaml
Event #46:
  excluded_from_calculation: true
  exclusion_reason: "Auto-validation: Unrealistic distance: 10850 km in 48.0h vs event #45"
```

**Benutzeraktion**:
1. Sieht dass Event #46 ausgeschlossen ist
2. Bearbeitet Kilometerstand auf korrekten Wert (1200)
3. Setzt `excluded_from_calculation` zurück auf `false`
4. Neuberechnung

### Beispiel 3: Manuelle Überschreibung

**Szenario**: Benutzer erstellt absichtlich Test-Event zum Lernen, möchte es ausgeschlossen haben

**Aktion**:
1. Tankvorgang über Lovelace-Card erstellen
2. Event bearbeiten, `excluded_from_calculation: true` setzen
3. `exclusion_reason: "Training/Demo-Event"` setzen
4. Event bleibt im Protokoll, beeinflusst aber keine Berechnungen

## Best Practices

### Für Endbenutzer

1. **Validierung nach Import ausführen**: Immer validieren nach Import historischer Daten
2. **Ausschlüsse prüfen**: Ausgeschlossene Events im Refueling Log Sensor überprüfen
3. **Manuelle Korrekturen**: Tippfehler in Originaldaten korrigieren statt sie ausgeschlossen zu lassen
4. **Test-Events behalten**: Test-Events nicht löschen, nur für zukünftige Referenz ausschließen

### Für Entwickler/Tester

1. **Test-Indikatoren verwenden**: Test-Tankstellen mit "Test" oder "Demo" Präfix benennen
2. **Validierung ausführen**: Test-Daten mit Validierungs-Button bereinigen
3. **Manueller Ausschluss**: Für persistente Test-Events, manuell ausschließen
4. **Datenqualität**: Test-Daten wenn möglich von Produktionsdaten getrennt halten

## Fehlerbehebung

### Gültige Events werden ausgeschlossen

**Symptom**: Legitime Tankvorgänge werden als ausgeschlossen markiert

**Ursachen**:
- Tankstellenname enthält zufällig "test" (z.B. "Test Tankstelle GmbH")
- Ungewöhnliches Fahrmuster (sehr lange Reise, sehr hohe Durchschnittsgeschwindigkeit)

**Lösung**:
1. `exclusion_reason` in Event-Attributen prüfen
2. Manuell `excluded_from_calculation: false` setzen
3. Optional Schwellenwertanpassungen melden

### Test-Events werden nicht ausgeschlossen

**Symptom**: Test-Events sind nach Validierung noch in Berechnungen enthalten

**Ursachen**:
- Tankstellenname enthält keine Test-Indikatoren
- Event besteht alle Validierungsprüfungen

**Lösung**:
1. Event manuell bearbeiten
2. `excluded_from_calculation: true` setzen
3. `exclusion_reason: "Manuell - Test-Event"` setzen

## Zugehörige Dokumentation

- [REFUELING_EVENT_VALIDATION.md](REFUELING_EVENT_VALIDATION.md) - Vollständige englische Dokumentation
- [CONSUMPTION_DATA_QUALITY_FIX.md](CONSUMPTION_DATA_QUALITY_FIX.md) - Datenqualitäts-Warnsystem
- [VERBRAUCHSBERECHNUNG_ERKLAERT_DE.md](VERBRAUCHSBERECHNUNG_ERKLAERT_DE.md) - Wie die Verbrauchsberechnung funktioniert
