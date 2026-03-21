"""Tankerkönig API provider for German fuel prices."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time as dt_time
from math import radians, sin, cos, sqrt, atan2
from typing import Any, Dict, List, Optional

import aiohttp

from homeassistant.util import dt as dt_util

from ..const import TANKERKONIG_API_URL
from ..models import FuelStation
from . import FuelPriceProvider, ProviderError

_LOGGER = logging.getLogger(__name__)

# Earth radius constant for Haversine formula
EARTH_RADIUS_KM = 6371.0


def _parse_price(value: Any) -> float | None:
    """Convert price value to float or None.

    Helper function to safely parse price values from API responses.
    The Tankerkönig API may return prices in various formats (strings,
    numbers, booleans, or null).

    Args:
        value: Price value from API (could be str, float, int, bool, None)

    Returns:
        Float price or None if invalid
    """
    if value is None or value is False:
        return None
    try:
        # Convert to float and validate it's a reasonable price
        price = float(value)
        # Sanity check: prices should be positive and less than or equal to 10 EUR/L
        # (prices above 10 EUR/L are unrealistic for regular fuel)
        if price > 0 and price <= 10.0:
            return price
        _LOGGER.debug("Price %s out of reasonable range (0-10 EUR/L), treating as None", price)
        return None
    except (ValueError, TypeError):
        _LOGGER.debug("Could not convert price value '%s' (type: %s) to float", value, type(value).__name__)
        return None


def _parse_is_open(value: Any) -> bool:
    """Convert isOpen value to boolean.

    Helper function to safely parse isOpen values from API responses.
    The Tankerkönig API may return isOpen in various formats (strings,
    numbers, booleans, or null).

    Args:
        value: isOpen value from API (could be str, bool, int, None)

    Returns:
        Boolean indicating if station is open (defaults to True if unclear)
    """
    if value is None:
        # If not specified, assume open to avoid filtering out valid stations
        return True

    # Handle boolean directly
    if isinstance(value, bool):
        return value

    # Handle numeric values (0 = closed, non-zero = open)
    if isinstance(value, (int, float)):
        return bool(value)

    # Handle string values
    if isinstance(value, str):
        value_lower = value.lower().strip()
        if value_lower in ("true", "1", "yes", "open"):
            return True
        elif value_lower in ("false", "0", "no", "closed"):
            return False
        else:
            _LOGGER.warning("Unexpected isOpen string value '%s', defaulting to True", value)
            return True

    # Unknown type - this indicates an API format change that should be investigated
    _LOGGER.warning("Unexpected isOpen value type '%s' (value: %s), defaulting to True", type(value).__name__, value)
    return True


# German weekday abbreviations used by Tankerkönig
_DE_DAYS = {
    "mo": 0,
    "di": 1,
    "mi": 2,
    "do": 3,
    "fr": 4,
    "sa": 5,
    "so": 6,
}


def _parse_time_str(t: str) -> Optional[dt_time]:
    """Parse a HH:MM time string into a :class:`datetime.time` object.

    Returns ``None`` if the string cannot be parsed.
    """
    try:
        h, m = t.split(":")[:2]
        return dt_time(int(h), int(m))
    except (ValueError, AttributeError):
        return None


def _applicable_days_to_weekdays(applicable_days: str) -> list[int]:
    """Convert a Tankerkönig ``applicable_days`` string to a list of weekday ints (0=Mon).

    Supports:
    * Single day: ``"Mo"``, ``"So"`` …
    * Range: ``"Mo-Fr"``, ``"Mo-So"`` …
    * Comma-separated: ``"Sa,So"`` (seen in some API responses)
    """
    weekdays: list[int] = []
    if not applicable_days:
        return weekdays

    for part in applicable_days.replace(";", ",").split(","):
        part = part.strip()
        if "-" in part:
            parts = part.split("-", 1)
            start_day = _DE_DAYS.get(parts[0].lower().strip())
            end_day = _DE_DAYS.get(parts[1].lower().strip())
            if start_day is not None and end_day is not None:
                if start_day <= end_day:
                    weekdays.extend(range(start_day, end_day + 1))
                else:
                    # wrap-around (e.g. Fr-Mo)
                    weekdays.extend(range(start_day, 7))
                    weekdays.extend(range(0, end_day + 1))
        else:
            day = _DE_DAYS.get(part.lower())
            if day is not None:
                weekdays.append(day)

    return weekdays


def is_station_open_at(
    opening_times: Optional[list],
    whole_day: bool,
    check_dt: datetime,
) -> bool:
    """Return ``True`` if the station is open at *check_dt*.

    Args:
        opening_times: List of opening-time dicts from Tankerkönig detail.php,
            each with keys ``applicable_days``, ``start``, ``end`` (HH:MM strings).
            May be ``None`` when the detail endpoint was not called.
        whole_day: When ``True`` the station operates 24 h and is always open.
        check_dt: The datetime to check (timezone-aware or naive).

    Returns:
        ``True`` when open, ``False`` when closed.  If *opening_times* is
        ``None`` (detail data not available) the function returns ``True`` to
        avoid false negatives.
    """
    if whole_day:
        return True

    if not opening_times:
        # No detail data – don't filter the station out
        return True

    weekday = check_dt.weekday()  # 0=Mon … 6=Sun
    check_time = check_dt.time().replace(second=0, microsecond=0)

    for slot in opening_times:
        applicable = slot.get("applicable_days") or slot.get("text", "")
        start_str = slot.get("start") or slot.get("open")
        end_str = slot.get("end") or slot.get("close")
        if not applicable or not start_str or not end_str:
            continue

        if weekday not in _applicable_days_to_weekdays(applicable):
            continue

        start_t = _parse_time_str(str(start_str))
        end_t = _parse_time_str(str(end_str))
        if start_t is None or end_t is None:
            continue

        if start_t <= end_t:
            # Normal slot: e.g. 06:00 – 22:00
            if start_t <= check_time <= end_t:
                return True
        else:
            # Midnight-spanning slot: e.g. 22:00 – 02:00
            if check_time >= start_t or check_time <= end_t:
                return True

    return False


def format_opening_hours(opening_times: Optional[list], whole_day: bool) -> str:
    """Return a human-readable opening-hours string for the Telegram notification.

    Example output: ``"Mo-Fr 06:00-22:00 | Sa 07:00-21:00 | So 08:00-20:00"``

    Returns an empty string when no data is available.
    """
    if whole_day:
        return "24h geöffnet"

    if not opening_times:
        return ""

    parts: list[str] = []
    for slot in opening_times:
        applicable = slot.get("applicable_days") or slot.get("text", "")
        start_str = slot.get("start") or slot.get("open", "")
        end_str = slot.get("end") or slot.get("close", "")
        if applicable and start_str and end_str:
            parts.append(f"{applicable} {start_str}-{end_str}")

    return " | ".join(parts)


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates using Haversine formula.

    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point

    Returns:
        Distance in kilometers
    """
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    # Haversine formula broken down for readability
    sin_dlat_half = sin(dlat / 2)
    sin_dlon_half = sin(dlon / 2)

    a = sin_dlat_half**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin_dlon_half**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def _format_station_name(brand: str, place: str, street: str, api_name: str) -> str:
    """Format station name according to specification.
    
    Builds station name as [brand] [place] [street].
    If any of these fields are missing or empty, falls back to API name.
    
    Args:
        brand: Station brand/chain
        place: City/place name
        street: Street name
        api_name: Original name from API (fallback)
        
    Returns:
        Formatted station name
    """
    # Clean and filter non-empty components
    components = []
    
    if brand and brand.strip():
        components.append(brand.strip())
    if place and place.strip():
        components.append(place.strip())
    if street and street.strip():
        components.append(street.strip())
    
    # If we have all three components, use them
    if len(components) == 3:
        return " ".join(components)
    
    # Otherwise, fall back to API name
    return api_name if api_name else "Unknown"


