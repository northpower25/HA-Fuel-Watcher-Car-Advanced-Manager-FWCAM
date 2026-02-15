# Geolocation-Based Fuel Station Proximity Notification - Konzept

**Version:** 1.0  
**Datum:** 2026-02-10  
**Status:** Konzept / Planung

---

## Zusammenfassung

Dieses Dokument beschreibt das Konzept für eine Geolokalisierungs-basierte Funktion, die automatisch die günstigsten Tankstellen in der Nähe des Fahrzeugs findet und den Benutzer benachrichtigt, wenn sich das Fahrzeug einer dieser Tankstellen nähert.

---

## 1. Anforderungen

### 1.1 Funktionale Anforderungen

1. **Tankstellen-Auswahl:**
   - Suche der N günstigsten Tankstellen in einem konfigurierbaren Umkreis der aktuellen Fahrzeugposition
   - Konfigurierbare Anzahl der günstigsten Tankstellen (z.B. Top 3, 5 oder 10)
   - Konfigurierbare Suchradius für Geolokalisierung (z.B. 5-25 km)
   - Berücksichtigung des Kraftstofftyps (E5, E10, Diesel)
   - Optional: Filterung nach Öffnungszeiten (nur geöffnete Tankstellen)

2. **Näherungserkennung:**
   - Kontinuierliche Überwachung der Fahrzeugposition
   - Erkennung, wenn sich das Fahrzeug einer vorausgewählten günstigen Tankstelle nähert
   - Konfigurierbarer Schwellenwert für die Näherungserkennung (z.B. 500m, 1km, 2km)
   - Vermeidung von Spam-Benachrichtigungen (Cooldown-Mechanismus)

3. **Benachrichtigungsfunktion:**
   - Schreiben einer Warnung/Benachrichtigung in eine dedizierte Entität
   - Entität kann für Notify-Automationen (Telegram, HA Companion App, etc.) genutzt werden
   - Bereitstellung von nützlichen Informationen: Name, Adresse, Preis, Entfernung, Navigations-URLs

4. **Konfigurierbarkeit:**
   - Anzahl der zu trackenden günstigen Tankstellen
   - Suchradius für Tankstellenauswahl
   - Näherungsschwellenwert für Benachrichtigungen
   - Update-Intervall für Position und Tankstellendaten
   - Optional: Nur benachrichtigen, wenn Tank unter einem bestimmten Level

---

## 2. Technische Architektur

### 2.1 Neue Entitäten

#### 2.1.1 Sensor: Nearby Cheap Stations
- **Entitätstyp:** `sensor.{vehicle_name}_nearby_cheap_stations`
- **State:** Anzahl der gefundenen günstigen Tankstellen
- **Attributes:**
  - `stations`: Liste der N günstigsten Tankstellen mit vollständigen Details:
    ```json
    [
      {
        "id": "station_uuid",
        "name": "Tankstelle ABC",
        "brand": "Markenname",
        "address": "Straße 123, 12345 Stadt",
        "latitude": 50.000000,
        "longitude": 10.000000,
        "distance_km": 3.2,
        "price": 1.589,
        "fuel_type": "e10",
        "is_open": true,
        "google_maps_url": "...",
        "apple_maps_url": "...",
        "waze_url": "..."
      }
    ]
    ```
  - `last_update`: Zeitstempel der letzten Aktualisierung
  - `search_radius_km`: Verwendeter Suchradius
  - `vehicle_latitude`: Aktuelle Fahrzeugposition (Lat)
  - `vehicle_longitude`: Aktuelle Fahrzeugposition (Lon)
  - `max_stations`: Konfigurierte Anzahl zu trackender Tankstellen

