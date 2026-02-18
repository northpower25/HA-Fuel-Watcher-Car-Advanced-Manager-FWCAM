"""
Refuel Recommendation Engine for haFWCMA
-----------------------------------------
Advanced refueling recommendations including:
- Multi-radius station comparison (10km vs 20km)
- Savings calculation considering driving distance and fuel consumption
- Position change tracking and cooldown mechanism
- Historical price-based forecast recommendations
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util

from .geolocation import calculate_distance
from .storage import get_price_history

_LOGGER = logging.getLogger(__name__)

# Position change tracking constants
SIGNIFICANT_POSITION_CHANGE_KM = 50.0  # Distance that triggers cooldown
POSITION_CHANGE_COOLDOWN_MINUTES = 30  # Cooldown period after significant movement
PRICE_CHANGE_THRESHOLD_FOR_COOLDOWN = 0.10  # 10 cents - only apply cooldown if price change is large

# Savings calculation constants
DEFAULT_AVG_CONSUMPTION = 7.0  # L/100km - typical value for mid-size vehicles

# Forecast recommendation constants
FORECAST_MIN_HISTORY_POINTS = 10  # Minimum number of price observations needed for forecast
FORECAST_SIGNIFICANT_PRICE_DIFFERENCE = 0.05  # €0.05/L - threshold for significant day-to-day price differences
FORECAST_NEAR_BEST_PRICE_MARGIN = 0.03  # €0.03/L - margin to consider current price "close to historical cheapest"
FORECAST_NEAR_HISTORICAL_BEST_MARGIN = 0.02  # €0.02/L - margin to consider current price "near historical best"

# Weekday names - used across multiple functions
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class PositionTracker:
    """Tracks vehicle position changes and manages recommendation cooldowns."""
    
    def __init__(self):
        """Initialize position tracker."""
        self._last_position: Optional[Tuple[float, float]] = None
        self._last_position_time: Optional[datetime] = None
        self._cooldown_until: Optional[datetime] = None
        self._last_price: Optional[float] = None
    
    def update(
        self,
        latitude: float,
        longitude: float,
        current_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Update position and check for significant changes.
        
        Args:
            latitude: Current latitude
            longitude: Current longitude
            current_price: Current fuel price (optional)
            
        Returns:
            Dictionary with position change info and cooldown status
        """
        now = dt_util.now()
        result = {
            "significant_change": False,
            "distance_moved_km": 0.0,
            "in_cooldown": False,
            "cooldown_reason": None,
        }
        
        # Check if we're in cooldown period
        if self._cooldown_until and now < self._cooldown_until:
            result["in_cooldown"] = True
            remaining_seconds = (self._cooldown_until - now).total_seconds()
            result["cooldown_remaining_minutes"] = remaining_seconds / 60
            return result
        
        # Calculate distance from last position
        if self._last_position:
            distance_km = calculate_distance(
                self._last_position[0],
                self._last_position[1],
                latitude,
                longitude
            )
            result["distance_moved_km"] = round(distance_km, 2)
            
            # Check if movement is significant
            if distance_km >= SIGNIFICANT_POSITION_CHANGE_KM:
                result["significant_change"] = True
                
                # Check if price changed significantly (indicating region change)
                price_changed_significantly = False
                if self._last_price is not None and current_price is not None:
                    price_delta = abs(current_price - self._last_price)
                    if price_delta >= PRICE_CHANGE_THRESHOLD_FOR_COOLDOWN:
                        price_changed_significantly = True
                        result["price_delta"] = round(price_delta, 3)
                
                # Apply cooldown if price changed significantly
                if price_changed_significantly:
                    self._cooldown_until = now + timedelta(minutes=POSITION_CHANGE_COOLDOWN_MINUTES)
                    result["in_cooldown"] = True
                    result["cooldown_remaining_minutes"] = POSITION_CHANGE_COOLDOWN_MINUTES
                    result["cooldown_reason"] = (
                        f"Moved {distance_km:.0f}km with price change of "
                        f"€{result.get('price_delta', 0):.3f}/L"
                    )
                    _LOGGER.info(
                        "Position change cooldown activated: moved %.0fkm, "
                        "price changed by €%.3f/L, cooldown for %d minutes",
                        distance_km,
                        result.get("price_delta", 0),
                        POSITION_CHANGE_COOLDOWN_MINUTES
                    )
        
        # Update tracking data
        self._last_position = (latitude, longitude)
        self._last_position_time = now
        if current_price is not None:
            self._last_price = current_price
        
        return result


