"""Geocoding utilities for trip tracking using OpenStreetMap Nominatim."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

# Nominatim API configuration
NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_USER_AGENT = "HomeAssistant-haFWCMA/1.0"
NOMINATIM_RATE_LIMIT_SECONDS = 1.0  # Nominatim requires 1 request per second
NOMINATIM_REQUEST_TIMEOUT_SECONDS = 10  # Timeout for API requests
CACHE_EXPIRY_DAYS = 30  # Cache geocoding results for 30 days


class GeocodingCache:
    """Simple cache for geocoding results to reduce API calls."""
    
    def __init__(self) -> None:
        """Initialize the geocoding cache."""
        self._cache: dict[str, dict[str, Any]] = {}
    
    def _make_key(self, latitude: float, longitude: float) -> str:
        """Create a cache key from coordinates.
        
        Rounds to 4 decimal places (~11 meters precision) to improve cache hits.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Cache key string
        """
        lat_rounded = round(latitude, 4)
        lon_rounded = round(longitude, 4)
        return f"{lat_rounded},{lon_rounded}"
    
    def get(self, latitude: float, longitude: float) -> str | None:
        """Get cached address for coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Cached address string or None if not found or expired
        """
        key = self._make_key(latitude, longitude)
        entry = self._cache.get(key)
        
        if not entry:
            return None
        
        # Check if entry has expired
        cached_time = entry.get("timestamp")
        if cached_time:
            try:
                cached_dt = dt_util.parse_datetime(cached_time)
                if cached_dt:
                    age = dt_util.now() - cached_dt
                    if age.days > CACHE_EXPIRY_DAYS:
                        # Entry expired, remove it
                        del self._cache[key]
                        return None
            except (ValueError, TypeError):
                pass
        
        return entry.get("address")
    
    def set(self, latitude: float, longitude: float, address: str) -> None:
        """Cache an address for coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            address: Address string to cache
        """
        key = self._make_key(latitude, longitude)
        self._cache[key] = {
            "address": address,
            "timestamp": dt_util.now().isoformat(),
        }
    
    def clear_expired(self) -> int:
        """Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        keys_to_remove = []
        now = dt_util.now()
        
        for key, entry in self._cache.items():
            cached_time = entry.get("timestamp")
            if cached_time:
                try:
                    cached_dt = dt_util.parse_datetime(cached_time)
                    if cached_dt:
                        age = now - cached_dt
                        if age.days > CACHE_EXPIRY_DAYS:
                            keys_to_remove.append(key)
                except (ValueError, TypeError):
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._cache[key]
        
        if keys_to_remove:
            _LOGGER.debug("Cleared %d expired geocoding cache entries", len(keys_to_remove))
        
        return len(keys_to_remove)