#### 2.1.2 Binary Sensor: Proximity Alert
- **Entitätstyp:** `binary_sensor.{vehicle_name}_near_cheap_station`
- **State:** `on` wenn in der Nähe einer günstigen Tankstelle, sonst `off`
- **Device Class:** `presence` oder `proximity`
- **Attributes:**
  - `station_name`: Name der nahegelegenen Tankstelle
  - `station_address`: Adresse
  - `distance_km`: Aktuelle Entfernung
  - `price`: Aktueller Preis
  - `fuel_type`: Kraftstofftyp
  - `proximity_threshold_km`: Verwendeter Schwellenwert
  - `station_details`: Vollständige Tankstellendetails (wie oben)
  - `navigation_urls`: Objekt mit Google Maps, Apple Maps, Waze URLs
  - `alert_message`: Fertige Nachricht für Benachrichtigungen, z.B.:
    ```
    "🚗 Günstige Tankstelle in der Nähe!
    📍 Tankstelle ABC (1.2 km entfernt)
    💰 Preis: €1.589/L (E10)
    🧭 Navigation: [Link]"
    ```

#### 2.1.3 Number: Proximity Threshold
- **Entitätstyp:** `number.{vehicle_name}_proximity_alert_distance`
- **Min:** 0.1 km
- **Max:** 10.0 km
- **Default:** 1.5 km
- **Step:** 0.1 km
- **Zweck:** Konfigurierbarer Abstand für Näherungsalarm

#### 2.1.4 Number: Cheap Stations Count
- **Entitätstyp:** `number.{vehicle_name}_cheap_stations_count`
- **Min:** 1
- **Max:** 20
- **Default:** 5
- **Step:** 1
- **Zweck:** Anzahl der zu trackenden günstigen Tankstellen

#### 2.1.5 Number: Cheap Stations Radius
- **Entitätstyp:** `number.{vehicle_name}_cheap_stations_radius`
- **Min:** 1 km
- **Max:** 50 km
- **Default:** 15 km
- **Step:** 1 km
- **Zweck:** Suchradius für günstige Tankstellen

#### 2.1.6 Switch: Enable Proximity Alerts
- **Entitätstyp:** `switch.{vehicle_name}_proximity_alerts`
- **Default:** `on`
- **Zweck:** Näherungsalarme aktivieren/deaktivieren

### 2.2 Datenfluss

```
┌─────────────────────────────────────────────────────────────────┐
│                     Fahrzeugposition (GPS)                      │
│                  (device_tracker entity)                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Geolocation Service / Coordinator                  │
│  - Prüft Position alle X Sekunden (z.B. 30-60s beim Fahren)   │
│  - Erkennt Bewegung (Geschwindigkeit > 5 km/h)                 │
└────────────┬───────────────────────────┬────────────────────────┘
             │                           │
             ▼                           ▼
┌────────────────────────┐  ┌───────────────────────────────────┐
│  Tankstellensuche      │  │   Proximity Check                 │
│  (alle 5-10 Min oder   │  │   (alle 30-60s)                   │
│   bei Position Change) │  │                                   │
│                        │  │ - Berechnet Entfernung zu jeder   │
│ - API Call zu          │  │   günstigen Tankstelle            │
│   Tankerkönig          │  │ - Prüft gegen Schwellenwert       │
│ - Sortierung nach      │  │ - Triggert Binary Sensor          │
│   Preis                │  │ - Anti-Spam-Logik                 │
│ - Top N auswählen      │  │   (Cooldown, Hysterese)          │
└────────────┬───────────┘  └───────────┬───────────────────────┘
             │                           │
             ▼                           ▼
┌────────────────────────┐  ┌───────────────────────────────────┐
│ Sensor Update:         │  │ Binary Sensor Update:             │
│ nearby_cheap_stations  │  │ near_cheap_station                │
└────────────────────────┘  └───────────┬───────────────────────┘
                                        │
                                        ▼
                            ┌──────────────────────────────┐
                            │  Home Assistant Automation   │
                            │  - State Change Trigger      │
                            │  - Notify Service Call       │
                            └──────────────────────────────┘
```

---

## 3. Datenquellen-Analyse

### 3.1 Fahrzeugposition (Latitude/Longitude)

