# K线事件通知优化设计方案

## 1. 背景与问题

### 1.1 当前架构

现有的 K 线数据存储架构采用单表设计：

```
┌─────────────────────────────────────────────────────────────┐
│                        klines 表                             │
│  - 存储所有 K 线数据（实时 + 历史）                           │
│  - is_closed 字段标记 K 线是否完结                           │
│  - INSERT 触发器 notify_kline_new() 发送通知                 │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心问题

**问题 1：通知粒度过粗**

当前的触发器对所有 INSERT 操作都发送 `kline_new` 通知，无法区分：
- 实时 K 线更新（`is_closed=false`）
- 完结 K 线写入（`is_closed=true`）
- 历史数据批量填充

**问题 2：历史填充触发大量噪声通知**

批量填充历史数据时，每条记录都会触发通知。

**问题 3：外部程序职责过重**

原方案要求外部程序感知 K 线完结状态，并手动写入多个表，增加了复杂度和出错风险。

### 1.3 优化目标

| 目标 | 说明 |
|------|------|
| **单一职责** | 外部程序只负责写入 `klines_live` |
| **触发器驱动** | 由触发器判断 `is_closed` 状态并自动流转数据 |
| **事务保证** | 所有操作在数据库事务中完成，保证一致性 |

### 1.4 业务需求

| 场景 | 触发条件 | 通知频道 | 下游处理 |
|------|----------|----------|----------|
| 实时 K 线更新 | `is_closed=false` | `kline_live` | 前端图表实时刷新 |
| K 线完结 | `is_closed=true` | `kline_closed` | 触发信号计算 |
| 历史数据填充 | 批量操作 | **不触发** | 仅写入数据库 |

## 2. 解决方案

### 2.1 设计原则

1. **职责分离**：每张表有明确的业务用途
2. **事件纯净**：按业务状态变化触发通知
3. **按需订阅**：下游服务只订阅关心的频道
4. **查询高效**：历史查询走专用归档表

### 2.2 表结构设计

采用双表分离设计：

```
┌───────────────────┐   ┌───────────────────┐
│   klines_live     │   │   klines_history  │
├───────────────────┤   ├───────────────────┤
│ 实时 K 线缓冲      │   │  历史数据归档      │
│ INSERT → 触发器    │   │  无通知            │
│                   │   │                   │
│ 总是发送实时通知    │   │                   │
│   + is_closed=t   │   │                   │
│     → 关闭通知     │   │                   │
│     → 写入历史     │   │                   │
│ 少量数据           │   │  大量数据          │
└───────────────────┘   └───────────────────┘
         │
         ├──────────────────────────────┐
         │                              │
         ▼                              ▼
   总是发送 kline_live          is_closed = true 时
         │                       ├─ 发送 kline_closed 通知
         │                       └─ 写入 klines_history
         │                              │
         ▼                              ▼
   前端 WebSocket              回测系统 / 交易系统
```

#### 2.2.1 klines_live 表

**用途**：存储当前正在形成的实时 K 线数据

**特点**：
- 每对 (symbol, interval) 只保留一条当前周期的 K 线
- 记录会随着价格变化不断更新
- INSERT 时触发器根据 `is_closed` 状态决定通知类型

```sql
CREATE TABLE klines_live (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,

    open_time TIMESTAMPTZ NOT NULL,
    close_time TIMESTAMPTZ NOT NULL,

    open_price NUMERIC(20, 8) NOT NULL,
    high_price NUMERIC(20, 8) NOT NULL,
    low_price NUMERIC(20, 8) NOT NULL,
    close_price NUMERIC(20, 8) NOT NULL,
    volume NUMERIC(28, 8) NOT NULL,
    quote_volume NUMERIC(28, 8) NOT NULL,
    number_of_trades INTEGER NOT NULL,
    taker_buy_base_volume NUMERIC(28, 8) NOT NULL,
    taker_buy_quote_volume NUMERIC(28, 8) NOT NULL,

    first_trade_id BIGINT,
    last_trade_id BIGINT,
    is_closed BOOLEAN DEFAULT FALSE,
    event_time TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT klines_live_symbol_interval_unique
        UNIQUE (symbol, interval)
);

CREATE INDEX idx_klines_live_symbol_interval
    ON klines_live (symbol, interval);
