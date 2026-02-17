# 🎉 Telegram Bot Bidirektionale Tankvorgang-Erfassung - Implementiert!

## ✅ Was wurde implementiert?

Eine vollständige, produktionsreife Lösung für die intelligente Erfassung von Tankvorgängen über Telegram mit folgenden Features:

### Kernfunktionalität

1. **Automatische Benachrichtigung** 📱
   - Bei jedem neuen Tankvorgang erhalten Sie eine Telegram-Nachricht
   - Zeigt alle erkannten Informationen an
   - Hebt fehlende Daten hervor
   - Bietet vier verschiedene Antwortmöglichkeiten

2. **Vier Antwortmethoden** 💬
   - ✅ **Inline-Tasten**: Schnelles Bestätigen/Bearbeiten/Löschen (VOLL IMPLEMENTIERT)
   - ✅ **Text**: Freie Eingabe wie "45.5 L, 1.599 €/L, Shell" (VOLL IMPLEMENTIERT)
   - 🔄 **Foto**: Quittung fotografieren (PLATZHALTER - OCR muss implementiert werden)
   - 🔄 **Sprache**: Sprachnachricht senden (PLATZHALTER - STT muss implementiert werden)

3. **KI-gestütztes Parsing** 🤖 (VOLL IMPLEMENTIERT)
   - Extrahiert automatisch Daten aus unstrukturierten Eingaben
   - Erkennt Liter, Preis, Kosten, KM-Stand, Tankstelle
   - Unterstützt verschiedene Formate und Schreibweisen
   - Markiert Tankvorgänge als "AI Processed" bei erfolgreicher Verarbeitung

4. **Vollständige Datenspeicherung** 💾 (VOLL IMPLEMENTIERT)
   - Rohdaten der Benutzerantwort
   - Geparste, strukturierte Daten
   - Telegram File-IDs für Fotos/Sprachnachrichten
   - Perfekt für Debugging und Nachvollziehbarkeit
   - Neue Data Quality: "AI Processed" für automatisch verarbeitete Daten

5. **Test-Button** 🧪 (NEU - VOLL IMPLEMENTIERT)
   - Button "Telegram API Test" im Home Assistant Dashboard
   - Erstellt echten Test-Tankvorgang mit fehlenden Daten
   - Wartet auf Benutzerantwort via Telegram
   - Zeigt Antwortzeit und erkannte Daten in Button-Attributen
   - Perfekt zum Testen der bidirektionalen Kommunikation

6. **Status-Anzeige** 📊 (VOLL IMPLEMENTIERT)
   - Binary Sensor zeigt Telegram-Bot-Status
   - Detaillierte Attribute zur Konfiguration
   - Button-Attribute zeigen Test-Ergebnisse

7. **Lovelace Card Integration** 💳 (NEU - VOLL IMPLEMENTIERT)
   - Zeigt Benutzer-Nachricht und AI-erkannte Daten nebeneinander
   - Sichtbar beim Bearbeiten von Tankvorgängen
   - Nur angezeigt wenn Telegram-Antwort vorhanden

## 🚀 Schnellstart

### Voraussetzungen

1. ✅ Home Assistant 2023.7 oder neuer
2. ✅ haFWCMA Integration bereits installiert
3. ✅ Telegram Bot konfiguriert (Token und Chat-ID in haFWCMA eingetragen)
4. ✅ Home Assistant `telegram_bot` Integration eingerichtet

Wenn Telegram noch nicht konfiguriert ist, siehe: [TELEGRAM_SETUP_DE.md](TELEGRAM_SETUP_DE.md)

### Installation

1. **Integration aktualisieren** (HACS oder manuell)
2. **Home Assistant neu starten**
3. **Status prüfen**: `binary_sensor.[fahrzeugname]_telegram_bot` sollte "on" sein
4. **Testen**:
   ```yaml
   service: hafwcma.simulate_refueling_event
   data:
     config_entry_id: "IHRE_CONFIG_ENTRY_ID"
     include_missing_data: true
   ```

### Erste Schritte

1. **Test-Button nutzen**
   - Öffnen Sie Home Assistant Dashboard
   - Suchen Sie den Button "Telegram API Test" für Ihr Fahrzeug
   - Klicken Sie den Button
   - Bei bidirektionaler Unterstützung: Antworten Sie auf die Telegram-Nachricht
   - Prüfen Sie die Button-Attribute für Testergebnisse

