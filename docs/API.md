# API Reference

## Providers

### FuelPriceProvider

Base interface for all fuel price providers.

```python
from custom_components.hafwcma.providers import FuelPriceProvider

class MyProvider(FuelPriceProvider):
    async def get_stations_nearby(
        self, latitude: float, longitude: float, radius: float, fuel_type: str
    ) -> List[FuelStation]:
        """Get stations near location."""
        pass
```

#### Methods

##### `get_stations_nearby(latitude, longitude, radius, fuel_type)`

Get fuel stations within specified radius.

**Parameters:**
- `latitude` (float): Geographic latitude
- `longitude` (float): Geographic longitude  
- `radius` (float): Search radius in kilometers
- `fuel_type` (str): Fuel type ('e5', 'e10', 'diesel')

**Returns:** `List[FuelStation]`

**Raises:** `ProviderError` on API failure

##### `get_station_details(station_id)`

Get detailed information for specific station.

**Parameters:**
- `station_id` (str): Unique station identifier

**Returns:** `FuelStation`

**Raises:** `ProviderError` on API failure

##### `validate_api_key(api_key)`

Validate API credentials.

**Parameters:**
- `api_key` (str): API key to validate

**Returns:** `bool` - True if valid

### TankerkoenigProvider

Tankerkönig API implementation.

```python
from custom_components.hafwcma.providers.tankerkonig import TankerkoenigProvider

provider = TankerkoenigProvider(api_key="YOUR_KEY", session=aiohttp_session)
stations = await provider.get_stations_nearby(52.5, 13.4, 5.0, "e5")
```

## Models

### FuelStation

Represents a fuel station with pricing.

```python
from custom_components.hafwcma.models import FuelStation

station = FuelStation(
    station_id="abc123",
    name="Station Name",
    brand="Brand",
    address="Street 1",
    city="City",
    latitude=52.5,
    longitude=13.4,
    distance=2.5,
    price_e5=1.649,
    price_e10=1.599,
    price_diesel=1.549,
    is_open=True
)
```

**Attributes:**
- `station_id` (str): Unique identifier
- `name` (str): Station name
- `brand` (str): Brand/chain name
- `address` (str): Street address
- `city` (str): City name
- `latitude` (float): Latitude coordinate
- `longitude` (float): Longitude coordinate
- `distance` (float): Distance from reference in km
- `price_e5` (Optional[float]): E5 price per liter
- `price_e10` (Optional[float]): E10 price per liter
- `price_diesel` (Optional[float]): Diesel price per liter
- `is_open` (bool): Operating status
- `last_updated` (Optional[datetime]): Last update time

**Methods:**

##### `get_price(fuel_type)`

Get price for specified fuel type.

**Parameters:**
- `fuel_type` (str): 'e5', 'e10', or 'diesel'

**Returns:** `Optional[float]` - Price or None

### Vehicle

Represents a vehicle with fuel data.

```python
from custom_components.hafwcma.models import Vehicle

vehicle = Vehicle(
    name="My Car",
    tank_capacity=50.0,
    fuel_type="e5",
    current_level=35.0,
    consumption_rate=7.5
)
```

**Attributes:**
- `name` (str): Vehicle identifier
- `tank_capacity` (float): Tank capacity in liters
- `fuel_type` (str): Fuel type used
- `current_level` (Optional[float]): Current fuel level
- `consumption_rate` (Optional[float]): L/100km
- `last_refuel_date` (Optional[datetime]): Last refuel date
- `last_refuel_amount` (Optional[float]): Last refuel amount
- `last_refuel_price` (Optional[float]): Last refuel price
- `odometer` (Optional[float]): Current odometer reading

**Properties:**

##### `tank_percentage`

Current tank fill percentage (0-100).

**Returns:** `Optional[float]`

##### `estimated_range`

Estimated remaining range in kilometers.

**Returns:** `Optional[float]`

### FuelForecast

Price forecast and recommendations.

```python
from custom_components.hafwcma.models import FuelForecast

forecast = FuelForecast(
    fuel_type="e5",
    current_price=1.649,
    predicted_trend="rising",
    confidence=0.8,
    recommendation="Consider refueling soon"
)
```

