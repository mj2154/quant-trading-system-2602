# API 服务数据模型

本文档记录 API 服务（`services/api-service/src/models/`）中所有的 Pydantic 数据模型。

## 模型目录结构

```
models/
├── trading/               # 交易数据模型（前端数据格式）
│   ├── kline_models.py           # K线数据
│   ├── symbol_models.py          # 交易对信息
│   ├── quote_models.py           # 报价/深度数据
│   ├── futures_models.py         # 期货扩展数据
│   └── order_models.py          # 交易订单模型
│
├── db/                    # 数据库表对应模型
│   ├── task_models.py           # 任务模型
│   ├── realtime_data_models.py  # 订阅/实时数据
│   ├── kline_history_models.py # K线历史
│   ├── account_models.py        # 账户信息
│   ├── exchange_models.py       # 交易所信息
│   ├── alert_config_models.py   # 告警配置
│   └── signal_models.py         # 信号模型
│
├── protocol/              # WebSocket 协议层模型
│   ├── ws_message.py             # 消息协议
│   ├── ws_payload.py            # 载荷数据
│   └── constants.py             # 协议常量
│
└── error_models.py        # 错误模型
```

---

## trading/ 交易数据模型

用于前端数据交换，格式与 TradingView 图表库兼容。

### base.py - 基础模型类

提供 camelCase/snake_case 自动转换的基类。

| 模型名称 | 用途 | 主要字段/方法 |
|---------|------|--------------|
| `CamelCaseModel` | 响应模型基类 | 序列化时自动转为 camelCase |
| `SnakeCaseModel` | 请求模型基类 | 接收 camelCase 自动转为 snake_case |

**CamelCaseModel**：

| 特性 | 说明 |
|------|------|
| 用途 | API 响应消息，内部使用 snake_case，序列化输出 camelCase |
| 示例 | internal_field -> "internalField" |
| 配置 | alias_generator=to_camel, by_alias=True |
| 方法 | model_dump(), model_dump_json() 默认使用 camelCase |

**SnakeCaseModel**：

| 特性 | 说明 |
|------|------|
| 用途 | 接收外部输入（WebSocket请求、API请求），自动将 camelCase 转为 snake_case |
| 示例 | "internalField" -> internal_field |
| 配置 | alias_generator=to_snake |
| 验证器 | convert_camel_to_snake() 在解析前转换所有键 |

**设计原则**：
- CamelCaseModel: 用于API响应，序列化时自动转为 camelCase
- SnakeCaseModel: 用于接收外部输入，自动将 camelCase 转为 snake_case

**命名规范 - 核心原则**：
> **后端内部使用 snake_case（蛇形命名），自动转换为 camelCase（驼峰）发送给前端**

| 层级 | 命名风格 | 说明 |
|------|----------|------|
| 后端代码（内部） | snake_case | Python 惯例，如 `open_time`, `close_price` |
| 响应输出（前端） | camelCase | API 服务自动转换后发给前端 |
| 前端输入（请求） | camelCase | 前端发送，后端 SnakeCaseModel 自动转换 |

**转换机制**：使用 Pydantic v2 的 `to_camel` / `to_snake` 自动转换。

```python
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

class OrderResponse(CamelCaseModel):
    """API 响应模型 - 序列化时自动转为 camelCase"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    order_id: int        # 内部使用 snake_case
    client_order_id: str # 序列化后: "clientOrderId": "xxx"
    created_at: int      # 序列化后: "createdAt": 1234567890
```

**示例 - WS协议 JSON vs 后端模型**：

```json
// 前端接收的响应（camelCase）
{
    "orderId": 22542179,
    "clientOrderId": "660e8400e29b41d4a716446655440001",
    "symbol": "BTCUSDT",
    "side": "BUY"
}
```

```python
# 后端模型定义（snake_case）
class OrderData(CamelCaseModel):
    order_id: int = Field(..., alias="orderId")
    client_order_id: str = Field(..., alias="clientOrderId")
    symbol: str
    side: str
```

**引用**：`docs/backend/design/DATABASE_COORDINATED_ARCHITECTURE.md#44-数据命名规范`

---

### kline_models.py - K线数据模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `KlineBar` | 单根K线数据（OHLCV） | `time`, `open`, `high`, `low`, `close`, `volume` |
| `KlineData` | 单个K线+元信息 | `symbol`, `interval`, `bar`, `is_bar_closed` |
| `KlineBars` | K线数据列表 | `symbol`, `interval`, `bars[]`, `count`, `no_data` |
| `KlineMeta` | K线请求元信息 | `symbol`, `interval`, `from_time`, `to`, `count`, `next_time` |
| `KlineResponse` | 响应格式（兼容旧版） | `data[]`, `meta` |

**使用场景**：
- `KlineBar` - WebSocket 推送实时K线、K线历史数据
- `KlineBars` - K线历史查询响应

### symbol_models.py - 交易对模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `SymbolInfo` | 交易对完整信息（TV格式） | `name`, `ticker`, `description`, `type`, `exchange`, `listed_exchange`, `session`, `timezone`, `minmov`, `pricescale`... (50+字段) |
| `SymbolSearchResult` | 单个搜索结果 | `symbol`, `full_name`, `description`, `type`, `exchange`, `ticker` |
| `SymbolSearchResults` | 搜索结果列表 | `symbols[]`, `total`, `count` |

**字段详情 - SymbolInfo（TradingView LibrarySymbolInfo 格式）**：

| 字段分类 | 字段名 | 类型 | 说明 |
|---------|--------|------|------|
| 必需字段 | `name` | str | 符号名称（如 "BTC/USDT"） |
| 必需字段 | `ticker` | str | 唯一标识符（如 "BTCUSDT"） |
| 必需字段 | `description` | str | 描述（如 "Bitcoin/Tether"） |
| 必需字段 | `type` | str | 标的类型（如 "crypto"） |
| 必需字段 | `exchange` | str | 交易所（如 "BINANCE"） |
| 必需字段 | `listed_exchange` | str | 上市交易所 |
| 必需字段 | `session` | str | 交易时段（如 "24x7"） |
| 必需字段 | `timezone` | str | 时区（如 "UTC"） |
| 必需字段 | `minmov` | float | 最小变动单位 |
| 必需字段 | `pricescale` | int | 价格刻度 |
| 可选字段 | `base_name` | list[str] | 基础名称 |
| 可选字段 | `has_intraday` | bool | 是否支持日内数据（默认 True） |
| 可选字段 | `has_daily` | bool | 是否支持日线数据（默认 True） |
| 可选字段 | `has_weekly_and_monthly` | bool | 是否支持周/月线（默认 True） |
| 可选字段 | `volume_precision` | int | 成交量精度 |
| 可选字段 | `supported_resolutions` | list[str] | 支持的分辨率 |

**使用场景**：
- `search_symbols` - 交易对搜索
- `resolve_symbol` - 交易对解析

### quote_models.py - 报价数据模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `QuotesValue` | 实时报价（TV格式） | `ch`, `chp`, `short_name`, `exchange`, `description`, `lp`, `ask`, `bid`, `spread`, `open_price`, `high_price`, `low_price`, `volume` |
| `QuotesData` | 报价数据 | `n` (symbol), `s` (status), `v` (QuotesValue) |
| `QuotesList` | 多交易对报价 | `quotes[]` |
| `PriceLevel` | 深度价格档位 | `price`, `quantity` |
| `OrderBookData` | 订单簿数据 | `symbol`, `bids[]`, `asks[]`, `last_update_id` |

**字段详情 - QuotesValue（TradingView DatafeedQuoteValues 格式）**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `ch` | float | 价格变化（change） |
| `chp` | float | 价格变化百分比（change percent） |
| `short_name` | str | 短名称（如 "BTCUSDT"） |
| `exchange` | str | 交易所名称（如 "BINANCE"） |
| `description` | str | 标的描述（如 "比特币/泰达币"） |
| `lp` | float | 最新价格（last price） |
| `ask` | float | 卖价 |
| `bid` | float | 买价 |
| `spread` | float | 价差 |
| `open_price` | float | 开盘价 |
| `high_price` | float | 最高价 |
| `low_price` | float | 最低价 |
| `prev_close_price` | float | 前收盘价（可选） |
| `volume` | float | 成交量 |

