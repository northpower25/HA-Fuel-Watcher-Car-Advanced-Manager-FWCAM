# Geolocation Feature - Quick Summary

## 📋 Was wurde erstellt? / What was created?

Es wurden zwei umfassende Konzeptdokumente erstellt:
- **Deutsch:** `docs/GEOLOCATION_CONCEPT.md`
- **English:** `docs/GEOLOCATION_CONCEPT_EN.md`

Two comprehensive concept documents were created:
- **German:** `docs/GEOLOCATION_CONCEPT.md`
- **English:** `docs/GEOLOCATION_CONCEPT_EN.md`

---

## 🎯 Kernfunktionalität / Core Functionality

### Was macht das Feature? / What does the feature do?

1. **Automatische Suche günstiger Tankstellen**
   - Findet die N günstigsten Tankstellen in konfigurierbarem Umkreis
   - Nutzt aktuelle Fahrzeugposition (GPS)
   - Berücksichtigt Kraftstofftyp (E5, E10, Diesel)

2. **Näherungserkennung**
   - Überwacht kontinuierlich Position
   - Erkennt wenn Fahrzeug sich günstiger Tankstelle nähert
   - Konfigurierbarer Schwellenwert (z.B. 1.5 km)

3. **Benachrichtigungen**
   - Schreibt Alert in dedizierte Entität
   - Nutzbar für Telegram, HA Companion App, etc.
   - Enthält: Name, Adresse, Preis, Entfernung, Navigations-Links

---

## 📊 Neue Entitäten / New Entities

### Sensor: Nearby Cheap Stations
```
sensor.{vehicle_name}_nearby_cheap_stations
```
- **State:** Anzahl gefundener günstiger Tankstellen
- **Attributes:** Liste mit Details (Name, Preis, Koordinaten, etc.)

### Binary Sensor: Proximity Alert
```
binary_sensor.{vehicle_name}_near_cheap_station
```
- **State:** `on` wenn in der Nähe, sonst `off`
- **Attributes:** Details zur nahegelegenen Tankstelle, fertige Alert-Nachricht

### Configuration Entities
```
number.{vehicle_name}_proximity_alert_distance     # 0.1-10 km, default: 1.5 km
number.{vehicle_name}_cheap_stations_count         # 1-20, default: 5
number.{vehicle_name}_cheap_stations_radius        # 1-50 km, default: 15 km
switch.{vehicle_name}_proximity_alerts             # Enable/Disable
```

---

## ✅ Analyse-Ergebnisse / Analysis Results

### Datenquellen / Data Sources

#### 1. GPS-Position ✅ GEEIGNET
- **Quelle:** device_tracker Entity (HA Companion App, OwnTracks, etc.)
- **Genauigkeit:** 5-30m (GPS-basiert) → **Ausreichend für Tankstellensuche**
- **Update-Frequenz:** 30-60s bei Bewegung → **Ausreichend für Fahrszenario**
- **Änderungen erforderlich:** ❌ Nein

#### 2. Tankstellendaten ✅ GEEIGNET MIT ANPASSUNGEN
- **Quelle:** Tankerkönig API (bereits implementiert)
- **Daten:** Name, Adresse, Koordinaten, Preise, Status
- **Strategie:** Zwei-Stufen-Ansatz
  - API-Update: Alle 10-15 Min (holt günstige Tankstellen)
  - Proximity-Check: Alle 30-60s (berechnet nur Distanz)
- **Performance:** ✅ Kein Problem, Distanzberechnung sehr schnell (< 1ms)

### Timing beim Fahren / Driving Timing

**Szenario:** 50 km/h Fahrt, 30s Update-Intervall
- Zurückgelegte Strecke: ~420 Meter
- Bei 1.5 km Schwellenwert: ~1-2 Minuten Reaktionszeit
- **Bewertung:** ✅ **Ausreichend**

---

## 🏗️ Implementierungs-Phasen / Implementation Phases

### Phase 1: MVP (Must-Have) ✅
**Aufwand:** ~20-30 Stunden
- ✅ Sensor für günstige Tankstellen
- ✅ Binary Sensor für Proximity Alert
- ✅ Konfigurierbare Number/Switch Entities
- ✅ Basis-Proximity-Logik mit Anti-Spam
- ✅ Dokumentation & Beispiel-Automationen

### Phase 2: Erweiterungen 🔶
**Aufwand:** ~15-20 Stunden
- 🔶 Tankstellenpräferenzen (Favoriten/Blacklist)
- 🔶 Reichweiten-Integration (nur tanken wenn nötig)
- 🔶 Preis-Trends pro Tankstelle
- 🔶 Adaptive Updates (basierend auf Geschwindigkeit)

### Phase 3: Advanced Features 🔮
**Später:**
- 🔮 Route-basierte Optimierung
- 🔮 ML-Preisprognosen pro Tankstelle
- 🔮 Geofencing / Zonen
- 🔮 Integration anderer Provider (international)

---

## 💡 Wichtige Design-Entscheidungen / Key Design Decisions

