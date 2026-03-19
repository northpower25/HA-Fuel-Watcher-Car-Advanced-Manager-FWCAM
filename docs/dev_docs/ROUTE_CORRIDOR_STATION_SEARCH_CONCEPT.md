# Routen-Korridor Tankstellensuche – Konzept / Route Corridor Station Search – Concept

**Version:** 1.1  
**Datum / Date:** 2026-03-19  
**Status:** Konzept (Offene Fragen beantwortet) / Concept (Open Questions Answered)  
**Priorität / Priority:** Hoch / High

---

## Zusammenfassung / Summary

### Deutsch
Dieses Dokument beschreibt das Konzept für eine intelligente Routenfunktion mit dynamischer Tankstellensuche entlang eines konfigurierbaren Korridors. Das System prognostiziert auf Basis des aktuellen Tankinhalts und des Verbrauchs, wann ein Tankstopp erforderlich ist, sucht proaktiv nach günstigen Tankstellen entlang der geplanten Route und benachrichtigt den Benutzer via Telegram, wenn sich besonders günstige Optionen im Korridor ergeben. Die Funktion berücksichtigt dabei auch den Umweg zur Tankstelle bei der Kostenoptimierung.

### English
This document describes the concept for an intelligent route function with dynamic fuel station search along a configurable corridor. The system predicts when a refueling stop will be needed based on the current fuel level and consumption rate, proactively searches for cheap stations along the planned route, and notifies the user via Telegram when particularly cheap options appear in the corridor. The detour distance to each station is also factored into the cost optimization.

---

## 1. Anforderungen / Requirements

### 1.1 Funktionale Anforderungen (DE) / Functional Requirements (EN)

#### 1.1.1 Routeneingabe vor Fahrtbeginn / Route Input Before Trip Start

**Deutsch:**
- Der Benutzer gibt vor Fahrtbeginn Ziel und optionale Zwischenziele ein
- Eingabe über **drei Kanäle** (beantwortet – Frage 2):
  - **FWCAM Lovelace-Dashboard** (Browser-Zugriff via HA-Frontend)
  - **HA Companion App** (iOS/Android – direkte Routeneingabe im Mobilkontext)
  - **Telegram-Bot** (Befehle `/route`, siehe Abschnitt 5)
- Unterstützung für Freitext-Adresseingabe mit Geocoding via OpenStreetMap Nominatim
- Unterstützung für GPS-Koordinaten
- Darstellung der geplanten Route in der Kartenansicht des FWCAM-Dashboards
- Optionale Angabe der bevorzugten Kraftstoffsorte (Standardmäßig aus Fahrzeugkonfiguration)
- **Geografischer Geltungsbereich: Deutschland** (TankerKönig API ist auf Deutschland beschränkt – beantwortet Frage 8)

**English:**
- The user enters the destination and optional waypoints before starting the trip
- Input via **three channels** (answered – Question 2):
  - **FWCAM Lovelace dashboard** (browser access via HA frontend)
  - **HA Companion App** (iOS/Android – direct route input in mobile context)
  - **Telegram bot** (commands `/route`, see Section 5)
- Support for free-text address input with geocoding via OpenStreetMap Nominatim
- Support for GPS coordinates
- Display of the planned route in the FWCAM dashboard map view
- Optional specification of the preferred fuel type (defaults to vehicle configuration)
- **Geographic scope: Germany only** (TankerKönig API is Germany-only – answers Question 8)

#### 1.1.2 Tankstopp-Prognose / Fuel Stop Prediction

**Deutsch:**
- Berechnung der voraussichtlichen Restreichweite aus aktuellem Tankstand und aktuellem Durchschnittsverbrauch
- Bestimmung des voraussichtlichen Tankstopppunkts auf der Route (Distanz × Verbrauch)
- Berücksichtigung eines konfigurierbaren Sicherheitspuffers (z.B. 15 % Restfüllstand)
- Wiederholende Neuberechnung während der Fahrt (bei jeder Positionsaktualisierung)
- **Fahrzeugposition via konfigurierter `device_tracker`-Entität** (beantwortet – Frage 3): Die in der Integration hinterlegte `device_tracker`-Entität liefert kontinuierlich GPS-Koordinaten und Geschwindigkeit zur Route-Projektion
- Anzeige des prognostizierten Tankstoppzeitpunkts/-orts als HA-Sensor-Attribut

**English:**
- Calculate estimated remaining range from current tank level and average consumption
- Determine the predicted refueling point on the route (distance × consumption)
- Respect a configurable safety buffer (e.g. 15 % remaining level)
- Repeated recalculation during the trip (on every position update)
- **Vehicle position via configured `device_tracker` entity** (answered – Question 3): the `device_tracker` entity registered in the integration continuously provides GPS coordinates and speed for route projection
- Display the predicted refueling point/time as an HA sensor attribute

#### 1.1.3 Korridor-basierte Tankstellensuche / Corridor-Based Station Search

**Deutsch:**
- Definition eines Korridors (Puffer links/rechts) um die geplante Route
- Konfigurierbare Korridorbreite (Standard: 5 km, Bereich: 1–50 km)
- Suche nach günstigen Tankstellen ausschließlich innerhalb dieses Korridors
- Berücksichtigung der Umwegdistanz (Strecke Hauptroute → Tankstelle → zurück) bei der Gesamtkostenberechnung
- Ranking der Tankstellen nach „effektivem Gesamtpreis" (Preis/Liter × benötigte Literzahl + Mehrkosten durch Umweg)
- Priorisierung von Tankstellen nahe dem prognostizierten Tankstoppunkt (±X km Fenster, konfigurierbar)

**English:**
- Define a corridor (buffer left/right) around the planned route
- Configurable corridor width (default: 5 km, range: 1–50 km)
- Search for cheap fuel stations exclusively within this corridor
- Account for the detour distance (main route → station → return) in the total cost calculation
- Rank stations by "effective total price" (price/litre × litres needed + cost of detour)
- Prioritise stations near the predicted refueling point (±X km window, configurable)

#### 1.1.4 Proaktive Telegram-Benachrichtigungen / Proactive Telegram Notifications

**Deutsch:**
- Beim Routenstart: Telegram-Nachricht mit dem prognostizierten Tankstoppplan und der empfohlenen Tankstelle
- Während der Fahrt: Regelmäßige Prüfung (konfigurierbar, Standard: alle 5 Minuten) ob eine günstigere Tankstelle im Korridor erschienen ist
- Telegram-Meldung, wenn eine Tankstelle mindestens X Cent/Liter günstiger ist als die aktuell empfohlene (konfigurierbarer Schwellenwert)
- Telegram-Meldung, wenn sich die Restreichweite dem letzten geplanten Tankstopp nähert (Warnschwelle konfigurierbar)
- Telegram-Nachrichten enthalten: Stationsname, Preis, Umweg-Distanz, effektiver Gesamtpreis, Navigationslinks (Google Maps, Waze, Apple Maps)

