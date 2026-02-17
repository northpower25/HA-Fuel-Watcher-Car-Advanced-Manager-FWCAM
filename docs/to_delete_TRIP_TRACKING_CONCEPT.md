# Trip Tracking (Fahrtenbuch) - Konzept und Implementierung / Concept and Implementation

**Version:** 1.0  
**Datum / Date:** 2026-02-13  
**Status:** Konzept / Concept

---

## Zusammenfassung / Summary

### Deutsch
Dieses Dokument beschreibt das Konzept für eine umfassende Trip-Tracking-Funktion (Fahrtenbuch) für die haFWCMA-Integration. Die Funktion ermöglicht die automatische Erkennung und Verwaltung von Fahrten mit Fokus auf Datenschutz, Kostenanalyse und Pattern-Erkennung.

### English
This document describes the concept for a comprehensive trip tracking (logbook) feature for the haFWCMA integration. The feature enables automatic detection and management of trips with focus on privacy, cost analysis, and pattern recognition.

---

## 1. Anforderungen / Requirements

### 1.1 Kernfunktionen / Core Functions

#### 1.1.1 Fahrt-Erkennung / Trip Detection
**Deutsch:**
- Automatische Erkennung von Fahrtbeginn und Fahrtende basierend auf Fahrzeugbewegung
- Verwendung der bestehenden Odometer-, Positions- und Tank-Level-Entitäten
- Ähnlich zur bestehenden Tankvorgang-Erkennung (Refueling Detection)
- Minimale Fahrtdistanz: 0.5 km (konfigurierbar)
- Merge-Zeitfenster für Kurzstopps: 5 Minuten (konfigurierbar)

**English:**
- Automatic detection of trip start and end based on vehicle movement
- Using existing odometer, position, and tank level entities
- Similar to existing refueling detection mechanism
- Minimum trip distance: 0.5 km (configurable)
- Merge time window for short stops: 5 minutes (configurable)

#### 1.1.2 Start- und Zielpositionen / Start and End Positions
**Deutsch:**
- Erfassung von GPS-Koordinaten (Latitude/Longitude) für Start und Ziel
- Automatische Reverse-Geocoding zur Adressauflösung (mit OpenStreetMap Nominatim API)
- Editierbare Adressen und Beschreibungen
- Optionale manuelle Zuordnung zu bekannten Orten (POIs)

**English:**
- Capture GPS coordinates (Latitude/Longitude) for start and end
- Automatic reverse geocoding to resolve addresses (using OpenStreetMap Nominatim API)
- Editable addresses and descriptions
- Optional manual assignment to known places (POIs)

#### 1.1.3 Kilometererfassung / Distance Recording
**Deutsch:**
- Erfassung der Fahrstrecke in Kilometern
- Berechnung aus Odometer-Differenz (Start zu Ende)
- Manuelle Korrektur möglich
- Validierung gegen GPS-Distanzberechnung (optional, als Qualitätsindikator)

**English:**
- Recording of trip distance in kilometers
- Calculation from odometer difference (start to end)
- Manual correction possible
- Validation against GPS distance calculation (optional, as quality indicator)

#### 1.1.4 Kostenberechnung / Cost Calculation
**Deutsch:**
- **Echte Kosten:** Berechnung basierend auf tatsächlichem Kraftstoffverbrauch
  - Verbrauch in Litern = (Tankstand Start - Tankstand Ende)
  - Kraftstoffkosten = Verbrauch × durchschnittlicher Literpreis
  - Zusätzliche Kosten: Maut, Parkgebühren (manuell erfassbar)
- **Steuerliche Kilometerpauschale (Deutschland):**
  - Standard: 0,30 € pro km (ab 1. km, konfigurierbar)
  - Ab 21. km: 0,38 € pro km (optional, konfigurierbar)
  - Fahrzeugklassen-abhängige Pauschalen (PKW, LKW, etc.)
- **Vergleichsanzeige:**
  - Echte Kosten vs. Kilometerpauschale
  - Ersparnis/Mehrkosten
  - Jahresrechnung (Hochrechnung)

**English:**
- **Real Costs:** Calculation based on actual fuel consumption
  - Consumption in liters = (Tank level start - Tank level end)
  - Fuel costs = Consumption × average price per liter
  - Additional costs: Tolls, parking fees (manually recordable)
- **Tax Mileage Rate (Germany):**
  - Standard: €0.30 per km (from 1st km, configurable)
  - From 21st km: €0.38 per km (optional, configurable)
  - Vehicle class-specific rates (car, truck, etc.)
- **Comparison Display:**
  - Real costs vs. mileage rate
  - Savings/additional costs
  - Annual calculation (projection)

#### 1.1.5 Lovelace-Karte / Lovelace Card
**Deutsch:**
- Erweiterung der bestehenden FWCAM-Karte
- Neue Registerkarte "Fahrtenbuch" / "Trip Log"
- Funktionen:
  - Tabelle aller Fahrten (sortierbar, filterbar)
  - Bearbeiten von Fahrten (Adressen, Zweck, Kategorie)
  - Löschen von Fahrten
  - Hinzufügen manueller Fahrten
  - Export-Funktion (CSV für Steuer)
  - Statistiken (Gesamt-km, Kosten, Durchschnittsverbrauch)
  - Pattern-Verwaltung (siehe unten)

