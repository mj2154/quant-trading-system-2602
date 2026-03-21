# 币安数据模型设计文档

> **日期**: 2026-03-21
> **状态**: 设计中
> **目的**: 为币安服务定义数据模型，严格遵循官方文档格式

---

## 1. 概述

### 1.1 模型分类

| 市场 | 数据类型 | GET 模型 | WS 模型 |
|------|----------|----------|---------|
| 现货 SPOT | K线 | BinanceSpotKlineGetModel | BinanceSpotKlineWSModel |
| 现货 SPOT | 24hr Ticker | BinanceSpotTicker24hrGetModel | BinanceSpotTicker24hrWSModel |
| 现货 SPOT | 账户信息 | BinanceSpotAccountGetModel | - |
| 现货 SPOT | 账户持仓变化 | - | BinanceSpotOutboundAccountPositionWSModel |
| 现货 SPOT | 余额更新 | - | BinanceSpotBalanceUpdateWSModel |
| 现货 SPOT | 外部锁定更新 | - | BinanceSpotExternalLockUpdateWSModel |
| 现货 SPOT | 事件流终止 | - | BinanceSpotEventStreamTerminatedWSModel |
| 现货 SPOT | 订单执行报告 | - | BinanceSpotExecutionReportWSModel |
| 现货 SPOT | 交易所信息 | BinanceSpotExchangeInfoGetModel | - |
| 期货 FUTURES | K线 | BinanceFuturesKlineGetModel | BinanceFuturesKlineWSModel |
| 期货 FUTURES | 24hr Ticker | BinanceFuturesTicker24hrGetModel | BinanceFuturesTicker24hrWSModel |
| 期货 FUTURES | 账户信息 | BinanceFuturesAccountGetModel | - |
| 期货 FUTURES | 账户更新 | - | BinanceFuturesAccountUpdateWSModel |
| 期货 FUTURES | 订单成交更新 | - | BinanceFuturesOrderTradeUpdateWSModel |
| 期货 FUTURES | 交易所信息 | BinanceFuturesExchangeInfoGetModel | - |

### 1.2 设计原则（强制）

**后续任何修改必须遵循以下原则：**

1. **现货与期货完全独立**
   - 现货模型和期货模型各自完整定义，互不参考
   - 不做"与XX相同"的推断，每个模型必须严格对应官方文档
   - 不存在"差异表"或"对比表"，每个模型自洽即可

2. **严格遵循官方文档**
   - 每个模型必须标注 `文档来源` 字段
   - 字段定义以官方文档为准，不自行推断
   - 官方文档没有的字段，不能出现在模型中

3. **禁止多余内容**
   - 不编写差异表（现货vs期货差异）
   - 不编写字段对照表（各模型独立自洽）
   - 不编写"设计决策说明"等总结性文字

4. **实现规范**
   - GET 模型：继承 `SnakeCaseModel`，使用 `alias` 处理字段映射
   - WS 模型：继承 `BaseModel`，直接用 `alias` 映射币安原始单字母字段

---

## 2. 现货（SPOT）数据模型

### 2.1 现货 K线

#### 2.1.1 GET K线

**接口**: `GET /api/v3/klines`
**文档来源**: `binance_spot_docs/01_REST API/Market Data endpoints.md`

**响应格式**（数组嵌套数组，无字段名）：
```json
[
  [
    1499040000000,      // [0] Open time
    "0.01634790",       // [1] Open
    "0.80000000",       // [2] High
    "0.01575800",       // [3] Low
    "0.01577100",       // [4] Close
    "148976.11427815",  // [5] Volume
    1499644799999,      // [6] Close time
    "2434.19055334",    // [7] Quote asset volume
    308,                // [8] Number of trades
    "1756.87402397",    // [9] Taker buy base asset volume
    "28.46694368",      // [10] Taker buy quote asset volume
    "0"                 // [11] Unused field
  ]
]
```

**模型定义**：
```python
class BinanceSpotKlineGetModel(SnakeCaseModel):
    """现货 K线 GET 响应模型

    接口: GET /api/v3/klines
    特点: 数组格式，按索引访问
    """

    open_time: int = Field(alias="0", description="K线开始时间")
    open_price: Decimal = Field(alias="1", description="开盘价")
    high_price: Decimal = Field(alias="2", description="最高价")
    low_price: Decimal = Field(alias="3", description="最低价")
    close_price: Decimal = Field(alias="4", description="收盘价")
    volume: Decimal = Field(alias="5", description="成交量")
    close_time: int = Field(alias="6", description="K线结束时间")
    quote_volume: Decimal = Field(alias="7", description="成交额")
    number_of_trades: int = Field(alias="8", description="交易笔数")
    taker_buy_base_volume: Decimal = Field(alias="9", description="主动买入成交量")
    taker_buy_quote_volume: Decimal = Field(alias="10", description="主动买入成交额")
    unused: str = Field(alias="11", description="未使用字段")

    model_config = ConfigDict(populate_by_name=True)
```

---

#### 2.1.2 WS K线

**Stream**: `<symbol>@kline_<interval>`
**文档来源**: `binance_spot_docs/WebSocket Streams.md`

**响应格式**：
```json
{
    "e": "kline",
    "E": 1672515782136,
    "s": "BNBBTC",
    "k": {
        "t": 1672515780000,
        "T": 1672515839999,
        "s": "BNBBTC",
        "i": "1m",
        "f": 100,
        "L": 200,
        "o": "0.0010",
        "c": "0.0020",
        "h": "0.0025",
        "l": "0.0015",
        "v": "1000",
        "n": 100,
        "x": false,
        "q": "1.0000",
        "V": "500",
        "Q": "0.500",
        "B": "123456"
    }
}
```

**模型定义**：
```python
class BinanceSpotKlineWSData(BaseModel):
    """现货 K线 WS 内部数据模型"""

    open_time: int = Field(alias="t", description="K线开始时间")
    close_time: int = Field(alias="T", description="K线结束时间")
    symbol: str = Field(alias="s", description="交易对")
    interval: str = Field(alias="i", description="K线间隔")
    first_trade_id: int = Field(alias="f", description="第一笔成交ID")
    last_trade_id: int = Field(alias="L", description="最后一笔成交ID")
    open_price: Decimal = Field(alias="o", description="开盘价")
    close_price: Decimal = Field(alias="c", description="收盘价")
    high_price: Decimal = Field(alias="h", description="最高价")
    low_price: Decimal = Field(alias="l", description="最低价")
    volume: Decimal = Field(alias="v", description="成交量")
    number_of_trades: int = Field(alias="n", description="交易笔数")
    is_closed: bool = Field(alias="x", description="K线是否已结束")
    quote_volume: Decimal = Field(alias="q", description="成交额")
    taker_buy_base_volume: Decimal = Field(alias="V", description="主动买入成交量")
    taker_buy_quote_volume: Decimal = Field(alias="Q", description="主动买入成交额")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotKlineWSModel(BaseModel):
    """现货 K线 WS 事件模型"""

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    symbol: str = Field(alias="s", description="交易对")
    kline: BinanceSpotKlineWSData = Field(alias="k", description="K线数据")

    model_config = ConfigDict(populate_by_name=True)
```

---



### 2.2 现货 24hr Ticker

#### 2.2.1 GET 24hr Ticker

**接口**: `GET /api/v3/ticker/24hr`
**文档来源**: `binance_spot_docs/01_REST API/Market Data endpoints.md`

**响应格式**：
```json
{
    "symbol": "BNBBTC",
    "priceChange": "-94.99999800",
    "priceChangePercent": "-95.960",
    "weightedAvgPrice": "0.29628482",
    "prevClosePrice": "0.10002000",
    "lastPrice": "4.00000200",
    "lastQty": "200.00000000",
    "bidPrice": "4.00000000",
    "bidQty": "100.00000000",
    "askPrice": "4.00000200",
    "askQty": "100.00000000",
    "openPrice": "99.00000000",
    "highPrice": "100.00000000",
    "lowPrice": "0.10000000",
    "volume": "8913.30000000",
    "quoteVolume": "15.30000000",
    "openTime": 1499783499040,
    "closeTime": 1499869899040,
    "firstId": 28385,
    "lastId": 28460,
    "count": 76
}
```

**模型定义**：
```python
class BinanceSpotTicker24hrGetModel(SnakeCaseModel):
    """现货 24hr Ticker GET 响应模型

    接口: GET /api/v3/ticker/24hr
    """

    symbol: str = Field(description="交易对")
    price_change: Decimal = Field(alias="priceChange", description="价格变动")
    price_change_percent: Decimal = Field(alias="priceChangePercent", description="价格变动百分比")
    weighted_avg_price: Decimal = Field(alias="weightedAvgPrice", description="加权平均价格")
    prev_close_price: Decimal = Field(alias="prevClosePrice", description="前一日收盘价")
    last_price: Decimal = Field(alias="lastPrice", description="最新价格")
    last_qty: Decimal = Field(alias="lastQty", description="最新成交量")
    bid_price: Decimal = Field(alias="bidPrice", description="最佳买价")
    bid_qty: Decimal = Field(alias="bidQty", description="最佳买量")
    ask_price: Decimal = Field(alias="askPrice", description="最佳卖价")
    ask_qty: Decimal = Field(alias="askQty", description="最佳卖量")
    open_price: Decimal = Field(alias="openPrice", description="开盘价")
    high_price: Decimal = Field(alias="highPrice", description="最高价")
    low_price: Decimal = Field(alias="lowPrice", description="最低价")
    volume: Decimal = Field(description="成交量")
    quote_volume: Decimal = Field(alias="quoteVolume", description="成交额")
    open_time: int = Field(alias="openTime", description="统计开始时间")
    close_time: int = Field(alias="closeTime", description="统计结束时间")
    first_id: int = Field(alias="firstId", description="首笔成交ID")
    last_id: int = Field(alias="lastId", description="末笔成交ID")
    count: int = Field(description="成交笔数")

    model_config = ConfigDict(populate_by_name=True)
```

---

#### 2.2.2 WS 24hr Ticker

**Stream**: `<symbol>@ticker`
**文档来源**: `binance_spot_docs/WebSocket Streams.md`

**响应格式**：
```json
{
    "e": "24hrTicker",
    "E": 1672515782136,
    "s": "BNBBTC",
    "p": "0.0015",
    "P": "250.00",
    "w": "0.0018",
    "x": "0.0009",
    "c": "0.0025",
    "Q": "10",
    "b": "0.0024",
    "B": "10",
    "a": "0.0026",
    "A": "100",
    "o": "0.0010",
    "h": "0.0025",
    "l": "0.0010",
    "v": "10000",
    "q": "18",
    "O": 0,
    "C": 86400000,
    "F": 0,
    "L": 18150,
    "n": 18151
}
```

