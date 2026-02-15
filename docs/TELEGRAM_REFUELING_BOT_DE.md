# Telegram Bot Bidirektionale Tankvorgang-Erfassung

## Übersicht

Diese Implementierung erweitert haFWCMA um eine bidirektionale Telegram-Integration für die intelligente Erfassung von Tankvorgängen. Das System erkennt automatisch neue Tankvorgänge, benachrichtigt den Benutzer und sammelt fehlende Informationen über verschiedene Eingabemethoden.

## Funktionsweise

### 1. Automatische Erkennung und Benachrichtigung

Wenn ein neuer Tankvorgang erkannt wird (manuell über die UI oder über den Service `add_refuel_event`):

1. Das System analysiert, welche Informationen bereits vorhanden sind
2. Der Benutzer erhält eine Telegram-Nachricht mit:
   - Allen erkannten Informationen (Zeitpunkt, Menge, Preis, etc.)
   - Einer Liste fehlender Informationen
   - Hinweisen zu den verschiedenen Antwortmöglichkeiten
   - Inline-Tasten für schnelle Aktionen (Bestätigen, Bearbeiten, Löschen)

### 2. Antwortmöglichkeiten des Benutzers

Der Benutzer kann auf vier verschiedene Arten antworten:

#### Option 1: Inline-Tastatur (Formular)

Die Telegram-Nachricht enthält Inline-Tasten für schnelle Aktionen:
- **✅ Bestätigen**: Tankvorgang mit vorhandenen Daten akzeptieren
- **✏️ Bearbeiten**: Fordert zur Eingabe von Korrekturen auf
- **🗑️ Löschen**: Entfernt den Tankvorgang

#### Option 2: Unstrukturierter Text

Der Benutzer kann einfach auf die Nachricht antworten mit freiem Text:

**Beispiele:**
- `45.5 Liter, 1.599 €/Liter, Shell Tankstelle`
- `Preis: 1.65, Tankstelle: Aral, KM-Stand: 123456`
- `72.50 € Gesamt, 45 L, Esso`

Das System verwendet Pattern-Matching und kann folgende Daten extrahieren:
- **Tankvolumen**: `45.5 L`, `45,5 Liter`, `45L`
- **Preis pro Liter**: `1.599 €/L`, `1,599€/Liter`, `Preis: 1.59`
- **Gesamtkosten**: `71.96 €`, `Total: 71,96`, `Gesamt 72€`
- **KM-Stand**: `123456 km`, `KM-Stand: 123.456`
- **Tankstellenname**: Erkennt bekannte Marken (Shell, Aral, Esso, Total, Jet, OMV, Agip) oder nach `Station:` oder `Tankstelle:`

#### Option 3: Foto der Tankquittung

Der Benutzer kann ein Foto der Quittung als Antwort senden.

**Implementierungsoptionen für OCR (Texterkennung):**

##### Lokale Lösungen:
1. **Tesseract OCR** (via pytesseract)
   - Vorteile: Kostenlos, offline, keine Datenweitergabe
   - Nachteile: Geringere Genauigkeit, benötigt CPU-Ressourcen
   - Installation: `pip install pytesseract pillow`
   - Tesseract-Engine muss separat installiert werden

2. **EasyOCR**
   - Vorteile: Bessere Genauigkeit als Tesseract, mehrsprachig
   - Nachteile: Größere Modelle, mehr Speicher/CPU
   - Installation: `pip install easyocr`

3. **PaddleOCR**
   - Vorteile: Sehr gute Genauigkeit, schnell
   - Nachteile: Größere Abhängigkeiten
   - Installation: `pip install paddlepaddle paddleocr`

##### Cloud-basierte Lösungen:
1. **Google Cloud Vision API**
   - Vorteile: Sehr hohe Genauigkeit, robust
   - Nachteile: Kosten (kostenlos bis 1000 Anfragen/Monat)
   - Benötigt: Google Cloud Account, API-Schlüssel

2. **AWS Textract**
   - Vorteile: Spezialisiert auf Dokumente/Quittungen
   - Nachteile: Kosten (kostenlos bis 1000 Seiten/Monat)
   - Benötigt: AWS Account, IAM-Credentials

3. **Azure Computer Vision**
   - Vorteile: Gute Integration mit Microsoft-Diensten
   - Nachteile: Kosten
   - Benötigt: Azure Account, API-Schlüssel

