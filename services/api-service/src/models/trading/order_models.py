"""
交易订单数据模型

定义订单请求和响应数据模型，用于验证和序列化。

设计参考 docs/backend/design/08-api-models.md 和 04-trading-orders.md：
- CreateOrderRequest: 创建订单请求
- GetOrderRequest: 查询订单请求
- ListOrdersRequest: 查询订单列表请求
- CancelOrderRequest: 撤销订单请求
- OrderData: 订单数据
- OrderListData: 订单列表数据
- OrderUpdateData: 订单更新推送数据

版本: v1.0.0
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class OrderSide(str, Enum):
    """订单方向"""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """订单类型

    与币安 API 保持一致：LIMIT, MARKET, STOP, STOP_MARKET, TAKE_PROFIT, TAKE_PROFIT_MARKET
    """

    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TRAILING_STOP_MARKET = "TRAILING_STOP_MARKET"


class OrderTimeInForce(str, Enum):
    """订单有效时间

    GTC - Good Till Cancel (成交为止)
    IOC - Immediate or Cancel (立即成交，否则取消)
    FOK - Fill or Kill (全部成交，否则取消)
    """

    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class MarketType(str, Enum):
    """市场类型"""

    SPOT = "SPOT"
    FUTURES = "FUTURES"


class CreateOrderRequest(BaseModel):
    """创建订单请求

    必填字段：symbol, side, type, quantity
    可选字段：price, timeInForce, positionSide, reduceOnly, clientOrderId

    设计参考：04-trading-orders.md order.create 参数
    """

    # 必填字段
    symbol: str = Field(..., description="交易对符号，如 BTCUSDT")
    side: OrderSide = Field(..., description="订单方向：BUY 或 SELL")
    type: OrderType = Field(..., description="订单类型：LIMIT, MARKET 等")
    quantity: float = Field(..., gt=0, description="订单数量，必须大于0")

    # 可选字段
    price: float | None = Field(None, description="限价价格")
    timeInForce: OrderTimeInForce | None = Field(None, description="订单有效时间")
    positionSide: str | None = Field(None, description="持仓方向：BOTH, LONG, SHORT")
    reduceOnly: bool = Field(False, description="是否只减仓")
    clientOrderId: str | None = Field(None, description="客户端自定义订单ID")
    marketType: MarketType = Field(MarketType.FUTURES, description="市场类型")

    @field_validator("price", mode="before")
    @classmethod
    def validate_price_for_market_order(cls, v, info):
        """市价单不应该有价格字段"""
        if info.data.get("type") == OrderType.MARKET and v is not None:
            logger.warning("Market order should not have price, ignoring price field")
            return None
        return v

    def model_post_init(self, __context) -> None:
        """验证逻辑"""
        # 限价单必须有价格
        if self.type == OrderType.LIMIT and self.price is None:
            raise ValueError("Limit order requires price field")

    class Config:
        use_enum_values = True


class GetOrderRequest(BaseModel):
    """查询订单请求

    至少需要提供 orderId 或 clientOrderId 之一

    设计参考：04-trading-orders.md order.query 参数
    """

    symbol: str = Field(..., description="交易对符号")
    orderId: int | str | None = Field(None, description="币安订单ID")
    clientOrderId: str | None = Field(None, description="客户端自定义订单ID")
    marketType: MarketType = Field(MarketType.FUTURES, description="市场类型")

    @field_validator("orderId", mode="before")
    @classmethod
    def convert_order_id(cls, v):
        """允许字符串形式的数字"""
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v

    def validate(self) -> bool:
        """验证必填字段"""
        if not self.orderId and not self.clientOrderId:
            raise ValueError("Either orderId or clientOrderId is required")
        return True

    class Config:
        use_enum_values = True


class ListOrdersRequest(BaseModel):
    """查询订单列表请求

    可选过滤条件
    """

    symbol: str | None = Field(None, description="交易对符号")
    status: str | None = Field(None, description="订单状态过滤")
    startTime: int | None = Field(None, description="起始时间（毫秒）")
    endTime: int | None = Field(None, description="结束时间（毫秒）")
    limit: int = Field(100, ge=1, le=1000, description="返回数量限制")
    marketType: MarketType = Field(MarketType.FUTURES, description="市场类型")

    class Config:
        use_enum_values = True


class CancelOrderRequest(BaseModel):
    """撤销订单请求

    至少需要提供 orderId 或 clientOrderId 之一

    设计参考：04-trading-orders.md order.cancel 参数
    """

    symbol: str = Field(..., description="交易对符号")
    orderId: int | str | None = Field(None, description="币安订单ID")
    clientOrderId: str | None = Field(None, description="客户端自定义订单ID")
    marketType: MarketType = Field(MarketType.FUTURES, description="市场类型")

    @field_validator("orderId", mode="before")
    @classmethod
    def convert_order_id(cls, v):
        """允许字符串形式的数字"""
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v

    def validate(self) -> bool:
        """验证必填字段"""
        if not self.orderId and not self.clientOrderId:
            raise ValueError("Either orderId or clientOrderId is required")
        return True

    class Config:
        use_enum_values = True


class GetOpenOrdersRequest(BaseModel):
    """查询当前挂单请求"""

    symbol: str | None = Field(None, description="交易对符号，不传则返回所有")
    marketType: MarketType = Field(MarketType.FUTURES, description="市场类型")

    class Config:
        use_enum_values = True


class OrderData(BaseModel):
    """订单数据

    包含订单的完整信息。
    data 字段存储币安 API 返回的完整 JSON 数据。

    设计参考：08-api-models.md OrderData
    """

    # 核心字段
    client_order_id: str | None = Field(None, description="客户端订单ID")
    binance_order_id: int | None = Field(None, description="币安订单ID")
    market_type: str = Field("FUTURES", description="市场类型")
    symbol: str = Field(..., description="交易对")
    status: str | None = Field(None, description="订单状态")

    # 附加数据
    data: dict[str, Any] = Field(default_factory=dict, description="币安API原始数据")
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")

    class Config:
        extra = "allow"  # 允许额外字段


class OrderListData(BaseModel):
    """订单列表数据

    设计参考：08-api-models.md OrderListData
    """

    orders: list[OrderData] = Field(default_factory=list, description="订单列表")
    count: int = Field(0, description="订单数量")

    @classmethod
    def from_list(cls, orders_data: list[dict[str, Any]]) -> "OrderListData":
        """从字典列表创建订单列表"""
        orders = [OrderData(**order) if isinstance(order, dict) else order for order in orders_data]
        return cls(orders=orders, count=len(orders))


class OrderUpdateData(OrderData):
    """订单更新推送数据

    继承 OrderData，额外包含实时更新的时间戳。

    设计参考：08-api-models.md OrderUpdateData
    """

    # 实时更新字段
    update_time: int | None = Field(None, description="更新时间戳（毫秒）")

    class Config:
        extra = "allow"


# 便捷验证函数

def validate_create_order_payload(data: dict[str, Any]) -> CreateOrderRequest:
    """验证并转换创建订单请求数据

    Args:
        data: 原始请求数据字典

    Returns:
        验证后的 CreateOrderRequest 对象

    Raises:
        ValidationError: 验证失败
    """
    return CreateOrderRequest(**data)


def validate_get_order_payload(data: dict[str, Any]) -> GetOrderRequest:
    """验证并转换查询订单请求数据

    Args:
        data: 原始请求数据字典

    Returns:
        验证后的 GetOrderRequest 对象

    Raises:
        ValidationError: 验证失败
    """
    return GetOrderRequest(**data)


def validate_cancel_order_payload(data: dict[str, Any]) -> CancelOrderRequest:
    """验证并转换撤销订单请求数据

    Args:
        data: 原始请求数据字典

    Returns:
        验证后的 CancelOrderRequest 对象

    Raises:
        ValidationError: 验证失败
    """
    return CancelOrderRequest(**data)
