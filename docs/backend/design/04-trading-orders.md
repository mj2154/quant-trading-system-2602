# 交易订单表设计

## 1. 设计目标

- 完美适配币安交易所交易数据格式
- 支持期货(U本位)、现货多市场
- 跨服务共享：binance-service(订单创建)、api-service(订单查询)、trading-service(交易执行)
- 极简JSONB方案，平衡灵活性与性能

## 2. 设计理念

### 2.1 极简JSONB方案

采用"核心字段列存储 + 完整数据JSONB"的混合方案：

| 存储方式 | 字段 | 原因 |
|---------|------|------|
| 列存储 | client_order_id, binance_order_id, market_type, symbol, status, side, order_type | 高频查询，需索引 |
| JSONB存储 | data | 完整保留币安原始数据，灵活适配多市场 |

### 2.2 为什么可行

- 个人开发环境，数据量小(<10万)
- 核心查询走索引，无性能问题
- JSONB内字段查询可后续按需添加GIN索引

## 3. 表结构

```sql
-- -----------------------------------------------------------------------------
-- trading_orders 交易订单表
-- 设计: 存储交易订单完整数据，INSERT触发order.new通知
-- 极简JSONB方案: 核心字段列存储，完整数据JSONB存储
-- -----------------------------------------------------------------------------
CREATE TABLE trading_orders (
    id BIGSERIAL PRIMARY KEY,

    -- 唯一标识（用于查询）
    client_order_id VARCHAR(36) NOT NULL UNIQUE,

    -- 币安订单ID（订单在交易所的唯一标识）
    binance_order_id BIGINT,

    -- 区分市场类型（用于路由查询）
    market_type VARCHAR(10) NOT NULL,  -- SPOT / FUTURES

    -- 交易对（如 BTCUSDT）
    symbol VARCHAR(20) NOT NULL,

    -- 核心状态（常用查询）
    status VARCHAR(20) NOT NULL DEFAULT 'NEW',  -- NEW / PARTIALLY_FILLED / FILLED / CANCELED / REJECTED / EXPIRED
    side VARCHAR(10) NOT NULL,                   -- BUY / SELL
    order_type VARCHAR(20) NOT NULL,              -- LIMIT / MARKET / STOP / TAKE_PROFIT 等

    -- 全部数据用JSONB存储（完美适配币安格式）
    data JSONB NOT NULL,

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_trading_orders_client_id ON trading_orders (client_order_id);
CREATE INDEX IF NOT EXISTS idx_trading_orders_binance_id ON trading_orders (binance_order_id);
CREATE INDEX IF NOT EXISTS idx_trading_orders_market_status ON trading_orders (market_type, status);
CREATE INDEX IF NOT EXISTS idx_trading_orders_symbol ON trading_orders (symbol);
CREATE INDEX IF NOT EXISTS idx_trading_orders_side ON trading_orders (side);
CREATE INDEX IF NOT EXISTS idx_trading_orders_created ON trading_orders (created_at DESC);

-- 复合索引：常用查询
CREATE INDEX IF NOT EXISTS idx_trading_orders_symbol_status ON trading_orders (symbol, status);
CREATE INDEX IF NOT EXISTS idx_trading_orders_market_created ON trading_orders (market_type, created_at DESC);

-- GIN索引（可选，用于JSON内字段查询）
-- CREATE INDEX IF NOT EXISTS idx_trading_orders_data ON trading_orders USING gin (data);

-- 转换为 Hypertable（时间分区）
SELECT create_hypertable('trading_orders', 'created_at');
```

## 4. 数据字段说明

### 4.1 核心列字段

| 字段 | 类型 | 说明 |
|------|------|------|
| client_order_id | VARCHAR(36) | 客户端订单ID（系统生成UUID） |
| binance_order_id | BIGINT | 币安订单ID |
| market_type | VARCHAR(10) | 市场类型：SPOT / FUTURES |
| symbol | VARCHAR(20) | 交易对 |
| status | VARCHAR(20) | 订单状态 |
| side | VARCHAR(10) | 买卖方向 |
| order_type | VARCHAR(20) | 订单类型 |
| data | JSONB | 完整订单数据 |

### 4.2 JSONB data 字段内容

#### 期货订单 (market_type = FUTURES)

```json
{
    "clientOrderId": "testOrder",
    "orderId": 22542179,
    "symbol": "BTCUSDT",
    "side": "BUY",
    "positionSide": "SHORT",
    "type": "LIMIT",
    "origType": "TRAILING_STOP_MARKET",
    "origQty": "10",
    "price": "50000",
    "avgPrice": "0.00000",
    "stopPrice": "9300",
    "executedQty": "0",
    "cumQty": "0",
    "cumQuote": "0",
    "status": "NEW",
    "timeInForce": "GTC",
    "reduceOnly": false,
    "closePosition": false,
    "workingType": "CONTRACT_PRICE",
    "priceProtect": false,
    "priceMatch": "NONE",
    "selfTradePreventionMode": "NONE",
    "goodTillDate": 1693207680000,
    "updateTime": 1566818724722
}
```