async def compare_stations_by_radius(
    hass: HomeAssistant,
    entry: ConfigEntry,
    stations_list: List[Dict[str, Any]],
    vehicle_lat: float,
    vehicle_lon: float,
    current_tank_level: float,
    tank_capacity: float,
    avg_consumption: float,
    near_radius: float = 10.0,
    far_radius: float = None,
) -> Dict[str, Any]:
    """Compare cheapest stations within near and far radius.
    
    Calculates true savings considering:
    - Distance to station and back
    - Fuel consumed during the trip
    - Amount of fuel to be purchased
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        stations_list: List of stations with prices and locations
        vehicle_lat: Vehicle latitude
        vehicle_lon: Vehicle longitude
        current_tank_level: Current tank level in liters
        tank_capacity: Maximum tank capacity in liters
        avg_consumption: Average consumption in L/100km (values <= 0 will be replaced
                        with DEFAULT_AVG_CONSUMPTION)
        near_radius: Radius for "near" stations comparison in km (default: 10.0)
        far_radius: Radius for "far" stations comparison in km (default: uses all stations in list)
        
    Returns:
        Dictionary with comparison results and savings calculation
    """
    if not stations_list:
        return {
            "has_comparison": False,
            "reason": "No stations available"
        }
    
    # Ensure we have valid consumption data (replace invalid values with default)
    if avg_consumption <= 0:
        avg_consumption = DEFAULT_AVG_CONSUMPTION  # Use default for typical mid-size vehicle
    
    # Calculate fuel to purchase (full tank minus current level)
    fuel_to_purchase = max(0, tank_capacity - current_tank_level)
    
    if fuel_to_purchase <= 0:
        return {
            "has_comparison": False,
            "reason": "Tank is full",
            "fuel_to_purchase": 0
        }
    
    # Separate stations by radius
    stations_near = []
    stations_far = []
    
    for station in stations_list:
        distance = station.get("distance_km", 0)
        if distance <= near_radius:
            stations_near.append(station)
        # If far_radius is specified, filter by it; otherwise use all stations
        if far_radius is None or distance <= far_radius:
            stations_far.append(station)
    
    # Find cheapest in each radius
    cheapest_near = None
    cheapest_far = None
    
    if stations_near:
        cheapest_near = min(stations_near, key=lambda s: s.get("price", float('inf')))
    
    if stations_far:
        cheapest_far = min(stations_far, key=lambda s: s.get("price", float('inf')))
    
    # If no far stations or same as near, no comparison needed
    if not cheapest_far or (cheapest_near and cheapest_near.get("id") == cheapest_far.get("id")):
        return {
            "has_comparison": False,
            "reason": "No different stations to compare",
            "cheapest_near": cheapest_near,
            "near_radius_km": near_radius,
        }
    
    # Calculate costs and savings
    if cheapest_near:
        # Cost at near station
        distance_near = cheapest_near.get("distance_km", 0)
        round_trip_near = distance_near * 2
        fuel_consumed_near = (round_trip_near * avg_consumption) / 100.0
        price_near = cheapest_near.get("price", 0)
        
        cost_fuel_near = fuel_to_purchase * price_near
        cost_trip_near = fuel_consumed_near * price_near
        total_cost_near = cost_fuel_near + cost_trip_near
        
        # Cost at far station
        distance_far = cheapest_far.get("distance_km", 0)
        round_trip_far = distance_far * 2
        fuel_consumed_far = (round_trip_far * avg_consumption) / 100.0
        price_far = cheapest_far.get("price", 0)
        
        cost_fuel_far = fuel_to_purchase * price_far
        cost_trip_far = fuel_consumed_far * price_far
        total_cost_far = cost_fuel_far + cost_trip_far
        
        # Calculate savings (can be negative if far is more expensive overall)
        savings = total_cost_near - total_cost_far
        savings_percent = (savings / total_cost_near * 100) if total_cost_near > 0 else 0
        
        # Prepare station data structures for near station
        near_data = {
            "name": cheapest_near.get("name"),
            "distance_km": round(distance_near, 1),
            "price": round(price_near, 3),
            "round_trip_km": round(round_trip_near, 1),
            "fuel_consumed": round(fuel_consumed_near, 2),
            "cost_fuel": round(cost_fuel_near, 2),
            "cost_trip": round(cost_trip_near, 2),
            "total_cost": round(total_cost_near, 2),
        }
        
        # Prepare station data structures for far station
        far_data = {
            "name": cheapest_far.get("name"),
            "distance_km": round(distance_far, 1),
            "price": round(price_far, 3),
            "round_trip_km": round(round_trip_far, 1),
            "fuel_consumed": round(fuel_consumed_far, 2),
            "cost_fuel": round(cost_fuel_far, 2),
            "cost_trip": round(cost_trip_far, 2),
            "total_cost": round(total_cost_far, 2),
        }
        
        return {
            "has_comparison": True,
            "fuel_to_purchase": round(fuel_to_purchase, 1),
            "avg_consumption": round(avg_consumption, 1),
            "near_radius_km": near_radius,
            "far_radius_km": far_radius if far_radius is not None else None,
            "far_radius_label": f"{far_radius}km" if far_radius is not None else "all stations",
            # Use descriptive keys for clarity
            "station_near": near_data,
            "station_far": far_data,
            # Keep old keys for backward compatibility with existing code
            "station_10km": near_data,
            "station_20km": far_data,
            # Also provide as nearest/cheapest for consistency with previous enhancement
            "nearest_station": near_data,
            "cheapest_station": far_data,
            "savings": round(savings, 2),
            "savings_percent": round(savings_percent, 1),
            "recommendation": _format_savings_recommendation(
                savings, cheapest_near, cheapest_far, distance_near, distance_far
            ),
            "comparison_type": "near_vs_far_radius",  # New comparison type
        }
    
    # No stations within near radius but there are stations available
    # Compare nearest station vs cheapest station for cost analysis
    if not cheapest_near and len(stations_list) >= 2:
        # Find the nearest station - O(n) complexity
        nearest_station = min(stations_list, key=lambda s: s.get("distance_km", float('inf')))
        
        # Find the cheapest station overall
        cheapest_overall = min(stations_list, key=lambda s: s.get("price", float('inf')))
        
        # Only compare if they are different stations
        if nearest_station.get("id") != cheapest_overall.get("id"):
            # Cost at nearest station
            distance_near = nearest_station.get("distance_km", 0)
            round_trip_near = distance_near * 2
            fuel_consumed_near = (round_trip_near * avg_consumption) / 100.0
            price_near = nearest_station.get("price", 0)
            
            cost_fuel_near = fuel_to_purchase * price_near
            cost_trip_near = fuel_consumed_near * price_near
            total_cost_near = cost_fuel_near + cost_trip_near
            
            # Cost at cheapest station
            distance_cheap = cheapest_overall.get("distance_km", 0)
            round_trip_cheap = distance_cheap * 2
            fuel_consumed_cheap = (round_trip_cheap * avg_consumption) / 100.0
            price_cheap = cheapest_overall.get("price", 0)
            
            cost_fuel_cheap = fuel_to_purchase * price_cheap
            cost_trip_cheap = fuel_consumed_cheap * price_cheap
            total_cost_cheap = cost_fuel_cheap + cost_trip_cheap
            
            # Calculate savings (can be negative if cheaper station is farther and more expensive overall)
            savings = total_cost_near - total_cost_cheap
            savings_percent = (savings / total_cost_near * 100) if total_cost_near > 0 else 0
            
            # Prepare station data structures
            nearest_data = {
                "name": nearest_station.get("name"),
                "distance_km": round(distance_near, 1),
                "price": round(price_near, 3),
                "round_trip_km": round(round_trip_near, 1),
                "fuel_consumed": round(fuel_consumed_near, 2),
                "cost_fuel": round(cost_fuel_near, 2),
                "cost_trip": round(cost_trip_near, 2),
                "total_cost": round(total_cost_near, 2),
            }
            
            cheapest_data = {
                "name": cheapest_overall.get("name"),
                "distance_km": round(distance_cheap, 1),
                "price": round(price_cheap, 3),
                "round_trip_km": round(round_trip_cheap, 1),
                "fuel_consumed": round(fuel_consumed_cheap, 2),
                "cost_fuel": round(cost_fuel_cheap, 2),
                "cost_trip": round(cost_trip_cheap, 2),
                "total_cost": round(total_cost_cheap, 2),
            }
            
            return {
                "has_comparison": True,
                "fuel_to_purchase": round(fuel_to_purchase, 1),
                "avg_consumption": round(avg_consumption, 1),
                # Use descriptive keys for clarity
                "nearest_station": nearest_data,
                "cheapest_station": cheapest_data,
                # Keep old keys for backward compatibility with existing code that expects
                # station_10km/station_20km keys. In this alternative comparison mode,
                # these keys represent nearest/cheapest rather than actual 10km/20km stations.
                "station_10km": nearest_data,
                "station_20km": cheapest_data,
                "savings": round(savings, 2),
                "savings_percent": round(savings_percent, 1),
                "recommendation": _format_savings_recommendation(
                    savings, nearest_station, cheapest_overall, distance_near, distance_cheap
                ),
                "comparison_type": "nearest_vs_cheapest",  # Indicate alternative comparison
            }
    
    # Insufficient stations for comparison
    # This happens when: no stations within 10km AND (only one station available OR nearest=cheapest)
    if len(stations_list) < 2:
        reason = "Only one station available"
    else:
        reason = "Nearest and cheapest stations are the same"
    
    return {
        "has_comparison": False,
        "reason": reason,
        "cheapest_20km": cheapest_20km,
    }


