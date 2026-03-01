# Traccar Integration Guide

**Connecting Traccar ↔ haFWCMA ↔ Freematics ONE+**

---

## 📑 Table of Contents

1. [What is Traccar?](#1-what-is-traccar)
2. [Why Traccar?](#2-why-traccar)
3. [Installation Options](#3-installation-options)
4. [Home Assistant Add-on Setup (Recommended)](#4-home-assistant-add-on-setup-recommended)
5. [Traccar Web Interface](#5-traccar-web-interface)
6. [Advanced Traccar Configuration](#6-advanced-traccar-configuration)
7. [Network Configuration](#7-network-configuration)
8. [Connecting haFWCMA to Traccar](#8-connecting-hafwcma-to-traccar)
9. [Monitoring & Alerting](#9-monitoring--alerting)
10. [Troubleshooting Traccar](#10-troubleshooting-traccar)

---

## 1. What is Traccar?

**Traccar** is a free, open-source GPS tracking platform that can receive location data from
hundreds of different GPS device types.  For the Freematics ONE+ integration with haFWCMA it
acts as the **central relay server**:

```
Freematics ONE+ ──► Traccar (GPS relay) ──► haFWCMA (processes data)
```

Traccar handles:
- Receiving raw GPS/OBD data from the Freematics ONE+
- Storing position history
- Providing a REST API that haFWCMA queries for trip and position data
- Optional: geofencing, alerts, user management

---

## 2. Why Traccar?

| Benefit | Detail |
|---------|--------|
| Native Freematics support | Traccar understands the Freematics protocol out of the box |
| Many protocols | Supports 200+ GPS tracker protocols |
| Open-source & free | No license costs |
| HA add-on available | One-click install via Home Assistant add-on store |
| REST API | haFWCMA can query trips, positions, and device status |
| Web UI | Real-time map view, reports, geofences |

---

## 3. Installation Options

| Option | Difficulty | Best For |
|--------|-----------|---------|
| [HA Add-on](#4-home-assistant-add-on-setup-recommended) | ⭐ Easy | Home Assistant OS / Supervised |
| Docker | ⭐⭐ Medium | Container installs, separate server |
| Bare-metal Java | ⭐⭐⭐ Advanced | Custom server environments |

> **Recommendation**: Use the Home Assistant add-on unless you already have a separate server.

---

## 4. Home Assistant Add-on Setup (Recommended)

### 4.1 Add Community Repository

1. In Home Assistant, go to **Settings** → **Add-ons** → **Add-on Store**
2. Click the **⋮** menu → **Repositories**
3. Enter:
   ```
   https://github.com/hassio-addons/repository
   ```
4. Click **Add** → **Close**

### 4.2 Install Traccar

1. Search for **"Traccar"** in the add-on store
2. Click the Traccar add-on → **Install**
3. Installation takes 2–5 minutes

### 4.3 Configure Network Ports

In the **Configuration** tab of the Traccar add-on, ensure the following ports are mapped:

```yaml
# Traccar add-on configuration
log_level: info
```

In the **Network** section of the add-on:

| Container Port | Host Port | Purpose |
|----------------|-----------|---------|
| 8082 | 8082 | Web UI & REST API |
| 5170 | 5170 | Freematics protocol |
| 5055 | 5055 | OsmAnd protocol |
| 5001 | 5001 | Teltonika protocol (if needed) |

> **Important**: Only the ports you actually use need to be forwarded.
> At minimum, map **8082** (API) and **5170** (Freematics protocol).

### 4.4 Configure Advanced Options (traccar.xml)

For advanced configuration, edit `traccar.xml` in the add-on's data directory
(`/addon_configs/a0d7b954_traccar/` on Home Assistant OS):

```xml
<?xml version='1.0' encoding='UTF-8'?>
<!DOCTYPE properties SYSTEM 'http://java.sun.com/dtd/properties.dtd'>
<properties>

    <!-- Database settings (H2 default, suitable for most users) -->
    <entry key='database.driver'>org.h2.Driver</entry>
    <entry key='database.url'>jdbc:h2:/data/database</entry>

    <!-- Data retention: keep position history for 90 days -->
    <entry key='database.positionsHistoryDays'>90</entry>

    <!-- Server settings -->
    <entry key='server.address'>0.0.0.0</entry>
    <entry key='server.port'>8082</entry>

    <!-- Protocol ports -->
    <entry key='freematics.port'>5170</entry>
    <entry key='osmand.port'>5055</entry>

    <!-- Security: enable if exposed to internet -->
    <!-- <entry key='server.forward'>true</entry> -->

</properties>
```

### 4.5 Start the Add-on

1. Go to the **Info** tab → enable **"Start on boot"**
2. Click **"Start"**
3. Check the **Log** tab – you should see:
   ```
   2024-XX-XX INFO: Traccar started
   2024-XX-XX INFO: Listening on port 5170 [freematics]
   2024-XX-XX INFO: Listening on port 5055 [osmand]
   2024-XX-XX INFO: HTTP server started on port 8082
   ```

---

## 5. Traccar Web Interface

### 5.1 First Login

- **URL**: `http://<your-ha-ip>:8082`
- **Default credentials**: `admin` / `admin`

**⚠ Change the default password immediately:**
1. Click the wrench icon (Settings) → **Account**
2. Change the password

### 5.2 Add Your Freematics Device

1. Click **Devices** (car icon in left panel)
2. Click **"+"** to add a new device
3. Configure:

| Field | Value | Notes |
|-------|-------|-------|
| **Name** | `My Car` | Friendly display name |
| **Identifier** | `freematics_car1` | Must exactly match `DEVICE_ID` in firmware |
| **Category** | `Car` | Optional |
| **Phone** | (empty) | Not needed |

4. Click **Save**

### 5.3 Understanding the Device Status

| Icon | Meaning |
|------|---------|
| 🟢 Green dot | Device is online and reporting |
| 🟡 Yellow dot | Device was recently online (within 24 hours) |
| ⚫ Grey dot | Device is offline / never reported |

### 5.4 Live Map View

Once your Freematics ONE+ sends data, the device will appear on the map in real time.  
Click the device to see:
- Current GPS coordinates
- Speed
- Last update time
- Custom attributes (OBD data)

### 5.5 Reports

Go to **Reports** for historical analysis:

| Report Type | What it Shows |
|-------------|--------------|
| **Route** | GPS track on a map for a time period |
| **Trips** | Start/end times, distance, duration per trip |
| **Summary** | Aggregated stats per device |
| **Events** | Geofence enter/exit, speeding alerts |

---

## 6. Advanced Traccar Configuration

### 6.1 Geofences

Create geofences for automatic alerts (e.g., when car leaves home area):

1. Go to **Geofences** → **"+"**
2. Draw a zone on the map or enter coordinates
3. Link the geofence to your device

### 6.2 Notifications

Set up push/email notifications:
1. **Settings** → **Notifications** → **"+"**
2. Choose notification type (geofence, offline, speeding)
3. Configure delivery method (email, web push)

### 6.3 API Access Tokens

For haFWCMA to authenticate without storing your password:

1. **Settings** → **Account** → scroll to **"Token"** section
2. Click **"Generate"**
3. Copy the token (shown only once!)
4. Use this token in haFWCMA configuration instead of password

### 6.4 Multiple Users

If multiple people need access:
1. **Settings** → **Users** → **"+"**
2. Create user accounts with appropriate permissions
3. haFWCMA should use a dedicated account with read-only access

---

## 7. Network Configuration

### 7.1 Local Network Access

If haFWCMA and Traccar are on the same HA instance:

| Service | URL |
|---------|-----|
| Traccar Web UI | `http://localhost:8082` |
| Traccar API | `http://localhost:8082/api` |

### 7.2 Internet Access for Freematics ONE+

The Freematics ONE+ (on mobile data) must reach Traccar from the internet.

#### Tailscale Funnel (Recommended)

See the [Freematics ONE+ Setup Guide](FREEMATICS_ONE_PLUS_SETUP_EN.md#5-making-traccar-reachable-from-the-internet)
for the full Tailscale setup.

Quick summary:
```bash
# On your HA host, expose Traccar's Freematics port
tailscale funnel 5170
```

The public address will be: `tcp://homeassistant.your-tailnet.ts.net:5170`

#### Router Port Forwarding

| Port | Protocol | Forward To |
|------|----------|-----------|
| 5170 | TCP+UDP | `<HA internal IP>:5170` |
| 5055 | TCP+UDP | `<HA internal IP>:5055` |

> Port 8082 (web UI) does **not** need to be exposed to the internet.
> Only the device-facing protocol ports (5170, 5055) need external access.

### 7.3 Firewall Checklist

Ensure the following are open:

```
From internet → HA host:
  ✓ TCP 5170  (Freematics protocol)
  ✓ UDP 5170  (Freematics protocol, if using UDP)
  ✓ TCP 5055  (OsmAnd, if used)

From HA (haFWCMA) → Traccar:
  ✓ TCP 8082  (internal – no internet exposure needed)

From Freematics ONE+ → Internet:
  ✓ TCP/UDP to your public IP/Tailscale address on port 5170
```

---

## 8. Connecting haFWCMA to Traccar

### 8.1 haFWCMA Configuration

> **Current status**: Traccar integration in haFWCMA is planned. The following describes the
> intended setup workflow. Check the haFWCMA changelog for when this feature lands.

In haFWCMA integration settings:

```yaml
# haFWCMA Traccar configuration (planned)
traccar:
  url: "http://localhost:8082"
  # Use token (preferred) or username/password:
  token: "your-api-token-from-traccar"
  # username: "admin"
  # password: "your-password"
  device_id: "freematics_car1"   # must match Traccar device identifier
  poll_interval: 30              # seconds between API polls
```

### 8.2 Data Flow

```
Traccar REST API  →  haFWCMA  →  HA Entities

/api/positions    →  GPS lat/lon, speed, attributes
/api/trips        →  Trip start/end, distance
/api/devices      →  Device status (online/offline)
```

### 8.3 Traccar API Endpoints Used by haFWCMA

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/session` | POST | Authenticate |
| `/api/devices` | GET | List devices, check status |
| `/api/positions` | GET | Get latest position |
| `/api/reports/trips` | GET | Get trip history |
| `/api/reports/route` | GET | Get GPS route for a trip |

### 8.4 Manual API Test

To verify the Traccar API is working before configuring haFWCMA:

```bash
# From your HA host (or any machine on the same network):

# 1. Authenticate
curl -c cookies.txt \
  -X POST "http://localhost:8082/api/session" \
  -d "email=admin&password=your-password"

# 2. List devices
curl -b cookies.txt "http://localhost:8082/api/devices"

# 3. Get latest positions
curl -b cookies.txt "http://localhost:8082/api/positions"
```

Expected response for `/api/devices`:
```json
[
  {
    "id": 1,
    "name": "My Car",
    "uniqueId": "freematics_car1",
    "status": "online",
    "lastUpdate": "2024-01-15T10:30:00.000+0000",
    "positionId": 42
  }
]
```

---

## 9. Monitoring & Alerting

### 9.1 Traccar Status Sensor in Home Assistant

You can monitor Traccar's health using HA's built-in REST sensor:

```yaml
# configuration.yaml
sensor:
  - platform: rest
    name: "Traccar Device Status"
    resource: "http://localhost:8082/api/devices"
    headers:
      Authorization: "Basic base64(admin:password)"
    value_template: "{{ value_json[0].status }}"
    scan_interval: 60
```

### 9.2 Geofence Automations

When haFWCMA receives geofence events from Traccar, it can trigger HA automations:

```yaml
# automation.yaml example (planned feature)
automation:
  - alias: "Car arrived home"
    trigger:
      - platform: state
        entity_id: sensor.my_car_geofence_status
        to: "home"
    action:
      - service: light.turn_on
        entity_id: light.garage
```

---

## 10. Troubleshooting Traccar

### Add-on Won't Start

```
Error: port 8082 already in use
```
→ Another service is using port 8082. Change Traccar's port in the add-on network settings.

### Device Shows as Offline

1. Check Freematics ONE+ serial monitor for connection errors
2. Verify `SERVER_HOST` and `SERVER_PORT` in firmware match your Traccar configuration
3. Test connectivity: `nc -zv <traccar-host> 5170`
4. Check Traccar logs for incoming connection attempts

### No Data in Reports

- Data only appears in reports after at least one complete trip is recorded
- Ensure the device has been active for more than a few minutes
- Check **Devices** → click device → **"Latest Position"** to see raw data

### Database Gets Too Large

Traccar's H2 database can grow over time. To limit it:
```xml
<!-- In traccar.xml -->
<entry key='database.positionsHistoryDays'>30</entry>
```

This deletes positions older than 30 days automatically.

### API Authentication Errors

```
HTTP 401 Unauthorized
```
1. Verify username/password are correct
2. Use a token instead of password (see section 6.3)
3. Check if the account has been locked (too many failed logins)

---

## 📎 Related Documentation

- **Freematics ONE+ Setup (EN)**: [FREEMATICS_ONE_PLUS_SETUP_EN.md](FREEMATICS_ONE_PLUS_SETUP_EN.md)
- **Freematics ONE+ Setup (DE)**: [FREEMATICS_ONE_PLUS_SETUP_DE.md](FREEMATICS_ONE_PLUS_SETUP_DE.md)
- **Traccar Setup (German)**: [TRACCAR_INTEGRATION_DE.md](TRACCAR_INTEGRATION_DE.md)
- **Trip Tracking**: [TRIP_TRACKING_README.md](TRIP_TRACKING_README.md)

---

## 🔗 External Resources

- [Traccar Documentation](https://www.traccar.org/documentation/)
- [Traccar API Reference](https://www.traccar.org/traccar-api/)
- [Traccar HA Add-on](https://github.com/hassio-addons/addon-traccar)
- [Traccar Supported Devices](https://www.traccar.org/devices/) (includes Freematics)
- [Tailscale for HA](https://www.home-assistant.io/integrations/tailscale/)

---

*Last updated: 2026-03*
