# Sensor Debug Explanation / Sensor-Debug-Erklärung

## Deutsch

### Problemanalyse

Sie haben zwei Hauptprobleme gemeldet:

#### 1. sensor.test_car_days_until_refuel zeigt "unknown"

**Attribute:**
- `data_source: no_vehicle_data`
- `data_points_used: 0`
- `forecast_recommendation: Waiting for consumption prediction and price history data`

**Ursache:**
Der Sensor zeigt "unknown", weil keine Fahrzeugdaten (Tank-Level oder Reichweite) empfangen werden. Der `data_source: no_vehicle_data` zeigt an, dass die Integration darauf wartet, dass Fahrzeugdaten verfügbar werden.

**Was bedeutet das?**
- Die Integration benötigt entweder einen Tank-Level-Sensor ODER einen Reichweiten-Sensor von Ihrem Fahrzeug
- Zusätzlich werden mindestens 5 Tankdaten-Punkte (Tankvorgänge) für Verbrauchsvorhersagen benötigt
- Aktuell: `data_points_used: 0` bedeutet, dass keine oder zu wenige Tankdaten vorhanden sind

**Lösung:**
1. Prüfen Sie, ob die Fahrzeug-Entities korrekt konfiguriert sind:
   - Tank-Level-Entity: `sensor.{name}_tank_level` sollte Werte liefern
   - Reichweiten-Entity: `sensor.{name}_range` sollte Werte liefern
2. Verwenden Sie den neuen `sensor.{name}_car_data_debug` Sensor, um zu prüfen, welche Daten empfangen werden
3. Führen Sie mindestens 5 Tankvorgänge durch (oder importieren Sie historische Daten)

#### 2. sensor.test_car_average_consumption_history zeigt null für "last_24h" und "last_7_days"

**Attribute:**
- `last_24h_consumption: null`
- `last_24h_km: 0`
- `last_7_days_consumption: null`
- `last_7_days_km: 0`
- Aber: `last_14_days` und `last_30_days` haben Daten

**Ursache:**
Dies ist **erwartetes Verhalten**, KEIN Fehler! Die Verbrauchsberechnung benötigt mindestens 2 Tankdaten-Punkte innerhalb des Zeitraums.

**Warum ist das so?**
Der Verbrauch wird zwischen zwei Tankvorgängen berechnet:
- **Verbrauch = (gefahrene Kilometer) / (getankte Liter) × 100**
- Mit nur 1 Tankvorgang kann kein Verbrauch berechnet werden
- Mit 0 Tankvorgängen erst recht nicht

**Beispiel:**
```
Letzte 24h (gleitendes Fenster – jetzt minus 24 Stunden):
  - 0 oder 1 Tankvorgang → null (erwartet)
  
Letzte 7 Tage (gleitendes Fenster – jetzt minus 7 Tage):
  - 0 oder 1 Tankvorgang → null (erwartet)
  
Letzte 14 Tage:
  - 2+ Tankvorgänge → Verbrauch wird berechnet ✓
  
Letzte 30 Tage:
  - 4+ Tankvorgänge → Verbrauch wird berechnet ✓
```

**Ist das ein Problem?**
Nein! Das System funktioniert korrekt. Je länger der Zeitraum, desto wahrscheinlicher sind 2+ Tankvorgänge vorhanden.

### Die neuen Debug-Sensoren

#### sensor.{name}_fuel_price_api_debug (vorher: api_debug)

Dieser Sensor wurde umbenannt für mehr Klarheit. Er zeigt:
- Status der Tankstellen-API-Anfragen
- Anzahl gefundener Tankstellen
- Fehler bei API-Anfragen
- Verwendete GPS-Position (Fahrzeug vs. konfiguriert)

#### sensor.{name}_car_data_debug (NEU)

Dieser neue Sensor hilft bei der Diagnose von Datenproblemen:

**Zeigt an:**
1. **Letzte empfangene Werte:**
   - `odometer_last_value` / `odometer_last_timestamp`
   - `tank_level_last_value` / `tank_level_last_timestamp`
   - `range_last_value` / `range_last_timestamp`
   - `position_last_value` / `position_last_timestamp`

2. **Datenqualität:**
   - `odometer_good_count` / `odometer_error_count`
   - `tank_good_count` / `tank_error_count`
   - etc.

3. **Berechnungs-Status:**
   - `trip_log_sufficient` - Ausreichend Daten für Fahrtenbuch? (true/false)
   - `refueling_log_sufficient` - Ausreichend Daten für Tankbuch? (true/false)
   - `average_consumption_history_sufficient` - Ausreichend für Verbrauchshistorie? (true/false)
   - `days_until_refuel_sufficient` - Ausreichend für Reichweitenvorhersage? (true/false)
   - `tank_level_sufficient` - Tank-Level-Sensor aktiv? (true/false)

4. **Empfehlungen:**
   - `recommendations` - Konkrete Handlungsempfehlungen zur Behebung fehlender Daten

**Verwendungsbeispiel:**

Wenn `sensor.{name}_days_until_refuel` "unknown" zeigt:
1. Öffnen Sie `sensor.{name}_car_data_debug`
2. Prüfen Sie `consumption_data_source`:
   - `no_vehicle_data` → Tank-Level oder Range-Sensor nicht konfiguriert oder keine Daten
   - `fallback_values` → Zu wenig Tankdaten (< 5 Tankvorgänge)
   - `historical_data` → Gut, verwendet echte Fahrzeugdaten
3. Prüfen Sie `days_until_refuel_sufficient`:
   - `false` → Schauen Sie `days_until_refuel_data_count`