**English:**
- Extension of existing FWCAM card
- New tab "Trip Log" / "Fahrtenbuch"
- Features:
  - Table of all trips (sortable, filterable)
  - Edit trips (addresses, purpose, category)
  - Delete trips
  - Add manual trips
  - Export function (CSV for tax)
  - Statistics (total km, costs, average consumption)
  - Pattern management (see below)

### 1.2 Datenschutz und Anonymisierung / Privacy and Anonymization

#### 1.2.1 Aktivierungs-Switch / Activation Switch
**Deutsch:**
- Separater Switch `switch.{vehicle_name}_trip_tracking_enabled`
- Standardmäßig deaktiviert (Opt-In)
- **Datenschutzhinweis beim Aktivieren:**
  ```
  ⚠️ DATENSCHUTZHINWEIS
  
  Das Fahrtenbuch erfasst:
  - Start- und Zielpositionen (GPS-Koordinaten)
  - Zeitstempel aller Fahrten
  - Adressen (automatisch aufgelöst)
  
  Als Fahrzeughalter sind Sie verpflichtet:
  ✓ Alle Nutzer des Fahrzeugs über die Aufzeichnung zu informieren
  ✓ Ggf. Einwilligung der Nutzer einzuholen
  ✓ DSGVO-konforme Datenspeicherung sicherzustellen
  
  Die Daten werden lokal in Home Assistant gespeichert und
  nicht an Dritte weitergegeben.
  
  Möchten Sie das Fahrtenbuch aktivieren?
  ```

**English:**
- Separate switch `switch.{vehicle_name}_trip_tracking_enabled`
- Disabled by default (Opt-In)
- **Privacy Notice on Activation:**
  ```
  ⚠️ PRIVACY NOTICE
  
  The trip log records:
  - Start and end positions (GPS coordinates)
  - Timestamps of all trips
  - Addresses (automatically resolved)
  
  As vehicle owner you are required to:
  ✓ Inform all users of the vehicle about the recording
  ✓ Obtain consent from users if necessary
  ✓ Ensure GDPR-compliant data storage
  
  Data is stored locally in Home Assistant and
  not shared with third parties.
  
  Do you want to activate the trip log?
  ```

#### 1.2.2 Zeitbasierte Anonymisierung / Time-Based Anonymization
**Deutsch:**
- Konfigurierbare Anonymisierungs-Zeiträume
- Beispiel: "Montag 08:00-09:00 und 17:00-18:00"
- In diesen Zeiträumen:
  - ✅ Fahrt wird erkannt und gezählt
  - ✅ Kilometer werden erfasst
  - ✅ Verbrauch wird erfasst
  - ❌ Keine GPS-Koordinaten gespeichert
  - ❌ Keine Adressen aufgelöst
  - ✅ Markierung als "Anonymisierte Fahrt"
  - ✅ Optional: Zuordnung zu Pattern (z.B. "Arbeitsweg")

**English:**
- Configurable anonymization time periods
- Example: "Monday 08:00-09:00 and 17:00-18:00"
- During these periods:
  - ✅ Trip is detected and counted
  - ✅ Kilometers are recorded
  - ✅ Consumption is recorded
  - ❌ No GPS coordinates stored
  - ❌ No addresses resolved
  - ✅ Marked as "Anonymized Trip"
  - ✅ Optional: Assignment to pattern (e.g., "Commute")

#### 1.2.3 Datenaufbewahrung / Data Retention
**Deutsch:**
- Konfigurierbare Aufbewahrungsdauer (Standard: 365 Tage)
- Optionen:
  - 30 Tage (1 Monat)
  - 90 Tage (3 Monate)
  - 365 Tage (1 Jahr)
  - Unbegrenzt (nur mit expliziter Bestätigung)
- Automatische Löschung älterer Daten
- Export vor Löschung (optional, automatisch)

**English:**
- Configurable retention period (default: 365 days)
- Options:
  - 30 days (1 month)
  - 90 days (3 months)
  - 365 days (1 year)
  - Unlimited (only with explicit confirmation)
- Automatic deletion of older data
- Export before deletion (optional, automatic)

### 1.3 Erweiterte Features / Advanced Features

#### 1.3.1 Fahrt-Pattern / Trip Patterns
**Deutsch:**
- Automatische Pattern-Erkennung nach manueller Bestätigung
- Pattern-Typen:
  - **Pendeln:** Zuhause ↔ Arbeit
  - **Routine:** Regelmäßige Fahrten zu bekannten Orten
  - **Tankstelle:** Fahrten zu Tankstellen
  - **Einkauf:** Fahrten zu Supermärkten/Geschäften
  - **Parken:** Fahrten zu bestimmten Parkplätzen
  - **Custom:** Benutzerdefinierte Pattern