```

#### 2.2.2 klines_history 表

**用途**：存储所有已完结的 K 线数据，供各模块查询

**特点**：
- 所有历史 K 线存储于此
- **不触发任何通知**
- 各模块查询的历史数据来源

```sql
CREATE TABLE klines_history (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,

    open_time TIMESTAMPTZ NOT NULL,
    close_time TIMESTAMPTZ NOT NULL,

    open_price NUMERIC(20, 8) NOT NULL,
    high_price NUMERIC(20, 8) NOT NULL,
    low_price NUMERIC(20, 8) NOT NULL,
    close_price NUMERIC(20, 8) NOT NULL,
    volume NUMERIC(28, 8) NOT NULL,
    quote_volume NUMERIC(28, 8) NOT NULL,
    number_of_trades INTEGER NOT NULL,
    taker_buy_base_volume NUMERIC(28, 8) NOT NULL,
    taker_buy_quote_volume NUMERIC(28, 8) NOT NULL,

    first_trade_id BIGINT,
    last_trade_id BIGINT,
    is_closed BOOLEAN DEFAULT TRUE,
    event_time TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT klines_history_symbol_interval_time_unique
        UNIQUE (symbol, interval, open_time),
    CONSTRAINT klines_history_open_time_check
        CHECK (open_time < close_time)
);

-- TimescaleDB 超表
SELECT create_hypertable('klines_history', 'open_time');

-- 索引
CREATE INDEX idx_klines_history_symbol_interval_time
    ON klines_history (symbol, interval, open_time DESC);

CREATE INDEX idx_klines_history_interval_time
    ON klines_history (interval, open_time DESC);
```

## 3. 触发器与通知设计

### 3.1 事件频道设计

| 频道 | 触发条件 | 事件类型 | 订阅者 |
|------|----------|----------|--------|
| `kline_live` | INSERT INTO klines_live（**始终触发**） | `kline.live` | API 服务（前端图表） |
| `kline_closed` | INSERT INTO klines_live（`is_closed=true`） | `kline.closed` | 回测系统、交易系统 |

### 3.2 事件格式

#### kline_live 事件

```json
{
  "event_id": "018e2a4d-7c3f-8a14-b123-0a1b2c3d4e5f",
  "event_type": "kline.live",
  "timestamp": "2026-01-31T10:00:00.000Z",
  "source": "database",
  "version": "1.0",
  "data": {
    "symbol": "BINANCE:BTCUSDT",
    "interval": "1m",
    "open_time": "2026-01-31T10:00:00.000Z",
    "close_time": "2026-01-31T10:01:00.000Z",
    "open_price": "50000.00",
    "high_price": "50100.00",
    "low_price": "49950.00",
    "close_price": "50050.00",
    "volume": "10.5",
    "quote_volume": "525000.00",
    "number_of_trades": 100,
    "is_closed": false
  }
}
```

#### kline_closed 事件

```json
{
  "event_id": "018e2a4d-7c3f-8a14-b123-0a1b2c3d4e5f",
  "event_type": "kline.closed",
  "timestamp": "2026-01-31T10:01:00.000Z",
  "source": "database",
  "version": "1.0",
  "data": {
    "symbol": "BINANCE:BTCUSDT",
    "interval": "1m",
    "open_time": "2026-01-31T10:00:00.000Z",
    "close_time": "2026-01-31T10:01:00.000Z",
    "open_price": "50000.00",
    "high_price": "50100.00",
    "low_price": "49950.00",
    "close_price": "50050.00",
    "volume": "10.5",
    "quote_volume": "525000.00",
    "number_of_trades": 100,
    "is_closed": true
  }
}
```

### 3.3 触发器实现

#### handle_kline_live()

**核心职责**：
1. **始终发送** `kline_live` 通知（实时数据更新）
2. 如果 `is_closed=true`，额外发送 `kline_closed` 通知并写入历史表

```sql
CREATE OR REPLACE FUNCTION handle_kline_live()
RETURNS TRIGGER AS $$
DECLARE
    v_event_id UUID;
    v_payload JSONB;
    v_closed_payload JSONB;
