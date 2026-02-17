# Map Preview Architecture

## Overview
This document explains how map previews work in the FWCAM card, combining the OSM tile image display (PR #101) with position marker overlay (PR #102).

## Architecture

```
┌─────────────────────────────────────────────┐
│  Map Preview Container                      │
│  (position: relative)                       │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │ Layer 1: OSM Tile Image               │ │
│  │ <img src="tile.openstreetmap.org/    │ │
│  │       15/16372/10896.png">            │ │
│  │                                       │ │
│  │ (width: 100%, height: 100%)           │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │ Layer 2: Position Marker (SVG)        │ │
│  │ (position: absolute, top: 0, left: 0) │ │
│  │                                       │ │
│  │    ●  ← Red circle with white border  │ │
│  │       positioned at exact coordinates │ │
│  │                                       │ │
│  │ (pointer-events: none - clickable)    │ │
│  └───────────────────────────────────────┘ │
│                                             │
└─────────────────────────────────────────────┘
```

## Data Flow

```
User enters coordinates (lat, lon)
         │
         ├─→ getStaticMapUrl(lat, lon)
         │   │
         │   ├─→ Calculate tile coordinates (xtile, ytile)
         │   └─→ Return: https://tile.openstreetmap.org/15/xtile/ytile.png
         │
         └─→ getMapMarkerPosition(lat, lon)
             │
             ├─→ Calculate exact position within tile
             └─→ Return: { x: 45.2%, y: 67.8% }

updateMapLinks() combines both:
  1. Sets img.src = OSM tile URL
  2. Sets marker cx/cy = calculated percentages
```

## Why This Approach?

### ❌ Previous Approach (Didn't Work)
```javascript
// SVG with external image reference
const svg = `<svg>
  <image href="https://tile.openstreetmap.org/..."/>
  <circle cx="${pixelX}" cy="${pixelY}"/>
</svg>`;
return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
```

**Problem:** Browsers block external images in SVG data URIs due to CSP/CORS security policies. Result: Only marker visible, no map tile.

### ✅ Current Approach (Works)
```html
<!-- Separate layers -->
<div style="position: relative">
  <img src="https://tile.openstreetmap.org/..." />
  <svg style="position: absolute; top: 0; left: 0">
    <circle cx="45.2%" cy="67.8%" />
  </svg>
</div>
```

**Why it works:** 
- Direct image URL: No CSP/CORS issues
- Absolute positioned SVG: Overlay works in all browsers
- Percentage coordinates: Responsive, scales with container
- Pointer-events none: SVG doesn't block clicks on image

## Key Functions

### getStaticMapUrl(lat, lon)
**Purpose:** Calculate which OSM tile contains the coordinates  
**Returns:** Direct OSM tile URL (e.g., `https://tile.openstreetmap.org/15/16372/10896.png`)  
**Used by:** img.src attribute

### getMapMarkerPosition(lat, lon)
**Purpose:** Calculate where within the tile the marker should appear  
**Returns:** Percentage coordinates (e.g., `{ x: 45.2, y: 67.8 }`)  
**Used by:** SVG circle cx/cy attributes

### updateMapLinks()
**Purpose:** Update both map image and marker when coordinates change  
**Actions:**
1. Sets image source to OSM tile URL
2. Calculates and applies marker position
3. Shows/hides preview based on coordinate validity

## Benefits

✅ **Both features work:** Map tile visible + position marker overlay  
✅ **Browser compatible:** No CSP/CORS issues  
✅ **Responsive:** Marker position scales with container  
✅ **Click-through:** SVG overlay doesn't block image clicks  
✅ **No external dependencies:** Pure HTML/CSS/JS solution  

## Testing Checklist

When modifying map preview functionality, verify:
- [ ] Map tile image loads and displays correctly
- [ ] Position marker appears at the correct location
- [ ] Marker is visible on the map tile
- [ ] Clicking on preview opens map in new window
- [ ] Works with various coordinates (equator, poles, edge cases)
- [ ] Responsive behavior (marker stays positioned correctly)
