"""POI (Point of Interest) management for trip tracking."""
from __future__ import annotations

import logging
from typing import Any

from .trip_patterns import haversine_distance, is_within_radius

_LOGGER = logging.getLogger(__name__)


def find_poi_at_location(
    latitude: float | None,
    longitude: float | None,
    pois: list[dict[str, Any]],
    max_distance_m: float = 200.0,
) -> dict[str, Any] | None:
    """Find a POI at or near a given location.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        pois: List of POI dictionaries
        max_distance_m: Maximum distance in meters
        
    Returns:
        Matching POI or None if not found
    """
    if latitude is None or longitude is None:
        return None
    
    closest_poi = None
    closest_distance = float('inf')
    
    for poi in pois:
        poi_lat = poi.get("latitude")
        poi_lon = poi.get("longitude")
        
        if poi_lat is None or poi_lon is None:
            continue
        
        # Check if within POI radius
        poi_radius = poi.get("radius_m", 200.0)
        if is_within_radius(latitude, longitude, poi_lat, poi_lon, poi_radius):
            distance = haversine_distance(latitude, longitude, poi_lat, poi_lon)
            if distance < closest_distance and distance <= max_distance_m:
                closest_distance = distance
                closest_poi = poi
    
    return closest_poi


def update_poi_visit(poi: dict[str, Any]) -> None:
    """Update POI visit statistics.
    
    Args:
        poi: POI dictionary to update
    """
    poi["visit_count"] = poi.get("visit_count", 0) + 1
    
    from homeassistant.util import dt as dt_util
    poi["updated_at"] = dt_util.now().isoformat()


def suggest_poi_from_location(
    latitude: float,
    longitude: float,
    address: str | None = None,
    poi_type: str = "custom",
) -> dict[str, Any]:
    """Suggest a POI definition from a location.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        address: Optional address string
        poi_type: Type of POI
        
    Returns:
        POI suggestion dictionary
    """
    # Generate name from address
    name = "Unknown Location"
    if address:
        # Use first part of address as name
        parts = address.split(",")
        if parts:
            name = parts[0].strip()
    
    # Determine icon based on type
    icon_map = {
        "home": "mdi:home",
        "work": "mdi:briefcase",
        "gas_station": "mdi:gas-station",
        "shop": "mdi:shopping",
        "parking": "mdi:parking",
        "custom": "mdi:map-marker",
    }
    icon = icon_map.get(poi_type, "mdi:map-marker")
    
    return {
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
        "radius_m": 200.0,
        "address": address,
        "poi_type": poi_type,
        "category": None,
        "icon": icon,
        "visit_count": 0,
        "is_favorite": False,
        "notes": None,
    }