**Aktuelle Implementierung:**
- Position wird aus `device_tracker` Entity gelesen (siehe `utils/vehicle_data.py`)
- Funktion: `async_get_device_tracker_coordinates()`
- Quelle: `CONF_POSITION_ENTITY` aus Konfiguration

**Eignung für Geolokalisierung:**
✅ **Geeignet**
- Position wird direkt aus HA device_tracker bezogen
- Unterstützt verschiedene Tracker (z.B. HA Companion App, OwnTracks, etc.)
- Genauigkeit: GPS-basiert, typisch 5-30m, ausreichend für Tankstellensuche

**Timing & Aktualisierung:**
- Update-Frequenz abhängig vom device_tracker
- HA Companion App: Typisch 30-60s bei Bewegung, länger bei Stillstand
- OwnTracks: Konfigurierbar, kann sehr häufig sein (5-30s)
- Für Fahrt-Szenario: Meist 30-60s Updates, **ausreichend** für Tankstellennäherung

**Empfehlung:**
- ✅ Keine Änderung an Datenquelle erforderlich
- ⚠️ Zwischenspeicherung der letzten Position für Offline-Robustheit
- ⚠️ Geschwindigkeitsberechnung zur Erkennung von Bewegung/Stillstand
- ⚠️ Adaptive Update-Strategie: Häufiger prüfen bei Bewegung, seltener bei Stillstand

### 3.2 Tankstellendaten (Tankerkönig API)

**Aktuelle Implementierung:**
- API-Client: `providers/tankerkonig.py`
- Methode: `async_fetch_stations()` - Sucht Tankstellen in Radius
- Update-Intervall: Konfigurierbar via `CONF_UPDATE_INTERVAL` (1-60 Min)
- Caching: Ja, über Coordinator Update-Mechanismus

**Eignung für Geolokalisierung:**
✅ **Geeignet mit Anpassungen**
- API liefert Liste aller Tankstellen im Radius mit Preisen und Koordinaten
- Daten enthalten bereits: Name, Adresse, Lat/Lon, Preis, Status (offen/geschlossen)
- Haversine-Distanzberechnung bereits implementiert

**Timing & Aktualisierung:**
- Aktueller Standard: 5-60 Min (zu beachten: API Rate Limits!)
- **Für Geolokalisierung:**
  - Günstige Tankstellen: Update alle 10-15 Min ausreichend (Preise ändern sich nicht ständig)
  - Entfernungsberechnung: Sollte häufiger sein (alle 30-60s), aber **nur Distanz-Calc**, kein API-Call!

**Empfehlung:**
- ✅ Bestehende API-Daten wiederverwenden
- ✅ **Zwei-Stufen-Ansatz:**
  1. **Langsamer API-Update** (alle 10-15 Min): Holt Liste der günstigen Tankstellen
  2. **Schneller Proximity-Check** (alle 30-60s): Berechnet nur Entfernung zu bekannten Tankstellen
- ✅ Zwischenspeicherung der Top-N-Tankstellen in Memory/Storage
- ⚠️ Respekt vor API-Rate-Limits (Tankerkönig erlaubt typisch 1 Request/Min pro IP)

### 3.3 Tankfüllstand (Optional Filter)

**Aktuelle Implementierung:**
- `CONF_TANK_LEVEL_ENTITY` liefert aktuellen Tankstand
- Bereits für Refueling-Detection genutzt

**Eignung:**
✅ **Optional nutzbar**
- Könnte als Filter dienen: Nur benachrichtigen wenn Tank < 30%
- Verhindert unnötige Alerts bei vollem Tank

---

## 4. Genauigkeit vs. Schnelligkeit

### 4.1 Anforderungen beim Fahren

**Szenario:** Fahrer nähert sich einer günstigen Tankstelle bei 50 km/h (≈ 14 m/s)

