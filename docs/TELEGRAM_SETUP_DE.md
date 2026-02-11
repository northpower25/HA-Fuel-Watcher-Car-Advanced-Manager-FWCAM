# Telegram Integration Einrichtungsanleitung

## Übersicht

haFWCMA unterstützt Telegram-Benachrichtigungen für Kraftstoffpreise, Tankempfehlungen und Tankwarnungen. Um **bidirektionale** Kommunikation (Empfang von Befehlen) zu ermöglichen, müssen Sie beide konfigurieren:

1. **haFWCMA Telegram-Einstellungen** - Zum Senden von Benachrichtigungen
2. **Home Assistant's `telegram_bot` Integration** - Zum Empfangen von Befehlen (optional, aber empfohlen)

## Schnelleinrichtung (Nur Benachrichtigungen Empfangen)

Wenn Sie nur Benachrichtigungen von haFWCMA **empfangen** möchten (keine bidirektionalen Funktionen), müssen Sie nur Telegram in haFWCMA konfigurieren:

1. Erstellen Sie einen Telegram-Bot über [@BotFather](https://t.me/botfather)
2. Holen Sie sich Ihre Chat-ID (siehe unten)
3. Geben Sie Bot-Token und Chat-ID in der haFWCMA-Konfiguration ein
4. Testen Sie die Verbindung während der Einrichtung

**Das war's!** haFWCMA kann Ihnen jetzt Benachrichtigungen senden.

## Vollständige Einrichtung (Bidirektionale Kommunikation)

Für erweiterte Funktionen wie das Protokollieren von Tankvorgängen über Telegram-Befehle oder das Abfragen des Tankstatus, folgen Sie diesen Schritten:

### Schritt 1: Telegram Bot Erstellen

1. Öffnen Sie Telegram und suchen Sie nach [@BotFather](https://t.me/botfather)
2. Senden Sie `/newbot` und folgen Sie den Anweisungen
3. Wählen Sie einen Namen und Benutzernamen für Ihren Bot
4. **Speichern Sie das API-Token** (sieht aus wie `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Schritt 2: Chat-ID Ermitteln

Sie benötigen Ihre Chat-ID zur Autorisierung der Kommunikation:

**Methode 1: Bot Verwenden**
1. Suchen Sie in Telegram nach [@userinfobot](https://t.me/userinfobot)
2. Starten Sie ein Gespräch damit
3. Er sendet Ihnen Ihre Chat-ID (eine Nummer wie `123456789`)

**Methode 2: Telegram API Verwenden**
1. Senden Sie eine Nachricht an Ihren neu erstellten Bot
2. Besuchen Sie: `https://api.telegram.org/bot<IHR_BOT_TOKEN>/getUpdates`
3. Suchen Sie nach `"chat":{"id":123456789}` in der Antwort

### Schritt 3: haFWCMA Konfigurieren

Während der haFWCMA-Einrichtung oder im Optionen-Flow:

1. **Telegram Bot Token**: Geben Sie Ihr Bot-Token aus Schritt 1 ein
2. **Telegram Chat ID**: Geben Sie Ihre Chat-ID aus Schritt 2 ein
3. Klicken Sie auf **Absenden** und testen Sie die Verbindung

Sie sollten eine Testnachricht von Ihrem Bot erhalten!

### Schritt 4: Home Assistant's telegram_bot Integration Konfigurieren

Um bidirektionale Funktionen zu aktivieren, fügen Sie dies zu Ihrer `configuration.yaml` hinzu:

```yaml
# Polling-Methode (empfohlen für die meisten Benutzer)
telegram_bot:
  - platform: polling
    api_key: IHR_BOT_TOKEN_HIER
    allowed_chat_ids:
      - IHRE_CHAT_ID_HIER
```

**Alternative: Webhooks** (erfordert öffentliche URL mit SSL):

```yaml
telegram_bot:
  - platform: webhooks
    api_key: IHR_BOT_TOKEN_HIER
    allowed_chat_ids:
      - IHRE_CHAT_ID_HIER
    url: https://ihre-domain.com/api/telegram_webhooks
```

**Wichtige Hinweise:**
- Verwenden Sie **dasselbe Bot-Token** und **dieselbe Chat-ID** wie in haFWCMA
- Starten Sie Home Assistant nach der Bearbeitung von `configuration.yaml` neu
- Die `telegram_bot` Integration verwendet Polling/Webhooks zum Empfangen von Nachrichten
- haFWCMA erkennt und verwendet diese Integration automatisch

### Schritt 5: Home Assistant Neu Starten

Nach dem Hinzufügen der `telegram_bot` Konfiguration:

1. Gehen Sie zu **Einstellungen** → **System** → **Neu starten**
2. Warten Sie, bis Home Assistant neu gestartet ist
3. Überprüfen Sie **Einstellungen** → **Geräte & Dienste** → **Integrationen**
4. Sie sollten "Telegram Bot" aufgelistet sehen

### Schritt 6: Bidirektionale Kommunikation Testen

Senden Sie diese Befehle an Ihren Bot in Telegram:

- `/help` - Verfügbare Befehle anzeigen
- `/status` - Aktuellen Fahrzeug- und Kraftstoffstatus anzeigen
- `/refuel` - Tankvorgang protokollieren (in Kürze verfügbar)

## Die Einrichtung Verstehen

### Warum Zwei Konfigurationen?

| Komponente | Zweck | Erforderlich für |
|-----------|---------|--------------|
| **haFWCMA Telegram Config** | Sendet Benachrichtigungen von HA an Sie | Alle Telegram-Funktionen |
| **HA telegram_bot Integration** | Empfängt Befehle von Ihnen an HA | Nur bidirektionale Funktionen |

### Ohne telegram_bot Integration

- ✅ Kraftstoffpreiswarnungen empfangen
- ✅ Tankempfehlungen empfangen
- ✅ Niedriger Tankstand-Warnungen empfangen
- ❌ Keine Befehle an haFWCMA senden können
- ❌ Tankvorgänge nicht über Telegram protokollieren können
- ❌ Kraftstoffstatus nicht abfragen können

### Mit telegram_bot Integration

- ✅ Alle Benachrichtigungsfunktionen
- ✅ Befehle an haFWCMA senden (`/help`, `/status`, etc.)
- ✅ Tankvorgänge über Telegram protokollieren (in Kürze)
- ✅ Interaktive Abfragen und Antworten

## "Conflict: terminated by other getUpdates request" Fehler Vermeiden

**Dieser Fehler tritt auf, wenn mehrere Anwendungen versuchen, `getUpdates` mit demselben Bot zu verwenden.**

### Lösungen:

1. **Verwenden Sie denselben Bot für haFWCMA und telegram_bot** (Empfohlen)
   - Konfigurieren Sie beide mit demselben Bot-Token
   - Nur `telegram_bot` verwendet Polling/Webhooks
   - haFWCMA sendet Nachrichten über HA's Service
   - Keine Konflikte!

2. **Separate Bots verwenden** (Nicht empfohlen)
   - Erstellen Sie zwei verschiedene Bots in @BotFather
   - Verwenden Sie einen für haFWCMA (nur senden)
   - Verwenden Sie einen anderen für telegram_bot (bidirektional)
   - Komplexer, kein wirklicher Vorteil

3. **telegram_bot nicht konfigurieren** (Eingeschränkte Funktionen)
   - Konfigurieren Sie nur Telegram in haFWCMA
   - Nur-Sende-Benachrichtigungen funktionieren einwandfrei
   - Keine bidirektionalen Funktionen

## Polling vs. Webhooks

### Polling (Empfohlen für die Meisten Benutzer)

**Vorteile:**
- ✅ Funktioniert ohne öffentliche URL
- ✅ Funktioniert hinter NAT/Firewall
- ✅ Einfach einzurichten
- ✅ Kein SSL-Zertifikat erforderlich

**Nachteile:**
- ❌ Etwas höhere Latenz (1-2 Sekunden)
- ❌ Verwendet mehr API-Aufrufe

**Verwenden, wenn:** Sie auf Home Assistant über das lokale Netzwerk zugreifen oder keine öffentliche Domain haben.

### Webhooks (Fortgeschritten)

**Vorteile:**
- ✅ Sofortige Nachrichtenzustellung
- ✅ Geringere API-Nutzung
- ✅ Effizienter

**Nachteile:**
- ❌ Erfordert öffentliche URL
- ❌ Erfordert gültiges SSL-Zertifikat
- ❌ Komplexere Einrichtung

**Verwenden, wenn:** Sie Home Assistant über `https://` mit einem gültigen SSL-Zertifikat zugänglich haben.

## Fehlerbehebung

### "Telegram test failed" während der Einrichtung

**Überprüfen:**
1. Bot-Token ist korrekt (keine Leerzeichen, vollständiges Token)
2. Chat-ID ist korrekt (numerisch, positiv oder negativ)
3. Sie haben mindestens eine Nachricht an Ihren Bot gesendet
4. Ihr Bot ist nicht blockiert

**Lösung:**
- Gehen Sie zurück und geben Sie die Anmeldedaten erneut ein
- Testen Sie manuell: `https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=test`

### "Conflict: terminated by other getUpdates request"

**Dieser Fehler wurde in der neuesten Version behoben!**

Wenn Sie ihn immer noch sehen:
1. Stellen Sie sicher, dass Sie die neueste haFWCMA-Version verwenden
2. Konfigurieren Sie nicht mehrere telegram_bot-Instanzen mit demselben Token
3. Verwenden Sie nur ein Bot-Token für alle Ihre Telegram-Integrationen

### Befehle funktionieren nicht

**Überprüfen:**
1. `telegram_bot` ist in `configuration.yaml` konfiguriert
2. Home Assistant wurde neu gestartet
3. Chat-ID in beiden Konfigurationen stimmt überein
4. Bot-Token in beiden Konfigurationen stimmt überein
5. Versuchen Sie `/help` - wenn dies funktioniert, sollten andere auch funktionieren

**Debuggen:**
- Überprüfen Sie Home Assistant-Logs: **Einstellungen** → **System** → **Protokolle**
- Suchen Sie nach "telegram" oder "hafwcma"

### Nachrichten werden nicht gesendet

**Überprüfen:**
1. Telegram-Konfiguration ist nicht leer
2. Verbindungstest war erfolgreich
3. Überprüfen Sie Home Assistant-Logs auf Fehler

## Erweitert: Automatisierungsbeispiele

### Benachrichtigung bei Niedrigem Tankstand

```yaml
automation:
  - alias: "Niedriger Tankstand Telegram-Warnung"
    trigger:
      - platform: numeric_state
        entity_id: sensor.vehicle_range
        below: 100
    action:
      - service: telegram_bot.send_message
        data:
          target: IHRE_CHAT_ID
          message: "⚠️ Niedriger Tankstand! Nur noch {{ states('sensor.vehicle_range') }} km Reichweite."
```

### Benachrichtigung bei Gutem Kraftstoffpreis

```yaml
automation:
  - alias: "Guter Kraftstoffpreis Warnung"
    trigger:
      - platform: numeric_state
        entity_id: sensor.nearest_station_price
        below: 1.50
    action:
      - service: telegram_bot.send_message
        data:
          target: IHRE_CHAT_ID
          message: "💰 Toller Preis! {{ states('sensor.nearest_station_name') }} hat Kraftstoff für €{{ states('sensor.nearest_station_price') }}/L"
```

## Zukünftige Funktionen (In Kürze)

- 📝 Tankvorgänge über Telegram-Chat protokollieren
- 🤖 KI-gestütztes Parsen von Tankdaten aus Text
- 📷 Quittungs-OCR zur automatischen Extraktion von Tankdaten
- 🗺️ Tankstellen über Inline-Tastaturen auswählen
- 📊 Kraftstoffstatistiken über Befehle abfragen
- 🔔 Interaktive Tank-Erinnerungen

## Zusätzliche Ressourcen

- [Home Assistant Telegram Bot Dokumentation](https://www.home-assistant.io/integrations/telegram_bot/)
- [Telegram Bot API Dokumentation](https://core.telegram.org/bots/api)
- [haFWCMA GitHub Issues](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)

## Benötigen Sie Hilfe?

Wenn Sie auf Probleme stoßen:

1. Überprüfen Sie den Abschnitt Fehlerbehebung oben
2. Überprüfen Sie Home Assistant-Protokolle
3. [Öffnen Sie ein Issue](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues) auf GitHub
4. Fügen Sie hinzu:
   - haFWCMA-Version
   - Home Assistant-Version
   - Fehlermeldungen aus den Protokollen
   - Schritte zur Reproduktion
