# Telegram Notification Troubleshooting - English Guide

## Issue Summary
Despite PR #116 implementation, the test flow creates a refueling event but no Telegram notification is sent. No error messages appear in the system log.

## Root Cause

The primary issue is likely that the **Home Assistant `telegram_bot` integration is not configured or not loaded** when haFWCMA initializes.

### Critical Check

The `TelegramRefuelingHandler` performs this check during setup:

```python
if "telegram_bot" not in self.hass.config.components:
    _LOGGER.warning("telegram_bot integration NOT FOUND!")
    return False
```

If this check fails:
- ❌ Event listeners are NOT registered
- ❌ `hafwcma_refueling_added` events are NOT handled
- ❌ NO notifications are sent
- ❌ Previous logging was insufficient to diagnose this

## Enhanced Logging (Solution Implemented)

Comprehensive logging has been added throughout the notification flow:

### 1. Setup Phase Logging

```
INFO: Setting up Telegram refueling handler. Checking for telegram_bot integration...
DEBUG: Available integrations: alarm_control_panel, automation, ...
WARNING: telegram_bot integration NOT FOUND! [if missing]
INFO: telegram_bot integration found - proceeding with event listener setup [if present]
DEBUG: Registered listener for hafwcma_refueling_added events
DEBUG: Registered listener for telegram_text events
INFO: Telegram refueling handler successfully initialized with 5 event listeners
INFO: ✅ Telegram refueling handler successfully initialized and ready for notifications
```

### 2. Event Processing Logging

```
INFO: Received refueling_added event
DEBUG: Event config_entry_id: abc123, Handler config_entry_id: abc123
INFO: Processing new refueling event: ID=123, liters=45.50, fuel_type=e10
INFO: Creating task to send Telegram notification for refuel ID 123
```

### 3. Notification Sending Logging

```
INFO: Preparing Telegram notification for refuel ID 123 (chat_id: 12345678)
INFO: Sending notification via telegram_bot service (target: 12345678, parse_mode: HTML)
DEBUG: Notification message: ⛽ <b>Neuer Tankvorgang erkannt!</b>...
INFO: Notification sent successfully with message_id: 456
INFO: Refueling notification sent for ID 123
```

### 4. Error Logging

```
ERROR: Failed to send refueling notification for ID 123: [error message] (type: ServiceNotFound)
    [Full exception stack trace]
```

## Parse Mode Question

**Question:** Does the parse mode setting in telegram_bot integration matter?

**Answer:** NO. The parse mode setting in the telegram_bot integration configuration does NOT affect haFWCMA notifications.

haFWCMA explicitly specifies `parse_mode: "HTML"` in every service call:

```python
await self.hass.services.async_call(
    "telegram_bot",
    "send_message",
    {
        "target": self.chat_id,
        "message": message,
        "parse_mode": "html",  # ← Always html, regardless of global setting
        "inline_keyboard": inline_keyboard,
    }
)
```

**Compatibility:** Works with all telegram_bot parse mode settings:
- ✅ Markdown (deprecated)
- ✅ MarkdownV2
- ✅ HTML
- ✅ Plain Text

## Diagnostic Steps

### 1. Check Integration Status

After restart, look for this in logs:
```
[custom_components.hafwcma] Setting up Telegram refueling handler. Checking for telegram_bot integration...
```

**If you see:**
```
WARNING: telegram_bot integration NOT FOUND!
```

**Then:** Configure telegram_bot integration:
1. Go to Settings → Devices & Services → Add Integration
2. Search for "Telegram Bot"
3. Add your bot token and chat ID
4. Restart Home Assistant

### 2. Verify Configuration

Required in `configuration.yaml`:
```yaml
telegram_bot:
  - platform: polling
    api_key: "YOUR_BOT_TOKEN"
    allowed_chat_ids:
      - 12345678  # Your chat ID from @userinfobot
```

### 3. "Access denied from 127.0.0.1" Error