def _format_savings_recommendation(
    savings: float,
    station_10km: Dict[str, Any],
    station_20km: Dict[str, Any],
    distance_10km: float,
    distance_20km: float,
) -> str:
    """Format user-friendly savings recommendation.
    
    Args:
        savings: Savings amount in EUR (positive = save by going to 20km)
        station_10km: 10km station data
        station_20km: 20km station data
        distance_10km: Distance to 10km station
        distance_20km: Distance to 20km station
        
    Returns:
        Formatted recommendation string
    """
    if savings > 2.0:
        return (
            f"💰 Save €{savings:.2f} by driving to {station_20km.get('name')} "
            f"({distance_20km:.1f}km away) instead of {station_10km.get('name')} "
            f"({distance_10km:.1f}km)"
        )
    elif savings > 0.5:
        return (
            f"💡 Small savings of €{savings:.2f} possible at {station_20km.get('name')} "
            f"({distance_20km:.1f}km) vs {station_10km.get('name')} ({distance_10km:.1f}km)"
        )
    elif savings > -0.5:
        return (
            f"≈ Similar cost: {station_10km.get('name')} ({distance_10km:.1f}km) "
            f"and {station_20km.get('name')} ({distance_20km:.1f}km)"
        )
    else:
        return (
            f"🏆 Best choice: {station_10km.get('name')} ({distance_10km:.1f}km). "
            f"Going to {station_20km.get('name')} ({distance_20km:.1f}km) "
            f"would cost €{abs(savings):.2f} more"
        )