def auto_detect_home_work(
    trips: list[dict[str, Any]],
    existing_pois: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Auto-detect Home and Work locations from trip patterns.
    
    Identifies the two most frequently visited locations as potential
    Home and Work locations.
    
    Args:
        trips: List of trip dictionaries
        existing_pois: List of existing POIs (to avoid duplicates)
        
    Returns:
        List of suggested POI dictionaries
    """
    if not trips:
        return []
    
    # Count visits to each location
    location_visits: dict[tuple[float, float], dict[str, Any]] = {}
    
    for trip in trips:
        # Count start locations
        start_lat = trip.get("start_latitude")
        start_lon = trip.get("start_longitude")
        if start_lat and start_lon:
            key = (round(start_lat, 3), round(start_lon, 3))
            if key not in location_visits:
                location_visits[key] = {
                    "latitude": start_lat,
                    "longitude": start_lon,
                    "address": trip.get("start_address"),
                    "count": 0,
                }
            location_visits[key]["count"] += 1
        
        # Count end locations
        end_lat = trip.get("end_latitude")
        end_lon = trip.get("end_longitude")
        if end_lat and end_lon:
            key = (round(end_lat, 3), round(end_lon, 3))
            if key not in location_visits:
                location_visits[key] = {
                    "latitude": end_lat,
                    "longitude": end_lon,
                    "address": trip.get("end_address"),
                    "count": 0,
                }
            location_visits[key]["count"] += 1
    
    if len(location_visits) < 2:
        return []
    
    # Sort by visit count
    sorted_locations = sorted(
        location_visits.values(),
        key=lambda x: x["count"],
        reverse=True,
    )
    
    suggestions = []
    
    # Check if these locations already exist as POIs
    for i, location in enumerate(sorted_locations[:2]):
        poi_type = "home" if i == 0 else "work"
        
        # Check if POI of this type already exists
        existing_poi = None
        for poi in existing_pois:
            if poi.get("poi_type") == poi_type:
                existing_poi = poi
                break
        
        if existing_poi:
            # Check if this location is the same as existing POI
            existing_lat = existing_poi.get("latitude")
            existing_lon = existing_poi.get("longitude")
            if existing_lat and existing_lon:
                if is_within_radius(
                    location["latitude"],
                    location["longitude"],
                    existing_lat,
                    existing_lon,
                    500.0,  # 500m radius for matching
                ):
                    continue
        
        # Create POI suggestion
        poi = suggest_poi_from_location(
            location["latitude"],
            location["longitude"],
            location.get("address"),
            poi_type,
        )
        poi["name"] = "Home" if poi_type == "home" else "Work"
        poi["visit_count"] = location["count"]
        poi["is_favorite"] = True
        
        suggestions.append(poi)
    
    return suggestions


def detect_gas_station_pois(
    trips: list[dict[str, Any]],
    refueling_log: list[dict[str, Any]],
    existing_pois: list[dict[str, Any]],
    min_visits: int = 2,
) -> list[dict[str, Any]]:
    """Detect frequently used gas stations from refueling log.
    
    Args:
        trips: List of trip dictionaries
        refueling_log: List of refueling events
        existing_pois: List of existing POIs (to avoid duplicates)
        min_visits: Minimum number of visits to suggest as POI
        
    Returns:
        List of suggested gas station POI dictionaries
    """
    if not refueling_log:
        return []
    
    # Count refueling events at each station location
    station_visits: dict[tuple[float, float], dict[str, Any]] = {}
    
    for refuel in refueling_log:
        lat = refuel.get("latitude")
        lon = refuel.get("longitude")
        
        if not lat or not lon:
            continue
        
        # Round to 3 decimals (~100m precision)
        key = (round(lat, 3), round(lon, 3))
        
        if key not in station_visits:
            station_visits[key] = {
                "latitude": lat,
                "longitude": lon,
                "station_name": refuel.get("station_name"),
                "count": 0,
            }
        station_visits[key]["count"] += 1
    
    # Filter stations with enough visits
    frequent_stations = [
        station for station in station_visits.values()
        if station["count"] >= min_visits
    ]
    
    if not frequent_stations:
        return []
    
    suggestions = []
    
    for station in frequent_stations:
        # Check if already exists
        exists = False
        for poi in existing_pois:
            if poi.get("poi_type") == "gas_station":
                poi_lat = poi.get("latitude")
                poi_lon = poi.get("longitude")
                if poi_lat and poi_lon:
                    if is_within_radius(
                        station["latitude"],
                        station["longitude"],
                        poi_lat,
                        poi_lon,
                        200.0,
                    ):
                        exists = True
                        break
        
        if exists:
            continue
        
        # Create POI suggestion
        name = station.get("station_name") or "Gas Station"
        
        poi = {
            "name": name,
            "latitude": station["latitude"],
            "longitude": station["longitude"],
            "radius_m": 150.0,  # Smaller radius for gas stations
            "address": None,
            "poi_type": "gas_station",
            "category": None,
            "icon": "mdi:gas-station",
            "visit_count": station["count"],
            "is_favorite": station["count"] >= 5,  # Favorite if 5+ visits
            "notes": f"Visited {station['count']} times",
        }
        
        suggestions.append(poi)
    
    return suggestions
