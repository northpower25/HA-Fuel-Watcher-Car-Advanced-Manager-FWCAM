"""
Historical Data Import for haFWCMA
-----------------------------------
Import historical data from Home Assistant's recorder to backfill
odometer history, detect past refueling events, and calculate
consumption statistics from existing vehicle entity data.

This allows the integration to use historical data from before
it was installed, providing immediate predictions and statistics.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util
from homeassistant.components.recorder import get_instance, history

from .storage import (
    add_odometer_observation,
    add_refuel_event,
    load_data,
    save_data,
)

_LOGGER = logging.getLogger(__name__)

# Constants for historical data import configuration
REFUEL_DETECTION_THRESHOLD_PERCENT = 4.0  # Minimum tank level increase (as percentage of tank capacity) to detect refueling
REFUEL_MERGE_TIME_WINDOW_MINUTES = 15  # Time window to merge multiple refueling events into one
REFUEL_DETECTION_MIN_TIME_GAP_MINUTES = 5  # Minimum time between separate refuelings (deprecated - use merge window)
ODOMETER_LOOKUP_MAX_TIME_DIFF_HOURS = 1  # Maximum time difference for odometer lookup
PRICE_LOOKUP_WINDOW_DAYS = 7  # Maximum age of price data to use for historical events
SECONDS_PER_HOUR = 3600  # Number of seconds in an hour
DUPLICATE_DETECTION_WINDOW_HOURS = 24  # Window for detecting duplicate refuelings
PERCENTAGE_MULTIPLIER = 100  # Multiplier for converting decimals to percentages
INVALID_SENSOR_STATES = ["unknown", "unavailable", "none", None, ""]  # States to ignore when processing sensor data


async def import_historical_vehicle_data(
    hass: HomeAssistant,
    entry: ConfigEntry,
    lookback_days: int = 90,
    force_reimport: bool = False,
    import_type: str = "automatic",
) -> dict[str, Any]:
    """Import historical vehicle data from Home Assistant's recorder.
    
    This function queries the recorder for historical states of the configured
    vehicle entities (odometer, tank level, range) and processes them to:
    1. Build odometer history
    2. Detect refueling events
    3. Calculate consumption between refuelings
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        lookback_days: Number of days to look back (default: 90)
        force_reimport: If True, reimport even if data already exists
        import_type: Type of import - "automatic" or "manual" (default: "automatic")
        
    Returns:
        Dictionary with import statistics:
        {
            "imported": bool,
            "reason": str,
            "odometer_points_imported": int,
            "refuel_events_detected": int,
            "date_range": str,
            "errors": list[str],
            "timestamp": str,
            "import_type": str,
        }
    """
    from ..const import (
        CONF_ODOMETER_ENTITY,
        CONF_TANK_LEVEL_ENTITY,
        CONF_RANGE_ENTITY,
        CONF_FUEL_TYPE,
        CONF_TANK_CAPACITY,
        DEFAULT_TANK_CAPACITY,
    )
    
    _LOGGER.info("Starting historical vehicle data import (lookback: %d days, type: %s)", lookback_days, import_type)
    
    timestamp = dt_util.now().isoformat()
    result = {
        "imported": False,
        "reason": "Not started",
        "odometer_points_imported": 0,
        "refuel_events_detected": 0,
        "date_range": "",
        "errors": [],
        "timestamp": timestamp,
        "import_type": import_type,
    }
    
    # Check if we should skip import (already imported and not forced)
    if not force_reimport:
        data = await load_data(hass, entry)
        if data.get("historical_import_completed"):
            result["reason"] = "Historical import already completed (use force_reimport to re-import)"
            _LOGGER.info("Skipping historical import - already completed")
            return result
    
    # Get entity IDs from config
    config = entry.data
    options = entry.options
    
    odometer_entity = options.get(CONF_ODOMETER_ENTITY) or config.get(CONF_ODOMETER_ENTITY)
    tank_level_entity = options.get(CONF_TANK_LEVEL_ENTITY) or config.get(CONF_TANK_LEVEL_ENTITY)
    range_entity = options.get(CONF_RANGE_ENTITY) or config.get(CONF_RANGE_ENTITY)
    fuel_type = options.get(CONF_FUEL_TYPE) or config.get(CONF_FUEL_TYPE, "e5")
    tank_capacity = options.get(CONF_TANK_CAPACITY) or config.get(CONF_TANK_CAPACITY, DEFAULT_TANK_CAPACITY)
    
    # Validate that at least odometer and tank level are configured
    if not odometer_entity:
        result["reason"] = "Odometer entity not configured"
        result["errors"].append("Cannot import without odometer entity")
        _LOGGER.warning("Cannot import historical data: odometer entity not configured")
        return result
    
    if not tank_level_entity:
        result["reason"] = "Tank level entity not configured"
        result["errors"].append("Cannot import without tank level entity")
        _LOGGER.warning("Cannot import historical data: tank level entity not configured")
        return result
    
    # Check if recorder is available
    try:
        recorder_instance = get_instance(hass)
        if not recorder_instance:
            result["reason"] = "Recorder not available"
            result["errors"].append("Home Assistant recorder is not enabled")
            _LOGGER.warning("Cannot import historical data: recorder not available")
            return result
    except Exception as err:
        result["reason"] = f"Error checking recorder: {err}"
        result["errors"].append(str(err))
        _LOGGER.error("Error checking recorder availability: %s", err)
        return result
    
    # Calculate time range
    end_time = dt_util.now()
    start_time = end_time - timedelta(days=lookback_days)
    result["date_range"] = f"{start_time.isoformat()} to {end_time.isoformat()}"
    
    _LOGGER.info(
        "Importing historical data from %s to %s",
        start_time.isoformat(),
        end_time.isoformat(),
    )
    
    try:
        # Import odometer history
        odometer_points = await _import_odometer_history(
            hass, entry, odometer_entity, start_time, end_time
        )
        result["odometer_points_imported"] = odometer_points
        _LOGGER.info("Imported %d odometer data points", odometer_points)
        
        # Import tank level history and detect refueling events
        refuel_events = await _import_tank_history_and_detect_refueling(
            hass, entry, tank_level_entity, odometer_entity, start_time, end_time, tank_capacity, fuel_type
        )
        result["refuel_events_detected"] = refuel_events
        _LOGGER.info("Detected %d refueling events", refuel_events)
        
        # Mark import as completed and store metadata
        data = await load_data(hass, entry)
        data["historical_import_completed"] = True
        data["historical_import_timestamp"] = timestamp
        data["historical_import_lookback_days"] = lookback_days
        data["last_historical_import"] = {
            "timestamp": timestamp,
            "type": import_type,
        }
        await save_data(hass, entry, data)
        
        result["imported"] = True
        result["reason"] = "Historical import completed successfully"
        
        _LOGGER.info(
            "Historical import completed: %d odometer points, %d refuel events (type: %s)",
            odometer_points,
            refuel_events,
            import_type,
        )
        
    except Exception as err:
        result["reason"] = f"Error during import: {err}"
        result["errors"].append(str(err))
        _LOGGER.error("Error importing historical data: %s", err, exc_info=True)
    
    return result


async def _import_odometer_history(
    hass: HomeAssistant,
    entry: ConfigEntry,
    odometer_entity: str,
    start_time: datetime,
    end_time: datetime,
) -> int:
    """Import odometer history from recorder.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        odometer_entity: Entity ID of odometer sensor
        start_time: Start of time range
        end_time: End of time range
        
    Returns:
        Number of data points imported
    """
    count = 0
    
    try:
        # Get historical states from recorder
        # Use history.state_changes_during_period to get state changes
        states = await hass.async_add_executor_job(
            history.state_changes_during_period,
            hass,
            start_time,
            end_time,
            odometer_entity,
        )
        
        if not states or odometer_entity not in states:
            _LOGGER.warning("No historical states found for odometer entity: %s", odometer_entity)
            return 0
        
        # Process states in chronological order, but sample to avoid overwhelming storage
        # Keep one reading per day max to reduce data volume
        states_by_day = {}
        for state in states[odometer_entity]:
            try:
                # Skip if state is unknown or unavailable
                if state.state in INVALID_SENSOR_STATES:
                    continue
                
                # Parse odometer value
                odometer_value = float(state.state)
                timestamp = state.last_changed
                
                # Group by day to avoid too many data points
                day_key = timestamp.date().isoformat()
                
                # Keep the first reading of each day
                if day_key not in states_by_day:
                    states_by_day[day_key] = {
                        "value": odometer_value,
                        "timestamp": timestamp.isoformat(),
                    }
                
            except (ValueError, TypeError) as err:
                _LOGGER.debug("Skipping invalid odometer state: %s (%s)", state.state, err)
                continue
        
        # Add sampled data to history
        for day_data in states_by_day.values():
            await add_odometer_observation(
                hass, 
                entry, 
                day_data["value"], 
                day_data["timestamp"]
            )
            count += 1
        
        _LOGGER.info(
            "Imported %d odometer readings (sampled from %d total states)",
            count,
            len(states[odometer_entity]),
        )
        
    except Exception as err:
        _LOGGER.error("Error importing odometer history: %s", err, exc_info=True)
        raise
    
    return count


async def _import_tank_history_and_detect_refueling(
    hass: HomeAssistant,
    entry: ConfigEntry,
    tank_level_entity: str,
    odometer_entity: str,
    start_time: datetime,
    end_time: datetime,
    tank_capacity: float,
    fuel_type: str,
) -> int:
    """Import tank level history and detect refueling events.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        tank_level_entity: Entity ID of tank level sensor
        odometer_entity: Entity ID of odometer sensor
        start_time: Start of time range
        end_time: End of time range
        tank_capacity: Tank capacity in liters
        fuel_type: Fuel type (e5, e10, diesel)
        
    Returns:
        Number of refueling events detected
    """
    refuel_count = 0
    
    try:
        # Load existing refueling log to check for duplicates
        from .storage import get_refueling_log
        from homeassistant.util import dt as dt_util
        
        existing_log = await get_refueling_log(hass, entry)
        existing_timestamps = set()
        for event in existing_log:
            if event.get("timestamp"):
                # Parse timestamp and store as datetime for comparison
                try:
                    ts = dt_util.parse_datetime(event["timestamp"])
                    if ts:
                        existing_timestamps.add(ts)
                except (ValueError, TypeError):
                    pass
        
        # Get historical states from recorder
        tank_states = await hass.async_add_executor_job(
            history.state_changes_during_period,
            hass,
            start_time,
            end_time,
            tank_level_entity,
        )
        
        if not tank_states or tank_level_entity not in tank_states:
            _LOGGER.warning("No historical states found for tank level entity: %s", tank_level_entity)
            return 0
        
        # Get odometer states for same period
        odometer_states_dict = await hass.async_add_executor_job(
            history.state_changes_during_period,
            hass,
            start_time,
            end_time,
            odometer_entity,
        )
        
        # Create a lookup for odometer values by timestamp
        odometer_lookup = {}
        if odometer_states_dict and odometer_entity in odometer_states_dict:
            for state in odometer_states_dict[odometer_entity]:
                try:
                    if state.state not in INVALID_SENSOR_STATES:
                        odometer_lookup[state.last_changed] = float(state.state)
                except (ValueError, TypeError):
                    continue
        
        # Process tank level states and detect refueling
        previous_level = None
        previous_time = None
        
        # Track potential refueling events to merge close ones
        pending_refuel_events = []
        
        # Determine if tank level is in percentage or liters from first valid state
        tank_level_in_percentage = False
        for state in tank_states[tank_level_entity]:
            if state.state not in INVALID_SENSOR_STATES:
                unit = state.attributes.get("unit_of_measurement", "").lower()
                if unit in ["%", "percent", "percentage"]:
                    tank_level_in_percentage = True
                    _LOGGER.debug("Tank level entity uses percentage unit: %s", unit)
                break
        
        # Calculate threshold in liters based on percentage
        threshold_liters = (REFUEL_DETECTION_THRESHOLD_PERCENT / 100.0) * tank_capacity
        _LOGGER.info(
            "Refueling detection configuration: threshold=%.1f%% (%.2fL), tank_capacity=%.1fL, merge_window=%d min",
            REFUEL_DETECTION_THRESHOLD_PERCENT,
            threshold_liters,
            tank_capacity,
            REFUEL_MERGE_TIME_WINDOW_MINUTES,
        )
        _LOGGER.info(
            "Existing refueling events in log: %d (will check for duplicates within %d hours)",
            len(existing_timestamps),
            DUPLICATE_DETECTION_WINDOW_HOURS,
        )
        
        for state in tank_states[tank_level_entity]:
            try:
                # Skip if state is unknown or unavailable
                if state.state in INVALID_SENSOR_STATES:
                    continue
                
                current_level = float(state.state)
                
                # Convert percentage to liters if needed
                if tank_level_in_percentage:
                    current_level = (current_level / 100.0) * tank_capacity
                
                current_time = state.last_changed
                
                # Detect refueling: significant increase in tank level
                if previous_level is not None:
                    level_increase = current_level - previous_level
                    
                    # Log all tank level increases (positive changes only) for debugging
                    if level_increase > 0:
                        _LOGGER.info(
                            "Tank level increase detected: +%.2fL at %s (%.1f%% raw, previous=%.2fL, current=%.2fL, threshold=%.2fL)",
                            level_increase,
                            current_time.isoformat(),
                            float(state.state) if tank_level_in_percentage else (level_increase / tank_capacity * 100),
                            previous_level,
                            current_level,
                            threshold_liters,
                        )
                    
                    # Refueling detected if increase exceeds threshold
                    if level_increase > threshold_liters:
                        # Check if this refueling is a duplicate
                        is_duplicate = False
                        for existing_ts in existing_timestamps:
                            time_diff_hours = abs((current_time - existing_ts).total_seconds()) / SECONDS_PER_HOUR
                            if time_diff_hours < DUPLICATE_DETECTION_WINDOW_HOURS:
                                is_duplicate = True
                                _LOGGER.warning(
                                    "Skipping duplicate refueling at %s (within %.1fh of existing event at %s)",
                                    current_time.isoformat(),
                                    time_diff_hours,
                                    existing_ts.isoformat(),
                                )
                                break
                        
                        if not is_duplicate:
                            # Add to pending events for potential merging
                            pending_refuel_events.append({
                                "timestamp": current_time,
                                "liters": level_increase,
                            })
                            _LOGGER.info(
                                "✓ Refueling event detected: +%.2fL at %s (exceeds threshold of %.2fL)",
                                level_increase,
                                current_time.isoformat(),
                                threshold_liters,
                            )
                        else:
                            _LOGGER.info(
                                "✗ Refueling event rejected as duplicate: +%.2fL at %s",
                                level_increase,
                                current_time.isoformat(),
                            )
                
                previous_level = current_level
                previous_time = current_time
                
            except (ValueError, TypeError) as err:
                _LOGGER.debug("Skipping invalid tank level state: %s (%s)", state.state, err)
                continue
        
        # Merge refueling events that occur within the merge time window
        _LOGGER.info(
            "Processing %d detected refueling event(s) for merging (merge window: %d minutes)",
            len(pending_refuel_events),
            REFUEL_MERGE_TIME_WINDOW_MINUTES,
        )
        merged_events = _merge_refueling_events(pending_refuel_events, REFUEL_MERGE_TIME_WINDOW_MINUTES)
        _LOGGER.info(
            "After merging: %d refueling event(s) to be added to storage",
            len(merged_events),
        )
        
        # Create refueling log entries for merged events
        for merged_event in merged_events:
            current_time = merged_event["timestamp"]
            level_increase = merged_event["liters"]
            merged_count = merged_event.get("merged_count", 1)
            
            # Find closest odometer reading
            odometer_km = _find_closest_odometer(odometer_lookup, current_time)
            
            # Get current price from integration data (if available)
            price_per_liter = await _get_current_price(hass, entry, current_time)
            
            # Calculate confidence based on data availability
            confidence = _calculate_confidence(
                odometer_km=odometer_km,
                price_per_liter=price_per_liter,
                level_increase=level_increase,
                tank_capacity=tank_capacity,
            )
            
            # Create refueling event with quality indicators
            event_data = {
                "timestamp": current_time.isoformat(),
                "odometer_km": odometer_km,
                "station_name": "Historical Import",
                "liters_refueled": level_increase,
                "price_per_liter": price_per_liter,
                "total_cost": level_increase * price_per_liter if price_per_liter else None,
                "latitude": None,
                "longitude": None,
                "fuel_type": fuel_type,
                "data_quality": "historical_import",
                "confidence": confidence,
            }
            
            await add_refuel_event(hass, entry, event_data)
            existing_timestamps.add(current_time)  # Add to prevent duplicates in same import
            refuel_count += 1
            
            if merged_count > 1:
                _LOGGER.info(
                    "Adding merged refueling event: +%.1fL at %s (merged %d events, odometer: %.1f km, confidence: %.2f)",
                    level_increase,
                    current_time.isoformat(),
                    merged_count,
                    odometer_km or 0,
                    confidence,
                )
            else:
                _LOGGER.info(
                    "Adding refueling event: +%.1fL at %s (odometer: %.1f km, confidence: %.2f)",
                    level_increase,
                    current_time.isoformat(),
                    odometer_km or 0,
                    confidence,
                )
        
        # Log summary if any refuelings were detected
        if refuel_count > 0:
            _LOGGER.info(
                "Historical import completed: detected %d refueling event(s) from tank level changes",
                refuel_count,
            )
        
    except Exception as err:
        _LOGGER.error("Error importing tank history: %s", err, exc_info=True)
        raise
    
    return refuel_count


def _merge_refueling_events(
    events: list[dict[str, Any]],
    merge_window_minutes: float,
) -> list[dict[str, Any]]:
    """Merge refueling events that occur within a time window.
    
    When multiple tank level increases occur close together (e.g., sensor updates
    during a single refueling session), merge them into a single event.
    
    Args:
        events: List of refueling events with 'timestamp' and 'liters' keys
        merge_window_minutes: Time window in minutes to consider events as part of same refueling
        
    Returns:
        List of merged refueling events
    """
    if not events:
        return []
    
    # Sort events by timestamp
    sorted_events = sorted(events, key=lambda x: x["timestamp"])
    
    merged = []
    current_group = None
    
    for event in sorted_events:
        if current_group is None:
            # Start a new group
            current_group = {
                "timestamp": event["timestamp"],
                "liters": event["liters"],
                "merged_count": 1,
            }
        else:
            # Check if this event should be merged with current group
            time_diff_minutes = (event["timestamp"] - current_group["timestamp"]).total_seconds() / 60
            
            if time_diff_minutes <= merge_window_minutes:
                # Merge into current group
                current_group["liters"] += event["liters"]
                current_group["merged_count"] += 1
                _LOGGER.info(
                    "Merging refueling events: %s (+%.2fL) merged with %s (+%.2fL), time diff: %.1f min",
                    event["timestamp"].isoformat(),
                    event["liters"],
                    current_group["timestamp"].isoformat(),
                    current_group["liters"] - event["liters"],  # Previous total before adding current
                    time_diff_minutes,
                )
            else:
                # Time gap too large, save current group and start new one
                merged.append(current_group)
                current_group = {
                    "timestamp": event["timestamp"],
                    "liters": event["liters"],
                    "merged_count": 1,
                }
    
    # Don't forget the last group
    if current_group is not None:
        merged.append(current_group)
    
    return merged


def _find_closest_odometer(
    odometer_lookup: dict[datetime, float],
    target_time: datetime,
) -> float | None:
    """Find the closest odometer reading to a given time.
    
    Args:
        odometer_lookup: Dictionary mapping timestamps to odometer values
        target_time: Target timestamp
        
    Returns:
        Closest odometer value or None if not found
    """
    if not odometer_lookup:
        return None
    
    # Find the closest timestamp
    closest_time = min(
        odometer_lookup.keys(),
        key=lambda t: abs((t - target_time).total_seconds()),
    )
    
    # Return value if within configured time window
    max_time_diff_seconds = ODOMETER_LOOKUP_MAX_TIME_DIFF_HOURS * SECONDS_PER_HOUR
    if abs((closest_time - target_time).total_seconds()) < max_time_diff_seconds:
        return odometer_lookup[closest_time]
    
    return None


async def _get_current_price(
    hass: HomeAssistant,
    entry: ConfigEntry,
    timestamp: datetime,
) -> float | None:
    """Get fuel price closest to a given timestamp from price history.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        timestamp: Target timestamp
        
    Returns:
        Price per liter or None if not found
    """
    try:
        from .storage import get_price_history
        from homeassistant.util import dt as dt_util
        
        price_history = await get_price_history(hass, entry)
        
        if not price_history:
            return None
        
        # Find closest price by timestamp
        closest_price = None
        min_time_diff = float('inf')
        
        max_price_age_seconds = PRICE_LOOKUP_WINDOW_DAYS * 24 * SECONDS_PER_HOUR
        
        for price_entry in price_history:
            try:
                price_time = dt_util.parse_datetime(price_entry.get("ts", ""))
                if not price_time:
                    continue
                
                time_diff = abs((price_time - timestamp).total_seconds())
                
                # Use price if within configured time window
                if time_diff < min_time_diff and time_diff < max_price_age_seconds:
                    min_time_diff = time_diff
                    closest_price = price_entry.get("price")
            except Exception:
                continue
        
        return closest_price
        
    except Exception as err:
        _LOGGER.debug("Error getting historical price: %s", err)
        return None


def _calculate_confidence(
    odometer_km: float | None,
    price_per_liter: float | None,
    level_increase: float,
    tank_capacity: float,
) -> float:
    """Calculate confidence score for a detected refueling event.
    
    Confidence is based on:
    - Availability of odometer data (0.4 weight)
    - Availability of price data (0.3 weight)
    - Reasonableness of refueling amount (0.3 weight)
    
    Args:
        odometer_km: Odometer reading at refueling (None if not available)
        price_per_liter: Price per liter (None if not available)
        level_increase: Amount of fuel added in liters
        tank_capacity: Tank capacity in liters
        
    Returns:
        Confidence score from 0.0 to 1.0 (higher is better)
    """
    confidence = 0.0
    
    # Odometer data available (40% weight)
    if odometer_km is not None and odometer_km > 0:
        confidence += 0.4
    
    # Price data available (30% weight)
    if price_per_liter is not None and price_per_liter > 0:
        confidence += 0.3
    
    # Refueling amount is reasonable (30% weight)
    # Consider it reasonable if between 10% and 100% of tank capacity
    if tank_capacity > 0:
        refuel_percentage = (level_increase / tank_capacity) * PERCENTAGE_MULTIPLIER
        if 10 <= refuel_percentage <= 100:
            confidence += 0.3
        elif refuel_percentage > 100:
            # Over 100% suggests measurement error or wrong tank capacity
            # Still give partial credit as refueling was detected
            confidence += 0.15
    else:
        # No tank capacity data, give partial credit
        confidence += 0.15
    
    return round(confidence, 2)