BEGIN
    v_event_id := uuidv7();

    -- ========== 始终发送 kline_live 通知（INSERT 或 UPDATE 都触发） ==========
    v_payload := jsonb_build_object(
        'event_id', v_event_id::TEXT,
        'event_type', 'kline.live',
        'timestamp', NOW()::TEXT,
        'source', 'database',
        'version', '1.0',
        'data', jsonb_build_object(
            'symbol', NEW.symbol,
            'interval', NEW.interval,
            'open_time', NEW.open_time::TEXT,
            'close_time', NEW.close_time::TEXT,
            'open_price', NEW.open_price::TEXT,
            'high_price', NEW.high_price::TEXT,
            'low_price', NEW.low_price::TEXT,
            'close_price', NEW.close_price::TEXT,
            'volume', NEW.volume::TEXT,
            'quote_volume', NEW.quote_volume::TEXT,
            'number_of_trades', NEW.number_of_trades,
            'is_closed', NEW.is_closed
        ),
        'metadata', jsonb_build_object(
            'table', 'klines_live',
            'operation', TG_OP,  -- 'INSERT' 或 'UPDATE'
            'row_id', NEW.id
        )
    );
    PERFORM pg_notify('kline_live', v_payload::TEXT);

    -- ========== 如果 K 线已完结，额外处理 ==========
    IF NEW.is_closed = true THEN
        -- 1. 写入历史表
        INSERT INTO klines_history (
            symbol, interval,
            open_time, close_time,
            open_price, high_price, low_price, close_price,
            volume, quote_volume, number_of_trades,
            taker_buy_base_volume, taker_buy_quote_volume,
            first_trade_id, last_trade_id,
            is_closed, event_time
        ) VALUES (
            NEW.symbol, NEW.interval,
            NEW.open_time, NEW.close_time,
            NEW.open_price, NEW.high_price, NEW.low_price, NEW.close_price,
            NEW.volume, NEW.quote_volume, NEW.number_of_trades,
            NEW.taker_buy_base_volume, NEW.taker_buy_quote_volume,
            NEW.first_trade_id, NEW.last_trade_id,
            true, NEW.event_time
        );

        -- 2. 发送 kline_closed 通知
        v_closed_payload := jsonb_build_object(
            'event_id', v_event_id::TEXT,
            'event_type', 'kline.closed',
            'timestamp', NOW()::TEXT,
            'source', 'database',
            'version', '1.0',
            'data', jsonb_build_object(
                'symbol', NEW.symbol,
                'interval', NEW.interval,
                'open_time', NEW.open_time::TEXT,
                'close_time', NEW.close_time::TEXT,
                'open_price', NEW.open_price::TEXT,
                'high_price', NEW.high_price::TEXT,
                'low_price', NEW.low_price::TEXT,
                'close_price', NEW.close_price::TEXT,
                'volume', NEW.volume::TEXT,
                'quote_volume', NEW.quote_volume::TEXT,
                'number_of_trades', NEW.number_of_trades,
                'is_closed', true
            ),
            'metadata', jsonb_build_object(
                'table', 'klines_live',
                'operation', 'KLINE_CLOSED'
            )
        );
        PERFORM pg_notify('kline_closed', v_closed_payload::TEXT);

        -- 3. 删除已完结的实时 K 线，为新周期腾出空间
        DELETE FROM klines_live
        WHERE symbol = NEW.symbol
          AND interval = NEW.interval
          AND open_time = NEW.open_time;

        -- 返回 NULL，不将已完结 K 线保留在 live 表
        RETURN NULL;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public;

CREATE TRIGGER trigger_handle_kline_live
    BEFORE INSERT OR UPDATE ON klines_live
    FOR EACH ROW
    EXECUTE FUNCTION handle_kline_live();
```

## 4. 数据写入流程

### 4.1 统一写入流程

外部程序（K线采集器）只需执行**单一操作**：

```
币安 WebSocket
       │
       ▼
┌──────────────────┐
│  解析 K 线数据    │
│  携带 is_closed 状态 │
└────────┬─────────┘
         │
         ▼