- **Pattern-Definition:**
  - Start-Radius: 200m (Standard)
  - Ziel-Radius: 200m (Standard)
  - Zeitfenster: ±30 Minuten (Standard)
  - Wochentage (z.B. nur Mo-Fr)
  - Toleranz-Abweichung: 10% Kilometer

- **Pattern-Attribute:**
  - Name (z.B. "Arbeitsweg")
  - Kategorie (Geschäftlich/Privat)
  - Beschreibung
  - Anonymisiert (ja/nein)
  - Steuerlich relevant (ja/nein)
  - Zweck (für Fahrtenbuch)

**English:**
- Automatic pattern recognition after manual confirmation
- Pattern Types:
  - **Commute:** Home ↔ Work
  - **Routine:** Regular trips to known places
  - **Gas Station:** Trips to gas stations
  - **Shopping:** Trips to supermarkets/stores
  - **Parking:** Trips to specific parking lots
  - **Custom:** User-defined patterns

- **Pattern Definition:**
  - Start radius: 200m (default)
  - End radius: 200m (default)
  - Time window: ±30 minutes (default)
  - Weekdays (e.g., Mon-Fri only)
  - Tolerance deviation: 10% kilometers

- **Pattern Attributes:**
  - Name (e.g., "Commute")
  - Category (Business/Private)
  - Description
  - Anonymized (yes/no)
  - Tax relevant (yes/no)
  - Purpose (for logbook)

#### 1.3.2 POI-Integration / POI Integration
**Deutsch:**
- Definition von Point of Interests (POIs)
- POI-Typen:
  - Zuhause (automatisch aus HA-Konfiguration)
  - Arbeit
  - Tankstellen (automatisch aus Stationsdaten)
  - Supermärkte/Geschäfte
  - Parkplätze
  - Custom

- **POI-Eigenschaften:**
  - Name
  - GPS-Koordinaten
  - Radius (Erkennungsbereich)
  - Adresse
  - Kategorie
  - Icon

- **Automatische Erkennung:**
  - Wenn Fahrt in POI-Radius startet/endet
  - Automatische Zuordnung
  - Vorschlag zur Pattern-Erstellung

**English:**
- Definition of Points of Interest (POIs)
- POI Types:
  - Home (automatically from HA configuration)
  - Work
  - Gas Stations (automatically from station data)
  - Supermarkets/Stores
  - Parking Lots
  - Custom

- **POI Properties:**
  - Name
  - GPS coordinates
  - Radius (detection area)
  - Address
  - Category
  - Icon

- **Automatic Detection:**
  - When trip starts/ends in POI radius
  - Automatic assignment
  - Suggestion for pattern creation

#### 1.3.3 Pay2Park Integration (Vorbereitung)
**Deutsch:**
- Datenbasis für zukünftige Pay2Park-Integration
- Erfassung von:
  - Parkplatzbelegung-Zeiträume
  - Häufigkeit der Parkplatznutzung
  - Durchschnittliche Parkdauer
- Schema-Erweiterung für Parkgebühren

**English:**
- Data foundation for future Pay2Park integration
- Recording of:
  - Parking occupancy periods
  - Frequency of parking lot usage
  - Average parking duration
- Schema extension for parking fees

---

## 2. Technische Architektur / Technical Architecture

### 2.1 Datenmodell / Data Model

#### 2.1.1 Trip-Objekt / Trip Object
```python
@dataclass
class Trip:
    """Represents a recorded trip."""
    
    # Identifiers
    trip_id: int  # Auto-incrementing ID
    timestamp_start: datetime  # Trip start time
    timestamp_end: datetime  # Trip end time
    
    # Distance and consumption
    distance_km: float  # Distance in km
    odometer_start: float | None  # Odometer at start
    odometer_end: float | None  # Odometer at end
    fuel_level_start: float | None  # Tank level at start (liters)
    fuel_level_end: float | None  # Tank level at end (liters)
    fuel_consumed: float | None  # Fuel consumed (liters)
    consumption_rate: float | None  # L/100km
    
    # Location data (nullable for anonymized trips)
    start_latitude: float | None
    start_longitude: float | None
    start_address: str | None  # Resolved or manually entered
    start_poi_id: int | None  # Reference to POI
    end_latitude: float | None
    end_longitude: float | None
    end_address: str | None  # Resolved or manually entered
    end_poi_id: int | None  # Reference to POI
    
    # Cost calculation
    fuel_price_avg: float | None  # Average price during trip
    fuel_cost: float  # Real fuel cost
    additional_costs: float  # Tolls, parking, etc.
    total_cost: float  # fuel_cost + additional_costs
    tax_mileage_rate: float  # Applied rate (€/km)
    tax_mileage_amount: float  # Calculated mileage rate amount
    cost_difference: float  # Real vs. tax (negative = savings)
    
    # Classification
    purpose: str | None  # Free text or from pattern
    category: str  # "business", "private", "commute"
    pattern_id: int | None  # Reference to matched pattern
    is_anonymized: bool  # True if location data omitted
    
    # Metadata
    is_manual: bool  # True if manually added
    quality_score: float  # 0-1 based on data completeness
    notes: str | None  # User notes
    created_at: datetime
    updated_at: datetime
```

