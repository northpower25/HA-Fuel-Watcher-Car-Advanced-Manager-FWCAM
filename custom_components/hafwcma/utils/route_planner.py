"""Route planner utilities for corridor-based fuel station search.

Provides classes and helpers for:
- Geocoding addresses via Nominatim
- Fetching route polylines from OSRM / OpenRouteService / Google Directions
- Building corridor polygons around routes
- Predicting fuel stop positions
- Ranking corridor stations by effective price
- Caching TankerKönig results with TTL
"""
from __future__ import annotations

import logging
import math
import time
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant

from .geolocation import calculate_distance, get_navigation_urls

_LOGGER = logging.getLogger(__name__)

# ── External API endpoints ──────────────────────────────────────────────────
OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/driving"
ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"

NOMINATIM_USER_AGENT = "HomeAssistant-haFWCMA/1.0"
REQUEST_TIMEOUT_SECONDS = 15
OSRM_TABLE_BASE_URL = "https://router.project-osrm.org/table/v1/driving"

# Distance (km) ahead of the predicted fuel stop used as the route re-entry
# point in the triangle-formula detour calculation.  Must be long enough that
# stations clearly off the route produce a meaningful positive detour value.
DETOUR_LOOKAHEAD_KM = 30.0

# Maximum number of refuel stops iterated in predict_fuel_stops_multi().
_MULTI_STOP_MAX_ITERATIONS = 20
# A stop is considered at the route end when within this many km of the total distance.
_ROUTE_END_TOLERANCE_KM = 0.5


# ── Internal routing helpers ────────────────────────────────────────────────

async def _fetch_route_osrm(
    origin: tuple[float, float],
    destination: tuple[float, float],
    waypoints: list[tuple[float, float]] | None = None,
    *,
    session: aiohttp.ClientSession | None = None,
) -> dict[str, Any]:
    """Fetch route from the OSRM public endpoint.

    Args:
        origin: (lat, lon) of the start point.
        destination: (lat, lon) of the end point.
        waypoints: Optional intermediate (lat, lon) stops.
        session: Optional aiohttp session to reuse.  Pass the HA-managed
            session (``async_get_clientsession(hass)``) to avoid blocking
            ``ssl.load_verify_locations`` calls in the event loop.

    Returns:
        Dict with ``polyline`` (list of (lat, lon)), ``distance_km`` and
        ``duration_s``, or an empty dict on error.
    """
    points = [origin] + (waypoints or []) + [destination]
    coords = ";".join(f"{lon},{lat}" for lat, lon in points)
    url = f"{OSRM_BASE_URL}/{coords}"
    params = {"overview": "full", "geometries": "geojson"}

    _own_session: aiohttp.ClientSession | None = None
    try:
        if session is None:
            _own_session = aiohttp.ClientSession()
            session = _own_session
        async with session.get(
            url,
            params=params,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
        ) as resp:
            if resp.status != 200:
                _LOGGER.error("OSRM API returned HTTP %d", resp.status)
                return {}
            data = await resp.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            _LOGGER.error("OSRM API error code: %s", data.get("code"))
            return {}

        route = data["routes"][0]
        # OSRM GeoJSON coordinates are [lon, lat] – convert to (lat, lon)
        polyline = [(lat, lon) for lon, lat in route["geometry"]["coordinates"]]
        return {
            "polyline": polyline,
            "distance_km": route["distance"] / 1000.0,
            "duration_s": route["duration"],
        }
    except Exception as err:
        _LOGGER.error("Error fetching OSRM route: %s", err)
        return {}
    finally:
        if _own_session is not None:
            await _own_session.close()


async def _fetch_route_openrouteservice(
    origin: tuple[float, float],
    destination: tuple[float, float],
    waypoints: list[tuple[float, float]] | None = None,
    api_key: str = "",
    *,
    session: aiohttp.ClientSession | None = None,
) -> dict[str, Any]:
    """Fetch route from OpenRouteService API.

    Args:
        origin: (lat, lon) of the start point.
        destination: (lat, lon) of the end point.
        waypoints: Optional intermediate (lat, lon) stops.
        api_key: ORS API key.
        session: Optional aiohttp session to reuse.  Pass the HA-managed
            session (``async_get_clientsession(hass)``) to avoid blocking
            ``ssl.load_verify_locations`` calls in the event loop.

    Returns:
        Dict with ``polyline``, ``distance_km``, ``duration_s``, or empty dict.
    """
    # ORS expects [[lon, lat], ...] coordinate arrays
    coords: list[list[float]] = [[origin[1], origin[0]]]
    for wp in (waypoints or []):
        coords.append([wp[1], wp[0]])
    coords.append([destination[1], destination[0]])

    headers = {"Authorization": api_key, "Content-Type": "application/json"}

    _own_session: aiohttp.ClientSession | None = None
    try:
        if session is None:
            _own_session = aiohttp.ClientSession()
            session = _own_session
        async with session.post(
            ORS_DIRECTIONS_URL,
            json={"coordinates": coords},
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
        ) as resp:
            if resp.status != 200:
                _LOGGER.error("ORS API returned HTTP %d", resp.status)
                return {}
            data = await resp.json()

        features = data.get("features", [])
        if not features:
            _LOGGER.error("ORS API returned no features")
            return {}

        feature = features[0]
        # ORS GeoJSON coordinates are [lon, lat] – convert to (lat, lon)
        polyline = [(lat, lon) for lon, lat in feature["geometry"]["coordinates"]]
        summary = feature.get("properties", {}).get("summary", {})
        return {
            "polyline": polyline,
            "distance_km": summary.get("distance", 0.0) / 1000.0,
            "duration_s": summary.get("duration", 0.0),
        }
    except Exception as err:
        _LOGGER.error("Error fetching ORS route: %s", err)
        return {}
    finally:
        if _own_session is not None:
            await _own_session.close()


