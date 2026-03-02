# Backend Codemap

> Last updated: 2026-03-01T04:42:00Z
> Detailed structure of backend services and their dependencies.

## Service Directory Structure

```
services/
├── api-service/
│   ├── src/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── gateway/
│   │   │   ├── websocket_handler.py
│   │   │   ├── client_manager.py
│   │   │   ├── subscription_manager.py
│   │   │   ├── data_processor.py
│   │   │   ├── task_router.py
│   │   │   ├── protocol.py
│   │   │   ├── alert_handler.py
│   │   │   └── strategy_handler.py (legacy)
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   ├── tasks_repository.py
│   │   │   ├── subscription_repository.py
│   │   │   ├── exchange_info_repository.py
│   │   │   ├── realtime_data_repository.py
│   │   │   ├── strategy_signals_repository.py
│   │   │   ├── alert_signal_repository.py
│   │   │   ├── strategy_metadata_repository.py
│   │   │   └── strategy_config_repository.py
│   │   ├── models/
│   │   │   ├── base.py
│   │   │   ├── error_models.py
│   │   │   ├── trading/
│   │   │   │   ├── kline_models.py
│   │   │   │   ├── futures_models.py
│   │   │   │   ├── quote_models.py
│   │   │   │   └── symbol_models.py
│   │   │   ├── db/
│   │   │   │   ├── exchange_models.py
│   │   │   │   ├── kline_history_models.py
│   │   │   │   ├── realtime_data_models.py
│   │   │   │   ├── task_models.py
│   │   │   │   ├── account_models.py
│   │   │   │   ├── signal_models.py
│   │   │   │   └── alert_config_models.py
│   │   │   └── protocol/
│   │   │       ├── ws_payload.py
│   │   │       ├── ws_message.py
│   │   │       └── constants.py
│   │   ├── api/
│   │   │   └── (REST endpoints)
│   │   ├── services/
│   │   │   └── exchange_sync_service.py
│   │   ├── converters/
│   │   │   ├── subscription.py
│   │   │   └── binance_converter.py
│   │   ├── constants/
│   │   │   ├── binance.py
│   │   │   └── currency.py
│   │   └── utils/
│   │       └── symbol.py
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── e2e/
│           ├── futures/ (REST + WS tests)
│           ├── spot/ (REST + WS tests)
│           └── run_*.py
│
├── binance-service/
│   ├── src/
│   │   ├── main.py              # Binance service entrypoint
│   │   ├── clients/
│   │   │   ├── base_http_client.py
│   │   │   ├── spot_http_client.py
│   │   │   ├── spot_ws_client.py
│   │   │   ├── spot_private_http_client.py
│   │   │   ├── futures_http_client.py
│   │   │   ├── futures_ws_client.py
│   │   │   ├── futures_private_http_client.py
│   │   │   ├── base_ws_client.py
│   │   │   ├── spot_user_stream_client.py
│   │   │   └── futures_user_stream_client.py
│   │   ├── storage/
│   │   │   └── exchange_repository.py
│   │   ├── events/
│   │   │   ├── task_listener.py
│   │   │   ├── exchange_info_handler.py
│   │   │   ├── notification.py
│   │   │   └── account_subscription_service.py
│   │   ├── db/
│   │   │   ├── tasks_repository.py
│   │   │   └── realtime_data_repository.py
│   │   ├── models/
│   │   │   ├── task.py
│   │   │   ├── kline_models.py
│   │   │   ├── exchange_info.py
│   │   │   ├── ticker.py
│   │   │   ├── base.py
│   │   │   ├── spot_account.py
│   │   │   ├── futures_account.py
│   │   │   └── trading_order.py
│   │   │       ├── OrderType
│   │   │       ├── OrderSide
│   │   │       ├── PositionSide
│   │   │       ├── TimeInForce
│   │   │       ├── OrderResponseType
│   │   │       ├── OrderStatus
│   │   │       ├── OrderRequest
│   │   │       ├── FuturesOrderRequest
│   │   │       ├── FuturesOrderResponse
│   │   │       ├── SpotOrderResponse
│   │   │       └── CancelOrderResponse
│   │   ├── services/
│   │   │   └── binance_service.py
│   │   ├── constants/
│   │   │   └── binance.py
│   │   ├── utils/
│   │   │   ├── resolution.py
│   │   │   ├── rsa_signer.py
│   │   │   └── ed25519_signer.py
│   │   └── ws_subscription_manager.py
│   ├── test_trading_futures.py     # 期货交易功能测试
│   └── test_trading_spot.py        # 现货交易功能测试
│
├── signal-service/
│   ├── src/
│   │   ├── main.py              # Signal service entrypoint
│   │   ├── strategies/
│   │   │   ├── base.py         # Strategy abstract base class
│   │   │   ├── backtest_base.py
│   │   │   ├── alpha_01_strategy.py
│   │   │   ├── random_strategy.py
│   │   │   ├── macd_resonance_strategy.py
│   │   │   └── registry.py     # Strategy registry
│   │   ├── indicators/
│   │   │   ├── ema.py
│   │   │   ├── ema_indicator.py
│   │   │   ├── macd.py
│   │   │   ├── macd_indicator.py
│   │   │   ├── atr_stop_loss_indicator.py
│   │   │   ├── pivot_point_np.py
│   │   │   ├── pivot_high_low.py
│   │   │   ├── declining_highs_indicator.py
│   │   │   ├── price_crossover_ema_indicator.py
│   │   │   ├── ema_crossover_reversal_indicator.py
│   │   │   └── indicator_cache.py
│   │   ├── listener/
│   │   │   ├── realtime_update_listener.py
│   │   │   └── alert_signal_listener.py
│   │   ├── services/
│   │   │   ├── signal_service.py
│   │   │   ├── trigger_engine.py
│   │   │   ├── alert_signal.py
│   │   │   ├── kline_cache.py
│   │   │   ├── kline_validator.py
│   │   │   ├── kline_utils.py
│   │   │   └── subscription_utils.py
│   │   └── db/
│   │       ├── database.py
│   │       ├── tasks_repository.py
│   │       ├── realtime_data_repository.py
│   │       ├── strategy_config_repository.py
│   │       ├── strategy_signals_repository.py
│   │       └── alert_config_repository.py
│
└── clash-proxy/
    ├── scripts/
    │   └── check_proxy_latency.py
    └── config/
```