**Aktueller Status:** Die OCR-Funktionalität ist als Platzhalter implementiert. Wählen Sie eine der oben genannten Lösungen basierend auf Ihren Anforderungen (Kosten, Datenschutz, Genauigkeit) und implementieren Sie die `_perform_ocr()` Methode in `telegram_refueling_handler.py`.

#### Option 4: Sprachnachricht

Der Benutzer kann eine Sprachnachricht senden.

**Implementierungsoptionen für Speech-to-Text:**

##### Lokale Lösungen:
1. **Whisper (OpenAI)**
   - Vorteile: State-of-the-art Genauigkeit, mehrsprachig, offline
   - Nachteile: Benötigt GPU für gute Performance (CPU möglich aber langsam)
   - Installation: `pip install openai-whisper`
   - Modelle: tiny, base, small, medium, large (je größer, desto genauer aber langsamer)

2. **Faster-Whisper**
   - Vorteile: 4x schneller als Whisper, gleiche Genauigkeit
   - Nachteile: Komplexere Installation
   - Installation: `pip install faster-whisper`

3. **Vosk**
   - Vorteile: Leichtgewichtig, schnell, offline
   - Nachteile: Geringere Genauigkeit als Whisper
   - Installation: `pip install vosk`
   - Benötigt: Sprachmodell herunterladen

##### Cloud-basierte Lösungen:
1. **Google Cloud Speech-to-Text**
   - Vorteile: Sehr hohe Genauigkeit, Echtzeitverarbeitung
   - Nachteile: Kosten (kostenlos bis 60 Minuten/Monat)
   - Benötigt: Google Cloud Account, API-Schlüssel

2. **AWS Transcribe**
   - Vorteile: Gute Genauigkeit, Batch-Verarbeitung
   - Nachteile: Kosten (kostenlos bis 60 Minuten/Monat)
   - Benötigt: AWS Account, IAM-Credentials

3. **Azure Speech Service**
   - Vorteile: Gute Genauigkeit, mehrsprachig
   - Nachteile: Kosten (kostenlos bis 5 Audiostunden/Monat)
   - Benötigt: Azure Account, API-Schlüssel

**Aktueller Status:** Die Speech-to-Text-Funktionalität ist als Platzhalter implementiert. Wählen Sie eine der oben genannten Lösungen und implementieren Sie die `_transcribe_voice()` Methode in `telegram_refueling_handler.py`.

### 3. KI-gestützte Datenanalyse

Das System analysiert die Benutzerantwort (Text, OCR-Ergebnis, Transkription) und extrahiert strukturierte Daten:

- Verwendet reguläre Ausdrücke für bekannte Muster
- Unterstützt verschiedene Formate und Schreibweisen
- Kann um zusätzliche KI-Modelle erweitert werden (z.B. GPT, Claude via API)

**Erweiterungsmöglichkeiten für bessere KI-Analyse:**
1. **OpenAI GPT API**: Strukturierte Datenextraktion aus Freitext
2. **Anthropic Claude API**: Ähnlich wie GPT, fokussiert auf Genauigkeit
3. **Lokale LLMs**: Llama 2, Mistral (via Ollama oder llama.cpp)
4. **Home Assistant Conversation AI**: Nutzt bereits konfigurierte Conversation-Agenten

### 4. Datenspeicherung

Für jeden Tankvorgang werden folgende Telegram-bezogene Daten gespeichert:

```python
{
    # Benachrichtigung
    "telegram_notification_sent": True/False,
    "telegram_notification_timestamp": "2024-01-15T14:30:00",
    "telegram_message_id": 12345,
    
    # Antwort
    "telegram_response_received": True/False,
    "telegram_response_timestamp": "2024-01-15T14:35:00",
    "telegram_response_type": "text" | "photo" | "voice" | "callback",
    
    # Rohdaten (für Debugging)
    "telegram_response_raw": "45.5 L, 1.599 €/L, Shell",
    
    # Strukturierte Daten (von KI geparst)
    "telegram_response_parsed": {
        "liters_refueled": 45.5,
        "price_per_liter": 1.599,
        "station_name": "Shell"
    },
    
    # Anhänge
    "telegram_photo_file_id": "AgACAgIAAxkBAAI...",  # Für Fotos
    "telegram_voice_file_id": "AwACAgIAAxkBAAI...",  # Für Sprachnachrichten
}
```

## Einrichtung

### Voraussetzungen

