# Enhanced Price Parsing - Verbesserte Preis-Erkennung

## Übersicht

Die Telegram-Refueling-Integration unterstützt jetzt intelligente Preis-Erkennung mit deutscher Zahlenformatierung und automatischen Berechnungen.

## Neue Funktionen

### 1. Komma als Dezimaltrenner

✅ **Alle Zahlenformate werden akzeptiert:**
- `1,599` (deutsche Schreibweise)
- `1.599` (internationale Schreibweise)
- Beide Formate funktionieren für alle Werte (Liter, Preis, Gesamtkosten)

### 2. Intelligente Preis-Erkennung

#### Automatische €/L Erkennung

Zahlen im Bereich **1,0 - 3,0** werden automatisch als Literpreise erkannt:

```
Eingabe: "1,599"
Erkennung: price_per_liter = 1.599 €/L
```

```
Eingabe: "45 L, 1,849"
Erkennung: 
  liters_refueled = 45 L
  price_per_liter = 1.849 €/L
  total_cost = 83.21 € (berechnet)
```

**Keine explizite Angabe von €/L oder eur/l nötig!**

#### Automatische Gesamtkosten-Erkennung

Zahlen im Bereich **20 - 99** (oder 10-99 mit Dezimalstellen) werden automatisch als Gesamtkosten erkannt:

```
Eingabe: "20"
Erkennung: total_cost = 20.00 €
```

```
Eingabe: "71,96"
Erkennung: total_cost = 71.96 €
```

```
Eingabe: "21,50 €"
Erkennung: total_cost = 21.50 €
```

### 3. Flexible Liter-Angaben

Alle folgenden Formate werden erkannt:

```
"20 L" → 20 Liter
"20l" → 20 Liter
"20 Liter" → 20 Liter
"20,5 L" → 20.5 Liter
"20.5 L" → 20.5 Liter
```

### 4. Flexible Währungsangaben

Gesamtkosten können mit verschiedenen Suffixen angegeben werden:

```
"20eur" → 20.00 €
"20 €" → 20.00 €
"20 EUR" → 20.00 €
"20euro" → 20.00 €
"71,96 €" → 71.96 €
```

### 5. Automatische Berechnungen

#### Berechnung Preis pro Liter

Wenn Gesamtkosten und Liter angegeben sind, wird der Literpreis berechnet:

```
Eingabe: "50 L, 71,96 €"
Erkennung:
  liters_refueled = 50 L
  total_cost = 71.96 €
  price_per_liter = 1.439 €/L (berechnet)
```

**Formel:** `price_per_liter = total_cost ÷ liters_refueled`

**Sicherheitsprüfung:** Berechneter Preis muss zwischen 1,0 und 3,0 €/L liegen

#### Berechnung Gesamtkosten

Wenn Literpreis und Liter angegeben sind, werden die Gesamtkosten berechnet:

```
Eingabe: "45,5 L, 1,599"
Erkennung:
  liters_refueled = 45.5 L
  price_per_liter = 1.599 €/L
  total_cost = 72.75 € (berechnet)
```

**Formel:** `total_cost = price_per_liter × liters_refueled`

## Beispiel-Dialoge

### Beispiel 1: Minimale Eingabe mit deutscher Formatierung

```
⛽ Tankvorgang #17
Neuer Tankvorgang erkannt!
📊 Menge: 39.30 Liter
❓ Fehlende Informationen: KM-Stand, Preis, Tankstelle
```

**Benutzer:** `1,599`

```
⛽ Tankvorgang #17
✅ Daten aktualisiert!
📊 Menge: 39.30 Liter
💰 Preis/Liter: 1.599 €
💵 Gesamtkosten: 62.84 € (berechnet)
❓ Fehlende Informationen: KM-Stand, Tankstelle
```

### Beispiel 2: Gesamtbetrag ohne Währung

```
⛽ Tankvorgang #18
Neuer Tankvorgang erkannt!
📊 Menge: 50.0 Liter
❓ Fehlende Informationen: KM-Stand, Preis, Tankstelle
```