**使用场景**：
- `QUOTES` 订阅 - 实时报价推送
- `get_quotes` - 批量报价查询

### futures_models.py - 期货数据模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `MarkPriceData` | 标记价格 | `symbol`, `mark_price`, `index_price`, `last_funding_rate`, `next_funding_time` |
| `FundingRateData` | 资金费率 | `symbol`, `funding_rate`, `funding_time` |
| `OpenInterestData` | 未平仓合约 | `symbol`, `open_interest`, `open_interest_value` |
| `FuturesSymbolInfo` | 期货交易对信息 | `exchange`, `symbol`, `base_asset`, `quote_asset`, `status`, `contract_type`, `delivery_date`, `listing_date`... |
| `PremiumIndexData` | 溢价指数 | `symbol`, `event_time`, `mark_price`, `index_price`, `mark_price_change`, `estimated_settle_price`, `time_to_funding` |
| `OpenInterestStatsData` | 未平仓统计 | `symbol`, `event_time`, `sum_open_interest`, `sum_open_interest_value`, `count` |

**字段详情 - MarkPriceData**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `symbol` | str | 交易对 |
| `mark_price` | float | 标记价格 |
| `index_price` | float | 指数价格 |
| `last_funding_rate` | float | 最近资金费率 |
| `next_funding_time` | int | 下次资金时间（毫秒时间戳） |

**字段详情 - FundingRateData**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `symbol` | str | 交易对 |
| `funding_rate` | float | 资金费率 |
| `funding_time` | int | 资金时间（毫秒时间戳） |

**字段详情 - OpenInterestData**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `symbol` | str | 交易对 |
| `open_interest` | float | 未平仓合约数 |
| `open_interest_value` | float | 未平仓合约价值 |

**字段详情 - FuturesSymbolInfo**：

| 字段分类 | 字段名 | 类型 | 说明 |
|---------|--------|------|------|
| 基础信息 | `exchange` | str | 交易所（默认 "BINANCE"） |
| 基础信息 | `symbol` | str | 交易对 |
| 基础信息 | `base_asset` | str | 基础资产 |
| 基础信息 | `quote_asset` | str | 计价资产 |
| 基础信息 | `status` | str | 状态 |
| 合约信息 | `contract_type` | str | 合约类型（"PERPETUAL" 等） |
| 合约信息 | `delivery_date` | int | 交割日期（永续合约为 None） |
| 合约信息 | `listing_date` | int | 上市日期（毫秒） |
| 交易规则 | `initial_margin` | float | 初始保证金 |
| 交易规则 | `maintenance_margin` | float | 维持保证金 |
| 交易规则 | `price_tick` | float | 价格最小变动单位 |
| 交易规则 | `min_qty` | float | 最小下单量 |
| 交易规则 | `max_qty` | float | 最大下单量 |
| 交易规则 | `max_notional_value` | float | 最大名义价值 |
| 手续费 | `liquidation_fee` | float | 强平手续费率 |
| 手续费 | `maker_commission` | float | 挂单手续费 |
| 手续费 | `taker_commission` | float | 吃单手续费 |

**使用场景**：
- 期货合约实时数据订阅
- 资金费率查询

---

## db/ 数据库表对应模型

与数据库表结构对应的 Pydantic 模型。

### task_models.py - 任务模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `TaskStatus` | 任务状态枚举 | `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` |
| `TaskType` | 任务类型枚举 | `TV_SUBSCRIBE_KLINE`, `SYSTEM_FETCH_EXCHANGE_INFO` 等 |
| `UnifiedTaskPayload` | 统一任务载荷 | `action`, `resource`, `params` |
| `TaskCreate` | 任务创建 | `type`, `payload` |
| `TaskResponse` | 任务响应 | `id`, `type`, `payload`, `result`, `status`, `created_at` |
| `TaskUpdate` | 任务更新 | `status`, `result` |
| `TaskListResponse` | 任务列表 | `items[]`, `total`, `page`, `page_size` |

**使用场景**：
- `tasks` 表的增删改查
- 任务创建和状态管理

### realtime_data_models.py - 订阅/实时数据模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `SubscriptionKey` | 订阅键解析 | `exchange`, `symbol`, `subscription_type`, `interval` |
| `SubscriptionDetail` | 订阅详情 | `client_id`, `subscription_key`, `symbol`, `subscription_type`, `created_at` |
| `ClientSubscriptions` | 客户端订阅 | `client_id`, `subscriptions[]`, `created_at` |
| `ExchangeSubscriptions` | 交易所订阅 | `exchange`, `streams[]`, `created_at` |
| `SubscriptionChange` | 订阅变更 | `exchange`, `subscribe[]`, `unsubscribe[]`, `total_required` |
| `SubscriptionStats` | 订阅统计 | `total_subscriptions`, `unique_symbols`, `active_clients` |
| `ProductTypeInfo` | 产品类型解析 | `type`, `base_symbol`, `quote_symbol`, `exchange_symbol`, `api_endpoint`, `ws_stream` |
| `SubscriptionRequest` | 订阅请求项 | `symbol`, `interval` |
| `SubscriptionBatch` | 批量订阅 | `client_id`, `subscriptions{}`, `timestamp` |
| `SubscriptionValidation` | 订阅验证 | `is_valid`, `errors[]`, `warnings[]` |
| `BatchSubscriptionResult` | 批量结果 | `successful_subscriptions{}`, `failed[]` |

**使用场景**：
- 订阅键解析和验证
- 客户端订阅管理
- 订阅统计

### kline_history_models.py - K线历史模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `KlineRecord` | K线数据（数据库） | `symbol`, `interval`, `open_time`, `close_time`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`, `quote_volume`, `number_of_trades` |
| `KlineCreate` | K线创建 | 与 KlineRecord 类似，用于插入数据库 |
| `KlineResponse` | K线响应格式 | 使用数字索引 `0`-`11` 的数组格式 |
| `KlineWebSocket` | WebSocket K线 | `event_type`, `event_time`, `symbol`, `kline` |
| `KlineInterval` | K线间隔常量 | `INTERVAL_1M`, `INTERVAL_5M` 等 |
| `KLineHistoryQuery` | 历史查询参数 | `symbol`, `interval`, `start_time`, `end_time`, `limit` |
| `KLineHistoryResponse` | 历史响应 | `symbol`, `interval`, `bars[]`, `count` |

**使用场景**：
- `klines_history` 表的数据操作
- K线历史查询

### account_models.py - 账户模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `AccountInfoCreate` | 账户创建 | `account_type`, `data` |
| `AccountInfoUpdate` | 账户更新 | `data`, `update_time` |
| `AccountInfoResponse` | 账户响应 | `account_type`, `data`, `update_time`, `created_at` |
| `AccountInfoListResponse` | 账户列表 | `items[]`, `total` |
| `SpotAccountInfo` | 现货账户视图 | `account_type`, `total_asset`, `total_btc`, `balances[]` |
| `FuturesAccountInfo` | 期货账户视图 | `account_type`, `total_balance`, `total_asset`, `available_balance`, `positions[]` |
| `AccountBalance` | 账户余额 | `asset`, `free`, `locked`, `total` |
| `PositionInfo` | 持仓信息 | `symbol`, `position_side`, `position_amount`, `entry_price`, `mark_price`, `unrealized_pnl`, `leverage`, `margin`, `pnl_percent` |

**使用场景**：
- `account_info` 表操作
- 账户信息查询和推送

---

#### 字段详情 - AccountInfoCreate

| 字段名 | 类型 | 必填 | 说明 | JSON字段 |
|--------|------|-----|------|----------|
| `account_type` | str | ✅ | 账户类型：`SPOT`(现货), `FUTURES`(期货) | `accountType` |
| `data` | dict | ✅ | 账户原始数据（JSON格式存储） | `data` |

---

#### 字段详情 - AccountInfoResponse