#### 2.1.2 TripPattern-Objekt / TripPattern Object
```python
@dataclass
class TripPattern:
    """Represents a recognized trip pattern."""
    
    # Identifiers
    pattern_id: int  # Auto-incrementing ID
    name: str  # e.g., "Commute to Work"
    
    # Pattern definition
    start_latitude: float
    start_longitude: float
    start_radius_m: float  # Detection radius
    end_latitude: float
    end_longitude: float
    end_radius_m: float  # Detection radius
    
    # Optional constraints
    weekdays: list[int] | None  # [0-6], None = all days
    time_window_start: time | None  # e.g., 07:30
    time_window_end: time | None  # e.g., 09:00
    distance_tolerance_percent: float  # ±% deviation
    
    # Classification
    category: str  # "business", "private", "commute"
    purpose: str  # For logbook entry
    is_anonymized: bool  # Anonymize future matches
    is_tax_relevant: bool  # For tax reporting
    
    # Statistics
    match_count: int  # Times this pattern was matched
    avg_distance_km: float
    avg_duration_minutes: float
    avg_fuel_consumption: float
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    last_matched: datetime | None
```

#### 2.1.3 POI-Objekt / POI Object
```python
@dataclass
class PointOfInterest:
    """Represents a Point of Interest."""
    
    # Identifiers
    poi_id: int  # Auto-incrementing ID
    name: str  # e.g., "Home", "Office", "Favorite Gas Station"
    
    # Location
    latitude: float
    longitude: float
    radius_m: float  # Detection radius (default 200m)
    address: str | None
    
    # Classification
    poi_type: str  # "home", "work", "gas_station", "shop", "parking", "custom"
    category: str | None
    icon: str  # Material Design Icon name
    
    # Metadata
    visit_count: int  # Times visited
    is_favorite: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
```

### 2.2 Datenspeicherung / Data Storage

#### 2.2.1 Storage Schema Extension
**Deutsch:**
Erweiterung der bestehenden `storage.py` für Trip-Daten:

**English:**
Extension of existing `storage.py` for trip data:

```python
# In load_data() default structure:
data = {
    "version": STORAGE_VERSION,
    # ... existing fields ...
    
    # Trip Tracking
    "trips": [],  # List of Trip objects (as dicts)
    "trip_patterns": [],  # List of TripPattern objects
    "pois": [],  # List of POI objects
    "next_trip_id": 1,
    "next_pattern_id": 1,
    "next_poi_id": 1,
    
    # Trip Tracking Configuration
    "trip_tracking_config": {
        "enabled": False,
        "privacy_notice_accepted": False,
        "privacy_notice_accepted_at": None,
        "min_trip_distance_km": 0.5,
        "merge_time_window_seconds": 300,  # 5 minutes
        "retention_days": 365,
        "auto_geocode": True,
        "geocode_service": "nominatim",  # OSM Nominatim
        
        # Anonymization
        "anonymization_schedules": [],  # List of time-based rules
        
        # Cost calculation
        "tax_mileage_rate_default": 0.30,  # €/km
        "tax_mileage_rate_above_20km": 0.38,  # €/km (from 21st km)
        "include_additional_costs": True,
    },
    
    # Statistics cache
    "trip_statistics": {
        "total_trips": 0,
        "total_distance_km": 0,
        "total_fuel_consumed": 0,
        "total_fuel_cost": 0,
        "avg_consumption_rate": 0,
        "last_calculated": None,
    },
}
```

#### 2.2.2 Retention Limits / Aufbewahrungsgrenzen
**Deutsch:**
- **Trips:** Basierend auf `retention_days` (Standard 365)
- **Patterns:** Unbegrenzt (benutzerdefiniert)
- **POIs:** Unbegrenzt (benutzerdefiniert)
- **Automatische Bereinigung:** Täglich um 03:00 Uhr

**English:**
- **Trips:** Based on `retention_days` (default 365)
- **Patterns:** Unlimited (user-defined)
- **POIs:** Unlimited (user-defined)
- **Automatic Cleanup:** Daily at 03:00 AM

#### 2.2.3 Performance Considerations / Performance-Überlegungen
**Deutsch:**
- Bei 2 Fahrten/Tag = 730 Trips/Jahr
- Durchschnittlich ~2 KB pro Trip
- Jährlicher Speicherbedarf: ~1.5 MB
- Akzeptabel für `.storage`-Dateien
- Optional: Archivierung älterer Daten in separate Datei

**English:**
- At 2 trips/day = 730 trips/year
- Average ~2 KB per trip
- Annual storage requirement: ~1.5 MB
- Acceptable for `.storage` files
- Optional: Archive older data to separate file

### 2.3 Neue Entitäten / New Entities

#### 2.3.1 Switch: Trip Tracking Enabled
```yaml
switch.{vehicle_name}_trip_tracking_enabled:
  state: off  # Default
  attributes:
    privacy_notice_accepted: false
    total_trips: 0
    last_trip: null
```

