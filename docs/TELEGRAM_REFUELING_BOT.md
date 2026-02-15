# Telegram Bot Bidirectional Refueling Tracking

## Overview

This implementation extends haFWCMA with bidirectional Telegram integration for intelligent refueling event capture. The system automatically detects new refueling events, notifies the user, and collects missing information through various input methods.

## How It Works

### 1. Automatic Detection and Notification

When a new refueling event is detected (manually via UI or through the `add_refuel_event` service):

1. The system analyzes which information is already available
2. The user receives a Telegram message with:
   - All detected information (timestamp, volume, price, etc.)
   - A list of missing information
   - Instructions for different response methods
   - Inline buttons for quick actions (Confirm, Edit, Delete)

### 2. User Response Options

The user can respond in four different ways:

#### Option 1: Inline Keyboard (Form)

The Telegram message contains inline buttons for quick actions:
- **✅ Confirm**: Accept refueling with existing data
- **✏️ Edit**: Prompts for corrections
- **🗑️ Delete**: Removes the refueling event

#### Option 2: Unstructured Text

The user can simply reply to the message with free text:

**Examples:**
- `45.5 liters, 1.599 €/L, Shell station`
- `Price: 1.65, Station: Aral, Odometer: 123456`
- `72.50 € total, 45 L, Esso`

The system uses pattern matching to extract:
- **Volume**: `45.5 L`, `45,5 Liter`, `45L`
- **Price per liter**: `1.599 €/L`, `1,599€/Liter`, `Price: 1.59`
- **Total cost**: `71.96 €`, `Total: 71,96`
- **Odometer**: `123456 km`, `Odometer: 123.456`
- **Station name**: Recognizes known brands (Shell, Aral, Esso, Total, Jet, OMV, Agip)

#### Option 3: Receipt Photo

The user can send a photo of the receipt.

**OCR Implementation Options:**

##### Local Solutions:
1. **Tesseract OCR** (via pytesseract) - Free, offline, lower accuracy
2. **EasyOCR** - Better accuracy, multilingual
3. **PaddleOCR** - Very good accuracy, fast

##### Cloud-based Solutions:
1. **Google Cloud Vision API** - Very high accuracy (free up to 1000 requests/month)
2. **AWS Textract** - Specialized for documents/receipts
3. **Azure Computer Vision** - Good Microsoft integration

**Current Status:** OCR functionality is implemented as a placeholder. Choose one of the above solutions and implement the `_perform_ocr()` method in `telegram_refueling_handler.py`.

#### Option 4: Voice Message

The user can send a voice message.

**Speech-to-Text Implementation Options:**

##### Local Solutions:
1. **Whisper (OpenAI)** - State-of-the-art accuracy, multilingual, offline
2. **Faster-Whisper** - 4x faster than Whisper, same accuracy
3. **Vosk** - Lightweight, fast, offline

##### Cloud-based Solutions:
1. **Google Cloud Speech-to-Text** - Very high accuracy (free up to 60 minutes/month)
2. **AWS Transcribe** - Good accuracy, batch processing
3. **Azure Speech Service** - Good accuracy, multilingual

**Current Status:** Speech-to-text functionality is implemented as a placeholder. Choose one of the above solutions and implement the `_transcribe_voice()` method in `telegram_refueling_handler.py`.

### 3. AI-Powered Data Analysis

The system analyzes the user's response (text, OCR result, transcription) and extracts structured data using regular expressions and pattern matching. Can be extended with AI models (GPT, Claude, local LLMs).

### 4. Data Storage

For each refueling event, the following Telegram-related data is stored:

```python
{
    # Notification
    "telegram_notification_sent": True/False,
    "telegram_notification_timestamp": "2024-01-15T14:30:00",
    "telegram_message_id": 12345,
    
    # Response
    "telegram_response_received": True/False,
    "telegram_response_timestamp": "2024-01-15T14:35:00",
    "telegram_response_type": "text" | "photo" | "voice" | "callback",
    "telegram_response_raw": "Raw user input",
    "telegram_response_parsed": { /* Structured data */ },
    "telegram_photo_file_id": "AgACAgIAAxkBAAI...",
    "telegram_voice_file_id": "AwACAgIAAxkBAAI...",
}
```

## Setup

### Prerequisites

1. **Telegram Bot configured** in Home Assistant
   - See [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) for details
   - Both haFWCMA Telegram token and `telegram_bot` integration must be set up

2. **Home Assistant `telegram_bot` Integration**
   ```yaml
   telegram_bot:
     - platform: polling
       api_key: YOUR_BOT_TOKEN
       allowed_chat_ids:
         - YOUR_CHAT_ID
   ```

