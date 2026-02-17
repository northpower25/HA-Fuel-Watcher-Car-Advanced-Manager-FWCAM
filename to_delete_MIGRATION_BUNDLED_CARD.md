# Migration Guide: Bundled Frontend Card

## Overview

As of version 0.0.35, the FWCAM frontend card is now bundled with the integration and automatically registered during installation. This change simplifies installation and eliminates the need for separate HACS installations.

## What Changed?

### Before (v0.0.34 and earlier)
- Integration and card were separate HACS components
- Users had to add the repository twice (once as "Integration", once as "Lovelace")
- This caused "Repository exists in the store" errors
- Card had to be installed separately via HACS Frontend

### After (v0.0.35 and later)
- Card is bundled with the integration
- Single HACS installation (Integration only)
- Card is automatically registered when integration loads
- No more "repository exists" errors

## Migration Steps

### If You Installed Both Integration and Card Separately

1. **Remove the old card from HACS (if installed separately)**
   - Open HACS → Frontend
   - Find "FWCAM Lovelace Card"
   - Click on it and select "Remove"
   
2. **Remove manual frontend configuration (if any)**
   - Open `configuration.yaml`
   - Remove any `frontend.extra_module_url` entries for fwcam-card
   - Example of what to remove:
     ```yaml
     frontend:
       extra_module_url:
         - /local/fwcam-card/fwcam-card.js  # REMOVE THIS
     ```

3. **Update the integration**
   - Open HACS → Integrations
   - Find "Fuel Watcher Car Advanced Manager"
   - Click "Update" (if available)
   - Or reinstall to get the latest version

4. **Restart Home Assistant**
   - Settings → System → Restart

5. **Clear browser cache**
   - Chrome/Edge: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
   - Firefox: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
   - Safari: `Cmd+Option+R`

6. **Verify card is working**
   - The card should still appear in your dashboard
   - It's now served from the integration instead of HACS Frontend

### If You Only Installed the Integration

No action needed! The card is now automatically available after the update.

### If You Manually Installed the Card

1. **Remove manual card files** (optional, for cleanup)
   - Delete `config/www/fwcam-card/` directory
   
2. **Remove manual resource registration**
   - Open `configuration.yaml`
   - Remove any `frontend.extra_module_url` or Lovelace `resources` entries for the card

3. **Restart Home Assistant**

4. **Clear browser cache**

## Verification

After migration, verify everything is working:

1. **Check integration is loaded**
   - Settings → System → Logs
   - Look for "FWCAM frontend card registered" message
   - Should see: "FWCAM frontend card registered at /hafwcma_local/fwcam-card.js?v=1.0.0"

2. **Check card is available**
   - Edit a dashboard
   - Click "Add Card"
   - Search for "FWCAM Card"
   - It should appear in the card picker

3. **Check card loads correctly**
   - Add the card to your dashboard
   - Configure with your refueling log sensor
   - Card should load and display data

## Troubleshooting

### Card not appearing in card picker

1. Ensure integration is properly installed via HACS
2. Restart Home Assistant
3. Clear browser cache completely
4. Check browser console for errors (F12 → Console)

### "Custom element doesn't exist: fwcam-card"

This means the card JavaScript hasn't loaded:
1. Clear browser cache and hard refresh
2. Restart Home Assistant
3. Check integration is loaded in Settings → System → Logs
4. Try a different browser to rule out cache issues

### Card shows old version

1. Check the version in HACS → Integrations
2. Update to latest version if available
3. Restart Home Assistant
4. Clear browser cache (important!)

### Still seeing "Repository exists" error

This shouldn't happen anymore, but if it does:
1. Remove all instances of the repository from HACS
2. Wait a few minutes
3. Re-add only as "Integration"
4. Do NOT add as "Lovelace" or "Frontend"

## Benefits of Bundled Approach

✅ **Single Installation** - Only install the integration, card comes automatically  
✅ **No Confusion** - No more choosing between Integration/Lovelace categories  
✅ **No Errors** - Eliminates "repository exists" errors  
✅ **Automatic Updates** - Card updates with integration  
✅ **Version Sync** - Integration and card always compatible  
✅ **Better UX** - Seamless installation experience  
✅ **Modern Approach** - Follows Home Assistant best practices  

## Support

If you encounter issues during migration:
- [GitHub Issues](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)
- [HACS Installation Guide](HACS_INSTALLATION.md)
- [Documentation](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM)

## Technical Details

For developers interested in the implementation:
- Card is now in `custom_components/hafwcma/www/`
- Served from `/hafwcma_local/fwcam-card.js?v={version}`
- Registered via `frontend_extra_module_url` in `__init__.py`
- Version parameter enables cache busting
- See [HACS_STRUCTURE_IMPLEMENTATION.md](HACS_STRUCTURE_IMPLEMENTATION.md) for full details
