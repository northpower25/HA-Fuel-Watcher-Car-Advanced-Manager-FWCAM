"""Tankerkönig API provider for German fuel prices."""
from __future__ import annotations

import logging
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from typing import Any, Dict, List

import aiohttp

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
                "timestamp": datetime.now().isoformat(),
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    # Store error response
                    self.last_api_response = {
                        "status": response.status,
                        "error": f"HTTP {response.status}",
                        "timestamp": datetime.now().isoformat(),
                    }
                    raise ProviderError(
                        f"Tankerkönig API returned status {response.status}"
                    )

                data = await response.json()
                # Store complete response for debugging
                self.last_api_response = {
                    "status": response.status,
                    "data": data,
                    "timestamp": datetime.now().isoformat(),
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
                    station = self._parse_station_data(station_data, latitude, longitude)
                    if station:
                        stations.append(station)

                _LOGGER.info("Found %d stations nearby", len(stations))
                return stations

        except aiohttp.ClientError as err:
            # Store error for debugging
            self.last_api_response = {
                "error": str(err),
                "error_type": type(err).__name__,
                "timestamp": datetime.now().isoformat(),
            }
            _LOGGER.error("Error fetching stations: %s", err)
            raise ProviderError(f"Network error: {err}") from err

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
                "timestamp": datetime.now().isoformat(),
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    # Store error response
                    self.last_api_response = {
                        "status": response.status,
                        "error": f"HTTP {response.status}",
                        "timestamp": datetime.now().isoformat(),
                    }
                    raise ProviderError(
                        f"Tankerkönig API returned status {response.status}"
                    )

                data = await response.json()
                # Store complete response for debugging
                self.last_api_response = {
                    "status": response.status,
                    "data": data,
                    "timestamp": datetime.now().isoformat(),
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
                "timestamp": datetime.now().isoformat(),
            }
            _LOGGER.error("Error fetching station details: %s", err)
            raise ProviderError(f"Network error: {err}") from err

    async def validate_api_key(self, api_key: str) -> bool:
        """Validate API key by making a test request.

        Args:
            api_key: API key to validate

        Returns:
            True if key is valid, False otherwise
        """
        params = {
            "lat": 52.521,  # Berlin coordinates for test
            "lng": 13.438,
            "rad": 1,
            "type": "e5",
            "apikey": api_key,
        }

        try:
            async with self.session.get(
                f"{TANKERKONIG_API_URL}/list.php", params=params, timeout=10
            ) as response:
                if response.status != 200:
                    return False

                data = await response.json()
                return data.get("ok", False)

        except (aiohttp.ClientError, TimeoutError):
            return False

    def _parse_station_data(self, data: Dict[str, Any], ref_lat: float = None, ref_lon: float = None) -> FuelStation | None:
        """Parse station data from API response.

        Args:
            data: Raw station data from API
            ref_lat: Reference latitude for distance calculation
            ref_lon: Reference longitude for distance calculation

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

            station = FuelStation(
                station_id=data.get("id", ""),
                name=data.get("name", "Unknown"),
                brand=data.get("brand", "Unknown"),
                address=data.get("street", "") + " " + data.get("houseNumber", ""),
                city=data.get("place", ""),
                latitude=station_lat,
                longitude=station_lon,
                distance=distance,
                price_e5=_parse_price(price_e5),
                price_e10=_parse_price(price_e10),
                price_diesel=_parse_price(price_diesel),
                is_open=_parse_is_open(data.get("isOpen")),
                last_updated=datetime.now(),
            )

            # Log detailed station info for debugging
            _LOGGER.debug(
                "Parsed station '%s': e5=%s, e10=%s, diesel=%s, open=%s (raw price obj: %s, isOpen=%s)",
                station.name,
                station.price_e5,
                station.price_e10,
                station.price_diesel,
                station.is_open,
                price_obj,
                data.get("isOpen"),
            )

            return station
        except (KeyError, ValueError) as err:
            _LOGGER.warning("Failed to parse station data: %s", err)
            return None