def _format_station_address(street: str, house_number: str, post_code: str, place: str) -> str:
    """Format station address according to specification.
    
    Builds address as [street] [houseNumber], [postCode] [place].
    
    Args:
        street: Street name
        house_number: House number
        post_code: Postal code
        place: City/place name
        
    Returns:
        Formatted address
    """
    # Build street address part
    street_parts = []
    if street and street.strip():
        street_parts.append(street.strip())
    if house_number and house_number.strip():
        street_parts.append(house_number.strip())
    
    street_address = " ".join(street_parts) if street_parts else ""
    
    # Build city part
    city_parts = []
    if post_code and post_code.strip():
        city_parts.append(post_code.strip())
    if place and place.strip():
        city_parts.append(place.strip())
    
    city_address = " ".join(city_parts) if city_parts else ""
    
    # Combine with comma separator
    if street_address and city_address:
        return f"{street_address}, {city_address}"
    elif street_address:
        return street_address
    elif city_address:
        return city_address
    else:
        return ""


class TankerkoenigProvider(FuelPriceProvider):
    """Provider for Tankerkönig fuel price API.

    Tankerkönig provides real-time fuel prices for gas stations in Germany.
    API documentation: https://creativecommons.tankerkoenig.de

    Attributes:
        api_key: API key for Tankerkönig service
        session: aiohttp session for API requests
    """

    def __init__(self, api_key: str, session: aiohttp.ClientSession) -> None:
        """Initialize Tankerkönig provider.

        Args:
            api_key: Valid Tankerkönig API key
            session: aiohttp client session
        """
        self.api_key = api_key
        self.session = session
        self.last_api_request = None  # Store last request details
        self.last_api_response = None  # Store last response data

    def _mask_api_key(self, params: dict) -> dict:
        """Mask API key in parameters for safe logging/storage.
        
        Args:
            params: Dictionary containing API parameters
            
        Returns:
            Dictionary with masked API key
        """
        masked = params.copy()
        if "apikey" in masked:
            key = masked["apikey"]
            masked["apikey"] = f"{key[:8]}..." if len(key) > 8 else "***"
        return masked

    async def _handle_error_response(self, response: aiohttp.ClientResponse) -> None:
        """Handle HTTP error responses and raise appropriate ProviderError.
        
        Attempts to read the response body for detailed error information,
        stores the error details for debugging, and raises a ProviderError
        with a comprehensive error message.
        
        Args:
            response: The aiohttp response object with a non-200 status
            
        Raises:
            ProviderError: Always raised with detailed error information
        """
        # Try to get response body for more detailed error information
        try:
            error_body = await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning(
                "Failed to read error response body for HTTP %d: %s",
                response.status,
                err
            )
            error_body = None
        
        # Store error response with full details
        self.last_api_response = {
            "status": response.status,
            "error": f"HTTP {response.status}",
            "error_body": error_body,
            "timestamp": dt_util.now().isoformat(),
        }
        
        # Create detailed error message
        error_msg = f"Tankerkönig API returned status {response.status}"
        if error_body:
            error_msg += f": {error_body}"
        
        raise ProviderError(error_msg)

    async def get_stations_nearby(
        self,
        latitude: float,
        longitude: float,
        radius: float,
        fuel_type: str,
    ) -> List[FuelStation]:
        """Get fuel stations near a location using Tankerkönig list endpoint.

        Args:
            latitude: Geographic latitude
            longitude: Geographic longitude
            radius: Search radius in kilometers
            fuel_type: Type of fuel ('e5', 'e10', 'diesel')

        Returns:
            List of fuel stations sorted by price (ascending)

        Raises:
            ProviderError: If API request fails
        """
        _LOGGER.debug(
            "Fetching stations near %s,%s with radius %s km",
            latitude,
            longitude,
            radius,
        )

        params = {
            "lat": latitude,
            "lng": longitude,
            "rad": radius,
            "type": fuel_type,
            "apikey": self.api_key,
            "sort": "price",
        }

        try:
            url = f"{TANKERKONIG_API_URL}/list.php"
            # Store request details for debugging (with masked API key)
            self.last_api_request = {
                "url": url,
                "params": self._mask_api_key(params),
                "timestamp": dt_util.now().isoformat(),
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    await self._handle_error_response(response)

                data = await response.json()
                # Store complete response for debugging
                self.last_api_response = {
                    "status": response.status,
                    "data": data,
                    "timestamp": dt_util.now().isoformat(),
                }

                if not data.get("ok"):
                    error_msg = data.get("message", "Unknown error")
                    raise ProviderError(f"Tankerkönig API error: {error_msg}")

                # Support both API response formats:
                # - Legacy format: stations at top level data["stations"]
                # - V4 format: stations nested in data["data"]["stations"]
                if "stations" in data:
                    stations_data = data["stations"]
                elif "data" in data:
                    # Try v4 format with nested data object
                    stations_data = data["data"].get("stations", [])
                else:
                    stations_data = []

                stations = []
                for station_data in stations_data:
                    station = self._parse_station_data(station_data, latitude, longitude, fuel_type)
                    if station:
                        stations.append(station)

                _LOGGER.info("Found %d stations nearby", len(stations))
                return stations

        except aiohttp.ClientError as err:
            # Store error for debugging
            self.last_api_response = {
                "error": str(err),
                "error_type": type(err).__name__,
                "timestamp": dt_util.now().isoformat(),
            }
            _LOGGER.error("Error fetching stations: %s", err)
            raise ProviderError(f"Network error: {err}") from err

    async def validate_api_key(self, api_key: str) -> bool:
        """Validate API key with Tankerkönig provider.

        Makes a minimal test request to the Tankerkönig list endpoint to verify
        that the provided API key is accepted by the API.

        Args:
            api_key: API key to validate

        Returns:
            True if the key is valid, False otherwise
        """
        params = {
            "lat": 52.521,
            "lng": 13.438,
            "rad": 1.0,
            "type": "e5",
            "apikey": api_key,
            "sort": "price",
        }
        try:
            url = f"{TANKERKONIG_API_URL}/list.php"
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return False
                data = await response.json()
                return bool(data.get("ok"))
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            return False

    async def get_station_details(self, station_id: str) -> FuelStation:
        """Get detailed information for a specific station.

        Args:
            station_id: Tankerkönig station UUID

        Returns:
            Detailed station information with current prices

        Raises:
            ProviderError: If API request fails or station not found
        """
        _LOGGER.debug("Fetching details for station %s", station_id)

        params = {
            "id": station_id,
            "apikey": self.api_key,
        }

        try:
            url = f"{TANKERKONIG_API_URL}/detail.php"
            # Store request details for debugging (with masked API key)
            self.last_api_request = {
                "url": url,
                "params": self._mask_api_key(params),
                "timestamp": dt_util.now().isoformat(),
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    await self._handle_error_response(response)

                data = await response.json()
                # Store complete response for debugging
                self.last_api_response = {
                    "status": response.status,
                    "data": data,
                    "timestamp": dt_util.now().isoformat(),
                }

                if not data.get("ok"):
                    error_msg = data.get("message", "Unknown error")
                    raise ProviderError(f"Tankerkönig API error: {error_msg}")

                # Support both API response formats:
                # - Legacy format: station at top level data["station"]
                # - V4 format: station nested in data["data"]["station"]
                if "station" in data:
                    station_data = data["station"]
                elif "data" in data:
                    # Try v4 format with nested data object
                    station_data = data["data"].get("station")
                else:
                    station_data = None

                if not station_data:
                    raise ProviderError(f"Station {station_id} not found")

                station = self._parse_station_data(station_data)
                if not station:
                    raise ProviderError(f"Failed to parse station {station_id}")

                return station

        except aiohttp.ClientError as err:
            # Store error for debugging
            self.last_api_response = {
                "error": str(err),
                "error_type": type(err).__name__,
                "timestamp": dt_util.now().isoformat(),
            }
            _LOGGER.error("Error fetching station details: %s", err)
            raise ProviderError(f"Network error: {err}") from err

    async def _fetch_opening_hours(
        self,
        station_id: str,
    ) -> tuple[Optional[list], bool]:
        """Fetch opening hours for a single station via detail.php.

        Returns a ``(opening_times, whole_day)`` tuple.  On any error returns
        ``(None, False)`` so the caller can still proceed without filtering.
        """
        params = {"id": station_id, "apikey": self.api_key}
        try:
            url = f"{TANKERKONIG_API_URL}/detail.php"
            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    return None, False
                data = await response.json()
                if not data.get("ok"):
                    return None, False
                # Support both v4 and legacy formats
                station_data = data.get("station") or (data.get("data") or {}).get("station") or {}
                opening_times = station_data.get("openingTimes") or None
                whole_day = bool(station_data.get("wholeDay", False))
                return opening_times, whole_day
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, KeyError) as err:
            _LOGGER.debug("Opening hours fetch failed for %s: %s", station_id, err)
            return None, False

    async def get_opening_hours_batch(
        self,
        station_ids: List[str],
    ) -> Dict[str, tuple]:
        """Fetch opening hours for multiple stations in parallel.

        Args:
            station_ids: List of Tankerkönig station UUIDs.

        Returns:
            Mapping ``station_id -> (opening_times, whole_day)``.
        """
        tasks = [self._fetch_opening_hours(sid) for sid in station_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out: Dict[str, tuple] = {}
        for sid, result in zip(station_ids, results):
            if isinstance(result, Exception):
                out[sid] = (None, False)
            else:
                out[sid] = result
        return out

    def _parse_station_data(self, data: Dict[str, Any], ref_lat: float = None, ref_lon: float = None, fuel_type: str = None) -> FuelStation | None:
        """Parse station data from API response.

        Args:
            data: Raw station data from API
            ref_lat: Reference latitude for distance calculation
            ref_lon: Reference longitude for distance calculation
            fuel_type: The fuel type that was requested (e.g., 'e5', 'e10', 'diesel').
                      When specified and a 'price' field exists in the response,
                      that price will be used for the corresponding fuel type field.

        Returns:
            FuelStation object or None if parsing fails
        """
        try:
            station_lat = data.get("lat", 0.0)
            station_lon = data.get("lng", 0.0)

            # Calculate distance if not provided or if reference coordinates given
            distance = data.get("dist", 0.0)
            # Use explicit None checks to avoid filtering out valid 0.0 coordinates
            if ref_lat is not None and ref_lon is not None and station_lat is not None and station_lon is not None:
                distance = _distance_km(ref_lat, ref_lon, station_lat, station_lon)

            # Extract prices from nested price object if present, otherwise try top-level
            # The Tankerkönig API v4 returns prices in a nested "price" object
            # Note: We skip empty dicts to fall back to top-level prices
            price_obj = data.get("price")
            if price_obj is not None and isinstance(price_obj, dict) and price_obj:
                # V4 API format: prices in nested object (non-empty dict)
                price_e5 = price_obj.get("e5")
                price_e10 = price_obj.get("e10")
                price_diesel = price_obj.get("diesel")
            else:
                # Fallback to top-level (legacy format, missing, None, or empty price object)
                price_e5 = data.get("e5")
                price_e10 = data.get("e10")
                price_diesel = data.get("diesel")
                
                # Special case: when requesting list.php with a specific fuel type,
                # the API returns a single 'price' field instead of individual fuel type fields
                if fuel_type and "price" in data:
                    single_price = data.get("price")
                    if fuel_type == "e5":
                        price_e5 = single_price
                    elif fuel_type == "e10":
                        price_e10 = single_price
                    elif fuel_type == "diesel":
                        price_diesel = single_price

            # Extract address components from API
            # Convert all values to strings to handle cases where API returns non-string types
            # Use 'or' operator to avoid converting None/False/0 to strings like "None"/"False"/"0"
            api_name = str(data.get("name") or "Unknown")
            brand = str(data.get("brand") or "")
            street = str(data.get("street") or "")
            house_number = str(data.get("houseNumber") or "")
            post_code = str(data.get("postCode") or "")
            place = str(data.get("place") or "")
            
            # Format station name and address according to specification
            formatted_name = _format_station_name(brand, place, street, api_name)
            formatted_address = _format_station_address(street, house_number, post_code, place)

            station = FuelStation(
                station_id=data.get("id", ""),
                name=formatted_name,
                brand=brand,
                address=formatted_address,
                city=place,
                street=street,
                house_number=house_number,
                post_code=post_code,
                latitude=station_lat,
                longitude=station_lon,
                distance=distance,
                price_e5=_parse_price(price_e5),
                price_e10=_parse_price(price_e10),
                price_diesel=_parse_price(price_diesel),
                is_open=_parse_is_open(data.get("isOpen")),
                last_updated=dt_util.now(),
            )

            # Log detailed station info for debugging
            _LOGGER.debug(
                "Parsed station '%s' (API name: '%s', brand: '%s', place: '%s', street: '%s'): "
                "address='%s' (raw: street='%s', number='%s', postcode='%s', city='%s'), "
                "e5=%s, e10=%s, diesel=%s, open=%s",
                station.name,
                api_name,
                brand,
                place,
                street,
                station.address,
                street,
                house_number,
                post_code,
                place,
                station.price_e5,
                station.price_e10,
                station.price_diesel,
                station.is_open,
            )

            return station
        except (KeyError, ValueError) as err:
            _LOGGER.warning("Failed to parse station data: %s", err)
            return None