| 字段名 | 类型 | 必填 | 说明 | JSON字段 |
|--------|------|-----|------|----------|
| `id` | int | ✅ | 记录ID | `id` |
| `account_type` | str | ✅ | 账户类型：`SPOT` / `FUTURES` | `accountType` |
| `data` | dict | ✅ | 账户原始数据（JSONB存储） | `data` |
| `update_time` | int | 否 | 币安返回的更新时间（毫秒时间戳） | `updateTime` |
| `created_at` | datetime | ✅ | 创建时间 | `createdAt` |
| `updated_at` | datetime | ✅ | 更新时间 | `updatedAt` |

---

#### 字段详情 - SpotAccountInfo（视图模型）

> **说明**：此模型从 `AccountInfoResponse.data` 字段解析而来，用于前端展示

| 字段名 | 类型 | 默认值 | 说明 | JSON字段 |
|--------|------|--------|------|----------|
| `account_type` | str | `"SPOT"` | 账户类型 | `accountType` |
| `exchange` | str | `"BINANCE"` | 交易所 | `exchange` |
| `total_asset` | float | `0.0` | 总资产（USDT） | `totalAsset` |
| `total_btc` | float | `0.0` | 总资产（BTC） | `totalBtc` |
| `balances` | list[dict] | `[]` | 余额列表 | `balances` |

---

#### 字段详情 - FuturesAccountInfo（视图模型）

> **说明**：此模型从 `AccountInfoResponse.data` 字段解析而来，用于前端展示

| 字段名 | 类型 | 默认值 | 说明 | JSON字段 |
|--------|------|--------|------|----------|
| `account_type` | str | `"FUTURES"` | 账户类型 | `accountType` |
| `exchange` | str | `"BINANCE"` | 交易所 | `exchange` |
| `total_balance` | float | `0.0` | 总余额 | `totalBalance` |
| `total_asset` | float | `0.0` | 总资产（USDT） | `totalAsset` |
| `available_balance` | float | `0.0` | 可用余额 | `availableBalance` |
| `total_position_value` | float | `0.0` | 持仓市值 | `totalPositionValue` |
| `total_unrealized_pnl` | float | `0.0` | 未实现盈亏 | `totalUnrealizedPnl` |
| `margin_balance` | float | `0.0` | 保证金余额 | `marginBalance` |
| `positions` | list[dict] | `[]` | 持仓列表 | `positions` |

---

#### 字段详情 - AccountBalance

| 字段名 | 类型 | 必填 | 说明 | JSON字段 |
|--------|------|-----|------|----------|
| `asset` | str | ✅ | 资产名称（如 `BTC`, `USDT`） | `asset` |
| `free` | float | 否 | 可用数量 | `free` |
| `locked` | float | 否 | 冻结数量 | `locked` |

**计算属性**：
| 属性 | 类型 | 说明 |
|------|------|------|
| `total` | float | 总数量 = free + locked |

---

#### 字段详情 - PositionInfo

| 字段名 | 类型 | 默认值 | 说明 | JSON字段 |
|--------|------|--------|------|----------|
| `symbol` | str | - | 交易对 | `symbol` |
| `position_side` | str | `"BOTH"` | 持仓方向：`LONG`, `SHORT`, `BOTH` | `positionSide` |
| `position_amount` | float | `0.0` | 持仓数量 | `positionAmount` |
| `entry_price` | float | `0.0` | 开仓价格 | `entryPrice` |
| `break_even_price` | float | `0.0` | 盈亏平衡价格 | `breakEvenPrice` |
| `realized_pnl` | float | `0.0` | 费前累计实现盈亏 | `realizedPnl` |
| `unrealized_pnl` | float | `0.0` | 未实现盈亏 | `unrealizedPnl` |
| `margin_type` | str | `"cross"` | 保证金类型：`isolated`(逐仓) / `cross`(全仓) | `marginType` |
| `isolated_wallet` | float | `0.0` | 逐仓钱包余额 | `isolatedWallet` |
| `mark_price` | float | `0.0` | 标记价格 | `markPrice` |
| `leverage` | int | `1` | 杠杆倍数 | `leverage` |
| `margin` | float | `0.0` | 保证金 | `margin` |

**计算属性**：
| 属性 | 类型 | 说明 |
|------|------|------|
| `pnl_percent` | float | 盈亏百分比 = (unrealized_pnl / margin) * 100 |

---

### exchange_models.py - 交易所信息模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `ExchangeInfo` | 交易所信息（轻量缓存） | `exchange`, `symbols`, `cached_at` |
| `RichExchangeInfo` | 完整交易所信息 | `market_type`, `exchange`, `timezone`, `server_time`, `symbols`, `cached_at` (含方法) |
| `SymbolMetadata` | 交易对元数据 | `symbol`, `exchange`, `product_type`, `base_symbol`, `quote_symbol`, `status` |

**字段详情 - ExchangeInfo**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `exchange` | str | 交易所代码（如 "BINANCE"） |
| `symbols` | list[dict] | 交易对列表 |
| `cached_at` | float | 缓存时间戳 |

**字段详情 - RichExchangeInfo**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `market_type` | str | 市场类型："spot" 或 "futures" |
| `exchange` | str | 交易所代码 |
| `timezone` | str | 时区（默认 "UTC"） |
| `server_time` | int | 服务器时间（毫秒） |
| `symbols` | list[dict] | 所有交易对的原始数据 |
| `cached_at` | float | 缓存时间戳 |

**RichExchangeInfo 方法**：

| 方法名 | 返回类型 | 说明 |
|--------|----------|------|
| `get_symbol_count()` | int | 获取交易对数量 |
| `filter_symbols_by_status(status)` | list[dict] | 按状态过滤交易对 |
| `get_trading_symbols()` | list[str] | 获取所有可交易交易对代码 |
| `find_symbol_by_name(symbol_name)` | dict | 根据名称查找交易对 |

**使用场景**：
- `exchange_info` 表操作
- 交易对信息查询

### alert_config_models.py - 告警配置模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `AlertConfigCreate` | 告警创建 | `id`, `name`, `description`, `strategy_type`, `symbol`, `interval`, `is_enabled`, `created_by` |
| `AlertConfigUpdate` | 告警更新 | `name`, `description`, `is_enabled` |
| `AlertConfigResponse` | 告警响应 | `id`, `name`, `description`, `strategy_type`, `symbol`, `interval`, `trigger_type`, `is_enabled`, `created_at`, `updated_at` |
| `AlertConfigListResponse` | 告警列表 | `items[]`, `total` |
| `EnableDisableResponse` | 启用/禁用响应 | `id`, `name`, `is_enabled`, `message` |
| `CreateAlertConfigRequest` | 创建请求 | `type`, `id`, `name`, `description`, `strategy_type`, `symbol`, `interval` |
| `ListAlertConfigsRequest` | 列表请求 | `type`, `symbol`, `is_enabled`, `limit`, `offset` |
| `UpdateAlertConfigRequest` | 更新请求 | `type`, `id`, `name`, `description`, `is_enabled` |
| `DeleteAlertConfigRequest` | 删除请求 | `type`, `id` |
| `EnableAlertConfigRequest` | 启用请求 | `type`, `id` |

**使用场景**：
- 告警配置 CRUD 操作（通过 WebSocket 消息）
- 告警启用/禁用

### signal_models.py - 信号模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `StrategyParam` | 策略参数 | `name`, `type`, `required`, `default`, `description` |
| `StrategyMetadataResponse` | 策略元数据响应 | `strategy_type`, `name`, `description`, `params[]` |
| `StrategyMetadataListResponse` | 策略元数据列表 | `strategies[]`, `total` |
| `SignalRecordResponse` | 信号记录响应 | `id`, `alert_id`, `strategy_type`, `symbol`, `interval`, `trigger_type`, `signal_time`, `signal_value`, `signal_reason`, `computed_at`, `source_subscription_key`, `metadata`, `created_by` |
| `SignalListResponse` | 信号列表响应 | `signals[]`, `total` |
| `EnableDisableResponse` | 启用/禁用响应 | `id`, `name`, `is_enabled`, `message` |

**字段详情 - StrategyParam**：

| 字段名 | 类型 | 说明 | JSON字段 |
|--------|------|------|----------|
| `name` | str | 参数名称 | `name` |
| `type` | str | 参数类型 | `type` |
| `required` | bool | 是否必填 | `required` |
| `default` | any | 默认值 | `default` |
| `description` | str | 参数描述 | `description` |