2. **Alternativ: Test-Tankvorgang über Service simulieren**
   ```yaml
   service: hafwcma.simulate_refueling_event
   data:
     config_entry_id: "IHRE_CONFIG_ENTRY_ID"
     include_missing_data: true
   ```

3. **Config Entry ID finden:**
   - Methode 1: Developer Tools → States → Suchen Sie `sensor.[fahrzeugname]_*` → Schauen Sie in die Attribute
   - Methode 2: Prüfen Sie die Button-Attribute von `button.[fahrzeugname]_telegram_api_test`
   - Methode 3: `.storage/core.config_entries` Datei (für fortgeschrittene Benutzer)

4. **Telegram-Nachricht empfangen** mit Tankvorgangs-Details

5. **Antworten** mit einer der Methoden:
   - Inline-Taste drücken (✅ Bestätigen / ✏️ Bearbeiten)
   - Text antworten: "45.5 L, 1.599 €/L, Shell"
   - Foto der Quittung senden (OCR muss noch implementiert werden)
   - Sprachnachricht senden (STT muss noch implementiert werden)

6. **Bestätigung erhalten** mit den erkannten Daten

7. **Tankvorgang prüfen** in der Lovelace Card:
   - Öffnen Sie den Tankvorgang zum Bearbeiten
   - Scrollen Sie nach unten zum Abschnitt "📱 Telegram Response"
   - Sehen Sie Ihre ursprüngliche Nachricht und die AI-erkannten Daten nebeneinander

## 📚 Dokumentation

### Hauptdokumente

1. **[TELEGRAM_REFUELING_BOT_DE.md](../dev_docs/TELEGRAM_REFUELING_BOT_DE.md)** - Vollständiger deutscher Leitfaden
   - Detaillierte Funktionsbeschreibung
   - Setup-Anleitung
   - Verwendung und Beispiele
   - OCR/STT Implementierungsoptionen
   - Datenschutz und Debugging

2. **[TELEGRAM_REFUELING_BOT.md](../dev_docs/TELEGRAM_REFUELING_BOT.md)** - English Guide
   - Complete English documentation
   - All essential information

3. **[TELEGRAM_REFUELING_BOT_EXAMPLES.md](TELEGRAM_REFUELING_BOT_EXAMPLES.md)** - Automation-Beispiele
   - Real-World-Automationen
   - Dashboard-Konfigurationen
   - Node-RED Flows
   - Troubleshooting

4. **[TELEGRAM_REFUELING_BOT_CONCEPT.md](../TELEGRAM_REFUELING_CONCEPT.md)** - Technisches Konzept
   - Architektur-Übersicht
   - Datenfluss-Diagramme
   - Implementierungsbeispiele
   - Roadmap

## 🎯 Beispiel-Workflow

### Szenario: Unterwegs getankt

1. **Sie tanken** bei einer Tankstelle
2. **Später zu Hause** fügen Sie den Tankvorgang in der haFWCMA-UI hinzu
3. **Sofort** erhalten Sie eine Telegram-Nachricht:
   ```
   ⛽ Neuer Tankvorgang erkannt!
   
   🕐 Zeitpunkt: 15.02.2024 14:30
   📊 Menge: 45.50 Liter
   
   ❓ Fehlende Informationen:
   Preis pro Liter, Gesamtkosten, KM-Stand, Tankstellenname
   
   💡 Wie können Sie antworten:
   • Antworten Sie mit Text
   • Senden Sie ein Foto der Quittung
   • Senden Sie eine Sprachnachricht
   • Nutzen Sie die Schaltflächen unten
   
   [✅ Bestätigen] [✏️ Bearbeiten]
   [🗑️ Löschen]
   ```

4. **Sie antworten** bequem von unterwegs:
   - Option A: "1.599 €/L, 72.70 € gesamt, Shell Tankstelle, 123456 km"
   - Option B: Foto der Quittung
   - Option C: Sprachnachricht: "Ich habe für 1 Euro 59 pro Liter getankt, insgesamt 72 Euro 70 bei Shell, KM-Stand 123.456"

5. **System extrahiert** die Daten automatisch:
   ```
   ✅ Daten für Tankvorgang #42 aktualisiert!
   
   Erkannte Daten:
   {
     "price_per_liter": 1.599,
     "total_cost": 72.70,
     "station_name": "Shell",
     "odometer_km": 123456.0
   }
   ```

6. **Fertig!** Alle Daten sind erfasst und in der Datenbank gespeichert.