async def _fetch_route_google(
    origin: tuple[float, float],
    destination: tuple[float, float],
    waypoints: list[tuple[float, float]] | None = None,
    api_key: str = "",
    *,
    session: aiohttp.ClientSession | None = None,
) -> dict[str, Any]:
    """Fetch route from Google Maps Directions API.

    Args:
        origin: (lat, lon) of the start point.
        destination: (lat, lon) of the end point.
        waypoints: Optional intermediate (lat, lon) stops.
        api_key: Google Maps API key.
        session: Optional aiohttp session to reuse.  Pass the HA-managed
            session (``async_get_clientsession(hass)``) to avoid blocking
            ``ssl.load_verify_locations`` calls in the event loop.

    Returns:
        Dict with ``polyline``, ``distance_km``, ``duration_s``, or empty dict.
    """
    params: dict[str, str] = {
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{destination[0]},{destination[1]}",
        "key": api_key,
    }
    if waypoints:
        params["waypoints"] = "|".join(f"{lat},{lon}" for lat, lon in waypoints)

    _own_session: aiohttp.ClientSession | None = None
    try:
        if session is None:
            _own_session = aiohttp.ClientSession()
            session = _own_session
        async with session.get(
            GOOGLE_DIRECTIONS_URL,
            params=params,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
        ) as resp:
            if resp.status != 200:
                _LOGGER.error("Google Directions API returned HTTP %d", resp.status)
                return {}
            data = await resp.json()

        if data.get("status") != "OK" or not data.get("routes"):
            _LOGGER.error("Google Directions API status: %s", data.get("status"))
            return {}

        route = data["routes"][0]
        legs = route.get("legs", [])
        total_distance = sum(leg["distance"]["value"] for leg in legs)
        total_duration = sum(leg["duration"]["value"] for leg in legs)
        polyline = _decode_google_polyline(route["overview_polyline"]["points"])
        return {
            "polyline": polyline,
            "distance_km": total_distance / 1000.0,
            "duration_s": float(total_duration),
        }
    except Exception as err:
        _LOGGER.error("Error fetching Google route: %s", err)
        return {}
    finally:
        if _own_session is not None:
            await _own_session.close()


