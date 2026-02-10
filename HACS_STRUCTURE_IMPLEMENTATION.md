# HACS Dual-Component Structure Implementation

## Overview

This document describes the implementation of a HACS-compatible dual-component structure for the Fuel Watcher Car Advanced Manager (FWCAM) repository.

## Problem Statement

The original repository had:
- A Home Assistant integration in `custom_components/hafwcma/`
- A Lovelace card in `www/fwcam-card/`
- A single `hacs.json` configured only for the integration

This structure prevented users from installing the Lovelace card via HACS, requiring manual installation only.

## Solution

Implemented a HACS-compatible structure that allows both the integration and Lovelace card to be distributed from the same repository as separate HACS components.

## Changes Made

### 1. Repository Structure

Created a new directory structure:

```
Repository Root
├── custom_components/
│   └── hafwcma/              # Integration (existing)
├── fwcam-card/               # NEW: Card component
│   ├── dist/                 # NEW: Card distribution files
│   │   ├── fwcam-card.js
│   │   └── fwcam-card.min.js
│   ├── hacs.json             # NEW: Card HACS config
│   ├── README.md             # NEW: Card documentation
│   └── README_DE.md          # NEW: German card docs
├── www/                      # KEPT: Backward compatibility
│   └── fwcam-card/           # DEPRECATED: Old location
├── hacs.json                 # UPDATED: Integration config
└── ...
```

### 2. HACS Configuration Files

#### Root `hacs.json` (Integration)
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

#### `fwcam-card/hacs.json` (Lovelace Card)
```json
{
  "name": "FWCAM Lovelace Card",
  "filename": "fwcam-card.js",
  "render_readme": true,
  "content_in_root": false
}
```

### 3. .gitignore Update

Modified `.gitignore` to exclude Python `dist/` directories while allowing `fwcam-card/dist/`:

```gitignore
dist/
!fwcam-card/dist/
```

### 4. Documentation Updates

**New Documents:**
- `HACS_INSTALLATION.md` - Comprehensive English installation guide
- `HACS_INSTALLATION_DE.md` - Comprehensive German installation guide
- `fwcam-card/README.md` - Detailed card documentation
- `fwcam-card/README_DE.md` - German card documentation

**Updated Documents:**
- `README.md` - Added quick installation links and dual-component info
- `docs/INSTALLATION.md` - Added Lovelace card installation section
- `docs/REFUELING_LOG_GUIDE.md` - Updated with HACS installation instructions
- `docs/REFUELING_LOG_GUIDE_DE.md` - Updated with HACS installation instructions
- `www/fwcam-card/README.md` - Added deprecation notice
- `TODO.md` - Marked Lovelace card tasks as completed

## How It Works

### For Users

Users can now install both components via HACS from the same repository:

**Integration Installation:**
1. HACS → Integrations → Custom repositories
2. Add URL with category "Integration"
3. Download "Fuel Watcher Car Advanced Manager"

**Card Installation:**
1. HACS → Frontend → Custom repositories
2. Add URL with category "Lovelace"
3. Download "FWCAM Lovelace Card"

### For HACS

HACS recognizes components based on:
- Directory structure
- `hacs.json` configuration
- Category specified when adding the repository

Since each component has its own `hacs.json` and directory:
- The root `hacs.json` + `custom_components/` → Integration
- The `fwcam-card/hacs.json` + `dist/` → Lovelace card

HACS treats them as separate installable components from the same repo.

## Backward Compatibility

The old `www/fwcam-card/` directory is **kept** for backward compatibility:
- Users with manual installations can continue using files from `www/`
- A deprecation notice guides users to the new structure
- No breaking changes for existing users

## Benefits

1. **Single Repository**: Both components in one repo, easier to maintain
2. **HACS Native**: No manual installation required
3. **Easy Updates**: One-click updates for both components
4. **Version Sync**: Keep integration and card versions aligned
5. **Proper Distribution**: Follows HACS best practices

## Future Considerations

### Versioning

Consider using the same version numbers for both components:
- Integration: `v0.0.33`
- Card: `v0.0.33`

This ensures compatibility and simplifies version management.

### Releases

When creating GitHub releases:
- Tag format: `v0.0.34`
- Include changes for both integration and card
- HACS automatically detects the correct files for each component

### Advanced Features

The TODO list includes additional Lovelace features that could be implemented:
- [ ] Graphical price trend visualization
- [ ] Consumption prediction accuracy visualization
- [ ] Interactive station map
- [ ] Custom panel for detailed statistics

These would require additional development but can be added to the same `fwcam-card/` structure.

## Testing Checklist

Before release, verify:

- [ ] Both `hacs.json` files are valid JSON
- [ ] Card JavaScript files are in `fwcam-card/dist/`
- [ ] All documentation links are correct
- [ ] README files render correctly on GitHub
- [ ] .gitignore properly excludes/includes files
- [ ] Card files are committed to git
- [ ] Version numbers are consistent

## Conclusion

The implementation successfully restructures the repository for HACS dual-component distribution while maintaining backward compatibility and providing comprehensive documentation for users.

---

**Implementation Date**: 2026-02-10  
**Version**: 0.0.33 (base)  
**Author**: GitHub Copilot Agent
