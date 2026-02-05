"""Telegram notification service for haFWCMA."""
from __future__ import annotations

import logging
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError

from . import MessageService, MessagingError

_LOGGER = logging.getLogger(__name__)


class TelegramNotifier(MessageService):
    """Telegram notification service implementation.
    
    Sends notifications about fuel prices, tank status, and recommendations
    via Telegram bot.
    
    Attributes:
        bot: Telegram Bot instance
        chat_id: Default chat ID for messages
    """

    def __init__(self, bot_token: str, chat_id: str) -> None:
        """Initialize Telegram notifier.
        
        Args:
            bot_token: Telegram bot token
            chat_id: Chat ID to send messages to
        """
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id

    async def send_message(self, message: str, **kwargs) -> bool:
        """Send a text message via Telegram.
        
        Args:
            message: Message text to send
            **kwargs: Additional Telegram-specific parameters
                - chat_id: Override default chat ID
                - parse_mode: Message parse mode (HTML, Markdown)
                
        Returns:
            True if message was sent successfully
            
        Raises:
            MessagingError: If sending fails
        """
        chat_id = kwargs.get("chat_id", self.chat_id)
        parse_mode = kwargs.get("parse_mode", None)

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode,
            )
            _LOGGER.debug("Telegram message sent successfully")
            return True

        except TelegramError as err:
            _LOGGER.error("Failed to send Telegram message: %s", err)
            raise MessagingError(f"Telegram error: {err}") from err

    async def send_price_alert(
        self,
        station_name: str,
        price: float,
        fuel_type: str,
        **kwargs
    ) -> bool:
        """Send fuel price alert via Telegram.
        
        Args:
            station_name: Name of the fuel station
            price: Current price per liter
            fuel_type: Type of fuel (e5, e10, diesel)
            **kwargs: Additional parameters
            
        Returns:
            True if sent successfully
        """
        fuel_emoji = {
            "e5": "⛽",
            "e10": "⛽",
            "diesel": "🚛",
        }.get(fuel_type, "⛽")

        message = (
            f"{fuel_emoji} <b>Fuel Price Alert</b>\n\n"
            f"Station: {station_name}\n"
            f"Fuel Type: {fuel_type.upper()}\n"
            f"Price: €{price:.3f}/L\n"
        )

        return await self.send_message(message, parse_mode="HTML", **kwargs)

    async def send_refuel_recommendation(
        self,
        vehicle_name: str,
        should_refuel: bool,
        reasoning: str,
        **kwargs
    ) -> bool:
        """Send refueling recommendation via Telegram.
        
        Args:
            vehicle_name: Name of the vehicle
            should_refuel: Whether to refuel now
            reasoning: Explanation of the recommendation
            **kwargs: Additional parameters
                - station_name: Recommended station name
                - price: Current price
                - savings: Estimated savings
                
        Returns:
            True if sent successfully
        """
        if should_refuel:
            emoji = "✅"
            action = "REFUEL NOW"
        else:
            emoji = "⏸️"
            action = "WAIT"

        message = (
            f"{emoji} <b>Refuel Recommendation</b>\n\n"
            f"Vehicle: {vehicle_name}\n"
            f"Action: <b>{action}</b>\n\n"
            f"Reason: {reasoning}\n"
        )

        if "station_name" in kwargs:
            message += f"\nRecommended Station: {kwargs['station_name']}\n"

        if "price" in kwargs:
            message += f"Price: €{kwargs['price']:.3f}/L\n"

        if "savings" in kwargs:
            message += f"Potential Savings: €{kwargs['savings']:.2f}\n"

        return await self.send_message(message, parse_mode="HTML", **kwargs)

    async def send_tank_low_alert(
        self,
        vehicle_name: str,
        tank_level: float,
        range_km: float,
        **kwargs
    ) -> bool:
        """Send low tank level alert.
        
        Args:
            vehicle_name: Name of the vehicle
            tank_level: Current tank level in liters
            range_km: Estimated remaining range
            **kwargs: Additional parameters
            
        Returns:
            True if sent successfully
        """
        message = (
            f"⚠️ <b>Low Tank Alert</b>\n\n"
            f"Vehicle: {vehicle_name}\n"
            f"Tank Level: {tank_level:.1f}L\n"
            f"Estimated Range: {range_km:.0f} km\n\n"
            f"Consider refueling soon."
        )

        return await self.send_message(message, parse_mode="HTML", **kwargs)