**字段详情 - StrategyMetadataResponse**：

| 字段名 | 类型 | 说明 | JSON字段 |
|--------|------|------|----------|
| `strategy_type` | str | 策略类型 | `strategyType` |
| `name` | str | 策略名称 | `name` |
| `description` | str | 策略描述 | `description` |
| `params` | list[StrategyParam] | 参数列表 | `params` |

**字段详情 - SignalRecordResponse**：

| 字段名 | 类型 | 说明 | JSON字段 |
|--------|------|------|----------|
| `id` | int | 信号ID | `id` |
| `alert_id` | str | 告警ID | `alertId` |
| `strategy_type` | str | 策略类型 | `strategyType` |
| `symbol` | str | 交易对 | `symbol` |
| `interval` | str | K线周期（如 "60", "240"） | `interval` |
| `trigger_type` | str | 触发类型 | `triggerType` |
| `signal_time` | int | 信号时间（毫秒时间戳） | `signalTime` |
| `signal_value` | any | 信号值 | `signalValue` |
| `signal_reason` | str \| null | 信号原因（如 "建仓信号", "清仓信号", "无信号"） | `signalReason` |
| `computed_at` | str \| null | 信号计算时间（ISO8601格式） | `computedAt` |
| `source_subscription_key` | str \| null | 触发该信号的订阅键 | `sourceSubscriptionKey` |
| `metadata` | dict \| null | 附加元数据 | `metadata` |
| `created_by` | str \| null | 创建者标识 | `createdBy` |

**JSON 示例（前端接收 - camelCase）**：
```json
{
    "id": 1,
    "alertId": "550e8400e29b41d4a716446655440001",
    "strategyType": "MACDResonanceStrategyV5",
    "symbol": "BINANCE:BTCUSDT",
    "interval": "60",
    "triggerType": "each_kline_close",
    "signalTime": 1704067200000,
    "signalValue": true,
    "signalReason": "建仓信号",
    "computedAt": "2026-02-13T10:00:00Z",
    "sourceSubscriptionKey": "BINANCE:BTCUSDT@KLINE_60",
    "metadata": {},
    "createdBy": "user_001"
}
```

> **重要**：此 JSON 格式与 WS协议设计文档（07-websocket-protocol.md）中的 SIGNAL_DATA 响应格式完全对齐。

**说明**：API 服务只负责接收信号通知（通过 WebSocket），不存储或管理信号。信号由 signal-service 处理。

### order_models.py - 交易订单模型

> **重要**：订单模型完全采用币安官方蛇形命名，与 WS协议设计文档 中的 JSON 示例完全对应

**枚举类型**：

| 枚举名称 | 值 | 说明 |
|---------|-----|------|
| `OrderSide` | `BUY`, `SELL` | 订单方向 |
| `OrderType` (现货) | `LIMIT`, `LIMIT_MAKER`, `MARKET`, `STOP_LOSS`, `STOP_LOSS_LIMIT`, `TAKE_PROFIT`, `TAKE_PROFIT_LIMIT` | 订单类型（现货） |
| `OrderType` (期货) | `LIMIT`, `MARKET`, `STOP`, `STOP_MARKET`, `TAKE_PROFIT`, `TAKE_PROFIT_MARKET`, `TRAILING_STOP_MARKET` | 订单类型（期货） |
| `OrderTimeInForce` | `GTC`, `IOC`, `FOK` | 订单时效 |
| `MarketType` | `SPOT`, `FUTURES` | 市场类型 |

**请求模型**：

| 模型名称 | 用途 | 蛇形字段 | JSON字段(camelCase) |
|---------|------|---------|---------------------|
| `CreateOrderRequest` | 创建订单 | `symbol`, `side`, `type`, `quantity`, `new_client_order_id` | `symbol`, `side`, `type`, `quantity`, `newClientOrderId` |
| `GetOrderRequest` | 查询订单 | `symbol`, `order_id`, `orig_client_order_id` | `symbol`, `orderId`, `origClientOrderId` |
| `ListOrdersRequest` | 查询列表 | `symbol`, `start_time`, `end_time`, `limit` | `symbol`, `startTime`, `endTime`, `limit` |
| `CancelOrderRequest` | 取消订单 | `symbol`, `order_id`, `orig_client_order_id`, `new_client_order_id` | `symbol`, `orderId`, `origClientOrderId`, `newClientOrderId` |
| `GetOpenOrdersRequest` | 查询挂单 | `symbol` | `symbol` |

**字段详情 - CreateOrderRequest**（期货）：

| 字段名 | 类型 | 必填 | 说明 | JSON字段 |
|--------|------|-----|------|----------|
| `symbol` | str | ✅ | 交易对 | `symbol` |
| `side` | str | ✅ | 方向 BUY/SELL | `side` |
| `type` | str | ✅ | 订单类型 | `type` |
| `quantity` | float | ✅ | 数量 | `quantity` |
| `new_client_order_id` | str | ✅ | 客户端订单ID | `newClientOrderId` |
| `price` | float | 条件必填 | 价格（LIMIT类型） | `price` |
| `time_in_force` | str | 条件必填 | 时效 GTC/IOC/FOK | `timeInForce` |
| `position_side` | str | 否 | 持仓方向 BOTH/LONG/SHORT | `positionSide` |
| `reduce_only` | bool | 否 | 是否只减仓 | `reduceOnly` |

**字段详情 - CreateOrderRequest**（现货）：

| 字段名 | 类型 | 必填 | 说明 | JSON字段 |
|--------|------|-----|------|----------|
| `symbol` | str | ✅ | 交易对 | `symbol` |
| `side` | str | ✅ | 方向 BUY/SELL | `side` |
| `type` | str | ✅ | 订单类型 | `type` |
| `quantity` | float | ✅ | 数量 | `quantity` |
| `new_client_order_id` | str | ✅ | 客户端订单ID | `newClientOrderId` |
| `price` | float | 条件必填 | 价格（LIMIT类型） | `price` |
| `time_in_force` | str | 条件必填 | 时效 GTC/IOC/FOK | `timeInForce` |
| `quote_order_qty` | float | 否 | 报价数量 | `quoteOrderQty` |

**响应模型**：

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `OrderData` | 订单数据 | `order_id`, `client_order_id`, `symbol`, `side`, `status`, `type` |
| `OrderListData` | 订单列表 | `orders[]`, `count` |
| `OrderUpdateData` | 订单更新推送 | 继承 OrderData，额外包含 `updated_at` |
| `OrderListResponseData` | 列表响应 | `orders[]`, `count` |
| `OrderCancelResponseData` | 取消响应 | `order_id`, `client_order_id`, `symbol`, `status` |
| `OpenOrdersResponseData` | 挂单响应 | `orders[]`, `count` |

**字段详情 - OrderData**：

> **重要**：完全采用币安蛇形命名，序列化自动转驼峰

| 字段名 | 类型 | 说明 | JSON字段 |
|--------|------|------|----------|
| `order_id` | int | 订单ID | `orderId` |
| `client_order_id` | str | 客户端订单ID | `clientOrderId` |
| `symbol` | str | 交易对 | `symbol` |
| `side` | str | 方向 | `side` |
| `type` | str | 类型 | `type` |
| `price` | str | 价格 | `price` |
| `orig_qty` | str | 原数量 | `origQty` |
| `executed_qty` | str | 已执行数量 | `executedQty` |
| `status` | str | 状态 | `status` |
| `time_in_force` | str | 时效 | `timeInForce` |
| `create_time` | int | 创建时间 | `createTime` |
| `update_time` | int | 更新时间 | `updateTime` |

**JSON 示例（前端接收 - camelCase）**：
```json
{
    "orderId": 22542179,
    "clientOrderId": "660e8400e29b41d4a716446655440001",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "price": "50000.00000000",
    "origQty": "0.00200000",
    "executedQty": "0.00200000",
    "status": "FILLED",
    "timeInForce": "GTC",
    "createTime": 1704067200000,
    "updateTime": 1704067200000
}
```

**说明**：交易订单模型与 trading_orders 表和 04-trading-orders.md 设计保持一致。data 字段存储币安 API 返回的完整 JSON 数据。

---

## protocol/ WebSocket 协议层模型