#### 2.3.2 Sensor: Trip Log
```yaml
sensor.{vehicle_name}_trip_log:
  state: 0  # Number of trips (today/this month/total - configurable)
  attributes:
    trips: [...]  # List of recent trips (last 50)
    total_trips: 730
    total_distance_km: 14600
    total_fuel_consumed: 950.5
    total_fuel_cost: 1663.88
    avg_consumption_rate: 6.5
    statistics:
      today: {...}
      this_week: {...}
      this_month: {...}
      this_year: {...}
```

#### 2.3.3 Sensor: Current Trip
```yaml
sensor.{vehicle_name}_current_trip:
  state: "in_progress"  # or "idle"
  attributes:
    trip_id: 731
    started_at: "2026-02-13T14:30:00"
    start_odometer: 45123.5
    start_fuel_level: 35.2
    distance_so_far: 5.3
    duration_minutes: 12
```

#### 2.3.4 Binary Sensor: On Trip
```yaml
binary_sensor.{vehicle_name}_on_trip:
  state: on  # on = currently on a trip
  device_class: moving
```

### 2.4 Services / Dienste

#### 2.4.1 hafwcma.add_trip (Manuelle Fahrt hinzufügen)
```yaml
service: hafwcma.add_trip
data:
  vehicle: "my_car"
  timestamp_start: "2026-02-13T08:00:00"
  timestamp_end: "2026-02-13T08:30:00"
  distance_km: 15.3
  start_address: "Home"
  end_address: "Office"
  category: "business"
  purpose: "Commute to work"
  fuel_cost: 2.50  # Optional
```

#### 2.4.2 hafwcma.edit_trip (Fahrt bearbeiten)
```yaml
service: hafwcma.edit_trip
data:
  vehicle: "my_car"
  trip_id: 123
  start_address: "Corrected Address"  # Optional
  category: "private"  # Optional
  purpose: "Shopping"  # Optional
  additional_costs: 5.00  # Optional (parking)
```

#### 2.4.3 hafwcma.delete_trip (Fahrt löschen)
```yaml
service: hafwcma.delete_trip
data:
  vehicle: "my_car"
  trip_id: 123
```

#### 2.4.4 hafwcma.create_pattern (Pattern erstellen)
```yaml
service: hafwcma.create_pattern
data:
  vehicle: "my_car"
  name: "Commute to Work"
  based_on_trip_id: 123  # Optional, use trip as template
  category: "business"
  purpose: "Work commute"
  is_anonymized: true
  weekdays: [0, 1, 2, 3, 4]  # Mon-Fri
```

#### 2.4.5 hafwcma.export_trips (Fahrten exportieren)
```yaml
service: hafwcma.export_trips
data:
  vehicle: "my_car"
  format: "csv"  # or "json", "excel"
  date_from: "2026-01-01"
  date_to: "2026-12-31"
  category_filter: "business"  # Optional
  output_path: "/config/www/exports/trips_2026.csv"
```

### 2.5 Trip Detection Logic / Fahrt-Erkennungslogik

#### 2.5.1 Trip Detection Algorithm
**Deutsch:**
Ähnlich zur Tankvorgang-Erkennung in `vehicle_tracker.py`:

**English:**
Similar to refueling detection in `vehicle_tracker.py`:

```python
class TripTracker:
    """Track vehicle trips and detect trip events."""
    
    MIN_TRIP_DISTANCE_KM = 0.5
    MERGE_TIME_WINDOW_SECONDS = 300  # 5 minutes
    STATIONARY_THRESHOLD_KM = 0.05  # 50 meters
    
    def update(self, vehicle_data: dict) -> dict:
        """Update with new vehicle data and detect trips.
        
        Returns:
            dict with trip_started, trip_ended, current_trip
        """
        
        # Create new snapshot
        current = VehicleSnapshot(...)
        
        # Detect trip start
        if self._is_trip_start(current):
            self._start_trip(current)
            return {"trip_started": True, "trip_id": self._current_trip_id}
        
        # Detect trip end
        if self._is_trip_end(current):
            trip = self._end_trip(current)
            return {"trip_ended": True, "trip": trip}
        
        # Update ongoing trip
        if self._current_trip:
            self._update_current_trip(current)
        
        return {"trip_started": False, "trip_ended": False}
    
    def _is_trip_start(self, snapshot: VehicleSnapshot) -> bool:
        """Detect if a trip is starting."""
        # Vehicle was stationary and now moving
        # Odometer increased
        # Position changed
        pass
    
    def _is_trip_end(self, snapshot: VehicleSnapshot) -> bool:
        """Detect if a trip has ended."""
        # Vehicle was moving and now stationary for MERGE_TIME_WINDOW
        # Odometer stable
        # Position stable
        pass
```

#### 2.5.2 Pattern Matching
```python
def match_pattern(trip: Trip, patterns: list[TripPattern]) -> TripPattern | None:
    """Match trip against known patterns."""
    
    for pattern in patterns:
        # Check location match
        if not _location_matches(trip, pattern):
            continue
        
        # Check time constraints
        if not _time_matches(trip, pattern):
            continue
        
        # Check distance tolerance
        if not _distance_matches(trip, pattern):
            continue
        
        return pattern
    
    return None
```