**模型定义**：
```python
class BinanceSpotTicker24hrWSModel(BaseModel):
    """现货 24hr Ticker WS 事件模型

    Stream: <symbol>@ticker
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    symbol: str = Field(alias="s", description="交易对")
    price_change: Decimal = Field(alias="p", description="价格变动")
    price_change_percent: Decimal = Field(alias="P", description="价格变动百分比")
    weighted_avg_price: Decimal = Field(alias="w", description="加权平均价格")
    first_price: Decimal = Field(alias="x", description="First trade(F)-1 price")
    last_price: Decimal = Field(alias="c", description="最新价格")
    last_qty: Decimal = Field(alias="Q", description="最新成交量")
    best_bid_price: Decimal = Field(alias="b", description="最佳买价")
    best_bid_qty: Decimal = Field(alias="B", description="最佳买量")
    best_ask_price: Decimal = Field(alias="a", description="最佳卖价")
    best_ask_qty: Decimal = Field(alias="A", description="最佳卖量")
    open_price: Decimal = Field(alias="o", description="开盘价")
    high_price: Decimal = Field(alias="h", description="最高价")
    low_price: Decimal = Field(alias="l", description="最低价")
    volume: Decimal = Field(alias="v", description="成交量")
    quote_volume: Decimal = Field(alias="q", description="成交额")
    open_time: int = Field(alias="O", description="统计开始时间")
    close_time: int = Field(alias="C", description="统计结束时间")
    first_trade_id: int = Field(alias="F", description="首笔成交ID")
    last_trade_id: int = Field(alias="L", description="末笔成交ID")
    number_of_trades: int = Field(alias="n", description="成交笔数")

    model_config = ConfigDict(populate_by_name=True)
```

---
### 2.3 现货交易所信息 GET

**接口**: `GET /api/v3/exchangeInfo`
**文档来源**: `binance_spot_docs/01_REST API/General endpoints.md`

**响应格式**：
```json
{
    "timezone": "UTC",
    "serverTime": 1565246363776,
    "rateLimits": [
        {
            "interval": "MINUTE",
            "intervalNum": 1,
            "limit": 1200,
            "rateLimitType": "REQUEST_WEIGHT"
        }
    ],
    "exchangeFilters": [],
    "symbols": [
        {
            "symbol": "ETHBTC",
            "status": "TRADING",
            "baseAsset": "ETH",
            "baseAssetPrecision": 8,
            "quoteAsset": "BTC",
            "quotePrecision": 8,
            "quoteAssetPrecision": 8,
            "baseCommissionPrecision": 8,
            "quoteCommissionPrecision": 8,
            "orderTypes": [
                "LIMIT",
                "LIMIT_MAKER",
                "MARKET",
                "STOP_LOSS",
                "STOP_LOSS_LIMIT",
                "TAKE_PROFIT",
                "TAKE_PROFIT_LIMIT"
            ],
            "icebergAllowed": true,
            "ocoAllowed": true,
            "otoAllowed": true,
            "opoAllowed": true,
            "quoteOrderQtyMarketAllowed": true,
            "allowTrailingStop": false,
            "cancelReplaceAllowed": false,
            "amendAllowed": false,
            "pegInstructionsAllowed": true,
            "isSpotTradingAllowed": true,
            "isMarginTradingAllowed": true,
            "filters": [],
            "permissions": [],
            "permissionSets": [["SPOT", "MARGIN"]],
            "defaultSelfTradePreventionMode": "NONE",
            "allowedSelfTradePreventionModes": ["NONE"]
        }
    ],
    "sors": [
        {
            "baseAsset": "BTC",
            "symbols": ["BTCUSDT", "BTCUSDC"]
        }
    ]
}
```

**模型定义**：
```python
class BinanceSpotExchangeInfoRateLimitModel(BaseModel):
    """现货交易所信息 - 频率限制子模型"""

    interval: str = Field(description="限流间隔")
    interval_num: int = Field(alias="intervalNum", description="间隔数量")
    limit: int = Field(description="限制数量")
    rate_limit_type: str = Field(alias="rateLimitType", description="限流类型")


class BinanceSpotExchangeInfoSymbolFilterModel(BaseModel):
    """现货交易所信息 - Symbol过滤器子模型（基类）"""

    filter_type: str = Field(alias="filterType", description="过滤器类型")


class BinanceSpotExchangeInfoSymbolModel(BaseModel):
    """现货交易所信息 - 交易对子模型"""

    symbol: str = Field(description="交易对")
    status: str = Field(description="交易对状态")
    base_asset: str = Field(alias="baseAsset", description="基础资产")
    base_asset_precision: int = Field(alias="baseAssetPrecision", description="基础资产精度")
    quote_asset: str = Field(alias="quoteAsset", description="报价资产")
    quote_precision: int = Field(alias="quotePrecision", description="报价精度（已废弃）")
    quote_asset_precision: int = Field(alias="quoteAssetPrecision", description="报价资产精度")
    base_commission_precision: int = Field(
        alias="baseCommissionPrecision", description="基础手续费精度"
    )
    quote_commission_precision: int = Field(
        alias="quoteCommissionPrecision", description="报价手续费精度"
    )
    order_types: list[str] = Field(alias="orderTypes", description="支持的订单类型")
    iceberg_allowed: bool = Field(alias="icebergAllowed", description="是否允许冰山单")
    oco_allowed: bool = Field(alias="ocoAllowed", description="是否允许OCO订单")
    oto_allowed: bool = Field(alias="otoAllowed", description="是否允许OTO订单")
    opo_allowed: bool = Field(alias="opoAllowed", description="是否允许OPO订单")
    quote_order_qty_market_allowed: bool = Field(
        alias="quoteOrderQtyMarketAllowed", description="是否允许quote订单数量市价单"
    )
    allow_trailing_stop: bool = Field(alias="allowTrailingStop", description="是否允许追踪止损")
    cancel_replace_allowed: bool = Field(
        alias="cancelReplaceAllowed", description="是否允许取消替换"
    )
    amend_allowed: bool = Field(alias="amendAllowed", description="是否允许修改订单")
    peg_instructions_allowed: bool = Field(
        alias="pegInstructionsAllowed", description="是否允许挂钩指令"
    )
    is_spot_trading_allowed: bool = Field(
        alias="isSpotTradingAllowed", description="是否允许现货交易"
    )
    is_margin_trading_allowed: bool = Field(
        alias="isMarginTradingAllowed", description="是否允许杠杆交易"
    )
    filters: list[dict] = Field(description="过滤器列表")
    permissions: list[str] = Field(description="权限列表")
    permission_sets: list[list[str]] = Field(
        alias="permissionSets", description="权限集合列表"
    )
    default_self_trade_prevention_mode: str = Field(
        alias="defaultSelfTradePreventionMode", description="默认自成交预防模式"
    )
    allowed_self_trade_prevention_modes: list[str] = Field(
        alias="allowedSelfTradePreventionModes", description="允许的自成交预防模式列表"
    )


class BinanceSpotExchangeInfoSorModel(BaseModel):
    """现货交易所信息 - SOR子模型"""

    base_asset: str = Field(alias="baseAsset", description="基础资产")
    symbols: list[str] = Field(description="交易对列表")


class BinanceSpotExchangeInfoGetModel(SnakeCaseModel):
    """现货交易所信息 GET 响应模型

    接口: GET /api/v3/exchangeInfo
    """

    timezone: str = Field(description="时区")
    server_time: int = Field(alias="serverTime", description="服务器时间")
    rate_limits: list[BinanceSpotExchangeInfoRateLimitModel] = Field(
        alias="rateLimits", description="频率限制列表"
    )
    exchange_filters: list[dict] = Field(
        alias="exchangeFilters", description="交易所过滤器列表"
    )
    symbols: list[BinanceSpotExchangeInfoSymbolModel] = Field(description="交易对列表")
    sors: list[BinanceSpotExchangeInfoSorModel] = Field(
        default=[], description="SOR列表"
    )

    model_config = ConfigDict(populate_by_name=True)
```

---


## 3. 期货（FUTURES）数据模型

### 3.1 期货 K线

#### 3.1.1 GET K线

**接口**: `GET /fapi/v1/klines`
**文档来源**: `binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/K 线数据.md`

**响应格式**（数组嵌套数组）：
```json
[
  [
    1499040000000,
    "0.01634790",
    "0.80000000",
    "0.01575800",
    "0.01577100",
    "148976.11427815",
    1499644799999,
    "2434.19055334",
    308,
    "1756.87402397",
    "28.46694368",
    "17928899.62484339"
  ]
]
```

**模型定义**：
```python
class BinanceFuturesKlineGetModel(SnakeCaseModel):
    """期货 K线 GET 响应模型

    接口: GET /fapi/v1/klines
    特点: 数组格式，按索引访问
    """

    open_time: int = Field(alias="0", description="K线开始时间")
    open_price: Decimal = Field(alias="1", description="开盘价")
    high_price: Decimal = Field(alias="2", description="最高价")
    low_price: Decimal = Field(alias="3", description="最低价")
    close_price: Decimal = Field(alias="4", description="收盘价")
    volume: Decimal = Field(alias="5", description="成交量")
    close_time: int = Field(alias="6", description="K线结束时间")
    quote_volume: Decimal = Field(alias="7", description="成交额")
    number_of_trades: int = Field(alias="8", description="交易笔数")
    taker_buy_base_volume: Decimal = Field(alias="9", description="主动买入成交量")
    taker_buy_quote_volume: Decimal = Field(alias="10", description="主动买入成交额")
    unused: str = Field(alias="11", description="忽略字段")

    model_config = ConfigDict(populate_by_name=True)
```

---

#### 3.1.2 WS K线

**Stream**: `<symbol>@kline_<interval>`
**文档来源**: `binance_futures_docs/01_U本位合约/02_Websocket行情推送/K线.md`

**响应格式**：
```json
{
    "e": "kline",
    "E": 1638747660000,
    "s": "BTCUSDT",
    "k": {
        "t": 1638747660000,
        "T": 1638747719999,
        "s": "BTCUSDT",
        "i": "1m",
        "f": 100,
        "L": 200,
        "o": "0.0010",
        "c": "0.0020",
        "h": "0.0025",
        "l": "0.0015",
        "v": "1000",
        "n": 100,
        "x": false,
        "q": "1.0000",
        "V": "500",
        "Q": "0.500",
        "B": "123456"
    }
}
```