async def analyze_forecast_recommendation(
    hass: HomeAssistant,
    entry: ConfigEntry,
    predicted_refuel_date: Optional[datetime],
    current_price: float,
) -> Dict[str, Any]:
    """Analyze historical prices for forecast recommendation.
    
    Compares prices at predicted refueling time with earlier times
    to recommend optimal refueling strategy.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        predicted_refuel_date: When refueling will be needed
        current_price: Current fuel price
        
    Returns:
        Dictionary with forecast recommendation
    """
    if not predicted_refuel_date:
        return {
            "has_forecast": False,
            "reason": "No prediction available"
        }
    
    # Get historical price data
    try:
        price_history = await get_price_history(hass, entry)
        if not price_history or len(price_history) < FORECAST_MIN_HISTORY_POINTS:
            return {
                "has_forecast": False,
                "reason": "Insufficient historical data"
            }
    except Exception as err:
        _LOGGER.warning("Error loading price history for forecast: %s", err)
        return {
            "has_forecast": False,
            "reason": f"Error loading data: {err}"
        }
    
    # Get predicted weekday and hour
    predicted_weekday = predicted_refuel_date.weekday()
    predicted_hour = predicted_refuel_date.hour
    
    # Analyze historical prices by weekday
    weekday_prices = defaultdict(list)
    
    # Parse price history
    for obs in price_history:
        ts_str = obs.get("ts")
        if not ts_str:
            continue
        
        try:
            ts = dt_util.parse_datetime(ts_str)
            if not ts:
                continue
            
            price = obs.get("price")
            if price is None:
                continue
            
            weekday = ts.weekday()
            weekday_prices[weekday].append(price)
        except Exception:
            continue
    
    # Calculate average price for each weekday
    weekday_averages = {}
    for weekday in range(7):
        prices = weekday_prices[weekday]
        if prices:
            weekday_averages[weekday] = sum(prices) / len(prices)
    
    if not weekday_averages:
        return {
            "has_forecast": False,
            "reason": "No valid historical prices"
        }
    
    # Get predicted weekday average
    predicted_avg = weekday_averages.get(predicted_weekday)
    
    if predicted_avg is None:
        return {
            "has_forecast": False,
            "reason": f"No data for {WEEKDAY_NAMES[predicted_weekday]}"
        }
    
    # Find cheapest weekday in history
    cheapest_weekday = min(weekday_averages.items(), key=lambda x: x[1])
    cheapest_weekday_num = cheapest_weekday[0]
    cheapest_avg = cheapest_weekday[1]
    
    # Calculate potential savings
    price_difference = predicted_avg - cheapest_avg
    
    # Determine recommendation
    should_refuel_early = False
    urgency = "low"
    forecast_trend = "stable"
    
    # Compare current price with historical averages
    current_vs_predicted = current_price - predicted_avg
    current_vs_cheapest = current_price - cheapest_avg
    
    # Check if predicted day is significantly more expensive
    if price_difference > FORECAST_SIGNIFICANT_PRICE_DIFFERENCE:
        # Check if current price is close to historical cheapest
        if current_vs_cheapest < FORECAST_NEAR_BEST_PRICE_MARGIN:
            should_refuel_early = True
            urgency = "medium"
            forecast_trend = "favorable_now"
        # Check if cheaper day is before predicted day
        elif cheapest_weekday_num < predicted_weekday:
            should_refuel_early = True
            urgency = "low"
            forecast_trend = "favorable_earlier"
    
    # Build recommendation
    recommendation = _format_forecast_recommendation(
        predicted_weekday,
        predicted_avg,
        cheapest_weekday_num,
        cheapest_avg,
        current_price,
        should_refuel_early,
        WEEKDAY_NAMES
    )
    
    return {
        "has_forecast": True,
        "predicted_date": predicted_refuel_date.isoformat(),
        "predicted_weekday": WEEKDAY_NAMES[predicted_weekday],
        "predicted_avg_price": round(predicted_avg, 3),
        "cheapest_weekday": WEEKDAY_NAMES[cheapest_weekday_num],
        "cheapest_avg_price": round(cheapest_avg, 3),
        "current_price": round(current_price, 3),
        "price_difference": round(price_difference, 3),
        "should_refuel": should_refuel_early,
        "urgency": urgency,
        "forecast_trend": forecast_trend,
        "recommendation": recommendation,
    }