**Symptom:** The following error appears in Home Assistant logs:
```
Logger: homeassistant.components.telegram_bot.webhooks
Access denied from 127.0.0.1
```

**Cause:** This error originates from the Home Assistant telegram_bot integration itself (not from haFWCMA). It occurs when the telegram_bot integration is configured in webhook mode and receives requests from untrusted IP addresses.

**What happens:**
- When you press inline keyboard buttons (✅ Confirm, ✏️ Edit, 🗑️ Delete), Telegram sends a webhook callback to Home Assistant
- If Home Assistant runs behind a reverse proxy, the request appears to come from 127.0.0.1
- Without proper `trusted_networks` configuration, this request is blocked
- Buttons don't work because callbacks cannot be processed

**Solution 1: Use Polling (Easiest)**

If you don't have a publicly accessible Home Assistant instance, use polling instead of webhooks:

```yaml
telegram_bot:
  - platform: polling
    api_key: "YOUR_BOT_TOKEN"
    allowed_chat_ids:
      - 12345678  # Your chat ID
```

**Solution 2: Configure Trusted Networks (For Webhook Mode)**

If you want to use webhooks (e.g., with Nabu Casa or your own public URL), add trusted networks:

```yaml
telegram_bot:
  - platform: webhooks
    api_key: "YOUR_BOT_TOKEN"
    allowed_chat_ids:
      - 12345678  # Your chat ID
    trusted_networks:
      - 127.0.0.1/32          # Local reverse proxy
      - 149.154.160.0/20      # Telegram IP range 1
      - 91.108.4.0/22         # Telegram IP range 2
      # If using Cloudflare: Add Cloudflare IP ranges
```

**Important:**
- After configuration changes: **Fully restart Home Assistant** (not just reload configuration)
- If using Nabu Casa: Add `127.0.0.1/32` to trusted_networks
- If using your own reverse proxy: Add the proxy's IP address