**Benutzer:** `71,96`

```
⛽ Tankvorgang #18
✅ Daten aktualisiert!
📊 Menge: 50.0 Liter
💰 Preis/Liter: 1.439 € (berechnet)
💵 Gesamtkosten: 71.96 €
❓ Fehlende Informationen: KM-Stand, Tankstelle
```

### Beispiel 3: Liter und Preis ohne Einheiten

```
⛽ Tankvorgang #19
Neuer Tankvorgang erkannt!
❓ Fehlende Informationen: Menge, Preis, KM-Stand, Tankstelle
```

**Benutzer:** `45 L, 1,849`

```
⛽ Tankvorgang #19
✅ Daten aktualisiert!
📊 Menge: 45.0 Liter
💰 Preis/Liter: 1.849 €
💵 Gesamtkosten: 83.21 € (berechnet)
❓ Fehlende Informationen: KM-Stand, Tankstelle
```

### Beispiel 4: Komplett mit Tankstelle

```
⛽ Tankvorgang #20
Neuer Tankvorgang erkannt!
❓ Fehlende Informationen: Menge, Preis, KM-Stand, Tankstelle
```

**Benutzer:** `50l, 1,599, Shell`

```
⛽ Tankvorgang #20
✅ Daten aktualisiert!
📊 Menge: 50.0 Liter
💰 Preis/Liter: 1.599 €
💵 Gesamtkosten: 79.95 € (berechnet)
🏪 Tankstelle: Shell
❓ Fehlende Informationen: KM-Stand
```

✅ **Shell wurde automatisch zum POI-Cache hinzugefügt**

## POI-Integration (Tankstellen-Cache)

### Automatisches Speichern

Wenn ein Tankstellenname erkannt wird, wird die Tankstelle automatisch zum POI-Cache (Points of Interest) hinzugefügt:

```
Eingabe: "Shell Tankstelle, 45 L, 1,599"
→ Tankstelle "Shell" wird zum POI-Cache hinzugefügt
→ Typ: gas_station (Tankstelle)
→ Icon: mdi:gas-station
```

### Vorteile der POI-Integration

1. **Trip-Tracking:** Tankstellen werden in Fahrten erkannt
2. **Statistiken:** Häufigkeit der Besuche wird gezählt
3. **Wiederverwendung:** Namen stehen für zukünftige Eingaben zur Verfügung
4. **Automatische Vervollständigung:** Kann für Vorschläge genutzt werden

### Duplikat-Vermeidung

Die Integration prüft automatisch:
- ✅ Existiert bereits eine Tankstelle mit diesem Namen?
- ✅ Existiert bereits ein POI an dieser Position? (wenn Koordinaten vorhanden)
- ✅ Keine doppelten Einträge

### Gespeicherte POI-Daten

Für jede Tankstelle wird gespeichert:
```json
{
  "name": "Shell",
  "poi_type": "gas_station",
  "icon": "mdi:gas-station",
  "address": "Optional: Adresse wenn vorhanden",
  "latitude": "Optional: Wenn bekannt",
  "longitude": "Optional: Wenn bekannt",
  "radius_m": 200.0,
  "visit_count": 0,
  "notes": "Auto-added from refueling data"
}
```

## Erkennungs-Prioritäten

Die Erkennung folgt dieser Priorität:

### 1. Explizite Angaben (Höchste Priorität)

```
"1,599 €/L" → Immer als Literpreis erkannt
"Gesamt: 71,96" → Immer als Gesamtkosten erkannt
"Preis: 1,849" → Immer als Literpreis erkannt
```

### 2. Intelligente Erkennung (Wenn keine explizite Angabe)

```
"1,599" → Als Literpreis erkannt (1,0 - 3,0 Bereich)
"71,96" → Als Gesamtkosten erkannt (20-200 Bereich)
"45 L" → Als Liter erkannt
```

### 3. Doppel-Erkennung vermeiden