def _format_forecast_recommendation(
    predicted_weekday: int,
    predicted_avg: float,
    cheapest_weekday: int,
    cheapest_avg: float,
    current_price: float,
    should_refuel_early: bool,
    weekday_names: List[str],
) -> str:
    """Format forecast recommendation message.
    
    Args:
        predicted_weekday: Weekday number of prediction
        predicted_avg: Average price on predicted weekday
        cheapest_weekday: Weekday number with cheapest prices
        cheapest_avg: Average price on cheapest weekday
        current_price: Current fuel price
        should_refuel_early: Whether to recommend early refueling
        weekday_names: List of weekday names
        
    Returns:
        Formatted recommendation string
    """
    predicted_day = weekday_names[predicted_weekday]
    cheapest_day = weekday_names[cheapest_weekday]
    price_diff = predicted_avg - cheapest_avg
    
    if should_refuel_early:
        if current_price <= cheapest_avg + FORECAST_NEAR_HISTORICAL_BEST_MARGIN:
            return (
                f"📊 Forecast: Current price (€{current_price:.3f}) is near historical best! "
                f"{predicted_day} avg is €{predicted_avg:.3f}. Consider refueling now."
            )
        else:
            return (
                f"📊 Forecast: Prices typically cheaper on {cheapest_day} (€{cheapest_avg:.3f}) "
                f"vs {predicted_day} (€{predicted_avg:.3f}, €{price_diff:.3f} more). "
                f"Consider refueling earlier."
            )
    else:
        if price_diff < FORECAST_NEAR_HISTORICAL_BEST_MARGIN:
            return (
                f"📊 Forecast: Prices stable. {predicted_day} avg (€{predicted_avg:.3f}) "
                f"similar to other days. Refuel when convenient."
            )
        else:
            return (
                f"📊 Forecast: Monitor prices. {predicted_day} avg is €{predicted_avg:.3f}. "
                f"Historically cheapest on {cheapest_day} (€{cheapest_avg:.3f})."
            )
