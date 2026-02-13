"""Anonymization utilities for trip tracking privacy."""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Any

_LOGGER = logging.getLogger(__name__)


def should_anonymize_trip(
    trip_start: datetime,
    anonymization_schedules: list[dict[str, Any]],
) -> bool:
    """Check if a trip should be anonymized based on time rules.
    
    Args:
        trip_start: Trip start datetime
        anonymization_schedules: List of anonymization schedule dictionaries
        
    Returns:
        True if trip should be anonymized
    """
    if not anonymization_schedules:
        return False
    
    trip_time = trip_start.time()
    trip_weekday = trip_start.weekday()  # 0 = Monday
    
    for schedule in anonymization_schedules:
        if not schedule.get("enabled", True):
            continue
        
        # Check weekdays
        weekdays = schedule.get("weekdays")
        if weekdays and trip_weekday not in weekdays:
            continue
        
        # Check time window
        time_start = schedule.get("time_start")
        time_end = schedule.get("time_end")
        
        if not time_start or not time_end:
            continue
        
        # Parse times if they're strings
        if isinstance(time_start, str):
            try:
                time_start = datetime.strptime(time_start, "%H:%M:%S").time()
            except ValueError:
                continue
        
        if isinstance(time_end, str):
            try:
                time_end = datetime.strptime(time_end, "%H:%M:%S").time()
            except ValueError:
                continue
        
        # Check if trip time is within window
        if time_start <= trip_time <= time_end:
            return True
    
    return False


def anonymize_trip_data(trip: dict[str, Any]) -> dict[str, Any]:
    """Remove location data from a trip for privacy.
    
    Args:
        trip: Trip data dictionary
        
    Returns:
        Anonymized trip data dictionary
    """
    trip = trip.copy()
    
    # Remove GPS coordinates
    trip["start_latitude"] = None
    trip["start_longitude"] = None
    trip["end_latitude"] = None
    trip["end_longitude"] = None
    
    # Remove addresses
    trip["start_address"] = None
    trip["end_address"] = None
    
    # Remove POI references
    trip["start_poi_id"] = None
    trip["end_poi_id"] = None
    
    # Mark as anonymized
    trip["is_anonymized"] = True
    
    # Keep other data (distance, fuel, costs) for statistics
    return trip


def apply_retention_policy(
    trips: list[dict[str, Any]],
    retention_days: int,
) -> tuple[list[dict[str, Any]], int]:
    """Remove trips older than retention period.
    
    Args:
        trips: List of trip dictionaries
        retention_days: Number of days to retain trips
        
    Returns:
        Tuple of (filtered trips, number of trips removed)
    """
    from homeassistant.util import dt as dt_util
    
    if retention_days <= 0:
        return trips, 0
    
    cutoff_date = dt_util.now() - timedelta(days=retention_days)
    
    filtered_trips = []
    removed_count = 0
    
    for trip in trips:
        trip_end = trip.get("timestamp_end")
        if trip_end:
            try:
                trip_dt = dt_util.parse_datetime(trip_end)
                if trip_dt and trip_dt >= cutoff_date:
                    filtered_trips.append(trip)
                else:
                    removed_count += 1
            except (ValueError, TypeError):
                # Keep trip if we can't parse the date
                filtered_trips.append(trip)
        else:
            # Keep trip if no end timestamp
            filtered_trips.append(trip)
    
    if removed_count > 0:
        _LOGGER.info(
            "Retention policy: removed %d trips older than %d days",
            removed_count,
            retention_days,
        )
    
    return filtered_trips, removed_count


def create_default_anonymization_schedules() -> list[dict[str, Any]]:
    """Create default anonymization schedules.
    
    Returns:
        List of default anonymization schedule dictionaries
    """
    return [
        {
            "name": "Work Commute (Morning)",
            "enabled": False,
            "weekdays": [0, 1, 2, 3, 4],  # Monday-Friday
            "time_start": "07:00:00",
            "time_end": "09:00:00",
            "description": "Anonymize morning commute trips",
        },
        {
            "name": "Work Commute (Evening)",
            "enabled": False,
            "weekdays": [0, 1, 2, 3, 4],  # Monday-Friday
            "time_start": "16:00:00",
            "time_end": "19:00:00",
            "description": "Anonymize evening commute trips",
        },
    ]


