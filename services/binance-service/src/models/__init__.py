"""数据模型模块"""

from .base import SnakeCaseModel, CamelCaseModel
from .kline_models import (
    BinanceSpotKlineGetModel,
    BinanceSpotKlineWSData,
    BinanceSpotKlineWSModel,
    BinanceFuturesKlineGetModel,
    BinanceFuturesKlineWSData,
    BinanceFuturesKlineWSModel,
)
from .ticker_models import (
    BinanceSpotTicker24hrGetModel,
    BinanceSpotTicker24hrWSModel,
    BinanceFuturesTicker24hrGetModel,
    BinanceFuturesTicker24hrWSModel,
)
from .internal_models import (
    InternalKlineData as InternalKlineDataAlias,
    InternalQuoteValues,
    InternalQuoteData,
    InternalQuotesResult,
)
from .exchange_info_models import (
    BinanceSpotExchangeInfoRateLimitModel,
    BinanceSpotExchangeInfoSymbolFilterModel,
    BinanceSpotExchangeInfoSymbolModel,
    BinanceSpotExchangeInfoSorModel,
    BinanceSpotExchangeInfoGetModel,
    BinanceFuturesExchangeInfoRateLimitModel,
    BinanceFuturesExchangeInfoAssetModel,
    BinanceFuturesExchangeInfoSymbolFilterModel,
    BinanceFuturesExchangeInfoSymbolModel,
    BinanceFuturesExchangeInfoGetModel,
    MarketType,
    ExchangeInfo,
)
from .account_models import (
    BinanceSpotAccountCommissionRateModel,
    BinanceSpotAccountBalanceModel,
    BinanceSpotAccountGetModel,
    BinanceFuturesAccountAssetModel,
    BinanceFuturesAccountPositionModel,
    BinanceFuturesAccountGetModel,
)
from .order_models import (
    BinanceSpotExecutionReportEvent,
    BinanceSpotExecutionReportWSModel,
    BinanceFuturesOrderDataModel,
    BinanceFuturesOrderTradeUpdateWSModel,
    BinanceSpotOrderPlaceResult,
    BinanceSpotOrderAmendResult,
    BinanceFuturesOrderPlaceResult,
    BinanceFuturesModifyOrderResult,
    BinanceSpotWsOrderRequest,
    BinanceFuturesWsOrderRequest,
    BinanceSpotFillModel,
)
from .ws_account_models import (
    BinanceSpotAccountPositionBalanceModel,
    BinanceSpotOutboundAccountPositionEvent,
    BinanceSpotOutboundAccountPositionWSModel,
    BinanceSpotBalanceUpdateEvent,
    BinanceSpotBalanceUpdateWSModel,
    BinanceSpotEventStreamTerminatedEvent,
    BinanceSpotEventStreamTerminatedWSModel,
    BinanceSpotExternalLockUpdateEvent,
    BinanceSpotExternalLockUpdateWSModel,
    BinanceFuturesAccountUpdateBalanceModel,
    BinanceFuturesAccountUpdatePositionModel,
    BinanceFuturesAccountUpdateDataModel,
    BinanceFuturesAccountUpdateWSModel,
)
from .ws_message import WSSubscribeRequest, WSUnsubscribeRequest, WSResponse

__all__ = [
    # 基类
    "SnakeCaseModel",
    "CamelCaseModel",
    # 现货 K线
    "BinanceSpotKlineGetModel",
    "BinanceSpotKlineWSData",
    "BinanceSpotKlineWSModel",
    # 期货 K线
    "BinanceFuturesKlineGetModel",
    "BinanceFuturesKlineWSData",
    "BinanceFuturesKlineWSModel",
    # 现货 24hr Ticker
    "BinanceSpotTicker24hrGetModel",
    "BinanceSpotTicker24hrWSModel",
    # 期货 24hr Ticker
    "BinanceFuturesTicker24hrGetModel",
    "BinanceFuturesTicker24hrWSModel",
    # 现货交易所信息
    "BinanceSpotExchangeInfoRateLimitModel",
    "BinanceSpotExchangeInfoSymbolFilterModel",
    "BinanceSpotExchangeInfoSymbolModel",
    "BinanceSpotExchangeInfoSorModel",
    "BinanceSpotExchangeInfoGetModel",
    # 期货交易所信息
    "BinanceFuturesExchangeInfoRateLimitModel",
    "BinanceFuturesExchangeInfoAssetModel",
    "BinanceFuturesExchangeInfoSymbolFilterModel",
    "BinanceFuturesExchangeInfoSymbolModel",
    "BinanceFuturesExchangeInfoGetModel",
    # 市场类型和数据库模型
    "MarketType",
    "ExchangeInfo",
    # 现货账户信息
    "BinanceSpotAccountCommissionRateModel",
    "BinanceSpotAccountBalanceModel",
    "BinanceSpotAccountGetModel",
    # 期货账户信息
    "BinanceFuturesAccountAssetModel",
    "BinanceFuturesAccountPositionModel",
    "BinanceFuturesAccountGetModel",
    # 现货订单执行报告 WS
    "BinanceSpotExecutionReportEvent",
    "BinanceSpotExecutionReportWSModel",
    # 期货订单成交更新 WS
    "BinanceFuturesOrderDataModel",
    "BinanceFuturesOrderTradeUpdateWSModel",
    # WebSocket 交易响应模型
    "BinanceSpotOrderPlaceResult",
    "BinanceSpotOrderAmendResult",
    "BinanceFuturesOrderPlaceResult",
    "BinanceFuturesModifyOrderResult",
    # WebSocket 交易请求模型
    "BinanceSpotWsOrderRequest",
    "BinanceFuturesWsOrderRequest",
    # 现货成交明细模型
    "BinanceSpotFillModel",
    # 现货 WS 账户模型
    "BinanceSpotAccountPositionBalanceModel",
    "BinanceSpotOutboundAccountPositionEvent",
    "BinanceSpotOutboundAccountPositionWSModel",
    "BinanceSpotBalanceUpdateEvent",
    "BinanceSpotBalanceUpdateWSModel",
    "BinanceSpotEventStreamTerminatedEvent",
    "BinanceSpotEventStreamTerminatedWSModel",
    "BinanceSpotExternalLockUpdateEvent",
    "BinanceSpotExternalLockUpdateWSModel",
    # 期货 WS 账户模型
    "BinanceFuturesAccountUpdateBalanceModel",
    "BinanceFuturesAccountUpdatePositionModel",
    "BinanceFuturesAccountUpdateDataModel",
    "BinanceFuturesAccountUpdateWSModel",
    # WebSocket 消息模型
    "WSSubscribeRequest",
    "WSUnsubscribeRequest",
    "WSResponse",
    # 内部数据模型
    "InternalKlineData",
    "InternalQuoteValues",
    "InternalQuoteData",
    "InternalQuotesResult",
]