def _decode_google_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decode a Google Maps encoded polyline string to (lat, lon) tuples."""
    result: list[tuple[float, float]] = []
    index = 0
    lat = 0
    lng = 0

    while index < len(encoded):
        shift = 0
        result_val = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result_val |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result_val >> 1) if (result_val & 1) else (result_val >> 1)
        lat += dlat

        shift = 0
        result_val = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result_val |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result_val >> 1) if (result_val & 1) else (result_val >> 1)
        lng += dlng

        result.append((lat / 1e5, lng / 1e5))

    return result


async def fetch_road_distances_osrm(
    origin: tuple[float, float],
    destinations: list[tuple[float, float]],
    *,
    session: aiohttp.ClientSession | None = None,
) -> list[float | None]:
    """Fetch one-way road distances from *origin* to each destination via OSRM table.

    Uses the OSRM ``/table/v1`` endpoint to compute road distances in a single
    HTTP request, which is much more efficient than N individual route calls.

    Args:
        origin: ``(lat, lon)`` of the single source point.
        destinations: List of ``(lat, lon)`` target points.
        session: Optional aiohttp session to reuse.  When provided the caller
            owns the session lifecycle (it will *not* be closed here).  When
            ``None`` a temporary session is created and closed automatically.
            Pass the HA-managed session (``async_get_clientsession(hass)``) to
            avoid the blocking ``ssl.load_verify_locations`` call in the event
            loop.

    Returns:
        List of road distances in km (one per destination), or ``None`` for
        any destination where the routing failed.  Returns an all-``None``
        list on network/API error.
    """
    if not destinations:
        return []

    # OSRM coordinates format: lon,lat (longitude first)
    all_points = [origin] + destinations
    coords_str = ";".join(f"{lon},{lat}" for lat, lon in all_points)

    # source index 0 = origin; destination indices = 1..N
    dest_indices = ";".join(str(i) for i in range(1, len(all_points)))
    url = f"{OSRM_TABLE_BASE_URL}/{coords_str}"
    params = {
        "sources": "0",
        "destinations": dest_indices,
        "annotations": "distance",
    }

    _own_session: aiohttp.ClientSession | None = None
    try:
        if session is None:
            _own_session = aiohttp.ClientSession()
            session = _own_session
        async with session.get(
            url,
            params=params,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
        ) as resp:
            if resp.status != 200:
                _LOGGER.warning("OSRM table API returned HTTP %d", resp.status)
                return [None] * len(destinations)
            data = await resp.json()

        if data.get("code") != "Ok":
            _LOGGER.warning("OSRM table API error: %s", data.get("code"))
            return [None] * len(destinations)

        # distances is a matrix: distances[source_row][dest_col] in metres
        distances_matrix = data.get("distances", [[]])
        if not distances_matrix or not distances_matrix[0]:
            return [None] * len(destinations)

        row = distances_matrix[0]
        result: list[float | None] = []
        for d in row:
            if d is None or d < 0:
                result.append(None)
            else:
                result.append(d / 1000.0)  # metres → km
        return result

    except Exception as err:
        _LOGGER.warning("Error fetching OSRM table distances: %s", err)
        return [None] * len(destinations)
    finally:
        if _own_session is not None:
            await _own_session.close()


async def fetch_road_distances_osrm_many_to_one(
    origins: list[tuple[float, float]],
    destination: tuple[float, float],
    *,
    session: aiohttp.ClientSession | None = None,
) -> list[float | None]:
    """Fetch road distances from each origin to a single destination via OSRM table.

    Uses the OSRM ``/table/v1`` endpoint with N sources and 1 destination so
    all distances are obtained in a single HTTP request.

    Args:
        origins: List of ``(lat, lon)`` source points.
        destination: Single ``(lat, lon)`` target point.
        session: Optional aiohttp session to reuse.  When provided the caller
            owns the session lifecycle (it will *not* be closed here).  When
            ``None`` a temporary session is created and closed automatically.
            Pass the HA-managed session (``async_get_clientsession(hass)``) to
            avoid the blocking ``ssl.load_verify_locations`` call in the event
            loop.

    Returns:
        List of road distances in km (one per origin), or ``None`` for any
        origin where the routing failed.  Returns an all-``None`` list on
        network/API error.
    """
    if not origins:
        return []

    # Append destination after origins; OSRM uses lon,lat order.
    # The loop `for lat, lon in all_points` unpacks (lat, lon) tuples, and
    # `f"{lon},{lat}"` emits them in the lon-first format required by OSRM.
    all_points = origins + [destination]
    coords_str = ";".join(f"{lon},{lat}" for lat, lon in all_points)

    # source indices cover origins (0..N-1); destination index is N
    src_indices = ";".join(str(i) for i in range(len(origins)))
    dest_index = str(len(origins))
    url = f"{OSRM_TABLE_BASE_URL}/{coords_str}"
    params = {
        "sources": src_indices,
        "destinations": dest_index,
        "annotations": "distance",
    }

    _own_session: aiohttp.ClientSession | None = None
    try:
        if session is None:
            _own_session = aiohttp.ClientSession()
            session = _own_session
        async with session.get(
            url,
            params=params,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
        ) as resp:
            if resp.status != 200:
                _LOGGER.warning("OSRM table API returned HTTP %d", resp.status)
                return [None] * len(origins)
            data = await resp.json()

        if data.get("code") != "Ok":
            _LOGGER.warning("OSRM table API error: %s", data.get("code"))
            return [None] * len(origins)

        # distances matrix: N rows (sources) × 1 column (destination)
        distances_matrix = data.get("distances", [])
        result: list[float | None] = []
        for row in distances_matrix:
            if not row or row[0] is None or row[0] < 0:
                result.append(None)
            else:
                result.append(row[0] / 1000.0)  # metres → km
        # Pad with None if the API returned fewer rows than expected
        while len(result) < len(origins):
            result.append(None)
        return result

    except Exception as err:
        _LOGGER.warning("Error fetching OSRM table distances (many-to-one): %s", err)
        return [None] * len(origins)
    finally:
        if _own_session is not None:
            await _own_session.close()


async def fetch_all_detour_distances_osrm(
    origin: tuple[float, float],
    waypoints: list[tuple[float, float]],
    destination: tuple[float, float],
    *,
    session: aiohttp.ClientSession | None = None,
) -> tuple[list[float | None], list[float | None], float | None]:
    """Fetch all triangle-formula distances in a single OSRM table call.

    Computes d(origin → each waypoint), d(each waypoint → destination), and
    d(origin → destination) using one HTTP request.  This is more reliable
    than two sequential calls because either all values succeed or all fail.

    With N waypoints the coordinate list sent to OSRM is::

        [origin(0), waypoint_0(1), waypoint_1(2), ..., waypoint_{N-1}(N), destination(N+1)]

    Setting ``sources = [0, 1, ..., N]`` (origin + N waypoints) and
    ``destinations = [1, 2, ..., N, N+1]`` (N waypoints + destination) causes
    OSRM to return an (N+1) × (N+1) distance matrix.  The columns correspond
    to the *destinations* list (indices 0..N-1 = waypoints, index N =
    destination), so we extract:

    * Row 0 (= origin), dest-col 0..N-1 → d(origin → waypoint_k) for k=0..N-1
    * Row 0 (= origin), dest-col N       → d(origin → destination)  [baseline]
    * Row k+1 (= waypoint_k), dest-col N → d(waypoint_k → destination) for k=0..N-1

    Args:
        origin: ``(lat, lon)`` of the route reference point (P_near).
        waypoints: ``(lat, lon)`` list of N gas-station points.
        destination: ``(lat, lon)`` of the route re-entry point (P_after).
        session: Optional aiohttp session to reuse.  When provided the caller
            owns the session lifecycle (it will *not* be closed here).  When
            ``None`` a temporary session is created and closed automatically.
            Pass the HA-managed session (``async_get_clientsession(hass)``) to
            avoid the blocking ``ssl.load_verify_locations`` call in the event
            loop.

    Returns:
        Tuple ``(origin_to_wp, wp_to_dest, baseline)`` where distances are in
        km.  ``origin_to_wp[k]`` is d(origin → waypoints[k]),
        ``wp_to_dest[k]`` is d(waypoints[k] → destination), and ``baseline``
        is d(origin → destination).  Any value is ``None`` when OSRM could
        not compute that particular distance.  Returns all-``None`` lists on
        network or API error.
    """
    if not waypoints:
        return [], [], None

    N = len(waypoints)
    # Points: [origin(0), wp_0(1), ..., wp_N-1(N), destination(N+1)]
    all_points = [origin] + waypoints + [destination]
    coords_str = ";".join(f"{lon},{lat}" for lat, lon in all_points)

    # sources = origin + all waypoints; destinations = all waypoints + destination
    src_indices = ";".join(str(i) for i in range(N + 1))
    dest_indices = ";".join(str(i) for i in range(1, N + 2))
    url = f"{OSRM_TABLE_BASE_URL}/{coords_str}"
    params = {
        "sources": src_indices,
        "destinations": dest_indices,
        "annotations": "distance",
    }

    def _safe_km(row: list, col: int) -> float | None:
        if col < len(row) and row[col] is not None and row[col] >= 0:
            return row[col] / 1000.0
        return None

    _own_session: aiohttp.ClientSession | None = None
    try:
        if session is None:
            _own_session = aiohttp.ClientSession()
            session = _own_session
        async with session.get(
            url,
            params=params,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
        ) as resp:
            if resp.status != 200:
                _LOGGER.warning("OSRM table API returned HTTP %d", resp.status)
                return [None] * N, [None] * N, None
            data = await resp.json()

        if data.get("code") != "Ok":
            _LOGGER.warning("OSRM table API error: %s", data.get("code"))
            return [None] * N, [None] * N, None

        # distances matrix: (N+1) rows × (N+1) columns
        matrix = data.get("distances", [])

        # Row 0: distances from origin to each waypoint (cols 0..N-1) and to
        # destination (col N).
        origin_to_wp: list[float | None] = [None] * N
        baseline: float | None = None
        if matrix:
            row0 = matrix[0]
            for k in range(N):
                origin_to_wp[k] = _safe_km(row0, k)
            baseline = _safe_km(row0, N)

        # Rows 1..N: distances from each waypoint to destination (col N).
        wp_to_dest: list[float | None] = [None] * N
        for k in range(N):
            if k + 1 < len(matrix):
                wp_to_dest[k] = _safe_km(matrix[k + 1], N)

        return origin_to_wp, wp_to_dest, baseline

    except Exception as err:
        _LOGGER.warning("Error fetching OSRM detour distances: %s", err)
        return [None] * N, [None] * N, None
    finally:
        if _own_session is not None:
            await _own_session.close()

def _compute_polyline_detour_km(
    station_lat: float,
    station_lon: float,
    polyline: list[tuple[float, float]],
    lookahead_km: float = DETOUR_LOOKAHEAD_KM,
) -> float:
    """Compute the route detour for a station using the straight-line triangle formula.

    Finds the nearest point on the route polyline to the station (P_near),
    then locates a point *lookahead_km* further along the polyline (P_after),
    and returns::

        detour = max(0, d_sl(P_near → station) + d_sl(station → P_after)
                        - d_sl(P_near → P_after))

    where ``d_sl`` is the straight-line (Haversine) distance.

    Using the **per-station nearest route point** as P_near is critical for
    accuracy.  A shared reference point (e.g. the predicted fuel stop) placed
    several km past a station's highway exit inflates the detour dramatically
    when the formula is evaluated with OSRM road distances.  Straight-line
    distances in the triangle formula cancel out most of the curvature error
    because all three legs are measured consistently, giving results that
    closely match Google Maps insertion-based detour values.

    Args:
        station_lat: Station latitude.
        station_lon: Station longitude.
        polyline: Route as a list of ``(lat, lon)`` tuples.
        lookahead_km: How far ahead of P_near to place P_after.  Defaults to
            :data:`DETOUR_LOOKAHEAD_KM`.

    Returns:
        Detour in km (always ≥ 0), rounded to 2 decimal places.
    """
    if not polyline or len(polyline) < 2:
        _LOGGER.debug(
            "_compute_polyline_detour_km: polyline is empty or too short – returning 0"
        )
        return 0.0

    # ── Step 1: project station onto the nearest polyline segment ──────────
    min_perp_dist = float("inf")
    nearest_lat = polyline[0][0]
    nearest_lon = polyline[0][1]
    nearest_dist_along = 0.0  # km along the polyline to the nearest point
    cumulative_km = 0.0

    for i in range(len(polyline) - 1):
        lat1, lon1 = polyline[i]
        lat2, lon2 = polyline[i + 1]
        seg_len = calculate_distance(lat1, lon1, lat2, lon2)

        # Project station onto segment [A, B] using a planar approximation.
        # Works well for the short polyline segments used by OSRM/ORS.
        dx = lat2 - lat1
        dy = lon2 - lon1
        len_sq = dx * dx + dy * dy
        # Threshold for a degenerate segment (start == end, coincident points).
        # Using 1e-18 rather than 0 to guard against floating-point rounding.
        if len_sq < 1e-18:
            t = 0.0
        else:
            t = max(
                0.0,
                min(
                    1.0,
                    ((station_lat - lat1) * dx + (station_lon - lon1) * dy) / len_sq,
                ),
            )

        proj_lat = lat1 + t * dx
        proj_lon = lon1 + t * dy
        perp = calculate_distance(station_lat, station_lon, proj_lat, proj_lon)

        if perp < min_perp_dist:
            min_perp_dist = perp
            nearest_lat = proj_lat
            nearest_lon = proj_lon
            nearest_dist_along = cumulative_km + t * seg_len

        cumulative_km += seg_len

    # ── Step 2: find P_after (lookahead_km further along the polyline) ─────
    target_km = nearest_dist_along + lookahead_km
    ahead_lat = polyline[-1][0]
    ahead_lon = polyline[-1][1]
    tmp_cumulative = 0.0

    for i in range(len(polyline) - 1):
        lat1, lon1 = polyline[i]
        lat2, lon2 = polyline[i + 1]
        seg_len = calculate_distance(lat1, lon1, lat2, lon2)
        if tmp_cumulative + seg_len >= target_km:
            t = (target_km - tmp_cumulative) / seg_len if seg_len > 0 else 0.0
            ahead_lat = lat1 + t * (lat2 - lat1)
            ahead_lon = lon1 + t * (lon2 - lon1)
            break
        tmp_cumulative += seg_len

    # ── Step 3: straight-line triangle formula ─────────────────────────────
    d_near_to_station = calculate_distance(nearest_lat, nearest_lon, station_lat, station_lon)
    d_station_to_ahead = calculate_distance(station_lat, station_lon, ahead_lat, ahead_lon)
    d_near_to_ahead = calculate_distance(nearest_lat, nearest_lon, ahead_lat, ahead_lon)

    detour = max(0.0, d_near_to_station + d_station_to_ahead - d_near_to_ahead)
    return round(detour, 2)


async def async_enrich_stations_with_road_detour(
    stations: list[dict[str, Any]],
    nearest_route_point: tuple[float, float] | None = None,
    ahead_route_point: tuple[float, float] | None = None,
    lookahead_km: float = DETOUR_LOOKAHEAD_KM,
    *,
    polyline: list[tuple[float, float]] | None = None,
    session: aiohttp.ClientSession | None = None,
) -> list[dict[str, Any]]:
    """Add road-based detour distances to corridor station dicts.

    Calculates the actual extra kilometres a driver incurs when diverting from
    the route to visit a station.

    **Preferred mode – polyline provided**:

    When *polyline* is supplied each station's detour is computed independently
    using :func:`_compute_polyline_detour_km`.  That function projects the
    station onto the nearest segment of the route polyline to obtain a
    per-station P_near, then finds a point *lookahead_km* further along the
    polyline (P_after), and evaluates the triangle formula with straight-line
    distances::

        detour = max(0, d_sl(P_near → station) + d_sl(station → P_after)
                        - d_sl(P_near → P_after))

    Using per-station P_near points (rather than a shared predicted-stop
    reference) is essential for accuracy when stations lie before or after
    the predicted fuel stop on the route.

    **Legacy mode – no polyline**:

    When *polyline* is ``None`` the function falls back to the original
    OSRM-based triangle formula using the shared *nearest_route_point* and
    *ahead_route_point*.  This mode is kept for backward compatibility.

    Args:
        stations: List of station dicts.  Each must have ``lat``/``latitude``
            and ``lng``/``longitude`` fields.
        nearest_route_point: ``(lat, lon)`` reference point used in legacy
            mode only (ignored when *polyline* is supplied).
        ahead_route_point: ``(lat, lon)`` re-entry point used in legacy mode
            only (ignored when *polyline* is supplied).
        lookahead_km: Distance ahead of P_near used to place P_after (both
            modes).
        polyline: Full route polyline as a list of ``(lat, lon)`` tuples.
            When provided, enables the accurate per-station detour calculation
            without any external network calls.
        session: Optional aiohttp session for legacy-mode OSRM requests.

    Returns:
        New list of station dicts with ``road_detour_km`` set to the computed
        extra distance and ``detour_km`` preserved as the original estimate.
    """
    if not stations:
        return []

    # ── Preferred mode: per-station polyline-based triangle formula ─────────
    if polyline is not None:
        enriched: list[dict[str, Any]] = []
        for st in stations:
            lat = float(st.get("lat") or st.get("latitude") or 0.0)
            lon = float(st.get("lng") or st.get("longitude") or 0.0)
            updated = dict(st)
            updated["road_detour_km"] = _compute_polyline_detour_km(
                lat, lon, polyline, lookahead_km
            )
            enriched.append(updated)
        return enriched

    # ── Legacy mode: OSRM-based triangle formula ────────────────────────────
    if nearest_route_point is None:
        # No reference point available – return stations unchanged
        return list(stations)

    station_coords: list[tuple[float, float]] = []
    for st in stations:
        lat = st.get("lat") or st.get("latitude", 0.0)
        lon = st.get("lng") or st.get("longitude", 0.0)
        station_coords.append((float(lat), float(lon)))

    if ahead_route_point is not None:
        # Single combined OSRM call: get d(P_near→stations), d(stations→P_after),
        # and d(P_near→P_after) all at once.  This avoids the reliability issue
        # of two sequential calls where the second call might fail while the
        # first succeeds, which previously triggered the incorrect 2× fallback.
        one_way_km, station_to_ahead_km, road_baseline = (
            await fetch_all_detour_distances_osrm(
                nearest_route_point, station_coords, ahead_route_point,
                session=session,
            )
        )
        # Use the OSRM-measured P_near→P_after distance as baseline; fall back
        # to the polyline estimate when OSRM could not compute it.
        baseline_km = road_baseline if road_baseline is not None else lookahead_km
    else:
        one_way_km = await fetch_road_distances_osrm(
            nearest_route_point, station_coords, session=session
        )
        station_to_ahead_km = [None] * len(stations)
        baseline_km = lookahead_km

    legacy_enriched: list[dict[str, Any]] = []
    for st, ow_km, s2a_km in zip(stations, one_way_km, station_to_ahead_km):
        updated = dict(st)
        if ow_km is not None:
            if s2a_km is not None:
                # Triangle formula: actual extra km vs. staying on route
                triangle_detour = max(0.0, ow_km + s2a_km - baseline_km)
                updated["road_detour_km"] = round(triangle_detour, 2)
            else:
                # Fallback: round-trip from same point (ahead_route_point absent
                # or OSRM could not route from this station to P_after)
                updated["road_detour_km"] = round(ow_km * 2.0, 2)
        else:
            # OSRM failed for this station – keep existing value or straight-line
            updated["road_detour_km"] = st.get("road_detour_km") or st.get("detour_km", 0.0)
        legacy_enriched.append(updated)

    return legacy_enriched


def select_categorized_stations(
    stations: list[dict[str, Any]],
) -> dict[str, dict[str, Any] | None]:
    """Select at least 3 stations in distinct recommendation categories.

    Categories:
        - **cheapest**: lowest ``effective_price_eur_per_l`` (road detour included)
        - **nearest**: smallest ``road_detour_km``
        - **middle**: best remaining station by effective price that differs
          from both *cheapest* and *nearest*

    Args:
        stations: Stations already enriched with ``road_detour_km`` and
            ``effective_price_eur_per_l`` keys.

    Returns:
        Dict with keys ``"cheapest"``, ``"nearest"``, ``"middle"``; each value
        is a station dict or ``None`` if insufficient stations are available.
    """
    if not stations:
        return {"cheapest": None, "nearest": None, "middle": None}

    # Best by effective price (road detour included)
    by_effective = sorted(
        stations, key=lambda s: s.get("effective_price_eur_per_l", float("inf"))
    )
    # Best by road detour (nearest to the route)
    by_detour = sorted(
        stations, key=lambda s: s.get("road_detour_km", float("inf"))
    )

    cheapest = by_effective[0] if by_effective else None
    nearest = by_detour[0] if by_detour else None

    # Avoid duplicate: if cheapest == nearest (same station), nearest uses runner-up
    cheapest_id = _station_id(cheapest)
    nearest_id = _station_id(nearest)
    if cheapest_id and cheapest_id == nearest_id and len(by_detour) > 1:
        nearest = by_detour[1]
        nearest_id = _station_id(nearest)

    # Middle: best effective price among stations that are neither cheapest nor nearest
    excluded = {cheapest_id, nearest_id}
    remaining = [s for s in by_effective if _station_id(s) not in excluded]
    middle = remaining[0] if remaining else None

    return {"cheapest": cheapest, "nearest": nearest, "middle": middle}


def _station_id(station: dict[str, Any] | None) -> str | None:
    """Return a stable identity key for a station dict (for deduplication)."""
    if station is None:
        return None
    sid = station.get("station_id") or station.get("id")
    if sid:
        return str(sid)
    lat = station.get("lat") or station.get("latitude")
    lon = station.get("lng") or station.get("longitude")
    return f"{lat},{lon}"


# ── RoutePlanner ────────────────────────────────────────────────────────────

class RoutePlanner:
    """Manages a single active route for a vehicle.

    Stores route state including the polyline, destination string, waypoints,
    and total distance.  Provides helpers for geocoding (forward) and for
    delegating to the configured routing provider.
    """

    def __init__(self) -> None:
        """Initialise with no active route."""
        self._active_route: dict[str, Any] | None = None

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def active_route(self) -> dict[str, Any] | None:
        """Return the full active route data dict, or None."""
        return self._active_route

    @property
    def is_active(self) -> bool:
        """Return True when a route is currently active."""
        return self._active_route is not None

    @property
    def destination(self) -> str | None:
        """Return the human-readable destination string."""
        if self._active_route:
            return self._active_route.get("destination")
        return None

    @property
    def waypoints(self) -> list[str]:
        """Return the list of waypoint strings (may be empty)."""
        if self._active_route:
            return self._active_route.get("waypoints", [])
        return []

    @property
    def total_distance_km(self) -> float | None:
        """Return total route distance in km, or None."""
        if self._active_route:
            return self._active_route.get("total_distance_km")
        return None

    @property
    def route_polyline(self) -> list[tuple[float, float]]:
        """Return route polyline as list of (lat, lon) tuples."""
        if self._active_route:
            return self._active_route.get("route_polyline", [])
        return []

    # ── Async methods ────────────────────────────────────────────────────────

    async def async_geocode_address(
        self, hass: HomeAssistant, address: str
    ) -> tuple[float, float] | None:
        """Forward-geocode an address string to (lat, lon) via Nominatim.

        Args:
            hass: Home Assistant instance used to obtain the shared aiohttp
                session, avoiding blocking ``ssl.load_verify_locations`` calls.
            address: Free-form address string.

        Returns:
            ``(lat, lon)`` tuple, or ``None`` on failure.
        """
        from homeassistant.helpers.aiohttp_client import async_get_clientsession
        session = async_get_clientsession(hass)
        try:
            async with session.get(
                NOMINATIM_SEARCH_URL,
                params={"q": address, "format": "json", "limit": 1},
                headers={"User-Agent": NOMINATIM_USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
            ) as resp:
                if resp.status != 200:
                    _LOGGER.error("Nominatim search returned HTTP %d", resp.status)
                    return None
                data = await resp.json()

            if not data:
                _LOGGER.warning("No geocoding results for address: %s", address)
                return None
            return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception as err:
            _LOGGER.error("Error geocoding address '%s': %s", address, err)
            return None

    async def async_calculate_route(
        self,
        hass: HomeAssistant,
        origin: tuple[float, float],
        destination: tuple[float, float],
        waypoints: list[tuple[float, float]] | None = None,
        provider: str = "osrm",
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Calculate a route and return polyline + metadata.

        Args:
            hass: Home Assistant instance used to obtain the shared aiohttp
                session, avoiding blocking ``ssl.load_verify_locations`` calls.
            origin: ``(lat, lon)`` start position.
            destination: ``(lat, lon)`` end position.
            waypoints: Optional intermediate ``(lat, lon)`` stops.
            provider: Routing provider – ``"osrm"``, ``"openrouteservice"``, or
                ``"google"``.
            api_key: API key required by ORS and Google providers.

        Returns:
            Dict with ``polyline``, ``distance_km``, ``duration_s`` on success,
            or an empty dict on error.
        """
        from homeassistant.helpers.aiohttp_client import async_get_clientsession
        session = async_get_clientsession(hass)
        if provider == "google":
            return await _fetch_route_google(origin, destination, waypoints, api_key or "", session=session)
        if provider == "openrouteservice":
            return await _fetch_route_openrouteservice(
                origin, destination, waypoints, api_key or "", session=session
            )
        return await _fetch_route_osrm(origin, destination, waypoints, session=session)

    async def async_set_route(self, route_data: dict[str, Any]) -> None:
        """Persist new route data as the active route.

        Args:
            route_data: Route dict containing at minimum ``destination`` and
                ``route_polyline``.
        """
        self._active_route = route_data
        _LOGGER.info(
            "Route set: destination=%s, distance=%.1f km",
            route_data.get("destination"),
            route_data.get("total_distance_km", 0.0),
        )

    async def async_cancel_route(self) -> None:
        """Cancel the active route and clear stored state."""
        if self._active_route:
            _LOGGER.info(
                "Route cancelled: destination=%s", self._active_route.get("destination")
            )
        self._active_route = None


