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
    
    def __init__(self) -> None:
        """Initialize the tracker."""
        self._previous_snapshot: VehicleSnapshot | None = None
        self._current_snapshot: VehicleSnapshot | None = None
        
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
            
            # Refueling detected if tank increased by more than 5 liters
            # (could be percentage or liters depending on entity)
            if tank_diff > 5:
                result["refueling_detected"] = True
                result["fuel_added"] = tank_diff
                _LOGGER.info(
                    "Refueling detected: tank level increased by %.2f units",
                    tank_diff,
                )
        
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