```
"1,599" → Wird NUR EINMAL verwendet
- Entweder als Literpreis ODER
- Als Gesamtkosten ODER  
- Als Liter
Aber niemals für mehrere Werte gleichzeitig
```

## Sicherheitsprüfungen

### Literpreis-Validierung

- **Minimum:** 1,0 €/L
- **Maximum:** 3,0 €/L
- **Grund:** Typischer Bereich für Kraftstoffpreise

### Gesamtkosten-Validierung

- **Minimum:** 10,00 €
- **Maximum:** 200,00 €
- **Grund:** Typischer Bereich für Tankfüllungen

### Berechnungs-Validierung

Berechnete Werte werden auf Plausibilität geprüft:
- Berechneter Literpreis muss im Bereich 1,0 - 3,0 €/L liegen
- Keine Division durch Null
- Keine negativen Werte

## Rückwärtskompatibilität

✅ **Alle bisherigen Formate funktionieren weiterhin:**

```
"45.5 L, 1.599 €/L" → Funktioniert
"45,5 Liter, 1,599 €/Liter" → Funktioniert
"Gesamt: 71,96 €" → Funktioniert
"Total: 71.96 EUR" → Funktioniert
"Preis: 1,849" → Funktioniert
```

✅ **Keine Breaking Changes:**
- Explizite Formate haben Priorität
- Intelligente Erkennung nur als Fallback
- Alle ursprünglichen Patterns bleiben erhalten

## Debug-Logging

Alle Erkennungen werden geloggt:

```
DEBUG: Extracted liters: 45.5
DEBUG: Extracted price/liter (smart detection): 1.599
DEBUG: Calculated total cost: 72.75 (from price 1.599 * liters 45.500)
DEBUG: Parsed data from text: {'liters_refueled': 45.5, 'price_per_liter': 1.599, 'total_cost': 72.75}
INFO: Added gas station 'Shell' to POI cache (ID: 42)
```

## Fehlerbehandlung

### Ungültige Eingaben werden ignoriert

```
Eingabe: "abc"
Erkennung: {} (leer)
→ Keine Fehlermeldung, einfach keine Daten erkannt
```

### Unplausible Werte werden gefiltert

```
Eingabe: "5,999" (zu hoch für Literpreis)
Erkennung: Als Gesamtkosten NICHT erkannt (zu niedrig)
→ Ignoriert, keine Erkennung
```

### POI-Fehler werden geloggt

```
POI-Speicherung fehlgeschlagen
→ Warnung im Log
→ Hauptfunktion läuft weiter
→ Kein Abbruch der Verarbeitung
```

## Zusammenfassung

### Unterstützte Eingabe-Formate

| Eingabe | Erkannt als | Wert |
|---------|-------------|------|
| `1,599` | Literpreis | 1.599 €/L |
| `1.599` | Literpreis | 1.599 €/L |
| `71,96` | Gesamtkosten | 71.96 € |
| `20` | Gesamtkosten | 20.00 € |
| `20 L` | Liter | 20.0 L |
| `20l` | Liter | 20.0 L |
| `20eur` | Gesamtkosten | 20.00 € |
| `20 €` | Gesamtkosten | 20.00 € |
| `1,599 €/L` | Literpreis (explizit) | 1.599 €/L |
| `Shell` | Tankstelle | Shell |

### Automatische Berechnungen

| Gegeben | Berechnet | Formel |
|---------|-----------|--------|
| Liter + Gesamtkosten | Literpreis | total ÷ liters |
| Liter + Literpreis | Gesamtkosten | price × liters |

### POI-Integration

| Aktion | Ergebnis |
|--------|----------|
| Tankstelle erkannt | Automatisch zu POI-Cache hinzugefügt |
| Duplikat | Wird NICHT doppelt hinzugefügt |
| Fehler | Warnung im Log, Hauptfunktion läuft weiter |

---

**Implementiert:** 2026-02-16  
**Version:** Enhanced Parsing v2.0  
**Status:** ✅ Produktiv