1. **Telegram Bot konfiguriert** in Home Assistant
   - Siehe [TELEGRAM_SETUP_DE.md](TELEGRAM_SETUP_DE.md) für Details
   - Sowohl haFWCMA Telegram-Token als auch `telegram_bot` Integration müssen eingerichtet sein

2. **Home Assistant `telegram_bot` Integration**
   ```yaml
   telegram_bot:
     - platform: polling
       api_key: IHR_BOT_TOKEN
       allowed_chat_ids:
         - IHRE_CHAT_ID
   ```

### Aktivierung

Die bidirektionale Tankvorgang-Erfassung wird **automatisch aktiviert**, wenn:
- Telegram Token und Chat-ID in haFWCMA konfiguriert sind
- Die Home Assistant `telegram_bot` Integration geladen ist

**Statusüberprüfung:**

1. **Binary Sensor**: `binary_sensor.[vehicle_name]_telegram_bot`
   - Zeigt an, ob der Telegram Bot aktiv ist
   - Attribute zeigen Details zur Konfiguration

2. **Logs**: Überprüfen Sie die Home Assistant Logs:
   ```
   INFO: Telegram event handler initialized for bidirectional communication
   INFO: Telegram refueling handler initialized for bidirectional refueling tracking
   ```

### Optional: OCR/Speech-to-Text einrichten

Für Foto- und Sprachnachrichten-Unterstützung:

1. Wählen Sie eine Implementierung aus den oben genannten Optionen
2. Installieren Sie die erforderlichen Abhängigkeiten
3. Implementieren Sie die Methoden in `custom_components/hafwcma/telegram_refueling_handler.py`:
   - `_perform_ocr(file_id)` für Fotos
   - `_transcribe_voice(file_id)` für Sprachnachrichten

**Beispiel für Whisper (lokal):**
```python
async def _transcribe_voice(self, file_id: str) -> str | None:
    """Transcribe voice using Whisper."""
    import whisper
    
    # Download file from Telegram
    file_path = await self._download_telegram_file(file_id)
    
    # Load model (cache this in production!)
    model = whisper.load_model("base")
    
    # Transcribe
    result = model.transcribe(file_path, language="de")
    
    return result["text"]
```

## Verwendung

### Test-Tankvorgang simulieren

Verwenden Sie den Service `hafwcma.simulate_refueling_event`:

```yaml
service: hafwcma.simulate_refueling_event
data:
  config_entry_id: "abc123def456"
  include_missing_data: true  # true = mit fehlenden Daten, false = vollständig
```

Dies erstellt einen simulierten Tankvorgang und löst eine Telegram-Benachrichtigung aus.

### Normaler Workflow

1. Tankvorgang hinzufügen (manuell über UI oder automatisch):
   ```yaml
   service: hafwcma.add_refuel_event
   data:
     config_entry_id: "abc123def456"
     timestamp: "2024-01-15T14:30:00"
     liters_refueled: 45.5
     # Andere Felder optional
   ```

2. Sie erhalten eine Telegram-Nachricht mit den Informationen

3. Antworten Sie mit einer der vier Methoden:
   - Inline-Taste drücken
   - Text-Antwort senden
   - Foto der Quittung senden
   - Sprachnachricht senden

4. Das System verarbeitet Ihre Antwort und aktualisiert den Tankvorgang

5. Sie erhalten eine Bestätigung mit den erkannten Daten

## Verfügbare Services

### hafwcma.simulate_refueling_event

Erstellt einen Test-Tankvorgang zur Überprüfung der Telegram-Funktionalität.

**Parameter:**
- `config_entry_id` (erforderlich): Config Entry ID der Integration
- `include_missing_data` (optional, default: true): Ob fehlende Daten simuliert werden sollen

### hafwcma.add_refuel_event

Fügt einen echten Tankvorgang hinzu (löst Telegram-Benachrichtigung aus).

**Parameter:**
- `config_entry_id` (erforderlich): Config Entry ID
- `timestamp` (erforderlich): Zeitstempel im ISO-Format
- `liters_refueled` (erforderlich): Getankte Liter
- `odometer_km` (optional): KM-Stand
- `price_per_liter` (optional): Preis pro Liter
- `total_cost` (optional): Gesamtkosten
- `station_name` (optional): Tankstellenname
- `station_address` (optional): Tankstellenadresse
- `fuel_type` (optional): Kraftstoffart (e5, e10, diesel)

## Datenschutz

