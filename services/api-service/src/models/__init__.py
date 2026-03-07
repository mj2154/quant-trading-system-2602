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
# 账户信息模型
from .db.account_models import (
    AccountBalance,
    AccountInfoCreate,
    AccountInfoListResponse,
    AccountInfoResponse,
    AccountInfoUpdate,
    FuturesAccountInfo,
    PositionInfo,
    SpotAccountInfo,
)

# 告警配置模型
from .db.alert_config_models import (
    AlertSignalCreate,
    AlertSignalListResponse,
    AlertSignalResponse,
    AlertSignalUpdate,
    CreateAlertSignalRequest,
    DeleteAlertSignalRequest,
    EnableAlertSignalRequest,
    EnableDisableResponse,
    ListAlertSignalsRequest,
    UpdateAlertSignalRequest,
)

# 交易所信息模型
from .db.exchange_models import (
    ExchangeInfo,
    RichExchangeInfo,
    SymbolMetadata,
)

# K线历史模型
from .db.kline_history_models import (
    KlineCreate,
    KlineData,
    KLineHistoryQuery,
    KLineHistoryResponse,
    KlineInterval,
    KlineResponse,
    KlineWebSocket,
)

# 实时数据/订阅模型
from .db.realtime_data_models import (
    BatchSubscriptionResult,
    ClientSubscriptions,
    ExchangeSubscriptions,
    ProductTypeInfo,
    SubscriptionBatch,
    SubscriptionChange,
    SubscriptionInfo,
    SubscriptionKey,
    SubscriptionRequest,
    SubscriptionStats,
    SubscriptionValidation,
)

# 信号模型（仅保留启用/禁用响应）
# EnableDisableResponse 已在 alert_config_models 中导入
from .db.task_models import (
    TaskCreate,
    TaskResponse,
    TaskStatus,
    TaskType,
    TaskUpdate,
    UnifiedTaskPayload,
    convert_legacy_task_type,
)

# ==================== 错误模型 ====================
from .error_models import (
    ACCOUNT_ERROR,
    AUTHENTICATION_ERROR,
    BINANCE_ERROR_CODES,
    RATE_LIMIT_ERROR,
    SIGNATURE_ERROR,
    TIMESTAMP_ERROR,
    AuthenticationError,
    BinanceAPIError,
    ErrorCode,
    ErrorMessage,
    RateLimitError,
    SignatureError,
    TimestampError,
    create_binance_error,
)

# 协议常量
from .protocol.constants import (
    INTERVAL_TO_RESOLUTION,
    PING_INTERVAL,
    PING_TIMEOUT,
    PROTOCOL_VERSION,
    RESOLUTION_TO_INTERVAL,
    WS_PATH,
    WS_USER_DATA_PATH,
    ProductType,
    SubscriptionType,
    WSAction,
    WSErrorCode,
    WSMessageType,
)

# ==================== 协议层模型 ====================
# WebSocket消息协议
from .protocol.ws_message import (
    ConfigRequest,
    KlinesRequest,
    MessageAck,
    MessageError,
    MessageRequest,
    MessageResponse,
    MessageResponseBase,
    MessageSuccess,
    MessageUpdate,
    MetricsRequest,
    QuotesRequest,
    ResolveSymbolRequest,
    SearchSymbolsRequest,
    ServerTimeRequest,
    SubscribeRequest,
    SubscriptionsRequest,
    UnsubscribeRequest,
    WebSocketMessage,
)

# WebSocket载荷模型
from .protocol.ws_payload import (
    ConfigData,
    # 别名
    ConfigResponse,
    ErrorData,
    KlinesResponse,
    MetricsData,
    MetricsResponse,
    QuotesResponse,
    ResolveSymbolData,
    ResolveSymbolResponse,
    SearchSymbolsData,
    SearchSymbolsResponse,
    ServerTimeData,
    ServerTimeResponse,
    SubscribeData,
    SubscribeResponse,
    SubscriptionsData,
    SubscriptionsResponse,
    TaskResultData,
    UnsubscribeData,
    UnsubscribeResponse,
)
from .protocol.ws_payload import (
    SubscriptionInfo as WSSubscriptionInfo,
)

# 期货模型
from .trading.futures_models import (
    FUTURES_RESOLUTIONS,
    FUTURES_SUBSCRIPTION_TYPES,
    FundingRateData,
    FuturesSymbolInfo,
    MarkPriceData,
    OpenInterestData,
    OpenInterestStatsData,
    PremiumIndexData,
)

# ==================== 交易相关模型 ====================
# K线模型
# 注意：KlineData 和 KlineResponse 已在 db/kline_history_models 中导入，避免重复定义
from .trading.kline_models import (
    KlineBar,
    KlineBars,
    KlineMeta,
    KlinesData,
    WSKlineData,
)

# 报价模型
from .trading.quote_models import (
    OrderBookData,
    PriceLevel,
    QuotesData,
    QuotesList,
    QuotesValue,
)

# 交易对模型
from .trading.symbol_models import (
    SymbolInfo,
    SymbolSearchResult,
    SymbolSearchResults,
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
    "KlineBars",
    "KlineData",
    "KlineMeta",
    "KlineResponse",
    "KlineCreate",
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
    "ConfigResponse",
    "KlinesResponse",
    "MetricsResponse",
    "QuotesResponse",
    "ResolveSymbolResponse",
    "SearchSymbolsResponse",
    "ServerTimeResponse",
    "SubscribeResponse",
    "SubscriptionsResponse",
    "UnsubscribeResponse",
    "SearchSymbolsData",
    "ResolveSymbolData",
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
