# Fix Summary: Map Image and Overlay Display Issue

## Issue
PR #102 implemented coordinate marker overlay, but the OSM map tile image from PR #101 disappeared. Users could see only the marker without the underlying map.

## Root Cause
PR #102 used SVG data URIs with external image references:
```javascript
const svg = `<svg>
  <image href="https://tile.openstreetmap.org/..."/>
  <circle cx="${pixelX}" cy="${pixelY}"/>
</svg>`;
return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
```

This approach fails because browsers block external images in SVG data URIs due to Content Security Policy (CSP) and Cross-Origin Resource Sharing (CORS) restrictions.

## Solution
Separated the map image and marker into two HTML layers:

### Before (Broken)
```html
<img src="data:image/svg+xml;...SVG with external image..." />
```
Result: ❌ Only marker visible, no map tile

### After (Fixed)
```html
<div style="position: relative">
  <img src="https://tile.openstreetmap.org/15/16372/10896.png" />
  <svg style="position: absolute; top: 0; left: 0">
    <circle cx="45.2%" cy="67.8%" r="8" fill="red" stroke="white" stroke-width="2"/>
    <circle cx="45.2%" cy="67.8%" r="3" fill="white"/>
  </svg>
</div>
```
Result: ✅ Both map tile AND marker overlay visible

## Technical Changes

### 1. HTML Structure (Lines 1767-1774, 1811-1818)
Changed from single `<img>` to layered container:
- Container: `position: relative` for absolute positioning context
- Image: OSM tile URL as direct src
- SVG: Absolute positioned overlay with `pointer-events: none`

### 2. getStaticMapUrl() Function (Lines 2736-2769)
**Before:** Created SVG data URI with embedded external image  
**After:** Returns direct OSM tile URL
```javascript
return `https://tile.openstreetmap.org/${zoom}/${xtile}/${ytile}.png`;
```

### 3. getMapMarkerPosition() Function (Lines 2771-2807)
**New function** to calculate marker position as percentage:
```javascript
return { x: percentX, y: percentY }; // 0-100 percentage coordinates
```

### 4. updateMapLinks() Function (Lines 2843-2868, 2879-2904)
**Enhanced** to set both image and marker:
1. Set `img.src` to OSM tile URL
2. Calculate marker position
3. Update SVG circle `cx` and `cy` attributes with percentages

## Files Modified
- `custom_components/hafwcma/www/fwcam-card.js` (main)
- `fwcam-card/dist/fwcam-card.js` (distribution)
- `www/fwcam-card/fwcam-card.js` (legacy)
- `docs/VEHICLE_POSITION_MARKER.md` (updated)
- `docs/MAP_PREVIEW_ARCHITECTURE.md` (new)

## Testing
✅ Tested with London (51.5074, -0.1278)  
✅ Tested with New York (40.7128, -74.0060)  
✅ Tested with Tokyo (35.6762, 139.6503)  
✅ Markers positioned correctly at calculated percentages  
✅ No CSP/CORS errors in browser console  

## Benefits
✅ **PR #101 functionality**: OSM tile image displays correctly  
✅ **PR #102 functionality**: Position marker overlay displays correctly  
✅ **Browser compatible**: No security policy violations  
✅ **Responsive**: Marker scales with container size  
✅ **Minimal changes**: Focused fix without unnecessary refactoring  

## Future Improvements (Optional)
The code review suggested:
1. Extract shared tile coordinate calculation into helper method
2. Extract marker positioning logic into reusable helper

These are good suggestions for reducing code duplication but not critical for functionality.

## Commit History
1. `69c0dad` - Fix map image display and overlay by separating tile image from marker overlay
2. `2a333ce` - Update documentation to explain the combined PR #101 + PR #102 fix
3. `48ce87a` - Fix code review comments - remove unused constant and fix JSDoc