┌────────────────────────────────────┐
│ INSERT INTO klines_live            │
│   ON CONFLICT (symbol, interval)   │
│   DO UPDATE SET close_price=...,   │
│                    volume=...,     │
│                    is_closed=...   │
└────────┬───────────────────────────┘
         │
         ▼
    ┌──────────────┐
    │ handle_kline_live() │
    │      触发器         │
    └────┬───────────┘
         │
         ├──────────────────────────────────────┐
         │                                      │
         ▼                                      ▼
    ┌──────────────────┐              ┌──────────────────────────────┐
    │ 始终发送          │              │ is_closed = true 时额外处理：│
    │ kline_live 通知   │              │ 1. 写入 klines_history       │
    └────────┬─────────┘              │ 2. 发送 kline_closed 通知     │
             │                        │ 3. 删除 live 中已完结记录     │
             │                        └──────────────────────────────┘
             │                                      │
             ▼                                      ▼
    前端图表实时刷新                    回测系统 / 交易系统 → 信号计算
```

### 4.2 外部程序职责

外部程序（K线采集器）只需：

```python
# 获取 WebSocket 推送的 K 线数据
kline_data = {
    "symbol": "BINANCE:BTCUSDT",
    "interval": "1m",
    "open_time": "2026-01-31T10:00:00.000Z",
    "close_time": "2026-01-31T10:01:00.000Z",
    "open_price": "50000.00",
    "high_price": "50100.00",
    "low_price": "49950.00",
    "close_price": "50050.00",
    "volume": "10.5",
    "quote_volume": "525000.00",
    "number_of_trades": 100,
    "is_closed": False,  # 币安 WebSocket 会标记新K线开始时的状态
    ...
}

# 写入实时表，触发器自动处理后续流程
async def save_kline(kline_data):
    await db.execute(
        INSERT_INTO_KLINES_LIVE,
        kline_data
    )
```

**无需感知**：
- K 线完结状态
- 历史表写入
- 通知触发

### 4.3 历史数据批量填充

```sql
-- 直接写入历史表，不触发任何通知
INSERT INTO klines_history (
    symbol, interval, open_time, close_time,
    open_price, high_price, low_price, close_price,
    volume, quote_volume, number_of_trades,
    taker_buy_base_volume, taker_buy_quote_volume,
    is_closed
)
SELECT
    symbol, interval, open_time, close_time,
    open_price, high_price, low_price, close_price,
    volume, quote_volume, number_of_trades,
    taker_buy_base_volume, taker_buy_quote_volume,
    TRUE AS is_closed
FROM historical_source;

-- klines_history 表无触发器，不会产生任何通知
```

## 5. 下游服务适配

### 5.1 API 服务（前端图表）

**监听频道**：`kline_live`

```python
async def listen_kline_live():
    async for notification in connection:
        if notification.channel == "kline_live":
            await websocket_manager.broadcast({
                "type": "kline_update",
                "data": notification.payload["data"]
            })
```

### 5.2 回测系统 / 交易系统（信号计算）

**监听频道**：`kline_closed`

```python
async def listen_kline_closed():
    async for notification in connection:
        if notification.channel == "kline_closed":
            await signal_calculator.calculate(
                kline=notification.payload["data"],
                symbol=notification.payload["data"]["symbol"]
            )
```

## 6. 数据查询

### 6.1 查询实时 K 线

```sql
SELECT * FROM klines_live
WHERE symbol = 'BINANCE:BTCUSDT'
  AND interval = '1m';
```

### 6.2 查询历史 K 线

```sql
SELECT * FROM klines_history
WHERE symbol = 'BINANCE:BTCUSDT'
  AND interval = '1m'
  AND open_time >= NOW() - INTERVAL '24 hours'
ORDER BY open_time DESC;
```

### 6.3 统一查询视图（可选）

```sql
CREATE VIEW klines_all AS
SELECT 'live' AS source, * FROM klines_live
UNION ALL
SELECT 'history' AS source, * FROM klines_history;
```

## 7. 数据迁移

### 7.1 从现有 klines 表迁移

```sql
-- 将现有数据迁移到历史表
INSERT INTO klines_history (
    symbol, interval, open_time, close_time,
    open_price, high_price, low_price, close_price,
    volume, quote_volume, number_of_trades,
    taker_buy_base_volume, taker_buy_quote_volume,
    first_trade_id, last_trade_id, is_closed, event_time
)
SELECT
    symbol, interval, open_time, close_time,
    open_price, high_price, low_price, close_price,
    volume, quote_volume, number_of_trades,
    taker_buy_base_volume, taker_buy_quote_volume,
    first_trade_id, last_trade_id, is_closed, event_time
