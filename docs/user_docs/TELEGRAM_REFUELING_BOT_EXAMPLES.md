# Example Automations for Telegram Refueling Bot

## Automatische Benachrichtigung bei manuellem Tankvorgang

Diese Automation sendet automatisch eine Telegram-Benachrichtigung, wenn Sie einen Tankvorgang über die UI hinzufügen:

```yaml
automation:
  - alias: "Tankvorgang Telegram Benachrichtigung"
    description: "Sendet Telegram-Nachricht bei neuem Tankvorgang"
    trigger:
      - platform: event
        event_type: hafwcma_refueling_added
    condition:
      # Optional: Nur für bestimmte config_entry_id
      - condition: template
        value_template: "{{ trigger.event.data.config_entry_id == 'IHRE_CONFIG_ENTRY_ID' }}"
    action:
      - service: notify.persistent_notification
        data:
          title: "Tankvorgang hinzugefügt"
          message: >
            Tankvorgang #{{ trigger.event.data.refuel_id }} wurde hinzugefügt.
            Telegram-Benachrichtigung wurde gesendet.
```

## Test-Automation für tägliche Simulation

Nützlich zum Testen der Telegram-Integration:

```yaml
automation:
  - alias: "Täglicher Tankvorgang-Test"
    description: "Simuliert täglich um 10:00 Uhr einen Tankvorgang"
    trigger:
      - platform: time
        at: "10:00:00"
    action:
      - service: hafwcma.simulate_refueling_event
        data:
          config_entry_id: "IHRE_CONFIG_ENTRY_ID"
          include_missing_data: true
```

## Erinnerung bei fehlender Antwort

Sendet eine Erinnerung, wenn nach 30 Minuten noch keine Antwort auf eine Tankvorgang-Benachrichtigung erfolgt ist:

```yaml
automation:
  - alias: "Tankvorgang Antwort-Erinnerung"
    description: "Erinnert nach 30 Minuten an fehlende Tankvorgang-Daten"
    trigger:
      - platform: event
        event_type: hafwcma_refueling_added
    action:
      - delay:
          minutes: 30
      - choose:
          - conditions:
              # Prüfen ob noch keine Antwort vorhanden
              - condition: template
                value_template: >
                  {% set refuel_id = trigger.event.data.refuel_id %}
                  {% set refuelings = state_attr('sensor.VEHICLE_NAME_refueling_log', 'recent_refuelings') %}
                  {% set refuel = refuelings | selectattr('id', 'eq', refuel_id) | first %}
                  {{ not refuel.get('telegram_response_received', False) }}
            sequence:
              - service: telegram_bot.send_message
                data:
                  target: IHRE_CHAT_ID
                  message: >
                    🔔 Erinnerung: Sie haben noch nicht auf die Tankvorgang-Nachricht geantwortet.
                    
                    Bitte ergänzen Sie die fehlenden Informationen für Tankvorgang #{{ trigger.event.data.refuel_id }}.
```

## Statistik-Benachrichtigung bei vollständiger Antwort

Sendet eine Zusammenfassung, wenn ein Tankvorgang vollständig erfasst wurde:

```yaml
automation:
  - alias: "Tankvorgang vollständig erfasst"
    description: "Bestätigung bei vollständigem Tankvorgang"
    trigger:
      - platform: event
        event_type: hafwcma_refueling_added
    action:
      - wait_for_trigger:
          - platform: template
            value_template: >
              {% set refuel_id = trigger.event.data.refuel_id %}
              {% set refuelings = state_attr('sensor.VEHICLE_NAME_refueling_log', 'recent_refuelings') %}
              {% set refuel = refuelings | selectattr('id', 'eq', refuel_id) | first %}
              {{ refuel.get('telegram_response_received', False) }}
        timeout:
          hours: 24
        continue_on_timeout: false
      - service: telegram_bot.send_message
        data:
          target: IHRE_CHAT_ID
          message: >
            ✅ Tankvorgang erfolgreich erfasst!
            
            📊 Ihre Statistiken:
            • Durchschnittsverbrauch: {{ state_attr('sensor.VEHICLE_NAME_consumption', 'average_consumption_l_100km') }} L/100km
            • Durchschnittspreis: {{ state_attr('sensor.VEHICLE_NAME_fuel_price_average', 'state') }} €/L
            • Letzte Tankstelle: {{ state_attr('sensor.VEHICLE_NAME_last_refueling', 'station_name') }}
```

## Button-Panel für schnelle Test-Befehle

