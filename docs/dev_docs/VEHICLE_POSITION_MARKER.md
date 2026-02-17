# Vehicle Position Marker Implementation

## Problem
After implementing PR #101, map preview images were displayed in the trip edit dialog, but they lacked a visual indicator showing the exact vehicle position. Users could see the map tile but couldn't identify where the coordinates were located.

With PR #102, a marker overlay was added, but due to browser security restrictions (CSP/CORS), SVG data URIs with external image references don't work - the map tile image disappeared, showing only the marker.

## Solution (Fixed)
The fix separates the OSM tile image (PR #101) from the marker overlay (PR #102) using a layered approach:
1. Display the OSM tile directly as an `<img>` element 
2. Overlay an SVG with position markers using absolute positioning
3. Calculate and position the marker dynamically based on coordinates

This approach combines both features successfully while respecting browser security constraints.

## Technical Implementation

### HTML Structure
Map previews now use a container with layered elements:

```html
<div id="start-location-map-preview" style="position: relative; width: 100%; aspect-ratio: 1;">
  <!-- Background: OSM tile image (PR #101) -->
  <img id="start-map-img" style="width: 100%; height: 100%; border-radius: 4px; cursor: pointer; object-fit: cover;">
  
  <!-- Overlay: Position marker (PR #102) -->
  <svg id="start-map-marker" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;">
    <circle id="start-marker-outer" cx="50%" cy="50%" r="8" fill="red" stroke="white" stroke-width="2" opacity="0.9"/>
    <circle id="start-marker-inner" cx="50%" cy="50%" r="3" fill="white" opacity="0.9"/>
  </svg>
</div>
```

### Calculation of OSM Tile URL
The `getStaticMapUrl()` function returns the direct OSM tile URL:

```javascript
getStaticMapUrl(lat, lon) {
  // Validate and clamp coordinates
  const clampedLat = Math.max(-MAX_MERCATOR_LAT, Math.min(MAX_MERCATOR_LAT, lat));
  
  // Calculate tile coordinates using Web Mercator projection
  const n = Math.pow(2, zoom);
  const xtile = Math.floor((lon + 180) / 360 * n);
  const ytile = Math.floor(latToMercatorY(clampedLat) * n);
  
  // Return direct OSM tile URL (browser-compatible)
  return `https://tile.openstreetmap.org/${zoom}/${xtile}/${ytile}.png`;
}
```

### Calculation of Marker Position
The `getMapMarkerPosition()` function calculates where to place the marker within the tile:

```javascript
getMapMarkerPosition(lat, lon) {
  // Calculate exact position within tile (0-1 range)
  const exactX = ((lon + 180) / 360 * n) - xtile;
  const exactY = (latToMercatorY(clampedLat) * n) - ytile;
  
  // Convert to percentage (0-100)
  const percentX = exactX * 100;
  const percentY = exactY * 100;
  
  return { x: percentX, y: percentY };
}
```

### Dynamic Marker Positioning
In `updateMapLinks()`, the marker position is updated dynamically:

```javascript
// Set the map tile image
const mapUrl = this.getStaticMapUrl(startLat, startLon);
startMapImg.src = mapUrl;

// Calculate and apply marker position
const markerPos = this.getMapMarkerPosition(startLat, startLon);
startMarkerOuter.setAttribute('cx', `${markerPos.x}%`);
startMarkerOuter.setAttribute('cy', `${markerPos.y}%`);
startMarkerInner.setAttribute('cx', `${markerPos.x}%`);
startMarkerInner.setAttribute('cy', `${markerPos.y}%`);
```

## Changes Made

### Files Updated
- `custom_components/hafwcma/www/fwcam-card.js` (main bundled version)
- `fwcam-card/dist/fwcam-card.js` (standalone distribution)
- `www/fwcam-card/fwcam-card.js` (legacy copy)

### Key Changes
1. **HTML Structure**: Changed from single `<img>` to container with layered `<img>` + `<svg>` overlay
2. **getStaticMapUrl()**: Simplified to return direct OSM tile URL (browser-compatible, fixes PR #101)
3. **getMapMarkerPosition()**: New function to calculate marker position as percentage
4. **updateMapLinks()**: Enhanced to dynamically position markers using calculated coordinates

### Key Features
- **Shows both map and marker**: Combines PR #101 (tile image) + PR #102 (position overlay)
- **Browser compatible**: No SVG data URIs with external images (CSP/CORS compliant)
- **Accurate positioning**: Uses Web Mercator projection for precise marker placement
- **Visual marker**: Red/white circle design clearly visible on any map background
- **No external dependencies**: Pure JavaScript and CSS implementation

## Testing
The implementation was tested with:
- Multiple coordinate sets (London, New York, Tokyo)
- Edge cases (near poles, invalid coordinates)
- Web Mercator projection clamping for extreme latitudes
- Layered HTML structure for image + overlay compatibility

## Benefits
✅ Users can now see BOTH the map tile AND the position marker  
✅ Fixes browser security issues with SVG data URIs containing external images  
✅ Improves usability of trip start/end location previews  
✅ No additional API calls or external services required  
✅ Consistent marker appearance across all maps  
✅ Combines benefits of both PR #101 and PR #102  

## Future Enhancements
Possible improvements could include:
- Customizable marker colors based on trip type (start=green, end=red)
- Different marker styles (pin, arrow, car icon)
- Multiple zoom levels
- Tooltip showing exact coordinates
