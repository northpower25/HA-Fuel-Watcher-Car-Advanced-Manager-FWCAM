# Freematics ONE+ Setup Guide

**Integration with Home Assistant Fuel Watcher Car Advanced Manager (haFWCMA)**

---

## 📑 Table of Contents

1. [Overview](#1-overview)
2. [Hardware Requirements](#2-hardware-requirements)
3. [Architecture & Data Flow](#3-architecture--data-flow)
4. [Setting Up Traccar on Home Assistant](#4-setting-up-traccar-on-home-assistant)
5. [Making Traccar Reachable from the Internet](#5-making-traccar-reachable-from-the-internet)
6. [Freematics ONE+ Firmware Configuration](#6-freematics-one-firmware-configuration)
7. [Flashing the Firmware](#7-flashing-the-firmware)
8. [Connecting haFWCMA to Traccar](#8-connecting-hafwcma-to-traccar)
9. [Verification & Testing](#9-verification--testing)
10. [Troubleshooting](#10-troubleshooting)
11. [Advanced Configuration](#11-advanced-configuration)

---

## 1. Overview

The **Freematics ONE+** is a compact OBD-II + GPS data logger based on ESP32 that reads vehicle
diagnostics (speed, RPM, engine load, fuel level, …) and GPS coordinates directly from your
car.  With a SIM card (or your phone's mobile hotspot) it transmits this data over the internet
to a **Traccar** server.  **haFWCMA** then reads that data from Traccar and uses it to update
trip logs, position sensors, and other vehicle entities in Home Assistant.

### What You Get

| Feature | Source |
|---------|--------|
| Live GPS position | Freematics ONE+ → Traccar → haFWCMA |
| Speed, RPM, engine load | Freematics ONE+ → Traccar → haFWCMA |
| Odometer / mileage | Freematics ONE+ → Traccar → haFWCMA |
| Automatic trip detection | haFWCMA (based on position/OBD data) |
| Fuel level (if supported by car) | Freematics ONE+ PID 0x2F |

### Key Assumption

> **The Freematics ONE+ and Home Assistant are NOT on the same network.**  
> The device uses a SIM card or a phone hotspot to connect to the internet.  
> Home Assistant is on your home network.

---

## 2. Hardware Requirements

### Freematics ONE+

- **Freematics ONE+** (ESP32-based, model with SIM module or WiFi)
  - SIM module variants: SIM7600, SIM5360, A9G, etc.
  - WiFi variant (for hotspot use)
- **Nano SIM card** with a data plan (even a cheap IoT SIM with ~100 MB/month is sufficient)
  - Alternatively: a mobile hotspot from your phone
- **OBD-II port** in your car (all cars manufactured after 2001 in the EU, 1996 in the USA)
- **USB cable (micro-USB)** for flashing the firmware
- **PC / Mac / Linux** with USB port for flashing

### Home Assistant Server

- Home Assistant OS, Supervised, or Container installation
- The Traccar add-on requires the **Supervisor** (i.e., Home Assistant OS or Supervised)
- At least 512 MB free RAM and ~200 MB free disk space for Traccar

---

## 3. Architecture & Data Flow

```
┌─────────────────────┐        Internet / Mobile Data
│  Freematics ONE+    │  ──────────────────────────────►  ┌─────────────────┐
│  (in your car)      │                                    │  Traccar Server  │
│                     │  ◄──────────────────────────────  │  (on your HA)    │
│  OBD-II data        │      Tailscale / Port Forward      │                 │
│  GPS coordinates    │                                    │  Port 5170 or   │
│  SIM / Hotspot      │                                    │  Port 5055       │
└─────────────────────┘                                    └────────┬────────┘
                                                                    │
                                                                    │ HTTP API
                                                                    ▼
                                                           ┌─────────────────┐
                                                           │  haFWCMA        │
                                                           │  (Home Assistant)│
                                                           │                 │
                                                           │  Trip Tracking  │
                                                           │  Position       │
                                                           │  Sensors        │
                                                           └─────────────────┘
```

### Communication Protocols

| Step | Protocol | Port | Notes |
|------|----------|------|-------|
| Freematics → Traccar | Freematics (UDP/TCP) | **5170** | Native Freematics protocol |
| Freematics → Traccar | OsmAnd (HTTP) | **5055** | Alternative, simpler protocol |
| haFWCMA → Traccar | HTTP REST API | **8082** | haFWCMA reads trip data |

---

## 4. Setting Up Traccar on Home Assistant

Traccar is an open-source GPS tracking server. The easiest way to run it on Home Assistant is
via the **Traccar community add-on**.

### 4.1 Install the Traccar Add-on

1. Open **Home Assistant UI** → **Settings** → **Add-ons** → **Add-on Store**
2. Click the three-dot menu (⋮) → **Repositories**
3. Add the following repository:
   ```
   https://github.com/hassio-addons/repository
   ```
4. Search for **"Traccar"** in the add-on store
5. Click **"Traccar"** → **"Install"**
6. Wait for installation to complete (may take several minutes)

### 4.2 Configure Traccar

After installation, go to the **Configuration** tab of the Traccar add-on:

```yaml
# Minimum configuration – adjust to your needs
log_level: info
```

**Important network ports** (configured in the Traccar add-on):

| Port | Protocol | Purpose |
|------|----------|---------|
| 8082 | HTTP | Traccar web UI & REST API |
| 5170 | TCP/UDP | Freematics protocol (native) |
| 5055 | TCP/UDP | OsmAnd GPS protocol |

Make sure these ports are listed under **Network** in the add-on configuration.

### 4.3 Start Traccar

1. Go to the **Info** tab of the Traccar add-on
2. Toggle **"Start on boot"** to ON
3. Click **"Start"**
4. Wait until the status shows **"Running"**

### 4.4 Access Traccar Web UI

Once running, open Traccar:
- **URL**: `http://<your-ha-ip>:8082`  (replace with your HA IP address)
- **Default login**: `admin` / `admin`  ← **Change this immediately!**

### 4.5 Create a Traccar Device for Your Car

1. Log in to Traccar Web UI
2. Click **"Devices"** → **"+"** (Add device)
3. Fill in:
   - **Name**: e.g., `My Car`
   - **Identifier**: This must match the `DEVICE_ID` you will configure in the firmware.
     Choose a unique string, e.g., `freematics_car1` or a number like `123456`
4. Click **"Save"**
5. Note down the **Device ID** you chose – you'll need it when configuring the firmware

---

## 5. Making Traccar Reachable from the Internet

Since the Freematics ONE+ connects via mobile data, it needs to reach Traccar over the internet.
There are several options – **Tailscale Funnel** is recommended as it requires no router
configuration.

### Option A: Tailscale Funnel (Recommended – No Router Config Needed)

**Tailscale** creates a secure VPN tunnel. **Tailscale Funnel** exposes a service to the
public internet via Tailscale's infrastructure.

#### Step 1: Install Tailscale on Home Assistant

1. In the HA **Add-on Store**, install the **Tailscale** add-on
2. Open the Tailscale add-on configuration and enable:
   ```yaml
   accept_dns: true
   advertise_exit_node: false
   ```
3. Start the add-on and follow the login link in the logs to authenticate with Tailscale
4. Note your device's Tailscale hostname, e.g., `homeassistant.your-tailnet.ts.net`

#### Step 2: Enable Tailscale Funnel for Traccar Port

Run the following command on your HA host (via SSH add-on or terminal):

```bash
# Expose Traccar Freematics protocol port to internet
tailscale funnel 5170

# Also expose the OsmAnd port if you want to use it
tailscale funnel 5055
```

After enabling Funnel, your Traccar server is reachable at:
```
tcp://homeassistant.your-tailnet.ts.net:5170
```

> **Note**: Tailscale Funnel is available on all Tailscale plans, but requires your account to
> have Funnel enabled. Check [tailscale.com/kb/1223/tailscale-funnel](https://tailscale.com/kb/1223/tailscale-funnel).

#### Step 3: Use the Funnel Address in Firmware

In the firmware configuration (see section 6), set:
```cpp
#define SERVER_HOST "homeassistant.your-tailnet.ts.net"
#define SERVER_PORT 5170
```

---

### Option B: Router Port Forwarding

If you have a static public IP address or use DynDNS, you can forward the port directly:

1. Log in to your **router admin panel** (usually `192.168.1.1` or `192.168.0.1`)
2. Find **"Port Forwarding"** or **"NAT"** settings
3. Add a rule:
   - **External port**: 5170
   - **Internal IP**: Your HA server's local IP (e.g., `192.168.1.100`)
   - **Internal port**: 5170
   - **Protocol**: TCP+UDP
4. Repeat for port 5055 if needed
5. Use your public IP or DynDNS hostname as `SERVER_HOST` in the firmware

> **Security Note**: Port forwarding exposes Traccar directly to the internet.  
> Ensure Traccar's admin password is strong and unique.

---

### Option C: Nabu Casa / Home Assistant Cloud

Home Assistant Cloud (Nabu Casa) provides remote access to the HA UI but does **not** expose
arbitrary TCP/UDP ports needed by Traccar. It is therefore **not suitable** for this use case.

---

## 6. Freematics ONE+ Firmware Configuration

The firmware source code is at:  
[https://github.com/northpower25/Freematics/tree/master/firmware_v5](https://github.com/northpower25/Freematics/tree/master/firmware_v5)

### 6.1 Prerequisites (Software)

Install the following on your PC:

1. **Arduino IDE** (2.x recommended) – [arduino.cc/en/software](https://www.arduino.cc/en/software)
2. **ESP32 board support** in Arduino IDE:
   - Go to **File** → **Preferences**
   - Add to "Additional boards manager URLs":
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Go to **Tools** → **Board** → **Boards Manager**, search for `esp32`, install
3. **Required libraries** (install via Arduino Library Manager):
   - `ArduinoJson`
   - `SPIFFS` (usually included with ESP32 board package)
4. **Python 3** with `esptool` for command-line flashing (optional):
   ```bash
   pip install esptool
   ```

### 6.2 Download the Firmware

```bash
git clone https://github.com/northpower25/Freematics.git
cd Freematics/firmware_v5
```

Or download the ZIP from GitHub and extract it.

### 6.3 Configure the Firmware

Open the main sketch directory. The key configuration file is **`config.h`** (or included in
the main `.ino` file). Edit these settings:

#### Network & Server Settings

```cpp
// ─── Server Configuration ───────────────────────────────────────────────────
// Your Traccar server hostname or IP address
#define SERVER_HOST     "homeassistant.your-tailnet.ts.net"

// Traccar Freematics protocol port (default 5170)
// Use 5055 for OsmAnd protocol instead
#define SERVER_PORT     5170

// Unique device identifier – must match what you configured in Traccar!
#define DEVICE_ID       "freematics_car1"
```

#### SIM Card Settings (for cellular connectivity)

```cpp
// ─── Cellular / SIM Card ────────────────────────────────────────────────────
// Set your SIM card's APN (Access Point Name)
// Examples:
//   Deutsche Telekom:  "internet.t-mobile"
//   Vodafone DE:       "web.vodafone.de"
//   1&1 / O2 DE:       "internet"
//   Prepaid IoT SIM:   check the SIM provider's documentation
#define CELL_APN        "internet"

// APN username and password (usually empty for German carriers)
#define CELL_APN_USER   ""
#define CELL_APN_PASS   ""

// Network module type – set to match your hardware
// Possible values: NET_SIM7600, NET_SIM5360, NET_SIM800, NET_A9G
#define NET_DEVICE      NET_SIM7600
```

#### WiFi Settings (alternative to SIM – for hotspot use)

```cpp
// ─── WiFi (use instead of or as fallback to cellular) ───────────────────────
// Enable WiFi support
#define ENABLE_WIFI     1

// WiFi credentials – use your phone's hotspot SSID and password
#define WIFI_SSID       "MyPhoneHotspot"
#define WIFI_PASS       "HotspotPassword"
```

#### GPS & OBD Settings

```cpp
// ─── GPS ────────────────────────────────────────────────────────────────────
// Interval between GPS readings (milliseconds)
#define GPS_INTERVAL    1000    // 1 second

// ─── OBD-II ─────────────────────────────────────────────────────────────────
// Enable OBD-II data collection
#define ENABLE_OBD      1

// OBD PIDs to collect (standard PIDs):
//   0x0D = Vehicle Speed (km/h)
//   0x0C = Engine RPM
//   0x04 = Engine Load (%)
//   0x05 = Coolant Temperature (°C)
//   0x2F = Fuel Tank Level (%) ← only if your car supports it
//   0x1F = Engine Run Time (s)
```

#### Data Transmission Settings

```cpp
// ─── Data Transmission ──────────────────────────────────────────────────────
// How often to send data to the server (seconds)
// Lower = more data, higher battery/data usage
// Higher = less frequent updates
#define SEND_INTERVAL   5       // every 5 seconds while driving

// Protocol: PROTO_METHOD_UDP (faster) or PROTO_METHOD_HTTP
#define PROTO_METHOD    PROTO_METHOD_UDP
```

### 6.4 OBD PID Reference

Common OBD-II PIDs supported by the Freematics firmware:

| PID (hex) | Parameter | Unit | Notes |
|-----------|-----------|------|-------|
| 0x04 | Engine Load | % | |
| 0x05 | Coolant Temp | °C | |
| 0x0A | Fuel Pressure | kPa | |
| 0x0B | Intake Manifold Pressure | kPa | |
| 0x0C | Engine RPM | rpm | |
| 0x0D | Vehicle Speed | km/h | Also used for odometer |
| 0x0F | Intake Air Temp | °C | |
| 0x10 | Mass Air Flow | g/s | |
| 0x11 | Throttle Position | % | |
| 0x1C | OBD standard | – | |
| 0x1F | Engine Run Time | s | |
| 0x21 | Distance with MIL on | km | |
| 0x2F | Fuel Tank Level | % | Not all cars support this |
| 0x33 | Barometric Pressure | kPa | |
| 0x46 | Ambient Air Temp | °C | |
| 0xA6 | Odometer | km | Mode 09 |

> **Note**: Not all cars support all PIDs. The firmware will skip unsupported PIDs automatically.

---

## 7. Flashing the Firmware

### 7.1 Connect the Freematics ONE+

1. Plug the Freematics ONE+ into your PC using a **micro-USB cable**
2. The device should appear as a serial port:
   - **Windows**: `COM3`, `COM4`, etc. (check Device Manager)
   - **macOS**: `/dev/cu.usbserial-*`
   - **Linux**: `/dev/ttyUSB0` or `/dev/ttyACM0`

### 7.2 Flash via Arduino IDE

1. Open the `firmware_v5` sketch in Arduino IDE
2. Go to **Tools** → **Board** → **ESP32 Arduino** → Select **"ESP32 Dev Module"**  
   (or the specific Freematics board if listed)
3. Set **Tools** → **Port** to your serial port
4. Set **Tools** → **Upload Speed** to `921600`
5. Click the **Upload** button (→ arrow)
6. Wait for "Done uploading" message

### 7.3 Flash via esptool (Command Line)

For more control or if Arduino IDE doesn't work:

```bash
# First, compile in Arduino IDE to get the .bin file
# Then flash with esptool:

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

Replace `/dev/ttyUSB0` with your actual serial port.

### 7.4 Verify the Upload

After flashing, open the **Serial Monitor** in Arduino IDE:
- **Baud rate**: 115200
- You should see startup messages including:
  ```
  [SYS] Freematics ONE+ starting...
  [NET] Connecting to APN: internet
  [GPS] GPS lock acquired
  [SRV] Connected to homeassistant.your-tailnet.ts.net:5170
  [OBD] OBD connected, Protocol: CAN
  ```

---

## 8. Connecting haFWCMA to Traccar

Once data is flowing into Traccar, configure haFWCMA to read it.

### 8.1 Traccar API Credentials

1. Open Traccar Web UI at `http://<your-ha-ip>:8082`
2. Go to **Settings** → **Account** and note your username/password
3. Alternatively, create a dedicated API token:
   - **Settings** → **User** → **Generate Token**
   - Note the token

### 8.2 Configure haFWCMA

> **Note**: Traccar integration in haFWCMA is currently in development. The following describes
> the intended configuration. Check the haFWCMA release notes for the current status.

In the haFWCMA integration configuration, add the Traccar connection:

1. Go to **Settings** → **Devices & Services** → **haFWCMA** → **Configure**
2. Look for **"Traccar Integration"** section
3. Fill in:
   - **Traccar URL**: `http://localhost:8082` (if running as HA add-on)
   - **Username**: your Traccar username
   - **Password**: your Traccar password (or API token)
   - **Device ID**: the identifier you configured in Traccar (e.g., `freematics_car1`)

### 8.3 Entity Mapping

After configuration, haFWCMA will create or update the following entities based on Traccar data:

| haFWCMA Entity | Data Source | Update Rate |
|----------------|-------------|-------------|
| `sensor.<car>_position` | GPS lat/lon from Traccar | Every data point |
| `sensor.<car>_speed` | OBD speed or GPS speed | Every data point |
| `sensor.<car>_odometer` | Accumulated GPS distance | Per trip |
| `sensor.<car>_engine_rpm` | OBD PID 0x0C | Every data point |
| `sensor.<car>_fuel_level` | OBD PID 0x2F | Every data point |
| Trip start/end | Detected from position + ignition | Automatic |

---

## 9. Verification & Testing

### 9.1 Check Traccar Web UI

1. Open `http://<your-ha-ip>:8082`
2. Go to **Devices** – your device should show a **green dot** (online)
3. Click the device → **"Latest Position"** – you should see GPS coordinates
4. Go to **Reports** → **Route** to see recent trips

### 9.2 Check Data in the Freematics Serial Monitor

With the device connected to USB and Serial Monitor open (115200 baud), look for:
- `[NET] Data sent` – confirms data is being transmitted
- `[GPS] Lat: xx.xxxxx Lon: xx.xxxxx` – confirms GPS fix
- `[OBD] Speed: xxx km/h` – confirms OBD data

### 9.3 Test with Phone Hotspot

Before buying a SIM card:
1. Enable a **mobile hotspot** on your phone
2. Set the hotspot SSID and password in the firmware config (see section 6.3)
3. The Freematics ONE+ will connect to your phone hotspot instead of cellular
4. Verify data appears in Traccar

### 9.4 Check haFWCMA Entities

In Home Assistant:
1. Go to **Settings** → **Devices & Services** → **haFWCMA**
2. Check the entities for your vehicle
3. Position and speed entities should update when driving

---

## 10. Troubleshooting

### Device Not Connecting to Server

| Symptom | Possible Cause | Solution |
|---------|---------------|----------|
| `[NET] Connection failed` | Wrong SERVER_HOST | Verify hostname/IP is correct and reachable |
| `[NET] APN error` | Wrong APN settings | Check your SIM card's APN documentation |
| `[NET] No signal` | Poor cellular coverage | Test in open area; check SIM card is activated |
| `[SRV] Timeout` | Firewall / port blocked | Verify Tailscale Funnel or port forwarding is active |

### No GPS Fix

| Symptom | Solution |
|---------|----------|
| `[GPS] No fix` for >5 min | Place device where it can see the sky; avoid tunnels |
| Inaccurate position | Normal for first fix; wait 1–2 min for accuracy to improve |

### No OBD Data

| Symptom | Solution |
|---------|----------|
| `[OBD] No response` | Check OBD-II port connection; car must be on (ignition ON) |
| `[OBD] Protocol error` | Some cars need the engine running, not just ignition ON |
| Missing PIDs | Not all cars support all PIDs; this is normal |

### Traccar Not Receiving Data

1. Check Traccar add-on logs: **Settings** → **Add-ons** → **Traccar** → **Logs**
2. Verify the port 5170 is listed under the add-on's **Network** settings
3. If using Tailscale Funnel, run `tailscale funnel status` to verify it's active
4. Try connecting from a device on your home network to `<ha-ip>:5170` using netcat:
   ```bash
   nc -zv <ha-ip> 5170
   ```

### haFWCMA Not Updating Entities

1. Check haFWCMA logs: **Settings** → **System** → **Logs** → filter for `hafwcma`
2. Verify the Traccar API URL is reachable from HA (test in browser: `http://localhost:8082/api/devices`)
3. Ensure the Device ID in haFWCMA config matches Traccar exactly

---

## 11. Advanced Configuration

### Multiple Vehicles

To track multiple cars:
1. Each Freematics ONE+ device needs a **unique Device ID** in the firmware config
2. Add each device to Traccar as a separate device
3. In haFWCMA, configure each car with its own Traccar Device ID

### Data Retention

Traccar stores raw GPS data. Configure retention in `traccar.xml`:
```xml
<entry key='database.positionsHistoryDays'>30</entry>
```

haFWCMA stores processed trip data in its own storage (`/config/.storage/hafwcma/`).

### Power Management

The Freematics ONE+ draws power from the OBD-II port. The OBD port in most cars is always live
(even with ignition off), so the device will continue to use a small amount of power (< 100 mA)
even when parked.

- The firmware includes a sleep mode that activates after a configurable idle period
- Configure in `config.h`:
  ```cpp
  #define IDLE_TIMEOUT    60   // seconds until sleep mode
  #define SLEEP_DURATION  300  // seconds to sleep
  ```

### Custom OBD PIDs

To add vehicle-specific PIDs not in the standard set:
```cpp
// In config.h, add your custom PID array:
const byte CUSTOM_PIDS[] = {0x01, 0x03, 0x0D, 0x0C, 0x2F};
```

---

## 📎 Related Documentation

- **German version**: [FREEMATICS_ONE_PLUS_SETUP_DE.md](FREEMATICS_ONE_PLUS_SETUP_DE.md)
- **Traccar Setup (English)**: [TRACCAR_INTEGRATION_EN.md](TRACCAR_INTEGRATION_EN.md)
- **Traccar Setup (German)**: [TRACCAR_INTEGRATION_DE.md](TRACCAR_INTEGRATION_DE.md)
- **Flash Tool Concept**: [../dev_docs/FREEMATICS_FLASH_TOOL_CONCEPT.md](../dev_docs/FREEMATICS_FLASH_TOOL_CONCEPT.md)
- **Trip Tracking**: [TRIP_TRACKING_README.md](TRIP_TRACKING_README.md)
- **Vehicle Entities**: [VEHICLE_ENTITIES.md](VEHICLE_ENTITIES.md)

---

## 🔗 External Resources

- [Freematics ONE+ Hardware Documentation](https://freematics.com/pages/freematics-one-plus/)
- [Freematics Firmware Source Code](https://github.com/northpower25/Freematics/tree/master/firmware_v5)
- [Traccar Home Assistant Add-on](https://github.com/hassio-addons/addon-traccar)
- [Traccar Documentation](https://www.traccar.org/documentation/)
- [Tailscale Funnel Documentation](https://tailscale.com/kb/1223/tailscale-funnel)
- [OBD-II PID Reference (Wikipedia)](https://en.wikipedia.org/wiki/OBD-II_PIDs)

---

*Last updated: 2026-03*  
*Firmware version: v5*  
*haFWCMA version: see [manifest.json](../../custom_components/hafwcma/manifest.json)*