**English:**
- At route start: Telegram message with predicted fuel stop plan and recommended station
- During the trip: Regular check (configurable, default: every 5 minutes) for a cheaper station in the corridor
- Telegram alert if a station is at least X cents/litre cheaper than the currently recommended one (configurable threshold)
- Telegram alert when remaining range approaches the last planned fuel stop (threshold configurable)
- Telegram messages include: station name, price, detour distance, effective total price, navigation links (Google Maps, Waze, Apple Maps)

#### 1.1.5 Konfigurierbarkeit / Configurability

**Deutsch:**
- Korridorbreite (km): Standard 5 km
- Tankstopp-Sicherheitspuffer (%): Standard 15 %
- Preis-Differenzschwelle für Telegram-Alarm (€/l): Standard 0,03 €/l
- Benachrichtigungsintervall während der Fahrt (Minuten): Standard 5
- Suchfenster um Tankstopppunkt (km): Standard ± 20 km
- Kraftstoffsorte (aus Fahrzeugkonfiguration, überschreibbar)
- Anzahl vorzuschlagender Tankstellen: Standard 3 (Top-N)
- Aktivierung/Deaktivierung der Funktion per Schalter

**English:**
- Corridor width (km): default 5 km
- Fuel stop safety buffer (%): default 15 %
- Price difference threshold for Telegram alert (€/l): default 0.03 €/l
- Notification interval during trip (minutes): default 5
- Search window around predicted fuel stop point (km): default ± 20 km
- Fuel type (from vehicle config, overridable)
- Number of stations to suggest: default 3 (Top-N)
- Enable/disable toggle for the feature

---

## 2. Technische Architektur / Technical Architecture

### 2.1 Systemübersicht / System Overview

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                           Home Assistant                                            │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                        haFWCMA Integration                                    │  │
│  │                                                                               │  │
│  │  ┌──────────────────┐  ┌────────────────────────┐  ┌─────────────────────┐   │  │
│  │  │  FWCAM Lovelace  │  │   Telegram Bot         │  │  HA Companion App   │   │  │
│  │  │  Card (Browser)  │  │   (Eingabe/Ausgabe)    │  │  (iOS / Android)    │   │  │
│  │  │  - Routeneingabe │  │   - /route Befehl      │  │  - Routeneingabe    │   │  │
│  │  │  - Kartenansicht │  │   - Benachrichtigungen │  │  - Statusansicht    │   │  │
│  │  └────────┬─────────┘  └──────────┬─────────────┘  └──────────┬──────────┘   │  │
│  │           └─────────────────────── ┴──────────────────────────┘              │  │
│  │                                    │                                          │  │
│  │  ┌─────────────────────────────────┴──────────────────────────────────────┐  │  │
│  │  │   device_tracker Entität (GPS-Position + Geschwindigkeit)              │  │  │
│  │  │   → Route-Projektion + vorausschauende Korridor-Cache-Berechnung       │  │  │
│  │  └─────────────────────────────────┬──────────────────────────────────────┘  │  │
│  │                                    ▼                                          │  │
│  │  ┌──────────────────────────────────────────────────────────┐               │  │
│  │  │         utils/route_planner.py  (NEU / NEW)              │               │  │
│  │  │                                                          │               │  │
│  │  │  - Routenberechnung / Route calculation                  │               │  │
│  │  │  - Korridor-Polygon-Erzeugung / Corridor polygon         │               │  │
│  │  │  - Tankstopp-Prognose / Fuel stop prediction             │               │  │
│  │  │  - Tankstellen-Filterung / Station filtering             │               │  │
│  │  │  - Kostenoptimierung / Cost optimization                 │               │  │
│  │  │  - Vorausschauender Cache / Predictive cache             │               │  │
│  │  └───────────────────────────┬──────────────────────────────┘               │  │
│  │                              │                                               │  │
│  │           ┌──────────────────┼──────────────────┐                           │  │
│  │           │                  │                  │                           │  │
│  │           ▼                  ▼                  ▼                           │  │
│  │  ┌─────────────────┐ ┌──────────────┐ ┌──────────────────────────────────┐ │  │
│  │  │ providers/      │ │ utils/       │ │ utils/                           │ │  │
│  │  │ tankerkonig.py  │ │ geolocation  │ │ prediction_engine.py +           │ │  │
│  │  │ (Preisabfrage   │ │ .py          │ │ consumption_prediction.py        │ │  │
│  │  │  + 5-Min-Cache) │ │              │ │                                  │ │  │
│  │  └─────────────────┘ └──────────────┘ └──────────────────────────────────┘ │  │
│  │                              │                                               │  │
│  │                              ▼                                               │  │
│  │  ┌──────────────────────────────────────────────────────┐                   │  │
│  │  │    sensor.py: RouteCorridorStationSensor (NEU/NEW)   │                   │  │
│  │  │    - active_route                                    │                   │  │
│  │  │    - predicted_fuel_stop                             │                   │  │
│  │  │    - corridor_stations                               │                   │  │
│  │  │    - best_station                                    │                   │  │
│  │  └──────────────────────────────────────────────────────┘                   │  │
│  │                              │                                               │  │
│  │                              ▼                                               │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐   │  │
│  │  │    messaging/telegram.py – send_route_alert()  (NEU)                 │   │  │
│  │  │    auch: API-Fehlerbenachrichtigungen / API error notifications       │   │  │
│  │  └──────────────────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                │                                                      │
│                    ┌───────────┴──────────────────────┐                              │
│                    │   Externe APIs / External APIs    │                              │
│                    │                                   │                              │
│                    │  Routing (Prio 1–4):              │                              │
│                    │   1. Google Maps API              │                              │
│                    │   2. Apple Maps                   │                              │
│                    │   3. Waze Routing                 │                              │
│                    │   4. Fahrzeug-Navigation          │                              │
│                    │      (Skoda/VW – falls API verf.) │                              │
│                    │   5. OSRM / ORS (Fallback)        │                              │
│                    │                                   │                              │
│                    │  Geocoding:                       │                              │
│                    │   - Nominatim (OSM)               │                              │
│                    │                                   │                              │
│                    │  Tankstellen (nur Deutschland):   │                              │
│                    │   - TankerKönig API               │                              │
│                    └───────────────────────────────────┘                              │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Neue Komponenten / New Components

#### 2.2.1 `utils/route_planner.py` (Neu / New)

**Deutsch:**
Zentrales Modul für alle routenbezogenen Berechnungen.

**Klassen / Classes:**
- `RoutePlanner` – Verwaltung aktiver Route, Wegpunkte, Geocoding
- `RouteCorridorCalculator` – Erzeugung des Korridor-Polygons um die Route
- `FuelStopPredictor` – Prognose des nächsten Tankstopps
- `CorridorStationRanker` – Ranking der Tankstellen nach effektivem Preis

**English:**
Central module for all route-related computations.

