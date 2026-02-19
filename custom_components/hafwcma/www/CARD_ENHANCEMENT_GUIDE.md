# FWCAM Card Enhancement Guide

This guide explains how to use the helper modules to enhance the FWCAM card with help popups, statistics displays, and improved UI components.

## Overview

The FWCAM card can be enhanced with:
- **Help System** - Inline help popups with documentation links
- **Statistics Cards** - Pre-styled stat displays
- **Collapsible Sections** - Organized, expandable content areas
- **Helper Functions** - Reusable UI components

## Available Helper Modules

### 1. `fwcam-card-help.js`

Contains help content in English and German for all entities and features.

**Structure:**
```javascript
HELP_CONTENT = {
  en: {
    fuel_price: {
      title: "Fuel Price Sensor",
      description: "...",
      details: "...",
      doc_link: "https://..."
    },
    // ... more entities
  },
  de: {
    // German translations
  }
}
```

### 2. `fwcam-card-helpers.js`

Provides reusable UI component functions.

**Available Functions:**

#### createHelpButton(helpKey, lang)
Creates a help button that triggers a popup.

```javascript
import { createHelpButton } from './fwcam-card-helpers.js';

const helpBtn = createHelpButton('fuel_price', 'en');
// Returns: <button class="help-button">...</button>
```

#### createSectionHeader(title, helpKey, lang)
Creates a section header with optional help button.

```javascript
const header = createSectionHeader('Fuel Price Information', 'fuel_price', 'en');
```

#### createStatCard(title, value, unit, icon, helpKey, lang)
Creates a styled statistics card.

```javascript
const statCard = createStatCard(
  'Avg Consumption',
  '6.5',
  'L/100km',
  'mdi:gauge',
  'consumption_prediction',
  'en'
);
```

#### createCollapsibleSection(id, title, content, expanded, helpKey, lang)
Creates an expandable/collapsible section.

```javascript
const debugSection = createCollapsibleSection(
  'debug-info',
  'Debug Information',
  '<p>Debug content here...</p>',
  false,  // Initially collapsed
  'statistics',
  'en'
);
```

#### createProgressBar(percentage, color)
Creates a styled progress bar.

```javascript
const tankBar = createProgressBar(75);  // 75% full
```

#### createBadge(text, type)
Creates a colored badge.

```javascript
const badge = createBadge('High', 'success');  // Green badge
// Types: 'success', 'warning', 'error', 'info'
```

#### getConfidenceBadge(confidence, lang)
Creates a confidence level badge.

```javascript
const confidenceBadge = getConfidenceBadge(0.95, 'en');
// Returns: 'High' badge in green
```

#### formatNumber(value, decimals, lang)
Formats numbers with locale-specific formatting.

```javascript
const formatted = formatNumber(1234.56, 2, 'de');
// Returns: "1.234,56" (German format)
```

#### formatDate(date, lang, includeTime)
Formats dates with locale-specific formatting.

```javascript
const formatted = formatDate('2024-01-15T10:30:00', 'en', true);
// Returns: "01/15/2024, 10:30 AM"
```

## Integration Examples

### Example 1: Add Help Button to Existing Section

```javascript
// In fwcam-card.js, find the section rendering code:

// BEFORE:
html += `<h3>Fuel Price Information</h3>`;

// AFTER:
import { createSectionHeader } from './fwcam-card-helpers.js';
html += createSectionHeader('Fuel Price Information', 'fuel_price', this.getLanguage());
```

### Example 2: Add Statistics Cards

```javascript
import { createStatCard } from './fwcam-card-helpers.js';

// In the statistics rendering section:
const stats = `
  ${createStatCard('Average Consumption', '6.5', 'L/100km', 'mdi:gauge', 'consumption_prediction', 'en')}
  ${createStatCard('Total Distance', '15234', 'km', 'mdi:map-marker-distance', null, 'en')}
  ${createStatCard('Total Refuelings', '87', '', 'mdi:gas-station', 'refueling_log', 'en')}
`;
```

### Example 3: Add Collapsible Debug Section

