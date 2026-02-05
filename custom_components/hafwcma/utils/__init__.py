"""Utility functions for haFWCMA integration."""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from ..models import FuelStation


def calculate_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate distance between two geographic coordinates using Haversine formula.
    
    Args:
        lat1: Latitude of first point in degrees
        lon1: Longitude of first point in degrees
        lat2: Latitude of second point in degrees
        lon2: Longitude of second point in degrees
        
    Returns:
        Distance in kilometers
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    # Earth radius in kilometers
    earth_radius = 6371.0

    return earth_radius * c


def find_cheapest_station(
    stations: List[FuelStation], fuel_type: str
) -> Optional[FuelStation]:
    """Find the station with the lowest price for specified fuel type.
    
    Args:
        stations: List of fuel stations to search
        fuel_type: Type of fuel to compare ('e5', 'e10', 'diesel')
        
    Returns:
        Station with lowest price or None if no stations have pricing
    """
    if not stations:
        return None

    stations_with_price = [
        s for s in stations if s.get_price(fuel_type) is not None
    ]

    if not stations_with_price:
        return None

    return min(stations_with_price, key=lambda s: s.get_price(fuel_type))


def find_best_station(
    stations: List[FuelStation],
    fuel_type: str,
    max_distance: Optional[float] = None,
    price_weight: float = 0.7,
    distance_weight: float = 0.3,
) -> Optional[FuelStation]:
    """Find the best station based on price and distance trade-off.
    
    Uses a weighted scoring system to balance low prices against
    proximity to current location.
    
    Args:
        stations: List of fuel stations to evaluate
        fuel_type: Type of fuel to compare
        max_distance: Maximum acceptable distance in km (optional)
        price_weight: Weight for price in scoring (0-1)
        distance_weight: Weight for distance in scoring (0-1)
        
    Returns:
        Best scoring station or None
    """
    if not stations:
        return None

    # Filter by distance if specified
    if max_distance is not None:
        stations = [s for s in stations if s.distance <= max_distance]

    # Filter out stations without pricing
    stations_with_price = [
        s for s in stations if s.get_price(fuel_type) is not None
    ]

    if not stations_with_price:
        return None

    # Normalize and score
    min_price = min(s.get_price(fuel_type) for s in stations_with_price)
    max_price = max(s.get_price(fuel_type) for s in stations_with_price)
    min_distance = min(s.distance for s in stations_with_price)
    max_distance = max(s.distance for s in stations_with_price)

    def score_station(station: FuelStation) -> float:
        """Calculate weighted score for a station (higher is better)."""
        price = station.get_price(fuel_type)
        
        # Normalize to 0-1 scale (inverted for price - lower is better)
        if max_price > min_price:
            price_score = 1 - (price - min_price) / (max_price - min_price)
        else:
            price_score = 1.0

        # Normalize distance (inverted - closer is better)
        if max_distance > min_distance:
            distance_score = 1 - (station.distance - min_distance) / (
                max_distance - min_distance
            )
        else:
            distance_score = 1.0

        return price_weight * price_score + distance_weight * distance_score

    return max(stations_with_price, key=score_station)


def calculate_refuel_amount(
    current_level: float, tank_capacity: float, fill_percentage: float = 100.0
) -> float:
    """Calculate amount of fuel needed to reach target fill level.
    
    Args:
        current_level: Current fuel level in liters
        tank_capacity: Total tank capacity in liters
        fill_percentage: Target fill percentage (0-100)
        
    Returns:
        Amount to refuel in liters
    """
    target_level = tank_capacity * (fill_percentage / 100.0)
    refuel_amount = max(0, target_level - current_level)
    return refuel_amount


def estimate_fuel_cost(
    amount: float, price_per_liter: float
) -> Tuple[float, float]:
    """Estimate total cost and potential savings.
    
    Args:
        amount: Amount of fuel in liters
        price_per_liter: Price per liter
        
    Returns:
        Tuple of (total_cost, rounded_cost)
    """
    total_cost = amount * price_per_liter
    rounded_cost = round(total_cost, 2)
    return total_cost, rounded_cost


def is_within_operating_hours(
    current_time: Optional[datetime] = None,
    open_hour: int = 6,
    close_hour: int = 22,
) -> bool:
    """Check if current time is within typical gas station operating hours.
    
    Args:
        current_time: Time to check (uses now if None)
        open_hour: Opening hour (0-23)
        close_hour: Closing hour (0-23)
        
    Returns:
        True if within operating hours
    """
    if current_time is None:
        current_time = datetime.now()

    current_hour = current_time.hour
    return open_hour <= current_hour < close_hour


def format_currency(amount: float, currency: str = "EUR") -> str:
    """Format amount as currency string.
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    if currency == "EUR":
        return f"€{amount:.2f}"
    return f"{amount:.2f} {currency}"


def format_fuel_price(price: float, currency: str = "EUR") -> str:
    """Format fuel price per liter.
    
    Args:
        price: Price per liter
        currency: Currency code
        
    Returns:
        Formatted price string
    """
    if currency == "EUR":
        return f"€{price:.3f}/L"
    return f"{price:.3f} {currency}/L"
