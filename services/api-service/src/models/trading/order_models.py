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
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from ..base import CamelCaseModel, SnakeCaseModel

logger = logging.getLogger(__name__)


class OrderSide(StrEnum):
    """订单方向"""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    """订单类型

    注意：现货和期货使用不同的订单类型命名！

    现货订单类型:
    - LIMIT, MARKET, LIMIT_MAKER
    - STOP_LOSS, STOP_LOSS_LIMIT
    - TAKE_PROFIT, TAKE_PROFIT_LIMIT
    - TRAILING_STOP_MARKET

    期货订单类型:
    - LIMIT, MARKET
    - STOP, STOP_MARKET
    - TAKE_PROFIT, TAKE_PROFIT_MARKET, TAKE_PROFIT_LIMIT
    - TRAILING_STOP_MARKET
    """

    # 现货 & 期货 通用
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    TRAILING_STOP_MARKET = "TRAILING_STOP_MARKET"

    # 现货专属
    LIMIT_MAKER = "LIMIT_MAKER"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"

    # 期货专属
    STOP = "STOP"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"


class OrderTimeInForce(StrEnum):
    """订单有效时间

    GTC - Good Till Cancel (成交为止)
    IOC - Immediate or Cancel (立即成交，否则取消)
    FOK - Fill or Kill (全部成交，否则取消)
    GTX - Good Till Crossing (Post Only 仅做Maker)
    GTD - Good Till Date (指定日期前有效)
    RPI - Retail Price Improvement (仅APP/Web)

    注意：GTX, GTD, RPI 仅期货支持
    """

    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"
    GTX = "GTX"  # 期货专属
    GTD = "GTD"  # 期货专属
    RPI = "RPI"  # 期货专属


class MarketType(StrEnum):
    """市场类型"""

    SPOT = "SPOT"
    FUTURES = "FUTURES"


class FuturesCreateOrderRequest(SnakeCaseModel):
    """期货创建订单请求

    严格遵循官方期货 API 文档设计：
    https://binance-docs.github.io/apidocs/futures/cn/#trade

    期货订单类型：LIMIT, MARKET, STOP, STOP_MARKET, TAKE_PROFIT, TAKE_PROFIT_MARKET, TRAILING_STOP_MARKET
    """

    # 必填字段
    symbol: str = Field(..., description="交易对符号，如 BTCUSDT")
    side: str = Field(..., description="订单方向：BUY 或 SELL")
    type: str = Field(..., description="订单类型：LIMIT, MARKET, STOP, STOP_MARKET, TAKE_PROFIT, TAKE_PROFIT_MARKET, TRAILING_STOP_MARKET")
    quantity: float = Field(..., gt=0, description="订单数量，必须大于0")

    # 订单标识（可选，币安自动生成）
    new_client_order_id: str | None = Field(None, description="客户端订单ID（可选，币安自动生成）")

    # 期货可选字段
    position_side: str | None = Field(None, description="持仓方向：BOTH, LONG, SHORT（对冲模式必填）")
    price: float | None = Field(None, description="限价价格（LIMIT 订单必填）")
    time_in_force: str | None = Field(None, description="订单有效时间：GTC, IOC, FOK, GTD")
    reduce_only: bool = Field(False, description="是否只减仓")
    stop_price: float | None = Field(None, description="止损/止盈价格")
    callback_rate: float | None = Field(None, description="回调比例（0.1-10，仅追踪止损）")
    new_order_resp_type: str | None = Field("ACK", description="响应格式：ACK, RESULT")
    price_match: str | None = Field(None, description="价格匹配模式")
    self_trade_prevention_mode: str | None = Field(None, description="自成交防止模式")
    good_till_date: int | None = Field(None, description="GTD 订单过期时间")

    @model_validator(mode="after")
    def validate_order(self) -> FuturesCreateOrderRequest:
        """验证期货订单必填字段"""
        # LIMIT 订单必须有价格
        if self.type == "LIMIT" and self.price is None:
            raise ValueError("Limit order requires price field")
        # LIMIT 订单必须有 time_in_force
        if self.type == "LIMIT" and self.time_in_force is None:
            raise ValueError("Limit order requires timeInForce field")
        return self


