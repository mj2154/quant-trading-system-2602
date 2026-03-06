"""
订单相关的数据模型 (WebSocket API)

严格遵循官方 WebSocket API 文档的字段命名。
内部使用蛇形命名，发送/接收时自动转换为驼峰。

设计原则：
- SnakeCaseModel 基类：接收外部输入时自动将 camelCase 转为 snake_case
- CamelCaseModel 基类：序列化输出时自动将 snake_case 转为 camelCase

引用：
- 现货 WS: https://binance-docs.github.io/apidocs/spot/cn/#websocket-api-trading-requests
- 期货 WS: https://binance-docs.github.io/apidocs/futures/cn/#websocket-api-trading-requests
"""

from enum import Enum
from typing import Optional

from pydantic import Field

from .base import CamelCaseModel, SnakeCaseModel


class OrderType(str, Enum):
    """订单类型"""
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"
    LIMIT_MAKER = "LIMIT_MAKER"
    TRAILING_STOP_MARKET = "TRAILING_STOP_MARKET"


class OrderSide(str, Enum):
    """订单方向"""
    BUY = "BUY"
    SELL = "SELL"


class PositionSide(str, Enum):
    """持仓方向（对冲模式）"""
    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"


class TimeInForce(str, Enum):
    """时间策略"""
    GTC = "GTC"  # Good Till Cancel - 成交为止
    IOC = "IOC"  # Immediate or Cancel - 立即成交，否则取消
    FOK = "FOK"  # Fill or Kill - 全部成交，否则取消


class OrderResponseType(str, Enum):
    """订单响应类型"""
    ACK = "ACK"    # 仅返回确认信息
    RESULT = "RESULT"  # 返回执行结果
    FULL = "FULL"  # 返回完整信息


class OrderStatus(str, Enum):
    """订单状态"""
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    PENDING_CANCEL = "PENDING_CANCEL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


# =============================================================================
# 现货订单请求模型 (WebSocket API)
# =============================================================================

class SpotWsOrderRequest(SnakeCaseModel):
    """现货 WebSocket 订单请求参数

    严格遵循官方文档: https://binance-docs.github.io/apidocs/spot/cn/#websocket-api-trading-requests

    与期货订单的主要区别:
    - 支持 quoteOrderQty (报价数量)
    - 支持 icebergQty (冰山订单)
    - 支持 trailingDelta (追踪止损)
    - 支持 strategyId/strategyType (策略)
    - 支持 pegPriceType/pegOffsetValue/pegOffsetType (Pegged订单)
    """

    # ========== 必填字段 ==========
    symbol: str = Field(..., description="交易对，如 BTCUSDT")
    side: str = Field(..., description="订单方向 BUY/SELL")
    type: str = Field(..., description="订单类型 LIMIT/MARKET/STOP_LOSS etc.")
    new_client_order_id: str = Field(..., alias="newClientOrderId", description="客户端订单ID（必填，用于关联请求和响应）")

    # quantity 或 quoteOrderQty 至少填写一个
    quantity: Optional[float] = Field(None, description="订单数量")
    quote_order_qty: Optional[float] = Field(None, alias="quoteOrderQty", description="报价数量（市价买单时指定支付金额）")

    # ========== 可选字段 ==========

    # 价格相关（限价单必需）
    price: Optional[float] = Field(None, description="限价价格")
    time_in_force: Optional[str] = Field(None, alias="timeInForce", description="时间策略 GTC/IOC/FOK")

    # 策略参数
    strategy_id: Optional[int] = Field(None, alias="strategyId", description="策略ID")
    strategy_type: Optional[int] = Field(None, alias="strategyType", description="策略类型（值不能小于1000000）")

    # 止损/止盈
    stop_price: Optional[float] = Field(None, alias="stopPrice", description="止损价格")
    trailing_delta: Optional[int] = Field(None, alias="trailingDelta", description="追踪止损delta")

    # 冰山订单参数
    iceberg_qty: Optional[float] = Field(None, alias="icebergQty", description="冰山订单数量")
    limit_iceberg_qty: Optional[float] = Field(None, alias="limitIcebergQty", description="冰山订单的限价部分数量")
    stop_iceberg_qty: Optional[float] = Field(None, alias="stopIcebergQty", description="止损单的冰山数量")

    # 策略参数 - 限价单和止损单
    limit_strategy_id: Optional[int] = Field(None, alias="limitStrategyId", description="限价单的策略ID")
    stop_strategy_id: Optional[int] = Field(None, alias="stopStrategyId", description="止损单的策略ID")

    # 止损限价单时间策略
    stop_limit_time_in_force: Optional[str] = Field(None, alias="stopLimitTimeInForce", description="止损限价单时间策略 GTC/IOC/FOK")

    # 响应格式
    new_order_resp_type: Optional[str] = Field("FULL", alias="newOrderRespType", description="响应格式 ACK/RESULT/FULL")

    # 自成交防止
    self_trade_prevention_mode: Optional[str] = Field(None, alias="selfTradePreventionMode", description="自成交防止模式")

    # Pegged订单参数
    peg_price_type: Optional[str] = Field(None, alias="pegPriceType", description="价格peg类型 PRIMARY_PEG/MARKET_PEG")
    peg_offset_value: Optional[int] = Field(None, alias="pegOffsetValue", description="peg偏移值")
    peg_offset_type: Optional[int] = Field(None, alias="pegOffsetType", description="peg偏移类型")

    def to_binance_params(self) -> dict:
        """转换为发送给币安的参数字典（驼峰命名）"""
        return self.model_dump(by_alias=True, exclude_none=True)


