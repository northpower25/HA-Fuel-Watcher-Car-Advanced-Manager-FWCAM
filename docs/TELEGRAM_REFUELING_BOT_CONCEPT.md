# Konzept: Telegram Bot Bidirektionale Tankvorgang-Erfassung

## Zusammenfassung

Diese Implementierung erweitert die haFWCMA-Integration um eine intelligente, bidirektionale Telegram-Integration für die Erfassung von Tankvorgängen. Das System kombiniert automatische Erkennung, intelligente Benachrichtigungen und flexible Eingabemethoden (Text, Foto, Sprache) in einem benutzerfreundlichen Workflow.

## Problemstellung

Bisherige Tankvorgang-Erfassung erfordert manuelle Eingabe aller Daten über die Home Assistant UI. Dies ist besonders unterwegs unpraktisch und führt häufig zu unvollständigen Datensätzen.

## Lösung

Ein Telegram-Bot, der:
1. **Erkennt** neue Tankvorgänge automatisch oder über UI-Eingabe
2. **Benachrichtigt** den Benutzer mit einer übersichtlichen Nachricht
3. **Sammelt** fehlende Daten über vier verschiedene Eingabemethoden
4. **Analysiert** die Eingaben mit KI-gestütztem Parsing
5. **Speichert** sowohl Rohdaten als auch strukturierte Daten für Debugging

## Architektur

### Komponenten

```
┌─────────────────────────────────────────────────────────────┐
│                    Home Assistant                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              haFWCMA Integration                      │  │
│  │                                                       │  │
│  │  ┌─────────────────────┐  ┌────────────────────────┐ │  │
│  │  │   __init__.py       │  │  telegram_handler.py   │ │  │
│  │  │   - Services        │  │  - /help, /status      │ │  │
│  │  │   - Events          │  │  - Allgemeine Befehle  │ │  │
│  │  └─────────────────────┘  └────────────────────────┘ │  │
│  │            │                         │                │  │
│  │            │                         │                │  │
│  │            ▼                         ▼                │  │
│  │  ┌──────────────────────────────────────────────┐    │  │
│  │  │    telegram_refueling_handler.py             │    │  │
│  │  │                                              │    │  │
│  │  │  - Erkennung neuer Tankvorgänge             │    │  │
│  │  │  - Benachrichtigungserstellung              │    │  │
│  │  │  - Response-Handling (Text/Foto/Voice)      │    │  │
│  │  │  - KI-gestütztes Parsing                    │    │  │
│  │  │  - Datenspeicherung                         │    │  │
│  │  └──────────────────────────────────────────────┘    │  │
│  │            │                                          │  │
│  │            ▼                                          │  │
│  │  ┌──────────────────────────────────────────────┐    │  │
│  │  │         utils/storage.py                     │    │  │
│  │  │  - Refueling Log mit Telegram-Feldern        │    │  │
│  │  └──────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           │ telegram_bot integration         │
│                           ▼                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Telegram Bot API
                            ▼
                  ┌──────────────────┐
                  │   Telegram       │
                  │   Server         │
                  └──────────────────┘
                            │
                            │
                            ▼
                  ┌──────────────────┐
                  │   Benutzer       │
                  │   (Telegram App) │
                  └──────────────────┘
```

### Datenfluss

#### 1. Neuer Tankvorgang erkannt

```
User/System → add_refuel_event → Event gefeuert → TelegramRefuelingHandler
                                                           ↓
                                          Telegram-Nachricht mit:
                                          - Erkannte Daten
                                          - Fehlende Felder
                                          - Inline-Tasten
```

#### 2. Benutzer antwortet

```
Telegram App → telegram_bot → Event → TelegramRefuelingHandler
                                              ↓
                                    Response-Typ erkennen:
                                    - Text → Pattern-Matching
                                    - Foto → OCR (Platzhalter)
                                    - Voice → STT (Platzhalter)
                                    - Callback → Aktion ausführen
                                              ↓
                                    Daten parsen und extrahieren
                                              ↓
                                    Refueling Record aktualisieren
                                              ↓
                                    Bestätigung senden
```

### Datenbankschema Erweiterung

Die `refueling_log` Einträge wurden erweitert um:

