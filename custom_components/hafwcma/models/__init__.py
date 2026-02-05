"""Data models for haFWCMA integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FuelStation:
    """Represents a fuel station with pricing information.
    
    Attributes:
        station_id: Unique identifier for the station
        name: Station name
        brand: Station brand/chain
        address: Street address
        city: City name
        latitude: Geographic latitude
        longitude: Geographic longitude
        distance: Distance from reference point in km
        price_e5: Price for E5 fuel in EUR
        price_e10: Price for E10 fuel in EUR
        price_diesel: Price for Diesel fuel in EUR
        is_open: Whether station is currently open
        last_updated: Timestamp of last price update
    """

    station_id: str
    name: str
    brand: str
    address: str
    city: str
    latitude: float
    longitude: float
    distance: float
    price_e5: Optional[float] = None
    price_e10: Optional[float] = None
    price_diesel: Optional[float] = None
    is_open: bool = True
    last_updated: Optional[datetime] = None

    def get_price(self, fuel_type: str) -> Optional[float]:
        """Get price for specified fuel type.
        
        Args:
            fuel_type: One of 'e5', 'e10', 'diesel'
            
        Returns:
            Price in EUR or None if not available
        """
        if fuel_type == "e5":
            return self.price_e5
        elif fuel_type == "e10":
            return self.price_e10
        elif fuel_type == "diesel":
            return self.price_diesel
        return None


@dataclass
class Vehicle:
    """Represents a vehicle with fuel management data.
    
    Attributes:
        name: Vehicle name/identifier
        tank_capacity: Total tank capacity in liters
        current_level: Current fuel level in liters
        fuel_type: Type of fuel used (e5, e10, diesel)
        consumption_rate: Average consumption in L/100km
        last_refuel_date: Date of last refueling
        last_refuel_amount: Amount refueled in liters
        last_refuel_price: Price per liter at last refuel
        odometer: Current odometer reading in km
    """

    name: str
    tank_capacity: float
    fuel_type: str
    current_level: Optional[float] = None
    consumption_rate: Optional[float] = None
    last_refuel_date: Optional[datetime] = None
    last_refuel_amount: Optional[float] = None
    last_refuel_price: Optional[float] = None
    odometer: Optional[float] = None

    @property
    def tank_percentage(self) -> Optional[float]:
        """Calculate current tank fill percentage.
        
        Returns:
            Percentage (0-100) or None if level unknown
        """
        if self.current_level is None:
            return None
        return (self.current_level / self.tank_capacity) * 100

    @property
    def estimated_range(self) -> Optional[float]:
        """Estimate remaining range in km.
        
        Returns:
            Estimated range in km or None if cannot calculate
        """
        if self.current_level is None or self.consumption_rate is None:
            return None
        return (self.current_level / self.consumption_rate) * 100


@dataclass
class FuelForecast:
    """Represents fuel price forecast data.
    
    Attributes:
        fuel_type: Type of fuel
        current_price: Current average price
        predicted_trend: Predicted trend ('rising', 'falling', 'stable')
        confidence: Forecast confidence level (0-1)
        recommendation: Recommendation text
        best_time_to_refuel: Recommended time to refuel
        forecast_period_hours: Forecast period in hours
    """

    fuel_type: str
    current_price: float
    predicted_trend: str
    confidence: float = 0.5
    recommendation: str = ""
    best_time_to_refuel: Optional[datetime] = None
    forecast_period_hours: int = 24


@dataclass
class RefuelRecommendation:
    """Represents a refueling recommendation.
    
    Attributes:
        vehicle: Vehicle name
        should_refuel_now: Whether to refuel now
        recommended_station: Best station to use
        estimated_savings: Potential savings compared to average
        reasoning: Explanation of recommendation
        urgency: Urgency level ('low', 'medium', 'high')
        timestamp: When recommendation was generated
    """

    vehicle: str
    should_refuel_now: bool
    recommended_station: Optional[FuelStation] = None
    estimated_savings: float = 0.0
    reasoning: str = ""
    urgency: str = "low"
    timestamp: Optional[datetime] = None
