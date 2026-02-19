"""
Consumption Prediction Engine for haFWCMA
------------------------------------------
Advanced consumption forecasting based on historical vehicle data.

Functions:
- Check data sufficiency for predictions
- Calculate consumption trends from mileage and tank level changes
- Predict days until refueling needed
- Provide confidence scoring for predictions
- Fallback to configuration values when insufficient data
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util

from .storage import (
    get_odometer_history,
    get_tank_history,
    load_data,
    save_data,
)

_LOGGER = logging.getLogger(__name__)

# Maximum days to simulate for weekday pattern calculation
# Prevents infinite loops in edge cases (e.g., extremely low daily km values)
MAX_PREDICTION_DAYS = 365

# Startup fallback tank level assumption
# When no vehicle data is available (e.g., after HA restart), we assume 50% tank level
# This is a conservative estimate that provides a reasonable initial prediction
# The value will be replaced with actual data as soon as vehicle sensors restore state
STARTUP_ASSUMED_TANK_LEVEL = 0.5  # 50% of tank capacity


def _parse_timestamp(ts: str) -> Optional[datetime]:
    """Parse ISO format timestamp.
    
    Args:
        ts: Timestamp string
        
    Returns:
        Timezone-aware datetime object or None if parse fails
    """
    try:
        # Use dt_util.parse_datetime to ensure timezone-aware datetime
        parsed = dt_util.parse_datetime(ts)
        if parsed:
            return parsed
        # Fallback to fromisoformat
        dt = datetime.fromisoformat(ts)
        # Make timezone-aware if it's naive
        if dt.tzinfo is None:
            return dt_util.as_local(dt)
        return dt
    except Exception:
        return None


async def check_data_sufficiency(
    hass: HomeAssistant,
    entry: ConfigEntry,
    min_data_points: int = 5,
) -> Dict[str, Any]:
    """Check if sufficient historical data is available for reliable predictions.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        min_data_points: Minimum number of data points required
        
    Returns:
        Dictionary with sufficiency info:
        {
            "sufficient": bool,
            "odometer_points": int,
            "tank_points": int,
            "consumption_events": int,
            "reason": str,
        }
    """
    from .storage import get_refueling_log
    
    odometer_history = await get_odometer_history(hass, entry)
    refueling_log = await get_refueling_log(hass, entry)
    
    odometer_points = len(odometer_history)
    refuel_count = len(refueling_log)
    
    # Count refueling events with valid data (odometer and fuel amount)
    # We need at least 2 refueling events to calculate consumption
    consumption_events = sum(
        1 for event in refueling_log 
        if (event.get("odometer_km") is not None and 
            event.get("liters_refueled") is not None and
            event.get("liters_refueled", 0) > 0)
    )
    
    # We need sufficient odometer history AND at least 2 refueling events to calculate consumption
    sufficient = (
        odometer_points >= min_data_points 
        and consumption_events >= 2  # Need at least 2 refueling events
    )
    
    if sufficient:
        reason = f"Sufficient data available ({odometer_points} odometer points, {consumption_events} refueling events)"
    else:
        reason = f"Insufficient data ({odometer_points}/{min_data_points} odometer points, {consumption_events} refueling events, need at least 2)"
    
    _LOGGER.debug(
        "Data sufficiency check: sufficient=%s, odometer=%d, refuelings=%d, consumption_events=%d",
        sufficient, odometer_points, refuel_count, consumption_events
    )
    
    return {
        "sufficient": sufficient,
        "odometer_points": odometer_points,
        "tank_points": refuel_count,  # Kept for backward compatibility - actually contains refuel count, not tank history points
        "consumption_events": consumption_events,
        "reason": reason,
    }


async def calculate_historical_consumption(
    hass: HomeAssistant,
    entry: ConfigEntry,
    lookback_days: int = 30,
) -> Dict[str, Any]:
    """Calculate consumption statistics from historical data.
    
    Analyzes odometer and refueling events to determine:
    - Average daily kilometers
    - Average fuel consumption rate (L/100km)
    - Consumption trend (increasing/decreasing/stable)
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        lookback_days: Number of days to look back
        
    Returns:
        Dictionary with consumption statistics:
        {
            "avg_daily_km": float,
            "avg_consumption_rate": float,  # L/100km
            "trend": str,  # "increasing", "decreasing", "stable"
            "confidence": float,  # 0-1
            "data_points": int,
        }
    """
    from .storage import calculate_consumption_history
    
    odometer_history = await get_odometer_history(hass, entry)
    
    # Use the storage.calculate_consumption_history function which properly calculates
    # consumption from refueling_log data
    consumption_data = await calculate_consumption_history(hass, entry, days=lookback_days)
    
    if not odometer_history or len(odometer_history) < 2:
        return {
            "avg_daily_km": 0.0,
            "avg_consumption_rate": consumption_data.get("avg_consumption_l_per_100km") or 0.0,
            "trend": "unknown",
            "confidence": 0.0,
            "data_points": 0,
        }
    
    # Filter by lookback period
    cutoff_time = dt_util.now() - timedelta(days=lookback_days)
    
    recent_odometer = [
        entry for entry in odometer_history
        if _parse_timestamp(entry.get("ts", "")) and 
           _parse_timestamp(entry.get("ts", "")) >= cutoff_time
    ]
    
    # Calculate average daily kilometers
    avg_daily_km = 0.0
    if len(recent_odometer) >= 2:
        sorted_odo = sorted(recent_odometer, key=lambda x: _parse_timestamp(x.get("ts", "")))
        first_entry = sorted_odo[0]
        last_entry = sorted_odo[-1]
        
        first_ts = _parse_timestamp(first_entry.get("ts", ""))
        last_ts = _parse_timestamp(last_entry.get("ts", ""))
        first_km = float(first_entry.get("value", 0))
        last_km = float(last_entry.get("value", 0))
        
        if first_ts and last_ts and last_km > first_km:
            days_elapsed = (last_ts - first_ts).total_seconds() / 86400
            if days_elapsed > 0:
                km_driven = last_km - first_km
                avg_daily_km = km_driven / days_elapsed
    
    # Get average consumption rate from refueling data
    avg_consumption_rate = consumption_data.get("avg_consumption_l_per_100km") or 0.0
    refuel_count = consumption_data.get("refuel_count", 0)
    
    # Calculate trend by comparing shorter vs longer periods
    trend = "stable"
    if refuel_count >= 4:
        # Compare last 7 days vs full period
        short_period = await calculate_consumption_history(hass, entry, days=min(7, lookback_days // 2))
        short_consumption = short_period.get("avg_consumption_l_per_100km")
        
        if short_consumption and avg_consumption_rate > 0:
            diff_percent = ((short_consumption - avg_consumption_rate) / avg_consumption_rate) * 100
            
            if diff_percent > 5:
                trend = "increasing"
            elif diff_percent < -5:
                trend = "decreasing"
    
    # Calculate confidence based on data points
    data_points = len(recent_odometer) + refuel_count
    if data_points >= 10:
        confidence = 1.0
    elif data_points >= 5:
        confidence = 0.7
    elif data_points >= 2:
        confidence = 0.4
    else:
        confidence = 0.1
    
    _LOGGER.debug(
        "Historical consumption: avg_daily_km=%.1f, avg_consumption=%.2f L/100km, "
        "trend=%s, confidence=%.2f, data_points=%d",
        avg_daily_km, avg_consumption_rate, trend, confidence, data_points
    )
    
    return {
        "avg_daily_km": round(avg_daily_km, 1),
        "avg_consumption_rate": round(avg_consumption_rate, 2),
        "trend": trend,
        "confidence": round(confidence, 2),
        "data_points": data_points,
    }


def _calculate_days_until_refuel_with_weekday_pattern(
    current_range_km: float,
    weekday_pattern: Dict[int, float],
    start_date: Optional[datetime] = None,
) -> Optional[float]:
    """Calculate days until refuel using weekday-specific driving patterns.
    
    This provides more accurate predictions by accounting for different
    driving distances on different days of the week.
    
    Edge cases handled:
    - If weekday_pattern is missing entries for some weekdays, falls back to
      averaging all available weekday values for missing days
    - If all pattern values are zero or negative, returns None immediately
    - If individual weekday has zero km, uses average of other weekdays
    
    Args:
        current_range_km: Current remaining range in km
        weekday_pattern: Dictionary mapping weekday (0=Mon, 6=Sun) to avg km driven
        start_date: Starting date for calculation (defaults to now)
        
    Returns:
        Days until refuel (may include fractional days) or None if calculation fails
    """
    # Validate inputs
    if not weekday_pattern or len(weekday_pattern) == 0 or current_range_km <= 0:
        return None
    
    # Check if all pattern values are non-positive (fail fast)
    if all(km <= 0 for km in weekday_pattern.values()):
        return None
    
    if start_date is None:
        start_date = dt_util.now()
    
    remaining_km = current_range_km
    days_elapsed = 0.0
    current_day = start_date
    
    # Simulate day-by-day consumption until range is depleted
    while remaining_km > 0 and days_elapsed < MAX_PREDICTION_DAYS:
        weekday = current_day.weekday()
        daily_km = weekday_pattern.get(weekday, 0)
        
        if daily_km <= 0:
            # If no pattern for this weekday, use average of all weekdays
            # len(weekday_pattern) > 0 is guaranteed by checks above
            daily_km = sum(weekday_pattern.values()) / len(weekday_pattern)
            
            # Safety check: if average is still zero or negative, fail
            if daily_km <= 0:
                return None
        
        # Check if this is the last partial day
        if remaining_km <= daily_km:
            # Calculate fractional day
            days_elapsed += remaining_km / daily_km
            break
        
        remaining_km -= daily_km
        days_elapsed += 1
        current_day += timedelta(days=1)
    
    return days_elapsed if days_elapsed < MAX_PREDICTION_DAYS else None


async def _calculate_avg_days_between_refuelings(
    hass: HomeAssistant,
    entry: ConfigEntry,
    lookback_days: int = 90,
) -> Optional[float]:
    """Calculate average days between refuelings from historical data.
    
    DEPRECATED: This function is no longer used in predict_days_until_refuel.
    It has been replaced with a smarter method that uses consumption forecasts
    and weekday patterns instead of just averaging time intervals between refuelings.
    Kept for backwards compatibility but may be removed in future versions.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        lookback_days: Number of days to look back
        
    Returns:
        Average days between refuelings or None if insufficient data
    """
    from .storage import get_refueling_log
    
    refueling_log = await get_refueling_log(hass, entry)
    
    if len(refueling_log) < 2:
        return None
    
    # Filter by lookback period
    cutoff_time = dt_util.now() - timedelta(days=lookback_days)
    
    recent_refuelings = []
    for event in refueling_log:
        try:
            event_time = dt_util.parse_datetime(event.get("timestamp", ""))
            if event_time and event_time >= cutoff_time:
                recent_refuelings.append(event_time)
        except (ValueError, TypeError):
            continue
    
    if len(recent_refuelings) < 2:
        return None
    
    # Sort by time
    recent_refuelings.sort()
    
    # Calculate intervals between consecutive refuelings
    intervals = []
    for i in range(len(recent_refuelings) - 1):
        interval_days = (recent_refuelings[i + 1] - recent_refuelings[i]).total_seconds() / 86400
        if interval_days > 0:
            intervals.append(interval_days)
    
    if not intervals:
        return None
    
    # Return average interval
    return sum(intervals) / len(intervals)


async def predict_days_until_refuel(
    hass: HomeAssistant,
    entry: ConfigEntry,
    current_range_km: Optional[float] = None,
    current_tank_level: Optional[float] = None,
    tank_capacity: Optional[float] = None,
    fallback_daily_km: float = 40.0,
    fallback_consumption_rate: float = 7.0,
    min_data_points: int = 5,
) -> Dict[str, Any]:
    """Predict days until refueling is needed.
    
    Uses historical data and ML patterns if available, otherwise falls back to configuration values.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        current_range_km: Current remaining range in km
        current_tank_level: Current tank level in liters
        tank_capacity: Tank capacity in liters
        fallback_daily_km: Fallback daily km if insufficient data
        fallback_consumption_rate: Fallback consumption rate (L/100km)
        min_data_points: Minimum data points for historical prediction
        
    Returns:
        Dictionary with prediction:
        {
            "days_until_refuel": float,
            "predicted_refuel_date": datetime,
            "data_source": str,  # "ml_enhanced", "historical_data" or "fallback_values"
            "confidence": float,
            "avg_daily_km": float,
            "avg_consumption_rate": float,
            "last_prediction_time": datetime,
            "data_points_used": int,
            "ml_prediction": dict,  # ML-specific predictions if available
        }
    """
    from .ml_engine import analyze_consumption_patterns, predict_with_ml
    
    now = dt_util.now()
    
    # During startup, vehicle data may not be available yet
    # However, we should still try to calculate an estimate using fallback values
    # This provides an initial value instead of showing "Unknown" after HA restart
    startup_scenario = current_range_km is None and current_tank_level is None
    if startup_scenario:
        _LOGGER.debug(
            "Startup scenario detected - no vehicle data available yet. "
            "Will attempt to calculate initial estimate using fallback values and tank capacity."
        )
    
    # Check data sufficiency
    sufficiency = await check_data_sufficiency(hass, entry, min_data_points)
    
    # Calculate historical consumption
    historical = await calculate_historical_consumption(hass, entry)
    
    # Try ML-enhanced prediction first
    ml_prediction = None
    ml_enabled = False
    
    if sufficiency["sufficient"] and current_range_km is not None:
        try:
            ml_prediction = await predict_with_ml(
                hass,
                entry,
                days_ahead=14,
                current_range_km=current_range_km,
            )
            
            if ml_prediction.get("ml_enabled") and ml_prediction.get("confidence", 0) >= 0.5:
                ml_enabled = True
                _LOGGER.info("ML prediction enabled with confidence %.2f", ml_prediction.get("confidence"))
        except Exception as err:
            _LOGGER.warning("ML prediction failed, falling back to historical: %s", err)
    
    # Determine data source and values
    use_historical = sufficiency["sufficient"] and historical["avg_daily_km"] > 0
    
    _LOGGER.debug(
        "Data sufficiency check: sufficient=%s, odometer_points=%d, consumption_events=%d",
        sufficiency["sufficient"],
        sufficiency.get("odometer_points", 0),
        sufficiency.get("consumption_events", 0)
    )
    _LOGGER.debug(
        "Historical data: avg_daily_km=%.2f, avg_consumption_rate=%.2f, confidence=%.2f, data_points=%d",
        historical.get("avg_daily_km", 0),
        historical.get("avg_consumption_rate", 0),
        historical.get("confidence", 0),
        historical.get("data_points", 0)
    )
    
    if ml_enabled and ml_prediction:
        data_source = "ml_enhanced"
        # Use ML weekday pattern for more accurate daily km
        weekday_pattern = ml_prediction.get("weekday_pattern", {})
        if weekday_pattern:
            avg_daily_km = sum(weekday_pattern.values()) / len(weekday_pattern)
        else:
            avg_daily_km = historical["avg_daily_km"]
        avg_consumption_rate = historical["avg_consumption_rate"]
        confidence = ml_prediction.get("confidence", 0.5)
        data_points_used = historical["data_points"]
    elif use_historical:
        data_source = "historical_data"
        avg_daily_km = historical["avg_daily_km"]
        avg_consumption_rate = historical["avg_consumption_rate"]
        confidence = historical["confidence"]
        data_points_used = historical["data_points"]
    else:
        data_source = "fallback_values"
        avg_daily_km = fallback_daily_km
        avg_consumption_rate = fallback_consumption_rate
        confidence = 0.3  # Low confidence for fallback
        data_points_used = 0
    
    # Calculate days until refuel with improved fallback logic
    days_until_refuel = None
    weekday_pattern = None
    
    # Debug logging for input parameters
    _LOGGER.debug(
        "predict_days_until_refuel inputs: current_range_km=%.2f, current_tank_level=%.2f, "
        "tank_capacity=%.2f, avg_daily_km=%.2f, avg_consumption_rate=%.2f, data_source=%s",
        current_range_km if current_range_km is not None else -1,
        current_tank_level if current_tank_level is not None else -1,
        tank_capacity if tank_capacity is not None else -1,
        avg_daily_km,
        avg_consumption_rate,
        data_source
    )
    
    # Extract weekday pattern if available from ML prediction
    if ml_enabled and ml_prediction:
        weekday_pattern = ml_prediction.get("weekday_pattern", {})
    
    # Method 1: Use range-based calculation (most accurate when available)
    if current_range_km is not None and current_range_km > 0 and avg_daily_km > 0:
        _LOGGER.debug("Method 1: Using range-based calculation")
        # If ML prediction has depletion date, use it for better accuracy
        if ml_enabled and ml_prediction.get("predicted_range_depletion_date"):
            try:
                depletion_date = dt_util.parse_datetime(ml_prediction["predicted_range_depletion_date"])
                if depletion_date:
                    days_until_refuel = (depletion_date - now).total_seconds() / 86400
                    _LOGGER.debug("Using ML depletion date for days_until_refuel: %.1f days", days_until_refuel)
            except (ValueError, TypeError) as err:
                _LOGGER.debug("Failed to parse ML depletion date: %s", err)
        
        # Try weekday-aware calculation if we have the pattern and no ML depletion date
        if days_until_refuel is None and weekday_pattern:
            days_until_refuel = _calculate_days_until_refuel_with_weekday_pattern(
                current_range_km, weekday_pattern, now
            )
            if days_until_refuel is not None:
                _LOGGER.debug(
                    "Calculated days_until_refuel using weekday pattern: %.1f days for %.1f km",
                    days_until_refuel, current_range_km
                )
        
        # Fallback to simple average if weekday calculation didn't work
        if days_until_refuel is None:
            days_until_refuel = current_range_km / avg_daily_km
            _LOGGER.debug("Calculated days_until_refuel from range: %.1f days (%.1f km / %.1f km/day)", 
                         days_until_refuel, current_range_km, avg_daily_km)
    else:
        _LOGGER.debug(
            "Method 1 skipped: current_range_km=%s (>0?=%s), avg_daily_km=%.2f (>0?=%s)",
            current_range_km,
            current_range_km is not None and current_range_km > 0,
            avg_daily_km,
            avg_daily_km > 0
        )
    
    # Method 2: Calculate from tank level and consumption rate
    if days_until_refuel is None and current_tank_level is not None and tank_capacity is not None and avg_consumption_rate > 0 and avg_daily_km > 0:
        _LOGGER.debug("Method 2: Using tank level-based calculation")
        # Calculate estimated range from tank level
        estimated_range_km = (current_tank_level / avg_consumption_rate) * 100
        
        # Try weekday-aware calculation if we have the pattern
        if weekday_pattern:
            days_until_refuel = _calculate_days_until_refuel_with_weekday_pattern(
                estimated_range_km, weekday_pattern, now
            )
            if days_until_refuel is not None:
                _LOGGER.debug(
                    "Calculated days_until_refuel from tank level using weekday pattern: %.1f days (%.1f L → %.1f km)",
                    days_until_refuel, current_tank_level, estimated_range_km
                )
        
        # Fallback to simple average if weekday calculation didn't work
        if days_until_refuel is None:
            days_until_refuel = estimated_range_km / avg_daily_km
            _LOGGER.debug(
                "Calculated days_until_refuel from tank level: %.1f days (%.1f L → %.1f km / %.1f km/day)",
                days_until_refuel, current_tank_level, estimated_range_km, avg_daily_km
            )
    else:
        if days_until_refuel is None:
            _LOGGER.debug(
                "Method 2 skipped: days_until_refuel=%s, current_tank_level=%s, tank_capacity=%s, "
                "avg_consumption_rate=%.2f (>0?=%s), avg_daily_km=%.2f (>0?=%s)",
                days_until_refuel,
                current_tank_level,
                tank_capacity,
                avg_consumption_rate,
                avg_consumption_rate > 0,
                avg_daily_km,
                avg_daily_km > 0
            )
    
    # Method 3: Intelligent fallback using consumption forecast with weekday pattern
    # This replaces the old method that simply averaged refueling intervals
    # Now we use actual consumption data even when exact range/tank level is unavailable
    if days_until_refuel is None and use_historical and avg_daily_km > 0 and avg_consumption_rate > 0:
        _LOGGER.debug("Method 3: Using consumption-based fallback with weekday awareness")
        
        # Use weekday pattern if available for more accurate prediction
        if weekday_pattern and tank_capacity is not None:
            # Estimate current tank level as 50% if unknown (conservative estimate)
            estimated_tank_level = tank_capacity * STARTUP_ASSUMED_TANK_LEVEL
            estimated_range_km = (estimated_tank_level / avg_consumption_rate) * 100
            
            days_until_refuel = _calculate_days_until_refuel_with_weekday_pattern(
                estimated_range_km, weekday_pattern, now
            )
            if days_until_refuel is not None:
                _LOGGER.debug(
                    "Method 3 (weekday-aware): Estimated %.1f days from assumed %.1f%% tank "
                    "(%.1f L → %.1f km range) using weekday consumption pattern",
                    days_until_refuel, 50.0, estimated_tank_level, estimated_range_km
                )
        
        # Fallback to simple calculation if weekday pattern didn't work
        if days_until_refuel is None and tank_capacity is not None:
            # Conservative estimate: assume tank is 50% full
            estimated_tank_level = tank_capacity * STARTUP_ASSUMED_TANK_LEVEL
            estimated_range_km = (estimated_tank_level / avg_consumption_rate) * 100
            days_until_refuel = estimated_range_km / avg_daily_km
            _LOGGER.debug(
                "Method 3 (simple): Estimated %.1f days from assumed %.1f%% tank "
                "(%.1f L → %.1f km range / %.1f km/day)",
                days_until_refuel, 50.0, estimated_tank_level, estimated_range_km, avg_daily_km
            )
    else:
        if days_until_refuel is None:
            _LOGGER.debug(
                "Method 3 skipped: days_until_refuel=%s, use_historical=%s, "
                "avg_daily_km=%.2f (>0?=%s), avg_consumption_rate=%.2f (>0?=%s)",
                days_until_refuel,
                use_historical,
                avg_daily_km,
                avg_daily_km > 0,
                avg_consumption_rate,
                avg_consumption_rate > 0
            )
    
    # Method 4: Startup fallback - calculate initial estimate using fallback values
    # This ensures we show an initial value instead of "Unknown" after HA restart
    if days_until_refuel is None and startup_scenario and tank_capacity is not None and avg_daily_km > 0 and avg_consumption_rate > 0:
        _LOGGER.debug("Method 4: Using startup fallback with configured values")
        # Conservative estimate: assume tank is 50% full
        estimated_tank_level = tank_capacity * STARTUP_ASSUMED_TANK_LEVEL
        estimated_range_km = (estimated_tank_level / avg_consumption_rate) * 100
        days_until_refuel = estimated_range_km / avg_daily_km
        _LOGGER.info(
            "Startup fallback: Estimated %.1f days from assumed 50%% tank "
            "(%.1f L → %.1f km range / %.1f km/day). "
            "This will be refined when actual vehicle data becomes available.",
            days_until_refuel, estimated_tank_level, estimated_range_km, avg_daily_km
        )
    
    # Log final result before returning
    if days_until_refuel is None:
        # Check if this is a startup scenario where no vehicle data is available yet
        # This is expected during HA restart before sensors restore state or vehicle entities have data
        is_startup_scenario = (current_range_km is None and current_tank_level is None)
        
        if is_startup_scenario:
            # Log at DEBUG level - this is expected during startup
            _LOGGER.debug(
                "Cannot calculate days_until_refuel during startup: both current_range_km and current_tank_level are None. "
                "This is expected until vehicle sensors restore state or provide data. "
                "tank_capacity=%s, avg_daily_km=%.2f, avg_consumption_rate=%.2f, use_historical=%s",
                tank_capacity,
                avg_daily_km,
                avg_consumption_rate,
                use_historical
            )
        else:
            # Log at WARNING level - we have some vehicle data but calculation still failed
            _LOGGER.warning(
                "ALL METHODS FAILED: days_until_refuel is None. "
                "current_range_km=%s, current_tank_level=%s, tank_capacity=%s, "
                "avg_daily_km=%.2f, avg_consumption_rate=%.2f, use_historical=%s",
                current_range_km,
                current_tank_level,
                tank_capacity,
                avg_daily_km,
                avg_consumption_rate,
                use_historical
            )
        
        # Safety fallback: Last resort calculation to ensure we return a value when we have the data
        # Skip this during startup scenario to avoid more log noise
        if not is_startup_scenario and use_historical and avg_daily_km > 0 and avg_consumption_rate > 0:
            # Try explicit type conversion and validation before calculation
            try:
                # Method A: Calculate from tank_level if all components are present
                if (current_tank_level is not None and tank_capacity is not None and 
                    float(current_tank_level) > 0 and float(tank_capacity) > 0 and 
                    float(avg_consumption_rate) > 0):
                    estimated_range_km = (float(current_tank_level) / float(avg_consumption_rate)) * 100.0
                    if estimated_range_km > 0:
                        days_until_refuel = estimated_range_km / float(avg_daily_km)
                        _LOGGER.info(
                            "Safety fallback applied (tank_level): Calculated %.1f days from tank_level %.2f L "
                            "(estimated range %.1f km / avg_daily_km %.1f)",
                            days_until_refuel, current_tank_level, estimated_range_km, avg_daily_km
                        )
                # Method B: Calculate from range_km if available
                elif current_range_km is not None and float(current_range_km) > 0:
                    days_until_refuel = float(current_range_km) / float(avg_daily_km)
                    _LOGGER.info(
                        "Safety fallback applied (range_km): Calculated %.1f days from range_km %.1f km / avg_daily_km %.1f",
                        days_until_refuel, current_range_km, avg_daily_km
                    )
                else:
                    _LOGGER.error(
                        "Safety fallback failed: Cannot calculate days_until_refuel. "
                        "Neither range_km nor (tank_level + tank_capacity) are available or valid."
                    )
            except (TypeError, ValueError, ZeroDivisionError) as err:
                _LOGGER.error(
                    "Safety fallback calculation failed with error: %s. "
                    "Values: current_range_km=%s, current_tank_level=%s, tank_capacity=%s, "
                    "avg_daily_km=%.2f, avg_consumption_rate=%.2f",
                    err, current_range_km, current_tank_level, tank_capacity,
                    avg_daily_km, avg_consumption_rate
                )
    
    # Calculate predicted refuel date
    if days_until_refuel is not None and days_until_refuel > 0:
        predicted_refuel_date = now + timedelta(days=days_until_refuel)
    else:
        predicted_refuel_date = None
    
    _LOGGER.info(
        "Consumption prediction: days_until_refuel=%.1f, data_source=%s, "
        "confidence=%.2f, avg_daily_km=%.1f, avg_consumption=%.2f L/100km",
        days_until_refuel or 0, data_source, confidence, avg_daily_km, avg_consumption_rate
    )
    
    return {
        "days_until_refuel": round(days_until_refuel, 1) if days_until_refuel is not None else None,
        "predicted_refuel_date": predicted_refuel_date,
        "data_source": data_source,
        "confidence": confidence,
        "avg_daily_km": avg_daily_km,
        "avg_consumption_rate": avg_consumption_rate,
        "last_prediction_time": now,
        "data_points_used": data_points_used,
        "ml_prediction": ml_prediction if ml_enabled else None,
        "weekday_pattern": weekday_pattern if weekday_pattern else None,
    }


async def store_prediction_result(
    hass: HomeAssistant,
    entry: ConfigEntry,
    prediction: Dict[str, Any],
) -> None:
    """Store prediction result in history for tracking accuracy.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        prediction: Prediction result dictionary
    """
    data = await load_data(hass, entry)
    
    if "prediction_history" not in data:
        data["prediction_history"] = []
    
    # Store prediction with serializable values
    # Handle both datetime objects and strings for timestamp fields
    last_prediction_time = prediction["last_prediction_time"]
    if isinstance(last_prediction_time, str):
        timestamp = last_prediction_time
    else:
        timestamp = last_prediction_time.isoformat()
    
    predicted_refuel_date = prediction["predicted_refuel_date"]
    if predicted_refuel_date is None:
        refuel_date_str = None
    elif isinstance(predicted_refuel_date, str):
        refuel_date_str = predicted_refuel_date
    else:
        refuel_date_str = predicted_refuel_date.isoformat()
    
    prediction_record = {
        "timestamp": timestamp,
        "days_until_refuel": prediction["days_until_refuel"],
        "predicted_refuel_date": refuel_date_str,
        "data_source": prediction["data_source"],
        "confidence": prediction["confidence"],
        "avg_daily_km": prediction["avg_daily_km"],
        "avg_consumption_rate": prediction["avg_consumption_rate"],
        "data_points_used": prediction["data_points_used"],
    }
    
    data["prediction_history"].append(prediction_record)
    
    # Keep only last 100 predictions
    if len(data["prediction_history"]) > 100:
        data["prediction_history"] = data["prediction_history"][-100:]
    
    await save_data(hass, entry, data)
    
    _LOGGER.debug("Stored prediction result in history")