**模型定义**：
```python
class BinanceFuturesKlineWSData(BaseModel):
    """期货 K线 WS 内部数据模型"""

    open_time: int = Field(alias="t", description="K线开始时间")
    close_time: int = Field(alias="T", description="K线结束时间")
    symbol: str = Field(alias="s", description="交易对")
    interval: str = Field(alias="i", description="K线间隔")
    first_trade_id: int = Field(alias="f", description="第一笔成交ID")
    last_trade_id: int = Field(alias="L", description="最后一笔成交ID")
    open_price: Decimal = Field(alias="o", description="开盘价")
    close_price: Decimal = Field(alias="c", description="收盘价")
    high_price: Decimal = Field(alias="h", description="最高价")
    low_price: Decimal = Field(alias="l", description="最低价")
    volume: Decimal = Field(alias="v", description="成交量")
    number_of_trades: int = Field(alias="n", description="交易笔数")
    is_closed: bool = Field(alias="x", description="K线是否已结束")
    quote_volume: Decimal = Field(alias="q", description="成交额")
    taker_buy_base_volume: Decimal = Field(alias="V", description="主动买入成交量")
    taker_buy_quote_volume: Decimal = Field(alias="Q", description="主动买入成交额")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesKlineWSModel(BaseModel):
    """期货 K线 WS 事件模型"""

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    symbol: str = Field(alias="s", description="交易对")
    kline: BinanceFuturesKlineWSData = Field(alias="k", description="K线数据")

    model_config = ConfigDict(populate_by_name=True)
```

---

### 3.2 期货 24hr Ticker

#### 3.2.1 GET 24hr Ticker

**接口**: `GET /fapi/v1/ticker/24hr`
**文档来源**: `binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/24hr价格变动情况.md`

**响应格式**：
```json
{
    "symbol": "BTCUSDT",
    "priceChange": "-94.99999800",
    "priceChangePercent": "-95.960",
    "weightedAvgPrice": "0.29628482",
    "lastPrice": "4.00000200",
    "lastQty": "200.00000000",
    "openPrice": "99.00000000",
    "highPrice": "100.00000000",
    "lowPrice": "0.10000000",
    "volume": "8913.30000000",
    "quoteVolume": "15.30000000",
    "openTime": 1499783499040,
    "closeTime": 1499869899040,
    "firstId": 28385,
    "lastId": 28460,
    "count": 76
}
```

**模型定义**：
```python
class BinanceFuturesTicker24hrGetModel(SnakeCaseModel):
    """期货 24hr Ticker GET 响应模型

    接口: GET /fapi/v1/ticker/24hr
    """

    symbol: str = Field(description="交易对")
    price_change: Decimal = Field(alias="priceChange", description="价格变动")
    price_change_percent: Decimal = Field(alias="priceChangePercent", description="价格变动百分比")
    weighted_avg_price: Decimal = Field(alias="weightedAvgPrice", description="加权平均价格")
    last_price: Decimal = Field(alias="lastPrice", description="最新价格")
    last_qty: Decimal = Field(alias="lastQty", description="最新成交量")
    open_price: Decimal = Field(alias="openPrice", description="开盘价")
    high_price: Decimal = Field(alias="highPrice", description="最高价")
    low_price: Decimal = Field(alias="lowPrice", description="最低价")
    volume: Decimal = Field(description="成交量")
    quote_volume: Decimal = Field(alias="quoteVolume", description="成交额")
    open_time: int = Field(alias="openTime", description="统计开始时间")
    close_time: int = Field(alias="closeTime", description="统计结束时间")
    first_id: int = Field(alias="firstId", description="首笔成交ID")
    last_id: int = Field(alias="lastId", description="末笔成交ID")
    count: int = Field(description="成交笔数")

    model_config = ConfigDict(populate_by_name=True)
```

---

#### 3.2.2 WS 24hr Ticker

**Stream**: `<symbol>@ticker`
**文档来源**: `binance_futures_docs/01_U本位合约/02_Websocket行情推送/按 Symbol 的完整 Ticker.md`

**响应格式**：
```json
{
    "e": "24hrTicker",
    "E": 123456789,
    "s": "BTCUSDT",
    "p": "0.0015",
    "P": "250.00",
    "w": "0.0018",
    "c": "0.0025",
    "Q": "10",
    "o": "0.0010",
    "h": "0.0025",
    "l": "0.0010",
    "v": "10000",
    "q": "18",
    "O": 0,
    "C": 86400000,
    "F": 0,
    "L": 18150,
    "n": 18151
}
```

**模型定义**：
```python
class BinanceFuturesTicker24hrWSModel(BaseModel):
    """期货 24hr Ticker WS 事件模型

    Stream: <symbol>@ticker
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    symbol: str = Field(alias="s", description="交易对")
    price_change: Decimal = Field(alias="p", description="价格变动")
    price_change_percent: Decimal = Field(alias="P", description="价格变动百分比")
    weighted_avg_price: Decimal = Field(alias="w", description="加权平均价格")
    last_price: Decimal = Field(alias="c", description="最新价格")
    last_qty: Decimal = Field(alias="Q", description="最新成交量")
    open_price: Decimal = Field(alias="o", description="开盘价")
    high_price: Decimal = Field(alias="h", description="最高价")
    low_price: Decimal = Field(alias="l", description="最低价")
    volume: Decimal = Field(alias="v", description="成交量")
    quote_volume: Decimal = Field(alias="q", description="成交额")
    open_time: int = Field(alias="O", description="统计开始时间")
    close_time: int = Field(alias="C", description="统计结束时间")
    first_trade_id: int = Field(alias="F", description="首笔成交ID")
    last_trade_id: int = Field(alias="L", description="末笔成交ID")
    number_of_trades: int = Field(alias="n", description="成交笔数")

    model_config = ConfigDict(populate_by_name=True)
```

---
### 3.3 期货交易所信息 GET

**接口**: `GET /fapi/v1/exchangeInfo`
**文档来源**: `binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/获取交易规则和交易对.md`

**响应格式**：
```json
{
    "exchangeFilters": [],
    "rateLimits": [
        {
            "interval": "MINUTE",
            "intervalNum": 1,
            "limit": 2400,
            "rateLimitType": "REQUEST_WEIGHT"
        }
    ],
    "serverTime": 1565613908500,
    "assets": [
        {
            "asset": "BTC",
            "marginAvailable": true,
            "autoAssetExchange": "-0.10"
        }
    ],
    "symbols": [
        {
            "symbol": "BLZUSDT",
            "pair": "BLZUSDT",
            "contractType": "PERPETUAL",
            "deliveryDate": 4133404800000,
            "onboardDate": 1598252400000,
            "status": "TRADING",
            "maintMarginPercent": "2.5000",
            "requiredMarginPercent": "5.0000",
            "baseAsset": "BLZ",
            "quoteAsset": "USDT",
            "marginAsset": "USDT",
            "pricePrecision": 5,
            "quantityPrecision": 0,
            "baseAssetPrecision": 8,
            "quotePrecision": 8,
            "underlyingType": "COIN",
            "underlyingSubType": ["STORAGE"],
            "settlePlan": 0,
            "triggerProtect": "0.15",
            "filters": [
                {
                    "filterType": "PRICE_FILTER",
                    "maxPrice": "300",
                    "minPrice": "0.0001",
                    "tickSize": "0.0001"
                },
                {
                    "filterType": "LOT_SIZE",
                    "maxQty": "10000000",
                    "minQty": "1",
                    "stepSize": "1"
                },
                {
                    "filterType": "MARKET_LOT_SIZE",
                    "maxQty": "590119",
                    "minQty": "1",
                    "stepSize": "1"
                },
                {
                    "filterType": "MAX_NUM_ORDERS",
                    "limit": 200
                },
                {
                    "filterType": "MIN_NOTIONAL",
                    "notional": "5.0"
                },
                {
                    "filterType": "PERCENT_PRICE",
                    "multiplierUp": "1.1500",
                    "multiplierDown": "0.8500",
                    "multiplierDecimal": "4"
                }
            ],
            "OrderType": [
                "LIMIT",
                "MARKET",
                "STOP",
                "STOP_MARKET",
                "TAKE_PROFIT",
                "TAKE_PROFIT_MARKET",
                "TRAILING_STOP_MARKET"
            ],
            "timeInForce": [
                "GTC",
                "IOC",
                "FOK",
                "GTX"
            ],
            "liquidationFee": "0.010000",
            "marketTakeBound": "0.30"
        }
    ],
    "timezone": "UTC"
}
```

**模型定义**：
```python
class BinanceFuturesExchangeInfoRateLimitModel(BaseModel):
    """期货交易所信息 - 频率限制子模型"""

    interval: str = Field(description="限流间隔")
    interval_num: int = Field(alias="intervalNum", description="间隔数量")
    limit: int = Field(description="限制数量")
    rate_limit_type: str = Field(alias="rateLimitType", description="限流类型")


class BinanceFuturesExchangeInfoAssetModel(BaseModel):
    """期货交易所信息 - 资产子模型"""

    asset: str = Field(description="资产名称")
    margin_available: bool = Field(
        alias="marginAvailable", description="是否可用作保证金"
    )
    auto_asset_exchange: str | None = Field(
        alias="autoAssetExchange", description="自动兑换阈值"
    )


class BinanceFuturesExchangeInfoSymbolFilterModel(BaseModel):
    """期货交易所信息 - Symbol过滤器子模型（基类）"""

    filter_type: str = Field(alias="filterType", description="过滤器类型")


class BinanceFuturesExchangeInfoSymbolModel(BaseModel):
    """期货交易所信息 - 交易对子模型"""

    symbol: str = Field(description="交易对")
    pair: str = Field(description="交易对名称")
    contract_type: str = Field(alias="contractType", description="合约类型")
    delivery_date: int = Field(alias="deliveryDate", description="交割日期")
    onboard_date: int = Field(alias="onboardDate", description="上线日期")
    status: str = Field(description="交易对状态")
    maint_margin_percent: str = Field(
        alias="maintMarginPercent", description="维持保证金比例（已废弃）"
    )
    required_margin_percent: str = Field(
        alias="requiredMarginPercent", description="所需保证金比例（已废弃）"
    )
    base_asset: str = Field(alias="baseAsset", description="基础资产")
    quote_asset: str = Field(alias="quoteAsset", description="报价资产")
    margin_asset: str = Field(alias="marginAsset", description="保证金资产")
    price_precision: int = Field(alias="pricePrecision", description="价格精度（请勿用作tickSize）")
    quantity_precision: int = Field(
        alias="quantityPrecision", description="数量精度（请勿用作stepSize）"
    )
    base_asset_precision: int = Field(alias="baseAssetPrecision", description="基础资产精度")
    quote_precision: int = Field(alias="quotePrecision", description="报价精度")
    underlying_type: str = Field(alias="underlyingType", description="底层资产类型")
    underlying_sub_type: list[str] = Field(
        alias="underlyingSubType", description="底层资产子类型"
    )
    settle_plan: int = Field(alias="settlePlan", description="结算计划")
    trigger_protect: str = Field(
        alias="triggerProtect", description="触发保护阈值"
    )
    filters: list[dict] = Field(description="过滤器列表")
    order_type: list[str] = Field(
        alias="OrderType", description="订单类型列表"
    )
    time_in_force: list[str] = Field(
        alias="timeInForce", description="有效期限列表"
    )
    liquidation_fee: str = Field(
        alias="liquidationFee", description="强平手续费率"
    )
    market_take_bound: str = Field(
        alias="marketTakeBound", description="市场单最大价格偏离比例"
    )


class BinanceFuturesExchangeInfoGetModel(SnakeCaseModel):
    """期货交易所信息 GET 响应模型

    接口: GET /fapi/v1/exchangeInfo
    """

    exchange_filters: list[dict] = Field(
        alias="exchangeFilters", description="交易所过滤器列表"
    )
    rate_limits: list[BinanceFuturesExchangeInfoRateLimitModel] = Field(
        alias="rateLimits", description="频率限制列表"
    )
    server_time: int = Field(alias="serverTime", description="服务器时间")
    assets: list[BinanceFuturesExchangeInfoAssetModel] = Field(description="资产列表")
    symbols: list[BinanceFuturesExchangeInfoSymbolModel] = Field(description="交易对列表")
    timezone: str = Field(description="时区")

    model_config = ConfigDict(populate_by_name=True)
```

