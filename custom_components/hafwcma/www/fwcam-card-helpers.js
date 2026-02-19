/**
 * FWCAM Card Helper Functions
 * 
 * Provides reusable helper functions and UI components for the FWCAM card.
 * 
 * @version 1.0.0
 */

/**
 * Create a help button with popup dialog
 * @param {string} helpKey - Key to look up help content
 * @param {string} lang - Language code ('en' or 'de')
 * @returns {string} HTML string for help button
 */
export function createHelpButton(helpKey, lang = 'en') {
  return `
    <button class="help-button" onclick="window.fwcamShowHelp('${helpKey}', '${lang}')" 
            title="${lang === 'de' ? 'Hilfe anzeigen' : 'Show help'}"
            aria-label="${lang === 'de' ? 'Hilfe' : 'Help'}">
      <ha-icon icon="mdi:help-circle-outline"></ha-icon>
    </button>
  `;
}

/**
 * Get help content HTML for display in dialog
 * @param {string} helpKey - Key to look up help content
 * @param {string} lang - Language code ('en' or 'de')
 * @param {object} HELP_CONTENT - Help content object
 * @returns {string} HTML string for help content
 */
export function getHelpContentHTML(helpKey, lang, HELP_CONTENT) {
  const content = HELP_CONTENT[lang] && HELP_CONTENT[lang][helpKey];
  
  if (!content) {
    return `<p>${lang === 'de' ? 'Hilfe nicht verfügbar' : 'Help not available'}</p>`;
  }
  
  return `
    <div class="help-content">
      <h3>${content.title}</h3>
      <p class="help-description">${content.description}</p>
      ${content.details ? `<p class="help-details">${content.details}</p>` : ''}
      ${content.doc_link ? `
        <p class="help-link">
          <a href="${content.doc_link}" target="_blank" rel="noopener noreferrer">
            <ha-icon icon="mdi:book-open-variant"></ha-icon>
            ${lang === 'de' ? 'Vollständige Dokumentation' : 'Full Documentation'}
          </a>
        </p>
      ` : ''}
    </div>
  `;
}

/**
 * Create a section header with optional help button
 * @param {string} title - Section title
 * @param {string} helpKey - Optional help content key
 * @param {string} lang - Language code
 * @returns {string} HTML string for section header
 */
export function createSectionHeader(title, helpKey = null, lang = 'en') {
  return `
    <div class="section-header">
      <h3>${title}</h3>
      ${helpKey ? createHelpButton(helpKey, lang) : ''}
    </div>
  `;
}

/**
 * Format a number with locale-specific formatting
 * @param {number} value - Number to format
 * @param {number} decimals - Number of decimal places
 * @param {string} lang - Language code
 * @returns {string} Formatted number
 */
export function formatNumber(value, decimals = 2, lang = 'en') {
  if (value === null || value === undefined || isNaN(value)) {
    return '-';
  }
  
  const locale = lang === 'de' ? 'de-DE' : 'en-US';
  return value.toLocaleString(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
}

/**
 * Format a date with locale-specific formatting
 * @param {string|Date} date - Date to format
 * @param {string} lang - Language code
 * @param {boolean} includeTime - Whether to include time
 * @returns {string} Formatted date
 */
export function formatDate(date, lang = 'en', includeTime = true) {
  if (!date) return '-';
  
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const locale = lang === 'de' ? 'de-DE' : 'en-US';
  
  const options = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  };
  
  if (includeTime) {
    options.hour = '2-digit';
    options.minute = '2-digit';
  }
  
  return dateObj.toLocaleString(locale, options);
}

/**
 * Create a statistics card
 * @param {string} title - Card title
 * @param {string} value - Main value to display
 * @param {string} unit - Unit of measurement
 * @param {string} icon - MDI icon name
 * @param {string} helpKey - Optional help key
 * @param {string} lang - Language code
 * @returns {string} HTML for statistics card
 */
export function createStatCard(title, value, unit, icon, helpKey = null, lang = 'en') {
  return `
    <div class="stat-card">
      <div class="stat-card-header">
        <ha-icon icon="${icon}"></ha-icon>
        <span class="stat-card-title">${title}</span>
        ${helpKey ? createHelpButton(helpKey, lang) : ''}
      </div>
      <div class="stat-card-value">
        <span class="stat-value">${value}</span>
        <span class="stat-unit">${unit}</span>
      </div>
    </div>
  `;
}

