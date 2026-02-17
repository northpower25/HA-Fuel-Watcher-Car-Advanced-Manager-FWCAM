# Feature: API Testing in Config Flow

**Status**: Deferred / In Planning  
**Priority**: Medium  
**Estimated Effort**: 15-20 hours  
**Version**: Planned for v1.0.0 or later  

## Overview

This feature adds API validation and testing functionality during the configuration flow to provide users with immediate feedback about the correctness of their API configuration.

## Problem Statement

Currently, the following issues exist in the setup/config flow:

1. **Fuel Price API**: No validation of API configuration during setup. Users only learn after completing the configuration whether their API credentials are correct.

2. **Telegram API**: No way to test if the Telegram configuration works and whether messages can be successfully sent/received.

## User Stories

### Story 1: Fuel Price API Validation
**As a** user  
**I want to** test during configuration if my fuel price API credentials are correct  
**So that** I can be sure the integration works before completing the configuration

**Acceptance Criteria:**
- After entering API configuration (Provider, API Key, Radius, Fuel Type)
- A test query to the API is performed when clicking "OK"
- A new window shows the result:
  - **On Success**: List of found cheapest stations near home
    - Station name
    - Address
    - Prices for e5, e10, diesel
    - "OK" button to continue
  - **On Error**: Complete error message from API
    - Technical error code
    - Human-readable error description
    - "Back" button to API configuration

### Story 2: Telegram API Validation
**As a** user  
**I want to** test during configuration if my Telegram integration works  
**So that** I can be sure I can receive notifications and respond to them

**Acceptance Criteria:**
- After entering Telegram configuration (Bot Token, Chat ID)
- A test message is sent when clicking "OK"
- Test message content:
  - **Title**: "FWCAM Test Message"
  - **Text**: "Your car says: 'I'm ready for intelligent refueling decision notifications! Please reply to this message so I can verify you can reach me'"
  - Requires a reply
- A waiting window is displayed:
  - Shows that a test message was sent
  - Prompts user to reply to the message
  - Buttons:
    - "Back" - return to Telegram configuration
    - "Cancel" - abort setup and rollback integration
- After receiving the reply:
  - Display: "Thank you for your reply: [Response text] now I can also receive information from you :-)"
  - "OK" button appears to continue

## Technical Requirements

### Architecture Changes

1. **Async Validation Flow**
   - New config flow steps for validation
   - Asynchronous API calls during configuration
   - State management for multi-step validation

2. **Fuel Price API Testing**
   - Implementation of `async_validate_fuel_api()` function
   - Use of home coordinates as test location
   - Error handling for various API error cases
   - Formatting of station results for UI display

3. **Telegram API Testing**
   - Implementation of `async_validate_telegram_api()` function
   - Sending a test message
   - Webhook or polling-based waiting for response
   - Timeout handling (e.g., 2 minutes)
   - State management for response waiting time

### Config Flow Structure

```
async_step_user (API Configuration)
  ↓
async_step_validate_api (NEW - API Test)
  ↓ [Success]
async_step_vehicle
  ↓
async_step_vehicle_entities
  ↓
async_step_telegram
  ↓
async_step_validate_telegram (NEW - Telegram Test)
  ↓ [Waiting for Response]
async_step_telegram_response (NEW - Response Processed)
  ↓ [Success]
async_step_prediction
```

### New Config Flow Steps

#### Step: `async_step_validate_api`
```python
async def async_step_validate_api(
    self, user_input: dict[str, Any] | None = None
) -> FlowResult:
    """Validate fuel price API configuration."""
    
    if user_input is None:
        # Perform API test
        try:
            # Test API with home coordinates
            stations = await test_api_connection(
                provider=self.data[CONF_PROVIDER],
                api_key=self.data[CONF_API_KEY],
                lat=self.hass.config.latitude,
                lon=self.hass.config.longitude,
                radius=self.data[CONF_RADIUS],
                fuel_type=self.data[CONF_FUEL_TYPE],
            )
            
            # Show success with station list
            return self.async_show_form(
                step_id="validate_api",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "result": "success",
                    "stations": format_stations(stations),
                },
            )
        except Exception as err:
            # Show error message
            return self.async_show_form(
                step_id="validate_api",
                data_schema=vol.Schema({}),
                errors={"base": "api_connection_failed"},
                description_placeholders={
                    "result": "error",
                    "error_message": str(err),
                },
            )
    else:
        # User clicked OK/Back button
        if "back" in user_input:
            return await self.async_step_user()
        return await self.async_step_vehicle()
```