# ── RouteCorridorCalculator ─────────────────────────────────────────────────

class RouteCorridorCalculator:
    """Builds a corridor polygon around a route polyline.

    Uses perpendicular offset segments to create a series of rectangles that
    approximate the corridor.  Point-in-polygon tests use ray-casting.
    """

    def calculate_corridor(
        self,
        polyline: list[tuple[float, float]],
        width_km: float,
    ) -> list[tuple[float, float]]:
        """Calculate a closed corridor polygon around the polyline.

        Args:
            polyline: Route as list of ``(lat, lon)`` points.
            width_km: Half-width of the corridor in km (total width = 2×).

        Returns:
            List of ``(lat, lon)`` vertices forming a closed polygon, or an
            empty list when the polyline has fewer than 2 points.
        """
        if len(polyline) < 2:
            return []

        left_side: list[tuple[float, float]] = []
        right_side: list[tuple[float, float]] = []

        for i in range(len(polyline) - 1):
            lat1, lon1 = polyline[i]
            lat2, lon2 = polyline[i + 1]

            dlat = lat2 - lat1
            dlon = lon2 - lon1
            length = math.sqrt(dlat * dlat + dlon * dlon)
            if length < 1e-10:
                continue

            # Approximate degree conversions at the segment midpoint
            lat_mid = (lat1 + lat2) / 2.0
            lat_deg_per_km = 1.0 / 111.0
            lon_deg_per_km = 1.0 / (111.0 * math.cos(math.radians(lat_mid)))

            # Perpendicular unit vector scaled to corridor half-width
            perp_lat = (-dlon / length) * width_km * lat_deg_per_km
            perp_lon = (dlat / length) * width_km * lon_deg_per_km

            if i == 0:
                left_side.append((lat1 + perp_lat, lon1 + perp_lon))
                right_side.append((lat1 - perp_lat, lon1 - perp_lon))

            left_side.append((lat2 + perp_lat, lon2 + perp_lon))
            right_side.append((lat2 - perp_lat, lon2 - perp_lon))

        # Closed polygon: left side forward then right side reversed
        polygon = left_side + list(reversed(right_side))
        if polygon:
            polygon.append(polygon[0])

        return polygon

    def is_point_in_corridor(
        self,
        lat: float,
        lon: float,
        polygon: list[tuple[float, float]],
    ) -> bool:
        """Test whether a point lies inside the corridor polygon (ray-casting).

        Args:
            lat: Point latitude.
            lon: Point longitude.
            polygon: Closed polygon as ``(lat, lon)`` vertices.

        Returns:
            ``True`` if the point is inside the polygon.
        """
        if not polygon:
            return False

        n = len(polygon)
        inside = False
        j = n - 1

        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > lon) != (yj > lon)) and (
                lat < (xj - xi) * (lon - yi) / (yj - yi) + xi
            ):
                inside = not inside
            j = i

        return inside


