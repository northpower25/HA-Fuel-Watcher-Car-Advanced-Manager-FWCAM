"""
Price Statistics Engine for haFWCMA
------------------------------------
Historical fuel price analysis with weekday and timeframe patterns.

Features:
- Weekday price patterns (Monday-Sunday)
- Best time frames per weekday (morning/afternoon/evening/night)
- Top 3 cheapest stations per weekday and period
- Last week, 14-day, and month price statistics
- Price trend analysis (up/down)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util

from .storage import get_price_history

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
        # Fallback to fromisoformat
        dt = datetime.fromisoformat(ts)
        # Make timezone-aware if it's naive
        if dt.tzinfo is None:
            return dt_util.as_local(dt)
        return dt
    except Exception:
        return None


def _get_timeframe(hour: int) -> str:
    """Get timeframe name based on hour.
    
    Args:
        hour: Hour of day (0-23)
        
    Returns:
        Timeframe name: morning, afternoon, evening, or night
    """
    if 7 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def _calculate_top_stations(
    prices_with_stations: List[Dict[str, Any]],
    top_n: int = 3
) -> List[Dict[str, Any]]:
    """Calculate top N cheapest stations from price data.
    
    Args:
        prices_with_stations: List of price observations with station data
        top_n: Number of top stations to return
        
    Returns:
        List of top N cheapest stations with average prices
    """
    # Group by station
    station_prices = defaultdict(list)
    station_info = {}
    
    for obs in prices_with_stations:
        station_id = obs.get("station_id")
        if not station_id:
            continue
            
        price = obs.get("price")
        if price is None:
            continue
            
        station_prices[station_id].append(price)
        
        # Keep station info (will be overwritten, but that's ok)
        if "station_name" in obs:
            station_info[station_id] = {
                "name": obs.get("station_name"),
                "brand": obs.get("station_brand"),
                "city": obs.get("station_city"),
                "street": obs.get("station_street"),
            }
    
    # Calculate average price per station
    station_averages = []
    for station_id, prices in station_prices.items():
        avg_price = sum(prices) / len(prices)
        info = station_info.get(station_id, {})
        
        # Format station name as [brand] [place] [street] or use name if components missing
        brand = info.get("brand", "")
        city = info.get("city", "")
        street = info.get("street", "")
        station_name = info.get("name", "Unknown")
        
        # Build formatted name if we have brand, city, and street
        if brand and city and street:
            formatted_name = f"{brand} {city} {street}"
        else:
            # Fall back to stored name
            formatted_name = station_name
        
        station_averages.append({
            "station_id": station_id,
            "station_name": formatted_name,
            "avg_price": round(avg_price, 3),
            "observations": len(prices),
        })
    
    # Sort by average price and return top N
    station_averages.sort(key=lambda x: x["avg_price"])
    return station_averages[:top_n]


def _calculate_weekday_statistics(
    price_history: List[Dict[str, Any]],
    start_date: datetime,
    end_date: datetime,
) -> Dict[str, Any]:
    """Calculate price statistics per weekday.
    
    Args:
        price_history: List of price observations
        start_date: Start of the period
        end_date: End of the period
        
    Returns:
        Dictionary with weekday statistics
    """
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # Group data by weekday
    weekday_data = {}
    for i in range(7):
        weekday_data[i] = {
            "prices": [],
            "timeframes": defaultdict(list),
            "stations": []
        }
    
    for obs in price_history:
        ts_str = obs.get("ts")
        if not ts_str:
            continue
            
        ts = _parse_iso_timestamp(ts_str)
        if not ts or ts < start_date or ts > end_date:
            continue
            
        price = obs.get("price")
        if price is None:
            continue
            
        weekday = ts.weekday()
        hour = ts.hour
        timeframe = _get_timeframe(hour)
        
        # Store price for weekday
        weekday_data[weekday]["prices"].append(price)
        weekday_data[weekday]["timeframes"][timeframe].append(price)
        
        # Store station info if available
        if obs.get("station_id"):
            weekday_data[weekday]["stations"].append(obs)
    
    # Calculate statistics for each weekday - always show all 7 weekdays
    result = {}
    for weekday in range(7):
        weekday_name = weekday_names[weekday]
        data = weekday_data[weekday]
        prices = data["prices"]
        
        if not prices:
            # No data for this weekday - show "Waiting for more data"
            result[weekday_name] = {
                "avg_price": "Waiting for more data",
                "best_timeframe": "Waiting for more data",
                "observations": 0,
            }
            # Add placeholder top stations
            result[weekday_name]["top_stations"] = [
                {"name": "Waiting for more data", "avg_price": "Waiting for more data"},
                {"name": "Waiting for more data", "avg_price": "Waiting for more data"},
                {"name": "Waiting for more data", "avg_price": "Waiting for more data"},
            ]
            continue
            
        avg_price = sum(prices) / len(prices)
        
        # Find best timeframe (lowest average price)
        best_timeframe = None
        best_timeframe_price = float('inf')
        
        for timeframe, tf_prices in data["timeframes"].items():
            if tf_prices:
                tf_avg = sum(tf_prices) / len(tf_prices)
                if tf_avg < best_timeframe_price:
                    best_timeframe_price = tf_avg
                    best_timeframe = timeframe
        
        # Get top 3 stations for this weekday
        top_stations = _calculate_top_stations(data["stations"], top_n=3)
        
        result[weekday_name] = {
            "avg_price": round(avg_price, 3),
            "min_price": round(min(prices), 3),
            "best_timeframe": best_timeframe if best_timeframe else "Waiting for more data",
            "observations": len(prices),
        }
        
        # Always show 3 station slots
        formatted_stations = []
        for i in range(3):
            if i < len(top_stations):
                formatted_stations.append({
                    "name": top_stations[i]["station_name"],
                    "avg_price": top_stations[i]["avg_price"],
                })
            else:
                # Fill missing slots with "Waiting for more data"
                formatted_stations.append({
                    "name": "Waiting for more data",
                    "avg_price": "Waiting for more data",
                })
        
        result[weekday_name]["top_stations"] = formatted_stations
    
    return result


def _calculate_period_statistics(
    price_history: List[Dict[str, Any]],
    start_date: datetime,
    end_date: datetime,
    previous_start_date: Optional[datetime] = None,
    previous_end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Calculate price statistics for a period.
    
    Args:
        price_history: List of price observations
        start_date: Start of the period
        end_date: End of the period
        previous_start_date: Start of previous period for trend comparison
        previous_end_date: End of previous period for trend comparison
        
    Returns:
        Dictionary with period statistics
    """
    # Filter observations for the period
    period_prices = []
    period_stations = []
    
    for obs in price_history:
        ts_str = obs.get("ts")
        if not ts_str:
            continue
            
        ts = _parse_iso_timestamp(ts_str)
        if not ts or ts < start_date or ts > end_date:
            continue
            
        price = obs.get("price")
        if price is None:
            continue
            
        period_prices.append(price)
        if obs.get("station_id"):
            period_stations.append(obs)
    
    if not period_prices:
        return None
    
    avg_price = sum(period_prices) / len(period_prices)
    
    # Calculate trend if previous period is provided
    trend = "Waiting for more data"
    if previous_start_date and previous_end_date:
        previous_prices = []
        for obs in price_history:
            ts_str = obs.get("ts")
            if not ts_str:
                continue
                
            ts = _parse_iso_timestamp(ts_str)
            if not ts or ts < previous_start_date or ts > previous_end_date:
                continue
                
            price = obs.get("price")
            if price is not None:
                previous_prices.append(price)
        
        if previous_prices:
            prev_avg_price = sum(previous_prices) / len(previous_prices)
            # Use a threshold to avoid floating-point precision issues
            # Consider differences less than 0.001 EUR (0.1 cent) as stable
            price_diff = avg_price - prev_avg_price
            if abs(price_diff) < 0.001:
                trend = "stable"
            elif price_diff > 0:
                trend = "up"
            else:
                trend = "down"
    
    # Get top 5 stations for this period
    top_stations = _calculate_top_stations(period_stations, top_n=5)
    
    result = {
        "avg_price": round(avg_price, 3),
        "observations": len(period_prices),
        "trend": trend,
    }
    
    # Always show 5 station slots with proper formatting
    formatted_stations = []
    for i in range(5):
        if i < len(top_stations):
            formatted_stations.append({
                "name": top_stations[i]["station_name"],
                "avg_price": top_stations[i]["avg_price"],
            })
        else:
            # Fill missing slots with "Waiting for more data"
            formatted_stations.append({
                "name": "Waiting for more data",
                "avg_price": "Waiting for more data",
            })
    
    result["top_stations"] = formatted_stations
    
    return result