---


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

**模型定义**：
```python
class BinanceSpotExecutionReportWSModel(BaseModel):
    """现货订单执行报告 WS 事件模型

    Stream: User Data Stream executionReport 事件
    """

    subscription_id: int = Field(alias="subscriptionId", description="订阅 ID")
    event: "BinanceSpotExecutionReportEvent" = Field(description="事件内容")


class BinanceSpotExecutionReportEvent(BaseModel):
    """现货订单执行报告事件内容模型"""

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    symbol: str = Field(alias="s", description="交易对")
    client_order_id: str = Field(alias="c", description="客户端订单 ID")
    side: str = Field(alias="S", description="订单方向")
    order_type: str = Field(alias="o", description="订单类型")
    time_in_force: str = Field(alias="f", description="有效期限")
    order_quantity: Decimal = Field(alias="q", description="订单数量")
    order_price: Decimal = Field(alias="p", description="订单价格")
    stop_price: Decimal = Field(alias="P", description="止损价格")
    iceberg_quantity: Decimal = Field(alias="F", description="冰山数量")
    order_list_id: int = Field(alias="g", description="订单列表 ID")
    original_client_order_id: str = Field(
        alias="C", description="原始客户端订单 ID（用于取消）"
    )
    execution_type: str = Field(alias="x", description="当前执行类型")
    order_status: str = Field(alias="X", description="当前订单状态")
    order_reject_reason: str = Field(alias="r", description="订单拒绝原因")
    order_id: int = Field(alias="i", description="订单 ID")
    last_executed_quantity: Decimal = Field(alias="l", description="最近执行数量")
    cumulative_filled_quantity: Decimal = Field(alias="z", description="累计成交数量")
    last_executed_price: Decimal = Field(alias="L", description="最近执行价格")
    commission_amount: Decimal = Field(alias="n", description="手续费金额")
    commission_asset: str | None = Field(alias="N", description="手续费资产")
    transaction_time: int = Field(alias="T", description="成交时间")
    trade_id: int = Field(alias="t", description="成交 ID")
    prevented_match_id: int = Field(alias="v", description="防止匹配 ID")
    execution_id: int = Field(alias="I", description="执行 ID")
    is_on_book: bool = Field(alias="w", description="订单是否在簿上")
    is_maker: bool = Field(alias="m", description="是否为做市商")
    ignore: bool = Field(alias="M", description="忽略字段")
    order_creation_time: int = Field(alias="O", description="订单创建时间")
    cumulative_quote_asset_qty: Decimal = Field(
        alias="Z", description="累计成交 quote 资产数量"
    )
    last_quote_asset_qty: Decimal = Field(
        alias="Y", description="最近成交 quote 资产数量"
    )
    quote_order_quantity: Decimal = Field(alias="Q", description="Quote 订单数量")
    working_time: int = Field(alias="W", description="工作时间")
    self_trade_prevention_mode: str = Field(
        alias="V", description="自成交预防模式"
    )
    # --- 条件字段（仅在特定条件下出现）---
    trailing_delta: int | None = Field(default=None, alias="d", description="追踪止损 Delta（仅追踪止损订单）")
    trailing_time: int | None = Field(default=None, alias="D", description="追踪止损时间（仅追踪止损订单）")
    strategy_id: int | None = Field(default=None, alias="j", description="策略 ID（设置了 strategyId 参数时）")
    strategy_type: int | None = Field(default=None, alias="J", description="策略类型（设置了 strategyType 参数时）")
    prevented_quantity: Decimal | None = Field(default=None, alias="A", description="防止匹配数量（订单因 STP 过期时）")
    last_prevented_quantity: Decimal | None = Field(default=None, alias="B", description="上次防止匹配数量（订单因 STP 过期时）")
    trade_group_id: int | None = Field(default=None, alias="u", description="交易组 ID")
    counter_order_id: int | None = Field(default=None, alias="U", description="对手方订单 ID")
    counter_symbol: str | None = Field(default=None, alias="Cs", description="对手方交易对")
    prevented_execution_quantity: Decimal | None = Field(default=None, alias="pl", description="防止执行数量")
    prevented_execution_price: Decimal | None = Field(default=None, alias="pL", description="防止执行价格")
    prevented_execution_quote_qty: Decimal | None = Field(default=None, alias="pY", description="防止执行 Quote 数量")
    match_type: str | None = Field(default=None, alias="b", description="匹配类型（有分配时）")
    allocation_id: int | None = Field(default=None, alias="a", description="分配 ID")
    working_floor: str | None = Field(default=None, alias="k", description="工作 floor（有分配时）")
    used_sor: bool | None = Field(default=None, alias="uS", description="是否使用 SOR")
    pegged_price_type: str | None = Field(default=None, alias="gP", description="挂钩价格类型（仅挂钩订单）")
    pegged_offset_type: str | None = Field(default=None, alias="gOT", description="挂钩偏移类型")
    pegged_offset_value: int | None = Field(default=None, alias="gOV", description="挂钩偏移值")
    pegged_price: str | None = Field(default=None, alias="gp", description="挂钩价格（仅挂钩订单）")

    model_config = ConfigDict(populate_by_name=True)
```

---

## 4. 现货（SPOT）账户与订单数据模型

### 4.1 现货账户信息 GET

**接口**: `GET /api/v3/account`
**文档来源**: `binance_spot_docs/01_REST API/Account Endpoints.md`

**响应格式**：
```json
{
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
        }
    ],
    "permissions": ["SPOT"],
    "uid": 354937868
}
```

**模型定义**：
```python
class BinanceSpotAccountCommissionRateModel(BaseModel):
    """现货账户手续费率子模型"""

    maker: str = Field(description="Maker 手续费率")
    taker: str = Field(description="Taker 手续费率")
    buyer: str = Field(description="买方手续费率")
    seller: str = Field(description="卖方手续费率")


class BinanceSpotAccountBalanceModel(BaseModel):
    """现货账户余额子模型"""

    asset: str = Field(description="资产名称")
    free: str = Field(description="可用余额")
    locked: str = Field(description="锁定余额")


class BinanceSpotAccountGetModel(SnakeCaseModel):
    """现货账户信息 GET 响应模型

    接口: GET /api/v3/account
    """

    maker_commission: int = Field(alias="makerCommission", description="Maker 手续费")
    taker_commission: int = Field(alias="takerCommission", description="Taker 手续费")
    buyer_commission: int = Field(alias="buyerCommission", description="买方手续费")
    seller_commission: int = Field(alias="sellerCommission", description="卖方手续费")
    commission_rates: BinanceSpotAccountCommissionRateModel = Field(
        alias="commissionRates", description="手续费率"
    )
    can_trade: bool = Field(alias="canTrade", description="是否可交易")
    can_withdraw: bool = Field(alias="canWithdraw", description="是否可提现")
    can_deposit: bool = Field(alias="canDeposit", description="是否可充值")
    brokered: bool = Field(description="是否经纪商")
    require_self_trade_prevention: bool = Field(
        alias="requireSelfTradePrevention", description="是否需要自成交预防"
    )
    prevent_sor: bool = Field(alias="preventSor", description="是否阻止 SOR")
    update_time: int = Field(alias="updateTime", description="最后更新时间")
    account_type: str = Field(alias="accountType", description="账户类型")
    balances: list[BinanceSpotAccountBalanceModel] = Field(
        description="账户余额列表"
    )
    permissions: list[str] = Field(description="账户权限列表")
    uid: int | None = Field(default=None, description="用户 ID（部分账户返回）")

    model_config = ConfigDict(populate_by_name=True)
```

---

### 4.3 现货账户持仓变化 WS

**Stream**: User Data Stream `outboundAccountPosition` 事件
**文档来源**: `binance_spot_docs/User Data Stream.md`

**响应格式**：
```json
{
    "subscriptionId": 0,
    "event": {
        "e": "outboundAccountPosition",
        "E": 1564034571105,
        "u": 1564034571073,
        "B": [
            {
                "a": "ETH",
                "f": "10000.000000",
                "l": "0.000000"
            }
        ]
    }
}
```

**模型定义**：
```python
class BinanceSpotAccountPositionBalanceModel(BaseModel):
    """现货账户持仓 - 余额子模型"""

    asset: str = Field(alias="a", description="资产名称")
    free: Decimal = Field(alias="f", description="可用余额")
    locked: Decimal = Field(alias="l", description="锁定余额")


class BinanceSpotOutboundAccountPositionEvent(BaseModel):
    """现货账户持仓变化事件内容模型"""

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    last_update_time: int = Field(alias="u", description="最后更新时间")
    balances: list[BinanceSpotAccountPositionBalanceModel] = Field(
        alias="B", description="余额列表"
    )


class BinanceSpotOutboundAccountPositionWSModel(BaseModel):
    """现货账户持仓变化 WS 事件模型

    Stream: User Data Stream outboundAccountPosition 事件
    """

    subscription_id: int = Field(alias="subscriptionId", description="订阅 ID")
    event: BinanceSpotOutboundAccountPositionEvent = Field(description="事件内容")

    model_config = ConfigDict(populate_by_name=True)
```

