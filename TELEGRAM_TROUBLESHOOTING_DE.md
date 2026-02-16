# Telegram Benachrichtigungen - Fehlerbehebung

## Problem: Keine Telegram-Benachrichtigungen nach Tankvorgang

Wenn nach dem Erstellen eines Tankvorgangs keine Telegram-Benachrichtigung versendet wird, gibt es mehrere mögliche Ursachen.

## Diagnose-Schritte

### 1. Prüfen der Home Assistant Logs

Die Integration erzeugt jetzt detaillierte Log-Einträge, um Probleme zu diagnostizieren:

```
Logger: custom_components.hafwcma.telegram_refueling_handler
```

**Wichtige Log-Nachrichten:**

#### Bei erfolgreicher Initialisierung:
```
INFO: Setting up Telegram refueling handler. Checking for telegram_bot integration...
INFO: telegram_bot integration found - proceeding with event listener setup
INFO: Telegram refueling handler successfully initialized with 5 event listeners
INFO: ✅ Telegram refueling handler successfully initialized and ready for notifications
```

#### Bei Telegram-Integration nicht gefunden:
```
WARNING: telegram_bot integration NOT FOUND!
ERROR: ❌ Telegram refueling handler setup FAILED. Refueling notifications will NOT be sent.
```

#### Bei Event-Empfang:
```
INFO: Received refueling_added event
INFO: Processing new refueling event: ID=123, liters=45.50, fuel_type=e10
INFO: Creating task to send Telegram notification for refuel ID 123
```

#### Bei Benachrichtigungs-Versand:
```
INFO: Preparing Telegram notification for refuel ID 123 (chat_id: 12345678)
INFO: Sending notification via telegram_bot service (target: 12345678, parse_mode: HTML)
INFO: Notification sent successfully with message_id: 456
INFO: Refueling notification sent for ID 123
```

### 2. Häufigste Fehlerursachen

#### ❌ Telegram Bot Integration nicht konfiguriert

**Symptom:** Log zeigt `telegram_bot integration NOT FOUND`

**Lösung:**
1. Die `telegram_bot` Integration muss in Home Assistant konfiguriert sein
2. Gehen Sie zu: Einstellungen → Geräte & Dienste → Integration hinzufügen
3. Suchen Sie nach "Telegram Bot" und fügen Sie sie hinzu
4. Dokumentation: https://www.home-assistant.io/integrations/telegram_bot/

**Erforderliche Konfiguration in configuration.yaml:**
```yaml
telegram_bot:
  - platform: polling
    api_key: "IHR_BOT_API_KEY"
    allowed_chat_ids:
      - 12345678  # Ihre Chat ID
```

#### ❌ Telegram Chat ID fehlt oder ist falsch

**Symptom:** Log zeigt `Telegram not configured (chat_id: missing, token: present)`

**Lösung:**
1. Überprüfen Sie die haFWCMA-Konfiguration
2. Stellen Sie sicher, dass die Telegram Chat ID korrekt eingetragen ist
3. Chat ID ermitteln: Senden Sie `/start` an @userinfobot auf Telegram

#### ❌ Config Entry ID stimmt nicht überein

**Symptom:** Log zeigt `Ignoring event from different config entry`

**Lösung:**
1. Dies tritt auf, wenn mehrere haFWCMA-Instanzen konfiguriert sind
2. Überprüfen Sie, ob der Tankvorgang für die richtige Fahrzeug-Instanz erstellt wurde

#### ❌ Service Call Fehler

**Symptom:** Log zeigt `Failed to send refueling notification`

**Lösung:**
1. Überprüfen Sie die telegram_bot Service-Logs
2. Stellen Sie sicher, dass der Bot läuft und erreichbar ist
3. Testen Sie den Bot mit dem Service-Aufruf in Home Assistant Developer Tools:
```yaml
service: telegram_bot.send_message
data:
  target: 12345678
  message: "Test"
  parse_mode: "HTML"
```

