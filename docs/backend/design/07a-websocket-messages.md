# WebSocket API 消息类型详解

> 本文档详细说明 WebSocket API 的所有消息类型、请求格式和响应格式。

---

## 目录

- [客户端请求](#客户端请求)
  - [GET 请求](#get-请求)
  - [订阅/取消订阅](#订阅取消订阅)
  - [交易操作](#交易操作)
  - [告警配置](#告警配置)
- [服务端响应](#服务端响应)
  - [响应格式](#响应格式)
  - [ACK 确认](#ack-确认)
  - [数据响应](#数据响应)
- [实时数据推送](#实时数据推送)
  - [K线推送](#k线推送)
  - [报价推送](#报价推送)
  - [信号推送](#信号推送)
  - [账户增量推送](#账户增量推送)

---

## 客户端请求

### GET 请求

所有获取数据的操作都统一使用顶层 `type` 字段区分具体操作类型。

#### 获取数据源配置

**请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_CONFIG",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456789,
    "data": {}
}
```

#### 搜索交易对

**请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_SEARCH_SYMBOLS",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456789,
    "data": {
        "query": "BTC",
        "exchange": "BINANCE",
        "symbolType": "crypto",
        "limit": 50
    }
}
```

#### 获取交易对详情

**请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_RESOLVE_SYMBOL",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456789,
    "data": {
        "symbol": "BINANCE:BTCUSDT"
    }
}
```

#### 获取 K 线数据

**请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_KLINES",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456789,
    "data": {
        "symbol": "BINANCE:BTCUSDT",
        "interval": "60",
        "fromTime": 1703123456000,
        "toTime": 1703210000000
    }
}
```

**周期映射**:
| 前端周期 | 说明 | 币安间隔 | 支持状态 |
|----------|------|----------|----------|
| `1` | 1分钟 | `1m` | ✅ 支持 |
| `5` | 5分钟 | `5m` | ✅ 支持 |
| `15` | 15分钟 | `15m` | ✅ 支持 |
| `60` | 1小时 | `1h` | ✅ 支持 |
| `240` | 4小时 | `4h` | ✅ 支持 |
| `1D` | 1天 | `1d` | ✅ 支持 |
| `1W` | 1周 | `1w` | ✅ 支持 |
| `1M` | 1月 | `1M` | ✅ 支持 |

#### 获取服务器时间

**请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_SERVER_TIME",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456789,
    "data": {}
}
```

#### 获取服务指标

**请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_METRICS",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456789,
    "data": {}
}
```

#### 获取报价

**请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_QUOTES",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456789,
    "data": {
        "symbols": ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT"]
    }
}
```

#### 查询当前订阅

**请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_SUBSCRIPTIONS",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456789,
    "data": {}
}
```

#### 获取账户信息

> **重要说明**: 账户信息通过 **REST API** 获取，而非 WebSocket API。
>
> - 期货账户: `GET /fapi/v2/account` (账户信息V2)
> - 现货账户: `GET /api/v3/account` (账户信息V3)

**期货账户请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_FUTURES_ACCOUNT",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {}
}
```

**现货账户请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_SPOT_ACCOUNT",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {}
}
```

**期货账户信息响应** (GET /fapi/v2/account):
```json
{
    "type": "ACCOUNT_DATA",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "feeTier": 0,
        "feeBurn": true,
        "canTrade": true,
        "canDeposit": true,
        "canWithdraw": true,
        "updateTime": 0,
        "multiAssetsMargin": false,
        "tradeGroupId": -1,
        "totalInitialMargin": "0.00000000",
        "totalMaintMargin": "0.00000000",
        "totalWalletBalance": "23.72469206",
        "totalUnrealizedProfit": "0.00000000",
        "totalMarginBalance": "23.72469206",
        "totalPositionInitialMargin": "0.00000000",
        "totalOpenOrderInitialMargin": "0.00000000",
        "totalCrossWalletBalance": "23.72469206",
        "totalCrossUnPnl": "0.00000000",
        "availableBalance": "23.72469206",
        "maxWithdrawAmount": "23.72469206",
        "assets": [
            {
                "asset": "USDT",
                "walletBalance": "23.72469206",
                "unrealizedProfit": "0.00000000",
                "marginBalance": "23.72469206",
                "maintMargin": "0.00000000",
                "initialMargin": "0.00000000",
                "positionInitialMargin": "0.00000000",
                "openOrderInitialMargin": "0.00000000",
                "crossWalletBalance": "23.72469206",
                "crossUnPnl": "0.00000000",
                "availableBalance": "23.72469206",
                "maxWithdrawAmount": "23.72469206",
                "marginAvailable": true,
                "updateTime": 1625474304765
            }
        ],
        "positions": [
            {
                "symbol": "BTCUSDT",
                "initialMargin": "0",
                "maintMargin": "0",
                "unrealizedProfit": "0.00000000",
                "positionInitialMargin": "0",
                "openOrderInitialMargin": "0",
                "leverage": "100",
                "isolated": true,
                "entryPrice": "0.00000",
                "maxNotional": "250000",
                "bidNotional": "0",
                "askNotional": "0",
                "positionSide": "BOTH",
                "positionAmt": "0",
                "updateTime": 0
            }
        ]
    }
}
```

**现货账户信息响应** (GET /api/v3/account):
```json
{
    "type": "ACCOUNT_DATA",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "makerCommission": 15,
        "takerCommission": 15,
        "buyerCommission": 0,
        "sellerCommission": 0,
        "commissionRates": {
            "maker": "0.00150000",
            "taker": "0.00150000",
            "buyer": "0.00000000",
            "seller": "0.00000000"
        },
        "canTrade": true,
        "canWithdraw": true,
        "canDeposit": true,
        "brokered": false,
        "requireSelfTradePrevention": false,
        "preventSor": false,
        "updateTime": 123456789,
        "accountType": "SPOT",
        "balances": [
            {
                "asset": "BTC",
                "free": "4723846.89208129",
                "locked": "0.00000000"
            },
            {
                "asset": "USDT",
                "free": "500.00000000",
                "locked": "0.00000000"
            }
        ],
        "permissions": ["SPOT"],
        "uid": 354937868
    }
}
```

#### 查询历史信号

**请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "LIST_SIGNALS",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "limit": 50,
        "offset": 0
    }
}
```

#### 策略元数据

**获取策略元数据列表**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_STRATEGY_METADATA",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {}
}
```

**获取指定策略元数据**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_STRATEGY_METADATA_BY_TYPE",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "strategyType": "MACDResonanceStrategyV5"
    }
}
```

---

### 订阅取消订阅

#### 订阅数据

**请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "SUBSCRIBE",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456789,
    "data": {
        "subscriptions": [
            "BINANCE:BTCUSDT@KLINE_60",
            "BINANCE:BTCUSDT@QUOTES"
        ]
    }
}
```

**支持的订阅键格式**:
| 数据类型 | 订阅键格式 | 说明 |
|----------|-----------|------|
| K线 | `EXCHANGE:SYMBOL@KLINE_INTERVAL` | 如 `BINANCE:BTCUSDT@KLINE_60` |
| 报价 | `EXCHANGE:SYMBOL@QUOTES` | 如 `BINANCE:BTCUSDT@QUOTES` |
| 成交 | `EXCHANGE:SYMBOL@TRADE` | 如 `BINANCE:BTCUSDT@TRADE` |
| 账户 | `EXCHANGE:PRODUCT@ACCOUNT` | 如 `BINANCE:FUTURES@ACCOUNT` |
| 信号 | `SIGNAL:ALERT_ID` | 如 `SIGNAL:550e8400e29b41d4a716446655440001` |

#### 取消订阅

**请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "UNSUBSCRIBE",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456789,
    "data": {
        "subscriptions": [
            "BINANCE:BTCUSDT@KLINE_60"
        ]
    }
}
```

**全部取消**:
```json
{
    "protocolVersion": "2.0",
    "type": "UNSUBSCRIBE",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456789,
    "data": {
        "all": true
    }
}
```

---

### 交易操作

> **详细数据模型**请参考 [08-api-models.md](./08-api-models.md)。

#### 请求ID说明

| 字段 | 说明 | 格式 | 必填 |
|------|------|------|------|
| `requestId` | WS请求追踪ID | UUID v4 hex (32字符) | ✅ |
| `newClientOrderId` | 订单标识ID（可选，币安自动生成） | UUID v4 hex (32字符) | ❌ |

> **重要说明**：`newClientOrderId` 为**可选字段**，与币安官方 API 保持一致：
> - 不传时，币安会自动生成订单标识
> - 传入时，使用自定义订单标识便于追踪
> - 订单响应中的 `orderId` 是更可靠的订单追踪标识（币安全局唯一）

#### 创建订单（期货）

```json
{
    "protocolVersion": "2.0",
    "type": "CREATE_ORDER",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "LIMIT",
        "quantity": 0.002,
        "newClientOrderId": "660e8400e29b41d4a716446655440001",
        "price": 50000.0,
        "timeInForce": "GTC",
        "positionSide": "BOTH",
        "reduceOnly": false
    }
}
```

**必填字段**: `symbol`, `side`, `type`, `quantity`
**可选字段**: `positionSide`, `price`, `timeInForce`, `reduceOnly`, `stopPrice`, `callbackRate`, `newOrderRespType`, `priceMatch`, `selfTradePreventionMode`, `goodTillDate`

> **注意**：期货不支持 `closePosition`, `activationPrice`, `workingType`, `priceProtect`

#### 创建订单（现货）

```json
{
    "protocolVersion": "2.0",
    "type": "CREATE_ORDER",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "LIMIT",
        "quantity": 0.002,
        "newClientOrderId": "660e8400e29b41d4a716446655440001",
        "price": 50000.0,
        "timeInForce": "GTC"
    }
}
```

**必填字段**: `symbol`, `side`, `type`, `quantity`
**可选字段**: `price`, `timeInForce`, `quoteOrderQty`, `stopPrice`, `icebergQty`, `trailingDelta`, `strategyId`, `strategyType`, `newOrderRespType`, `selfTradePreventionMode`

> **注意**：现货不支持 `positionSide`, `reduceOnly`

#### 查询订单

```json
{
    "protocolVersion": "2.0",
    "type": "GET_ORDER",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "symbol": "BTCUSDT",
        "origClientOrderId": "660e8400e29b41d4a716446655440001"
    }
}
```

#### 查询订单列表

```json
{
    "protocolVersion": "2.0",
    "type": "LIST_ORDERS",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "symbol": "BTCUSDT",
        "orderId": 123456789,
        "limit": 50
    }
}
```

#### 取消订单

```json
{
    "protocolVersion": "2.0",
    "type": "CANCEL_ORDER",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "symbol": "BTCUSDT",
        "origClientOrderId": "660e8400e29b41d4a716446655440001"
    }
}
```

#### 修改订单（期货）

```json
{
    "protocolVersion": "2.0",
    "type": "MODIFY_ORDER",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.003,
        "price": 51000.0,
        "timestamp": 1703426755754,
        "origClientOrderId": "660e8400e29b41d4a716446655440001",
        "newClientOrderId": "770e8400e29b41d4a716446655440002",
        "positionSide": "BOTH"
    }
}
```

**必填字段**: `symbol`, `side`, `quantity`, `price`, `timestamp`, `origClientOrderId` 或 `orderId`
**限制**: 仅支持 LIMIT 订单修改

#### 修改订单（现货）

```json
{
    "protocolVersion": "2.0",
    "type": "MODIFY_ORDER",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "symbol": "BTCUSDT",
        "timestamp": 1741922620419,
        "origClientOrderId": "660e8400e29b41d4a716446655440001",
        "newClientOrderId": "770e8400e29b41d4a716446655440002",
        "newQty": 0.001
    }
}
```

**必填字段**: `symbol`, `timestamp`, `newQty`, `origClientOrderId` 或 `orderId`
**限制**: `newQty` 必须大于0且小于原订单数量，只能减少数量

#### 查询当前挂单

```json
{
    "protocolVersion": "2.0",
    "type": "GET_OPEN_ORDERS",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "symbol": "BTCUSDT"
    }
}
```

---

### 告警配置

#### ID说明

| 字段 | 说明 | 格式 |
|------|------|------|
| `requestId` | WS请求追踪ID | UUID v4 hex (32字符) |
| `id` | 告警配置ID | UUID v4 hex (32字符) |

#### 创建告警配置

```json
{
    "protocolVersion": "2.0",
    "type": "CREATE_ALERT_CONFIG",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "id": "550e8400e29b41d4a716446655440001",
        "name": "macd_resonance_btcusdt",
        "description": "BTCUSDT MACD共振告警",
        "strategyType": "MACDResonanceStrategyV5",
        "symbol": "BINANCE:BTCUSDT",
        "interval": "60",
        "triggerType": "each_kline_close",
        "params": {
            "macd1Fastperiod": 12,
            "macd1Slowperiod": 26,
            "macd1Signalperiod": 9,
            "macd2Fastperiod": 12,
            "macd2Slowperiod": 26,
            "macd2Signalperiod": 9
        },
        "enabled": true
    }
}
```

#### 列出告警配置

```json
{
    "protocolVersion": "2.0",
    "type": "LIST_ALERT_CONFIGS",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "limit": 50,
        "offset": 0
    }
}
```

#### 更新告警配置

```json
{
    "protocolVersion": "2.0",
    "type": "UPDATE_ALERT_CONFIG",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "id": "550e8400e29b41d4a716446655440001",
        "enabled": false
    }
}
```

#### 删除告警配置

```json
{
    "protocolVersion": "2.0",
    "type": "DELETE_ALERT_CONFIG",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067200000,
    "data": {
        "id": "550e8400e29b41d4a716446655440001"
    }
}
```

---

## 服务端响应

### 响应格式

所有响应遵循统一格式：

```json
{
    "protocolVersion": "2.0",
    "type": "xxx",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456790,
    "data": { }
}
```

### ACK 确认

> **两阶段响应模式**：异步请求（如订阅、交易）采用两阶段确认：
> - **阶段1 (ACK)**：确认收到请求，返回空 `data` 对象
> - **阶段2**：返回具体数据类型（如 `SUBSCRIPTION_DATA`、`ORDER_DATA`）

**ACK 确认示例**（阶段1）:
```json
{
    "protocolVersion": "2.0",
    "type": "ACK",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456790,
    "data": {}
}
```

**三阶段模式说明**（适用于 SUBSCRIBE/UNSUBSCRIBE）：

| 阶段 | type | requestId | 说明 |
|------|------|-----------|------|
| 1 | `ACK` | ✅ 有 | 确认收到请求，返回空 data |
| 2 | `SUBSCRIPTION_DATA` | ✅ 有 | 确认处理完成，返回订阅列表 |
| - | `UPDATE` | ❌ 无 | **实时数据推送**（独立机制） |

> **重要区分**：
> - `success` 响应：请求-响应模式的最终回复，包含 `requestId`
> - `update` 推送：服务端主动推送的实时数据，**不包含 requestId**

### 数据响应

#### 配置数据响应

```json
{
    "protocolVersion": "2.0",
    "type": "CONFIG_DATA",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456790,
    "data": {
        "supportsSearch": true,
        "supportedResolutions": ["1", "5", "15", "60", "240", "1D", "1W", "1M"]
    }
}
```

#### K线数据响应

```json
{
    "protocolVersion": "2.0",
    "type": "KLINES_DATA",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456790,
    "data": {
        "symbol": "BTCUSDT",
        "interval": "60",
        "klines": [
            [1703123400000, "97000.00", "97600.00", "96800.00", "97500.00", "125.43"]
        ]
    }
}
```

#### 报价数据响应

```json
{
    "protocolVersion": "2.0",
    "type": "QUOTES_DATA",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456790,
    "data": {
        "quotes": [
            {
                "symbol": "BINANCE:BTCUSDT",
                "lp": 97500.00,
                "ask": 97501.00,
                "bid": 97499.00,
                "volume": 45678.90,
                "timestamp": 1703123456000
            }
        ]
    }
}
```

#### 搜索结果数据响应

```json
{
    "protocolVersion": "2.0",
    "type": "SEARCH_SYMBOLS_DATA",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456790,
    "data": {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "fullName": "Bitcoin/USDT",
                "description": "Bitcoin vs Tether",
                "exchange": "BINANCE",
                "type": "crypto"
            }
        ]
    }
}
```

#### 交易对详情数据响应

```json
{
    "protocolVersion": "2.0",
    "type": "SYMBOL_DATA",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456790,
    "data": {
        "symbol": "BINANCE:BTCUSDT",
        "fullName": "Bitcoin/USDT",
        "description": "Bitcoin vs Tether",
        "exchange": "BINANCE",
        "type": "crypto",
        "pricePrecision": 2,
        "quantityPrecision": 3,
        "minQuantity": 0.001,
        "maxQuantity": 100
    }
}
```

#### 订阅确认数据响应

```json
{
    "protocolVersion": "2.0",
    "type": "SUBSCRIPTION_DATA",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456790,
    "data": {
        "subscriptions": [
            "BINANCE:BTCUSDT@KLINE_60",
            "BINANCE:BTCUSDT@QUOTES"
        ]
    }
}
```

#### 服务器时间数据响应

```json
{
    "protocolVersion": "2.0",
    "type": "SERVER_TIME_DATA",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456790,
    "data": {
        "serverTime": 1703123456789
    }
}
```

#### 服务指标数据响应

```json
{
    "protocolVersion": "2.0",
    "type": "METRICS_DATA",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456790,
    "data": {
        "activeConnections": 5,
        "totalSubscriptions": 12,
        "uniqueSymbols": 8,
        "exchangeSubscriptions": {
            "BINANCE": 12
        }
    }
}
```

#### 订单数据响应

```json
{
    "protocolVersion": "2.0",
    "type": "ORDER_DATA",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067205000,
    "data": {
        "symbol": "BTCUSDT",
        "orderId": 123456789,
        "clientOrderId": "660e8400e29b41d4a716446655440001",
        "price": "50000.00",
        "origQty": "0.002",
        "executedQty": "0.000",
        "status": "NEW",
        "side": "BUY",
        "type": "LIMIT",
        "timeInForce": "GTC",
        "createTime": 1704067200000,
        "updateTime": 1704067200000
    }
}
```

#### 订单列表数据响应

```json
{
    "protocolVersion": "2.0",
    "type": "ORDER_LIST_DATA",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1704067205000,
    "data": {
        "orders": [
            {
                "symbol": "BTCUSDT",
                "orderId": 123456789,
                "clientOrderId": "660e8400e29b41d4a716446655440001",
                "price": "50000.00",
                "origQty": "0.002",
                "executedQty": "0.000",
                "status": "NEW",
                "side": "BUY",
                "type": "LIMIT"
            }
        ],
        "total": 1
    }
}
```

#### 请求类型与数据类型映射表

| 请求类型 | 响应数据类型 | 说明 |
|----------|-------------|------|
| `GET_KLINES` | `KLINES_DATA` | K线历史数据 |
| `GET_QUOTES` | `QUOTES_DATA` | 报价数据 |
| `GET_CONFIG` | `CONFIG_DATA` | 数据源配置 |
| `GET_SERVER_TIME` | `SERVER_TIME_DATA` | 服务器时间 |
| `GET_METRICS` | `METRICS_DATA` | 服务指标 |
| `GET_SEARCH_SYMBOLS` | `SEARCH_SYMBOLS_DATA` | 搜索结果数据 |
| `GET_RESOLVE_SYMBOL` | `SYMBOL_DATA` | 交易对详情数据 |
| `GET_SUBSCRIPTIONS` | `SUBSCRIPTION_DATA` | 当前订阅列表 |
| `GET_SPOT_ACCOUNT` | `ACCOUNT_DATA` | 现货账户信息 |
| `GET_FUTURES_ACCOUNT` | `ACCOUNT_DATA` | 期货账户信息 |
| `SUBSCRIBE` | `SUBSCRIPTION_DATA` | 订阅确认 |
| `UNSUBSCRIBE` | `SUBSCRIPTION_DATA` | 取消订阅确认 |
| `CREATE_ALERT_CONFIG` | `ALERT_CONFIG_DATA` | 告警配置 |
| `LIST_ALERT_CONFIGS` | `ALERT_CONFIG_DATA` | 告警配置列表 |
| `UPDATE_ALERT_CONFIG` | `ALERT_CONFIG_DATA` | 告警配置更新结果 |
| `DELETE_ALERT_CONFIG` | `ALERT_CONFIG_DATA` | 告警配置删除结果 |
| `LIST_SIGNALS` | `SIGNAL_DATA` | 信号数据列表 |
| `GET_STRATEGY_METADATA` | `STRATEGY_METADATA_DATA` | 策略元数据列表 |
| `GET_STRATEGY_METADATA_BY_TYPE` | `STRATEGY_METADATA_DATA` | 指定策略元数据 |
| `CREATE_ORDER` | `ORDER_DATA` | 订单创建结果 |
| `GET_ORDER` | `ORDER_DATA` | 订单查询结果 |
| `LIST_ORDERS` | `ORDER_LIST_DATA` | 订单列表 |
| `GET_OPEN_ORDERS` | `ORDER_LIST_DATA` | 当前挂单列表 |
| `CANCEL_ORDER` | `ORDER_DATA` | 订单取消结果 |
| `MODIFY_ORDER` | 响应模型见 08-api-models.md | 期货: `FuturesModifyOrderResponse`，现货: `SpotAmendOrderResponse` |

---

## 实时数据推送

> **重要说明**：推送消息**不包含** `requestId` 字段，是服务端主动推送。

### 推送类型汇总

| 推送类型 | 说明 | 频率 |
|----------|------|------|
| `UPDATE` (K线) | K线数据推送 | 实时 |
| `UPDATE` (报价) | 报价数据推送 | 实时 |
| `UPDATE` (信号) | 信号触发推送 | 实时 |
| `UPDATE` (账户) | 账户余额变化推送 | 实时 |
| `UPDATE` (订单) | 订单状态变化推送 | 实时 |
| `status_update` | 服务状态推送 | 每5秒 |

### K线推送

```json
{
    "type": "UPDATE",
    "timestamp": 1703123456790,
    "subscriptionKey": "BINANCE:BTCUSDT@KLINE_1",
    "data": {
        "content": {
            "time": 1703123400000,
            "open": 97000.00,
            "high": 97600.00,
            "low": 96800.00,
            "close": 97500.00,
            "volume": 125.43
        }
    }
}
```

### 报价推送

```json
{
    "type": "UPDATE",
    "timestamp": 1703123456790,
    "subscriptionKey": "BINANCE:BTCUSDT@QUOTES",
    "data": {
        "content": {
            "n": "BINANCE:BTCUSDT",
            "s": "ok",
            "v": {
                "lp": 97500.00,
                "ask": 97501.00,
                "bid": 97499.00,
                "volume": 45678.90
            }
        }
    }
}
```

### 信号推送

```json
{
    "type": "UPDATE",
    "timestamp": 1704067205000,
    "subscriptionKey": "SIGNAL:550e8400e29b41d4a716446655440001",
    "data": {
        "eventType": "signal_new",
        "content": {
            "id": 123,
            "alertId": "550e8400e29b41d4a716446655440001",
            "name": "BTC MACD共振",
            "strategyType": "MACDResonanceStrategyV5",
            "symbol": "BINANCE:BTCUSDT",
            "interval": "60",
            "signalValue": true,
            "signalReason": "建仓信号",
            "computedAt": "2026-02-13T10:00:05Z"
        }
    }
}
```

### 账户增量推送

> **说明**: 此为 WebSocket 推送，用于实时账户变化通知。
> 与 REST API 获取的完整账户信息不同（见上文"获取账户信息"部分）。

#### 期货账户（ACCOUNT_UPDATE）

```json
{
    "type": "UPDATE",
    "timestamp": 1704067205000,
    "subscriptionKey": "BINANCE:FUTURES@ACCOUNT",
    "data": {
        "eventType": "account_update",
        "content": {
            "e": "ACCOUNT_UPDATE",
            "E": 1704067205000,
            "a": {
                "m": "ORDER",
                "B": [{ "a": "USDT", "wb": "5200.00", "cw": "4200.00" }],
                "P": [{ "s": "BTCUSDT", "pa": "0.500", "ep": "50000.00" }]
            }
        }
    }
}
```

#### 现货账户事件（outboundAccountPosition / balanceUpdate / executionReport）

> **重要说明**：现货账户推送有三种事件类型，所有事件都统一使用币安原始短字段名。
> 代码实现使用 Pydantic alias 功能，字段名（如 `event_type`）映射到 JSON 输出（如 `e`）。
> 参考: `binance-docs/binance_spot_docs/User Data Stream.md`

**outboundAccountPosition 事件** - 账户余额变化时推送：
```json
{
    "type": "UPDATE",
    "timestamp": 1704067205000,
    "subscriptionKey": "BINANCE:SPOT@ACCOUNT",
    "data": {
        "e": "outboundAccountPosition",
        "E": 1564034571105,
        "u": 1564034571073,
        "B": [
            { "a": "ETH", "f": "10000.000000", "l": "0.000000" }
        ]
    }
}
```

**balanceUpdate 事件** - 充值/提现/转账时推送：
```json
{
    "type": "UPDATE",
    "timestamp": 1704067205000,
    "subscriptionKey": "BINANCE:SPOT@ACCOUNT",
    "data": {
        "e": "balanceUpdate",
        "E": 1573200697110,
        "a": "BTC",
        "d": "100.00000000",
        "T": 1573200697068
    }
}
```

**executionReport 事件** - 订单状态更新时推送：
```json
{
    "type": "UPDATE",
    "timestamp": 1704067205000,
    "subscriptionKey": "BINANCE:SPOT@ACCOUNT",
    "data": {
        "e": "executionReport",
        "E": 1499405658658,
        "s": "ETHBTC",
        "c": "mUvoqJxFIILMdfAW5iGSOW",
        "S": "BUY",
        "o": "LIMIT",
        "f": "GTC",
        "q": "1.00000000",
        "p": "0.10264410",
        "P": "0.00000000",
        "F": "0.00000000",
        "g": -1,
        "C": "",
        "x": "NEW",
        "X": "NEW",
        "r": "NONE",
        "i": 4293153,
        "l": "0.00000000",
        "z": "0.00000000",
        "L": "0.00000000",
        "n": "0",
        "N": null,
        "T": 1499405658657,
        "t": -1,
        "v": 3,
        "I": 8641984,
        "w": true,
        "m": false,
        "M": false,
        "O": 1499405658657,
        "Z": "0.00000000",
        "Y": "0.00000000",
        "Q": "0.00000000",
        "W": 1499405658657,
        "V": "NONE"
    }
}
```

> **条件字段**：executionReport 事件可能包含以下条件字段（见文档 `Conditional Fields in Execution Report` 节）：
> `d`(Trailing Delta), `D`(Trailing Time), `j`(Strategy Id), `J`(Strategy Type), `v`(Prevented Match Id), `A`(Prevented Quantity), `B`(Last Prevented Quantity), `u`(Trade Group Id), `U`(Counter Order Id), `Cs`(Counter Symbol), `pl`(Prevented Execution Quantity), `pL`(Prevented Execution Price), `pY`(Prevented Execution Quote Qty), `W`(Working Time), `b`(Match Type), `a`(Allocation ID), `k`(Working Floor), `uS`(UsedSor), `gP`(Pegged Price Type), `gOT`(Pegged offset Type), `gOV`(Pegged Offset Value), `gp`(Pegged Price)

### 服务状态推送

> **推送频率**: 每 5 秒

```json
{
    "type": "status_update",
    "timestamp": 1703123456.789,
    "data": {
        "metrics": {
            "activeConnections": 5,
            "totalSubscriptions": 12,
            "uniqueSymbols": 8,
            "exchangeSubscriptions": {
                "BINANCE": 12
            }
        }
    }
}
```

### 订单状态推送

```json
{
    "type": "UPDATE",
    "timestamp": 1704067205000,
    "subscriptionKey": "BINANCE:FUTURES@ACCOUNT",
    "data": {
        "eventType": "order_update",
        "content": {
            "e": "ORDER_TRADE_UPDATE",
            "E": 1704067205000,
            "s": "BTCUSDT",
            "i": 123456789,
            "X": "FILLED",
            "l": "0.002",
            "z": "0.002",
            "L": "50000.00",
            "n": "10.00",
            "T": 1704067205000
        }
    }
}
```

---

> **完整错误码定义**请参考 [07b-websocket-errorcodes.md](./07b-websocket-errorcodes.md)。
>
> **版本变更历史**请参考 [07c-websocket-changelog.md](./07c-websocket-changelog.md)。
