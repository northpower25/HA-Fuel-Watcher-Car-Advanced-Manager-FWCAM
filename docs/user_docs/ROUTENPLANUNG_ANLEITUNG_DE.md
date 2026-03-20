# Routenplanung – Benutzeranleitung

**Funktion:** Routen-Korridor Tankstellensuche  
**Verfügbar ab:** v0.2.20  
**Geografischer Geltungsbereich:** Nur Deutschland (erfordert TankerKönig API)

---

## Übersicht

Der Reiter **Routenplanung** im FWCAM-Dashboard ermöglicht es, eine Fahrtroute zu planen und automatisch die günstigsten Tankstellen entlang der Strecke zu finden. Anstatt in einem fixen Radius um die aktuelle Position zu suchen, definiert die Routenplanung einen konfigurierbaren **Korridor** (Pufferzone) um die geplante Route und wertet nur die Tankstellen innerhalb dieses Korridors aus.

Funktionsübersicht:

- 🗺️ **Routenberechnung** über OSRM (kostenlos), OpenRouteService oder Google Maps API
- 🔍 **Korridor-basierte Tankstellensuche** – nur Stationen auf dem Weg werden berücksichtigt
- ⛽ **Tankstopp-Prognose** – schätzt, wo auf der Route getankt werden muss (auf Basis von aktuellem Tankstand und Durchschnittsverbrauch)
- 💰 **Effektiver Preisvergleich** – Umwegkosten zu jeder Tankstelle werden eingerechnet
- 📱 **Navigationslinks** – direkte Navigation zur günstigsten Tankstelle via Google Maps, Waze oder Apple Maps
- 🔔 **Telegram-Benachrichtigungen** – Bestätigungen beim Starten und Beenden der Route inkl. sofortiger Tankstopp-Prognose mit Top-5-Tankstellen

---

## Voraussetzungen

| Voraussetzung | Details |
|---|---|
| TankerKönig API-Schlüssel | Bereits in den FWCAM-Integrationseinstellungen konfiguriert |
| Fahrzeug mit bekanntem Tankstand | Die Integration muss den Tankstand erfassen (via `device_tracker`, OBD oder Freematics) |
| Konfigurierter Durchschnittsverbrauch | Wird in den Integrationseinstellungen angegeben und für die Tankstoppprognose benötigt |
| Internetzugang | Erforderlich für Geocoding (Nominatim) und Routing-APIs |
| Nur Deutschland | TankerKönig deckt ausschließlich deutsche Tankstellen ab |

---

## Entitäten für die Tankstopp-Prognose

Die Tankstopp-Prognose greift auf folgende Datenquellen zu:

| Datenpunkt | Entität | Beschreibung |
|---|---|---|
| **Fahrzeugposition** | konfigurierte `device_tracker`-Entität (Startpunkt der Route) | Wird über die in den Integrationseinstellungen verknüpfte `position_entity` bezogen. Beispiel: `device_tracker.mein_auto` |
| **Restreichweite / Tankfüllstand** | `sensor.[entry_id]_range` | Verbleibende Reichweite in km – Hauptquelle für die Prognose. Alternativ wird der Tankfüllstand in Litern aus `sensor.[entry_id]_tank_level` genutzt. |
| **Durchschnittsverbrauch** | `sensor.[entry_id]_average_consumption_history` | Mittlerer Verbrauch in l/100 km aus dem Verbrauchsverlauf. Wird in der Konfiguration als `avg_consumption_rate` geführt. |

**Prognoseformel (vereinfacht):**

```
nutzbare_reichweite = (tankfüllstand_liter × (1 − sicherheitspuffer%)) / verbrauch × 100
tankstopp_km       = aktuelle_position_auf_route + nutzbare_reichweite
```

Ein **15 % Sicherheitspuffer** wird standardmäßig abgezogen, um Reserve für Umwege und Staus zu gewährleisten.

> **Tipp:** Sind Tankstand oder Verbrauch nicht verfügbar, erscheint kein Tankstopp-Hinweis in der Benachrichtigung. Stelle sicher, dass die oben genannten Entitäten in den Integrationseinstellungen verknüpft sind.

