# Smart Confirmation Message Formatting

## Übersicht

Die Telegram-Bestätigungsnachrichten wurden verbessert, um klarer zu zeigen, was gerade erkannt wurde und was noch fehlt.

## Verbesserungen

### 1. Erkennungs-Highlight

**Neu:** Zeigt genau, was aus der letzten Eingabe erkannt wurde.

```
✅ Erkannt: 💰 1.599 €/L, 💵 62.84 €
```

Statt generisch:
```
✅ Daten aktualisiert!
```

### 2. Kompakte Darstellung fehlender Felder

**Vorher (mehrere Zeilen):**
```
❓ Fehlende Informationen:
KM-Stand, Preis pro Liter, Gesamtkosten, Tankstellenname

💡 Wie können Sie antworten:
• Antworten Sie mit 'Tankvorgang #17: <Ihre Daten>'
• Oder einfach: '45.5 L, 1.599 €/L, Shell'
• Senden Sie ein Foto der Quittung
• Senden Sie eine Sprachnachricht
• Nutzen Sie die Schaltflächen unten
```

**Nachher (eine Zeile):**
```
❓ Noch fehlend: KM-Stand, Tankstellenname

💡 Tipp: Einfach weitere Daten senden (z.B. '155000 km, Shell')
```

### 3. Bessere visuelle Hierarchie

Die Nachricht ist jetzt so strukturiert:

1. **Kopfzeile:** Tankvorgang-ID
2. **Status:** Was wurde gerade erkannt
3. **Aktuelle Daten:** Vollständige Übersicht
4. **Fehlende Felder:** Was noch benötigt wird (wenn vorhanden)
5. **Tipp:** Kurze Anleitung

## Beispiel-Ablauf

### Schritt 1: Initiale Benachrichtigung

```
⛽ Tankvorgang #17
Neuer Tankvorgang erkannt!

🕐 Zeitpunkt: 16.02.2026 19:37
📊 Menge: 39.30 Liter
⚡ Kraftstoffart: e10

❓ Noch fehlend: KM-Stand, Preis pro Liter, Gesamtkosten, Tankstellenname

💡 Tipp: Einfach weitere Daten senden (z.B. '155000 km, Shell')

[✅ Fertig] [✏️ Weiter bearbeiten]
[🗑️ Löschen]
```

### Schritt 2: Benutzer sendet "1,599"

**Eingabe:** `1,599`

**Erkannt:** 
- Preis pro Liter: 1.599 €/L
- Gesamtkosten: 62.84 € (automatisch berechnet)

**Antwort:**
```
⛽ Tankvorgang #17
✅ Erkannt: 💰 1.599 €/L, 💵 62.84 €

🕐 Zeitpunkt: 16.02.2026 19:37
📊 Menge: 39.30 Liter
💰 Preis/Liter: 1.599 €
💵 Gesamtkosten: 62.84 €
⚡ Kraftstoffart: e10

❓ Noch fehlend: KM-Stand, Tankstellenname

💡 Tipp: Einfach weitere Daten senden (z.B. '155000 km, Shell')

[✅ Fertig] [✏️ Weiter bearbeiten]
[🗑️ Löschen]
```

**Vorteile:**
- ✅ Klar sichtbar: "1.599" wurde als Preis erkannt
- ✅ Zeigt auch die automatische Berechnung (62.84 €)
- ✅ Fokus auf fehlende Felder (nur noch KM-Stand und Tankstelle)

### Schritt 3: Benutzer sendet "155000 km, Shell"

**Eingabe:** `155000 km, Shell`

**Erkannt:**
- KM-Stand: 155000 km
- Tankstelle: Shell