# =============================================================================
# 期货订单请求模型 (WebSocket API)
# =============================================================================

class FuturesWsOrderRequest(SnakeCaseModel):
    """期货 WebSocket 订单请求参数

    严格遵循官方文档: https://binance-docs.github.io/apidocs/futures/cn/#websocket-api-trading-requests

    与现货订单的主要区别:
    - 支持 positionSide (持仓方向)
    - 支持 reduceOnly (只减仓)
    - 支持 closePosition (全平仓)
    - 支持 activationPrice (触发价格)
    - 支持 callbackRate (回调比例)
    - 支持 workingType (触发价格类型)
    - 支持 priceProtect (价格保护)
    - 支持 priceMatch (价格匹配)
    - 支持 goodTillDate (GTD到期时间)
    """

    # ========== 必填字段 ==========
    symbol: str = Field(..., description="交易对，如 BTCUSDT")
    side: str = Field(..., description="订单方向 BUY/SELL")
    type: str = Field(..., description="订单类型 LIMIT/MARKET/STOP_LOSS etc.")
    new_client_order_id: str = Field(..., alias="newClientOrderId", description="客户端订单ID（必填，用于关联请求和响应）")

    # quantity 或 closePosition 至少填写一个
    quantity: Optional[float] = Field(None, description="订单数量")

    # ========== 可选字段 ==========

    # 价格相关
    price: Optional[float] = Field(None, description="限价价格")
    time_in_force: Optional[str] = Field(None, alias="timeInForce", description="时间策略 GTC/IOC/FOK")

    # 持仓方向（对冲模式）- 期货特有
    position_side: Optional[str] = Field(None, alias="positionSide", description="持仓方向 LONG/SHORT/BOTH")

    # 止损/止盈 - 期货特有
    stop_price: Optional[float] = Field(None, alias="stopPrice", description="止损价格")
    reduce_only: bool = Field(False, alias="reduceOnly", description="是否仅减仓")
    close_position: bool = Field(False, alias="closePosition", description="是否全平仓")

    # 追踪止损 - 期货特有
    activation_price: Optional[float] = Field(None, alias="activationPrice", description="触发价格（追踪止损）")
    callback_rate: Optional[float] = Field(None, alias="callbackRate", description="回调比例（0.1-10）")

    # 响应格式
    new_order_resp_type: Optional[str] = Field("ACK", alias="newOrderRespType", description="响应格式 ACK/RESULT/FULL")

    # 期货特有参数
    working_type: Optional[str] = Field("CONTRACT_PRICE", alias="workingType", description="触发价格类型 MARK_PRICE/CONTRACT_PRICE")
    price_protect: bool = Field(False, alias="priceProtect", description="是否开启价格保护")
    price_match: Optional[str] = Field(None, alias="priceMatch", description="价格匹配模式 OPPONENT/QUEUE等")
    self_trade_prevention_mode: Optional[str] = Field(None, alias="selfTradePreventionMode", description="自成交防止模式")
    good_till_date: Optional[int] = Field(None, alias="goodTillDate", description="GTD订单过期时间")

    def to_binance_params(self) -> dict:
        """转换为发送给币安的参数字典（驼峰命名）"""
        return self.model_dump(by_alias=True, exclude_none=True)