---

### 4.4 现货余额更新 WS

**Stream**: User Data Stream `balanceUpdate` 事件
**文档来源**: `binance_spot_docs/User Data Stream.md`

**响应格式**：
```json
{
    "subscriptionId": 0,
    "event": {
        "e": "balanceUpdate",
        "E": 1573200697110,
        "a": "BTC",
        "d": "100.00000000",
        "T": 1573200697068
    }
}
```

**模型定义**：
```python
class BinanceSpotBalanceUpdateEvent(BaseModel):
    """现货余额更新事件内容模型"""

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    asset: str = Field(alias="a", description="资产名称")
    balance_delta: Decimal = Field(alias="d", description="余额变动")
    clear_time: int = Field(alias="T", description="清算时间")


class BinanceSpotBalanceUpdateWSModel(BaseModel):
    """现货余额更新 WS 事件模型

    Stream: User Data Stream balanceUpdate 事件
    """

    subscription_id: int = Field(alias="subscriptionId", description="订阅 ID")
    event: BinanceSpotBalanceUpdateEvent = Field(description="事件内容")

    model_config = ConfigDict(populate_by_name=True)
```

---

### 4.5 现货事件流终止 WS

**Stream**: User Data Stream `eventStreamTerminated` 事件
**文档来源**: `binance_spot_docs/User Data Stream.md`

**响应格式**：
```json
{
    "subscriptionId": 0,
    "event": {
        "e": "eventStreamTerminated",
        "E": 1728973001334
    }
}
```

**模型定义**：
```python
class BinanceSpotEventStreamTerminatedEvent(BaseModel):
    """现货事件流终止事件内容模型"""

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")


class BinanceSpotEventStreamTerminatedWSModel(BaseModel):
    """现货事件流终止 WS 事件模型

    Stream: User Data Stream eventStreamTerminated 事件
    """

    subscription_id: int = Field(alias="subscriptionId", description="订阅 ID")
    event: BinanceSpotEventStreamTerminatedEvent = Field(description="事件内容")

    model_config = ConfigDict(populate_by_name=True)
```

---

### 4.6 现货订单列表状态 WS

**Stream**: User Data Stream `listStatus` 事件
**文档来源**: `binance_spot_docs/User Data Stream.md`

**响应格式**：
```json
{
    "subscriptionId": 0,
    "event": {
        "e": "listStatus",
        "E": 1564035303637,
        "s": "ETHBTC",
        "g": 2,
        "c": "OCO",
        "l": "EXEC_STARTED",
        "L": "EXECUTING",
        "r": "NONE",
        "C": "F4QN4G8DlFATFlIUQ0cjdD",
        "T": 1564035303625,
        "O": [
            {
                "s": "ETHBTC",
                "i": 17,
                "c": "AJYsMjErWJesZvqlJCTUgL"
            },
            {
                "s": "ETHBTC",
                "i": 18,
                "c": "bfYPSQdLoqAJeNrOr9adzq"
            }
        ]
    }
}
```

**模型定义**：
```python
class BinanceSpotListStatusOrderModel(BaseModel):
    """现货订单列表状态 - 订单子模型"""

    symbol: str = Field(alias="s", description="交易对")
    order_id: int = Field(alias="i", description="订单 ID")
    client_order_id: str = Field(alias="c", description="客户端订单 ID")


class BinanceSpotListStatusEvent(BaseModel):
    """现货订单列表状态事件内容模型"""

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    symbol: str = Field(alias="s", description="交易对")
    order_list_id: int = Field(alias="g", description="订单列表 ID")
    contingency_type: str = Field(alias="c", description=" contingency 类型")
    list_status_type: str = Field(alias="l", description="列表状态类型")
    list_order_status: str = Field(alias="L", description="列表订单状态")
    list_reject_reason: str = Field(alias="r", description="列表拒绝原因")
    list_client_order_id: str = Field(alias="C", description="列表客户端订单 ID")
    transaction_time: int = Field(alias="T", description="成交时间")
    orders: list[BinanceSpotListStatusOrderModel] = Field(
        alias="O", description="订单列表"
    )


class BinanceSpotListStatusWSModel(BaseModel):
    """现货订单列表状态 WS 事件模型

    Stream: User Data Stream listStatus 事件
    """

    subscription_id: int = Field(alias="subscriptionId", description="订阅 ID")
    event: BinanceSpotListStatusEvent = Field(description="事件内容")

    model_config = ConfigDict(populate_by_name=True)
```

---

### 4.7 现货外部锁定更新 WS

**Stream**: User Data Stream `externalLockUpdate` 事件
**文档来源**: `binance_spot_docs/User Data Stream.md`

**响应格式**：
```json
{
    "subscriptionId": 0,
    "event": {
        "e": "externalLockUpdate",
        "E": 1581557507324,
        "a": "NEO",
        "d": "10.00000000",
        "T": 1581557507268
    }
}
```

**模型定义**：
```python
class BinanceSpotExternalLockUpdateEvent(BaseModel):
    """现货外部锁定更新事件内容模型"""

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    asset: str = Field(alias="a", description="资产名称")
    delta: Decimal = Field(alias="d", description="变动数量")
    transaction_time: int = Field(alias="T", description="交易时间")


class BinanceSpotExternalLockUpdateWSModel(BaseModel):
    """现货外部锁定更新 WS 事件模型

    Stream: User Data Stream externalLockUpdate 事件
    """

    subscription_id: int = Field(alias="subscriptionId", description="订阅 ID")
    event: BinanceSpotExternalLockUpdateEvent = Field(description="事件内容")

    model_config = ConfigDict(populate_by_name=True)
```

---

### 4.8 现货订单执行报告 WS

**Stream**: User Data Stream `executionReport` 事件
**文档来源**: `binance_spot_docs/User Data Stream.md`

**响应格式**：
```json
{
    "subscriptionId": 0,
    "event": {
        "e": "executionReport",


## 5. 期货（FUTURES）账户与订单数据模型

### 5.1 期货账户信息 GET

**接口**: `GET /fapi/v3/account`
**文档来源**: `binance_futures_docs/01_U本位合约/02_账户接口/03_REST API/账户信息V3(USER-DATA).md`

**响应格式**（single-asset mode）：
```json
{
    "totalInitialMargin": "0.00000000",
    "totalMaintMargin": "0.00000000",
    "totalWalletBalance": "103.12345678",
    "totalUnrealizedProfit": "0.00000000",
    "totalMarginBalance": "103.12345678",
    "totalPositionInitialMargin": "0.00000000",
    "totalOpenOrderInitialMargin": "0.00000000",
    "totalCrossWalletBalance": "103.12345678",
    "totalCrossUnPnl": "0.00000000",
    "availableBalance": "103.12345678",
    "maxWithdrawAmount": "103.12345678",
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
            "updateTime": 1625474304765
        }
    ],
    "positions": [
        {
            "symbol": "BTCUSDT",
            "positionSide": "BOTH",
            "positionAmt": "1.000",
            "unrealizedProfit": "0.00000000",
            "isolatedMargin": "0.00000000",
            "notional": "0",
            "isolatedWallet": "0",
            "initialMargin": "0",
            "maintMargin": "0",
            "updateTime": 0
        }
    ]
}
```

**模型定义**：
```python
class BinanceFuturesAccountAssetModel(BaseModel):
    """期货账户资产子模型"""

    asset: str = Field(description="资产名称")
    wallet_balance: Decimal = Field(alias="walletBalance", description="钱包余额")
    unrealized_profit: Decimal = Field(alias="unrealizedProfit", description="未实现盈亏")
    margin_balance: Decimal = Field(alias="marginBalance", description="保证金余额")
    maint_margin: Decimal = Field(alias="maintMargin", description="维持保证金")
    initial_margin: Decimal = Field(alias="initialMargin", description="总初始保证金")
    position_initial_margin: Decimal = Field(
        alias="positionInitialMargin", description="持仓初始保证金"
    )
    open_order_initial_margin: Decimal = Field(
        alias="openOrderInitialMargin", description="挂单初始保证金"
    )
    cross_wallet_balance: Decimal = Field(
        alias="crossWalletBalance", description="跨账户钱包余额"
    )
    cross_un_pnl: Decimal = Field(alias="crossUnPnl", description="跨账户未实现盈亏")
    available_balance: Decimal = Field(alias="availableBalance", description="可用余额")
    max_withdraw_amount: Decimal = Field(
        alias="maxWithdrawAmount", description="最大可转出数量"
    )
    update_time: int = Field(alias="updateTime", description="最后更新时间")


class BinanceFuturesAccountPositionModel(BaseModel):
    """期货账户持仓子模型"""

    symbol: str = Field(description="交易对")
    position_side: str = Field(alias="positionSide", description="持仓方向")
    position_amt: Decimal = Field(alias="positionAmt", description="持仓数量")
    unrealized_profit: Decimal = Field(alias="unrealizedProfit", description="未实现盈亏")
    isolated_margin: Decimal = Field(alias="isolatedMargin", description="逐仓保证金")
    notional: Decimal = Field(description="名义价值")
    isolated_wallet: Decimal = Field(alias="isolatedWallet", description="逐仓钱包")
    initial_margin: Decimal = Field(alias="initialMargin", description="初始保证金")
    maint_margin: Decimal = Field(alias="maintMargin", description="维持保证金")
    update_time: int = Field(alias="updateTime", description="最后更新时间")


class BinanceFuturesAccountGetModel(SnakeCaseModel):
    """期货账户信息 GET 响应模型

    接口: GET /fapi/v3/account
    """

    total_initial_margin: Decimal = Field(
        alias="totalInitialMargin", description="总初始保证金"
    )
    total_maint_margin: Decimal = Field(
        alias="totalMaintMargin", description="总维持保证金"
    )
    total_wallet_balance: Decimal = Field(
        alias="totalWalletBalance", description="总钱包余额"
    )
    total_unrealized_profit: Decimal = Field(
        alias="totalUnrealizedProfit", description="总未实现盈亏"
    )
    total_margin_balance: Decimal = Field(
        alias="totalMarginBalance", description="总保证金余额"
    )
    total_position_initial_margin: Decimal = Field(
        alias="totalPositionInitialMargin", description="总持仓初始保证金"
    )
    total_open_order_initial_margin: Decimal = Field(
        alias="totalOpenOrderInitialMargin", description="总挂单初始保证金"
    )
    total_cross_wallet_balance: Decimal = Field(
        alias="totalCrossWalletBalance", description="总跨账户钱包余额"
    )
    total_cross_un_pnl: Decimal = Field(
        alias="totalCrossUnPnl", description="总跨账户未实现盈亏"
    )
    available_balance: Decimal = Field(
        alias="availableBalance", description="可用余额"
    )
    max_withdraw_amount: Decimal = Field(
        alias="maxWithdrawAmount", description="最大可转出数量"
    )
    assets: list[BinanceFuturesAccountAssetModel] = Field(description="资产列表")
    positions: list[BinanceFuturesAccountPositionModel] = Field(description="持仓列表")

    model_config = ConfigDict(populate_by_name=True)
