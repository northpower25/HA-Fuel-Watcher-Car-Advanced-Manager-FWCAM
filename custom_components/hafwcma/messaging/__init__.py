"""Messaging module for haFWCMA integration."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

_LOGGER = logging.getLogger(__name__)


class MessageService(ABC):
    """Abstract base class for messaging services.
    
    Defines the interface for sending notifications about fuel prices,
    tank levels, and refueling recommendations.
    """

    @abstractmethod
    async def send_message(self, message: str, **kwargs) -> bool:
        """Send a text message.
        
        Args:
            message: Message text to send
            **kwargs: Additional service-specific parameters
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        pass

    @abstractmethod
    async def send_price_alert(
        self,
        station_name: str,
        price: float,
        fuel_type: str,
        **kwargs
    ) -> bool:
        """Send fuel price alert notification.
        
        Args:
            station_name: Name of the fuel station
            price: Current price per liter
            fuel_type: Type of fuel
            **kwargs: Additional parameters
            
        Returns:
            True if sent successfully
        """
        pass

    @abstractmethod
    async def send_refuel_recommendation(
        self,
        vehicle_name: str,
        should_refuel: bool,
        reasoning: str,
        **kwargs
    ) -> bool:
        """Send refueling recommendation.
        
        Args:
            vehicle_name: Name of the vehicle
            should_refuel: Whether to refuel now
            reasoning: Explanation of the recommendation
            **kwargs: Additional parameters
            
        Returns:
            True if sent successfully
        """
        pass


class MessagingError(Exception):
    """Exception raised when messaging operation fails."""

    pass
