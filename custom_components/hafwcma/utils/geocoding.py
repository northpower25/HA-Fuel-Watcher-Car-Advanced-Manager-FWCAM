"""Geocoding utilities for trip tracking using OpenStreetMap Nominatim."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, TYPE_CHECKING

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

# Nominatim API configuration
NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_USER_AGENT = "HomeAssistant-haFWCMA/1.0"
NOMINATIM_RATE_LIMIT_SECONDS = 1.0  # Nominatim requires 1 request per second
NOMINATIM_REQUEST_TIMEOUT_SECONDS = 10  # Timeout for API requests
CACHE_EXPIRY_DAYS = 30  # Cache geocoding results for 30 days

# Session timeout configuration
SESSION_TIMEOUT_TOTAL_SECONDS = 30  # Overall session timeout
SESSION_TIMEOUT_CONNECT_SECONDS = 10  # Connection timeout
SESSION_TIMEOUT_SOCK_READ_SECONDS = 20  # Socket read timeout


class GeocodingCache:
    """Simple cache for geocoding results to reduce API calls."""
    
    def __init__(self, initial_cache: dict[str, dict[str, Any]] | None = None) -> None:
        """Initialize the geocoding cache.
        
        Args:
            initial_cache: Optional initial cache data loaded from storage
        """
        self._cache: dict[str, dict[str, Any]] = initial_cache or {}
    
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
    
    def get(self, latitude: float, longitude: float) -> dict[str, str] | None:
        """Get cached geocoding data for coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Dict with 'location_name' and 'address' keys, or None if not found or expired
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
        
        return {
            "location_name": entry.get("location_name", ""),
            "address": entry.get("address", ""),
        }
    
    def set(
        self,
        latitude: float,
        longitude: float,
        address: str,
        location_name: str = "",
    ) -> None:
        """Cache geocoding data for coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            address: Address string to cache
            location_name: Location name to cache
        """
        key = self._make_key(latitude, longitude)
        self._cache[key] = {
            "address": address,
            "location_name": location_name,
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
    
    def get_all_cached_data(self) -> dict[str, dict[str, Any]]:
        """Get all cached data for persistence.
        
        Returns:
            Dictionary of all cache entries
        """
        return self._cache.copy()
    
    def set_all_cached_data(self, cache_data: dict[str, dict[str, Any]]) -> None:
        """Set all cached data from persistent storage.
        
        Args:
            cache_data: Dictionary of cache entries to load
        """
        self._cache = cache_data.copy()
        _LOGGER.debug("Loaded %d geocoding cache entries from storage", len(self._cache))
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get statistics about the cache for debugging.
        
        Returns:
            Dictionary with cache statistics including count and sample entries
        """
        cache_entries = []
        for key, entry in self._cache.items():
            try:
                coords = key.split(",")
                if len(coords) != 2:
                    _LOGGER.warning("Malformed cache key: %s", key)
                    continue
                    
                cache_entries.append({
                    "latitude": float(coords[0]),
                    "longitude": float(coords[1]),
                    "location_name": entry.get("location_name", ""),
                    "address": entry.get("address", ""),
                    "timestamp": entry.get("timestamp", ""),
                })
            except (ValueError, IndexError) as err:
                _LOGGER.warning("Error parsing cache key '%s': %s", key, err)
                continue
        
        return {
            "total_entries": len(self._cache),
            "entries": cache_entries,
        }


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
            # Create session with proper timeout configuration
            timeout = aiohttp.ClientTimeout(
                total=SESSION_TIMEOUT_TOTAL_SECONDS,
                connect=SESSION_TIMEOUT_CONNECT_SECONDS,
                sock_read=SESSION_TIMEOUT_SOCK_READ_SECONDS
            )
            self._session = aiohttp.ClientSession(timeout=timeout)
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
    ) -> dict[str, str | bool] | None:
        """Reverse geocode coordinates to location name and address.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            use_cache: Whether to use cached results
            
        Returns:
            Dict with 'location_name', 'address', and 'from_cache' keys, or None if geocoding failed
        """
        # Check cache first
        if use_cache:
            cached_data = self._cache.get(latitude, longitude)
            if cached_data:
                _LOGGER.debug(
                    "Using cached data for (%.4f, %.4f): name=%s, address=%s",
                    latitude,
                    longitude,
                    cached_data.get("location_name", ""),
                    cached_data.get("address", ""),
                )
                # Add from_cache indicator
                result = cached_data.copy()
                result["from_cache"] = True
                return result
        
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
            
            # Use ClientTimeout object for proper timeout handling
            timeout = aiohttp.ClientTimeout(total=NOMINATIM_REQUEST_TIMEOUT_SECONDS)
            async with session.get(url, params=params, headers=headers, timeout=timeout) as response:
                self._last_request_time = dt_util.now()
                
                if response.status == 200:
                    data = await response.json()
                    address = self._format_address(data)
                    location_name = self._extract_location_name(data)
                    
                    result = {
                        "location_name": location_name or "",
                        "address": address or "",
                        "from_cache": False,
                    }
                    
                    # Cache the result
                    if (address or location_name) and use_cache:
                        self._cache.set(latitude, longitude, address or "", location_name or "")
                    
                    _LOGGER.debug(
                        "Geocoded (%.4f, %.4f) to: name=%s, address=%s",
                        latitude,
                        longitude,
                        location_name,
                        address,
                    )
                    return result
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
    
    def _extract_location_name(self, data: dict[str, Any]) -> str | None:
        """Extract location name from Nominatim response.
        
        Args:
            data: Nominatim API response data
            
        Returns:
            Location name string or None
        """
        if not data:
            return None
        
        # Get address components
        address = data.get("address", {})
        
        # Priority: shop, amenity, building, name field
        # These represent specific places rather than just addresses
        location_name = ""
        
        if address.get("shop"):
            location_name = address["shop"]
        elif address.get("amenity"):
            location_name = address["amenity"]
        elif address.get("building"):
            location_name = address["building"]
        elif address.get("house_number") and address.get("road"):
            location_name = f"{address['road']} {address['house_number']}"
        elif address.get("road"):
            location_name = address["road"]
        
        # If we found a specific place name, use it (overrides the above)
        if data.get("name") and data["name"] != address.get("road"):
            location_name = data["name"]
        
        return location_name if location_name else None
    
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
    
    def get_cache_data(self) -> dict[str, dict[str, Any]]:
        """Get all cached data for persistence.
        
        Returns:
            Dictionary of all cache entries
        """
        return self._cache.get_all_cached_data()
    
    def load_cache_data(self, cache_data: dict[str, dict[str, Any]]) -> None:
        """Load cached data from persistent storage.
        
        Args:
            cache_data: Dictionary of cache entries to load
        """
        self._cache.set_all_cached_data(cache_data)
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for debugging.
        
        Returns:
            Dictionary with cache statistics
        """
        return self._cache.get_cache_stats()
    
    def set_cache_entry(
        self,
        latitude: float,
        longitude: float,
        location_name: str = "",
        address: str = "",
    ) -> None:
        """Manually set a cache entry for coordinates.
        
        This is used when location data is manually entered by the user,
        allowing it to be reused for future trips with the same coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            location_name: Location name to cache
            address: Address to cache
        """
        self._cache.set(latitude, longitude, address, location_name)


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
) -> dict[str, str] | None:
    """Geocode a trip location to location name and address.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        use_cache: Whether to use cached results
        
    Returns:
        Dict with 'location_name' and 'address' keys, or None if geocoding failed or coordinates not provided
    """
    if latitude is None or longitude is None:
        return None
    
    geocoder = get_geocoder()
    return await geocoder.reverse_geocode(latitude, longitude, use_cache=use_cache)