## 🔍 Was kann das Text-Parsing erkennen?

Das System versteht verschiedene Formate:

### Tankvolumen
- ✅ "45.5 L"
- ✅ "45,5 Liter"
- ✅ "45L"
- ✅ "45.5 liters"

### Preis pro Liter
- ✅ "1.599 €/L"
- ✅ "1,599€/Liter"
- ✅ "Preis: 1.59"
- ✅ "1.599 EUR/l"

### Gesamtkosten
- ✅ "71.96 €"
- ✅ "Total: 71,96"
- ✅ "Gesamt 72€"
- ✅ "Summe: 71.96 EUR"

### KM-Stand
- ✅ "123456 km"
- ✅ "KM-Stand: 123.456"
- ✅ "Kilometerstand 123456"
- ✅ "123456km"

### Tankstelle
- ✅ Bekannte Marken: Shell, Aral, Esso, Total, Jet, OMV, Agip
- ✅ "Station: Beliebiger Name"
- ✅ "Tankstelle: Beliebiger Name"

## 📸 Foto-Support (Optional)

**STATUS: 🔄 IN VORBEREITUNG - Implementierung erforderlich**

Die Infrastruktur für Foto-Verarbeitung ist vorhanden, aber die OCR-Engine muss noch implementiert werden.

### Was bereits funktioniert:
- ✅ Foto-Upload via Telegram wird empfangen
- ✅ File-ID wird gespeichert
- ✅ Foto wird als "telegram_response_type: photo" markiert
- ✅ Platzhalter-Nachricht wird angezeigt

### Was noch implementiert werden muss:
- ❌ OCR-Engine zur Texterkennung
- ❌ Download des Fotos vom Telegram-Server
- ❌ Verarbeitung und Texterkennung

### Implementierungsoptionen:

Für die Quittungs-Erkennung können Sie eine OCR-Lösung implementieren:

### Lokale Optionen (Datenschutz)
- **Tesseract OCR**: Kostenlos, offline
  - Installation: `apt-get install tesseract-ocr` + Python: `pip install pytesseract`
  - Config Flow Erweiterung: Checkbox "Use Tesseract OCR"
- **EasyOCR**: Bessere Genauigkeit, mehrsprachig
  - Installation: `pip install easyocr`
  - Config Flow Erweiterung: Checkbox "Use EasyOCR"
- **PaddleOCR**: Sehr gute Genauigkeit, schnell
  - Installation: `pip install paddleocr`
  - Config Flow Erweiterung: Checkbox "Use PaddleOCR"

### Cloud-Optionen (Hohe Genauigkeit)
- **Google Cloud Vision**: Bis 1000 Anfragen/Monat kostenlos
  - Config Flow Erweiterung: API Key Feld
- **AWS Textract**: Spezialisiert auf Dokumente
  - Config Flow Erweiterung: AWS Credentials
- **Azure Computer Vision**: Microsoft-Integration
  - Config Flow Erweiterung: Azure API Key

### Erforderliche Config Flow Änderungen:
1. Neuer Schritt "OCR Configuration" im Setup
2. Auswahl zwischen Local/Cloud
3. Bei Local: Auswahl der Engine (Tesseract/EasyOCR/PaddleOCR)
4. Bei Cloud: API-Schlüssel Eingabe
5. Test-Button zur Verifikation

**Implementierungsort**: `telegram_refueling_handler.py` → Methode `_perform_ocr()`

**Implementierungsanleitung** in der Dokumentation!

## 🎤 Sprach-Support (Optional)

**STATUS: 🔄 IN VORBEREITUNG - Implementierung erforderlich**

Die Infrastruktur für Sprachnachrichten-Verarbeitung ist vorhanden, aber die STT-Engine muss noch implementiert werden.

### Was bereits funktioniert:
- ✅ Sprachnachrichten via Telegram werden empfangen
- ✅ File-ID wird gespeichert
- ✅ Voice-Nachricht wird als "telegram_response_type: voice" markiert
- ✅ Platzhalter-Nachricht wird angezeigt

### Was noch implementiert werden muss:
- ❌ Speech-to-Text Engine zur Transkription
- ❌ Download der Sprachdatei vom Telegram-Server
- ❌ Audio-Konvertierung (Telegram sendet .ogg Format)
- ❌ Transkription und Verarbeitung

### Implementierungsoptionen:

Für Sprachnachrichten können Sie eine Speech-to-Text-Lösung implementieren:

