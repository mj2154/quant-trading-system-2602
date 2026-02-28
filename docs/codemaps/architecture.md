# Architecture Codemap

> Last updated: 2026-02-22T12:00:00Z
> This document provides a high-level overview of the system's architecture.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         QUANT TRADING SYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐      │
│  │   API Service   │────▶│   TimescaleDB    │◀────│  Binance Service │      │
│  │   (Port 8000)   │     │  (Port 5432)     │     │   (Port 8001)    │      │
│  │                 │     │                  │     │                   │      │
│  │  - WebSocket    │     │  - Tasks         │     │  - Spot REST     │      │
│  │  - REST API     │◀────│  - Subscriptions │────▶│  - Spot WS       │      │
│  │  - Subscriptions│     │  - Kline Data    │     │  - Futures REST  │      │
│  │  - Notifications│     │  - Signals       │     │  - Futures WS    │      │
│  └─────────────────┘     └──────────────────┘     └─────────────────┘      │
│           │                       ▲                       │                  │
│           │                       │                       │                  │
│           ▼                       │                       ▼                  │
│  ┌─────────────────┐             │              ┌─────────────────┐        │
│  │ Signal Service  │─────────────┴──────────────│  Clash Proxy    │        │
│  │   (Port 8002)   │                            │  (Ports 7890-   │        │
│  │                 │                            │   7892, 9090)   │        │
│  │  - Strategies   │                            │                 │        │
│  │  - Indicators   │                            │  - HTTP Proxy  │        │
│  │  - Alert Engine │                            │  - SOCKS5      │        │
│  └─────────────────┘                            └─────────────────┘        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Service Architecture

### API Service (`services/api-service/`)

| Component | Path | Purpose |
|-----------|------|---------|
| Gateway | `src/gateway/` | WebSocket handling, client management |
| Database | `src/db/` | Repositories for tasks, subscriptions, signals |
| Models | `src/models/` | Pydantic models for API payloads |
| API | `src/api/` | REST endpoints (strategy, alert) |
| Services | `src/services/` | Business logic (exchange sync) |
| Protocol | `src/protocol/` | WebSocket message protocols |
| Converters | `src/converters/` | Data transformation |

**Key Files:**
- `main.py` - FastAPI entrypoint with WebSocket support
- `websocket_handler.py` - WebSocket connection lifecycle
- `subscription_manager.py` - Kline subscription tracking
- `data_processor.py` - PostgreSQL NOTIFY/LISTEN
- `strategy_handler.py` - Strategy CRUD operations
- `alert_handler.py` - Alert configuration management

### Binance Service (`services/binance-service/`)

| Component | Path | Purpose |
|-----------|------|---------|
| Clients | `src/clients/` | HTTP and WebSocket clients for Binance |
| Storage | `src/storage/` | Data persistence layer |
| Events | `src/events/` | Event publishing and listening |
| Models | `src/models/` | Binance-specific data models |

**Key Files:**
- `spot_http_client.py` - Spot REST API wrapper
- `futures_ws_client.py` - Futures WebSocket handler
- `kline_repository.py` - Kline data persistence
- `task_listener.py` - Task queue polling

### Signal Service (`services/signal-service/`)

| Component | Path | Purpose |
|-----------|------|---------|
| Strategies | `src/strategies/` | Trading strategy implementations |
| Indicators | `src/indicators/` | Technical indicators (EMA, MACD, ATR, etc.) |
| Listener | `src/listener/` | Database event listeners |
| Services | `src/services/` | Signal computation and alert engine |
| DB | `src/db/` | Data repositories |

**Key Files:**
- `base.py` - Strategy abstract base class
- `alpha_01_strategy.py` - Alpha strategy implementation
- `ema_indicator.py` - Exponential Moving Average
- `macd_indicator.py` - MACD indicator
- `trigger_engine.py` - Alert trigger processing

### Clash Proxy (`services/clash-proxy/`)

| Component | Path | Purpose |
|-----------|------|---------|
| Scripts | `scripts/` | Health checks and latency testing |

## Data Flow

```
Binance API ──▶ Clients ──▶ Converters ──▶ Storage ──▶ Database
                     │                           │
                     │                           ▼
                     │                    PostgreSQL NOTIFY
                     │                           │
                     ▼                           ▼
              Binance Service              API Service
                     │                           │
                     ▼                           ▼
              Signal Service              WebSocket Push
                     │                           │
                     ▼                           ▼
              Database (signals)           Frontend
```

## Communication Patterns

1. **REST API**: External clients → API Service → Database
2. **WebSocket**: External clients ↔ API Service ↔ Database NOTIFY
3. **Binance HTTP**: Binance Service → Binance REST API
4. **Binance WebSocket**: Binance Service ↔ Binance WebSocket Streams
5. **Task Polling**: Binance Service → Database (task table)
6. **Signal Events**: Signal Service ↔ Database (kline.new, signal.new)

## Database Coordination

The system uses PostgreSQL/TimescaleDB as the coordination center:

| Pattern | Mechanism |
|---------|-----------|
| Task Scheduling | `tasks` table + polling |
| Subscriptions | `subscriptions` table + NOTIFY |
| Real-time Updates | PostgreSQL LISTEN/NOTIFY |
| Kline Storage | TimescaleDB hypertables |
| Signal Events | `strategy_signals` + NOTIFY |

## File Statistics

| Category | Count |
|----------|-------|
| Total Python Files | 166+ |
| API Service | 53 files |
| Binance Service | 31 files |
| Signal Service | 32 files |
| Clash Proxy | 2 files |
| Frontend (Vue) | 10 files |

## Technology Stack

| Layer | Technology |
|-------|------------|
| Database | PostgreSQL + TimescaleDB |
| API Framework | FastAPI |
| Async Runtime | Python asyncio |
| HTTP Client | httpx |
| WebSocket | websockets |
| Configuration | python-dotenv |
| Data Validation | Pydantic |
| Container | Docker |
| Frontend | Vue 3 + TypeScript |
| Charting | TradingView Lightweight Charts |
