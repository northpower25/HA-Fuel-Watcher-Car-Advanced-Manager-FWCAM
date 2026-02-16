"""
Machine Learning Module for haFWCMA
------------------------------------
Implements basic machine learning algorithms for improved consumption and range predictions.

Features:
- Time-series trend analysis
- Pattern recognition (weekday/weekend, seasonal)
- Adaptive learning from prediction accuracy
- Confidence scoring improvements
"""
from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

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

# Outlier detection thresholds for daily km calculations
# These values represent reasonable bounds for typical vehicle usage patterns
# MAX: Extremely high but possible for long-distance driving (e.g., 800km road trip)
# MIN: Minimum to avoid near-zero calculations that might indicate sensor errors
MAX_REASONABLE_DAILY_KM = 800.0
MIN_REASONABLE_DAILY_KM = 0.1


def _parse_iso_timestamp(ts: str) -> Optional[datetime]:
    """Parse ISO format timestamp.
    
    Args:
        ts: Timestamp string in ISO format
        
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


async def analyze_consumption_patterns(
    hass: HomeAssistant,
    entry: ConfigEntry,
    lookback_days: int = 90,
) -> Dict[str, Any]:
    """Analyze consumption patterns using machine learning techniques.
    
    Identifies:
    - Weekday vs weekend patterns
    - Weekly trends
    - Seasonal variations
    - Anomalies in consumption
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        lookback_days: Days to analyze
        
    Returns:
        Dictionary with pattern analysis:
        {
            "weekday_pattern": {weekday: avg_km},
            "weekend_factor": float,  # Multiplier for weekend vs weekday
            "trend_direction": str,  # "increasing", "decreasing", "stable"
            "trend_strength": float,  # 0-1
            "confidence": float,  # 0-1
        }
    """
    odometer_history = await get_odometer_history(hass, entry)
    
    if not odometer_history or len(odometer_history) < 7:
        return {
            "weekday_pattern": {},
            "weekend_factor": 1.0,
            "trend_direction": "stable",
            "trend_strength": 0.0,
            "confidence": 0.0,
        }
    
    # Filter by lookback period
    cutoff_time = dt_util.now() - timedelta(days=lookback_days)
    recent_history = [
        entry for entry in odometer_history
        if _parse_iso_timestamp(entry.get("ts", "")) and 
           _parse_iso_timestamp(entry.get("ts", "")) >= cutoff_time
    ]
    
    if len(recent_history) < 7:
        return {
            "weekday_pattern": {},
            "weekend_factor": 1.0,
            "trend_direction": "stable",
            "trend_strength": 0.0,
            "confidence": 0.0,
        }
    
    # Sort by timestamp - filter out entries with None timestamps first
    valid_history = [
        entry for entry in recent_history 
        if _parse_iso_timestamp(entry.get("ts", "")) is not None
    ]
    sorted_history = sorted(valid_history, key=lambda x: _parse_iso_timestamp(x.get("ts", "")))
    
    # Calculate daily km for each day
    weekday_km: Dict[int, List[float]] = {i: [] for i in range(7)}
    
    # Track outliers for logging
    outliers_detected = 0
    
    for i in range(len(sorted_history) - 1):
        current = sorted_history[i]
        next_entry = sorted_history[i + 1]
        
        current_ts = _parse_iso_timestamp(current.get("ts", ""))
        next_ts = _parse_iso_timestamp(next_entry.get("ts", ""))
        
        if not current_ts or not next_ts:
            continue
        
        try:
            current_km = float(current.get("value", 0))
            next_km = float(next_entry.get("value", 0))
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "Invalid odometer value in ML analysis: current=%s, next=%s (error: %s)",
                current.get("value"), next_entry.get("value"), err
            )
            continue
        
        # Calculate km driven
        km_driven = next_km - current_km
        days_elapsed = (next_ts - current_ts).total_seconds() / 86400
        
        # Validation: Skip invalid or suspicious data
        if days_elapsed <= 0:
            _LOGGER.debug("Skipping entry with non-positive time elapsed: %.4f days", days_elapsed)
            continue
        
        if km_driven < 0:
            _LOGGER.debug(
                "Skipping entry with negative km driven: %.1f km (odometer rollback or reset?)",
                km_driven
            )
            continue
        
        if days_elapsed > 2:
            # Skip entries with gaps > 2 days to avoid inaccurate attribution
            continue
        
        # Calculate daily km
        daily_km = km_driven / days_elapsed
        
        # Outlier detection: Flag and skip extremely high daily km values
        if daily_km > MAX_REASONABLE_DAILY_KM:
            outliers_detected += 1
            _LOGGER.warning(
                "Outlier detected: %.1f km/day (%.1f km over %.2f days) from %s to %s. "
                "Skipping this data point. Check odometer readings: current=%.1f km, next=%.1f km",
                daily_km,
                km_driven,
                days_elapsed,
                current_ts.strftime("%Y-%m-%d %H:%M"),
                next_ts.strftime("%Y-%m-%d %H:%M"),
                current_km,
                next_km
            )
            continue
        
        # Skip extremely low values that might indicate sensor errors
        if daily_km < MIN_REASONABLE_DAILY_KM:
            _LOGGER.debug("Skipping very low daily km: %.4f km/day", daily_km)
            continue
        
        # Assign to weekday
        weekday = current_ts.weekday()
        weekday_km[weekday].append(daily_km)
    
    # Log outlier detection summary
    if outliers_detected > 0:
        _LOGGER.warning(
            "ML Pattern Analysis: Detected and filtered %d outlier(s) with suspiciously high daily km values. "
            "This can happen due to comma/decimal separator issues, odometer reading errors, or data corruption.",
            outliers_detected
        )
    
    # Calculate weekday pattern with additional outlier filtering
    weekday_pattern = {}
    for weekday, km_list in weekday_km.items():
        if not km_list:
            continue
        
        # Apply statistical outlier removal within each weekday's data
        # Use IQR method if we have enough data points
        if len(km_list) >= 4:
            sorted_km = sorted(km_list)
            
            # Use statistics.quantiles for accurate quartile calculation
            # quantiles(data, n=4) returns 3 cut points for quartiles
            try:
                quartiles = statistics.quantiles(sorted_km, n=4)
                
                # Ensure we have the expected number of quartiles
                if len(quartiles) >= 3:
                    q1 = quartiles[0]  # 25th percentile
                    q3 = quartiles[2]  # 75th percentile
                    iqr = q3 - q1
                    
                    # Define outliers as values outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR]
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    
                    # Filter outliers
                    filtered_km = [km for km in km_list if lower_bound <= km <= upper_bound]
                    
                    if filtered_km:
                        weekday_pattern[weekday] = sum(filtered_km) / len(filtered_km)
                        
                        # Log if we filtered out values
                        if len(filtered_km) < len(km_list):
                            _LOGGER.info(
                                "Weekday %d: Filtered %d/%d outliers using IQR method (bounds: %.1f-%.1f km/day)",
                                weekday, len(km_list) - len(filtered_km), len(km_list),
                                lower_bound, upper_bound
                            )
                    else:
                        # All values were outliers - use median as fallback
                        weekday_pattern[weekday] = statistics.median(sorted_km)
                        _LOGGER.warning(
                            "Weekday %d: All values were statistical outliers. Using median: %.1f km/day",
                            weekday, weekday_pattern[weekday]
                        )
                else:
                    # Insufficient quartile data - just use average
                    weekday_pattern[weekday] = sum(km_list) / len(km_list)
            except (statistics.StatisticsError, IndexError, ValueError) as err:
                # Not enough data, all values identical, or other statistical error - just use average
                _LOGGER.debug("Could not calculate quartiles for weekday %d: %s. Using simple average.", weekday, err)
                weekday_pattern[weekday] = sum(km_list) / len(km_list)
        else:
            # Not enough data for statistical filtering, just average
            weekday_pattern[weekday] = sum(km_list) / len(km_list)
    
    # Calculate weekend factor (Sat/Sun vs Mon-Fri)
    weekday_avg = []
    weekend_avg = []
    
    for weekday, avg_km in weekday_pattern.items():
        if weekday < 5:  # Mon-Fri
            weekday_avg.append(avg_km)
        else:  # Sat-Sun
            weekend_avg.append(avg_km)
    
    if weekday_avg and weekend_avg:
        weekday_mean = sum(weekday_avg) / len(weekday_avg)
        weekend_mean = sum(weekend_avg) / len(weekend_avg)
        weekend_factor = weekend_mean / weekday_mean if weekday_mean > 0 else 1.0
    else:
        weekend_factor = 1.0
    
    # Calculate trend using linear regression on recent data
    if len(sorted_history) >= 14:
        # Use last 14 days for trend
        recent_14 = sorted_history[-14:]
        
        # Simple linear regression
        x_values = []
        y_values = []
        
        for i, entry in enumerate(recent_14):
            y_values.append(float(entry.get("value", 0)))
            x_values.append(i)
        
        # Calculate slope (trend)
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_xx = sum(x * x for x in x_values)
        
        if n * sum_xx - sum_x * sum_x != 0:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
            
            # Normalize slope to daily km change
            days_span = (_parse_iso_timestamp(recent_14[-1].get("ts", "")) - 
                        _parse_iso_timestamp(recent_14[0].get("ts", ""))).days
            
            if days_span > 0:
                daily_change = slope / days_span
                
                # Determine trend direction and strength
                if abs(daily_change) < 0.5:
                    trend_direction = "stable"
                    trend_strength = 0.0
                elif daily_change > 0:
                    trend_direction = "increasing"
                    trend_strength = min(abs(daily_change) / 5.0, 1.0)  # Normalize to 0-1
                else:
                    trend_direction = "decreasing"
                    trend_strength = min(abs(daily_change) / 5.0, 1.0)
            else:
                trend_direction = "stable"
                trend_strength = 0.0
        else:
            trend_direction = "stable"
            trend_strength = 0.0
    else:
        trend_direction = "stable"
        trend_strength = 0.0
    
    # Calculate confidence based on data quantity and consistency
    data_count_factor = min(len(recent_history) / 30, 1.0)  # More data = higher confidence
    
    # Check consistency (variance in weekday patterns)
    if weekday_pattern:
        pattern_values = list(weekday_pattern.values())
        if len(pattern_values) > 1:
            mean_pattern = sum(pattern_values) / len(pattern_values)
            variance = sum((x - mean_pattern) ** 2 for x in pattern_values) / len(pattern_values)
            std_dev = variance ** 0.5
            # Use coefficient of variation for consistency
            if mean_pattern > 0:
                coefficient_of_variation = std_dev / mean_pattern
                consistency_factor = max(0.0, 1.0 - coefficient_of_variation)
            else:
                consistency_factor = 0.0
        else:
            consistency_factor = 0.5
    else:
        consistency_factor = 0.0
    
    confidence = (data_count_factor * 0.6 + consistency_factor * 0.4)
    
    _LOGGER.debug(
        "ML Pattern Analysis: weekday_pattern=%s, weekend_factor=%.2f, "
        "trend=%s (%.2f), confidence=%.2f",
        weekday_pattern, weekend_factor, trend_direction, trend_strength, confidence
    )
    
    return {
        "weekday_pattern": weekday_pattern,
        "weekend_factor": round(weekend_factor, 2),
        "trend_direction": trend_direction,
        "trend_strength": round(trend_strength, 2),
        "confidence": round(confidence, 2),
    }


async def predict_with_ml(
    hass: HomeAssistant,
    entry: ConfigEntry,
    days_ahead: int = 7,
    current_range_km: Optional[float] = None,
) -> Dict[str, Any]:
    """Predict future consumption using machine learning.
    
    Combines pattern recognition with historical data for better predictions.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        days_ahead: Number of days to predict
        current_range_km: Current vehicle range
        
    Returns:
        Dictionary with ML-enhanced predictions:
        {
            "predicted_daily_km": List[float],  # Predictions for next N days
            "predicted_range_depletion_date": datetime,
            "confidence": float,
            "ml_enabled": bool,
        }
    """
    # Get pattern analysis
    patterns = await analyze_consumption_patterns(hass, entry)
    
    if patterns["confidence"] < 0.3:
        # Not enough data for ML predictions
        return {
            "predicted_daily_km": [],
            "predicted_range_depletion_date": None,
            "confidence": 0.0,
            "ml_enabled": False,
        }
    
    # Get base daily km from patterns
    weekday_pattern = patterns["weekday_pattern"]
    
    if not weekday_pattern:
        return {
            "predicted_daily_km": [],
            "predicted_range_depletion_date": None,
            "confidence": 0.0,
            "ml_enabled": False,
        }
    
    # Predict for next N days based on weekday pattern
    predicted_daily_km = []
    now = dt_util.now()
    
    for day_offset in range(days_ahead):
        future_date = now + timedelta(days=day_offset)
        weekday = future_date.weekday()
        
        # Get predicted km for this weekday
        if weekday in weekday_pattern:
            predicted_km = weekday_pattern[weekday]
        else:
            # Use average if no data for this weekday
            predicted_km = sum(weekday_pattern.values()) / len(weekday_pattern)
        
        # Apply trend adjustment
        trend_direction = patterns["trend_direction"]
        trend_strength = patterns["trend_strength"]
        
        if trend_direction == "increasing":
            predicted_km *= (1.0 + trend_strength * 0.1 * day_offset)
        elif trend_direction == "decreasing":
            predicted_km *= (1.0 - trend_strength * 0.1 * day_offset)
        
        predicted_daily_km.append(round(predicted_km, 1))
    
    # Calculate range depletion date if range is known
    predicted_range_depletion_date = None
    if current_range_km is not None and current_range_km > 0:
        remaining_range = current_range_km
        depletion_day = 0
        
        for day_offset, daily_km in enumerate(predicted_daily_km):
            remaining_range -= daily_km
            if remaining_range <= 0:
                depletion_day = day_offset
                break
        
        if remaining_range > 0:
            # Range lasts beyond prediction window
            avg_daily = sum(predicted_daily_km) / len(predicted_daily_km)
            additional_days = remaining_range / avg_daily if avg_daily > 0 else 0
            depletion_day = days_ahead + additional_days
        
        predicted_range_depletion_date = now + timedelta(days=depletion_day)
    
    # Calculate average predicted daily km for logging
    avg_predicted_daily_km = sum(predicted_daily_km) / len(predicted_daily_km) if predicted_daily_km else 0.0
    
    _LOGGER.info(
        "ML Prediction: days_ahead=%d, avg_predicted_daily_km=%.1f, "
        "depletion_date=%s, confidence=%.2f",
        days_ahead,
        avg_predicted_daily_km,
        predicted_range_depletion_date.isoformat() if predicted_range_depletion_date else "N/A",
        patterns["confidence"]
    )
    
    return {
        "predicted_daily_km": predicted_daily_km,
        "predicted_range_depletion_date": predicted_range_depletion_date.isoformat() if predicted_range_depletion_date else None,
        "confidence": patterns["confidence"],
        "ml_enabled": True,
        "weekday_pattern": patterns["weekday_pattern"],
        "trend": patterns["trend_direction"],
        "trend_strength": patterns["trend_strength"],
    }


async def store_ml_model(
    hass: HomeAssistant,
    entry: ConfigEntry,
    model_data: Dict[str, Any],
) -> None:
    """Store ML model parameters in Home Assistant database.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        model_data: Model parameters to store
    """
    data = await load_data(hass, entry)
    
    if "ml_models" not in data:
        data["ml_models"] = {}
    
    data["ml_models"]["consumption_pattern"] = {
        "timestamp": dt_util.now().isoformat(),
        "data": model_data,
    }
    
    await save_data(hass, entry, data)


async def get_ml_model(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> Optional[Dict[str, Any]]:
    """Retrieve stored ML model parameters.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Model data or None
    """
    data = await load_data(hass, entry)
    
    if "ml_models" not in data:
        return None
    
    return data["ml_models"].get("consumption_pattern")
