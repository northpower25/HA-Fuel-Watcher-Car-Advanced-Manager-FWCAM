# Fahrtenbuch-Implementierung - Zusammenfassung

**Status:** Konzeptphase abgeschlossen  
**Datum:** 13.02.2026

---

## Überblick

Dieses Dokument bietet eine schnelle Übersicht über das umfassende Fahrtenbuch-Konzept für haFWCMA. Für vollständige Details siehe [TRIP_TRACKING_CONCEPT.md](TRIP_TRACKING_CONCEPT.md).

---

## Kernfunktionen

### 1. Automatische Fahrterkennung ✅
- Erkennt Fahrtbeginn/-ende basierend auf Fahrzeugbewegung
- Minimale Fahrstrecke: 0,5 km (konfigurierbar)
- Zusammenführungs-Zeitfenster für Kurzstopps: 5 Minuten
- Erfasst: Distanz, Zeitstempel, Kilometer, Kraftstoffverbrauch

### 2. Kostenanalyse 💰
- **Echte Kosten:** Basierend auf tatsächlichem Kraftstoffverbrauch
- **Kilometerpauschale:** Deutsche Steuersätze (0,30 €/km, 0,38 €/km ab 21. km)
- **Vergleich:** Zeigt Ersparnis/Mehrkosten
- Zusatzkosten-Erfassung (Maut, Parkgebühren)

### 3. Datenschutz & Anonymisierung 🔒
- **Opt-In standardmäßig** mit Datenschutzhinweis
- Zeitbasierte Anonymisierung (z.B. Pendelzeiten)
- Konfigurierbare Datenaufbewahrung (30-365 Tage)
- DSGVO-konform gestaltet
- Nur lokale Speicherung

### 4. Pattern-Erkennung 🎯
- Automatische Erkennung regelmäßiger Routen (Zuhause ↔ Arbeit)
- Nutzerbestätigung erforderlich vor Pattern-Aktivierung
- Unterstützt anonymisierte Patterns
- Kategorien: Geschäftlich, Privat, Pendeln
- Automatische Zuordnung bei zukünftigen Fahrten

### 5. Standortverwaltung 📍
- GPS-Koordinaten-Erfassung
- Automatische Adressauflösung (OpenStreetMap Nominatim)
- Editierbare Adressen
- POI (Point of Interest) Verwaltung
- Integration mit Zuhause/Arbeit/Tankstellen

### 6. Lovelace-Karten-Integration 📊
- Neue Registerkarte "Fahrtenbuch" in bestehender FWCAM-Karte
- Fahrten-Tabelle mit Sortierung, Filterung, Paginierung
- Fahrten-Bearbeitungsdialog
- Pattern-Verwaltungsdialog
- Statistik-Dashboard
- CSV-Export für Steuerzwecke

---

## Datenmodell

### Fahrt-Objekt
```python
- trip_id: Eindeutige Kennung
- timestamps: Start- und Endzeit
- distance_km: Zurückgelegte Distanz
- odometer_start/end: Kilometerstände
- fuel_level_start/end: Tankfüllstände
- fuel_consumed: Verbrauchte Liter
- start/end_latitude/longitude: GPS (nullable)
- start/end_address: Aufgelöste Adressen (nullable)
- fuel_cost: Echte Kraftstoffkosten
- tax_mileage_amount: Kilometerpauschalen-Berechnung
- purpose: Fahrtzweck (Text)
- category: geschäftlich/privat/pendeln
- pattern_id: Zugeordnetes Pattern (falls vorhanden)
- is_anonymized: Datenschutz-Flag
```

### Fahrt-Pattern-Objekt
```python
- pattern_id: Eindeutige Kennung
- name: Pattern-Name (z.B. "Arbeitsweg")
- start/end_coordinates: GPS mit Radius
- weekdays: [0-6] oder None
- time_window: Optionale Zeitbeschränkungen
- category: geschäftlich/privat/pendeln
- is_anonymized: Treffer automatisch anonymisieren
- statistics: Ø Distanz, Dauer, Verbrauch
```

### Point-of-Interest-Objekt
```python
- poi_id: Eindeutige Kennung
- name: POI-Name
- latitude/longitude: GPS-Koordinaten
- radius_m: Erkennungsradius
- poi_type: zuhause/arbeit/tankstelle/geschäft/parkplatz/custom
- visit_count: Statistiken
```

---

## Speicherung

### Erweitertes Speicherschema
```python
data = {
    # ... bestehende Felder ...
    "trips": [],  # Liste von Fahrt-Objekten
    "trip_patterns": [],  # Liste von Pattern-Objekten
    "pois": [],  # Liste von POI-Objekten
    "trip_tracking_config": {
        "enabled": False,
        "min_trip_distance_km": 0.5,
        "retention_days": 365,
        "tax_mileage_rate_default": 0.30,
        "anonymization_schedules": [],
    },
    "trip_statistics": {
        "total_trips": 0,
        "total_distance_km": 0,
        "total_fuel_consumed": 0,
        # ...
    },
}
```