#### 现货订单 (market_type = SPOT)

```json
{
    "symbol": "BTCUSDT",
    "orderId": 28,
    "orderListId": -1,
    "clientOrderId": "6gCrw2kRUAF9CvJDGP16IP",
    "transactTime": 1507725176595,
    "price": "0.00000000",
    "origQty": "10.00000000",
    "executedQty": "10.00000000",
    "origQuoteOrderQty": "0.000000",
    "cummulativeQuoteQty": "10.00000000",
    "status": "FILLED",
    "timeInForce": "GTC",
    "type": "MARKET",
    "side": "SELL",
    "workingTime": 1507725176595,
    "selfTradePreventionMode": "NONE",
    "fills": [
        {
            "price": "4000.00000000",
            "qty": "1.00000000",
            "commission": "4.00000000",
            "commissionAsset": "USDT",
            "tradeId": 56
        }
    ]
}
```

## 5. 数据流设计

### 5.1 订单创建流程

```
前端/交易服务
    ↓ POST /api/v3/order 或 /fapi/v1/order
binance-service
    ↓ 调用币安API下单
    ↓ INSERT trading_orders (status=NEW)
数据库
    ↓ INSERT 触发 notify_order_new()
trading_order.new 通知
    ↓
api-service → WebSocket推送 → 前端
trading-service → 交易决策处理
```

### 5.2 订单状态更新流程

```
币安 WebSocket 用户数据流
    ↓ ORDER_TRADE_UPDATE 事件
binance-service
    ↓ UPDATE trading_orders SET data=..., status=...
    ↓ UPDATE 触发 notify_order_update()
数据库
    ↓
trading_order.update 通知
    ↓
api-service → WebSocket推送 → 前端
```

### 5.3 通知频道

| 频道 | 触发条件 | 发送者 | 接收者 |
|------|---------|--------|--------|
| order.new | INSERT trading_orders | 数据库 | api-service, trading-service |
| order.update | UPDATE data/status | 数据库 | api-service, trading-service |
| order.cancel | UPDATE status=CANCELED | 数据库 | api-service, trading-service |

## 6. 使用示例

### 6.1 创建订单

```python
# binance-service 创建订单
client_order_id = str(uuid.uuid4())

# 调用币安API
result = await binance_client.create_order(...)

# 写入数据库
await pool.execute("""
    INSERT INTO trading_orders (
        client_order_id, binance_order_id, market_type, symbol,
        status, side, order_type, data
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
""",
    client_order_id,
    result["orderId"],
    "FUTURES",
    result["symbol"],
    result["status"],
    result["side"],
    result["type"],
    result  # 完整JSON
)
```

### 6.2 查询订单

```python
# 通过client_order_id查询
row = await pool.fetchrow("""
    SELECT * FROM trading_orders
    WHERE client_order_id = $1
""", client_order_id)

# 通过binance_order_id查询
row = await pool.fetchrow("""
    SELECT * FROM trading_orders
    WHERE binance_order_id = $1
""", binance_order_id)

# 查询某交易对的所有订单
rows = await pool.fetch("""
    SELECT * FROM trading_orders
    WHERE symbol = $1 AND status IN ('NEW', 'PARTIALLY_FILLED')
    ORDER BY created_at DESC
""", symbol)
```

### 6.3 更新订单状态

```python
# 通过WebSocket接收订单更新
await pool.execute("""
    UPDATE trading_orders
    SET data = $1,
        status = $2,
        updated_at = NOW()
    WHERE client_order_id = $3
""",
    update_data,        # 完整JSON
    update_data["status"],
    update_data["clientOrderId"]
)
```

## 7. 官方文档参考

- **期货U本位**: `binance_futures_docs/01_U本位合约/02_交易接口/03_REST API/下单(TRADE).md`
- **现货**: `binance_spot_docs/01_REST API/Trading endpoints.md`
- **期货响应**: `01_U本位合约/02_交易接口/03_REST API/查询订单(USER-DATA).md`
- **现货响应**: `01_REST API/Trading endpoints.md` (Conditional fields in Order Responses)

## 8. 相关文档

- [QUANT_TRADING_SYSTEM_ARCHITECTURE.md](./QUANT_TRADING_SYSTEM_ARCHITECTURE.md) - 完整实施文档
- [03-binance-service.md](./03-binance-service.md) - 币安服务交易功能设计
- [01-task-subscription.md](./01-task-subscription.md) - 任务与订阅管理

---

**版本**: v1.0
**更新**: 2026-03-02 - 新增交易订单表设计