**Classes:**
- `RoutePlanner` – Manage active route, waypoints, geocoding
- `RouteCorridorCalculator` – Generate corridor polygon around the route
- `FuelStopPredictor` – Predict the next fuel stop
- `CorridorStationRanker` – Rank stations by effective price

#### 2.2.2 Neue Sensoren / New Sensors

| Sensor | Zustand / State | Attribute |
|--------|-----------------|-----------|
| `sensor.{vehicle}_active_route` | `active` / `inactive` | `destination`, `waypoints`, `total_distance_km`, `route_polyline`, `corridor_width_km` |
| `sensor.{vehicle}_predicted_fuel_stop` | Distanz zum Stop (km) / distance to stop (km) | `predicted_position_lat`, `predicted_position_lon`, `predicted_position_address`, `km_remaining_to_stop`, `time_remaining_to_stop`, `safety_buffer_pct` |
| `sensor.{vehicle}_corridor_best_station` | Effektiver Preis €/l | `station_name`, `station_address`, `station_lat`, `station_lon`, `price_per_litre`, `detour_km`, `effective_total_cost_eur`, `google_maps_url`, `waze_url`, `apple_maps_url`, `last_notified_at` |
| `sensor.{vehicle}_corridor_stations` | Anzahl Stationen / Number of stations | `stations` (Liste/List Top-N), `corridor_width_km`, `search_window_km` |

#### 2.2.3 Neue Konfigurationsparameter / New Configuration Parameters

```python
# const.py Ergänzungen / additions
CONF_ROUTE_CORRIDOR_WIDTH_KM      = "route_corridor_width_km"       # Standard / Default: 5
CONF_ROUTE_FUEL_SAFETY_BUFFER_PCT = "route_fuel_safety_buffer_pct"  # Standard / Default: 15
CONF_ROUTE_PRICE_ALERT_DELTA      = "route_price_alert_delta"        # Standard / Default: 0.03
CONF_ROUTE_NOTIFY_INTERVAL_MIN    = "route_notify_interval_min"      # Standard / Default: 5
CONF_ROUTE_SEARCH_WINDOW_KM       = "route_search_window_km"         # Standard / Default: 20
CONF_ROUTE_TOP_N_STATIONS         = "route_top_n_stations"           # Standard / Default: 3
CONF_ROUTE_ROUTING_PROVIDER       = "route_routing_provider"
# Werte / Values (beantwortet – Frage 1 / answered – Question 1):
#   "google"      – Google Maps API (Standard / Default)
#   "apple"       – Apple Maps (primär iOS / primarily iOS)
#   "waze"        – Waze Routing API
#   "vehicle"     – Fahrzeug-Navigation (Skoda/VW, falls API verfügbar)
#   "osrm"        – OSRM (Open Source Routing Machine, Fallback)
#   "openrouteservice" – OpenRouteService (Fallback mit Höhenprofil)
CONF_ROUTE_AVOID_TOLLS            = "route_avoid_tolls"              # False (zukünftige Option / future option)
```

---

## 3. Algorithmen / Algorithms

### 3.1 Korridor-Polygon-Berechnung / Corridor Polygon Calculation

**Deutsch:**
1. Route-Polyline (Liste von GPS-Punkten) vom konfigurierten Routing-Provider empfangen (Google Maps, Apple Maps, Waze, Fahrzeug-Navigation oder Fallback OSRM/ORS – beantwortet Frage 1 und 6)
2. Für jeden Liniensegment: Berechnung eines Rechteck-Puffers ±`corridor_width_km` (Haversine-Methode)
3. Union aller Segment-Puffer = Gesamt-Korridor-Polygon
4. Tankstellen werden nur dann berücksichtigt, wenn ihre Koordinaten `(lat, lon)` innerhalb des Polygons liegen (Point-in-Polygon-Test, z.B. Ray-Casting-Algorithmus)

**English:**
1. Receive route polyline (list of GPS points) from the configured routing provider (Google Maps, Apple Maps, Waze, vehicle navigation, or fallback OSRM/ORS – answers Questions 1 and 6)
2. For each line segment: calculate a rectangular buffer of ±`corridor_width_km` (Haversine method)
3. Union of all segment buffers = total corridor polygon
4. Stations are included only if their coordinates `(lat, lon)` lie within the polygon (point-in-polygon test, e.g. ray-casting algorithm)

```
Route:  A ──────────────── B ──────────────── C
         ╔══════════════════════════════════╗
         ║       Korridor / Corridor        ║
         ╚══════════════════════════════════╝
              ★ Tankstelle A (drin / inside)
                        ✗ Tankstelle B (draußen / outside)
```

### 3.2 Tankstopp-Prognose / Fuel Stop Prediction

**Deutsch:**
```
Reichweite_verbleibend = (Tankstand_aktuell_L - Puffer_L) / Verbrauch_L_pro_km
Puffer_L = Tankkapazität × safety_buffer_pct / 100

Tankstopp_Distanz_km = Aktuelle_Routenposition + Reichweite_verbleibend

Tankstopp_Position = Interpolation auf der Polyline bei Tankstopp_Distanz_km
```

**English:**
```
remaining_range = (current_fuel_L - buffer_L) / consumption_L_per_km
buffer_L = tank_capacity × safety_buffer_pct / 100

fuel_stop_distance_km = current_route_position + remaining_range

fuel_stop_position = interpolated point on polyline at fuel_stop_distance_km
```

### 3.3 Effektiver Gesamtpreis / Effective Total Price

**Deutsch:**
Der „effektive Gesamtpreis" einer Tankstelle berücksichtigt den Listenpreis sowie die Mehrkosten durch den Umweg. Dadurch wird eine Tankstelle 3 km vom Weg mit günstigem Preis fair gegen eine Tankstelle direkt an der Route mit etwas höherem Preis abgewogen.

**English:**
The "effective total price" of a station factors in the listed price plus the extra cost of the detour. This allows a station 3 km off-route with a low price to be fairly weighed against a station directly on-route with a slightly higher price.

```
Umweg_km = Distanz(Hauptroute → Tankstelle → Hauptroute)
Umweg_Kraftstoff_L = Umweg_km × Verbrauch_L_pro_km
Umweg_Kosten_EUR = Umweg_Kraftstoff_L × Stationspreis

Benötigte_Liter = (Tankkapazität - Tankstand_bei_Ankunft)
Tankkosten_EUR = Benötigte_Liter × Stationspreis
Gesamtkosten_EUR = Tankkosten_EUR + Umweg_Kosten_EUR

Effektiver_Preis_EUR_pro_L = Gesamtkosten_EUR / Benötigte_Liter
```

```
detour_km = distance(main_route → station → main_route)
detour_fuel_L = detour_km × consumption_L_per_km
detour_cost_EUR = detour_fuel_L × station_price

litres_needed = (tank_capacity - estimated_fuel_at_arrival)
fuel_cost_EUR = litres_needed × station_price
total_cost_EUR = fuel_cost_EUR + detour_cost_EUR

effective_price_EUR_per_L = total_cost_EUR / litres_needed
```

