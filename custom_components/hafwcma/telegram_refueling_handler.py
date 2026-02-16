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

import json
import logging
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
        
        # Build notification message
        message_parts = ["⛽ <b>Neuer Tankvorgang erkannt!</b>\n"]
        
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
            message_parts.append(f"🏪 Tankstelle: {station_name}")
        else:
            missing_fields.append("Tankstellenname")
        
        station_address = refuel_data.get("station_address")
        if station_address:
            message_parts.append(f"📍 Adresse: {station_address}")
        
        fuel_type = refuel_data.get("fuel_type")
        if fuel_type:
            message_parts.append(f"⚡ Kraftstoffart: {fuel_type}")
        
        # Show missing fields
        if missing_fields:
            message_parts.append(f"\n❓ <b>Fehlende Informationen:</b>")
            message_parts.append(", ".join(missing_fields))
            message_parts.append(
                "\n💡 <b>Wie können Sie antworten:</b>\n"
                "• Antworten Sie mit Text (z.B. '45.5 L, 1.599 €/L, Shell')\n"
                "• Senden Sie ein Foto der Quittung\n"
                "• Senden Sie eine Sprachnachricht\n"
                "• Nutzen Sie die Schaltflächen unten"
            )
        
        message = "\n".join(message_parts)
        
        # Create inline keyboard for quick actions
        inline_keyboard = [
            [
                {"text": "✅ Bestätigen", "callback_data": f"refuel_confirm_{refuel_id}"},
                {"text": "✏️ Bearbeiten", "callback_data": f"refuel_edit_{refuel_id}"},
            ],
            [
                {"text": "🗑️ Löschen", "callback_data": f"refuel_delete_{refuel_id}"},
            ],
        ]
        
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
        reply_to_message_id = event_data.get("reply_to_message", {}).get("message_id")
        
        # Check if this is a reply to one of our refueling notifications
        refuel_id = self._find_refuel_by_message_id(reply_to_message_id)
        
        if refuel_id:
            _LOGGER.debug("Received text response for refuel ID %s: %s", refuel_id, text[:50])
            self.hass.async_create_task(
                self._process_text_response(refuel_id, text)
            )
        else:
            _LOGGER.debug("Text message not linked to any pending refueling")

    @callback
    def _handle_telegram_callback_response(self, event: Event) -> None:
        """Handle inline keyboard button presses.
        
        Args:
            event: Telegram callback event
        """
        event_data = event.data
        
        # Only handle events from our configured chat
        if str(event_data.get("chat_id")) != str(self.chat_id):
            return
        
        callback_data = event_data.get("data", "")
        
        _LOGGER.debug("Received callback: %s", callback_data)
        
        # Parse callback data
        if callback_data.startswith("refuel_"):
            parts = callback_data.split("_")
            if len(parts) >= 3:
                action = parts[1]
                refuel_id = int(parts[2])
                
                self.hass.async_create_task(
                    self._process_callback_action(refuel_id, action, event_data)
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
        reply_to_message_id = event_data.get("reply_to_message", {}).get("message_id")
        
        # Get the largest photo (best quality)
        file_id = None
        if photo and len(photo) > 0:
            file_id = photo[-1].get("file_id")
        
        refuel_id = self._find_refuel_by_message_id(reply_to_message_id)
        
        if refuel_id and file_id:
            _LOGGER.debug("Received photo response for refuel ID %s", refuel_id)
            self.hass.async_create_task(
                self._process_photo_response(refuel_id, file_id, caption)
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
        reply_to_message_id = event_data.get("reply_to_message", {}).get("message_id")
        
        refuel_id = self._find_refuel_by_message_id(reply_to_message_id)
        
        if refuel_id and file_id:
            _LOGGER.debug("Received voice response for refuel ID %s", refuel_id)
            self.hass.async_create_task(
                self._process_voice_response(refuel_id, file_id)
            )

    def _find_refuel_by_message_id(self, message_id: int | None) -> int | None:
        """Find refuel ID by Telegram message ID.
        
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
        from .utils.storage import update_refueling_record
        
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
        
        # Send confirmation
        await self._send_telegram_message(
            f"✅ Daten für Tankvorgang #{refuel_id} aktualisiert!\n\n"
            f"Erkannte Daten:\n{json.dumps(parsed_data, indent=2, ensure_ascii=False)}"
        )
        
        # Remove from pending
        self._pending_refuelings.pop(refuel_id, None)

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
            
        elif action == "edit":
            # Prompt for editing
            await self._answer_callback_query(
                event_data.get("id"),
                "✏️ Bitte senden Sie die aktualisierten Daten"
            )
            
            await self._send_telegram_message(
                f"✏️ Bitte antworten Sie mit den aktualisierten Daten für Tankvorgang #{refuel_id}:\n\n"
                "Beispiel: 45.5 Liter, 1.599 €/Liter, Shell Tankstelle"
            )
            
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
            f"OCR-Text:\n{ocr_text or 'Keine Daten erkannt'}\n\n"
            f"Erkannte Daten:\n{json.dumps(parsed_data, indent=2, ensure_ascii=False)}"
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
            f"Transkription:\n{transcription or 'Keine Daten erkannt'}\n\n"
            f"Erkannte Daten:\n{json.dumps(parsed_data, indent=2, ensure_ascii=False)}"
        )
        
        # Remove from pending
        self._pending_refuelings.pop(refuel_id, None)

    async def _parse_refuel_text(self, text: str) -> dict[str, Any]:
        """Parse unstructured text to extract refueling data.
        
        Uses pattern matching and AI to extract structured data.
        
        Args:
            text: Unstructured text input
            
        Returns:
            Dictionary with extracted data
        """
        import re
        
        parsed = {}
        
        if not text:
            return parsed
        
        # Extract liters (various formats)
        # Examples: "45.5 L", "45,5 Liter", "45.5L", "45.5 liters"
        liter_patterns = [
            r"(\d+[.,]\d+)\s*(?:L|l|Liter|liter)",
            r"(\d+)\s*(?:L|l|Liter|liter)",
        ]
        for pattern in liter_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1).replace(",", "."))
                    parsed["liters_refueled"] = value
                    break
                except:
                    pass
        
        # Extract price per liter
        # Examples: "1.599 €/L", "1,599€/Liter", "1.59 EUR/l"
        price_patterns = [
            r"(\d+[.,]\d+)\s*(?:€|EUR|euro)?\s*/\s*(?:L|l|Liter)",
            r"Preis[:\s]+(\d+[.,]\d+)",
        ]
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(",", "."))
                    parsed["price_per_liter"] = value
                    break
                except:
                    pass
        
        # Extract total cost
        # Examples: "71.96 €", "71,96 EUR", "Total: 71.96"
        cost_patterns = [
            r"(?:Gesamt|Total|Summe)[:\s]+(\d+[.,]\d+)",
            r"(\d+[.,]\d+)\s*(?:€|EUR|euro)(?!\s*/)",
        ]
        for pattern in cost_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(",", "."))
                    parsed["total_cost"] = value
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
        
        _LOGGER.debug("Parsed data from text: %s", parsed)
        return parsed

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
