"""
数据模型模块

包含所有Pydantic数据模型，按功能模块组织：

## 数据库表对应模型 (db/)
- task_models.py - 任务模型
- realtime_data_models.py - 实时数据/订阅模型
- kline_history_models.py - K线历史模型
- account_models.py - 账户信息模型
- exchange_models.py - 交易所信息模型
- alert_config_models.py - 告警配置模型
- signal_models.py - 信号模型

## 交易相关模型 (trading/)
- kline_models.py - K线数据模型
- symbol_models.py - 交易对模型
- quote_models.py - 报价数据模型
- futures_models.py - 期货扩展模型

## 协议层模型 (protocol/)
- ws_message.py - WebSocket消息协议
- ws_payload.py - WebSocket数据载荷
- constants.py - 协议常量

## 错误模型
- error_models.py - 错误码和错误类

作者: Claude Code
版本: v2.0.0
"""

# ==================== 数据库表对应模型 ====================

# 任务模型
from .db.task_models import (
    UnifiedTaskPayload,
    TaskType,
    TaskStatus,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    convert_legacy_task_type,
)

# 实时数据/订阅模型
from .db.realtime_data_models import (
    SubscriptionKey,
    SubscriptionInfo,
    ClientSubscriptions,
    ExchangeSubscriptions,
    SubscriptionChange,
    SubscriptionStats,
    ProductTypeInfo,
    SubscriptionRequest,
    SubscriptionBatch,
    SubscriptionValidation,
    BatchSubscriptionResult,
)

# K线历史模型
from .db.kline_history_models import (
    KlineData,
    KlineCreate,
    KlineResponse,
    KlineWebSocket,
    KlineInterval,
    KLineHistoryQuery,
    KLineHistoryResponse,
)

# 账户信息模型
from .db.account_models import (
    AccountInfoCreate,
    AccountInfoUpdate,
    AccountInfoResponse,
    AccountInfoListResponse,
    SpotAccountInfo,
    FuturesAccountInfo,
    AccountBalance,
    PositionInfo,
)

# 交易所信息模型
from .db.exchange_models import (
    ExchangeInfo,
    RichExchangeInfo,
    SymbolMetadata,
)

# 告警配置模型
from .db.alert_config_models import (
    AlertSignalCreate,
    AlertSignalUpdate,
    AlertSignalResponse,
    AlertSignalListResponse,
    EnableDisableResponse,
    CreateAlertSignalRequest,
    ListAlertSignalsRequest,
    UpdateAlertSignalRequest,
    DeleteAlertSignalRequest,
    EnableAlertSignalRequest,
)

# 信号模型（仅保留启用/禁用响应）
from .db.signal_models import (
    EnableDisableResponse,
)

# ==================== 交易相关模型 ====================

# K线模型
from .trading.kline_models import (
    KlineBar,
    KlineData,
    KlineBars,
    KlineMeta,
    KlineResponse,
    KlinesData,
    WSKlineData,
)

# 交易对模型
from .trading.symbol_models import (
    SymbolInfo,
    SymbolSearchResult,
    SymbolSearchResults,
)

# 报价模型
from .trading.quote_models import (
    QuotesValue,
    QuotesData,
    QuotesList,
    PriceLevel,
    OrderBookData,
)

# 期货模型
from .trading.futures_models import (
    MarkPriceData,
    FundingRateData,
    OpenInterestData,
    FuturesSymbolInfo,
    PremiumIndexData,
    OpenInterestStatsData,
    FUTURES_SUBSCRIPTION_TYPES,
    FUTURES_RESOLUTIONS,
)

# ==================== 协议层模型 ====================

# WebSocket消息协议
from .protocol.ws_message import (
    WebSocketMessage,
    MessageRequest,
    ConfigRequest,
    SearchSymbolsRequest,
    ResolveSymbolRequest,
    KlinesRequest,
    ServerTimeRequest,
    QuotesRequest,
    SubscribeRequest,
    UnsubscribeRequest,
    SubscriptionsRequest,
    MetricsRequest,
    MessageResponseBase,
    MessageResponse,
    MessageSuccess,
    MessageAck,
    MessageError,
    MessageUpdate,
)

# WebSocket载荷模型
from .protocol.ws_payload import (
    ConfigData,
    SearchSymbolsData,
    ServerTimeData,
    SubscribeData,
    UnsubscribeData,
    SubscriptionsData,
    MetricsData,
    ErrorData,
    TaskResultData,
    SubscriptionInfo as WSSubscriptionInfo,
    # 别名
    ConfigResponse,
    SearchSymbolsResponse,
    ResolveSymbolData,
    ResolveSymbolResponse,
    KlinesResponse,
    ServerTimeResponse,
    QuotesResponse,
    SubscriptionsResponse,
    MetricsResponse,
    SubscribeResponse,
    UnsubscribeResponse,
)

# 协议常量
from .protocol.constants import (
    PROTOCOL_VERSION,
    WS_PATH,
    WS_USER_DATA_PATH,
    PING_INTERVAL,
    PING_TIMEOUT,
    WSAction,
    WSMessageType,
    SubscriptionType,
    ProductType,
    WSErrorCode,
    RESOLUTION_TO_INTERVAL,
    INTERVAL_TO_RESOLUTION,
)

