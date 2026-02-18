# Kostenvergleich Tankstellen - Dokumentation

## Übersicht

Der Kostenvergleich ermittelt, ob es sich lohnt, zu einer weiter entfernten aber günstigeren Tankstelle zu fahren. Dabei werden **alle relevanten Kosten** berücksichtigt:

- **Kraftstoffpreis an der Tankstelle**
- **Zusätzlich verbrauchter Kraftstoff** für die Hin- und Rückfahrt
- **Zu tankende Menge** (leerer Tank wird berücksichtigt)

## Konfiguration

### Neue Konfigurationsoptionen

Die Kostenvergleichsfunktion nutzt folgende konfigurierbare Parameter:

| Entity | Beschreibung | Standard | Bereich |
|--------|--------------|----------|---------|
| `number.{car}_cheap_near_stations_radius` | Radius für "nahe" Tankstellen in km | 10.0 km | 1.0 - 30.0 km |
| `number.{car}_cheap_stations_radius` | Radius für "ferne" Tankstellen (Gesamtsuchradius) in km | 15.0 km | 1.0 - 50.0 km |
| `sensor.{car}_average_consumption_history` | Durchschnittlicher Verbrauch aus Historie | - | Automatisch berechnet |

**Hinweis:** Der "Near Radius" sollte kleiner sein als der "Stations Radius". Der Vergleich findet zwischen der günstigsten Tankstelle im Near Radius und der günstigsten Tankstelle im gesamten Stations Radius statt.

## Berechnungsgrundlage

### Formeln

Die Berechnung erfolgt in mehreren Schritten:

#### 1. Zu tankende Menge
```
fuel_to_purchase = tank_capacity - current_tank_level
```

**Datenquellen:**
- `tank_capacity`: Aus Konfiguration (`CONF_TANK_CAPACITY`)
- `current_tank_level`: Von `sensor.{car}_tank_level` (in Litern)

#### 2. Kraftstoffverbrauch für Fahrt
```
round_trip_km = station_distance_km × 2
fuel_consumed = (round_trip_km × avg_consumption) / 100
```

**Datenquellen:**
- `station_distance_km`: Aus GPS-Koordinaten berechnet (Luftlinie)
- `avg_consumption`: Von `sensor.{car}_average_consumption_history` (in L/100km)

#### 3. Kosten an Tankstelle "Nah"
```
cost_fuel_near = fuel_to_purchase × price_near
cost_trip_near = fuel_consumed_near × price_near
total_cost_near = cost_fuel_near + cost_trip_near
```

**Datenquellen:**
- `price_near`: Aktueller Preis von Tankerkönig API
- `fuel_to_purchase`: Siehe Schritt 1
- `fuel_consumed_near`: Siehe Schritt 2

#### 4. Kosten an Tankstelle "Fern"
```
cost_fuel_far = fuel_to_purchase × price_far
cost_trip_far = fuel_consumed_far × price_far
total_cost_far = cost_fuel_far + cost_trip_far
```

**Datenquellen:**
- `price_far`: Aktueller Preis von Tankerkönig API
- `fuel_to_purchase`: Siehe Schritt 1
- `fuel_consumed_far`: Siehe Schritt 2

#### 5. Ersparnis berechnen
```
savings = total_cost_near - total_cost_far
savings_percent = (savings / total_cost_near) × 100
```

**Interpretation:**
- **Positiver Wert**: Ersparnis durch Fahrt zur ferneren Tankstelle
- **Negativer Wert**: Mehrkosten durch Fahrt zur ferneren Tankstelle

### Beispielrechnung

**Ausgangssituation:**
- Tankkapazität: 50 Liter
- Aktueller Tankstand: 10 Liter
- Durchschnittsverbrauch: 7.0 L/100km

**Tankstelle "Nah" (8 km entfernt):**
- Preis: 1.589 €/L
- Hin- und Rückfahrt: 16 km
- Verbrauch für Fahrt: (16 × 7.0) / 100 = 1.12 L

**Berechnung Tankstelle "Nah":**
```
Zu tanken: 50 - 10 = 40 L
Kosten Tanken: 40 × 1.589 = 63.56 €
Kosten Fahrt: 1.12 × 1.589 = 1.78 €
Gesamtkosten: 63.56 + 1.78 = 65.34 €
```

**Tankstelle "Fern" (14 km entfernt):**
- Preis: 1.539 €/L
- Hin- und Rückfahrt: 28 km
- Verbrauch für Fahrt: (28 × 7.0) / 100 = 1.96 L

