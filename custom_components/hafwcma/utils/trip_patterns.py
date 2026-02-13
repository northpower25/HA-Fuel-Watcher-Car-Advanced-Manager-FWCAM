"""Pattern recognition for trip tracking."""
from __future__ import annotations

import logging
from datetime import datetime, time
from math import radians, cos, sin, asin, sqrt
from typing import Any

_LOGGER = logging.getLogger(__name__)


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate the great circle distance between two points on earth (in meters).
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
        
    Returns:
        Distance in meters
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371000  # Radius of earth in meters
    return c * r


def is_within_radius(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    radius_m: float,
) -> bool:
    """Check if two points are within a specified radius.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
        radius_m: Radius in meters
        
    Returns:
        True if points are within radius
    """
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    return distance <= radius_m


def match_pattern(
    trip: dict[str, Any],
    pattern: dict[str, Any],
) -> bool:
    """Check if a trip matches a pattern.
    
    Args:
        trip: Trip data dictionary
        pattern: Pattern data dictionary
        
    Returns:
        True if trip matches pattern
    """
    # Check start location
    start_lat = trip.get("start_latitude")
    start_lon = trip.get("start_longitude")
    pattern_start_lat = pattern.get("start_latitude")
    pattern_start_lon = pattern.get("start_longitude")
    
    if not all([start_lat, start_lon, pattern_start_lat, pattern_start_lon]):
        return False
    
    start_radius = pattern.get("start_radius_m", 200.0)
    if not is_within_radius(
        start_lat, start_lon,
        pattern_start_lat, pattern_start_lon,
        start_radius
    ):
        return False
    
    # Check end location
    end_lat = trip.get("end_latitude")
    end_lon = trip.get("end_longitude")
    pattern_end_lat = pattern.get("end_latitude")
    pattern_end_lon = pattern.get("end_longitude")
    
    if not all([end_lat, end_lon, pattern_end_lat, pattern_end_lon]):
        return False
    
    end_radius = pattern.get("end_radius_m", 200.0)
    if not is_within_radius(
        end_lat, end_lon,
        pattern_end_lat, pattern_end_lon,
        end_radius
    ):
        return False
    
    # Check distance tolerance
    trip_distance = trip.get("distance_km", 0)
    pattern_avg_distance = pattern.get("avg_distance_km", 0)
    distance_tolerance = pattern.get("distance_tolerance_percent", 10.0)
    
    if pattern_avg_distance > 0:
        distance_diff_percent = abs(trip_distance - pattern_avg_distance) / pattern_avg_distance * 100
        if distance_diff_percent > distance_tolerance:
            return False
    
    # Check weekday constraint
    weekdays = pattern.get("weekdays")
    if weekdays is not None and isinstance(weekdays, list):
        try:
            trip_start = trip.get("timestamp_start")
            if trip_start:
                from homeassistant.util import dt as dt_util
                trip_dt = dt_util.parse_datetime(trip_start)
                if trip_dt:
                    trip_weekday = trip_dt.weekday()  # 0 = Monday
                    if trip_weekday not in weekdays:
                        return False
        except (ValueError, TypeError):
            pass
    
    # Check time window constraint
    time_window_start = pattern.get("time_window_start")
    time_window_end = pattern.get("time_window_end")
    
    if time_window_start and time_window_end:
        try:
            trip_start = trip.get("timestamp_start")
            if trip_start:
                from homeassistant.util import dt as dt_util
                trip_dt = dt_util.parse_datetime(trip_start)
                if trip_dt:
                    trip_time = trip_dt.time()
                    
                    # Parse time windows if they're strings
                    if isinstance(time_window_start, str):
                        time_window_start = datetime.strptime(time_window_start, "%H:%M:%S").time()
                    if isinstance(time_window_end, str):
                        time_window_end = datetime.strptime(time_window_end, "%H:%M:%S").time()
                    
                    # Check if trip time is within window
                    if not (time_window_start <= trip_time <= time_window_end):
                        return False
        except (ValueError, TypeError) as err:
            _LOGGER.warning("Error checking time window: %s", err)
    
    return True