```

---

### 5.2 期货订单成交更新 WS

**Stream**: User Data Stream `ORDER_TRADE_UPDATE` 事件
**文档来源**: `binance_futures_docs/01_U本位合约/02_Websocket账户信息推送/订单交易更新推送.md`

**响应格式**：
```json
{
    "e": "ORDER_TRADE_UPDATE",
    "E": 1568879465651,
    "T": 1568879465650,
    "o": {
        "s": "BTCUSDT",
        "c": "TEST",
        "S": "SELL",
        "o": "TRAILING_STOP_MARKET",
        "f": "GTC",
        "q": "0.001",
        "p": "0",
        "ap": "0",
        "sp": "7103.04",
        "x": "NEW",
        "X": "NEW",
        "i": 8886774,
        "l": "0",
        "z": "0",
        "L": "0",
        "N": "USDT",
        "n": "0",
        "T": 1568879465650,
        "t": 0,
        "b": "0",
        "a": "9.91",
        "m": false,
        "R": false,
        "wt": "CONTRACT_PRICE",
        "ot": "TRAILING_STOP_MARKET",
        "ps": "LONG",
        "cp": false,
        "AP": "7476.89",
        "cr": "5.0",
        "pP": false,
        "si": 0,
        "ss": 0,
        "rp": "0",
        "V": "EXPIRE_TAKER",
        "pm": "OPPONENT",
        "gtd": 0,
        "er": "0"
    }
}
```

**模型定义**：
```python
class BinanceFuturesOrderDataModel(BaseModel):
    """期货订单数据子模型"""

    symbol: str = Field(alias="s", description="交易对")
    client_order_id: str = Field(alias="c", description="客户端订单 ID")
    side: str = Field(alias="S", description="订单方向")
    order_type: str = Field(alias="o", description="订单类型")
    time_in_force: str = Field(alias="f", description="有效期限")
    original_quantity: Decimal = Field(alias="q", description="原始数量")
    original_price: Decimal = Field(alias="p", description="原始价格")
    average_price: Decimal = Field(alias="ap", description="平均价格")
    stop_price: Decimal = Field(alias="sp", description="止损价格")
    execution_type: str = Field(alias="x", description="执行类型")
    order_status: str = Field(alias="X", description="订单状态")
    order_id: int = Field(alias="i", description="订单 ID")
    order_last_filled_qty: Decimal = Field(alias="l", description="订单最近成交数量")
    order_filled_accumulated_qty: Decimal = Field(
        alias="z", description="订单累计成交数量"
    )
    last_filled_price: Decimal = Field(alias="L", description="最近成交价格")
    commission_asset: str = Field(alias="N", description="手续费资产")
    commission: Decimal = Field(alias="n", description="手续费金额")
    order_trade_time: int = Field(alias="T", description="订单成交时间")
    trade_id: int = Field(alias="t", description="成交 ID")
    bids_notional: Decimal = Field(alias="b", description="Bid 订单名义价值")
    ask_notional: Decimal = Field(alias="a", description="Ask 订单名义价值")
    is_maker: bool = Field(alias="m", description="是否为做市商")
    is_reduce_only: bool = Field(alias="R", description="是否为只减仓")
    stop_price_working_type: str = Field(alias="wt", description="止损价格工作类型")
    original_order_type: str = Field(alias="ot", description="原始订单类型")
    position_side: str = Field(alias="ps", description="持仓方向")
    if_close_all: bool = Field(alias="cp", description="是否全平")
    activation_price: Decimal = Field(alias="AP", description="激活价格")
    callback_rate: Decimal = Field(alias="cr", description="回调率")
    if_price_protect: bool = Field(alias="pP", description="是否开启价格保护")
    ignore_1: int = Field(alias="si", description="忽略字段")
    ignore_2: int = Field(alias="ss", description="忽略字段")
    realized_profit: Decimal = Field(alias="rp", description="已实现盈亏")
    stp_mode: str = Field(alias="V", description="自成交预防模式")
    price_match_mode: str = Field(alias="pm", description="价格匹配模式")
    tif_gtd_order_auto_cancel_time: int = Field(
        alias="gtd", description="GTD 订单自动取消时间"
    )
    expiry_reason: str = Field(alias="er", description="过期原因")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesOrderTradeUpdateWSModel(BaseModel):
    """期货订单成交更新 WS 事件模型

    Stream: User Data Stream ORDER_TRADE_UPDATE 事件
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    transaction_time: int = Field(alias="T", description="交易时间")
    order_data: BinanceFuturesOrderDataModel = Field(alias="o", description="订单数据")

    model_config = ConfigDict(populate_by_name=True)
```

---

### 5.3 期货账户更新 WS

**Stream**: User Data Stream `ACCOUNT_UPDATE` 事件
**文档来源**: `binance_futures_docs/01_U本位合约/02_Websocket账户信息推送/Balance和Position更新推送.md`

**响应格式**：
```json
{
    "e": "ACCOUNT_UPDATE",
    "E": 1564745798939,
    "T": 1564745798938,
    "a": {
        "m": "ORDER",
        "B": [
            {
                "a": "USDT",
                "wb": "122624.12345678",
                "cw": "100.12345678",
                "bc": "50.12345678"
            }
        ],
        "P": [
            {
                "s": "BTCUSDT",
                "pa": "0",
                "ep": "0.00000",
                "bep": "0",
                "cr": "200",
                "up": "0",
                "mt": "isolated",
                "iw": "0.00000000",
                "ps": "BOTH"
            }
        ]
    }
}
```

**模型定义**：
```python
class BinanceFuturesAccountUpdateBalanceModel(BaseModel):
    """期货账户更新 - 余额子模型"""

    asset: str = Field(alias="a", description="资产名称")
    wallet_balance: Decimal = Field(alias="wb", description="钱包余额")
    cross_wallet_balance: Decimal = Field(alias="cw", description="跨账户钱包余额")
    balance_change: Decimal = Field(alias="bc", description="余额变动（不含盈亏和手续费）")


class BinanceFuturesAccountUpdatePositionModel(BaseModel):
    """期货账户更新 - 持仓子模型"""

    symbol: str = Field(alias="s", description="交易对")
    position_amt: Decimal = Field(alias="pa", description="持仓数量")
    entry_price: Decimal = Field(alias="ep", description="入场价格")
    break_even_price: Decimal = Field(alias="bep", description="盈亏平衡价格")
    accumulated_realized: Decimal = Field(alias="cr", description="累计已实现盈亏（费前）")
    unrealized_profit: Decimal = Field(alias="up", description="未实现盈亏")
    margin_type: str = Field(alias="mt", description="保证金类型")
    isolated_wallet: Decimal = Field(alias="iw", description="逐仓钱包余额")
    position_side: str = Field(alias="ps", description="持仓方向")


class BinanceFuturesAccountUpdateDataModel(BaseModel):
    """期货账户更新 - 更新数据子模型"""

    update_reason: str = Field(alias="m", description="更新原因类型")
    balances: list[BinanceFuturesAccountUpdateBalanceModel] = Field(
        alias="B", description="余额列表"
    )
    positions: list[BinanceFuturesAccountUpdatePositionModel] = Field(
        alias="P", description="持仓列表"
    )


class BinanceFuturesAccountUpdateWSModel(BaseModel):
    """期货账户更新 WS 事件模型

    Stream: User Data Stream ACCOUNT_UPDATE 事件
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    transaction_time: int = Field(alias="T", description="交易时间")
    update_data: BinanceFuturesAccountUpdateDataModel = Field(
        alias="a", description="更新数据"
    )

    model_config = ConfigDict(populate_by_name=True)
```

---

## 6. WebSocket 交易 API 模型

> **日期**: 2026-03-21
> **新增**: 币安 WebSocket 交易 API 的请求/响应模型

### 6.1 通用 WebSocket 响应模型

所有币安 WebSocket API 响应都遵循统一的格式：

**响应格式**：
```json
{
    "id": "e2a85d9f-07a5-4f94-8d5f-789dc3deb097",
    "status": 200,
    "result": { ... },
    "error": null,
    "rateLimits": [ ... ]
}
```

**模型定义**：
```python
class WSResponse(BaseModel):
    """WebSocket 通用响应模型

    用于解析所有币安 WebSocket API 的响应。
    成功响应: status=200, result有值, error=None
    失败响应: status!=200, result=None, error有值
    """

    id: int | str = Field(description="请求 ID，与请求中的 id 对应")
    status: int = Field(description="响应状态码 (200=成功, 400=失败)")
    result: dict | list | None = Field(default=None, description="成功时的结果数据")
    error: dict | None = Field(default=None, description="失败时的错误信息")
    rate_limits: list[dict] | None = Field(
        default=None, alias="rateLimits", description="速率限制信息"
    )

    model_config = ConfigDict(populate_by_name=True)