**Attributes:**
- `fuel_type` (str): Fuel type
- `current_price` (float): Current average price
- `predicted_trend` (str): 'rising', 'falling', 'stable'
- `confidence` (float): Confidence level (0-1)
- `recommendation` (str): Text recommendation
- `best_time_to_refuel` (Optional[datetime]): Optimal time
- `forecast_period_hours` (int): Forecast horizon

## Messaging

### MessageService

Base interface for messaging services.

```python
from custom_components.hafwcma.messaging import MessageService

class MyMessenger(MessageService):
    async def send_message(self, message: str, **kwargs) -> bool:
        """Send message."""
        pass
```

#### Methods

##### `send_message(message, **kwargs)`

Send text message.

**Parameters:**
- `message` (str): Message text
- `**kwargs`: Service-specific parameters

**Returns:** `bool` - Success status

##### `send_price_alert(station_name, price, fuel_type, **kwargs)`

Send fuel price alert.

**Parameters:**
- `station_name` (str): Station name
- `price` (float): Current price
- `fuel_type` (str): Fuel type
- `**kwargs`: Additional parameters

**Returns:** `bool` - Success status

##### `send_refuel_recommendation(vehicle_name, should_refuel, reasoning, **kwargs)`

Send refueling recommendation.

**Parameters:**
- `vehicle_name` (str): Vehicle name
- `should_refuel` (bool): Whether to refuel
- `reasoning` (str): Recommendation explanation
- `**kwargs`: Additional parameters

**Returns:** `bool` - Success status

### TelegramNotifier

Telegram notification implementation.

```python
from custom_components.hafwcma.messaging.telegram import TelegramNotifier

notifier = TelegramNotifier(bot_token="TOKEN", chat_id="CHAT_ID")
await notifier.send_price_alert("Station", 1.649, "e5")
```

## Utilities

### Distance Calculation

```python
from custom_components.hafwcma.utils import calculate_distance

distance = calculate_distance(52.5, 13.4, 52.6, 13.5)  # Returns km
```

### Find Cheapest Station

```python
from custom_components.hafwcma.utils import find_cheapest_station

cheapest = find_cheapest_station(stations, "e5")
```

### Find Best Station

```python
from custom_components.hafwcma.utils import find_best_station

best = find_best_station(
    stations,
    fuel_type="e5",
    max_distance=10.0,
    price_weight=0.7,
    distance_weight=0.3
)
```

### Forecasting

```python
from custom_components.hafwcma.utils.forecast import FuelPriceForecaster

forecaster = FuelPriceForecaster()
forecaster.add_price_observation("e5", 1.649)
forecast = forecaster.predict_trend("e5")
should_refuel, reason = forecaster.should_refuel_now("e5", 45.0)
```

## Constants

```python
from custom_components.hafwcma.const import (
    DOMAIN,              # "hafwcma"
    FUEL_TYPE_E5,        # "e5"
    FUEL_TYPE_E10,       # "e10"
    FUEL_TYPE_DIESEL,    # "diesel"
    DEFAULT_RADIUS,      # 5.0 km
    DEFAULT_TANK_CAPACITY,  # 50.0 L
)
```

## Events

The integration fires the following events:

### `hafwcma_fuel_price_alert`

Fired when significant price change detected.

**Data:**
- `station_name` (str)
- `price` (float)
- `fuel_type` (str)
- `change` (float)

### `hafwcma_tank_low`

Fired when tank level is low.

**Data:**
- `vehicle_name` (str)
- `tank_level` (float)
- `tank_percentage` (float)

### `hafwcma_refuel_recommendation`

Fired when refueling is recommended.

**Data:**
- `vehicle_name` (str)
- `should_refuel` (bool)
- `reasoning` (str)
- `recommended_station` (str)

## Services

Currently no custom services are exposed. All functionality is available via sensors and events.

## Error Handling

### ProviderError

Raised when fuel price provider encounters error.

```python
from custom_components.hafwcma.providers import ProviderError

try:
    stations = await provider.get_stations_nearby(...)
except ProviderError as err:
    _LOGGER.error("Provider error: %s", err)
```

### MessagingError

Raised when messaging operation fails.

```python
from custom_components.hafwcma.messaging import MessagingError

try:
    await notifier.send_message(...)
except MessagingError as err:
    _LOGGER.error("Messaging error: %s", err)
```
