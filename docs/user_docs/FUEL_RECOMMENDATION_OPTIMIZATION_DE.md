# Optimierung der Tankempfehlung - Implementierungszusammenfassung

## Überblick
Diese Implementierung fügt haFWCMA erweiterte Tankempfehlungsfunktionen hinzu und löst das Problem der Optimierung von Tankempfehlungen basierend auf Fahrverhalten, historischen Preismustern und intelligenter Positionsverfolgung.

## Implementierte Funktionen

### 1. Abkühlmechanismus bei Positionsänderungen

**Gelöstes Problem:** 
Große Preissprünge beim Fahren von einer Region mit hohen Preisen in eine Region mit niedrigen Preisen führten zu irreführenden Empfehlungen (z.B. "toller Preis!", obwohl die Preise in der neuen Region eigentlich nicht so gut sind).

**Lösung:**
- **PositionTracker**-Klasse überwacht Fahrzeugpositionsänderungen
- Aktiviert Abkühlphase wenn:
  - Fahrzeug bewegt sich ≥50km UND
  - Preis ändert sich um ≥0,10€/L
- Während der Abkühlphase (30 Minuten):
  - Empfehlungen werden pausiert
  - Benutzer sieht Nachricht: "⏸️ Bewegung XXkm mit Preisänderung von €X,XXX/L. Empfehlungen vorübergehend pausiert."

**Konstanten (im Code konfigurierbar):**
- `SIGNIFICANT_POSITION_CHANGE_KM = 50.0`
- `POSITION_CHANGE_COOLDOWN_MINUTES = 30`
- `PRICE_CHANGE_THRESHOLD_FOR_COOLDOWN = 0.10`

### 2. Multi-Radius-Tankstellenvergleich (10km vs 20km)

**Gelöstes Problem:**
Benutzer möchten wissen, ob es sich lohnt, weiter zu einer günstigeren Tankstelle zu fahren, unter Berücksichtigung der zusätzlichen Kraftstoffkosten für die Fahrt.

**Lösung:**
- Vergleicht günstigste Tankstellen innerhalb von 10km und 20km Radius
- Berechnet **echte Einsparungen** unter Berücksichtigung von:
  - Zu tankende Kraftstoffmenge (Tankkapazität - aktueller Füllstand)
  - Entfernung zur Tankstelle und zurück (Rundfahrt)
  - Auf der Fahrt verbrauchter Kraftstoff (basierend auf Durchschnittsverbrauch)
  - Preisunterschied pro Liter

**Beispielausgabe:**
```
station_comparison:
  10km:
    name: "Shell Frankfurt Hauptstraße"
    distance_km: 5.0
    price: 1.75
    total_cost: 71.22  # Inkl. Kraftstoff + Fahrtkosten
  20km:
    name: "Aral Offenbach Berliner Straße"
    distance_km: 15.0
    price: 1.65
    total_cost: 69.47
  savings: 1.76  # Euro
  savings_percent: 2.5
  comparison_recommendation: "💰 Spare €1,76 durch Fahrt zu Aral..."
```

**Empfehlungsnachrichten:**
- Einsparung > 2,00€: "💰 Spare €X,XX durch Fahrt zur [20km-Tankstelle]..."
- Einsparung 0,50€-2,00€: "💡 Kleine Einsparung von €X,XX möglich bei..."
- Einsparung ≈ 0€: "≈ Ähnliche Kosten..."
- Negative Einsparung: "🏆 Beste Wahl: [10km-Tankstelle]..."

### 3. Vorhersage-Empfehlung basierend auf historischen Preisen

**Gelöstes Problem:**
Benutzer möchten wissen, ob sie jetzt tanken oder warten sollten, basierend darauf, wann sie tanken müssen und historischen Preismustern.

**Lösung:**
- Analysiert historische Preise nach Wochentag
- Vergleicht vorhergesagten Tanktag mit historisch günstigsten Tagen
- Empfiehlt früheres Tanken wenn:
  - Vorhergesagter Tanktag typischerweise höhere Preise hat UND
  - Aktueller Preis nahe dem historischen Bestpreis ist

**Beispielszenario:**
- Vorhersage: Tanken erforderlich am Freitag
- Historische Daten: Freitags durchschnittlich 1,74€/L, Samstags durchschnittlich 1,65€/L
- Aktueller Preis: 1,67€/L
- **Empfehlung:** "📊 Prognose: Aktueller Preis (€1,67) ist nahe am historischen Bestwert! Freitag-Durchschnitt ist €1,74. Erwägen Sie jetzt zu tanken."