```

---

### 6.2 现货（SPOT）WebSocket 交易模型

#### 6.2.1 现货订单下单请求

**方法**: `order.place`
**文档来源**: `binance_spot_docs/01_WebSocket API/Trading requests.md`

**请求格式**：
```json
{
    "id": "56374a46-3061-486b-a311-99ee972eb648",
    "method": "order.place",
    "params": {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "LIMIT",
        "timeInForce": "GTC",
        "price": "0.1",
        "quantity": "10"
    }
}
```

**模型定义**：
```python
class BinanceSpotWsOrderRequest(BaseModel):
    """现货订单下单请求模型

    注意：apiKey, timestamp, signature 由客户端在构建参数时自动添加
    """

    symbol: str = Field(alias="symbol", description="交易对")
    side: str = Field(alias="side", description="订单方向 BUY/SELL")
    order_type: str = Field(alias="type", description="订单类型")
    quantity: float = Field(alias="quantity", description="订单数量")
    price: Optional[float] = Field(default=None, alias="price", description="订单价格")
    time_in_force: Optional[str] = Field(
        default=None, alias="timeInForce", description="有效期限 GTC/IOC/FOK"
    )
    stop_price: Optional[float] = Field(
        default=None, alias="stopPrice", description="止损价格"
    )
    quote_order_qty: Optional[float] = Field(
        default=None, alias="quoteOrderQty", description="Quote 订单数量"
    )
    iceberg_qty: Optional[float] = Field(
        default=None, alias="icebergQty", description="冰山数量"
    )
    new_client_order_id: Optional[str] = Field(
        default=None, alias="newClientOrderId", description="客户端订单 ID"
    )
    new_order_resp_type: Optional[str] = Field(
        default=None, alias="newOrderRespType", description="响应类型 ACK/RESULT/FULL"
    )
    self_trade_prevention_mode: Optional[str] = Field(
        default=None, alias="selfTradePreventionMode", description="自成交预防模式"
    )
    trailing_delta: Optional[int] = Field(
        default=None, alias="trailingDelta", description="追踪止损 Delta"
    )
    strategy_id: Optional[int] = Field(
        default=None, alias="strategyId", description="策略 ID"
    )
    strategy_type: Optional[int] = Field(
        default=None, alias="strategyType", description="策略类型"
    )
    peg_price_type: Optional[str] = Field(
        default=None, alias="pegPriceType", description="挂钩价格类型"
    )
    peg_offset_value: Optional[int] = Field(
        default=None, alias="pegOffsetValue", description="挂钩偏移值"
    )
    peg_offset_type: Optional[str] = Field(
        default=None, alias="pegOffsetType", description="挂钩偏移类型"
    )
    recv_window: Optional[int] = Field(
        default=None, alias="recvWindow", description="接收窗口"
    )
    # 认证参数（由客户端自动添加）
    api_key: Optional[str] = Field(default=None, alias="apiKey", description="API Key")
    timestamp: Optional[int] = Field(default=None, alias="timestamp", description="时间戳")
    signature: Optional[str] = Field(default=None, alias="signature", description="签名")

    model_config = ConfigDict(populate_by_name=True)
```

#### 6.2.2 现货订单下单响应

**方法**: `order.place`
**文档来源**: `binance_spot_docs/01_WebSocket API/Trading requests.md`

**响应格式**：
```json
{
    "id": "e2a85d9f-07a5-4f94-8d5f-789dc3deb097",
    "status": 200,
    "result": {
        "symbol": "BTCUSDT",
        "orderId": 12510053279,
        "orderListId": -1,
        "clientOrderId": "a097fe6304b20a7e4fc436",
        "transactTime": 1655716096505,
        "price": "0.10000000",
        "origQty": "10.00000000",
        "executedQty": "0.00000000",
        "cummulativeQuoteQty": "0.00000000",
        "status": "NEW",
        "timeInForce": "GTC",
        "type": "LIMIT",
        "side": "BUY",
        "workingTime": 1655716096505,
        "selfTradePreventionMode": "NONE",
        "fills": [
            {
                "price": "0.10000000",
                "qty": "1.00000000",
                "commission": "0.00000000",
                "commissionAsset": "BNB"
            }
        ]
    }
}
```

**说明**: `fills` 字段取决于 `newOrderRespType` 参数：
- `ACK` - 不包含 fills
- `RESULT` - 不包含 fills
- `FULL` - 包含 fills（立即成交的成交明细列表）

**模型定义**：
```python
class BinanceSpotFillModel(BaseModel):
    """现货成交明细模型"""

    price: str = Field(description="成交价格")
    qty: str = Field(description="成交数量")
    commission: str = Field(description="手续费金额")
    commission_asset: str = Field(alias="commissionAsset", description="手续费资产")
    trade_id: int = Field(alias="tradeId", description="成交 ID")
    # SOR 订单特有字段
    match_type: Optional[str] = Field(
        default=None, alias="matchType", description="匹配类型（SOR 订单）"
    )
    alloc_id: Optional[int] = Field(
        default=None, alias="allocId", description="分配 ID（SOR 订单）"
    )

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotOrderPlaceResult(BaseModel):
    """现货订单下单响应结果模型

    方法: order.place
    """

    symbol: str = Field(description="交易对")
    order_id: int = Field(alias="orderId", description="订单 ID")
    order_list_id: int = Field(alias="orderListId", description="订单列表 ID (-1 表示无)")
    client_order_id: str = Field(alias="clientOrderId", description="客户端订单 ID")
    transact_time: int = Field(alias="transactTime", description="成交时间")
    price: str = Field(description="订单价格")
    orig_qty: str = Field(alias="origQty", description="原始数量")
    executed_qty: str = Field(alias="executedQty", description="已成交数量")
    cummulative_quote_qty: str = Field(
        alias="cummulativeQuoteQty", description="累计 Quote 成交数量"
    )
    status: str = Field(description="订单状态 (NEW/FILLED/PARTIALLY_FILLED/CANCELED/...)")
    time_in_force: str = Field(alias="timeInForce", description="有效期限 (GTC/IOC/FOK)")
    order_type: str = Field(alias="type", description="订单类型")
    side: str = Field(description="订单方向 (BUY/SELL)")
    working_time: int = Field(alias="workingTime", description="工作时间")
    self_trade_prevention_mode: str = Field(
        alias="selfTradePreventionMode", description="自成交预防模式"
    )
    fills: list[BinanceSpotFillModel] = Field(
        default_factory=list, alias="fills", description="成交明细（仅 FULL 响应类型）"
    )

    model_config = ConfigDict(populate_by_name=True)
```

#### 6.2.3 现货订单修改响应

**方法**: `order.amend.keepPriority`
**文档来源**: `binance_spot_docs/01_WebSocket API/Trading requests.md`

**响应格式**：
```json
{
    "id": "56374a46-3061-486b-a311-89ee972eb648",
    "status": 200,
    "result": {
        "transactTime": 1741923284382,
        "executionId": 16,
        "amendedOrder": {
            "symbol": "BTCUSDT",
            "orderId": 12,
            "orderListId": -1,
            "origClientOrderId": "my_test_order1",
            "clientOrderId": "4zR9HFcEq8gM1tWUqPEUHc",
            "price": "5.00000000",
            "qty": "5.00000000",
            "executedQty": "0.00000000",
            "status": "NEW",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": "BUY",
            "workingTime": 1741923284364,
            "selfTradePreventionMode": "NONE"
        }
    }
}
```

**模型定义**：
```python
class BinanceSpotAmendedOrderModel(BaseModel):
    """现货订单修改后的订单信息模型"""

    symbol: str = Field(description="交易对")
    order_id: int = Field(alias="orderId", description="订单 ID")
    order_list_id: int = Field(alias="orderListId", description="订单列表 ID")
    orig_client_order_id: str = Field(alias="origClientOrderId", description="原始客户端订单 ID")
    client_order_id: str = Field(alias="clientOrderId", description="客户端订单 ID")
    price: str = Field(description="订单价格")
    qty: str = Field(description="订单数量")
    executed_qty: str = Field(alias="executedQty", description="已成交数量")
    status: str = Field(description="订单状态")
    time_in_force: str = Field(alias="timeInForce", description="有效期限")
    order_type: str = Field(alias="type", description="订单类型")
    side: str = Field(description="订单方向")
    working_time: int = Field(alias="workingTime", description="工作时间")
    self_trade_prevention_mode: str = Field(
        alias="selfTradePreventionMode", description="自成交预防模式"
    )

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotOrderAmendResult(BaseModel):
    """现货订单修改响应结果模型

    方法: order.amend.keepPriority
    """

    transact_time: int = Field(alias="transactTime", description="成交时间")
    execution_id: int = Field(alias="executionId", description="执行 ID")
    amended_order: BinanceSpotAmendedOrderModel = Field(
        alias="amendedOrder", description="修改后的订单信息"
    )

    model_config = ConfigDict(populate_by_name=True)
```

---

### 6.3 期货（FUTURES）WebSocket 交易模型

#### 6.3.1 期货订单下单请求

**方法**: `order.place`
**文档来源**: `binance_futures_docs/01_U本位合约/02_交易接口/03_WebSocket API/下单(TRADE).md`

**请求格式**：
```json
{
    "id": "3f7df6e3-2df4-44b9-9919-d2f38f90a99a",
    "method": "order.place",
    "params": {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "LIMIT",
        "quantity": "0.1",
        "price": "43000.0",
        "timestamp": 1702654000000
    }
}
```

**模型定义**：
```python
class BinanceFuturesWsOrderRequest(BaseModel):
    """期货订单下单请求模型

    注意：apiKey, timestamp, signature 由客户端在构建参数时自动添加
    """

    symbol: str = Field(alias="symbol", description="交易对")
    side: str = Field(alias="side", description="订单方向 BUY/SELL")
    order_type: str = Field(alias="type", description="订单类型")
    quantity: float = Field(alias="quantity", description="订单数量")
    price: Optional[float] = Field(default=None, alias="price", description="订单价格")
    time_in_force: Optional[str] = Field(
        default=None, alias="timeInForce", description="有效期限 GTC/IOC/FOK"
    )
    stop_price: Optional[float] = Field(
        default=None, alias="stopPrice", description="止损价格"
    )
    reduce_only: bool = Field(default=False, alias="reduceOnly", description="是否仅减仓")
    position_side: Optional[str] = Field(
        default=None, alias="positionSide", description="持仓方向 LONG/SHORT"
    )
    new_client_order_id: Optional[str] = Field(
        default=None, alias="newClientOrderId", description="客户端订单 ID"
    )
    new_order_resp_type: Optional[str] = Field(
        default=None, alias="newOrderRespType", description="响应类型 ACK/RESULT，默认 ACK"
    )
    self_trade_prevention_mode: Optional[str] = Field(
        default=None, alias="selfTradePreventionMode", description="自成交预防模式"
    )
    good_till_date: Optional[int] = Field(
        default=None, alias="goodTillDate", description="GTD 有效期（毫秒时间戳）"
    )
    price_protect: Optional[bool] = Field(
        default=None, alias="priceProtect", description="是否开启价格保护"
    )
    working_type: Optional[str] = Field(
        default=None, alias="workingType", description="触发类型 MARK/PRICE"
    )
    callback_rate: Optional[float] = Field(
        default=None, alias="callbackRate", description="追踪止损回调率"
    )
    close_position: Optional[bool] = Field(
        default=None, alias="closePosition", description="是否全平"
    )
    activation_price: Optional[float] = Field(
        default=None, alias="activationPrice", description="激活价格（追踪止损）"
    )
    price_match: Optional[str] = Field(
        default=None, alias="priceMatch", description="价格匹配模式"
    )
    recv_window: Optional[int] = Field(
        default=None, alias="recvWindow", description="接收窗口"
    )
    # 认证参数（由客户端自动添加）
    api_key: Optional[str] = Field(default=None, alias="apiKey", description="API Key")
    timestamp: Optional[int] = Field(default=None, alias="timestamp", description="时间戳")
    signature: Optional[str] = Field(default=None, alias="signature", description="签名")

    model_config = ConfigDict(populate_by_name=True)