### 3.4 Benachrichtigungslogik / Notification Logic

**Deutsch:**
```
Beim Routenstart:
  → Berechne prognostizierten Tankstopp
  → Suche Top-N Stationen im Korridor um Tankstopp ± search_window_km
  → Sende initiale Telegram-Nachricht mit Tankplan

Während der Fahrt (alle notify_interval_min Minuten):
  → Aktualisiere Tankstopp-Prognose
  → Suche erneut Stationen im Korridor
  → Berechne neuen besten effektiven Preis
  → WENN (best_new_price < last_notified_price - price_alert_delta):
      → Sende Telegram-Alarm "Günstigere Tankstelle gefunden!"
      → Aktualisiere last_notified_price
  → WENN (verbleibende Reichweite < Warnschwelle):
      → Sende Telegram-Tankwarnalarm
```

**English:**
```
At route start:
  → Calculate predicted fuel stop
  → Search Top-N stations in corridor around fuel stop ± search_window_km
  → Send initial Telegram message with fuel stop plan

During the trip (every notify_interval_min minutes):
  → Update fuel stop prediction
  → Search stations in corridor again
  → Calculate new best effective price
  → IF (best_new_price < last_notified_price - price_alert_delta):
      → Send Telegram alert "Cheaper station found!"
      → Update last_notified_price
  → IF (remaining range < warning threshold):
      → Send Telegram low-fuel alert
```

---

### 3.5 Vorausschauender Cache-Algorithmus / Predictive Caching Algorithm

> **Hintergrund / Background:** Die TankerKönig-API erlaubt maximal eine Anfrage pro 5 Minuten. Um API-Aufrufe zu reduzieren und dennoch aktuelle Daten bereitzustellen, wird ein vorausschauender Cache auf Basis der aktuellen GPS-Geschwindigkeit eingesetzt (beantwortet – Frage 4).

**Deutsch:**
```
Vorausschauender Cache-Zyklus (alle 5 Minuten):

  t=0:  Aktuelle Position P0 aus device_tracker (GPS-Koordinaten + Geschwindigkeit v_kmh)
        │
        ▼
        Prognose-Position P10 berechnen:
          Distanz_10min_km = v_kmh × (10/60)
          P10 = Interpolierter Punkt auf Route-Polyline bei P0 + Distanz_10min_km
        │
        ▼
        TankerKönig API anfragen:
          Suchzentrum = P10  (vorausschauende Position in 10 Minuten)
          Suchradius = corridor_width_km + puffer_km
        │
        ▼
        Ergebnisse im Cache speichern (TTL = 5 Minuten)
        │
  t=5:  Aktuelle Position P5 aus device_tracker
        │
        ▼
        Korridor-Filterung mit gecachten Stationen
        (keine neue API-Anfrage erforderlich)
        │
        ▼
        Neue Prognose-Position P15 berechnen → nächste API-Anfrage vorbereiten
        │
  t=10: Neue TankerKönig API anfragen (Suchzentrum = P20)
        Ergebnisse ersetzen alten Cache-Eintrag
```

**English:**
```
Predictive cache cycle (every 5 minutes):

  t=0:  Current position P0 from device_tracker (GPS coordinates + speed v_kmh)
        │
        ▼
        Calculate predicted position P10:
          distance_10min_km = v_kmh × (10/60)
          P10 = interpolated point on route polyline at P0 + distance_10min_km
        │
        ▼
        Query TankerKönig API:
          search_centre = P10  (predicted position in 10 minutes)
          search_radius = corridor_width_km + buffer_km
        │
        ▼
        Store results in cache (TTL = 5 minutes)
        │
  t=5:  Current position P5 from device_tracker
        │
        ▼
        Filter corridor with cached stations
        (no new API call required)
        │
        ▼
        Calculate new predicted position P15 → prepare next API query
        │
  t=10: New TankerKönig API query (search_centre = P20)
        Replace old cache entry with new results
```

**Fallback bei niedriger / hoher Geschwindigkeit / Fallback for low / high speed:**
- **Fahrzeug steht (v < 5 km/h):** Cache-Zyklus pausiert; Suche bleibt auf aktuelle Position zentriert
- **Sehr hohe Geschwindigkeit (v > 130 km/h):** Prognose-Horizont wird auf 15 Minuten ausgedehnt, Suchradius vergrößert

---

### 3.6 API-Fehlerbehandlung / API Error Handling

> (beantwortet – Frage 7 / answered – Question 7)

**Deutsch:**
- Fehler bei Routing-APIs (Google, Apple, Waze, OSRM, ORS) werden abgefangen und per **Telegram-Nachricht** gemeldet
- Fehler bei der TankerKönig-API werden geloggt und per Telegram gemeldet; die Integration fällt auf den zuletzt gecachten Zustand zurück
- Fehler-Nachrichtenformat:
  ```
  ⚠️ FWCAM Routing-Fehler / Routing Error
  Komponente: Google Maps API
  Fehler: [Fehlermeldung / Error message]
  Aktion: Route konnte nicht berechnet werden. Bitte Route erneut eingeben.
  ```
- Jeder Fehlertyp wird maximal **einmal pro Fahrt** per Telegram gemeldet (keine Spam-Flut)
- Bei vollständigem API-Ausfall: Sicherer Fallback auf OSRM/ORS; wenn kein Provider erreichbar, Route-Modus deaktiviert

**English:**
- Errors from routing APIs (Google, Apple, Waze, OSRM, ORS) are caught and reported via **Telegram message**
- TankerKönig API errors are logged and reported via Telegram; the integration falls back to the last cached state
- Error message format:
  ```
  ⚠️ FWCAM Routing Error
  Component: Google Maps API
  Error: [error message]
  Action: Route could not be calculated. Please re-enter the route.
  ```
- Each error type is reported via Telegram at most **once per trip** (no spam flood)
- In case of complete API failure: safe fallback to OSRM/ORS; if no provider is reachable, route mode is deactivated

---

## 4. Datenfluss / Data Flow

### 4.1 Vor der Fahrt / Before the Trip

```
Benutzer gibt Ziel ein / User enters destination
(Lovelace-Dashboard, HA Companion App oder Telegram)
            │
            ▼
    Geocoding (Nominatim)
    Adresse → GPS-Koordinaten
            │
            ▼
    Routing API (Google Maps / Apple / Waze / Fahrzeug-Nav. / OSRM / ORS)
    Route-Polyline + Distanz + Zwischenpunkte
    [Bei Fehler: Telegram-Benachrichtigung + Fallback-Provider]
            │
            ▼
    RouteCorridorCalculator
    Korridor-Polygon erzeugen
            │
            ▼
    FuelStopPredictor
    Tankstopp-Position berechnen
    (device_tracker: aktuelle GPS-Position als Ausgangspunkt)
            │
            ▼
    TankerKönig API (nur Deutschland)
    Tankstellen im Korridor abfragen
    + Cache aufwärmen für Prognose-Position P10
            │
            ▼
    CorridorStationRanker
    Ranking nach effektivem Preis
            │
            ▼
    Telegram: Tankplan senden / Send fuel plan
    HA Sensor: RouteCorridorStationSensor aktualisieren
```

