# HACS Integration with Bundled Frontend Card

## Overview

This document describes the implementation of a modern HACS-compatible structure for the Fuel Watcher Car Advanced Manager (FWCAM) repository, where the frontend card is bundled with the integration.

## Problem Statement

The original dual-component structure had:
- A Home Assistant integration in `custom_components/hafwcma/`
- A separate Lovelace card in `fwcam-card/` with its own `hacs.json`
- Users had to install both components separately via HACS

This caused issues:
- Users received "Repository exists in the store" errors when trying to add the same repository twice
- HACS no longer has a "Lovelace" category (replaced with "Dashboard")
- Confusion about whether to use "Integration" or "Lovelace" category
- Manual installation complexity

## Modern Solution

Implemented a bundled approach where the frontend card is included with the integration and automatically registered during setup. This is the modern, recommended approach for Home Assistant custom integrations with custom cards.

## Changes Made

### 1. Repository Structure

```
Repository Root
├── custom_components/
│   └── hafwcma/              # Integration
│       ├── www/              # NEW: Frontend card files
│       │   └── fwcam-card.js # Card JavaScript
│       ├── __init__.py       # UPDATED: Card registration
│       ├── manifest.json
│       └── ...
├── fwcam-card/               # KEPT: Documentation & source
│   ├── dist/                 # Distribution files
│   ├── README.md             # Card documentation
│   └── README_DE.md          # German docs
├── www/                      # DEPRECATED: Old location
│   └── fwcam-card/           # For backward compatibility
├── hacs.json                 # Integration only
└── ...
```

### 2. Frontend Card Registration

Added automatic card registration in `custom_components/hafwcma/__init__.py`:

```python
async def _async_register_frontend_card(hass: HomeAssistant) -> None:
    """Register the FWCAM frontend card."""
    # Register static path for serving the card
    await hass.http.async_register_static_paths([{
        "url_path": f"/{DOMAIN}_local",
        "path": str(card_dir),
    }])
    
    # Add to frontend extra module URLs
    card_url = f"/{DOMAIN}_local/{CARD_FILENAME}?v={CARD_VERSION}"
    hass.data.setdefault("frontend_extra_module_url", set()).add(card_url)
```

This is called during `async_setup()` to ensure the card is registered when the integration loads.

### 3. HACS Configuration

The root `hacs.json` remains as an integration-only config:

```json
{
  "name": "Fuel Watcher Car Advanced Manager",
  "domains": ["hafwcma"],
  "country": ["DE"],
  "render_readme": true,
  "iot_class": "cloud_polling",
  "homeassistant": "2023.1.0"
}
```

**Removed**: `fwcam-card/hacs.json` (no longer needed)

### 4. Documentation Updates

**Updated Documents:**
- `HACS_INSTALLATION.md` - Single installation process (integration only)
- `HACS_INSTALLATION_DE.md` - German version, single installation
- `HACS_STRUCTURE_IMPLEMENTATION.md` - This document, new approach

**Key Message**: Users only install the integration via HACS, and the card is automatically available.

## How It Works

### For Users

1. **Install Integration via HACS**
   - HACS → Integrations → Custom repositories
   - Add URL with category "Integration"
   - Download "Fuel Watcher Car Advanced Manager"

2. **Restart Home Assistant**
   - The integration loads
   - Frontend card is automatically registered
   - Card becomes available in Lovelace

3. **Use the Card**
   - No separate installation needed
   - Card appears in card picker
   - Configure as `type: custom:fwcam-card`

### For HACS

HACS recognizes this as a standard integration:
- Downloads `custom_components/hafwcma/` to Home Assistant
- Integration's `__init__.py` runs on startup
- Card registration happens automatically

### For Home Assistant

When the integration loads:
1. `async_setup()` is called
2. `_async_register_frontend_card()` registers the static path
3. Card URL is added to `frontend_extra_module_url`
4. Frontend loads the card module automatically
5. Card appears in Lovelace card picker

## Benefits

1. **Single Installation**: Users install only the integration
2. **No Confusion**: No ambiguity about which HACS category to use
3. **No Errors**: No "repository exists" errors
4. **Automatic Updates**: Card updates with integration
5. **Modern Approach**: Follows Home Assistant best practices
6. **Version Sync**: Card and integration always match
7. **Better UX**: Seamless installation experience

## Backward Compatibility

The old `www/fwcam-card/` directory is kept for users who:
- Manually installed the card previously
- Have direct references in their configuration

A migration guide is provided in documentation for these users.

## Technical Details

### Card Serving

The card is served from:
```
/hafwcma_local/fwcam-card.js?v={version}
```

This URL:
- Is unique to this integration (using domain prefix)
- Includes version parameter for cache busting
- Is automatically registered on integration load

### Version Management

Card version is defined in `__init__.py`:
```python
CARD_VERSION = "1.0.0"
```

Increment this when the card changes to force browser cache refresh.

### Error Handling

The registration function:
- Checks if card file exists
- Logs warnings if card is missing
- Continues integration setup even if card fails
- Provides detailed error logging

## Testing Checklist

- [x] Card file copied to `custom_components/hafwcma/www/`
- [x] Frontend registration code added to `__init__.py`
- [x] Removed `fwcam-card/hacs.json`
- [x] Updated HACS installation documentation (EN)
- [x] Updated HACS installation documentation (DE)
- [x] Updated structure documentation
- [ ] Test installation via HACS
- [ ] Verify card appears in card picker
- [ ] Test card functionality
- [ ] Verify browser cache handling

## Migration Guide for Users

If users previously installed the card separately:

1. **Remove old card from HACS Frontend** (if installed)
2. **Remove manual configuration**:
   - Check `configuration.yaml` for `frontend.extra_module_url` entries
   - Remove any entries pointing to `/local/fwcam-card.js`
3. **Update/reinstall integration** via HACS
4. **Restart Home Assistant**
5. **Clear browser cache**
6. Card is now provided automatically

## Future Considerations

### Multiple Cards

If additional cards are added in the future:
- Place them in `custom_components/hafwcma/www/`
- Register them in `_async_register_frontend_card()`
- Each card gets a unique filename

### Card Development

For card development:
- Source files can remain in `fwcam-card/`
- Build process copies to `custom_components/hafwcma/www/`
- Version number in `__init__.py` should be updated after builds

### Alternative: Config Flow Registration

An alternative approach would be to register the card during config flow:
- Pros: Card only loads when integration is configured
- Cons: More complex, requires reload if integration removed
- Current approach (on setup) is simpler and more reliable

## Conclusion

The implementation successfully modernizes the repository structure to use the recommended bundled approach. This eliminates HACS installation confusion, prevents errors, and provides a better user experience while following Home Assistant best practices.

---

**Implementation Date**: 2026-02-10  
**Version**: 0.0.35 (updated)  
**Author**: GitHub Copilot Agent