**Further Information:**
- [Home Assistant telegram_bot Documentation](https://www.home-assistant.io/integrations/telegram_bot/)
- [GitHub Issue about this problem](https://github.com/home-assistant/core/issues/101980)

### 4. Inline Keyboard Buttons - Text and Symbols

**Question:** Why do buttons show "✅ Confirm" instead of just "✅"?

**Answer:** Buttons intentionally display **Emoji + Text** together. This is:
- ✅ **Standard in Telegram bots**: Most professional Telegram bots use text labels with emojis
- ✅ **Better user experience**: Clear labels prevent misunderstandings
- ✅ **Accessibility**: Screen readers can read text, but not all emojis are unambiguous

**Button Labels:**
- `✅ Confirm` - Confirms the refueling with automatically detected data
- `✏️ Edit` - Allows manual input/correction of data
- `🗑️ Delete` - Deletes the refueling completely

**Technical Background:**
Buttons are sent as `inline_keyboard` in this format:
```python
{
    "text": "✅ Confirm",
    "callback_data": "refuel_confirm_123"
}
```

This follows the official Telegram Bot API specification and best practices for Telegram bot development.

**Note:** If buttons don't work at all or show "Loading..." indefinitely, see the "Access denied from 127.0.0.1" error above.

### 5. Replying to Telegram Messages

**Problem:** "When I reply to the message, nothing is recognized"

**Solution:** To correctly match a reply, use one of the following methods:

**Method 1: Mention Refuel ID in Text (Recommended)**

Include the refueling number (#15, #16, etc.) in your reply:
```
Refueling #15: 45.5 liters, 1.599 €/liter, Shell
```

The integration automatically detects `#15` and correctly assigns the data.

**Method 2: Use Inline Keyboard Buttons (Easiest)**

Use the buttons in the notification:
- Press `✏️ Edit`, then enter data
- No manual matching needed

**Method 3: Time-based Matching**

If you reply within a few minutes of receiving a notification, the reply is automatically assigned to the most recent pending refueling.

**Important:**
- The integration **cannot** retrieve message_id from sent messages (Home Assistant API limitation)
- Therefore, "Reply to message" doesn't work reliably
- **Use the #-number or buttons instead**

### 6. Enable Debug Logging

Add to `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.hafwcma: debug
    custom_components.hafwcma.telegram_refueling_handler: debug
    custom_components.hafwcma.button: debug
```

Restart Home Assistant.

### 7. Run Test Flow

1. Press the "Telegram API Test" button
2. Watch logs in real-time
3. Check Telegram for notification

**Expected log sequence:**
```
[button] Test refueling created with ID 123
[button] Firing hafwcma_refueling_added event...
[telegram_refueling_handler] Received refueling_added event
[telegram_refueling_handler] Processing new refueling event: ID=123
[telegram_refueling_handler] Preparing Telegram notification
[telegram_refueling_handler] Sending notification via telegram_bot service
[telegram_refueling_handler] Notification sent successfully with message_id: 456
```

### 8. Manual Service Test

Test telegram_bot directly in Developer Tools → Services:

```yaml
service: telegram_bot.send_message
data:
  target: 12345678
  message: "Manual test"
  parse_mode: "HTML"
```

If this fails, the problem is with telegram_bot, not haFWCMA.

## Common Issues and Solutions

### Issue 1: telegram_bot not found
**Symptoms:** Log shows "telegram_bot integration NOT FOUND"
**Solution:** Install and configure telegram_bot integration

### Issue 2: Wrong chat ID
**Symptoms:** Log shows "Telegram not configured (chat_id: missing)"
**Solution:** 
- Send `/start` to @userinfobot on Telegram to get your chat ID
- Update haFWCMA configuration with correct chat ID

### Issue 3: Different config entry
**Symptoms:** Log shows "Ignoring event from different config entry"
**Solution:** Ensure refueling is created for the correct vehicle instance

### Issue 4: Service call fails
**Symptoms:** Log shows "Failed to send refueling notification"
**Solution:**
- Check telegram_bot service logs
- Verify bot is running and reachable
- Test bot with manual service call

## Files Modified

1. `custom_components/hafwcma/telegram_refueling_handler.py`
   - Enhanced setup logging with integration check
   - Enhanced event handling logging
   - Enhanced notification sending logging
   - Added MAX_LOG_MESSAGE_LENGTH constant

2. `custom_components/hafwcma/__init__.py`
   - Enhanced handler initialization logging
   - Added success/failure indicators (✅/❌)
   - Added event firing logs

3. `custom_components/hafwcma/button.py`
   - Enhanced test flow logging
   - Added event firing details

4. `TELEGRAM_TROUBLESHOOTING_DE.md` (German version)
5. `TELEGRAM_NOTIFICATION_LOGGING_SUMMARY.md` (Technical summary)

## What Changed

### Before
- Minimal logging
- Silent failures when telegram_bot missing
- Difficult to diagnose issues
- No documentation

### After
- ✅ Comprehensive logging at every step
- ✅ Clear warnings when telegram_bot missing
- ✅ Easy identification of issues
- ✅ Detailed troubleshooting guide
- ✅ Better error messages with stack traces

### What Didn't Change
- ❌ No behavior changes
- ❌ No parse mode changes (still HTML)
- ❌ No logic changes
- ❌ Only logging additions

## Expected Outcome

After these changes:
- ✅ Clear visibility into why notifications might not be sent
- ✅ Easy identification of telegram_bot integration issues
- ✅ Detailed trace of the notification flow
- ✅ Better error messages and stack traces
- ✅ Comprehensive troubleshooting documentation
- ✅ Faster diagnosis and resolution of issues

## Security

✅ **CodeQL Analysis:** No security vulnerabilities found
✅ **Code Review:** No issues found
✅ **Syntax Check:** All files validated

---

**Created:** 2024-02-16
**Status:** Complete and tested
**Language:** English (German version: TELEGRAM_TROUBLESHOOTING_DE.md)
