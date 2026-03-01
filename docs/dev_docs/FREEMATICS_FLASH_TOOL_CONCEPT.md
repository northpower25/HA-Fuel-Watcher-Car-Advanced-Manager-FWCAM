# Freematics ONE+ Flash Tool – Concept & Specification

**A user-friendly configuration and flashing tool for the Freematics ONE+ firmware**

---

## 📑 Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Goals](#2-goals)
3. [Architecture Overview](#3-architecture-overview)
4. [User Interface Concept](#4-user-interface-concept)
5. [Technical Implementation](#5-technical-implementation)
6. [Configuration Parameters](#6-configuration-parameters)
7. [Flashing Process](#7-flashing-process)
8. [Security Considerations](#8-security-considerations)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [Alternatives Considered](#10-alternatives-considered)

---

## 1. Problem Statement

Configuring and flashing the Freematics ONE+ firmware currently requires:

1. Installing Arduino IDE and ESP32 board support (~500 MB)
2. Cloning the firmware repository
3. Manually editing `config.h` (requires C/C++ knowledge)
4. Compiling the firmware (~2–5 minutes)
5. Flashing via Arduino IDE or `esptool`

This multi-step process is error-prone for non-technical users and creates a significant
barrier to adoption.  A dedicated **Flash Tool** would replace steps 1–5 with a single
graphical interface.

---

## 2. Goals

### Primary Goals

- ✅ **No coding required**: Users should never need to edit source code
- ✅ **Single window**: All configuration in one place
- ✅ **One-click flash**: Enter settings, click "Flash", done
- ✅ **Cross-platform**: Windows, macOS, Linux
- ✅ **Pre-built binaries**: No Python/Node.js required to run the tool itself

### Non-Goals (out of scope for v1)

- Building the firmware from source (tool uses pre-built firmware binaries)
- Supporting every possible hardware variant in the first release
- OTA (over-the-air) firmware updates

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Flash Tool (GUI)                         │
│                                                             │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Configuration  │  │  Port Select │  │  Flash Button │  │
│  │  Form           │  │  & Detect    │  │  & Progress   │  │
│  └────────┬────────┘  └──────┬───────┘  └───────┬───────┘  │
│           │                 │                   │           │
└───────────┼─────────────────┼───────────────────┼───────────┘
            │                 │                   │
            ▼                 ▼                   ▼
   ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐
   │  Config Patcher │  │  Serial Port │  │  esptool      │
   │  (patches NVS   │  │  Enumeration │  │  (bundled)    │
   │   partition)    │  │              │  │               │
   └─────────────────┘  └──────────────┘  └───────────────┘
            │                                      │
            ▼                                      ▼
   ┌─────────────────┐                    ┌───────────────┐
   │  Pre-built      │                    │  Freematics   │
   │  Firmware .bin  │ ──────────────────►│  ONE+ (ESP32) │
   │  (bundled)      │                    │               │
   └─────────────────┘                    └───────────────┘
```

### Key Design Decision: NVS Partition Patching

Instead of recompiling the firmware for each user, the tool patches the **NVS (Non-Volatile
Storage) partition** of the pre-built binary.  The Freematics firmware stores runtime
configuration in the ESP32 NVS, which can be written as a separate binary partition without
rebuilding the entire firmware.

This means:
- The firmware binary is compiled once (by the project maintainer)
- The tool only writes the user's configuration to the NVS partition
- Flash time is reduced from 5 minutes (compilation) to ~30 seconds (flash only)

---

## 4. User Interface Concept

### Main Window Layout

```
╔══════════════════════════════════════════════════════════════╗
║  🚗 Freematics ONE+ Flash Tool                          v1.0 ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  FIRMWARE                                                    ║
║  ┌─────────────────────────────────────────────────────┐    ║
║  │ Firmware version: v5.2.1  [Check for Updates]       │    ║
║  └─────────────────────────────────────────────────────┘    ║
║                                                              ║
║  SERVER CONNECTION                                           ║
║  Server address: [homeassistant.ts.net          ]           ║
║  Server port:    [5170      ]  Protocol: [Freematics ▼]     ║
║  Device ID:      [freematics_car1               ]           ║
║                                                              ║
║  NETWORK (choose one)                                        ║
║  ○ SIM Card (Cellular)                                       ║
║    APN:      [internet                          ]           ║
║    Username: [                    ] (optional)               ║
║    Password: [                    ] (optional)               ║
║    Module:   [SIM7600 ▼]                                     ║
║                                                              ║
║  ● WiFi / Phone Hotspot                                      ║
║    SSID:     [MyPhoneHotspot                    ]           ║
║    Password: [••••••••••••                      ]           ║
║                                                              ║
║  DEVICE                                                      ║
║  Port: [COM3 – Silicon Labs CP2102 ▼]  [🔄 Refresh]        ║
║                                                              ║
║  ╔════════════════════════════════════════════════════╗     ║
║  ║  [ Flash Firmware ]                                ║     ║
║  ╚════════════════════════════════════════════════════╝     ║
║                                                              ║
║  ┌─────────────────────────────────────────────────────┐    ║
║  │ Status: Ready                                       │    ║
║  └─────────────────────────────────────────────────────┘    ║
╚══════════════════════════════════════════════════════════════╝
```

### Flash Progress Dialog

```
╔══════════════════════════════════════════════════════════════╗
║  Flashing Firmware...                                        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  ✅ Connecting to device (COM3)                              ║
║  ✅ Writing bootloader        [████████████████████] 100%   ║
║  ✅ Writing partition table   [████████████████████] 100%   ║
║  ⏳ Writing firmware          [████████░░░░░░░░░░░░]  42%  ║
║  ⬜ Writing configuration                                    ║
║                                                              ║
║  Elapsed: 0:14  Estimated remaining: 0:19                    ║
║                                                              ║
║                              [ Cancel ]                      ║
╚══════════════════════════════════════════════════════════════╝
```

### Success Dialog

```
╔══════════════════════════════════════════════════════════════╗
║  ✅ Flash Complete!                                          ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  The Freematics ONE+ has been successfully flashed.          ║
║                                                              ║
║  Next steps:                                                 ║
║  1. Unplug the USB cable                                     ║
║  2. Insert the device into your car's OBD-II port            ║
║  3. Verify data in Traccar: http://your-ha:8082              ║
║                                                              ║
║  Device ID: freematics_car1                                  ║
║  Server:    homeassistant.ts.net:5170                        ║
║                                                              ║
║  [ Save Configuration ]    [ Open Documentation ]    [ OK ] ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 5. Technical Implementation

### Technology Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| GUI framework | **Python + Tkinter** or **Electron** | Cross-platform, easy packaging |
| Serial communication | `pyserial` | Mature, cross-platform serial library |
| Firmware flashing | `esptool.py` (bundled) | Official Espressif tool, reliable |
| Configuration storage | JSON file | Simple, human-readable |
| Firmware download | HTTPS + SHA-256 verification | Secure firmware updates |

### Recommended: Python + Tkinter

For the initial version, Python with Tkinter is recommended because:
- Tkinter is bundled with Python (no extra dependencies)
- `esptool.py` is a Python library (seamless integration)
- `pyserial` handles serial port detection
- Can be packaged as a single executable with PyInstaller

### Directory Structure

```
freematics-flash-tool/
├── flash_tool.py           # Main application
├── config.py               # Configuration models
├── flasher.py              # esptool wrapper
├── firmware/
│   ├── firmware_v5.bin     # Pre-built firmware
│   ├── bootloader.bin
│   ├── partitions.bin
│   ├── boot_app0.bin
│   └── firmware.json       # Version metadata
├── requirements.txt        # Python dependencies
├── build.py                # PyInstaller build script
└── README.md
```

### Key Python Modules

#### `config.py` – Configuration Model

```python
from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class FreematicsConfig:
    """User configuration for Freematics ONE+ firmware."""

    # Server settings
    server_host: str = ""
    server_port: int = 5170
    device_id: str = ""
    protocol: str = "freematics"  # "freematics" or "osmand"

    # Network: cellular
    use_cellular: bool = True
    cell_apn: str = "internet"
    cell_apn_user: str = ""
    cell_apn_pass: str = ""
    net_device: str = "SIM7600"

    # Network: WiFi
    use_wifi: bool = False
    wifi_ssid: str = ""
    wifi_pass: str = ""

    # OBD settings
    send_interval: int = 5          # seconds
    gps_interval: int = 1000        # milliseconds
    idle_timeout: int = 60          # seconds
    sleep_duration: int = 300       # seconds

    def to_nvs_entries(self) -> dict:
        """Convert to NVS key-value pairs for the ESP32."""
        return {
            "SERVER_HOST": self.server_host,
            "SERVER_PORT": str(self.server_port),
            "DEVICE_ID": self.device_id,
            "CELL_APN": self.cell_apn,
            "CELL_APN_USER": self.cell_apn_user,
            "CELL_APN_PASS": self.cell_apn_pass,
            "NET_DEVICE": self.net_device,
            "WIFI_SSID": self.wifi_ssid if self.use_wifi else "",
            "WIFI_PASS": self.wifi_pass if self.use_wifi else "",
            "SEND_INTERVAL": str(self.send_interval),
            "GPS_INTERVAL": str(self.gps_interval),
        }

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.__dict__, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "FreematicsConfig":
        with open(path) as f:
            data = json.load(f)
        return cls(**data)
```

#### `flasher.py` – esptool Wrapper

```python
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional


class FirmwareFlasher:
    """Wraps esptool.py to flash the Freematics firmware."""

    FIRMWARE_DIR = Path(__file__).parent / "firmware"

    def flash(
        self,
        port: str,
        config: "FreematicsConfig",
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> None:
        """Flash firmware and configuration to the device.

        Args:
            port: Serial port, e.g. 'COM3' or '/dev/ttyUSB0'
            config: User configuration to write
            progress_callback: Called with (stage_name, percent_complete)
        """
        # Step 1: Generate NVS partition binary with user config
        nvs_bin = self._generate_nvs_partition(config)

        # Step 2: Flash all partitions
        flash_args = [
            sys.executable, "-m", "esptool",
            "--chip", "esp32",
            "--port", port,
            "--baud", "921600",
            "write_flash",
            "--flash_mode", "dio",
            "--flash_freq", "40m",
            "--flash_size", "detect",
            "0x1000",  str(self.FIRMWARE_DIR / "bootloader.bin"),
            "0x8000",  str(self.FIRMWARE_DIR / "partitions.bin"),
            "0xe000",  str(self.FIRMWARE_DIR / "boot_app0.bin"),
            "0x10000", str(self.FIRMWARE_DIR / "firmware_v5.bin"),
            "0x3F9000", str(nvs_bin),   # NVS partition offset
        ]

        if progress_callback:
            progress_callback("Flashing firmware", 0)

        result = subprocess.run(flash_args, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Flash failed: {result.stderr}")

        if progress_callback:
            progress_callback("Done", 100)

    def _generate_nvs_partition(self, config: "FreematicsConfig") -> Path:
        """Generate an NVS partition binary from the config."""
        import nvs_partition_gen  # from esp-idf or standalone tool

        entries = config.to_nvs_entries()
        # Write CSV for nvs_partition_gen
        csv_path = Path("/tmp/freematics_nvs.csv")
        with open(csv_path, "w") as f:
            f.write("key,type,encoding,value\n")
            f.write("freematics,namespace,,\n")
            for key, value in entries.items():
                f.write(f"{key},data,string,{value}\n")

        nvs_bin_path = Path("/tmp/freematics_nvs.bin")
        nvs_partition_gen.generate(str(csv_path), str(nvs_bin_path), 0x6000)
        return nvs_bin_path

    def list_ports(self) -> list[tuple[str, str]]:
        """Return list of (port_name, description) tuples."""
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        return [(p.device, p.description) for p in ports]
```

---

## 6. Configuration Parameters

The tool exposes the following configuration parameters to the user:

### Essential (always shown)

| Parameter | Label | Default | Validation |
|-----------|-------|---------|------------|
| `server_host` | Server Address | – | Non-empty, valid hostname/IP |
| `server_port` | Server Port | 5170 | 1–65535 |
| `device_id` | Device ID | – | Non-empty, alphanumeric + `_-` |

### Network: SIM Card

| Parameter | Label | Default | Notes |
|-----------|-------|---------|-------|
| `cell_apn` | APN | `internet` | From SIM provider |
| `cell_apn_user` | APN Username | (empty) | Often not needed |
| `cell_apn_pass` | APN Password | (empty) | Often not needed |
| `net_device` | Module Type | `SIM7600` | Dropdown: SIM7600, SIM5360, SIM800, A9G |

### Network: WiFi / Hotspot

| Parameter | Label | Default | Notes |
|-----------|-------|---------|-------|
| `wifi_ssid` | WiFi Network Name | – | Your hotspot SSID |
| `wifi_pass` | WiFi Password | – | Your hotspot password |

### Advanced (collapsed by default)

| Parameter | Label | Default | Notes |
|-----------|-------|---------|-------|
| `send_interval` | Data Send Interval | 5 s | How often to transmit |
| `gps_interval` | GPS Sample Rate | 1000 ms | GPS polling interval |
| `idle_timeout` | Idle Timeout | 60 s | Seconds until sleep mode |
| `sleep_duration` | Sleep Duration | 300 s | Seconds in sleep mode |

### APN Quick-Select (German Carriers)

The tool includes a dropdown with common German carrier APNs:

| Carrier | APN | User | Pass |
|---------|-----|------|------|
| Deutsche Telekom / congstar | `internet.telekom` | (empty) | (empty) |
| Vodafone | `web.vodafone.de` | (empty) | (empty) |
| O2 / 1&1 / simplytel | `internet` | (empty) | (empty) |
| Aldi Talk | `internet.eplus.de` | (empty) | (empty) |
| Lidl Connect | `internet.eplus.de` | (empty) | (empty) |
| REWE Mobil | `internet.eplus.de` | (empty) | (empty) |
| Blau | `internet.eplus.de` | (empty) | (empty) |

---

## 7. Flashing Process

### Step-by-Step Flash Procedure

```
1. Validate configuration
   └─ All required fields filled?
   └─ Server reachable? (optional connectivity test)

2. Detect device
   └─ Scan serial ports
   └─ Identify ESP32 device
   └─ Check if device is in flash mode

3. Download/verify firmware (if not cached)
   └─ Check firmware version against manifest
   └─ Download if newer version available
   └─ Verify SHA-256 checksum

4. Generate NVS partition
   └─ Convert config to NVS CSV format
   └─ Run nvs_partition_gen to create binary

5. Flash partitions (in order)
   └─ 0x1000   – bootloader.bin
   └─ 0x8000   – partitions.bin
   └─ 0xe000   – boot_app0.bin
   └─ 0x10000  – firmware_v5.bin
   └─ 0x3F9000 – nvs_config.bin (user configuration)

6. Verify
   └─ Read back device info
   └─ Display success message
```

### Error Handling

| Error | Recovery |
|-------|---------|
| Device not found | Guide user to install CP2102/CH340 driver |
| Flash failed mid-way | Retry from step 5 (partial flash is safe) |
| Wrong baud rate | Automatically try lower speeds (460800, 115200) |
| Port busy | Show "Close Arduino IDE or other serial tools" |

---

## 8. Security Considerations

### WiFi Password Storage

- Configuration is saved to a local JSON file
- WiFi/hotspot passwords are stored **in plaintext** in the config file
- Users should be warned not to share the config file
- Future: encrypt sensitive fields using OS keychain

### Firmware Integrity

- All pre-built firmware binaries are signed with the project's private key
- The tool verifies the signature before flashing
- Firmware is downloaded over HTTPS only
- SHA-256 checksums are displayed to the user

### Device ID Uniqueness

- The Device ID must be unique across all Traccar devices
- The tool can auto-generate a UUID-based ID to avoid collisions
- Users should not reuse the same Device ID for multiple cars

---

## 9. Implementation Roadmap

### v1.0 – Minimum Viable Product

- [ ] Python + Tkinter GUI
- [ ] Serial port detection and selection
- [ ] Configuration form (server, network, device ID)
- [ ] NVS partition generation
- [ ] Firmware flash via bundled esptool
- [ ] Pre-built firmware for SIM7600 + SIM5360 variants
- [ ] Windows installer (.exe via PyInstaller)
- [ ] macOS bundle (.app via PyInstaller)

### v1.1 – Quality of Life

- [ ] APN quick-select for common German carriers
- [ ] Connectivity test (ping server before flashing)
- [ ] Serial monitor built-in (view device output after flash)
- [ ] Save/load configuration presets
- [ ] Automatic firmware update check

### v1.2 – Extended Hardware Support

- [ ] WiFi-only variant support
- [ ] A9G module support
- [ ] SIM800 support
- [ ] Battery-powered mode configuration

### v2.0 – Advanced Features

- [ ] OTA update capability (push config changes without USB)
- [ ] Multiple vehicle profiles
- [ ] Integration with haFWCMA setup wizard

---

## 10. Alternatives Considered

### Option A: Web-based Tool (Browser + WebSerial API)

**Pros**: No installation required, works on all platforms  
**Cons**: WebSerial API only available in Chrome/Edge; complex packaging; less reliable  
**Decision**: Not chosen for v1, may add as v1.1 alternative

### Option B: Arduino IDE Plugin

**Pros**: Users may already have Arduino IDE  
**Cons**: Requires Arduino IDE 2.x; complex plugin ecosystem; not beginner-friendly  
**Decision**: Not suitable as the primary tool

### Option C: Mobile App (Flutter)

**Pros**: Phone can be used near the car  
**Cons**: Phones lack USB host capability for flashing; OTG cable required  
**Decision**: Not suitable for flashing; possible future companion app for monitoring only

### Option D: GitHub Actions / Cloud Compile

**Pros**: Always uses latest firmware; no local compilation  
**Cons**: Requires GitHub account; network dependency; binary download then flash still needed  
**Decision**: Could supplement the flash tool for firmware updates but not replace it

---

## 📎 Related Documentation

- **Freematics ONE+ Setup (EN)**: [../user_docs/FREEMATICS_ONE_PLUS_SETUP_EN.md](../user_docs/FREEMATICS_ONE_PLUS_SETUP_EN.md)
- **Freematics ONE+ Setup (DE)**: [../user_docs/FREEMATICS_ONE_PLUS_SETUP_DE.md](../user_docs/FREEMATICS_ONE_PLUS_SETUP_DE.md)
- **Traccar Integration (EN)**: [../user_docs/TRACCAR_INTEGRATION_EN.md](../user_docs/TRACCAR_INTEGRATION_EN.md)

---

## 🔗 External Resources

- [esptool.py Documentation](https://docs.espressif.com/projects/esptool/en/latest/)
- [ESP32 NVS Partition Generator](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/storage/nvs_partition_gen.html)
- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [PySerial Documentation](https://pyserial.readthedocs.io/)
- [Freematics ONE+ Hardware](https://freematics.com/pages/freematics-one-plus/)

---

*Concept version: 1.0*  
*Created: 2026-03*  
*Status: Proposal – feedback welcome*
