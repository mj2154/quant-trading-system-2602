# API 服务数据模型

本文档记录 API 服务（`services/api-service/src/models/`）中所有的 Pydantic 数据模型。

## 模型目录结构

```
models/
├── trading/               # 交易数据模型（前端数据格式）
│   ├── kline_models.py           # K线数据
│   ├── symbol_models.py          # 交易对信息
│   ├── quote_models.py           # 报价/深度数据
│   └── futures_models.py         # 期货扩展数据
│
├── db/                    # 数据库表对应模型
│   ├── task_models.py           # 任务模型
│   ├── realtime_data_models.py  # 订阅/实时数据
│   ├── kline_history_models.py # K线历史
│   ├── account_models.py        # 账户信息
│   ├── exchange_models.py       # 交易所信息
│   ├── alert_config_models.py   # 告警配置
│   └── signal_models.py         # 信号模型（仅启用/禁用响应）
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
| `SubscriptionInfo` | 订阅详情 | `client_id`, `subscription_key`, `symbol`, `subscription_type`, `created_at` |
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
| `KlineData` | K线数据（数据库） | `symbol`, `interval`, `open_time`, `close_time`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`, `quote_volume`, `number_of_trades` |
| `KlineCreate` | K线创建 | 与 KlineData 类似，用于插入数据库 |
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
| `SpotAccountInfo` | 现货账户 | `account_type`, `balances[]`, `update_time` |
| `FuturesAccountInfo` | 期货账户 | `account_type`, `assets[]`, `positions[]`, `update_time` |
| `AccountBalance` | 账户余额 | `asset`, `free`, `locked` |
| `PositionInfo` | 持仓信息 | `symbol`, `entry_price`, `mark_price`, `quantity`, `unrealized_pnl` |

**使用场景**：
- `account_info` 表操作
- 账户信息查询和推送

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
| `AlertSignalCreate` | 告警创建 | `id`, `name`, `description`, `strategy_type`, `symbol`, `interval`, `is_enabled`, `created_by` |
| `AlertSignalUpdate` | 告警更新 | `name`, `description`, `is_enabled` |
| `AlertSignalResponse` | 告警响应 | `id`, `name`, `description`, `strategy_type`, `symbol`, `interval`, `is_enabled`, `created_at`, `updated_at` |
| `AlertSignalListResponse` | 告警列表 | `items[]`, `total` |
| `EnableDisableResponse` | 启用/禁用响应 | `id`, `name`, `is_enabled`, `message` |
| `CreateAlertSignalRequest` | 创建请求 | `type`, `id`, `name`, `description`, `strategy_type`, `symbol`, `interval` |
| `ListAlertSignalsRequest` | 列表请求 | `type`, `symbol`, `is_enabled`, `limit`, `offset` |
| `UpdateAlertSignalRequest` | 更新请求 | `type`, `id`, `name`, `description`, `is_enabled` |
| `DeleteAlertSignalRequest` | 删除请求 | `type`, `id` |
| `EnableAlertSignalRequest` | 启用请求 | `type`, `id` |

**使用场景**：
- 告警配置 CRUD 操作（通过 WebSocket 消息）
- 告警启用/禁用

### signal_models.py - 信号模型

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| `EnableDisableResponse` | 启用/禁用响应 | `id`, `name`, `is_enabled`, `message` |

**说明**：API 服务只负责接收信号通知（通过 WebSocket），不存储或管理信号。信号由 signal-service 处理。

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
| `ConfigData` | 配置数据 | `supports_search`, `supports_group_request`, `supported_resolutions[]` |
| `SearchSymbolsData` | 搜索数据 | `symbols[]`, `total` |
| `ServerTimeData` | 时间数据 | `server_time`, `timezone` |
| `SubscribeData` | 订阅确认 | `subscriptions[]` |
| `UnsubscribeData` | 取消确认 | `subscriptions[]` |
| `SubscriptionsData` | 订阅列表 | `subscriptions[]` |
| `MetricsData` | 指标数据 | `active_connections`, `total_subscriptions` |
| `ErrorData` | 错误数据 | `code`, `message` |
| `TaskResultData` | 任务结果 | `task_id`, `result` |
| `SubscriptionInfo` | 订阅信息 | `symbol`, `subscriptions[]` |

**使用场景**：
- 响应消息中的 data 字段内容定义

### constants.py - 协议常量

| 常量名称 | 用途 | 值 |
|---------|------|-----|
| `PROTOCOL_VERSION` | 协议版本 | `"2.0"` |
| `WS_PATH` | WebSocket 路径 | `"/ws/market"` |
| `WS_USER_DATA_PATH` | 用户数据路径 | `"/ws/user"` |
| `PING_INTERVAL` | 心跳间隔 | `20` 秒 |
| `PING_TIMEOUT` | 心跳超时 | `60` 秒 |
| `WSAction` | 动作枚举 | `GET`, `SUBSCRIBE`, `UNSUBSCRIBE` |
| `WSMessageType` | 消息类型 | `CONFIG`, `SEARCH_SYMBOLS`, `KLINES` 等 |
| `SubscriptionType` | 订阅类型 | `KLINE`, `QUOTES`, `TRADE`, `ACCOUNT` |
| `ProductType` | 产品类型 | `SPOT`, `FUTURES`, `PERPETUAL` |
| `WSErrorCode` | 错误码 | `UNKNOWN`, `INVALID_REQUEST`, `AUTH_REQUIRED` 等 |
| `RESOLUTION_TO_INTERVAL` | 分辨率→间隔 | TV分辨率到数据库间隔的映射 |
| `INTERVAL_TO_RESOLUTION` | 间隔→分辨率 | 数据库间隔到TV分辨率的映射 |

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

**版本**：v1.1
**更新**：2026-02-28 - 修复模型字段描述错误，对比实际代码更正 SymbolInfo、QuotesValue、ExchangeInfo、RichExchangeInfo、FuturesModel 等模型字段；新增 base.py 基础类说明
