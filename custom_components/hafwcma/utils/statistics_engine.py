"""
Statistics Engine for haFWCMA
-----------------------------
Self-learning consumption and range logic based on vehicle data.

Functions:
- Evaluate odometer history
- Calculate daily kilometers
- Track weekday average values
- Calculate average daily kilometers
- Estimate range in days

Based on the fuel_watcher statistics_engine.py.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util

from .storage import (
    get_odometer_history,
    get_weekday_consumption,
    update_weekday_consumption,
    load_data,
    save_data,
)

import logging

_LOGGER = logging.getLogger(__name__)


def _parse_ts(ts: str) -> Optional[datetime]:
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


async def recompute_weekday_stats(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Recompute weekday statistics from odometer history.
    
    This function can be used if logic changes or
    historical data needs to be recomputed.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    data = await load_data(hass, entry)
    odo = await get_odometer_history(hass, entry)

    # Reset stats
    data["weekday_consumption"] = {}
    stats = data["weekday_consumption"]

    if len(odo) < 2:
        # Not enough data
        await update_weekday_consumption(hass, entry, 0, 0.0)
        return

    # Sort by timestamp
    odo_sorted = sorted(
        odo,
        key=lambda x: _parse_ts(x.get("ts") or "") or dt_util.as_local(datetime.min),
    )

    last = odo_sorted[0]
    last_ts = _parse_ts(last.get("ts") or "")
    last_val = last.get("value")

    for entry_ in odo_sorted[1:]:
        ts = _parse_ts(entry_.get("ts") or "")
        val = entry_.get("value")

        if ts is None or last_ts is None:
            last_ts = ts
            last_val = val
            continue

        try:
            km = float(val) - float(last_val)
        except Exception:
            last_ts = ts
            last_val = val
            continue

        if km <= 0:
            last_ts = ts
            last_val = val
            continue

        weekday = ts.weekday()
        weekday_str = str(weekday)
        if weekday_str not in stats:
            stats[weekday_str] = {"km": 0.0, "count": 0}

        stats[weekday_str]["km"] += km
        stats[weekday_str]["count"] += 1

        last_ts = ts
        last_val = val

    data["weekday_consumption"] = stats
    await save_data(hass, entry, data)


async def get_avg_daily_km(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    fallback: float = 40.0,
) -> float:
    """Compute average daily kilometers based on weekday statistics.
    
    When there is not enough data, the fallback value is used.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        fallback: Fallback value when insufficient data
        
    Returns:
        Average daily kilometers
    """
    stats = await get_weekday_consumption(hass, entry)

    if not stats:
        return fallback

    total_km = 0.0
    total_days = 0

    for wd, s in stats.items():
        km = float(s.get("km", 0.0))
        count = int(s.get("count", 0))
        if count <= 0:
            continue
        total_km += km
        total_days += count

    if total_days <= 0:
        return fallback

    avg = total_km / total_days
    # Limit to reasonable values
    if avg <= 0:
        return fallback

    return round(avg, 1)


async def estimate_days_left(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    km_left: Optional[float],
    fallback_daily_km: float = 40.0,
) -> Optional[float]:
    """Estimate remaining days based on km_left and learned daily km.
    
    Used by sensors to calculate days until refuel needed.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        km_left: Remaining range in kilometers
        fallback_daily_km: Fallback daily km value
        
    Returns:
        Estimated days left or None if cannot calculate
    """
    if km_left is None:
        return None

    avg_daily_km = await get_avg_daily_km(hass, entry, fallback=fallback_daily_km)
    if avg_daily_km <= 0:
        return None

    days = km_left / avg_daily_km
    return round(days, 1)


async def calculate_consumption_rate(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    distance_km: float,
    fuel_used_liters: float,
) -> Optional[float]:
    """Calculate fuel consumption rate in L/100km.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        distance_km: Distance traveled in kilometers
        fuel_used_liters: Fuel consumed in liters
        
    Returns:
        Consumption rate in L/100km or None if invalid
    """
    if distance_km <= 0 or fuel_used_liters <= 0:
        return None
    
    consumption = (fuel_used_liters / distance_km) * 100
    
    # Sanity check: typical car consumption is between 2-30 L/100km
    if consumption < 1.0 or consumption > 50.0:
        _LOGGER.warning(
            "Unusual consumption rate calculated: %.2f L/100km (distance: %.2f km, fuel: %.2f L)",
            consumption,
            distance_km,
            fuel_used_liters,
        )
        # Still return it but log warning
    
    return round(consumption, 2)


async def get_average_consumption_rate(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    fallback: float | None = 7.0,
) -> float | None:
    """Get average fuel consumption rate from tank history.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        fallback: Fallback consumption rate in L/100km. Pass None to return None
                  when no historical data is available (allows callers to distinguish
                  "no data" from an actual historical average).
        
    Returns:
        Average consumption rate in L/100km, or fallback if no data available
    """
    data = await load_data(hass, entry)
    tank_history = data.get("tank_history", [])
    
    if not tank_history:
        return fallback
    
    # Collect consumption rates from refueling events
    consumption_rates = []
    for event in tank_history:
        rate = event.get("consumption_rate")
        if rate and 1.0 <= rate <= 50.0:  # Sanity check
            consumption_rates.append(rate)
    
    if not consumption_rates:
        return fallback
    
    # Calculate average
    avg = sum(consumption_rates) / len(consumption_rates)
    return round(avg, 2)