# =============================================================================
# 查询/取消订单请求模型 (WebSocket API - 通用)
# =============================================================================

from pydantic import model_validator


class WsQueryOrderRequest(SnakeCaseModel):
    """WebSocket 查询订单请求参数

    现货: order.status
    期货: order.status
    """

    # ========== 必填字段 ==========
    symbol: str = Field(..., description="交易对")

    # orderId 或 origClientOrderId 至少填写一个
    order_id: Optional[int] = Field(None, alias="orderId", description="订单ID")
    orig_client_order_id: Optional[str] = Field(None, alias="origClientOrderId", description="客户端订单ID")

    @model_validator(mode="after")
    def validate_required_fields(self) -> "WsQueryOrderRequest":
        """验证至少填写一个订单ID"""
        if not self.order_id and not self.orig_client_order_id:
            raise ValueError("Either orderId or origClientOrderId is required")
        return self

    def to_binance_params(self) -> dict:
        """转换为发送给币安的参数字典（驼峰命名）"""
        return self.model_dump(by_alias=True, exclude_none=True)


class WsCancelOrderRequest(SnakeCaseModel):
    """WebSocket 取消订单请求参数

    现货: order.cancel
    期货: order.cancel
    """

    # ========== 必填字段 ==========
    symbol: str = Field(..., description="交易对")

    # orderId 或 origClientOrderId 至少填写一个
    order_id: Optional[int] = Field(None, alias="orderId", description="订单ID")
    orig_client_order_id: Optional[str] = Field(None, alias="origClientOrderId", description="客户端订单ID")

    # ========== 可选字段 ==========
    new_client_order_id: Optional[str] = Field(None, alias="newClientOrderId", description="用于唯一标识此次取消操作")

    # 现货特有
    cancel_restrictions: Optional[str] = Field(None, alias="cancelRestrictions", description="取消限制条件 ONLY_NEW/ONLY_PARTIALLY_FILLED")

    @model_validator(mode="after")
    def validate_required_fields(self) -> "WsCancelOrderRequest":
        """验证至少填写一个订单ID"""
        if not self.order_id and not self.orig_client_order_id:
            raise ValueError("Either orderId or origClientOrderId is required")
        return self

    def to_binance_params(self) -> dict:
        """转换为发送给币安的参数字典（驼峰命名）"""
        return self.model_dump(by_alias=True, exclude_none=True)


# =============================================================================
# 响应模型 (WebSocket API)
# =============================================================================

class SpotWsOrderResponse(SnakeCaseModel):
    """现货 WebSocket 订单响应

    严格遵循官方文档: https://binance-docs.github.io/apidocs/spot/cn/#websocket-api-trading-requests
    """

    # 订单标识
    order_id: int = Field(..., alias="orderId")
    order_list_id: int = Field(-1, alias="orderListId")
    client_order_id: str = Field(..., alias="clientOrderId")
    transaction_time: int = Field(..., alias="transactTime")

    # 订单方向和类型
    symbol: str
    side: str
    order_type: str = Field(..., alias="type")

    # 数量和价格
    orig_qty: str = Field("0", alias="origQty")
    price: str = "0"
    executed_qty: str = Field("0", alias="executedQty")
    cummulative_quote_qty: str = Field("0", alias="cummulativeQuoteQty")
    orig_quote_order_qty: Optional[str] = Field(None, alias="origQuoteOrderQty")

    # 订单状态
    status: str

    # 时间策略
    time_in_force: Optional[str] = Field(None, alias="timeInForce")

    # 冰山订单
    iceberg_qty: Optional[str] = Field(None, alias="icebergQty")

    # 时间戳
    update_time: int = Field(..., alias="updateTime")
    is_working: bool = Field(..., alias="isWorking")
    working_time: Optional[int] = Field(None, alias="workingTime")

    # 自成交防止
    self_trade_prevention_mode: Optional[str] = Field(None, alias="selfTradePreventionMode")

    # 成交明细（仅FULL响应包含）
    fills: Optional[list[dict]] = None

    # 条件字段
    stop_price: Optional[str] = Field(None, alias="stopPrice")
    strategy_id: Optional[int] = Field(None, alias="strategyId")
    strategy_type: Optional[int] = Field(None, alias="strategyType")
    trailing_delta: Optional[int] = Field(None, alias="trailingDelta")
    trailing_time: Optional[int] = Field(None, alias="trailingTime")
    used_sor: Optional[bool] = Field(None, alias="usedSor")
    working_floor: Optional[str] = Field(None, alias="workingFloor")
    peg_price_type: Optional[str] = Field(None, alias="pegPriceType")
    peg_offset_value: Optional[int] = Field(None, alias="pegOffsetValue")
    peg_offset_type: Optional[int] = Field(None, alias="pegOffsetType")
    pegged_price: Optional[str] = Field(None, alias="peggedPrice")
    prevented_match_id: Optional[int] = Field(None, alias="preventedMatchId")
    prevented_quantity: Optional[str] = Field(None, alias="preventedQuantity")

    class Config:
        extra = "allow"