#### Step: `async_step_validate_telegram`
```python
async def async_step_validate_telegram(
    self, user_input: dict[str, Any] | None = None
) -> FlowResult:
    """Validate Telegram API configuration."""
    
    if user_input is None:
        # Send test message
        try:
            await send_telegram_test_message(
                token=self.data[CONF_TELEGRAM_TOKEN],
                chat_id=self.data[CONF_TELEGRAM_CHAT_ID],
            )
            
            # Store timestamp for timeout
            self._telegram_test_start = datetime.now()
            
            # Show waiting screen
            return self.async_show_form(
                step_id="validate_telegram",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "message": "Test message sent. Please reply to continue.",
                },
            )
        except Exception as err:
            return self.async_show_form(
                step_id="validate_telegram",
                data_schema=vol.Schema({}),
                errors={"base": "telegram_send_failed"},
                description_placeholders={
                    "error_message": str(err),
                },
            )
    else:
        # User action (back/cancel)
        if "cancel" in user_input:
            # Rollback integration
            raise AbortFlow("user_cancelled")
        return await self.async_step_telegram()
```

#### Step: `async_step_telegram_response`
```python
async def async_step_telegram_response(
    self, user_input: dict[str, Any] | None = None
) -> FlowResult:
    """Process Telegram response."""
    
    # This step is triggered by webhook/polling
    response_text = self._telegram_response
    
    return self.async_show_form(
        step_id="telegram_response",
        data_schema=vol.Schema({}),
        description_placeholders={
            "response_text": response_text,
            "message": f"Thank you for your reply: {response_text}",
        },
    )
```

### UI/UX Considerations

1. **Loading Indicators**: Show loading animation while API calls are running
2. **Timeout Handling**: Clear timeout messages (e.g., "Telegram response not received within 2 minutes")
3. **Error Details**: Technical details in collapsible sections for advanced users
4. **Retry Mechanism**: Option to retry on failures
5. **Skip Option**: Advanced users can skip tests

### Dependencies

- Home Assistant Config Flow Framework
- Telegram Bot API (python-telegram-bot library)
- Existing Provider implementations (TankerKönig)
- Async HTTP Client (aiohttp)

## Implementation Phases

### Phase 1: API Validation (MVP)
**Effort**: 8-10 hours

- Implement `async_step_validate_api`
- API test function for TankerKönig
- Success and error display
- Back navigation on errors

### Phase 2: Telegram Validation (Basic)
**Effort**: 10-12 hours

- Implement `async_step_validate_telegram`
- Send test message
- Simple polling for response (without webhook)
- Timeout handling
- Abort functionality

### Phase 3: Improvements (Optional)
**Effort**: 5-8 hours

- Webhook-based response handling (faster)
- Retry mechanisms
- Skip options
- Enhanced error handling
- Logging and diagnostics

## Risks and Challenges

1. **Complexity**: Multi-step async flows significantly increase code complexity
2. **State Management**: State between steps must be properly managed
3. **Telegram Timing**: Waiting for user response can lead to long setup times
4. **Timeout Handling**: Correct handling of timeouts without memory leaks
5. **User Experience**: Additional steps might be perceived as too complex
6. **Testing**: Difficult to test without real API credentials

## Alternatives

1. **Post-Setup Validation**: Tests after configuration completion via services
2. **Optional Testing**: Tests as optional button in config, not in flow
3. **Separate Test Integration**: Own "Test" config entry for validation
4. **Documentation**: Better error documentation instead of automatic tests

## Decision

**Implemented** - Feature has been successfully implemented:

1. ✅ Phase 1 (MVP): API validation with basic error handling
2. ✅ Phase 2 (Basic): Telegram validation with simple test message sending
3. ⏸️ Phase 3 (Optional): Advanced features like webhook-based response handling for Telegram can be added later

## Implemented Features

### API Validation
- Test API connection with home coordinates during config flow
- Display top 5 found stations with name, address, and prices
- Detailed error messages on API failures
- "Back" navigation on errors to correct API configuration

### Telegram Validation
- Send test message when setting up Telegram integration
- Confirmation of successful sending
- Error handling with detailed error messages
- Option to correct on failures
- Optional: Skip if Telegram is not configured

## Next Steps (Optional Enhancements)

1. ⏸️ Webhook-based response handling for Telegram (Phase 3)
2. ⏸️ Polling mechanism for Telegram responses
3. ⏸️ Advanced retry mechanisms
4. ⏸️ Skip options for advanced users
5. ⏸️ Enhanced logging and diagnostics

## References

- Original Issue: GitHub Discussion from 2026-02-11
- Config Flow Documentation: https://developers.home-assistant.io/docs/config_entries_config_flow_handler
- Telegram Bot API: https://core.telegram.org/bots/api
- TankerKönig API: https://creativecommons.tankerkoenig.de

---

**Created**: 2026-02-11  
**Last Updated**: 2026-02-11  
**Author**: Development Team  
**Status**: Implemented (MVP + Basic)