| Update-Intervall | Zurückgelegte Strecke | Eignung               |
|------------------|-----------------------|-----------------------|
| 10 Sekunden      | ~140 Meter            | ⚠️ Könnte zu spät sein |
| 30 Sekunden      | ~420 Meter            | ✅ Akzeptabel          |
| 60 Sekunden      | ~840 Meter            | ⚠️ Grenzwertig         |
| 120 Sekunden     | ~1.68 km              | ❌ Zu langsam          |

**Empfehlung:**
- **Proximity-Check:** Alle 30-60 Sekunden
- **Vorwarnung:** Bei Schwellenwert von 1-2 km hat Fahrer ca. 1-2 Minuten Reaktionszeit
- **Dynamische Anpassung:** Bei höherer Geschwindigkeit (> 80 km/h) häufiger prüfen

### 4.2 Genauigkeitsanforderungen

**GPS-Genauigkeit:**
- Typisch: 5-30 Meter (Smartphone GPS)
- Ausreichend für: Ja! Tankstellen sind groß genug (50-100m Zufahrtsbereich)

**Distanzberechnung:**
- Haversine-Formel: Genau genug für < 50 km Entfernungen
- Bereits implementiert in `providers/tankerkonig.py`

**Schwellenwert-Empfehlung:**
- Minimum: 500 Meter (Innerstädtisch)
- Empfohlen: 1.5 km (Landstraße/Autobahn)
- Maximum: 5 km (bei sehr hoher Geschwindigkeit oder ländlicher Gegend)

### 4.3 Performance-Optimierung

**Speicher vs. Rechenzeit:**
1. **Zwischenspeicherung:**
   - Top-N günstige Tankstellen in Memory speichern
   - Nur Koordinaten und kritische Daten
   - Speicherbedarf: Minimal (< 10 KB für 10 Tankstellen)

2. **Distanzberechnung:**
   - Haversine für N Tankstellen: Sehr schnell (< 1ms für 10 Stationen)
   - Kann problemlos alle 30s laufen

3. **API-Calls:**
   - Sollten NICHT häufiger als alle 5-10 Min sein
   - Rate-Limiting beachten!

**Vorgeschlagene Update-Strategie:**
```python
# Pseudo-Code
API_UPDATE_INTERVAL = 10 * 60  # 10 Minuten
PROXIMITY_CHECK_INTERVAL_MOVING = 30  # 30 Sekunden wenn fahrend
PROXIMITY_CHECK_INTERVAL_STATIONARY = 300  # 5 Minuten wenn stehend
MOVEMENT_THRESHOLD = 5  # km/h

if vehicle_speed > MOVEMENT_THRESHOLD:
    # Fahrend: Häufige Proximity-Checks
    check_proximity_every(30 seconds)
else:
    # Stillstand: Seltene Checks
    check_proximity_every(5 minutes)

# API-Calls unabhängig vom Bewegungsstatus
fetch_cheap_stations_every(10 minutes)
```

---

## 5. Implementierungsvorschlag

### 5.1 Neue Komponenten

#### 5.1.1 Geolocation Service (`utils/geolocation_service.py`)
```python
class GeolocationService:
    """Service für Geolokalisierungs-basierte Tankstellen-Funktionen."""
    
    async def find_cheap_stations(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        count: int,
        fuel_type: str
    ) -> list[FuelStation]:
        """Findet die N günstigsten Tankstellen im Radius."""
        
    async def calculate_proximity(
        self,
        vehicle_lat: float,
        vehicle_lon: float,
        stations: list[FuelStation],
        threshold_km: float
    ) -> FuelStation | None:
        """Prüft ob Fahrzeug nahe einer Tankstelle ist."""
        
    def is_vehicle_moving(
        self,
        previous_position: tuple,
        current_position: tuple,
        time_delta: float
    ) -> bool:
        """Erkennt ob Fahrzeug sich bewegt."""
```

