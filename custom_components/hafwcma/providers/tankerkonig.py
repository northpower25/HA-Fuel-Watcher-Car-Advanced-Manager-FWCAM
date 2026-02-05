"""Tankerkönig API provider for German fuel prices."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

import aiohttp

from ..const import TANKERKONIG_API_URL
from ..models import FuelStation
from . import FuelPriceProvider, ProviderError

_LOGGER = logging.getLogger(__name__)


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
                    station = self._parse_station_data(station_data)
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

    def _parse_station_data(self, data: Dict[str, Any]) -> FuelStation | None:
        """Parse station data from API response.
        
        Args:
            data: Raw station data from API
            
        Returns:
            FuelStation object or None if parsing fails
        """
        try:
            return FuelStation(
                station_id=data.get("id", ""),
                name=data.get("name", "Unknown"),
                brand=data.get("brand", "Unknown"),
                address=data.get("street", "") + " " + data.get("houseNumber", ""),
                city=data.get("place", ""),
                latitude=data.get("lat", 0.0),
                longitude=data.get("lng", 0.0),
                distance=data.get("dist", 0.0),
                price_e5=data.get("e5"),
                price_e10=data.get("e10"),
                price_diesel=data.get("diesel"),
                is_open=data.get("isOpen", True),
                last_updated=datetime.now(),
            )
        except (KeyError, ValueError) as err:
            _LOGGER.warning("Failed to parse station data: %s", err)
            return None
