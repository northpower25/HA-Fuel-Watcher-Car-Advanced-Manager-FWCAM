"""Vehicle data tracking and analysis utilities."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


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
            fuel_consumed = self._trip_start_snapshot.tank_level - snapshot.tank_level
            if fuel_consumed > 0 and distance_km > 0:
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
