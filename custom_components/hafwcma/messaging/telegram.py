"""Telegram notification service for haFWCMA."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from telegram import Bot
from telegram.error import TelegramError

from . import MessageService, MessagingError
from ..const import TELEGRAM_METHOD_INTEGRATION, TELEGRAM_METHOD_DIRECT_API

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class TelegramNotifier(MessageService):
    """Telegram notification service implementation.
    
    Sends notifications about fuel prices, tank status, and recommendations
    via Telegram. Uses Home Assistant's telegram_bot service if available,
    otherwise falls back to direct bot usage.
    
    Attributes:
        hass: Home Assistant instance (optional, for using HA's telegram_bot service)
        bot: Telegram Bot instance (fallback for direct usage)
        chat_id: Default chat ID for messages
    """

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        hass: HomeAssistant | None = None,
    ) -> None:
        """Initialize Telegram notifier.
        
        Args:
            bot_token: Telegram bot token
            chat_id: Chat ID to send messages to
            hass: Home Assistant instance (optional, for using HA's service)
        """
        self.hass = hass
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id
        self._use_ha_service = (
            hass is not None and "telegram_bot" in hass.config.components
        )
        
        # Store which method is being used
        self.telegram_method = (
            TELEGRAM_METHOD_INTEGRATION if self._use_ha_service else TELEGRAM_METHOD_DIRECT_API
        )
        
        if self._use_ha_service:
            _LOGGER.info(
                "TelegramNotifier using Home Assistant's telegram_bot service (bidirectional communication available)"
            )
        else:
            _LOGGER.info(
                "TelegramNotifier using direct bot API (one-way notifications only - telegram_bot integration not found)"
            )

    async def send_message(self, message: str, **kwargs) -> bool:
        """Send a text message via Telegram.
        
        Uses Home Assistant's telegram_bot service if available,
        otherwise uses direct bot API.
        
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
        parse_mode = kwargs.get("parse_mode", "html")

        try:
            if self._use_ha_service and self.hass:
                # Use Home Assistant's telegram_bot service
                await self.hass.services.async_call(
                    "telegram_bot",
                    "send_message",
                    {
                        "target": chat_id,
                        "message": message,
                        "parse_mode": parse_mode,
                    },
                    blocking=True,
                )
            else:
                # Fallback to direct bot API
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
        except Exception as err:
            _LOGGER.error("Failed to send Telegram message: %s", err)
            raise MessagingError(f"Error: {err}") from err

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

        return await self.send_message(message, parse_mode="html", **kwargs)

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

        return await self.send_message(message, parse_mode="html", **kwargs)

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

        return await self.send_message(message, parse_mode="html", **kwargs)
