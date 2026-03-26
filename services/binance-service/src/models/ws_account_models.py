"""
币安 WebSocket 账户数据模型

严格遵循文档: docs/backend/design/09-binance-models.md

包含:
- 现货账户持仓变化 WS (outboundAccountPosition)
- 现货余额更新 WS (balanceUpdate)
- 现货事件流终止 WS (eventStreamTerminated)
- 现货外部锁定更新 WS (externalLockUpdate)
- 现货订单列表状态 WS (listStatus)
- 期货账户更新 WS (ACCOUNT_UPDATE)
- 期货简化交易 WS (TRADE_LITE)
- 期货保证金追缴 WS (MARGIN_CALL)
- 期货条件单更新 WS (ALGO_UPDATE)
- 期货策略更新 WS (STRATEGY_UPDATE)
- 期货网格更新 WS (GRID_UPDATE)
- 期货条件单触发拒绝 WS (CONDITIONAL_ORDER_TRIGGER_REJECT)
- 期货账户配置更新 WS (ACCOUNT_CONFIG_UPDATE)
- 期货 ListenKey 过期 WS (listenKeyExpired)
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


# =============================================================================
# 现货（SPOT）订单列表状态 WS 模型
# =============================================================================


class BinanceSpotListStatusOrderModel(BaseModel):
    """现货订单列表状态 - 订单子模型

    文档来源: binance_spot_docs/User Data Stream.md
    """

    symbol: str = Field(alias="s", description="交易对")
    order_id: int = Field(alias="i", description="订单 ID")
    client_order_id: str = Field(alias="c", description="客户端订单 ID")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotListStatusEvent(BaseModel):
    """现货订单列表状态事件内容模型

    文档来源: binance_spot_docs/User Data Stream.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    symbol: str = Field(alias="s", description="交易对")
    order_list_id: int = Field(alias="g", description="订单列表 ID")
    contingency_type: str = Field(alias="c", description="关联类型")
    list_status_type: str = Field(alias="l", description="列表状态类型")
    list_order_status: str = Field(alias="L", description="列表订单状态")
    list_reject_reason: str = Field(alias="r", description="列表拒绝原因")
    list_client_order_id: str = Field(alias="C", description="列表客户端订单 ID")
    transaction_time: int = Field(alias="T", description="成交时间")
    orders: list[BinanceSpotListStatusOrderModel] = Field(
        alias="O", description="订单列表"
    )

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotListStatusWSModel(BaseModel):
    """现货订单列表状态 WS 事件模型

    Stream: User Data Stream listStatus 事件
    文档来源: binance_spot_docs/User Data Stream.md
    """

    subscription_id: int = Field(alias="subscriptionId", description="订阅 ID")
    event: BinanceSpotListStatusEvent = Field(description="事件内容")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 期货（FUTURES）简化交易 WS 模型
# =============================================================================


class BinanceFuturesTradeLiteWSModel(BaseModel):
    """期货简化交易 WS 事件模型

    Stream: User Data Stream TRADE_LITE 事件
    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-Trade-Lite.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    transaction_time: int = Field(alias="T", description="交易时间")
    symbol: str = Field(alias="s", description="交易对")
    original_quantity: Decimal = Field(alias="q", description="原始数量")
    original_price: Decimal = Field(alias="p", description="原始价格")
    is_maker: bool = Field(alias="m", description="是否为做市商")
    client_order_id: str = Field(alias="c", description="客户端订单 ID")
    side: str = Field(alias="S", description="订单方向")
    last_filled_price: Decimal = Field(alias="L", description="最近成交价格")
    last_filled_quantity: Decimal = Field(alias="l", description="最近成交数量")
    trade_id: int = Field(alias="t", description="成交 ID")
    order_id: int = Field(alias="i", description="订单 ID")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 期货（FUTURES）保证金追缴 WS 模型
# =============================================================================


class BinanceFuturesMarginCallPositionModel(BaseModel):
    """期货保证金追缴 - 持仓子模型

    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-Margin-Call.md
    """

    symbol: str = Field(alias="s", description="交易对")
    position_side: str = Field(alias="ps", description="持仓方向")
    position_amt: Decimal = Field(alias="pa", description="持仓数量")
    margin_type: str = Field(alias="mt", description="保证金类型")
    isolated_wallet: Decimal = Field(alias="iw", description="逐仓钱包")
    mark_price: Decimal = Field(alias="mp", description="标记价格")
    unrealized_profit: Decimal = Field(alias="up", description="未实现盈亏")
    maintenance_margin_required: Decimal = Field(alias="mm", description="维持保证金要求")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesMarginCallWSModel(BaseModel):
    """期货保证金追缴 WS 事件模型

    Stream: User Data Stream MARGIN_CALL 事件
    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-Margin-Call.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    cross_wallet_balance: Decimal = Field(alias="cw", description="跨账户钱包余额")
    positions: list[BinanceFuturesMarginCallPositionModel] = Field(
        alias="p", description="追缴持仓列表"
    )

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 期货（FUTURES）条件单更新 WS 模型
# =============================================================================