### 2.6 Geocoding Integration

#### 2.6.1 OpenStreetMap Nominatim API
**Deutsch:**
- Kostenloser Reverse-Geocoding-Service
- Anforderungen:
  - User-Agent Header (Integration-Name)
  - Rate Limit: 1 Request/Sekunde
  - Caching von Ergebnissen
- Privacy: Keine Registrierung erforderlich

**English:**
- Free reverse geocoding service
- Requirements:
  - User-Agent header (integration name)
  - Rate limit: 1 request/second
  - Caching of results
- Privacy: No registration required

```python
async def reverse_geocode(
    latitude: float,
    longitude: float,
    hass: HomeAssistant,
) -> str | None:
    """Resolve coordinates to address using OSM Nominatim."""
    
    # Check cache first
    cache_key = f"{latitude:.6f},{longitude:.6f}"
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]
    
    # Rate limiting
    await _rate_limiter.acquire()
    
    url = f"https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "json",
        "addressdetails": 1,
    }
    headers = {
        "User-Agent": "Home Assistant haFWCMA/1.0"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    address = _format_address(data)
                    _geocode_cache[cache_key] = address
                    return address
    except Exception as err:
        _LOGGER.warning("Geocoding failed: %s", err)
    
    return None
```

---

## 3. Lovelace Card Integration

### 3.1 Erweiterung der FWCAM-Karte / FWCAM Card Extension

**Deutsch:**
Neue Registerkarte in `fwcam-card`:

**English:**
New tab in `fwcam-card`:

```typescript
// New tab: Trip Log
{
  id: 'trips',
  label: 'Fahrtenbuch / Trip Log',
  content: TripLogView
}

// TripLogView component
interface TripLogView {
  // Trip table
  tripTable: {
    columns: ['Date', 'Start', 'End', 'Distance', 'Cost', 'Category', 'Actions'],
    sortable: true,
    filterable: {
      dateRange: DateRangePicker,
      category: ['All', 'Business', 'Private', 'Commute'],
      pattern: PatternSelector,
    },
    pagination: {
      rowsPerPage: [10, 25, 50, 100],
    },
  },
  
  // Statistics panel
  statistics: {
    period: ['Today', 'Week', 'Month', 'Year', 'All'],
    metrics: {
      totalTrips: number,
      totalDistance: number,
      totalCost: number,
      avgConsumption: number,
      costComparison: {
        realCost: number,
        taxRate: number,
        difference: number,
      },
    },
  },
  
  // Action buttons
  actions: {
    addTrip: Button,
    exportTrips: Button,
    managePatterns: Button,
    managePOIs: Button,
  },
}
```

### 3.2 Trip Edit Dialog
```typescript
interface TripEditDialog {
  tripId: number,
  fields: {
    startAddress: TextField,
    endAddress: TextField,
    startPOI: POISelector,
    endPOI: POISelector,
    category: Select<'business' | 'private' | 'commute'>,
    purpose: TextField,
    additionalCosts: NumberField,
    notes: TextArea,
  },
  actions: {
    save: Button,
    cancel: Button,
    delete: Button,
    createPattern: Button,  // Create pattern from this trip
  },
}
```

### 3.3 Pattern Management Dialog
```typescript
interface PatternManagementDialog {
  patterns: Array<{
    id: number,
    name: string,
    category: string,
    matchCount: number,
    isAnonymized: boolean,
  }>,
  actions: {
    createNew: Button,
    edit: (patternId) => void,
    delete: (patternId) => void,
    toggleAnonymize: (patternId) => void,
  },
}
```

---

## 4. Weitere Features und Ideen / Additional Features and Ideas

### 4.1 Vorgeschlagene Features / Suggested Features

#### 4.1.1 Statistiken und Reports / Statistics and Reports
**Deutsch:**
- Monatliche/Jährliche Zusammenfassungen
- Verbrauchs-Trends über Zeit
- Kosten-Trends
- Top-Routen (häufigste Fahrten)
- Export für Steuererklärung (ELSTER-kompatibel)

**English:**
- Monthly/Annual summaries
- Consumption trends over time
- Cost trends
- Top routes (most frequent trips)
- Export for tax returns (ELSTER-compatible)

#### 4.1.2 Automatisierungen / Automations
**Deutsch:**
- Benachrichtigung bei vergessener Fahrt-Kategorisierung
- Erinnerung zur monatlichen Überprüfung
- Automatische Backup-Erstellung
- Alert bei ungewöhnlich hohem Verbrauch

**English:**
- Notification for uncategorized trips
- Monthly review reminder
- Automatic backup creation
- Alert for unusually high consumption

#### 4.1.3 Integration mit anderen Systemen / Integration with Other Systems
**Deutsch:**
- Google Calendar (Termine → Fahrtzweck)
- Home Assistant Kalender
- Tankstellen-Daten (Tanken als spezielle Fahrt)
- Wetter-Daten (Einfluss auf Verbrauch)