#### 5.1.2 Geolocation Coordinator (`geolocation_coordinator.py`)
```python
class GeolocationCoordinator(DataUpdateCoordinator):
    """Coordinator für Geolokalisierungs-Updates."""
    
    def __init__(self, ...):
        # Zwei Update-Intervalle:
        # - API-Update: 10 Min (holt günstige Tankstellen)
        # - Proximity-Check: 30-60s (prüft Entfernung)
        
    async def _async_update_data(self):
        """Führt Updates durch basierend auf Timing."""
        # Unterscheidet zwischen API-Update und Proximity-Check
```

#### 5.1.3 Neue Sensoren
- `GeolocationCheapStationsSensor`: Liste günstiger Tankstellen
- `GeolocationProximityBinarySensor`: Näherungsalarm
- Entsprechende Number/Switch Entities für Konfiguration

### 5.2 Konfiguration

**Config Flow Erweiterung:**
- Neuer Step: "Geolocation Settings" (optional)
- Felder:
  - Enable Geolocation Features (Boolean)
  - Number of cheap stations to track (1-20, default: 5)
  - Search radius for cheap stations (1-50 km, default: 15)
  - Proximity alert distance (0.1-10 km, default: 1.5)
  - Only alert when tank below % (0-100, default: 30)

**Options Flow Erweiterung:**
- Alle obigen Einstellungen sollten änderbar sein
- Plus: Enable/Disable Geolocation

### 5.3 Anti-Spam Mechanismus

**Problem:** Vermeidung von Spam-Benachrichtigungen
- Fahrer fährt an Tankstelle vorbei → Alert
- Fährt wieder weg → Alert off
- Fährt wieder hin → Alert (Spam!)

**Lösung: Cooldown + Hysterese**
```python
ALERT_COOLDOWN = 30 * 60  # 30 Minuten
HYSTERESIS_FACTOR = 1.3  # 30% mehr Entfernung zum Deaktivieren

if distance < threshold:
    if not alerted_recently(station_id, ALERT_COOLDOWN):
        trigger_alert()
elif distance > threshold * HYSTERESIS_FACTOR:
    deactivate_alert()
```

**Zusätzlich:**
- Pro Tankstelle tracken, wann zuletzt gewarnt wurde
- Persistente Speicherung in Storage
- Optional: Nach Tanken automatisch alle Alerts zurücksetzen

### 5.4 Automation-Beispiele

**Beispiel 1: Telegram-Benachrichtigung**
```yaml
automation:
  - alias: "Notify about nearby cheap station"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_near_cheap_station
        to: "on"
    condition:
      - condition: numeric_state
        entity_id: sensor.my_car_tank_level
        below: 30  # Nur wenn Tank unter 30%
    action:
      - service: notify.telegram
        data:
          message: >
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'alert_message') }}
```

**Beispiel 2: HA Companion App Notification mit Aktion**
```yaml
automation:
  - alias: "Cheap station proximity alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_near_cheap_station
        to: "on"
    action:
      - service: notify.mobile_app_smartphone
        data:
          title: "Günstige Tankstelle in der Nähe!"
          message: >
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'station_name') }}
            - {{ state_attr('binary_sensor.my_car_near_cheap_station', 'distance_km') }} km
            - €{{ state_attr('binary_sensor.my_car_near_cheap_station', 'price') }}/L
          data:
            actions:
              - action: "NAVIGATE"
                title: "Navigation starten"
                uri: >
                  {{ state_attr('binary_sensor.my_car_near_cheap_station', 'navigation_urls').google_maps }}
              - action: "IGNORE"
                title: "Ignorieren"
```

---

## 6. Zusätzliche Ideen und Features

### 6.1 Route-basierte Optimierung
**Idee:** Nicht nur aktuelle Position, sondern geplante Route berücksichtigen
- Integration mit Navigation (Google Maps, Apple Maps)
- Suche Tankstellen entlang der Route
- Priorisierung nach: Preis + Umweg in Minuten