class BinanceFuturesAlgoOrderDataModel(BaseModel):
    """期货条件单数据子模型

    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-Algo-Order-Update.md
    """

    client_algo_id: str = Field(alias="caid", description="客户端算法订单 ID")
    algo_id: int = Field(alias="aid", description="算法订单 ID")
    algo_type: str = Field(alias="at", description="算法类型")
    order_type: str = Field(alias="o", description="订单类型")
    symbol: str = Field(alias="s", description="交易对")
    side: str = Field(alias="S", description="订单方向")
    position_side: str = Field(alias="ps", description="持仓方向")
    time_in_force: str = Field(alias="f", description="有效期限")
    quantity: Decimal = Field(alias="q", description="数量")
    algo_status: str = Field(alias="X", description="算法订单状态")
    algo_order_id: str = Field(alias="ai", description="算法订单 ID")
    avg_fill_price: Decimal = Field(alias="ap", description="平均成交价格")
    executed_quantity: Decimal = Field(alias="aq", description="已成交数量")
    actual_order_type: str = Field(alias="act", description="实际订单类型")
    trigger_price: Decimal = Field(alias="tp", description="触发价格")
    order_price: Decimal = Field(alias="p", description="订单价格")
    stp_mode: str = Field(alias="V", description="STP 模式")
    working_type: str = Field(alias="wt", description="工作类型")
    price_match: str = Field(alias="pm", description="价格匹配模式")
    if_close_all: bool = Field(alias="cp", description="是否全平")
    if_price_protect: bool = Field(alias="pP", description="是否开启价格保护")
    is_reduce_only: bool = Field(alias="R", description="是否仅减仓")
    trigger_time: int = Field(alias="tt", description="触发时间")
    good_till_date: int = Field(alias="gtd", description="GTD 有效期")
    reject_reason: str = Field(alias="rm", description="拒绝原因")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesAlgoUpdateWSModel(BaseModel):
    """期货条件单更新 WS 事件模型

    Stream: User Data Stream ALGO_UPDATE 事件
    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-Algo-Order-Update.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    transaction_time: int = Field(alias="T", description="交易时间")
    event_time: int = Field(alias="E", description="事件时间")
    order_data: BinanceFuturesAlgoOrderDataModel = Field(alias="o", description="订单数据")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 期货（FUTURES）策略更新 WS 模型
# =============================================================================


class BinanceFuturesStrategyUpdateDataModel(BaseModel):
    """期货策略更新数据子模型

    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-STRATEGY-UPDATE.md
    """

    strategy_id: int = Field(alias="si", description="策略 ID")
    strategy_type: str = Field(alias="st", description="策略类型")
    strategy_status: str = Field(alias="ss", description="策略状态")
    symbol: str = Field(alias="s", description="交易对")
    update_time: int = Field(alias="ut", description="更新时间")
    op_code: int = Field(alias="c", description="操作代码")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesStrategyUpdateWSModel(BaseModel):
    """期货策略更新 WS 事件模型

    Stream: User Data Stream STRATEGY_UPDATE 事件
    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-STRATEGY-UPDATE.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    transaction_time: int = Field(alias="T", description="交易时间")
    event_time: int = Field(alias="E", description="事件时间")
    strategy_data: BinanceFuturesStrategyUpdateDataModel = Field(
        alias="su", description="策略数据"
    )

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 期货（FUTURES）网格更新 WS 模型
# =============================================================================