### 1. Zwei-Stufen-Update-Strategie
```
API-Update:        Alle 10-15 Minuten → Neue Tankstellenliste holen
Proximity-Check:   Alle 30-60 Sekunden → Nur Distanz berechnen
```
**Vorteil:** Respektiert API-Rate-Limits, trotzdem schnell genug für Fahrszenario

### 2. Anti-Spam-Mechanismus
```python
ALERT_COOLDOWN = 30 * 60  # 30 Minuten
HYSTERESIS_FACTOR = 1.3   # 30% mehr Distanz zum Deaktivieren
```
**Vorteil:** Verhindert nervige Mehrfach-Benachrichtigungen

### 3. Adaptive Updates (Phase 2)
```python
if vehicle_speed > 5 km/h:
    check_proximity_every(30 seconds)  # Fahrend
else:
    check_proximity_every(5 minutes)   # Stillstand
```
**Vorteil:** Schont Batterie bei Stillstand, schnell bei Fahrt

---

## 📝 Beispiel-Automation / Example Automation

```yaml
automation:
  - alias: "Günstige Tankstelle in der Nähe"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_near_cheap_station
        to: "on"
    condition:
      - condition: numeric_state
        entity_id: sensor.my_car_tank_level
        below: 30  # Nur bei Tank unter 30%
    action:
      - service: notify.telegram
        data:
          message: >
            {{ state_attr('binary_sensor.my_car_near_cheap_station', 'alert_message') }}
```

**Ergebnis / Result:**
```
🚗 Günstige Tankstelle in der Nähe!
📍 Shell Tankstelle (1.2 km entfernt)
💰 Preis: €1.589/L (E10)
🧭 Navigation: [Link]
```

---

## ⚠️ Risiken & Lösungen / Risks & Solutions

| Risiko                  | Lösung                                    | Status |
|-------------------------|-------------------------------------------|--------|
| API Rate Limits         | Zwei-Stufen-Update, Caching              | ✅     |
| Batterieverbrauch       | Adaptive Updates, Opt-in                  | ✅     |
| Spam-Benachrichtigungen | Cooldown + Hysterese                      | ✅     |
| Offline-Situationen     | Fallback auf Cache                        | ✅     |
| Datenschutz             | Alles lokal, Opt-in, Dokumentation        | ✅     |

---

## 🎯 Empfehlung / Recommendation

### ⭐ Start mit Phase 1 (MVP)

**Begründung:**
1. ✅ Liefert vollständige, nutzbare Lösung
2. ✅ Überschaubarer Aufwand (~20-30h)
3. ✅ Solide Basis für zukünftige Erweiterungen
4. ✅ Professioneller Release möglich

**Nicht empfohlen:**
- ❌ Nur Teil-Features (wäre unbefriedigend)
- ❌ Direkt mit Phase 2 starten (zu komplex ohne Basis)

---

## 📚 Nächste Schritte / Next Steps

1. ✅ **Konzept reviewen** ← **DU BIST HIER / YOU ARE HERE**
2. ⬜ **Feedback geben & Freigabe erteilen**
3. ⬜ **Technisches Design erstellen**
   - Detaillierte Klassendiagramme
   - API-Spezifikationen
4. ⬜ **Prototyp entwickeln**
5. ⬜ **MVP implementieren**
6. ⬜ **Testen & Dokumentieren**
7. ⬜ **Release**

---

## 📖 Vollständige Dokumentation / Full Documentation

Für alle Details siehe / For all details see:
- **Deutsch:** `docs/GEOLOCATION_CONCEPT.md` (41 Seiten)
- **English:** `docs/GEOLOCATION_CONCEPT_EN.md` (37 pages)

Enthalten / Includes:
- ✅ Detaillierte Anforderungen
- ✅ Technische Architektur
- ✅ Datenfluss-Diagramme
- ✅ Datenquellen-Analyse (GPS, API)
- ✅ Genauigkeit vs. Schnelligkeit-Analyse
- ✅ Implementierungsvorschlag
- ✅ Zusätzliche Feature-Ideen (6+)
- ✅ Risiko-Analyse
- ✅ MVP-Definition mit Zeitschätzung
- ✅ Entscheidungsmatrix
- ✅ Offene Fragen
- ✅ Zusammenfassung & Empfehlung

---

## ❓ Fragen? / Questions?

**Bitte prüfen Sie die vollständigen Konzeptdokumente und geben Sie Feedback:**
1. Sind die vorgeschlagenen Entitäten sinnvoll?
2. Ist die Zwei-Stufen-Update-Strategie akzeptabel?
3. Passen die Default-Werte (5 Tankstellen, 15 km Radius, 1.5 km Schwellenwert)?
4. Soll das Feature opt-in oder opt-out sein?
5. Welche Phase-2-Features sind am wichtigsten?

**Please review the complete concept documents and provide feedback:**
1. Are the proposed entities sensible?
2. Is the two-tier update strategy acceptable?
3. Do the default values fit (5 stations, 15 km radius, 1.5 km threshold)?
4. Should the feature be opt-in or opt-out?
5. Which Phase 2 features are most important?

---

**Bereit für Implementierung nach Ihrer Freigabe! / Ready for implementation after your approval!** 🚀
