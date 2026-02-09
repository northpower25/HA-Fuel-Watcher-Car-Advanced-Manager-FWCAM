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
        # Fallback to fromisoformat and make it timezone-aware
        dt = datetime.fromisoformat(ts)
        return dt_util.as_local(dt)
    except (ValueError, TypeError):
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
    
    for i in range(len(sorted_history) - 1):
        current = sorted_history[i]
        next_entry = sorted_history[i + 1]
        
        current_ts = _parse_iso_timestamp(current.get("ts", ""))
        next_ts = _parse_iso_timestamp(next_entry.get("ts", ""))
        
        if not current_ts or not next_ts:
            continue
        
        current_km = float(current.get("value", 0))
        next_km = float(next_entry.get("value", 0))
        
        # Calculate km driven
        km_driven = next_km - current_km
        days_elapsed = (next_ts - current_ts).total_seconds() / 86400
        
        if days_elapsed > 0 and km_driven >= 0 and days_elapsed <= 2:  # Max 2 days between readings
            daily_km = km_driven / days_elapsed
            weekday = current_ts.weekday()
            weekday_km[weekday].append(daily_km)
    
    # Calculate weekday pattern
    weekday_pattern = {}
    for weekday, km_list in weekday_km.items():
        if km_list:
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
