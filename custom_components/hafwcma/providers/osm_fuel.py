"""OSM Overpass API provider for fuel stations on international routes.

Used when the predicted fuel-stop point lies outside Germany (where
Tankerkönig has no coverage).  Returns basic station data without
fuel prices.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time as dt_time
from typing import Any, Optional
from urllib.parse import quote

import aiohttp

_LOGGER = logging.getLogger(__name__)

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

# Maps abbreviated English/OSM day names to Python weekday ints (0=Mon).
_OSM_DAYS: dict[str, int] = {
    "mo": 0,
    "tu": 1,
    "we": 2,
    "th": 3,
    "fr": 4,
    "sa": 5,
    "su": 6,
}


def _parse_osm_time(t: str) -> Optional[dt_time]:
    """Parse ``HH:MM`` time string to :class:`datetime.time`, or ``None``."""
    try:
        parts = t.strip().split(":")
        return dt_time(int(parts[0]), int(parts[1]))
    except (ValueError, AttributeError, IndexError):
        return None


def _osm_days_to_weekdays(day_spec: str) -> list[int]:
    """Convert an OSM day-range string to a list of weekday ints.

    Handles:
    * Single day: ``"Mo"``, ``"Su"`` …
    * Range: ``"Mo-Fr"``, ``"Sa-Su"`` …
    * Comma-separated: ``"Mo,We,Fr"``
    """
    weekdays: list[int] = []
    if not day_spec:
        return weekdays
    for part in day_spec.replace(";", ",").split(","):
        part = part.strip()
        if "-" in part:
            halves = part.split("-", 1)
            left = halves[0].strip().lower()
            right = halves[1].strip().lower()
            # Only treat as day range if both sides are known day abbreviations
            start = _OSM_DAYS.get(left)
            end = _OSM_DAYS.get(right)
            if start is not None and end is not None:
                if start <= end:
                    weekdays.extend(range(start, end + 1))
                else:
                    # wrap-around (e.g. Fr-Mo)
                    weekdays.extend(range(start, 7))
                    weekdays.extend(range(0, end + 1))
            # If either token is not a day abbreviation, skip (e.g. time ranges)
        else:
            d = _OSM_DAYS.get(part.lower())
            if d is not None:
                weekdays.append(d)
    return weekdays


def is_osm_station_open_at(opening_hours: str, check_dt: datetime) -> Optional[bool]:
    """Return ``True`` if the OSM station is open at *check_dt*, ``False`` if closed,
    or ``None`` if the opening_hours string is unparseable (caller should not filter).

    Handles the most common OSM formats:
    * ``24/7``
    * ``HH:MM-HH:MM`` (applies to all days)
    * ``Mo-Fr HH:MM-HH:MM; Sa-Su HH:MM-HH:MM``
    * ``Mo-Su HH:MM-HH:MM``

    Complex OSM rule-sets (public holidays, month ranges, etc.) are treated as
    *unknown* → returns ``None`` so the caller does not filter the station out.
    """
    if not opening_hours:
        return None

    oh = opening_hours.strip()

    if oh in ("24/7", "24/7;", "24h", "0-24"):
        return True

    weekday = check_dt.weekday()
    check_time = check_dt.time().replace(second=0, microsecond=0)

    # Split on semicolons to get individual rules
    matched = False
    parsed_any_rule = False

    for rule in oh.split(";"):
        rule = rule.strip()
        if not rule:
            continue

        # Split into day-spec and time-spec tokens
        # e.g. "Mo-Fr 06:00-22:00" → day_part="Mo-Fr", time_part="06:00-22:00"
        tokens = rule.split()
        if len(tokens) == 2:
            day_part, time_part = tokens
        elif len(tokens) == 1 and "-" in tokens[0] and ":" in tokens[0]:
            # Only a time range, no day spec → applies every day
            day_part = "Mo-Su"
            time_part = tokens[0]
        else:
            # Unrecognised format – skip this rule
            continue

        # Parse time range
        if "-" not in time_part:
            continue
        time_parts = time_part.split("-", 1)
        start_t = _parse_osm_time(time_parts[0])
        end_t = _parse_osm_time(time_parts[1])
        if start_t is None or end_t is None:
            continue

        # Parse day spec
        applicable = _osm_days_to_weekdays(day_part)
        if not applicable:
            continue

        parsed_any_rule = True

        if weekday not in applicable:
            continue

        # Check time
        if start_t <= end_t:
            if start_t <= check_time <= end_t:
                matched = True
                break
        else:
            # Midnight-spanning slot
            if check_time >= start_t or check_time <= end_t:
                matched = True
                break

    if not parsed_any_rule:
        # Could not parse any rule → don't filter
        return None

    return matched


async def fetch_osm_fuel_stations(
    session: aiohttp.ClientSession,
    lat: float,
    lon: float,
    radius_m: int = 5000,
    max_stations: int = 10,
) -> list[dict[str, Any]]:
    """Fetch fuel stations near (*lat*, *lon*) from the OSM Overpass API.

    Returns a list of station dicts compatible with the corridor-station
    pipeline.  Station dicts include ``lat``, ``lng``, ``name``, ``address``,
    ``opening_hours``, ``source="osm"``; ``price`` is always ``None`` because
    OSM does not carry live fuel-price data.

    Args:
        session: aiohttp client session.
        lat: Latitude of the search centre.
        lon: Longitude of the search centre.
        radius_m: Search radius in metres (default 5 000 m / 5 km).
        max_stations: Maximum number of stations to return.

    Returns:
        List of station dicts (may be empty on error or no results).
    """
    query = (
        f"[out:json][timeout:15];"
        f"("
        f'node["amenity"="fuel"](around:{radius_m},{lat},{lon});'
        f'way["amenity"="fuel"](around:{radius_m},{lat},{lon});'
        f");"
        f"out center tags;"
    )

    try:
        async with session.post(
            OVERPASS_API_URL,
            data={"data": query},
            timeout=aiohttp.ClientTimeout(total=20),
            headers={"User-Agent": "HA-FWCAM/1.0 (HomeAssistant fuel watcher)"},
        ) as resp:
            if resp.status != 200:
                _LOGGER.warning(
                    "Overpass API returned HTTP %d for (%.4f, %.4f)", resp.status, lat, lon
                )
                return []
            data = await resp.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
        _LOGGER.warning("Overpass API request failed: %s", err)
        return []

    stations: list[dict[str, Any]] = []
    for elem in data.get("elements", []):
        tags = elem.get("tags") or {}

        # Coordinates
        if elem.get("type") == "node":
            s_lat = elem.get("lat")
            s_lon = elem.get("lon")
        elif elem.get("type") == "way":
            center = elem.get("center") or {}
            s_lat = center.get("lat")
            s_lon = center.get("lon")
        else:
            continue

        if s_lat is None or s_lon is None:
            continue

        # Name / brand
        name = (
            tags.get("name")
            or tags.get("brand")
            or tags.get("operator")
            or "Tankstelle"
        )

        # Address components
        street = tags.get("addr:street", "")
        housenumber = tags.get("addr:housenumber", "")
        postcode = tags.get("addr:postcode", "")
        city = (
            tags.get("addr:city")
            or tags.get("addr:town")
            or tags.get("addr:village")
            or tags.get("addr:municipality")
            or ""
        )
        street_part = f"{street} {housenumber}".strip() if housenumber else street
        city_part = f"{postcode} {city}".strip()
        if street_part and city_part:
            address = f"{street_part}, {city_part}"
        elif street_part:
            address = street_part
        elif city_part:
            address = city_part
        else:
            address = ""

        opening_hours = tags.get("opening_hours", "")

        stations.append(
            {
                "station_id": str(elem.get("id", "")),
                "name": name,
                "address": address,
                "lat": float(s_lat),
                "lng": float(s_lon),
                # No live price data from OSM
                "price": None,
                "is_open": True,
                "opening_hours": opening_hours,
                # Straight-line distance placeholder; replaced by road_detour_km later
                "detour_km": 0.0,
                "source": "osm",
            }
        )

        if len(stations) >= max_stations:
            break

    return stations
