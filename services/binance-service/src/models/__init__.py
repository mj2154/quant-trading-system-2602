"""数据模型模块"""

from .base import SnakeCaseModel, CamelCaseModel
from .kline_models import (
    KlineData,
    KlineCreate,
    KlineResponse,
    KlineWebSocket,
    KlineWebSocketData,
    KlineInterval,
)
from .ticker import (
    Ticker24hrSpot,
    Ticker24hrFutures,
    WebSocketTickerSpot,
    WebSocketTickerFutures,
)
from .exchange_info import (
    ExchangeInfo,
    ExchangeInfoSymbol,
    ExchangeInfoResponse,
    PriceFilter,
    LotSizeFilter,
    MinNotionalFilter,
    MarketType,
    ExchangeInfoStatus,
)
from .task import (
    UnifiedTaskPayload,
    TaskActions,
    convert_legacy_task_type,
)
from .spot_account import (
    SpotAccountInfo,
    CommissionRates,
    Balance,
)
from .futures_account import (
    FuturesAccountInfo,
    FuturesAsset,
    FuturesPosition,
)
from .ws_message import (
    WSRequest,
    WSSubscribeRequest,
    WSUnsubscribeRequest,
)

__all__ = [
    # 基类
    "SnakeCaseModel",
    "CamelCaseModel",
    # K线数据模型
    "KlineData",
    "KlineCreate",
    "KlineResponse",
    "KlineWebSocket",
    "KlineWebSocketData",
    "KlineInterval",
    # 24hr Ticker模型
    "Ticker24hrSpot",
    "Ticker24hrFutures",
    "WebSocketTickerSpot",
    "WebSocketTickerFutures",
    # 交易所信息模型
    "ExchangeInfo",
    "ExchangeInfoSymbol",
    "ExchangeInfoResponse",
    "PriceFilter",
    "LotSizeFilter",
    "MinNotionalFilter",
    "MarketType",
    "ExchangeInfoStatus",
    # 账户模型
    "SpotAccountInfo",
    "FuturesAccountInfo",
    "CommissionRates",
    "Balance",
    "FuturesAsset",
    "FuturesPosition",
    # 任务模型
    "UnifiedTaskPayload",
    "TaskActions",
    "convert_legacy_task_type",
    # WebSocket消息模型
    "WSRequest",
    "WSSubscribeRequest",
    "WSUnsubscribeRequest",
]