### Lokale Optionen (Datenschutz)
- **Whisper (OpenAI)**: State-of-the-art, offline möglich
  - Installation: `pip install openai-whisper`
  - Modellgröße wählbar (tiny bis large)
  - Config Flow Erweiterung: Whisper Model Selection (tiny/base/small/medium/large)
- **Faster-Whisper**: 4x schneller als Whisper
  - Installation: `pip install faster-whisper`
  - Config Flow Erweiterung: Checkbox "Use Faster-Whisper"
- **Vosk**: Leichtgewichtig, schnell
  - Installation: `pip install vosk` + Modell-Download
  - Config Flow Erweiterung: Vosk Model Path

### Cloud-Optionen (Hohe Genauigkeit)
- **Google Speech-to-Text**: Bis 60 Min/Monat kostenlos
  - Config Flow Erweiterung: Google Cloud API Key
- **AWS Transcribe**: Batch-Verarbeitung
  - Config Flow Erweiterung: AWS Credentials
- **Azure Speech**: Mehrsprachig
  - Config Flow Erweiterung: Azure Speech Key

### Erforderliche Config Flow Änderungen:
1. Neuer Schritt "Speech-to-Text Configuration" im Setup
2. Auswahl zwischen Local/Cloud
3. Bei Local: Auswahl der Engine und Modell
4. Bei Cloud: API-Schlüssel Eingabe
5. Sprach-Auswahl (Deutsch, Englisch, etc.)
6. Test-Button zur Verifikation

**Implementierungsort**: `telegram_refueling_handler.py` → Methode `_transcribe_voice()`

**Implementierungsanleitung** in der Dokumentation!

## 🛡️ Datenschutz

### Standard: Lokal
- ✅ Alle Daten bleiben in Home Assistant
- ✅ Keine Weitergabe an Dritte
- ✅ Text-Parsing komplett lokal
- ✅ Verschlüsselte Speicherung

### Optional: Cloud-Dienste
- 📸 Nur wenn Sie OCR/STT implementieren
- 🔒 Sie wählen den Anbieter
- 📋 Prüfen Sie die Datenschutzrichtlinien
- 💡 Empfehlung: Lokale Lösungen für sensible Daten

## 🧪 Testen

### Methode 1: Test-Button verwenden (EMPFOHLEN)

Der einfachste Weg zum Testen:

1. **Button finden**:
   - Öffnen Sie Ihr Home Assistant Dashboard
   - Suchen Sie nach `button.[fahrzeugname]_telegram_api_test`
   - Oder: Entities → Filter "telegram"

2. **Button drücken**:
   - Klicken Sie auf den Button
   - System prüft automatisch ob bidirektionale Kommunikation verfügbar ist
   - Bei Unterstützung: Echter Tankvorgang wird erstellt
   - Sonst: Einfache Test-Nachricht wird gesendet

3. **Auf Telegram antworten**:
   - Sie erhalten eine Nachricht über einen neuen Tankvorgang
   - Antworten Sie mit: "45.5 L, 1.599 €/L, Shell, 123456 km"
   - Oder nutzen Sie die Inline-Buttons

4. **Ergebnisse prüfen**:
   - Öffnen Sie die Button-Entität
   - Schauen Sie in die Attribute:
     - `test_refuel_id`: ID des Test-Tankvorgangs
     - `test_refuel_created_at`: Zeitpunkt der Erstellung
     - `test_refuel_response_at`: Zeitpunkt der Antwort
     - `test_response_time_seconds`: Antwortzeit in Sekunden
     - `test_refuel_response_raw`: Ihre ursprüngliche Nachricht
     - `test_refuel_response_parsed`: Die erkannten Daten

### Methode 2: Test-Service verwenden

Für fortgeschrittene Benutzer oder Automationen:

```yaml
service: hafwcma.simulate_refueling_event
data:
  config_entry_id: "abc123def456"  # Ihre Config Entry ID
  include_missing_data: true        # true = mit fehlenden Daten
```

**Config Entry ID finden:**
1. Developer Tools → States
2. Suchen Sie nach `sensor.[fahrzeugname]_*` oder `button.[fahrzeugname]_telegram_api_test`
3. Schauen Sie in die Attribute
4. Oder: Prüfen Sie `.storage/core.config_entries` (für Experten)

### Status überprüfen