def cache_manual_location(
    latitude: float | None,
    longitude: float | None,
    location_name: str | None = None,
    address: str | None = None,
) -> None:
    """Manually cache location data for coordinates.
    
    This is used when a user manually enters location information for a trip,
    so that subsequent trips with the same coordinates can use the cached data.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        location_name: Location name to cache
        address: Address to cache
    """
    if latitude is None or longitude is None:
        return
    
    # Only cache if at least one field has data
    if not location_name and not address:
        return
    
    geocoder = get_geocoder()
    geocoder.set_cache_entry(
        latitude=latitude,
        longitude=longitude,
        location_name=location_name or "",
        address=address or "",
    )
    
    _LOGGER.debug(
        "Manually cached location for (%.4f, %.4f): name=%s, address=%s",
        latitude,
        longitude,
        location_name or "",
        address or "",
    )


async def load_geocoding_cache_from_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Load geocoding cache from a config entry's storage.
    
    NOTE: This function is currently not called automatically. It's available for future use
    when implementing persistent cache across Home Assistant restarts.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    from .storage import load_data
    
    try:
        data = await load_data(hass, entry)
        cache_data = data.get("geocoding_cache", {})
        
        geocoder = get_geocoder()
        geocoder.load_cache_data(cache_data)
        
        _LOGGER.debug("Loaded geocoding cache from storage for entry %s", entry.entry_id)
    except Exception as err:
        _LOGGER.warning("Failed to load geocoding cache from storage: %s", err)


