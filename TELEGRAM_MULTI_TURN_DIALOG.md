# Telegram Multi-Turn Dialog Implementation

## Problem Solved

### Issue 1: Buttons Showing "text" Instead of Labels

**Problem:** Inline keyboard buttons were displaying the literal text "text" three times instead of showing the proper button labels like "✅ Bestätigen", "✏️ Bearbeiten", "🗑️ Löschen".

**Root Cause:** The inline keyboard was using the wrong format for Home Assistant's `telegram_bot` service. The code was using Python dictionary format:
```python
{"text": "✅ Bestätigen", "callback_data": "refuel_confirm_15"}
```

**Solution:** Changed to the array format expected by Home Assistant:
```python
["✅ Bestätigen", "refuel_confirm_15"]
```

### Issue 2: No Multi-Turn Dialog Support

**Problem:** After the user provided data once, the dialog was closed. If the initial recognition didn't work or was incomplete, users couldn't continue to provide more data.

**Root Cause:** The code removed the refueling from the pending list immediately after receiving the first response, preventing further interactions.

**Solution:** Implemented a multi-turn dialog system that:
1. Keeps the refueling in pending after each response
2. Sends an updated status message after each data update
3. Shows current data and remaining missing fields
4. Provides buttons to continue editing or mark as done
5. Only closes the dialog when user explicitly clicks "Fertig" (Done) or "Bestätigen" (Confirm)

## How It Works Now

### Initial Notification

When a new refueling event is detected, the user receives a message like:

```
⛽ Tankvorgang #15
Neuer Tankvorgang erkannt!

🕐 Zeitpunkt: 16.02.2026 19:37
📊 Menge: 39.30 Liter
⚡ Kraftstoffart: e10

❓ Fehlende Informationen:
KM-Stand, Preis pro Liter, Gesamtkosten, Tankstellenname

💡 Wie können Sie antworten:
• Antworten Sie mit 'Tankvorgang #15: <Ihre Daten>'
• Oder einfach: '45.5 L, 1.599 €/L, Shell' (wird automatisch zugeordnet)
• Senden Sie ein Foto der Quittung
• Senden Sie eine Sprachnachricht
• Nutzen Sie die Schaltflächen unten

[✅ Fertig] [✏️ Weiter bearbeiten]
[🗑️ Löschen]
```

### User Provides First Response

User sends: `"155000 km, Shell Tankstelle"`

### Updated Status Message

The system processes the data and sends an updated message:

```
⛽ Tankvorgang #15
✅ Daten aktualisiert!

🕐 Zeitpunkt: 16.02.2026 19:37
📊 Menge: 39.30 Liter
🔢 KM-Stand: 155000.0 km
⚡ Kraftstoffart: e10
🏪 Tankstelle: Shell Tankstelle

❓ Fehlende Informationen:
Preis pro Liter, Gesamtkosten

💡 Wie können Sie antworten:
• Antworten Sie mit 'Tankvorgang #15: <Ihre Daten>'
• Oder einfach: '45.5 L, 1.599 €/L, Shell' (wird automatisch zugeordnet)
• Senden Sie ein Foto der Quittung
• Senden Sie eine Sprachnachricht
• Nutzen Sie die Schaltflächen unten

[✅ Fertig] [✏️ Weiter bearbeiten]
[🗑️ Löschen]
```

### User Continues Adding Data

User sends: `"1.599 €/L, 62.78 € total"`

### Final Status Message

```
⛽ Tankvorgang #15
✅ Daten aktualisiert!

🕐 Zeitpunkt: 16.02.2026 19:37
📊 Menge: 39.30 Liter
🔢 KM-Stand: 155000.0 km
💰 Preis/Liter: 1.599 €
💵 Gesamtkosten: 62.78 €
⚡ Kraftstoffart: e10
🏪 Tankstelle: Shell Tankstelle

✅ Alle Daten vollständig!

[✅ Bestätigen] [✏️ Bearbeiten]
[🗑️ Löschen]
```

Notice how the buttons change from "Fertig/Weiter bearbeiten" to "Bestätigen/Bearbeiten" when all data is complete.

## Technical Details

### Inline Keyboard Format

**Before (INCORRECT):**
```python
inline_keyboard = [
    [
        {"text": "✅ Bestätigen", "callback_data": "refuel_confirm_15"},
        {"text": "✏️ Bearbeiten", "callback_data": "refuel_edit_15"},
    ],
    [
        {"text": "🗑️ Löschen", "callback_data": "refuel_delete_15"},
    ],
]
```

**After (CORRECT):**
```python
inline_keyboard = [
    [
        ["✅ Bestätigen", "refuel_confirm_15"],
        ["✏️ Bearbeiten", "refuel_edit_15"],
    ],
    [
        ["🗑️ Löschen", "refuel_delete_15"],
    ],
]
```

### Helper Method: `_build_refuel_status_message`

This new method:
- Takes refuel ID and data
- Builds a formatted status message
- Identifies missing fields
- Returns appropriate inline keyboard buttons based on completion status
- Can be used for both initial notifications and updates

### Multi-Turn Dialog Flow

1. **Initial Notification**
   - User receives notification with detected data
   - Missing fields are highlighted
   - Refueling added to pending list

