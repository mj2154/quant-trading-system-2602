# Data Models Codemap

> Last updated: 2026-02-22T12:00:00Z
> Overview of data models, schemas, and type definitions.

## Model Categories

### 1. Task Models

**Location:** `services/*/src/models/task.py`

```python
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskType(Enum):
    SPOT_KLINE = "spot_kline"
    FUTURES_KLINE = "futures_kline"
    SPOT_DEPTH = "spot_depth"
    FUTURES_DEPTH = "futures_depth"
    EXCHANGE_INFO = "exchange_info"

class Task:
    task_id: str
    task_type: TaskType
    symbol: str
    interval: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    parameters: dict
```

### 2. Kline Models

**Location:** `services/binance-service/src/models/binance_kline.py`

```python
class Kline:
    symbol: str
    interval: str
    open_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    close_time: datetime
    quote_volume: Decimal
    trades: int
```

### 3. Subscription Models

**Location:** `services/api-service/src/models/subscription_models.py`

```python
class SubscriptionType(Enum):
    KLINE = "kline"
    TICKER = "ticker"
    DEPTH = "depth"
    TRADE = "trade"

class Subscription:
    subscription_id: str
    client_id: str
    symbol: str
    interval: str
    subscription_type: SubscriptionType
    created_at: datetime
```

### 4. Strategy Models

**Location:** `services/api-service/src/models/strategy_models.py`

```python
class StrategyType(Enum):
    ALPHA_01 = "alpha_01"
    RANDOM = "random"
    MACD_RESONANCE = "macd_resonance"

class StrategyConfig:
    strategy_id: str
    name: str
    strategy_type: StrategyType
    symbol: str
    interval: str
    enabled: bool
    parameters: dict
    created_at: datetime
    updated_at: datetime
```

### 5. Alert Models

**Location:** `services/api-service/src/models/alert_models.py`

```python
class AlertType(Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    SIGNAL_GENERATED = "signal_generated"

class AlertConfig:
    alert_id: str
    name: str
    alert_type: AlertType
    symbol: str
    condition: dict
    enabled: bool
    created_at: datetime
```

### 6. Binance API Models

**Location:** `services/api-service/src/models/binance_api.py`

#### Spot Kline Response
```python
class SpotKlineResponse:
    symbol: str
    interval: str
    start_time: int
    end_time: int
    data: List[SpotKline]
```

#### Exchange Info
```python
class ExchangeInfo:
    timezone: str
    server_time: int
    symbols: List[Symbol]
    filters: List[dict]
```

#### Symbol
```python
class Symbol:
    symbol: str
    status: str
    base_asset: str
    quote_asset: str
    base_precision: int
    quote_precision: int
```

### 7. WebSocket Models

**Location:** `services/api-service/src/models/websocket.py`

```python
class WSMessageType(Enum):
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    KLINE = "kline"
    TICKER = "ticker"
    DEPTH = "depth"
    ERROR = "error"

class WSMessage:
    type: WSMessageType
    payload: dict
    timestamp: int
```

### 8. Error Models

**Location:** `services/api-service/src/models/error_models.py`

```python
class ErrorCode(Enum):
    INVALID_SYMBOL = 1001
    INVALID_INTERVAL = 1002
    SUBSCRIPTION_FAILED = 2001
    CONNECTION_LOST = 2002

class APIError:
    code: ErrorCode
    message: str
    details: dict
```

### 9. Unified Models

**Location:** `services/api-service/src/models/unified_models.py`

```python
class UnifiedKline:
    symbol: str
    exchange: str  # "binance_spot" | "binance_futures"
    interval: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
```

### 10. Signal Models (Signal Service)

**Location:** `services/signal-service/src/db/strategy_signals_repository.py`

```python
class StrategySignal:
    signal_id: str
    strategy_id: str
    symbol: str
    signal_type: str  # "buy" | "sell"
    price: Decimal
    timestamp: datetime
    metadata: dict
```

## Constants

### Binance Constants

**Location:** `services/api-service/src/constants/binance.py`

```python
INTERVALS = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "1w", "1M"]

SPOT_BASE_URL = "https://api.binance.com"
FUTURES_BASE_URL = "https://fapi.binance.com"

WS_SPOT_BASE = "wss://stream.binance.com:9443/ws"
WS_FUTURES_BASE = "wss://fstream.binance.com/ws"
```

### Currency Constants

**Location:** `services/api-service/src/constants/currency.py`

```python
DEFAULT_QUOTE_ASSET = "USDT"

SUPPORTED_QUOTE_ASSETS = ["USDT", "BUSD", "BTC", "ETH", "BNB"]
```

## Database Schema Reference

### Tasks Table
```sql
CREATE TABLE tasks (
    task_id VARCHAR(64) PRIMARY KEY,
    task_type VARCHAR(32) NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    interval VARCHAR(8),
    status VARCHAR(16) DEFAULT 'pending',
    parameters JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Subscriptions Table
```sql
CREATE TABLE subscriptions (
    subscription_id VARCHAR(64) PRIMARY KEY,
    client_id VARCHAR(64) NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    interval VARCHAR(8),
    subscription_type VARCHAR(32) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Klines Table (TimescaleDB)
```sql
CREATE TABLE klines (
    time TIMESTAMP NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    interval VARCHAR(8) NOT NULL,
    open_price DECIMAL(20, 8),
    high_price DECIMAL(20, 8),
    low_price DECIMAL(20, 8),
    close_price DECIMAL(20, 8),
    volume DECIMAL(24, 8),
    quote_volume DECIMAL(24, 8),
    trades INTEGER
);

SELECT create_hypertable('klines', 'time');
```

### Strategy Signals Table
```sql
CREATE TABLE strategy_signals (
    signal_id VARCHAR(64) PRIMARY KEY,
    strategy_id VARCHAR(64) NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    signal_type VARCHAR(16) NOT NULL,
    price DECIMAL(20, 8),
    timestamp TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);
```

### Alert Configs Table
```sql
CREATE TABLE alert_configs (
    alert_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    alert_type VARCHAR(32) NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    condition JSONB NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Model Statistics

| Category | Files | Primary Models |
|----------|-------|----------------|
| API Service Models | 10 | Task, Kline, Subscription, WebSocket, Error, Strategy, Alert |
| Binance Service Models | 5 | Kline, Exchange Info, Task, Ticker, Unified |
| Signal Service Models | 4 | Signal, Config, Alert |
| Constants | 2 | Binance, Currency |

## Type Hints Usage

All models use Python type annotations:

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

@dataclass
class Kline:
    symbol: str
    interval: str
    open_time: datetime
    open_price: Decimal
    # ...
```

## Validation

Models are validated using Pydantic:

```python
from pydantic import BaseModel, validator

class Kline(BaseModel):
    symbol: str
    open_price: Decimal
    # ...

    @validator('symbol')
    def validate_symbol(cls, v):
        assert len(v) <= 16, 'symbol too long'
        return v.upper()
```
