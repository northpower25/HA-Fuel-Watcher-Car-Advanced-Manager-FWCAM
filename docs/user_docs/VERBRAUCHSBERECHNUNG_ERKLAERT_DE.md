# Verbrauchsberechnung - Wie es funktioniert

## Sensor-Attribute verstehen

### Das `data_source` Attribut

Wenn Sie sich verbrauchsbezogene Sensoren ansehen wie:
- `sensor.xxx_average_consumption_forecast`
- `sensor.xxx_average_consumption_history` 
- `sensor.xxx_days_until_refuel`

Sehen Sie möglicherweise ein Attribut namens `data_source` mit einem dieser Werte:

#### 1. `"historical_data"` ✅ **Das ist GUT!**
- Ihre Verbrauchsprognosen basieren auf **echten Daten** Ihres Fahrzeugs
- Das System hat Ihre Tankhistorie und Kilometerstände analysiert
- Dies liefert **genaue, personalisierte** Verbrauchsschätzungen
- **Dies ist der erwartete und gewünschte Zustand**, wenn Sie genügend Daten haben

#### 2. `"ml_enhanced"` ⭐ **Das ist NOCH BESSER!**
- Maschinelles Lernen wurde auf Ihre historischen Daten angewendet
- Wochentags-Fahrmuster werden erkannt (z.B. mehr Fahrten an Arbeitstagen)
- Noch genauere Vorhersagen basierend auf Verhaltensanalyse
- Erfordert ausreichende historische Daten zur Aktivierung

#### 3. `"fallback_values"` ⚠️ **Benötigt mehr Daten**
- Noch nicht genug historische Daten verfügbar
- System verwendet Standard-/konfigurierte Werte als Schätzungen
- Zur Verbesserung: Tankvorgänge hinzufügen und mehr fahren, um Verlauf aufzubauen
- Importieren Sie historische Daten mit den Import-Buttons, falls verfügbar

---

## Wie Verbrauchsberechnungen funktionieren

### 1. Datenerfassung

Die Integration verfolgt:
- **Kilometerstände** - von Ihrem Fahrzeug-Odometer-Sensor
- **Tankfüllstandsänderungen** - von Ihrem Tankfüllstandssensor
- **Tankvorgänge** - automatisch erkannt, wenn Tankstand steigt
- **Zeitstempel** - wann jeder Datenpunkt erfasst wurde

### 2. Verbrauchshistorie-Berechnung

Läuft bei **jedem Coordinator-Update** (typischerweise alle 5 Minuten):

```
Für jeden Zeitraum (heute, 7 Tage, 14 Tage, 30 Tage):
  1. Tankvorgänge innerhalb dieses Zeitraums filtern
  2. Gefahrene Strecke zwischen Tankvorgängen berechnen
  3. Verbrauchten Kraftstoff berechnen (aus Tankmengen)
  4. Berechnen: Verbrauch = (Liter / Kilometer) * 100
```

**Ergebnis**: Durchschnitt L/100km für jeden Zeitraum

### 3. Verbrauchsprognose-Berechnung

Läuft **periodisch** (konfigurierbares Intervall, Standard: alle paar Stunden):

```
1. Prüfen, ob genügend historische Daten vorhanden sind (mindestens 5 Datenpunkte)
2. Fahrmuster analysieren (tägliche km, Wochentagsmuster)
3. Durchschnittliche Verbrauchsrate berechnen
4. Tage bis zum nächsten Tankvorgang basierend auf aktuellem Tankstand vorhersagen
5. Schätzen, wann Sie das nächste Mal tanken müssen
```

**Ergebnis**: Vorhersagen mit Konfidenzwerten

### 4. Verbrauchsvorhersage-Berechnung

Läuft **nach Abschluss der Prognose**:

```
1. Verbrauchsprognosedaten übernehmen
2. Wochentagsfahrmuster anwenden (falls ML-erweitert)
3. Erwartete gefahrene km für verschiedene Zeiträume berechnen
4. Benötigten Kraftstoff und Kosten basierend auf historischen Preisen schätzen
```

**Ergebnis**: Kostenprognosen für morgen, nächste Woche, etc.

---

## Die Attribute verstehen

### Häufige Attribute bei Verbrauchssensoren

| Attribut | Bedeutung | Beispiel |
|-----------|---------|---------|
| `data_source` | Woher die Prognosedaten stammen | `"historical_data"` |
| `data_points_used` | Anzahl analysierter Datenpunkte | `957` |
| `data_points_required` | Minimum für Prognosen benötigt | `5` |
| `data_points_percentage` | Wie viele Daten Sie haben | `100` (bedeutet 100%+ verfügbar) |
| `last_prediction` | Wann Prognose zuletzt aktualisiert wurde | `2024-01-15T10:30:00` |
| `confidence` | Wie zuverlässig die Prognose ist | `0.85` (85% Konfidenz) |

### Was `data_points_percentage: 100` bedeutet

Dies bedeutet, Sie haben **100% oder mehr** der erforderlichen Datenpunkte:
- Erforderlich: Minimum 5 Datenpunkte
- Sie haben: 957 Datenpunkte
- Prozentsatz: (957 / 5) * 100 = **weit über 100%** (in Anzeige auf 100 begrenzt)
- **Status**: Exzellente Datenabdeckung ✅

---

## Den Neuberechnen-Button verwenden

