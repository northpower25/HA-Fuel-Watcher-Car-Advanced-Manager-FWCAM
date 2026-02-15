# Vehicle Position Marker Implementation

## Problem
After implementing PR #101, map preview images were displayed in the trip edit dialog, but they lacked a visual indicator showing the exact vehicle position. Users could see the map tile but couldn't identify where the coordinates were located.

## Solution
Modified the `getStaticMapUrl()` function in `fwcam-card.js` to overlay a position marker on the OpenStreetMap tiles.

## Technical Implementation

### Calculation of Exact Position
The function now calculates the precise pixel coordinates of the vehicle position within the 256×256 pixel OSM tile:

```javascript
// Calculate the exact position within the tile (0-256 pixels)
const exactX = ((lon + 180) / 360 * n) - xtile;
const exactY = (latToMercatorY(clampedLat) * n) - ytile;
const pixelX = exactX * TILE_SIZE_PX;
const pixelY = exactY * TILE_SIZE_PX;
```

### SVG Overlay with Marker
The function creates an SVG that includes:
1. The OSM tile as a background image
2. A red circle marker (8px radius) with white border at the exact coordinates
3. A white center dot (3px radius) for better visibility

```javascript
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${TILE_SIZE_PX}" height="${TILE_SIZE_PX}">
  <image href="${tileUrl}" width="${TILE_SIZE_PX}" height="${TILE_SIZE_PX}"/>
  <circle cx="${pixelX}" cy="${pixelY}" r="8" fill="red" stroke="white" stroke-width="2" opacity="0.9"/>
  <circle cx="${pixelX}" cy="${pixelY}" r="3" fill="white" opacity="0.9"/>
</svg>`;
```

### Data URI Encoding
The SVG is encoded as a data URI and returned to be displayed in the img element:

```javascript
return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
```

## Changes Made

### Files Updated
- `custom_components/hafwcma/www/fwcam-card.js` (main bundled version)
- `fwcam-card/dist/fwcam-card.js` (standalone distribution)
- `www/fwcam-card/fwcam-card.js` (legacy copy)

### Key Features
- **Accurate positioning**: Uses Web Mercator projection calculations for precise marker placement
- **Visual marker**: Red/white circle design is clearly visible on any map background
- **Browser compatible**: SVG data URIs work in all modern browsers
- **No external dependencies**: Pure JavaScript implementation without additional libraries

## Testing
The implementation was tested with:
- Multiple coordinate sets (London, New York, Tokyo)
- Edge cases (near poles, invalid coordinates)
- Web Mercator projection clamping for extreme latitudes

## Benefits
✅ Users can now immediately see where their vehicle is located on the map  
✅ Improves usability of trip start/end location previews  
✅ No additional API calls or external services required  
✅ Consistent marker appearance across all maps  

## Future Enhancements
Possible improvements could include:
- Customizable marker colors based on trip type (start=green, end=red)
- Different marker styles (pin, arrow, car icon)
- Multiple zoom levels
- Tooltip showing exact coordinates
