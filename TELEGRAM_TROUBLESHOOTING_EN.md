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
        "parse_mode": "HTML",  # ← Always HTML, regardless of global setting
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

### 3. Enable Debug Logging

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

### 4. Run Test Flow

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

### 5. Manual Service Test

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