### 3. Parse Mode Einstellungen

Die Integration verwendet **HTML** als Parse Mode für alle Telegram-Nachrichten.

#### Parse Mode Kompatibilität

| Parse Mode | In haFWCMA verwendet | Kompatibel |
|------------|---------------------|------------|
| **HTML** | ✅ Ja (Standard) | ✅ Vollständig |
| MarkdownV2 | ❌ Nein | ⚠️ Nicht getestet |
| Markdown (veraltet) | ❌ Nein | ⚠️ Nicht empfohlen |
| Nur-Text | ❌ Nein | ❌ Keine Formatierung |

**Wichtig:** Die Einstellung "Parse Mode" in der Home Assistant telegram_bot Integration beeinflusst **nicht** die haFWCMA-Benachrichtigungen. haFWCMA sendet den Parse Mode explizit mit jedem Service Call:

```python
{
    "target": chat_id,
    "message": message,
    "parse_mode": "HTML",  # <-- Explizit gesetzt
    "inline_keyboard": inline_keyboard,
}
```

#### HTML Formatierung in Benachrichtigungen

Die Integration nutzt folgende HTML-Tags:
- `<b>...</b>` für fette Schrift
- Keine weiteren Tags oder Sonderzeichen

Dies ist mit allen telegram_bot Konfigurationen kompatibel.

### 4. Test-Flow durchführen

1. Drücken Sie die "Telegram API Test" Schaltfläche in Home Assistant
2. Beobachten Sie die Logs (siehe oben)
3. Prüfen Sie, ob eine Telegram-Nachricht empfangen wird

**Erwartetes Verhalten:**
- Ein Test-Tankvorgang wird erstellt
- Eine Telegram-Benachrichtigung wird versendet
- Die Nachricht enthält interaktive Schaltflächen (✅ Bestätigen, ✏️ Bearbeiten, 🗑️ Löschen)

### 5. Debug-Modus aktivieren

Um noch detailliertere Logs zu erhalten, fügen Sie dies zu Ihrer `configuration.yaml` hinzu:

```yaml
logger:
  default: info
  logs:
    custom_components.hafwcma: debug
    custom_components.hafwcma.telegram_refueling_handler: debug
    custom_components.hafwcma.button: debug
```

Danach Home Assistant neu starten.

## Zusammenfassung der Logging-Verbesserungen

Die folgenden Logging-Verbesserungen wurden implementiert:

### Setup-Phase
- ✅ Prüfung der telegram_bot Integration mit Liste aller verfügbaren Integrationen
- ✅ Detaillierte Warnung wenn telegram_bot fehlt
- ✅ Bestätigung bei erfolgreicher Registrierung aller Event Listener
- ✅ Zählung der registrierten Listener

### Event-Verarbeitung
- ✅ Empfang des refueling_added Events
- ✅ Config Entry ID Abgleich mit Details
- ✅ Refueling-Daten (ID, Liter, Kraftstoffart)
- ✅ Task-Erstellung für Benachrichtigung

### Benachrichtigungs-Versand
- ✅ Chat ID und Parse Mode
- ✅ Vorschau der Nachricht (erste 200 Zeichen)
- ✅ Service Call Rückgabewert
- ✅ Message ID bei Erfolg
- ✅ Warnung wenn Message ID fehlt
- ✅ Detaillierte Fehlerinformationen mit Exception-Typ und Stack Trace

### Button Test
- ✅ Event-Details beim Feuern (Config Entry ID, Refuel ID)
- ✅ Bestätigung nach erfolgreichem Feuern

## Support

Wenn das Problem weiterhin besteht:
1. Sammeln Sie alle relevanten Log-Einträge
2. Überprüfen Sie die telegram_bot Konfiguration
3. Testen Sie den telegram_bot Service manuell
4. Erstellen Sie ein Issue mit den Log-Einträgen

---

**Letzte Aktualisierung:** 2024
**Version:** 1.0