### 4.2 Während der Fahrt / During the Trip

```
Position-Update (device_tracker: GPS-Koordinaten + Geschwindigkeit)
            │
            ▼
    RouteCorridorStationSensor
    Position auf Route projizieren
            │
            ▼
    FuelStopPredictor
    Prognose aktualisieren
    (Verbrauch + verbleibender Kraftstoff)
            │
            ▼
    Vorausschauender Cache-Check:
    Ist Cache noch gültig? (< 5 Min. alt)
      JA  → Korridor-Filterung mit Cache-Daten (kein API-Call)
      NEIN→ TankerKönig API anfragen (Suchzentrum = P10-Prognose)
            [Bei Fehler: Telegram-Benachrichtigung, Cache behalten]
            │
            ▼
    Benachrichtigungslogik prüfen
    Günstiger als zuvor? → Telegram
    Reichweite kritisch?  → Telegram
```

---

## 5. Telegram Bot Integration

### 5.1 Neue Befehle / New Commands

| Befehl / Command | Beschreibung DE | Description EN |
|------------------|-----------------|----------------|
| `/route [Ziel]` | Setzt das Fahrziel und startet Routenmodus | Sets destination and activates route mode |
| `/route [Ziel] via [ZZ1] via [ZZ2]` | Route mit Zwischenzielen | Route with waypoints |
| `/routestatus` | Aktuellen Routenstatus abfragen | Query current route status |
| `/routecancel` | Aktive Route beenden | End active route |
| `/corridor [km]` | Korridorbreite ändern | Change corridor width |

### 5.2 Beispiel-Nachrichten / Example Messages

**Routenstart / Route Start:**
```
🗺️ Route aktiviert!
📍 Ziel: München Hauptbahnhof (346 km)
⛽ Prognose Tankstopp bei: ~230 km (Ingolstadt Bereich)

🏆 Empfohlene Tankstelle im Korridor:
   Aral Tankstelle Ingolstadt Nord
   💰 E10: 1,689 €/l
   📏 Umweg: 0,8 km
   💶 Effektiver Preis: 1,702 €/l (inkl. Umweg)
   🗺️ https://maps.google.com/?q=...

📋 Weitere Optionen im Korridor:
   2. Shell Ingolstadt Ost - 1,699 €/l (0,2 km Umweg)
   3. JET Manching - 1,712 €/l (direkt an Route)

⚙️ Korridor: 5 km | Sicherheitspuffer: 15%
```

**Günstigere Tankstelle gefunden / Cheaper Station Found:**
```
💡 Günstigere Tankstelle im Korridor!

NEU: JET Neuburg a.d. Donau
   💰 E10: 1,659 €/l (↓ 0,043 €/l günstiger!)
   📏 Umweg: 1,2 km
   💶 Effektiv: 1,676 €/l
   📍 Liegt in ~48 km (ca. 32 Min.)
   🗺️ Google Maps | Waze | Apple Maps

Bisherige Empfehlung: 1,702 €/l
Ersparnis für Volltankung (40 L): ~1,72 €
```

**Reichweitenwarnung / Range Warning:**
```
⚠️ Reichweitenwarnung!
Tank reicht noch für ~42 km.
Nächste empfohlene Tankstelle: 38 km entfernt.

JETZT TANKEN: Aral Schrobenhausen
   💰 E10: 1,689 €/l | 📏 0,5 km Umweg
   🗺️ https://maps.google.com/?q=...
```

---

## 6. Eigene Optimierungsvorschläge / Additional Optimization Ideas

### 6.1 Preisvorhersage-Integration / Price Forecast Integration

**Deutsch:**
Die bereits vorhandene `utils/forecast.py` und `utils/price_statistics_engine.py` können genutzt werden, um nicht nur den aktuellen Preis, sondern auch die Preisentwicklung zu berücksichtigen. Wenn der Preis einer Tankstelle laut Prognose in den nächsten 2 Stunden fallen wird, empfiehlt das System eventuell zu warten.

**English:**
The existing `utils/forecast.py` and `utils/price_statistics_engine.py` can be used to consider not just the current price but also the price trend. If a station's price is forecast to fall in the next 2 hours, the system may recommend waiting.

### 6.2 Mehrfach-Tankstopp-Planung / Multi-Fuel-Stop Planning

**Deutsch:**
Bei sehr langen Routen (> 600 km) plant das System mehrere Tankstopps im Voraus und optimiert die Gesamtkosten über alle Stopps hinweg. Beispiel: Nicht bei jeder günstigen Tankstelle kurz tanken, sondern strategisch bei der günstigsten Tankstelle voll tanken.

**English:**
For very long routes (> 600 km), the system plans multiple fuel stops in advance and optimises the total cost across all stops. Example: don't refuel a little at every cheap station, but instead fill up completely at the cheapest strategic station.

### 6.3 Verkehrs- und Zeitfaktor / Traffic and Time Factor

**Deutsch:**
Berücksichtigung von Verkehrsdaten (z.B. über OSRM oder OpenRouteService Verkehrs-API): Eine Tankstelle, die nur durch starken Stau erreichbar ist, wird im Ranking abgewertet. Die Zeitkosten des Umwegs (geschätzte Verzögerung in Minuten) werden als optionaler Faktor eingerechnet.

**English:**
Account for traffic data (e.g. via OSRM or OpenRouteService traffic API): a station reachable only through heavy traffic is ranked lower. The time cost of the detour (estimated delay in minutes) is included as an optional factor.

### 6.4 Fahrstil-Anpassung / Driving Style Adaptation

**Deutsch:**
Nutzung der `utils/ml_engine.py` und `utils/consumption_prediction.py`, um den tatsächlichen Verbrauch für die aktuelle Route zu schätzen – basierend auf historischen Daten ähnlicher Routen (Autobahn vs. Stadtverkehr, Steigungs-Profil), anstatt nur den globalen Durchschnittsverbrauch zu verwenden. Dies erhöht die Genauigkeit der Tankstopp-Prognose erheblich.

**English:**
Use `utils/ml_engine.py` and `utils/consumption_prediction.py` to estimate actual consumption for the current route based on historical data from similar routes (motorway vs. city, elevation profile), rather than relying on the global average consumption. This significantly improves fuel stop prediction accuracy.

### 6.5 Preisoptimaler Tankfüllstand / Price-Optimal Fill Level

**Deutsch:**
Statt immer voll zu tanken berechnet das System den optimalen Tankfüllstand für den nächsten Stop. Wenn kurz hinter dem aktuellen Tankstoppfenster eine deutlich günstigere Tankstelle liegt, empfiehlt das System nur so viel zu tanken, dass diese Tankstelle erreicht wird (plus Puffer).

