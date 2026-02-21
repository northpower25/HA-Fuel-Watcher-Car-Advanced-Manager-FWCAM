# Behebung von Verbrauchsdaten-Qualitätsproblemen

## Problem

Nach der Implementierung von PR #140 können Verbrauchssensoren falsche oder verdächtige Werte anzeigen, wie z.B.:
- Sehr hohe tägliche km (z.B. 11.111 km an einem Tag)
- Identische Werte für verschiedene Zeiträume (heute und letzte Woche zeigen dieselben Daten)
- Unrealistisch niedrige oder hohe Verbrauchsraten

## Ursache

Diese Probleme treten typischerweise auf, wenn:
1. **Tankevents haben falsche Zeitstempel** - Alle Events wurden mit demselben aktuellen Zeitstempel versehen statt mit ihren historischen Daten
2. **Kilometerstände sind inkorrekt** - Manuelle Eingaben oder Import-Fehler haben unrealistische Kilometerstände erzeugt
3. **Probleme beim historischen Datenimport** - Kilometerstand-Historie wurde ohne entsprechende Tankfüllstands-Historie importiert

## Lösung

### 1. Validierungswarnungen in Logs

Das System fügt jetzt Validierungsprüfungen in `calculate_consumption_history()` hinzu, die verdächtige Muster erkennen:

```python
# Warnung wenn Durchschnitt 1000 km/Tag überschreitet (unrealistisch)
if avg_km_per_day > 1000:
    _LOGGER.warning(
        "VERDÄCHTIGE DATEN - Durchschnitt %.1f km/Tag (gesamt: %d km). "
        "Prüfen Sie Ihr Tankprotokoll auf Datenqualitätsprobleme.",
        avg_km_per_day, total_km
    )
```

Prüfen Sie Ihre Home Assistant Logs auf diese Warnungen, um problematische Daten zu identifizieren.

### 2. Sensor-Attribut-Warnungen

Der `ConsumptionHistorySensor` enthält jetzt ein `data_quality_warning` Attribut, wenn verdächtige Daten erkannt werden:

- **Hohe tägliche km Warnung**: "Heute zeigt 11111 km gefahren, was ungewöhnlich hoch ist..."
- **Identische Zeitraum-Warnung**: "Letzte Woche und heute zeigen nahezu identische km..."

Diese Warnungen leiten Benutzer an:
1. Tankprotokoll auf falsche Daten prüfen
2. Neuberechnungs-Button verwenden um Vorhersagen zu aktualisieren
3. Historische Daten bei Bedarf neu importieren

### 3. Verbrauchsprognose funktioniert korrekt (Erwartetes Verhalten)

Es ist **normal und korrekt**, dass alle Prognosezeiträume dieselbe Verbrauchsrate (L/100km) zeigen:

```
tomorrow_consumption: 1.69
next_week_consumption: 1.69  ← Dies ist KORREKT!
next_14_days_consumption: 1.69
next_month_consumption: 1.69
```

**Warum?** Die Verbrauchsrate (L/100km) ist die Effizienz Ihres Fahrzeugs, die sich nicht täglich ändert. Was sich ÄNDERT ist:
- Erwartete gefahrene km (basierend auf Wochentagsmustern)
- Erwartete Kraftstoffkosten (tomorrow_cost, next_week_cost, etc.)

Die Prognose verwendet dieselbe Verbrauchsrate, wendet sie aber auf unterschiedliche erwartete Strecken an.

## Datenprobleme beheben

### Option 1: Neuberechnungs-Button (Empfohlen)

1. Gehen Sie zu Ihrem Fahrzeug-Device in Home Assistant
2. Drücken Sie den **"Recalculate Trip Statistics"** Button
3. Dies erzwingt eine neue Berechnung der Verbrauchsprognose
4. Warten Sie auf das nächste Coordinator-Update (typischerweise 5 Minuten)
5. Prüfen Sie, ob die Warnungen behoben sind

### Option 2: Historische Daten neu importieren

Wenn Tankevents falsche Zeitstempel haben:

