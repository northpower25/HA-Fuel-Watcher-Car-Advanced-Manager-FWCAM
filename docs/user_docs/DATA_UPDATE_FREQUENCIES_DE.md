# Datenaktualisierungsfrequenzen und Konfiguration

Dieses Dokument erklärt, wann und wie oft verschiedene Datentypen automatisch erfasst, berechnet oder aktualisiert werden in der haFWCMA-Integration, zusammen mit Konfigurationsoptionen und wichtigen Warnungen.

## Inhaltsverzeichnis

1. [Übersicht der Datenaktualisierung](#übersicht-der-datenaktualisierung)
2. [Automatische Aktualisierungen](#automatische-aktualisierungen)
3. [Manuelle Aktualisierungen](#manuelle-aktualisierungen)
4. [Konfigurationsoptionen](#konfigurationsoptionen)
5. [Wichtige Warnungen](#wichtige-warnungen)
6. [Historischer Datenimport](#historischer-datenimport)

---

## Übersicht der Datenaktualisierung

Die Integration sammelt und verarbeitet Daten aus mehreren Quellen:

- **Kraftstoffpreis-API** (Tankerkönig): Aktuelle Kraftstoffpreise von nahegelegenen Tankstellen
- **Fahrzeug-Entitäten**: Kilometerstand, Tankfüllstand, Reichweite und Position aus Ihrer Fahrzeugintegration
- **Berechnete Vorhersagen**: Verbrauchsprognosen und Tankempfehlungen
- **Historische Statistiken**: Durchschnittsverbrauch über verschiedene Zeiträume

Jede Datenquelle hat ihre eigene Aktualisierungsfrequenz, um Genauigkeit mit Systemleistung und API-Ratenlimits zu balancieren.

---

## Automatische Aktualisierungen

### 1. Kraftstoffpreis-API-Aktualisierungen

**Standardfrequenz:** Alle 15 Minuten  
**Konfigurierbarer Bereich:** 1-60 Minuten  
**Konfigurations-Entität:** `number.[fahrzeugname]_api_update_interval`

Die Integration fragt die Tankerkönig-API im konfigurierten Intervall nach aktuellen Kraftstoffpreisen ab. Um Ratenlimitierung zu vermeiden, wenn mehrere Home Assistant-Instanzen gleichzeitig auf die API zugreifen, wird jede Aktualisierung automatisch um ±2% des konfigurierten Intervalls randomisiert.

**Was wird aktualisiert:**
- Aktuelle Kraftstoffpreise bei nahegelegenen Tankstellen
- Tankstelleninformationen (Name, Adresse, Entfernung)
- Öffnungsstatus der Tankstellen
- Preistrends und Prognosen

**Aktualisierungs-Trigger:**
- Zeitbasiert: Alle X Minuten (konfiguriertes Intervall)
- Manuell: Über `switch.[fahrzeugname]_manual_refresh`
- Manuell: Über `button.[fahrzeugname]_test_api_connection`

### 2. Fahrzeugdaten-Aktualisierungen

**Frequenz:** Gleich wie Kraftstoffpreis-API-Aktualisierungen  
**Standard:** Alle 15 Minuten  
**Konfigurations-Entität:** `number.[fahrzeugname]_api_update_interval`

Fahrzeugdaten von Ihren konfigurierten Entitäten (Kilometerstand, Tankfüllstand, Reichweite, Position) werden im gleichen Intervall wie die Kraftstoffpreis-API abgerufen. Diese Daten werden verwendet um:
- Tankvorgänge zu erkennen
- Verbrauchsmuster zu verfolgen
- Fahrstatistiken zu berechnen

**Was wird aktualisiert:**
- Aktueller Kilometerstand
- Aktueller Tankfüllstand (Liter oder Prozent)
- Aktuelle geschätzte Reichweite
- Aktuelle Fahrzeugposition (wenn konfiguriert)

**Aktualisierungs-Trigger:**
- Zeitbasiert: Alle X Minuten (gleich wie API-Intervall)
- Manuell: Über `button.[fahrzeugname]_refresh_vehicle_data`
- Manuell: Über `switch.[fahrzeugname]_manual_refresh`

**Datenspeicherung:**
- Kilometerstände werden in Historie gespeichert (bis zu 1000 Einträge)
- Tankvorgänge werden automatisch erkannt und protokolliert (bis zu 100 Ereignisse)
- Alle Daten werden persistent in `.storage/hafwcma_<entry_id>.json` gespeichert

### 3. Verbrauchsprognose-Aktualisierungen

**Standardfrequenz:** Alle 6 Stunden  
**Konfigurierbarer Bereich:** 0,5-24 Stunden  
**Konfigurations-Entität:** `number.[fahrzeugname]_consumption_prediction_interval`

Die Verbrauchsprognose-Engine analysiert historische Fahrdaten um zu berechnen:
- Tage bis zum nächsten Tanken
- Durchschnittlich gefahrene Kilometer pro Tag
- Durchschnittliche Kraftstoffverbrauchsrate (L/100km)
- Vertrauensniveau der Vorhersagen

**Was wird berechnet:**
- `sensor.[fahrzeugname]_days_until_refuel` und seine Attribute
- Vorhersagedatenquelle (fallback_values, historical_data oder ml_enhanced)
- Vertrauenswert (0-1 Skala)

**Aktualisierungs-Trigger:**
- Zeitbasiert: Alle X Stunden (konfiguriertes Intervall)
- Manuell: Über `switch.[fahrzeugname]_manual_prediction`

**Datenanforderungen:**
Die Vorhersage-Engine benötigt eine Mindestanzahl an Datenpunkten, bevor sie von Fallback-Werten zu historischen Datenvorhersagen wechselt. Dies wird über `number.[fahrzeugname]_consumption_min_data_points` konfiguriert (Standard: 5).

**Vorhersagemodi:**
1. **Fallback-Werte** (data_points_used < Minimum):
   - Verwendet konfigurierte Standardwerte
   - Niedriges Vertrauen (typisch 0,3-0,5)
   - Attribut `data_points_percentage` zeigt Fortschritt zum Minimum

2. **Historische Daten** (ausreichend Datenpunkte):
   - Verwendet tatsächliche Fahrmuster
   - Höheres Vertrauen (0,6-0,8)
   - Basiert auf Ihren echten Verbrauchsdaten

3. **ML-Enhanced** (mit Mustererkennung):
   - Enthält Wochentag/Wochenende-Muster
   - Höchstes Vertrauen (0,7-0,9)
   - Berücksichtigt Trends und saisonale Variationen

### 4. Verbrauchshistorie-Berechnung

**Frequenz:** Bei jeder Koordinator-Aktualisierung  
**Standard:** Alle 15 Minuten (mit API/Fahrzeugdaten)

Historische Verbrauchsstatistiken werden jedes Mal neu berechnet, wenn neue Fahrzeugdaten abgerufen werden. Dies bietet Echtzeit-Updates für:
- `sensor.[fahrzeugname]_average_consumption_history` und seine Attribute

**Berechnete Zeiträume:**
- **Heute**: Verbrauch des aktuellen Tages (Mitternacht bis jetzt)
- **Letzte Woche**: Rollierender 7-Tage-Zeitraum
- **Letzte 14 Tage**: Rollierender 14-Tage-Zeitraum
- **Letzter Monat**: Rollierender 30-Tage-Zeitraum

**Datenquelle:**
Berechnungen basieren auf erkannten Tankvorgängen. Mindestens 2 Tankvorgänge innerhalb jedes Zeitraums sind erforderlich, um den Verbrauch zu berechnen (verbrauchter Kraftstoff zwischen Tankvorgängen geteilt durch gefahrene Strecke).

### 5. Verbrauchsprognose

**Frequenz:** Bei jeder Verbrauchsprognose-Aktualisierung  
**Standard:** Alle 6 Stunden

Der Prognose-Sensor liefert Vorhersagen für zukünftigen Verbrauch basierend auf erlernten Mustern. Derzeit gibt er die gleiche durchschnittliche Verbrauchsrate für alle Zeiträume zurück, mit geplanten Verbesserungen für zeitspezifische Prognosen.

**Was wird prognostiziert:**
- Erwarteter Verbrauch für morgen
- Durchschnittsverbrauch nächste Woche
- Durchschnittsverbrauch nächste 14 Tage
- Durchschnittsverbrauch nächster Monat

---

## Manuelle Aktualisierungen

### Buttons

#### 1. Test API Connection
**Entität:** `button.[fahrzeugname]_test_api_connection`

Testet die Tankerkönig-API-Verbindung und zeigt detaillierte Ergebnisse an:
- API-Antwortstatus
- Anzahl der gefundenen Tankstellen
- Nächste und günstigste Tankstelleninformationen
- Request/Response-Debugging-Informationen

**Verwenden wenn:**
- API-Schlüssel-Gültigkeit testen
- API-Verbindungsprobleme debuggen
- Tankstellensuche-Konfiguration verifizieren

#### 2. Import Historical Data
**Entität:** `button.[fahrzeugname]_import_historical_data`

Importiert historische Fahrzeugdaten aus der Home Assistant Recorder-Datenbank. Dies füllt auf:
- Kilometerstand-Historie (bis zu 90 Tage)
- Erkannte Tankvorgänge aus Tankfüllstand-Änderungen
- Verbrauchsberechnungen aus historischen Daten

**Verwenden wenn:**
- Ersteinrichtung für sofortige Vorhersagen
- Nach Änderung der Fahrzeug-Entitäten
- Um historische Daten nach Konfigurationsänderungen neu zu verarbeiten

**Hinweis:** Import läuft automatisch beim Integration-Start, kann aber manuell mit `force_reimport=True` erneut ausgelöst werden.

#### 3. Refresh Vehicle Data
**Entität:** `button.[fahrzeugname]_refresh_vehicle_data`

Ruft sofort aktuelle Daten von konfigurierten Fahrzeug-Entitäten ab und aktualisiert alle Sensoren.

**Verwenden wenn:**
- Sie sofortige Aktualisierung ohne Warten auf nächstes Intervall möchten
- Nach dem Tanken um das Ereignis sofort zu erkennen
- Entitäts-Konfiguration testen

### Switches

#### 1. Manual Refresh Switch
**Entität:** `switch.[fahrzeugname]_manual_refresh`

Löst vollständige Datenaktualisierung aus:
- Kraftstoffpreis-API-Aufruf
- Fahrzeugdaten-Abruf
- Alle Sensor-Aktualisierungen

Der Schalter schaltet sich automatisch nach Abschluss der Aktualisierung aus.

#### 2. Manual Prediction Switch
**Entität:** `switch.[fahrzeugname]_manual_prediction`

Löst sofortige Verbrauchsprognose-Berechnung mit aktuellen Daten aus. Nützlich für:
- Vorhersagegenauigkeit testen
- Vorhersage-Aktualisierung nach Konfigurationsänderungen erzwingen
- Sofortige Prognose nach Import historischer Daten erhalten

---

## Konfigurationsoptionen

### Aktualisierungsintervalle

#### API Update Interval
**Entität:** `number.[fahrzeugname]_api_update_interval`  
**Bereich:** 1-60 Minuten  
**Standard:** 15 Minuten

Steuert wie oft die Kraftstoffpreis-API aufgerufen und Fahrzeugdaten abgerufen werden.

**Überlegungen:**
- Niedrigere Werte (1-5 Min): Aktuellere Preise aber höhere API-Nutzung
- Höhere Werte (30-60 Min): Weniger API-Aufrufe aber seltenere Aktualisierungen
- Empfohlen: 10-20 Minuten für normale Nutzung

#### Consumption Prediction Interval
**Entität:** `number.[fahrzeugname]_consumption_prediction_interval`  
**Bereich:** 0,5-24 Stunden  
**Standard:** 6 Stunden

Steuert wie oft die Vorhersage-Engine Prognosen neu berechnet.

**Überlegungen:**
- Niedrigere Werte (0,5-2 Std): Reaktionsfähiger auf Änderungen aber höhere CPU-Auslastung
- Höhere Werte (12-24 Std): Seltenere Aktualisierungen aber niedrigere Systemlast
- Empfohlen: 6-12 Stunden für die meisten Benutzer

### Datenanforderungen

#### Minimum Data Points
**Entität:** `number.[fahrzeugname]_consumption_min_data_points`  
**Bereich:** 2-50 Punkte  
**Standard:** 5 Punkte

Mindestanzahl historischer Kilometerstand-Ablesungen erforderlich, bevor von Fallback-Werten zu historischen Datenvorhersagen gewechselt wird.

**Überlegungen:**
- Niedrigere Werte (2-3): Schnellerer Wechsel zum historischen Modus aber weniger genau
- Höhere Werte (10-20): Zuverlässigere Vorhersagen aber längere Wartezeit
- Empfohlen: 5-10 Punkte für ausgewogene Genauigkeit

---

## Wichtige Warnungen

### API-Ratenlimitierung

**Tankerkönig-API-Limits:**
- Die Tankerkönig-API hat Ratenlimits um Missbrauch zu verhindern
- Übermäßige API-Aufrufe können zu temporärer IP-Blockierung führen
- Die Integration beinhaltet automatische Randomisierung (±2%), um Last zu verteilen

**Best Practices:**
- Aktualisierungsintervall nicht unter 5 Minuten setzen, es sei denn notwendig
- Schnelle manuelle Aktualisierungen vermeiden
- Eine Instanz pro Standort ist ausreichend

**Anzeichen für Ratenlimitierung:**
- API-Anfragen schlagen mit HTTP 429-Fehlern fehl
- Leere Tankstellenlisten trotz gültiger Konfiguration
- Temporäre Unfähigkeit, Preise abzurufen

**Was zu tun ist:**
- Aktualisierungsintervall erhöhen
- 15-30 Minuten warten vor erneutem Versuch
- API-Nutzung in `sensor.[fahrzeugname]_api_debug` prüfen

### Systemlast

**CPU- und Speichernutzung:**
Die Integration führt verschiedene Berechnungen durch, die Systemressourcen verbrauchen:

**Leichte Operationen (häufig):**
- Abruf von Fahrzeug-Entitätszuständen: Minimale Auswirkung
- Speichern von Kilometerständen: Sehr geringe Auswirkung
- Preisvergleiche: Geringe Auswirkung

**Mittlere Operationen (periodisch):**
- Tankerkennung: Niedrig-mittlere Auswirkung
- Verbrauchshistorie-Berechnung: Mittlere Auswirkung (iteriert durch Ereignisse)
- API-Anfragen: Mittlere Auswirkung (Netzwerk-I/O)

**Schwere Operationen (selten):**
- Historischer Datenimport: Hohe Auswirkung initial (Datenbankabfragen)
- ML-verbesserte Vorhersagen: Mittel-hohe Auswirkung (Musteranalyse)
- Wochentag-Statistik-Neuberechnung: Mittlere Auswirkung

**Empfehlungen:**
- Standard-Intervalle für normale Nutzung beibehalten
- Manuellen Import nicht wiederholt ausführen
- Systemressourcen überwachen bei Low-Power-Geräten (Raspberry Pi)

### Datenbankwachstum

**Speicherüberlegungen:**
- Jeder Fahrzeugeintrag speichert bis zu 1000 Kilometerstand-Ablesungen
- Bis zu 100 Tankvorgänge pro Fahrzeug
- Preishistorie begrenzt auf 1000 Einträge
- Vorhersagehistorie für Genauigkeitsverfolgung

**Geschätzter Speicher:**
- Typische Nutzung: 100-500 KB pro Fahrzeug
- Mit voller Historie: Bis zu 2-5 MB pro Fahrzeug
- Speicherort: `.storage/hafwcma_<entry_id>.json`

**Automatische Bereinigung:**
Älteste Einträge werden automatisch entfernt, wenn Limits erreicht sind (FIFO - First In, First Out).

### Datengenauigkeit

**Vorhersagegenauigkeit hängt ab von:**
1. **Datenqualität**: Genaue Fahrzeug-Entitäten sind essentiell
2. **Fahrkonsistenz**: Regelmäßige Muster verbessern Vorhersagen
3. **Zeithorizont**: Vorhersagen sind genauer für nahe Zukunft
4. **Tankerkennung**: Tankfüllstand-Sensor muss ausreichende Auflösung haben

**Häufige Genauigkeitsprobleme:**
- Ungenaue Kilometerstand-Ablesungen → Falsche Verbrauchsberechnungen
- Fehlende Tankvorgänge → Lücken in Verbrauchshistorie
- Unregelmäßige Fahrmuster → Niedrigeres Vorhersagevertrauen
- Tankfüllstand-Sensor mit großen Schritten → Verpasste Tankvorgänge

**Genauigkeit verbessern:**
- Sicherstellen, dass Fahrzeug-Entitäten regelmäßig aktualisieren
- Hochauflösende Tankfüllstand-Sensoren verwenden (kontinuierliche Werte besser als Schritte)
- Zeit für Datensammlung lassen (mindestens 2-3 Tankvorgänge)
- `data_points_percentage`-Attribut prüfen um Fortschritt zu verfolgen

---

## Historischer Datenimport

### Automatischer Import

Beim ersten Start importiert die Integration automatisch historische Daten aus dem Home Assistant Recorder:

**Was wird importiert:**
- Kilometerstand-Ablesungen der letzten 90 Tage
- Tankfüllstand-Änderungen um vergangene Tankvorgänge zu erkennen
- Berechneter Verbrauch zwischen erkannten Tankvorgängen

**Voraussetzungen:**
- Home Assistant Recorder muss aktiviert sein
- Fahrzeug-Entitäten müssen historische Daten haben
- Kilometerstand- und Tankfüllstand-Entitäten müssen konfiguriert sein

**Import-Prozess:**
1. Wartet 10 Sekunden nach Integration-Start
2. Fragt Recorder nach historischen Zuständen ab
3. Verarbeitet Zustände in chronologischer Reihenfolge
4. Erkennt Tankvorgänge (Tankfüllstand-Erhöhungen > 5L)
5. Berechnet Verbrauch zwischen Tankvorgängen
6. Speichert verarbeitete Daten in Integration-Speicher

**Import-Ergebnisse:**
Prüfen Sie `button.[fahrzeugname]_import_historical_data` Attribute nach Start:
- `odometer_points_imported`: Anzahl historischer Kilometerstand-Ablesungen
- `refuel_events_detected`: Anzahl gefundener Tankvorgänge
- `date_range`: Importierter Zeitraum
- `imported`: Erfolgsstatus

### Manueller Import

Erzwingen Sie Neu-Import historischer Daten:

1. Drücken Sie `button.[fahrzeugname]_import_historical_data`
2. Warten Sie auf Abschluss (typisch 10-30 Sekunden)
3. Prüfen Sie Button-Attribute für Ergebnisse
4. Vorhersagen werden beim nächsten Vorhersageintervall aktualisiert

**Anwendungsfälle für manuellen Import:**
- Nach Änderung der Fahrzeug-Entitäts-Konfiguration
- Wenn automatischer Import beim Start fehlschlug
- Um Daten nach Behebung von Entitätsproblemen neu zu verarbeiten
- Testen mit verschiedenen Lookback-Zeiträumen

### Import-Performance

**Benötigte Zeit:**
- 10-30 Sekunden für 90 Tage Daten
- Abhängig von Datenbankgröße und Historievolumen
- Nicht-blockierende Operation (läuft im Hintergrund)

**Auswirkung:**
- Initialer Import: Mittlere Datenbanklast
- Nachfolgende Operationen: Minimale Auswirkung
- Import wird übersprungen wenn bereits abgeschlossen (außer bei Erzwingung)

### Import-Fehlerbehebung

**Keine Daten importiert:**
1. Prüfen Sie, dass Recorder in Home Assistant aktiviert ist
2. Verifizieren Sie, dass Fahrzeug-Entitäten historische Daten haben
3. Prüfen Sie, dass Entitäts-IDs korrekt konfiguriert sind
4. Überprüfen Sie Home Assistant Logs auf Fehler

**Weniger Ereignisse als erwartet:**
- Tankfüllstand-Sensor hat möglicherweise nicht ausreichende Auflösung
- Tankerkennungs-Schwellwert (5L) ist möglicherweise zu hoch für Ihr Fahrzeug
- Prüfen Sie auf Lücken in historischen Daten

**Falsche Verbrauchsberechnungen:**
- Verifizieren Sie, dass Kilometerstand-Ablesungen genau sind
- Prüfen Sie, dass Tankkapazität korrekt konfiguriert ist
- Stellen Sie sicher, dass Tankvorgänge Kilometerstand-Ablesungen haben
- Überprüfen Sie Tanklog auf Datenqualität

---

## Zusammenfassung

**Standardkonfiguration (Empfohlen für die meisten Benutzer):**
- API/Fahrzeug-Aktualisierungen: Alle 15 Minuten
- Vorhersage-Aktualisierungen: Alle 6 Stunden
- Minimale Datenpunkte: 5
- Historischer Import: Automatisch beim Start (90 Tage)

**Aggressive Konfiguration (Häufigere Aktualisierungen):**
- API/Fahrzeug-Aktualisierungen: Alle 5-10 Minuten
- Vorhersage-Aktualisierungen: Alle 2-4 Stunden
- Minimale Datenpunkte: 3
- ⚠️ Höhere API-Nutzung und Systemlast

**Konservative Konfiguration (Minimale Systemauswirkung):**
- API/Fahrzeug-Aktualisierungen: Alle 30-60 Minuten
- Vorhersage-Aktualisierungen: Alle 12-24 Stunden
- Minimale Datenpunkte: 10
- ⚠️ Weniger reaktiv auf Änderungen

**Überwachen Sie Ihr Setup:**
- Prüfen Sie `sensor.[fahrzeugname]_api_debug` für API-Status
- Überprüfen Sie `data_points_percentage` im Vorhersage-Sensor
- Beobachten Sie `data_points_used` um Lernfortschritt zu verfolgen
- Verwenden Sie `sensor.[fahrzeugname]_average_consumption_history` um Berechnungen zu verifizieren

**Fragen oder Probleme?**
- Siehe [TROUBLESHOOTING.md](TROUBLESHOOTING.md) für häufige Probleme
- Prüfen Sie [GitHub Issues](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)
