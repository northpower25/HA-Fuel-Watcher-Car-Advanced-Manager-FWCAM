# haFWCMA Blueprints - Dokumentation

Diese Blueprints ermöglichen die einfache Integration von haFWCMA-Funktionen in Ihre Home Assistant Automationen und Skripte.

---

## 📦 Installation

### Methode 1: Direkter Import (Empfohlen)

Klicken Sie auf die Import-Links unten oder fügen Sie die Blueprint-URL manuell in Home Assistant hinzu:

1. Gehen Sie zu **Einstellungen** → **Automationen & Szenen**
2. Klicken Sie auf **Blueprints**
3. Klicken Sie unten rechts auf **Blueprint importieren**
4. Fügen Sie die URL ein
5. Klicken Sie **Vorschau** und dann **Importieren**

### Methode 2: Manuelle Installation

1. Laden Sie die `.yaml` Datei herunter
2. Kopieren Sie sie nach `/config/blueprints/automation/` oder `/config/blueprints/script/`
3. Starten Sie Home Assistant neu (oder laden Sie Blueprints neu)

---

## 🤖 Automation Blueprints

### 1. Niedriger Tankstand Alarm

**Funktion**: Warnt Sie rechtzeitig vor einem leeren Tank mit konfigurierbaren Dringlichkeitsstufen.

**Import-Link**:
```
https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/blueprints/automation/low_fuel_alert.yaml
```

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fnorthpower25%2FHA-Fuel-Watcher-Car-Advanced-Manager-FWCAM%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Flow_fuel_alert.yaml)

**Konfigurierbare Parameter**:
- **Tankempfehlungs-Sensor**: Der haFWCMA Sensor mit Tankempfehlungen
- **Dringlichkeitsstufe**: Kritisch (< 10%), Hoch (< 20%), Mittel (< 35%)
- **Benachrichtigungsdienst**: Ihr Notification Service (z.B. `notify.mobile_app_iphone`)
- **Cooldown**: Wartezeit zwischen Benachrichtigungen (1-24 Stunden)

**Beispiel-Automation**:
```yaml
alias: Tankalarm bei niedrigem Stand
description: Benachrichtigt mich bei weniger als 20% Tankinhalt
use_blueprint:
  path: low_fuel_alert.yaml
  input:
    refueling_recommendation_sensor: sensor.mein_auto_refueling_recommendation
    urgency_level: high
    notify_service: notify.mobile_app_iphone
    cooldown_hours: 6
```

**Benachrichtigungsbeispiele**:
- **Kritisch**: "🚨 KRITISCH: Tank fast leer! Nur noch 5L (8%). Reichweite: ca. 40km. Bitte SOFORT tanken!"
- **Hoch**: "⚠️ Tankstand niedrig. Aktuell: 12L (20%). Reichweite: ca. 95km. Tanken Sie heute."
- **Mittel**: "💡 Tankempfehlung: Tanken empfohlen in 1-2 Tagen. Tank: 30%. Reichweite: 210km"

---

### 2. Tankpreis Preisrückgang Benachrichtigung

**Funktion**: Informiert Sie, wenn der Kraftstoffpreis unter einen definierten Schwellwert fällt.

**Import-Link**:
```
https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/blueprints/automation/price_drop_notification.yaml
```

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fnorthpower25%2FHA-Fuel-Watcher-Car-Advanced-Manager-FWCAM%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fprice_drop_notification.yaml)

**Konfigurierbare Parameter**:
- **Kraftstoffpreis-Sensor**: Der haFWCMA Preissensor
- **Preisschwelle**: Benachrichtigen wenn Preis darunter fällt (EUR/Liter)
- **Benachrichtigungsdienst**: Ihr Notification Service
- **Tankstellen-Info einbeziehen**: Zeigt günstigste Tankstelle (true/false)
- **Cooldown**: Wartezeit zwischen Benachrichtigungen (1-24 Stunden)

**Beispiel-Automation**:
```yaml
alias: Preis-Alarm bei Diesel unter 1.45€
description: Informiert mich bei günstigen Dieselpreisen
use_blueprint:
  path: price_drop_notification.yaml
  input:
    fuel_price_sensor: sensor.mein_auto_fuel_price
    price_threshold: 1.45
    notify_service: notify.mobile_app_iphone
    include_station_info: true
    cooldown_hours: 3
```