**Berechnung Tankstelle "Fern":**
```
Zu tanken: 40 L
Kosten Tanken: 40 × 1.539 = 61.56 €
Kosten Fahrt: 1.96 × 1.539 = 3.02 €
Gesamtkosten: 61.56 + 3.02 = 64.58 €
```

**Ersparnis:**
```
Ersparnis = 65.34 - 64.58 = 0.76 €
Prozent = (0.76 / 65.34) × 100 = 1.2%
```

**Empfehlung:** Fahre zur ferneren Tankstelle und spare 0.76 €

## Status-Tabelle mit Praxisbeispielen

| Status | Beschreibung | Beispiel | Sensor-Attribut |
|--------|--------------|----------|-----------------|
| **Ersparnis positiv** | Lohnt sich zur ferneren Tankstelle zu fahren | `+2.50 € (save by driving to 15.0km radius)` | `costsaving_far_vs_near_station` |
| **Ersparnis negativ** | Lohnt sich NICHT zur ferneren Tankstelle zu fahren | `-1.20 € (costs more, stay within 10.0km)` | `costsaving_far_vs_near_station` |
| **Keine verschiedenen Tankstellen** | Dieselbe Tankstelle ist in beiden Radien die günstigste | `Not applicable - only one station available` | `costsaving_far_vs_near_station` |
| **Tank voll** | Tank ist bereits voll, kein Vergleich nötig | `Tank is full - no savings calculation` | `costsaving_far_vs_near_station` |
| **Keine Tankstellen verfügbar** | Keine Tankstellen in beiden Radien gefunden | `Waiting for station data` | `costsaving_far_vs_near_station` |
| **Nächste = Günstigste** | Die nächste Tankstelle ist auch die günstigste | `Not applicable - nearest is also cheapest` | `costsaving_far_vs_near_station` |
| **Nur eine Tankstelle** | Nur eine Tankstelle insgesamt gefunden | `Not applicable - only one station available` | `costsaving_far_vs_near_station` |
| **Warten auf Daten** | System startet oder lädt Daten | `Waiting for more data` | `costsaving_far_vs_near_station` |

## Detaillierte Attribut-Struktur

### `sensor.{car}_cheapest_station` Attribute

Wenn ein Vergleich möglich ist (`station_comparison`), werden folgende Daten bereitgestellt:

```yaml
station_comparison:
  comparison_type: "near_vs_far_radius"
  near_radius_km: 10.0
  far_radius_km: 15.0
  near:
    name: "JET Tankstelle"
    distance_km: 8.2
    price: 1.589
    round_trip_km: 16.4
    fuel_consumed: 1.15
    cost_fuel: 63.56
    cost_trip: 1.83
    total_cost: 65.39
  far:
    name: "ARAL Tankstelle"
    distance_km: 13.7
    price: 1.539
    round_trip_km: 27.4
    fuel_consumed: 1.92
    cost_trip: 2.95
    cost_fuel: 61.56
    total_cost: 64.51
  savings: 0.88
  savings_percent: 1.3
  comparison_recommendation: "💰 Save €0.88 by driving to ARAL Tankstelle (13.7km away)"
  fuel_to_purchase: 40.0
```

### Vergleichstypen (comparison_type)

1. **`near_vs_far_radius`**: Neuer konfigurierbarer Vergleich zwischen Near Radius und Far Radius
2. **`nearest_vs_cheapest`**: Automatischer Fallback wenn keine Tankstellen im Near Radius
3. **`10km_vs_20km`**: Legacy-Modus (Rückwärtskompatibilität)

## Empfehlungslogik

Die Empfehlung basiert auf folgenden Kriterien:

### 1. Signifikante Ersparnis (> 2.00 €)
```
💰 Save €2.50 by driving to ARAL (13.7km away) instead of JET (8.2km away)
```

### 2. Kleine Ersparnis (0.50 € - 2.00 €)
```
✅ Save €0.88 by driving to ARAL (13.7km away)
```

### 3. Minimale Ersparnis (0.00 € - 0.50 €)
```
✓ Minor savings of €0.25 at ARAL (13.7km away)
```

### 4. Keine Ersparnis / Verlust
```
⚠️ Stay at JET (8.2km away) - ARAL costs €1.20 more overall
```

## Verwendung in Automationen