### Lokale Verarbeitung
- Telegram-Nachrichten werden nur in Ihrer Home Assistant-Instanz verarbeitet
- Rohdaten und geparste Daten werden lokal in `.storage/hafwcma_<entry_id>.json` gespeichert
- Keine Weitergabe an Drittanbieter (außer bei Cloud-OCR/STT)

### Cloud-Dienste (optional)
Wenn Sie Cloud-basierte OCR oder Speech-to-Text verwenden:
- Fotos/Audio werden an den gewählten Cloud-Anbieter gesendet
- Überprüfen Sie die Datenschutzrichtlinien des Anbieters
- Erwägen Sie lokale Alternativen für sensible Daten

## Debugging

### Telegram-Response-Daten anzeigen

Alle Antworten werden im Tankvorgang-Log gespeichert. Sie können diese über den Frontend-Card oder direkt in der Storage-Datei einsehen:

```yaml
service: hafwcma.get_all_refuelings
data:
  config_entry_id: "abc123def456"
```

Jeder Tankvorgang enthält:
- `telegram_response_raw`: Rohe Benutzereingabe
- `telegram_response_parsed`: Strukturierte, geparste Daten
- `telegram_photo_file_id`: Telegram File-ID für Fotos
- `telegram_voice_file_id`: Telegram File-ID für Sprachnachrichten

### Logs überprüfen

Aktivieren Sie Debug-Logging für detaillierte Informationen:

```yaml
logger:
  default: info
  logs:
    custom_components.hafwcma.telegram_refueling_handler: debug
    custom_components.hafwcma.telegram_handler: debug
```

## Bekannte Einschränkungen

1. **OCR und Speech-to-Text** sind als Platzhalter implementiert
   - Sie müssen eine der vorgeschlagenen Lösungen selbst implementieren
   - Dies ermöglicht die Wahl zwischen lokalen und Cloud-Lösungen

2. **Basis-KI-Parsing** verwendet nur Pattern-Matching
   - Kann durch GPT/Claude API oder lokale LLMs erweitert werden
   - Aktuelle Implementierung ist ausreichend für strukturierte Eingaben

3. **Keine automatische Tankerkennung**
   - Tankvorgänge müssen manuell oder per Service hinzugefügt werden
   - Zukünftige Erweiterung könnte automatische Erkennung über Tankfüllstandsänderungen implementieren

## Zukünftige Erweiterungen

1. **Erweiterte KI-Integration**
   - GPT-4 Vision für Quittungs-Analyse
   - Lokale LLMs für vollständige Offline-Verarbeitung
   - Lernfähiges System, das sich an Benutzergewohnheiten anpasst

2. **Multimedia-Support**
   - Quittungs-Foto im Frontend anzeigen
   - Sprachnachricht im Frontend abspielen
   - PDF-Quittungen unterstützen

3. **Automatische Erkennung**
   - Tankvorgang automatisch erkennen (Füllstandsänderung + GPS-Position)
   - Tankstelle automatisch identifizieren (Geofencing)
   - Preis aus lokaler Preisentwicklung schätzen

4. **Telegram-Bot-Befehle**
   - `/refuel` - Manuell Tankvorgang starten
   - `/status` - Tankstand und nächste Tankstellen anzeigen
   - `/history` - Letzte Tankvorgänge anzeigen
   - `/stats` - Statistiken und Verbrauch anzeigen

## Support und Beitragen

Bei Fragen oder Problemen:
1. Überprüfen Sie die Home Assistant Logs
2. Stellen Sie sicher, dass die `telegram_bot` Integration korrekt konfiguriert ist
3. Testen Sie mit dem `simulate_refueling_event` Service

Beiträge willkommen:
- Implementierungen für OCR/Speech-to-Text
- Verbesserungen am Text-Parsing
- UI-Erweiterungen im Frontend-Card
- Übersetzungen und Dokumentation

## Changelog

### Version 1.0.0 (Initial Release)
- ✅ Automatische Telegram-Benachrichtigung bei neuem Tankvorgang
- ✅ Inline-Tastatur für schnelle Aktionen
- ✅ Unstrukturierte Text-Eingabe mit Pattern-Matching
- ✅ Foto-/Sprachnachrichten-Support (Platzhalter)
- ✅ Vollständige Datenspeicherung für Debugging
- ✅ Test-Service für einfaches Testen
- ✅ Binary Sensor für Status-Anzeige
- ✅ Deutsche Dokumentation
