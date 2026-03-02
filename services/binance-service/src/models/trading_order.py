"""
订单相关的数据模型

定义订单类型、订单方向、时间策略等枚举和订单请求/响应模型。
严格遵循官方API文档的字段命名。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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
    GTD = "GTC"  # Good Till Date - 指定日期前有效


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


@dataclass
class OrderRequest:
    """订单请求参数"""
    symbol: str                    # 交易对，如 BTCUSDT
    side: OrderSide                # 买入或卖出
    order_type: OrderType          # 订单类型
    quantity: float                # 数量
    price: Optional[float] = None  # 价格（限价单必需）
    time_in_force: Optional[TimeInForce] = None  # 时间策略
    stop_price: Optional[float] = None  # 止损/止盈价格
    reduce_only: bool = False      # 是否仅减仓
    new_client_order_id: Optional[str] = None  # 客户端订单ID
    position_side: Optional[PositionSide] = None  # 持仓方向（对冲模式）
    new_order_resp_type: OrderResponseType = OrderResponseType.ACK  # 响应类型

    def to_dict(self) -> dict:
        """转换为字典"""
        params = {
            "symbol": self.symbol.upper(),
            "side": self.side.value,
            "type": self.order_type.value,
            "quantity": str(self.quantity),
            "newOrderRespType": self.new_order_resp_type.value,
        }

        if self.price is not None:
            params["price"] = str(self.price)

        if self.time_in_force is not None:
            params["timeInForce"] = self.time_in_force.value

        if self.stop_price is not None:
            params["stopPrice"] = str(self.stop_price)

        if self.reduce_only:
            params["reduceOnly"] = "true"

        if self.new_client_order_id is not None:
            params["newClientOrderId"] = self.new_client_order_id

        if self.position_side is not None:
            params["positionSide"] = self.position_side.value

        return params


@dataclass
class FuturesOrderRequest(OrderRequest):
    """期货订单请求（扩展）"""
    # 期货特有参数
    price_match: Optional[str] = None  # 价格匹配模式
    self_trade_prevention_mode: Optional[str] = None  # 自成交防止模式
    good_till_date: Optional[int] = None  # 过期时间戳

    def to_dict(self) -> dict:
        """转换为字典"""
        params = super().to_dict()

        if self.price_match is not None:
            params["priceMatch"] = self.price_match

        if self.self_trade_prevention_mode is not None:
            params["selfTradePreventionMode"] = self.self_trade_prevention_mode

        if self.good_till_date is not None:
            params["goodTillDate"] = str(self.good_till_date)

        return params


# ========== 响应模型（严格遵循官方文档）==========


class FuturesOrderResponse(BaseModel):
    """期货订单响应

    严格遵循官方文档格式：https://binance-docs.github.io/apidocs/futures/cn/
    POST /fapi/v1/order 响应字段
    """
    # 订单标识
    order_id: int = Field(..., alias="orderId", description="订单ID")
    client_order_id: str = Field(..., alias="clientOrderId", description="客户端订单ID")
    symbol: str = Field(..., description="交易对")

    # 订单方向和类型
    side: str = Field(..., description="订单方向 BUY/SELL")
    position_side: Optional[str] = Field(None, alias="positionSide", description="持仓方向 LONG/SHORT/BOTH")
    order_type: str = Field(..., alias="type", description="订单类型")
    orig_type: Optional[str] = Field(None, alias="origType", description="原始订单类型")

    # 数量和价格
    orig_qty: str = Field(..., alias="origQty", description="原始数量")
    price: str = Field(..., description="订单价格")
    avg_price: str = Field(..., alias="avgPrice", description="平均成交价格")
    stop_price: Optional[str] = Field(None, alias="stopPrice", description="止损价格")

    # 成交情况
    executed_qty: str = Field(..., alias="executedQty", description="已成交数量")
    cum_qty: str = Field(..., alias="cumQty", description="累计成交数量")
    cum_quote: str = Field(..., alias="cumQuote", description="累计成交金额")

    # 订单状态
    status: str = Field(..., description="订单状态 NEW/PARTIALLY_FILLED/FILLED/CANCELED/REJECTED/EXPIRED")

    # 时间策略
    time_in_force: Optional[str] = Field(None, alias="timeInForce", description="时间策略 GTC/IOC/FOK/GTD")

    # 其他标志
    reduce_only: bool = Field(..., alias="reduceOnly", description="是否仅减仓")
    close_position: bool = Field(..., alias="closePosition", description="是否全平")
    working_type: str = Field(..., alias="workingType", description="触发价格类型")
    price_protect: bool = Field(..., alias="priceProtect", description="是否开启价格保护")
    price_match: Optional[str] = Field(None, alias="priceMatch", description="价格匹配模式")
    self_trade_prevention_mode: Optional[str] = Field(
        None, alias="selfTradePreventionMode", description="自成交防止模式"
    )
    good_till_date: Optional[int] = Field(None, alias="goodTillDate", description="GTD订单过期时间")

    # 时间戳
    update_time: int = Field(..., alias="updateTime", description="更新时间")


class SpotOrderResponse(BaseModel):
    """现货订单响应

    严格遵循官方文档格式：https://binance-docs.github.io/apidocs/spot/cn/
    POST /api/v3/order 响应字段
    """
    # 订单标识
    order_id: int = Field(..., alias="orderId", description="订单ID")
    client_order_id: str = Field(..., alias="clientOrderId", description="客户端订单ID")
    symbol: str = Field(..., description="交易对")
    transaction_time: int = Field(..., alias="transactionTime", description="成交时间")

    # 订单方向和类型
    side: str = Field(..., description="订单方向 BUY/SELL")
    order_type: str = Field(..., alias="type", description="订单类型")

    # 数量和价格
    orig_qty: str = Field(..., alias="origQty", description="原始数量")
    price: str = Field(..., description="订单价格")
    executed_qty: str = Field(..., alias="executedQty", description="已成交数量")
    cummulative_quote_qty: str = Field(..., alias="cummulativeQuoteQty", description="累计成交金额")

    # 订单状态
    status: str = Field(..., description="订单状态 NEW/PARTIALLY_FILLED/FILLED/CANCELED/REJECTED/EXPIRED")

    # 时间策略
    time_in_force: str = Field(..., alias="timeInForce", description="时间策略 GTC/IOC/FOK")

    # 冰山订单
    iceberg_qty: Optional[str] = Field(None, alias="icebergQty", description="冰山数量")

    # 时间戳
    update_time: int = Field(..., alias="updateTime", description="更新时间")
    is_working: bool = Field(..., alias="isWorking", description="是否正在工作")


class CancelOrderResponse(BaseModel):
    """撤销订单响应

    严格遵循官方文档格式
    """
    # 订单标识
    order_id: int = Field(..., alias="orderId", description="订单ID")
    client_order_id: str = Field(..., alias="clientOrderId", description="客户端订单ID")
    symbol: str = Field(..., description="交易对")

    # 订单方向和类型
    side: str = Field(..., description="订单方向 BUY/SELL")
    order_type: str = Field(..., alias="type", description="订单类型")

    # 数量和价格
    orig_qty: str = Field(..., alias="origQty", description="原始数量")
    executed_qty: str = Field(..., alias="executedQty", description="已成交数量")
    price: str = Field(..., description="订单价格")

    # 订单状态
    status: str = Field(..., description="订单状态 CANCELED")

    # 时间戳
    update_time: int = Field(..., alias="updateTime", description="更新时间")