### Beispiel: Benachrichtigung bei hoher Ersparnis

```yaml
automation:
  - alias: "Hohe Kraftstoffersparnis Benachrichtigung"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_car_cheapest_station
        attribute: savings
        above: 3.0
    condition:
      - condition: template
        value_template: "{{ state_attr('sensor.my_car_cheapest_station', 'station_comparison') is not none }}"
    action:
      - service: notify.mobile_app
        data:
          title: "💰 Kraftstoff-Ersparnis!"
          message: >
            {{ state_attr('sensor.my_car_cheapest_station', 'station_comparison')['comparison_recommendation'] }}
```

### Beispiel: Template für Dashboard

```yaml
type: markdown
content: |
  ## Tankstellen-Vergleich
  
  **Near Radius:** {{ state_attr('sensor.my_car_cheapest_station', 'station_comparison')['near_radius_km'] }} km
  **Far Radius:** {{ state_attr('sensor.my_car_cheapest_station', 'station_comparison')['far_radius_label'] | default('Alle Tankstellen') }}
  
  ### Tankstelle Nah
  - {{ state_attr('sensor.my_car_cheapest_station', 'station_comparison')['near']['name'] }}
  - Entfernung: {{ state_attr('sensor.my_car_cheapest_station', 'station_comparison')['near']['distance_km'] }} km
  - Preis: {{ state_attr('sensor.my_car_cheapest_station', 'station_comparison')['near']['price'] }} €/L
  - Gesamtkosten: {{ state_attr('sensor.my_car_cheapest_station', 'station_comparison')['near']['total_cost'] }} €
  
  ### Tankstelle Fern
  - {{ state_attr('sensor.my_car_cheapest_station', 'station_comparison')['far']['name'] }}
  - Entfernung: {{ state_attr('sensor.my_car_cheapest_station', 'station_comparison')['far']['distance_km'] }} km
  - Preis: {{ state_attr('sensor.my_car_cheapest_station', 'station_comparison')['far']['price'] }} €/L
  - Gesamtkosten: {{ state_attr('sensor.my_car_cheapest_station', 'station_comparison')['far']['total_cost'] }} €
  
  ### 💰 Ersparnis
  **{{ state_attr('sensor.my_car_cheapest_station', 'costsaving_far_vs_near_station') }}**
```

## Fehlerbehebung

### Problem: "Waiting for more data"
**Ursache:** Sensor hat noch keine Daten von der API erhalten
**Lösung:** Warten bis zur nächsten Aktualisierung (alle 10 Minuten)

### Problem: "Not applicable - only one station available"
**Ursache:** Nur eine Tankstelle im konfigurierten Radius gefunden
**Lösung:** `number.{car}_cheap_stations_radius` erhöhen

### Problem: Negative Ersparnis bei günstigerer Tankstelle
**Ursache:** Die Fahrkosten übersteigen die Preisersparnis
**Erklärung:** Dies ist korrekt - die Gesamtkosten (Tanken + Fahrt) sind höher

### Problem: Verbrauch wird nicht berücksichtigt
**Ursache:** Keine Verbrauchsdaten in Historie
**Lösung:** 
1. Mindestens 3 Tankungen durchführen
2. Warten bis `sensor.{car}_average_consumption_history` Daten hat
3. Fallback nutzt DEFAULT_AVG_CONSUMPTION (7.5 L/100km)

## Hinweise

1. **Luftlinie vs. Straßenentfernung**: Die Entfernung wird als Luftlinie berechnet. Die tatsächliche Fahrtstrecke kann länger sein.

2. **Zeitersparnis nicht berücksichtigt**: Die Berechnung berücksichtigt nur monetäre Kosten, nicht die zusätzliche Fahrzeit.

3. **Aktuelle Preise**: Preise werden alle 10 Minuten von der Tankerkönig API aktualisiert.

4. **Tank nicht leer**: Die Berechnung geht davon aus, dass der Tank vollgetankt wird (bis zur Kapazität).

5. **Verbrauch dynamisch**: Der durchschnittliche Verbrauch basiert auf den letzten Tankungen und kann variieren.

## Weitere Informationen

- [Fuel Recommendation Optimization](FUEL_RECOMMENDATION_OPTIMIZATION_DE.md)
- [Geolocation Quickstart](GEOLOCATION_QUICKSTART.md)
- [Data Update Frequencies](DATA_UPDATE_FREQUENCIES_DE.md)