### Speicherbedarf
- ~2 KB pro Fahrt
- Bei 2 Fahrten/Tag = ~1,5 MB pro Jahr
- Akzeptabel für `.storage`-Dateien
- Automatische Bereinigung basierend auf Aufbewahrungsrichtlinie

---

## Neue Entitäten

### 1. Switch
```yaml
switch.{vehicle_name}_trip_tracking_enabled:
  state: off  # Standard (Opt-In)
  attributes:
    privacy_notice_accepted: false
    total_trips: 0
```

### 2. Sensoren
```yaml
sensor.{vehicle_name}_trip_log:
  state: 730  # Gesamt-Fahrten
  attributes:
    trips: [...]  # Letzte Fahrten
    statistics: {...}

sensor.{vehicle_name}_current_trip:
  state: "in_progress"  # oder "idle"
  attributes:
    started_at: "..."
    distance_so_far: 5.3
```

### 3. Binärsensor
```yaml
binary_sensor.{vehicle_name}_on_trip:
  state: on  # Aktuell auf Fahrt
  device_class: moving
```

---

## Dienste (Services)

1. **hafwcma.add_trip** - Fahrt manuell hinzufügen
2. **hafwcma.edit_trip** - Bestehende Fahrt bearbeiten
3. **hafwcma.delete_trip** - Fahrt löschen
4. **hafwcma.create_pattern** - Fahrt-Pattern erstellen
5. **hafwcma.export_trips** - Nach CSV/JSON exportieren

---

## Implementierungsplan

### Phase 1: Grundfunktionalität (Priorität: HOCH)
- Fahrterkennungslogik
- Fahrt-Datenmodell
- Speichererweiterung
- Switch-Entität
- Datenschutzhinweis
- Grundlegende Aufzeichnung

### Phase 2: Kostenberechnung (Priorität: HOCH)
- Kraftstoffverbrauchs-Berechnung
- Kilometerpauschalen-Konfiguration
- Kostenvergleich

### Phase 3: Geocoding (Priorität: HOCH)
- OSM Nominatim Integration
- Adressauflösung
- Caching und Rate-Limiting

### Phase 4: Pattern-Erkennung (Priorität: MITTEL)
- Pattern-Datenmodell
- Matching-Algorithmus
- Pattern-Erstellung und -Anwendung

### Phase 5: POI-Verwaltung (Priorität: MITTEL)
- POI-Datenmodell
- Erkennungslogik
- Zuhause/Arbeit-Auto-Erkennung

### Phase 6: Anonymisierung (Priorität: MITTEL)
- Zeitbasierte Anonymisierungsregeln
- Anwendungslogik
- Datenaufbewahrungs-Bereinigung

### Phase 7: Lovelace-Karte (Priorität: NIEDRIG)
- Fahrtenbuch-Registerkarte
- Fahrten-Tabelle und Dialoge
- Pattern/POI-Verwaltungs-UI
- Export-Funktionalität

### Phase 8: Dienste (Priorität: NIEDRIG)
- Service-Implementierungen
- Home Assistant Integration

### Phase 9: Tests & Dokumentation (Priorität: FORTLAUFEND)
- Unit-Tests
- Integrationstests
- Benutzerdokumentation
- Datenschutz-Leitfaden

---

## Technische Architektur

### Fahrterkennung
Basierend auf bestehender `VehicleDataTracker`-Architektur:
- Überwacht Kilometerstand- und Positionsänderungen
- Erkennt Start: Fahrzeug beginnt sich zu bewegen
- Erkennt Ende: Fahrzeug stationär für Zusammenführungs-Zeitfenster
- Ähnlich wie Tankvorgang-Erkennungs-Pattern

### Geocoding
- OpenStreetMap Nominatim API (kostenlos)
- Rate-Limiting: 1 Anfrage/Sekunde
- Ergebnis-Caching
- User-Agent: "Home Assistant haFWCMA/1.0"

### Pattern-Matching
1. Prüft Standort-Übereinstimmung (Start/Ende innerhalb Radius)
2. Prüft Zeitbeschränkungen (Wochentag, Zeitfenster)
3. Prüft Distanz-Toleranz (±10%)
4. Wendet Pattern-Attribute automatisch an

---

## Datenschutz & DSGVO

### Opt-In-Design
- Fahrtenbuch standardmäßig deaktiviert
- Expliziter Datenschutzhinweis erforderlich
- Nutzer muss Bedingungen akzeptieren

### Datenschutzhinweis-Inhalt
- Welche Daten erfasst werden (GPS, Zeitstempel, Adressen)
- Verantwortung des Halters, Fahrzeugnutzer zu informieren
- DSGVO-Konformitäts-Anforderungen
- Garantie für lokale Speicherung

### Anonymisierungs-Features
- Zeitbasierte Regeln (z.B. "Mo-Fr 08:00-09:00")
- Keine GPS-Koordinaten für anonymisierte Fahrten gespeichert
- Pattern-basierte Anonymisierung
- Konfigurierbare Aufbewahrungsfristen

