# Traccar-Integrations-Anleitung

**Verbindung Traccar ↔ haFWCMA ↔ Freematics ONE+**

---

## 📑 Inhaltsverzeichnis

1. [Was ist Traccar?](#1-was-ist-traccar)
2. [Warum Traccar?](#2-warum-traccar)
3. [Installationsoptionen](#3-installationsoptionen)
4. [Home Assistant Add-on-Einrichtung (Empfohlen)](#4-home-assistant-add-on-einrichtung-empfohlen)
5. [Traccar-Web-Oberfläche](#5-traccar-web-oberfläche)
6. [Erweiterte Traccar-Konfiguration](#6-erweiterte-traccar-konfiguration)
7. [Netzwerkkonfiguration](#7-netzwerkkonfiguration)
8. [haFWCMA mit Traccar verbinden](#8-hafwcma-mit-traccar-verbinden)
9. [Überwachung & Alarme](#9-überwachung--alarme)
10. [Fehlerbehebung bei Traccar](#10-fehlerbehebung-bei-traccar)

---

## 1. Was ist Traccar?

**Traccar** ist eine kostenlose Open-Source-GPS-Tracking-Plattform, die Standortdaten von
Hunderten verschiedener GPS-Gerätetypen empfangen kann.  Für die Integration des Freematics
ONE+ mit haFWCMA dient es als **zentraler Relay-Server**:

```
Freematics ONE+ ──► Traccar (GPS-Relay) ──► haFWCMA (verarbeitet Daten)
```

Traccar übernimmt:
- Empfang der rohen GPS/OBD-Daten vom Freematics ONE+
- Speicherung des Positionsverlaufs
- Bereitstellung einer REST-API, die haFWCMA für Fahrten- und Positionsdaten abfragt
- Optional: Geofencing, Alarme, Benutzerverwaltung

---

## 2. Warum Traccar?

| Vorteil | Details |
|---------|---------|
| Natives Freematics-Protokoll | Traccar versteht das Freematics-Protokoll sofort |
| Viele Protokolle | Unterstützt 200+ GPS-Tracker-Protokolle |
| Open-Source & kostenlos | Keine Lizenzkosten |
| HA-Add-on verfügbar | Ein-Klick-Installation über den Home-Assistant-Add-on-Store |
| REST-API | haFWCMA kann Fahrten, Positionen und Gerätestatus abfragen |
| Web-Oberfläche | Echtzeit-Kartenansicht, Berichte, Geofences |

---

## 3. Installationsoptionen

| Option | Schwierigkeit | Am besten für |
|--------|--------------|---------------|
| [HA-Add-on](#4-home-assistant-add-on-einrichtung-empfohlen) | ⭐ Einfach | Home Assistant OS / Supervised |
| Docker | ⭐⭐ Mittel | Container-Installationen, separater Server |
| Bare-Metal Java | ⭐⭐⭐ Fortgeschritten | Individuelle Server-Umgebungen |

> **Empfehlung**: Verwenden Sie das Home-Assistant-Add-on, sofern Sie keinen separaten Server
> haben.

---

## 4. Home Assistant Add-on-Einrichtung (Empfohlen)

### 4.1 Community-Repository hinzufügen

1. Gehen Sie in Home Assistant zu **Einstellungen** → **Add-ons** → **Add-on-Store**
2. Klicken Sie auf das **⋮**-Menü → **Repositories**
3. Geben Sie ein:
   ```
   https://github.com/hassio-addons/repository
   ```
4. Klicken Sie auf **Hinzufügen** → **Schließen**

### 4.2 Traccar installieren

1. Suchen Sie im Add-on-Store nach **"Traccar"**
2. Klicken Sie auf das Traccar-Add-on → **Installieren**
3. Die Installation dauert 2–5 Minuten

### 4.3 Netzwerk-Ports konfigurieren

Stellen Sie im Tab **Konfiguration** des Traccar-Add-ons sicher, dass folgende Ports
zugeordnet sind:

```yaml
# Traccar-Add-on-Konfiguration
log_level: info
```

Im Abschnitt **Netzwerk** des Add-ons:

| Container-Port | Host-Port | Zweck |
|----------------|-----------|-------|
| 8082 | 8082 | Web-Oberfläche & REST-API |
| 5170 | 5170 | Freematics-Protokoll |
| 5055 | 5055 | OsmAnd-Protokoll |
| 5001 | 5001 | Teltonika-Protokoll (falls benötigt) |

> **Wichtig**: Nur die tatsächlich verwendeten Ports müssen weitergeleitet werden.
> Mindestens **8082** (API) und **5170** (Freematics-Protokoll) zuordnen.

### 4.4 Erweiterte Optionen konfigurieren (traccar.xml)

Für erweiterte Konfiguration bearbeiten Sie `traccar.xml` im Datenverzeichnis des Add-ons
(`/addon_configs/a0d7b954_traccar/` bei Home Assistant OS):

```xml
<?xml version='1.0' encoding='UTF-8'?>
<!DOCTYPE properties SYSTEM 'http://java.sun.com/dtd/properties.dtd'>
<properties>

    <!-- Datenbankeinstellungen (H2 Standard, für die meisten Benutzer geeignet) -->
    <entry key='database.driver'>org.h2.Driver</entry>
    <entry key='database.url'>jdbc:h2:/data/database</entry>

    <!-- Datenspeicherung: Positionsverlauf für 90 Tage aufbewahren -->
    <entry key='database.positionsHistoryDays'>90</entry>

    <!-- Servereinstellungen -->
    <entry key='server.address'>0.0.0.0</entry>
    <entry key='server.port'>8082</entry>

    <!-- Protokoll-Ports -->
    <entry key='freematics.port'>5170</entry>
    <entry key='osmand.port'>5055</entry>

</properties>
```

### 4.5 Add-on starten

1. Gehen Sie zum Tab **Info** → aktivieren Sie **"Beim Systemstart starten"**
2. Klicken Sie auf **"Starten"**
3. Prüfen Sie den Tab **Protokoll** – Sie sollten sehen:
   ```
   INFO: Traccar gestartet
   INFO: Wartet auf Port 5170 [freematics]
   INFO: Wartet auf Port 5055 [osmand]
   INFO: HTTP-Server gestartet auf Port 8082
   ```

---

## 5. Traccar-Web-Oberfläche

### 5.1 Erster Login

- **URL**: `http://<Ihre-HA-IP>:8082`
- **Standard-Zugangsdaten**: `admin` / `admin`

**⚠ Standard-Passwort sofort ändern:**
1. Klicken Sie auf das Schraubenschlüssel-Symbol (Einstellungen) → **Konto**
2. Passwort ändern

### 5.2 Ihr Freematics-Gerät hinzufügen

1. Klicken Sie auf **Geräte** (Auto-Symbol im linken Bereich)
2. Klicken Sie auf **"+"** um ein neues Gerät hinzuzufügen
3. Konfigurieren Sie:

| Feld | Wert | Hinweise |
|------|------|----------|
| **Name** | `Mein Auto` | Anzeigename |
| **Kennung** | `freematics_auto1` | Muss exakt mit `DEVICE_ID` in der Firmware übereinstimmen |
| **Kategorie** | `Auto` | Optional |
| **Telefon** | (leer) | Nicht benötigt |

4. Klicken Sie auf **Speichern**

### 5.3 Gerätestatus verstehen

| Symbol | Bedeutung |
|--------|-----------|
| 🟢 Grüner Punkt | Gerät ist online und sendet |
| 🟡 Gelber Punkt | Gerät war kürzlich online (innerhalb von 24 Stunden) |
| ⚫ Grauer Punkt | Gerät ist offline / hat noch nie gesendet |

### 5.4 Live-Kartenansicht

Sobald Ihr Freematics ONE+ Daten sendet, erscheint das Gerät in Echtzeit auf der Karte.
Klicken Sie auf das Gerät, um folgendes zu sehen:
- Aktuelle GPS-Koordinaten
- Geschwindigkeit
- Zeitpunkt der letzten Aktualisierung
- Benutzerdefinierte Attribute (OBD-Daten)

### 5.5 Berichte

Gehen Sie zu **Berichte** für historische Analysen:

| Berichtstyp | Was er zeigt |
|-------------|-------------|
| **Route** | GPS-Spur auf einer Karte für einen Zeitraum |
| **Fahrten** | Start-/Endzeiten, Strecke, Dauer pro Fahrt |
| **Zusammenfassung** | Aggregierte Statistiken pro Gerät |
| **Ereignisse** | Geofence-Ein/-Ausfahrt, Geschwindigkeitsalarme |

---

## 6. Erweiterte Traccar-Konfiguration

### 6.1 Geofences

Erstellen Sie Geofences für automatische Alarme (z. B. wenn das Auto den Heimbereich verlässt):

1. Gehen Sie zu **Geofences** → **"+"**
2. Zeichnen Sie eine Zone auf der Karte oder geben Sie Koordinaten ein
3. Verknüpfen Sie den Geofence mit Ihrem Gerät

### 6.2 Benachrichtigungen

Richten Sie Push-/E-Mail-Benachrichtigungen ein:
1. **Einstellungen** → **Benachrichtigungen** → **"+"**
2. Benachrichtigungstyp wählen (Geofence, Offline, Geschwindigkeitsüberschreitung)
3. Liefermethode konfigurieren (E-Mail, Web-Push)

### 6.3 API-Zugriffstoken

Damit haFWCMA ohne gespeichertes Passwort authentifizieren kann:

1. **Einstellungen** → **Konto** → scrollen zum Abschnitt **"Token"**
2. Klicken Sie auf **"Generieren"**
3. Kopieren Sie das Token (nur einmal angezeigt!)
4. Verwenden Sie dieses Token in der haFWCMA-Konfiguration statt des Passworts

### 6.4 Mehrere Benutzer

Wenn mehrere Personen Zugriff benötigen:
1. **Einstellungen** → **Benutzer** → **"+"**
2. Benutzerkonten mit entsprechenden Berechtigungen erstellen
3. haFWCMA sollte ein dediziertes Konto mit Lesezugriff verwenden

---

## 7. Netzwerkkonfiguration

### 7.1 Lokaler Netzwerkzugriff

Wenn haFWCMA und Traccar auf der gleichen HA-Instanz laufen:

| Dienst | URL |
|--------|-----|
| Traccar-Web-Oberfläche | `http://localhost:8082` |
| Traccar-API | `http://localhost:8082/api` |

### 7.2 Internetzugang für Freematics ONE+

Der Freematics ONE+ (über Mobilfunkdaten) muss Traccar über das Internet erreichen.

#### Tailscale Funnel (Empfohlen)

Die vollständige Tailscale-Einrichtung finden Sie in der
[Freematics ONE+ Einrichtungsanleitung](FREEMATICS_ONE_PLUS_SETUP_DE.md#5-traccar-über-das-internet-erreichbar-machen).

Kurzübersicht:
```bash
# Auf Ihrem HA-Host den Traccar-Freematics-Port freigeben
tailscale funnel 5170
```

Die öffentliche Adresse lautet dann: `tcp://homeassistant.ihr-tailnet.ts.net:5170`

#### Router-Port-Weiterleitung

| Port | Protokoll | Weiterleiten an |
|------|-----------|-----------------|
| 5170 | TCP+UDP | `<HA-interne-IP>:5170` |
| 5055 | TCP+UDP | `<HA-interne-IP>:5055` |

> Port 8082 (Web-Oberfläche) muss **nicht** ins Internet freigegeben werden.
> Nur die geräteseitigen Protokoll-Ports (5170, 5055) benötigen externen Zugang.

### 7.3 Firewall-Checkliste

Stellen Sie sicher, dass folgendes geöffnet ist:

```
Von Internet → HA-Host:
  ✓ TCP 5170  (Freematics-Protokoll)
  ✓ UDP 5170  (Freematics-Protokoll, bei UDP-Nutzung)
  ✓ TCP 5055  (OsmAnd, falls verwendet)

Von HA (haFWCMA) → Traccar:
  ✓ TCP 8082  (intern – kein Internetzugang nötig)

Vom Freematics ONE+ → Internet:
  ✓ TCP/UDP zur öffentlichen IP/Tailscale-Adresse auf Port 5170
```

---

## 8. haFWCMA mit Traccar verbinden

### 8.1 haFWCMA-Konfiguration

> **Aktueller Status**: Die Traccar-Integration in haFWCMA befindet sich in der Planung.
> Das Folgende beschreibt den geplanten Einrichtungsablauf. Prüfen Sie das haFWCMA-Änderungsprotokoll
> für den aktuellen Zeitpunkt dieser Funktion.

In den haFWCMA-Integrationseinstellungen:

```yaml
# haFWCMA Traccar-Konfiguration (geplant)
traccar:
  url: "http://localhost:8082"
  # Token verwenden (bevorzugt) oder Benutzername/Passwort:
  token: "Ihr-API-Token-aus-Traccar"
  # username: "admin"
  # password: "Ihr-Passwort"
  device_id: "freematics_auto1"   # muss mit Traccar-Gerätekennung übereinstimmen
  poll_interval: 30               # Sekunden zwischen API-Abfragen
```

### 8.2 Datenfluss

```
Traccar REST API  →  haFWCMA  →  HA-Entitäten

/api/positions    →  GPS-Lat/Lon, Geschwindigkeit, Attribute
/api/trips        →  Fahrtstart/-ende, Strecke
/api/devices      →  Gerätestatus (online/offline)
```

### 8.3 Traccar-API-Endpunkte, die haFWCMA nutzt

| Endpunkt | Methode | Zweck |
|----------|---------|-------|
| `/api/session` | POST | Authentifizierung |
| `/api/devices` | GET | Geräte auflisten, Status prüfen |
| `/api/positions` | GET | Neueste Position abrufen |
| `/api/reports/trips` | GET | Fahrtverlauf abrufen |
| `/api/reports/route` | GET | GPS-Route für eine Fahrt abrufen |

### 8.4 Manueller API-Test

Um die Traccar-API zu überprüfen, bevor haFWCMA konfiguriert wird:

```bash
# Von Ihrem HA-Host (oder einem Gerät im gleichen Netzwerk):

# 1. Authentifizieren
curl -c cookies.txt \
  -X POST "http://localhost:8082/api/session" \
  -d "email=admin&password=Ihr-Passwort"

# 2. Geräte auflisten
curl -b cookies.txt "http://localhost:8082/api/devices"

# 3. Neueste Positionen abrufen
curl -b cookies.txt "http://localhost:8082/api/positions"
```

Erwartete Antwort für `/api/devices`:
```json
[
  {
    "id": 1,
    "name": "Mein Auto",
    "uniqueId": "freematics_auto1",
    "status": "online",
    "lastUpdate": "2024-01-15T10:30:00.000+0000",
    "positionId": 42
  }
]
```

---

## 9. Überwachung & Alarme

### 9.1 Traccar-Status-Sensor in Home Assistant

Sie können die Traccar-Funktionsfähigkeit mit dem integrierten HA-REST-Sensor überwachen:

```yaml
# configuration.yaml
sensor:
  - platform: rest
    name: "Traccar Gerätestatus"
    resource: "http://localhost:8082/api/devices"
    headers:
      Authorization: "Basic base64(admin:passwort)"
    value_template: "{{ value_json[0].status }}"
    scan_interval: 60
```

### 9.2 Geofence-Automationen

Wenn haFWCMA Geofence-Ereignisse von Traccar empfängt, können HA-Automationen ausgelöst werden:

```yaml
# automation.yaml Beispiel (geplante Funktion)
automation:
  - alias: "Auto zu Hause angekommen"
    trigger:
      - platform: state
        entity_id: sensor.mein_auto_geofence_status
        to: "zuhause"
    action:
      - service: light.turn_on
        entity_id: light.garage
```

---

## 10. Fehlerbehebung bei Traccar

### Add-on startet nicht

```
Fehler: Port 8082 bereits belegt
```
→ Ein anderer Dienst verwendet Port 8082. Ändern Sie den Traccar-Port in den Add-on-Netzwerkeinstellungen.

### Gerät zeigt als Offline

1. Freematics ONE+ Seriellen Monitor auf Verbindungsfehler prüfen
2. `SERVER_HOST` und `SERVER_PORT` in der Firmware auf Traccar-Konfiguration prüfen
3. Konnektivität testen: `nc -zv <traccar-host> 5170`
4. Traccar-Protokolle auf eingehende Verbindungsversuche prüfen

### Keine Daten in Berichten

- Daten erscheinen erst in Berichten nach mindestens einer vollständigen aufgezeichneten Fahrt
- Gerät muss mindestens einige Minuten aktiv gewesen sein
- **Geräte** → Gerät anklicken → **"Letzte Position"** für Rohdaten prüfen

### Datenbank wird zu groß

Die H2-Datenbank von Traccar kann über die Zeit wachsen. Zur Begrenzung:
```xml
<!-- In traccar.xml -->
<entry key='database.positionsHistoryDays'>30</entry>
```

Dadurch werden Positionen, die älter als 30 Tage sind, automatisch gelöscht.

### API-Authentifizierungsfehler

```
HTTP 401 Nicht autorisiert
```
1. Benutzername/Passwort auf Richtigkeit prüfen
2. Token statt Passwort verwenden (siehe Abschnitt 6.3)
3. Prüfen, ob das Konto gesperrt wurde (zu viele fehlgeschlagene Anmeldungen)

---

## 📎 Verwandte Dokumentation

- **Freematics ONE+ Einrichtung (DE)**: [FREEMATICS_ONE_PLUS_SETUP_DE.md](FREEMATICS_ONE_PLUS_SETUP_DE.md)
- **Freematics ONE+ Einrichtung (EN)**: [FREEMATICS_ONE_PLUS_SETUP_EN.md](FREEMATICS_ONE_PLUS_SETUP_EN.md)
- **Traccar-Einrichtung (Englisch)**: [TRACCAR_INTEGRATION_EN.md](TRACCAR_INTEGRATION_EN.md)
- **Fahrtenbuch**: [TRIP_TRACKING_README.md](TRIP_TRACKING_README.md)

---

## 🔗 Externe Ressourcen

- [Traccar-Dokumentation](https://www.traccar.org/documentation/)
- [Traccar-API-Referenz](https://www.traccar.org/traccar-api/)
- [Traccar HA-Add-on](https://github.com/hassio-addons/addon-traccar)
- [Traccar unterstützte Geräte](https://www.traccar.org/devices/) (enthält Freematics)
- [Tailscale für HA](https://www.home-assistant.io/integrations/tailscale/)

---

*Zuletzt aktualisiert: März 2026*