# ── FuelStopPredictor ────────────────────────────────────────────────────────

class FuelStopPredictor:
    """Predicts where along a route the vehicle will need to refuel."""

    def predict_fuel_stop(
        self,
        polyline: list[tuple[float, float]],
        current_position: tuple[float, float],
        tank_level_liters: float,
        tank_capacity: float,
        consumption_l_per_100km: float,
        safety_buffer_pct: float = 15.0,
    ) -> dict[str, Any]:
        """Calculate the predicted refuel point along the route.

        Args:
            polyline: Route as ``(lat, lon)`` list.
            current_position: Current vehicle ``(lat, lon)``.
            tank_level_liters: Current fuel level in litres.
            tank_capacity: Full tank capacity in litres (unused here but kept
                for interface consistency).
            consumption_l_per_100km: Average consumption rate.
            safety_buffer_pct: Percentage of fuel to keep in reserve.

        Returns:
            Dict with ``predicted_distance_km``, ``predicted_lat``,
            ``predicted_lon``, ``km_remaining_to_stop``,
            ``safety_buffer_pct``.  Empty dict on invalid input.
        """
        if not polyline or consumption_l_per_100km <= 0:
            return {}

        usable_fuel = tank_level_liters * (1.0 - safety_buffer_pct / 100.0)
        max_range_km = (usable_fuel / consumption_l_per_100km) * 100.0

        projection = self.project_position_on_route(
            polyline, current_position[0], current_position[1]
        )
        current_dist_km = projection["distance_along_route_km"]
        target_dist_km = current_dist_km + max_range_km

        predicted_point = self._find_point_at_distance(polyline, target_dist_km)
        if predicted_point is None:
            predicted_point = polyline[-1]
            target_dist_km = self._total_route_distance(polyline)

        km_remaining = max(0.0, target_dist_km - current_dist_km)

        return {
            "predicted_distance_km": round(target_dist_km, 2),
            "predicted_lat": predicted_point[0],
            "predicted_lon": predicted_point[1],
            "km_remaining_to_stop": round(km_remaining, 2),
            "safety_buffer_pct": safety_buffer_pct,
        }

    def predict_fuel_stops_multi(
        self,
        polyline: list[tuple[float, float]],
        current_position: tuple[float, float],
        tank_level_liters: float,
        tank_capacity: float,
        consumption_l_per_100km: float,
        safety_buffer_pct: float = 15.0,
    ) -> list[dict[str, Any]]:
        """Calculate all predicted refuel stops for a long route.

        The first stop uses the current ``tank_level_liters``; every subsequent
        stop assumes the vehicle was refuelled to a full tank (``tank_capacity``)
        at the previous stop.

        Args:
            polyline: Route as ``(lat, lon)`` list.
            current_position: Current vehicle ``(lat, lon)``.
            tank_level_liters: Current fuel level in litres.
            tank_capacity: Full tank capacity in litres.
            consumption_l_per_100km: Average consumption rate.
            safety_buffer_pct: Percentage of fuel to keep in reserve.

        Returns:
            List of stop dicts (same format as :meth:`predict_fuel_stop`).
            Empty list when no stop is needed or on invalid input.
        """
        if not polyline or consumption_l_per_100km <= 0:
            return []

        total_route_km = self._total_route_distance(polyline)
        stops: list[dict[str, Any]] = []
        current_pos = current_position
        current_fuel = tank_level_liters

        for _ in range(_MULTI_STOP_MAX_ITERATIONS):
            stop = self.predict_fuel_stop(
                polyline=polyline,
                current_position=current_pos,
                tank_level_liters=current_fuel,
                tank_capacity=tank_capacity,
                consumption_l_per_100km=consumption_l_per_100km,
                safety_buffer_pct=safety_buffer_pct,
            )
            if not stop:
                break
            # If the predicted stop is at or beyond the route end, no further stop needed
            if stop["predicted_distance_km"] >= total_route_km - _ROUTE_END_TOLERANCE_KM:
                break
            stops.append(stop)
            # Assume a full tank refuel; continue from the predicted stop location
            current_pos = (stop["predicted_lat"], stop["predicted_lon"])
            current_fuel = tank_capacity

        return stops

    def project_position_on_route(
        self,
        polyline: list[tuple[float, float]],
        current_lat: float,
        current_lon: float,
    ) -> dict[str, Any]:
        """Find the nearest point on the polyline and return the route distance.

        Args:
            polyline: Route as ``(lat, lon)`` list.
            current_lat: Current latitude.
            current_lon: Current longitude.

        Returns:
            Dict with ``distance_along_route_km``, ``nearest_lat``,
            ``nearest_lon``, ``segment_index``.
        """
        if not polyline:
            return {
                "distance_along_route_km": 0.0,
                "nearest_lat": current_lat,
                "nearest_lon": current_lon,
                "segment_index": 0,
            }

        min_dist = float("inf")
        best_segment = 0
        best_point = polyline[0]
        distance_to_best = 0.0
        cumulative_km = 0.0

        for i in range(len(polyline) - 1):
            lat1, lon1 = polyline[i]
            lat2, lon2 = polyline[i + 1]
            seg_len = calculate_distance(lat1, lon1, lat2, lon2)

            proj_lat, proj_lon, t = self._project_point_on_segment(
                current_lat, current_lon, lat1, lon1, lat2, lon2
            )
            dist = calculate_distance(current_lat, current_lon, proj_lat, proj_lon)

            if dist < min_dist:
                min_dist = dist
                best_segment = i
                best_point = (proj_lat, proj_lon)
                distance_to_best = cumulative_km + t * seg_len

            cumulative_km += seg_len

        return {
            "distance_along_route_km": distance_to_best,
            "nearest_lat": best_point[0],
            "nearest_lon": best_point[1],
            "segment_index": best_segment,
        }

    def _project_point_on_segment(
        self,
        px: float,
        py: float,
        ax: float,
        ay: float,
        bx: float,
        by: float,
    ) -> tuple[float, float, float]:
        """Project point P onto segment AB; return (proj_lat, proj_lon, t)."""
        dx = bx - ax
        dy = by - ay
        len_sq = dx * dx + dy * dy
        if len_sq < 1e-12:
            return ax, ay, 0.0
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / len_sq))
        return ax + t * dx, ay + t * dy, t

    def _find_point_at_distance(
        self,
        polyline: list[tuple[float, float]],
        target_km: float,
    ) -> tuple[float, float] | None:
        """Return the interpolated (lat, lon) at *target_km* along the polyline."""
        cumulative = 0.0
        for i in range(len(polyline) - 1):
            lat1, lon1 = polyline[i]
            lat2, lon2 = polyline[i + 1]
            seg_len = calculate_distance(lat1, lon1, lat2, lon2)
            if cumulative + seg_len >= target_km:
                t = (target_km - cumulative) / seg_len if seg_len > 0 else 0.0
                return lat1 + t * (lat2 - lat1), lon1 + t * (lon2 - lon1)
            cumulative += seg_len
        return None

    def find_point_at_distance(
        self,
        polyline: list[tuple[float, float]],
        target_km: float,
    ) -> tuple[float, float] | None:
        """Return the interpolated (lat, lon) at *target_km* along the polyline.

        Public API for callers outside this class.

        Args:
            polyline: Route as ``(lat, lon)`` list.
            target_km: Distance along the polyline in km.

        Returns:
            Interpolated ``(lat, lon)`` at the requested distance, or ``None``
            when *target_km* is beyond the end of the polyline.
        """
        return self._find_point_at_distance(polyline, target_km)

    def _total_route_distance(self, polyline: list[tuple[float, float]]) -> float:
        """Return the total length of the polyline in km."""
        total = 0.0
        for i in range(len(polyline) - 1):
            total += calculate_distance(
                polyline[i][0], polyline[i][1],
                polyline[i + 1][0], polyline[i + 1][1],
            )
        return total