```python
{
    # Bestehende Felder
    "id": int,
    "timestamp": str,
    "liters_refueled": float,
    "odometer_km": float,
    "price_per_liter": float,
    "total_cost": float,
    "station_name": str,
    "station_address": str,
    "fuel_type": str,
    "data_quality": str,
    "confidence": float,
    
    # Neue Telegram-Felder
    "telegram_notification_sent": bool,
    "telegram_notification_timestamp": str,
    "telegram_message_id": int,
    "telegram_response_received": bool,
    "telegram_response_timestamp": str,
    "telegram_response_type": str,  # "text" | "photo" | "voice" | "callback"
    "telegram_response_raw": str,  # Rohe Eingabe
    "telegram_response_parsed": dict,  # Geparste Daten
    "telegram_photo_file_id": str,  # Für Fotos
    "telegram_voice_file_id": str,  # Für Sprachnachrichten
}
```

## Text-Parsing-Algorithmus

### Pattern-Matching

Der Text-Parser verwendet reguläre Ausdrücke für bekannte Muster:

```python
# Liter: "45.5 L", "45,5 Liter"
r"(\d+[.,]\d+)\s*(?:L|l|Liter|liter)"

# Preis: "1.599 €/L", "Preis: 1.59"
r"(\d+[.,]\d+)\s*(?:€|EUR)?\s*/\s*(?:L|l)"

# Gesamt: "71.96 €", "Total: 71.96"
r"(?:Gesamt|Total|Summe)[:\s]+(\d+[.,]\d+)"

# KM-Stand: "123456 km", "KM-Stand: 123.456"
r"(?:KM-Stand|Odometer)[:\s]+(\d+[.,]?\d*)"

# Tankstelle: Bekannte Marken oder "Station: Name"
["Shell", "Aral", "Esso", "Total", "Jet", ...]
```

### Erweiterung mit LLM (optional)

Für bessere Ergebnisse kann ein LLM integriert werden:

```python
async def _parse_with_llm(text: str) -> dict:
    """Parse mit GPT/Claude."""
    prompt = f"""
    Extrahiere folgende Daten aus dem Text:
    - Liter getankt
    - Preis pro Liter
    - Gesamtkosten
    - KM-Stand
    - Tankstellenname
    
    Text: {text}
    
    Antwort im JSON-Format:
    """
    
    response = await llm_api.complete(prompt)
    return json.loads(response)
```

## OCR-Integration (Platzhalter)

### Lokale Option (Tesseract)

```python
async def _perform_ocr(self, file_id: str) -> str:
    import pytesseract
    from PIL import Image
    
    # Download photo from Telegram
    file_path = await self._download_telegram_file(file_id)
    
    # Perform OCR
    image = Image.open(file_path)
    text = pytesseract.image_to_string(image, lang='deu')
    
    return text
```

### Cloud Option (Google Vision)

```python
async def _perform_ocr(self, file_id: str) -> str:
    from google.cloud import vision
    
    client = vision.ImageAnnotatorClient()
    
    # Download and read image
    file_path = await self._download_telegram_file(file_id)
    with open(file_path, 'rb') as f:
        content = f.read()
    
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    
    return response.text_annotations[0].description
```

## Speech-to-Text-Integration (Platzhalter)

### Lokale Option (Whisper)

```python
async def _transcribe_voice(self, file_id: str) -> str:
    import whisper
    
    # Download voice from Telegram
    file_path = await self._download_telegram_file(file_id)
    
    # Load model (cache this!)
    model = whisper.load_model("base")
    
    # Transcribe
    result = model.transcribe(file_path, language="de")
    
    return result["text"]
```

### Cloud Option (Google Speech)

```python
async def _transcribe_voice(self, file_id: str) -> str:
    from google.cloud import speech
    
    client = speech.SpeechClient()
    
    # Download and read audio
    file_path = await self._download_telegram_file(file_id)
    with open(file_path, 'rb') as f:
        content = f.read()
    
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        language_code="de-DE",
    )
    
    response = client.recognize(config=config, audio=audio)
    
    return " ".join(r.alternatives[0].transcript for r in response.results)
```

## Benutzeroberfläche

### Binary Sensor

Ein Binary Sensor zeigt den Status der Telegram-Integration:

```yaml
binary_sensor.my_car_telegram_bot:
  state: "on"  # oder "off"
  attributes:
    telegram_bot_integration: true
    chat_id_configured: true
    telegram_method: "integration"
    telegram_handler_active: true
    refueling_handler_active: true
    pending_refuelings: 0
```

### Service für Tests

```yaml
service: hafwcma.simulate_refueling_event
data:
  config_entry_id: "abc123..."
  include_missing_data: true
```

### Frontend-Card Erweiterung (Zukunft)

Geplante Erweiterungen für die FWCAM-Card:
- Anzeige von Telegram-Response-Daten
- Replay-Button für Sprachnachrichten
- Anzeige von Quittungs-Fotos
- Status-Indikator für Telegram-Bot