FROM klines;

-- 初始化 klines_live 表（获取最新的未完结 K 线）
INSERT INTO klines_live (
    symbol, interval, open_time, close_time,
    open_price, high_price, low_price, close_price,
    volume, quote_volume, number_of_trades,
    taker_buy_base_volume, taker_buy_quote_volume,
    first_trade_id, last_trade_id, is_closed, event_time
)
SELECT DISTINCT ON (symbol, interval)
    symbol, interval, open_time, close_time,
    open_price, high_price, low_price, close_price,
    volume, quote_volume, number_of_trades,
    taker_buy_base_volume, taker_buy_quote_volume,
    first_trade_id, last_trade_id, is_closed, event_time
FROM klines
WHERE is_closed = false
ORDER BY symbol, interval, open_time DESC;
```

## 8. 文件清单

| 文件路径 | 操作 | 说明 |
|----------|------|------|
| `docker/init-scripts/01-database-init.sql` | 新建/修改 | 数据库初始化脚本（单一真相来源） |

## 9. 验证测试

### 9.1 测试场景

| 测试 | 操作 | 期望结果 |
|------|------|----------|
| 新K线插入 | `INSERT INTO klines_live` | 收到 `kline_live` 通知 |
| 价格更新 | `UPDATE klines_live SET close_price=...` | 收到 `kline_live` 通知 |
| 完结K线 | `INSERT INTO klines_live (is_closed=true)` | 收到 `kline_live` + `kline_closed` 通知，`klines_history` 有新记录 |
| 历史填充 | `INSERT INTO klines_history` | 无通知 |

### 9.2 测试用例

```sql
-- 测试 1：实时K线更新
INSERT INTO klines_live (
    symbol, interval, open_time, close_time,
    open_price, high_price, low_price, close_price,
    volume, quote_volume, number_of_trades,
    is_closed
) VALUES (
    'BINANCE:BTCUSDT', '1m',
    NOW(), NOW() + INTERVAL '1 minute',
    50000.00, 50100.00, 49950.00, 50050.00,
    10.5, 525000.00, 100,
    FALSE
);
-- 期望：收到 kline_live 通知

-- 测试 2：K线完结（两条通知）
INSERT INTO klines_live (
    symbol, interval, open_time, close_time,
    open_price, high_price, low_price, close_price,
    volume, quote_volume, number_of_trades,
    is_closed
) VALUES (
    'BINANCE:BTCUSDT', '1m',
    NOW(), NOW() + INTERVAL '1 minute',
    50000.00, 50100.00, 49950.00, 50050.00,
    10.5, 525000.00, 100,
    TRUE
);
-- 期望：
--   1. 收到 kline_live 通知（始终发送）
--   2. 收到 kline_closed 通知（is_closed=true 时额外发送）
--   3. klines_history 有一条新记录
--   4. klines_live 中该记录被删除
```

## 10. 总结

### 10.1 设计变更

| 版本 | 表数量 | 特点 |
|------|--------|------|
| 原设计 | 3 表 | klines_live + klines_closed + klines_history |
| 优化后 | **2 表** | klines_live + klines_history（删掉 klines_closed） |

### 10.2 表职责

| 表 | 职责 |
|---|------|
| `klines_live` | 实时 K 线缓冲，外部程序唯一写入目标 |
| `klines_history` | 历史数据归档，不触发任何通知 |

### 10.3 触发器行为

`handle_kline_live()` 触发器逻辑：

```
INSERT klines_live
        │
        ▼
┌───────────────────────┐
│  始终发送 kline_live  │
│       通知            │
└───────────┬───────────┘
            │
            ├── is_closed = false ──→ 完成
            │
            └── is_closed = true ──→ 额外执行：
                                       1. 写入 klines_history
                                       2. 发送 kline_closed 通知
                                       3. 删除 live 中该记录
```

### 10.4 核心优势

| 优势 | 说明 |
|------|------|
| **表更少** | 从 3 表简化为 2 表，减少维护复杂度 |
| **入口唯一** | 外部程序只写 `klines_live`，无需感知业务逻辑 |
| **通知更全** | 完结 K 线同时发送实时 + 关闭两个通知 |
| **自动流转** | 触发器自动完成历史归档 |

