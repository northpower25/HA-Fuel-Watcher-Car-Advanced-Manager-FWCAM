# Freematics ONE+ Einrichtungsanleitung

**Integration mit Home Assistant Fuel Watcher Car Advanced Manager (haFWCMA)**

---

## 📑 Inhaltsverzeichnis

1. [Überblick](#1-überblick)
2. [Hardware-Voraussetzungen](#2-hardware-voraussetzungen)
3. [Architektur & Datenfluss](#3-architektur--datenfluss)
4. [Traccar auf Home Assistant einrichten](#4-traccar-auf-home-assistant-einrichten)
5. [Traccar über das Internet erreichbar machen](#5-traccar-über-das-internet-erreichbar-machen)
6. [Freematics ONE+ Firmware konfigurieren](#6-freematics-one-firmware-konfigurieren)
7. [Firmware flashen](#7-firmware-flashen)
8. [haFWCMA mit Traccar verbinden](#8-hafwcma-mit-traccar-verbinden)
9. [Überprüfung & Test](#9-überprüfung--test)
10. [Fehlerbehebung](#10-fehlerbehebung)
11. [Erweiterte Konfiguration](#11-erweiterte-konfiguration)

---

## 1. Überblick

Der **Freematics ONE+** ist ein kompakter OBD-II + GPS-Datenlogger auf Basis des ESP32-
Mikrocontrollers, der Fahrzeugdiagnosedaten (Geschwindigkeit, Drehzahl, Motorlast, Tankfüllstand
usw.) und GPS-Koordinaten direkt aus dem Fahrzeug ausliest.  Mit einer SIM-Karte (oder dem
mobilen Hotspot Ihres Smartphones) überträgt er diese Daten über das Internet an einen
**Traccar**-Server.  **haFWCMA** liest diese Daten anschließend aus Traccar aus und verwendet
sie, um Fahrtenprotokolle, Positionssensoren und andere Fahrzeug-Entitäten in Home Assistant
zu aktualisieren.

### Was Sie erhalten

| Funktion | Quelle |
|----------|--------|
| Live-GPS-Position | Freematics ONE+ → Traccar → haFWCMA |
| Geschwindigkeit, Drehzahl, Motorlast | Freematics ONE+ → Traccar → haFWCMA |
| Kilometerzähler / Kilometerstand | Freematics ONE+ → Traccar → haFWCMA |
| Automatische Fahrtenerkennung | haFWCMA (basierend auf Position/OBD-Daten) |
| Tankfüllstand (wenn vom Fahrzeug unterstützt) | Freematics ONE+ PID 0x2F |

### Wichtige Annahme

> **Der Freematics ONE+ und Home Assistant befinden sich NICHT im gleichen Netzwerk.**  
> Das Gerät verwendet eine SIM-Karte oder einen mobilen Hotspot, um eine Verbindung zum
> Internet herzustellen. Home Assistant befindet sich in Ihrem Heimnetzwerk.

---

## 2. Hardware-Voraussetzungen

### Freematics ONE+

- **Freematics ONE+** (ESP32-basiert, Modell mit SIM-Modul oder WiFi)
  - SIM-Modul-Varianten: SIM7600, SIM5360, A9G usw.
  - WiFi-Variante (für Hotspot-Nutzung)
- **Nano-SIM-Karte** mit Datentarif (bereits ein günstiger IoT-Tarif mit ~100 MB/Monat reicht)
  - Alternative: mobiler Hotspot von Ihrem Smartphone
- **OBD-II-Anschluss** in Ihrem Fahrzeug (alle nach 2001 in der EU, 1996 in den USA hergestellten
  Fahrzeuge)
- **USB-Kabel (Micro-USB)** zum Flashen der Firmware
- **PC / Mac / Linux** mit USB-Anschluss zum Flashen

### Home Assistant Server

- Home Assistant OS, Supervised oder Container-Installation
- Das Traccar-Add-on benötigt den **Supervisor** (d. h. Home Assistant OS oder Supervised)
- Mindestens 512 MB freier RAM und ~200 MB freier Festplattenspeicher für Traccar

---

## 3. Architektur & Datenfluss

```
┌─────────────────────┐        Internet / Mobilfunk
│  Freematics ONE+    │  ────────────────────────────►  ┌─────────────────┐
│  (in Ihrem Auto)    │                                  │  Traccar-Server  │
│                     │  ◄────────────────────────────  │  (auf Ihrem HA)  │
│  OBD-II-Daten       │      Tailscale / Port-           │                 │
│  GPS-Koordinaten    │      Weiterleitung                │  Port 5170 oder │
│  SIM / Hotspot      │                                  │  Port 5055       │
└─────────────────────┘                                  └────────┬────────┘
                                                                  │
                                                                  │ HTTP-API
                                                                  ▼
                                                         ┌─────────────────┐
                                                         │  haFWCMA        │
                                                         │  (Home Assistant)│
                                                         │                 │
                                                         │  Fahrtenbuch    │
                                                         │  Position       │
                                                         │  Sensoren       │
                                                         └─────────────────┘
```

### Kommunikationsprotokolle

| Schritt | Protokoll | Port | Hinweise |
|---------|-----------|------|----------|
| Freematics → Traccar | Freematics (UDP/TCP) | **5170** | Natives Freematics-Protokoll |
| Freematics → Traccar | OsmAnd (HTTP) | **5055** | Alternativ, einfacheres Protokoll |
| haFWCMA → Traccar | HTTP REST API | **8082** | haFWCMA liest Fahrtdaten |

---

## 4. Traccar auf Home Assistant einrichten

Traccar ist ein Open-Source-GPS-Tracking-Server. Die einfachste Möglichkeit, ihn auf Home
Assistant zu betreiben, ist das **Traccar-Community-Add-on**.

### 4.1 Traccar-Add-on installieren

1. Öffnen Sie die **Home Assistant-Oberfläche** → **Einstellungen** → **Add-ons** → **Add-on-Store**
2. Klicken Sie auf das Drei-Punkte-Menü (⋮) → **Repositories**
3. Fügen Sie folgendes Repository hinzu:
   ```
   https://github.com/hassio-addons/repository
   ```
4. Suchen Sie im Add-on-Store nach **"Traccar"**
5. Klicken Sie auf **"Traccar"** → **"Installieren"**
6. Warten Sie auf den Abschluss der Installation (kann einige Minuten dauern)

### 4.2 Traccar konfigurieren

Gehen Sie nach der Installation auf den Tab **Konfiguration** des Traccar-Add-ons:

```yaml
# Minimale Konfiguration – passen Sie nach Bedarf an
log_level: info
```

**Wichtige Netzwerkports** (konfiguriert im Traccar-Add-on):

| Port | Protokoll | Zweck |
|------|-----------|-------|
| 8082 | HTTP | Traccar-Web-Oberfläche & REST-API |
| 5170 | TCP/UDP | Freematics-Protokoll (nativ) |
| 5055 | TCP/UDP | OsmAnd-GPS-Protokoll |

Stellen Sie sicher, dass diese Ports unter **Netzwerk** in der Add-on-Konfiguration aufgelistet sind.

### 4.3 Traccar starten

1. Gehen Sie zum Tab **Info** des Traccar-Add-ons
2. Aktivieren Sie **"Beim Systemstart starten"**
3. Klicken Sie auf **"Starten"**
4. Warten Sie, bis der Status **"Läuft"** anzeigt

### 4.4 Auf Traccar-Web-Oberfläche zugreifen

Nach dem Start öffnen Sie Traccar:
- **URL**: `http://<Ihre-HA-IP>:8082`  (ersetzen Sie durch Ihre HA-IP-Adresse)
- **Standard-Login**: `admin` / `admin`  ← **Sofort ändern!**

### 4.5 Traccar-Gerät für Ihr Fahrzeug anlegen

1. Melden Sie sich in der Traccar-Web-Oberfläche an
2. Klicken Sie auf **"Geräte"** → **"+"** (Gerät hinzufügen)
3. Füllen Sie aus:
   - **Name**: z. B. `Mein Auto`
   - **Kennung**: Muss mit der `DEVICE_ID` übereinstimmen, die Sie in der Firmware konfigurieren.
     Wählen Sie eine eindeutige Zeichenkette, z. B. `freematics_auto1` oder eine Zahl wie `123456`
4. Klicken Sie auf **"Speichern"**
5. Notieren Sie sich die gewählte **Gerätekennung** – Sie benötigen sie bei der Firmware-Konfiguration

---

## 5. Traccar über das Internet erreichbar machen

Da sich der Freematics ONE+ über Mobilfunkdaten verbindet, muss er Traccar über das Internet
erreichen können. Es gibt mehrere Möglichkeiten – **Tailscale Funnel** wird empfohlen, da keine
Router-Konfiguration erforderlich ist.

### Option A: Tailscale Funnel (Empfohlen – keine Router-Konfiguration nötig)

**Tailscale** erstellt einen sicheren VPN-Tunnel. **Tailscale Funnel** macht einen Dienst über
die Tailscale-Infrastruktur im öffentlichen Internet zugänglich.

#### Schritt 1: Tailscale auf Home Assistant installieren

1. Installieren Sie im HA **Add-on-Store** das **Tailscale**-Add-on
2. Öffnen Sie die Tailscale-Add-on-Konfiguration und aktivieren Sie:
   ```yaml
   accept_dns: true
   advertise_exit_node: false
   ```
3. Starten Sie das Add-on und folgen Sie dem Login-Link in den Protokollen, um sich bei
   Tailscale zu authentifizieren
4. Notieren Sie den Tailscale-Hostnamen Ihres Geräts, z. B.
   `homeassistant.ihr-tailnet.ts.net`

#### Schritt 2: Tailscale Funnel für den Traccar-Port aktivieren

Führen Sie den folgenden Befehl auf Ihrem HA-Host aus (über das SSH-Add-on oder Terminal):

```bash
# Traccar Freematics-Protokoll-Port ins Internet freigeben
tailscale funnel 5170

# Optional: OsmAnd-Port ebenfalls freigeben
tailscale funnel 5055
```

Nach der Aktivierung von Funnel ist Ihr Traccar-Server erreichbar unter:
```
tcp://homeassistant.ihr-tailnet.ts.net:5170
```

> **Hinweis**: Tailscale Funnel ist in allen Tailscale-Plänen verfügbar, erfordert aber, dass
> Funnel für Ihr Konto aktiviert ist.
> Prüfen Sie [tailscale.com/kb/1223/tailscale-funnel](https://tailscale.com/kb/1223/tailscale-funnel).

#### Schritt 3: Funnel-Adresse in der Firmware verwenden

Setzen Sie in der Firmware-Konfiguration (siehe Abschnitt 6):
```cpp
#define SERVER_HOST "homeassistant.ihr-tailnet.ts.net"
#define SERVER_PORT 5170
```

---

### Option B: Router-Port-Weiterleitung

Wenn Sie eine statische öffentliche IP-Adresse haben oder DynDNS verwenden, können Sie den
Port direkt weiterleiten:

1. Melden Sie sich in der **Router-Administrationsoberfläche** an (meist `192.168.1.1`)
2. Suchen Sie die Einstellungen für **"Portweiterleitung"** oder **"NAT"**
3. Fügen Sie eine Regel hinzu:
   - **Externer Port**: 5170
   - **Interne IP**: Die lokale IP Ihres HA-Servers (z. B. `192.168.1.100`)
   - **Interner Port**: 5170
   - **Protokoll**: TCP+UDP
4. Wiederholen Sie dies für Port 5055 falls benötigt
5. Verwenden Sie Ihre öffentliche IP oder Ihren DynDNS-Hostnamen als `SERVER_HOST` in der Firmware

> **Sicherheitshinweis**: Port-Weiterleitung macht Traccar direkt aus dem Internet zugänglich.
> Stellen Sie sicher, dass das Traccar-Admin-Passwort stark und einzigartig ist.

---

### Option C: Nabu Casa / Home Assistant Cloud

Home Assistant Cloud (Nabu Casa) bietet Fernzugriff auf die HA-Benutzeroberfläche, macht aber
**keine** beliebigen TCP/UDP-Ports verfügbar, die Traccar benötigt. Es ist daher für diesen
Anwendungsfall **nicht geeignet**.

---

## 6. Freematics ONE+ Firmware konfigurieren

Der Firmware-Quellcode befindet sich unter:  
[https://github.com/northpower25/Freematics/tree/master/firmware_v5](https://github.com/northpower25/Freematics/tree/master/firmware_v5)

### 6.1 Voraussetzungen (Software)

Installieren Sie folgendes auf Ihrem PC:

1. **Arduino IDE** (2.x empfohlen) – [arduino.cc/en/software](https://www.arduino.cc/en/software)
2. **ESP32-Board-Unterstützung** in der Arduino IDE:
   - Gehen Sie zu **Datei** → **Voreinstellungen**
   - Fügen Sie zu "Zusätzliche Boardverwalter-URLs" hinzu:
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Gehen Sie zu **Werkzeuge** → **Board** → **Boardverwalter**, suchen Sie `esp32`, installieren
3. **Erforderliche Bibliotheken** (über Arduino-Bibliotheksverwaltung installieren):
   - `ArduinoJson`
   - `SPIFFS` (normalerweise im ESP32-Board-Paket enthalten)
4. **Python 3** mit `esptool` für das Flashen über die Befehlszeile (optional):
   ```bash
   pip install esptool
   ```

### 6.2 Firmware herunterladen

```bash
git clone https://github.com/northpower25/Freematics.git
cd Freematics/firmware_v5
```

Oder laden Sie das ZIP von GitHub herunter und entpacken Sie es.

### 6.3 Firmware konfigurieren

Öffnen Sie das Haupt-Sketch-Verzeichnis. Die wichtigste Konfigurationsdatei ist **`config.h`**
(oder in der Haupt-`.ino`-Datei enthalten). Bearbeiten Sie folgende Einstellungen:

#### Netzwerk- und Server-Einstellungen

```cpp
// ─── Server-Konfiguration ────────────────────────────────────────────────────
// Hostname oder IP-Adresse Ihres Traccar-Servers
#define SERVER_HOST     "homeassistant.ihr-tailnet.ts.net"

// Traccar Freematics-Protokoll-Port (Standard: 5170)
// Verwenden Sie 5055 für das OsmAnd-Protokoll
#define SERVER_PORT     5170

// Eindeutige Gerätekennung – muss mit der Kennung in Traccar übereinstimmen!
#define DEVICE_ID       "freematics_auto1"
```

#### SIM-Karten-Einstellungen (für Mobilfunkverbindung)

```cpp
// ─── Mobilfunk / SIM-Karte ──────────────────────────────────────────────────
// APN (Access Point Name) Ihrer SIM-Karte
// Beispiele:
//   Deutsche Telekom:   "internet.t-mobile"
//   Vodafone DE:        "web.vodafone.de"
//   1&1 / O2 DE:        "internet"
//   congstar:           "internet.telekom"
//   simplytel:          "internet"
//   IoT-SIM:            Dokumentation des SIM-Anbieters prüfen
#define CELL_APN        "internet"

// APN-Benutzername und -Passwort (meist leer bei deutschen Anbietern)
#define CELL_APN_USER   ""
#define CELL_APN_PASS   ""

// Netzwerkmodul-Typ – passend zu Ihrer Hardware
// Mögliche Werte: NET_SIM7600, NET_SIM5360, NET_SIM800, NET_A9G
#define NET_DEVICE      NET_SIM7600
```

#### WiFi-Einstellungen (Alternative zur SIM – für Hotspot-Nutzung)

```cpp
// ─── WiFi (als Alternative oder Rückfall zu Mobilfunk) ──────────────────────
// WiFi-Unterstützung aktivieren
#define ENABLE_WIFI     1

// WiFi-Zugangsdaten – verwenden Sie den Hotspot-SSID und das Passwort Ihres Smartphones
#define WIFI_SSID       "MeinSmartphoneHotspot"
#define WIFI_PASS       "HotspotPasswort"
```

#### GPS- und OBD-Einstellungen

```cpp
// ─── GPS ────────────────────────────────────────────────────────────────────
// Abstand zwischen GPS-Messungen (Millisekunden)
#define GPS_INTERVAL    1000    // 1 Sekunde

// ─── OBD-II ─────────────────────────────────────────────────────────────────
// OBD-II-Datenerfassung aktivieren
#define ENABLE_OBD      1

// Zu erfassende OBD-PIDs (Standard-PIDs):
//   0x0D = Fahrzeuggeschwindigkeit (km/h)
//   0x0C = Motordrehzahl
//   0x04 = Motorlast (%)
//   0x05 = Kühlmitteltemperatur (°C)
//   0x2F = Tankfüllstand (%) ← nur wenn Ihr Fahrzeug es unterstützt
//   0x1F = Motorlaufzeit (s)
```

#### Datenübertragungseinstellungen

```cpp
// ─── Datenübertragung ───────────────────────────────────────────────────────
// Wie oft Daten an den Server gesendet werden (Sekunden)
// Niedriger = mehr Daten, höherer Batterie-/Datenverbrauch
// Höher = seltenere Aktualisierungen
#define SEND_INTERVAL   5       // alle 5 Sekunden während der Fahrt

// Protokoll: PROTO_METHOD_UDP (schneller) oder PROTO_METHOD_HTTP
#define PROTO_METHOD    PROTO_METHOD_UDP
```

### 6.4 OBD-PID-Referenz

Häufige OBD-II-PIDs, die von der Freematics-Firmware unterstützt werden:

| PID (hex) | Parameter | Einheit | Hinweise |
|-----------|-----------|---------|----------|
| 0x04 | Motorlast | % | |
| 0x05 | Kühlmitteltemperatur | °C | |
| 0x0A | Kraftstoffdruck | kPa | |
| 0x0B | Saugrohrdruck | kPa | |
| 0x0C | Motordrehzahl | U/min | |
| 0x0D | Fahrzeuggeschwindigkeit | km/h | Auch für Kilometerzähler |
| 0x0F | Ansauglufttemperatur | °C | |
| 0x10 | Luftmassenstrom | g/s | |
| 0x11 | Drosselklappenstellung | % | |
| 0x1F | Motorlaufzeit | s | |
| 0x21 | Fahrtstrecke mit MIL | km | |
| 0x2F | Tankfüllstand | % | Nicht alle Fahrzeuge unterstützen dies |
| 0x33 | Luftdruck | kPa | |
| 0x46 | Außentemperatur | °C | |
| 0xA6 | Kilometerzähler | km | Modus 09 |

> **Hinweis**: Nicht alle Fahrzeuge unterstützen alle PIDs. Die Firmware überspringt
> nicht unterstützte PIDs automatisch.

---

## 7. Firmware flashen

### 7.1 Freematics ONE+ anschließen

1. Schließen Sie den Freematics ONE+ mit einem **Micro-USB-Kabel** an Ihren PC an
2. Das Gerät sollte als serieller Port erscheinen:
   - **Windows**: `COM3`, `COM4` usw. (im Geräte-Manager prüfen)
   - **macOS**: `/dev/cu.usbserial-*`
   - **Linux**: `/dev/ttyUSB0` oder `/dev/ttyACM0`

### 7.2 Flashen über die Arduino IDE

1. Öffnen Sie den `firmware_v5`-Sketch in der Arduino IDE
2. Gehen Sie zu **Werkzeuge** → **Board** → **ESP32 Arduino** → wählen Sie **"ESP32 Dev Module"**
   (oder das spezifische Freematics-Board, falls aufgeführt)
3. Setzen Sie **Werkzeuge** → **Port** auf Ihren seriellen Port
4. Setzen Sie **Werkzeuge** → **Upload-Geschwindigkeit** auf `921600`
5. Klicken Sie auf die Schaltfläche **Hochladen** (→ Pfeil)
6. Warten Sie auf die Meldung „Hochladen abgeschlossen"

### 7.3 Flashen über esptool (Befehlszeile)

Für mehr Kontrolle oder wenn die Arduino IDE nicht funktioniert:

```bash
# Zuerst in der Arduino IDE kompilieren, um die .bin-Datei zu erhalten
# Dann mit esptool flashen:

esptool.py \
  --chip esp32 \
  --port /dev/ttyUSB0 \
  --baud 921600 \
  write_flash \
  --flash_mode dio \
  --flash_freq 40m \
  --flash_size detect \
  0x1000 bootloader.bin \
  0x8000 partitions.bin \
  0xe000 boot_app0.bin \
  0x10000 firmware_v5.ino.bin
```

Ersetzen Sie `/dev/ttyUSB0` durch Ihren tatsächlichen seriellen Port.

### 7.4 Upload überprüfen

Öffnen Sie nach dem Flashen den **Seriellen Monitor** in der Arduino IDE:
- **Baudrate**: 115200
- Sie sollten Startmeldungen sehen, darunter:
  ```
  [SYS] Freematics ONE+ startet...
  [NET] Verbindung zu APN: internet
  [GPS] GPS-Fix erhalten
  [SRV] Verbunden mit homeassistant.ihr-tailnet.ts.net:5170
  [OBD] OBD verbunden, Protokoll: CAN
  ```

---

## 8. haFWCMA mit Traccar verbinden

Sobald Daten in Traccar fließen, konfigurieren Sie haFWCMA zum Lesen dieser Daten.

### 8.1 Traccar-API-Zugangsdaten

1. Öffnen Sie die Traccar-Web-Oberfläche unter `http://<Ihre-HA-IP>:8082`
2. Gehen Sie zu **Einstellungen** → **Konto** und notieren Sie Benutzername/Passwort
3. Alternativ erstellen Sie ein dediziertes API-Token:
   - **Einstellungen** → **Benutzer** → **Token generieren**
   - Notieren Sie das Token

### 8.2 haFWCMA konfigurieren

> **Hinweis**: Die Traccar-Integration in haFWCMA befindet sich derzeit in der Entwicklung.
> Das Folgende beschreibt die geplante Konfiguration. Prüfen Sie die haFWCMA-Release-Notes für
> den aktuellen Status.

Fügen Sie in der haFWCMA-Integrationskonfiguration die Traccar-Verbindung hinzu:

1. Gehen Sie zu **Einstellungen** → **Geräte & Dienste** → **haFWCMA** → **Konfigurieren**
2. Suchen Sie den Abschnitt **"Traccar-Integration"**
3. Füllen Sie aus:
   - **Traccar-URL**: `http://localhost:8082` (wenn als HA-Add-on betrieben)
   - **Benutzername**: Ihr Traccar-Benutzername
   - **Passwort**: Ihr Traccar-Passwort (oder API-Token)
   - **Gerätekennung**: Die in Traccar konfigurierte Kennung (z. B. `freematics_auto1`)

### 8.3 Entitätszuordnung

Nach der Konfiguration erstellt oder aktualisiert haFWCMA folgende Entitäten auf Basis von
Traccar-Daten:

| haFWCMA-Entität | Datenquelle | Aktualisierungsrate |
|-----------------|-------------|---------------------|
| `sensor.<auto>_position` | GPS-Lat/Lon von Traccar | Bei jedem Datenpunkt |
| `sensor.<auto>_speed` | OBD-Geschwindigkeit oder GPS-Geschwindigkeit | Bei jedem Datenpunkt |
| `sensor.<auto>_odometer` | Akkumulierte GPS-Strecke | Pro Fahrt |
| `sensor.<auto>_engine_rpm` | OBD-PID 0x0C | Bei jedem Datenpunkt |
| `sensor.<auto>_fuel_level` | OBD-PID 0x2F | Bei jedem Datenpunkt |
| Fahrt-Start/Ende | Erkannt aus Position + Zündung | Automatisch |

---

## 9. Überprüfung & Test

### 9.1 Traccar-Web-Oberfläche prüfen

1. Öffnen Sie `http://<Ihre-HA-IP>:8082`
2. Gehen Sie zu **Geräte** – Ihr Gerät sollte einen **grünen Punkt** haben (online)
3. Klicken Sie auf das Gerät → **"Letzte Position"** – Sie sollten GPS-Koordinaten sehen
4. Gehen Sie zu **Berichte** → **Route**, um aktuelle Fahrten zu sehen

### 9.2 Daten im Freematics-Seriellen-Monitor prüfen

Mit dem Gerät über USB verbunden und offenem Seriellem Monitor (115200 Baud):
- `[NET] Daten gesendet` – bestätigt Datenübertragung
- `[GPS] Lat: xx.xxxxx Lon: xx.xxxxx` – bestätigt GPS-Fix
- `[OBD] Geschwindigkeit: xxx km/h` – bestätigt OBD-Daten

### 9.3 Test mit Smartphone-Hotspot

Bevor Sie eine SIM-Karte kaufen:
1. Aktivieren Sie einen **mobilen Hotspot** auf Ihrem Smartphone
2. Konfigurieren Sie SSID und Passwort des Hotspots in der Firmware-Konfiguration (Abschnitt 6.3)
3. Der Freematics ONE+ verbindet sich mit dem Smartphone-Hotspot statt über Mobilfunk
4. Überprüfen Sie, ob Daten in Traccar erscheinen

### 9.4 haFWCMA-Entitäten prüfen

In Home Assistant:
1. Gehen Sie zu **Einstellungen** → **Geräte & Dienste** → **haFWCMA**
2. Prüfen Sie die Entitäten Ihres Fahrzeugs
3. Positions- und Geschwindigkeitsentitäten sollten sich beim Fahren aktualisieren

---

## 10. Fehlerbehebung

### Gerät verbindet sich nicht mit Server

| Symptom | Mögliche Ursache | Lösung |
|---------|-----------------|--------|
| `[NET] Verbindung fehlgeschlagen` | Falscher SERVER_HOST | Hostname/IP prüfen und Erreichbarkeit testen |
| `[NET] APN-Fehler` | Falsche APN-Einstellungen | APN-Dokumentation Ihres SIM-Anbieters prüfen |
| `[NET] Kein Signal` | Schlechte Mobilfunkabdeckung | Im Freien testen; SIM-Karte auf Aktivierung prüfen |
| `[SRV] Timeout` | Firewall / Port gesperrt | Tailscale Funnel oder Port-Weiterleitung prüfen |

### Kein GPS-Fix

| Symptom | Lösung |
|---------|--------|
| `[GPS] Kein Fix` für >5 Minuten | Gerät im Freien platzieren, wo der Himmel sichtbar ist |
| Ungenaue Position | Normal beim ersten Fix; 1–2 Minuten auf Genauigkeitsverbesserung warten |

### Keine OBD-Daten

| Symptom | Lösung |
|---------|--------|
| `[OBD] Keine Antwort` | OBD-II-Anschluss prüfen; Fahrzeug muss eingeschaltet sein |
| `[OBD] Protokollfehler` | Einige Fahrzeuge brauchen laufenden Motor, nicht nur Zündung ein |
| Fehlende PIDs | Nicht alle Fahrzeuge unterstützen alle PIDs; das ist normal |

### Traccar empfängt keine Daten

1. Traccar-Add-on-Protokolle prüfen: **Einstellungen** → **Add-ons** → **Traccar** → **Protokolle**
2. Sicherstellen, dass Port 5170 unter **Netzwerk** in den Add-on-Einstellungen aufgeführt ist
3. Bei Tailscale Funnel: `tailscale funnel status` ausführen
4. Verbindungstest vom Heimnetzwerk: `nc -zv <ha-ip> 5170`

### haFWCMA-Entitäten werden nicht aktualisiert

1. haFWCMA-Protokolle prüfen: **Einstellungen** → **System** → **Protokolle** → nach `hafwcma` filtern
2. Traccar-API-URL prüfen (im Browser: `http://localhost:8082/api/devices`)
3. Sicherstellen, dass Gerätekennung in haFWCMA-Konfiguration exakt mit Traccar übereinstimmt

---

## 11. Erweiterte Konfiguration

### Mehrere Fahrzeuge

Um mehrere Autos zu verfolgen:
1. Jeder Freematics ONE+ benötigt eine **eindeutige Gerätekennung** in der Firmware-Konfiguration
2. Jedes Gerät als separates Gerät in Traccar hinzufügen
3. In haFWCMA jedes Auto mit seiner eigenen Traccar-Gerätekennung konfigurieren

### Datenspeicherung

Traccar speichert rohe GPS-Daten. Konfigurieren Sie die Aufbewahrungszeit in `traccar.xml`:
```xml
<entry key='database.positionsHistoryDays'>30</entry>
```

haFWCMA speichert verarbeitete Fahrtdaten in seinem eigenen Speicher
(`/config/.storage/hafwcma/`).

### Energieverwaltung

Der Freematics ONE+ bezieht Strom vom OBD-II-Anschluss. Der OBD-Anschluss ist in den meisten
Fahrzeugen immer aktiv (auch bei ausgeschalteter Zündung), daher verbraucht das Gerät auch
beim Parken etwas Strom (< 100 mA).

- Die Firmware enthält einen Schlafmodus, der nach einer konfigurierbaren Leerlaufzeit aktiviert wird
- In `config.h` konfigurieren:
  ```cpp
  #define IDLE_TIMEOUT    60   // Sekunden bis zum Schlafmodus
  #define SLEEP_DURATION  300  // Sekunden im Schlafmodus
  ```

### Benutzerdefinierte OBD-PIDs

Um fahrzeugspezifische PIDs hinzuzufügen, die nicht im Standardsatz enthalten sind:
```cpp
// In config.h, eigenes PID-Array hinzufügen:
const byte CUSTOM_PIDS[] = {0x01, 0x03, 0x0D, 0x0C, 0x2F};
```

---

## 📎 Verwandte Dokumentation

- **Englische Version**: [FREEMATICS_ONE_PLUS_SETUP_EN.md](FREEMATICS_ONE_PLUS_SETUP_EN.md)
- **Traccar-Einrichtung (Englisch)**: [TRACCAR_INTEGRATION_EN.md](TRACCAR_INTEGRATION_EN.md)
- **Traccar-Einrichtung (Deutsch)**: [TRACCAR_INTEGRATION_DE.md](TRACCAR_INTEGRATION_DE.md)
- **Flash-Tool-Konzept**: [../dev_docs/FREEMATICS_FLASH_TOOL_CONCEPT.md](../dev_docs/FREEMATICS_FLASH_TOOL_CONCEPT.md)
- **Fahrtenbuch**: [TRIP_TRACKING_README.md](TRIP_TRACKING_README.md)
- **Fahrzeug-Entitäten**: [VEHICLE_ENTITIES.md](VEHICLE_ENTITIES.md)

---

## 🔗 Externe Ressourcen

- [Freematics ONE+ Hardware-Dokumentation](https://freematics.com/pages/freematics-one-plus/)
- [Freematics Firmware-Quellcode](https://github.com/northpower25/Freematics/tree/master/firmware_v5)
- [Traccar Home Assistant Add-on](https://github.com/hassio-addons/addon-traccar)
- [Traccar-Dokumentation](https://www.traccar.org/documentation/)
- [Tailscale-Funnel-Dokumentation](https://tailscale.com/kb/1223/tailscale-funnel)
- [OBD-II-PID-Referenz (Wikipedia)](https://de.wikipedia.org/wiki/OBD-II_PIDs)

---

*Zuletzt aktualisiert: März 2026*  
*Firmware-Version: v5*  
*haFWCMA-Version: siehe [manifest.json](../../custom_components/hafwcma/manifest.json)*
