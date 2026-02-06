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
            List of fuel stations sorted by distance
            
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
            "sort": "dist",
        }

        try:
            async with self.session.get(
                f"{TANKERKONIG_API_URL}/list.php", params=params
            ) as response:
                if response.status != 200:
                    raise ProviderError(
                        f"Tankerkönig API returned status {response.status}"
                    )

                data = await response.json()

                if not data.get("ok"):
                    error_msg = data.get("message", "Unknown error")
                    raise ProviderError(f"Tankerkönig API error: {error_msg}")

                stations = []
                for station_data in data.get("stations", []):
                    station = self._parse_station_data(station_data, latitude, longitude)
                    if station:
                        stations.append(station)

                _LOGGER.info("Found %d stations nearby", len(stations))
                return stations

        except aiohttp.ClientError as err:
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
            async with self.session.get(
                f"{TANKERKONIG_API_URL}/detail.php", params=params
            ) as response:
                if response.status != 200:
                    raise ProviderError(
                        f"Tankerkönig API returned status {response.status}"
                    )

                data = await response.json()

                if not data.get("ok"):
                    error_msg = data.get("message", "Unknown error")
                    raise ProviderError(f"Tankerkönig API error: {error_msg}")

                station_data = data.get("station")
                if not station_data:
                    raise ProviderError(f"Station {station_id} not found")

                station = self._parse_station_data(station_data)
                if not station:
                    raise ProviderError(f"Failed to parse station {station_id}")

                return station

        except aiohttp.ClientError as err:
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
            
            station = FuelStation(
                station_id=data.get("id", ""),
                name=data.get("name", "Unknown"),
                brand=data.get("brand", "Unknown"),
                address=data.get("street", "") + " " + data.get("houseNumber", ""),
                city=data.get("place", ""),
                latitude=station_lat,
                longitude=station_lon,
                distance=distance,
                price_e5=_parse_price(data.get("e5")),
                price_e10=_parse_price(data.get("e10")),
                price_diesel=_parse_price(data.get("diesel")),
                is_open=data.get("isOpen", True),
                last_updated=datetime.now(),
            )
            
            # Log detailed station info for debugging
            _LOGGER.debug(
                "Parsed station '%s': e5=%s, e10=%s, diesel=%s, open=%s (raw: e5=%s, e10=%s, diesel=%s, isOpen=%s)",
                station.name,
                station.price_e5,
                station.price_e10,
                station.price_diesel,
                station.is_open,
                data.get("e5"),
                data.get("e10"),
                data.get("diesel"),
                data.get("isOpen"),
            )
            
            return station
        except (KeyError, ValueError) as err:
            _LOGGER.warning("Failed to parse station data: %s", err)
            return None