**English:**
- Google Calendar (appointments → trip purpose)
- Home Assistant calendar
- Gas station data (refueling as special trip)
- Weather data (impact on consumption)

#### 4.1.4 Machine Learning Enhancements
**Deutsch:**
- Vorhersage von Fahrten (wann fährt der Nutzer normalerweise?)
- Automatische Zweck-Zuordnung basierend auf Zeit/Ort/Tag
- Verbrauchs-Vorhersage basierend auf Route und Wetter
- Anomalie-Erkennung (untypische Fahrten)

**English:**
- Trip prediction (when does user normally drive?)
- Automatic purpose assignment based on time/location/day
- Consumption prediction based on route and weather
- Anomaly detection (atypical trips)

### 4.2 Limitationen / Limitations

#### 4.2.1 Technische Limitationen / Technical Limitations
**Deutsch:**
- Abhängig von GPS-Genauigkeit der Fahrzeug-Integration
- Odometer-Updates müssen häufig genug sein (< 5 Min)
- Geocoding-Service erfordert Internetverbindung
- Speicherplatzbedarf bei vielen Fahrten
- Performance bei sehr großen Datenmengen (>10.000 Trips)

**English:**
- Dependent on GPS accuracy of vehicle integration
- Odometer updates must be frequent enough (< 5 min)
- Geocoding service requires internet connection
- Storage requirements for many trips
- Performance with very large datasets (>10,000 trips)

#### 4.2.2 Datenschutz-Limitationen / Privacy Limitations
**Deutsch:**
- DSGVO-Anforderungen müssen durch Nutzer sichergestellt werden
- Keine Garantie für lückenlose Anonymisierung bei Pattern
- Geocoding-Requests gehen an externe Services (OSM)
- Daten bleiben lokal, aber Backup könnte exponiert werden

**English:**
- GDPR requirements must be ensured by user
- No guarantee for complete anonymization with patterns
- Geocoding requests go to external services (OSM)
- Data stays local, but backup could be exposed

#### 4.2.3 Nicht implementierte Features / Features Not Implemented
**Deutsch:**
- Echtzeit-Navigation
- Route-Optimierung
- Multi-Fahrzeug-Routen-Vergleich
- Integration mit externen Fahrtenbuch-Apps
- Automatische Steuererklärung-Erstellung

**English:**
- Real-time navigation
- Route optimization
- Multi-vehicle route comparison
- Integration with external logbook apps
- Automatic tax return creation

---

## 5. Implementierungsplan / Implementation Plan

### Phase 1: Grundfunktionalität / Basic Functionality
- [ ] Trip detection logic in `vehicle_tracker.py`
- [ ] Trip data model in `models/__init__.py`
- [ ] Storage extension in `utils/storage.py`
- [ ] Trip tracking switch entity
- [ ] Privacy notice dialog
- [ ] Basic trip recording

### Phase 2: Kostenberechnung / Cost Calculation
- [ ] Fuel consumption calculation
- [ ] Cost calculation logic
- [ ] Tax mileage rate configuration
- [ ] Cost comparison calculations

### Phase 3: Geocoding Integration
- [ ] OSM Nominatim API integration
- [ ] Address resolution
- [ ] Geocoding cache
- [ ] Rate limiting

### Phase 4: Pattern Recognition
- [ ] Pattern data model
- [ ] Pattern matching algorithm
- [ ] Pattern creation from trips
- [ ] Automatic pattern application

### Phase 5: POI Management
- [ ] POI data model
- [ ] POI detection logic
- [ ] Home/Work auto-detection
- [ ] Gas station POI integration

### Phase 6: Anonymization
- [ ] Time-based anonymization rules
- [ ] Anonymization application logic
- [ ] Pattern anonymization
- [ ] Data retention cleanup

### Phase 7: Lovelace Card Extension
- [ ] Trip log tab
- [ ] Trip table with sorting/filtering
- [ ] Trip edit dialog
- [ ] Pattern management dialog
- [ ] POI management dialog
- [ ] Export functionality

### Phase 8: Services and Automations
- [ ] Add trip service
- [ ] Edit trip service
- [ ] Delete trip service
- [ ] Create pattern service
- [ ] Export trips service

### Phase 9: Testing and Documentation
- [ ] Unit tests for trip detection
- [ ] Integration tests
- [ ] User documentation (DE/EN)
- [ ] Privacy guide
- [ ] Migration guide

---

## 6. Sicherheit und Datenschutz / Security and Privacy

### 6.1 Datensicherheit / Data Security
**Deutsch:**
- Alle Daten lokal in `.storage`
- Keine Übertragung an externe Server (außer Geocoding)
- Verschlüsselung durch Home Assistant Storage
- Backup-Empfehlungen in Dokumentation

**English:**
- All data local in `.storage`
- No transmission to external servers (except geocoding)
- Encryption through Home Assistant Storage
- Backup recommendations in documentation

### 6.2 DSGVO-Konformität / GDPR Compliance
**Deutsch:**
- Opt-In Prinzip (standardmäßig deaktiviert)
- Explizite Einwilligung mit Hinweispflicht
- Datenminimierung durch Anonymisierung
- Recht auf Löschung (manuelle Datenlöschung)
- Transparenz (alle Daten einsehbar)
- Portabilität (Export-Funktion)

