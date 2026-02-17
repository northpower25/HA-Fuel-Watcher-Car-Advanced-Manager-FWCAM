# haFWCMA - Fuel Watcher Car Advanced Manager
## Vollständige Dokumentation (Deutsch)

---

## 📑 Inhaltsverzeichnis

1. [Grundlagen](#1-grundlagen)
2. [Setup und Konfiguration](#2-setup-und-konfiguration)
3. [Fahrzeug-Integrationen](#3-fahrzeug-integrationen)
4. [Tankpreis-API Anbindung](#4-tankpreis-api-anbindung)
5. [Telegram-Integration](#5-telegram-integration)
6. [Funktionsübersicht](#6-funktionsübersicht)
7. [Erweiterte Funktionen](#7-erweiterte-funktionen)
8. [Blueprints und Automationen](#8-blueprints-und-automationen)
9. [Fehlerbehebung](#9-fehlerbehebung)

---

## 1. Grundlagen

### 1.1 Was ist haFWCMA?

**Fuel Watcher Car Advanced Manager (haFWCMA)** ist eine umfassende Home Assistant Integration zur:
- Überwachung von Kraftstoffpreisen
- Verwaltung von Fahrzeug-Tankständen
- Erstellung intelligenter Tankempfehlungen
- Automatischen Erkennung von Tankvorgängen
- Aufzeichnung von Fahrten (Fahrtenbuch)
- Berechnung von Kraftstoffverbrauch und Kosten

### 1.2 Hauptfunktionen

#### ⛽ Tankpreis-Überwachung
- Echtzeit-Kraftstoffpreise über Tankerkönig API (Deutschland)
- Suche nach Tankstellen im konfigurierbaren Radius
- Unterstützung für E5, E10 und Diesel
- Sortierung nach Entfernung und Preis
- Preistrendanalyse und Vorhersagen

#### 🚗 Fahrzeugverwaltung
- Integration mit bestehenden Fahrzeug-Entities
- Automatische Tankerkennung
- Echtzeit-Verbrauchsüberwachung
- Reichweitenberechnung
- Mehrere Fahrzeuge unterstützt

#### 📊 Intelligente Vorhersagen
- Selbstlernendes Verbrauchstracking
- Machine Learning für erweiterte Prognosen
- Wochentag-basierte Muster
- Tankempfehlungen mit Dringlichkeitsstufen
- Kostenoptimierung (Preis vs. Entfernung)

#### 📱 Telegram-Integration
- Bidirektionale Kommunikation
- Preisalarme und Warnungen
- Tankvorgang-Protokollierung per Chat
- OCR für Tankbelege
- Spracherkennung für Tankdaten

#### 🗺️ Fahrtenbuch (Trip Tracking)
- Automatische Fahrterkennung
- Kostenberechnung (tatsächlich vs. Pendlerpauschale)
- Mustererkennung für wiederkehrende Routen
- POI-Verwaltung (Zuhause, Arbeit, Tankstellen)
- DSGVO-konform mit Anonymisierung

### 1.3 Systemanforderungen

**Home Assistant**
- Version: 2023.9 oder höher
- Recorder-Integration aktiviert (für Verlaufsdaten)
- HACS installiert (empfohlen)

**Externe APIs**
- Tankerkönig API-Key (kostenlos, Deutschland)
- Telegram Bot Token (optional, für Benachrichtigungen)
- OpenStreetMap Nominatim (optional, für Geocoding)

**Fahrzeug-Integration**
- Mindestens eine der folgenden Entities:
  - Kilometerzähler (odometer)
  - Tankfüllstand (fuel level)
  - Reichweite (range)
  - Position (device_tracker)

### 1.4 Datenfluss-Übersicht

```
┌─────────────────┐
│  Tankerkönig    │
│      API        │──┐
└─────────────────┘  │
                     │
┌─────────────────┐  │    ┌──────────────────┐
│   Fahrzeug-     │  │    │                  │
│   Integration   │──┼───▶│   haFWCMA        │
│   (BMW, etc.)   │  │    │   Integration    │
└─────────────────┘  │    │                  │
                     │    └──────────────────┘
┌─────────────────┐  │             │
│   Telegram      │──┘             │
│      Bot        │                │
└─────────────────┘                ▼
                          ┌─────────────────┐
                          │  Home Assistant │
                          │    Entities     │
                          │   & Services    │
                          └─────────────────┘
```

---

## 2. Setup und Konfiguration

### 2.1 Installation via HACS (Empfohlen)

**Schritt 1: HACS Repository hinzufügen**
1. Öffnen Sie HACS in Home Assistant
2. Klicken Sie auf "Integrationen"
3. Klicken Sie auf "⋮" (Menü) → "Custom repositories"
4. Fügen Sie hinzu:
   - **Repository**: `northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM`
   - **Kategorie**: Integration
5. Klicken Sie "Hinzufügen"

**Schritt 2: Integration installieren**
1. Suchen Sie nach "Fuel Watcher Car Advanced Manager"
2. Klicken Sie "Download"
3. Starten Sie Home Assistant neu

**Schritt 3: Integration hinzufügen**
1. Gehen Sie zu **Einstellungen** → **Geräte & Dienste**
2. Klicken Sie **+ Integration hinzufügen**
3. Suchen Sie "Fuel Watcher Car Advanced Manager"
4. Folgen Sie dem Konfigurations-Assistenten

📖 **Detaillierte Anleitung**: [HACS_INSTALLATION_DE.md](HACS_INSTALLATION_DE.md)

### 2.2 Konfigurations-Schritte

Der Setup-Assistent führt Sie durch folgende Schritte:

#### Schritt 1: Tankerkönig API-Konfiguration
- **API-Key**: Ihr Tankerkönig API-Schlüssel
- **Latitude/Longitude**: Standard-Suchposition (z.B. Ihr Zuhause)
- **Suchradius**: Entfernung in km (1-25 km)
- **Fuel Type**: E5, E10 oder Diesel

**API-Key erhalten:**
1. Registrieren Sie sich auf https://creativecommons.tankerkoenig.de
2. Beantragen Sie einen kostenlosen API-Key
3. Kopieren Sie den Key in die Konfiguration

**Technische Limitationen:**
- Max. 10 Anfragen pro Minute
- Max. 50 Stationen pro Anfrage
- Nur Deutschland verfügbar

#### Schritt 2: Fahrzeug-Konfiguration
- **Fahrzeugname**: Anzeigename (z.B. "Mein BMW")
- **Tankkapazität**: Maximales Volumen in Litern
- **Kraftstofftyp**: E5, E10, Diesel, Super Plus

#### Schritt 3: Fahrzeug-Entities (Optional)
Verknüpfen Sie vorhandene Home Assistant Entities:

- **Kilometerzähler**: `sensor.my_car_odometer`
- **Tankfüllstand**: `sensor.my_car_fuel_level`
- **Reichweite**: `sensor.my_car_range`
- **Position**: `device_tracker.my_car`

**Wichtig**: Nur device_tracker Entities werden für Position unterstützt.

📖 **Details**: [docs/VEHICLE_ENTITIES.md](VEHICLE_ENTITIES.md)

#### Schritt 4: Telegram (Optional)
- **Bot Token**: Von @BotFather erhalten
- **Chat ID**: Ihre Telegram Chat-ID

**API-Validierung**: Die Integration testet automatisch die Verbindungen während der Einrichtung.

### 2.3 Optionen konfigurieren

Nach der Installation können Sie Einstellungen anpassen:

1. Gehen Sie zu **Einstellungen** → **Geräte & Dienste**
2. Finden Sie "Fuel Watcher Car Advanced Manager"
3. Klicken Sie **Konfigurieren**

**Verfügbare Optionen:**
- Suchradius ändern
- API-Aktualisierungsintervall (1-60 Minuten)
- Vorhersage-Einstellungen
- Telegram-Einstellungen aktualisieren
- Fahrzeug-Entities ändern

### 2.4 Entities-Übersicht

Nach der Installation werden folgende Entities erstellt:

**Sensoren:**
- `sensor.{name}_fuel_price` - Aktueller Kraftstoffpreis
- `sensor.{name}_nearest_station` - Nächste Tankstelle
- `sensor.{name}_cheapest_station` - Günstigste Tankstelle
- `sensor.{name}_consumption_average` - Durchschnittsverbrauch
- `sensor.{name}_consumption_forecast` - Verbrauchsprognose
- `sensor.{name}_refueling_log` - Tankvorgang-Protokoll
- `sensor.{name}_trip_log` - Fahrtenbuch
- `sensor.{name}_current_trip` - Aktuelle Fahrt
- `sensor.{name}_fuel_price_api_debug` - Debug-Informationen zur Tankstellen-API
- `sensor.{name}_car_data_debug` - Debug-Informationen zu Fahrzeugdaten

**Schalter:**
- `switch.{name}_manual_refresh` - Manuelle Datenaktualisierung
- `switch.{name}_trip_tracking` - Fahrtenerfassung ein/aus

**Buttons:**
- `button.{name}_test_api` - API-Verbindung testen

**Binärsensoren:**
- `binary_sensor.{name}_on_trip` - Auf Fahrt (Ja/Nein)

---

## 3. Fahrzeug-Integrationen

### 3.1 Unterstützte Fahrzeug-Integrationen

haFWCMA kann mit jeder Home Assistant Integration zusammenarbeiten, die folgende Entity-Typen bereitstellt:

#### BMW Connected Drive
```yaml
# Beispiel-Entities
sensor.bmw_mileage          # Kilometerzähler
sensor.bmw_fuel_level       # Tankfüllstand in Litern
sensor.bmw_remaining_range  # Reichweite in km
device_tracker.bmw_location # GPS-Position
```

#### Tesla
```yaml
sensor.tesla_odometer
sensor.tesla_battery_level  # Für Elektro (nicht unterstützt)
device_tracker.tesla_location
```

#### Mercedes Me
```yaml
sensor.mercedes_odometer
sensor.mercedes_fuel_level
sensor.mercedes_range
device_tracker.mercedes_location
```

#### Generic OBD2
```yaml
sensor.car_mileage
sensor.car_fuel_tank
device_tracker.car_gps
```

### 3.2 Entity-Anforderungen

#### Kilometerzähler (Odometer)
- **Typ**: `sensor.*`
- **Einheit**: Kilometer (km)
- **Format**: Numerisch (z.B. 123456.7)
- **Verwendung**: Verbrauchsberechnung, Tankerkennung

**Wichtig**: 
- Der Kilometerzähler muss kontinuierlich ansteigen
- Sprünge oder Rückgänge können zu falschen Berechnungen führen

#### Tankfüllstand (Fuel Level)
- **Typ**: `sensor.*`
- **Einheit**: Liter (L) oder Prozent (%)
- **Format**: Numerisch (z.B. 45.5 oder 75)
- **Verwendung**: Automatische Tankerkennung, Reichweitenberechnung

**Unterstützte Formate:**
- Absolute Werte: `45.5 L`, `32 L`
- Prozent: `75%`, `80`

**Tankerkennung-Logik:**
```
Wenn:
  - Tankfüllstand steigt um ≥ 5 Liter (oder ≥ 10%)
  - Kilometerzähler hat sich seit letztem Check erhöht
  - Mindestens 30 Minuten seit letztem Tankvorgang
Dann:
  - Neuen Tankvorgang protokollieren
  - Verbrauch seit letztem Tanken berechnen
  - Telegram-Benachrichtigung senden (optional)
```

#### Reichweite (Range)
- **Typ**: `sensor.*`
- **Einheit**: Kilometer (km)
- **Format**: Numerisch (z.B. 450.0)
- **Verwendung**: Verbrauchsanalyse, Vorhersagen

#### Position (Device Tracker)
- **Typ**: `device_tracker.*` (Nur device_tracker!)
- **Attribute**: `latitude`, `longitude`
- **Verwendung**: Nächste Tankstelle finden, Fahrtenerkennung

**Wichtig**: Sensor-Entities mit GPS-Daten werden NICHT unterstützt.

### 3.3 Manuelle Entity-Erstellung

Wenn Ihre Fahrzeug-Integration keine passenden Entities bereitstellt:

#### Template Sensor für Prozent → Liter
```yaml
# configuration.yaml
template:
  - sensor:
      - name: "Auto Tankfüllstand Liter"
        unit_of_measurement: "L"
        state: >
          {% set percent = states('sensor.car_fuel_percent') | float(0) %}
          {% set capacity = 60 %}  # Ihre Tankkapazität
          {{ (percent / 100 * capacity) | round(1) }}
```

#### Template Sensor für Meilen → Kilometer
```yaml
template:
  - sensor:
      - name: "Auto Kilometerzähler"
        unit_of_measurement: "km"
        state: >
          {% set miles = states('sensor.car_odometer_miles') | float(0) %}
          {{ (miles * 1.60934) | round(1) }}
```

### 3.4 Technische Limitationen

**Datenqualität:**
- Entities müssen regelmäßig aktualisiert werden (mind. täglich)
- Veraltete Daten (>24h) werden mit Warnung angezeigt
- `unavailable` oder `unknown` States werden ignoriert

**Genauigkeit:**
- Tankerkennungsgenauigkeit: ±2 Liter
- Verbrauchsberechnung: ±0.5 L/100km (abhängig von Datenqualität)
- Reichweitenvorhersage: ±50 km

**Performance:**
- Historiendaten: Max. 90 Tage für Berechnungen
- Aktualisierungsrate: Folgt der Entity-Update-Rate
- Speicher: ~1 MB pro 1000 Tankvorgänge

---

## 4. Tankpreis-API Anbindung

### 4.1 Tankerkönig API (Deutschland)

Die Integration nutzt die offizielle Tankerkönig API für Echtzeit-Kraftstoffpreise in Deutschland.

#### API-Key erhalten
1. Besuchen Sie https://creativecommons.tankerkoenig.de
2. Registrieren Sie sich kostenlos
3. Beantragen Sie einen API-Key
4. Erhalten Sie Ihren Key per E-Mail

**Kosten**: Kostenlos für private Nutzung

#### API-Limitierungen
- **Rate Limit**: 10 Anfragen pro Minute
- **Maximale Stationen**: 50 pro Anfrage
- **Geographische Abdeckung**: Nur Deutschland
- **Verfügbare Kraftstofftypen**: E5, E10, Diesel, Super Plus

**Technische Details:**
```python
# API Endpoint
GET https://creativecommons.tankerkoenig.de/json/list.php

# Parameter
api_key: Your_API_Key
lat: 51.5074  # Latitude
lng: 9.9347   # Longitude
rad: 5        # Radius in km
type: e5      # Fuel type
sort: dist    # Sort by distance
```

### 4.2 Konfiguration in haFWCMA

#### Standard-Suchposition
Die Latitude/Longitude in der Konfiguration definiert:
- Wo nach Tankstellen gesucht wird (wenn keine Fahrzeugposition verfügbar)
- Ihr "Zuhause" für Entfernungsberechnungen
- Basis für Preisvergleiche

**Beste Praxis:**
- Nutzen Sie die Koordinaten Ihres Zuhauses
- Falls Fahrzeugposition verfügbar: Diese wird automatisch bevorzugt

#### Suchradius
- **Minimum**: 1 km
- **Maximum**: 25 km
- **Empfohlen**: 5-10 km (für Stadt), 15-25 km (für Land)

**Beachten Sie:**
- Größerer Radius = mehr Stationen = mehr API-Daten
- Kleinerer Radius = schnellere Antworten
- API-Limit: max. 50 Stationen

#### Update-Intervall
- **Standard**: 15 Minuten
- **Bereich**: 1-60 Minuten
- **Empfohlen**: 10-30 Minuten

**Randomisierung**: 
Das tatsächliche Intervall wird leicht randomisiert (±10%), um simultane API-Aufrufe zu vermeiden.

### 4.3 Preisdaten-Verarbeitung

#### Sensoren
**Fuel Price Sensor** (`sensor.{name}_fuel_price`)
- Aktueller Preis pro Liter für Ihren Kraftstofftyp
- Attribute:
  - `price_history`: Letzte 24 Stunden
  - `trend`: rising/falling/stable
  - `price_change`: Änderung seit letzter Aktualisierung
  - `last_update`: Zeitstempel

**Nearest Station** (`sensor.{name}_nearest_station`)
- Nächste Tankstelle basierend auf Position
- Attribute:
  - `name`: Tankstellenname
  - `brand`: Marke (Shell, Aral, etc.)
  - `address`: Vollständige Adresse
  - `distance`: Entfernung in km
  - `prices`: {e5, e10, diesel}
  - `lat`, `lng`: GPS-Koordinaten
  - `navigation_links`: Google Maps, Apple Maps, Waze

**Cheapest Station** (`sensor.{name}_cheapest_station`)
- Günstigste Tankstelle im Suchradius
- Gleiche Attribute wie Nearest Station
- Zusätzlich:
  - `savings_vs_nearest`: Ersparnis in EUR
  - `extra_distance`: Mehrkilometer zur nächsten

#### Preisvergleichs-Logik

Die Integration berechnet automatisch, ob sich die Fahrt zur günstigeren Tankstelle lohnt:

```python
# Vereinfachte Berechnungslogik
extra_distance_km = cheapest.distance - nearest.distance
fuel_needed_for_trip = (extra_distance_km / 100) * consumption_l_per_100km
extra_fuel_cost = fuel_needed_for_trip * nearest.price_per_liter

price_difference_per_liter = nearest.price - cheapest.price
tank_capacity = 60  # Liter
max_savings = price_difference_per_liter * tank_capacity

net_savings = max_savings - extra_fuel_cost

# Empfehlung: Weiterfahren nur wenn net_savings >= 0.50 EUR
```

**Konstante**: `STATION_RECOMMENDATION_MIN_SAVINGS = 0.50` EUR

### 4.4 Historische Preisanalyse

Die Integration sammelt und analysiert Preisdaten über Zeit:

**Weekday Price Statistics** (`sensor.{name}_weekday_price_statistics`)
- Durchschnittspreis pro Wochentag
- Beste Tankzeiten identifizieren
- Top 3 günstigste Stationen pro Tag

**Period Price Statistics** (`sensor.{name}_period_price_statistics`)
- Letzte Woche, 14 Tage, Monat
- Preistrends und -analysen
- Durchschnitts-, Min-, Max-Preise

### 4.5 Zukünftige API-Erweiterungen

**Geplante Provider** (siehe TODO.md):
- Europa: Autobahn Tank & Rast (ATAR)
- UK: PetrolPrices API
- US: GasBuddy API
- International: OpenCharge (für E-Ladestationen)

**Framework vorhanden**: Das Provider-System ist erweiterbar.

---

## 5. Telegram-Integration

### 5.1 Übersicht

Die Telegram-Integration bietet zwei Ebenen:
1. **Einweg-Benachrichtigungen** (nur haFWCMA → Sie)
2. **Bidirektionale Kommunikation** (haFWCMA ↔ Sie)

### 5.2 Einweg-Benachrichtigungen (Einfaches Setup)

Nur Benachrichtigungen empfangen, keine Befehle senden.

#### Setup-Schritte
1. **Bot erstellen** mit @BotFather in Telegram
2. **Chat-ID** ermitteln (via @userinfobot)
3. **In haFWCMA konfigurieren** (Bot Token + Chat ID)

📖 **Detaillierte Anleitung**: [docs/TELEGRAM_SETUP_DE.md](TELEGRAM_SETUP_DE.md)

#### Benachrichtigungstypen
- 📉 **Preisalarme**: "Diesel unter 1.40€ bei Shell!"
- ⛽ **Tankwarnungen**: "Nur noch 5 Liter im Tank!"
- 💡 **Empfehlungen**: "Jetzt tanken? Preis steigt voraussichtlich morgen."
- ✅ **Tankerkennung**: "Tankvorgang erkannt: 45.5L für 68.22€"

### 5.3 Bidirektionale Kommunikation (Vollständiges Setup)

Ermöglicht Tankvorgang-Protokollierung per Chat und Befehle.

#### Zusätzlicher Setup
**Home Assistant telegram_bot Integration**

```yaml
# configuration.yaml
telegram_bot:
  - platform: polling
    api_key: YOUR_BOT_TOKEN
    allowed_chat_ids:
      - YOUR_CHAT_ID
```

**Wichtig**: Verwenden Sie den gleichen Bot Token wie in haFWCMA!

📖 **Detaillierte Anleitung**: [docs/TELEGRAM_SETUP_DE.md](TELEGRAM_SETUP_DE.md)

### 5.4 Tankvorgang-Protokollierung per Telegram

#### Workflow

1. **Automatische Erkennung**: Integration erkennt Tankvorgang
2. **Benachrichtigung**: Sie erhalten Telegram-Nachricht mit Basisinformationen
3. **Interaktive Vervollständigung**: Antworten Sie mit Details
4. **Multi-Turn Dialog**: Mehrfache Nachrichten ergänzen Daten
5. **Bestätigung**: Klicken Sie "Fertig" oder "Bestätigen"

#### Unterstützte Eingabeformate

**Text-Nachrichten**
```
45 Liter 1.599 Shell
68.50€ Aral Hauptstraße
1650km KM-Stand
Diesel e10 super
```

**Sprach-Nachrichten**
- Automatische Transkription (Telegram STT)
- Gleiche Parsing-Logik wie Text
- Fallback zu Text bei Erkennungsfehlern

**Fotos (OCR)**
- Senden Sie Foto von Tankbeleg
- OCR extrahiert Text
- Parsing wie bei Text-Nachrichten

#### Erkennungs-Features

**Kraftstoffmenge**
- `45 Liter`, `45L`, `45.5 l`
- Minimum: 1 Liter
- Maximum: Tankkapazität + 10%

**Preis**
- `1.599` (Preis/Liter)
- `68.50€` (Gesamtkosten)
- Automatische Unterscheidung durch Wertebereich

**Kilometerstand**
- `1650km`, `1650 KM`, `KM-Stand: 123456`
- Minimum: 4 Ziffern
- Validierung gegen letzte Einträge

**Tankstellenname**
- Marken: Shell, Aral, Esso, Total, Jet, OMV, etc.
- Strukturierte Formate: `MARKE [PLZ] ORT [STRASSE]`
- Fallback: Marke + 3 Worte

**Kraftstofftyp**
- `e5`, `super e5`, `E5`
- `e10`, `super e10`, `E10`
- `diesel`, `Diesel`
- `super plus`, `Super Plus` (→ e5)

#### Smart Confirmation

Nachrichten heben neu erkannte Felder hervor:

```
✅ Erkannt: 45.5 Liter, 1.599€/L
❓ Noch fehlend: Tankstelle, Kilometerstand

💡 Tipp: Senden Sie eine Nachricht wie "Shell 1650km"
```

**Buttons:**
- ✅ **Fertig** (unvollständige Daten erlaubt)
- ✅ **Bestätigen** (nur bei vollständigen Daten)
- ✏️ **Weiter bearbeiten** (Dialog fortsetzen)

📖 **Details**: [SMART_CONFIRMATION_FORMATTING_DE.md](SMART_CONFIRMATION_FORMATTING_DE.md)

### 5.5 POI-Integration

Tankstellen aus Telegram-Antworten werden automatisch als POI gespeichert:

- **Typ**: `gas_station`
- **Duplikatsprüfung**: Name und Position
- **Integration**: Mit Trip Log POI-System
- **Verwendung**: Besuchszählung, Statistiken

### 5.6 Technische Limitationen

**Telegram Bot API**
- Message Rate: Max. 30 Nachrichten/Sekunde
- File Size: Max. 20 MB für Fotos
- OCR: Nur für lateinische Zeichen optimiert

**Sprach-Transkription**
- Telegram's STT (Speech-to-Text)
- Genauigkeit: ~85% (Deutsch)
- Funktioniert nur mit Telegram Mobile App

**Datenschutz**
- Alle Daten werden lokal in Home Assistant gespeichert
- Keine externen KI-APIs (außer Telegram STT/OCR)
- POI-Anonymisierung optional verfügbar

---

## 6. Funktionsübersicht

### 6.1 Trip-Erkennung und -Bearbeitung

#### Was ist Trip Tracking?

Das **Fahrtenbuch-Feature** erkennt und protokolliert automatisch Ihre Fahrten:
- Start/Ziel mit GPS-Koordinaten
- Distanz und Dauer
- Kraftstoffverbrauch und -kosten
- Zweck (Arbeit, Privat, Geschäftlich)
- Anonymisierung für Datenschutz

📖 **Detaillierte Dokumentation**: [docs/TRIP_TRACKING_README.md](TRIP_TRACKING_README.md)

#### Automatische Fahrterkennung

**Bedingungen für Trip-Start:**
```
Wenn:
  - Kilometerzähler steigt um ≥ 0.5 km
  - Fahrzeug war vorher ≥ 10 Minuten still
  - Trip Tracking ist aktiviert (switch.{name}_trip_tracking = on)
Dann:
  - Neue Fahrt beginnen
  - Start-Position speichern (wenn GPS verfügbar)
  - Start-Zeit aufzeichnen
```

**Bedingungen für Trip-Ende:**
```
Wenn:
  - Kilometerzähler ändert sich nicht mehr
  - Fahrzeug steht ≥ 10 Minuten still
  - Oder: Neuer Tankvorgang erkannt
Dann:
  - Fahrt beenden
  - End-Position speichern
  - Distanz, Dauer, Verbrauch berechnen
  - Optional: Geocoding für Adressen
```

#### Kostenberechnung

**Reale Kraftstoffkosten:**
```python
fuel_consumed = distance_km / 100 * consumption_l_per_100km
fuel_cost = fuel_consumed * current_fuel_price
total_cost = fuel_cost + additional_costs  # z.B. Parkgebühren
```

**Deutsche Pendlerpauschale** (2024):
```python
# Bis 20 km: 0.30 € pro km
# Ab 21 km: 0.38 € pro km
if distance_km <= 20:
    tax_compensation = distance_km * 0.30
else:
    tax_compensation = (20 * 0.30) + ((distance_km - 20) * 0.38)
```

**Vergleich:**
```python
savings_vs_tax = tax_compensation - real_cost
# Positiv: Sie bekommen mehr zurück als Sie ausgeben
# Negativ: Echte Kosten höher als Erstattung
```

#### Mustererkennung (Pattern Recognition)

Die Integration lernt wiederkehrende Routen:

**Erkennung:**
- Start- und Zielposition ähnlich (±500m)
- Distanz ähnlich (±10%)
- Mindestens 3x gefahren

**Pattern-Attribute:**
- `name`: "Zuhause → Arbeit"
- `count`: Wie oft gefahren
- `avg_distance`: Durchschnittliche Distanz
- `avg_duration`: Durchschnittliche Dauer
- `avg_consumption`: Durchschnittlicher Verbrauch

**Verwendung:**
- Automatische Zweck-Zuweisung
- Vorhersage von Verbrauch und Dauer
- Anonymisierung (siehe unten)

#### POI-Verwaltung

**POI-Typen:**
- `home`: Zuhause (automatisch erkannt)
- `work`: Arbeit (automatisch erkannt)
- `gas_station`: Tankstelle (aus Tankprotokollen)
- `custom`: Benutzerdefiniert

**Auto-Erkennung:**
- **Home**: Häufigster Startpunkt nachts (22-06 Uhr)
- **Work**: Häufigster Zielpunkt werktags (08-18 Uhr)

**Besuchszählung:**
Jede Fahrt zu/von einem POI erhöht den Besuchszähler.

#### DSGVO-konforme Anonymisierung

**Zeitbasierte Regeln:**
```yaml
# Beispiel-Konfiguration
anonymization_rules:
  - after_days: 30
    action: remove_gps      # GPS-Koordinaten löschen
  - after_days: 90
    action: remove_address  # Geocodierte Adressen löschen
  - after_days: 365
    action: anonymize_full  # Vollständige Anonymisierung
```

**Pattern-basierte Anonymisierung:**
- Fahrten mit erkanntem Muster: GPS sofort entfernen
- Nur Pattern-Referenz behalten (z.B. "Pattern #3")

**Datenlöschung:**
```yaml
data_retention:
  max_trip_age_days: 1095  # 3 Jahre
  auto_delete: true
```

#### Services für Trip-Verwaltung

**hafwcma.add_trip**
```yaml
service: hafwcma.add_trip
data:
  config_entry_id: "abc123"
  start_time: "2024-01-15T08:00:00"
  end_time: "2024-01-15T08:30:00"
  distance_km: 25.5
  purpose: "work"
  notes: "Via Autobahn"
```

**hafwcma.edit_trip**
```yaml
service: hafwcma.edit_trip
data:
  config_entry_id: "abc123"
  trip_id: "trip_20240115_080000"
  purpose: "business"
  additional_costs: 5.00  # Parkgebühr
```

**hafwcma.delete_trip**
```yaml
service: hafwcma.delete_trip
data:
  config_entry_id: "abc123"
  trip_id: "trip_20240115_080000"
```

**hafwcma.export_trips**
```yaml
service: hafwcma.export_trips
data:
  config_entry_id: "abc123"
  format: "csv"  # oder "json"
  start_date: "2024-01-01"
  end_date: "2024-12-31"
```

### 6.2 Tankvorgangs-Erkennung und -Bearbeitung

#### Automatische Erkennung

**Erkennungslogik:**
```python
# Bedingungen (ALLE müssen erfüllt sein)
tank_increase = current_tank_level - previous_tank_level
odometer_increase = current_odometer - previous_odometer

is_refueling = (
    tank_increase >= 5.0  # Mindestens 5 Liter
    AND odometer_increase > 0  # Kilometerzähler gestiegen
    AND minutes_since_last_refuel >= 30  # Mindestabstand
)
```

**Erkannte Daten:**
- **Timestamp**: Zeitpunkt der Erkennung
- **Liters**: Getankte Menge
- **Odometer**: Aktueller Kilometerstand
- **Price** (optional): Aktueller Kraftstoffpreis
- **Station** (optional): Empfohlene Station zum Zeitpunkt
- **Position** (optional): GPS-Koordinaten

**Datenqualität**: `auto_detected` (Confidence: 0.85)

#### Manuelle Erfassung

**Via Lovelace Card:**
1. Öffnen Sie die FWCAM Card
2. Klicken Sie "Refueling Log" Tab
3. Klicken Sie "+ Tankvorgang hinzufügen"
4. Füllen Sie das Formular aus
5. Klicken Sie "Speichern"

**Via Service:**
```yaml
service: hafwcma.add_refuel_event
data:
  config_entry_id: "abc123"
  timestamp: "2024-01-15T14:30:00"
  liters_refueled: 45.5
  odometer_km: 123456
  price_per_liter: 1.599
  total_cost: 72.70
  station_name: "Shell Station"
  fuel_type: "diesel"
  data_quality: "manual"
  confidence: 1.0
```

**Datenqualität**: `manual` (Confidence: 1.0)

#### Via Telegram

Siehe [5.4 Tankvorgang-Protokollierung per Telegram](#54-tankvorgang-protokollierung-per-telegram)

**Datenqualität**: 
- `telegram_text` (Confidence: 0.75)
- `telegram_voice` (Confidence: 0.65)
- `telegram_photo` (Confidence: 0.70)

#### Datenfelder

**Pflichtfelder:**
- `timestamp`: Zeitpunkt
- `liters_refueled`: Getankte Liter

**Optionale Felder:**
- `odometer_km`: Kilometerstand
- `price_per_liter`: Preis pro Liter
- `total_cost`: Gesamtkosten
- `station_name`: Tankstellenname
- `station_address`: Adresse
- `fuel_type`: Kraftstofftyp
- `latitude`, `longitude`: Position
- `notes`: Notizen
- `telegram_*`: Telegram-Metadaten

**Berechnete Felder:**
- `consumption_l_per_100km`: Verbrauch seit letztem Tanken
- `cost_per_km`: Kosten pro Kilometer
- `distance_since_last_refuel`: Gefahrene Kilometer

#### Bearbeitung

**Via Lovelace Card:**
1. Klicken Sie auf einen Eintrag in der Refueling Log Tabelle
2. Edit-Dialog öffnet sich
3. Ändern Sie Felder
4. Klicken Sie "Speichern"

**Via Service:**
```yaml
service: hafwcma.update_refueling_event
data:
  config_entry_id: "abc123"
  event_id: "refuel_20240115_143000"
  price_per_liter: 1.589  # Korrigierter Preis
  station_name: "Aral Station"  # Korrigierter Name
```

**Löschung:**
```yaml
service: hafwcma.delete_refueling_event
data:
  config_entry_id: "abc123"
  event_id: "refuel_20240115_143000"
```

#### Verbrauchsberechnung

**Grundformel:**
```python
distance = current_odometer - last_refuel_odometer
consumption_l_per_100km = (liters_refueled / distance) * 100
```

**Beispiel:**
```
Letzter Tankvorgang: 123000 km, 50 Liter
Aktueller Tankvorgang: 123600 km, 45 Liter

distance = 123600 - 123000 = 600 km
consumption = (45 / 600) * 100 = 7.5 L/100km
```

**Wichtig:**
- Erste Tankung: Kein Verbrauch berechnet (keine Referenz)
- Ungültige Daten: Negative Distanz → Fehler
- Tanklücken: Verbrauch kann verfälscht sein (z.B. Kanister)

### 6.3 Tankpreis-Abruf und Vorschläge

#### Preis-Sensoren

**Current Fuel Price** (`sensor.{name}_fuel_price`)
```yaml
state: 1.599  # EUR pro Liter
attributes:
  price_history:
    - timestamp: 2024-01-15T10:00:00
      price: 1.589
    - timestamp: 2024-01-15T10:15:00
      price: 1.599
  trend: "rising"  # rising, falling, stable
  price_change: +0.010  # EUR
  last_update: 2024-01-15T10:30:00
  source: "tankerkoenig"
```

**Trend-Berechnung:**
```python
recent_prices = price_history[-12:]  # Letzte 3 Stunden (15min Intervall)
avg_early = mean(recent_prices[:6])
avg_late = mean(recent_prices[6:])

if avg_late > avg_early + 0.005:
    trend = "rising"
elif avg_late < avg_early - 0.005:
    trend = "falling"
else:
    trend = "stable"
```

#### Stations-Sensoren

**Nearest Station** (`sensor.{name}_nearest_station`)
```yaml
state: "Shell - Hauptstraße 123"
attributes:
  name: "Shell"
  brand: "Shell"
  address: "Hauptstraße 123, 12345 Musterstadt"
  distance: 1.2  # km
  prices:
    e5: 1.599
    e10: 1.549
    diesel: 1.479
  lat: 51.5074
  lng: 9.9347
  station_id: "abc123def"
  is_open: true
  last_update: 2024-01-15T10:30:00
  navigation_links:
    google_maps: "https://www.google.com/maps/dir/?api=1&destination=51.5074,9.9347"
    apple_maps: "http://maps.apple.com/?daddr=51.5074,9.9347"
    waze: "https://waze.com/ul?ll=51.5074,9.9347&navigate=yes"
```

**Cheapest Station** (`sensor.{name}_cheapest_station`)
Gleiche Attribute wie Nearest Station, plus:
```yaml
attributes:
  savings_vs_nearest: 0.020  # EUR/L günstiger
  extra_distance: 3.5  # km weiter
  recommended: true  # Lohnt sich die Fahrt?
  net_savings: 0.75  # EUR bei vollem Tank nach Abzug Fahrtkosten
```

#### Empfehlungslogik

**Einfache Empfehlung:**
```python
# Nächste Station verwenden, wenn:
if cheapest.price >= nearest.price - 0.005:  # < 0.5 Cent billiger
    recommendation = nearest
```

**Erweiterte Empfehlung** (mit Fahrtkosten):
```python
extra_distance = cheapest.distance - nearest.distance
fuel_for_trip = (extra_distance / 100) * vehicle.consumption_l_per_100km
trip_cost = fuel_for_trip * nearest.price

price_diff_per_liter = nearest.price - cheapest.price
max_savings = price_diff_per_liter * vehicle.tank_capacity

net_savings = max_savings - trip_cost

# Empfehlung nur wenn >= 0.50 EUR Nettoersparnis
if net_savings >= STATION_RECOMMENDATION_MIN_SAVINGS:
    recommendation = cheapest
else:
    recommendation = nearest
```

**Konstante**: `STATION_RECOMMENDATION_MIN_SAVINGS = 0.50` EUR

#### Wochentag-Statistiken

**Weekday Price Statistics** (`sensor.{name}_weekday_price_statistics`)
```yaml
state: "Montag"  # Bester Wochentag zum Tanken
attributes:
  monday:
    avg_price: 1.589
    min_price: 1.549
    max_price: 1.629
    sample_count: 120
    top_stations:
      - name: "Shell Hauptstraße"
        avg_price: 1.559
      - name: "Aral Bahnhofstraße"
        avg_price: 1.569
      - name: "Esso Industriestraße"
        avg_price: 1.579
  tuesday:
    # ... gleiche Struktur
  # ... weitere Wochentage
  best_day: "monday"
  worst_day: "friday"
```

#### Perioden-Statistiken

**Period Price Statistics** (`sensor.{name}_period_price_statistics`)
```yaml
state: "falling"  # Preistrend
attributes:
  last_week:
    avg_price: 1.589
    min_price: 1.549
    max_price: 1.649
    trend: "rising"
    price_change: +0.030
    top_stations:
      - name: "Shell Hauptstraße"
        avg_price: 1.559
        visit_count: 5
  last_14_days:
    # ... gleiche Struktur
  last_month:
    # ... gleiche Struktur
```

### 6.4 Statistische Module

#### Verbrauchsstatistiken

**Average Consumption History** (`sensor.{name}_consumption_average`)
```yaml
state: 7.5  # L/100km (aktueller Durchschnitt)
attributes:
  today: 7.2
  week: 7.4
  14_days: 7.5
  month: 7.6
  all_time: 7.8
  sample_count: 45  # Anzahl Tankvorgänge
  data_quality: "good"  # good, medium, low
  last_update: 2024-01-15T10:30:00
```

**Datenqualität:**
- `good`: ≥ 30 Tankvorgänge, letzte <7 Tage
- `medium`: 10-29 Tankvorgänge, letzte <30 Tage
- `low`: <10 Tankvorgänge oder >30 Tage alt

**Consumption Forecast** (`sensor.{name}_consumption_forecast`)
```yaml
state: 7.3  # L/100km (Vorhersage für morgen)
attributes:
  tomorrow: 7.3
  next_week: 7.5
  next_14_days: 7.6
  next_month: 7.7
  confidence: 0.85  # 0.0-1.0
  prediction_method: "machine_learning"  # ml, historical_average, fallback
  factors:
    - "weekday_pattern"
    - "seasonal_trend"
    - "recent_driving_behavior"
```

**Vorhersage-Methoden:**

1. **Machine Learning** (Best, Confidence: 0.85-0.95)
   - Wochentagsmuster
   - Saisonale Trends
   - Letzte Fahrten gewichtet

2. **Historical Average** (Good, Confidence: 0.70-0.85)
   - Durchschnitt der letzten N Tankvorgänge
   - Wochentagsgewichtung

3. **Fallback** (Confidence: 0.50)
   - Konfigurierter Default-Wert
   - Wenn <5 historische Tankvorgänge

#### Tankempfehlungen

**Refueling Recommendation** (`sensor.{name}_refueling_recommendation`)
```yaml
state: "medium"  # Dringlichkeit: low, medium, high, critical
attributes:
  urgency_level: "medium"
  estimated_range_km: 280
  estimated_days_until_empty: 4.2
  recommended_action: "Tank in den nächsten 2 Tagen"
  current_price_status: "favorable"  # favorable, neutral, high
  price_trend: "rising"
  best_time_to_refuel: "today_evening"
  reasoning:
    - "Preis steigt voraussichtlich morgen"
    - "Tank bei ~30%, noch 280km Reichweite"
    - "Durchschnittlich 67km pro Tag"
```

**Dringlichkeitsstufen:**
```python
if estimated_range_km < 50 or tank_percent < 10:
    urgency = "critical"  # Sofort tanken!
elif estimated_days_until_empty < 2 or tank_percent < 20:
    urgency = "high"  # Heute tanken
elif estimated_days_until_empty < 4 or tank_percent < 35:
    urgency = "medium"  # In 1-2 Tagen tanken
else:
    urgency = "low"  # Kein Handlungsbedarf
```

**Preisbewertung:**
```python
current_price = fuel_price_sensor.state
avg_price_7_days = statistics.last_week.avg_price

if current_price < avg_price_7_days - 0.020:
    price_status = "favorable"  # Guter Preis, jetzt tanken
elif current_price > avg_price_7_days + 0.020:
    price_status = "high"  # Hoher Preis, wenn möglich warten
else:
    price_status = "neutral"
```

#### Fahrmuster-Analyse

**Weekday Driving Pattern** (`sensor.{name}_weekday_driving_pattern`)
```yaml
state: "67.4 km"  # Durchschnitt pro Tag
attributes:
  monday: "85.2 km"
  tuesday: "82.1 km"
  wednesday: "78.5 km"
  thursday: "81.3 km"
  friday: "87.6 km"
  saturday: "42.3 km"
  sunday: "15.2 km"
  weekday_avg: "82.9 km"
  weekend_avg: "28.8 km"
  most_active_day: "friday"
  least_active_day: "sunday"
```

**Verwendung:**
- Vorhersage täglicher Kilometer
- Tankempfehlungen personalisieren
- Muster für Trip Tracking

---

## 7. Erweiterte Funktionen

### 7.1 Geolocation-basierte Näherungserkennung

**Status**: Konzept erstellt, Implementierung ausstehend

📖 **Konzept-Dokumente**:
- [docs/GEOLOCATION_CONCEPT.md](../dev_docs/GEOLOCATION_CONCEPT.md) (Deutsch)
- [docs/GEOLOCATION_CONCEPT_EN.md](../dev_docs/GEOLOCATION_CONCEPT_EN.md) (English)

**Geplante Features:**
- Sensor für N günstigste Stationen im Radius
- Binary Sensor für Näherungsalarme
- Anti-Spam mit Cooldown
- Automations-Beispiele

### 7.2 Predictive Maintenance (Geplant)

Basierend auf Verbrauchsanomalien:
- Warnung bei plötzlich erhöhtem Verbrauch
- Motorcheck-Empfehlungen
- Wartungsintervall-Tracking

### 7.3 Multi-Fahrzeug-Unterstützung (In Planung)

Aktuell: Ein Fahrzeug pro Integration-Instanz
Zukünftig: Mehrere Fahrzeuge in einer Instanz

### 7.4 Historische Daten-Import

Die Integration kann vorhandene Historiendaten importieren:

**Via Debug Button** (Temporär verfügbar):
```yaml
# Exportiert Fahrzeugdaten für Test-Datasets
button.{name}_export_vehicle_data
```

Erstellt CSV-Dateien in `/config/www/export/`:
- `{entity}_history_{timestamp}.csv`
- `{entity}_statistics_{timestamp}.csv`

---

## 8. Blueprints und Automationen

### 8.1 Blueprint-Struktur

Alle Blueprints sind direkt aus GitHub importierbar:

```
blueprints/
├── automation/
│   ├── low_fuel_alert.yaml
│   ├── price_drop_notification.yaml
│   ├── refueling_reminder.yaml
│   ├── trip_logging.yaml
│   └── geolocation_proximity.yaml
└── script/
    ├── manual_refuel_entry.yaml
    ├── trip_completion.yaml
    └── fuel_price_query.yaml
```

### 8.2 Verfügbare Automation-Blueprints

📖 **Alle Blueprints**: Siehe [BLUEPRINTS_DE.md](BLUEPRINTS_DE.md)

#### Low Fuel Alert
**Import-Link:**
```
https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/blueprints/automation/low_fuel_alert.yaml
```

**Funktion**: Warnung bei niedrigem Tankstand

#### Price Drop Notification
**Import-Link:**
```
https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/blueprints/automation/price_drop_notification.yaml
```

**Funktion**: Benachrichtigung bei Preisrückgang

### 8.3 Verfügbare Script-Blueprints

#### Manual Refuel Entry
**Import-Link:**
```
https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/blueprints/script/manual_refuel_entry.yaml
```

**Funktion**: Manueller Tankvorgang-Eintrag

📖 **Komplette Blueprint-Dokumentation**: [BLUEPRINTS_DE.md](BLUEPRINTS_DE.md)

---

## 9. Fehlerbehebung

### 9.1 Häufige Probleme

#### "API connection failed"
**Ursachen:**
- Ungültiger API-Key
- Rate Limit erreicht
- Netzwerkprobleme

**Lösungen:**
1. API-Key prüfen
2. Warten (Rate Limit: 1 Minute)
3. Netzwerk prüfen
4. API-Test-Button verwenden

#### "No refueling detected"
**Ursachen:**
- Tank-Sensor nicht konfiguriert
- Tankanstieg < 5 Liter
- Kilometerzähler nicht gestiegen

**Lösungen:**
1. Tank-Entity prüfen
2. Manuell Tankvorgang hinzufügen
3. Schwellwert in Code anpassen (für Entwickler)

#### Telegram funktioniert nicht
📖 **Siehe**: 
- [docs/TELEGRAM_TROUBLESHOOTING_DE.md](TELEGRAM_TROUBLESHOOTING_DE.md)
- [TELEGRAM_ISSUE_RESOLUTION.md](TELEGRAM_ISSUE_RESOLUTION.md)

### 9.2 Debug-Logs aktivieren

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.hafwcma: debug
```

### 9.3 Debug-Sensoren verwenden

haFWCMA bietet zwei spezielle Debug-Sensoren zur Diagnose von Problemen:

#### sensor.{name}_fuel_price_api_debug

Dieser Sensor zeigt Informationen über die Tankstellen-API-Anfragen:

**Attribute:**
- `api_response_status` - Status der letzten API-Anfrage (success/error)
- `timestamp` - Zeitstempel der letzten Anfrage
- `location_source` - Quelle der verwendeten Position (vehicle/fallback)
- `stations_found` - Anzahl gefundener Tankstellen
- `stations_with_price_and_open` - Anzahl geöffneter Tankstellen mit Preis
- `stations_closed` - Anzahl geschlossener Tankstellen
- `stations_no_price` - Anzahl Tankstellen ohne Preis
- `api_request_summary` - Zusammenfassung der API-Anfrage
- `api_response_summary` - Zusammenfassung der API-Antwort
- `error` - Fehlermeldung (falls vorhanden)

**Verwendung:**
- Prüfen, ob die API korrekt antwortet
- Diagnose von "keine Tankstelle gefunden" Problemen
- Überprüfung der verwendeten Position (Fahrzeug vs. konfiguriert)

#### sensor.{name}_car_data_debug

Dieser Sensor zeigt den Status der Fahrzeugdaten-Erfassung:

**Attribute:**
- `odometer_last_value` / `odometer_last_timestamp` - Letzter Kilometerstand
- `tank_level_last_value` / `tank_level_last_timestamp` - Letzter Tankfüllstand
- `range_last_value` / `range_last_timestamp` - Letzte Reichweite
- `position_last_value` / `position_last_timestamp` - Letzte GPS-Position
- `odometer_good_count` / `odometer_error_count` - Anzahl gültige/fehlerhafte Daten
- `tank_good_count` / `tank_error_count` - Anzahl gültige/fehlerhafte Daten
- `range_good_count` / `range_error_count` - Anzahl gültige/fehlerhafte Daten
- `position_good_count` / `position_error_count` - Anzahl gültige/fehlerhafte Daten
- `trip_log_data_count` / `trip_log_sufficient` - Daten für Fahrtenbuch vorhanden?
- `refueling_log_data_count` / `refueling_log_sufficient` - Daten für Tankbuch vorhanden?
- `average_consumption_history_data_count` / `average_consumption_history_sufficient` - Daten für Verbrauchshistorie vorhanden?
- `days_until_refuel_data_count` / `days_until_refuel_sufficient` - Daten für Reichweitenvorhersage vorhanden?
- `tank_level_data_count` / `tank_level_sufficient` - Tankfüllstand-Sensor vorhanden?
- `consumption_data_source` - Quelle der Verbrauchsberechnung (historical_data/ml_enhanced/fallback_values/no_vehicle_data)
- `recommendations` - Empfehlungen zur Behebung fehlender Daten

**Verwendung:**
- Diagnose von "unknown" oder "unavailable" Sensor-Werten
- Prüfen, ob Fahrzeugdaten korrekt empfangen werden
- Identifizieren fehlender Konfigurationen (z.B. nicht konfigurierte Entities)
- Verstehen, warum Berechnungen nicht funktionieren (z.B. "Days Until Refuel" = unknown)

**Beispiel-Szenario:**
Wenn `sensor.{name}_days_until_refuel` den Wert "unknown" zeigt:
1. Öffnen Sie `sensor.{name}_car_data_debug`
2. Prüfen Sie `consumption_data_source`:
   - `no_vehicle_data` → Tank-Level oder Range-Sensor fehlt
   - `fallback_values` → Zu wenig Tankdaten (< 5 Tankvorgänge)
3. Prüfen Sie `days_until_refuel_sufficient`:
   - `false` → Schauen Sie `days_until_refuel_data_count` für benötigte Anzahl
4. Lesen Sie `recommendations` für konkrete Lösungsvorschläge

### 9.4 Diagnose-Export (Geplant)

**Zukünftig**: One-Click Diagnose-Daten Export
Siehe TODO.md → "Diagnostic Data Export Feature"

---

## 📚 Weitere Dokumentation

### Englische Dokumentation
- [README.md](../../README.md) - English overview
- [docs/TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)
- [docs/GEOLOCATION_CONCEPT_EN.md](../dev_docs/GEOLOCATION_CONCEPT_EN.md)

### Deutsche Dokumentation
- [HACS_INSTALLATION_DE.md](HACS_INSTALLATION_DE.md)
- [docs/TELEGRAM_SETUP_DE.md](TELEGRAM_SETUP_DE.md)
- [docs/REFUELING_LOG_GUIDE_DE.md](REFUELING_LOG_GUIDE_DE.md)

### Technische Dokumentation
- [DEVELOPER_NOTES.md](DEVELOPER_NOTES.md)
- [docs/API.md](../dev_docs/API.md)
- [docs/DATA_STORAGE.md](DATA_STORAGE.md)

---

**Version**: 1.0.0  
**Stand**: 2024-02-17  
**Lizenz**: MIT