**Benachrichtigungsbeispiel**:
```
💰 Günstiger Kraftstoffpreis!
Der Preis ist unter 1.45€/L gefallen!

Aktuell: 1.43€/L
Trend: falling

🏆 Günstigste Tankstelle:
Shell Hauptstraße 123
Entfernung: 2.3km
Preis: 1.41€/L
```

---

### 3. Intelligente Tankerinnerung

**Funktion**: Tägliche Erinnerung basierend auf Tankstand, Fahrmustern und Preisentwicklung.

**Import-Link**:
```
https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/blueprints/automation/refueling_reminder.yaml
```

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fnorthpower25%2FHA-Fuel-Watcher-Car-Advanced-Manager-FWCAM%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Frefueling_reminder.yaml)

**Konfigurierbare Parameter**:
- **Tankempfehlungs-Sensor**: Der haFWCMA Tankempfehlungs-Sensor
- **Kraftstoffpreis-Sensor**: Der haFWCMA Preissensor
- **Erinnerungszeit**: Tageszeit für Erinnerung (z.B. 18:00)
- **Benachrichtigungsdienst**: Ihr Notification Service
- **Minimale Dringlichkeit**: Nur bei dieser oder höherer Dringlichkeit erinnern

**Beispiel-Automation**:
```yaml
alias: Tägliche Tankerinnerung um 18 Uhr
description: Erinnert mich abends ans Tanken wenn nötig
use_blueprint:
  path: refueling_reminder.yaml
  input:
    refueling_recommendation_sensor: sensor.mein_auto_refueling_recommendation
    fuel_price_sensor: sensor.mein_auto_fuel_price
    reminder_time: "18:00:00"
    notify_service: notify.mobile_app_iphone
    min_urgency: medium
```

**Benachrichtigungsbeispiel**:
```
⛽ Tankerinnerung
💡 Tanken in den nächsten Tagen empfohlen

📊 Status:
• Tank: 32%
• Reichweite: ca. 225km
• Tage bis leer: 3.5

💰 Preis-Info:
• Aktuell: 1.48€/L
• Trend: rising
• ⏳ Hoher Preis - wenn möglich warten

Tanken Sie in 1-2 Tagen wenn Preis fällt.
```

---

### 4. Automatische Fahrtprotokollierung

**Funktion**: Protokolliert Fahrten automatisch und benachrichtigt bei Fahrtstart/-ende.

**Import-Link**:
```
https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/blueprints/automation/trip_logging.yaml
```

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fnorthpower25%2FHA-Fuel-Watcher-Car-Advanced-Manager-FWCAM%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Ftrip_logging.yaml)

**Konfigurierbare Parameter**:
- **Auf-Fahrt Sensor**: Binary Sensor für aktive Fahrt
- **Aktuelle-Fahrt Sensor**: Sensor mit Fahrtdetails
- **Benachrichtigungsdienst**: Optional, für Benachrichtigungen
- **Automatische Kategorisierung**: Fahrtenzweck automatisch zuweisen (true/false)
- **Bei Fahrtende benachrichtigen**: Zeigt Fahrtdetails nach Ende (true/false)

**Beispiel-Automation**:
```yaml
alias: Fahrtenbuch Automatik
description: Protokolliert alle Fahrten automatisch
use_blueprint:
  path: trip_logging.yaml
  input:
    on_trip_sensor: binary_sensor.mein_auto_on_trip
    current_trip_sensor: sensor.mein_auto_current_trip
    notify_service: notify.mobile_app_iphone
    auto_categorize: true
    notify_on_trip_end: true
```

**Benachrichtigungsbeispiel (Fahrtende)**:
```
🏁 Fahrt beendet
Fahrt: 25.5km in 32min
Zweck: work
Verbrauch: 7.2L/100km
Kosten: 2.75€

📍 Muster erkannt: Zuhause → Arbeit
```

---

### 5. Geolocation Näherungsalarm (Geplant)

**Funktion**: Warnt wenn Sie sich in der Nähe einer günstigen Tankstelle befinden.

**Status**: 🚧 In Planung (siehe [docs/GEOLOCATION_CONCEPT.md](../dev_docs/GEOLOCATION_CONCEPT.md))

**Import-Link**:
```
https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/blueprints/automation/geolocation_proximity.yaml
```

**Hinweis**: Diese Funktion ist noch nicht implementiert. Der Blueprint ist als Platzhalter vorhanden.