**Herausforderung:**
- Benötigt Route-Daten (nicht standardmäßig in HA verfügbar)
- Komplexe Berechnung
- Eventuell externe API (Google Directions, OSRM)

**Bewertung:** 🔶 Medium-Term Feature, nicht für MVP

### 6.2 Tankstellenpräferenzen
**Idee:** Benutzer kann Tankstellen-Marken bevorzugen oder ausschließen
- Favoriten-Liste (z.B. "Nur Shell und Esso")
- Blacklist (z.B. "Nie Tankstelle XY")

**Implementation:**
- Neue Konfigurationsoption
- Filterung in `find_cheap_stations()`

**Bewertung:** ✅ Einfach zu implementieren, sinnvoll für Kundenbindungsprogramme

### 6.3 Zeitbasierte Optimierung
**Idee:** Lerne Preismuster und empfehle beste Tankzeit
- "Tankstelle X ist abends meist 5 Cent günstiger"
- ML-basierte Vorhersage

**Implementation:**
- Erweiterung des bestehenden ML-Engines
- Historische Preisdaten pro Tankstelle

**Bewertung:** 🔶 Interessant, aber komplex. Long-term Feature.

### 6.4 Crowdsourcing / Community-Features
**Idee:** Teilen von Tankstelleninformationen in Community
- "User hat bei Tankstelle X vor 5 Min getankt zu Preis Y"
- Echtzeit-Preis-Updates von Community

**Implementation:**
- Benötigt zentralen Server
- Datenschutz-Bedenken
- Konkurrenz zu Tankerkönig

**Bewertung:** ❌ Außerhalb des Scope, zu komplex

### 6.5 Integration mit Tank-Größe und Reichweite
**Idee:** Intelligente Alerts basierend auf Reichweite
- "Du hast noch 150km Reichweite, günstige Tankstelle in 20km"
- Berechne ob man Tankstelle erreichen kann

**Implementation:**
- Nutze bestehende Range-Daten
- Einfache Vergleichslogik

**Bewertung:** ✅ Sinnvoll und einfach! Sollte im MVP enthalten sein.

### 6.6 Preis-Verlauf und Trends pro Tankstelle
**Idee:** Zeige Preisverlauf der günstigen Tankstellen
- "Diese Tankstelle war letzte Woche 8 Cent teurer"
- Trend-Arrows (↗️ ↘️ →)

**Implementation:**
- Erweiterung der Storage um Preis-Historie pro Tankstelle
- Neue Attribute an Sensor

**Bewertung:** ✅ Nützlich, moderate Komplexität. Good-to-have für MVP.

### 6.7 Geofencing / Zonen
**Idee:** Definiere "Zonen" (z.B. Arbeitsweg) und nur dort suchen
- "Suche nur Tankstellen auf meinem Arbeitsweg"
- Zone Drawing auf Karte

**Implementation:**
- Polygon-basierte Geofencing
- HA Zone-Integration

**Bewertung:** 🔶 Interessant, aber komplex. Nicht für MVP.

---

## 7. Risiken und Herausforderungen

### 7.1 API Rate Limits
**Problem:** Tankerkönig API hat Limits
- Max ~10 Requests/Minute
- Bei vielen Nutzern könnte Integration geblockt werden

**Lösung:**
- Zwischenspeicherung nutzen (bereits implementiert)
- Update-Intervall nicht unter 5 Minuten
- Exponential Backoff bei Fehlern

### 7.2 Batterieverbrauch
**Problem:** Häufige GPS-Checks verbrauchen Batterie
- Besonders bei Smartphone als device_tracker

**Lösung:**
- Adaptive Update-Strategie (langsamer bei Stillstand)
- Optional: Nur aktivieren wenn Navigation aktiv
- Nutze HA Companion App Settings (die App optimiert bereits)

### 7.3 Offline-Situationen
**Problem:** Kein Internet während der Fahrt
- Keine API-Updates möglich
- GPS könnte trotzdem funktionieren