用于 WebSocket 消息的请求/响应格式。

### ws_message.py - 消息协议模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `WebSocketMessage` | 统一消息格式 | `protocol_version`, `type`, `request_id`, `timestamp`, `data` |
| `MessageRequest` | 请求消息 | 继承 WebSocketMessage |
| `ConfigRequest` | 配置请求 | `type: "GET_CONFIG"` |
| `SearchSymbolsRequest` | 搜索请求 | `type: "GET_SEARCH_SYMBOLS"`, `query`, `exchange`, `limit` |
| `ResolveSymbolRequest` | 解析请求 | `type: "GET_RESOLVE_SYMBOL"`, `symbol` |
| `KlinesRequest` | K线请求 | `type: "GET_KLINES"`, `symbol`, `interval`, `from_time`, `to_time` |
| `ServerTimeRequest` | 时间请求 | `type: "GET_SERVER_TIME"` |
| `QuotesRequest` | 报价请求 | `type: "GET_QUOTES"`, `symbols[]` |
| `SubscribeRequest` | 订阅请求 | `type: "SUBSCRIBE"`, `subscriptions[]` |
| `UnsubscribeRequest` | 取消订阅 | `type: "UNSUBSCRIBE"`, `subscriptions[]` |
| `SubscriptionsRequest` | 订阅列表 | `type: "GET_SUBSCRIPTIONS"`, `client_id` |
| `MetricsRequest` | 指标请求 | `type: "GET_METRICS"` |
| `MessageResponseBase` | 响应基类 | `type`, `request_id`, `data` |
| `MessageSuccess` | 成功响应 | `type: "KLINES_DATA"` 等数据类型, `request_id`, `data` |
| `MessageError` | 错误响应 | `type: "ERROR"`, `request_id`, `data.error_code`, `data.error_message` |
| `MessageUpdate` | 更新推送 | `type: "UPDATE"`, `data` |

**使用场景**：
- WebSocket 消息的请求/响应格式定义
- 消息类型验证

### ws_payload.py - 载荷数据模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `SymbolType` | 交易对类型 | `crypto`, `forex`, `stock` |
| `ConfigData` | 配置数据 | `supportsSearch`, `supportsGroupRequest`, `supportedResolutions[]` |
| `SearchSymbolsData` | 搜索数据 | `symbols[]`, `total` |
| `ServerTimeData` | 时间数据 | `serverTime`, `timezone` |
| `FailedSubscription` | 失败的订阅 | `symbol`, `error_code`, `error_message` |
| `SubscribeData` | 订阅确认 | `subscriptions[]` |
| `UnsubscribeData` | 取消确认 | `subscriptions[]` |
| `SubscriptionItem` | 订阅项 | `symbol`, `subscriptions[]` |
| `SubscriptionsData` | 订阅列表 | `subscriptions[]` |
| `SystemMetrics` | 系统指标 | `active_connections`, `total_subscriptions`, `unique_symbols` |
| `MetricsData` | 指标数据 | `active_connections`, `total_subscriptions` |
| `ErrorData` | 错误数据 | `error_code`, `error_message` |
| `TaskResultData` | 任务结果 | `task_id`, `result` |
| `SubscriptionInfo` | 订阅信息 | `symbol`, `subscriptions[]` |
| `OrderResponseData` | 订单响应数据 | `type`, `status`, `task_id`, `result`, `payload` |
| `AccountResponseData` | 账户响应数据 | `account_type`, `data` |
| `SignalData` | 信号数据 | `signals[]` |

**字段详情 - SymbolType**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `crypto` | str | 加密货币 |
| `forex` | str | 外汇 |
| `stock` | str | 股票 |

**字段详情 - FailedSubscription**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `symbol` | str | 订阅的交易对 |
| `error_code` | str | 错误码 |
| `error_message` | str | 错误信息 |

**字段详情 - SubscriptionItem**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `symbol` | str | 交易对 |
| `subscriptions` | list[str] | 订阅列表 |

**字段详情 - SystemMetrics**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `active_connections` | int | 活跃连接数 |
| `total_subscriptions` | int | 总订阅数 |
| `unique_symbols` | int | 唯一交易对数 |
| `exchange_subscriptions` | dict | 各交易所订阅统计 |

**字段详情 - OrderResponseData**（对应 WS协议 ORDER_DATA 响应）：

> **重要**：此模型采用蛇形命名，序列化时自动转换为驼峰发送给前端

| 字段名 | 类型 | 说明 | JSON字段 |
|--------|------|------|----------|
| `type` | str | 固定值 `"order"` | `"type"` |
| `status` | str | 任务状态 | `"status"` |
| `task_id` | int | 任务ID | `"taskId"` |
| `result` | dict | 订单结果 | `"result"` |
| `payload` | dict | 请求载荷 | `"payload"` |
| `error_code` | str | 错误码（失败时） | `"errorCode"` |
| `error_message` | str | 错误信息（失败时） | `"errorMessage"` |

**JSON 示例（前端接收 - camelCase）**：
```json
{
    "type": "order",
    "status": "COMPLETED",
    "taskId": 123,
    "result": {
        "orderId": 22542179,
        "clientOrderId": "660e8400e29b41d4a716446655440001",
        "symbol": "BTCUSDT",
        "side": "BUY"
    },
    "payload": {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.002
    }
}
```

**字段详情 - ErrorData**：

| 字段名 | 类型 | 说明 | JSON字段 |
|--------|------|------|----------|
| `error_code` | str | 错误码 | `"errorCode"` |
| `error_message` | str | 错误信息 | `"errorMessage"` |

**使用场景**：
- 响应消息中的 data 字段内容定义

---

#### 账户数据模型（WS协议 ACCOUNT_DATA 响应）

> **重要说明**：账户信息分为两种数据模型，**来源不同，格式不同**：
> - **GET 请求**：获取完整账户快照（`GET_FUTURES_ACCOUNT` / `GET_SPOT_ACCOUNT`）
> - **订阅推送**：获取增量更新（`ACCOUNT_UPDATE` / `outboundAccountPosition`）

##### 1. 期货账户信息（GET 请求 - 完整快照）

**模型**: `FuturesAccountData` - 对应 WS协议 `GET_FUTURES_ACCOUNT` 响应

> **数据来源**: Binance WebSocket API (`v2/account.status`)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `account_type` | str | 固定值 `"FUTURES"` |
| `account` | dict | 账户详情 |

**Account 字段**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `totalInitialMargin` | str | 总初始保证金（仅 USDT 资产） |
| `totalMaintMargin` | str | 总维持保证金（仅 USDT 资产） |
| `totalWalletBalance` | str | 总钱包余额（仅 USDT 资产） |
| `totalUnrealizedProfit` | str | 总未实现盈亏（仅 USDT 资产） |
| `totalMarginBalance` | str | 总保证金余额（仅 USDT 资产） |
| `totalPositionInitialMargin` | str | 持仓所需初始保证金（仅 USDT 资产） |
| `totalOpenOrderInitialMargin` | str | 挂单所需初始保证金（仅 USDT 资产） |
| `totalCrossWalletBalance` | str | 全仓钱包余额（仅 USDT 资产） |
| `totalCrossUnPnl` | str | 全仓未实现盈亏（仅 USDT 资产） |
| `availableBalance` | str | 可用余额 |
| `maxWithdrawAmount` | str | 最大可转出金额 |
| `feeTier` | int | 账户手续费等级 |
| `feeBurn` | bool | 是否开启手续费折扣: true=折扣开启, false=折扣关闭 |
| `multiAssetsMargin` | bool | 是否为多资产模式 |
| `tradeGroupId` | int | 交易组ID |
| `updateTime` | long | 更新时间（毫秒） |
| `assets` | list | 资产列表 |
| `positions` | list | 持仓列表 |
| `rateLimits` | list[dict] | 速率限制信息 |

