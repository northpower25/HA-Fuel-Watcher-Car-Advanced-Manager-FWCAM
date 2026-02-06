"""
Prediction Engine for haFWCMA
-----------------------------
Main prediction and recommendation engine that combines:
- Price analysis (price_engine)
- Statistical analysis (statistics_engine)
- Refuel decision logic

Generates intelligent refueling recommendations based on:
- Current fuel level
- Price trends
- Driving patterns
- Configurable thresholds
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .storage import (
    get_last_price,
    set_last_price,
    set_last_decision,
    get_last_decision,
)
from .price_engine import (
    compute_price_delta,
    compute_price_delta_percent,
    compute_price_trend,
    get_price_statistics,
)
from .statistics_engine import (
    estimate_days_left,
    get_avg_daily_km,
)

_LOGGER = logging.getLogger(__name__)

# Configuration key names (will be added to const.py)
CONF_PRICE_DROP_PERCENT_THRESHOLD = "price_drop_percent_threshold"
CONF_PRICE_DROP_ABSOLUTE_THRESHOLD = "price_drop_absolute_threshold"
CONF_LOW_FUEL_THRESHOLD = "low_fuel_threshold"
CONF_CRITICAL_FUEL_THRESHOLD = "critical_fuel_threshold"
CONF_FALLBACK_DAILY_KM = "fallback_daily_km"

# Default values
DEFAULT_PRICE_DROP_PERCENT = 2.0  # 2% price drop
DEFAULT_PRICE_DROP_ABSOLUTE = 0.05  # 5 cents drop
DEFAULT_LOW_FUEL_THRESHOLD = 30.0  # 30% tank level
DEFAULT_CRITICAL_FUEL_THRESHOLD = 15.0  # 15% tank level
DEFAULT_FALLBACK_DAILY_KM = 40.0  # 40 km per day


async def evaluate_refuel_strategy(
    hass: HomeAssistant,
    entry: ConfigEntry,
    current_price: float,
    tank_percentage: float,
    range_km: Optional[float] = None,
    station_name: Optional[str] = None,
) -> dict:
    """Main refueling strategy evaluation.
    
    Decides if vehicle should refuel now based on multiple factors:
    - Price trends and thresholds
    - Tank level urgency
    - Estimated days until empty
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        current_price: Current fuel price in EUR/L
        tank_percentage: Tank fill percentage (0-100)
        range_km: Estimated range in km (optional)
        station_name: Name of station being evaluated (optional)
        
    Returns:
        Dictionary with recommendation:
        {
            "should_refuel": bool,
            "reason": str,
            "urgency": str,  # "low", "medium", "high", "critical"
            "price_delta": float,
            "price_delta_percent": float,
            "days_left": float,
            "recommendation": str,  # User-friendly recommendation text
        }
    """
    options = entry.options or entry.data

    # Get configuration thresholds
    percent_threshold = float(
        options.get(CONF_PRICE_DROP_PERCENT_THRESHOLD, DEFAULT_PRICE_DROP_PERCENT)
    )
    absolute_threshold = float(
        options.get(CONF_PRICE_DROP_ABSOLUTE_THRESHOLD, DEFAULT_PRICE_DROP_ABSOLUTE)
    )
    low_fuel_threshold = float(
        options.get(CONF_LOW_FUEL_THRESHOLD, DEFAULT_LOW_FUEL_THRESHOLD)
    )
    critical_fuel_threshold = float(
        options.get(CONF_CRITICAL_FUEL_THRESHOLD, DEFAULT_CRITICAL_FUEL_THRESHOLD)
    )
    fallback_daily_km = float(
        options.get(CONF_FALLBACK_DAILY_KM, DEFAULT_FALLBACK_DAILY_KM)
    )

    last_price = await get_last_price(hass, entry)

    # Calculate price changes
    price_delta = await compute_price_delta(hass, entry, current_price=current_price)
    price_delta_percent = await compute_price_delta_percent(
        hass, entry, current_price=current_price
    )
    price_trend = await compute_price_trend(hass, entry, window=5)
    
    # Estimate days until empty
    days_left = None
    if range_km:
        days_left = await estimate_days_left(
            hass, entry, km_left=range_km, fallback_daily_km=fallback_daily_km
        )

    # Initialize decision
    should_refuel = False
    urgency = "low"
    reason = "No action needed"
    recommendation = "Tank level adequate, prices stable."

    # First check: Is this the first observation?
    if last_price is None:
        await set_last_price(hass, entry, current_price)
        decision = {
            "should_refuel": False,
            "reason": "initial",
            "urgency": "low",
            "timestamp": datetime.now().isoformat(),
        }
        await set_last_decision(hass, entry, decision)
        
        return {
            "should_refuel": False,
            "reason": "Initial price observation",
            "urgency": "low",
            "price_delta": 0.0,
            "price_delta_percent": 0.0,
            "days_left": days_left,
            "recommendation": "Monitoring prices...",
        }

    # CRITICAL: Tank is critically low
    if tank_percentage <= critical_fuel_threshold:
        should_refuel = True
        urgency = "critical"
        reason = f"Critical tank level ({tank_percentage:.1f}%)"
        recommendation = f"⚠️ REFUEL IMMEDIATELY! Tank at {tank_percentage:.1f}%"
        
    # HIGH: Tank is low
    elif tank_percentage <= low_fuel_threshold:
        should_refuel = True
        urgency = "high"
        reason = f"Low tank level ({tank_percentage:.1f}%)"
        
        if price_delta and price_delta < 0:
            recommendation = f"🔔 Refuel now - tank low ({tank_percentage:.1f}%) and prices favorable"
        else:
            recommendation = f"⛽ Refuel soon - tank at {tank_percentage:.1f}%"
    
    # MEDIUM: Good price opportunity
    elif price_delta and price_delta_percent:
        # Check absolute threshold
        if absolute_threshold > 0 and price_delta <= -absolute_threshold:
            should_refuel = True
            urgency = "medium"
            reason = f"Price dropped by {abs(price_delta):.3f} EUR/L"
            recommendation = f"💰 Good price! Down {abs(price_delta):.3f}€/L ({price_delta_percent:.1f}%)"
            
        # Check percent threshold
        elif percent_threshold > 0 and price_delta_percent <= -percent_threshold:
            should_refuel = True
            urgency = "medium"
            reason = f"Price dropped by {abs(price_delta_percent):.1f}%"
            recommendation = f"💰 Good price! Down {abs(price_delta_percent):.1f}% ({abs(price_delta):.3f}€/L)"
    
    # Consider price trend for additional context
    if not should_refuel and price_trend:
        if price_trend == "falling":
            if tank_percentage < 50:
                recommendation = "📉 Prices falling but tank getting low. Monitor closely."
            else:
                recommendation = "📉 Prices falling. Wait if tank adequate."
        elif price_trend == "rising":
            if tank_percentage < 50:
                should_refuel = True
                urgency = "medium"
                reason = "Prices rising and tank below half"
                recommendation = f"📈 Prices rising! Tank at {tank_percentage:.1f}%, refuel soon."
            else:
                recommendation = f"📈 Prices rising but tank at {tank_percentage:.1f}%. Monitor."
        else:  # stable
            if tank_percentage < 40:
                recommendation = f"Tank at {tank_percentage:.1f}%. Refuel at convenience."
            else:
                recommendation = "All good. No urgent action needed."
    
    # Add days until empty to recommendation if available
    if days_left and days_left < 3:
        if days_left < 1:
            urgency = "high"
            recommendation += f" ⚠️ Less than 1 day of fuel!"
        else:
            recommendation += f" (~{days_left:.1f} days of fuel)"

    # Store decision
    decision = {
        "should_refuel": should_refuel,
        "reason": reason,
        "urgency": urgency,
        "price_delta": price_delta,
        "price_delta_percent": price_delta_percent,
        "timestamp": datetime.now().isoformat(),
        "station_name": station_name,
    }
    await set_last_decision(hass, entry, decision)
    
    # Update last price if we're recommending refueling
    if should_refuel:
        await set_last_price(hass, entry, current_price)

    _LOGGER.debug(
        "Refuel strategy: should_refuel=%s, urgency=%s, reason=%s, "
        "tank=%.1f%%, price_delta=%.3f, price_delta_percent=%.2f%%",
        should_refuel,
        urgency,
        reason,
        tank_percentage,
        price_delta or 0,
        price_delta_percent or 0,
    )

    return {
        "should_refuel": should_refuel,
        "reason": reason,
        "urgency": urgency,
        "price_delta": price_delta or 0.0,
        "price_delta_percent": price_delta_percent or 0.0,
        "days_left": days_left,
        "recommendation": recommendation,
    }


async def get_prediction_summary(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict:
    """Get a summary of current predictions and statistics.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Dictionary with prediction summary
    """
    # Get last decision
    last_decision = await get_last_decision(hass, entry)
    
    # Get price statistics
    price_stats = await get_price_statistics(hass, entry, days=7)
    
    # Get average daily km
    avg_daily_km = await get_avg_daily_km(hass, entry, fallback=DEFAULT_FALLBACK_DAILY_KM)
    
    # Get price trend
    price_trend = await compute_price_trend(hass, entry, window=5)
    
    return {
        "last_decision": last_decision,
        "price_statistics": price_stats,
        "avg_daily_km": avg_daily_km,
        "price_trend": price_trend,
    }
