# Route Planner – User Guide

**Feature:** Route Corridor Station Search  
**Available since:** v0.2.20  
**Geographic scope:** Germany only (requires TankerKönig API)

---

## Overview

The **Route Planner** tab in the FWCAM dashboard lets you plan a trip and automatically find the cheapest fuel stations along your route. Instead of searching in a fixed radius around your current position, the Route Planner builds a configurable **corridor** (buffer zone) around your planned route and only evaluates stations within that corridor.

Key features:

- 🗺️ **Route calculation** via OSRM (free), OpenRouteService, or Google Maps API
- 🔍 **Corridor-based station search** – only stations on your way count
- ⛽ **Fuel stop prediction** – estimates where you will need to refuel based on current fuel level and average consumption
- 💰 **Effective price ranking** – accounts for the detour cost to reach each station
- 📱 **Navigation links** – one-tap navigation to the best station via Google Maps, Waze, or Apple Maps
- 🔔 **Telegram notifications** – receive route start/cancel confirmations including an immediate fuel stop prediction with the top-5 corridor stations

---

## Prerequisites

| Requirement | Details |
|---|---|
| TankerKönig API key | Already configured in the FWCAM integration settings |
| Vehicle with known fuel level | Integration must track tank level (via `device_tracker` or OBD/Freematics) |
| Average consumption configured | Set in the integration settings for accurate fuel stop prediction |
| Internet access | Required for geocoding (Nominatim) and routing APIs |
| Germany-only | TankerKönig only covers German fuel stations |

---

## Entities Used for Fuel Stop Prediction

The fuel stop prediction relies on three data sources from the FWCAM integration:

| Data | Entity | Description |
|---|---|---|
| **Vehicle position** | Linked `device_tracker` entity (configured as `position_entity`) | Current GPS coordinates used as the route starting point. Example: `device_tracker.my_car` |
| **Range / tank level** | `sensor.[entry_id]_range` | Remaining range in km – primary source for the prediction. The tank level in litres from `sensor.[entry_id]_tank_level` is used as fallback. |
| **Average consumption** | `sensor.[entry_id]_average_consumption_history` | Average fuel consumption in l/100 km derived from historical trip data (`avg_consumption_rate`). |

**Simplified prediction formula:**

```
usable_range = (tank_litres × (1 − safety_buffer%)) / consumption × 100
stop_km      = current_position_on_route + usable_range
```

A **15 % safety buffer** is applied by default to keep a reserve for detours and traffic.

> **Tip:** If tank level or consumption data is unavailable, no fuel stop hint is included in the notification. Make sure the entities above are linked in the integration settings.

---

## The Route Planner Tab

Open the FWCAM card in your Home Assistant dashboard and switch to the **🗺️ Route Planner** tab.

### Input Fields

| Field | Description | Default |
|---|---|---|
| **Destination** | Address or city name (e.g. `München Hauptbahnhof`) | – |
| **Waypoints** | Optional intermediate stops, comma-separated (e.g. `Augsburg, Ingolstadt`) | – |
| **Corridor Width (km)** | Buffer around the route to search for stations (1–50 km) | 5 km |
| **Routing Provider** | Service used to calculate the route | OSRM (free) |
| **Google API Key** | Only required when *Google Maps* is selected as provider | – |

### Routing Providers