class SpotCreateOrderRequest(SnakeCaseModel):
    """现货创建订单请求

    严格遵循官方现货 API 文档设计：
    https://binance-docs.github.io/apidocs/spot/cn/#trade

    现货订单类型：LIMIT, MARKET, LIMIT_MAKER, STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT, TRAILING_STOP_MARKET
    """

    # 必填字段
    symbol: str = Field(..., description="交易对符号，如 BTCUSDT")
    side: str = Field(..., description="订单方向：BUY 或 SELL")
    type: str = Field(..., description="订单类型：LIMIT, MARKET, LIMIT_MAKER, STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT, TRAILING_STOP_MARKET")
    quantity: float = Field(..., gt=0, description="订单数量，必须大于0")

    # 订单标识（可选，币安自动生成）
    new_client_order_id: str | None = Field(None, description="客户端订单ID（可选，币安自动生成）")

    # 现货可选字段
    price: float | None = Field(None, description="限价价格（LIMIT/LIMIT_MAKER 订单必填）")
    time_in_force: str | None = Field(None, description="订单有效时间：GTC, IOC, FOK")
    quote_order_qty: float | None = Field(None, description="报价数量（市价买单时指定支付金额）")
    stop_price: float | None = Field(None, description="止损价格（止损单必需）")
    iceberg_qty: float | None = Field(None, description="冰山订单数量")
    trailing_delta: int | None = Field(None, description="追踪止损 delta")
    strategy_id: int | None = Field(None, description="策略 ID")
    strategy_type: int | None = Field(None, description="策略类型（值不能小于 1000000）")
    new_order_resp_type: str | None = Field("FULL", description="响应格式：ACK, RESULT, FULL")
    self_trade_prevention_mode: str | None = Field(None, description="自成交防止模式")

    @model_validator(mode="after")
    def validate_order(self) -> SpotCreateOrderRequest:
        """验证现货订单必填字段"""
        # LIMIT/LIMIT_MAKER 订单必须有价格
        if self.type in ("LIMIT", "LIMIT_MAKER") and self.price is None:
            raise ValueError(f"{self.type} order requires price field")
        # LIMIT 订单必须有 time_in_force
        if self.type == "LIMIT" and self.time_in_force is None:
            raise ValueError("Limit order requires timeInForce field")
        # 市价单必须有 quantity 或 quote_order_qty
        if self.type == "MARKET" and self.quantity is None and self.quote_order_qty is None:
            raise ValueError("Market order requires quantity or quoteOrderQty")
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
    def validate_required_fields(self) -> GetOrderRequest:
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
    def validate_required_fields(self) -> CancelOrderRequest:
        """验证必填字段"""
        if not self.order_id and not self.orig_client_order_id:
            raise ValueError("Either orderId or origClientOrderId is required")
        return self


class FuturesModifyOrderRequest(SnakeCaseModel):
    """期货修改订单请求

    期货 order.modify API - 可修改价格和数量，仅支持 LIMIT 订单

    设计参考：04-trading-orders.md order.modify 参数
    - 前端发送 camelCase，后端自动转换为 snake_case
    - 通过 symbol 前缀区分期货/现货（.PERP 为期货）
    """

    # 必填字段
    symbol: str = Field(..., description="交易对符号")
    side: str = Field(..., description="订单方向：BUY 或 SELL")
    quantity: float = Field(..., gt=0, description="新订单数量")
    price: float = Field(..., gt=0, description="新订单价格")
    timestamp: int = Field(..., description="时间戳（毫秒）")

    # orderId 或 origClientOrderId 至少填写一个
    order_id: int | str | None = Field(None, description="币安订单ID")
    orig_client_order_id: str | None = Field(None, description="客户端自定义订单ID")

    # 可选字段
    new_client_order_id: str | None = Field(
        None, description="新客户端订单ID（用于标识此次修改）"
    )
    position_side: str | None = Field(
        None, description="持仓方向：BOTH, LONG, SHORT"
    )
    price_match: str | None = Field(
        None, description="价格匹配模式（与 price 不能同时使用）"
    )
    recv_window: int | None = Field(
        None, description="接收窗口时间（可选）"
    )

    @field_validator("order_id", mode="before")
    @classmethod
    def convert_order_id(cls, v):
        """允许字符串形式的数字"""
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v

    @model_validator(mode="after")
    def validate_required_fields(self) -> FuturesModifyOrderRequest:
        """验证必填字段"""
        if not self.order_id and not self.orig_client_order_id:
            raise ValueError("Either orderId or origClientOrderId is required")
        return self