**English:**
Instead of always filling up completely, the system calculates the optimal fill level for the next stop. If a significantly cheaper station is just beyond the current refueling window, the system recommends filling up only enough to reach that station (plus buffer).

### 6.6 Öffnungszeiten-Bewusstsein / Opening Hours Awareness

**Deutsch:**
Die TankerKönig-API liefert Öffnungszeitstatus. Das System berechnet die voraussichtliche Ankunftszeit an der Tankstelle und schließt Tankstellen aus, die zu diesem Zeitpunkt voraussichtlich geschlossen sind. Bei langen Nachtfahrten werden bevorzugt 24h-Tankstellen vorgeschlagen.

**English:**
The TankerKönig API provides opening status. The system calculates the expected arrival time at the station and excludes stations that are likely to be closed at that time. For long overnight drives, 24-hour stations are preferred.

### 6.7 Mehrfahrzeug-Koordination / Multi-Vehicle Coordination

**Deutsch:**
Bei mehreren konfigurierten Fahrzeugen (Familienreise in mehreren Autos) können die Tankplanung koordiniert werden: Wenn zwei Fahrzeuge dieselbe Strecke fahren, nutzen beide denselben Routenplan und können gemeinsam an derselben günstigen Tankstelle halten.

**English:**
With multiple configured vehicles (family trip in multiple cars), fuel planning can be coordinated: if two vehicles are travelling the same route, both use the same route plan and can stop at the same cheap station together.

### 6.8 Historische Routenanalyse / Historical Route Analysis

**Deutsch:**
Das System erkennt häufig gefahrene Routen (z.B. regelmäßige Fahrten zur Arbeit) und schlägt beim Routenstart automatisch die Einstellungen vor, die bei dieser Route in der Vergangenheit gut funktioniert haben (bevorzugte Tankstellen, optimale Puffergröße).

**English:**
The system recognises frequently driven routes (e.g. regular commutes) and automatically suggests at route start the settings that worked well for this route in the past (preferred stations, optimal buffer size).

### 6.9 Kraftstoffpreis-Benachrichtigung bei Routenüberschneidung / Fuel Price Alert on Route Overlap

**Deutsch:**
Auch wenn keine aktive Route gesetzt ist, kann das System erkennen, dass das Fahrzeug gerade eine bekannte „Günstig-Zone" (gespeicherte günstige Tankstellen aus historischen Daten) durchfährt, und eine situative Empfehlung ausgeben.

**English:**
Even without an active route, the system can detect that the vehicle is passing through a known "cheap zone" (saved cheap stations from historical data) and issue a situational recommendation.

### 6.10 Klimaeffizienz-Optimierung / Climate Efficiency Optimization

**Deutsch:**
Optionale Integration von Wetterdaten (OpenWeatherMap): Hohe Außentemperaturen erhöhen den Verbrauch durch Klimaanlage. Das System korrigiert die Verbrauchsprognose bei extremen Temperaturen nach oben, um konservativere Tankstopps zu planen.

**English:**
Optional integration of weather data (OpenWeatherMap): high ambient temperatures increase consumption due to air conditioning. The system adjusts the consumption estimate upward in extreme temperatures for more conservative fuel stop planning.

---

## 7. Routing-Provider / Routing Providers

> **Entschieden (Frage 1 & 6) / Decided (Questions 1 & 6):** Standard-Provider ist **Google Maps**, gefolgt von Apple Maps, Waze und Fahrzeug-Navigation (Skoda/VW). OSRM und ORS dienen als Fallback-Optionen. Die Priorisierung kann in der Config-Flow konfiguriert werden.

### 7.1 Google Maps (Standard / Default)

**Deutsch:**
- **Standard-Routing-Provider** für die Integration
- Hervorragende Routing-Qualität mit Echtzeit-Verkehrsdaten
- Liefert präzise Route-Polylines (GeoJSON/Encoded Polyline)
- **API-Key erforderlich** (Google Maps Platform – Directions API)
- Kostenloses Kontingent vorhanden; kostenpflichtig bei hohem Volumen
- Unterstützt Vermeidung von Mautstraßen (für spätere Optimierung, Frage 5)

**English:**
- **Default routing provider** for the integration
- Excellent routing quality with real-time traffic data
- Delivers precise route polylines (GeoJSON/Encoded Polyline)
- **API key required** (Google Maps Platform – Directions API)
- Free tier available; costs apply at high volume
- Supports toll-road avoidance (for future optimization, Question 5)

### 7.2 Apple Maps

**Deutsch:**
- Nativ auf iOS-Geräten verfügbar; tiefe Integration mit HA Companion App auf iPhone/iPad
- Nutzung über **MapKit JS** (Web) oder Deep-Link-Schema `maps://` für Turn-by-Turn-Navigation
- Kein separater API-Key für reine Deep-Link-Navigation erforderlich
- Routing-Polyline für Korridor-Berechnung über Apple Maps Server API (API-Key erforderlich)
- **Empfohlen für iOS-Nutzer** als Alternative zu Google Maps

**English:**
- Natively available on iOS devices; deep integration with HA Companion App on iPhone/iPad
- Used via **MapKit JS** (web) or Deep-Link scheme `maps://` for turn-by-turn navigation
- No separate API key required for pure deep-link navigation
- Routing polyline for corridor calculation via Apple Maps Server API (API key required)
- **Recommended for iOS users** as an alternative to Google Maps

### 7.3 Waze

**Deutsch:**
- Sehr gute Echtzeit-Verkehrs- und Stau-Informationen (Community-basiert)
- Navigation via Waze Deep-Link `waze://` oder `https://waze.com/ul` möglich
- **Keine öffentliche Routing-Polyline-API** – Waze wird daher primär für **Navigations-Links** in Telegram-Nachrichten genutzt
- Routing-Polyline für Korridor-Berechnung muss von anderem Provider kommen (z.B. Google)

**English:**
- Excellent real-time traffic and congestion information (community-based)
- Navigation via Waze Deep-Link `waze://` or `https://waze.com/ul`
- **No public routing polyline API** – Waze is therefore primarily used for **navigation links** in Telegram messages
- Routing polyline for corridor calculation must come from another provider (e.g. Google)

### 7.4 Fahrzeug-Navigation / Vehicle Navigation (Skoda / VW)

> **(Frage 6 beantwortet / Question 6 answered)**

**Deutsch:**
- Idealziel: Nutzung der eingebauten Fahrzeug-Navigation (z.B. Skoda Laura, VW We Connect)
- **Aktuelle Verfügbarkeit:** Skoda/VW bieten über die **We Connect API** und **Skoda Connect API** begrenzte Fahrzeugdaten; eine direkte Routenübernahme aus der Fahrzeug-Navigation ist über diese APIs **aktuell nicht standardmäßig verfügbar**
- **Möglicher Ansatz:** Auslesen der Ziel-/Routeninformation aus dem Fahrzeug-Infotainment via `custom_components/skodaconnect` oder `volkswagencarnet` HA-Integrationen, falls verfügbar und konfiguriert
- **Fallback:** Wenn keine Fahrzeug-Navigation-API verfügbar ist, wird automatisch Google Maps (oder der nächste konfigurierten Provider) verwendet

