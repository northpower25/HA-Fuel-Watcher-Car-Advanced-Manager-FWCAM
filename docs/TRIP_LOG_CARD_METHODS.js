/**
 * Trip Log Extension for FWCAM Card
 * 
 * This file contains the additional methods needed to implement trip log functionality
 * in the FWCAM card. These methods should be added to the FWCAMCard class in fwcam-card.js
 * 
 * @version 1.0.0
 * @author northpower25
 */

// ============================================================================
// INITIALIZATION (Add to constructor around line 43)
// ============================================================================

// Add these properties to the constructor:
this._filterTripYear = '';
this._filterTripMonth = '';
this._filterTripCategory = '';
this._sortTripColumn = 'timestamp_start';
this._sortTripDirection = 'desc';


// ============================================================================
// RENDER METHODS (Add after renderRefuelingLog method around line 770)
// ============================================================================

/**
 * Render trip log section with sorting and filtering
 */
renderTripLog(trips) {
  if (!trips || trips.length === 0) {
    return `
      <div class="section">
        <h3>Trip Log</h3>
        <p class="no-data">No trips recorded yet. Enable trip tracking to start logging trips.</p>
      </div>
    `;
  }
  
  // Apply filtering
  const filteredTrips = this.filterTrips(trips);
  
  // Apply sorting
  const sortedTrips = this.sortTrips(filteredTrips);
  
  // Get unique years for filter dropdown
  const years = this.getUniqueTripYears(trips);
  const months = [
    { value: '', label: 'All Months' },
    { value: '01', label: 'January' },
    { value: '02', label: 'February' },
    { value: '03', label: 'March' },
    { value: '04', label: 'April' },
    { value: '05', label: 'May' },
    { value: '06', label: 'June' },
    { value: '07', label: 'July' },
    { value: '08', label: 'August' },
    { value: '09', label: 'September' },
    { value: '10', label: 'October' },
    { value: '11', label: 'November' },
    { value: '12', label: 'December' }
  ];
  
  const categories = [
    { value: '', label: 'All Categories' },
    { value: 'business', label: 'Business' },
    { value: 'private', label: 'Private' },
    { value: 'commute', label: 'Commute' }
  ];
  
  return `
    <div class="section">
      <h3>Trip Log</h3>

      <div class="filter-controls">
        <label>
          Year:
          <select class="filter-select" data-filter="trip-year">
            <option value="">All Years</option>
            ${years.map(year => `
              <option value="${year}" ${this._filterTripYear === year ? 'selected' : ''}>${year}</option>
            `).join('')}
          </select>
        </label>
        <label>
          Month:
          <select class="filter-select" data-filter="trip-month">
            ${months.map(month => `
              <option value="${month.value}" ${this._filterTripMonth === month.value ? 'selected' : ''}>${month.label}</option>
            `).join('')}
          </select>
        </label>
        <label>
          Category:
          <select class="filter-select" data-filter="trip-category">
            ${categories.map(cat => `
              <option value="${cat.value}" ${this._filterTripCategory === cat.value ? 'selected' : ''}>${cat.label}</option>
            `).join('')}
          </select>
        </label>
        ${(this._filterTripYear || this._filterTripMonth || this._filterTripCategory) ? `
          <button class="clear-filters-button" data-action="clear-trip-filters">
            <ha-icon icon="mdi:filter-remove"></ha-icon>
            <span>Clear Filters</span>
          </button>
        ` : ''}
        <div class="filter-info">
          Showing ${sortedTrips.length} of ${trips.length} trips
        </div>
      </div>

      <div class="table-container">
        <table class="trip-table">
          <thead>
            <tr>
              <th class="sortable ${this._sortTripColumn === 'timestamp_start' ? 'sorted-' + this._sortTripDirection : ''}" 
                  data-sort-trip-column="timestamp_start">
                Start Time
                ${this.renderTripSortIcon('timestamp_start')}
              </th>
              <th class="sortable ${this._sortTripColumn === 'timestamp_end' ? 'sorted-' + this._sortTripDirection : ''}" 
                  data-sort-trip-column="timestamp_end">
                End Time
                ${this.renderTripSortIcon('timestamp_end')}
              </th>
              <th class="sortable ${this._sortTripColumn === 'distance_km' ? 'sorted-' + this._sortTripDirection : ''}" 
                  data-sort-trip-column="distance_km">
                Distance (km)
                ${this.renderTripSortIcon('distance_km')}
              </th>
              <th class="sortable ${this._sortTripColumn === 'duration_minutes' ? 'sorted-' + this._sortTripDirection : ''}" 
                  data-sort-trip-column="duration_minutes">
                Duration
                ${this.renderTripSortIcon('duration_minutes')}
              </th>
              <th class="sortable ${this._sortTripColumn === 'category' ? 'sorted-' + this._sortTripDirection : ''}" 
                  data-sort-trip-column="category">
                Category
                ${this.renderTripSortIcon('category')}
              </th>
              <th class="sortable ${this._sortTripColumn === 'fuel_consumed' ? 'sorted-' + this._sortTripDirection : ''}" 
                  data-sort-trip-column="fuel_consumed">
                Fuel (L)
                ${this.renderTripSortIcon('fuel_consumed')}
              </th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${sortedTrips.length === 0 ? `
              <tr>
                <td colspan="7" class="no-data">No trips match the current filters</td>
              </tr>
            ` : sortedTrips.slice(0, this._config.rows_per_page).map(trip => `
              <tr data-trip-id="${trip.trip_id}">
                <td>${this.formatDateTime(trip.timestamp_start)}</td>
                <td>${this.formatDateTime(trip.timestamp_end)}</td>
                <td>${this.formatNumber(trip.distance_km, 1)}</td>
                <td>${this.formatDuration(trip.duration_minutes)}</td>
                <td>
                  <span class="category-badge category-${trip.category || 'private'}">
                    ${this.capitalizeFirst(trip.category || 'private')}
                  </span>
                </td>
                <td>${trip.fuel_consumed ? this.formatNumber(trip.fuel_consumed, 2) : 'N/A'}</td>
                <td class="actions">
                  <button class="action-button edit-button" 
                          data-action="edit-trip" 
                          data-trip-id="${trip.trip_id}"
                          title="Edit">
                    <ha-icon icon="mdi:pencil"></ha-icon>
                  </button>
                  <button class="action-button delete-button" 
                          data-action="delete-trip" 
                          data-trip-id="${trip.trip_id}"
                          title="Delete">
                    <ha-icon icon="mdi:delete"></ha-icon>
                  </button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

/**
 * Render trip edit dialog
 */
renderTripDialog() {
  return `
    <div id="trip-dialog" class="dialog-overlay" style="display: none;">
      <div class="dialog-content">
        <div class="dialog-header">
          <h2 id="trip-dialog-title">Edit Trip</h2>
          <button class="dialog-close" data-action="close-trip-dialog">
            <ha-icon icon="mdi:close"></ha-icon>
          </button>
        </div>
        <div class="dialog-body">
          <form id="trip-form">
            <input type="hidden" id="trip-id" name="trip-id">
            
            <div class="form-section">
              <h3>Trip Information (Read-only)</h3>
              
              <div class="form-row">
                <div class="form-field">
                  <label>Start Time</label>
                  <input type="text" id="trip-timestamp-start" readonly>
                </div>
                <div class="form-field">
                  <label>End Time</label>
                  <input type="text" id="trip-timestamp-end" readonly>
                </div>
              </div>
              
              <div class="form-row">
                <div class="form-field">
                  <label>Distance (km)</label>
                  <input type="text" id="trip-distance" readonly>
                </div>
                <div class="form-field">
                  <label>Duration</label>
                  <input type="text" id="trip-duration" readonly>
                </div>
              </div>
              
              <div class="form-row">
                <div class="form-field">
                  <label>Fuel Consumed (L)</label>
                  <input type="text" id="trip-fuel-consumed" readonly>
                </div>
              </div>
            </div>
            
            <div class="form-section">
              <h3>Editable Fields</h3>
              
              <div class="form-field">
                <label for="trip-category">Category *</label>
                <select id="trip-category" name="category" required>
                  <option value="private">Private</option>
                  <option value="business">Business</option>
                  <option value="commute">Commute</option>
                </select>
              </div>
              
              <div class="form-field">
                <label for="trip-purpose">Purpose</label>
                <input type="text" id="trip-purpose" name="purpose" placeholder="e.g., Client meeting, Shopping">
              </div>
              
              <div class="form-field">
                <label for="trip-additional-costs">Additional Costs (€)</label>
                <input type="number" id="trip-additional-costs" name="additional_costs" step="0.01" min="0" placeholder="0.00">
                <small>Tolls, parking fees, etc.</small>
              </div>
              
              <div class="form-field">
                <label for="trip-notes">Notes</label>
                <textarea id="trip-notes" name="notes" rows="3" placeholder="Additional notes about this trip"></textarea>
              </div>
            </div>
            
            <div class="form-actions">
              <button type="button" class="secondary-button" data-action="close-trip-dialog">Cancel</button>
              <button type="submit" class="primary-button">Save Changes</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;
}

// ============================================================================
// FILTER & SORT METHODS (Add after sort/filter methods around line 850)
// ============================================================================

/**
 * Filter trips by year, month, and category
 */
filterTrips(trips) {
  if (!trips || trips.length === 0) return [];
  
  return trips.filter(trip => {
    if (!trip.timestamp_start) return false;
    
    const tripDate = new Date(trip.timestamp_start);
    const tripYear = tripDate.getFullYear().toString();
    const tripMonth = String(tripDate.getMonth() + 1).padStart(2, '0');
    const tripCategory = trip.category || 'private';
    
    // Year filter
    if (this._filterTripYear && tripYear !== this._filterTripYear) {
      return false;
    }
    
    // Month filter
    if (this._filterTripMonth && tripMonth !== this._filterTripMonth) {
      return false;
    }
    
    // Category filter
    if (this._filterTripCategory && tripCategory !== this._filterTripCategory) {
      return false;
    }
    
    return true;
  });
}

/**
 * Sort trips by column
 */
sortTrips(trips) {
  if (!trips || trips.length === 0) return [];
  
  const sorted = [...trips].sort((a, b) => {
    let aVal = a[this._sortTripColumn];
    let bVal = b[this._sortTripColumn];
    
    // Handle null/undefined values
    if (aVal === null || aVal === undefined) aVal = '';
    if (bVal === null || bVal === undefined) bVal = '';
    
    // Convert to lowercase for string comparison
    if (typeof aVal === 'string') aVal = aVal.toLowerCase();
    if (typeof bVal === 'string') bVal = bVal.toLowerCase();
    
    // Compare values
    if (aVal < bVal) return this._sortTripDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return this._sortTripDirection === 'asc' ? 1 : -1;
    return 0;
  });
  
  return sorted;
}

/**
 * Get unique years from trips
 */
getUniqueTripYears(trips) {
  if (!trips || trips.length === 0) return [];
  
  const years = new Set();
  trips.forEach(trip => {
    if (trip.timestamp_start) {
      const year = new Date(trip.timestamp_start).getFullYear().toString();
      years.add(year);
    }
  });
  
  return Array.from(years).sort((a, b) => b - a);
}

/**
 * Render sort icon for trip table headers
 */
renderTripSortIcon(column) {
  if (this._sortTripColumn !== column) {
    return '<ha-icon icon="mdi:unfold-more-horizontal" class="sort-icon inactive"></ha-icon>';
  }
  const icon = this._sortTripDirection === 'asc' ? 'mdi:arrow-up' : 'mdi:arrow-down';
  return `<ha-icon icon="${icon}" class="sort-icon active"></ha-icon>`;
}

// ============================================================================
// FORMAT METHODS (Add after format methods around line 400)
// ============================================================================

/**
 * Format duration from minutes to HH:MM
 */
formatDuration(minutes) {
  if (!minutes || minutes === 0) return '0:00';
  
  const hours = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  
  return `${hours}:${String(mins).padStart(2, '0')}`;
}

/**
 * Capitalize first letter of string
 */
capitalizeFirst(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// ============================================================================
// EVENT HANDLERS (Add to attachEventListeners method around line 920)
// ============================================================================

// Add these cases to the existing event listener attachment:

// Trip filter changes
filterSelects = this.shadowRoot.querySelectorAll('.filter-select[data-filter^="trip-"]');
filterSelects.forEach(select => {
  select.addEventListener('change', (e) => {
    const filterType = e.target.dataset.filter;
    if (filterType === 'trip-year') {
      this._filterTripYear = e.target.value;
    } else if (filterType === 'trip-month') {
      this._filterTripMonth = e.target.value;
    } else if (filterType === 'trip-category') {
      this._filterTripCategory = e.target.value;
    }
    this.forceRender();
  });
});

// Trip table sorting
const tripSortHeaders = this.shadowRoot.querySelectorAll('[data-sort-trip-column]');
tripSortHeaders.forEach(header => {
  header.addEventListener('click', (e) => {
    const column = e.currentTarget.dataset.sortTripColumn;
    if (this._sortTripColumn === column) {
      this._sortTripDirection = this._sortTripDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this._sortTripColumn = column;
      this._sortTripDirection = 'desc';
    }
    this.forceRender();
  });
});

// Clear trip filters button
const clearTripFiltersButton = this.shadowRoot.querySelector('[data-action="clear-trip-filters"]');
if (clearTripFiltersButton) {
  clearTripFiltersButton.addEventListener('click', () => {
    this._filterTripYear = '';
    this._filterTripMonth = '';
    this._filterTripCategory = '';
    this.forceRender();
  });
}

// Edit trip button
const editTripButtons = this.shadowRoot.querySelectorAll('[data-action="edit-trip"]');
editTripButtons.forEach(button => {
  button.addEventListener('click', (e) => {
    const tripId = parseInt(e.currentTarget.dataset.tripId);
    this.showEditTripDialog(tripId);
  });
});

// Delete trip button
const deleteTripButtons = this.shadowRoot.querySelectorAll('[data-action="delete-trip"]');
deleteTripButtons.forEach(button => {
  button.addEventListener('click', (e) => {
    const tripId = parseInt(e.currentTarget.dataset.tripId);
    this.deleteTrip(tripId);
  });
});

// Trip dialog close buttons
const closeTripDialogButtons = this.shadowRoot.querySelectorAll('[data-action="close-trip-dialog"]');
closeTripDialogButtons.forEach(button => {
  button.addEventListener('click', () => {
    this.closeTripDialog();
  });
});

// Trip dialog form submit
const tripForm = this.shadowRoot.getElementById('trip-form');
if (tripForm) {
  tripForm.addEventListener('submit', (e) => {
    e.preventDefault();
    this.handleTripFormSubmit();
  });
}

// Trip dialog background click to close
const tripDialog = this.shadowRoot.getElementById('trip-dialog');
if (tripDialog) {
  tripDialog.addEventListener('click', (e) => {
    if (e.target === tripDialog) {
      this.closeTripDialog();
    }
  });
}

// ============================================================================
// DIALOG METHODS (Add after dialog methods around line 1100)
// ============================================================================

/**
 * Show edit trip dialog
 */
showEditTripDialog(tripId) {
  const trip = this._recentTrips.find(t => t.trip_id === tripId);
  if (!trip) {
    console.error('Trip not found:', tripId);
    return;
  }
  
  const dialog = this.shadowRoot.getElementById('trip-dialog');
  if (!dialog) return;
  
  // Fill form with trip data
  const form = this.shadowRoot.getElementById('trip-form');
  if (form) {
    form.querySelector('#trip-id').value = trip.trip_id;
    form.querySelector('#trip-timestamp-start').value = this.formatDateTime(trip.timestamp_start);
    form.querySelector('#trip-timestamp-end').value = this.formatDateTime(trip.timestamp_end);
    form.querySelector('#trip-distance').value = this.formatNumber(trip.distance_km, 1) + ' km';
    form.querySelector('#trip-duration').value = this.formatDuration(trip.duration_minutes);
    form.querySelector('#trip-fuel-consumed').value = trip.fuel_consumed ? this.formatNumber(trip.fuel_consumed, 2) + ' L' : 'N/A';
    form.querySelector('#trip-category').value = trip.category || 'private';
    form.querySelector('#trip-purpose').value = trip.purpose || '';
    form.querySelector('#trip-additional-costs').value = trip.additional_costs || '';
    form.querySelector('#trip-notes').value = trip.notes || '';
  }
  
  dialog.style.display = 'flex';
}

/**
 * Close trip dialog
 */
closeTripDialog() {
  const dialog = this.shadowRoot.getElementById('trip-dialog');
  if (dialog) {
    dialog.style.display = 'none';
  }
}

/**
 * Handle trip form submit
 */
async handleTripFormSubmit() {
  const form = this.shadowRoot.getElementById('trip-form');
  if (!form) return;
  
  const tripId = parseInt(form.querySelector('#trip-id').value);
  const category = form.querySelector('#trip-category').value;
  const purpose = form.querySelector('#trip-purpose').value;
  const additionalCosts = parseFloat(form.querySelector('#trip-additional-costs').value) || 0;
  const notes = form.querySelector('#trip-notes').value;
  
  const tripData = {
    config_entry_id: this.getConfigEntryId(),
    trip_id: tripId,
    category: category,
    purpose: purpose || undefined,
    additional_costs: additionalCosts || undefined,
    notes: notes || undefined
  };
  
  try {
    await this.editTrip(tripData);
    this.closeTripDialog();
  } catch (error) {
    console.error('Error editing trip:', error);
    alert('Failed to edit trip. Please try again.');
  }
}

// ============================================================================
// CSS STYLES (Add to getStyles method around line 1550)
// ============================================================================

/* Add these styles to the getStyles() method */

/* Trip table styles */
.trip-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.trip-table th {
  background: var(--primary-background-color);
  padding: 12px 8px;
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid var(--divider-color);
  white-space: nowrap;
}

.trip-table td {
  padding: 10px 8px;
  border-bottom: 1px solid var(--divider-color);
}

.trip-table tr:hover {
  background: var(--table-row-hover-color, rgba(0, 0, 0, 0.05));
}

/* Category badges */
.category-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  text-transform: capitalize;
}

.category-business {
  background: var(--label-badge-blue, #2196F3);
  color: white;
}

.category-private {
  background: var(--label-badge-grey, #9E9E9E);
  color: white;
}

.category-commute {
  background: var(--label-badge-green, #4CAF50);
  color: white;
}

/* Trip dialog styles */
#trip-dialog .dialog-content {
  max-width: 600px;
}

#trip-dialog .form-section {
  margin-bottom: 24px;
}

#trip-dialog .form-section h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-text-color);
  border-bottom: 1px solid var(--divider-color);
  padding-bottom: 8px;
}

#trip-dialog .form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

#trip-dialog .form-field input[readonly] {
  background: var(--disabled-text-color, #f5f5f5);
  cursor: not-allowed;
  color: var(--secondary-text-color);
}

#trip-dialog textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--divider-color);
  border-radius: 4px;
  font-family: inherit;
  resize: vertical;
}

#trip-dialog small {
  display: block;
  margin-top: 4px;
  color: var(--secondary-text-color);
  font-size: 12px;
}