class NominatimGeocoder:
    """Geocoder using OpenStreetMap Nominatim API."""
    
    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        """Initialize the geocoder.
        
        Args:
            session: Optional aiohttp session to use for requests
        """
        self._session = session
        self._own_session = False
        self._cache = GeocodingCache()
        self._last_request_time: datetime | None = None
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have a session for making requests.
        
        Returns:
            aiohttp ClientSession
        """
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._own_session = True
        return self._session
    
    async def close(self) -> None:
        """Close the session if we own it."""
        if self._own_session and self._session:
            await self._session.close()
            self._session = None
    
    async def _respect_rate_limit(self) -> None:
        """Wait if necessary to respect Nominatim rate limit (1 request/second)."""
        if self._last_request_time is not None:
            time_since_last = (dt_util.now() - self._last_request_time).total_seconds()
            if time_since_last < NOMINATIM_RATE_LIMIT_SECONDS:
                wait_time = NOMINATIM_RATE_LIMIT_SECONDS - time_since_last
                _LOGGER.debug("Rate limiting: waiting %.2f seconds", wait_time)
                await asyncio.sleep(wait_time)
    
    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        use_cache: bool = True,
    ) -> str | None:
        """Reverse geocode coordinates to an address.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            use_cache: Whether to use cached results
            
        Returns:
            Address string or None if geocoding failed
        """
        # Check cache first
        if use_cache:
            cached_address = self._cache.get(latitude, longitude)
            if cached_address:
                _LOGGER.debug(
                    "Using cached address for (%.4f, %.4f): %s",
                    latitude,
                    longitude,
                    cached_address,
                )
                return cached_address
        
        # Make API request
        try:
            session = await self._ensure_session()
            
            # Respect rate limit
            await self._respect_rate_limit()
            
            url = f"{NOMINATIM_BASE_URL}/reverse"
            params = {
                "lat": latitude,
                "lon": longitude,
                "format": "json",
                "addressdetails": 1,
                "zoom": 18,  # Street level detail
            }
            headers = {
                "User-Agent": NOMINATIM_USER_AGENT,
            }
            
            _LOGGER.debug("Geocoding request: %s with params %s", url, params)
            
            async with session.get(url, params=params, headers=headers, timeout=NOMINATIM_REQUEST_TIMEOUT_SECONDS) as response:
                self._last_request_time = dt_util.now()
                
                if response.status == 200:
                    data = await response.json()
                    address = self._format_address(data)
                    
                    # Cache the result
                    if address and use_cache:
                        self._cache.set(latitude, longitude, address)
                    
                    _LOGGER.debug(
                        "Geocoded (%.4f, %.4f) to: %s",
                        latitude,
                        longitude,
                        address,
                    )
                    return address
                else:
                    _LOGGER.warning(
                        "Geocoding failed with status %d: %s",
                        response.status,
                        await response.text(),
                    )
                    return None
        except asyncio.TimeoutError:
            _LOGGER.warning("Geocoding request timed out")
            return None
        except Exception as err:
            _LOGGER.warning("Error during geocoding: %s", err)
            return None
    
    def _format_address(self, data: dict[str, Any]) -> str | None:
        """Format address from Nominatim response.
        
        Args:
            data: Nominatim API response data
            
        Returns:
            Formatted address string or None
        """
        if not data:
            return None
        
        # Get address components
        address = data.get("address", {})
        
        # Build address string with available components
        parts = []
        
        # Street and number
        road = address.get("road")
        house_number = address.get("house_number")
        if road:
            if house_number:
                parts.append(f"{road} {house_number}")
            else:
                parts.append(road)
        
        # City
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
        )
        postcode = address.get("postcode")
        if city:
            if postcode:
                parts.append(f"{postcode} {city}")
            else:
                parts.append(city)
        
        # Country (only if no city)
        if not city:
            country = address.get("country")
            if country:
                parts.append(country)
        
        # Join parts
        if parts:
            return ", ".join(parts)
        
        # Fallback to display_name if no structured address
        return data.get("display_name")
    
    def clear_cache(self) -> None:
        """Clear the geocoding cache."""
        self._cache = GeocodingCache()
        _LOGGER.info("Geocoding cache cleared")
    
    def clear_expired_cache(self) -> int:
        """Clear expired cache entries.
        
        Returns:
            Number of entries removed
        """
        return self._cache.clear_expired()


# Global geocoder instance
_geocoder: NominatimGeocoder | None = None


def get_geocoder() -> NominatimGeocoder:
    """Get the global geocoder instance.
    
    Returns:
        NominatimGeocoder instance
    """
    global _geocoder
    if _geocoder is None:
        _geocoder = NominatimGeocoder()
    return _geocoder


async def geocode_trip_location(
    latitude: float | None,
    longitude: float | None,
    use_cache: bool = True,
) -> str | None:
    """Geocode a trip location to an address.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        use_cache: Whether to use cached results
        
    Returns:
        Address string or None if geocoding failed or coordinates not provided
    """
    if latitude is None or longitude is None:
        return None
    
    geocoder = get_geocoder()
    return await geocoder.reverse_geocode(latitude, longitude, use_cache=use_cache)