4. Lesen Sie `recommendations` für Lösungsvorschläge

### Weitere Vorschläge für die Debug-Entität

Folgende Informationen könnten noch hilfreich sein:

1. **API-Statistiken:**
   - Anzahl erfolgreicher/fehlgeschlagener API-Anfragen (gesamt)
   - Durchschnittliche API-Antwortzeit
   - Letzte API-Fehler (mit Zeitstempel)

2. **Daten-Alter:**
   - Wie alt sind die letzten empfangenen Daten?
   - Warnung wenn Daten > 24 Stunden alt

3. **Konfigurations-Prüfung:**
   - Sind alle konfigurierten Entities verfügbar?
   - Liste fehlender oder nicht verfügbarer Entities

4. **Verbrauchshistorie:**
   - Anzahl Tankdaten pro Zeitraum (heute/Woche/Monat)
   - Ältester/neuester Tankdatensatz

5. **Integrations-Status:**
   - Wann wurde die letzte erfolgreiche Aktualisierung durchgeführt?
   - Wie viele Aktualisierungen wurden durchgeführt (gesamt)?

---

## English

### Problem Analysis

You reported two main issues:

#### 1. sensor.test_car_days_until_refuel shows "unknown"

**Attributes:**
- `data_source: no_vehicle_data`
- `data_points_used: 0`
- `forecast_recommendation: Waiting for consumption prediction and price history data`

**Cause:**
The sensor shows "unknown" because no vehicle data (tank level or range) is being received. The `data_source: no_vehicle_data` indicates the integration is waiting for vehicle data to become available.

**What does this mean?**
- The integration needs either a tank level sensor OR a range sensor from your vehicle
- Additionally, at least 5 refueling data points are required for consumption predictions
- Currently: `data_points_used: 0` means no or insufficient refueling data exists

**Solution:**
1. Check if vehicle entities are correctly configured:
   - Tank level entity: `sensor.{name}_tank_level` should provide values
   - Range entity: `sensor.{name}_range` should provide values
2. Use the new `sensor.{name}_car_data_debug` sensor to check which data is being received
3. Perform at least 5 refueling events (or import historical data)

#### 2. sensor.test_car_average_consumption_history shows null for "last_24h" and "last_7_days"

**Attributes:**
- `last_24h_consumption: null`
- `last_24h_km: 0`
- `last_7_days_consumption: null`
- `last_7_days_km: 0`
- But: `last_14_days` and `last_30_days` have data

**Cause:**
This is **expected behavior**, NOT a bug! Consumption calculation requires at least 2 refueling data points within the time period.

**Why?**
Consumption is calculated between two refueling events:
- **Consumption = (kilometers driven) / (liters refueled) × 100**
- With only 1 refueling event, consumption cannot be calculated
- With 0 refueling events, even less so

**Example:**
```
Last 24h (rolling window – now minus 24 hours):
  - 0 or 1 refueling event → null (expected)
  
Last 7 days (rolling window – now minus 7 days):
  - 0 or 1 refueling event → null (expected)
  
Last 14 days:
  - 2+ refueling events → consumption calculated ✓
  
Last 30 days:
  - 4+ refueling events → consumption calculated ✓
```

**Is this a problem?**
No! The system is working correctly. The longer the time period, the more likely 2+ refueling events are present.

### The New Debug Sensors

#### sensor.{name}_fuel_price_api_debug (formerly: api_debug)

This sensor was renamed for clarity. It shows:
- Fuel station API request status
- Number of stations found
- API request errors
- GPS position used (vehicle vs. configured)

#### sensor.{name}_car_data_debug (NEW)

This new sensor helps diagnose data issues:

**Shows:**
1. **Last received values:**
   - `odometer_last_value` / `odometer_last_timestamp`
   - `tank_level_last_value` / `tank_level_last_timestamp`
   - `range_last_value` / `range_last_timestamp`
   - `position_last_value` / `position_last_timestamp`

2. **Data quality:**
   - `odometer_good_count` / `odometer_error_count`
   - `tank_good_count` / `tank_error_count`
   - etc.

3. **Calculation status:**
   - `trip_log_sufficient` - Enough data for trip log? (true/false)
   - `refueling_log_sufficient` - Enough data for refueling log? (true/false)
   - `average_consumption_history_sufficient` - Enough for consumption history? (true/false)
   - `days_until_refuel_sufficient` - Enough for range prediction? (true/false)
   - `tank_level_sufficient` - Tank level sensor active? (true/false)

4. **Recommendations:**
   - `recommendations` - Specific action recommendations to fix missing data

**Usage Example:**

If `sensor.{name}_days_until_refuel` shows "unknown":
1. Open `sensor.{name}_car_data_debug`
2. Check `consumption_data_source`:
   - `no_vehicle_data` → Tank level or range sensor not configured or no data
   - `fallback_values` → Insufficient refueling data (< 5 events)
   - `historical_data` → Good, using real vehicle data
3. Check `days_until_refuel_sufficient`:
   - `false` → Look at `days_until_refuel_data_count`
4. Read `recommendations` for solutions

### Additional Suggestions for the Debug Entity

The following information could be helpful:

1. **API Statistics:**
   - Number of successful/failed API requests (total)
   - Average API response time
   - Recent API errors (with timestamps)

2. **Data Age:**
   - How old is the last received data?
   - Warning if data > 24 hours old

3. **Configuration Check:**
   - Are all configured entities available?
   - List of missing or unavailable entities

4. **Consumption History:**
   - Number of refueling data points per period (today/week/month)
   - Oldest/newest refueling record

5. **Integration Status:**
   - When was the last successful update?
   - How many updates have been performed (total)?