2. **User Sends Data**
   - Text is parsed to extract structured data
   - Refueling record is updated
   - **Refueling stays in pending list** ← KEY CHANGE

3. **Updated Status Sent**
   - System retrieves updated refueling data
   - Builds new status message with current state
   - Shows remaining missing fields
   - Sends message with appropriate buttons

4. **User Continues or Finishes**
   - User can send more data (loop to step 2)
   - User clicks "Fertig" to finish (even if incomplete)
   - User clicks "Bestätigen" when all data is complete
   - User clicks "Löschen" to delete

5. **Dialog Closed**
   - Refueling removed from pending list
   - No more automatic responses to messages about this refueling

### Button Actions

| Button | Action | Removes from Pending? | Use Case |
|--------|--------|----------------------|----------|
| ✅ Bestätigen | Confirms complete data | Yes | When all required data is present |
| ✅ Fertig | Marks as done | Yes | User wants to finish even with missing data |
| ✏️ Bearbeiten / Weiter bearbeiten | Prompts for more data | No | User wants to add/edit more data |
| 🗑️ Löschen | Deletes refueling | Yes | User wants to remove this entry |

## Code Changes

### File: `custom_components/hafwcma/telegram_refueling_handler.py`

1. **Line 318-328**: Fixed inline keyboard format
2. **Line 725-845**: New `_build_refuel_status_message` helper method
3. **Line 228-250**: Updated `_send_refueling_notification` to use helper
4. **Line 847-935**: Rewrote `_process_text_response` for multi-turn dialog
5. **Line 972-985**: Added "done" action in callback handler
6. **Line 987-1003**: Updated "edit" action to keep dialog open

## Testing Recommendations

### Test 1: Button Labels Display

1. Create a new refueling event
2. Check Telegram notification
3. **Expected:** Buttons show "✅ Bestätigen", "✏️ Bearbeiten", "🗑️ Löschen"
4. **NOT:** "text", "text", "text"

### Test 2: Multi-Turn Data Collection

1. Create refueling with minimal data (e.g., just timestamp and fuel type)
2. Reply with: `"50000 km"`
3. **Expected:** New message showing km-stand updated, still has missing fields
4. Reply with: `"1.499 €/L, Shell"`
5. **Expected:** Another update showing price and station added
6. Continue until all fields filled
7. **Expected:** Final message shows "✅ Alle Daten vollständig!"

### Test 3: Completion Options

**Scenario A: Complete data**
1. Fill all required fields through multiple messages
2. **Expected:** Buttons change to "✅ Bestätigen" and "✏️ Bearbeiten"
3. Click "Bestätigen"
4. **Expected:** Dialog closes, no more responses

**Scenario B: Incomplete data - User wants to finish anyway**
1. Provide partial data
2. **Expected:** Buttons show "✅ Fertig" and "✏️ Weiter bearbeiten"
3. Click "Fertig"
4. **Expected:** Dialog closes with incomplete data saved

**Scenario C: User wants to continue editing**
1. Provide some data
2. Click "✏️ Weiter bearbeiten"
3. **Expected:** Prompt to send more data, dialog stays open
4. Send more data
5. **Expected:** Another update message

### Test 4: Button Presses Work

1. Create refueling
2. Click each button and verify:
   - **✅ Bestätigen/Fertig:** Confirmation message, dialog closes
   - **✏️ Bearbeiten:** Prompt for data, dialog stays open
   - **🗑️ Löschen:** Deletion confirmation, entry removed

## Migration Notes

### For Existing Users

If users have refuelings already in pending state from before this update:
- They will work with the new multi-turn dialog
- Initial buttons might still be in old format (already sent messages can't be edited)
- New responses will use the new format

### Backward Compatibility

- All existing refueling records work unchanged
- The new `_build_refuel_status_message` method handles both old and new data formats
- No database migrations needed

## Future Improvements

### Possible Enhancements

1. **Edit Message Instead of New Message**
   - Currently sends a new message for each update
   - Could use `telegram_bot.edit_message` to update the original
   - Would require storing message_id (not currently available)

2. **Smart Field Detection**
   - Analyze which fields are most commonly missing
   - Prompt specifically for those fields
   - Example: "Noch fehlend: KM-Stand. Bitte senden Sie Ihren aktuellen KM-Stand."

3. **Validation Warnings**
   - Check for suspicious values (e.g., price > 3.00 €/L)
   - Warn user and ask for confirmation
   - Example: "⚠️ Preis 4.50 €/L erscheint ungewöhnlich hoch. Korrekt?"

4. **Multiple Refuelings**
   - Handle case where user has multiple pending refuelings
   - Ask which one to update if ambiguous
   - Example: "Sie haben 2 offene Tankvorgänge. Welchen meinen Sie? #14 oder #15?"

## References

- Home Assistant telegram_bot integration: https://www.home-assistant.io/integrations/telegram_bot/
- Telegram Bot API inline keyboards: https://core.telegram.org/bots/api#inlinekeyboardmarkup
- Related issue: User feedback about button display and dialog flow

---

**Implementation Date:** 2026-02-16  
**Version:** Post-PR-fix  
**Status:** ✅ Implemented and ready for testing