class SpotAmendOrderRequest(SnakeCaseModel):
    """现货修改订单请求

    现货 order.amend.keepPriority API - 只能减少数量

    设计参考：04-trading-orders.md order.modify 参数
    - 前端发送 camelCase，后端自动转换为 snake_case
    - 通过 symbol 前缀区分期货/现货
    """

    # 必填字段
    symbol: str = Field(..., description="交易对符号")
    new_qty: float = Field(..., gt=0, description="新订单数量（必须小于原订单数量）")
    timestamp: int = Field(..., description="时间戳（毫秒）")

    # orderId 或 origClientOrderId 至少填写一个
    order_id: int | str | None = Field(None, description="币安订单ID")
    orig_client_order_id: str | None = Field(None, description="客户端自定义订单ID")

    # 可选字段
    new_client_order_id: str | None = Field(
        None, description="新客户端订单ID（用于标识此次修改）"
    )
    recv_window: int | None = Field(
        None, description="接收窗口时间（可选，最大60000）"
    )

    @field_validator("order_id", mode="before")
    @classmethod
    def convert_order_id(cls, v):
        """允许字符串形式的数字"""
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v

    @model_validator(mode="after")
    def validate_required_fields(self) -> SpotAmendOrderRequest:
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


class OrderData(CamelCaseModel):
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

    model_config = {"extra": "allow"}  # 允许额外字段


class OrderListData(CamelCaseModel):
    """订单列表数据

    设计参考：08-api-models.md OrderListData
    """

    orders: list[OrderData] = Field(default_factory=list, description="订单列表")
    count: int = Field(0, description="订单数量")

    @classmethod
    def from_list(cls, orders_data: list[dict[str, Any]]) -> OrderListData:
        """从字典列表创建订单列表"""
        orders = [
            OrderData(**order) if isinstance(order, dict) else order
            for order in orders_data
        ]
        return cls(orders=orders, count=len(orders))


class OrderUpdateData(OrderData):
    """订单更新推送数据

    继承 OrderData，额外包含实时更新的时间戳。

    设计参考：08-api-models.md OrderUpdateData
    """

    # 实时更新字段
    update_time: int | None = Field(None, description="更新时间戳（毫秒）")

    model_config = {"extra": "allow"}


# ==================== 响应数据模型 ====================


class OrderListResponseData(CamelCaseModel):
    """订单列表响应数据模型

    用于构建 WebSocket 响应，确保类型安全。
    替代手动字典拼接。

    设计原则：
    - 使用 Pydantic 模型确保类型安全
    - 禁止在响应处理中手动拼装字典

    版本: v1.0.0
    """

    orders: list[OrderData]  # 订单列表
    count: int = 0  # 订单数量


class OrderCancelResponseData(CamelCaseModel):
    """取消订单响应数据模型

    用于构建取消订单的 WebSocket 响应。

    版本: v1.0.0
    """

    task_id: int | None = Field(None, description="任务ID")
    status: str = Field("PENDING", description="订单状态")
    order_id: str | None = Field(None, description="币安订单ID")
    orig_client_order_id: str | None = Field(None, description="客户端订单ID")