# ==================== 错误模型 ====================

from .error_models import (
    ErrorCode,
    ErrorMessage,
    BINANCE_ERROR_CODES,
    BinanceAPIError,
    AuthenticationError,
    RateLimitError,
    TimestampError,
    SignatureError,
    ACCOUNT_ERROR,
    AUTHENTICATION_ERROR,
    TIMESTAMP_ERROR,
    RATE_LIMIT_ERROR,
    SIGNATURE_ERROR,
    create_binance_error,
)

# ==================== 统一导出 ====================

__all__ = [
    # 协议版本
    "PROTOCOL_VERSION",
    "WS_PATH",
    "WS_USER_DATA_PATH",
    "PING_INTERVAL",
    "PING_TIMEOUT",

    # 任务模型
    "UnifiedTaskPayload",
    "TaskType",
    "TaskStatus",
    "TaskCreate",
    "TaskResponse",
    "TaskUpdate",
    "convert_legacy_task_type",

    # 订阅模型
    "SubscriptionKey",
    "SubscriptionInfo",
    "ClientSubscriptions",
    "ExchangeSubscriptions",
    "SubscriptionChange",
    "SubscriptionStats",
    "ProductTypeInfo",
    "SubscriptionRequest",
    "SubscriptionBatch",
    "SubscriptionValidation",
    "BatchSubscriptionResult",

    # K线模型
    "KlineBar",
    "KlineData",
    "KlineBars",
    "KlineMeta",
    "KlineResponse",
    "KlineData",
    "KlineCreate",
    "KlineResponse",
    "KlineWebSocket",
    "KlineInterval",
    "KLineHistoryQuery",
    "KLineHistoryResponse",
    "KlinesData",
    "WSKlineData",

    # 账户模型
    "AccountInfoCreate",
    "AccountInfoUpdate",
    "AccountInfoResponse",
    "AccountInfoListResponse",
    "SpotAccountInfo",
    "FuturesAccountInfo",
    "AccountBalance",
    "PositionInfo",

    # 交易所模型
    "ExchangeInfo",
    "RichExchangeInfo",
    "SymbolMetadata",

    # 告警配置模型
    "AlertSignalCreate",
    "AlertSignalUpdate",
    "AlertSignalResponse",
    "AlertSignalListResponse",
    "EnableDisableResponse",
    "CreateAlertSignalRequest",
    "ListAlertSignalsRequest",
    "UpdateAlertSignalRequest",
    "DeleteAlertSignalRequest",
    "EnableAlertSignalRequest",

    # 信号模型
    "StrategyConfigCreate",
    "StrategyConfigUpdate",
    "StrategyConfigResponse",
    # 信号模型（仅启用/禁用响应）
    "EnableDisableResponse",

    # 交易对模型
    "SymbolInfo",
    "SymbolSearchResult",
    "SymbolSearchResults",

    # 报价模型
    "QuotesValue",
    "QuotesData",
    "QuotesList",
    "PriceLevel",
    "OrderBookData",

    # 期货模型
    "MarkPriceData",
    "FundingRateData",
    "OpenInterestData",
    "FuturesSymbolInfo",
    "PremiumIndexData",
    "OpenInterestStatsData",
    "FUTURES_SUBSCRIPTION_TYPES",
    "FUTURES_RESOLUTIONS",

    # WebSocket消息协议
    "WebSocketMessage",
    "MessageRequest",
    "ConfigRequest",
    "SearchSymbolsRequest",
    "ResolveSymbolRequest",
    "KlinesRequest",
    "ServerTimeRequest",
    "QuotesRequest",
    "SubscribeRequest",
    "UnsubscribeRequest",
    "SubscriptionsRequest",
    "MetricsRequest",
    "MessageResponseBase",
    "MessageResponse",
    "MessageSuccess",
    "MessageAck",
    "MessageError",
    "MessageUpdate",

    # WebSocket载荷
    "ConfigData",
    "SearchSymbolsData",
    "ServerTimeData",
    "SubscribeData",
    "UnsubscribeData",
    "SubscriptionsData",
    "MetricsData",
    "ErrorData",
    "TaskResultData",
    "WSSubscriptionInfo",

    # 协议常量
    "WSAction",
    "WSMessageType",
    "SubscriptionType",
    "ProductType",
    "WSErrorCode",
    "RESOLUTION_TO_INTERVAL",
    "INTERVAL_TO_RESOLUTION",

    # 错误模型
    "ErrorCode",
    "ErrorMessage",
    "BINANCE_ERROR_CODES",
    "BinanceAPIError",
    "AuthenticationError",
    "RateLimitError",
    "TimestampError",
    "SignatureError",
    "ACCOUNT_ERROR",
    "AUTHENTICATION_ERROR",
    "TIMESTAMP_ERROR",
    "RATE_LIMIT_ERROR",
    "SIGNATURE_ERROR",
    "create_binance_error",
]