```javascript
import { createCollapsibleSection } from './fwcam-card-helpers.js';

const debugContent = `
  <div class="debug-info">
    <p>Last API Call: ${lastApiCall}</p>
    <p>Cache Status: ${cacheStatus}</p>
  </div>
`;

const debugSection = createCollapsibleSection(
  'debug-section',
  '🐛 Debug Information',
  debugContent,
  false,  // Collapsed by default
  'statistics',  // Help key
  'en'
);

// Add to card HTML
html += debugSection;
```

### Example 4: Add Help Popup Dialog Handler

```javascript
// In the FWCAMCard class, add a listener for help events:

constructor() {
  super();
  // ... existing code ...
  
  // Listen for help button clicks
  document.addEventListener('fwcam-show-help', (e) => {
    this.showHelpDialog(e.detail.helpKey, e.detail.lang);
  });
}

showHelpDialog(helpKey, lang) {
  import('./fwcam-card-help.js').then(module => {
    const HELP_CONTENT = module.HELP_CONTENT;
    const content = HELP_CONTENT[lang] && HELP_CONTENT[lang][helpKey];
    
    if (!content) return;
    
    // Create dialog HTML
    const dialog = document.createElement('div');
    dialog.className = 'fwcam-help-dialog';
    dialog.innerHTML = `
      <div class="help-dialog-overlay" onclick="this.parentElement.remove()"></div>
      <div class="help-dialog-content">
        <h2>${content.title}</h2>
        <p class="help-description">${content.description}</p>
        ${content.details ? `<p class="help-details">${content.details}</p>` : ''}
        ${content.doc_link ? `
          <p class="help-link">
            <a href="${content.doc_link}" target="_blank" rel="noopener noreferrer">
              📖 ${lang === 'de' ? 'Vollständige Dokumentation' : 'Full Documentation'}
            </a>
          </p>
        ` : ''}
        <button onclick="this.closest('.fwcam-help-dialog').remove()">
          ${lang === 'de' ? 'Schließen' : 'Close'}
        </button>
      </div>
    `;
    
    document.body.appendChild(dialog);
  });
}
```

### Example 5: Add Help Dialog Styles

```javascript
// In the getStyles() method of FWCAMCard, add:

const helpStyles = `
  .fwcam-help-dialog {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 10000;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .help-dialog-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
  }
  
  .help-dialog-content {
    position: relative;
    background: var(--card-background-color);
    border-radius: 8px;
    padding: 24px;
    max-width: 600px;
    max-height: 80vh;
    overflow-y: auto;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    z-index: 1;
  }
  
  .help-dialog-content h2 {
    margin: 0 0 16px 0;
    color: var(--primary-text-color);
  }
  
  .help-description {
    font-size: 14px;
    color: var(--primary-text-color);
    margin-bottom: 12px;
  }
  
  .help-details {
    font-size: 13px;
    color: var(--secondary-text-color);
    margin-bottom: 16px;
    padding: 12px;
    background: var(--secondary-background-color);
    border-radius: 4px;
  }
  
  .help-link {
    margin: 16px 0;
  }
  
  .help-link a {
    color: var(--primary-color);
    text-decoration: none;
    font-weight: 500;
  }
  
  .help-link a:hover {
    text-decoration: underline;
  }
  
  .help-dialog-content button {
    background: var(--primary-color);
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
  }
  
  .help-dialog-content button:hover {
    opacity: 0.9;
  }
  
  .help-button {
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 4px;
    margin-left: 8px;
    color: var(--secondary-text-color);
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  
  .help-button:hover {
    color: var(--primary-color);
  }
  
  .help-button ha-icon {
    --mdc-icon-size: 20px;
  }
  
  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }
  
  .section-header h3 {
    margin: 0;
    flex: 1;
  }
  
  .stat-card {
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  
  .stat-card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--secondary-text-color);
    font-size: 13px;
  }
  
  .stat-card-header ha-icon {
    --mdc-icon-size: 18px;
  }
  
  .stat-card-value {
    display: flex;
    align-items: baseline;
    gap: 4px;
  }
  
  .stat-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--primary-text-color);
  }
  
  .stat-unit {
    font-size: 14px;
    color: var(--secondary-text-color);
  }
  
  .collapsible-section {
    margin: 16px 0;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    overflow: hidden;
  }
  
  .collapsible-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: var(--secondary-background-color);
    cursor: pointer;
    user-select: none;
  }
  
  .collapsible-header:hover {
    background: var(--disabled-color);
  }
  
  .collapse-icon {
    --mdc-icon-size: 20px;
    transition: transform 0.2s;
  }
  
  .collapsible-section.expanded .collapse-icon {
    transform: rotate(90deg);
  }
  
  .collapsible-title {
    flex: 1;
    font-weight: 500;
  }
  
  .collapsible-content {
    padding: 16px;
  }
  
  .progress-bar {
    width: 100%;
    height: 24px;
    background: var(--disabled-color);
    border-radius: 12px;
    overflow: hidden;
    position: relative;
  }
  
  .progress-bar-fill {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: width 0.3s ease;
  }
  
  .progress-bar-text {
    font-size: 12px;
    font-weight: 600;
    color: white;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  }
  
  .badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    color: white;
  }
  
  .empty-state {
    text-align: center;
    padding: 48px 24px;
    color: var(--secondary-text-color);
  }
  
  .empty-state ha-icon {
    --mdc-icon-size: 48px;
    opacity: 0.5;
    margin-bottom: 16px;
  }
  
  .empty-state p {
    font-size: 14px;
    margin: 0;
  }
