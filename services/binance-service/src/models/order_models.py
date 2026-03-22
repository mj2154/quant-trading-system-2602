"""
币安订单数据模型

严格遵循文档: docs/backend/design/09-binance-models.md

包含:
- 现货订单执行报告: User Data Stream executionReport 事件
- 期货订单成交更新: User Data Stream ORDER_TRADE_UPDATE 事件
- WebSocket 交易 API 响应模型
- WebSocket 交易 API 请求模型
"""

from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from .base import SnakeCaseModel


# =============================================================================
# 现货（SPOT）订单执行报告 WS 模型
# =============================================================================


class BinanceSpotExecutionReportEvent(BaseModel):
    """现货订单执行报告事件内容模型

    Stream: User Data Stream executionReport 事件
    文档来源: binance_spot_docs/User Data Stream.md
    """

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
    prevented_match_id: int | None = Field(default=None, alias="v", description="防止匹配 ID（仅订单因 STP 过期时）")
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
    trailing_delta: int | None = Field(
        default=None, alias="d", description="追踪止损 Delta（仅追踪止损订单）"
    )
    trailing_time: int | None = Field(
        default=None, alias="D", description="追踪止损时间（仅追踪止损订单）"
    )
    strategy_id: int | None = Field(
        default=None, alias="j", description="策略 ID（设置了 strategyId 参数时）"
    )
    strategy_type: int | None = Field(
        default=None, alias="J", description="策略类型（设置了 strategyType 参数时）"
    )
    prevented_quantity: Decimal | None = Field(
        default=None, alias="A", description="防止匹配数量（订单因 STP 过期时）"
    )
    last_prevented_quantity: Decimal | None = Field(
        default=None, alias="B", description="上次防止匹配数量（订单因 STP 过期时）"
    )
    trade_group_id: int | None = Field(
        default=None, alias="u", description="交易组 ID"
    )
    counter_order_id: int | None = Field(
        default=None, alias="U", description="对手方订单 ID"
    )
    counter_symbol: str | None = Field(
        default=None, alias="Cs", description="对手方交易对"
    )
    prevented_execution_quantity: Decimal | None = Field(
        default=None, alias="pl", description="防止执行数量"
    )
    prevented_execution_price: Decimal | None = Field(
        default=None, alias="pL", description="防止执行价格"
    )
    prevented_execution_quote_qty: Decimal | None = Field(
        default=None, alias="pY", description="防止执行 Quote 数量"
    )
    match_type: str | None = Field(
        default=None, alias="b", description="匹配类型（有分配时）"
    )
    allocation_id: int | None = Field(
        default=None, alias="a", description="分配 ID"
    )
    working_floor: str | None = Field(
        default=None, alias="k", description="工作 floor（有分配时）"
    )
    used_sor: bool | None = Field(
        default=None, alias="uS", description="是否使用 SOR"
    )
    pegged_price_type: str | None = Field(
        default=None, alias="gP", description="挂钩价格类型（仅挂钩订单）"
    )
    pegged_offset_type: str | None = Field(
        default=None, alias="gOT", description="挂钩偏移类型"
    )
    pegged_offset_value: int | None = Field(
        default=None, alias="gOV", description="挂钩偏移值"
    )
    pegged_price: str | None = Field(
        default=None, alias="gp", description="挂钩价格（仅挂钩订单）"
    )

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotExecutionReportWSModel(BaseModel):
    """现货订单执行报告 WS 事件模型

    Stream: User Data Stream executionReport 事件
    文档来源: binance_spot_docs/User Data Stream.md
    """

    subscription_id: int = Field(alias="subscriptionId", description="订阅 ID")
    event: BinanceSpotExecutionReportEvent = Field(description="事件内容")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 期货（FUTURES）订单成交更新 WS 模型
# =============================================================================


class BinanceFuturesOrderDataModel(BaseModel):
    """期货订单数据子模型

    文档来源: binance_futures_docs/01_U本位合约/02_Websocket账户信息推送/订单交易更新推送.md
    """

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
    文档来源: binance_futures_docs/01_U本位合约/02_Websocket账户信息推送/订单交易更新推送.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    transaction_time: int = Field(alias="T", description="交易时间")
    order_data: BinanceFuturesOrderDataModel = Field(alias="o", description="订单数据")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# WebSocket 交易 API 响应模型
# =============================================================================


class BinanceSpotOrderPlaceResult(BaseModel):
    """现货订单下单响应结果模型

    方法: order.place
    文档来源: binance_spot_docs/01_WebSocket API/Trading requests.md
    """

    symbol: str = Field(alias="symbol", description="交易对")
    order_id: int = Field(alias="orderId", description="订单 ID")
    order_list_id: int = Field(alias="orderListId", description="订单列表 ID (-1 表示无)")
    client_order_id: str = Field(alias="clientOrderId", description="客户端订单 ID")
    transact_time: int = Field(alias="transactTime", description="成交时间")
    price: str = Field(alias="price", description="订单价格")
    orig_qty: str = Field(alias="origQty", description="原始数量")
    executed_qty: str = Field(alias="executedQty", description="已成交数量")
    cummulative_quote_qty: str = Field(
        alias="cummulativeQuoteQty", description="累计 Quote 成交数量"
    )
    status: str = Field(alias="status", description="订单状态")
    time_in_force: str = Field(alias="timeInForce", description="有效期限")
    order_type: str = Field(alias="type", description="订单类型")
    side: str = Field(alias="side", description="订单方向")
    working_time: int = Field(alias="workingTime", description="工作时间")
    self_trade_prevention_mode: str = Field(
        alias="selfTradePreventionMode", description="自成交预防模式"
    )
    fills: list["BinanceSpotFillModel"] = Field(
        default_factory=list, alias="fills", description="成交明细（仅 FULL 响应类型）"
    )

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotFillModel(BaseModel):
    """现货成交明细模型

    文档来源: binance_spot_docs/01_WebSocket API/Trading requests.md
    """

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