**English:**
- Opt-in principle (disabled by default)
- Explicit consent with notification requirement
- Data minimization through anonymization
- Right to deletion (manual data deletion)
- Transparency (all data viewable)
- Portability (export function)

### 6.3 Best Practices / Beste Praktiken
**Deutsch:**
- Regelmäßige Datenüberprüfung
- Kurze Aufbewahrungsfristen wählen
- Anonymisierung für Routinefahrten nutzen
- Sichere Backups mit Verschlüsselung
- Zugriffsrechte auf Home Assistant beschränken

**English:**
- Regular data review
- Choose short retention periods
- Use anonymization for routine trips
- Secure backups with encryption
- Restrict access to Home Assistant

---

## 7. Zusammenfassung und Empfehlungen / Summary and Recommendations

### 7.1 Zusammenfassung / Summary
**Deutsch:**
Das Trip-Tracking-Feature erweitert haFWCMA um eine umfassende Fahrtenbuch-Funktion mit Fokus auf:
- **Automatisierung:** Automatische Erkennung und Aufzeichnung
- **Kostenanalyse:** Vergleich echter Kosten vs. Kilometerpauschale
- **Pattern-Erkennung:** Intelligente Routinen-Erkennung
- **Datenschutz:** Opt-In, Anonymisierung, lokale Speicherung
- **Benutzerfreundlichkeit:** Integration in bestehende FWCAM-Karte

**English:**
The trip tracking feature extends haFWCMA with comprehensive logbook functionality focusing on:
- **Automation:** Automatic detection and recording
- **Cost Analysis:** Comparison of real costs vs. mileage rate
- **Pattern Recognition:** Intelligent routine detection
- **Privacy:** Opt-in, anonymization, local storage
- **User-Friendliness:** Integration into existing FWCAM card

### 7.2 Empfehlungen / Recommendations

#### 7.2.1 Implementierungs-Prioritäten / Implementation Priorities
**Deutsch:**
1. **Hoch:** Phase 1-3 (Grundfunktion, Kosten, Geocoding)
2. **Mittel:** Phase 4-6 (Pattern, POI, Anonymisierung)
3. **Niedrig:** Phase 7-8 (Card, Services)
4. **Optional:** Erweiterte Features (ML, Integrationen)

**English:**
1. **High:** Phase 1-3 (Basic function, costs, geocoding)
2. **Medium:** Phase 4-6 (Patterns, POI, anonymization)
3. **Low:** Phase 7-8 (Card, services)
4. **Optional:** Advanced features (ML, integrations)

#### 7.2.2 Technische Empfehlungen / Technical Recommendations
**Deutsch:**
- Nutzung der bestehenden `VehicleDataTracker`-Architektur
- Wiederverwendung von Geolocation-Utilities
- Ähnliche Storage-Patterns wie Tankhistorie
- Schrittweise Integration in bestehende Card
- Separate Feature-Flag für Beta-Testing

**English:**
- Use existing `VehicleDataTracker` architecture
- Reuse geolocation utilities
- Similar storage patterns as tank history
- Gradual integration into existing card
- Separate feature flag for beta testing

#### 7.2.3 Dokumentations-Empfehlungen / Documentation Recommendations
**Deutsch:**
- Ausführliche Datenschutz-Dokumentation (DE/EN)
- Setup-Guide mit Screenshots
- Beispiel-Automationen
- FAQ zu rechtlichen Fragen
- Video-Tutorial (optional)

**English:**
- Comprehensive privacy documentation (DE/EN)
- Setup guide with screenshots
- Example automations
- FAQ on legal questions
- Video tutorial (optional)

---

## 8. Offene Fragen / Open Questions

1. **Deutsch:** Soll die automatische Pattern-Erkennung opt-in oder opt-out sein?
   **English:** Should automatic pattern recognition be opt-in or opt-out?

2. **Deutsch:** Wie sollen mehrere Zwischenstopps behandelt werden (Trip-Chaining)?
   **English:** How should multiple intermediate stops be handled (trip chaining)?

3. **Deutsch:** Soll es eine Integration mit Apple CarPlay/Android Auto geben?
   **English:** Should there be integration with Apple CarPlay/Android Auto?

4. **Deutsch:** Wie detailliert sollen die Export-Formate für Steuererklärungen sein?
   **English:** How detailed should export formats for tax returns be?

5. **Deutsch:** Soll es eine Möglichkeit geben, Trips nachträglich zu splitten/mergen?
   **English:** Should there be an option to split/merge trips retroactively?

---

**Ende des Konzeptdokuments / End of Concept Document**

**Nächste Schritte / Next Steps:**
1. Review und Feedback zu diesem Konzept
2. Priorisierung der Features
3. Detaillierte technische Spezifikation für Phase 1
4. Beginn der Implementierung

**Hinweis / Note:**
Dieses Dokument ist als lebendiges Dokument gedacht und wird während der Implementierung aktualisiert.
