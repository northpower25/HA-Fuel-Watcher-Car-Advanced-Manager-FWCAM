"""Telegram Refueling Handler for bidirectional refueling event communication.

This module provides specialized handling for refueling events via Telegram,
including:
- Automatic notification when new refueling events are detected
- Interactive forms for missing data collection
- Photo receipt processing (OCR)
- Voice message transcription
- AI-powered data parsing and structuring
"""
from __future__ import annotations

import html
import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import service

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

# Constants for logging
MAX_LOG_MESSAGE_LENGTH = 200  # Maximum characters to log from notification message


class TelegramRefuelingHandler:
    """Handle Telegram interactions for refueling events.
    
    This handler manages bidirectional communication for refueling events:
    1. Sends notifications when new refueling events are detected
    2. Collects missing data via various input methods
    3. Processes and structures user responses
    4. Updates refueling records with collected data
    
    Attributes:
        hass: Home Assistant instance
        config_entry: Configuration entry for this integration instance
        chat_id: Authorized chat ID for this integration
        telegram_handler: Reference to the main TelegramEventHandler
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        chat_id: str,
        telegram_handler: Any = None,
    ) -> None:
        """Initialize the Telegram refueling handler.
        
        Args:
            hass: Home Assistant instance
            config_entry: Configuration entry
            chat_id: Telegram chat ID to monitor
            telegram_handler: Reference to main TelegramEventHandler
        """
        self.hass = hass
        self.config_entry = config_entry
        self.chat_id = chat_id
        self.telegram_handler = telegram_handler
        self._remove_listeners: list = []
        self._pending_refuelings: dict[int, dict] = {}  # refuel_id -> context data

    async def async_setup(self) -> bool:
        """Set up the Telegram refueling handler.
        
        Registers event listeners for refueling-related events.
        
        Returns:
            True if setup was successful
        """
        # Check if telegram_bot integration is loaded
        _LOGGER.info(
            "🔧 Setting up Telegram refueling handler. Checking for telegram_bot integration..."
        )
        _LOGGER.debug(
            "Available integrations: %s",
            ", ".join(sorted(self.hass.config.components))
        )
        
        if "telegram_bot" not in self.hass.config.components:
            _LOGGER.warning(
                "❌ telegram_bot integration NOT FOUND! "
                "Bidirectional refueling features will not be available. "
                "Please configure the telegram_bot integration in Home Assistant. "
                "See: https://www.home-assistant.io/integrations/telegram_bot/"
            )
            return False
        
        _LOGGER.info("✅ telegram_bot integration found - proceeding with event listener setup")
        
        # Verify telegram_bot service is available
        if not self.hass.services.has_service("telegram_bot", "send_message"):
            _LOGGER.warning(
                "⚠️ telegram_bot integration loaded but send_message service not available yet. "
                "Proceeding with listener setup, but notifications may fail."
            )
        else:
            _LOGGER.info("✅ telegram_bot.send_message service is available")

        # Listen for new refueling events (custom event)
        self._remove_listeners.append(
            self.hass.bus.async_listen(
                f"{DOMAIN}_refueling_added",
                self._handle_new_refueling_event
            )
        )
        _LOGGER.info("✅ Registered listener for %s_refueling_added events", DOMAIN)
        
        # Listen for Telegram text responses (replies to our messages)
        self._remove_listeners.append(
            self.hass.bus.async_listen(
                "telegram_text",
                self._handle_telegram_text_response
            )
        )
        _LOGGER.debug("Registered listener for telegram_text events")
        
        # Listen for Telegram callback (inline keyboard button presses)
        self._remove_listeners.append(
            self.hass.bus.async_listen(
                "telegram_callback",
                self._handle_telegram_callback_response
            )
        )
        _LOGGER.debug("Registered listener for telegram_callback events")
        
        # Listen for Telegram photo messages
        self._remove_listeners.append(
            self.hass.bus.async_listen(
                "telegram_photo",
                self._handle_telegram_photo_response
            )
        )
        _LOGGER.debug("Registered listener for telegram_photo events")
        
        # Listen for Telegram voice messages
        self._remove_listeners.append(
            self.hass.bus.async_listen(
                "telegram_voice",
                self._handle_telegram_voice_response
            )
        )
        _LOGGER.debug("Registered listener for telegram_voice events")
        
        _LOGGER.info(
            "✅ Telegram refueling handler successfully initialized with %d event listeners. "
            "Listening for '%s_refueling_added' events for config_entry_id: %s",
            len(self._remove_listeners),
            DOMAIN,
            self.config_entry.entry_id
        )
        return True

    async def async_unload(self) -> bool:
        """Unload the Telegram refueling handler.
        
        Removes all event listeners.
        
        Returns:
            True if unload was successful
        """
        for remove_listener in self._remove_listeners:
            remove_listener()
        self._remove_listeners.clear()
        self._pending_refuelings.clear()
        
        _LOGGER.info("Telegram refueling handler unloaded")
        return True

    @callback
    def _handle_new_refueling_event(self, event: Event) -> None:
        """Handle new refueling event detection.
        
        Args:
            event: Refueling added event
        """
        _LOGGER.info("📨 TelegramRefuelingHandler received refueling_added event")
        event_data = event.data
        
        # Only handle events from our config entry
        config_entry_id = event_data.get("config_entry_id")
        _LOGGER.debug(
            "Event config_entry_id: %s, Handler config_entry_id: %s",
            config_entry_id,
            self.config_entry.entry_id
        )
        
        if config_entry_id != self.config_entry.entry_id:
            _LOGGER.debug(
                "Ignoring event from different config entry (expected: %s, got: %s)",
                self.config_entry.entry_id,
                config_entry_id
            )
            return
        
        refuel_id = event_data.get("refuel_id")
        refuel_data = event_data.get("refuel_data", {})
        
        _LOGGER.info(
            "✅ Matched config entry - Processing refueling event: ID=%s, liters=%.2f, fuel_type=%s",
            refuel_id,
            refuel_data.get("liters_refueled", 0),
            refuel_data.get("fuel_type", "unknown")
        )
        
        # Store in pending dict for response tracking
        self._pending_refuelings[refuel_id] = {
            "data": refuel_data,
            "notified_at": datetime.now().isoformat(),
        }
        
        _LOGGER.info("📤 Creating task to send Telegram notification for refuel ID %s", refuel_id)
        # Send notification asynchronously
        self.hass.async_create_task(
            self._send_refueling_notification(refuel_id, refuel_data)
        )

    async def _send_refueling_notification(
        self,
        refuel_id: int,
        refuel_data: dict[str, Any],
    ) -> None:
        """Send Telegram notification for new refueling event.
        
        Args:
            refuel_id: ID of the refueling event
            refuel_data: Refueling event data
        """
        _LOGGER.info(
            "Preparing Telegram notification for refuel ID %s (chat_id: %s)",
            refuel_id,
            self.chat_id
        )
        
        # Build notification message using helper
        message, inline_keyboard = await self._build_refuel_status_message(
            refuel_id, refuel_data, is_update=False
        )
        
        try:
            # Check if telegram_bot service is still available
            if not self.hass.services.has_service("telegram_bot", "send_message"):
                _LOGGER.error(
                    "❌ telegram_bot send_message service is not available! "
                    "Cannot send notification for refuel ID %s. "
                    "The telegram_bot integration may not be properly configured.",
                    refuel_id
                )
                return
            
            # Ensure chat_id is in the correct format (integer for telegram_bot service)
            try:
                target_chat_id = int(self.chat_id) if isinstance(self.chat_id, str) else self.chat_id
            except (ValueError, TypeError):
                # If conversion fails, use original value as-is
                target_chat_id = self.chat_id
            
            _LOGGER.info(
                "📤 Sending notification via telegram_bot service (target: %s [type: %s], parse_mode: html)",
                target_chat_id,
                type(target_chat_id).__name__
            )
            _LOGGER.debug("Notification message: %s", message[:MAX_LOG_MESSAGE_LENGTH])
            
            # Send message via telegram_bot service
            # Note: telegram_bot.send_message does not support return_response parameter
            # The service completes successfully but doesn't return message_id
            await self.hass.services.async_call(
                "telegram_bot",
                "send_message",
                {
                    "target": target_chat_id,
                    "message": message,
                    "parse_mode": "html",
                    "inline_keyboard": inline_keyboard,
                },
                blocking=True,
            )
            
            _LOGGER.info("✅ Telegram notification service call completed successfully for refuel ID %s", refuel_id)
            
            # Update refueling record with notification data
            # Note: We cannot get message_id from the service call as it doesn't support return_response
            from .utils.storage import update_refueling_record
            await update_refueling_record(
                self.hass,
                self.config_entry,
                refuel_id,
                {
                    "telegram_notification_sent": True,
                    "telegram_notification_timestamp": datetime.now().isoformat(),
                }
            )
            _LOGGER.debug("Updated refueling record with notification metadata")
            
            _LOGGER.info("✅ Refueling notification sent for ID %s", refuel_id)
            
        except ServiceValidationError as err:
            _LOGGER.error(
                f"Failed to send refueling notification for ID {refuel_id}: {err}\n\n"
                f"⚠️ This error indicates that the telegram_bot integration is not properly configured.\n"
                f"Please ensure your configuration.yaml includes:\n\n"
                f"telegram_bot:\n"
                f"  - platform: polling\n"
                f"    api_key: YOUR_BOT_TOKEN\n"
                f"    allowed_chat_ids:\n"
                f"      - {self.chat_id}\n\n"
                f"See documentation: https://www.home-assistant.io/integrations/telegram_bot/"
            )
        except Exception as err:
            _LOGGER.error(
                "Failed to send refueling notification for ID %s: %s (type: %s)",
                refuel_id,
                err,
                type(err).__name__,
                exc_info=True
            )

    @callback
    def _handle_telegram_text_response(self, event: Event) -> None:
        """Handle text responses to refueling notifications.
        
        Args:
            event: Telegram text event
        """
        event_data = event.data
        
        # Only handle events from our configured chat
        if str(event_data.get("chat_id")) != str(self.chat_id):
            return
        
        text = event_data.get("text", "")
        
        _LOGGER.info("📨 Received Telegram text message: '%s' (length: %d)", text[:50], len(text))
        
        # Strategy 1: Try to extract refuel_id from text content (e.g., "Tankvorgang #123")
        refuel_id = self._extract_refuel_id_from_text(text)
        if refuel_id:
            _LOGGER.info("✅ Extracted refuel_id %s from text content", refuel_id)
        
        # Strategy 2: Try to find by message_id (will be None due to HA limitations)
        if not refuel_id:
            reply_to_message_id = event_data.get("reply_to_message", {}).get("message_id")
            refuel_id = self._find_refuel_by_message_id(reply_to_message_id)
        
        # Strategy 3: Use temporal matching (most recent) as fallback
        if not refuel_id:
            _LOGGER.debug(
                "Explicit ID and message_id matching failed. "
                "Using temporal matching to find most recent pending refueling."
            )
            refuel_id = self._find_most_recent_pending_refuel()
        
        if refuel_id:
            _LOGGER.info("✅ Matched text response to refuel ID %s: %s", refuel_id, text[:50])
            self.hass.async_create_task(
                self._process_text_response(refuel_id, text)
            )
        else:
            _LOGGER.info(
                "⚠️ Text message not linked to any pending refueling. "
                "No pending refuelings available or all have been processed."
            )

    @callback
    def _handle_telegram_callback_response(self, event: Event) -> None:
        """Handle inline keyboard button presses.
        
        Args:
            event: Telegram callback event
        """
        event_data = event.data
        
        # Only handle events from our configured chat
        if str(event_data.get("chat_id")) != str(self.chat_id):
            _LOGGER.debug(
                "Ignoring callback from different chat (expected: %s, got: %s)",
                self.chat_id,
                event_data.get("chat_id")
            )
            return
        
        callback_data = event_data.get("data", "")
        callback_id = event_data.get("id")
        
        _LOGGER.info("🔘 Received Telegram callback: data='%s', id=%s", callback_data, callback_id)
        
        # Parse callback data
        if callback_data.startswith("refuel_"):
            parts = callback_data.split("_")
            _LOGGER.debug("Callback data parts: %s", parts)
            
            if len(parts) >= 3:
                action = parts[1]
                try:
                    refuel_id = int(parts[2])
                    _LOGGER.info(
                        "✅ Parsed callback action='%s' for refuel_id=%s",
                        action,
                        refuel_id
                    )
                    self.hass.async_create_task(
                        self._process_callback_action(refuel_id, action, event_data)
                    )
                except ValueError as err:
                    _LOGGER.error(
                        "❌ Failed to parse refuel_id from callback_data '%s': %s",
                        callback_data,
                        err
                    )
                    # Answer callback query with error
                    self.hass.async_create_task(
                        self._answer_callback_query(callback_id, "❌ Fehler beim Parsen der Daten")
                    )
            else:
                _LOGGER.warning(
                    "⚠️ Invalid callback data format: '%s' (expected at least 3 parts)",
                    callback_data
                )
                # Answer callback query with error
                self.hass.async_create_task(
                    self._answer_callback_query(callback_id, "❌ Ungültiges Format")
                )
        else:
            _LOGGER.debug(
                "Ignoring callback with non-refuel data: '%s'",
                callback_data
            )

    @callback
    def _handle_telegram_photo_response(self, event: Event) -> None:
        """Handle photo (receipt) responses.
        
        Args:
            event: Telegram photo event
        """
        event_data = event.data
        
        # Only handle events from our configured chat
        if str(event_data.get("chat_id")) != str(self.chat_id):
            return
        
        photo = event_data.get("photo", [])
        caption = event_data.get("caption", "")
        
        _LOGGER.info("📷 Received Telegram photo message with caption: '%s'", caption[:50] if caption else "(no caption)")
        
        # Get the largest photo (best quality)
        file_id = None
        if photo and len(photo) > 0:
            file_id = photo[-1].get("file_id")
        
        if not file_id:
            _LOGGER.warning("⚠️ Photo message received but no file_id found")
            return
        
        # Strategy 1: Try to extract refuel_id from caption (e.g., "Tankvorgang #123")
        refuel_id = self._extract_refuel_id_from_text(caption) if caption else None
        if refuel_id:
            _LOGGER.info("✅ Extracted refuel_id %s from photo caption", refuel_id)
        
        # Strategy 2: Try to find by message_id (will be None due to HA limitations)
        if not refuel_id:
            reply_to_message_id = event_data.get("reply_to_message", {}).get("message_id")
            refuel_id = self._find_refuel_by_message_id(reply_to_message_id)
        
        # Strategy 3: Use temporal matching (most recent) as fallback
        if not refuel_id:
            _LOGGER.debug(
                "Explicit ID and message_id matching failed. "
                "Using temporal matching to find most recent pending refueling."
            )
            refuel_id = self._find_most_recent_pending_refuel()
        
        if refuel_id:
            _LOGGER.info("✅ Matched photo response to refuel ID %s", refuel_id)
            self.hass.async_create_task(
                self._process_photo_response(refuel_id, file_id, caption)
            )
        else:
            _LOGGER.info(
                "⚠️ Photo message not linked to any pending refueling. "
                "No pending refuelings available or all have been processed."
            )

    @callback
    def _handle_telegram_voice_response(self, event: Event) -> None:
        """Handle voice message responses.
        
        Args:
            event: Telegram voice event
        """
        event_data = event.data
        
        # Only handle events from our configured chat
        if str(event_data.get("chat_id")) != str(self.chat_id):
            return
        
        file_id = event_data.get("file_id")
        
        _LOGGER.info("🎤 Received Telegram voice message (file_id: %s)", file_id[:20] if file_id else "None")
        
        if not file_id:
            _LOGGER.warning("⚠️ Voice message received but no file_id found")
            return
        
        # Try to find by message_id first (will be None due to HA limitations)
        reply_to_message_id = event_data.get("reply_to_message", {}).get("message_id")
        refuel_id = self._find_refuel_by_message_id(reply_to_message_id)
        
        # If not found by message_id, use temporal matching (most recent)
        if not refuel_id:
            _LOGGER.debug(
                "Message ID matching failed (reply_to_message_id: %s). "
                "Using temporal matching to find most recent pending refueling.",
                reply_to_message_id
            )
            refuel_id = self._find_most_recent_pending_refuel()
        
        if refuel_id:
            _LOGGER.info("✅ Matched voice response to refuel ID %s", refuel_id)
            self.hass.async_create_task(
                self._process_voice_response(refuel_id, file_id)
            )
        else:
            _LOGGER.info(
                "⚠️ Voice message not linked to any pending refueling. "
                "No pending refuelings available or all have been processed."
            )

    def _extract_refuel_id_from_text(self, text: str) -> int | None:
        """Extract refuel ID from text message.
        
        Looks for patterns like:
        - "Tankvorgang #123"
        - "#123"
        - "Refuel #123"
        
        Args:
            text: Text to parse
            
        Returns:
            Refuel ID if found, None otherwise
        """
        if not text:
            return None
        
        # Pattern: "Tankvorgang #123" or "#123" or "Refuel #123"
        patterns = [
            r'[Tt]ankvorgang\s*#(\d+)',
            r'[Rr]efuel\s*#(\d+)',
            r'#(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    refuel_id = int(match.group(1))
                    # Verify this refuel_id is in pending refuelings
                    if refuel_id in self._pending_refuelings:
                        _LOGGER.debug(
                            "Extracted refuel_id %s from text using pattern '%s'",
                            refuel_id,
                            pattern
                        )
                        return refuel_id
                    else:
                        _LOGGER.debug(
                            "Extracted refuel_id %s from text but not in pending refuelings",
                            refuel_id
                        )
                except (ValueError, AttributeError):
                    continue
        
        return None

    def _find_refuel_by_message_id(self, message_id: int | None) -> int | None:
        """Find refuel ID by Telegram message ID.
        
        NOTE: Due to Home Assistant telegram_bot integration limitations,
        message_id is never available, so this method always returns None.
        Use _find_most_recent_pending_refuel() instead.
        
        Args:
            message_id: Telegram message ID
            
        Returns:
            Refuel ID if found, None otherwise
        """
        if not message_id:
            return None
        
        for refuel_id, context in self._pending_refuelings.items():
            if context.get("message_id") == message_id:
                return refuel_id
        
        return None

    def _find_most_recent_pending_refuel(self) -> int | None:
        """Find the most recent pending refueling event.
        
        Since message threading via message_id is not available in Home Assistant's
        telegram_bot integration, we use temporal matching - assuming the user is
        responding to the most recently sent notification.
        
        Returns:
            Refuel ID of the most recent pending refueling, or None if no pending refuelings
        """
        if not self._pending_refuelings:
            _LOGGER.debug("No pending refuelings found")
            return None
        
        # Find the most recent by comparing notified_at timestamps
        most_recent_id = None
        most_recent_time = None
        
        for refuel_id, context in self._pending_refuelings.items():
            notified_at = context.get("notified_at")
            if notified_at:
                if most_recent_time is None or notified_at > most_recent_time:
                    most_recent_time = notified_at
                    most_recent_id = refuel_id
        
        if most_recent_id:
            _LOGGER.debug(
                "Found most recent pending refueling: ID=%s, notified_at=%s",
                most_recent_id,
                most_recent_time
            )
        else:
            _LOGGER.debug("No refuelings with valid notified_at timestamp found")
        
        return most_recent_id

    async def _build_refuel_status_message(
        self,
        refuel_id: int,
        refuel_data: dict[str, Any],
        is_update: bool = False,
    ) -> tuple[str, list]:
        """Build a status message for a refueling event.
        
        Args:
            refuel_id: ID of the refueling event
            refuel_data: Refueling event data
            is_update: Whether this is an update message (vs initial notification)
            
        Returns:
            Tuple of (message, inline_keyboard)
        """
        # Build status message
        message_parts = [
            f"⛽ <b>Tankvorgang #{refuel_id}</b>\n",
        ]
        
        if is_update:
            message_parts.append("<i>✅ Daten aktualisiert!</i>\n")
        else:
            message_parts.append("<i>Neuer Tankvorgang erkannt!</i>\n")
        
        # Show detected data
        timestamp = refuel_data.get("timestamp", "Unbekannt")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp = dt.strftime("%d.%m.%Y %H:%M")
            except:
                pass
        
        message_parts.append(f"🕐 Zeitpunkt: {timestamp}")
        
        # Track what's missing
        missing_fields = []
        
        liters = refuel_data.get("liters_refueled")
        if liters:
            message_parts.append(f"📊 Menge: {liters:.2f} Liter")
        else:
            missing_fields.append("Tankvolumen")
        
        odometer = refuel_data.get("odometer_km")
        if odometer:
            message_parts.append(f"🔢 KM-Stand: {odometer:.1f} km")
        else:
            missing_fields.append("KM-Stand")
        
        price_per_liter = refuel_data.get("price_per_liter")
        if price_per_liter:
            message_parts.append(f"💰 Preis/Liter: {price_per_liter:.3f} €")
        else:
            missing_fields.append("Preis pro Liter")
        
        total_cost = refuel_data.get("total_cost")
        if total_cost:
            message_parts.append(f"💵 Gesamtkosten: {total_cost:.2f} €")
        else:
            missing_fields.append("Gesamtkosten")
        
        station_name = refuel_data.get("station_name")
        if station_name:
            message_parts.append(f"🏪 Tankstelle: {html.escape(str(station_name))}")
        else:
            missing_fields.append("Tankstellenname")
        
        station_address = refuel_data.get("station_address")
        if station_address:
            message_parts.append(f"📍 Adresse: {html.escape(str(station_address))}")
        
        fuel_type = refuel_data.get("fuel_type")
        if fuel_type:
            message_parts.append(f"⚡ Kraftstoffart: {html.escape(str(fuel_type))}")
        
        # Show missing fields or completion status
        if missing_fields:
            message_parts.append(f"\n❓ <b>Fehlende Informationen:</b>")
            message_parts.append(", ".join(missing_fields))
            message_parts.append(
                f"\n💡 <b>Wie können Sie antworten:</b>\n"
                f"• Antworten Sie mit 'Tankvorgang #{refuel_id}: &lt;Ihre Daten&gt;'\n"
                f"• Oder einfach: '45.5 L, 1.599 €/L, Shell' (wird automatisch zugeordnet)\n"
                f"• Senden Sie ein Foto der Quittung\n"
                f"• Senden Sie eine Sprachnachricht\n"
                f"• Nutzen Sie die Schaltflächen unten"
            )
        else:
            message_parts.append(f"\n✅ <b>Alle Daten vollständig!</b>")
        
        message = "\n".join(message_parts)
        
        # Create inline keyboard
        # Format: [["Button Text", "callback_data"]] for Home Assistant telegram_bot service
        if missing_fields:
            # Still have missing data - offer Continue and Done options
            inline_keyboard = [
                [
                    ["✅ Fertig", f"refuel_done_{refuel_id}"],
                    ["✏️ Weiter bearbeiten", f"refuel_edit_{refuel_id}"],
                ],
                [
                    ["🗑️ Löschen", f"refuel_delete_{refuel_id}"],
                ],
            ]
        else:
            # All data complete - offer Confirm and Delete
            inline_keyboard = [
                [
                    ["✅ Bestätigen", f"refuel_confirm_{refuel_id}"],
                    ["✏️ Bearbeiten", f"refuel_edit_{refuel_id}"],
                ],
                [
                    ["🗑️ Löschen", f"refuel_delete_{refuel_id}"],
                ],
            ]
        
        return message, inline_keyboard

    async def _process_text_response(self, refuel_id: int, text: str) -> None:
        """Process unstructured text response.
        
        Uses AI/pattern matching to extract structured data from text.
        
        Args:
            refuel_id: Refueling event ID
            text: User's text response
        """
        _LOGGER.info("Processing text response for refuel ID %s", refuel_id)
        
        # Parse the text to extract data
        parsed_data = await self._parse_refuel_text(text)
        
        # Update refueling record
        from .utils.storage import update_refueling_record, get_refueling_record
        
        updates = {
            "telegram_response_received": True,
            "telegram_response_timestamp": datetime.now().isoformat(),
            "telegram_response_type": "text",
            "telegram_response_raw": text,
            "telegram_response_parsed": parsed_data,
            "data_quality": "ai_processed",  # Mark as AI processed
        }
        
        # Merge parsed data into updates
        if parsed_data:
            updates.update(parsed_data)
        
        await update_refueling_record(
            self.hass,
            self.config_entry,
            refuel_id,
            updates
        )
        
        # Fire event for test button to catch
        self.hass.bus.async_fire(
            f"{DOMAIN}_refueling_updated",
            {
                "config_entry_id": self.config_entry.entry_id,
                "refuel_id": refuel_id,
                "telegram_response_raw": text,
                "telegram_response_parsed": parsed_data,
            }
        )
        
        # Save station to POI cache if station name was provided
        if parsed_data.get("station_name"):
            await self._save_station_to_poi(
                station_name=parsed_data["station_name"],
                station_address=parsed_data.get("station_address"),
                # Note: We don't have coordinates from text parsing alone
                # These would need to come from the refueling record or geocoding
            )
        
        # Get updated refueling data
        refuel_data = await get_refueling_record(
            self.hass,
            self.config_entry,
            refuel_id
        )
        
        if not refuel_data:
            _LOGGER.error("Failed to get refueling record %s after update", refuel_id)
            return
        
        # Send updated status message with current data and remaining missing fields
        message, inline_keyboard = await self._build_refuel_status_message(
            refuel_id, refuel_data, is_update=True
        )
        
        # Send the updated message via telegram_bot service
        try:
            target_chat_id = int(self.chat_id) if isinstance(self.chat_id, str) else self.chat_id
            
            await self.hass.services.async_call(
                "telegram_bot",
                "send_message",
                {
                    "target": target_chat_id,
                    "message": message,
                    "parse_mode": "html",
                    "inline_keyboard": inline_keyboard,
                },
                blocking=True,
            )
            
            _LOGGER.info("✅ Sent updated status message for refuel ID %s", refuel_id)
        except Exception as err:
            _LOGGER.error("Failed to send updated status message: %s", err)
        
        # DON'T remove from pending - keep dialog open for multi-turn interaction
        # Only remove when user clicks "Fertig" or "Bestätigen" button
        _LOGGER.debug("Keeping refuel ID %s in pending for multi-turn dialog", refuel_id)

    async def _process_callback_action(
        self,
        refuel_id: int,
        action: str,
        event_data: dict,
    ) -> None:
        """Process inline keyboard button action.
        
        Args:
            refuel_id: Refueling event ID
            action: Action (confirm, edit, delete)
            event_data: Event data from Telegram
        """
        _LOGGER.info("Processing callback action '%s' for refuel ID %s", action, refuel_id)
        
        if action == "confirm":
            # Mark as confirmed
            from .utils.storage import update_refueling_record
            await update_refueling_record(
                self.hass,
                self.config_entry,
                refuel_id,
                {
                    "telegram_response_received": True,
                    "telegram_response_timestamp": datetime.now().isoformat(),
                    "telegram_response_type": "callback",
                    "telegram_response_raw": "confirmed",
                    "data_quality": "ai_processed",  # Mark as AI processed
                }
            )
            
            # Fire event for test button to catch
            self.hass.bus.async_fire(
                f"{DOMAIN}_refueling_updated",
                {
                    "config_entry_id": self.config_entry.entry_id,
                    "refuel_id": refuel_id,
                    "telegram_response_raw": "confirmed",
                    "telegram_response_parsed": {},
                }
            )
            
            await self._answer_callback_query(
                event_data.get("id"),
                "✅ Tankvorgang bestätigt!"
            )
            
            # Remove from pending
            self._pending_refuelings.pop(refuel_id, None)
            
        elif action == "done":
            # User indicates they're done adding data (even if incomplete)
            await self._answer_callback_query(
                event_data.get("id"),
                "✅ Tankvorgang abgeschlossen!"
            )
            
            # Remove from pending
            self._pending_refuelings.pop(refuel_id, None)
            
        elif action == "edit":
            # Prompt for editing - keep in pending for multi-turn dialog
            await self._answer_callback_query(
                event_data.get("id"),
                "✏️ Bitte senden Sie die aktualisierten Daten"
            )
            
            await self._send_telegram_message(
                f"✏️ Bitte antworten Sie mit den aktualisierten Daten für Tankvorgang #{refuel_id}:\n\n"
                "Beispiel: 45.5 Liter, 1.599 €/Liter, Shell Tankstelle"
            )
            # Don't remove from pending - keep dialog open
            
        elif action == "delete":
            # Delete the refueling event
            try:
                from .utils.storage import delete_refueling_record
                await delete_refueling_record(
                    self.hass,
                    self.config_entry,
                    refuel_id
                )
                
                await self._answer_callback_query(
                    event_data.get("id"),
                    "🗑️ Tankvorgang gelöscht!"
                )
                
                # Remove from pending
                self._pending_refuelings.pop(refuel_id, None)
                
            except Exception as err:
                _LOGGER.error("Failed to delete refueling %s: %s", refuel_id, err)
                await self._answer_callback_query(
                    event_data.get("id"),
                    "❌ Fehler beim Löschen"
                )

    async def _process_photo_response(
        self,
        refuel_id: int,
        file_id: str,
        caption: str,
    ) -> None:
        """Process photo (receipt) response.
        
        Performs OCR on the receipt image to extract data.
        
        Args:
            refuel_id: Refueling event ID
            file_id: Telegram file ID of the photo
            caption: Optional caption text
        """
        _LOGGER.info("Processing photo response for refuel ID %s", refuel_id)
        
        # TODO: Implement OCR processing
        # Options:
        # 1. Local: Tesseract OCR via pytesseract
        # 2. Cloud: Google Vision API, AWS Textract, Azure Computer Vision
        # 3. HA Integration: Use existing HA integrations if available
        
        ocr_text = await self._perform_ocr(file_id)
        parsed_data = await self._parse_refuel_text(ocr_text) if ocr_text else {}
        
        # Update refueling record
        from .utils.storage import update_refueling_record
        
        updates = {
            "telegram_response_received": True,
            "telegram_response_timestamp": datetime.now().isoformat(),
            "telegram_response_type": "photo",
            "telegram_response_raw": f"Caption: {caption}\nOCR: {ocr_text}",
            "telegram_response_parsed": parsed_data,
            "telegram_photo_file_id": file_id,
            "data_quality": "ai_processed",  # Mark as AI processed
        }
        
        # Merge parsed data
        if parsed_data:
            updates.update(parsed_data)
        
        await update_refueling_record(
            self.hass,
            self.config_entry,
            refuel_id,
            updates
        )
        
        # Fire event for test button to catch
        self.hass.bus.async_fire(
            f"{DOMAIN}_refueling_updated",
            {
                "config_entry_id": self.config_entry.entry_id,
                "refuel_id": refuel_id,
                "telegram_response_raw": f"Caption: {caption}\nOCR: {ocr_text}",
                "telegram_response_parsed": parsed_data,
            }
        )
        
        # Send confirmation
        await self._send_telegram_message(
            f"📷 Quittung für Tankvorgang #{refuel_id} empfangen!\n\n"
            f"OCR-Text:\n<code>{html.escape(ocr_text or 'Keine Daten erkannt')}</code>\n\n"
            f"Erkannte Daten:\n<code>{html.escape(json.dumps(parsed_data, indent=2, ensure_ascii=False))}</code>"
        )
        
        # Remove from pending
        self._pending_refuelings.pop(refuel_id, None)

    async def _process_voice_response(
        self,
        refuel_id: int,
        file_id: str,
    ) -> None:
        """Process voice message response.
        
        Performs speech-to-text transcription.
        
        Args:
            refuel_id: Refueling event ID
            file_id: Telegram file ID of the voice message
        """
        _LOGGER.info("Processing voice response for refuel ID %s", refuel_id)
        
        # TODO: Implement speech-to-text
        # Options:
        # 1. Local: Vosk, Whisper (OpenAI), faster-whisper
        # 2. Cloud: Google Speech-to-Text, AWS Transcribe, Azure Speech
        # 3. HA Integration: Use existing HA integrations if available
        
        transcription = await self._transcribe_voice(file_id)
        parsed_data = await self._parse_refuel_text(transcription) if transcription else {}
        
        # Update refueling record
        from .utils.storage import update_refueling_record
        
        updates = {
            "telegram_response_received": True,
            "telegram_response_timestamp": datetime.now().isoformat(),
            "telegram_response_type": "voice",
            "telegram_response_raw": transcription,
            "telegram_response_parsed": parsed_data,
            "telegram_voice_file_id": file_id,
            "data_quality": "ai_processed",  # Mark as AI processed
        }
        
        # Merge parsed data
        if parsed_data:
            updates.update(parsed_data)
        
        await update_refueling_record(
            self.hass,
            self.config_entry,
            refuel_id,
            updates
        )
        
        # Fire event for test button to catch
        self.hass.bus.async_fire(
            f"{DOMAIN}_refueling_updated",
            {
                "config_entry_id": self.config_entry.entry_id,
                "refuel_id": refuel_id,
                "telegram_response_raw": transcription,
                "telegram_response_parsed": parsed_data,
            }
        )
        
        # Send confirmation
        await self._send_telegram_message(
            f"🎤 Sprachnachricht für Tankvorgang #{refuel_id} empfangen!\n\n"
            f"Transkription:\n<code>{html.escape(transcription or 'Keine Daten erkannt')}</code>\n\n"
            f"Erkannte Daten:\n<code>{html.escape(json.dumps(parsed_data, indent=2, ensure_ascii=False))}</code>"
        )
        
        # Remove from pending
        self._pending_refuelings.pop(refuel_id, None)

    async def _parse_refuel_text(self, text: str) -> dict[str, Any]:
        """Parse unstructured text to extract refueling data.
        
        Uses pattern matching and AI to extract structured data.
        Enhanced to recognize German number formats and smart price detection.
        
        Args:
            text: Unstructured text input
            
        Returns:
            Dictionary with extracted data
        """
        parsed = {}
        
        if not text:
            return parsed
        
        # Extract liters (various formats)
        # Examples: "45.5 L", "45,5 Liter", "45.5L", "45.5 liters", "20 L", "20l"
        liter_patterns = [
            r"(\d+[.,]\d+)\s*(?:L|l|Liter|liter)(?!\s*/)",  # Decimal with L/Liter (not €/L)
            r"(\d+)\s*(?:L|l|Liter|liter)(?!\s*/)",        # Integer with L/Liter (not €/L)
        ]
        for pattern in liter_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1).replace(",", "."))
                    parsed["liters_refueled"] = value
                    _LOGGER.debug("Extracted liters: %s", value)
                    break
                except:
                    pass
        
        # Extract price per liter - prioritize explicit €/L formats first
        # Examples: "1.599 €/L", "1,599€/Liter", "1.59 EUR/l"
        price_patterns = [
            r"(\d+[.,]\d+)\s*(?:€|EUR|euro)?\s*/\s*(?:L|l|Liter)",  # With explicit /L
            r"Preis[:\s]+(\d+[.,]\d+)",  # After "Preis:"
        ]
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(",", "."))
                    parsed["price_per_liter"] = value
                    _LOGGER.debug("Extracted price/liter (explicit): %s", value)
                    break
                except:
                    pass
        
        # Smart price detection: Numbers like 1,xxx or 2,xxx are likely €/L prices
        # Only if no explicit price/liter was found and value is between 1.0 and 3.0
        if "price_per_liter" not in parsed:
            standalone_price_pattern = r"\b([12][.,]\d{1,3})\b"
            matches = re.findall(standalone_price_pattern, text)
            for match in matches:
                try:
                    value = float(match.replace(",", "."))
                    # Fuel prices are typically between 1.0 and 3.0 €/L
                    if 1.0 <= value <= 3.0:
                        parsed["price_per_liter"] = value
                        _LOGGER.debug("Extracted price/liter (smart detection): %s", value)
                        break
                except:
                    pass
        
        # Extract total cost
        # Examples: "71.96 €", "71,96 EUR", "Total: 71.96", "20eur", "20 €", "20 EUR"
        # Numbers 20-99 without L/Liter suffix are likely total costs
        cost_patterns = [
            r"(?:Gesamt|Total|Summe)[:\s]+(\d+[.,]\d+)",  # With keyword
            r"(\d+[.,]\d+)\s*(?:€|EUR|euro|eur)(?!\s*/)",  # Decimal with currency (not €/L)
            r"(\d+)\s*(?:€|EUR|euro|eur)(?!\s*/)",         # Integer with currency (not €/L)
        ]
        for pattern in cost_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(",", "."))
                    parsed["total_cost"] = value
                    _LOGGER.debug("Extracted total cost (explicit): %s", value)
                    break
                except:
                    pass
        
        # Smart total cost detection: Numbers 20-99 (or 10-99 with decimals) are likely total costs
        # Only if no explicit total cost was found and no liter suffix
        if "total_cost" not in parsed:
            # Match decimal numbers 10.xx - 99.xx or integers 20-99
            standalone_cost_pattern = r"\b((?:[1-9]\d)[.,]?\d{0,2})\b"
            matches = re.findall(standalone_cost_pattern, text)
            for match in matches:
                # Skip if this number is already used for price_per_liter
                if "price_per_liter" in parsed:
                    price_str = str(parsed["price_per_liter"]).replace(".", ",")
                    if match.replace(",", ".") == str(parsed["price_per_liter"]):
                        continue
                
                try:
                    value = float(match.replace(",", "."))
                    # Total costs typically between 10 and 200 EUR
                    if 10.0 <= value <= 200.0:
                        # Make sure it's not the same as liters
                        if "liters_refueled" in parsed:
                            if abs(value - parsed["liters_refueled"]) < 0.01:
                                continue
                        parsed["total_cost"] = value
                        _LOGGER.debug("Extracted total cost (smart detection): %s", value)
                        break
                except:
                    pass
        
        # Extract odometer
        # Examples: "123456 km", "123.456 km", "KM-Stand: 123456"
        odometer_patterns = [
            r"(?:KM-Stand|Kilometerstand|Odometer|km)[:\s]+(\d+[.,]?\d*)",
            r"(\d{5,7})\s*km",
        ]
        for pattern in odometer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(".", "").replace(",", "."))
                    parsed["odometer_km"] = value
                    break
                except:
                    pass
        
        # Extract station name (simple heuristic)
        # Look for known brands or "Station:" prefix
        station_brands = ["Shell", "Aral", "Esso", "Total", "Jet", "OMV", "Agip"]
        for brand in station_brands:
            if brand.lower() in text.lower():
                parsed["station_name"] = brand
                break
        
        # Check for station keyword
        if "station_name" not in parsed:
            station_match = re.search(r"(?:Station|Tankstelle)[:\s]+([A-Za-zäöüÄÖÜß\s]+)", text, re.IGNORECASE)
            if station_match:
                parsed["station_name"] = station_match.group(1).strip()
        
        # Calculate price_per_liter if we have total_cost and liters but no explicit price
        if "price_per_liter" not in parsed and "total_cost" in parsed and "liters_refueled" in parsed:
            try:
                calculated_price = parsed["total_cost"] / parsed["liters_refueled"]
                # Sanity check: fuel price should be between 1.0 and 3.0 €/L
                if 1.0 <= calculated_price <= 3.0:
                    parsed["price_per_liter"] = round(calculated_price, 3)
                    _LOGGER.debug(
                        "Calculated price/liter: %.3f (from total %.2f / liters %.2f)",
                        calculated_price,
                        parsed["total_cost"],
                        parsed["liters_refueled"]
                    )
            except (ZeroDivisionError, ValueError):
                pass
        
        # Calculate total_cost if we have price_per_liter and liters but no explicit total
        if "total_cost" not in parsed and "price_per_liter" in parsed and "liters_refueled" in parsed:
            try:
                calculated_total = parsed["price_per_liter"] * parsed["liters_refueled"]
                parsed["total_cost"] = round(calculated_total, 2)
                _LOGGER.debug(
                    "Calculated total cost: %.2f (from price %.3f * liters %.2f)",
                    calculated_total,
                    parsed["price_per_liter"],
                    parsed["liters_refueled"]
                )
            except (ValueError):
                pass
        
        _LOGGER.debug("Parsed data from text: %s", parsed)
        return parsed

    async def _save_station_to_poi(
        self,
        station_name: str,
        station_address: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> None:
        """Save a gas station to POI cache for trip tracking.
        
        Args:
            station_name: Name of the gas station
            station_address: Optional address of the station
            latitude: Optional latitude coordinate
            longitude: Optional longitude coordinate
        """
        try:
            from .utils.storage import get_pois, add_poi
            from .utils.poi_management import find_poi_at_location, suggest_poi_from_location
            
            # Get existing POIs
            existing_pois = await get_pois(self.hass, self.config_entry)
            
            # Check if this station already exists as POI
            if latitude and longitude:
                existing_poi = find_poi_at_location(
                    latitude, longitude, existing_pois, max_distance_m=200.0
                )
                if existing_poi:
                    _LOGGER.debug("Station already exists as POI: %s", existing_poi.get("name"))
                    return
            
            # Check if a POI with this name already exists
            for poi in existing_pois:
                if poi.get("name", "").lower() == station_name.lower():
                    _LOGGER.debug("Station with name '%s' already exists in POI cache", station_name)
                    return
            
            # Create new POI for the gas station
            if latitude and longitude:
                poi_data = suggest_poi_from_location(
                    latitude, longitude, station_address, poi_type="gas_station"
                )
                poi_data["name"] = station_name
            else:
                # Create POI without coordinates (will be updated later if location is found)
                poi_data = {
                    "name": station_name,
                    "latitude": None,
                    "longitude": None,
                    "radius_m": 200.0,
                    "address": station_address,
                    "poi_type": "gas_station",
                    "category": None,
                    "icon": "mdi:gas-station",
                    "visit_count": 0,
                    "is_favorite": False,
                    "notes": "Auto-added from refueling data",
                }
            
            poi_id = await add_poi(self.hass, self.config_entry, poi_data)
            _LOGGER.info("Added gas station '%s' to POI cache (ID: %s)", station_name, poi_id)
            
        except Exception as err:
            _LOGGER.warning("Failed to save station to POI cache: %s", err)

    async def _perform_ocr(self, file_id: str) -> str | None:
        """Perform OCR on a photo file.
        
        This is a placeholder for OCR implementation.
        
        Args:
            file_id: Telegram file ID
            
        Returns:
            Extracted text or None
        """
        # TODO: Implement actual OCR
        # Options documented in the documentation
        _LOGGER.warning("OCR not yet implemented. File ID: %s", file_id)
        return "OCR not yet implemented - please implement using one of the suggested services"

    async def _transcribe_voice(self, file_id: str) -> str | None:
        """Transcribe a voice message.
        
        This is a placeholder for speech-to-text implementation.
        
        Args:
            file_id: Telegram file ID
            
        Returns:
            Transcribed text or None
        """
        # TODO: Implement actual speech-to-text
        # Options documented in the documentation
        _LOGGER.warning("Speech-to-text not yet implemented. File ID: %s", file_id)
        return "Speech-to-text not yet implemented - please implement using one of the suggested services"

    async def _send_telegram_message(self, message: str) -> None:
        """Send a message via Telegram.
        
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

    async def _answer_callback_query(
        self,
        callback_query_id: str,
        text: str,
    ) -> None:
        """Answer a callback query (inline keyboard button press).
        
        Args:
            callback_query_id: Callback query ID
            text: Answer text (shown as notification)
        """
        try:
            await self.hass.services.async_call(
                "telegram_bot",
                "answer_callback_query",
                {
                    "callback_query_id": callback_query_id,
                    "message": text,
                },
                blocking=True,
            )
        except Exception as err:
            _LOGGER.error("Failed to answer callback query: %s", err)

    async def notify_refueling_added(self, refuel_id: int, refuel_data: dict) -> None:
        """Public method to trigger refueling notification.
        
        This can be called directly when a refueling is added via service.
        
        Args:
            refuel_id: ID of the refueling event
            refuel_data: Refueling event data
        """
        # Trigger the event
        self.hass.bus.async_fire(
            f"{DOMAIN}_refueling_added",
            {
                "config_entry_id": self.config_entry.entry_id,
                "refuel_id": refuel_id,
                "refuel_data": refuel_data,
            }
        )