## Module Dependencies

### API Service Dependencies

```
main.py
├── FastAPI
├── websockets
├── gateway/
│   ├── websocket_handler.py
│   ├── client_manager.py
│   ├── subscription_manager.py
│   ├── data_processor.py
│   ├── alert_handler.py
│   └── task_router.py
├── db/
│   ├── database.py (asyncpg)
│   └── repositories/
└── models/ (pydantic)
```

### Binance Service Dependencies

```
main.py
├── clients/
│   ├── spot_http_client.py (httpx)
│   ├── futures_http_client.py (httpx)
│   ├── spot_ws_client.py (websockets)
│   ├── futures_ws_client.py (websockets)
│   ├── spot_private_http_client.py (HMAC/RSA)
│   ├── futures_private_http_client.py (HMAC/RSA/ED25519)
│   ├── spot_user_stream_client.py
│   └── futures_user_stream_client.py
├── storage/
│   └── exchange_repository.py
├── events/
│   ├── task_listener.py
│   ├── exchange_info_handler.py
│   └── account_subscription_service.py
└── db/ (sqlalchemy core)
```

### Signal Service Dependencies

```
main.py
├── strategies/
│   ├── base.py
│   ├── alpha_01_strategy.py
│   ├── random_strategy.py
│   └── macd_resonance_strategy.py
├── indicators/
│   ├── ema.py
│   ├── macd.py
│   ├── atr_stop_loss_indicator.py
│   └── pivot_point_np.py
├── listener/
│   ├── realtime_update_listener.py
│   └── alert_signal_listener.py
├── services/
│   ├── signal_service.py
│   ├── trigger_engine.py
│   ├── alert_signal.py
│   ├── kline_cache.py
│   └── kline_validator.py
└── db/
    ├── database.py
    └── repositories/
```

## Port Allocation

| Service | Port | Protocol |
|---------|------|----------|
| API Service | 8000 | HTTP/WebSocket |
| Binance Service | 8001 | Internal |
| Signal Service | 8002 | Internal |
| Clash Proxy HTTP | 7890 | HTTP |
| Clash Proxy SOCKS5 | 7891 | SOCKS5 |
| Clash Proxy API | 7892 | HTTP |
| Clash Proxy Metrics | 9090 | Prometheus |

## Database Tables

| Table | Service | Purpose |
|-------|---------|---------|
| tasks | api-service, binance-service | Task queue |
| subscriptions | api-service | Kline subscriptions |
| klines | binance-service | OHLCV data |
| exchange_info | binance-service | Exchange metadata |
| realtime_data | binance-service | Real-time price data |
| strategy_configs | signal-service | Strategy configurations |
| strategy_signals | signal-service | Generated signals |
| alert_configs | signal-service | Alert configurations |
| account_info | binance-service | Account balances and positions |

## Entry Points

| Service | Entry Point |
|---------|-------------|
| API Service | `services/api-service/src/main.py` |
| Binance Service | `services/binance-service/src/main.py` |
| Signal Service | `services/signal-service/src/main.py` |
| Clash Proxy | `services/clash-proxy/scripts/check_proxy_latency.py` |

## Technical Indicators Available

The signal-service includes the following technical indicators:

| Indicator | File | Description |
|-----------|------|-------------|
| EMA | `ema.py`, `ema_indicator.py` | Exponential Moving Average |
| MACD | `macd.py`, `macd_indicator.py` | Moving Average Convergence Divergence |
| ATR Stop Loss | `atr_stop_loss_indicator.py` | Average True Range Stop Loss |
| Pivot Points | `pivot_point_np.py` | Pivot Point calculation |
| Pivot High/Low | `pivot_high_low.py` | Pivot high/low detection |
| Declining Highs | `declining_highs_indicator.py` | Declining highs pattern |
| Price Crossover EMA | `price_crossover_ema_indicator.py` | Price crossing EMA |
| EMA Crossover | `ema_crossover_reversal_indicator.py` | EMA crossover reversal |

## Account Integration

Binance Service now supports private API endpoints:

- **Spot Account**: Balance queries via `/api/v3/account`
- **Futures Account**: Account balance via `/fapi/v2/account`
- **User Data Streams**: Real-time account updates via WebSocket
- **Signature Methods**: HMAC SHA256, RSA SHA256, ED25519

## Trading Functionality

Trading functionality (order placement, cancellation, and query) is now implemented:

- **Futures Trading**: Via `/fapi/v1/order`, `/fapi/v1/order/test`, DELETE `/fapi/v1/order`
- **Spot Trading**: Via `/api/v3/order`, `/api/v3/order/test`, DELETE `/api/v3/order`
- **Data Models**: See `src/models/trading_order.py` for complete order type definitions
- **Test Files**: `test_trading_futures.py`, `test_trading_spot.py`

## File Statistics

| Service | Python Files | Test Files | Total |
|---------|-------------|------------|-------|
| api-service | 53 | 76 | 129 |
| binance-service | 41 | 23 | 64 |
| signal-service | 35 | 19 | 54 |
| **Total** | **129** | **118** | **248** |