```

#### 6.3.2 期货订单下单响应

**方法**: `order.place`
**文档来源**: `binance_futures_docs/01_U本位合约/02_交易接口/03_WebSocket API/下单(TRADE).md`

**响应格式**：
```json
{
    "id": "3f7df6e3-2df4-44b9-9919-d2f38f90a99a",
    "status": 200,
    "result": {
        "orderId": 325078477,
        "symbol": "BTCUSDT",
        "status": "NEW",
        "clientOrderId": "iCXL1BywlBaf2sesNUrVl3",
        "price": "43187.00",
        "avgPrice": "0.00",
        "origQty": "0.100",
        "executedQty": "0.000",
        "cumQty": "0.000",
        "cumQuote": "0.00000",
        "timeInForce": "GTC",
        "type": "LIMIT",
        "reduceOnly": false,
        "closePosition": false,
        "side": "BUY",
        "positionSide": "BOTH",
        "stopPrice": "0.00",
        "workingType": "CONTRACT_PRICE",
        "priceProtect": false,
        "origType": "LIMIT",
        "priceMatch": "NONE",
        "selfTradePreventionMode": "NONE",
        "goodTillDate": 0,
        "updateTime": 1702555534435
    }
}
```

**模型定义**：
```python
class BinanceFuturesOrderPlaceResult(BaseModel):
    """期货订单下单响应结果模型

    方法: order.place
    """

    order_id: int = Field(alias="orderId", description="订单 ID")
    symbol: str = Field(description="交易对")
    status: str = Field(description="订单状态 (NEW/FILLED/PARTIALLY_FILLED/CANCELED/...)")
    client_order_id: str = Field(alias="clientOrderId", description="客户端订单 ID")
    price: str = Field(description="订单价格")
    avg_price: str = Field(alias="avgPrice", description="平均价格")
    orig_qty: str = Field(alias="origQty", description="原始数量")
    executed_qty: str = Field(alias="executedQty", description="已成交数量")
    cum_qty: str = Field(alias="cumQty", description="累计成交数量")
    cum_quote: str = Field(alias="cumQuote", description="累计成交额")
    time_in_force: str = Field(alias="timeInForce", description="有效期限")
    order_type: str = Field(alias="type", description="订单类型")
    reduce_only: bool = Field(alias="reduceOnly", description="是否仅减仓")
    close_position: bool = Field(alias="closePosition", description="是否全平")
    side: str = Field(description="订单方向")
    position_side: str = Field(alias="positionSide", description="持仓方向")
    stop_price: str = Field(alias="stopPrice", description="止损价格")
    working_type: str = Field(alias="workingType", description="工作类型")
    price_protect: bool = Field(alias="priceProtect", description="是否开启价格保护")
    orig_type: str = Field(alias="origType", description="原始订单类型")
    price_match: str = Field(alias="priceMatch", description="价格匹配模式")
    self_trade_prevention_mode: str = Field(
        alias="selfTradePreventionMode", description="自成交预防模式"
    )
    good_till_date: int = Field(alias="goodTillDate", description="有效截止日期")
    update_time: int = Field(alias="updateTime", description="更新时间")

    model_config = ConfigDict(populate_by_name=True)
```

#### 6.3.3 期货订单修改响应

**方法**: `order.modify`
**文档来源**: `binance_futures_docs/01_U本位合约/02_交易接口/03_WebSocket API/修改订单(TRADE).md`

**响应格式**：与 `order.place` 格式相同

**模型定义**：
```python
class BinanceFuturesModifyOrderResponse(BaseModel):
    """期货订单修改响应结果模型

    方法: order.modify
    响应格式与 order.place 相同
    """

    order_id: int = Field(alias="orderId", description="订单 ID")
    symbol: str = Field(description="交易对")
    status: str = Field(description="订单状态")
    client_order_id: str = Field(alias="clientOrderId", description="客户端订单 ID")
    price: str = Field(description="订单价格")
    avg_price: str = Field(alias="avgPrice", description="平均价格")
    orig_qty: str = Field(alias="origQty", description="原始数量")
    executed_qty: str = Field(alias="executedQty", description="已成交数量")
    cum_qty: str = Field(alias="cumQty", description="累计成交数量")
    cum_quote: str = Field(alias="cumQuote", description="累计成交额")
    time_in_force: str = Field(alias="timeInForce", description="有效期限")
    order_type: str = Field(alias="type", description="订单类型")
    reduce_only: bool = Field(alias="reduceOnly", description="是否仅减仓")
    close_position: bool = Field(alias="closePosition", description="是否全平")
    side: str = Field(description="订单方向")
    position_side: str = Field(alias="positionSide", description="持仓方向")
    stop_price: str = Field(alias="stopPrice", description="止损价格")
    working_type: str = Field(alias="workingType", description="工作类型")
    price_protect: bool = Field(alias="priceProtect", description="是否开启价格保护")
    orig_type: str = Field(alias="origType", description="原始订单类型")
    price_match: str = Field(alias="priceMatch", description="价格匹配模式")
    self_trade_prevention_mode: str = Field(
        alias="selfTradePreventionMode", description="自成交预防模式"
    )
    good_till_date: int = Field(alias="goodTillDate", description="有效截止日期")
    update_time: int = Field(alias="updateTime", description="更新时间")

    model_config = ConfigDict(populate_by_name=True)
```

---

## 7. 模型汇总

### 7.1 现货（SPOT）模型

| 模型类名 | 说明 |
|----------|------|
| BinanceSpotKlineGetModel | 现货 K线 GET |
| BinanceSpotKlineWSModel | 现货 K线 WS |
| BinanceSpotTicker24hrGetModel | 现货 24hr Ticker GET |
| BinanceSpotTicker24hrWSModel | 现货 24hr Ticker WS |
| BinanceSpotAccountGetModel | 现货账户信息 GET |
| BinanceSpotAccountBalanceModel | 现货账户余额子模型 |
| BinanceSpotAccountCommissionRateModel | 现货账户手续费率子模型 |
| BinanceSpotAccountPositionBalanceModel | 现货持仓余额子模型 |
| BinanceSpotOutboundAccountPositionWSModel | 现货账户持仓变化 WS |
| BinanceSpotBalanceUpdateWSModel | 现货余额更新 WS |
| BinanceSpotEventStreamTerminatedWSModel | 现货事件流终止 WS |
| BinanceSpotListStatusOrderModel | 现货订单列表状态子模型 |
| BinanceSpotListStatusWSModel | 现货订单列表状态 WS |
| BinanceSpotExternalLockUpdateWSModel | 现货外部锁定更新 WS |
| BinanceSpotExecutionReportWSModel | 现货订单执行报告 WS |
| BinanceSpotFillModel | 现货成交填充子模型 |
| BinanceSpotAmendedOrderModel | 现货修改订单子模型 |
| BinanceSpotOrderPlaceResult | 现货订单下单响应 |
| BinanceSpotOrderAmendResult | 现货订单修改响应 |
| BinanceSpotExchangeInfoGetModel | 现货交易所信息 GET |
| BinanceSpotExchangeInfoSymbolModel | 现货交易所信息交易对子模型 |
| BinanceSpotExchangeInfoRateLimitModel | 现货交易所信息频率限制子模型 |
| BinanceSpotExchangeInfoSymbolFilterModel | 现货交易所信息过滤器子模型 |
| BinanceSpotExchangeInfoSorModel | 现货 SOR 参数子模型 |

### 7.2 期货（FUTURES）模型

| 模型类名 | 说明 |
|----------|------|
| BinanceFuturesKlineGetModel | 期货 K线 GET |
| BinanceFuturesKlineWSModel | 期货 K线 WS |
| BinanceFuturesTicker24hrGetModel | 期货 24hr Ticker GET |
| BinanceFuturesTicker24hrWSModel | 期货 24hr Ticker WS |
| BinanceFuturesAccountGetModel | 期货账户信息 GET |
| BinanceFuturesAccountAssetModel | 期货账户资产子模型 |
| BinanceFuturesAccountPositionModel | 期货持仓子模型 |
| BinanceFuturesAccountUpdateWSModel | 期货账户更新 WS |
| BinanceFuturesAccountUpdateBalanceModel | 期货余额更新子模型 |
| BinanceFuturesAccountUpdatePositionModel | 期货持仓更新子模型 |
| BinanceFuturesAccountUpdateDataModel | 期货账户更新数据子模型 |
| BinanceFuturesOrderTradeUpdateWSModel | 期货订单成交更新 WS |
| BinanceFuturesOrderDataModel | 期货订单数据子模型 |
| BinanceFuturesOrderPlaceResult | 期货订单下单响应 |
| BinanceFuturesModifyOrderResponse | 期货订单修改响应 |
| BinanceFuturesExchangeInfoGetModel | 期货交易所信息 GET |
| BinanceFuturesExchangeInfoSymbolModel | 期货交易所信息交易对子模型 |
| BinanceFuturesExchangeInfoRateLimitModel | 期货交易所信息频率限制子模型 |
| BinanceFuturesExchangeInfoAssetModel | 期货交易所信息资产子模型 |
| BinanceFuturesExchangeInfoSymbolFilterModel | 期货交易所信息过滤器子模型 |

### 7.3 通用模型

| 模型类名 | 说明 |
|----------|------|
| WSResponse | WebSocket 通用响应 |

---

## 8. 参考资料

- 现货 REST API: `binance_spot_docs/01_REST API/Market Data endpoints.md`
- 现货 WebSocket: `binance_spot_docs/WebSocket Streams.md`
- 现货账户 REST API: `binance_spot_docs/01_REST API/Account Endpoints.md`
- 现货 User Data Stream: `binance_spot_docs/User Data Stream.md`
  - 包含: executionReport, outboundAccountPosition, balanceUpdate, listStatus, eventStreamTerminated, externalLockUpdate
- 现货交易所信息: `binance_spot_docs/01_REST API/General endpoints.md`
- 期货 REST API: `binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/`
- 期货 WebSocket: `binance_futures_docs/01_U本位合约/02_Websocket行情推送/`
- 期货账户 REST API: `binance_futures_docs/01_U本位合约/02_账户接口/03_REST API/账户信息V3(USER-DATA).md`
- 期货 User Data Stream:
  - 订单交易更新: `binance_futures_docs/01_U本位合约/02_Websocket账户信息推送/订单交易更新推送.md`
  - 账户余额/持仓更新: `binance_futures_docs/01_U本位合约/02_Websocket账户信息推送/Balance和Position更新推送.md`
- 期货交易所信息: `binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/获取交易规则和交易对.md`
