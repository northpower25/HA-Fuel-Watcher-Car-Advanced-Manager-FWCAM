# Telegram Integration Setup Guide

## Overview

haFWCMA supports Telegram notifications for fuel prices, refueling recommendations, and tank alerts. To enable **bidirectional** communication (receiving commands from you), you need to configure both:

1. **haFWCMA Telegram settings** - For sending notifications
2. **Home Assistant's `telegram_bot` integration** - For receiving commands (optional but recommended)

## Quick Setup (Send-Only Notifications)

If you only want to **receive** notifications from haFWCMA (no bidirectional features), you only need to configure Telegram in haFWCMA:

1. Create a Telegram bot using [@BotFather](https://t.me/botfather)
2. Get your Chat ID (see below)
3. Enter Bot Token and Chat ID in haFWCMA configuration
4. Test the connection during setup

**That's it!** haFWCMA can now send you notifications.

## Full Setup (Bidirectional Communication)

For advanced features like logging refueling via Telegram commands or querying fuel status, follow these steps:

### Step 1: Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the instructions
3. Choose a name and username for your bot
4. **Save the API token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Get Your Chat ID

You need your Chat ID to authorize communication:

**Method 1: Using a Bot**
1. Search for [@userinfobot](https://t.me/userinfobot) in Telegram
2. Start a conversation with it
3. It will send you your Chat ID (a number like `123456789`)

**Method 2: Using Telegram API**
1. Send a message to your newly created bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for `"chat":{"id":123456789}` in the response

### Step 3: Configure haFWCMA

During haFWCMA setup or in the options flow:

1. **Telegram Bot Token**: Enter your bot token from Step 1
2. **Telegram Chat ID**: Enter your Chat ID from Step 2
3. Click **Submit** and test the connection

You should receive a test message from your bot!

### Step 4: Configure Home Assistant's telegram_bot Integration

To enable bidirectional features, add this to your `configuration.yaml`:

```yaml
# Polling method (recommended for most users)
telegram_bot:
  - platform: polling
    api_key: YOUR_BOT_TOKEN_HERE
    allowed_chat_ids:
      - YOUR_CHAT_ID_HERE
```

**Alternative: Webhooks** (requires public URL with SSL):

```yaml
telegram_bot:
  - platform: webhooks
    api_key: YOUR_BOT_TOKEN_HERE
    allowed_chat_ids:
      - YOUR_CHAT_ID_HERE
    url: https://your-domain.com/api/telegram_webhooks
```

**Important Notes:**
- Use the **same Bot Token** and **Chat ID** as in haFWCMA
- Restart Home Assistant after editing `configuration.yaml`
- The `telegram_bot` integration uses polling/webhooks to receive messages
- haFWCMA will automatically detect and use this integration

### Step 5: Restart Home Assistant

After adding the `telegram_bot` configuration:

1. Go to **Settings** → **System** → **Restart**
2. Wait for Home Assistant to restart
3. Check **Settings** → **Devices & Services** → **Integrations**
4. You should see "Telegram Bot" listed

### Step 6: Test Bidirectional Communication

Send these commands to your bot in Telegram:

- `/help` - Show available commands
- `/status` - Display current vehicle and fuel status
- `/refuel` - Log a refueling event (coming soon)

## Understanding the Setup

### Why Two Configurations?

| Component | Purpose | Required for |
|-----------|---------|--------------|
| **haFWCMA Telegram Config** | Sends notifications from HA to you | All Telegram features |
| **HA telegram_bot Integration** | Receives commands from you to HA | Bidirectional features only |

### Without telegram_bot Integration

- ✅ Receive fuel price alerts
- ✅ Receive refueling recommendations
- ✅ Receive low tank warnings
- ❌ Cannot send commands to haFWCMA
- ❌ Cannot log refueling via Telegram
- ❌ Cannot query fuel status

### With telegram_bot Integration

- ✅ All notification features
- ✅ Send commands to haFWCMA (`/help`, `/status`, etc.)
- ✅ Log refueling events via Telegram (coming soon)
- ✅ Interactive queries and responses

## Avoiding "Conflict: terminated by other getUpdates request" Error

**This error occurs when multiple applications try to use `getUpdates` with the same bot.**

### Solutions:

1. **Use the same bot for both haFWCMA and telegram_bot** (Recommended)
   - Configure both with the same Bot Token
   - Only `telegram_bot` uses polling/webhooks
   - haFWCMA sends messages via HA's service
   - No conflicts!

2. **Use separate bots** (Not recommended)
   - Create two different bots in @BotFather
   - Use one for haFWCMA (send-only)
   - Use another for telegram_bot (bidirectional)
   - More complex, no real benefit

3. **Don't configure telegram_bot** (Limited features)
   - Only configure Telegram in haFWCMA
   - Send-only notifications work fine
   - No bidirectional features

## Polling vs. Webhooks

### Polling (Recommended for Most Users)

**Pros:**
- ✅ Works without public URL
- ✅ Works behind NAT/firewall
- ✅ Easy to set up
- ✅ No SSL certificate needed

**Cons:**
- ❌ Slightly higher latency (1-2 seconds)
- ❌ Uses more API calls

**Use when:** You access Home Assistant via local network or don't have a public domain.

### Webhooks (Advanced)

**Pros:**
- ✅ Instant message delivery
- ✅ Lower API usage
- ✅ More efficient

**Cons:**
- ❌ Requires public URL
- ❌ Requires valid SSL certificate
- ❌ More complex setup

**Use when:** You have Home Assistant accessible via `https://` with a valid SSL certificate.

## Troubleshooting

### "Telegram test failed" during setup

**Check:**
1. Bot Token is correct (no spaces, complete token)
2. Chat ID is correct (numeric, positive or negative)
3. You've sent at least one message to your bot
4. Your bot is not blocked

**Solution:**
- Go back and re-enter credentials
- Test manually: `https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=test`

### "Conflict: terminated by other getUpdates request"

**This error has been fixed in the latest version!**

If you still see it:
1. Make sure you're using the latest haFWCMA version
2. Don't configure multiple telegram_bot instances with the same token
3. Use only one bot token across all your Telegram integrations

### Commands don't work

**Check:**
1. `telegram_bot` is configured in `configuration.yaml`
2. Home Assistant has been restarted
3. Chat ID in both configurations matches
4. Bot token in both configurations matches
5. Try `/help` - if this works, others should too

**Debug:**
- Check Home Assistant logs: **Settings** → **System** → **Logs**
- Search for "telegram" or "hafwcma"

### Messages not sending

**Check:**
1. Telegram configuration is not empty
2. Test connection was successful
3. Check Home Assistant logs for errors

## Advanced: Automation Examples

### Notify on Low Tank

```yaml
automation:
  - alias: "Low Tank Telegram Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.vehicle_range
        below: 100
    action:
      - service: telegram_bot.send_message
        data:
          target: YOUR_CHAT_ID
          message: "⚠️ Low tank! Only {{ states('sensor.vehicle_range') }} km remaining."
```

### Notify on Good Fuel Price

```yaml
automation:
  - alias: "Good Fuel Price Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.nearest_station_price
        below: 1.50
    action:
      - service: telegram_bot.send_message
        data:
          target: YOUR_CHAT_ID
          message: "💰 Great price! {{ states('sensor.nearest_station_name') }} has fuel for €{{ states('sensor.nearest_station_price') }}/L"
```

## Future Features (Coming Soon)

- 📝 Log refueling events via Telegram chat
- 🤖 AI-powered parsing of refueling data from text
- 📷 Receipt OCR to automatically extract refueling data
- 🗺️ Select fuel stations via inline keyboards
- 📊 Query fuel statistics via commands
- 🔔 Interactive refueling reminders

## Additional Resources

- [Home Assistant Telegram Bot Documentation](https://www.home-assistant.io/integrations/telegram_bot/)
- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [haFWCMA GitHub Issues](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)

## Need Help?

If you encounter issues:

1. Check the troubleshooting section above
2. Review Home Assistant logs
3. [Open an issue](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues) on GitHub
4. Include:
   - haFWCMA version
   - Home Assistant version
   - Error messages from logs
   - Steps to reproduce