**Assets（资产列表）数组元素字段**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `asset` | str | 资产名称（如 USDT, BUSD, BTC） |
| `walletBalance` | str | 余额 |
| `unrealizedProfit` | str | 未实现盈亏 |
| `marginBalance` | str | 保证金余额 |
| `maintMargin` | str | 维持保证金 |
| `initialMargin` | str | 当前所需起始保证金 |
| `positionInitialMargin` | str | 持仓所需起始保证金（基于最新标记价格） |
| `openOrderInitialMargin` | str | 当前挂单所需起始保证金（基于最新标记价格） |
| `crossWalletBalance` | str | 全仓账户余额 |
| `crossUnPnl` | str | 全仓持仓未实现盈亏 |
| `availableBalance` | str | 可用余额 |
| `maxWithdrawAmount` | str | 最大可转出余额 |
| `marginAvailable` | bool | 该资产是否可用作多资产模式的保证金 |
| `updateTime` | long | 更新时间（毫秒） |

**Positions（持仓列表）数组元素字段**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `symbol` | str | 交易对符号（如 BTCUSDT） |
| `initialMargin` | str | 持仓所需起始保证金（基于最新标记价格） |
| `maintMargin` | str | 维持保证金 |
| `unrealizedProfit` | str | 持仓未实现盈亏 |
| `positionInitialMargin` | str | 持仓所需起始保证金（基于最新标记价格） |
| `openOrderInitialMargin` | str | 当前挂单所需起始保证金（基于最新标记价格） |
| `leverage` | str | 当前杠杆倍数 |
| `isolated` | bool | 是否为逐仓 |
| `entryPrice` | str | 平均入场价格 |
| `maxNotional` | str | 当前杠杆下的最大可用名义价值 |
| `bidNotional` | str | 买单名义价值（忽略） |
| `askNotional` | str | 卖单名义价值（忽略） |
| `positionSide` | str | 持仓方向: BOTH(单向), LONG(多头), SHORT(空头) |
| `positionAmt` | str | 持仓数量 |
| `updateTime` | long | 更新时间（毫秒） |

> **JSON 示例**: 参考 WS 协议文档 `1.6 获取期货账户信息` 节

---

##### 2. 现货账户信息（GET 请求 - 完整快照）

**模型**: `SpotAccountData` - 对应 WS协议 `GET_SPOT_ACCOUNT` 响应

> **数据来源**: Binance REST API (`GET /api/v3/account`)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `account_type` | str | 固定值 `"SPOT"` |
| `account` | dict | 账户详情 |

**Account 字段**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `makerCommission` | int | 挂单手续费率 |
| `takerCommission` | int | 吃单手续费率 |
| `buyerCommission` | int | 买入手续费率 |
| `sellerCommission` | int | 卖出手续费率 |
| `commissionRates` | dict | 手续费率详情 |
| `canTrade` | bool | 是否可以交易 |
| `canWithdraw` | bool | 是否可以提现 |
| `canDeposit` | bool | 是否可以充值 |
| `brokered` | bool | 是否为经纪商账户 |
| `requireSelfTradePrevention` | bool | 是否需要自我交易预防 |
| `preventSor` | bool | 是否阻止 SOR |
| `updateTime` | int | 最后更新时间（毫秒） |
| `accountType` | str | 账户类型 |
| `balances` | list | 余额列表 |
| `permissions` | list[str] | 权限列表 |
| `uid` | long | 用户ID |
| `rateLimits` | list[dict] | 速率限制信息 |

**CommissionRates（手续费率详情）字段**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `maker` | str | 挂单手续费率 |
| `taker` | str | 吃单手续费率 |
| `buyer` | str | 买入手续费率 |
| `seller` | str | 卖出手续费率 |

**Balances（余额列表）数组元素字段**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `asset` | str | 资产名称 |
| `free` | str | 可用数量 |
| `locked` | str | 锁定数量 |

> **JSON 示例**: 参考 WS 协议文档 `1.7 获取现货账户信息` 节

---

##### 3. 期货账户增量推送（订阅）

**模型**: `FuturesAccountUpdate` - 对应 WS协议 `ACCOUNT_UPDATE` 事件

> **数据来源**: Binance WebSocket User Data Stream (`ACCOUNT_UPDATE`)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `event_type` | str | 固定值 `"account_update"` |
| `subscription_key` | str | 订阅键，如 `"BINANCE:ACCOUNT@FUTURES"` |
| `content` | dict | 推送内容 |

**Content 字段**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `e` | str | 事件类型：`"ACCOUNT_UPDATE"` |
| `E` | int | 事件时间（毫秒） |
| `T` | int | 事务时间（毫秒） |
| `a` | dict | 更新数据 |

**a (更新数据) 字段**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `m` | str | 事件原因：`DEPOSIT`, `WITHDRAW`, `ORDER`, `FUNDING_FEE`, `WITHDRAW_REJECT`, `ADJUSTMENT`, `INSURANCE_CLEAR`, `ADMIN_DEPOSIT`, `ADMIN_WITHDRAW`, `MARGIN_TRANSFER`, `MARGIN_TYPE_CHANGE`, `ASSET_TRANSFER`, `OPTIONS_PREMIUM_FEE`, `OPTIONS_SETTLE_PROFIT`, `AUTO_EXCHANGE`, `COIN_SWAP_DEPOSIT`, `COIN_SWAP_WITHDRAW` |
| `B` | list[dict] | 余额更新列表 |
| `P` | list[dict] | 持仓更新列表 |

**B (余额) 字段**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `a` | str | 资产名称 |
| `wb` | str | 钱包余额 |
| `cw` | str | 可用余额（扣除挂单保证金） |
| `bc` | str | 变更金额 |

**P (持仓) 字段**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `s` | str | 交易对 |
| `pa` | str | 持仓数量 |
| `ep` | str | 开仓价格 |
| `bep` | str | 盈亏平衡价格 |
| `cr` | str | 费前累计实现盈亏 |
| `up` | str | 未实现盈亏 |
| `mt` | str | 保证金类型：`isolated`(逐仓) / `cross`(全仓) |
| `iw` | str | 逐仓钱包余额 |
| `ps` | str | 持仓方向：`LONG`, `SHORT`, `BOTH` |

> **JSON 示例**: 参考 WS 协议文档 `3.3.2 期货账户增量推送` 节

---

##### 4. 现货账户增量推送（订阅）

**模型**: `SpotAccountUpdate` - 对应 WS协议 `outboundAccountPosition` 事件

> **数据来源**: Binance WebSocket User Data Stream (`outboundAccountPosition`)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `event_type` | str | 固定值 `"account_update"` |
| `subscription_key` | str | 订阅键，如 `"BINANCE:ACCOUNT@SPOT"` |
| `content` | dict | 推送内容 |

**Content 字段**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `e` | str | 事件类型：`"outboundAccountPosition"` |
| `E` | int | 事件时间（毫秒） |
| `u` | int | 账户最后更新时间（毫秒） |
| `B` | list[dict] | 余额列表 |

**B (余额) 字段**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `a` | str | 资产名称 |
| `f` | str | 可用余额 |
| `l` | str | 冻结余额 |

> **JSON 示例**: 参考 WS 协议文档 `3.3.3 现货账户增量推送` 节

---

### constants.py - 协议常量

| 常量名称 | 用途 | 值 |
|---------|------|-----|
| `PROTOCOL_VERSION` | 协议版本 | `"2.0"` |
| `WS_PATH` | WebSocket 路径 | `"/ws"` |
| `WS_USER_DATA_PATH` | 用户数据路径 | `"/ws/user"` |
| `PING_INTERVAL` | 心跳间隔 | `20` 秒 |
| `PING_TIMEOUT` | 心跳超时 | `60` 秒 |

**WSAction - 动作枚举**：

| 值 | 说明 |
|-----|------|
| `GET` | 获取数据 |
| `SUBSCRIBE` | 订阅 |
| `UNSUBSCRIBE` | 取消订阅 |

**WSMessageType - 消息类型**：