### Was macht `button.xxx_recalculate_trip_statistics`?

Wenn Sie diesen Button drücken:

1. **Neuberechnung der Fahrtenstatistiken** aus gespeicherten Fahrtendaten
   - Gesamte gefahrene Strecke
   - Gesamter Kraftstoffverbrauch
   - Fahrtenkategorie-Zähler (geschäftlich/privat/Pendelverkehr)

2. **Erzwingt Aktualisierung der Verbrauchsprognose**
   - Setzt den Prognose-Intervall-Timer zurück
   - Veranlasst sofortige Neuberechnung der Prognosen beim nächsten Update
   - Aktualisiert alle Verbrauchssensoren mit frischen Daten

3. **Löst Coordinator-Aktualisierung aus**
   - Holt neueste Fahrzeugdaten
   - Führt alle Berechnungen mit neuen Daten durch
   - Aktualisiert alle Sensoren

### Wann den Neuberechnen-Button verwenden

- Nach dem Import historischer Daten
- Nach manuellem Hinzufügen/Bearbeiten von Tankvorgängen
- Wenn Sensorwerte veraltet erscheinen
- Nach Konfigurationsänderungen

---

## Die Import-Buttons verstehen

### `button.xxx_import_historical_vehicle_data`

**Was importiert wird**:
- Kilometerstände aus Home Assistant Verlauf
- Tankstandsänderungen aus Sensor-Verlauf
- Erkannte Tankvorgänge

**Wann zu verwenden**:
- Ersteinrichtung zum Aufbau der historischen Datenbank
- Nach Neuinstallation, um vergangene Daten zu erhalten
- Wenn Sie vorhandene Sensordaten haben, aber leere Tankhistorie

**Was NICHT importiert wird**:
- GPS-basierte Fahrtendaten (verwenden Sie dafür den anderen Button)

### `button.xxx_import_historical_trip_data`

**Was importiert wird**:
- GPS-Positionsverlauf vom Device Tracker
- Erkannte Fahrten basierend auf Standortänderungen
- Fahrten-Start-/Endpunkte und Routen

**Wann zu verwenden**:
- Wenn Trip-Tracking-Funktion aktiviert ist
- Zur Analyse historischer Fahrmuster
- Nach Aktivierung des Trip-Trackings, um vergangene Fahrten zu importieren

**Voraussetzungen**:
- Trip-Tracking muss in der Konfiguration aktiviert sein
- Fahrzeugpositions-Entity muss konfiguriert sein

---

## Fehlerbehebung

### "Warum zeigen meine Sensoren `data_source: historical_data`?"

**Antwort**: Das ist korrekt! Es bedeutet, dass Ihr System echte historische Daten von Ihrem Fahrzeug verwendet.

### "Warum aktualisiert der Neuberechnen-Button nicht sofort?"

**Antwort**: 
- **Vor diesem Fix**: Prognosen hatten Intervall-Drosselung
- **Nach diesem Fix**: Button erzwingt sofortige Neuberechnung
- Sie müssen möglicherweise die Integration neu laden oder HA neu starten, um das aktualisierte Button-Verhalten zu erhalten

### "Meine Prognosen zeigen niedrige Konfidenz"

**Mögliche Ursachen**:
1. Nicht genügend Tankvorgänge (mindestens 2 benötigt)
2. Unregelmäßige Tankmuster
3. Fehlende Kilometerstände
4. Kürzlich importierte Daten benötigen Zeit zur Verarbeitung

**Lösungen**:
- Normal weiterfahren und tanken
- Sicherstellen, dass Fahrzeugsensoren richtig konfiguriert sind
- Historische Daten importieren, falls verfügbar
- Auf mehr Datenakkumulation warten

### "Verbrauchswerte scheinen falsch"

**Prüfen Sie**:
1. Tankkapazität korrekt konfiguriert
2. Odometer-Sensor meldet in Kilometern (nicht Meilen)
3. Tankstandssensor meldet Prozent (0-100%)
4. Neueste Tankvorgänge sind korrekt protokolliert

---

## Datenanforderungen

### Minimale Daten für Prognosen

- **Mindestens 2 Tankvorgänge** mit Kilometerständen
- **Mindestens 5 Datenpunkte** insgesamt (konfigurierbar)
- Kilometerstände müssen zwischen Ereignissen steigen
- Zeitstempel müssen gültig und in Reihenfolge sein

### Optimale Daten für beste Prognosen

- **30+ Tage** Fahrverlauf
- **Regelmäßige Tankmuster** (wöchentlich oder häufiger)
- **Genaue Kilometerstände** (keine Lücken oder Sprünge)
- **Vollständige Tankstandsdaten**
- **Positionsdaten** für standortbasierte Funktionen (optional)

---

## Zusammenfassung

✅ **`data_source: "historical_data"` ist GUT** - es bedeutet, Ihr System funktioniert korrekt

✅ **`data_points_used: 957` ist EXZELLENT** - Sie haben reichlich Daten

✅ **Verwenden Sie den Neuberechnen-Button**, um sofortige Prognose-Aktualisierungen zu erzwingen

✅ **Import-Buttons** helfen beim Aufbau der historischen Datenbank aus vorhandenen Sensordaten

❌ **Keine Sorge**, wenn Sie "historical_data" sehen - es ist kein Fehler!