async def save_geocoding_cache_to_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Save geocoding cache to a config entry's storage.
    
    NOTE: This function is currently not called automatically. It's available for future use
    when implementing persistent cache across Home Assistant restarts.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    from .storage import load_data, save_data
    
    try:
        geocoder = get_geocoder()
        cache_data = geocoder.get_cache_data()
        
        data = await load_data(hass, entry)
        data["geocoding_cache"] = cache_data
        await save_data(hass, entry, data)
        
        _LOGGER.debug("Saved geocoding cache to storage for entry %s (entries: %d)", 
                     entry.entry_id, len(cache_data))
    except Exception as err:
        _LOGGER.warning("Failed to save geocoding cache to storage: %s", err)


async def rebuild_cache_from_trips(hass: HomeAssistant, entry: ConfigEntry) -> int:
    """Rebuild geocoding cache from existing trip data.
    
    This function scans all existing trips and caches their location data
    (start/end coordinates with names and addresses) to enable auto-fill
    for future trips with the same coordinates.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Number of cache entries created
    """
    from .storage import get_trips
    
    def _cache_location_if_valid(
        geocoder: NominatimGeocoder,
        latitude: float | None,
        longitude: float | None,
        name: str,
        address: str,
    ) -> bool:
        """Helper to cache location if coordinates are valid and data exists.
        
        Returns:
            True if location was cached, False otherwise
        """
        if latitude is not None and longitude is not None and (name or address):
            geocoder.set_cache_entry(
                latitude=latitude,
                longitude=longitude,
                location_name=name or "",
                address=address or "",
            )
            return True
        return False
    
    try:
        trips = await get_trips(hass, entry)
        geocoder = get_geocoder()
        cache_count = 0
        
        for trip in trips:
            # Cache start location
            if _cache_location_if_valid(
                geocoder,
                trip.get("start_latitude"),
                trip.get("start_longitude"),
                trip.get("start_name", ""),
                trip.get("start_address", ""),
            ):
                cache_count += 1
            
            # Cache end location
            if _cache_location_if_valid(
                geocoder,
                trip.get("end_latitude"),
                trip.get("end_longitude"),
                trip.get("end_name", ""),
                trip.get("end_address", ""),
            ):
                cache_count += 1
        
        _LOGGER.info(
            "Rebuilt geocoding cache from %d trips, created %d cache entries",
            len(trips),
            cache_count
        )
        return cache_count
        
    except Exception as err:
        _LOGGER.error("Failed to rebuild geocoding cache from trips: %s", err, exc_info=True)
        return 0
