"""
Historical Data Import for haFWCMA
-----------------------------------
Import historical data from Home Assistant's recorder to backfill
odometer history, detect past refueling events, and calculate
consumption statistics from existing vehicle entity data.

This allows the integration to use historical data from before
it was installed, providing immediate predictions and statistics.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util
from homeassistant.components.recorder import get_instance, history
from homeassistant.components.recorder.statistics import statistics_during_period

from .storage import (
    add_odometer_observation,
    add_refuel_event,
    load_data,
    save_data,
)

_LOGGER = logging.getLogger(__name__)


def _normalize_numeric_string(value: str | float | int) -> str:
    """Normalize numeric string by replacing comma decimal separators with dots.
    
    Handles both German locale format (e.g., "1.234,56") and standard format (e.g., "1234.56").
    This prevents misinterpretation of localized number formats.
    
    Args:
        value: Numeric value as string, float, or int
        
    Returns:
        Normalized string with dot as decimal separator
    """
    if isinstance(value, (int, float)):
        return str(value)
    
    value_str = str(value).strip()
    
    # Count dots and commas to determine format
    dot_count = value_str.count('.')
    comma_count = value_str.count(',')
    
    if comma_count > 0 and dot_count > 0:
        # Mixed format - determine which is decimal separator
        last_dot_pos = value_str.rfind('.')
        last_comma_pos = value_str.rfind(',')
        
        if last_comma_pos > last_dot_pos:
            # Comma is decimal separator (German format: "1.234,56")
            value_str = value_str.replace('.', '').replace(',', '.')
        else:
            # Dot is decimal separator (English format: "1,234.56")
            value_str = value_str.replace(',', '')
    elif comma_count > 1:
        # Multiple commas - they're thousands separators (English format: "1,234,567")
        value_str = value_str.replace(',', '')
    elif comma_count == 1:
        # Single comma - could be decimal separator or thousands separator
        # Heuristics:
        # - If exactly 3 digits after comma AND comma is not near start: thousands separator (e.g., "1,234")
        # - If 1-2 digits after comma: likely decimal separator (e.g., "123,45" or "1,5")
        # - If comma is very early (first or second position): likely decimal (e.g., "1,5" or "12,34")
        comma_pos = value_str.find(',')
        digits_after_comma = len(value_str) - comma_pos - 1
        
        if digits_after_comma == 3 and comma_pos >= 1:
            # Likely thousands separator (e.g., "1,234" or "12,345")
            # But only if there are enough digits before comma
            digits_before_comma = comma_pos
            if digits_before_comma >= 1 and digits_before_comma <= 3:
                # This looks like thousands separator format
                value_str = value_str.replace(',', '')
            else:
                # Unusual format - treat as decimal to be safe
                value_str = value_str.replace(',', '.')
        else:
            # 1-2 digits after comma, or > 3 digits - likely decimal separator
            value_str = value_str.replace(',', '.')
    elif dot_count > 1:
        # Multiple dots - they're thousands separators (German format: "1.234.567")
        value_str = value_str.replace('.', '')
    
    return value_str


# Simple state-like class for wrapping long-term statistics data
class _StateLike:
    """Minimal state-like object to wrap long-term statistics data."""
    
    def __init__(self, value: float, timestamp: datetime) -> None:
        """Initialize state-like object.
        
        Args:
            value: The sensor value
            timestamp: The timestamp for this value
        """
        self.state = str(value)
        self.last_changed = timestamp
        self.attributes = {}

# Constants for historical data import configuration
REFUEL_DETECTION_THRESHOLD_PERCENT = 3.5  # Minimum tank level increase (as percentage of tank capacity) to detect refueling
REFUEL_MERGE_TIME_WINDOW_MINUTES = 90  # Time window to merge multiple refueling events into one (90 min covers hourly statistics data where a single fill-up may span two consecutive hourly readings)
REFUEL_DETECTION_MIN_TIME_GAP_MINUTES = 5  # Minimum time between separate refuelings (deprecated - use merge window)
ODOMETER_LOOKUP_MAX_TIME_DIFF_HOURS = 1  # Maximum time difference for odometer lookup
PRICE_LOOKUP_WINDOW_DAYS = 7  # Maximum age of price data to use for historical events
SECONDS_PER_HOUR = 3600  # Number of seconds in an hour
DUPLICATE_DETECTION_WINDOW_HOURS = 24  # Window for detecting duplicate refuelings
PERCENTAGE_MULTIPLIER = 100  # Multiplier for converting decimals to percentages
PERCENTAGE_MAX_VALUE = 100.0  # Maximum valid value for a percentage-based sensor reading (0–100 range)
UNIT_DETECTION_SAMPLE_SIZE = 10  # Number of historical values to sample when inferring sensor unit from value range
INVALID_SENSOR_STATES = ["unknown", "unavailable", "none", "null", None, ""]  # States to ignore when processing sensor data
SHORT_TERM_HISTORY_DAYS = 10  # Home Assistant default history retention (short-term)
LONG_TERM_STATISTICS_OVERLAP_DAYS = 1  # Overlap between short-term and long-term queries to ensure no gaps
MAX_ODOMETER_HISTORY_ENTRIES = 1000  # Maximum number of odometer history entries to keep
ODOMETER_HISTORY_TRUNCATE_TO = 900  # Truncate to this size before adding new entries to ensure we stay under max


async def import_historical_vehicle_data(
    hass: HomeAssistant,
    entry: ConfigEntry,
    lookback_days: int = 90,
    force_reimport: bool = False,
    import_type: str = "automatic",
) -> dict[str, Any]:
    """Import historical vehicle data from Home Assistant's recorder.
    
    This function queries the recorder for historical states of the configured
    vehicle entities (odometer, tank level, range) and processes them to:
    1. Build odometer history
    2. Detect refueling events
    3. Calculate consumption between refuelings
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        lookback_days: Number of days to look back (default: 90)
        force_reimport: If True, reimport even if data already exists
        import_type: Type of import - "automatic" or "manual" (default: "automatic")
        
    Returns:
        Dictionary with import statistics:
        {
            "imported": bool,
            "reason": str,
            "odometer_points_imported": int,
            "refuel_events_detected": int,
            "date_range": str,
            "errors": list[str],
            "timestamp": str,
            "import_type": str,
        }
    """
    from ..const import (
        CONF_ODOMETER_ENTITY,
        CONF_TANK_LEVEL_ENTITY,
        CONF_RANGE_ENTITY,
        CONF_FUEL_TYPE,
        CONF_TANK_CAPACITY,
        DEFAULT_TANK_CAPACITY,
    )
    
    _LOGGER.info("Starting historical vehicle data import (lookback: %d days, type: %s)", lookback_days, import_type)
    
    timestamp = dt_util.now().isoformat()
    result = {
        "imported": False,
        "reason": "Not started",
        "odometer_points_imported": 0,
        "refuel_events_detected": 0,
        "date_range": "",
        "errors": [],
        "timestamp": timestamp,
        "import_type": import_type,
    }
    
    # Check if we should skip import (already imported and not forced)
    if not force_reimport:
        data = await load_data(hass, entry)
        if data.get("historical_import_completed"):
            result["reason"] = "Historical import already completed (use force_reimport to re-import)"
            _LOGGER.info("Skipping historical import - already completed")
            return result
    
    # Get entity IDs from config
    config = entry.data
    options = entry.options
    
    odometer_entity = options.get(CONF_ODOMETER_ENTITY) or config.get(CONF_ODOMETER_ENTITY)
    tank_level_entity = options.get(CONF_TANK_LEVEL_ENTITY) or config.get(CONF_TANK_LEVEL_ENTITY)
    range_entity = options.get(CONF_RANGE_ENTITY) or config.get(CONF_RANGE_ENTITY)
    fuel_type = options.get(CONF_FUEL_TYPE) or config.get(CONF_FUEL_TYPE, "e5")
    tank_capacity = options.get(CONF_TANK_CAPACITY) or config.get(CONF_TANK_CAPACITY, DEFAULT_TANK_CAPACITY)
    
    # Validate that at least odometer and tank level are configured
    if not odometer_entity:
        result["reason"] = "Odometer entity not configured"
        result["errors"].append("Cannot import without odometer entity")
        _LOGGER.warning("Cannot import historical data: odometer entity not configured")
        return result
    
    if not tank_level_entity:
        result["reason"] = "Tank level entity not configured"
        result["errors"].append("Cannot import without tank level entity")
        _LOGGER.warning("Cannot import historical data: tank level entity not configured")
        return result
    
    # Check if recorder is available
    try:
        recorder_instance = get_instance(hass)
        if not recorder_instance:
            result["reason"] = "Recorder not available"
            result["errors"].append("Home Assistant recorder is not enabled")
            _LOGGER.warning("Cannot import historical data: recorder not available")
            return result
    except Exception as err:
        result["reason"] = f"Error checking recorder: {err}"
        result["errors"].append(str(err))
        _LOGGER.error("Error checking recorder availability: %s", err)
        return result
    
    # Calculate time range
    end_time = dt_util.now()
    start_time = end_time - timedelta(days=lookback_days)
    result["date_range"] = f"{start_time.isoformat()} to {end_time.isoformat()}"
    
    _LOGGER.info(
        "Importing historical data from %s to %s",
        start_time.isoformat(),
        end_time.isoformat(),
    )
    
    try:
        # Import odometer history
        odometer_points = await _import_odometer_history(
            hass, entry, odometer_entity, start_time, end_time
        )
        result["odometer_points_imported"] = odometer_points
        _LOGGER.info("Imported %d odometer data points", odometer_points)
        
        # Import tank level history and detect refueling events
        refuel_events = await _import_tank_history_and_detect_refueling(
            hass, entry, tank_level_entity, odometer_entity, start_time, end_time, tank_capacity, fuel_type
        )
        result["refuel_events_detected"] = refuel_events
        _LOGGER.info("Detected %d refueling events", refuel_events)
        
        # Mark import as completed and store metadata
        data = await load_data(hass, entry)
        data["historical_import_completed"] = True
        data["historical_import_timestamp"] = timestamp
        data["historical_import_lookback_days"] = lookback_days
        data["last_historical_import"] = {
            "timestamp": timestamp,
            "type": import_type,
        }
        await save_data(hass, entry, data)
        
        result["imported"] = True
        result["reason"] = "Historical import completed successfully"
        
        _LOGGER.info(
            "Historical import completed: %d odometer points, %d refuel events (type: %s)",
            odometer_points,
            refuel_events,
            import_type,
        )
        
    except Exception as err:
        result["reason"] = f"Error during import: {err}"
        result["errors"].append(str(err))
        _LOGGER.error("Error importing historical data: %s", err, exc_info=True)
    
    return result


async def _fetch_long_term_statistics(
    hass: HomeAssistant,
    entity_id: str,
    start_time: datetime,
    end_time: datetime,
) -> list[dict[str, Any]]:
    """Fetch long-term statistics for an entity.
    
    This function queries Home Assistant's long-term statistics database
    which retains hourly aggregated data indefinitely (unlike short-term
    history which is typically purged after 10 days).
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to fetch statistics for
        start_time: Start of time range
        end_time: End of time range
        
    Returns:
        List of state-like dictionaries with 'timestamp' and 'value' keys
    """
    _LOGGER.debug(
        "Fetching long-term statistics for %s from %s to %s",
        entity_id,
        start_time.isoformat(),
        end_time.isoformat(),
    )
    
    try:
        # Get recorder instance to use async_add_executor_job
        recorder_instance = get_instance(hass)
        
        # Fetch statistics using recorder's executor for proper database access
        stats = await recorder_instance.async_add_executor_job(
            statistics_during_period,
            hass,
            start_time,
            end_time,
            {entity_id},
            "hour",
            None,
            {"mean", "state"},
        )
        
        if not stats or entity_id not in stats:
            _LOGGER.debug("No long-term statistics found for %s", entity_id)
            return []
        
        # Convert statistics to state-like objects
        result = []
        for stat in stats[entity_id]:
            # Try to get the most appropriate value: state (last value) or mean
            value = stat.get("state") or stat.get("mean")
            if value is not None:
                # stat["start"] contains the datetime for this hourly period
                timestamp = stat.get("start")
                if timestamp:
                    # Convert float timestamp to datetime if needed
                    if isinstance(timestamp, (int, float)):
                        timestamp = dt_util.utc_from_timestamp(timestamp)
                    result.append({
                        "timestamp": timestamp,
                        "value": value,
                    })
        
        _LOGGER.info(
            "Retrieved %d data points from long-term statistics for %s",
            len(result),
            entity_id,
        )
        return result
        
    except Exception as err:
        _LOGGER.warning(
            "Failed to fetch long-term statistics for %s: %s",
            entity_id,
            err,
        )
        return []


async def _import_odometer_history(
    hass: HomeAssistant,
    entry: ConfigEntry,
    odometer_entity: str,
    start_time: datetime,
    end_time: datetime,
) -> int:
    """Import odometer history from recorder.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        odometer_entity: Entity ID of odometer sensor
        start_time: Start of time range
        end_time: End of time range
        
    Returns:
        Number of data points imported
    """
    count = 0
    
    try:
        # Split the time range into short-term (recent) and long-term (older) periods
        now = dt_util.now()
        short_term_cutoff = now - timedelta(days=SHORT_TERM_HISTORY_DAYS - LONG_TERM_STATISTICS_OVERLAP_DAYS)
        
        all_states = []
        
        # Fetch long-term statistics for older data (if applicable)
        if start_time < short_term_cutoff:
            long_term_end = min(short_term_cutoff, end_time)
            _LOGGER.info(
                "Fetching odometer data from long-term statistics (%s to %s)",
                start_time.isoformat(),
                long_term_end.isoformat(),
            )
            
            long_term_data = await _fetch_long_term_statistics(
                hass,
                odometer_entity,
                start_time,
                long_term_end,
            )
            
            # Convert long-term statistics to state-like objects
            for data_point in long_term_data:
                all_states.append(_StateLike(data_point["value"], data_point["timestamp"]))
            
            _LOGGER.info("Retrieved %d data points from long-term statistics", len(long_term_data))
        
        # Fetch short-term history for recent data
        short_term_start = max(start_time, short_term_cutoff)
        if short_term_start < end_time:
            _LOGGER.info(
                "Retrieving odometer states from short-term history (%s to %s) in chunks...",
                short_term_start.isoformat(),
                end_time.isoformat(),
            )
            
            chunk_days = 7  # Query 7 days at a time
            current_start = short_term_start
            short_term_count = 0
            
            while current_start < end_time:
                current_end = min(current_start + timedelta(days=chunk_days), end_time)
                
                # Use recorder instance for proper database access
                recorder_instance = get_instance(hass)
                chunk_states = await recorder_instance.async_add_executor_job(
                    history.state_changes_during_period,
                    hass,
                    current_start,
                    current_end,
                    odometer_entity,
                )
                
                if chunk_states and odometer_entity in chunk_states:
                    chunk_count = len(chunk_states[odometer_entity])
                    all_states.extend(chunk_states[odometer_entity])
                    short_term_count += chunk_count
                
                current_start = current_end
            
            _LOGGER.info(
                "Retrieved %d odometer states from short-term history",
                short_term_count,
            )
        
        if not all_states:
            _LOGGER.warning("No historical states found for odometer entity: %s", odometer_entity)
            return 0
        
        _LOGGER.info(
            "Retrieved total of %d odometer data points (long-term statistics + short-term history)",
            len(all_states),
        )
        
        # Process states in chronological order
        # For trip detection, we need to capture all significant odometer changes,
        # not just one per day. Keep readings where odometer changes by at least
        # the minimum trip distance threshold.
        processed_states = []
        last_saved_value = None
        
        for state in all_states:
            try:
                # Skip if state is unknown or unavailable
                if state.state in INVALID_SENSOR_STATES:
                    continue
                
                # Parse odometer value with normalization for comma decimal separators
                odometer_value = float(_normalize_numeric_string(state.state))
                timestamp = state.last_changed
                
                # Keep this reading if:
                # 1. It's the first reading, OR
                # 2. Odometer changed by at least the minimum trip distance
                if last_saved_value is None or abs(odometer_value - last_saved_value) >= TRIP_DETECTION_MIN_DISTANCE_KM:
                    processed_states.append({
                        "value": odometer_value,
                        "timestamp": timestamp.isoformat(),
                    })
                    last_saved_value = odometer_value
                
            except (ValueError, TypeError) as err:
                _LOGGER.debug("Skipping invalid odometer state: %s (%s)", state.state, err)
                continue
        
        # Add processed data to history in batch to avoid race conditions
        # Load data once, append all observations, save once
        if processed_states:
            data = await load_data(hass, entry)
            
            # Ensure odometer_history exists
            if "odometer_history" not in data:
                data["odometer_history"] = []
            
            # Truncate existing history first to make room for new entries
            if len(data["odometer_history"]) > ODOMETER_HISTORY_TRUNCATE_TO:
                # Keep only the most recent entries to ensure we stay under the maximum
                # after adding new data (up to ~200 new entries in a typical 90-day import)
                data["odometer_history"] = data["odometer_history"][-ODOMETER_HISTORY_TRUNCATE_TO:]
            
            # Append all new observations
            for state_data in processed_states:
                data["odometer_history"].append({
                    "ts": state_data["timestamp"],
                    "value": state_data["value"]
                })
                count += 1
            
            await save_data(hass, entry, data)
        
        _LOGGER.info(
            "Imported %d odometer readings with significant changes (from %d total states)",
            count,
            len(all_states),
        )
        
    except Exception as err:
        _LOGGER.error("Error importing odometer history: %s", err, exc_info=True)
        raise
    
    return count


async def _import_tank_history_and_detect_refueling(
    hass: HomeAssistant,
    entry: ConfigEntry,
    tank_level_entity: str,
    odometer_entity: str,
    start_time: datetime,
    end_time: datetime,
    tank_capacity: float,
    fuel_type: str,
) -> int:
    """Import tank level history and detect refueling events.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        tank_level_entity: Entity ID of tank level sensor
        odometer_entity: Entity ID of odometer sensor
        start_time: Start of time range
        end_time: End of time range
        tank_capacity: Tank capacity in liters
        fuel_type: Fuel type (e5, e10, diesel)
        
    Returns:
        Number of refueling events detected
    """
    refuel_count = 0
    
    try:
        # Load existing refueling log to check for duplicates
        from .storage import get_refueling_log
        from homeassistant.util import dt as dt_util
        
        existing_log = await get_refueling_log(hass, entry)
        existing_timestamps = set()
        for event in existing_log:
            if event.get("timestamp"):
                # Parse timestamp and store as datetime for comparison
                try:
                    ts = dt_util.parse_datetime(event["timestamp"])
                    if ts:
                        # Ensure timezone-aware for comparison
                        if ts.tzinfo is None:
                            ts = dt_util.as_local(ts)
                        existing_timestamps.add(ts)
                except (ValueError, TypeError):
                    pass
        
        # Split the time range into short-term (recent) and long-term (older) periods
        now = dt_util.now()
        short_term_cutoff = now - timedelta(days=SHORT_TERM_HISTORY_DAYS - LONG_TERM_STATISTICS_OVERLAP_DAYS)
        
        all_tank_states = []
        
        # Fetch long-term statistics for older data (if applicable)
        if start_time < short_term_cutoff:
            long_term_end = min(short_term_cutoff, end_time)
            _LOGGER.info(
                "Fetching tank level data from long-term statistics (%s to %s)",
                start_time.isoformat(),
                long_term_end.isoformat(),
            )
            
            long_term_data = await _fetch_long_term_statistics(
                hass,
                tank_level_entity,
                start_time,
                long_term_end,
            )
            
            # Convert long-term statistics to state-like objects
            for data_point in long_term_data:
                all_tank_states.append(_StateLike(data_point["value"], data_point["timestamp"]))
            
            _LOGGER.info("Retrieved %d tank level data points from long-term statistics", len(long_term_data))
        
        # Fetch short-term history for recent data
        short_term_start = max(start_time, short_term_cutoff)
        if short_term_start < end_time:
            _LOGGER.info(
                "Retrieving tank level states from short-term history (%s to %s) in chunks...",
                short_term_start.isoformat(),
                end_time.isoformat(),
            )
            
            chunk_days = 7  # Query 7 days at a time
            current_start = short_term_start
            
            while current_start < end_time:
                current_end = min(current_start + timedelta(days=chunk_days), end_time)
                
                _LOGGER.debug(
                    "Querying chunk: %s to %s",
                    current_start.isoformat(),
                    current_end.isoformat(),
                )
                
                # Use recorder instance for proper database access
                recorder_instance = get_instance(hass)
                chunk_states = await recorder_instance.async_add_executor_job(
                    history.state_changes_during_period,
                    hass,
                    current_start,
                    current_end,
                    tank_level_entity,
                )
                
                if chunk_states and tank_level_entity in chunk_states:
                    all_tank_states.extend(chunk_states[tank_level_entity])
                    _LOGGER.debug(
                        "Retrieved %d states from chunk, total so far: %d",
                        len(chunk_states[tank_level_entity]),
                        len(all_tank_states),
                    )
                
                current_start = current_end
        
        if not all_tank_states:
            _LOGGER.warning("No historical states found for tank level entity: %s", tank_level_entity)
            return 0
        
        # Log how many states were retrieved
        _LOGGER.info(
            "Retrieved total of %d tank level data points (long-term statistics + short-term history) for period %s to %s",
            len(all_tank_states),
            start_time.isoformat(),
            end_time.isoformat(),
        )
        
        # Log first and last timestamps to verify order
        if all_tank_states:
            first_state = all_tank_states[0]
            last_state = all_tank_states[-1]
            _LOGGER.info(
                "State range: first=%s (state=%s), last=%s (state=%s)",
                first_state.last_changed.isoformat(),
                first_state.state,
                last_state.last_changed.isoformat(),
                last_state.state,
            )
        
        # Get odometer states for same period (also use long-term statistics + short-term history)
        _LOGGER.debug("Retrieving odometer states with long-term statistics support...")
        
        all_odometer_states = []
        
        # Fetch long-term statistics for older odometer data (if applicable)
        if start_time < short_term_cutoff:
            long_term_end = min(short_term_cutoff, end_time)
            _LOGGER.debug(
                "Fetching odometer data from long-term statistics for lookup (%s to %s)",
                start_time.isoformat(),
                long_term_end.isoformat(),
            )
            
            long_term_odo_data = await _fetch_long_term_statistics(
                hass,
                odometer_entity,
                start_time,
                long_term_end,
            )
            
            # Convert long-term statistics to state-like objects
            for data_point in long_term_odo_data:
                all_odometer_states.append(_StateLike(data_point["value"], data_point["timestamp"]))
        
        # Fetch short-term history for recent odometer data
        short_term_start = max(start_time, short_term_cutoff)
        if short_term_start < end_time:
            chunk_days = 7
            current_start = short_term_start
            
            while current_start < end_time:
                current_end = min(current_start + timedelta(days=chunk_days), end_time)
                
                # Use recorder instance for proper database access
                recorder_instance = get_instance(hass)
                chunk_states = await recorder_instance.async_add_executor_job(
                    history.state_changes_during_period,
                    hass,
                    current_start,
                    current_end,
                    odometer_entity,
                )
                
                if chunk_states and odometer_entity in chunk_states:
                    all_odometer_states.extend(chunk_states[odometer_entity])
                
                current_start = current_end
        
        # Create a lookup for odometer values by timestamp
        odometer_lookup = {}
        for state in all_odometer_states:
                try:
                    if state.state not in INVALID_SENSOR_STATES:
                        timestamp = state.last_changed
                        # Ensure timezone-aware
                        if timestamp.tzinfo is None:
                            timestamp = dt_util.as_local(timestamp)
                        odometer_lookup[timestamp] = float(_normalize_numeric_string(state.state))
                except (ValueError, TypeError):
                    continue
        
        _LOGGER.info("Built odometer lookup with %d readings", len(odometer_lookup))
        
        # Process tank level states and detect refueling
        previous_level = None
        previous_time = None
        
        # Track potential refueling events to merge close ones
        pending_refuel_events = []
        
        # Track statistics for debugging
        total_states_processed = 0
        states_skipped_invalid = 0
        states_with_positive_increase = 0
        states_below_threshold = 0
        
        # Determine if tank level is in percentage or liters.
        # Priority 1: live entity state (always has correct unit_of_measurement attribute).
        #   This handles the common case where all_tank_states are _StateLike objects
        #   from long-term statistics – those objects have empty attributes dicts and
        #   therefore cannot supply unit information themselves.
        # Priority 2: first valid state's attributes (fallback for real State objects).
        tank_level_in_percentage = False
        live_entity_state = hass.states.get(tank_level_entity)
        if live_entity_state is not None:
            unit = live_entity_state.attributes.get("unit_of_measurement", "").lower()
            if unit in ["%", "percent", "percentage"]:
                tank_level_in_percentage = True
                _LOGGER.debug(
                    "Tank level entity uses percentage unit (detected from live state): %s", unit
                )
            else:
                _LOGGER.debug(
                    "Tank level entity unit from live state: '%s' (treating as liters)", unit
                )
        else:
            # Fallback: check the first valid historical state's attributes
            for state in all_tank_states:
                if state.state not in INVALID_SENSOR_STATES:
                    # Both real State objects and _StateLike have attributes property
                    unit = state.attributes.get("unit_of_measurement", "").lower()
                    if unit in ["%", "percent", "percentage"]:
                        tank_level_in_percentage = True
                        _LOGGER.debug("Tank level entity uses percentage unit (from history): %s", unit)
                    break
        
        # Last-resort heuristic: if unit is still unknown, infer from the data values.
        # Sensors reporting percentage will have values in 0-100; sensors reporting
        # liters directly can exceed 100 for large tanks but cannot exceed typical
        # tank capacities (< 200 L).  If all valid values are <= PERCENTAGE_MAX_VALUE AND
        # the configured tank_capacity is > PERCENTAGE_MAX_VALUE, the data is almost
        # certainly in %.
        if not tank_level_in_percentage and tank_capacity > PERCENTAGE_MAX_VALUE:
            valid_values = []
            for state in all_tank_states:
                if state.state not in INVALID_SENSOR_STATES:
                    try:
                        valid_values.append(float(_normalize_numeric_string(state.state)))
                    except (ValueError, TypeError):
                        pass
                    if len(valid_values) >= UNIT_DETECTION_SAMPLE_SIZE:
                        break
            if valid_values and max(valid_values) <= PERCENTAGE_MAX_VALUE:
                tank_level_in_percentage = True
                _LOGGER.warning(
                    "Tank level unit could not be determined from entity or history; "
                    "inferred PERCENTAGE from value range (max sampled value: %.1f, tank_capacity: %.1fL). "
                    "Verify CONF_TANK_LEVEL_ENTITY unit configuration.",
                    max(valid_values),
                    tank_capacity,
                )
        
        _LOGGER.info(
            "Tank level unit detection: tank_level_in_percentage=%s (tank_capacity=%.1fL)",
            tank_level_in_percentage,
            tank_capacity,
        )
        
        # Calculate threshold in liters based on percentage
        threshold_liters = (REFUEL_DETECTION_THRESHOLD_PERCENT / 100.0) * tank_capacity
        _LOGGER.info(
            "Refueling detection configuration: threshold=%.1f%% (%.2fL), tank_capacity=%.1fL, merge_window=%d min",
            REFUEL_DETECTION_THRESHOLD_PERCENT,
            threshold_liters,
            tank_capacity,
            REFUEL_MERGE_TIME_WINDOW_MINUTES,
        )
        _LOGGER.info(
            "Existing refueling events in log: %d (will check for duplicates within %d hours)",
            len(existing_timestamps),
            DUPLICATE_DETECTION_WINDOW_HOURS,
        )
        
        for state in all_tank_states:
            total_states_processed += 1
            try:
                # Skip if state is unknown or unavailable
                if state.state in INVALID_SENSOR_STATES:
                    states_skipped_invalid += 1
                    continue
                
                current_level = float(_normalize_numeric_string(state.state))
                
                # Convert percentage to liters if needed
                if tank_level_in_percentage:
                    current_level = (current_level / 100.0) * tank_capacity
                
                current_time = state.last_changed
                
                # Detect refueling: significant increase in tank level
                if previous_level is not None:
                    level_increase = current_level - previous_level
                    
                    # Log all tank level increases (positive changes only) for debugging
                    if level_increase > 0:
                        states_with_positive_increase += 1
                        _LOGGER.info(
                            "Tank level increase detected: +%.2fL at %s (%.1f%% raw, previous=%.2fL, current=%.2fL, threshold=%.2fL)",
                            level_increase,
                            current_time.isoformat(),
                            float(state.state) if tank_level_in_percentage else (level_increase / tank_capacity * 100),
                            previous_level,
                            current_level,
                            threshold_liters,
                        )
                    
                    # Refueling detected if increase exceeds threshold
                    if level_increase > threshold_liters:
                        # Physical constraint: a single detected increase cannot exceed
                        # the full tank capacity (it would be physically impossible to add
                        # more fuel than the tank can hold).  This guards against mis-detected
                        # events caused by unit confusion or sensor calibration drift.
                        if level_increase > tank_capacity:
                            _LOGGER.warning(
                                "Skipping physically impossible refueling: +%.2fL exceeds tank capacity of %.1fL at %s "
                                "(possible unit mismatch – check whether tank_level_entity reports in %% or liters)",
                                level_increase,
                                tank_capacity,
                                current_time.isoformat(),
                            )
                            previous_level = current_level
                            previous_time = current_time
                            continue

                        # Check if this refueling is a duplicate
                        is_duplicate = False
                        
                        # Ensure current_time is timezone-aware for comparison
                        current_time_aware = current_time
                        if current_time_aware.tzinfo is None:
                            current_time_aware = dt_util.as_local(current_time_aware)
                        
                        for existing_ts in existing_timestamps:
                            time_diff_hours = abs((current_time_aware - existing_ts).total_seconds()) / SECONDS_PER_HOUR
                            if time_diff_hours < DUPLICATE_DETECTION_WINDOW_HOURS:
                                is_duplicate = True
                                _LOGGER.warning(
                                    "Skipping duplicate refueling at %s (within %.1fh of existing event at %s)",
                                    current_time.isoformat(),
                                    time_diff_hours,
                                    existing_ts.isoformat(),
                                )
                                break
                        
                        if not is_duplicate:
                            # Add to pending events for potential merging
                            pending_refuel_events.append({
                                "timestamp": current_time_aware,
                                "liters": level_increase,
                            })
                            _LOGGER.info(
                                "✓ Refueling event detected: +%.2fL at %s (exceeds threshold of %.2fL, raw_state=%s)",
                                level_increase,
                                current_time.isoformat(),
                                threshold_liters,
                                state.state,
                            )
                        else:
                            _LOGGER.info(
                                "✗ Refueling event rejected as duplicate: +%.2fL at %s",
                                level_increase,
                                current_time.isoformat(),
                            )
                    else:
                        # Log why it didn't meet threshold
                        if level_increase > 0:
                            states_below_threshold += 1
                            _LOGGER.debug(
                                "Tank increase below threshold: +%.2fL at %s (threshold: %.2fL)",
                                level_increase,
                                current_time.isoformat(),
                                threshold_liters,
                            )
                
                previous_level = current_level
                previous_time = current_time
                
            except (ValueError, TypeError) as err:
                states_skipped_invalid += 1
                try:
                    timestamp_str = state.last_changed.isoformat()
                except Exception:
                    timestamp_str = 'unknown'
                _LOGGER.warning("Skipping invalid tank level state at %s: %s (%s)", 
                              timestamp_str,
                              state.state if hasattr(state, 'state') else 'unknown', 
                              err)
                continue
        
        # Log processing statistics
        _LOGGER.info(
            "Tank level processing complete: processed=%d, skipped_invalid=%d, positive_increases=%d, below_threshold=%d, detected=%d",
            total_states_processed,
            states_skipped_invalid,
            states_with_positive_increase,
            states_below_threshold,
            len(pending_refuel_events),
        )
        
        # Merge refueling events that occur within the merge time window
        _LOGGER.info(
            "Processing %d detected refueling event(s) for merging (merge window: %d minutes)",
            len(pending_refuel_events),
            REFUEL_MERGE_TIME_WINDOW_MINUTES,
        )
        
        # Log all pending events before merging
        if pending_refuel_events:
            _LOGGER.info("Pending refueling events before merging:")
            for i, evt in enumerate(pending_refuel_events, 1):
                _LOGGER.info("  %d. %s: +%.2fL", i, evt["timestamp"].isoformat(), evt["liters"])
        
        merged_events = _merge_refueling_events(pending_refuel_events, REFUEL_MERGE_TIME_WINDOW_MINUTES)
        
        # Physical constraint: cap each merged event at tank_capacity.
        # After merging consecutive hourly readings the summed amount can still
        # exceed the physical tank size due to sensor mean-value artefacts.
        for evt in merged_events:
            if evt["liters"] > tank_capacity:
                _LOGGER.warning(
                    "Capping merged refueling amount %.2fL to tank capacity %.1fL at %s",
                    evt["liters"],
                    tank_capacity,
                    evt["timestamp"].isoformat(),
                )
                evt["liters"] = tank_capacity
        
        _LOGGER.info(
            "After merging: %d refueling event(s) to be added to storage",
            len(merged_events),
        )
        
        # Log all merged events
        if merged_events:
            _LOGGER.info("Merged refueling events to be saved:")
            for i, evt in enumerate(merged_events, 1):
                _LOGGER.info("  %d. %s: +%.2fL (merged_count=%d)", 
                           i, evt["timestamp"].isoformat(), evt["liters"], 
                           evt.get("merged_count", 1))
        
        # Create refueling log entries for merged events
        for merged_event in merged_events:
            current_time = merged_event["timestamp"]
            level_increase = merged_event["liters"]
            merged_count = merged_event.get("merged_count", 1)
            
            # Find closest odometer reading
            odometer_km = _find_closest_odometer(odometer_lookup, current_time)
            
            # Get current price from integration data (if available)
            price_per_liter = await _get_current_price(hass, entry, current_time)
            
            # Calculate confidence based on data availability
            confidence = _calculate_confidence(
                odometer_km=odometer_km,
                price_per_liter=price_per_liter,
                level_increase=level_increase,
                tank_capacity=tank_capacity,
            )
            
            # Create refueling event with quality indicators
            event_data = {
                "timestamp": current_time.isoformat(),
                "odometer_km": odometer_km,
                "station_name": "Historical Import",
                "liters_refueled": level_increase,
                "price_per_liter": price_per_liter,
                "total_cost": level_increase * price_per_liter if price_per_liter else None,
                "latitude": None,
                "longitude": None,
                "fuel_type": fuel_type,
                "data_quality": "historical_import",
                "confidence": confidence,
            }
            
            await add_refuel_event(hass, entry, event_data)
            
            # Add to prevent duplicates in same import (ensure timezone-aware)
            current_time_aware = current_time
            if current_time_aware.tzinfo is None:
                current_time_aware = dt_util.as_local(current_time_aware)
            existing_timestamps.add(current_time_aware)
            refuel_count += 1
            
            if merged_count > 1:
                _LOGGER.info(
                    "✓ Saved merged refueling event #%d: +%.1fL at %s (merged %d events, odometer: %.1f km, confidence: %.2f)",
                    refuel_count,
                    level_increase,
                    current_time.isoformat(),
                    merged_count,
                    odometer_km or 0,
                    confidence,
                )
            else:
                _LOGGER.info(
                    "✓ Saved refueling event #%d: +%.1fL at %s (odometer: %.1f km, confidence: %.2f)",
                    refuel_count,
                    level_increase,
                    current_time.isoformat(),
                    odometer_km or 0,
                    confidence,
                )
        
        # Log summary if any refuelings were detected
        if refuel_count > 0:
            _LOGGER.info(
                "Historical import completed: detected %d refueling event(s) from tank level changes",
                refuel_count,
            )
        
    except Exception as err:
        _LOGGER.error("Error importing tank history: %s", err, exc_info=True)
        raise
    
    return refuel_count


def _merge_refueling_events(
    events: list[dict[str, Any]],
    merge_window_minutes: float,
) -> list[dict[str, Any]]:
    """Merge refueling events that occur within a time window.
    
    When multiple tank level increases occur close together (e.g., sensor updates
    during a single refueling session), merge them into a single event.
    
    Args:
        events: List of refueling events with 'timestamp' and 'liters' keys
        merge_window_minutes: Time window in minutes to consider events as part of same refueling
        
    Returns:
        List of merged refueling events
    """
    if not events:
        return []
    
    # Sort events by timestamp
    sorted_events = sorted(events, key=lambda x: x["timestamp"])
    
    merged = []
    current_group = None
    
    for event in sorted_events:
        if current_group is None:
            # Start a new group
            current_group = {
                "timestamp": event["timestamp"],
                "liters": event["liters"],
                "merged_count": 1,
            }
        else:
            # Check if this event should be merged with current group
            time_diff_minutes = (event["timestamp"] - current_group["timestamp"]).total_seconds() / 60
            
            if time_diff_minutes <= merge_window_minutes:
                # Log before merging to show previous state
                previous_total = current_group["liters"]
                # Merge into current group
                current_group["liters"] += event["liters"]
                current_group["merged_count"] += 1
                _LOGGER.info(
                    "Merging refueling events: %s (+%.2fL) merged with %s (previous total: +%.2fL), time diff: %.1f min",
                    event["timestamp"].isoformat(),
                    event["liters"],
                    current_group["timestamp"].isoformat(),
                    previous_total,
                    time_diff_minutes,
                )
            else:
                # Time gap too large, save current group and start new one
                merged.append(current_group)
                current_group = {
                    "timestamp": event["timestamp"],
                    "liters": event["liters"],
                    "merged_count": 1,
                }
    
    # Don't forget the last group
    if current_group is not None:
        merged.append(current_group)
    
    return merged


def _find_closest_odometer(
    odometer_lookup: dict[datetime, float],
    target_time: datetime,
) -> float | None:
    """Find the closest odometer reading to a given time.
    
    Args:
        odometer_lookup: Dictionary mapping timestamps to odometer values
        target_time: Target timestamp
        
    Returns:
        Closest odometer value or None if not found
    """
    if not odometer_lookup:
        return None
    
    # Find the closest timestamp
    closest_time = min(
        odometer_lookup.keys(),
        key=lambda t: abs((t - target_time).total_seconds()),
    )
    
    # Return value if within configured time window
    max_time_diff_seconds = ODOMETER_LOOKUP_MAX_TIME_DIFF_HOURS * SECONDS_PER_HOUR
    if abs((closest_time - target_time).total_seconds()) < max_time_diff_seconds:
        return odometer_lookup[closest_time]
    
    return None


async def _get_current_price(
    hass: HomeAssistant,
    entry: ConfigEntry,
    timestamp: datetime,
) -> float | None:
    """Get fuel price closest to a given timestamp from price history.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        timestamp: Target timestamp
        
    Returns:
        Price per liter or None if not found
    """
    try:
        from .storage import get_price_history
        from homeassistant.util import dt as dt_util
        
        price_history = await get_price_history(hass, entry)
        
        if not price_history:
            return None
        
        # Find closest price by timestamp
        closest_price = None
        min_time_diff = float('inf')
        
        max_price_age_seconds = PRICE_LOOKUP_WINDOW_DAYS * 24 * SECONDS_PER_HOUR
        
        for price_entry in price_history:
            try:
                price_time = dt_util.parse_datetime(price_entry.get("ts", ""))
                if not price_time:
                    continue
                
                # Ensure timezone-aware for comparison
                price_time_aware = price_time
                if price_time_aware.tzinfo is None:
                    price_time_aware = dt_util.as_local(price_time_aware)
                timestamp_aware = timestamp
                if timestamp_aware.tzinfo is None:
                    timestamp_aware = dt_util.as_local(timestamp_aware)
                
                time_diff = abs((price_time_aware - timestamp_aware).total_seconds())
                
                # Use price if within configured time window
                if time_diff < min_time_diff and time_diff < max_price_age_seconds:
                    min_time_diff = time_diff
                    closest_price = price_entry.get("price")
            except Exception:
                continue
        
        return closest_price
        
    except Exception as err:
        _LOGGER.debug("Error getting historical price: %s", err)
        return None


def _calculate_confidence(
    odometer_km: float | None,
    price_per_liter: float | None,
    level_increase: float,
    tank_capacity: float,
) -> float:
    """Calculate confidence score for a detected refueling event.
    
    Confidence is based on:
    - Availability of odometer data (0.4 weight)
    - Availability of price data (0.3 weight)
    - Reasonableness of refueling amount (0.3 weight)
    
    Args:
        odometer_km: Odometer reading at refueling (None if not available)
        price_per_liter: Price per liter (None if not available)
        level_increase: Amount of fuel added in liters
        tank_capacity: Tank capacity in liters
        
    Returns:
        Confidence score from 0.0 to 1.0 (higher is better)
    """
    confidence = 0.0
    
    # Odometer data available (40% weight)
    if odometer_km is not None and odometer_km > 0:
        confidence += 0.4
    
    # Price data available (30% weight)
    if price_per_liter is not None and price_per_liter > 0:
        confidence += 0.3
    
    # Refueling amount is reasonable (30% weight)
    # Consider it reasonable if between 10% and 100% of tank capacity
    if tank_capacity > 0:
        refuel_percentage = (level_increase / tank_capacity) * PERCENTAGE_MULTIPLIER
        if 10 <= refuel_percentage <= 100:
            confidence += 0.3
        elif refuel_percentage > 100:
            # Over 100% suggests measurement error or wrong tank capacity
            # Still give partial credit as refueling was detected
            confidence += 0.15
    else:
        # No tank capacity data, give partial credit
        confidence += 0.15
    
    return round(confidence, 2)


# Trip detection constants
TRIP_DETECTION_MIN_DISTANCE_KM = 0.5  # Minimum distance to consider as a trip
TRIP_MERGE_TIME_WINDOW_MINUTES = 5  # Time window to merge short stops into single trip
TRIP_MAX_SPEED_KMH = 300  # Maximum reasonable speed (to filter outliers)
TRIP_MIN_DURATION_MINUTES = 1  # Minimum trip duration
MIN_LOCATION_DIFFERENCE_DEGREES = 0.001  # Minimum coordinate difference (~100m) to consider locations distinct
MAX_TANK_LEVEL_LOOKUP_TIME_HOURS = 6.0  # Maximum time difference (hours) for a valid tank level reading near a trip
MAX_REASONABLE_FUEL_CONSUMPTION_L_PER_100KM = 50.0  # Upper plausibility bound for fuel consumption
MIN_REASONABLE_FUEL_CONSUMPTION_L_PER_100KM = 1.0   # Lower plausibility bound for fuel consumption


async def import_historical_trip_data(
    hass: HomeAssistant,
    entry: ConfigEntry,
    lookback_days: int = 90,
    force_reimport: bool = False,
    import_type: str = "automatic",
) -> dict[str, Any]:
    """Import historical trip data from Home Assistant's recorder.
    
    This function queries the recorder for historical states of the configured
    vehicle entities (odometer, tank level, GPS location) and processes them to:
    1. Detect historical trips based on odometer changes
    2. Calculate trip metrics (distance, duration, fuel consumption)
    3. Build trip history
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        lookback_days: Number of days to look back (default: 90)
        force_reimport: If True, reimport even if data already exists
        import_type: Type of import - "automatic" or "manual" (default: "automatic")
        
    Returns:
        Dictionary with import statistics:
        {
            "imported": bool,
            "reason": str,
            "trips_detected": int,
            "date_range": str,
            "errors": list[str],
            "timestamp": str,
            "import_type": str,
        }
    """
    from ..const import (
        CONF_ODOMETER_ENTITY,
        CONF_TANK_LEVEL_ENTITY,
        CONF_POSITION_ENTITY,
        CONF_TANK_CAPACITY,
        DEFAULT_TANK_CAPACITY,
        DOMAIN,
    )
    
    result = {
        "imported": False,
        "reason": "Not started",
        "trips_detected": 0,
        "date_range": "",
        "errors": [],
        "timestamp": dt_util.now().isoformat(),
        "import_type": import_type,
    }
    
    data = None  # Track whether data was loaded
    
    try:
        # Load storage data first to check trip tracking config
        data = await load_data(hass, entry)
        
        # Check if trip tracking is enabled from storage
        trip_config = data.get("trip_tracking_config", {})
        trip_tracking_enabled = trip_config.get("enabled", False)
        if not trip_tracking_enabled:
            result["reason"] = "Trip tracking is not enabled for this vehicle"
            _LOGGER.warning(
                "Historical trip import skipped: Trip tracking not enabled for %s",
                entry.title,
            )
            return result
        
        # Check if we should skip import (unless forced)
        if not force_reimport:
            last_import = data.get("last_historical_import")
            if last_import and last_import.get("imported"):
                result["reason"] = "Historical trip import already completed. Use force_reimport=True to re-import."
                _LOGGER.info(
                    "Skipping historical trip import: already imported on %s (type: %s)",
                    last_import.get("timestamp"),
                    last_import.get("type"),
                )
                return result
        
        # Get entity IDs from config
        odometer_entity = entry.data.get(CONF_ODOMETER_ENTITY)
        tank_level_entity = entry.data.get(CONF_TANK_LEVEL_ENTITY)
        location_entity = entry.data.get(CONF_POSITION_ENTITY)
        options = entry.options
        tank_capacity = (
            options.get(CONF_TANK_CAPACITY)
            or entry.data.get(CONF_TANK_CAPACITY, DEFAULT_TANK_CAPACITY)
        )
        
        if not odometer_entity:
            result["reason"] = "No odometer entity configured"
            result["errors"].append("Odometer entity is required for trip detection")
            return result
        
        # Calculate time range
        end_time = dt_util.now()
        start_time = end_time - timedelta(days=lookback_days)
        result["date_range"] = f"{start_time.date()} to {end_time.date()}"
        
        _LOGGER.info(
            "Starting historical trip import for %s (lookback: %d days, type: %s)",
            entry.title,
            lookback_days,
            import_type,
        )
        
        # Import trip data
        trips_detected = await _import_trip_history(
            hass,
            entry,
            odometer_entity,
            tank_level_entity,
            location_entity,
            start_time,
            end_time,
            tank_capacity,
        )
        
        result["trips_detected"] = trips_detected
        
        # IMPORTANT: Reload data after _import_trip_history since it saved trips
        # Using the old 'data' variable would overwrite the trips that were just saved
        data = await load_data(hass, entry)
        
        # Get odometer history count for debugging
        odometer_history_count = len(data.get("odometer_history", []))
        
        # Store import metadata
        # Note: Both timestamp and completion_timestamp are set to the same value
        # for consistency. In the future, timestamp could track start time if needed.
        completion_timestamp = dt_util.now().isoformat()
        data["last_historical_import"] = {
            "imported": True,
            "timestamp": completion_timestamp,  # Import completion time (for backward compatibility)
            "completion_timestamp": completion_timestamp,  # Import completion time (explicit field)
            "type": import_type,
            "trips_detected": trips_detected,
            "odometer_points_available": odometer_history_count,
            "lookback_days": lookback_days,
            "date_range": result["date_range"],
        }
        
        await save_data(hass, entry, data)
        
        result["imported"] = True
        result["reason"] = "Historical trip import completed successfully"
        
        _LOGGER.info(
            "Historical trip import completed: %d trips detected (type: %s)",
            trips_detected,
            import_type,
        )
        
    except Exception as err:
        result["reason"] = f"Error during import: {err}"
        result["errors"].append(str(err))
        _LOGGER.error("Error importing historical trip data: %s", err, exc_info=True)
        
        # Store error metadata - load data if not already loaded
        try:
            if data is None:
                data = await load_data(hass, entry)
            
            data["last_historical_import"] = {
                "imported": False,
                "timestamp": dt_util.now().isoformat(),
                "type": "error",
                "error": str(err),
                "errors": result["errors"],
            }
            await save_data(hass, entry, data)
        except Exception as save_err:
            _LOGGER.error("Error saving historical import error metadata: %s", save_err)
    
    return result


async def _import_trip_history(
    hass: HomeAssistant,
    entry: ConfigEntry,
    odometer_entity: str,
    tank_level_entity: str | None,
    location_entity: str | None,
    start_time: datetime,
    end_time: datetime,
    tank_capacity: float = 50.0,
) -> int:
    """Import trip history from recorder.
    
    Detects trips based on odometer changes and calculates trip metrics.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        odometer_entity: Entity ID of odometer sensor
        tank_level_entity: Entity ID of tank level sensor (optional)
        location_entity: Entity ID of location sensor (optional)
        start_time: Start of time range
        end_time: End of time range
        tank_capacity: Tank capacity in liters (used for % → L conversion)
        
    Returns:
        Number of trips detected
    """
    from homeassistant.util import dt as dt_util
    
    trip_count = 0
    
    try:
        # Import odometer history first
        odometer_points = await _import_odometer_history(
            hass,
            entry,
            odometer_entity,
            start_time,
            end_time,
        )
        
        if odometer_points == 0:
            _LOGGER.warning("No odometer data found for trip detection")
            return 0
        
        # Get tank level history for fuel consumption calculation
        tank_level_states = []
        tank_level_in_percentage = False
        if tank_level_entity:
            tank_level_states = await _fetch_entity_history(
                hass,
                tank_level_entity,
                start_time,
                end_time,
            )
            # Detect whether tank level is reported as percentage or liters
            # (same 3-tier logic as refueling detection)
            live_entity_state = hass.states.get(tank_level_entity)
            if live_entity_state is not None:
                unit = live_entity_state.attributes.get("unit_of_measurement", "").lower()
                if unit in ["%", "percent", "percentage"]:
                    tank_level_in_percentage = True
            if not tank_level_in_percentage:
                for state in tank_level_states:
                    if state.state not in INVALID_SENSOR_STATES:
                        unit = getattr(state, "attributes", {}).get("unit_of_measurement", "").lower()
                        if unit in ["%", "percent", "percentage"]:
                            tank_level_in_percentage = True
                        break
            if not tank_level_in_percentage and tank_capacity > PERCENTAGE_MAX_VALUE:
                valid_vals = []
                for state in tank_level_states:
                    if state.state not in INVALID_SENSOR_STATES:
                        try:
                            valid_vals.append(float(_normalize_numeric_string(state.state)))
                        except (ValueError, TypeError):
                            pass
                        if len(valid_vals) >= UNIT_DETECTION_SAMPLE_SIZE:
                            break
                if valid_vals and max(valid_vals) <= PERCENTAGE_MAX_VALUE:
                    tank_level_in_percentage = True
            _LOGGER.debug(
                "Trip fuel consumption: tank_level_in_percentage=%s (tank_capacity=%.1f L)",
                tank_level_in_percentage,
                tank_capacity,
            )
        
        # Get location history for GPS coordinates
        # Note: Position entities store GPS coords in attributes, not state values.
        # Long-term statistics only store numeric state values, not attributes.
        # Therefore, we must disable statistics and use only short-term history.
        location_states = []
        if location_entity:
            location_states = await _fetch_entity_history(
                hass,
                location_entity,
                start_time,
                end_time,
                use_statistics=False,  # Position data is in attributes, not available in statistics
            )
            
            # Warn if lookback exceeds short-term history retention
            now = dt_util.now()
            short_term_cutoff = now - timedelta(days=SHORT_TERM_HISTORY_DAYS)
            if start_time < short_term_cutoff:
                lookback_days = int((end_time - start_time).total_seconds() / (24 * SECONDS_PER_HOUR))
                _LOGGER.warning(
                    "GPS location history requested for %d days, but Home Assistant only retains "
                    "short-term history for %d days. Trips detected from older data will not have "
                    "GPS coordinates. Consider reducing lookback period or enabling longer history retention.",
                    lookback_days,
                    SHORT_TERM_HISTORY_DAYS,
                )
        
        # Load storage data
        data = await load_data(hass, entry)
        existing_trips = data.get("trips", [])
        
        # Get existing trip timestamps to avoid duplicates
        existing_timestamps = set()
        for trip in existing_trips:
            if trip.get("timestamp_start"):
                try:
                    ts = dt_util.parse_datetime(trip["timestamp_start"])
                    if ts:
                        # Ensure timezone-aware for comparison
                        if ts.tzinfo is None:
                            ts = dt_util.as_local(ts)
                        existing_timestamps.add(ts)
                except Exception:
                    pass
        
        # Detect trips from odometer changes
        odometer_history = data.get("odometer_history", [])
        if len(odometer_history) < 2:
            _LOGGER.warning("Insufficient odometer data for trip detection (need at least 2 points)")
            return 0
        
        # Sort odometer history by timestamp
        sorted_history = sorted(odometer_history, key=lambda x: x.get("ts", ""))
        
        # Detect trips by analyzing odometer changes
        _LOGGER.info("Analyzing %d odometer points for trip detection", len(sorted_history))
        _LOGGER.debug(
            "Trip detection thresholds: min_distance=%.1f km, min_duration=%.1f min, max_speed=%.1f km/h",
            TRIP_DETECTION_MIN_DISTANCE_KM,
            TRIP_MIN_DURATION_MINUTES,
            TRIP_MAX_SPEED_KMH,
        )
        
        pending_trips = []
        previous_point = None
        trips_filtered_by_distance = 0
        trips_filtered_by_duration = 0
        trips_filtered_by_speed = 0
        trips_filtered_by_duplicate = 0
        
        for current_point in sorted_history:
            if previous_point is None:
                previous_point = current_point
                continue
            
            try:
                # Calculate distance traveled
                prev_odometer = previous_point.get("value")
                curr_odometer = current_point.get("value")
                
                if prev_odometer is None or curr_odometer is None:
                    previous_point = current_point
                    continue
                
                distance_km = curr_odometer - prev_odometer
                
                # Parse timestamps
                prev_time = dt_util.parse_datetime(previous_point.get("ts"))
                curr_time = dt_util.parse_datetime(current_point.get("ts"))
                
                if not prev_time or not curr_time:
                    previous_point = current_point
                    continue
                
                # Ensure timezone-aware for comparisons
                prev_time_aware = prev_time
                if prev_time_aware.tzinfo is None:
                    prev_time_aware = dt_util.as_local(prev_time_aware)
                curr_time_aware = curr_time
                if curr_time_aware.tzinfo is None:
                    curr_time_aware = dt_util.as_local(curr_time_aware)
                
                # Calculate duration
                duration_seconds = (curr_time_aware - prev_time_aware).total_seconds()
                duration_minutes = duration_seconds / 60
                
                # Check if this is a valid trip
                if distance_km >= TRIP_DETECTION_MIN_DISTANCE_KM and duration_minutes >= TRIP_MIN_DURATION_MINUTES:
                    # Calculate average speed (km/h)
                    avg_speed = (distance_km / duration_seconds) * 3600 if duration_seconds > 0 else 0
                    
                    # Filter out unrealistic speeds (likely data errors)
                    if avg_speed <= TRIP_MAX_SPEED_KMH:
                        # Check for duplicates
                        is_duplicate = False
                        for existing_ts in existing_timestamps:
                            time_diff_minutes = abs((prev_time_aware - existing_ts).total_seconds()) / 60
                            if time_diff_minutes < TRIP_MERGE_TIME_WINDOW_MINUTES:
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            # Get tank levels for fuel consumption
                            # Use time-bounded lookup to prevent picking readings from far away
                            fuel_level_start = _find_closest_tank_level(
                                tank_level_states, prev_time_aware,
                                max_time_diff_hours=MAX_TANK_LEVEL_LOOKUP_TIME_HOURS,
                            )
                            fuel_level_end = _find_closest_tank_level(
                                tank_level_states, curr_time_aware,
                                max_time_diff_hours=MAX_TANK_LEVEL_LOOKUP_TIME_HOURS,
                            )
                            
                            # Calculate fuel consumed
                            fuel_consumed = None
                            if fuel_level_start is not None and fuel_level_end is not None and fuel_level_start > fuel_level_end:
                                raw_diff = fuel_level_start - fuel_level_end
                                # Convert percentage to liters if the entity reports in %
                                if tank_level_in_percentage:
                                    fuel_consumed = (raw_diff / 100.0) * tank_capacity
                                else:
                                    fuel_consumed = raw_diff
                                # Sanity-check: discard implausible consumption rates
                                if fuel_consumed is not None and distance_km > 0:
                                    consumption_per_100km = (fuel_consumed / distance_km) * 100
                                    if (consumption_per_100km > MAX_REASONABLE_FUEL_CONSUMPTION_L_PER_100KM
                                            or consumption_per_100km < MIN_REASONABLE_FUEL_CONSUMPTION_L_PER_100KM):
                                        _LOGGER.warning(
                                            "Discarding implausible fuel consumption for trip (%.1f km): "
                                            "%.2f L (%.1f L/100km). "
                                            "Possible cause: tank level readings too far from trip time or unit mismatch.",
                                            distance_km,
                                            fuel_consumed,
                                            consumption_per_100km,
                                        )
                                        fuel_consumed = None
                            
                            # Get GPS coordinates
                            # For start: prefer location just before the trip started
                            # For end: prefer location just after the trip ended
                            start_lat, start_lon = _find_closest_location(location_states, prev_time_aware, prefer_after=False)
                            end_lat, end_lon = _find_closest_location(location_states, curr_time_aware, prefer_after=True)
                            
                            # Check if locations are distinct
                            has_distinct_locations = False
                            if (start_lat is not None and end_lat is not None and
                                start_lon is not None and end_lon is not None):
                                # Locations are considered different if they differ by at least MIN_LOCATION_DIFFERENCE_DEGREES (~100m)
                                has_distinct_locations = (
                                    abs(start_lat - end_lat) > MIN_LOCATION_DIFFERENCE_DEGREES or 
                                    abs(start_lon - end_lon) > MIN_LOCATION_DIFFERENCE_DEGREES
                                )
                            
                            # Determine original position quality (before any backfill)
                            has_start = start_lat is not None and start_lon is not None
                            has_end = end_lat is not None and end_lon is not None
                            if has_start and has_end:
                                position_quality = "full"
                            elif has_start or has_end:
                                position_quality = "partial"
                            else:
                                position_quality = "none"
                            
                            # Create trip data
                            trip_data = {
                                "timestamp_start": prev_time_aware.isoformat(),
                                "timestamp_end": curr_time_aware.isoformat(),
                                "distance_km": round(distance_km, 2),
                                "odometer_start": round(prev_odometer, 1),
                                "odometer_end": round(curr_odometer, 1),
                                "duration_minutes": round(duration_minutes, 1),
                                "fuel_consumed": round(fuel_consumed, 2) if fuel_consumed else None,
                                "start_latitude": start_lat,
                                "start_longitude": start_lon,
                                "end_latitude": end_lat,
                                "end_longitude": end_lon,
                                "position_quality": position_quality,
                                "category": "private",  # Default category
                                "data_quality": "historical_import",
                                "confidence": _calculate_trip_confidence(
                                    fuel_consumed=fuel_consumed,
                                    start_lat=start_lat,
                                    end_lat=end_lat,
                                    has_start_and_end_info=has_distinct_locations,
                                ),
                            }
                            
                            pending_trips.append(trip_data)
                            existing_timestamps.add(prev_time_aware)
                            
                            # Log warning if start and end locations are the same
                            if start_lat == end_lat and start_lon == end_lon and start_lat is not None:
                                _LOGGER.warning(
                                    "Trip detected with identical start and end GPS coordinates (%.4f, %.4f). "
                                    "This may indicate infrequent location updates. Consider using a location "
                                    "entity that updates more frequently during trips.",
                                    start_lat,
                                    start_lon,
                                )
                            
                            _LOGGER.debug(
                                "Trip detected: %.1f km from %s to %s (%.1f min, avg speed: %.1f km/h, "
                                "distinct_locations: %s)",
                                distance_km,
                                prev_time.isoformat(),
                                curr_time.isoformat(),
                                duration_minutes,
                                avg_speed,
                                has_distinct_locations,
                            )
                        else:
                            trips_filtered_by_duplicate += 1
                            _LOGGER.debug(
                                "Filtered trip as duplicate: %.1f km from %s (within %d min of existing trip)",
                                distance_km,
                                prev_time.isoformat(),
                                TRIP_MERGE_TIME_WINDOW_MINUTES,
                            )
                    else:
                        trips_filtered_by_speed += 1
                        _LOGGER.debug(
                            "Filtered trip due to unrealistic speed: %.1f km/h (%.1f km in %.1f min)",
                            avg_speed,
                            distance_km,
                            duration_minutes,
                        )
                else:
                    # Log why trip was filtered
                    if distance_km < TRIP_DETECTION_MIN_DISTANCE_KM:
                        trips_filtered_by_distance += 1
                    elif duration_minutes < TRIP_MIN_DURATION_MINUTES:
                        trips_filtered_by_duration += 1
            
            except Exception as err:
                _LOGGER.warning("Error processing odometer point: %s", err)
            
            previous_point = current_point
        
        # Save detected trips in batch to avoid race conditions
        # Load data once, add all trips with proper ID assignment and statistics, save once
        
        # Position backfill: for trips with missing start or end coordinates,
        # use the end/start coordinates of the neighboring trip in chronological order.
        if pending_trips:
            _backfill_trip_positions(pending_trips)
        
        _LOGGER.info(
            "Trip detection summary: %d trips detected, %d filtered (distance: %d, duration: %d, speed: %d, duplicate: %d)",
            len(pending_trips),
            trips_filtered_by_distance + trips_filtered_by_duration + trips_filtered_by_speed + trips_filtered_by_duplicate,
            trips_filtered_by_distance,
            trips_filtered_by_duration,
            trips_filtered_by_speed,
            trips_filtered_by_duplicate,
        )
        
        if pending_trips:
            data = await load_data(hass, entry)
            
            # Initialize trips list if not present
            if "trips" not in data:
                data["trips"] = []
            
            # Initialize trip_statistics if not present
            if "trip_statistics" not in data:
                data["trip_statistics"] = {
                    "total_trips": 0,
                    "total_distance_km": 0.0,
                    "total_fuel_consumed": 0.0,
                    "total_fuel_cost": 0.0,
                    "total_additional_costs": 0.0,
                    "business_trips": 0,
                    "private_trips": 0,
                    "commute_trips": 0,
                }
            
            # Get starting trip ID
            next_id = data.get("next_trip_id", 1)
            now = dt_util.now().isoformat()
            
            # Process all trips in batch
            for trip_data in pending_trips:
                try:
                    # Assign trip ID
                    trip_data["trip_id"] = next_id
                    next_id += 1
                    
                    # Add timestamps
                    trip_data.setdefault("created_at", now)
                    trip_data.setdefault("updated_at", now)
                    
                    # Add trip to storage
                    data["trips"].append(trip_data)
                    
                    # Update statistics
                    stats = data["trip_statistics"]
                    stats["total_trips"] = (stats.get("total_trips") or 0) + 1
                    stats["total_distance_km"] = (stats.get("total_distance_km") or 0.0) + (trip_data.get("distance_km") or 0.0)
                    stats["total_fuel_consumed"] = (stats.get("total_fuel_consumed") or 0.0) + (trip_data.get("fuel_consumed") or 0.0)
                    stats["total_fuel_cost"] = (stats.get("total_fuel_cost") or 0.0) + (trip_data.get("fuel_cost") or 0.0)
                    stats["total_additional_costs"] = (stats.get("total_additional_costs") or 0.0) + (trip_data.get("additional_costs") or 0.0)
                    
                    # Update category counters
                    category = trip_data.get("category", "private")
                    category_key = f"{category}_trips"
                    stats[category_key] = (stats.get(category_key) or 0) + 1
                    
                    trip_count += 1
                    _LOGGER.debug(
                        "Prepared trip for save: %s to %s (%.1f km)",
                        trip_data["timestamp_start"],
                        trip_data["timestamp_end"],
                        trip_data["distance_km"],
                    )
                except Exception as err:
                    _LOGGER.error("Error preparing trip for save: %s", err)
            
            # Update next_trip_id
            data["next_trip_id"] = next_id
            
            # Save all trips at once
            await save_data(hass, entry, data)
        
        if trip_count > 0:
            _LOGGER.info(
                "Historical trip import completed: detected %d trips from odometer changes",
                trip_count,
            )
        
    except Exception as err:
        _LOGGER.error("Error importing trip history: %s", err, exc_info=True)
        raise
    
    return trip_count


def _backfill_trip_positions(trips: list[dict[str, Any]]) -> None:
    """Backfill missing GPS coordinates in trips from neighboring trips.

    Trips are processed in chronological order (ascending timestamp_start).
    - Missing start position → filled from the end position of the previous trip.
    - Missing end position   → filled from the start position of the next trip.

    The ``position_quality`` field already reflects the *original* data quality
    ("full", "partial", "none") set during detection, so it is left unchanged.
    A separate ``position_backfilled`` flag is added to trips that received at
    least one coordinate from a neighbor.

    Args:
        trips: List of trip dictionaries (modified in place).
    """
    if not trips:
        return

    # Ensure chronological order
    trips.sort(key=lambda t: t.get("timestamp_start", ""))

    backfilled = 0
    for i, trip in enumerate(trips):
        start_missing = trip.get("start_latitude") is None or trip.get("start_longitude") is None
        end_missing = trip.get("end_latitude") is None or trip.get("end_longitude") is None

        if start_missing and i > 0:
            prev = trips[i - 1]
            if prev.get("end_latitude") is not None and prev.get("end_longitude") is not None:
                trip["start_latitude"] = prev["end_latitude"]
                trip["start_longitude"] = prev["end_longitude"]
                trip.setdefault("position_backfilled", True)
                backfilled += 1
                _LOGGER.debug(
                    "Backfilled start position for trip %s from previous trip end (%.4f, %.4f)",
                    trip.get("timestamp_start"),
                    trip["start_latitude"],
                    trip["start_longitude"],
                )

        if end_missing and i < len(trips) - 1:
            nxt = trips[i + 1]
            if nxt.get("start_latitude") is not None and nxt.get("start_longitude") is not None:
                trip["end_latitude"] = nxt["start_latitude"]
                trip["end_longitude"] = nxt["start_longitude"]
                trip.setdefault("position_backfilled", True)
                backfilled += 1
                _LOGGER.debug(
                    "Backfilled end position for trip %s from next trip start (%.4f, %.4f)",
                    trip.get("timestamp_start"),
                    trip["end_latitude"],
                    trip["end_longitude"],
                )

    if backfilled:
        _LOGGER.info(
            "Position backfill: filled %d missing coordinate(s) across %d trip(s)",
            backfilled,
            len(trips),
        )


async def _fetch_entity_history(
    hass: HomeAssistant,
    entity_id: str,
    start_time: datetime,
    end_time: datetime,
    use_statistics: bool = True,
) -> list[Any]:
    """Fetch entity history from recorder.
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to fetch history for
        start_time: Start of time range
        end_time: End of time range
        use_statistics: Whether to use long-term statistics for older data.
                       Set to False for entities that store data in attributes
                       (e.g., position entities with lat/lon in attributes).
        
    Returns:
        List of state objects
    """
    try:
        # Split time range for short-term and long-term data
        now = dt_util.now()
        short_term_cutoff = now - timedelta(days=SHORT_TERM_HISTORY_DAYS - LONG_TERM_STATISTICS_OVERLAP_DAYS)
        
        all_states = []
        
        # Fetch long-term statistics for older data (if enabled and entity supports it)
        if use_statistics and start_time < short_term_cutoff:
            long_term_end = min(short_term_cutoff, end_time)
            long_term_data = await _fetch_long_term_statistics(
                hass,
                entity_id,
                start_time,
                long_term_end,
            )
            
            for data_point in long_term_data:
                all_states.append(_StateLike(data_point["value"], data_point["timestamp"]))
        
        # Fetch short-term history for recent data (or all data if statistics disabled)
        if end_time > short_term_cutoff or not use_statistics:
            # For entities that don't use statistics, fetch full history range
            short_term_start = start_time if not use_statistics else max(start_time, short_term_cutoff)
            
            recorder_instance = get_instance(hass)
            states = await recorder_instance.async_add_executor_job(
                history.state_changes_during_period,
                hass,
                short_term_start,
                end_time,
                entity_id,
            )
            
            if entity_id in states:
                all_states.extend(states[entity_id])
        
        _LOGGER.debug("Retrieved %d states for %s (use_statistics: %s)", len(all_states), entity_id, use_statistics)
        return all_states
        
    except Exception as err:
        _LOGGER.warning("Failed to fetch history for %s: %s", entity_id, err)
        return []


def _find_closest_tank_level(
    tank_level_states: list[Any],
    target_time: datetime,
    max_time_diff_hours: float = float('inf'),
) -> float | None:
    """Find the closest tank level reading to a target time.
    
    Args:
        tank_level_states: List of tank level state objects
        target_time: Target timestamp
        max_time_diff_hours: Maximum allowed time difference in hours. Readings
            further away than this are ignored. Defaults to no limit.
        
    Returns:
        Tank level value or None if not found
    """
    if not tank_level_states:
        return None
    
    max_time_diff_seconds = max_time_diff_hours * SECONDS_PER_HOUR
    closest_state = None
    min_diff_seconds = float('inf')
    
    for state in tank_level_states:
        if state.state in INVALID_SENSOR_STATES:
            continue
        
        try:
            state_time = state.last_changed
            # Ensure timezone-aware for comparison
            state_time_aware = state_time
            if state_time_aware.tzinfo is None:
                state_time_aware = dt_util.as_local(state_time_aware)
            target_time_aware = target_time
            if target_time_aware.tzinfo is None:
                target_time_aware = dt_util.as_local(target_time_aware)
            
            time_diff_seconds = abs((target_time_aware - state_time_aware).total_seconds())
            
            if time_diff_seconds <= max_time_diff_seconds and time_diff_seconds < min_diff_seconds:
                min_diff_seconds = time_diff_seconds
                closest_state = state
        except Exception:
            continue
    
    if closest_state:
        try:
            return float(closest_state.state)
        except (ValueError, TypeError):
            return None
    
    return None


def _is_valid_coordinate(value: Any) -> bool:
    """Check if a coordinate value is valid (not invalid state string).
    
    Args:
        value: The coordinate value to check
        
    Returns:
        True if value is a valid number, False otherwise
    """
    if value is None:
        return False
    
    # Check if value is an invalid state string
    if isinstance(value, str):
        if value.lower() in ["unknown", "unavailable", "none", "null", ""]:
            return False
    
    # Try to convert to float
    try:
        float_val = float(value)
        # Check if it's a reasonable coordinate value
        # Use -180 to 180 range to cover both latitude (-90 to 90) and longitude (-180 to 180)
        return -180 <= float_val <= 180
    except (ValueError, TypeError):
        return False


def _find_closest_location(
    location_states: list[Any],
    target_time: datetime,
    prefer_after: bool = False,
) -> tuple[float | None, float | None]:
    """Find the closest GPS location to a target time.
    
    Args:
        location_states: List of location state objects
        target_time: Target timestamp
        prefer_after: If True, prefer states after target_time when choosing closest
        
    Returns:
        Tuple of (latitude, longitude) or (None, None) if not found
    """
    if not location_states:
        return None, None
    
    closest_state = None
    min_time_diff_seconds = float('inf')
    
    for state in location_states:
        if state.state in INVALID_SENSOR_STATES:
            continue
        
        try:
            state_time = state.last_changed
            # Ensure timezone-aware for comparison
            state_time_aware = state_time
            if state_time_aware.tzinfo is None:
                state_time_aware = dt_util.as_local(state_time_aware)
            target_time_aware = target_time
            if target_time_aware.tzinfo is None:
                target_time_aware = dt_util.as_local(target_time_aware)
            
            time_diff_seconds = (target_time_aware - state_time_aware).total_seconds()
            abs_time_diff_seconds = abs(time_diff_seconds)
            
            # Determine if we should update the closest state
            should_update = False
            
            if abs_time_diff_seconds < min_time_diff_seconds:
                # This state is closer - update unless we have a direction preference
                if prefer_after:
                    # Only update if this state is after target OR if no better option exists yet
                    # time_diff_seconds < 0 means state_time > target_time (state is after target)
                    should_update = time_diff_seconds < 0 or closest_state is None
                else:
                    # No preference or prefer before - just take the closer one
                    should_update = True
                    
                if should_update:
                    min_time_diff_seconds = abs_time_diff_seconds
                    closest_state = state
            elif abs_time_diff_seconds == min_time_diff_seconds and prefer_after:
                # Equally close - prefer states after target when specified
                # time_diff_seconds < 0 means state_time > target_time (state is after target)
                if time_diff_seconds < 0:
                    closest_state = state
        except Exception:
            continue
    
    if closest_state and hasattr(closest_state, "attributes"):
        lat = closest_state.attributes.get("latitude")
        lon = closest_state.attributes.get("longitude")
        
        # Validate that lat/lon are not invalid values
        if _is_valid_coordinate(lat) and _is_valid_coordinate(lon):
            return lat, lon
    
    return None, None


def _calculate_trip_confidence(
    fuel_consumed: float | None,
    start_lat: float | None,
    end_lat: float | None,
    has_start_and_end_info: bool = False,
) -> float:
    """Calculate confidence score for a detected trip.
    
    Confidence levels:
    - 1.0: Manual entry (set separately, not by this function)
    - 0.7-0.8: Auto-detected with both start and end GPS + fuel data
    - 0.5-0.7: Auto-detected with GPS but missing some data
    - 0.3-0.5: Auto-detected without GPS or missing both locations
    
    Args:
        fuel_consumed: Fuel consumed during trip (None if not available)
        start_lat: Start latitude (None if not available)
        end_lat: End latitude (None if not available)
        has_start_and_end_info: Whether trip has distinct start and end locations
        
    Returns:
        Confidence score from 0.3 to 0.8 (higher is better)
    """
    # Base confidence for detected trip
    confidence = 0.3
    
    # GPS location data available (up to +0.3)
    if start_lat is not None and end_lat is not None:
        # Check if start and end are different (not the same location)
        if has_start_and_end_info or abs(start_lat - end_lat) > 0.001:
            # Both locations present and different
            confidence += 0.3
        else:
            # Both locations present but same (lower confidence)
            confidence += 0.15
    elif start_lat is not None or end_lat is not None:
        # Only one location available
        confidence += 0.1
    
    # Fuel consumption data available (up to +0.2)
    if fuel_consumed is not None and fuel_consumed > 0:
        confidence += 0.2
    
    return round(confidence, 2)
