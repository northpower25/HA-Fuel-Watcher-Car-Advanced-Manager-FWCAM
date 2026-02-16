# Erweiterte Tankvorgangs-Erkennung

## Übersicht

Nach der Implementierung von PR #128 wurden die Erkennungsmuster für Kilometerstände und Tankstellennamen deutlich verbessert. Dieses Dokument beschreibt die neuen Funktionen und gibt Beispiele für deren Verwendung.

## Kilometerstand-Erkennung

### Unterstützte Formate

Die Kilometerstand-Erkennung unterstützt jetzt mehrere Formate:

1. **Mit Keyword**: `KM-Stand: 123456`, `Kilometerstand: 123456`, `Odometer: 123456`
2. **Kompakt**: `1650km` (Zahl direkt gefolgt von "km")
3. **Mit Leerzeichen**: `1650 km`, `1650 KM` (Groß-/Kleinschreibung egal)
4. **Mit Tausendertrennzeichen**: `123.456 km`, `123,456 km`

### Beispiele

```
✅ "1650km HEM Kummerfeld"
   → odometer_km: 1650.0

✅ "1650 KM HEM Kummerfeld"
   → odometer_km: 1650.0

✅ "Kilometerstand: 54321 Shell Neumünster"
   → odometer_km: 54321.0

✅ "12345 KM ESSO Berlin"
   → odometer_km: 12345.0
```

### Technische Details

- **Mindestanzahl Ziffern**: 4 (unterstützt Werte ab 1000 km)
- **Maximale Anzahl Ziffern**: 7 (bis 9.999.999 km)
- **Groß-/Kleinschreibung**: Wird ignoriert (case-insensitive)
- **Leerzeichen**: Optional zwischen Zahl und "km"/"KM"

## Tankstellennamen-Erkennung

### Unterstützte Muster

Die Tankstellennamen-Erkennung unterstützt jetzt komplexe Muster:

1. **MARKE STADT**: `HEM Kummerfeld`, `Shell Hamburg`
2. **MARKE STADT STRASSE**: `ARAL Elmshorn Musterstrasse`
3. **MARKE PLZ STADT**: `Shell 12345 Hamburg`
4. **MARKE PLZ STADT STRASSE HAUSNR**: `ARAL 25336 Elmshorn Hauptstraße 42`

### Erkannte Komponenten

- **Marke** (erforderlich): Name der Tankstellenkette
- **PLZ** (optional): 5-stellige Postleitzahl vor dem Städtenamen
- **Stadt** (erforderlich): Städtename
- **Straße** (optional): Straßenname (erkennt Suffixe wie "straße", "str.", "weg", "platz", "allee")
- **Hausnummer** (optional): 1-3-stellige Hausnummer nach dem Straßennamen

### Unterstützte Marken

Die folgenden deutschen Tankstellenmarken werden erkannt (Groß-/Kleinschreibung egal):

- **Internationale**: Shell, Aral, Esso, Total, Jet, OMV, Agip
- **Deutsche**: HEM, Westfalen, Star, Raiffeisen, bft

### Beispiele

```
✅ "1650km HEM Kummerfeld"
   → station_name: "HEM Kummerfeld"

✅ "ARAL Elmshorn Musterstrasse"
   → station_name: "ARAL Elmshorn Musterstrasse"

✅ "ARAL 25336 Elmshorn Hauptstraße 42"
   → station_name: "ARAL 25336 Elmshorn Hauptstraße 42"

✅ "Shell Hamburg"
   → station_name: "Shell Hamburg"

✅ "Kilometerstand: 54321 Shell Neumünster"
   → station_name: "Shell Neumünster"
```

### Fallback-Verhalten

Wenn kein strukturiertes Muster erkannt wird:

1. Marke + erste 3 Wörter danach werden verwendet
2. Wenn keine Wörter folgen, nur der Markenname
3. Wenn keine Marke erkannt wird, wird nach "Station:" oder "Tankstelle:" gesucht

## Foto- und Sprachnachrichten

### Speicherung der Daten

Wenn Sie mit einem Foto oder einer Sprachnachricht antworten, werden folgende Daten am Tankvorgang-Objekt gespeichert:

#### Foto (Quittung)