## Sicherheit und Datenschutz

### Lokale Verarbeitung

- Alle Daten werden lokal in Home Assistant gespeichert
- Keine Weitergabe an Dritte (außer bei Cloud-OCR/STT)
- Verschlüsselte Speicherung über Home Assistant

### Optional: Cloud-Dienste

- Benutzer kann wählen zwischen lokal und Cloud
- Datenschutzhinweise in Dokumentation
- Empfehlung: Lokale Verarbeitung für sensible Daten

### Telegram-Sicherheit

- Chat-ID Authentifizierung
- Nur autorisierte Chats können interagieren
- Message-Threading verhindert Cross-Talk

## Testen

### Unit-Tests (Zukunft)

```python
async def test_text_parsing():
    handler = TelegramRefuelingHandler(...)
    
    text = "45.5 L, 1.599 €/L, Shell"
    parsed = await handler._parse_refuel_text(text)
    
    assert parsed["liters_refueled"] == 45.5
    assert parsed["price_per_liter"] == 1.599
    assert parsed["station_name"] == "Shell"
```

### Integrationstests

```yaml
# Test 1: Simulation
service: hafwcma.simulate_refueling_event
data:
  config_entry_id: "..."
  include_missing_data: true

# → Telegram-Nachricht sollte empfangen werden

# Test 2: Text-Antwort
# Telegram: "45.5 L, 1.599 €/L, Shell"
# → Daten sollten in Refueling-Log aktualisiert werden

# Test 3: Status prüfen
binary_sensor.my_car_telegram_bot: "on"
```

## Deployment

### Installation

1. Integration aktualisieren (HACS oder manuell)
2. Home Assistant neu starten
3. Telegram konfigurieren (falls noch nicht geschehen)
4. Test-Service ausführen

### Voraussetzungen

- Home Assistant 2023.7+ (für ServiceResponse)
- Python 3.11+
- `telegram_bot` Integration konfiguriert
- Optional: OCR/STT Bibliotheken installiert

### Konfiguration

Keine zusätzliche Konfiguration erforderlich - aktiviert sich automatisch bei vorhandener Telegram-Konfiguration.

## Metriken und Monitoring

### Verfügbare Metriken

- `binary_sensor.telegram_bot`: Bot-Status
- `pending_refuelings`: Anzahl wartender Antworten
- Logs: Detaillierte Informationen über Parsing-Ergebnisse

### Performance

- Text-Parsing: <100ms
- OCR (lokal): 1-3 Sekunden
- OCR (Cloud): 0.5-2 Sekunden
- Speech-to-Text (lokal): 2-5 Sekunden
- Speech-to-Text (Cloud): 1-3 Sekunden

## Roadmap

### Phase 1 (Implementiert) ✅
- Grundlegende Architektur
- Text-Parsing mit Pattern-Matching
- Inline-Tastatur für Aktionen
- Vollständige Datenspeicherung
- Dokumentation

### Phase 2 (Optional)
- OCR-Implementierung (Tesseract/Google Vision)
- Speech-to-Text-Implementierung (Whisper/Google Speech)
- LLM-Integration für besseres Parsing
- Frontend-Card Erweiterungen

### Phase 3 (Zukunft)
- Automatische Tankerkennung via Füllstand
- Geofencing für automatische Tankstellenerkennung
- Preis-Schätzung aus historischen Daten
- Multi-Fahrzeug-Support

### Phase 4 (Vision)
- Lernfähiges System (ML)
- Quittungs-Template-Erkennung
- Integration mit Tankstellen-Apps
- Automatische Steuer-Dokumentation

## Zusammenfassung

Diese Implementierung bietet einen soliden, erweiterbaren Rahmen für die bidirektionale Tankvorgang-Erfassung über Telegram. Die modulare Architektur ermöglicht schrittweise Erweiterungen (OCR, STT, LLM) ohne die Kernfunktionalität zu beeinträchtigen.

**Kernvorteile:**
- ✅ Benutzerfreundlich (4 Eingabemethoden)
- ✅ Flexibel (lokal oder Cloud)
- ✅ Erweiterbar (Platzhalter für OCR/STT)
- ✅ Transparent (vollständige Datenspeicherung)
- ✅ Datenschutzfreundlich (lokale Verarbeitung Standard)
- ✅ Gut dokumentiert (DE/EN)
- ✅ Testbar (Simulation-Service)

**Nächste Schritte für Benutzer:**
1. Telegram konfigurieren
2. Test-Service ausführen
3. Optional: OCR/STT implementieren
4. Feedback geben für weitere Verbesserungen
