# Backend Codemap

> Last updated: 2026-02-22T12:00:00Z
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
│   │   │   ├── strategy_handler.py
│   │   │   ├── strategy_metadata_handler.py
│   │   │   └── alert_handler.py
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   ├── tasks_repository.py
│   │   │   ├── subscription_repository.py
│   │   │   ├── exchange_info_repository.py
│   │   │   ├── realtime_data_repository.py
│   │   │   ├── strategy_config_repository.py
│   │   │   ├── strategy_signals_repository.py
│   │   │   ├── strategy_metadata_repository.py
│   │   │   └── alert_signal_repository.py
│   │   ├── models/
│   │   │   ├── task.py
│   │   │   ├── unified_models.py
│   │   │   ├── binance_api.py
│   │   │   ├── subscription_models.py
│   │   │   ├── kline.py
│   │   │   ├── websocket.py
│   │   │   ├── error_models.py
│   │   │   ├── strategy_models.py
│   │   │   └── alert_models.py
│   │   ├── api/
│   │   │   ├── strategy.py
│   │   │   └── alert.py
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
│       ├── e2e/
│       │   ├── base_e2e_test.py
│       │   ├── test_spot_rest_e2e.py
│       │   ├── test_spot_ws_e2e.py
│       │   ├── test_futures_rest_e2e.py
│       │   ├── test_futures_ws_e2e.py
│       │   ├── test_ws_reconnect_e2e.py
│       │   └── run_e2e_tests.py
│       ├── test_clients.py
│       └── conftest.py
│
├── binance-service/
│   ├── src/
│   │   ├── main.py              # Binance service entrypoint
│   │   ├── clients/
│   │   │   ├── base_http_client.py
│   │   │   ├── spot_http_client.py
│   │   │   ├── spot_ws_client.py
│   │   │   ├── futures_http_client.py
│   │   │   ├── futures_ws_client.py
│   │   │   └── base_ws_client.py
│   │   ├── storage/
│   │   │   ├── kline_repository.py
│   │   │   └── exchange_repository.py
│   │   ├── events/
│   │   │   ├── task_listener.py
│   │   │   ├── exchange_info_handler.py
│   │   │   ├── subscription_sync.py
│   │   │   └── notification.py
│   │   ├── db/
│   │   │   ├── tasks_repository.py
│   │   │   └── realtime_data_repository.py
│   │   ├── models/
│   │   │   ├── task.py
│   │   │   ├── binance_kline.py
│   │   │   ├── exchange_info.py
│   │   │   ├── ticker.py
│   │   │   └── unified_models.py
│   │   ├── services/
│   │   │   └── binance_service.py
│   │   ├── constants/
│   │   │   └── binance.py
│   │   └── utils/
│   │       └── resolution.py
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
│   │   │   ├── base.py
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
│   │   │   ├── indicator_cache.py
│   │   │   └── indicator_nb.py
│   │   ├── listener/
│   │   │   ├── realtime_update_listener.py
│   │   │   └── alert_signal_listener.py
│   │   ├── services/
│   │   │   ├── signal_service.py
│   │   │   ├── trigger_engine.py
│   │   │   └── alert_signal.py
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
│   ├── strategy_handler.py
│   ├── strategy_metadata_handler.py
│   └── alert_handler.py
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
│   └── futures_ws_client.py (websockets)
├── storage/
│   ├── kline_repository.py
│   └── exchange_repository.py
├── events/
│   ├── task_listener.py
│   ├── exchange_info_handler.py
│   └── subscription_sync.py
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
│   └── alert_signal.py
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