Fügen Sie diese Buttons zu Ihrem Dashboard hinzu:

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Telegram Refueling Bot
    entities:
      - entity: binary_sensor.VEHICLE_NAME_telegram_bot
        name: Bot Status
      - type: button
        name: Test Tankvorgang (fehlende Daten)
        tap_action:
          action: call-service
          service: hafwcma.simulate_refueling_event
          service_data:
            config_entry_id: "IHRE_CONFIG_ENTRY_ID"
            include_missing_data: true
      - type: button
        name: Test Tankvorgang (vollständig)
        tap_action:
          action: call-service
          service: hafwcma.simulate_refueling_event
          service_data:
            config_entry_id: "IHRE_CONFIG_ENTRY_ID"
            include_missing_data: false
      - type: button
        name: Telegram Test-Nachricht
        tap_action:
          action: call-service
          service: telegram_bot.send_message
          service_data:
            target: IHRE_CHAT_ID
            message: "🧪 Test-Nachricht von Home Assistant"
```

## Script für manuellen Tankvorgang mit Telegram

Erstellen Sie ein Script, um Tankvorgänge manuell mit direkter Telegram-Benachrichtigung hinzuzufügen:

```yaml
script:
  add_refueling_with_telegram:
    alias: "Tankvorgang hinzufügen (mit Telegram)"
    icon: mdi:gas-station
    fields:
      liters:
        description: "Getankte Liter"
        example: "45.5"
      station:
        description: "Tankstellenname (optional)"
        example: "Shell"
        required: false
    sequence:
      - service: hafwcma.add_refuel_event
        data:
          config_entry_id: "IHRE_CONFIG_ENTRY_ID"
          timestamp: "{{ now().isoformat() }}"
          liters_refueled: "{{ liters }}"
          station_name: "{{ station | default('') }}"
      - service: notify.persistent_notification
        data:
          title: "Tankvorgang hinzugefügt"
          message: "Tankvorgang mit {{ liters }}L wurde hinzugefügt. Telegram-Benachrichtigung gesendet."
```

## Verwendung in Node-RED

Falls Sie Node-RED verwenden, hier ist ein Beispiel-Flow:

```json
[
  {
    "id": "refuel_telegram_node",
    "type": "api-call-service",
    "name": "Simulate Refueling",
    "server": "home_assistant",
    "version": 5,
    "service_domain": "hafwcma",
    "service": "simulate_refueling_event",
    "data": "{\"config_entry_id\":\"IHRE_CONFIG_ENTRY_ID\",\"include_missing_data\":true}"
  }
]
```

## Hinweise

1. **CONFIG_ENTRY_ID finden:**
   ```yaml
   service: hafwcma.get_all_refuelings
   # Die Response enthält die config_entry_id
   ```
   
   Oder über Developer Tools -> States -> Suchen Sie nach `sensor.VEHICLE_NAME_*` und schauen Sie in die Attribute.

2. **CHAT_ID finden:**
   - Bereits während der Telegram-Setup konfiguriert
   - Steht in der haFWCMA-Konfiguration
   - Oder via [@userinfobot](https://t.me/userinfobot)

3. **VEHICLE_NAME:**
   - Der Name, den Sie während der haFWCMA-Einrichtung angegeben haben
   - Wird in Entity-IDs verwendet (z.B. `sensor.my_car_refueling_log`)
   - Leerzeichen werden durch Unterstriche ersetzt

## Troubleshooting

### Benachrichtigung wird nicht gesendet

1. Überprüfen Sie `binary_sensor.VEHICLE_NAME_telegram_bot` - sollte `on` sein
2. Prüfen Sie die Logs auf Fehler:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.hafwcma.telegram_refueling_handler: debug
   ```
3. Testen Sie die Telegram-Verbindung mit dem Test-Button in der UI

### Antwort wird nicht erkannt

1. Stellen Sie sicher, dass Sie auf die Benachrichtigungs-Nachricht antworten (Reply)
2. Überprüfen Sie die Logs für Parsing-Fehler
3. Verwenden Sie strukturierte Eingaben (z.B. "45.5 L, 1.599 €/L, Shell")

### Bot reagiert nicht

1. Prüfen Sie, ob die `telegram_bot` Integration läuft:
   ```
   Einstellungen -> Geräte & Dienste -> Integrationen -> Telegram Bot
   ```
2. Starten Sie Home Assistant neu
3. Überprüfen Sie, ob die Chat-ID korrekt ist