### Activation

Bidirectional refueling tracking is **automatically activated** when:
- Telegram token and chat ID are configured in haFWCMA
- The Home Assistant `telegram_bot` integration is loaded

**Status Check:**

1. **Binary Sensor**: `binary_sensor.[vehicle_name]_telegram_bot`
   - Shows if the Telegram bot is active
   - Attributes show configuration details

2. **Logs**: Check Home Assistant logs for:
   ```
   INFO: Telegram refueling handler initialized for bidirectional refueling tracking
   ```

## Usage

### Simulate Test Refueling

Use the `hafwcma.simulate_refueling_event` service:

```yaml
service: hafwcma.simulate_refueling_event
data:
  config_entry_id: "abc123def456"
  include_missing_data: true  # true = with missing data, false = complete
```

This creates a simulated refueling event and triggers a Telegram notification.

### Normal Workflow

1. Add refueling event (manually via UI or automatically):
   ```yaml
   service: hafwcma.add_refuel_event
   data:
     config_entry_id: "abc123def456"
     timestamp: "2024-01-15T14:30:00"
     liters_refueled: 45.5
     # Other fields optional
   ```

2. You receive a Telegram message with the information

3. Respond using one of the four methods:
   - Press inline button
   - Send text reply
   - Send receipt photo
   - Send voice message

4. The system processes your response and updates the refueling event

5. You receive a confirmation with the recognized data

## Available Services

### hafwcma.simulate_refueling_event

Creates a test refueling event to verify Telegram functionality.

**Parameters:**
- `config_entry_id` (required): Integration config entry ID
- `include_missing_data` (optional, default: true): Whether to simulate missing data

### hafwcma.add_refuel_event

Adds a real refueling event (triggers Telegram notification).

**Parameters:**
- `config_entry_id` (required): Config entry ID
- `timestamp` (required): ISO format timestamp
- `liters_refueled` (required): Liters refueled
- `odometer_km` (optional): Odometer reading
- `price_per_liter` (optional): Price per liter
- `total_cost` (optional): Total cost
- `station_name` (optional): Station name
- `station_address` (optional): Station address
- `fuel_type` (optional): Fuel type (e5, e10, diesel)

## Privacy

### Local Processing
- Telegram messages are processed only in your Home Assistant instance
- Raw and parsed data stored locally in `.storage/hafwcma_<entry_id>.json`
- No third-party data sharing (except when using cloud OCR/STT)

### Cloud Services (optional)
If using cloud-based OCR or Speech-to-Text:
- Photos/audio are sent to the chosen cloud provider
- Review the provider's privacy policy
- Consider local alternatives for sensitive data

## Debugging

### View Telegram Response Data

All responses are stored in the refueling log:

```yaml
service: hafwcma.get_all_refuelings
data:
  config_entry_id: "abc123def456"
```

### Enable Debug Logging

```yaml
logger:
  default: info
  logs:
    custom_components.hafwcma.telegram_refueling_handler: debug
    custom_components.hafwcma.telegram_handler: debug
```

## Known Limitations

1. **OCR and Speech-to-Text** are implemented as placeholders
   - You must implement one of the suggested solutions yourself
   - This allows choosing between local and cloud solutions

2. **Basic AI parsing** uses only pattern matching
   - Can be extended with GPT/Claude API or local LLMs
   - Current implementation is sufficient for structured inputs

3. **No automatic refueling detection**
   - Refueling events must be added manually or via service
   - Future enhancement could implement automatic detection via tank level changes

## Future Enhancements

1. **Advanced AI Integration** - GPT-4 Vision, local LLMs, learning system
2. **Multimedia Support** - Display receipts, play voice messages in frontend
3. **Automatic Detection** - Detect refueling via level changes and GPS
4. **Telegram Bot Commands** - `/refuel`, `/status`, `/history`, `/stats`

## Support

For issues or questions:
1. Check Home Assistant logs
2. Ensure `telegram_bot` integration is correctly configured
3. Test with `simulate_refueling_event` service

Contributions welcome:
- OCR/Speech-to-Text implementations
- Text parsing improvements
- Frontend card UI enhancements
- Translations and documentation

## Changelog

### Version 1.0.0 (Initial Release)
- ✅ Automatic Telegram notification on new refueling
- ✅ Inline keyboard for quick actions
- ✅ Unstructured text input with pattern matching
- ✅ Photo/voice message support (placeholder)
- ✅ Complete data storage for debugging
- ✅ Test service for easy testing
- ✅ Binary sensor for status display
- ✅ Comprehensive documentation
