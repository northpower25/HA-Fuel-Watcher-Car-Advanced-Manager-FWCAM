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
            "🚗 <b>haFWCMA Telegram Commands</b>\n\n"
            f"{CMD_HELP} - Show this help message\n"
            f"{CMD_STATUS} - Show current vehicle and fuel status\n"
            f"{CMD_REFUEL} - Log a refueling event (coming soon)\n\n"
            "<b>🗺️ Route Commands</b>\n"
            f"{CMD_ROUTE} &lt;destination&gt; - Start a route to destination\n"
            f"{CMD_ROUTE_STATUS} - Show current route status\n"
            f"{CMD_ROUTE_CANCEL} - Cancel active route\n"
            f"{CMD_CORRIDOR} [km] - Change corridor width (e.g. /corridor 10)\n\n"
            "<i>More features coming soon!</i>"
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
        """Handle /route <destination> command.

        Joins all args as the destination string and calls hafwcma.set_route.

        Args:
            event_data: Event data from Telegram.
            args: Command arguments (words after /route).
        """
        if not args:
            await self._send_telegram_message(
                f"ℹ️ Usage: <code>{CMD_ROUTE} &lt;destination&gt;</code>\n"
                f"Example: <code>{CMD_ROUTE} München Hauptbahnhof</code>"
            )
            return

        destination = " ".join(args)
        entry_id = self.config_entry.entry_id

        await self._send_telegram_message(
            f"🗺️ Setting route to <b>{html.escape(destination)}</b>…"
        )

        try:
            result = await self.hass.services.async_call(
                DOMAIN,
                "set_route",
                {"config_entry_id": entry_id, "destination": destination},
                blocking=True,
                return_response=True,
            )
            if result and result.get("success"):
                km = result.get("route", {}).get("total_distance_km", "?")
                await self._send_telegram_message(
                    f"✅ Route set!\n"
                    f"📍 Destination: <b>{html.escape(destination)}</b>\n"
                    f"📏 Distance: {km} km\n\n"
                    f"Use {CMD_ROUTE_STATUS} to check corridor station recommendations."
                )
            else:
                error = result.get("error", "Unknown error") if result else "No response"
                await self._send_telegram_message(
                    f"❌ Could not set route: {html.escape(str(error))}"
                )
        except Exception as err:
            _LOGGER.error("Error in _handle_route_command: %s", err)
            await self._send_telegram_message(
                f"❌ Error setting route: {html.escape(str(err))}"
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
                "ℹ️ No active route.\n\n"
                f"Start one with: <code>{CMD_ROUTE} &lt;destination&gt;</code>"
            )
            return

        lines = ["🗺️ <b>Active Route</b>\n"]
        lines.append(f"📍 Destination: <b>{html.escape(str(route_data.get('destination', 'N/A')))}</b>")
        lines.append(f"📏 Distance: {route_data.get('total_distance_km', 'N/A')} km")
        lines.append(f"⚙️ Corridor: {route_data.get('corridor_width_km', 5)} km wide")

        fuel_stop = route_data.get("fuel_stop") or {}
        if fuel_stop.get("km_remaining_to_stop") is not None:
            lines.append(f"\n⛽ <b>Predicted Fuel Stop</b>")
            lines.append(f"   ~{fuel_stop['km_remaining_to_stop']} km ahead")

        best = route_data.get("best_corridor_station")
        if best:
            nav = best.get("navigation_urls") or {}
            lines.append(f"\n🏆 <b>Best Corridor Station</b>")
            lines.append(f"   {html.escape(str(best.get('name', 'Unknown')))}")
            lines.append(f"   💰 {best.get('price', 'N/A')} €/l")
            lines.append(f"   📏 Detour: {best.get('detour_km', 0)} km")
            lines.append(f"   💶 Effective: {best.get('effective_price_eur_per_l', 'N/A')} €/l")
            if nav.get("google_maps"):
                lines.append(f"   🗺️ <a href=\"{nav['google_maps']}\">Google Maps</a>")

        corridor_stations: list[dict] = route_data.get("corridor_stations", [])
        if len(corridor_stations) > 1:
            lines.append(f"\n📋 <b>Other Corridor Stations</b>")
            for i, st in enumerate(corridor_stations[1:4], start=2):
                lines.append(
                    f"   {i}. {html.escape(str(st.get('name', 'N/A')))} – "
                    f"{st.get('price', 'N/A')} €/l "
                    f"({st.get('detour_km', 0)} km detour)"
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
                "✅ Route cancelled. Corridor station search is now inactive."
            )
        except Exception as err:
            _LOGGER.error("Error in _handle_routecancel_command: %s", err)
            await self._send_telegram_message(
                f"❌ Error cancelling route: {html.escape(str(err))}"
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
