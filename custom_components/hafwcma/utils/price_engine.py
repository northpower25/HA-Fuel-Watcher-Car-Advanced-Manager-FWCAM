"""
Price Engine for haFWCMA
------------------------
Price analysis logic including:
- Price delta (absolute and percent)
- Price spike detection
- Price trend analysis
- Last known price tracking

Based on the fuel_watcher price_engine.py.
"""
from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .storage import (
    get_price_history,
    get_last_price,
    get_tank_history,
)

_LOGGER = logging.getLogger(__name__)


def _parse_ts(ts: str) -> Optional[datetime]:
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


async def _get_last_price_from_history(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> Optional[float]:
    """Return last price from price_history.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Last price or None
    """
    prices = await get_price_history(hass, entry)
    if not prices:
        return None

    # Sort by timestamp
    sorted_prices = sorted(
        prices,
        key=lambda x: _parse_ts(x.get("ts") or "") or datetime.min,
    )

    return sorted_prices[-1].get("price")


async def _get_last_price_from_tank_history(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> Optional[float]:
    """Return last price_per_liter from tank_history.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Last price from refueling or None
    """
    events = await get_tank_history(hass, entry)
    if not events:
        return None

    # Get most recent event with price data
    for event in reversed(events):
        price = event.get("price_per_liter")
        if price is not None:
            return price
    
    return None


async def get_last_known_price(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> Optional[float]:
    """Return the most reliable last known price.
    
    Priority:
    1. Last price from tank history (actual refuel)
    2. Last price from price history
    3. Last stored price
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Last known price or None
    """
    # Try tank history first (actual refuel price)
    tank_price = await _get_last_price_from_tank_history(hass, entry)
    if tank_price is not None:
        return tank_price

    # Try price history
    history_price = await _get_last_price_from_history(hass, entry)
    if history_price is not None:
        return history_price
    
    # Fall back to stored last price
    return await get_last_price(hass, entry)


async def compute_price_delta(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    current_price: Optional[float],
) -> Optional[float]:
    """Compute absolute price delta.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        current_price: Current price to compare
        
    Returns:
        Price delta in EUR or None
    """
    if current_price is None:
        return None

    last_price = await get_last_known_price(hass, entry)
    if last_price is None:
        return None

    delta = current_price - float(last_price)
    return round(delta, 3)


async def compute_price_delta_percent(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    current_price: Optional[float],
) -> Optional[float]:
    """Compute percent price delta.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        current_price: Current price to compare
        
    Returns:
        Price delta in percent or None
    """
    if current_price is None:
        return None

    last_price = await get_last_known_price(hass, entry)
    if last_price is None or last_price == 0:
        return None

    percent = ((current_price - last_price) / last_price) * 100
    return round(percent, 2)


async def detect_price_spike(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    current_price: Optional[float],
    threshold: float = 0.08,
) -> Optional[bool]:
    """Detect price spike.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        current_price: Current price to check
        threshold: Absolute difference threshold in EUR/L
        
    Returns:
        True if spike detected, False if not, None if cannot determine
    """
    delta = await compute_price_delta(hass, entry, current_price=current_price)
    if delta is None:
        return None

    return delta >= threshold


async def compute_price_trend(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    window: int = 5,
) -> Optional[str]:
    """Compute price trend based on last N price entries.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        window: Number of recent entries to analyze
        
    Returns:
        "rising", "falling", "stable", or None (not enough data)
    """
    prices = await get_price_history(hass, entry)
    if len(prices) < 2:
        return None

    # Sort chronologically
    sorted_prices = sorted(
        prices,
        key=lambda x: _parse_ts(x.get("ts") or "") or datetime.min,
    )

    # Take last N entries
    window_prices = sorted_prices[-window:]
    values = [p.get("price") for p in window_prices if p.get("price") is not None]

    if len(values) < 2:
        return None

    # Compare first and last in window
    first_price = values[0]
    last_price = values[-1]
    
    # Use a small threshold to avoid noise (0.5 cent)
    threshold = 0.005
    
    if last_price > first_price + threshold:
        return "rising"
    elif last_price < first_price - threshold:
        return "falling"
    else:
        return "stable"


async def get_price_statistics(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    days: int = 7,
) -> dict[str, Optional[float]]:
    """Get price statistics for recent period.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        days: Number of days to analyze
        
    Returns:
        Dictionary with min, max, avg prices
    """
    prices = await get_price_history(hass, entry)
    
    if not prices:
        return {
            "min_price": None,
            "max_price": None,
            "avg_price": None,
            "current_price": None,
        }
    
    # Filter to recent days
    cutoff = datetime.now().timestamp() - (days * 24 * 3600)
    recent_prices = []
    
    for p in prices:
        ts = _parse_ts(p.get("ts") or "")
        if ts and ts.timestamp() > cutoff:
            price = p.get("price")
            if price is not None:
                recent_prices.append(price)
    
    if not recent_prices:
        return {
            "min_price": None,
            "max_price": None,
            "avg_price": None,
            "current_price": None,
        }
    
    return {
        "min_price": round(min(recent_prices), 3),
        "max_price": round(max(recent_prices), 3),
        "avg_price": round(sum(recent_prices) / len(recent_prices), 3),
        "current_price": recent_prices[-1],
    }