/**
 * Create a collapsible section
 * @param {string} id - Unique ID for the section
 * @param {string} title - Section title
 * @param {string} content - Section content HTML
 * @param {boolean} expanded - Whether section is initially expanded
 * @param {string} helpKey - Optional help key
 * @param {string} lang - Language code
 * @returns {string} HTML for collapsible section
 */
export function createCollapsibleSection(id, title, content, expanded = false, helpKey = null, lang = 'en') {
  return `
    <div class="collapsible-section ${expanded ? 'expanded' : ''}">
      <div class="collapsible-header" onclick="window.fwcamToggleSection('${id}')">
        <ha-icon class="collapse-icon" icon="mdi:chevron-${expanded ? 'down' : 'right'}"></ha-icon>
        <span class="collapsible-title">${title}</span>
        ${helpKey ? createHelpButton(helpKey, lang) : ''}
      </div>
      <div class="collapsible-content" id="${id}" style="display: ${expanded ? 'block' : 'none'};">
        ${content}
      </div>
    </div>
  `;
}

/**
 * Create a progress bar
 * @param {number} percentage - Progress percentage (0-100)
 * @param {string} color - Optional color
 * @returns {string} HTML for progress bar
 */
export function createProgressBar(percentage, color = null) {
  const clampedPercentage = Math.min(100, Math.max(0, percentage));
  const barColor = color || (
    clampedPercentage < 20 ? '#f44336' : 
    clampedPercentage < 50 ? '#ff9800' : 
    '#4caf50'
  );
  
  return `
    <div class="progress-bar">
      <div class="progress-bar-fill" style="width: ${clampedPercentage}%; background-color: ${barColor};">
        <span class="progress-bar-text">${Math.round(clampedPercentage)}%</span>
      </div>
    </div>
  `;
}

/**
 * Create a badge
 * @param {string} text - Badge text
 * @param {string} type - Badge type (success, warning, error, info)
 * @returns {string} HTML for badge
 */
export function createBadge(text, type = 'info') {
  const colors = {
    success: '#4caf50',
    warning: '#ff9800',
    error: '#f44336',
    info: '#2196f3'
  };
  
  return `
    <span class="badge badge-${type}" style="background-color: ${colors[type] || colors.info};">
      ${text}
    </span>
  `;
}

/**
 * Get confidence level badge HTML
 * @param {number} confidence - Confidence value (0-1)
 * @param {string} lang - Language code
 * @returns {string} HTML for confidence badge
 */
export function getConfidenceBadge(confidence, lang = 'en') {
  if (confidence >= 0.95) {
    return createBadge(lang === 'de' ? 'Hoch' : 'High', 'success');
  } else if (confidence >= 0.7) {
    return createBadge(lang === 'de' ? 'Mittel' : 'Medium', 'warning');
  } else {
    return createBadge(lang === 'de' ? 'Niedrig' : 'Low', 'error');
  }
}

/**
 * Sanitize HTML to prevent XSS
 * @param {string} html - HTML to sanitize
 * @returns {string} Sanitized HTML
 */
export function sanitizeHTML(html) {
  const div = document.createElement('div');
  div.textContent = html;
  return div.innerHTML;
}

/**
 * Create empty state message
 * @param {string} message - Message to display
 * @param {string} icon - Optional icon
 * @returns {string} HTML for empty state
 */
export function createEmptyState(message, icon = 'mdi:information-outline') {
  return `
    <div class="empty-state">
      <ha-icon icon="${icon}"></ha-icon>
      <p>${message}</p>
    </div>
  `;
}

/**
 * Global functions that need to be attached to window
 */
window.fwcamShowHelp = function(helpKey, lang) {
  // This will be implemented in the main card
  const event = new CustomEvent('fwcam-show-help', {
    detail: { helpKey, lang },
    bubbles: true,
    composed: true
  });
  document.dispatchEvent(event);
};

window.fwcamToggleSection = function(sectionId) {
  const section = document.getElementById(sectionId);
  const parent = section?.closest('.collapsible-section');
  const icon = parent?.querySelector('.collapse-icon');
  
  if (section && parent) {
    const isExpanded = section.style.display !== 'none';
    section.style.display = isExpanded ? 'none' : 'block';
    parent.classList.toggle('expanded');
    
    if (icon) {
      icon.setAttribute('icon', isExpanded ? 'mdi:chevron-right' : 'mdi:chevron-down');
    }
  }
};

console.info(
  '%c FWCAM-CARD-HELPERS %c v1.0.0 ',
  'color: white; background: #4caf50; font-weight: 700;',
  'color: #4caf50; background: white; font-weight: 700;'
);
