/**
 * FWCAM Card Help Content
 * 
 * Provides inline help documentation for all entities and features in the FWCAM card.
 * Content is available in both English and German.
 * 
 * @version 1.0.0
 */

export const HELP_CONTENT = {
  en: {
    // Sensors
    fuel_price: {
      title: "Fuel Price Sensor",
      description: "Displays the current fuel price (€/L) at the nearest or cheapest station within your configured search radius. Updates automatically based on the API update interval.",
      details: "This sensor queries fuel price data from your selected provider (e.g., Tankerkönig) and shows the most economical option considering both price and distance.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#fuel-price-sensor"
    },
    tank_level: {
      title: "Tank Level Sensor",
      description: "Shows your vehicle's current fuel tank level as a percentage. This value is estimated based on your consumption patterns and recorded refueling events.",
      details: "The tank level is calculated from your last known refueling event, minus the estimated fuel consumption based on distance traveled and your vehicle's average consumption rate.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#tank-level-sensor"
    },
    range: {
      title: "Range Sensor",
      description: "Estimated remaining range in kilometers based on current tank level and consumption patterns.",
      details: "Calculated using: Current tank level (liters) × Average consumption rate (L/100km). The prediction becomes more accurate as more consumption data is collected.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#range-sensor"
    },
    nearest_station: {
      title: "Nearest Station Sensor",
      description: "Information about the closest fuel station, including name, address, and distance from your current location.",
      details: "This sensor updates whenever fuel price data is refreshed and considers your vehicle's current position or Home Assistant's location.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#nearest-station-sensor"
    },
    consumption_prediction: {
      title: "Consumption Prediction Sensor",
      description: "AI-powered prediction of your vehicle's fuel consumption (L/100km) based on historical driving patterns and environmental factors.",
      details: "Uses machine learning to analyze your refueling history, trip data, and seasonal patterns to provide increasingly accurate consumption estimates.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#consumption-prediction-sensor"
    },
    refueling_log: {
      title: "Refueling Log Sensor",
      description: "Complete history of all refueling events with details like date, amount, price, location, and data quality indicators.",
      details: "Supports manual entry, Telegram bot integration, and automatic detection of missed refueling events. Each event includes confidence scores and data quality metrics.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#refueling-log-sensor"
    },
    trip_log: {
      title: "Trip Log Sensor",
      description: "Comprehensive log of all trips with start/end times, locations, distances, fuel consumption, and categorization (business/private/commute).",
      details: "Automatically tracks trips when trip tracking is enabled. Supports manual editing, geocoding, and export for tax purposes. Can detect missed trips from odometer history.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#trip-log-sensor"
    },
    current_trip: {
      title: "Current Trip Sensor",
      description: "Real-time information about an ongoing trip, including start time, distance traveled so far, and estimated fuel consumption.",
      details: "Active only when a trip is in progress. Updates as the vehicle moves and provides live statistics until the trip ends.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#current-trip-sensor"
    },
    nearby_cheap_stations: {
      title: "Nearby Cheap Stations Sensor",
      description: "List of the cheapest fuel stations within your configured radius, sorted by price and including distance information.",
      details: "Helps you find the best refueling opportunities near you. The number of stations shown is configurable.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#nearby-cheap-stations-sensor"
    },
    
    // Switches
    proximity_alerts: {
      title: "Proximity Alerts Switch",
      description: "Enable or disable notifications when you're near a cheap fuel station and your tank level is below the alert threshold.",
      details: "When enabled, you'll receive alerts via Telegram (if configured) when approaching stations with good prices and low tank levels.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#proximity-alerts-switch"
    },
    trip_tracking: {
      title: "Trip Tracking Switch",
      description: "Enable or disable automatic trip detection and logging based on odometer changes.",
      details: "When enabled, the system automatically creates trip records when it detects vehicle movement. Useful for mileage logging and tax documentation.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#trip-tracking-switch"
    },
    
    // Numbers
    api_update_interval: {
      title: "API Update Interval",
      description: "How often (in minutes) to query the fuel price API for updated prices. Range: 1-60 minutes.",
      details: "Lower values provide more frequent updates but may hit API rate limits. Recommended: 15 minutes. A small random jitter is added to prevent simultaneous requests.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#api-update-interval-number"
    },
    consumption_min_data_points: {
      title: "Minimum Data Points for Consumption Prediction",
      description: "Minimum number of refueling events required before consumption predictions are calculated. Range: 2-100.",
      details: "Higher values increase prediction accuracy but require more historical data. Recommended: 5-10 refueling events.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#consumption-min-data-points-number"
    },
    consumption_prediction_interval: {
      title: "Consumption Prediction Interval",
      description: "How often (in hours) to recalculate fuel consumption predictions. Range: 1-168 hours.",
      details: "Predictions are computationally intensive. Lower values provide fresher predictions but use more resources. Recommended: 6-24 hours.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#consumption-prediction-interval-number"
    },
    proximity_alert_distance: {
      title: "Proximity Alert Distance",
      description: "Distance in kilometers within which you'll receive proximity alerts for cheap stations. Range: 1-50 km.",
      details: "Alerts trigger when you're within this distance of a station that meets your price and tank level criteria.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#proximity-alert-distance-number"
    },
    cheap_stations_radius: {
      title: "Cheap Stations Search Radius",
      description: "Search radius in kilometers for finding cheap fuel stations. Range: 1-50 km.",
      details: "Larger radius finds more stations but may include inconvenient locations. Affects fuel price sensor and nearby stations list.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#cheap-stations-radius-number"
    },
    cheap_stations_count: {
      title: "Number of Cheap Stations to Display",
      description: "How many of the cheapest stations to show in the nearby stations list. Range: 1-20.",
      details: "Shows the top N cheapest stations within your search radius, sorted by price.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#cheap-stations-count-number"
    },
    min_tank_level_for_alerts: {
      title: "Minimum Tank Level for Proximity Alerts",
      description: "Tank level percentage below which proximity alerts will be triggered. Range: 1-100%.",
      details: "Alerts only fire when tank is below this threshold. Prevents unnecessary notifications when tank is full.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#min-tank-level-for-alerts-number"
    },
    
    // Features
    refueling_table: {
      title: "Refueling Log Table",
      description: "Complete history of all refueling events with sorting, filtering, and editing capabilities.",
      details: "Click any row to edit. Use the Add button to manually record a refueling. Events can be filtered by date and sorted by any column. Confidence scores indicate data quality (Manual=1.0, Telegram=0.8-0.9, Auto-recovered=0.5).",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/user_docs/REFUELING_LOG_GUIDE.md"
    },
    trip_table: {
      title: "Trip Log Table",
      description: "Complete history of all trips with categorization, geocoding, and map previews.",
      details: "Supports business/private/commute categorization for tax purposes. Click coordinates to auto-fill location names. View trip routes on static maps. Export for documentation.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#trip-log-sensor"
    },
    statistics: {
      title: "Statistics Overview",
      description: "Analytical insights from your refueling and trip data.",
      details: "Includes average consumption, total distance, refueling frequency, cost analysis, and trend identification.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md"
    },
    telegram_integration: {
      title: "Telegram Integration",
      description: "Submit refueling events via Telegram bot using natural language or voice messages.",
      details: "AI-powered parsing understands messages like 'Tankte 45 Liter für 1.65€/L bei Shell'. Supports German and English. Raw message and parsed data are both saved for verification.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/TELEGRAM_INTEGRATION.md"
    }
  },
  
  de: {
    // Sensors
    fuel_price: {
      title: "Kraftstoffpreis-Sensor",
      description: "Zeigt den aktuellen Kraftstoffpreis (€/L) an der nächstgelegenen oder günstigsten Tankstelle innerhalb Ihres konfigurierten Suchradius an. Aktualisiert sich automatisch basierend auf dem API-Aktualisierungsintervall.",
      details: "Dieser Sensor fragt Kraftstoffpreisdaten von Ihrem ausgewählten Anbieter (z.B. Tankerkönig) ab und zeigt die wirtschaftlichste Option unter Berücksichtigung von Preis und Entfernung.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#fuel-price-sensor"
    },
    tank_level: {
      title: "Tankfüllstand-Sensor",
      description: "Zeigt den aktuellen Tankfüllstand Ihres Fahrzeugs als Prozentsatz an. Dieser Wert wird basierend auf Ihren Verbrauchsmustern und aufgezeichneten Tankvorgängen geschätzt.",
      details: "Der Tankfüllstand wird aus Ihrem letzten bekannten Tankvorgang berechnet, abzüglich des geschätzten Kraftstoffverbrauchs basierend auf der zurückgelegten Strecke und der durchschnittlichen Verbrauchsrate Ihres Fahrzeugs.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#tank-level-sensor"
    },
    range: {
      title: "Reichweiten-Sensor",
      description: "Geschätzte verbleibende Reichweite in Kilometern basierend auf dem aktuellen Tankfüllstand und Verbrauchsmustern.",
      details: "Berechnet mit: Aktueller Tankfüllstand (Liter) × Durchschnittlicher Verbrauch (L/100km). Die Vorhersage wird genauer, je mehr Verbrauchsdaten gesammelt werden.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#range-sensor"
    },
    nearest_station: {
      title: "Nächste Tankstelle-Sensor",
      description: "Informationen über die nächstgelegene Tankstelle, einschließlich Name, Adresse und Entfernung von Ihrer aktuellen Position.",
      details: "Dieser Sensor wird aktualisiert, wenn Kraftstoffpreisdaten aktualisiert werden, und berücksichtigt die aktuelle Position Ihres Fahrzeugs oder den Standort von Home Assistant.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#nearest-station-sensor"
    },
    consumption_prediction: {
      title: "Verbrauchsvorhersage-Sensor",
      description: "KI-gestützte Vorhersage des Kraftstoffverbrauchs Ihres Fahrzeugs (L/100km) basierend auf historischen Fahrmustern und Umweltfaktoren.",
      details: "Verwendet maschinelles Lernen zur Analyse Ihrer Tankhistorie, Fahrtdaten und saisonalen Muster, um zunehmend genaue Verbrauchsschätzungen zu liefern.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#consumption-prediction-sensor"
    },
    refueling_log: {
      title: "Tankprotokoll-Sensor",
      description: "Vollständige Historie aller Tankvorgänge mit Details wie Datum, Menge, Preis, Standort und Datenqualitätsindikatoren.",
      details: "Unterstützt manuelle Eingabe, Telegram-Bot-Integration und automatische Erkennung verpasster Tankvorgänge. Jeder Vorgang enthält Konfidenzwerte und Datenqualitätsmetriken.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#refueling-log-sensor"
    },
    trip_log: {
      title: "Fahrtprotokoll-Sensor",
      description: "Umfassendes Protokoll aller Fahrten mit Start-/Endzeiten, Standorten, Entfernungen, Kraftstoffverbrauch und Kategorisierung (Geschäftlich/Privat/Pendeln).",
      details: "Verfolgt Fahrten automatisch, wenn die Fahrtverfolgung aktiviert ist. Unterstützt manuelle Bearbeitung, Geokodierung und Export für steuerliche Zwecke. Kann verpasste Fahrten aus der Kilometerstandshistorie erkennen.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#trip-log-sensor"
    },
    current_trip: {
      title: "Aktuelle Fahrt-Sensor",
      description: "Echtzeit-Informationen über eine laufende Fahrt, einschließlich Startzeit, bisher zurückgelegter Strecke und geschätztem Kraftstoffverbrauch.",
      details: "Nur aktiv, wenn eine Fahrt läuft. Aktualisiert sich während der Fahrzeugbewegung und liefert Live-Statistiken bis zum Ende der Fahrt.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#current-trip-sensor"
    },
    nearby_cheap_stations: {
      title: "Günstige Tankstellen in der Nähe-Sensor",
      description: "Liste der günstigsten Tankstellen in Ihrem konfigurierten Radius, sortiert nach Preis und mit Entfernungsinformation.",
      details: "Hilft Ihnen, die besten Tankmöglichkeiten in Ihrer Nähe zu finden. Die Anzahl der angezeigten Tankstellen ist konfigurierbar.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#nearby-cheap-stations-sensor"
    },
    
    // Switches
    proximity_alerts: {
      title: "Näherungsalarme-Schalter",
      description: "Aktivieren oder deaktivieren Sie Benachrichtigungen, wenn Sie sich in der Nähe einer günstigen Tankstelle befinden und Ihr Tankfüllstand unter dem Alarmschwellenwert liegt.",
      details: "Wenn aktiviert, erhalten Sie Benachrichtigungen über Telegram (falls konfiguriert), wenn Sie sich Tankstellen mit guten Preisen nähern und der Tankfüllstand niedrig ist.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#proximity-alerts-switch"
    },
    trip_tracking: {
      title: "Fahrtverfolgung-Schalter",
      description: "Aktivieren oder deaktivieren Sie die automatische Fahrterkennung und -protokollierung basierend auf Kilometerstandsänderungen.",
      details: "Wenn aktiviert, erstellt das System automatisch Fahrtaufzeichnungen, wenn es Fahrzeugbewegungen erkennt. Nützlich für Kilometerprotokollierung und Steuerdokumentation.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#trip-tracking-switch"
    },
    
    // Numbers
    api_update_interval: {
      title: "API-Aktualisierungsintervall",
      description: "Wie oft (in Minuten) die Kraftstoffpreis-API für aktualisierte Preise abgefragt wird. Bereich: 1-60 Minuten.",
      details: "Niedrigere Werte liefern häufigere Updates, können aber API-Ratenlimits erreichen. Empfohlen: 15 Minuten. Ein kleiner Zufallsjitter wird hinzugefügt, um gleichzeitige Anfragen zu verhindern.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#api-update-interval-number"
    },
    consumption_min_data_points: {
      title: "Minimale Datenpunkte für Verbrauchsvorhersage",
      description: "Minimale Anzahl von Tankvorgängen, die erforderlich sind, bevor Verbrauchsvorhersagen berechnet werden. Bereich: 2-100.",
      details: "Höhere Werte erhöhen die Vorhersagegenauigkeit, erfordern aber mehr historische Daten. Empfohlen: 5-10 Tankvorgänge.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#consumption-min-data-points-number"
    },
    consumption_prediction_interval: {
      title: "Verbrauchsvorhersage-Intervall",
      description: "Wie oft (in Stunden) Kraftstoffverbrauchsvorhersagen neu berechnet werden. Bereich: 1-168 Stunden.",
      details: "Vorhersagen sind rechenintensiv. Niedrigere Werte liefern aktuellere Vorhersagen, verbrauchen aber mehr Ressourcen. Empfohlen: 6-24 Stunden.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#consumption-prediction-interval-number"
    },
    proximity_alert_distance: {
      title: "Näherungsalarm-Entfernung",
      description: "Entfernung in Kilometern, innerhalb derer Sie Näherungsalarme für günstige Tankstellen erhalten. Bereich: 1-50 km.",
      details: "Alarme werden ausgelöst, wenn Sie sich innerhalb dieser Entfernung von einer Tankstelle befinden, die Ihre Preis- und Tankfüllstandskriterien erfüllt.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#proximity-alert-distance-number"
    },
    cheap_stations_radius: {
      title: "Suchradius für günstige Tankstellen",
      description: "Suchradius in Kilometern zum Finden günstiger Tankstellen. Bereich: 1-50 km.",
      details: "Größerer Radius findet mehr Tankstellen, kann aber unbequeme Standorte einschließen. Beeinflusst Kraftstoffpreis-Sensor und Liste naher Tankstellen.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#cheap-stations-radius-number"
    },
    cheap_stations_count: {
      title: "Anzahl anzuzeigender günstiger Tankstellen",
      description: "Wie viele der günstigsten Tankstellen in der Liste naher Tankstellen angezeigt werden. Bereich: 1-20.",
      details: "Zeigt die Top-N günstigsten Tankstellen innerhalb Ihres Suchradius, sortiert nach Preis.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#cheap-stations-count-number"
    },
    min_tank_level_for_alerts: {
      title: "Minimaler Tankfüllstand für Näherungsalarme",
      description: "Tankfüllstand-Prozentsatz, unter dem Näherungsalarme ausgelöst werden. Bereich: 1-100%.",
      details: "Alarme werden nur ausgelöst, wenn der Tank unter diesem Schwellenwert liegt. Verhindert unnötige Benachrichtigungen bei vollem Tank.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#min-tank-level-for-alerts-number"
    },
    
    // Features
    refueling_table: {
      title: "Tankprotokoll-Tabelle",
      description: "Vollständige Historie aller Tankvorgänge mit Sortier-, Filter- und Bearbeitungsmöglichkeiten.",
      details: "Klicken Sie auf eine Zeile zum Bearbeiten. Verwenden Sie die Hinzufügen-Schaltfläche für manuelle Erfassung. Ereignisse können nach Datum gefiltert und nach jeder Spalte sortiert werden. Konfidenzwerte zeigen Datenqualität (Manuell=1.0, Telegram=0.8-0.9, Auto-wiederhergestellt=0.5).",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/user_docs/REFUELING_LOG_GUIDE.md"
    },
    trip_table: {
      title: "Fahrtprotokoll-Tabelle",
      description: "Vollständige Historie aller Fahrten mit Kategorisierung, Geokodierung und Kartenvorschau.",
      details: "Unterstützt Geschäftlich/Privat/Pendeln-Kategorisierung für steuerliche Zwecke. Klicken Sie auf Koordinaten für automatisches Ausfüllen von Ortsnamen. Zeigen Sie Fahrtstrecken auf statischen Karten. Export für Dokumentation.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md#trip-log-sensor"
    },
    statistics: {
      title: "Statistik-Übersicht",
      description: "Analytische Einblicke aus Ihren Tank- und Fahrtdaten.",
      details: "Enthält Durchschnittsverbrauch, Gesamtstrecke, Tankhäufigkeit, Kostenanalyse und Trenderkennung.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/ENTITIES.md"
    },
    telegram_integration: {
      title: "Telegram-Integration",
      description: "Übermitteln Sie Tankvorgänge über Telegram-Bot mit natürlicher Sprache oder Sprachnachrichten.",
      details: "KI-gestütztes Parsing versteht Nachrichten wie 'Tankte 45 Liter für 1.65€/L bei Shell'. Unterstützt Deutsch und Englisch. Rohe Nachricht und geparste Daten werden beide zur Verifizierung gespeichert.",
      doc_link: "https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/blob/main/docs/TELEGRAM_INTEGRATION.md"
    }
  }
};