**Attribute hinzugefügt zu sensor.{fahrzeug}_days_until_refuel:**
```yaml
forecast_trend: "favorable_now" | "favorable_earlier" | "stable"
forecast_should_refuel: true | false
forecast_urgency: "low" | "medium" | "high"
forecast_recommendation: "Benutzerfreundliche Nachricht"
forecast_predicted_weekday: "Freitag"
forecast_predicted_avg_price: 1.74
forecast_cheapest_weekday: "Samstag"
forecast_cheapest_avg_price: 1.65
forecast_price_difference: 0.09
```

## Technische Implementierung

### Neues Modul: `refuel_recommendation_engine.py`

**Klassen:**
- `PositionTracker`: Verfolgt Positionsänderungen und verwaltet Abkühlphasen
  - `update(lat, lon, price)` → gibt Abkühlstatus zurück
  
**Funktionen:**
- `compare_stations_by_radius()`: Berechnet 10km vs 20km Vergleich
- `analyze_forecast_recommendation()`: Analysiert historische Preise für Vorhersage
- `_format_savings_recommendation()`: Formatiert benutzerfreundliche Nachrichten
- `_format_forecast_recommendation()`: Formatiert Vorhersagenachrichten

### Integrationspunkte

**In `sensor.py` → `HaFWCMACoordinator`:**
1. `_position_tracker` Initialisierung hinzugefügt
2. `_async_update_data()` modifiziert:
   - Ruft `position_tracker.update()` auf wenn Fahrzeugposition verfügbar
   - Überspringt Empfehlungen während Abkühlphase
   - Ruft `compare_stations_by_radius()` auf wenn nahegelegene Tankstellen verfügbar
   - Fügt `position_change_info` und `radius_comparison` zu Koordinatordaten hinzu

3. `_update_consumption_prediction()` modifiziert:
   - Ruft `analyze_forecast_recommendation()` nach Vorhersage auf
   - Fügt Vorhersageempfehlung zu Vorhersagedaten hinzu

**In `FuelPriceSensor`:**
- `station_comparison` Attribut mit 10km/20km Daten hinzugefügt
- `in_cooldown` und `cooldown_remaining_minutes` Attribute hinzugefügt

**In `ConsumptionPredictionSensor`:**
- Vorhersage-Attribute hinzugefügt:
  - `forecast_trend`
  - `forecast_should_refuel`
  - `forecast_urgency`
  - `forecast_recommendation`
  - Plus detaillierte Vorhersagedaten (Wochentage, Preise, Differenzen)

## Datenfluss

```
Coordinator Update
    ↓
1. Fahrzeugposition & Preis abrufen
    ↓
2. PositionTracker.update()
    ↓
3. Wenn Abkühlphase → Empfehlungen überspringen
   Wenn keine Abkühlphase → Empfehlungen generieren
    ↓
4. Wenn nearby_stations verfügbar → compare_stations_by_radius()
    ↓
5. Wenn consumption_prediction → analyze_forecast_recommendation()
    ↓
6. Daten zurückgeben mit:
   - position_change_info
   - radius_comparison
   - forecast_recommendation
    ↓
Sensoren zeigen Attribute an
```

## Nutzungsbeispiele

### Positionsänderungs-Abkühlphase in Aktion

**Szenario:** Benutzer fährt von München (1,80€/L) nach Stuttgart (1,65€/L)

1. Fahrzeugposition: München (48.1351°, 11.5820°)
2. Preis: 1,80€/L
3. *Fahrt 230km*
4. Fahrzeugposition: Stuttgart (48.7758°, 9.1829°)
5. Preis: 1,65€/L
6. **Abkühlphase aktiviert:**
   - Entfernung: 230km > 50km ✓
   - Preisänderung: 0,15€ > 0,10€ ✓
7. **Empfehlung:** "⏸️ Bewegung 230km mit Preisänderung von €0,150/L. Empfehlungen vorübergehend pausiert."
8. Nach 30 Minuten → Normale Empfehlungen werden fortgesetzt

### Tankstellenvergleich Beispiel

**Szenario:** Tank bei 20%, Kapazität 50L, Verbrauch 7L/100km

**10km Tankstelle:**
- Entfernung: 5km
- Preis: 1,75€/L
- Zu tankende Menge: 40L
- Rundfahrt: 10km
- Verbrauchter Kraftstoff: 0,7L
- Gesamtkosten: 70,00€ (Kraftstoff) + 1,22€ (Fahrt) = 71,22€