**Lösung:**
- Fallback auf letzte bekannte Daten
- Offline-Modus: Nutze Cache
- Status-Indikator in Sensor-Attributen

### 7.4 Datenschutz
**Problem:** Tracking von Fahrzeugposition
- Sensible Daten

**Lösung:**
- Alles lokal in HA (kein Cloud)
- Opt-in Feature
- Dokumentation über Daten-Nutzung

### 7.5 Komplexität für Benutzer
**Problem:** Viele neue Einstellungen
- Könnte überwältigend sein

**Lösung:**
- Sinnvolle Defaults
- Optional: "Quick Setup" Modus
- Gute Dokumentation

---

## 8. MVP (Minimum Viable Product) Definition

### Phase 1: Kern-Funktionalität ✅
**Must-Have:**
1. ✅ Sensor für günstige Tankstellen (Top N)
2. ✅ Binary Sensor für Proximity Alert
3. ✅ Number Entities für Konfiguration (Anzahl, Radius, Schwellenwert)
4. ✅ Basis-Proximity-Logik (Distanzberechnung)
5. ✅ Anti-Spam-Mechanismus (Cooldown)
6. ✅ Dokumentation und Beispiel-Automationen

**Nicht im MVP:**
- ❌ Route-basierte Optimierung
- ❌ ML-basierte Zeitvorhersagen
- ❌ Komplexe Geofencing

### Phase 2: Erweiterungen 🔶
**Nice-to-Have:**
1. 🔶 Tankstellenpräferenzen (Favoriten/Blacklist)
2. 🔶 Reichweiten-Integration (nur tanken wenn nötig)
3. 🔶 Preis-Trends pro Tankstelle
4. 🔶 Adaptive Update-Strategie (basierend auf Geschwindigkeit)

### Phase 3: Advanced Features 🔮
**Zukunft:**
1. 🔮 Route-basierte Optimierung
2. 🔮 ML-Preisprognosen pro Tankstelle
3. 🔮 Geofencing / Zonen
4. 🔮 Integration mit anderen Providern (international)

---

## 9. Zeitplan & Aufwand (Schätzung)

### Phase 1 (MVP)
**Aufwand:** ~20-30 Stunden
- Geolocation Service: 4h
- Coordinator: 4h
- Sensor Entities: 6h
- Number/Switch Entities: 2h
- Anti-Spam-Logik: 3h
- Tests: 4h
- Dokumentation: 4h
- Config/Options Flow: 3h

### Phase 2 (Erweiterungen)
**Aufwand:** ~15-20 Stunden
- Präferenzen: 4h
- Reichweiten-Integration: 3h
- Preis-Trends: 5h
- Adaptive Updates: 3h
- Tests & Docs: 5h

---

## 10. Entscheidungsmatrix

| Feature                        | Komplexität | Nutzen | Priorität | MVP |
|--------------------------------|-------------|--------|-----------|-----|
| Günstige Tankstellen Sensor    | Niedrig     | Hoch   | 1         | ✅  |
| Proximity Binary Sensor        | Niedrig     | Hoch   | 1         | ✅  |
| Konfigurierbare Schwellenwerte | Niedrig     | Hoch   | 1         | ✅  |
| Anti-Spam-Mechanismus          | Mittel      | Hoch   | 1         | ✅  |
| Tankstellenpräferenzen         | Niedrig     | Mittel | 2         | 🔶  |
| Reichweiten-basiertes Filtern  | Niedrig     | Hoch   | 2         | 🔶  |
| Preis-Trends pro Tankstelle    | Mittel      | Mittel | 2         | 🔶  |
| Adaptive Update-Strategie      | Mittel      | Mittel | 2         | 🔶  |
| Route-basierte Optimierung     | Hoch        | Hoch   | 3         | 🔮  |
| ML-Zeitvorhersagen             | Hoch        | Mittel | 3         | 🔮  |
| Geofencing                     | Hoch        | Niedrig| 3         | 🔮  |

---