```json
{
  "telegram_response_received": true,
  "telegram_response_timestamp": "2024-01-15T10:30:00",
  "telegram_response_type": "photo",
  "telegram_response_raw": "Caption: [Ihre Bildunterschrift]\nOCR: [Erkannter Text]",
  "telegram_response_parsed": {
    "liters_refueled": 45.5,
    "price_per_liter": 1.599,
    "total_cost": 72.75
  },
  "telegram_photo_file_id": "AgACAgIAAxkBAAI...",
  "data_quality": "ai_processed"
}
```

#### Sprachnachricht

```json
{
  "telegram_response_received": true,
  "telegram_response_timestamp": "2024-01-15T10:30:00",
  "telegram_response_type": "voice",
  "telegram_response_raw": "[Transkribierter Text]",
  "telegram_response_parsed": {
    "odometer_km": 1650,
    "station_name": "HEM Kummerfeld"
  },
  "telegram_voice_file_id": "AwACAgIAAxkBAAI...",
  "data_quality": "ai_processed"
}
```

### OCR/STT Verarbeitung

**Wichtig**: Die OCR (Optical Character Recognition) und STT (Speech-to-Text) Funktionen sind derzeit als TODO markiert und müssen noch implementiert werden. Die Infrastruktur zur Speicherung der Daten ist jedoch bereits vorhanden.

**Geplante Optionen für OCR**:
- Lokal: Tesseract OCR via pytesseract
- Cloud: Google Vision API, AWS Textract, Azure Computer Vision
- Home Assistant Integration: Verwendung vorhandener HA-Integrationen

**Geplante Optionen für STT**:
- Lokal: Vosk, Whisper (OpenAI), faster-whisper
- Cloud: Google Speech-to-Text, AWS Transcribe, Azure Speech
- Home Assistant Integration: Verwendung vorhandener HA-Integrationen

### Spätere Erkennungsprozesse

Die gespeicherten Rohdaten (`telegram_response_raw`) und File-IDs (`telegram_photo_file_id`, `telegram_voice_file_id`) können für spätere Erkennungsprozesse verwendet werden:

1. **Nachträgliche OCR-Verarbeitung**: Wenn OCR später implementiert wird, können gespeicherte Foto-File-IDs erneut verarbeitet werden
2. **Verbesserte STT-Modelle**: Wenn bessere Spracherkennungsmodelle verfügbar werden, können Sprachnachrichten erneut transkribiert werden
3. **Manuelle Korrektur**: Die Rohdaten können zur manuellen Überprüfung und Korrektur verwendet werden

## Integration mit dem Parsing

Alle Erkennungsmethoden (Text, OCR, STT) verwenden dieselbe `_parse_refuel_text` Methode, die:

1. **Liter** aus verschiedenen Formaten extrahiert
2. **Preis pro Liter** erkennt (explizit oder smart detection)
3. **Gesamtkosten** berechnet oder extrahiert
4. **Kilometerstand** mit den oben beschriebenen Mustern erkennt
5. **Tankstellennamen** mit strukturierter Mustererkennung extrahiert
6. **Fehlende Werte berechnet** (z.B. Preis aus Gesamtkosten ÷ Liter)

## Best Practices

### Für optimale Erkennung

1. **Kilometerstand**: Verwenden Sie "km" oder "KM" direkt nach der Zahl
2. **Tankstelle**: Beginnen Sie mit dem Markennamen, gefolgt von Ort
3. **Vollständigkeit**: Je mehr Informationen Sie angeben, desto besser die Erkennung
4. **Reihenfolge**: MARKE [PLZ] STADT [STRASSE] [HAUSNR]

### Beispiel für komplette Eingabe

```
1650km HEM 25436 Kummerfeld Hauptstraße 15
45.5L 1.599€/L 72.75€
```

Dies erkennt:
- Kilometerstand: 1650 km
- Tankstelle: HEM 25436 Kummerfeld Hauptstraße 15
- Liter: 45.5 L
- Preis: 1.599 €/L
- Gesamtkosten: 72.75 €

## Technische Implementation

Die Erkennung erfolgt durch reguläre Ausdrücke (Regex) in der Methode `_parse_refuel_text` in der Datei `telegram_refueling_handler.py`:

- **Kilometerstand-Erkennung**: Siehe Kommentare bei "Extract odometer"
- **Tankstellennamen-Erkennung**: Siehe Kommentare bei "Extract station name with enhanced pattern matching"

Alle Muster sind case-insensitive und unterstützen deutsche Umlaute (ä, ö, ü, ß).