---

## Der Reiter „Routenplanung"

Öffne die FWCAM-Karte im Home-Assistant-Dashboard und wechsle zum Reiter **🗺️ Route Planner** (Routenplanung).

### Eingabefelder

| Feld | Beschreibung | Standard |
|---|---|---|
| **Destination (Ziel)** | Adresse oder Stadtname (z. B. `München Hauptbahnhof`) | – |
| **Waypoints (Zwischenziele)** | Optionale Zwischenstopps, kommagetrennt (z. B. `Augsburg, Ingolstadt`) | – |
| **Corridor Width (Korridorbreite, km)** | Puffer um die Route für die Tankstellensuche (1–50 km) | 5 km |
| **Routing Provider (Routing-Anbieter)** | Dienst zur Routenberechnung | OSRM (kostenlos) |
| **Google API Key** | Nur erforderlich, wenn *Google Maps* als Anbieter gewählt wurde | – |

### Routing-Anbieter

| Anbieter | Kosten | Hinweise |
|---|---|---|
| **OSRM** | Kostenlos, kein API-Schlüssel erforderlich | Nutzt den öffentlichen OSRM-Demoserver. Gute Genauigkeit für deutsche Straßen. |
| **OpenRouteService** | Kostenloses Kontingent verfügbar | Erfordert einen kostenlosen API-Schlüssel von [openrouteservice.org](https://openrouteservice.org). |
| **Google Maps** | Kostenpflichtig (Google Cloud) | Höchste Genauigkeit. Erfordert einen Google Maps Directions API-Schlüssel, der direkt in der Karte eingegeben wird. |

### Schaltflächen

| Schaltfläche | Aktion |
|---|---|
| **Start Route (Route starten)** | Geocodiert Ziel/Zwischenziele, berechnet die Route, sucht Korridor-Tankstellen und aktualisiert die Sensor-Entitäten |
| **Cancel Route (Route abbrechen)** | Bricht die aktive Route ab und leert alle Route-Sensoren |

---

## Schritt-für-Schritt: Route planen

1. Öffne die **FWCAM-Karte** in Home Assistant.
2. Klicke auf den Reiter **🗺️ Route Planner**.
3. Gib dein **Ziel** in das Textfeld ein (Freitext-Adresse oder Stadtname).
4. Optional: Gib **Zwischenziele** ein (kommagetrennt).
5. Passe die **Korridorbreite** bei Bedarf an (Standard 5 km ist für die meisten Autobahnfahrten geeignet).
6. Wähle deinen bevorzugten **Routing-Anbieter** (OSRM wird für die normale Nutzung empfohlen).
7. Klicke auf **Start Route**.
8. Die Karte zeigt ein grünes **✅ Route Active**-Banner, sobald die Route berechnet wurde.

---

## Anzeige einer aktiven Route

Sobald eine Route aktiv ist, zeigt die Karte folgende Informationen:

### Routenzusammenfassung
- **Destination (Ziel)** – die geocodierte Zieladresse
- **Distance (Entfernung)** – Gesamtstrecke in km
- **Corridor Width (Korridorbreite)** – der konfigurierte Suchpuffer
- **Predicted Fuel Stop (Prognostizierter Tankstopp)** – geschätzte Entfernung in km bis zum benötigten Tankstopp (~X km)

### 🏆 Beste Korridor-Tankstelle
Die einzelne beste Tankstelle, bewertet nach **effektivem Preis** (siehe unten):
- **Tankstellenname**
- **Preis pro Liter** (€/l)
- **Umweg** – zusätzliche Strecke zur Tankstelle
- **Effektiver Preis** – Gesamtkosten pro Liter inkl. Umwegkosten
- Navigationslinks: **Google Maps**, **Waze**, **Apple Maps**

### 📋 Top Korridor-Tankstellen
Eine Tabelle der Top-3-Tankstellen mit denselben Spalten wie oben.

---

## Berechnung des effektiven Preises

Die Routenplanung bewertet Tankstellen nicht nur nach dem Zapfsäulenpreis, sondern nach dem **effektiven Preis pro Liter**, der den Umweg berücksichtigt:

```
effektiver_preis = zapfsäulenpreis + (umweg_km × kraftstoffkosten_pro_km)
```

wobei `kraftstoffkosten_pro_km` aus folgendem berechnet wird:
```
kraftstoffkosten_pro_km = durchschnittsverbrauch_l_pro_100km / 100 × zapfsäulenpreis
```

Eine Tankstelle, die 2 km vom Weg liegt, aber 3 Cent pro Liter günstiger ist, kann je nach Fahrzeugverbrauch trotzdem die beste Wahl sein.

---

## Sensor-Entitäten

Die Routenplanung erstellt folgende Home-Assistant-Sensor-Entitäten (werden von der FWCAM-Karte automatisch erkannt):

| Entität | Beschreibung |
|---|---|
| `sensor.[fahrzeugname]_active_route` | Routenstatus (`active` / `idle`) und Routenattribute |
| `sensor.[fahrzeugname]_predicted_fuel_stop` | Prognostizierte Entfernung (km) bis zum Tankstopp |
| `sensor.[fahrzeugname]_corridor_best_station` | Beste Korridor-Tankstelle mit Navigationslinks |
| `sensor.[fahrzeugname]_corridor_stations` | Liste aller bewerteten Korridor-Tankstellen |

### Attribute von `active_route`

| Attribut | Typ | Beschreibung |
|---|---|---|
| `destination` | string | Geocodierte Zieladresse |
| `total_distance_km` | float | Gesamtstrecke in km |
| `corridor_width_km` | float | Konfigurierte Korridorbreite |
| `routing_provider` | string | Verwendeter Anbieter (`osrm` / `openrouteservice` / `google`) |

### Attribute von `corridor_best_station`

| Attribut | Typ | Beschreibung |
|---|---|---|
| `station_name` | string | Tankstellenname |
| `price_per_litre` | float | Zapfsäulenpreis in €/l |
| `detour_km` | float | Umwegdistanz in km |
| `effective_price_eur_per_l` | float | Effektiver Preis nach Umwegkosten |
| `google_maps_url` | string | Direkter Google-Maps-Navigationslink |
| `waze_url` | string | Waze-Navigationslink |
| `apple_maps_url` | string | Apple-Maps-Navigationslink |

---

## Dienste direkt nutzen

Die Routenplanung kann auch über Home-Assistant-Dienste aufgerufen werden (z. B. in Automationen oder Skripten):

### `hafwcma.set_route`

```yaml
service: hafwcma.set_route
data:
  config_entry_id: "deine_config_entry_id"
  destination: "München Hauptbahnhof"
  waypoints:
    - "Augsburg"
    - "Ingolstadt"
  corridor_width_km: 5
  routing_provider: "osrm"
  # google_api_key: "AIza..." # nur für Google-Maps-Anbieter
```

| Parameter | Pflicht | Typ | Standard | Beschreibung |
|---|---|---|---|---|
| `config_entry_id` | ✅ | string | – | Deine FWCAM-Konfigurationseintrags-ID |
| `destination` | ✅ | string | – | Zieladresse |
| `waypoints` | ❌ | list[string] | `[]` | Zwischenstopps |
| `corridor_width_km` | ❌ | float | `5.0` | Korridorbreite in km |
| `routing_provider` | ❌ | string | `"osrm"` | `osrm` / `openrouteservice` / `google` |
| `google_api_key` | ❌ | string | `""` | Google Maps API-Schlüssel (nur für `google`-Anbieter) |

### `hafwcma.cancel_route`

```yaml
service: hafwcma.cancel_route
data:
  config_entry_id: "deine_config_entry_id"
```

---

## Telegram-Benachrichtigungen & Befehle

Wenn Telegram in der FWCAM-Integration konfiguriert ist, werden folgende Benachrichtigungen gesendet:

- **Route gestartet** – Bestätigung mit Ziel, Entfernung, prognostiziertem Tankstopp-km und den **Top-5-Tankstellen im Korridor** (Preis/l + Entfernung von der Route)
- **Route abgebrochen** – Bestätigungsnachricht

### Telegram-Befehle für die Routenplanung

Der Telegram-Bot unterstützt folgende Befehle:

| Befehl | Beschreibung |
|---|---|
| `/route start <Adresse>` | Route zum angegebenen Ziel starten |
| `/route start <Adresse> <km>` | Route starten mit eigener Korridorbreite (1–50 km). Beispiel: `/route start München Hbf 10` |
| `/route stop` | Aktive Route beenden |
| `/routestatus` | Aktuellen Routenstatus mit Tankstopp-Prognose und bester Tankstelle anzeigen |
| `/routecancel` | Aktive Route abbrechen (gleichwertig zu `/route stop`) |
| `/corridor [km]` | Korridorbreite der laufenden Route anpassen |
| `/help` | Alle Befehle anzeigen |

Zur Telegram-Konfiguration siehe [TELEGRAM_SETUP_DE.md](../TELEGRAM_SETUP_DE.md).

---

## Kartenkonfiguration

Der Routenplanungs-Reiter ist standardmäßig aktiviert. Um ihn auszublenden, füge `show_route_planner: false` zur Karten-YAML hinzu:

```yaml
type: custom:fwcam-card
entity: sensor.mein_auto_fuel_price
show_route_planner: false
```

---

## Fehlerbehebung

| Problem | Ursache | Lösung |
|---|---|---|
| „Start Route" reagiert nicht | Kein Ziel eingegeben oder JS-Fehler | Browser-Konsole öffnen (F12) und nach Fehlern suchen; sicherstellen, dass das Zielfeld nicht leer ist |
| Route aktiv, aber keine Tankstellen angezeigt | Keine TankerKönig-Stationen im Korridor gefunden | Korridorbreite erhöhen oder TankerKönig-API-Schlüssel prüfen |
| Ziel nicht gefunden | Geocoding über Nominatim fehlgeschlagen | Genauere Adresse angeben (Straße, Hausnummer, Stadt) |
| Entfernung zeigt `—` | Routing-Anbieter hat einen Fehler zurückgegeben | Anbieter wechseln (OSRM versuchen); Netzwerkverbindung prüfen |
| Tankstopp-Prognose nicht verfügbar | Tankstand oder Verbrauch nicht konfiguriert | Sicherstellen, dass Tankstand und Durchschnittsverbrauch durch die Fahrzeug-Integration gemeldet werden |
| Google-Maps-Anbieter schlägt fehl | Ungültiger API-Schlüssel oder Abrechnung nicht aktiviert | Schlüssel in der [Google Cloud Console](https://console.cloud.google.com) prüfen (Directions API muss aktiviert sein) |

---

## Einschränkungen

- **Nur Deutschland** – TankerKönig-Tankstellendaten decken ausschließlich Deutschland ab.
- **OSRM öffentlicher Server** – der kostenlose OSRM-Demoserver kann bei häufiger Nutzung gedrosselt sein; für intensiven Einsatz empfiehlt sich eine selbst gehostete OSRM-Instanz.
- **Kraftstoffsorte** – die Korridor-Suche verwendet die in den Integrationseinstellungen konfigurierte Kraftstoffsorte.
- **Echtzeitpreise** – Tankstellenpreise werden im TankerKönig-Abfrageintervall aktualisiert (Standard: alle 30 Minuten).

---

## Verwandte Dokumentation

- [ROUTE_PLANNER_GUIDE.md](ROUTE_PLANNER_GUIDE.md) – Englische Version dieser Anleitung
- [TELEGRAM_SETUP_DE.md](../TELEGRAM_SETUP_DE.md) – Telegram-Benachrichtigungen konfigurieren
- [VEHICLE_ENTITIES.md](../VEHICLE_ENTITIES.md) – Fahrzeug für die Tankstandsmeldung einbinden
- [docs/dev_docs/ROUTE_CORRIDOR_STATION_SEARCH_CONCEPT.md](../dev_docs/ROUTE_CORRIDOR_STATION_SEARCH_CONCEPT.md) – Technisches Designdokument
