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

from pydantic import BaseModel, Field, field_validator, model_validator

from ..base import SnakeCaseModel

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


class CreateOrderRequest(SnakeCaseModel):
    """创建订单请求

    必填字段：symbol, side, type, quantity, new_client_order_id
    可选字段根据 order type 不同而变化

    设计参考：
    - 现货: https://binance-docs.github.io/apidocs/spot/cn/#trade
    - 期货: https://binance-docs.github.io/apidocs/futures/cn/#trade

    完全采用币安蛇形命名，前端发送camelCase后端自动转换
    """

    # 必填字段
    symbol: str = Field(..., description="交易对符号，如 BTCUSDT")
    side: str = Field(..., description="订单方向：BUY 或 SELL")
    type: str = Field(..., description="订单类型：LIMIT, MARKET 等")
    quantity: float = Field(..., gt=0, description="订单数量，必须大于0")

    # 必填：订单标识（UUID格式）
    new_client_order_id: str = Field(..., description="客户端订单ID（UUID格式，必填）")

    # 可选字段（蛇形命名与币安一致）
    price: float | None = Field(None, description="限价价格")
    time_in_force: str | None = Field(None, description="订单有效时间：GTC, IOC, FOK")
    position_side: str | None = Field("BOTH", description="持仓方向：BOTH, LONG, SHORT")
    reduce_only: bool = Field(False, description="是否只减仓")
    stop_price: float | None = Field(None, description="止损价格")
    activation_price: float | None = Field(None, description="触发价格（追踪止损）")
    callback_rate: float | None = Field(None, description="回调比例（0.1-10）")
    working_type: str | None = Field("CONTRACT_PRICE", description="触发价格类型")
    price_protect: bool = Field(False, description="价格保护")
    close_position: bool = Field(False, description="是否全平仓")
    price_match: str | None = Field(None, description="价格匹配")
    good_till_date: int | None = Field(None, description="GTD订单取消时间")

    # 现货可选字段
    quote_order_qty: float | None = Field(None, description="报价数量（市价买单时指定支付金额）")
    iceberg_qty: float | None = Field(None, description="冰山订单数量")
    self_trade_prevention_mode: str | None = Field(None, description="自成交防止模式")
    new_order_resp_type: str | None = Field("FULL", description="响应格式：ACK, RESULT, FULL")

    @model_validator(mode="after")
    def validate_order(self) -> "CreateOrderRequest":
        """验证订单必填字段"""

        # 限价单必须有价格
        if self.type == "LIMIT" and self.price is None:
            raise ValueError("Limit order requires price field")

        # LIMIT 订单必须有 time_in_force
        if self.type == "LIMIT" and self.time_in_force is None:
            raise ValueError("Limit order requires timeInForce field")

        return self


class GetOrderRequest(SnakeCaseModel):
    """查询订单请求

    至少需要提供 order_id 或 orig_client_order_id 之一

    设计参考：04-trading-orders.md order.query 参数
    - 前端发送 camelCase，后端自动转换为 snake_case
    - 通过 symbol 前缀区分期货/现货（.PERP 为期货）
    - 现货和期货参数完全一致
    """

    symbol: str = Field(..., description="交易对符号")
    order_id: int | str | None = Field(None, description="币安订单ID")
    orig_client_order_id: str | None = Field(None, description="客户端自定义订单ID")

    @field_validator("order_id", mode="before")
    @classmethod
    def convert_order_id(cls, v):
        """允许字符串形式的数字"""
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v

    @model_validator(mode="after")
    def validate_required_fields(self) -> "GetOrderRequest":
        """验证必填字段"""
        if not self.order_id and not self.orig_client_order_id:
            raise ValueError("Either orderId or origClientOrderId is required")
        return self


class ListOrdersRequest(SnakeCaseModel):
    """查询订单列表请求

    可选过滤条件

    设计参考：04-trading-orders.md
    - 前端发送 camelCase，后端自动转换为 snake_case
    - 通过 symbol 前缀区分期货/现货（.PERP 为期货）
    """

    symbol: str | None = Field(None, description="交易对符号")
    status: str | None = Field(None, description="订单状态过滤")
    start_time: int | None = Field(None, description="起始时间（毫秒）")
    end_time: int | None = Field(None, description="结束时间（毫秒）")
    limit: int = Field(100, ge=1, le=1000, description="返回数量限制")


class CancelOrderRequest(SnakeCaseModel):
    """撤销订单请求

    至少需要提供 order_id 或 orig_client_order_id 之一

    设计参考：04-trading-orders.md order.cancel 参数
    - 前端发送 camelCase，后端自动转换为 snake_case
    - 通过 symbol 前缀区分期货/现货（.PERP 为期货）
    - 现货特有可选参数：new_client_order_id, cancel_restrictions
    """

    symbol: str = Field(..., description="交易对符号")
    order_id: int | str | None = Field(None, description="币安订单ID")
    orig_client_order_id: str | None = Field(None, description="客户端自定义订单ID")

    # 现货特有可选参数（期货不支持）
    new_client_order_id: str | None = Field(
        None, description="用于唯一标识此次取消操作（仅现货支持）"
    )
    cancel_restrictions: str | None = Field(
        None, description="取消限制条件：ONLY_NEW, ONLY_PARTIALLY_FILLED（仅现货支持）"
    )

    @field_validator("order_id", mode="before")
    @classmethod
    def convert_order_id(cls, v):
        """允许字符串形式的数字"""
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v

    @model_validator(mode="after")
    def validate_required_fields(self) -> "CancelOrderRequest":
        """验证必填字段"""
        if not self.order_id and not self.orig_client_order_id:
            raise ValueError("Either orderId or origClientOrderId is required")
        return self


class GetOpenOrdersRequest(SnakeCaseModel):
    """查询当前挂单请求

    设计参考：04-trading-orders.md
    - 前端发送 camelCase，后端自动转换为 snake_case
    - 通过 symbol 前缀区分期货/现货（.PERP 为期货）
    """

    symbol: str | None = Field(None, description="交易对符号，不传则返回所有")


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