class FuturesModifyOrderResponseData(CamelCaseModel):
    """期货修改订单响应数据模型

    期货 order.modify 响应直接返回订单对象。

    设计参考：08-api-models.md FuturesModifyOrderResponseData
    版本: v1.0.0
    """

    task_id: int | None = Field(None, description="任务ID")
    status: str = Field("PENDING", description="订单状态")
    orig_client_order_id: str | None = Field(None, description="原客户端订单ID")

    # 订单信息
    order_id: int | None = Field(None, description="币安订单ID")
    symbol: str | None = Field(None, description="交易对")
    price: str | None = Field(None, description="订单价格")
    avg_price: str | None = Field(None, description="平均成交价格")
    orig_qty: str | None = Field(None, description="原始数量")
    executed_qty: str | None = Field(None, description="已执行数量")
    order_type: str | None = Field(None, alias="type", description="订单类型")
    side: str | None = Field(None, description="买卖方向")
    position_side: str | None = Field(None, description="持仓方向")
    stop_price: str | None = Field(None, description="止损价格")
    time_in_force: str | None = Field(None, description="时间策略")
    update_time: int | None = Field(None, description="更新时间")


class SpotAmendOrderResponseData(CamelCaseModel):
    """现货修改订单响应数据模型

    现货 order.amend.keepPriority 响应包含 amendedOrder 嵌套数据。

    设计参考：08-api-models.md SpotAmendOrderResponseData
    版本: v1.0.0
    """

    task_id: int | None = Field(None, description="任务ID")
    status: str = Field("PENDING", description="订单状态")
    orig_client_order_id: str | None = Field(None, description="原客户端订单ID")

    # 执行信息
    transact_time: int | None = Field(None, description="交易时间（毫秒）")
    execution_id: int | None = Field(None, description="执行ID")

    # amendedOrder 订单数据
    amended_order_id: int | None = Field(None, description="修改后的订单ID")
    amended_symbol: str | None = Field(None, description="交易对")
    amended_price: str | None = Field(None, description="订单价格")
    amended_qty: str | None = Field(None, description="订单数量")
    amended_executed_qty: str | None = Field(None, description="已执行数量")
    amended_status: str | None = Field(None, description="订单状态")
    amended_order_type: str | None = Field(None, alias="amendedType", description="订单类型")
    amended_side: str | None = Field(None, description="买卖方向")
    amended_time_in_force: str | None = Field(None, alias="amendedTimeInForce", description="时间策略")


class OpenOrdersResponseData(CamelCaseModel):
    """当前挂单响应数据模型

    用于构建查询挂单的 WebSocket 响应。

    版本: v1.0.0
    """

    orders: list[OrderData]  # 挂单列表
    count: int = 0  # 挂单数量


# 便捷验证函数


def validate_create_order_payload(
    data: dict[str, Any],
) -> FuturesCreateOrderRequest | SpotCreateOrderRequest:
    """验证并转换创建订单请求数据

    Args:
        data: 原始请求数据字典

    Returns:
        验证后的订单请求对象

    Raises:
        ValidationError: 验证失败
    """
    # 根据 market_type 或 symbol 自动选择验证模型
    symbol = data.get("symbol", "").upper()
    if ".PERP" in symbol or "BINANCE:" in symbol and not (
        symbol.startswith("BINANCE:") and ".PERP" not in symbol
    ):
        return FuturesCreateOrderRequest(**data)
    return SpotCreateOrderRequest(**data)


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


def validate_futures_modify_order_payload(data: dict[str, Any]) -> FuturesModifyOrderRequest:
    """验证并转换期货修改订单请求数据

    Args:
        data: 原始请求数据字典

    Returns:
        验证后的 FuturesModifyOrderRequest 对象

    Raises:
        ValidationError: 验证失败
    """
    return FuturesModifyOrderRequest(**data)


def validate_spot_amend_order_payload(data: dict[str, Any]) -> SpotAmendOrderRequest:
    """验证并转换现货修改订单请求数据

    Args:
        data: 原始请求数据字典

    Returns:
        验证后的 SpotAmendOrderRequest 对象

    Raises:
        ValidationError: 验证失败
    """
    return SpotAmendOrderRequest(**data)
