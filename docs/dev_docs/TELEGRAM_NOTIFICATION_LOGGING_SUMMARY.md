# Telegram Notification Troubleshooting - Summary

## Issue Reported
Despite PR #116 implementation, the test flow creates a refueling event but no Telegram notification is sent. No error messages appear in the system log.

## Root Cause Analysis

The primary issue is likely that the **Home Assistant `telegram_bot` integration is not configured or not loaded** when haFWCMA initializes.

### Critical Dependency Check

The `TelegramRefuelingHandler` performs this check during setup:

```python
if "telegram_bot" not in self.hass.config.components:
    _LOGGER.warning(
        "telegram_bot integration NOT FOUND! "
        "Bidirectional refueling features will not be available."
    )
    return False
```

If this check fails:
- ❌ Event listeners are NOT registered
- ❌ `hafwcma_refueling_added` events are NOT handled
- ❌ NO notifications are sent
- ❌ Previous logging was insufficient to diagnose this

## Solution Implemented

### Enhanced Logging

Comprehensive logging has been added throughout the notification flow to enable proper diagnosis:

#### 1. Setup Phase Logging

**Location:** `telegram_refueling_handler.py:async_setup()`

```
INFO: Setting up Telegram refueling handler. Checking for telegram_bot integration...
DEBUG: Available integrations: alarm_control_panel, automation, ...
WARNING: telegram_bot integration NOT FOUND! [if missing]
INFO: telegram_bot integration found - proceeding with event listener setup [if found]
DEBUG: Registered listener for hafwcma_refueling_added events
DEBUG: Registered listener for telegram_text events
DEBUG: Registered listener for telegram_callback events
DEBUG: Registered listener for telegram_photo events
DEBUG: Registered listener for telegram_voice events
INFO: Telegram refueling handler successfully initialized with 5 event listeners
```

**In main init:**
```
INFO: ✅ Telegram refueling handler successfully initialized and ready for notifications
ERROR: ❌ Telegram refueling handler setup FAILED. Refueling notifications will NOT be sent.
```

#### 2. Event Processing Logging

**Location:** `telegram_refueling_handler.py:_handle_new_refueling_event()`

```
INFO: Received refueling_added event
DEBUG: Event config_entry_id: abc123, Handler config_entry_id: abc123
INFO: Processing new refueling event: ID=123, liters=45.50, fuel_type=e10
INFO: Creating task to send Telegram notification for refuel ID 123
```

#### 3. Notification Sending Logging

**Location:** `telegram_refueling_handler.py:_send_refueling_notification()`

```
INFO: Preparing Telegram notification for refuel ID 123 (chat_id: 12345678)
INFO: Sending notification via telegram_bot service (target: 12345678, parse_mode: HTML)
DEBUG: Notification message: ⛽ <b>Neuer Tankvorgang erkannt!</b>...
DEBUG: telegram_bot service call returned: {...}
INFO: Notification sent successfully with message_id: 456
INFO: Refueling notification sent for ID 123
```

**On Error:**
```
ERROR: Failed to send refueling notification for ID 123: [error message] (type: ServiceNotFound)
    [Full stack trace]
```

#### 4. Button Test Logging

**Location:** `button.py:_test_bidirectional_flow()`

```
INFO: Test refueling created with ID 123
INFO: Firing hafwcma_refueling_added event (config_entry_id: abc123, refuel_id: 123)
INFO: Event fired successfully. Notification should be sent shortly.
```

## Parse Mode Question

**Answer:** The parse mode setting in the telegram_bot integration configuration does NOT affect haFWCMA notifications.

haFWCMA explicitly specifies `parse_mode: "HTML"` in every service call:

```python
await self.hass.services.async_call(
    "telegram_bot",
    "send_message",
    {
        "target": self.chat_id,
        "message": message,
        "parse_mode": "html",  # ← Always html
        "inline_keyboard": inline_keyboard,
    }
)
```

**Supported formatting:**
- `<b>text</b>` for bold
- Basic HTML only, no complex formatting

**Compatibility:** Works with all telegram_bot parse mode settings (Markdown, MarkdownV2, HTML, Plain Text) because the parse mode is explicitly set per message.

## Diagnostic Steps for Users

### 1. Check Integration Status

**Look for this in logs after restart:**
```
[custom_components.hafwcma] Setting up Telegram refueling handler. Checking for telegram_bot integration...
```

**If you see:**
```
WARNING: telegram_bot integration NOT FOUND!
```

**Solution:** Configure telegram_bot integration in Home Assistant:
1. Go to Settings → Devices & Services → Add Integration
2. Search for "Telegram Bot"
3. Configure with your bot token
4. Restart Home Assistant

### 2. Verify Configuration

**Required in `configuration.yaml`:**
```yaml
telegram_bot:
  - platform: polling
    api_key: "YOUR_BOT_TOKEN"
    allowed_chat_ids:
      - 12345678  # Your chat ID
```

### 3. Enable Debug Logging

**Add to `configuration.yaml`:**
```yaml
logger:
  default: info
  logs:
    custom_components.hafwcma: debug
    custom_components.hafwcma.telegram_refueling_handler: debug
    custom_components.hafwcma.button: debug
```

Restart Home Assistant, then run the test.

### 4. Run Test Flow

1. Press the "Telegram API Test" button in Home Assistant
2. Watch the logs in real-time
3. Check Telegram for the notification

**Expected log sequence:**
```
[button] Test refueling created with ID 123
[button] Firing hafwcma_refueling_added event...
[button] Event fired successfully
[telegram_refueling_handler] Received refueling_added event
[telegram_refueling_handler] Processing new refueling event: ID=123
[telegram_refueling_handler] Creating task to send Telegram notification
[telegram_refueling_handler] Preparing Telegram notification for refuel ID 123
[telegram_refueling_handler] Sending notification via telegram_bot service
[telegram_refueling_handler] Notification sent successfully with message_id: 456
```

### 5. Manual Service Test

Test telegram_bot directly in Developer Tools → Services:

```yaml
service: telegram_bot.send_message
data:
  target: 12345678
  message: "Manual test message"
  parse_mode: "HTML"
```

If this fails, the problem is with telegram_bot configuration, not haFWCMA.

## Files Modified

1. **custom_components/hafwcma/telegram_refueling_handler.py**
   - Enhanced async_setup() with detailed integration check
   - Enhanced _handle_new_refueling_event() with event details
   - Enhanced _send_refueling_notification() with comprehensive logging

2. **custom_components/hafwcma/__init__.py**
   - Enhanced handler initialization logging
   - Added success/failure indicators
   - Added event firing logs in services

3. **custom_components/hafwcma/button.py**
   - Enhanced test flow logging
   - Added event firing details

4. **TELEGRAM_TROUBLESHOOTING_DE.md** (NEW)
   - Complete German troubleshooting guide
   - All log examples
   - Common issues and solutions

## Expected Outcome

After these changes:
- ✅ Clear visibility into why notifications might not be sent
- ✅ Easy identification of telegram_bot integration issues
- ✅ Detailed trace of the notification flow
- ✅ Better error messages and stack traces
- ✅ Comprehensive troubleshooting documentation

## No Code Behavior Changes

**Important:** These changes only add logging. The actual notification logic is unchanged:
- Same parse mode (HTML)
- Same service calls
- Same event handling
- Same error handling

The only difference is that issues are now properly logged and visible.

---

**Created:** 2024-02-16
**Issue:** Telegram notifications not sent after refueling
**Status:** Logging enhanced, ready for user diagnosis