**English:**
- Ideal goal: use the built-in vehicle navigation (e.g. Skoda Laura, VW We Connect)
- **Current availability:** Skoda/VW offer limited vehicle data via the **We Connect API** and **Skoda Connect API**; direct route import from the vehicle navigation is **not currently available as standard** via these APIs
- **Possible approach:** Read destination/route information from the vehicle infotainment via `custom_components/skodaconnect` or `volkswagencarnet` HA integrations, if available and configured
- **Fallback:** If no vehicle navigation API is available, Google Maps (or the next configured provider) is used automatically

### 7.5 OSRM (Open Source Routing Machine) – Fallback

**Deutsch:**
- Kostenlos, selbst-hostbar oder als öffentlicher Endpoint
- Liefert präzise Route-Polylines (GeoJSON)
- Kein API-Key erforderlich für den öffentlichen Demo-Server
- Limitierungen beim öffentlichen Demo-Server (Rate Limits)
- **Rolle:** Fallback wenn Google/Apple/Waze nicht konfiguriert oder nicht erreichbar

**English:**
- Free, self-hostable or public endpoint
- Delivers precise route polylines (GeoJSON)
- No API key required for the public demo server
- Rate limits apply for the public demo server
- **Role:** Fallback when Google/Apple/Waze not configured or unreachable

### 7.6 OpenRouteService (ORS) – Fallback

**Deutsch:**
- Kostenloser API-Key verfügbar (mit Limit)
- Erweiterte Routing-Optionen (Vermeidung von Maut, Fähren, etc.)
- Unterstützt Höhenprofil (für verbessertes Verbrauchsmodell)
- **Rolle:** Sekundärer Fallback; besonders geeignet wenn Höhenprofil-Daten für ML-Verbrauchsschätzung benötigt werden

**English:**
- Free API key available (with limits)
- Advanced routing options (avoid tolls, ferries, etc.)
- Supports elevation profile (for improved consumption model)
- **Role:** Secondary fallback; particularly useful when elevation profile data is needed for ML consumption estimation

### 7.7 Maut-Vermeidung / Toll Avoidance

> **(Frage 5 beantwortet / Question 5 answered)**

**Deutsch:**
Maut-Straßen-Vermeidung ist in Deutschland kaum relevant (wenige Mautstraßen). Die Option `CONF_ROUTE_AVOID_TOLLS` wird als konfigurierbare Einstellung vorbereitet (`False` als Standard), aber **erst in einer späteren Optimierungsphase** aktiv implementiert.

**English:**
Toll road avoidance is barely relevant in Germany (few toll roads). The `CONF_ROUTE_AVOID_TOLLS` option is prepared as a configurable setting (`False` as default), but **only actively implemented in a later optimization phase**.

### 7.8 Abstraktionsschicht / Abstraction Layer

**Deutsch:**
`utils/route_planner.py` implementiert eine Provider-Abstraktion, sodass der Benutzer in der Config-Flow den bevorzugten Routing-Provider auswählen kann. Neue Provider können leicht ergänzt werden. Provider-Priorität (konfigurierbar): Google → Apple → Waze → Fahrzeug-Nav → OSRM → ORS.

**English:**
`utils/route_planner.py` implements a provider abstraction, allowing the user to select the preferred routing provider in the config flow. New providers can be added easily. Provider priority (configurable): Google → Apple → Waze → Vehicle Nav → OSRM → ORS.

---

## 8. Datenschutz / Privacy

**Deutsch:**
- Routendaten (Ziel, Wegpunkte) werden nur im HA-RAM und temporärem Storage gespeichert
- Keine persistente Speicherung von Routenzielen ohne explizite Benutzereinwilligung
- Koordinaten werden nur an den Routing-Provider und TankerKönig (bereits genutzt) übermittelt
- Anonymisierung der Routendaten im Debug-Export konsistent mit der bestehenden `_Anonymizer`-Klasse in `utils/debug_export.py`
- Routendaten werden nach Fahrtende automatisch gelöscht (konfigurierbare Aufbewahrungszeit)

**English:**
- Route data (destination, waypoints) is stored only in HA RAM and temporary storage
- No persistent storage of route destinations without explicit user consent
- Coordinates are only transmitted to the routing provider and TankerKönig (already in use)
- Route data anonymisation in debug exports consistent with the existing `_Anonymizer` class in `utils/debug_export.py`
- Route data is automatically deleted after the trip ends (configurable retention period)

---

## 9. Beantwortete Fragen / Answered Questions

| Nr. | Frage (DE) | Question (EN) | Antwort (DE) | Answer (EN) | Dok.-Abschnitt |
|-----|------------|---------------|--------------|-------------|----------------|
| 1 | Welcher Routing-Provider wird standardmäßig genutzt? | Which routing provider is used by default? | **Google Maps** (Standard); zusätzlich Apple Maps, Waze, Fahrzeug-Navigation (Skoda/VW); OSRM/ORS als Fallback | **Google Maps** (default); additionally Apple Maps, Waze, vehicle navigation (Skoda/VW); OSRM/ORS as fallback | Abschnitt 7 |
| 2 | Soll die Routeneingabe auch über die HA-Companion-App möglich sein? | Should route input also be possible via the HA Companion App? | **Ja** – Routenplanung über Companion App (iOS/Android), Telegram und Browser (Lovelace) | **Yes** – route planning via Companion App (iOS/Android), Telegram and browser (Lovelace) | Abschnitt 1.1.1 |
| 3 | Wie wird die genaue Position auf der Route (Route-Projektion) berechnet? | How is the precise position on the route (route projection) computed? | Via konfigurierter **`device_tracker`-Entität** der Integration (GPS-Koordinaten + Geschwindigkeit) | Via configured **`device_tracker` entity** of the integration (GPS coordinates + speed) | Abschnitte 1.1.2, 3.5, 4.2 |
| 4 | Soll der Korridor-Suchalgorithmus Caching nutzen um API-Calls zu reduzieren? | Should the corridor search algorithm use caching to reduce API calls? | **Ja** – vorausschauender Cache auf Basis GPS-Geschwindigkeit: Suche für Prognoseposition in 10 Min., Cache-TTL 5 Min. (TankerKönig-Limit) | **Yes** – predictive cache based on GPS speed: search for predicted position in 10 min, cache TTL 5 min (TankerKönig limit) | Abschnitt 3.5 |
| 5 | Sollen Maut-Straßen optionally vermieden werden? | Should toll roads optionally be avoided? | **Später** – in Deutschland kaum Mautstraßen; Option `avoid_tolls` vorbereitet, aber erst in späterer Phase implementiert | **Later** – few toll roads in Germany; `avoid_tolls` option prepared but only implemented in a later phase | Abschnitte 2.2.3, 7.7 |
| 6 | Integration mit HA-Navigation (falls vorhanden)? | Integration with HA navigation (if present)? | Idealerweise Fahrzeug-Navigation (Skoda/VW über We Connect/Skoda Connect API, falls verfügbar); Fallback: Google, Apple, Waze | Ideally vehicle navigation (Skoda/VW via We Connect/Skoda Connect API, if available); fallback: Google, Apple, Waze | Abschnitt 7.4 |
| 7 | Wie soll das Routing-API-Fehlerverhalten aussehen? | How should routing API error handling behave? | Fehler per **Telegram-Benachrichtigung** melden (max. 1× pro Fehlertyp/Fahrt), sicherer Fallback auf nächsten Provider, Route-Modus deaktivieren bei vollständigem Ausfall | Report errors via **Telegram notification** (max. once per error type/trip), safe fallback to next provider, deactivate route mode on complete failure | Abschnitt 3.6 |
| 8 | TankerKönig-API ist auf Deutschland beschränkt – internationale Route-Unterstützung? | TankerKönig API is Germany-only – international route support? | **Nur Deutschland** – internationale Unterstützung zunächst nicht geplant | **Germany only** – international support not planned initially | Abschnitt 1.1.1 |

