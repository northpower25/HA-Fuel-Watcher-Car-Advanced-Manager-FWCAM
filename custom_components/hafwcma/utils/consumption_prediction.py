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


def _parse_timestamp(ts: str) -> Optional[datetime]:
    """Parse ISO format timestamp.
    
    Args:
        ts: Timestamp string
        
    Returns:
        Datetime object or None if parse fails
    """
    try:
        return datetime.fromisoformat(ts)
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
    odometer_history = await get_odometer_history(hass, entry)
    tank_history = await get_tank_history(hass, entry)
    
    odometer_points = len(odometer_history)
    tank_points = len(tank_history)
    
    # Count refueling events with valid consumption data
    consumption_events = sum(
        1 for event in tank_history 
        if event.get("consumption_rate") and event.get("consumption_rate") > 0
    )
    
    sufficient = (
        odometer_points >= min_data_points 
        and consumption_events >= max(2, min_data_points // 2)
    )
    
    if sufficient:
        reason = f"Sufficient data available ({odometer_points} odometer points, {consumption_events} consumption events)"
    else:
        reason = f"Insufficient data ({odometer_points}/{min_data_points} odometer points, {consumption_events} consumption events)"
    
    _LOGGER.debug(
        "Data sufficiency check: sufficient=%s, odometer=%d, tank=%d, consumption=%d",
        sufficient, odometer_points, tank_points, consumption_events
    )
    
    return {
        "sufficient": sufficient,
        "odometer_points": odometer_points,
        "tank_points": tank_points,
        "consumption_events": consumption_events,
        "reason": reason,
    }


async def calculate_historical_consumption(
    hass: HomeAssistant,
    entry: ConfigEntry,
    lookback_days: int = 30,
) -> Dict[str, Any]:
    """Calculate consumption statistics from historical data.
    
    Analyzes odometer and tank level changes to determine:
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
    odometer_history = await get_odometer_history(hass, entry)
    tank_history = await get_tank_history(hass, entry)
    
    if not odometer_history or len(odometer_history) < 2:
        return {
            "avg_daily_km": 0.0,
            "avg_consumption_rate": 0.0,
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
            else:
                avg_daily_km = 0.0
        else:
            avg_daily_km = 0.0
    else:
        avg_daily_km = 0.0
    
    # Calculate average consumption rate from refueling events
    recent_tank = [
        event for event in tank_history
        if _parse_timestamp(event.get("timestamp", "")) and
           _parse_timestamp(event.get("timestamp", "")) >= cutoff_time and
           event.get("consumption_rate") and
           1.0 <= event.get("consumption_rate", 0) <= 50.0  # Sanity check
    ]
    
    if recent_tank:
        consumption_rates = [event.get("consumption_rate", 0) for event in recent_tank]
        avg_consumption_rate = sum(consumption_rates) / len(consumption_rates)
        
        # Calculate trend from first half vs second half
        if len(consumption_rates) >= 4:
            mid_point = len(consumption_rates) // 2
            first_half_avg = sum(consumption_rates[:mid_point]) / mid_point
            second_half_avg = sum(consumption_rates[mid_point:]) / (len(consumption_rates) - mid_point)
            
            diff_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100
            
            if diff_percent > 5:
                trend = "increasing"
            elif diff_percent < -5:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"
    else:
        avg_consumption_rate = 0.0
        trend = "unknown"
    
    # Calculate confidence based on data points
    data_points = len(recent_odometer) + len(recent_tank)
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
    
    # Calculate days until refuel
    if current_range_km is not None and current_range_km > 0:
        # Use range-based calculation (most accurate)
        days_until_refuel = current_range_km / avg_daily_km if avg_daily_km > 0 else None
        
        # If ML prediction has depletion date, use it for better accuracy
        if ml_enabled and ml_prediction.get("predicted_range_depletion_date"):
            try:
                depletion_date = datetime.fromisoformat(ml_prediction["predicted_range_depletion_date"])
                days_until_refuel = (depletion_date - now).total_seconds() / 86400
            except (ValueError, TypeError) as err:
                _LOGGER.debug("Failed to parse ML depletion date: %s", err)
                # Use calculated value
                
    elif current_tank_level is not None and tank_capacity is not None and avg_consumption_rate > 0:
        # Calculate range from tank level and consumption rate
        estimated_range_km = (current_tank_level / avg_consumption_rate) * 100
        days_until_refuel = estimated_range_km / avg_daily_km if avg_daily_km > 0 else None
    else:
        # Cannot calculate
        days_until_refuel = None
    
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
        "days_until_refuel": round(days_until_refuel, 1) if days_until_refuel else None,
        "predicted_refuel_date": predicted_refuel_date,
        "data_source": data_source,
        "confidence": confidence,
        "avg_daily_km": avg_daily_km,
        "avg_consumption_rate": avg_consumption_rate,
        "last_prediction_time": now,
        "data_points_used": data_points_used,
        "ml_prediction": ml_prediction if ml_enabled else None,
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
    prediction_record = {
        "timestamp": prediction["last_prediction_time"].isoformat(),
        "days_until_refuel": prediction["days_until_refuel"],
        "predicted_refuel_date": prediction["predicted_refuel_date"].isoformat() if prediction["predicted_refuel_date"] else None,
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