| 值 | 说明 |
|-----|------|
| `GET_CONFIG` | 获取配置 |
| `GET_SERVER_TIME` | 获取服务器时间 |
| `GET_METRICS` | 获取指标 |
| `GET_KLINES` | 获取K线 |
| `GET_SEARCH_SYMBOLS` | 搜索交易对 |
| `GET_RESOLVE_SYMBOL` | 解析交易对 |
| `GET_QUOTES` | 获取报价 |
| `GET_SUBSCRIPTIONS` | 获取订阅列表 |
| `GET_SPOT_ACCOUNT` | 获取现货账户 |
| `GET_FUTURES_ACCOUNT` | 获取期货账户 |
| `SUBSCRIBE` | 订阅 |
| `UNSUBSCRIBE` | 取消订阅 |
| `CREATE_ORDER` | 创建订单 |
| `GET_ORDER` | 查询订单 |
| `LIST_ORDERS` | 查询订单列表 |
| `CANCEL_ORDER` | 取消订单 |
| `GET_OPEN_ORDERS` | 查询挂单 |
| `CREATE_ALERT_CONFIG` | 创建告警配置 |
| `LIST_ALERT_CONFIGS` | 列出告警配置 |
| `UPDATE_ALERT_CONFIG` | 更新告警配置 |
| `DELETE_ALERT_CONFIG` | 删除告警配置 |
| `LIST_SIGNALS` | 查询信号 |
| `GET_STRATEGY_METADATA` | 获取策略元数据 |
| `GET_STRATEGY_METADATA_BY_TYPE` | 获取指定策略元数据 |
| `ACK` | 请求确认 |
| `ERROR` | 错误响应 |
| `UPDATE` | 实时数据推送 |
| `CONFIG_DATA` | 配置数据响应 |
| `KLINES_DATA` | K线数据响应 |
| `QUOTES_DATA` | 报价数据响应 |
| `SYMBOL_DATA` | 交易对详情响应 |
| `SEARCH_SYMBOLS_DATA` | 搜索结果响应 |
| `SUBSCRIPTION_DATA` | 订阅确认响应 |
| `ACCOUNT_DATA` | 账户数据响应 |
| `ORDER_DATA` | 订单数据响应 |
| `ORDER_LIST_DATA` | 订单列表响应 |
| `ORDER_UPDATE` | 订单更新推送 |
| `ALERT_CONFIG_DATA` | 告警配置响应 |
| `SIGNAL_DATA` | 信号数据响应 |
| `STRATEGY_METADATA_DATA` | 策略元数据响应 |

**SubscriptionType - 订阅类型**：

| 值 | 说明 | 示例 |
|-----|------|------|
| `KLINE` | K线数据 | `BINANCE:BTCUSDT@KLINE_1` |
| `QUOTES` | 报价数据 | `BINANCE:BTCUSDT@QUOTES` |
| `TRADE` | 交易数据 | `BINANCE:BTCUSDT@TRADE` |
| `ACCOUNT` | 账户数据 | `BINANCE:ACCOUNT@SPOT` |
| `TICKER` | 24hr行情 | `BINANCE:BTCUSDT@TICKER` |

**ProductType - 产品类型**：

| 值 | 说明 |
|-----|------|
| `SPOT` | 现货 |
| `FUTURES` | 期货（U本位永续） |
| `PERPETUAL` | 永续合约 |

**WSErrorCode - 错误码**：

| 值 | 说明 |
|-----|------|
| `UNKNOWN` | 未知错误 |
| `INVALID_REQUEST` | 无效请求 |
| `AUTH_REQUIRED` | 需要认证 |
| `INVALID_SYMBOL` | 无效交易对 |
| `INVALID_INTERVAL` | 无效间隔 |
| `SUBSCRIPTION_FAILED` | 订阅失败 |
| `ORDER_FAILED` | 订单失败 |
| `RATE_LIMIT` | 速率限制 |

**RESOLUTION_TO_INTERVAL / INTERVAL_TO_RESOLUTION**：