---

## 📜 Script Blueprints

### 1. Manueller Tankvorgang-Eintrag

**Funktion**: Fügt einen Tankvorgang manuell zum Protokoll hinzu.

**Import-Link**:
```
https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/blueprints/script/manual_refuel_entry.yaml
```

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fnorthpower25%2FHA-Fuel-Watcher-Car-Advanced-Manager-FWCAM%2Fblob%2Fmain%2Fblueprints%2Fscript%2Fmanual_refuel_entry.yaml)

**Konfigurierbare Parameter**:
- **Config Entry ID**: Ihre haFWCMA Integration ID
- **Liter getankt**: Menge des Kraftstoffs (1-200L)
- **Preis pro Liter**: Kraftstoffpreis (optional)
- **Kilometerstand**: Aktueller Stand (optional)
- **Tankstellen-Name**: Name der Station (optional)
- **Kraftstofftyp**: diesel, e5, e10, super_plus

**Verwendung**:
```yaml
alias: Schneller Tankvorgang-Eintrag
description: Fügt 45L Diesel hinzu
use_blueprint:
  path: manual_refuel_entry.yaml
  input:
    config_entry_id: "abc123def456"
    liters: 45.5
    price_per_liter: 1.599
    odometer: 123456
    station_name: "Shell Hauptstraße"
    fuel_type: diesel
```

**Tipp**: Finden Sie Ihre Config Entry ID:
1. Gehen Sie zu **Entwicklerwerkzeuge** → **Zustände**
2. Suchen Sie nach einem haFWCMA Sensor
3. Die ID steht im Attribut `config_entry_id`

---

### 2. Fahrtabschluss-Handler

**Funktion**: Bearbeitet und kategorisiert eine beendete Fahrt nachträglich.

**Import-Link**:
```
https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/blueprints/script/trip_completion.yaml
```

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fnorthpower25%2FHA-Fuel-Watcher-Car-Advanced-Manager-FWCAM%2Fblob%2Fmain%2Fblueprints%2Fscript%2Ftrip_completion.yaml)

**Konfigurierbare Parameter**:
- **Config Entry ID**: Ihre haFWCMA Integration ID
- **Trip ID**: Die ID der Fahrt (siehe Trip Log)
- **Fahrtenzweck**: private, work, business, other
- **Notizen**: Freitext-Notizen (optional)
- **Zusatzkosten**: Parkgebühren, Maut, etc. (optional)

**Verwendung**:
```yaml
alias: Fahrt als Geschäftsreise markieren
description: Aktualisiert Fahrt mit Geschäftszweck
use_blueprint:
  path: trip_completion.yaml
  input:
    config_entry_id: "abc123def456"
    trip_id: "trip_20240115_080000"
    purpose: business
    notes: "Kundenbesuch in München"
    additional_costs: 5.50
```

---

### 3. Tankpreis-Abfrage

**Funktion**: Ruft aktuelle Tankstellenpreise ab und sendet eine formatierte Übersicht.

**Import-Link**:
```
https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/blueprints/script/fuel_price_query.yaml
```

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fnorthpower25%2FHA-Fuel-Watcher-Car-Advanced-Manager-FWCAM%2Fblob%2Fmain%2Fblueprints%2Fscript%2Ffuel_price_query.yaml)

**Konfigurierbare Parameter**:
- **Kraftstoffpreis-Sensor**: Der haFWCMA Preissensor
- **Nächste-Tankstelle Sensor**: Sensor für nächste Station
- **Günstigste-Tankstelle Sensor**: Sensor für günstigste Station
- **Benachrichtigungsdienst**: Optional, sonst Persistent Notification
- **Navigation-Links einbeziehen**: Google Maps Links (true/false)

**Verwendung**:
```yaml
alias: Tankpreise abfragen
description: Zeigt aktuelle Preise und Tankstellen
use_blueprint:
  path: fuel_price_query.yaml
  input:
    fuel_price_sensor: sensor.mein_auto_fuel_price
    nearest_station_sensor: sensor.mein_auto_nearest_station
    cheapest_station_sensor: sensor.mein_auto_cheapest_station
    notify_service: notify.mobile_app_iphone
    include_navigation: true
```

