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
        self._bot_token = bot_token
        self._bot: Bot | None = None  # Lazy initialisation avoids blocking SSL setup
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

    @property
    def bot(self) -> "Bot | None":
        """Return the cached Telegram Bot instance, or ``None`` if not yet created.

        Prefer :meth:`_ensure_bot` (async) for all sending code so that Bot
        initialisation is deferred to a worker thread and never blocks the HA
        event loop.  This property exists only for read-only introspection
        (e.g. testing or diagnostics).
        """
        return self._bot

    async def _ensure_bot(self) -> "Bot":
        """Return (or create) the Telegram Bot instance asynchronously.

        Creates the Bot in an executor thread when HA is available to avoid
        blocking the event loop with the ``ssl.load_verify_locations`` call
        that ``python-telegram-bot`` makes during SSL context initialisation.
        """
        if self._bot is None:
            if self.hass is not None:
                self._bot = await self.hass.async_add_executor_job(
                    lambda: Bot(token=self._bot_token)
                )
            else:
                self._bot = Bot(token=self._bot_token)
        return self._bot

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
                bot = await self._ensure_bot()
                await bot.send_message(
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
        best_station: dict | None = None,
        top_stations: list[dict] | None = None,
        corridor_km: float = 5,
        safety_buffer_pct: float = 15,
        categorized_stations: dict | None = None,
        departure_time: str | None = None,
        eta_at_stop: str | None = None,
        abroad_fuel_stop: bool = False,
        fuel_type: str = "E5",
        no_refuel_needed: bool = False,
    ) -> bool:
        """Send a route-started notification with 3-category station recommendations.

        Resets the per-trip error deduplication set so that each new route
        starts with a clean slate.

        Args:
            destination: Human-readable destination string.
            total_distance_km: Total route distance in km, or None.
            predicted_stop_km: Distance to predicted fuel stop in km, or None.
            best_station: Deprecated – best corridor station dict (kept for
                backwards compatibility; ignored when *categorized_stations* is
                provided).
            top_stations: Deprecated – list of top corridor station dicts (kept
                for backwards compatibility).
            corridor_km: Corridor half-width in km.
            safety_buffer_pct: Fuel safety buffer percentage.
            categorized_stations: Dict with keys ``"cheapest"``, ``"nearest"``,
                ``"middle"`` – each value is a station dict or ``None``.
            departure_time: Human-readable departure time string (e.g. "08:30").
            eta_at_stop: Estimated arrival time string at fuel stop (e.g. "10:45").
            abroad_fuel_stop: When ``True`` the predicted stop is outside Germany;
                station blocks are formatted without price information and use
                OSM-sourced data.
            fuel_type: Fuel type label shown in the header (e.g. "E5", "E10", "Diesel").
            no_refuel_needed: When ``True`` the full tank is sufficient for the
                entire route; a notice is shown instead of station blocks.

        Returns:
            True if the message was sent successfully.
        """
        self._reported_errors = set()

        dist_str = f"{total_distance_km:.0f} km" if total_distance_km is not None else "?"
        fuel_label = html.escape(fuel_type.upper())
        lines = [
            f"⛽️ <b>Günstigste {fuel_label}-Tankstellen entlang der Route</b>",
            f"📍 Umkreis: {corridor_km} km | Nur geöffnete Stationen",
            f"📍 Ziel: <b>{html.escape(destination)}</b> ({dist_str})",
        ]

        if departure_time:
            lines.append(f"🕐 Abfahrt: <b>{html.escape(departure_time)}</b>")
        if predicted_stop_km is not None:
            stop_line = f"⛽️ Prognose Tankstopp bei: ~{predicted_stop_km:.0f} km"
            if eta_at_stop:
                stop_line += f" (~{html.escape(eta_at_stop)} Uhr)"
            lines.append(stop_line)

        # ── 3-category station recommendations ──────────────────────────────
        cats = categorized_stations or {}
        cheapest = cats.get("cheapest")
        nearest = cats.get("nearest")
        middle = cats.get("middle")

        # Fall back to legacy best_station / top_stations when no categories set
        if not cats:
            cheapest = best_station
            nearest = (top_stations or [])[1] if (top_stations and len(top_stations) > 1) else None
            middle = (top_stations or [])[2] if (top_stations and len(top_stations) > 2) else None

        def _fmt_station_block(number: int, label: str, station: dict, ftype: str) -> list[str]:
            nav = station.get("navigation_urls") or {}
            price = station.get("price")
            detour = station.get("road_detour_km") or station.get("detour_km", 0)
            eff = station.get("effective_price_eur_per_l")
            opening_hours = station.get("opening_hours", "")
            is_osm = station.get("source") == "osm"

            name = station.get("name", "N/A")
            city = station.get("city", "")
            street = station.get("street", "")
            address = station.get("address", "")
            if city and street:
                name_line = f"{html.escape(name)}, {html.escape(city)}, {html.escape(street)}"
            elif address:
                name_line = f"{html.escape(name)}, {html.escape(address)}"
            else:
                name_line = html.escape(name)

            block = [
                "",
                f"{number}. <b>{name_line}</b> ({html.escape(label)})",
            ]
            if not is_osm and price is not None:
                block.append(f"   💰 {html.escape(ftype.upper())}: {price} €/l")
                block.append(f"   📏 Streckenumweg: {detour} km")
                if eff is not None:
                    block.append(f"   💶 Effektiv: {eff} €/l (inkl. Umweg)")
            else:
                block.append(f"   📏 Streckenumweg: {detour} km")
            if opening_hours:
                block.append(f"   🕒 Öffnungszeiten: {html.escape(str(opening_hours))}")
            nav_parts = []
            if nav.get("google_maps"):
                nav_parts.append(f"<a href=\"{nav['google_maps']}\">Google Maps</a>")
            if nav.get("apple_maps"):
                nav_parts.append(f"<a href=\"{nav['apple_maps']}\">Apple Maps</a>")
            if nav.get("waze"):
                nav_parts.append(f"<a href=\"{nav['waze']}\">Waze</a>")
            if nav_parts:
                block.append(f"   🗺️ {' | '.join(nav_parts)}")
            return block

        if no_refuel_needed:
            lines += [
                "",
                "✅ <b>Voraussichtlich keine Betankung erforderlich</b>",
                "ℹ️ Bei einem vollen Tank bei Routenstart reicht der Kraftstoff "
                "voraussichtlich für die gesamte Strecke.",
            ]
        elif abroad_fuel_stop:
            # International stop: show up to 3 nearest OSM stations without price
            if nearest:
                lines.append("")
                lines.append("🌍 <b>Tankstellen im Ausland (keine Preisinfo verfügbar)</b>")
                lines += _fmt_station_block(1, "Nächste Tankstelle", nearest, fuel_type)
            if middle:
                lines += _fmt_station_block(2, "Nächste Tankstelle", middle, fuel_type)
            if cheapest:
                lines += _fmt_station_block(3, "Nächste Tankstelle", cheapest, fuel_type)
        else:
            if cheapest:
                lines += _fmt_station_block(1, "Preis Günstigste Tankstelle", cheapest, fuel_type)
            if nearest:
                lines += _fmt_station_block(2, "Strecke günstigste Tankstelle", nearest, fuel_type)
            if middle:
                lines += _fmt_station_block(3, "Kompromiss aus Preis/Strecke", middle, fuel_type)

        lines += [
            "",
            f"⚙️ Korridor: {corridor_km} km | Sicherheitspuffer: {safety_buffer_pct}%",
        ]

        return await self.send_message("\n".join(lines), parse_mode="html")

    async def send_route_update(
        self,
        destination: str,
        total_distance_km: float | None,
        predicted_stop_km: float | None,
        categorized_stations: dict | None = None,
        corridor_km: float = 5,
        fuel_type: str = "E5",
        current_time: str | None = None,
        eta_at_stop: str | None = None,
        abroad_fuel_stop: bool = False,
    ) -> bool:
        """Send a during-trip route update notification with station recommendations.

        Args:
            destination: Human-readable destination string.
            total_distance_km: Total route distance in km, or None.
            predicted_stop_km: Updated distance to predicted fuel stop in km, or None.
            categorized_stations: Dict with keys ``"cheapest"``, ``"nearest"``,
                ``"middle"`` – each value is a station dict or ``None``.
            corridor_km: Corridor half-width in km.
            fuel_type: Fuel type label (e.g. "E5", "E10", "Diesel").
            current_time: Current time string for display (e.g. "14:30").
            eta_at_stop: Estimated arrival time string at fuel stop.
            abroad_fuel_stop: When ``True`` the predicted stop is outside Germany.

        Returns:
            True if the message was sent successfully.
        """
        dist_str = f"{total_distance_km:.0f} km" if total_distance_km is not None else "?"
        fuel_label = html.escape(fuel_type.upper())
        lines = [
            f"⛽️ <b>Günstigste {fuel_label}-Tankstellen entlang der Route</b>",
            f"📍 Umkreis: {corridor_km} km | Nur geöffnete Stationen",
            f"📍 Ziel: <b>{html.escape(destination)}</b> ({dist_str})",
        ]

        if current_time:
            lines.append(f"🕐 Aktuelle Zeit: <b>{html.escape(current_time)}</b>")
        if predicted_stop_km is not None:
            stop_line = f"⛽️ Prognose Tankstopp bei: ~{predicted_stop_km:.0f} km"
            if eta_at_stop:
                stop_line += f" (~{html.escape(eta_at_stop)} Uhr)"
            lines.append(stop_line)

        cats = categorized_stations or {}
        cheapest = cats.get("cheapest")
        nearest = cats.get("nearest")
        middle = cats.get("middle")

        def _fmt_block(number: int, label: str, station: dict, ftype: str) -> list[str]:
            nav = station.get("navigation_urls") or {}
            price = station.get("price")
            detour = station.get("road_detour_km") or station.get("detour_km", 0)
            eff = station.get("effective_price_eur_per_l")
            opening_hours = station.get("opening_hours", "")
            is_osm = station.get("source") == "osm"

            name = station.get("name", "N/A")
            city = station.get("city", "")
            street = station.get("street", "")
            address = station.get("address", "")
            if city and street:
                name_line = f"{html.escape(name)}, {html.escape(city)}, {html.escape(street)}"
            elif address:
                name_line = f"{html.escape(name)}, {html.escape(address)}"
            else:
                name_line = html.escape(name)

            block = ["", f"{number}. <b>{name_line}</b> ({html.escape(label)})"]
            if not is_osm and price is not None:
                block.append(f"   💰 {html.escape(ftype.upper())}: {price} €/l")
                block.append(f"   📏 Streckenumweg: {detour} km")
                if eff is not None:
                    block.append(f"   💶 Effektiv: {eff} €/l (inkl. Umweg)")
            else:
                block.append(f"   📏 Streckenumweg: {detour} km")
            if opening_hours:
                block.append(f"   🕒 Öffnungszeiten: {html.escape(str(opening_hours))}")
            nav_parts = []
            if nav.get("google_maps"):
                nav_parts.append(f"<a href=\"{nav['google_maps']}\">Google Maps</a>")
            if nav.get("apple_maps"):
                nav_parts.append(f"<a href=\"{nav['apple_maps']}\">Apple Maps</a>")
            if nav.get("waze"):
                nav_parts.append(f"<a href=\"{nav['waze']}\">Waze</a>")
            if nav_parts:
                block.append(f"   🗺️ {' | '.join(nav_parts)}")
            return block

        if abroad_fuel_stop:
            if nearest:
                lines.append("")
                lines.append("🌍 <b>Tankstellen im Ausland (keine Preisinfo verfügbar)</b>")
                lines += _fmt_block(1, "Nächste Tankstelle", nearest, fuel_type)
            if middle:
                lines += _fmt_block(2, "Nächste Tankstelle", middle, fuel_type)
            if cheapest:
                lines += _fmt_block(3, "Nächste Tankstelle", cheapest, fuel_type)
        else:
            if cheapest:
                lines += _fmt_block(1, "Preis Günstigste Tankstelle", cheapest, fuel_type)
            if nearest:
                lines += _fmt_block(2, "Strecke günstigste Tankstelle", nearest, fuel_type)
            if middle:
                lines += _fmt_block(3, "Kompromiss aus Preis/Strecke", middle, fuel_type)

        lines += ["", f"⚙️ Korridor: {corridor_km} km"]
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
