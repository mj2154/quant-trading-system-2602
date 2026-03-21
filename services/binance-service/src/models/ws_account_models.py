"""
币安 WebSocket 账户数据模型

严格遵循文档: docs/backend/design/09-binance-models.md

包含:
- 现货账户持仓变化 WS (outboundAccountPosition)
- 现货余额更新 WS (balanceUpdate)
- 现货事件流终止 WS (eventStreamTerminated)
- 期货账户更新 WS (ACCOUNT_UPDATE)
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# 现货（SPOT）账户持仓变化 WS 模型
# =============================================================================


class BinanceSpotAccountPositionBalanceModel(BaseModel):
    """现货账户持仓 - 余额子模型

    文档来源: binance_spot_docs/User Data Stream.md
    """

    asset: str = Field(alias="a", description="资产名称")
    free: Decimal = Field(alias="f", description="可用余额")
    locked: Decimal = Field(alias="l", description="锁定余额")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotOutboundAccountPositionEvent(BaseModel):
    """现货账户持仓变化事件内容模型

    文档来源: binance_spot_docs/User Data Stream.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    last_update_time: int = Field(alias="u", description="最后更新时间")
    balances: list[BinanceSpotAccountPositionBalanceModel] = Field(
        alias="B", description="余额列表"
    )

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotOutboundAccountPositionWSModel(BaseModel):
    """现货账户持仓变化 WS 事件模型

    Stream: User Data Stream outboundAccountPosition 事件
    文档来源: binance_spot_docs/User Data Stream.md
    """

    subscription_id: int = Field(alias="subscriptionId", description="订阅 ID")
    event: BinanceSpotOutboundAccountPositionEvent = Field(description="事件内容")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 现货（SPOT）余额更新 WS 模型
# =============================================================================


class BinanceSpotBalanceUpdateEvent(BaseModel):
    """现货余额更新事件内容模型

    文档来源: binance_spot_docs/User Data Stream.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    asset: str = Field(alias="a", description="资产名称")
    balance_delta: Decimal = Field(alias="d", description="余额变动")
    clear_time: int = Field(alias="T", description="清算时间")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotBalanceUpdateWSModel(BaseModel):
    """现货余额更新 WS 事件模型

    Stream: User Data Stream balanceUpdate 事件
    文档来源: binance_spot_docs/User Data Stream.md
    """

    subscription_id: int = Field(alias="subscriptionId", description="订阅 ID")
    event: BinanceSpotBalanceUpdateEvent = Field(description="事件内容")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 现货（SPOT）事件流终止 WS 模型
# =============================================================================


class BinanceSpotEventStreamTerminatedEvent(BaseModel):
    """现货事件流终止事件内容模型

    文档来源: binance_spot_docs/User Data Stream.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotEventStreamTerminatedWSModel(BaseModel):
    """现货事件流终止 WS 事件模型

    Stream: User Data Stream eventStreamTerminated 事件
    文档来源: binance_spot_docs/User Data Stream.md
    """

    subscription_id: int = Field(alias="subscriptionId", description="订阅 ID")
    event: BinanceSpotEventStreamTerminatedEvent = Field(description="事件内容")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 现货（SPOT）外部锁定更新 WS 模型
# =============================================================================


class BinanceSpotExternalLockUpdateEvent(BaseModel):
    """现货外部锁定更新事件内容模型

    文档来源: binance_spot_docs/User Data Stream.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    asset: str = Field(alias="a", description="资产名称")
    delta: Decimal = Field(alias="d", description="变动数量")
    transaction_time: int = Field(alias="T", description="交易时间")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotExternalLockUpdateWSModel(BaseModel):
    """现货外部锁定更新 WS 事件模型

    Stream: User Data Stream externalLockUpdate 事件
    文档来源: binance_spot_docs/User Data Stream.md
    """

    subscription_id: int = Field(alias="subscriptionId", description="订阅 ID")
    event: BinanceSpotExternalLockUpdateEvent = Field(description="事件内容")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 期货（FUTURES）账户更新 WS 模型
# =============================================================================


class BinanceFuturesAccountUpdateBalanceModel(BaseModel):
    """期货账户更新 - 余额子模型

    文档来源: binance_futures_docs/01_U本位合约/02_Websocket账户信息推送/Balance和Position更新推送.md
    """

    asset: str = Field(alias="a", description="资产名称")
    wallet_balance: Decimal = Field(alias="wb", description="钱包余额")
    cross_wallet_balance: Decimal = Field(alias="cw", description="跨账户钱包余额")
    balance_change: Decimal = Field(alias="bc", description="余额变动（不含盈亏和手续费）")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesAccountUpdatePositionModel(BaseModel):
    """期货账户更新 - 持仓子模型

    文档来源: binance_futures_docs/01_U本位合约/02_Websocket账户信息推送/Balance和Position更新推送.md
    """

    symbol: str = Field(alias="s", description="交易对")
    position_amt: Decimal = Field(alias="pa", description="持仓数量")
    entry_price: Decimal = Field(alias="ep", description="入场价格")
    break_even_price: Decimal = Field(alias="bep", description="盈亏平衡价格")
    accumulated_realized: Decimal = Field(
        alias="cr", description="累计已实现盈亏（费前）"
    )
    unrealized_profit: Decimal = Field(alias="up", description="未实现盈亏")
    margin_type: str = Field(alias="mt", description="保证金类型")
    isolated_wallet: Decimal = Field(alias="iw", description="逐仓钱包余额")
    position_side: str = Field(alias="ps", description="持仓方向")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesAccountUpdateDataModel(BaseModel):
    """期货账户更新 - 更新数据子模型

    文档来源: binance_futures_docs/01_U本位合约/02_Websocket账户信息推送/Balance和Position更新推送.md
    """

    update_reason: str = Field(alias="m", description="更新原因类型")
    balances: list[BinanceFuturesAccountUpdateBalanceModel] = Field(
        alias="B", description="余额列表"
    )
    positions: list[BinanceFuturesAccountUpdatePositionModel] = Field(
        alias="P", description="持仓列表"
    )

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesAccountUpdateWSModel(BaseModel):
    """期货账户更新 WS 事件模型

    Stream: User Data Stream ACCOUNT_UPDATE 事件
    文档来源: binance_futures_docs/01_U本位合约/02_Websocket账户信息推送/Balance和Position更新推送.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    transaction_time: int = Field(alias="T", description="交易时间")
    update_data: BinanceFuturesAccountUpdateDataModel = Field(
        alias="a", description="更新数据"
    )

    model_config = ConfigDict(populate_by_name=True)