**Antwort:**
```
⛽ Tankvorgang #17
✅ Erkannt: 🔢 155000.0 km, 🏪 Shell

🕐 Zeitpunkt: 16.02.2026 19:37
📊 Menge: 39.30 Liter
🔢 KM-Stand: 155000.0 km
💰 Preis/Liter: 1.599 €
💵 Gesamtkosten: 62.84 €
⚡ Kraftstoffart: e10
🏪 Tankstelle: Shell

✅ Alle Daten vollständig!

[✅ Bestätigen] [✏️ Bearbeiten]
[🗑️ Löschen]
```

**Vorteile:**
- ✅ Zeigt genau, was aus "155000 km, Shell" extrahiert wurde
- ✅ Alle Daten sind jetzt vollständig
- ✅ Buttons ändern sich zu "Bestätigen" statt "Fertig"

## Technische Details

### Neue Parameter

Die Methode `_build_refuel_status_message` hat einen neuen optionalen Parameter:

```python
async def _build_refuel_status_message(
    self,
    refuel_id: int,
    refuel_data: dict[str, Any],
    is_update: bool = False,
    newly_recognized: dict[str, Any] | None = None,  # NEU
) -> tuple[str, list]:
```

### Integration

Wird automatisch von `_process_text_response` genutzt:

```python
message, inline_keyboard = await self._build_refuel_status_message(
    refuel_id, 
    refuel_data, 
    is_update=True, 
    newly_recognized=parsed_data  # Übergibt erkannte Daten
)
```

### Erkennungs-Logik

Für jedes Feld in `newly_recognized` wird geprüft, ob es einen Wert hat:

```python
if newly_recognized.get("liters_refueled"):
    recognized_items.append(f"📊 {newly_recognized['liters_refueled']:.2f} Liter")
if newly_recognized.get("price_per_liter"):
    recognized_items.append(f"💰 {newly_recognized['price_per_liter']:.3f} €/L")
# ... weitere Felder
```

Die erkannten Items werden dann in einer Zeile angezeigt:

```python
message_parts.append("<i>✅ <b>Erkannt:</b> " + ", ".join(recognized_items) + "</i>\n")
```

## Vorteile

### 1. Sofortiges Feedback

Der Benutzer sieht **sofort**, was aus seiner Eingabe erkannt wurde:
- ✅ Bestätigt die korrekte Erkennung
- ✅ Ermöglicht schnelle Korrektur bei Fehlern
- ✅ Zeigt auch automatische Berechnungen

### 2. Weniger visueller Lärm

**Vorher:** Lange Aufzählungsliste mit Anweisungen
**Nachher:** Kompakter Ein-Zeilen-Tipp

Spart Platz und ist übersichtlicher.

### 3. Fokus auf das Wesentliche

Die Nachricht zeigt:
1. Was **NEU** ist (gerade erkannt)
2. Was **VORHANDEN** ist (aktueller Stand)
3. Was **FEHLT** (noch zu ergänzen)

### 4. Intelligente Formatierung

- Bei **Updates:** Zeigt "✅ Erkannt: ..." mit neuen Feldern
- Bei **Vollständigkeit:** Zeigt "✅ Alle Daten vollständig!"
- Bei **Initial:** Zeigt "Neuer Tankvorgang erkannt!"

## Rückwärtskompatibilität

✅ **Keine Breaking Changes**
- Parameter `newly_recognized` ist optional
- Bestehende Aufrufe funktionieren weiterhin
- Initial-Benachrichtigungen unverändert

## Zusammenfassung

| Aspekt | Vorher | Nachher |
|--------|--------|---------|
| Status | "Daten aktualisiert!" | "✅ Erkannt: 💰 1.599 €/L, 💵 62.84 €" |
| Fehlende Felder | 6 Zeilen | 1 Zeile |
| Anleitung | 5 Bullet Points | 1 Zeile mit Beispiel |
| Übersichtlichkeit | Mittel | Hoch |
| Feedback-Qualität | Generisch | Spezifisch |

---

**Implementiert:** 2026-02-16  
**Version:** Smart Formatting v1.0  
**Status:** ✅ Produktiv