class BinanceSpotAmendedOrderModel(BaseModel):
    """现货订单修改后的订单信息模型"""

    symbol: str = Field(alias="symbol", description="交易对")
    order_id: int = Field(alias="orderId", description="订单 ID")
    order_list_id: int = Field(alias="orderListId", description="订单列表 ID")
    orig_client_order_id: str = Field(alias="origClientOrderId", description="原始客户端订单 ID")
    client_order_id: str = Field(alias="clientOrderId", description="客户端订单 ID")
    price: str = Field(alias="price", description="订单价格")
    qty: str = Field(alias="qty", description="订单数量")
    executed_qty: str = Field(alias="executedQty", description="已成交数量")
    status: str = Field(alias="status", description="订单状态")
    time_in_force: str = Field(alias="timeInForce", description="有效期限")
    order_type: str = Field(alias="type", description="订单类型")
    side: str = Field(alias="side", description="订单方向")
    working_time: int = Field(alias="workingTime", description="工作时间")
    self_trade_prevention_mode: str = Field(
        alias="selfTradePreventionMode", description="自成交预防模式"
    )

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotOrderAmendResult(BaseModel):
    """现货订单修改响应结果模型

    方法: order.amend.keepPriority
    文档来源: binance_spot_docs/01_WebSocket API/Trading requests.md
    """

    transact_time: int = Field(alias="transactTime", description="成交时间")
    execution_id: int = Field(alias="executionId", description="执行 ID")
    amended_order: BinanceSpotAmendedOrderModel = Field(
        alias="amendedOrder", description="修改后的订单信息"
    )

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesOrderPlaceResult(BaseModel):
    """期货订单下单响应结果模型

    方法: order.place
    文档来源: binance_futures_docs/01_U本位合约/02_交易接口/03_WebSocket API/下单(TRADE).md
    """

    order_id: int = Field(alias="orderId", description="订单 ID")
    symbol: str = Field(alias="symbol", description="交易对")
    status: str = Field(alias="status", description="订单状态")
    client_order_id: str = Field(alias="clientOrderId", description="客户端订单 ID")
    price: str = Field(alias="price", description="订单价格")
    avg_price: str = Field(alias="avgPrice", description="平均价格")
    orig_qty: str = Field(alias="origQty", description="原始数量")
    executed_qty: str = Field(alias="executedQty", description="已成交数量")
    cum_qty: str = Field(alias="cumQty", description="累计成交数量")
    cum_quote: str = Field(alias="cumQuote", description="累计成交额")
    time_in_force: str = Field(alias="timeInForce", description="有效期限")
    order_type: str = Field(alias="type", description="订单类型")
    reduce_only: bool = Field(alias="reduceOnly", description="是否仅减仓")
    close_position: bool = Field(alias="closePosition", description="是否全平")
    side: str = Field(alias="side", description="订单方向")
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


class BinanceFuturesModifyOrderResult(BaseModel):
    """期货订单修改响应结果模型

    方法: order.modify
    文档来源: binance_futures_docs/01_U本位合约/02_交易接口/03_WebSocket API/修改订单(TRADE).md
    """

    order_id: int = Field(alias="orderId", description="订单 ID")
    symbol: str = Field(alias="symbol", description="交易对")
    status: str = Field(alias="status", description="订单状态")
    client_order_id: str = Field(alias="clientOrderId", description="客户端订单 ID")
    price: str = Field(alias="price", description="订单价格")
    avg_price: str = Field(alias="avgPrice", description="平均价格")
    orig_qty: str = Field(alias="origQty", description="原始数量")
    executed_qty: str = Field(alias="executedQty", description="已成交数量")
    cum_qty: str = Field(alias="cumQty", description="累计成交数量")
    cum_quote: str = Field(alias="cumQuote", description="累计成交额")
    time_in_force: str = Field(alias="timeInForce", description="有效期限")
    order_type: str = Field(alias="type", description="订单类型")
    reduce_only: bool = Field(alias="reduceOnly", description="是否仅减仓")
    close_position: bool = Field(alias="closePosition", description="是否全平")
    side: str = Field(alias="side", description="订单方向")
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


# =============================================================================
# WebSocket 交易 API 请求模型
# =============================================================================


class BinanceSpotWsOrderRequest(BaseModel):
    """现货订单下单请求模型

    方法: order.place
    文档来源: binance_spot_docs/01_WebSocket API/Trading requests.md

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


class BinanceFuturesWsOrderRequest(BaseModel):
    """期货订单下单请求模型

    方法: order.place
    文档来源: binance_futures_docs/01_U本位合约/02_交易接口/03_WebSocket API/下单(TRADE).md

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
