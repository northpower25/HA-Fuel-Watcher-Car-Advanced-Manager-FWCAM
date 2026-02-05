"""Base provider interface for fuel price providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..models import FuelStation


class FuelPriceProvider(ABC):
    """Abstract base class for fuel price providers.
    
    This interface defines the contract that all fuel price providers
    must implement to be compatible with haFWCMA.
    """

    @abstractmethod
    async def get_stations_nearby(
        self,
        latitude: float,
        longitude: float,
        radius: float,
        fuel_type: str,
    ) -> List[FuelStation]:
        """Get fuel stations near a location.
        
        Args:
            latitude: Geographic latitude
            longitude: Geographic longitude
            radius: Search radius in kilometers
            fuel_type: Type of fuel to search for
            
        Returns:
            List of fuel stations with pricing
            
        Raises:
            ProviderError: If API request fails
        """
        pass

    @abstractmethod
    async def get_station_details(self, station_id: str) -> FuelStation:
        """Get detailed information for a specific station.
        
        Args:
            station_id: Unique station identifier
            
        Returns:
            Detailed station information
            
        Raises:
            ProviderError: If API request fails
        """
        pass

    @abstractmethod
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate API key with provider.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass


class ProviderError(Exception):
    """Exception raised when provider encounters an error."""

    pass