### DSGVO-Rechte
- ✅ Informationsrecht (Datenschutzhinweis)
- ✅ Auskunftsrecht (alle Fahrten ansehen)
- ✅ Recht auf Löschung (Fahrten löschen/Feature deaktivieren)
- ✅ Recht auf Datenübertragbarkeit (Export-Funktion)
- ✅ Datenminimierung (Anonymisierung)
- ✅ Speicherbegrenzung (Aufbewahrungsfristen)

---

## Zusätzliche Feature-Ideen

### Statistiken & Reports
- Monatliche/Jährliche Zusammenfassungen
- Verbrauchstrends
- Kostentrends
- Top-Routen
- ELSTER-kompatibler Export (Deutsche Steuererklärung)

### Automatisierungen
- Benachrichtigung für unkategorisierte Fahrten
- Monatliche Überprüfungs-Erinnerung
- Automatisches Backup
- Hohe-Verbrauchs-Warnungen

### Machine Learning
- Fahrt-Vorhersage
- Automatische Zweck-Zuordnung
- Verbrauchs-Vorhersage
- Anomalie-Erkennung

### Integrationen
- Home Assistant Kalender
- Google Kalender
- Wetterdaten (Verbrauchseinfluss)
- Pay2Park (zukünftig)

---

## Limitationen

### Technisch
- Abhängig von GPS-Genauigkeit
- Benötigt häufige Kilometerstand-Updates (< 5 Min)
- Geocoding benötigt Internet
- Performance mit >10.000 Fahrten

### Datenschutz
- DSGVO-Konformitäts-Verantwortung beim Nutzer
- Geocoding-Anfragen an externen Dienst (OSM)
- Backup-Sicherheit muss vom Nutzer gewährleistet werden

### Nicht Implementiert
- Echtzeit-Navigation
- Routen-Optimierung
- Integration mit externen Fahrtenbuch-Apps
- Automatische Steuererklärung-Erstellung

---

## Nächste Schritte

1. ✅ **Konzept-Review** - Dieses Konzeptdokument überprüfen
2. ⏳ **Feature-Priorisierung** - Entscheiden, welche Features zuerst implementiert werden
3. ⏳ **Phase 1 Freigabe** - Freigabe für Start der Phase 1 Implementierung
4. ⏳ **Technische Spezifikation** - Detaillierte Spezifikationen für Phase 1
5. ⏳ **Implementierung** - Entwicklung beginnen

---

## Fragen zur Überprüfung

1. Soll die automatische Pattern-Erkennung Opt-In oder Opt-Out sein?
2. Wie sollen mehrere Zwischenstopps behandelt werden (Trip-Chaining)?
3. Soll es eine Apple CarPlay/Android Auto Integration geben?
4. Wie detailliert sollen Steuer-Export-Formate sein?
5. Sollen Fahrten nachträglich teilbar/zusammenführbar sein?

---

## Erstellte Dateien

- `/docs/TRIP_TRACKING_CONCEPT.md` - Vollständiges Konzeptdokument (DE/EN, 1200+ Zeilen)
- `/docs/TRIP_TRACKING_IMPLEMENTATION_SUMMARY.md` - Englische Zusammenfassung
- `/docs/TRIP_TRACKING_IMPLEMENTATION_SUMMARY_DE.md` - Dieses deutsche Zusammenfassungsdokument

---

## Geschätzter Aufwand

| Phase | Aufwand | Abhängigkeiten |
|-------|---------|----------------|
| Phase 1 | 3-4 Tage | Keine |
| Phase 2 | 1-2 Tage | Phase 1 |
| Phase 3 | 2-3 Tage | Phase 1 |
| Phase 4 | 3-4 Tage | Phase 1, 3 |
| Phase 5 | 2-3 Tage | Phase 3 |
| Phase 6 | 2-3 Tage | Phase 1, 4 |
| Phase 7 | 5-7 Tage | Alle vorherigen |
| Phase 8 | 2-3 Tage | Phase 1-6 |
| Phase 9 | Fortlaufend | Alle Phasen |

**Gesamtschätzung: 20-30 Arbeitstage** für vollständige Implementierung

---

## Fazit

Das Fahrtenbuch-Feature wird die Fähigkeiten von haFWCMA erheblich erweitern, indem es umfassende Logbook-Funktionalität hinzufügt. Das Design priorisiert:

- ✅ **Datenschutz** - Opt-In, Anonymisierung, lokale Speicherung
- ✅ **Automatisierung** - Automatische Erkennung und Pattern-Erkennung
- ✅ **Kostenanalyse** - Echte Kosten vs. Kilometerpauschalen
- ✅ **Benutzerfreundlichkeit** - Integration in bestehende Karte
- ✅ **DSGVO-Konformität** - Vollständige Unterstützung der Datenschutzrechte

Der phasenweise Implementierungsansatz ermöglicht inkrementelle Entwicklung und Tests, wobei die kritischsten Features (Fahrterkennung, Kostenberechnung, Geocoding) in den Phasen 1-3 priorisiert werden.

---

**Für vollständige Details siehe:** [TRIP_TRACKING_CONCEPT.md](TRIP_TRACKING_CONCEPT.md)