# ── CorridorStationRanker ────────────────────────────────────────────────────

class CorridorStationRanker:
    """Ranks fuel stations inside the route corridor by effective price.

    Effective price accounts for the extra fuel burned driving to the station
    and back to the route (the detour penalty).
    """

    def rank_stations(
        self,
        stations: list[dict[str, Any]],
        fuel_needed_liters: float,
        consumption_l_per_100km: float,
    ) -> list[dict[str, Any]]:
        """Sort stations by effective price, cheapest first.

        Each station dict must have ``lat``/``latitude``, ``lng``/``longitude``,
        and ``price`` keys.  Uses ``road_detour_km`` (round-trip road distance)
        when available, falling back to ``detour_km`` (straight-line).
        Adds ``effective_price_eur_per_l``, ``total_cost_eur``,
        and ``navigation_urls`` to each result dict.

        Args:
            stations: Raw station dicts from TankerKönig (or similar).
            fuel_needed_liters: Litres to fill at the station.
            consumption_l_per_100km: Vehicle consumption rate.

        Returns:
            Stations sorted ascending by ``effective_price_eur_per_l``.
        """
        ranked: list[dict[str, Any]] = []

        for station in stations:
            lat = station.get("lat") or station.get("latitude")
            lon = station.get("lng") or station.get("longitude")
            price = station.get("price")

            if lat is None or lon is None or price is None:
                continue

            # Prefer road-based round-trip detour; fall back to straight-line
            detour_km = float(
                station.get("road_detour_km")
                if station.get("road_detour_km") is not None
                else station.get("detour_km", 0.0)
            )
            effective_price = self.calculate_effective_price(
                price, detour_km, consumption_l_per_100km, fuel_needed_liters
            )
            total_cost = effective_price * fuel_needed_liters
            nav_urls = get_navigation_urls(lat, lon, station.get("name", ""))

            enriched = dict(station)
            enriched.update(
                {
                    "detour_km": round(detour_km, 2),
                    "effective_price_eur_per_l": round(effective_price, 4),
                    "total_cost_eur": round(total_cost, 2),
                    "navigation_urls": nav_urls,
                }
            )
            ranked.append(enriched)

        ranked.sort(key=lambda s: s["effective_price_eur_per_l"])
        return ranked

    def calculate_effective_price(
        self,
        station_price: float,
        detour_km: float,
        consumption_l_per_100km: float,
        litres_needed: float,
    ) -> float:
        """Calculate the effective price per litre including detour fuel cost.

        Formula::

            detour_fuel_cost = (detour_km / 100) × consumption × station_price
            effective_price  = station_price + (detour_fuel_cost / litres_needed)

        Args:
            station_price: Headline price per litre at the station.
            detour_km: Total detour distance (to station + back to route).
            consumption_l_per_100km: Vehicle consumption rate.
            litres_needed: Litres to be purchased.

        Returns:
            Effective price per litre as a float.
        """
        if litres_needed <= 0:
            return station_price
        detour_fuel_cost = (detour_km / 100.0) * consumption_l_per_100km * station_price
        return station_price + (detour_fuel_cost / litres_needed)


