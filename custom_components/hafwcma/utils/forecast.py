"""Forecast utilities for fuel price prediction."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from homeassistant.util import dt as dt_util

from ..models import FuelForecast

_LOGGER = logging.getLogger(__name__)


class FuelPriceForecaster:
    """Simple fuel price forecasting engine.
    
    Provides basic trend analysis and recommendations based on
    historical price data and patterns.
    
    TODO: Implement more sophisticated forecasting algorithms
    TODO: Add machine learning models for better predictions
    TODO: Integrate external price trend APIs
    """

    def __init__(self) -> None:
        """Initialize forecaster."""
        self.price_history: Dict[str, List[tuple[datetime, float]]] = {}

    def add_price_observation(
        self, fuel_type: str, price: float, timestamp: Optional[datetime] = None
    ) -> None:
        """Add a price observation to history.
        
        Args:
            fuel_type: Type of fuel
            price: Price per liter
            timestamp: Time of observation (uses now if None)
        """
        if timestamp is None:
            timestamp = dt_util.now()

        if fuel_type not in self.price_history:
            self.price_history[fuel_type] = []

        self.price_history[fuel_type].append((timestamp, price))

        # Keep only last 30 days of data
        cutoff_date = dt_util.now() - timedelta(days=30)
        self.price_history[fuel_type] = [
            (ts, p) for ts, p in self.price_history[fuel_type] if ts > cutoff_date
        ]

    def predict_trend(
        self, fuel_type: str, lookback_hours: int = 24
    ) -> FuelForecast:
        """Predict fuel price trend.
        
        Args:
            fuel_type: Type of fuel to forecast
            lookback_hours: Hours of historical data to consider
            
        Returns:
            Forecast with trend prediction
        """
        if fuel_type not in self.price_history:
            _LOGGER.warning("No price history for %s", fuel_type)
            return FuelForecast(
                fuel_type=fuel_type,
                current_price=0.0,
                predicted_trend="unknown",
                confidence=0.0,
                recommendation="Insufficient data for forecast",
            )

        history = self.price_history[fuel_type]
        if len(history) < 2:
            current_price = history[-1][1] if history else 0.0
            return FuelForecast(
                fuel_type=fuel_type,
                current_price=current_price,
                predicted_trend="unknown",
                confidence=0.0,
                recommendation="Need more data points for forecast",
            )

        # Filter to lookback period
        cutoff_time = dt_util.now() - timedelta(hours=lookback_hours)
        recent_history = [(ts, p) for ts, p in history if ts > cutoff_time]

        if len(recent_history) < 2:
            recent_history = history[-10:]  # Use last 10 points as fallback

        # Calculate trend
        prices = [p for _, p in recent_history]
        current_price = prices[-1]
        avg_price = sum(prices) / len(prices)

        # Simple linear trend
        price_change = prices[-1] - prices[0]
        trend_threshold = 0.01  # 1 cent threshold

        if price_change > trend_threshold:
            trend = "rising"
            recommendation = "Consider refueling soon - prices are rising"
        elif price_change < -trend_threshold:
            trend = "falling"
            recommendation = "Wait if possible - prices are falling"
        else:
            trend = "stable"
            recommendation = "Prices are stable - refuel as needed"

        # Calculate confidence based on data consistency
        price_variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
        confidence = min(1.0, 1.0 / (1.0 + price_variance * 10))

        return FuelForecast(
            fuel_type=fuel_type,
            current_price=current_price,
            predicted_trend=trend,
            confidence=confidence,
            recommendation=recommendation,
            forecast_period_hours=24,
        )

    def should_refuel_now(
        self,
        fuel_type: str,
        tank_percentage: float,
        urgency_threshold: float = 25.0,
    ) -> tuple[bool, str]:
        """Determine if vehicle should refuel now.
        
        Args:
            fuel_type: Type of fuel
            tank_percentage: Current tank fill percentage
            urgency_threshold: Percentage below which refueling is urgent
            
        Returns:
            Tuple of (should_refuel, reasoning)
        """
        # Check tank level urgency
        if tank_percentage < urgency_threshold:
            return True, f"Tank level critical ({tank_percentage:.1f}%)"

        # Get price forecast
        forecast = self.predict_trend(fuel_type)

        if forecast.predicted_trend == "rising":
            if tank_percentage < 50:
                return True, "Prices rising and tank below half - refuel now"
            else:
                return False, "Prices rising but tank adequate - monitor closely"

        elif forecast.predicted_trend == "falling":
            if tank_percentage < 30:
                return True, "Tank getting low - refuel despite falling prices"
            else:
                return False, "Prices falling - wait for better rates"

        else:  # stable or unknown
            if tank_percentage < 40:
                return True, "Tank below 40% - refuel at convenience"
            else:
                return False, "Tank adequate - no urgent need to refuel"

    def clear_history(self, fuel_type: Optional[str] = None) -> None:
        """Clear price history.
        
        Args:
            fuel_type: Specific fuel type to clear (clears all if None)
        """
        if fuel_type is None:
            self.price_history.clear()
        elif fuel_type in self.price_history:
            del self.price_history[fuel_type]
