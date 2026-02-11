"""Vehicle data tracking and analysis utilities."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
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
    REFUEL_DETECTION_THRESHOLD_PERCENT = 4.0
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
                    if self._pending_refuel_liters > 0:
                        result["refueling_detected"] = True
                        result["fuel_added"] = self._pending_refuel_liters
                        result["refuel_timestamp"] = self._last_refuel_timestamp.isoformat() if self._last_refuel_timestamp else None
                        result["refuel_odometer_km"] = self._previous_snapshot.odometer_km
                        result["refuel_latitude"] = self._previous_snapshot.latitude
                        result["refuel_longitude"] = self._previous_snapshot.longitude
                        
                        _LOGGER.info(
                            "Refueling session complete: %.2f liters added at odometer %.1f km",
                            self._pending_refuel_liters,
                            self._previous_snapshot.odometer_km or 0,
                        )
                    
                    # Start new refueling session
                    self._pending_refuel_liters = tank_diff
                    self._pending_refuel_start = self._current_snapshot.timestamp
                    self._last_refuel_timestamp = self._current_snapshot.timestamp
                    
                    _LOGGER.debug(
                        "New refueling session started: +%.2f liters",
                        tank_diff,
                    )
            elif self._pending_refuel_liters > 0:
                # No more increases detected, finalize pending refuel if merge window expired
                if (
                    self._pending_refuel_start is not None
                    and (self._current_snapshot.timestamp - self._pending_refuel_start).total_seconds()
                    > self.REFUEL_MERGE_TIME_WINDOW_SECONDS
                ):
                    result["refueling_detected"] = True
                    result["fuel_added"] = self._pending_refuel_liters
                    result["refuel_timestamp"] = self._last_refuel_timestamp.isoformat() if self._last_refuel_timestamp else None
                    result["refuel_odometer_km"] = self._current_snapshot.odometer_km
                    result["refuel_latitude"] = self._current_snapshot.latitude
                    result["refuel_longitude"] = self._current_snapshot.longitude
                    
                    _LOGGER.info(
                        "Refueling session complete: %.2f liters added at odometer %.1f km",
                        self._pending_refuel_liters,
                        self._current_snapshot.odometer_km or 0,
                    )
                    
                    # Reset pending refuel
                    self._pending_refuel_liters = 0.0
                    self._pending_refuel_start = None
        
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