1. Gehen Sie zu Ihrem Fahrzeug-Device
2. Drücken Sie den **"Import Historical Vehicle Data"** Button
3. Das System wird:
   - Kilometerstand-Historie aus dem Recorder importieren
   - Tankfüllstands-Historie aus dem Recorder importieren
   - Tankevents aus Tankfüllstands-Erhöhungen erkennen
   - Kilometerstände zu Tankevents nach Zeitstempel zuordnen
4. Warten Sie bis der Import abgeschlossen ist
5. Prüfen Sie die Import-Ergebnisse in den Button-Attributen

**Wichtig**: Dies erfordert SOWOHL Kilometerstand ALS AUCH Tankfüllstand Sensor-Historie in der Home Assistant Recorder-Datenbank.

### Option 3: Manuelle Korrektur

Wenn bestimmte Tankevents falsche Daten haben:

1. Öffnen Sie die **Refueling Log Sensor** Attribute
2. Identifizieren Sie Events mit verdächtigen Kilometerständen oder Zeitstempeln
3. Bearbeiten oder löschen Sie diese Events über die Lovelace Card
4. Verwenden Sie den Neuberechnungs-Button um Vorhersagen zu aktualisieren

## Vorbeugung

Um zukünftige Datenqualitätsprobleme zu vermeiden:

1. **Richtige Sensorkonfiguration sicherstellen**: Konfigurieren Sie sowohl Kilometerstand- als auch Tankfüllstand-Sensoren
2. **Historische Imports verifizieren**: Prüfen Sie, dass Tankfüllstands-Historie verfügbar ist vor dem Import
3. **Warnungen überwachen**: Prüfen Sie Sensor-Attribute regelmäßig auf Datenqualitätswarnungen
4. **Auto-Erkennung verwenden**: Lassen Sie das System Tankungen aus Tankfüllstands-Änderungen erkennen statt manuelle Eingabe

## Technische Details

### Verbrauchshistorie-Berechnung

Für jeden Zeitraum (heute, letzte Woche, 14 Tage, 30 Tage):

1. Tankevents nach Zeitstempel-Cutoff filtern
2. Events chronologisch sortieren
3. Für jedes aufeinanderfolgende Event-Paar:
   - Gefahrene km berechnen: `nächster_kilometerstand - aktueller_kilometerstand`
   - Verbrauchten Kraftstoff holen: `liters_refueled` vom aktuellen Event
4. Summen bilden: `total_km`, `total_liters`
5. Durchschnitt berechnen: `(total_liters / total_km) * 100`

**Wichtige Erkenntnis**: Wenn alle Tankevents denselben Zeitstempel haben, fallen sie alle in den "heute" Bereich, wodurch heute und letzte Woche identische Werte zeigen.

### Validierungsschwellen

- **Tägliche km Warnung**: > 1000 km/Tag Durchschnitt
- **Zeitraum-Ähnlichkeit**: < 1% Unterschied zwischen heute und Wochensummen

Diese Schwellen sind konservativ um False Positives zu vermeiden, während offensichtliche Datenfehler erkannt werden.

## Beispiel-Szenario

**Problem**: Nach historischem Import zeigt der Sensor:
```
last_24h_km: 11111
last_7_days_km: 11111
```

**Diagnose**: 
- Logs prüfen: "SUSPICIOUS DATA - Average 11111.0 km/day"
- Attribute prüfen: `data_quality_warning` erscheint
- Tankprotokoll prüfen: Alle Events haben Zeitstempel "2026-02-17T16:00:00"

**Lösung**:
- Events wurden mit aktuellem Zeitstempel statt historischen Daten importiert
- Neu importieren mit richtiger Tankfüllstands-Historie für korrekte Zeitstempel
- ODER Event-Zeitstempel manuell im Tankprotokoll aktualisieren
- Neuberechnungs-Button drücken zum Aktualisieren

## Zugehörige Dokumentation

- [CONSUMPTION_DATA_QUALITY_FIX.md](CONSUMPTION_DATA_QUALITY_FIX.md) - Vollständige englische Dokumentation
- [VERBRAUCHSBERECHNUNG_ERKLAERT_DE.md](VERBRAUCHSBERECHNUNG_ERKLAERT_DE.md) - Wie die Verbrauchsberechnung funktioniert