def find_matching_patterns(
    trip: dict[str, Any],
    patterns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find all patterns that match a trip.
    
    Args:
        trip: Trip data dictionary
        patterns: List of pattern dictionaries
        
    Returns:
        List of matching patterns, sorted by match quality (best first)
    """
    matching = []
    
    for pattern in patterns:
        if match_pattern(trip, pattern):
            # Calculate match quality score
            score = calculate_match_quality(trip, pattern)
            matching.append({
                "pattern": pattern,
                "score": score,
            })
    
    # Sort by score (highest first)
    matching.sort(key=lambda x: x["score"], reverse=True)
    
    return [m["pattern"] for m in matching]


def calculate_match_quality(
    trip: dict[str, Any],
    pattern: dict[str, Any],
) -> float:
    """Calculate a quality score for how well a trip matches a pattern.
    
    Higher score means better match. Score is in range [0, 100].
    
    Args:
        trip: Trip data dictionary
        pattern: Pattern data dictionary
        
    Returns:
        Match quality score (0-100)
    """
    score = 100.0
    
    # Distance accuracy (0-30 points)
    trip_distance = trip.get("distance_km", 0)
    pattern_avg_distance = pattern.get("avg_distance_km", 0)
    
    if pattern_avg_distance > 0:
        distance_diff_percent = abs(trip_distance - pattern_avg_distance) / pattern_avg_distance * 100
        distance_score = max(0, 30 - distance_diff_percent)
        score = score - 30 + distance_score
    
    # Location accuracy (0-40 points, 20 per location)
    start_lat = trip.get("start_latitude")
    start_lon = trip.get("start_longitude")
    pattern_start_lat = pattern.get("start_latitude")
    pattern_start_lon = pattern.get("start_longitude")
    
    if all([start_lat, start_lon, pattern_start_lat, pattern_start_lon]):
        start_distance = haversine_distance(
            start_lat, start_lon,
            pattern_start_lat, pattern_start_lon,
        )
        start_radius = pattern.get("start_radius_m", 200.0)
        start_score = max(0, 20 * (1 - start_distance / start_radius))
        score = score - 20 + start_score
    
    end_lat = trip.get("end_latitude")
    end_lon = trip.get("end_longitude")
    pattern_end_lat = pattern.get("end_latitude")
    pattern_end_lon = pattern.get("end_longitude")
    
    if all([end_lat, end_lon, pattern_end_lat, pattern_end_lon]):
        end_distance = haversine_distance(
            end_lat, end_lon,
            pattern_end_lat, pattern_end_lon,
        )
        end_radius = pattern.get("end_radius_m", 200.0)
        end_score = max(0, 20 * (1 - end_distance / end_radius))
        score = score - 20 + end_score
    
    # Pattern usage frequency (0-30 points)
    match_count = pattern.get("match_count", 0)
    frequency_score = min(30, match_count * 2)  # Up to 15 uses = full score
    score = score - 30 + frequency_score
    
    return max(0, min(100, score))


def detect_recurring_trips(
    trips: list[dict[str, Any]],
    min_occurrences: int = 3,
    location_radius_m: float = 200.0,
    distance_tolerance_percent: float = 10.0,
) -> list[dict[str, Any]]:
    """Detect recurring trip patterns from trip history.
    
    Args:
        trips: List of trip dictionaries
        min_occurrences: Minimum number of similar trips to form a pattern
        location_radius_m: Radius in meters for location matching
        distance_tolerance_percent: Tolerance for distance variation
        
    Returns:
        List of detected pattern suggestions
    """
    if len(trips) < min_occurrences:
        return []
    
    patterns = []
    used_trip_indices = set()
    
    # Sort trips by timestamp (oldest first)
    sorted_trips = sorted(trips, key=lambda x: x.get("timestamp_start", ""))
    
    # Group similar trips
    for i, trip in enumerate(sorted_trips):
        if i in used_trip_indices:
            continue
        
        # Find similar trips
        similar = [trip]
        similar_indices = {i}
        
        for j, other_trip in enumerate(sorted_trips[i + 1:], start=i + 1):
            if j in used_trip_indices:
                continue
            
            if are_trips_similar(
                trip,
                other_trip,
                location_radius_m,
                distance_tolerance_percent,
            ):
                similar.append(other_trip)
                similar_indices.add(j)
        
        # Check if we have enough occurrences
        if len(similar) >= min_occurrences:
            pattern = create_pattern_from_trips(similar)
            if pattern:
                patterns.append(pattern)
                used_trip_indices.update(similar_indices)
    
    return patterns


def are_trips_similar(
    trip1: dict[str, Any],
    trip2: dict[str, Any],
    location_radius_m: float,
    distance_tolerance_percent: float,
) -> bool:
    """Check if two trips are similar enough to be part of same pattern.
    
    Args:
        trip1: First trip dictionary
        trip2: Second trip dictionary
        location_radius_m: Radius in meters for location matching
        distance_tolerance_percent: Tolerance for distance variation
        
    Returns:
        True if trips are similar
    """
    # Check start locations
    start1_lat = trip1.get("start_latitude")
    start1_lon = trip1.get("start_longitude")
    start2_lat = trip2.get("start_latitude")
    start2_lon = trip2.get("start_longitude")
    
    if not all([start1_lat, start1_lon, start2_lat, start2_lon]):
        return False
    
    if not is_within_radius(
        start1_lat, start1_lon,
        start2_lat, start2_lon,
        location_radius_m
    ):
        return False
    
    # Check end locations
    end1_lat = trip1.get("end_latitude")
    end1_lon = trip1.get("end_longitude")
    end2_lat = trip2.get("end_latitude")
    end2_lon = trip2.get("end_longitude")
    
    if not all([end1_lat, end1_lon, end2_lat, end2_lon]):
        return False
    
    if not is_within_radius(
        end1_lat, end1_lon,
        end2_lat, end2_lon,
        location_radius_m
    ):
        return False
    
    # Check distance similarity
    dist1 = trip1.get("distance_km", 0)
    dist2 = trip2.get("distance_km", 0)
    
    if dist1 > 0 and dist2 > 0:
        avg_dist = (dist1 + dist2) / 2
        # Additional safety check (should never be zero given the condition above)
        if avg_dist > 0:
            dist_diff_percent = abs(dist1 - dist2) / avg_dist * 100
            if dist_diff_percent > distance_tolerance_percent:
                return False
    
    return True


def create_pattern_from_trips(trips: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Create a pattern definition from a group of similar trips.
    
    Args:
        trips: List of similar trip dictionaries
        
    Returns:
        Pattern dictionary or None if pattern cannot be created
    """
    if not trips:
        return None
    
    # Calculate average location for start
    start_lats = [t.get("start_latitude") for t in trips if t.get("start_latitude")]
    start_lons = [t.get("start_longitude") for t in trips if t.get("start_longitude")]
    
    if not start_lats or not start_lons:
        return None
    
    avg_start_lat = sum(start_lats) / len(start_lats)
    avg_start_lon = sum(start_lons) / len(start_lons)
    
    # Calculate average location for end
    end_lats = [t.get("end_latitude") for t in trips if t.get("end_latitude")]
    end_lons = [t.get("end_longitude") for t in trips if t.get("end_longitude")]
    
    if not end_lats or not end_lons:
        return None
    
    avg_end_lat = sum(end_lats) / len(end_lats)
    avg_end_lon = sum(end_lons) / len(end_lons)
    
    # Calculate average distance
    distances = [t.get("distance_km", 0) for t in trips if t.get("distance_km", 0) > 0]
    avg_distance = sum(distances) / len(distances) if distances else 0
    
    # Calculate average duration
    durations = [t.get("duration_minutes", 0) for t in trips if t.get("duration_minutes", 0) > 0]
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    # Calculate average fuel consumption
    consumptions = [t.get("fuel_consumed", 0) for t in trips if t.get("fuel_consumed", 0) > 0]
    avg_consumption = sum(consumptions) / len(consumptions) if consumptions else 0
    
    # Detect common weekdays
    weekdays = []
    try:
        from homeassistant.util import dt as dt_util
        for trip in trips:
            trip_start = trip.get("timestamp_start")
            if trip_start:
                trip_dt = dt_util.parse_datetime(trip_start)
                if trip_dt:
                    weekday = trip_dt.weekday()
                    if weekday not in weekdays:
                        weekdays.append(weekday)
    except (ValueError, TypeError):
        pass
    
    # Generate pattern name
    from_addr = trips[0].get("start_address", "Location A")
    to_addr = trips[0].get("end_address", "Location B")
    
    # Truncate addresses for name
    from_short = from_addr.split(",")[0] if from_addr else "Start"
    to_short = to_addr.split(",")[0] if to_addr else "End"
    
    pattern_name = f"{from_short} → {to_short}"
    
    # Determine most common category
    categories = [t.get("category", "private") for t in trips]
    most_common_category = max(set(categories), key=categories.count)
    
    pattern = {
        "name": pattern_name,
        "start_latitude": avg_start_lat,
        "start_longitude": avg_start_lon,
        "start_radius_m": 200.0,
        "end_latitude": avg_end_lat,
        "end_longitude": avg_end_lon,
        "end_radius_m": 200.0,
        "weekdays": weekdays if weekdays else None,
        "distance_tolerance_percent": 10.0,
        "category": most_common_category,
        "purpose": f"Regular trip: {pattern_name}",
        "is_anonymized": False,
        "is_tax_relevant": most_common_category == "business",
        "match_count": len(trips),
        "avg_distance_km": avg_distance,
        "avg_duration_minutes": avg_duration,
        "avg_fuel_consumption": avg_consumption,
    }
    
    return pattern