`;

return baseStyles + helpStyles;
```

## Best Practices

### 1. Progressive Enhancement
Add help features incrementally:
- Start with help buttons on main sections
- Add statistics cards for key metrics
- Implement collapsible sections for advanced features
- Add debug section last

### 2. Language Support
Always provide both English and German:
```javascript
const lang = this.getLanguage();  // Returns 'en' or 'de'
const helpBtn = createHelpButton('fuel_price', lang);
```

### 3. Accessibility
- Use semantic HTML
- Include `aria-label` attributes
- Ensure keyboard navigation works
- Test with screen readers

### 4. Performance
- Lazy load help content
- Cache formatted strings
- Minimize DOM manipulation
- Use event delegation

### 5. Styling
- Use CSS variables for theme compatibility
- Follow Home Assistant design patterns
- Ensure responsive design
- Test in both light and dark modes

## Testing

### Manual Testing Checklist
- [ ] Help buttons appear correctly
- [ ] Help popups open and close properly
- [ ] Links open in new tabs
- [ ] Content is readable in light/dark mode
- [ ] Mobile display is correct
- [ ] Statistics cards display properly
- [ ] Collapsible sections work
- [ ] Progress bars render correctly
- [ ] Badges have correct colors
- [ ] Language switching works

### Browser Compatibility
Test in:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Home Assistant Companion App (mobile)

## Troubleshooting

### Help Popup Not Appearing
1. Check browser console for errors
2. Verify `fwcam-card-help.js` is loaded
3. Ensure event listener is registered
4. Check z-index conflicts

### Styles Not Applied
1. Verify styles are in `getStyles()` method
2. Check CSS variable names match theme
3. Clear browser cache
4. Reload resources

### Content Not Translated
1. Verify language detection works
2. Check HELP_CONTENT has both en/de
3. Ensure helpKey matches content keys
4. Validate fallback to 'en' works

## Future Enhancements

Planned features:
- [ ] Inline tooltips for quick help
- [ ] Video tutorials embedded in help
- [ ] Interactive tours for first-time users
- [ ] Context-sensitive help based on user actions
- [ ] Help search functionality
- [ ] Community-contributed tips

## Contributing

To add new help content:
1. Edit `fwcam-card-help.js`
2. Add entries for both `en` and `de`
3. Include title, description, details, doc_link
4. Test in both languages
5. Submit a pull request

## Resources

- [FWCAM Card Documentation](../docs/user_docs/REFUELING_LOG_GUIDE.md)
- [Entity Documentation](../docs/ENTITIES.md)
- [Home Assistant Lovelace Docs](https://www.home-assistant.io/lovelace/)
- [MDI Icon Reference](https://materialdesignicons.com/)

---

**Need help?** Open an issue on GitHub or check the documentation!
