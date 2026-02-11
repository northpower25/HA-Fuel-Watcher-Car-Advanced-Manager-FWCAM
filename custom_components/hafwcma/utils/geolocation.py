"""Geolocation utilities for proximity detection and station management."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
from typing import Any
from urllib.parse import quote

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

# Earth radius constant for Haversine formula
EARTH_RADIUS_KM = 6371.0


def calculate_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
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
    
    sin_dlat_half = sin(dlat / 2)
    sin_dlon_half = sin(dlon / 2)
    
    a = sin_dlat_half**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin_dlon_half**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return EARTH_RADIUS_KM * c


def get_navigation_urls(latitude: float, longitude: float, name: str = "") -> dict[str, str]:
    """Generate navigation URLs for different mapping apps.
    
    Args:
        latitude: Station latitude
        longitude: Station longitude
        name: Optional station name for better navigation
        
    Returns:
        Dictionary with navigation URLs for different apps
    """
    # Encode name for URL
    encoded_name = quote(name) if name else ""
    
    return {
        "google_maps": f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}",
        "apple_maps": f"https://maps.apple.com/?q={encoded_name}&ll={latitude},{longitude}",
        "waze": f"https://www.waze.com/ul?ll={latitude},{longitude}&navigate=yes",
    }


def format_alert_message(
    station_name: str,
    distance_km: float,
    price: float,
    fuel_type: str,
    address: str = "",
    navigation_url: str = "",
) -> str:
    """Format a user-friendly alert message for notifications.
    
    Optimized for mobile notifications including CarPlay/Android Auto.
    
    Args:
        station_name: Name of the station
        distance_km: Distance to station in km
        price: Fuel price per liter
        fuel_type: Type of fuel (e5, e10, diesel)
        address: Optional station address
        navigation_url: Optional navigation URL
        
    Returns:
        Formatted alert message
    """
    fuel_emoji = {
        "e5": "⛽",
        "e10": "⛽",
        "diesel": "🚛",
    }
    
    emoji = fuel_emoji.get(fuel_type.lower(), "⛽")
    fuel_display = fuel_type.upper()
    
    parts = [
        f"🚗 Günstige Tankstelle in der Nähe!",
        f"📍 {station_name} ({distance_km:.1f} km)",
        f"💰 Preis: €{price:.3f}/L ({fuel_display})",
    ]
    
    if address:
        parts.append(f"📫 {address}")
    
    if navigation_url:
        parts.append(f"🧭 Navigation: {navigation_url}")
    
    return "\n".join(parts)


class ProximityTracker:
    """Track proximity alerts with anti-spam mechanism.
    
    Implements cooldown and hysteresis to prevent alert spam.
    """
    
    def __init__(
        self,
        cooldown_seconds: int = 1800,
        hysteresis_factor: float = 1.3,
    ):
        """Initialize proximity tracker.
        
        Args:
            cooldown_seconds: Minimum time between alerts for same station
            hysteresis_factor: Distance multiplier to reset alert state
        """
        self.cooldown_seconds = cooldown_seconds
        self.hysteresis_factor = hysteresis_factor
        self._alert_history: dict[str, dict[str, Any]] = {}
    
    def should_alert(
        self,
        station_id: str,
        current_distance: float,
        threshold_distance: float,
    ) -> bool:
        """Determine if an alert should be triggered for a station.
        
        Implements cooldown period and hysteresis to prevent spam.
        
        Args:
            station_id: Unique station identifier
            current_distance: Current distance to station in km
            threshold_distance: Alert threshold distance in km
            
        Returns:
            True if alert should be triggered, False otherwise
        """
        now = dt_util.utcnow()
        
        # Check if we're within threshold
        within_threshold = current_distance <= threshold_distance
        
        if station_id not in self._alert_history:
            # First time seeing this station
            if within_threshold:
                self._alert_history[station_id] = {
                    "last_alert": now,
                    "last_distance": current_distance,
                    "alerted": True,
                }
                return True
            return False
        
        history = self._alert_history[station_id]
        
        # Check if we're in cooldown period
        time_since_alert = (now - history["last_alert"]).total_seconds()
        in_cooldown = time_since_alert < self.cooldown_seconds
        
        if within_threshold:
            if history["alerted"] and in_cooldown:
                # Already alerted and still in cooldown
                return False
            elif not history["alerted"]:
                # Was outside threshold, now entering - trigger alert
                history["last_alert"] = now
                history["last_distance"] = current_distance
                history["alerted"] = True
                return True
            else:
                # Cooldown expired, trigger new alert
                history["last_alert"] = now
                history["last_distance"] = current_distance
                history["alerted"] = True
                return True
        else:
            # Outside threshold - check hysteresis
            reset_distance = threshold_distance * self.hysteresis_factor
            if current_distance >= reset_distance:
                # Far enough away to reset alert state
                history["alerted"] = False
                history["last_distance"] = current_distance
            return False
    
    def reset_station(self, station_id: str) -> None:
        """Reset alert state for a specific station.
        
        Args:
            station_id: Station ID to reset
        """
        if station_id in self._alert_history:
            del self._alert_history[station_id]
    
    def reset_all(self) -> None:
        """Reset all alert states."""
        self._alert_history.clear()
    
    def get_station_info(self, station_id: str) -> dict[str, Any] | None:
        """Get tracking info for a station.
        
        Args:
            station_id: Station ID to query
            
        Returns:
            Dictionary with tracking info or None if not tracked
        """
        return self._alert_history.get(station_id)


def enrich_station_data(station: dict[str, Any], vehicle_lat: float, vehicle_lon: float) -> dict[str, Any]:
    """Enrich station data with distance and navigation information.
    
    Args:
        station: Station data dictionary
        vehicle_lat: Vehicle latitude
        vehicle_lon: Vehicle longitude
        
    Returns:
        Enriched station dictionary
    """
    station_lat = station.get("lat") or station.get("latitude")
    station_lon = station.get("lng") or station.get("longitude")
    
    if station_lat is None or station_lon is None:
        _LOGGER.warning("Station %s missing coordinates", station.get("id", "unknown"))
        return station
    
    # Calculate distance
    distance = calculate_distance(vehicle_lat, vehicle_lon, station_lat, station_lon)
    
    # Generate navigation URLs
    nav_urls = get_navigation_urls(
        station_lat,
        station_lon,
        station.get("name", "")
    )
    
    # Create enriched copy
    enriched = station.copy()
    enriched["distance_km"] = round(distance, 2)
    enriched["navigation_urls"] = nav_urls
    
    return enriched


def find_nearest_cheap_station(
    stations: list[dict[str, Any]],
    vehicle_lat: float,
    vehicle_lon: float,
    proximity_threshold: float,
) -> dict[str, Any] | None:
    """Find the nearest cheap station within proximity threshold.
    
    Args:
        stations: List of station dictionaries (should be sorted by price)
        vehicle_lat: Vehicle latitude
        vehicle_lon: Vehicle longitude
        proximity_threshold: Maximum distance in km
        
    Returns:
        Nearest cheap station within threshold or None
    """
    nearest = None
    min_distance = float('inf')
    
    for station in stations:
        station_lat = station.get("lat") or station.get("latitude")
        station_lon = station.get("lng") or station.get("longitude")
        
        if station_lat is None or station_lon is None:
            continue
        
        distance = calculate_distance(vehicle_lat, vehicle_lon, station_lat, station_lon)
        
        if distance <= proximity_threshold and distance < min_distance:
            min_distance = distance
            nearest = station.copy()
            nearest["distance_km"] = round(distance, 2)
    
    return nearest