详见 [WS协议设计文档](./07-websocket-protocol.md#tv分辨率映射表) 的 TV 分辨率映射表。

---

## error_models.py - 错误模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `ErrorCode` | 错误码 | `code`, `message`, `description` |
| `ErrorMessage` | 错误消息 | `error`, `message`, `code` |
| `BinanceAPIError` | 币安API错误 | `code`, `message`, `error` |
| `AuthenticationError` | 认证错误 | 继承 BinanceAPIError |
| `RateLimitError` | 速率限制错误 | 继承 BinanceAPIError |
| `TimestampError` | 时间戳错误 | 继承 BinanceAPIError |
| `SignatureError` | 签名错误 | 继承 BinanceAPIError |
| `ACCOUNT_ERROR` | 账户错误常量 | `"ACCOUNT_ERROR"` |
| `AUTHENTICATION_ERROR` | 认证错误常量 | `"AUTHENTICATION_ERROR"` |
| `RATE_LIMIT_ERROR` | 速率限制常量 | `"RATE_LIMIT_ERROR"` |
| `TIMESTAMP_ERROR` | 时间戳错误常量 | `"TIMESTAMP_ERROR"` |
| `SIGNATURE_ERROR` | 签名错误常量 | `"SIGNATURE_ERROR"` |

**使用场景**：
- API 错误处理
- 错误响应格式化
- 币安 API 错误码映射

---

## 🔗 前后端数据模型对齐说明

### 架构原则

本设计严格遵循"**契约驱动开发**"理念，后端数据模型严格按照前端 TypeScript 接口构建，实现零转换成本和完全类型对齐。

### 数据流架构

```
前端 TypeScript 接口 ← → 后端 Python 模型 ← → TradingView 库
     ↓                         ↓              ↓
  类型定义              Pydantic 模型      官方标准
  (单一事实来源)        (运行时验证)      (最终目标)
```

### 对齐策略

1. **类型严格对齐**
   - 前端 TypeScript 接口定义严格符合 TradingView 官方标准
   - 后端 Pydantic 模型 100% 对齐前端接口字段
   - 实现编译时和运行时双重类型验证

2. **零转换设计**
   - 后端直接输出 TradingView 兼容格式
   - 避免 datafeed 层进行数据转换
   - 减少错误源和性能开销

3. **契约驱动开发**
   - 前端接口变更自动影响后端实现
   - 通过类型系统保证一致性
   - API 文档与代码同步更新

### 对齐验证

**SymbolInfo 模型对齐度**: 100% ✅
- 所有必需字段严格匹配
- 可选字段完全覆盖
- 严格类型定义完全一致

**Bar 模型对齐度**: 100% ✅
- 字段名、类型、含义完全一致
- TradingView 标准完全兼容

**QuotesValue 模型对齐度**: 100% ✅
- 报价数据字段 100% 匹配
- 扩展字段支持完整实现

### 订单数据模型设计原则

> **设计原则**：完全采用币安官方格式，避免参数命名混乱
> - data 字段完全采用币安蛇形命名（与币安API完全一致）
> - 前端发送 camelCase，后端 SnakeCaseModel 基类自动转换
> - 期货与现货完全分开建模，结构清晰不混淆
> - 区分 requestId（请求追踪）和 newClientOrderId（订单标识）

#### 期货 vs 现货区分

通过交易对符号前缀区分：

| 前缀 | 市场 | 示例 |
|------|------|------|
| `BINANCE:` | 现货 | `BINANCE:BTCUSDT` |
| `BINANCE:` + `.PERP` 后缀 | U本位永续合约 | `BINANCE:BTCUSDT.PERP` |

> **注意**：不再使用 `marketType` 字段区分，通过 symbol 前缀自动识别

#### Order Type 强制参数（U本位合约/期货）

> 注意：期货使用不同的订单类型命名，与现货不同！

| Order Type | 强制必填参数 |
|------------|-------------|
| `LIMIT` | `quantity`, `price`, `timeInForce` |
| `MARKET` | `quantity` |
| `STOP` | `quantity`, `stopPrice` |
| `STOP_MARKET` | `stopPrice` |
| `TAKE_PROFIT` | `quantity`, `stopPrice` |
| `TAKE_PROFIT_MARKET` | `stopPrice` |
| `TRAILING_STOP_MARKET` | `callbackRate` |

#### Order Type 强制参数（现货）

> 注意：现货使用不同的订单类型命名，与期货不同！

| Order Type | 强制必填参数 |
|------------|-------------|
| `LIMIT` | `quantity`, `price`, `timeInForce` |
| `LIMIT_MAKER` | `quantity`, `price` |
| `MARKET` | `quantity` 或 `quoteOrderQty` |
| `STOP_LOSS` | `quantity`, `stopPrice` 或 `trailingDelta` |
| `STOP_LOSS_LIMIT` | `quantity`, `price`, `timeInForce`, `stopPrice` 或 `trailingDelta` |
| `TAKE_PROFIT` | `quantity`, `stopPrice` 或 `trailingDelta` |
| `TAKE_PROFIT_LIMIT` | `quantity`, `price`, `timeInForce`, `stopPrice` 或 `trailingDelta` |

#### 期货特有参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `positionSide` | string | 持仓方向：`BOTH`(默认), `LONG`, `SHORT` |
| `reduceOnly` | bool | 是否只减仓，默认 `false` |
| `priceMatch` | string | 价格匹配：`OPPONENT`, `QUEUE` 等 |
| `closePosition` | bool | 是否全平仓 |
| `activationPrice` | float | 触发价格（追踪止损） |
| `callbackRate` | float | 回调比例（0.1-10） |
| `workingType` | string | 触发价格类型：`MARK_PRICE`, `CONTRACT_PRICE` |
| `priceProtect` | bool | 价格保护 |

#### 现货特有参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `quoteOrderQty` | float | 报价数量（以USDT计价） |
| `icebergQty` | float | 冰山数量 |
| `trailingDelta` | int | 追踪Delta |
| `strategyId` | int | 策略ID |
| `strategyType` | int | 策略类型 |
| `selfTradePreventionMode` | string | 自成交预防模式 |
| `newOrderRespType` | string | 响应格式：ACK/RESULT/FULL（默认FULL） |

#### 订单ID说明

| 字段 | 说明 | 用途 |
|------|------|------|
| `requestId` | WS请求追踪ID（UUID格式） | 用于关联请求与响应 |
| `newClientOrderId` | 订单标识ID（UUID格式） | 创建订单时设置，用于追踪订单 |
| `origClientOrderId` | 客户端订单ID（原值） | 查询/取消订单时使用 |

> **重要**：取消和查询订单时使用 `origClientOrderId`（下单时传入的客户端订单ID），而非 `newClientOrderId`。

#### ORDER_DATA 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 固定值 `"order"` |
| `status` | string | 任务状态：`COMPLETED` / `FAILED` |
| `taskId` | int | order_tasks 表的任务 ID |
| `result` | object | 币安 API 返回的订单信息（成功时） |
| `payload` | object | 下单时传入的参数（用于前端回显） |
| `errorCode` | string | 错误码（失败时） |
| `errorMessage` | string | 错误信息（失败时） |

> **设计说明**：响应数据完全采用币安蛇形命名，与 [04-trading-orders.md](./04-trading-orders.md) 保持一致。

---

## 附录：快速模板

本章节提供标准化的 Pydantic 模型代码模板，帮助工程师快速编写数据模型。

### 1. 标准化 import 语句

```python
"""模型文件 docstring

参考文档: docs/backend/design/08-api-models.md
"""
import logging
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from ..base import CamelCaseModel, SnakeCaseModel

logger = logging.getLogger(__name__)
```

**导入顺序**：
1. 标准库（logging, datetime, enum, typing）
2. 第三方库（pydantic）
3. 本地模块（base, 其他 model）

---

### 2. 模型基类选择

| 场景 | 基类 | 说明 |
|------|------|------|
| **API 响应** | `CamelCaseModel` | 序列化时自动转 camelCase 给前端 |
| **请求接收** | `SnakeCaseModel` | 自动将前端 camelCase 转 snake_case |
| **数据库模型** | `CamelCaseModel` | 内部使用 snake_case，输出 camelCase |
| **枚举类型** | `StrEnum` | 推荐使用，Python 3.11+ 原生支持 |

---

### 3. Field 配置速查

```python
from pydantic import Field
from typing import Optional

class ExampleModel(CamelCaseModel):
    """模型说明 docstring"""

    # 必填字段（使用 ... 表示）
    required_field: str = Field(..., description="必填字段说明")

    # 可选字段（带默认值）
    optional_field: int = Field(default=0, description="可选字段，默认0")

    # 字符串字段，带长度限制
    name: str = Field(..., min_length=1, max_length=100, description="名称")

    # 数值字段，带范围限制
    price: float = Field(..., gt=0, le=1000000, description="价格")

    # 可选字段（使用 Optional 或 | None）
    description: Optional[str] = Field(default=None, description="描述")

    # 列表字段
    tags: list[str] = Field(default_factory=list, description="标签列表")

    # 字段验证器
    @field_validator('field_name')
    @classmethod
    def validate_field(cls, v):
        """字段验证器"""
        if not valid:
            raise ValueError('error message')
        return v
```

---

### 4. 完整模型示例

```python
class KlineBar(CamelCaseModel):
    """单根K线数据（OHLCV）

    用于 WebSocket 推送实时K线、K线历史数据。

    字段说明：
    - time: K线开始时间（秒，Unix时间戳）
    - open/high/low/close: 价格数据
    - volume: 成交量

    JSON 示例（前端接收）:
    {
        "time": 1704067200,
        "open": 50000.0,
        "high": 51000.0,
        "low": 49500.0,
        "close": 50500.0,
        "volume": 1234.56
    }
    """
    time: int = Field(..., description="K线开始时间（秒）")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: float = Field(..., description="成交量")


class OrderRequest(SnakeCaseModel):
    """订单创建请求

    用于接收前端创建的订单请求。

    字段说明：
    - symbol: 交易对符号
    - side: 买卖方向
    - type: 订单类型
    - quantity: 数量
    - price: 价格（LIMIT单必填）
    """
    symbol: str = Field(..., description="交易对符号，如 BTCUSDT")
    side: str = Field(..., description="订单方向：BUY 或 SELL")
    type: str = Field(..., description="订单类型：LIMIT, MARKET 等")
    quantity: float = Field(..., gt=0, description="订单数量")
    price: float | None = Field(default=None, description="价格（LIMIT单必填）")
    time_in_force: str | None = Field(default="GTC", description="时效：GTC/IOC/FOK")

    @field_validator('side')
    @classmethod
    def validate_side(cls, v):
        if v not in ('BUY', 'SELL'):
            raise ValueError('side must be BUY or SELL')
        return v
```

---

### 5. 常见模式

#### 5.1 枚举类型

```python
class OrderStatus(StrEnum):
    """订单状态"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
```

#### 5.2 嵌套模型

```python
class PositionInfo(CamelCaseModel):
    """持仓信息"""
    symbol: str = Field(..., description="交易对")
    position_amount: float = Field(default=0.0, description="持仓数量")
    unrealized_pnl: float = Field(default=0.0, description="未实现盈亏")


class FuturesAccountInfo(CamelCaseModel):
    """期货账户信息"""
    account_type: str = Field(default="FUTURES", description="账户类型")
    total_balance: float = Field(default=0.0, description="总余额")
    positions: list[PositionInfo] = Field(default_factory=list, description="持仓列表")
```

#### 5.3 计算属性

```python
from pydantic import computed_field

class AccountBalance(CamelCaseModel):
    """账户余额"""
    free: float = Field(default=0.0, description="可用数量")
    locked: float = Field(default=0.0, description="冻结数量")

    @computed_field
    @property
    def total(self) -> float:
        """总数量 = free + locked"""
        return self.free + self.locked
```

#### 5.4 响应包装

```python
class DeleteResponse(CamelCaseModel):
    """删除操作响应"""
    success: bool = Field(..., description="是否成功")
    deleted_id: int = Field(..., description="已删除记录的ID")
    message: str = Field(default="", description="附加消息")
```

---

### 6. 快速检查清单

编写新模型时，检查以下事项：

- [ ] 选择了正确的基类（CamelCaseModel / SnakeCaseModel）
- [ ] 必填字段使用 `Field(...)`
- [ ] 可选字段有合理的默认值
- [ ] 数值字段有合理的范围限制（gt, ge, lt, le）
- [ ] 字符串字段有长度限制（min_length, max_length）
- [ ] 添加了 docstring 说明模型用途
- [ ] 每个字段有 description
- [ ] 需要验证的字段添加了 `@field_validator`
- [ ] 导入了必要的类型（Optional, Any, list 等）

---

**版本**：v1.5
**更新**：2026-03-17 - 新增附录：快速模板章节，包含标准化import语句、Field配置速查、完整模型示例、常见模式