---

## 10. Implementierungs-Roadmap / Implementation Roadmap

> **Status: Konzept (Fragen beantwortet) – Umsetzung noch nicht gestartet / Concept (questions answered) – implementation not started**

### Phase 1: Kern-Routing (Basis / Core)
- [ ] Routing-Provider-Abstraktion in `utils/route_planner.py` (Google, Apple, Waze, Fahrzeug-Nav, OSRM, ORS)
- [ ] Google Maps Directions API Integration (Standard-Provider)
- [ ] Geocoding-Integration (Adresse → GPS, wiederverwendet `utils/geocoding.py`)
- [ ] device_tracker-Entität als Positionsquelle verdrahten
- [ ] Korridor-Polygon-Berechnung
- [ ] Tankstopp-Prognose (wiederverwendet `utils/prediction_engine.py`)

### Phase 2: Stationsuche, Caching und Kostenoptimierung
- [ ] Korridor-Filterung der TankerKönig-Stationen (nur Deutschland)
- [ ] Vorausschauender Cache-Algorithmus (GPS-Geschwindigkeit → Prognoseposition → 5-Min-TTL)
- [ ] Effektiver-Preis-Algorithmus (inkl. Umwegkosten)
- [ ] `sensor.py`: `RouteCorridorStationSensor` hinzufügen
- [ ] Persistenz der aktiven Route (wiederverwendet `utils/storage.py`)

### Phase 3: Dashboard, Telegram und Fehlerbehandlung
- [ ] Routeneingabe-UI im FWCAM Lovelace-Card (Browser)
- [ ] HA Companion App Routeneingabe-Unterstützung
- [ ] Kartenansicht: Route + Korridor + Tankstellen-Marker
- [ ] Telegram-Befehle: `/route`, `/routecancel`, `/routestatus`
- [ ] Telegram-Nachrichten: Routenstart, günstigere Station, Reichweitenwarnung
- [ ] API-Fehlerbehandlung mit Telegram-Benachrichtigungen (Abschnitt 3.6)

### Phase 4: Optimierungen
- [ ] Apple Maps Server API Integration
- [ ] Waze Navigation-Links in Telegram-Nachrichten
- [ ] Fahrzeug-Navigation (Skoda/VW We Connect / Skoda Connect) – falls API verfügbar
- [ ] Preisvorhersage-Integration
- [ ] Mehrfach-Tankstopp-Planung
- [ ] Öffnungszeiten-Bewusstsein
- [ ] Fahrstil-Anpassung (ML-basiert)

### Phase 5: Erweiterungen (Zukunft / Future)
- [ ] Maut-Straßen-Vermeidung (`avoid_tolls`-Option)
- [ ] Mehrfahrzeug-Koordination
- [ ] Historische Routenanalyse
- [ ] Wetterdaten-Integration
- [ ] Preisoptimaler Tankfüllstand

---

## 11. Abhängigkeiten / Dependencies

### 11.1 Bestehende Module (wiederverwendet / reused)
- `utils/geolocation.py` – Haversine-Distanzberechnung, Navigations-URLs
- `utils/geocoding.py` – Adress-Geocoding
- `utils/prediction_engine.py` – Verbrauchsprognose
- `utils/consumption_prediction.py` – ML-basierte Verbrauchsschätzung
- `utils/forecast.py` – Preisvorhersage
- `utils/price_statistics_engine.py` – Preisstatistiken
- `providers/tankerkonig.py` – Tankstellenpreise
- `messaging/telegram.py` – Telegram-Benachrichtigungen
- `utils/storage.py` – Datenpersistenz
- `utils/debug_export.py` – Anonymisierung

### 11.2 Neue externe Abhängigkeiten / New External Dependencies

**Routing-APIs / Routing APIs (HTTP-Requests via `aiohttp`, bereits vorhanden / already present):**
- **Google Maps Directions API** – Primär-Provider; API-Key erforderlich (Google Maps Platform)
- **Apple Maps Server API** – Sekundär-Provider für iOS; API-Key erforderlich (Apple Developer)
- **Waze** – Nur Navigation-Deep-Links, keine Polyline-API; kein Key erforderlich
- **Fahrzeug-Navigation (Skoda/VW)** – Optional; über `custom_components/skodaconnect` oder `volkswagencarnet` HA-Integrationen (falls installiert)
- **OSRM** – Fallback; kein API-Key für öffentlichen Demo-Server
- **OpenRouteService** – Fallback; kostenloser API-Key verfügbar
- **Keine neuen Python-Pakete** erforderlich – ausschließlich HTTP-Requests via `aiohttp`

---

## 12. Verwandte Dokumente / Related Documents

- [GEOLOCATION_CONCEPT.md](GEOLOCATION_CONCEPT.md) – Bestehende Geolokalisierungs-Grundlage
- [GEOLOCATION_CONCEPT_EN.md](GEOLOCATION_CONCEPT_EN.md) – Geolocation concept (English)
- [TRIP_TRACKING_CONCEPT.md](TRIP_TRACKING_CONCEPT.md) – Fahrtenbuch-Konzept
- [TELEGRAM_REFUELING_BOT_CONCEPT.md](TELEGRAM_REFUELING_BOT_CONCEPT.md) – Telegram Bot-Konzept
- [REFUELING_PREDICTION_IMPROVEMENT.md](REFUELING_PREDICTION_IMPROVEMENT.md) – Tankprognose-Verbesserungen

---

*Erstellt / Created: 2026-03-19 | Aktualisiert / Updated: 2026-03-19 (v1.1 – Offene Fragen beantwortet) | Autor / Author: FWCAM Development Team*