| Provider | Cost | Notes |
|---|---|---|
| **OSRM** | Free, no key needed | Uses the public OSRM demo server. Good accuracy for German roads. |
| **OpenRouteService** | Free tier available | Requires a free API key from [openrouteservice.org](https://openrouteservice.org). Enter the key in the integration settings. |
| **Google Maps** | Paid (Google Cloud) | Most accurate routing. Requires a Google Maps Directions API key entered directly in the card. |

### Buttons

| Button | Action |
|---|---|
| **Start Route** | Geocodes the destination/waypoints, fetches the route, finds corridor stations, updates the route sensors |
| **Cancel Route** | Stops the active route and clears all route sensors |

---

## Step-by-Step: Plan a Route

1. Open the **FWCAM card** in Home Assistant.
2. Click the **🗺️ Route Planner** tab.
3. Enter your **Destination** in the text field (free-text address or city name).
4. Optionally enter **Waypoints** (comma-separated).
5. Adjust **Corridor Width** if needed (default 5 km is suitable for most motorway trips).
6. Select your preferred **Routing Provider** (OSRM is recommended for casual use).
7. Click **Start Route**.
8. The card will show a green **✅ Route Active** banner once the route is calculated.

---

## Active Route Display

Once a route is active, the card shows:

### Route Summary
- **Destination** – the geocoded target address
- **Distance** – total route distance in km
- **Corridor Width** – the configured search buffer
- **Predicted Fuel Stop** – estimated distance ahead where refueling will be needed (~X km)

### 🏆 Best Corridor Station
The single best station ranked by **effective price** (see below):
- **Station name**
- **Price per litre** (€/l)
- **Detour** – extra distance to reach the station from the route
- **Effective Price** – total cost per litre after accounting for the detour
- Navigation links: **Google Maps**, **Waze**, **Apple Maps**

### 📋 Top Corridor Stations
A table of the top 3 ranked stations showing the same columns as above.

---

## How the Effective Price Is Calculated

The Route Planner ranks stations not just by pump price but by the **effective price per litre**, which accounts for the detour:

```
effective_price = pump_price + (detour_km × fuel_cost_per_km)
```

where `fuel_cost_per_km` is derived from:
```
fuel_cost_per_km = average_consumption_l_per_100km / 100 × pump_price
```

This means a station that is 2 km off the route but 3 cents cheaper per litre may still be the best value depending on your vehicle's consumption.

---

## Sensor Entities

The Route Planner creates the following Home Assistant sensor entities (auto-detected by the FWCAM card):

| Entity | Description |
|---|---|
| `sensor.[car_name]_active_route` | Route state (`active` / `idle`) and route attributes |
| `sensor.[car_name]_predicted_fuel_stop` | Distance ahead (km) where a fuel stop is predicted |
| `sensor.[car_name]_corridor_best_station` | Best ranked corridor station with navigation URLs |
| `sensor.[car_name]_corridor_stations` | List of all ranked corridor stations |

### `active_route` Attributes

| Attribute | Type | Description |
|---|---|---|
| `destination` | string | Geocoded destination address |
| `total_distance_km` | float | Total route distance in km |
| `corridor_width_km` | float | Configured corridor width |
| `routing_provider` | string | Provider used (`osrm` / `openrouteservice` / `google`) |

### `corridor_best_station` Attributes

| Attribute | Type | Description |
|---|---|---|
| `station_name` | string | Station name |
| `price_per_litre` | float | Pump price in €/l |
| `detour_km` | float | Detour distance in km |
| `effective_price_eur_per_l` | float | Effective price after detour cost |
| `google_maps_url` | string | Direct navigation link |
| `waze_url` | string | Waze navigation link |
| `apple_maps_url` | string | Apple Maps navigation link |

---

## Using Services Directly

You can also trigger the Route Planner via Home Assistant services (e.g. in automations or scripts):

### `hafwcma.set_route`

```yaml
service: hafwcma.set_route
data:
  config_entry_id: "your_config_entry_id"
  destination: "München Hauptbahnhof"
  waypoints:
    - "Augsburg"
    - "Ingolstadt"
  corridor_width_km: 5
  routing_provider: "osrm"
  # google_api_key: "AIza..." # only for Google Maps provider
```

| Parameter | Required | Type | Default | Description |
|---|---|---|---|---|
| `config_entry_id` | ✅ | string | – | Your FWCAM config entry ID |
| `destination` | ✅ | string | – | Destination address |
| `waypoints` | ❌ | list[string] | `[]` | Intermediate stops |
| `corridor_width_km` | ❌ | float | `5.0` | Corridor width in km |
| `routing_provider` | ❌ | string | `"osrm"` | `osrm` / `openrouteservice` / `google` |
| `google_api_key` | ❌ | string | `""` | Google Maps API key (only for `google` provider) |

### `hafwcma.cancel_route`

```yaml
service: hafwcma.cancel_route
data:
  config_entry_id: "your_config_entry_id"
```

---

## Telegram Notifications & Commands

If Telegram is configured in your FWCAM integration, you will receive notifications when:

- **Route starts** – confirmation with destination, distance, predicted fuel stop (km), and the **top-5 corridor stations** (price/l + distance from route)
- **Route is cancelled** – confirmation message

### Telegram Bot Commands for Route Planning

| Command | Description |
|---|---|
| `/route start <address>` | Start a route to the given destination |
| `/route start <address> <km>` | Start a route with a custom corridor width (1–50 km). Example: `/route start Munich Central 10` |
| `/route stop` | Stop/cancel the active route |
| `/routestatus` | Show active route status including fuel stop prediction and best station |
| `/routecancel` | Cancel the active route (same as `/route stop`) |
| `/corridor [km]` | Adjust corridor width for the running route |
| `/help` | Show all available commands |

To configure Telegram, see [TELEGRAM_SETUP.md](../TELEGRAM_SETUP.md).

---

## Card Configuration

The Route Planner tab is enabled by default. To hide it, add `show_route_planner: false` to your card YAML:

```yaml
type: custom:fwcam-card
entity: sensor.my_car_fuel_price
show_route_planner: false
```

---

## Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| "Start Route" does nothing | Missing destination or JS error | Open browser console (F12) and check for errors; ensure destination field is not empty |
| Route Active but no stations shown | No TankerKönig stations found in corridor | Increase corridor width or check TankerKönig API key |
| Destination not found | Geocoding failed (Nominatim) | Try a more specific address (include city, street number) |
| Route distance shows `—` | Routing provider returned an error | Switch provider (try OSRM); check network connectivity |
| Predicted fuel stop unavailable | Tank level or consumption not configured | Ensure fuel level and average consumption are reported by your vehicle integration |
| Google Maps provider fails | Invalid API key or billing not enabled | Verify the key in [Google Cloud Console](https://console.cloud.google.com) with Directions API enabled |

---

## Limitations

- **Germany only** – TankerKönig station data covers Germany exclusively.
- **OSRM public server** – the free OSRM demo server may be rate-limited; for high-frequency use, set up a self-hosted OSRM instance.
- **Fuel type** – the corridor search uses the fuel type configured in the integration settings.
- **Real-time updates** – station prices update at the TankerKönig polling interval configured in the integration (default: every 30 minutes).

---

## Related Documentation

- [ROUTENPLANUNG_ANLEITUNG_DE.md](ROUTENPLANUNG_ANLEITUNG_DE.md) – German version of this guide
- [TELEGRAM_SETUP.md](../TELEGRAM_SETUP.md) – Configure Telegram notifications
- [VEHICLE_ENTITIES.md](../VEHICLE_ENTITIES.md) – Connect your vehicle to report fuel level
- [docs/dev_docs/ROUTE_CORRIDOR_STATION_SEARCH_CONCEPT.md](../dev_docs/ROUTE_CORRIDOR_STATION_SEARCH_CONCEPT.md) – Technical design document