## 11. Empfohlener Startpunkt

### Option A: Vollständige Integration (Empfohlen ✅)
**Start mit Phase 1 (MVP)**
- Implementiere alle Kern-Features
- Gut getestet und dokumentiert
- Benutzer können sofort nutzen

**Vorteile:**
- Komplette Funktionalität
- Professioneller Release
- Gute Basis für zukünftige Erweiterungen

**Nachteile:**
- Mehr Entwicklungszeit
- Größerer Testing-Aufwand

### Option B: Minimaler Start
**Nur kritische Features**
- Nur günstige Tankstellen Sensor
- Kein Proximity Alert (Benutzer macht Automation selbst)

**Vorteile:**
- Schneller Release
- Weniger Komplexität

**Nachteile:**
- Unvollständig
- Benutzer muss mehr selbst konfigurieren
- Weniger intuitiv

### ⭐ Empfehlung: Option A
Die Entwicklung von Phase 1 (MVP) ist überschaubar (~20-30h) und liefert eine vollständige, professionelle Lösung. Der Mehrwert gegenüber Option B rechtfertigt den zusätzlichen Aufwand.

---

## 12. Nächste Schritte

1. ✅ **Dieses Konzept reviewen und freigeben**
2. ⬜ **Technisches Design erstellen**
   - Detaillierte Klassendiagramme
   - API-Spezifikationen
   - Datenbankschema
3. ⬜ **Prototyp entwickeln**
   - Geolocation Service
   - Basis-Coordinator
4. ⬜ **MVP implementieren**
   - Alle Phase-1-Features
5. ⬜ **Testen und Dokumentieren**
   - Unit Tests
   - Integration Tests
   - Benutzer-Dokumentation
6. ⬜ **Release vorbereiten**
   - CHANGELOG
   - Migration Guide
   - Beispiel-Konfigurationen

---

## 13. Offene Fragen

1. **Soll Geolocation standardmäßig aktiviert sein?**
   - Vorschlag: Opt-in (aus Datenschutz- und Batterie-Gründen)

2. **Welche Default-Werte für Schwellenwerte?**
   - Vorschlag: 
     - Anzahl Tankstellen: 5
     - Suchradius: 15 km
     - Proximity-Schwellenwert: 1.5 km

3. **Soll das Feature in Config Flow oder nur Options Flow konfigurierbar sein?**
   - Vorschlag: Optional in Config Flow, voll einstellbar in Options Flow

4. **Brauchen wir eine separate Dokumentations-Seite?**
   - Vorschlag: Ja, `docs/GEOLOCATION_GUIDE.md` und `docs/GEOLOCATION_GUIDE_DE.md`

5. **Integration in Custom Card?**
   - Vorschlag: Phase 2 - Zeige günstige Tankstellen + Map in Card

---

## 14. Zusammenfassung

### ✅ Machbarkeit
Die Geolokalisierungs-Funktion ist **technisch machbar** und gut in die bestehende Architektur integrierbar.

### ✅ Datenquellen
Sowohl GPS-Position als auch Tankstellendaten sind **ausreichend genau und aktuell** für diesen Zweck.

### ✅ Performance
Durch **intelligente Caching-Strategie** (API-Calls alle 10 Min, Proximity-Checks alle 30-60s) ist die Performance kein Problem.

### ✅ Benutzerfreundlichkeit
Durch **sinnvolle Defaults** und **optionale Konfiguration** ist das Feature leicht zu nutzen ohne überwältigend zu sein.

### ⚠️ Herausforderungen
- API Rate Limits (gelöst durch Caching)
- Batterieverbrauch (gelöst durch adaptive Updates)
- Anti-Spam (gelöst durch Cooldown + Hysterese)

### 🎯 Empfehlung
**Start mit Phase 1 (MVP)** - liefert vollständige, professionelle Lösung mit allen Kern-Features.

---

**Ende des Konzeptdokuments**

*Feedback und Vorschläge willkommen!*