**Ergebnis-Beispiel**:
```
⛽ Aktuelle Tankstellenpreise
💰 Aktueller Preis: 1.48€/L (diesel)
📈 Trend: rising

📍 Nächste Tankstelle:
Shell Hauptstraße 123
Entfernung: 1.2km
Preis: 1.48€/L
🗺️ https://www.google.com/maps/dir/?api=1&destination=51.5074,9.9347

💎 Günstigste Tankstelle:
Aral Bahnhofstraße 45
Entfernung: 3.5km
Preis: 1.43€/L
💰 Ersparnis: 0.05€/L (2.3km Mehrweg)
🗺️ https://www.google.com/maps/dir/?api=1&destination=51.5123,9.9456
```

---

## 🔧 Erweiterte Nutzung

### Dashboard-Button erstellen

Fügen Sie einen Button zu Ihrem Dashboard hinzu, der ein Script ausführt:

```yaml
type: button
name: Tankpreis abrufen
icon: mdi:gas-station
tap_action:
  action: call-service
  service: script.tankpreis_abfrage
```

### Automation mit mehreren Bedingungen

Kombinieren Sie mehrere haFWCMA Features:

```yaml
alias: Smart Tankerinnerung
trigger:
  - platform: time
    at: "18:00:00"
condition:
  - condition: numeric_state
    entity_id: sensor.mein_auto_refueling_recommendation
    attribute: tank_level_percent
    below: 30
  - condition: state
    entity_id: sensor.mein_auto_fuel_price
    attribute: price_status
    state: favorable
action:
  - service: notify.mobile_app_iphone
    data:
      title: "⛽ Perfekte Zeit zum Tanken!"
      message: "Tank bei {{ states.sensor.mein_auto_refueling_recommendation.attributes.tank_level_percent }}% UND günstiger Preis!"
```

### Voice Assistant Integration

Erstellen Sie einen Intent für Alexa/Google Assistant:

```yaml
# configuration.yaml
intent_script:
  TankpreisAbfragen:
    speech:
      text: >
        Der aktuelle Dieselpreis beträgt {{ states('sensor.mein_auto_fuel_price') }} Euro pro Liter.
        Die nächste Tankstelle ist {{ states('sensor.mein_auto_nearest_station') }}.
    action:
      service: script.tankpreis_abfrage
```

---

## 🐛 Troubleshooting

### "Blueprint konnte nicht importiert werden"
- Prüfen Sie die URL auf Tippfehler
- Stellen Sie sicher, dass Sie mit dem Internet verbunden sind
- Versuchen Sie, die Datei manuell herunterzuladen

### "Entity nicht gefunden"
- Prüfen Sie, dass die haFWCMA Integration installiert und konfiguriert ist
- Überprüfen Sie die Entity-IDs in **Entwicklerwerkzeuge** → **Zustände**
- Passen Sie die Entity-IDs im Blueprint an Ihre Installation an

### "Service nicht verfügbar"
- Stellen Sie sicher, dass die entsprechenden Services existieren
- Für Telegram: `notify.` Dienst muss konfiguriert sein
- Für Trip/Refuel Services: haFWCMA muss korrekt installiert sein

### "Config Entry ID nicht gefunden"
1. Gehen Sie zu **Entwicklerwerkzeuge** → **Zustände**
2. Klicken Sie auf einen haFWCMA Sensor
3. Suchen Sie nach `config_entry_id` in den Attributen
4. Kopieren Sie den Wert (z.B. `abc123def456`)

---

## 📚 Weitere Ressourcen

- **Haupt-Dokumentation**: [DOKUMENTATION_DE.md](DOKUMENTATION_DE.md)
- **README**: [README.md](../../README.md)
- **TODO & Roadmap**: [TODO.md](../../TODO.md)
- **Telegram Setup**: [docs/TELEGRAM_SETUP_DE.md](TELEGRAM_SETUP_DE.md)
- **Trip Tracking**: [docs/TRIP_TRACKING_README.md](TRIP_TRACKING_README.md)

---

## 🤝 Beitragen

Haben Sie einen nützlichen Blueprint erstellt? Teilen Sie ihn mit der Community!

1. Forken Sie das Repository
2. Fügen Sie Ihren Blueprint zu `blueprints/automation/` oder `blueprints/script/` hinzu
3. Erstellen Sie einen Pull Request
4. Dokumentieren Sie den Blueprint in dieser Datei

---

**Version**: 1.0.0  
**Stand**: 2024-02-17  
**Lizenz**: MIT
