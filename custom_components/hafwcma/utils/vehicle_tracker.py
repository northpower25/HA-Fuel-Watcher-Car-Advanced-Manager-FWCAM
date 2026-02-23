"""Vehicle data tracking and analysis utilities."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

# Constants for missed trip detection
# Confidence score for trips recovered from odometer history after system restart
# Scale: 0.3 (low) to 1.0 (high), where 0.5 indicates medium confidence
RECOVERED_TRIP_CONFIDENCE = 0.5

# Confidence score for refuelings recovered from tank level history after system restart
# Scale: 0.3 (low) to 1.0 (high), where 0.5 indicates medium confidence
RECOVERED_REFUELING_CONFIDENCE = 0.5

# Time window in minutes for detecting duplicate trips
DUPLICATE_DETECTION_WINDOW_MINUTES = 5

# Default lookback window in hours for checking missed trips
DEFAULT_MISSED_TRIP_LOOKBACK_HOURS = 24

# Default lookback window in hours for checking missed refuelings
DEFAULT_MISSED_REFUELING_LOOKBACK_HOURS = 24


@dataclass
class VehicleSnapshot:
    """Snapshot of vehicle data at a point in time."""
    
    timestamp: datetime
    odometer_km: float | None
    tank_level: float | None
    range_km: float | None
    latitude: float | None
    longitude: float | None


class VehicleDataTracker:
    """Track vehicle data changes and detect events like refueling."""
    
    # Default threshold as percentage of tank capacity
    REFUEL_DETECTION_THRESHOLD_PERCENT = 3.5
    # Merge time window for close refueling events (in seconds)
    REFUEL_MERGE_TIME_WINDOW_SECONDS = 900  # 15 minutes
    
    def __init__(self, tank_capacity: float = 50.0) -> None:
        """Initialize the tracker.
        
        Args:
            tank_capacity: Tank capacity in liters (used for percentage-based detection)
        """
        self._previous_snapshot: VehicleSnapshot | None = None
        self._current_snapshot: VehicleSnapshot | None = None
        self._last_refuel_timestamp: datetime | None = None
        self._tank_capacity = tank_capacity
        self._pending_refuel_liters = 0.0  # Track accumulated refuel for merging
        self._pending_refuel_start = None  # Start time of current refuel session
        self._refuel_session_start_snapshot: VehicleSnapshot | None = None  # Snapshot at start of refuel session
        
    def update(self, vehicle_data: dict[str, Any]) -> dict[str, Any]:
        """Update with new vehicle data and detect changes.
        
        Args:
            vehicle_data: Current vehicle data from entities
            
        Returns:
            Dictionary with detected events and calculations
        """
        # Create new snapshot
        self._previous_snapshot = self._current_snapshot
        self._current_snapshot = VehicleSnapshot(
            timestamp=dt_util.now(),
            odometer_km=vehicle_data.get("odometer_km"),
            tank_level=vehicle_data.get("tank_level"),
            range_km=vehicle_data.get("range_km"),
            latitude=vehicle_data.get("latitude"),
            longitude=vehicle_data.get("longitude"),
        )
        
        result = {
            "refueling_detected": False,
            "fuel_consumed": None,
            "distance_traveled": None,
            "average_consumption": None,  # L/100km
        }
        
        # Need at least 2 snapshots to detect changes
        if not self._previous_snapshot:
            return result
            
        # Detect refueling (significant tank level increase)
        if (
            self._current_snapshot.tank_level is not None
            and self._previous_snapshot.tank_level is not None
        ):
            tank_diff = self._current_snapshot.tank_level - self._previous_snapshot.tank_level
            
            # Calculate threshold based on percentage of tank capacity
            threshold = (self.REFUEL_DETECTION_THRESHOLD_PERCENT / 100.0) * self._tank_capacity
            
            # Check if this is a refueling event
            if tank_diff > threshold:
                # Check if this is part of an ongoing refueling session (within merge window)
                if (
                    self._pending_refuel_start is not None
                    and (self._current_snapshot.timestamp - self._pending_refuel_start).total_seconds()
                    <= self.REFUEL_MERGE_TIME_WINDOW_SECONDS
                ):
                    # Accumulate into pending refuel
                    self._pending_refuel_liters += tank_diff
                    _LOGGER.debug(
                        "Merging refuel: +%.2f liters (total pending: %.2f liters)",
                        tank_diff,
                        self._pending_refuel_liters,
                    )
                else:
                    # This is a new refueling session or merge window expired
                    # Report any pending refuel first
                    if self._pending_refuel_liters > 0 and self._refuel_session_start_snapshot is not None:
                        result["refueling_detected"] = True
                        result["fuel_added"] = self._pending_refuel_liters
                        result["refuel_timestamp"] = self._pending_refuel_start.isoformat()
                        result["refuel_odometer_km"] = self._refuel_session_start_snapshot.odometer_km
                        result["refuel_latitude"] = self._refuel_session_start_snapshot.latitude
                        result["refuel_longitude"] = self._refuel_session_start_snapshot.longitude
                        
                        _LOGGER.info(
                            "Refueling session complete: %.2f liters added at %s (odometer: %.1f km)",
                            self._pending_refuel_liters,
                            self._pending_refuel_start.isoformat(),
                            self._refuel_session_start_snapshot.odometer_km or 0,
                        )
                    
                    # Start new refueling session
                    self._pending_refuel_liters = tank_diff
                    self._pending_refuel_start = self._current_snapshot.timestamp
                    self._refuel_session_start_snapshot = self._current_snapshot
                    self._last_refuel_timestamp = self._current_snapshot.timestamp
                    
                    _LOGGER.debug(
                        "New refueling session started: +%.2f liters at %s",
                        tank_diff,
                        self._current_snapshot.timestamp.isoformat(),
                    )
            elif self._pending_refuel_liters > 0:
                # No more increases detected, finalize pending refuel if merge window expired
                if (
                    self._pending_refuel_start is not None
                    and (self._current_snapshot.timestamp - self._pending_refuel_start).total_seconds()
                    > self.REFUEL_MERGE_TIME_WINDOW_SECONDS
                    and self._refuel_session_start_snapshot is not None
                ):
                    result["refueling_detected"] = True
                    result["fuel_added"] = self._pending_refuel_liters
                    result["refuel_timestamp"] = self._pending_refuel_start.isoformat()
                    result["refuel_odometer_km"] = self._refuel_session_start_snapshot.odometer_km
                    result["refuel_latitude"] = self._refuel_session_start_snapshot.latitude
                    result["refuel_longitude"] = self._refuel_session_start_snapshot.longitude
                    
                    _LOGGER.info(
                        "Refueling session complete: %.2f liters added at %s (odometer: %.1f km)",
                        self._pending_refuel_liters,
                        self._pending_refuel_start.isoformat(),
                        self._refuel_session_start_snapshot.odometer_km or 0,
                    )
                    
                    # Reset pending refuel
                    self._pending_refuel_liters = 0.0
                    self._pending_refuel_start = None
                    self._refuel_session_start_snapshot = None
        
        # Calculate fuel consumption (only if no refueling)
        if (
            not result["refueling_detected"]
            and self._current_snapshot.tank_level is not None
            and self._previous_snapshot.tank_level is not None
            and self._current_snapshot.odometer_km is not None
            and self._previous_snapshot.odometer_km is not None
        ):
            fuel_consumed = self._previous_snapshot.tank_level - self._current_snapshot.tank_level
            distance_traveled = self._current_snapshot.odometer_km - self._previous_snapshot.odometer_km
            
            if fuel_consumed > 0 and distance_traveled > 0:
                result["fuel_consumed"] = fuel_consumed
                result["distance_traveled"] = distance_traveled
                # Calculate L/100km
                result["average_consumption"] = (fuel_consumed / distance_traveled) * 100
                
                _LOGGER.debug(
                    "Consumption: %.2f L over %.2f km = %.2f L/100km",
                    fuel_consumed,
                    distance_traveled,
                    result["average_consumption"],
                )
        
        return result
    
    def get_current_snapshot(self) -> VehicleSnapshot | None:
        """Get the current vehicle snapshot."""
        return self._current_snapshot
    
    def get_previous_snapshot(self) -> VehicleSnapshot | None:
        """Get the previous vehicle snapshot."""
        return self._previous_snapshot


class TripTracker:
    """Track trips based on vehicle movement."""
    
    # Default minimum trip distance in km
    DEFAULT_MIN_TRIP_DISTANCE_KM = 0.5
    # Default merge time window for short stops (in seconds)
    DEFAULT_MERGE_TIME_WINDOW_SECONDS = 300  # 5 minutes
    
    def __init__(
        self,
        min_trip_distance_km: float = DEFAULT_MIN_TRIP_DISTANCE_KM,
        merge_time_window_seconds: int = DEFAULT_MERGE_TIME_WINDOW_SECONDS,
    ) -> None:
        """Initialize the trip tracker.
        
        Args:
            min_trip_distance_km: Minimum distance to consider as a trip
            merge_time_window_seconds: Time window to merge short stops
        """
        self._min_trip_distance_km = min_trip_distance_km
        self._merge_time_window_seconds = merge_time_window_seconds
        
        # Current trip state
        self._trip_in_progress = False
        self._trip_start_snapshot: VehicleSnapshot | None = None
        self._trip_last_snapshot: VehicleSnapshot | None = None
        self._trip_stop_timestamp: datetime | None = None
        
    def update(self, snapshot: VehicleSnapshot) -> dict[str, Any]:
        """Update with new vehicle snapshot and detect trips.
        
        Args:
            snapshot: Current vehicle snapshot
            
        Returns:
            Dictionary with trip detection results:
            - trip_started: bool - True if new trip started
            - trip_ended: bool - True if trip ended
            - trip_data: dict - Trip data if trip ended
            - on_trip: bool - True if currently on a trip
        """
        result = {
            "trip_started": False,
            "trip_ended": False,
            "trip_data": None,
            "on_trip": self._trip_in_progress,
        }
        
        # Need odometer data to detect trips
        if snapshot.odometer_km is None:
            return result
        
        # Check if trip should start
        if not self._trip_in_progress:
            # Start a new trip
            if self._should_start_trip(snapshot):
                self._start_trip(snapshot)
                result["trip_started"] = True
                result["on_trip"] = True
                _LOGGER.info(
                    "Trip started at odometer %.1f km",
                    snapshot.odometer_km,
                )
        else:
            # Trip in progress - check if it should end
            if self._should_end_trip(snapshot):
                trip_data = self._end_trip(snapshot)
                result["trip_ended"] = True
                result["trip_data"] = trip_data
                result["on_trip"] = False
                _LOGGER.info(
                    "Trip ended: %.2f km, duration: %s",
                    trip_data.get("distance_km", 0),
                    trip_data.get("duration", "unknown"),
                )
            else:
                # Update last snapshot for ongoing trip
                self._trip_last_snapshot = snapshot
                # Clear stop timestamp if vehicle is moving again
                if self._trip_stop_timestamp and self._is_vehicle_moving(snapshot):
                    _LOGGER.debug("Vehicle moving again, clearing stop timestamp")
                    self._trip_stop_timestamp = None
        
        return result
    
    def _should_start_trip(self, snapshot: VehicleSnapshot) -> bool:
        """Determine if a trip should start.
        
        Args:
            snapshot: Current vehicle snapshot
            
        Returns:
            True if trip should start
        """
        # If we have a last snapshot, check if there's enough distance traveled
        if self._trip_last_snapshot and self._trip_last_snapshot.odometer_km is not None:
            distance = snapshot.odometer_km - self._trip_last_snapshot.odometer_km
            if distance >= self._min_trip_distance_km:
                return True
            return False
        
        # No previous data, assume trip can start
        return True
    
    def _should_end_trip(self, snapshot: VehicleSnapshot) -> bool:
        """Determine if a trip should end.
        
        Args:
            snapshot: Current vehicle snapshot
            
        Returns:
            True if trip should end
        """
        if not self._trip_last_snapshot or self._trip_last_snapshot.odometer_km is None:
            return False
        
        # Check if vehicle has stopped (no odometer change)
        distance_since_last = snapshot.odometer_km - self._trip_last_snapshot.odometer_km
        
        if distance_since_last < 0.01:  # Essentially no movement
            # Vehicle has stopped or is stationary
            if self._trip_stop_timestamp is None:
                # First time detecting stop
                self._trip_stop_timestamp = snapshot.timestamp
                _LOGGER.debug("Vehicle stopped, starting merge window")
                return False
            else:
                # Check if merge window has expired
                time_stopped = (snapshot.timestamp - self._trip_stop_timestamp).total_seconds()
                if time_stopped >= self._merge_time_window_seconds:
                    _LOGGER.debug(
                        "Merge window expired (%.1f seconds), ending trip",
                        time_stopped,
                    )
                    return True
                # Still within merge window
                return False
        else:
            # Vehicle is moving - don't end trip
            return False
    
    def _is_vehicle_moving(self, snapshot: VehicleSnapshot) -> bool:
        """Check if vehicle is moving based on odometer change.
        
        Args:
            snapshot: Current vehicle snapshot
            
        Returns:
            True if vehicle appears to be moving
        """
        if not self._trip_last_snapshot or self._trip_last_snapshot.odometer_km is None:
            return False
        
        if snapshot.odometer_km is None:
            return False
        
        distance = snapshot.odometer_km - self._trip_last_snapshot.odometer_km
        return distance >= 0.01  # At least 10 meters
    
    def _start_trip(self, snapshot: VehicleSnapshot) -> None:
        """Start a new trip.
        
        Args:
            snapshot: Snapshot at trip start
        """
        self._trip_in_progress = True
        self._trip_start_snapshot = snapshot
        self._trip_last_snapshot = snapshot
        self._trip_stop_timestamp = None
    
    def _end_trip(self, snapshot: VehicleSnapshot) -> dict[str, Any]:
        """End the current trip and return trip data.
        
        Args:
            snapshot: Snapshot at trip end
            
        Returns:
            Dictionary with trip data
        """
        if not self._trip_start_snapshot:
            _LOGGER.warning("Trip end called without trip start")
            self._trip_in_progress = False
            return {}
        
        # Calculate trip metrics
        distance_km = 0.0
        if (
            snapshot.odometer_km is not None
            and self._trip_start_snapshot.odometer_km is not None
        ):
            distance_km = snapshot.odometer_km - self._trip_start_snapshot.odometer_km
        
        fuel_consumed = None
        consumption_rate = None
        if (
            self._trip_start_snapshot.tank_level is not None
            and snapshot.tank_level is not None
        ):
            raw_consumed = self._trip_start_snapshot.tank_level - snapshot.tank_level
            # Only store positive values; negative means a refueling occurred during the trip
            if raw_consumed > 0:
                fuel_consumed = raw_consumed
                if distance_km > 0:
                    consumption_rate = (fuel_consumed / distance_km) * 100  # L/100km
        
        duration = snapshot.timestamp - self._trip_start_snapshot.timestamp
        
        trip_data = {
            "timestamp_start": self._trip_start_snapshot.timestamp.isoformat(),
            "timestamp_end": snapshot.timestamp.isoformat(),
            "distance_km": distance_km,
            "odometer_start": self._trip_start_snapshot.odometer_km,
            "odometer_end": snapshot.odometer_km,
            "fuel_level_start": self._trip_start_snapshot.tank_level,
            "fuel_level_end": snapshot.tank_level,
            "fuel_consumed": fuel_consumed,
            "consumption_rate": consumption_rate,
            "start_latitude": self._trip_start_snapshot.latitude,
            "start_longitude": self._trip_start_snapshot.longitude,
            "end_latitude": snapshot.latitude,
            "end_longitude": snapshot.longitude,
            "duration": str(duration),
            "duration_minutes": duration.total_seconds() / 60,
        }
        
        # Reset trip state
        self._trip_in_progress = False
        self._trip_start_snapshot = None
        self._trip_last_snapshot = snapshot
        self._trip_stop_timestamp = None
        
        return trip_data
    
    def is_on_trip(self) -> bool:
        """Check if currently on a trip.
        
        Returns:
            True if trip is in progress
        """
        return self._trip_in_progress
    
    def get_current_trip_data(self) -> dict[str, Any] | None:
        """Get data for the current trip in progress.
        
        Returns:
            Dictionary with current trip data or None if no trip in progress
        """
        if not self._trip_in_progress or not self._trip_start_snapshot:
            return None
        
        if not self._trip_last_snapshot:
            return None
        
        # Calculate current metrics
        distance_km = 0.0
        if (
            self._trip_last_snapshot.odometer_km is not None
            and self._trip_start_snapshot.odometer_km is not None
        ):
            distance_km = self._trip_last_snapshot.odometer_km - self._trip_start_snapshot.odometer_km
        
        duration = self._trip_last_snapshot.timestamp - self._trip_start_snapshot.timestamp
        
        return {
            "timestamp_start": self._trip_start_snapshot.timestamp.isoformat(),
            "distance_km": distance_km,
            "odometer_start": self._trip_start_snapshot.odometer_km,
            "start_latitude": self._trip_start_snapshot.latitude,
            "start_longitude": self._trip_start_snapshot.longitude,
            "duration": str(duration),
            "duration_minutes": duration.total_seconds() / 60,
        }


def detect_missed_trips_from_history(
    odometer_history: list[dict[str, Any]],
    existing_trip_timestamps: set[datetime],
    min_trip_distance_km: float = 0.5,
    min_duration_minutes: float = 1.0,
    max_speed_kmh: float = 300.0,
    lookback_hours: int = DEFAULT_MISSED_TRIP_LOOKBACK_HOURS,
) -> list[dict[str, Any]]:
    """Detect trips from recent odometer history that may have been missed.
    
    This function is used to detect trips that were missed due to HA restart,
    integration reload, or gaps in updates. It analyzes recent odometer history
    to find significant odometer changes that represent trips.
    
    Args:
        odometer_history: List of odometer history points with 'ts' and 'value' keys
        existing_trip_timestamps: Set of existing trip start timestamps to avoid duplicates
        min_trip_distance_km: Minimum distance to consider as a trip (default: 0.5 km)
        min_duration_minutes: Minimum duration to consider as a trip (default: 1 minute)
        max_speed_kmh: Maximum reasonable speed to filter outliers (default: 300 km/h)
        lookback_hours: How many hours back to look for missed trips (default: 24)
        
    Returns:
        List of detected trip dictionaries with trip data
    """
    detected_trips = []
    
    if not odometer_history or len(odometer_history) < 2:
        return detected_trips
    
    # Calculate cutoff time for lookback window
    now = dt_util.now()
    cutoff_time = now - timedelta(hours=lookback_hours)
    
    # Sort history by timestamp
    sorted_history = sorted(odometer_history, key=lambda x: x.get("ts", ""))
    
    # Analyze consecutive points for trips
    previous_point = None
    
    for current_point in sorted_history:
        if previous_point is None:
            previous_point = current_point
            continue
        
        try:
            # Parse values
            prev_odometer = previous_point.get("value")
            curr_odometer = current_point.get("value")
            
            if prev_odometer is None or curr_odometer is None:
                previous_point = current_point
                continue
            
            # Parse timestamps
            prev_time = dt_util.parse_datetime(previous_point.get("ts"))
            curr_time = dt_util.parse_datetime(current_point.get("ts"))
            
            if not prev_time or not curr_time:
                previous_point = current_point
                continue
            
            # Ensure timezone-aware
            if prev_time.tzinfo is None:
                prev_time = dt_util.as_local(prev_time)
            if curr_time.tzinfo is None:
                curr_time = dt_util.as_local(curr_time)
            
            # Skip if outside lookback window
            if prev_time < cutoff_time:
                previous_point = current_point
                continue
            
            # Calculate trip metrics
            distance_km = curr_odometer - prev_odometer
            duration_seconds = (curr_time - prev_time).total_seconds()
            duration_minutes = duration_seconds / 60
            
            # Check if this is a valid trip
            if distance_km >= min_trip_distance_km and duration_minutes >= min_duration_minutes:
                # Calculate average speed
                avg_speed = (distance_km / duration_seconds) * 3600 if duration_seconds > 0 else 0
                
                # Filter unrealistic speeds
                if avg_speed <= max_speed_kmh:
                    # Check for duplicates (within configured time window)
                    is_duplicate = False
                    for existing_ts in existing_trip_timestamps:
                        time_diff_minutes = abs((prev_time - existing_ts).total_seconds()) / 60
                        if time_diff_minutes < DUPLICATE_DETECTION_WINDOW_MINUTES:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        start_lat = previous_point.get("lat")
                        start_lon = previous_point.get("lon")
                        end_lat = current_point.get("lat")
                        end_lon = current_point.get("lon")
                        has_start = start_lat is not None and start_lon is not None
                        has_end = end_lat is not None and end_lon is not None
                        if has_start and has_end:
                            position_quality = "full"
                        elif has_start or has_end:
                            position_quality = "partial"
                        else:
                            position_quality = "none"
                        trip_data = {
                            "timestamp_start": prev_time.isoformat(),
                            "timestamp_end": curr_time.isoformat(),
                            "distance_km": round(distance_km, 2),
                            "odometer_start": round(prev_odometer, 1),
                            "odometer_end": round(curr_odometer, 1),
                            "duration_minutes": round(duration_minutes, 1),
                            "fuel_consumed": None,  # Not available from odometer history alone
                            "consumption_rate": None,
                            "start_latitude": start_lat,
                            "start_longitude": start_lon,
                            "end_latitude": end_lat,
                            "end_longitude": end_lon,
                            "position_quality": position_quality,
                            "category": "private",
                            "data_quality": "recovered_from_history",
                            "confidence": RECOVERED_TRIP_CONFIDENCE,
                        }
                        
                        detected_trips.append(trip_data)
                        existing_trip_timestamps.add(prev_time)
                        
                        _LOGGER.info(
                            "Recovered missed trip from history: %.1f km from %s to %s (%.1f min)",
                            distance_km,
                            prev_time.isoformat(),
                            curr_time.isoformat(),
                            duration_minutes,
                        )
        
        except Exception as err:
            _LOGGER.debug("Error analyzing odometer point for missed trips: %s", err)
        
        previous_point = current_point
    
    return detected_trips


def detect_missed_refuelings_from_history(
    tank_level_history: list[dict[str, Any]],
    existing_refuel_timestamps: set[datetime],
    tank_capacity: float = 50.0,
    min_refuel_threshold_percent: float = 3.5,
    lookback_hours: int = DEFAULT_MISSED_REFUELING_LOOKBACK_HOURS,
) -> list[dict[str, Any]]:
    """Detect refueling events from recent tank level history that may have been missed.
    
    This function is used to detect refuelings that were missed due to HA restart,
    integration reload, or gaps in updates. It analyzes recent tank level history
    to find significant tank level increases that represent refueling events.
    
    Args:
        tank_level_history: List of tank level history points with 'ts', 'value' (liters), and 'odometer_km' keys
        existing_refuel_timestamps: Set of existing refueling timestamps to avoid duplicates
        tank_capacity: Tank capacity in liters (default: 50.0)
        min_refuel_threshold_percent: Minimum threshold as percentage of tank capacity (default: 3.5%)
        lookback_hours: How many hours back to look for missed refuelings (default: 24)
        
    Returns:
        List of detected refueling event dictionaries
    """
    detected_refuelings = []
    
    if not tank_level_history or len(tank_level_history) < 2:
        return detected_refuelings
    
    # Calculate cutoff time for lookback window
    now = dt_util.now()
    cutoff_time = now - timedelta(hours=lookback_hours)
    
    # Calculate threshold in liters
    threshold_liters = (min_refuel_threshold_percent / 100.0) * tank_capacity
    
    # Sort history by timestamp
    sorted_history = sorted(tank_level_history, key=lambda x: x.get("ts", ""))
    
    # Analyze consecutive points for refuelings
    previous_point = None
    
    for current_point in sorted_history:
        if previous_point is None:
            previous_point = current_point
            continue
        
        try:
            # Parse values
            prev_tank_level = previous_point.get("value")
            curr_tank_level = current_point.get("value")
            
            if prev_tank_level is None or curr_tank_level is None:
                previous_point = current_point
                continue
            
            # Parse timestamps
            prev_time = dt_util.parse_datetime(previous_point.get("ts"))
            curr_time = dt_util.parse_datetime(current_point.get("ts"))
            
            if not prev_time or not curr_time:
                previous_point = current_point
                continue
            
            # Ensure timezone-aware
            if prev_time.tzinfo is None:
                prev_time = dt_util.as_local(prev_time)
            if curr_time.tzinfo is None:
                curr_time = dt_util.as_local(curr_time)
            
            # Skip if outside lookback window
            if prev_time < cutoff_time:
                previous_point = current_point
                continue
            
            # Calculate tank level change
            tank_diff = curr_tank_level - prev_tank_level
            
            # Check if this is a refueling event (significant increase in tank level)
            if tank_diff > threshold_liters:
                # Physical constraint: cannot refuel more than tank capacity
                if tank_diff > tank_capacity:
                    _LOGGER.debug(
                        "Skipping physically impossible refueling: +%.2fL > tank capacity %.1fL at %s",
                        tank_diff,
                        tank_capacity,
                        curr_time.isoformat(),
                    )
                    previous_point = current_point
                    continue
                
                # Check for duplicates (within configured time window)
                is_duplicate = False
                for existing_ts in existing_refuel_timestamps:
                    time_diff_minutes = abs((curr_time - existing_ts).total_seconds()) / 60
                    if time_diff_minutes < DUPLICATE_DETECTION_WINDOW_MINUTES:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    # Get odometer readings if available
                    odometer_km = current_point.get("odometer_km")
                    
                    refuel_event = {
                        "timestamp": curr_time.isoformat(),
                        "odometer_km": odometer_km,
                        "liters_refueled": round(tank_diff, 2),
                        "price_per_liter": None,  # Not available from history
                        "total_cost": None,  # Not available from history
                        "station_name": None,  # Not available from history
                        "latitude": None,  # Not available from tank level history
                        "longitude": None,  # Not available from tank level history
                        "fuel_type": None,  # Will use default from config
                        "data_quality": "recovered_from_tank_history",
                        # Medium confidence: based on tank level increase pattern without direct refueling event confirmation
                        # Lower than real-time detection due to missing context (location, station, exact time)
                        "confidence": RECOVERED_REFUELING_CONFIDENCE,
                        "excluded_from_calculation": False,
                    }
                    
                    detected_refuelings.append(refuel_event)
                    existing_refuel_timestamps.add(curr_time)
                    
                    _LOGGER.info(
                        "Recovered missed refueling from tank level history: %.1f L at %s (odometer: %s km)",
                        tank_diff,
                        curr_time.isoformat(),
                        f"{odometer_km:.1f}" if odometer_km else "unknown",
                    )
        
        except Exception as err:
            _LOGGER.debug("Error analyzing tank level point for missed refuelings: %s", err)
        
        previous_point = current_point
    
    return detected_refuelings


def compute_fuel_consumed_from_history(
    tank_level_history: list[dict[str, Any]],
    trip_start: datetime,
    trip_end: datetime,
) -> float | None:
    """Compute fuel consumed during a trip from tank level history.

    Finds the tank level reading closest to (and at or before) trip start and the
    reading closest to (and at or before) trip end, then returns the difference.

    Returns None if data is insufficient, timestamps cannot be parsed, or the
    level did not decrease (i.e. a refueling occurred during the trip).

    Args:
        tank_level_history: List of {ts: str, value: float, ...} observations.
        trip_start: Trip start datetime (timezone-aware).
        trip_end: Trip end datetime (timezone-aware).

    Returns:
        Fuel consumed in litres (positive float) or None.
    """
    if not tank_level_history:
        return None

    # Parse history entries into (datetime, float) pairs
    parsed: list[tuple[datetime, float]] = []
    for entry in tank_level_history:
        ts_str = entry.get("ts")
        val = entry.get("value")
        if not ts_str or val is None:
            continue
        try:
            ts = dt_util.parse_datetime(ts_str)
            if ts is None:
                continue
            if ts.tzinfo is None:
                ts = dt_util.as_local(ts)
            parsed.append((ts, float(val)))
        except (ValueError, TypeError):
            continue

    if not parsed:
        return None

    parsed.sort(key=lambda x: x[0])

    # Find last recorded level at or before trip_start
    level_at_start: float | None = None
    for ts, val in parsed:
        if ts <= trip_start:
            level_at_start = val

    # Find last recorded level at or before trip_end
    level_at_end: float | None = None
    for ts, val in parsed:
        if ts <= trip_end:
            level_at_end = val

    if level_at_start is None or level_at_end is None:
        return None

    consumed = level_at_start - level_at_end
    return consumed if consumed > 0 else None