```yaml
binary_sensor.my_car_telegram_bot:
  state: "on"  # Sollte "on" sein
  attributes:
    telegram_bot_integration: true
    telegram_handler_active: true
    refueling_handler_active: true
    pending_refuelings: 0
```

## 📊 Gespeicherte Daten

Alle Tankvorgänge enthalten nun:

```python
{
    # Bestehende Felder
    "id": 42,
    "timestamp": "2024-02-15T14:30:00",
    "liters_refueled": 45.5,
    "price_per_liter": 1.599,
    "total_cost": 72.70,
    "station_name": "Shell",
    # ... weitere Felder
    
    # Neue Telegram-Felder
    "telegram_notification_sent": true,
    "telegram_notification_timestamp": "2024-02-15T14:30:05",
    "telegram_message_id": 12345,
    "telegram_response_received": true,
    "telegram_response_timestamp": "2024-02-15T14:35:00",
    "telegram_response_type": "text",
    "telegram_response_raw": "1.599 €/L, 72.70 € gesamt, Shell, 123456 km",
    "telegram_response_parsed": {
        "price_per_liter": 1.599,
        "total_cost": 72.70,
        "station_name": "Shell",
        "odometer_km": 123456.0
    }
}
```

**Perfekt für:**
- 🔍 Debugging
- 📊 Analyse
- 🧾 Nachvollziehbarkeit
- 🎓 Training von KI-Modellen

## 🎨 Automation-Beispiele

### Täglicher Test

```yaml
automation:
  - alias: "Täglicher Tankvorgang-Test"
    trigger:
      - platform: time
        at: "10:00:00"
    action:
      - service: hafwcma.simulate_refueling_event
        data:
          config_entry_id: "IHRE_CONFIG_ENTRY_ID"
          include_missing_data: true
```

### Erinnerung nach 30 Minuten

```yaml
automation:
  - alias: "Tankvorgang Antwort-Erinnerung"
    trigger:
      - platform: event
        event_type: hafwcma_refueling_added
    action:
      - delay:
          minutes: 30
      - service: telegram_bot.send_message
        data:
          target: IHRE_CHAT_ID
          message: "🔔 Bitte ergänzen Sie die Tankvorgang-Daten"
```

Mehr Beispiele in [TELEGRAM_REFUELING_BOT_EXAMPLES.md](TELEGRAM_REFUELING_BOT_EXAMPLES.md)

## ❓ Häufige Fragen

### Wird automatisch aktiviert?
Ja! Wenn Telegram konfiguriert ist, aktiviert sich die Funktion automatisch.

### Muss ich OCR/STT implementieren?
Nein! Text und Inline-Tasten funktionieren sofort. OCR/STT sind optional.

### Wie erkenne ich, ob es funktioniert?
Prüfen Sie `binary_sensor.[fahrzeug]_telegram_bot` - sollte "on" sein.

### Kostet das etwas?
Lokale Verarbeitung ist kostenlos. Cloud-Dienste haben oft Free Tiers.

### Ist es sicher?
Ja! Alle Daten bleiben lokal, außer Sie wählen Cloud-OCR/STT.

## 🐛 Troubleshooting

### Benachrichtigung wird nicht gesendet
1. ✅ Prüfen Sie `binary_sensor` Status
2. ✅ Überprüfen Sie die Logs
3. ✅ Testen Sie mit Test-Button in der UI

### Antwort wird nicht erkannt
1. ✅ Auf die Nachricht antworten (Reply)
2. ✅ Strukturierte Eingabe verwenden
3. ✅ Logs auf Parsing-Fehler prüfen

### Bot reagiert nicht
1. ✅ `telegram_bot` Integration läuft?
2. ✅ Home Assistant neu starten
3. ✅ Chat-ID korrekt?

**Detaillierte Hilfe** in der Dokumentation!

## 🎉 Los geht's!

1. **Aktualisieren** Sie die Integration
2. **Starten** Sie Home Assistant neu
3. **Testen** Sie mit dem Simulations-Service
4. **Genießen** Sie die komfortable Tankvorgang-Erfassung!

## 📞 Support

- 📚 Vollständige Dokumentation in `docs/`
- 🧪 Test-Service zum Ausprobieren
- 🔍 Debug-Logging verfügbar
- 💬 GitHub Issues für Feedback

## 🙏 Danke!

Vielen Dank, dass Sie haFWCMA verwenden. Diese Implementierung macht die Tankvorgang-Erfassung so einfach wie nie zuvor!

**Viel Spaß beim Tanken! ⛽**