def get_privacy_summary(
    trip_config: dict[str, Any],
    trip_statistics: dict[str, Any],
) -> dict[str, Any]:
    """Generate a summary of privacy settings and their impact.
    
    Args:
        trip_config: Trip tracking configuration
        trip_statistics: Trip statistics
        
    Returns:
        Privacy summary dictionary
    """
    total_trips = trip_statistics.get("total_trips", 0)
    
    # Count anonymization schedules
    schedules = trip_config.get("anonymization_schedules", [])
    active_schedules = sum(1 for s in schedules if s.get("enabled", True))
    
    # Estimate percentage of trips that would be anonymized
    # This is a rough estimate based on schedule time windows
    estimated_anonymized_percent = 0
    if active_schedules > 0:
        # Assume 2 trips per day on average
        # Count total hours covered by schedules
        total_hours = 0
        for schedule in schedules:
            if not schedule.get("enabled", True):
                continue
            
            try:
                time_start = schedule.get("time_start")
                time_end = schedule.get("time_end")
                
                if isinstance(time_start, str):
                    time_start = datetime.strptime(time_start, "%H:%M:%S").time()
                if isinstance(time_end, str):
                    time_end = datetime.strptime(time_end, "%H:%M:%S").time()
                
                # Calculate hours in window
                start_minutes = time_start.hour * 60 + time_start.minute
                end_minutes = time_end.hour * 60 + time_end.minute
                hours = (end_minutes - start_minutes) / 60
                
                # Count weekdays
                weekdays = schedule.get("weekdays", [])
                if weekdays:
                    # Scale by proportion of week
                    hours = hours * (len(weekdays) / 7.0)
                
                total_hours += hours
            except (ValueError, TypeError, AttributeError):
                pass
        
        # Estimate percentage (assuming trips evenly distributed across day)
        estimated_anonymized_percent = min(100, (total_hours / 24.0) * 100)
    
    return {
        "tracking_enabled": trip_config.get("enabled", False),
        "auto_geocoding": trip_config.get("auto_geocode", True),
        "retention_days": trip_config.get("retention_days", 365),
        "active_anonymization_schedules": active_schedules,
        "total_anonymization_schedules": len(schedules),
        "estimated_anonymized_percent": round(estimated_anonymized_percent, 1),
        "total_trips_recorded": total_trips,
        "data_stored_locally": True,
        "privacy_notice_accepted": trip_config.get("privacy_notice_accepted", False),
    }


def generate_privacy_notice() -> str:
    """Generate privacy notice text for trip tracking.
    
    Returns:
        Privacy notice text
    """
    return """
Trip Tracking Privacy Notice

By enabling trip tracking, you acknowledge and agree to the following:

DATA COLLECTION:
- GPS coordinates (start and end locations)
- Timestamps (trip start and end times)
- Odometer readings and distances
- Fuel consumption data
- Addresses (via reverse geocoding from OpenStreetMap)

DATA STORAGE:
- All data is stored locally in your Home Assistant instance
- Data is NOT sent to external servers (except for address geocoding)
- Storage location: .storage/hafwcma_<entry_id>.json

DATA USAGE:
- Calculate trip costs and statistics
- Detect recurring trip patterns
- Generate reports and insights

YOUR RIGHTS:
- View all collected data via sensors and attributes
- Edit or delete individual trips
- Configure data retention period
- Set up time-based anonymization
- Export data at any time
- Disable tracking to stop data collection

THIRD-PARTY SERVICES:
- OpenStreetMap Nominatim API is used for address resolution
- Geocoding requests include GPS coordinates only
- Rate limited to 1 request per second per Nominatim usage policy

GDPR COMPLIANCE:
- Right to be informed: This notice
- Right to access: View all trip data
- Right to erasure: Delete trips or disable tracking
- Right to data portability: Export functionality
- Data minimization: Only essential data collected
- Storage limitation: Configurable retention policy

For more information, see the documentation or contact support.
"""