# ── PredictiveStationCache ───────────────────────────────────────────────────

class PredictiveStationCache:
    """Simple in-memory cache for TankerKönig station results with TTL.

    Uses a coarse 2-decimal-place coordinate grid (≈ 1 km) as the cache key
    so that nearby positions share cached results.
    """

    def __init__(self, ttl_seconds: int = 300) -> None:
        """Initialise cache with given TTL (default: 5 minutes).

        Args:
            ttl_seconds: Seconds before a cache entry expires.
        """
        self._ttl = ttl_seconds
        self._cache: dict[str, dict[str, Any]] = {}

    # ── Cache key ─────────────────────────────────────────────────────────

    def _make_key(self, lat: float, lon: float) -> str:
        """Build cache key; 2 decimal places ≈ 1.1 km grid."""
        return f"{round(lat, 2)},{round(lon, 2)}"

    # ── Public API ─────────────────────────────────────────────────────────

    def get_cached(self, lat: float, lon: float) -> list[dict[str, Any]] | None:
        """Return cached station list, or ``None`` if missing or expired.

        Args:
            lat: Latitude of the query position.
            lon: Longitude of the query position.

        Returns:
            List of station dicts, or ``None``.
        """
        key = self._make_key(lat, lon)
        entry = self._cache.get(key)
        if not entry:
            return None
        if time.time() - entry["timestamp"] > self._ttl:
            del self._cache[key]
            return None
        return entry["stations"]

    def update_cache(
        self, lat: float, lon: float, stations: list[dict[str, Any]]
    ) -> None:
        """Store fresh station results in the cache.

        Args:
            lat: Latitude of the query position.
            lon: Longitude of the query position.
            stations: Station dicts to cache.
        """
        key = self._make_key(lat, lon)
        self._cache[key] = {"timestamp": time.time(), "stations": stations}

    def calculate_predicted_position(
        self,
        polyline: list[tuple[float, float]],
        current_lat: float,
        current_lon: float,
        speed_kmh: float = 100.0,
    ) -> tuple[float, float] | None:
        """Predict vehicle position in 10 minutes for pre-fetch optimisation.

        Args:
            polyline: Active route polyline.
            current_lat: Current latitude.
            current_lon: Current longitude.
            speed_kmh: Assumed travel speed in km/h (default 100).

        Returns:
            Predicted ``(lat, lon)`` in 10 minutes, or ``None`` if beyond the
            route end.
        """
        predictor = FuelStopPredictor()
        projection = predictor.project_position_on_route(
            polyline, current_lat, current_lon
        )
        current_dist = projection["distance_along_route_km"]
        # Distance covered in 10 minutes at speed_kmh
        predicted_dist = current_dist + (speed_kmh / 6.0)
        return predictor._find_point_at_distance(polyline, predicted_dist)