class BinanceFuturesGridUpdateDataModel(BaseModel):
    """期货网格更新数据子模型

    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-GRID-UPDATE.md
    """

    strategy_id: int = Field(alias="si", description="策略 ID")
    strategy_type: str = Field(alias="st", description="策略类型")
    strategy_status: str = Field(alias="ss", description="策略状态")
    symbol: str = Field(alias="s", description="交易对")
    realized_pnl: str = Field(alias="r", description="已实现盈亏")
    unmatched_avg_price: str = Field(alias="up", description="未成交平均价格")
    unmatched_qty: str = Field(alias="uq", description="未成交数量")
    unmatched_fee: str = Field(alias="uf", description="未成交手续费")
    matched_pnl: str = Field(alias="mp", description="已匹配盈亏")
    update_time: int = Field(alias="ut", description="更新时间")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesGridUpdateWSModel(BaseModel):
    """期货网格更新 WS 事件模型

    Stream: User Data Stream GRID_UPDATE 事件
    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-GRID-UPDATE.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    transaction_time: int = Field(alias="T", description="交易时间")
    event_time: int = Field(alias="E", description="事件时间")
    grid_data: BinanceFuturesGridUpdateDataModel = Field(alias="gu", description="网格数据")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 期货（FUTURES）条件单触发拒绝 WS 模型
# =============================================================================


class BinanceFuturesConditionalOrderRejectDataModel(BaseModel):
    """期货条件单拒绝数据子模型

    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-Conditional-Order-Trigger-Reject.md
    """

    symbol: str = Field(alias="s", description="交易对")
    order_id: int = Field(alias="i", description="订单 ID")
    reject_reason: str = Field(alias="r", description="拒绝原因")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesConditionalOrderTriggerRejectWSModel(BaseModel):
    """期货条件单触发拒绝 WS 事件模型

    Stream: User Data Stream CONDITIONAL_ORDER_TRIGGER_REJECT 事件
    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-Conditional-Order-Trigger-Reject.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    transaction_time: int = Field(alias="T", description="消息发送时间")
    reject_data: BinanceFuturesConditionalOrderRejectDataModel = Field(
        alias="or", description="拒绝数据"
    )

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 期货（FUTURES）账户配置更新 WS 模型
# =============================================================================


class BinanceFuturesAccountConfigLeverageModel(BaseModel):
    """期货账户配置 - 杠杆子模型

    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-Account-Configuration-Update-previous-Leverage-Update.md
    """

    symbol: str = Field(alias="s", description="交易对")
    leverage: int = Field(alias="l", description="杠杆倍数")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesAccountConfigMultiAssetModel(BaseModel):
    """期货账户配置 - 多资产模式子模型

    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-Account-Configuration-Update-previous-Leverage-Update.md
    """

    multi_asset_mode: bool = Field(alias="j", description="多资产模式")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesAccountConfigUpdateWSModel(BaseModel):
    """期货账户配置更新 WS 事件模型

    Stream: User Data Stream ACCOUNT_CONFIG_UPDATE 事件
    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-Account-Configuration-Update-previous-Leverage-Update.md

    注意: 事件可能包含 leverage_config(杠杆)或 multi_asset_config(多资产模式)之一，不会同时包含
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    transaction_time: int = Field(alias="T", description="交易时间")
    leverage_config: BinanceFuturesAccountConfigLeverageModel | None = Field(
        default=None, alias="ac", description="杠杆配置"
    )
    multi_asset_config: BinanceFuturesAccountConfigMultiAssetModel | None = Field(
        default=None, alias="ai", description="多资产模式配置"
    )

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 期货（FUTURES）ListenKey 过期 WS 模型
# =============================================================================


class BinanceFuturesListenKeyExpiredWSModel(BaseModel):
    """期货 ListenKey 过期 WS 事件模型

    Stream: User Data Stream listenKeyExpired 事件
    文档来源: binance_futures_docs/01_USD-M Futures/02_User Data Streams/Event-User-Data-Stream-Expired.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: str = Field(alias="E", description="事件时间")
    listen_key: str = Field(alias="listenKey", description="过期的 ListenKey")

    model_config = ConfigDict(populate_by_name=True)