class FuturesWsOrderResponse(SnakeCaseModel):
    """期货 WebSocket 订单响应

    严格遵循官方文档: https://binance-docs.github.io/apidocs/futures/cn/#websocket-api-trading-requests
    """

    # 订单标识
    order_id: int = Field(..., alias="orderId")
    client_order_id: str = Field(..., alias="clientOrderId")
    symbol: str

    # 订单方向和类型
    side: str
    position_side: Optional[str] = Field(None, alias="positionSide")
    order_type: str = Field(..., alias="type")
    orig_type: Optional[str] = Field(None, alias="origType")

    # 数量和价格
    orig_qty: str = Field("0", alias="origQty")
    price: str = "0"
    avg_price: str = Field("0", alias="avgPrice")
    stop_price: Optional[str] = Field(None, alias="stopPrice")

    # 成交情况
    executed_qty: str = Field("0", alias="executedQty")
    cum_qty: str = Field("0", alias="cumQty")
    cum_quote: str = Field("0", alias="cumQuote")

    # 订单状态
    status: str

    # 时间策略
    time_in_force: Optional[str] = Field(None, alias="timeInForce")

    # 其他标志
    reduce_only: bool = Field(False, alias="reduceOnly")
    close_position: bool = Field(False, alias="closePosition")
    working_type: str = Field("CONTRACT_PRICE", alias="workingType")
    price_protect: bool = Field(False, alias="priceProtect")
    price_match: Optional[str] = Field(None, alias="priceMatch")
    self_trade_prevention_mode: Optional[str] = Field(None, alias="selfTradePreventionMode")
    good_till_date: Optional[int] = Field(None, alias="goodTillDate")

    # 时间戳
    update_time: int = Field(..., alias="updateTime")

    # 条件字段
    strategy_id: Optional[int] = Field(None, alias="strategyId")
    strategy_type: Optional[int] = Field(None, alias="strategyType")
    trailing_delta: Optional[int] = Field(None, alias="trailingDelta")
    trailing_time: Optional[int] = Field(None, alias="trailingTime")
    prevented_match_id: Optional[int] = Field(None, alias="preventedMatchId")
    prevented_quantity: Optional[str] = Field(None, alias="preventedQuantity")

    class Config:
        extra = "allow"


class WsCancelOrderResponse(SnakeCaseModel):
    """WebSocket 取消订单响应

    现货: order.cancel
    期货: order.cancel
    """

    # 订单标识
    symbol: str
    order_id: int = Field(..., alias="orderId")
    order_list_id: int = Field(-1, alias="orderListId")
    orig_client_order_id: str = Field(..., alias="origClientOrderId")
    client_order_id: str = Field(..., alias="clientOrderId")
    transact_time: int = Field(..., alias="transactTime")

    # 订单方向和类型
    side: str
    order_type: str = Field(..., alias="type")

    # 数量和价格
    orig_qty: str = Field("0", alias="origQty")
    executed_qty: str = Field("0", alias="executedQty")
    cummulative_quote_qty: str = Field("0", alias="cummulativeQuoteQty")
    price: str = "0"

    # 订单状态
    status: str

    # 时间策略
    time_in_force: Optional[str] = Field(None, alias="timeInForce")

    # 条件字段
    stop_price: Optional[str] = Field(None, alias="stopPrice")
    iceberg_qty: Optional[str] = Field(None, alias="icebergQty")
    self_trade_prevention_mode: Optional[str] = Field(None, alias="selfTradePreventionMode")
    strategy_id: Optional[int] = Field(None, alias="strategyId")
    strategy_type: Optional[int] = Field(None, alias="strategyType")

    class Config:
        extra = "allow"
