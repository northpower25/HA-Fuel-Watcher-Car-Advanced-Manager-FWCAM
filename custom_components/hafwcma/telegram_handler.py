"""Telegram event handler for bidirectional communication with haFWCMA.

This module provides integration with Home Assistant's telegram_bot platform
to enable bidirectional communication for advanced features like:
- Logging refueling events via Telegram
- Selecting fuel stations via Telegram
- Interactive queries about fuel prices
"""
from __future__ import annotations

import html
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import service

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

# Telegram command constants
CMD_REFUEL = "/refuel"
CMD_STATUS = "/status"
CMD_HELP = "/help"
CMD_ROUTE = "/route"
CMD_ROUTE_STATUS = "/routestatus"
CMD_ROUTE_CANCEL = "/routecancel"
CMD_CORRIDOR = "/corridor"

# All supported commands
SUPPORTED_COMMANDS = [CMD_REFUEL, CMD_STATUS, CMD_HELP, CMD_ROUTE, CMD_ROUTE_STATUS, CMD_ROUTE_CANCEL, CMD_CORRIDOR]


class TelegramEventHandler:
    """Handle Telegram events for haFWCMA integration.
    
    This handler listens to telegram_command and telegram_text events
    from Home Assistant's telegram_bot integration and processes them
    for haFWCMA-specific functionality.
    
    Attributes:
        hass: Home Assistant instance
        config_entry: Configuration entry for this integration instance
        chat_id: Authorized chat ID for this integration
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        chat_id: str,
    ) -> None:
        """Initialize the Telegram event handler.
        
        Args:
            hass: Home Assistant instance
            config_entry: Configuration entry
            chat_id: Telegram chat ID to monitor
        """
        self.hass = hass
        self.config_entry = config_entry
        self.chat_id = chat_id
        self._remove_listeners: list = []

    async def async_setup(self) -> bool:
        """Set up the Telegram event handler.
        
        Registers event listeners for telegram_command and telegram_text events.
        
        Returns:
            True if setup was successful
        """
        # Check if telegram_bot integration is loaded
        if "telegram_bot" not in self.hass.config.components:
            _LOGGER.info(
                "telegram_bot integration not found. "
                "Bidirectional Telegram features will not be available. "
                "To enable these features, please configure the telegram_bot integration."
            )
            return False

        # Register event listeners
        self._remove_listeners.append(
            self.hass.bus.async_listen("telegram_command", self._handle_telegram_command)
        )
        self._remove_listeners.append(
            self.hass.bus.async_listen("telegram_text", self._handle_telegram_text)
        )
        self._remove_listeners.append(
            self.hass.bus.async_listen("telegram_callback", self._handle_telegram_callback)
        )
        
        _LOGGER.info("Telegram event handler initialized for chat ID: %s", self.chat_id)
        return True

    async def async_unload(self) -> bool:
        """Unload the Telegram event handler.
        
        Removes all event listeners.
        
        Returns:
            True if unload was successful
        """
        for remove_listener in self._remove_listeners:
            remove_listener()
        self._remove_listeners.clear()
        
        _LOGGER.info("Telegram event handler unloaded")
        return True

    @callback
    def _handle_telegram_command(self, event: Event) -> None:
        """Handle telegram_command events.
        
        Args:
            event: Telegram command event
        """
        event_data = event.data
        
        # Only handle events from our configured chat
        if str(event_data.get("chat_id")) != str(self.chat_id):
            return
        
        command = event_data.get("command")
        args = event_data.get("args", [])
        
        _LOGGER.debug("Received Telegram command: %s with args: %s", command, args)
        
        # Route to appropriate handler
        if command == CMD_HELP:
            self.hass.async_create_task(self._handle_help_command(event_data))
        elif command == CMD_STATUS:
            self.hass.async_create_task(self._handle_status_command(event_data))
        elif command == CMD_REFUEL:
            self.hass.async_create_task(self._handle_refuel_command(event_data, args))
        elif command == CMD_ROUTE:
            self.hass.async_create_task(self._handle_route_command(event_data, args))
        elif command == CMD_ROUTE_STATUS:
            self.hass.async_create_task(self._handle_routestatus_command(event_data))
        elif command == CMD_ROUTE_CANCEL:
            self.hass.async_create_task(self._handle_routecancel_command(event_data))
        elif command == CMD_CORRIDOR:
            self.hass.async_create_task(self._handle_corridor_command(event_data, args))
        else:
            # Unknown command
            self.hass.async_create_task(
                self._send_telegram_message(
                    f"Unknown command: {command}\n"
                    f"Type {CMD_HELP} for available commands."
                )
            )

    @callback
    def _handle_telegram_text(self, event: Event) -> None:
        """Handle telegram_text events (non-command messages).
        
        Args:
            event: Telegram text event
        """
        event_data = event.data
        
        # Only handle events from our configured chat
        if str(event_data.get("chat_id")) != str(self.chat_id):
            return
        
        text = event_data.get("text", "")
        
        _LOGGER.debug("Received Telegram text: %s", text[:50])
        
        # Future: Could implement conversational AI or parsing for refueling data
        # For now, just acknowledge
        # self.hass.async_create_task(
        #     self._send_telegram_message("Message received. Use commands to interact.")
        # )

    @callback
    def _handle_telegram_callback(self, event: Event) -> None:
        """Handle telegram_callback events (inline keyboard button presses).
        
        Args:
            event: Telegram callback event
        """
        event_data = event.data
        
        # Only handle events from our configured chat
        if str(event_data.get("chat_id")) != str(self.chat_id):
            return
        
        callback_data = event_data.get("data", "")
        
        _LOGGER.debug("Received Telegram callback: %s", callback_data)
        
        # Future: Handle inline keyboard callbacks
        # For now, just log

    async def _handle_help_command(self, event_data: dict[str, Any]) -> None:
        """Handle /help command.

        Args:
            event_data: Event data from Telegram
        """
        help_text = (
            "🚗 <b>haFWCMA – Telegram Hilfe</b>\n\n"
            "<b>ℹ️ Allgemeine Befehle</b>\n"
            f"{CMD_HELP} – Diese Hilfe anzeigen\n"
            f"{CMD_STATUS} – Fahrzeug- und Kraftstoffstatus anzeigen\n"
            f"{CMD_REFUEL} – Tankvorgang protokollieren (demnächst)\n\n"
            "<b>🗺️ Routenplanung</b>\n"
            f"<code>{CMD_ROUTE} start &lt;Adresse&gt; [km]</code>\n"
            f"  Route starten, optional mit Korridor-Breite in km\n"
            f"  Beispiel: <code>{CMD_ROUTE} start München Hbf 10</code>\n"
            f"<code>{CMD_ROUTE} stop</code>\n"
            f"  Aktive Route beenden\n"
            f"{CMD_ROUTE_STATUS} – Aktuellen Routenstatus anzeigen\n"
            f"{CMD_ROUTE_CANCEL} – Aktive Route abbrechen\n"
            f"{CMD_CORRIDOR} [km] – Korridor-Breite ändern (z. B. /corridor 10)\n\n"
            "<b>⛽ Tankstopp-Prognose</b>\n"
            "Beim Starten einer Route wird sofort eine Tankstopp-Prognose\n"
            "berechnet. Die Prognose basiert auf:\n"
            "  • <b>Position</b>: verknüpfte <code>device_tracker</code>-Entität\n"
            "  • <b>Restreichweite</b>: <code>sensor.[ID]_range</code>\n"
            "  • <b>Verbrauch</b>: <code>sensor.[ID]_average_consumption_history</code>\n\n"
            "<i>Weitere Funktionen folgen!</i>"
        )

        await self._send_telegram_message(help_text)

    async def _handle_status_command(self, event_data: dict[str, Any]) -> None:
        """Handle /status command.
        
        Args:
            event_data: Event data from Telegram
        """
        # Get coordinator data for this config entry
        coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
        
        if not coordinator:
            await self._send_telegram_message("❌ Unable to retrieve status data.")
            return
        
        # Build status message
        status_lines = ["🚗 <b>Vehicle Status</b>\n"]
        
        # Get vehicle data from coordinator
        # Note: Field names match the coordinator's data structure
        if hasattr(coordinator, "data") and coordinator.data:
            vehicle_data = coordinator.data.get("vehicle", {})
            
            if vehicle_data:
                status_lines.append(f"Tank Level: {vehicle_data.get('tank_level', 'N/A')} L")
                status_lines.append(f"Range: {vehicle_data.get('range', 'N/A')} km")
                status_lines.append(f"Odometer: {vehicle_data.get('odometer', 'N/A')} km")
            
            # Get price data
            price_data = coordinator.data.get("prices", {})
            if price_data:
                status_lines.append("\n⛽ <b>Fuel Prices</b>")
                if "nearest_station" in price_data:
                    station = price_data["nearest_station"]
                    station_name = station.get('name', 'Unknown Station')
                    status_lines.append(f"\n{html.escape(str(station_name))}")
                    status_lines.append(f"Price: €{station.get('price', 'N/A')}/L")
                    status_lines.append(f"Distance: {station.get('distance', 'N/A')} km")
        else:
            status_lines.append("No data available yet.")
        
        await self._send_telegram_message("\n".join(status_lines))

    async def _handle_refuel_command(
        self,
        event_data: dict[str, Any],
        args: list[str],
    ) -> None:
        """Handle /refuel command.
        
        Future implementation will allow logging refueling events via Telegram.
        
        Args:
            event_data: Event data from Telegram
            args: Command arguments
        """
        await self._send_telegram_message(
            "🚧 Refueling logging via Telegram is coming soon!\n\n"
            "In the future, you'll be able to log your refueling events "
            "directly through this chat."
        )

    async def _send_telegram_message(self, message: str) -> None:
        """Send a message via Telegram.
        
        Uses Home Assistant's telegram_bot.send_message service.
        
        Args:
            message: Message text to send
        """
        try:
            await self.hass.services.async_call(
                "telegram_bot",
                "send_message",
                {
                    "target": self.chat_id,
                    "message": message,
                    "parse_mode": "html",
                },
                blocking=True,
            )
        except Exception as err:
            _LOGGER.error("Failed to send Telegram message: %s", err)

    async def _handle_route_command(
        self,
        event_data: dict[str, Any],
        args: list[str],
    ) -> None:
        """Handle /route command with start/stop subcommands.

        Supported syntax:
          /route start <address> [corridor_km]  – start a new route
          /route stop                           – stop/cancel the active route

        For backwards compatibility a bare ``/route <destination>`` (without a
        ``start``/``stop`` keyword) is still treated as ``/route start``.

        Args:
            event_data: Event data from Telegram.
            args: Command arguments (words after /route).
        """
        if not args:
            await self._send_telegram_message(
                f"ℹ️ <b>Routenplanung</b>\n\n"
                f"<code>{CMD_ROUTE} start &lt;Adresse&gt; [km]</code>\n"
                f"  Route starten (optional: Korridorbreite in km)\n"
                f"  Beispiel: <code>{CMD_ROUTE} start München Hbf 10</code>\n\n"
                f"<code>{CMD_ROUTE} stop</code>\n"
                f"  Aktive Route beenden\n\n"
                f"Tipp: {CMD_HELP} für alle Befehle"
            )
            return

        subcommand = args[0].lower()

        # ── /route stop ──────────────────────────────────────────────────────
        if subcommand == "stop":
            await self._handle_routecancel_command(event_data)
            return

        # ── /route start <address> [corridor_km] ────────────────────────────
        # Accept both "start <address>" and bare "<address>" for compatibility.
        if subcommand == "start":
            route_args = args[1:]
        else:
            route_args = args  # bare /route <destination>

        if not route_args:
            await self._send_telegram_message(
                f"ℹ️ Bitte Zieladresse angeben.\n"
                f"Beispiel: <code>{CMD_ROUTE} start München Hbf</code>"
            )
            return

        # Check whether the last token is a numeric corridor width
        corridor_km: float | None = None
        try:
            candidate = float(route_args[-1])
            if 1 <= candidate <= 50:
                corridor_km = candidate
                route_args = route_args[:-1]
            elif route_args[-1].replace(".", "", 1).isdigit():
                # The token looks like a number but is out of the valid range
                await self._send_telegram_message(
                    "⚠️ Korridorbreite muss zwischen 1 und 50 km liegen.\n"
                    f"Beispiel: <code>{CMD_ROUTE} start München Hbf 10</code>"
                )
                return
        except (ValueError, IndexError):
            pass

        if not route_args:
            await self._send_telegram_message(
                f"ℹ️ Bitte Zieladresse angeben.\n"
                f"Beispiel: <code>{CMD_ROUTE} start München Hbf</code>"
            )
            return

        destination = " ".join(route_args)
        entry_id = self.config_entry.entry_id

        service_data: dict[str, Any] = {
            "config_entry_id": entry_id,
            "destination": destination,
        }
        if corridor_km is not None:
            service_data["corridor_width_km"] = corridor_km

        corridor_info = f" (Korridor: {corridor_km} km)" if corridor_km is not None else ""
        await self._send_telegram_message(
            f"🗺️ Route wird berechnet nach <b>{html.escape(destination)}</b>{html.escape(corridor_info)}…"
        )

        try:
            result = await self.hass.services.async_call(
                DOMAIN,
                "set_route",
                service_data,
                blocking=True,
                return_response=True,
            )
            if not result or not result.get("success"):
                error = result.get("error", "Unbekannter Fehler") if result else "Keine Antwort"
                await self._send_telegram_message(
                    f"❌ Route konnte nicht berechnet werden: {html.escape(str(error))}"
                )
                return
            # On success the standard send_route_started notification (including
            # fuel stop prediction and top corridor stations) is sent by the
            # set_route service handler, so no additional message is needed here.
        except Exception as err:
            _LOGGER.error("Error in _handle_route_command: %s", err)
            await self._send_telegram_message(
                f"❌ Fehler beim Berechnen der Route: {html.escape(str(err))}"
            )

    async def _handle_routestatus_command(self, event_data: dict[str, Any]) -> None:
        """Handle /routestatus command.

        Shows the active route, predicted fuel stop, and best corridor station.

        Args:
            event_data: Event data from Telegram.
        """
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        route_data: dict[str, Any] = {}
        if coordinator and hasattr(coordinator, "data") and coordinator.data:
            route_data = coordinator.data.get("route_data") or {}

        if not route_data.get("is_active"):
            await self._send_telegram_message(
                "ℹ️ Keine aktive Route.\n\n"
                f"Starten mit: <code>{CMD_ROUTE} start &lt;Zieladresse&gt;</code>"
            )
            return

        lines = ["🗺️ <b>Aktive Route</b>\n"]
        lines.append(f"📍 Ziel: <b>{html.escape(str(route_data.get('destination', 'N/A')))}</b>")
        lines.append(f"📏 Strecke: {route_data.get('total_distance_km', 'N/A')} km")
        lines.append(f"⚙️ Korridor: {route_data.get('corridor_width_km', 5)} km")

        fuel_stop = route_data.get("fuel_stop") or {}
        if fuel_stop.get("km_remaining_to_stop") is not None:
            lines.append(f"\n⛽ <b>Prognostizierter Tankstopp</b>")
            lines.append(f"   ~{fuel_stop['km_remaining_to_stop']} km")

        best = route_data.get("best_corridor_station")
        if best:
            nav = best.get("navigation_urls") or {}
            lines.append(f"\n🏆 <b>Beste Korridor-Tankstelle</b>")
            lines.append(f"   {html.escape(str(best.get('name', 'Unbekannt')))}")
            lines.append(f"   💰 {best.get('price', 'N/A')} €/l")
            lines.append(f"   📏 Umweg: {best.get('detour_km', 0)} km")
            lines.append(f"   💶 Effektiv: {best.get('effective_price_eur_per_l', 'N/A')} €/l")
            if nav.get("google_maps"):
                lines.append(f"   🗺️ <a href=\"{nav['google_maps']}\">Google Maps</a>")

        corridor_stations: list[dict] = route_data.get("corridor_stations", [])
        if len(corridor_stations) > 1:
            lines.append(f"\n📋 <b>Weitere Korridor-Tankstellen</b>")
            for i, st in enumerate(corridor_stations[1:4], start=2):
                lines.append(
                    f"   {i}. {html.escape(str(st.get('name', 'N/A')))} – "
                    f"{st.get('price', 'N/A')} €/l "
                    f"({st.get('detour_km', 0)} km Umweg)"
                )

        await self._send_telegram_message("\n".join(lines))

    async def _handle_routecancel_command(self, event_data: dict[str, Any]) -> None:
        """Handle /routecancel command.

        Cancels the active route via hafwcma.cancel_route service.

        Args:
            event_data: Event data from Telegram.
        """
        entry_id = self.config_entry.entry_id
        try:
            await self.hass.services.async_call(
                DOMAIN,
                "cancel_route",
                {"config_entry_id": entry_id},
                blocking=True,
                return_response=True,
            )
            await self._send_telegram_message(
                "✅ Route beendet. Korridor-Tankstellensuche ist jetzt inaktiv."
            )
        except Exception as err:
            _LOGGER.error("Error in _handle_routecancel_command: %s", err)
            await self._send_telegram_message(
                f"❌ Fehler beim Beenden der Route: {html.escape(str(err))}"
            )

    async def _handle_corridor_command(
        self,
        event_data: dict[str, Any],
        args: list[str],
    ) -> None:
        """Handle /corridor [km] command – update the corridor search width.

        Args:
            event_data: Event data from Telegram.
            args: Command arguments; first element should be a number (km).
        """
        if not args:
            coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
            current_width = 5
            if coordinator and hasattr(coordinator, "data") and coordinator.data:
                current_width = (coordinator.data.get("route_data") or {}).get(
                    "corridor_width_km", 5
                )
            await self._send_telegram_message(
                f"ℹ️ Current corridor width: <b>{current_width} km</b>\n\n"
                f"To change it: <code>{CMD_CORRIDOR} &lt;km&gt;</code>\n"
                f"Example: <code>{CMD_CORRIDOR} 10</code>"
            )
            return

        try:
            new_width = float(args[0])
            if new_width <= 0 or new_width > 50:
                raise ValueError("out of range")
        except (ValueError, IndexError):
            await self._send_telegram_message(
                "❌ Invalid corridor width. Please provide a number between 1 and 50 km."
            )
            return

        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if coordinator and hasattr(coordinator, "data") and coordinator.data:
            route_data = coordinator.data.get("route_data")
            if route_data:
                route_data["corridor_width_km"] = new_width
                entry_data = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {})
                route_planner = entry_data.get("route_planner")
                if route_planner and route_planner.active_route:
                    route_planner.active_route["corridor_width_km"] = new_width
                coordinator.async_update_listeners()

        await self._send_telegram_message(
            f"✅ Corridor width updated to <b>{new_width} km</b>."
        )