def _calculate_daily_cheapest_prices(
    price_history: List[Dict[str, Any]],
    start_date: datetime,
    end_date: datetime,
) -> List[Dict[str, Any]]:
    """Calculate the cheapest price recorded per calendar day.

    Args:
        price_history: List of price observations
        start_date: Start of the period
        end_date: End of the period

    Returns:
        List of {date: str (YYYY-MM-DD), min_price: float} sorted by date.
    """
    daily_min: Dict[str, float] = {}

    for obs in price_history:
        ts_str = obs.get("ts")
        if not ts_str:
            continue

        ts = _parse_iso_timestamp(ts_str)
        if not ts or ts < start_date or ts > end_date:
            continue

        price = obs.get("price")
        if price is None:
            continue

        day_key = ts.strftime("%Y-%m-%d")
        if day_key not in daily_min or price < daily_min[day_key]:
            daily_min[day_key] = price

    return [
        {"date": day, "min_price": round(daily_min[day], 3)}
        for day in sorted(daily_min)
    ]


async def calculate_price_statistics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> Dict[str, Any]:
    """Calculate comprehensive price statistics.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        
    Returns:
        Dictionary with price statistics including:
        - weekday_patterns: Statistics per weekday
        - last_week: Statistics for last 7 days
        - last_14_days: Statistics for last 14 days
        - last_month: Statistics for last 30 days
    """
    price_history = await get_price_history(hass, entry)
    
    if not price_history:
        _LOGGER.debug("No price history available for statistics")
        return {}
    
    now = dt_util.now()
    
    # Define periods
    last_week_start = now - timedelta(days=7)
    last_week_end = now
    
    previous_week_start = now - timedelta(days=14)
    previous_week_end = now - timedelta(days=7)
    
    last_14_days_start = now - timedelta(days=14)
    last_14_days_end = now
    
    previous_14_days_start = now - timedelta(days=28)
    previous_14_days_end = now - timedelta(days=14)
    
    last_month_start = now - timedelta(days=30)
    last_month_end = now
    
    previous_month_start = now - timedelta(days=60)
    previous_month_end = now - timedelta(days=30)
    
    # Calculate weekday patterns for last week
    weekday_patterns = _calculate_weekday_statistics(
        price_history,
        last_week_start,
        last_week_end,
    )
    
    # Calculate period statistics
    last_week_stats = _calculate_period_statistics(
        price_history,
        last_week_start,
        last_week_end,
        previous_week_start,
        previous_week_end,
    )
    
    last_14_days_stats = _calculate_period_statistics(
        price_history,
        last_14_days_start,
        last_14_days_end,
        previous_14_days_start,
        previous_14_days_end,
    )
    
    last_month_stats = _calculate_period_statistics(
        price_history,
        last_month_start,
        last_month_end,
        previous_month_start,
        previous_month_end,
    )
    
    # Calculate daily cheapest prices for last 30 days (for line chart)
    daily_cheapest = _calculate_daily_cheapest_prices(
        price_history,
        last_month_start,
        last_month_end,
    )

    result = {}
    
    if weekday_patterns:
        result["weekday_patterns"] = weekday_patterns
    
    if last_week_stats:
        result["last_week"] = last_week_stats
    
    if last_14_days_stats:
        result["last_14_days"] = last_14_days_stats
    
    if last_month_stats:
        result["last_month"] = last_month_stats

    if daily_cheapest:
        result["daily_cheapest_prices"] = daily_cheapest
    
    _LOGGER.debug("Price statistics calculated: %d weekdays, periods: %s", 
                  len(weekday_patterns), list(result.keys()))
    
    return result