**20km Tankstelle:**
- Entfernung: 15km
- Preis: 1,65€/L
- Zu tankende Menge: 40L
- Rundfahrt: 30km
- Verbrauchter Kraftstoff: 2,1L
- Gesamtkosten: 66,00€ (Kraftstoff) + 3,47€ (Fahrt) = 69,47€

**Einsparung: 1,75€** → "💡 Kleine Einsparung von €1,75 möglich bei..."

### Vorhersage-Empfehlung Beispiel

**Szenario:** Heute ist Mittwoch, Vorhersage sagt, Sie brauchen Freitag Kraftstoff

**Historische Analyse:**
- Montag-Donnerstag: 1,70-1,74€/L Durchschnitt
- Freitag: 1,74€/L Durchschnitt
- Samstag: 1,65€/L Durchschnitt (günstigster)
- Sonntag: 1,66€/L Durchschnitt

**Aktueller Preis:** 1,67€/L

**Empfehlung:** "📊 Prognose: Aktueller Preis (€1,67) ist nahe am historischen Bestwert! Freitag-Durchschnitt ist €1,74. Erwägen Sie jetzt zu tanken."

## Konfiguration

Keine zusätzliche Konfiguration erforderlich. Die neuen Funktionen verwenden vorhandene:
- `tank_capacity`: Zur Berechnung der zu tankenden Menge
- `consumption_min_data_points`: Für Verbrauchshistorie (wird im Durchschnittsverbrauch verwendet)
- Preishistorie-Speicher: Für historische Analyse
- Daten nahegelegener günstiger Tankstellen: Für Radiusvergleich

## Leistungsaspekte

- **Positionsverfolgung:** Minimaler Overhead, einfache Entfernungsberechnung
- **Radiusvergleich:** Läuft nur wenn nearby_cheap_stations Daten verfügbar
- **Vorhersageanalyse:** Läuft nur während Verbrauchsvorhersage-Updates (konfigurierbares Intervall)
- **Speicher:** Kein zusätzlicher Speicher erforderlich, verwendet vorhandene price_history

## Validierung

Validierungstests bestätigen:
- ✓ Positionsverfolgung erkennt korrekt signifikante Bewegungen
- ✓ Abkühlphase wird nur ausgelöst wenn sowohl Entfernungs- als auch Preisschwellen erreicht sind
- ✓ Einsparungsberechnung berücksichtigt genau die Fahrtkosten
- ✓ Vorhersagelogik identifiziert korrekt günstigste Tage
- ✓ Empfehlungen sind benutzerfreundlich formatiert

## Zukünftige Verbesserungen

Mögliche Erweiterungen:
1. Abkühlphasen-Parameter über UI konfigurierbar machen
2. "Tageszeit"-Analyse zur Vorhersage hinzufügen (nicht nur Wochentag)
3. Verkehrsbedingungen in Fahrtkostenberechnungen berücksichtigen
4. Benutzerpräferenz hinzufügen: "Ich fahre gerne X km für Y Cent Ersparnis"
5. Historische Analyse: "Sie tanken normalerweise samstags um 14 Uhr"

## Geänderte Dateien

1. `custom_components/hafwcma/sensor.py`
   - PositionTracker Initialisierung hinzugefügt
   - Coordinator-Update-Logik modifiziert
   - Sensor-Attribute erweitert

2. `custom_components/hafwcma/utils/refuel_recommendation_engine.py` (NEU)
   - Vollständige Implementierung der neuen Funktionen

## Test-Empfehlungen

Für Benutzer zum Testen:
1. Fahren Sie >50km zwischen Regionen mit unterschiedlichen Preisen → Abkühlphase überprüfen
2. `station_comparison` Attribut am fuel_price Sensor überprüfen
3. Vorhersage-Attribute am days_until_refuel Sensor überprüfen
4. Überprüfen, ob Empfehlungen sinnvoll und umsetzbar sind
5. Protokolle auf Fehler oder Warnungen überwachen

## Fazit

Diese Implementierung bietet Benutzern:
- **Intelligentere Empfehlungen**, die nicht auf temporäre Preisänderungen beim Bewegen reagieren
- **Finanzielle Transparenz** durch Darstellung tatsächlicher Einsparungen unter Berücksichtigung der Fahrtkosten
- **Prädiktive Einblicke** basierend auf historischen Preismustern
- **Umsetzbare Informationen** zur Optimierung des Tankzeitpunkts

Alle Funktionen integrieren sich nahtlos in die bestehende haFWCMA-Funktionalität.
