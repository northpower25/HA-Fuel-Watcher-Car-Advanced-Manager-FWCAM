"""Telegram notification service for haFWCMA."""
from __future__ import annotations

import html
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
        # Track which API error components have already been notified this trip
        self._reported_errors: set[str] = set()

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
            f"Station: {html.escape(str(station_name))}\n"
            f"Fuel Type: {html.escape(str(fuel_type).upper())}\n"
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
            f"Vehicle: {html.escape(str(vehicle_name))}\n"
            f"Action: <b>{action}</b>\n\n"
            f"Reason: {html.escape(str(reasoning))}\n"
        )

        if "station_name" in kwargs:
            message += f"\nRecommended Station: {html.escape(str(kwargs['station_name']))}\n"

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
            f"Vehicle: {html.escape(str(vehicle_name))}\n"
            f"Tank Level: {tank_level:.1f}L\n"
            f"Estimated Range: {range_km:.0f} km\n\n"
            f"Consider refueling soon."
        )

        return await self.send_message(message, parse_mode="html", **kwargs)

    async def send_route_started(
        self,
        destination: str,
        total_distance_km: float | None,
        predicted_stop_km: float | None,
        best_station: dict | None,
        top_stations: list[dict],
        corridor_km: float = 5,
        safety_buffer_pct: float = 15,
    ) -> bool:
        """Send a route-started notification matching the concept doc format.

        Resets the per-trip error deduplication set so that each new route
        starts with a clean slate.

        Args:
            destination: Human-readable destination string.
            total_distance_km: Total route distance in km, or None.
            predicted_stop_km: Distance to predicted fuel stop in km, or None.
            best_station: Best corridor station dict (may be None on route start).
            top_stations: List of top corridor station dicts.
            corridor_km: Corridor half-width in km.
            safety_buffer_pct: Fuel safety buffer percentage.

        Returns:
            True if the message was sent successfully.
        """
        self._reported_errors = set()

        dist_str = f"{total_distance_km:.0f} km" if total_distance_km is not None else "?"
        lines = [
            "🗺️ <b>Route aktiviert!</b>",
            f"📍 Ziel: <b>{html.escape(destination)}</b> ({dist_str})",
        ]

        if predicted_stop_km is not None:
            lines.append(f"⛽ Prognose Tankstopp bei: ~{predicted_stop_km:.0f} km")

        if best_station:
            nav = best_station.get("navigation_urls") or {}
            lines += [
                "",
                "🏆 <b>Empfohlene Tankstelle im Korridor:</b>",
                f"   {html.escape(str(best_station.get('name', 'N/A')))}",
                f"   💰 {best_station.get('price', 'N/A')} €/l",
                f"   📏 Umweg: {best_station.get('detour_km', 0)} km",
                f"   💶 Effektiver Preis: {best_station.get('effective_price_eur_per_l', 'N/A')} €/l (inkl. Umweg)",
            ]
            google_url = nav.get("google_maps")
            if google_url:
                lines.append(f"   🗺️ <a href=\"{google_url}\">Google Maps</a>")

        if top_stations:
            lines += ["", "📋 <b>Weitere Optionen im Korridor:</b>"]
            for i, st in enumerate(top_stations[1:3], start=2):
                detour = st.get("detour_km", 0)
                detour_str = f"{detour} km Umweg" if detour else "direkt an Route"
                lines.append(
                    f"   {i}. {html.escape(str(st.get('name', 'N/A')))} – "
                    f"{st.get('price', 'N/A')} €/l ({detour_str})"
                )

        lines += [
            "",
            f"⚙️ Korridor: {corridor_km} km | Sicherheitspuffer: {safety_buffer_pct}%",
        ]

        return await self.send_message("\n".join(lines), parse_mode="html")

    async def send_cheaper_station_alert(
        self,
        new_station: dict,
        old_price: float,
        distance_to_station_km: float | None,
        savings_40l: float | None,
        fuel_type: str = "E10",
    ) -> bool:
        """Send a notification when a cheaper corridor station is found.

        Args:
            new_station: New (cheaper) station dict with price, name, etc.
            old_price: Previous best station price per litre.
            distance_to_station_km: Approximate distance ahead to new station.
            savings_40l: Estimated savings for a 40 L fill-up.
            fuel_type: Fuel type label (default "E10").

        Returns:
            True if sent successfully.
        """
        nav = new_station.get("navigation_urls") or {}
        new_price = new_station.get("price", 0)
        delta = old_price - new_price
        detour_km = new_station.get("detour_km", 0)
        eff_price = new_station.get("effective_price_eur_per_l", new_price)

        lines = [
            "💡 <b>Günstigere Tankstelle im Korridor!</b>",
            "",
            f"NEU: <b>{html.escape(str(new_station.get('name', 'N/A')))}</b>",
            f"   💰 {fuel_type}: {new_price:.3f} €/l (↓ {delta:.3f} €/l günstiger!)",
            f"   📏 Umweg: {detour_km} km",
            f"   💶 Effektiv: {eff_price:.3f} €/l",
        ]
        if distance_to_station_km is not None:
            lines.append(f"   📍 Liegt in ~{distance_to_station_km:.0f} km")
        nav_parts = []
        if nav.get("google_maps"):
            nav_parts.append(f"<a href=\"{nav['google_maps']}\">Google Maps</a>")
        if nav.get("waze"):
            nav_parts.append(f"<a href=\"{nav['waze']}\">Waze</a>")
        if nav.get("apple_maps"):
            nav_parts.append(f"<a href=\"{nav['apple_maps']}\">Apple Maps</a>")
        if nav_parts:
            lines.append(f"   🗺️ {' | '.join(nav_parts)}")

        lines += [
            "",
            f"Bisherige Empfehlung: {old_price:.3f} €/l",
        ]
        if savings_40l is not None:
            lines.append(f"Ersparnis für Volltankung (40 L): ~{savings_40l:.2f} €")

        return await self.send_message("\n".join(lines), parse_mode="html")

    async def send_range_warning(
        self,
        range_km: float,
        nearest_recommended_station: dict | None,
        fuel_type: str = "E10",
    ) -> bool:
        """Send a low-range warning notification.

        Args:
            range_km: Estimated remaining range in km.
            nearest_recommended_station: Nearest station to refuel at (may be None).
            fuel_type: Fuel type label.

        Returns:
            True if sent successfully.
        """
        lines = [
            "⚠️ <b>Reichweitenwarnung!</b>",
            f"Tank reicht noch für ~{range_km:.0f} km.",
        ]

        if nearest_recommended_station:
            nav = nearest_recommended_station.get("navigation_urls") or {}
            detour_km = nearest_recommended_station.get("detour_km", 0)
            price = nearest_recommended_station.get("price", "N/A")
            name = nearest_recommended_station.get("name", "N/A")
            dist_ahead = nearest_recommended_station.get("distance_km", "?")
            lines += [
                f"Nächste empfohlene Tankstelle: {dist_ahead} km entfernt.",
                "",
                f"JETZT TANKEN: <b>{html.escape(str(name))}</b>",
                f"   💰 {fuel_type}: {price} €/l | 📏 {detour_km} km Umweg",
            ]
            if nav.get("google_maps"):
                lines.append(f"   🗺️ <a href=\"{nav['google_maps']}\">Google Maps</a>")

        return await self.send_message("\n".join(lines), parse_mode="html")

    async def send_route_api_error(
        self,
        component: str,
        error_message: str,
    ) -> bool:
        """Send an API error notification – at most once per component per trip.

        Uses ``_reported_errors`` to deduplicate: if the same *component* has
        already been reported during this trip the message is suppressed and
        ``False`` is returned without sending.

        Calling :meth:`send_route_started` resets the deduplication set so
        that a new trip starts clean.

        Args:
            component: Component/provider that failed (e.g. "OSRM", "TankerKönig").
            error_message: Human-readable error description.

        Returns:
            True if the message was sent, False if suppressed or on error.
        """
        if component in self._reported_errors:
            _LOGGER.debug(
                "Suppressing duplicate API error notification for component '%s'", component
            )
            return False

        self._reported_errors.add(component)
        message = (
            f"⚠️ <b>Route Planner – API Error</b>\n\n"
            f"Component: <code>{html.escape(component)}</code>\n"
            f"Error: {html.escape(error_message)}"
        )
        return await self.send_message(message, parse_mode="html")
