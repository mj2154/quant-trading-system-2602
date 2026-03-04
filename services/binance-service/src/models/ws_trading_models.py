"""
WebSocket交易请求/响应模型

用于私有WebSocket交易的请求和响应数据结构。
支持Ed25519签名认证的订单操作。
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class WSRequest(BaseModel):
    """WebSocket请求基础模型

    字段说明：
    - id: 请求ID，用于匹配响应
    - method: 请求方法名
    - params: 请求参数
    """

    id: str
    method: str
    params: Optional[dict[str, Any]] = None


class WSResponse(BaseModel):
    """WebSocket响应模型

    字段说明：
    - id: 请求ID，用于匹配请求
    - status: 响应状态码（200成功，4xx/5xx失败）
    - result: 成功时的响应数据（可能是字典或数组）
    - error: 失败时的错误信息
    """

    id: str
    status: int
    result: Optional[Any] = None  # 支持字典和数组类型
    error: Optional[dict[str, Any]] = None


class WSAuthParams(BaseModel):
    """WebSocket session.logon 认证参数

    字段说明：
    - api_key: API密钥
    - signature: Ed25519签名
    - timestamp: 毫秒时间戳
    - recv_window: 接收窗口时间（可选）
    """

    api_key: str = Field(..., alias="apiKey")
    signature: str
    timestamp: int
    recv_window: Optional[int] = Field(default=None, alias="recvWindow")

    model_config = {"populate_by_name": True}


class WSOrderParams(BaseModel):
    """WebSocket订单请求参数

    字段说明：
    - symbol: 交易对符号
    - side: 订单方向（BUY/SELL）
    - type: 订单类型（LIMIT/MARKET/STOP_LOSS等）
    - time_in_force: 时间策略（GTC/IOC/FOK）
    - price: 价格
    - quantity: 数量
    - stop_price: 止损价格
    - new_client_order_id: 客户端订单ID
    - timestamp: 毫秒时间戳
    - api_key: API密钥
    - signature: Ed25519签名
    - recv_window: 接收窗口时间
    """

    symbol: str
    side: str
    order_type: str = Field(..., alias="type")
    quantity: Optional[str] = None
    price: Optional[str] = None
    time_in_force: Optional[str] = Field(default=None, alias="timeInForce")
    stop_price: Optional[str] = Field(default=None, alias="stopPrice")
    new_client_order_id: Optional[str] = Field(
        default=None, alias="newClientOrderId"
    )
    quote_order_qty: Optional[str] = Field(default=None, alias="quoteOrderQty")
    # 签名相关参数
    timestamp: int
    api_key: str = Field(..., alias="apiKey")
    signature: str
    recv_window: Optional[int] = Field(default=None, alias="recvWindow")

    model_config = {"populate_by_name": True}


class WSAuthResponse(BaseModel):
    """WebSocket session.logon 认证响应

    基于官方期货WebSocket API文档：
    - api_key: API密钥
    - authorized_since: 认证开始时间（毫秒）
    - connected_since: 连接建立时间（毫秒）
    - return_rate_limits: 是否返回速率限制信息
    - server_time: 服务器时间（毫秒）
    """

    api_key: Optional[str] = Field(default=None, alias="apiKey")
    authorized_since: Optional[int] = Field(default=None, alias="authorizedSince")
    connected_since: int = Field(..., alias="connectedSince")
    return_rate_limits: bool = Field(default=False, alias="returnRateLimits")
    server_time: int = Field(..., alias="serverTime")

    model_config = {"populate_by_name": True}


class WSOrderResponse(BaseModel):
    """WebSocket订单响应

    基于官方U本位合约期货API文档：
    https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/websocket-api

    字段说明：
    - order_id: 订单ID
    - symbol: 交易对
    - status: 订单状态（NEW/FILLED/PARTIALLY_FILLED/CANCELED/REJECTED/EXPIRED）
    - client_order_id: 客户端订单ID
    - price: 价格
    - avg_price: 平均成交价格
    - orig_qty: 原始数量
    - executed_qty: 已执行数量
    - cum_qty: 累计成交数量
    - cum_quote: 累计成交额（USDT-M）
    - time_in_force: 时间策略（GTC/IOC/FOK/GTD）
    - type: 订单类型（LIMIT/MARKET/STOP/TAKE_PROFIT等）
    - reduce_only: 是否仅减仓
    - close_position: 是否平仓
    - side: 订单方向（BUY/SELL）
    - position_side: 持仓方向（BOTH/LONG/SHORT）
    - stop_price: 止损价格
    - working_type: 工作价格类型（MARK_PRICE/CONTRACT_PRICE）
    - price_protect: 价格保护
    - orig_type: 原始订单类型
    - price_match: 价格匹配模式
    - self_trade_prevention_mode: 自成交防止模式
    - good_till_date: 有效日期
    - time: 订单创建时间（毫秒）
    - update_time: 最后更新时间（毫秒）
    """

    # 核心字段 - 使用Optional和默认值来处理缺失字段
    order_id: int = Field(..., alias="orderId")
    symbol: str
    status: str

    # 订单标识
    client_order_id: str = Field(..., alias="clientOrderId")

    # 价格和数量
    price: str = "0.00"
    avg_price: str = Field(default="0.00", alias="avgPrice")
    orig_qty: str = "0.000"
    executed_qty: str = Field(default="0.000", alias="executedQty")
    cum_qty: str = Field(default="0.000", alias="cumQty")
    cum_quote: str = Field(default="0.00000", alias="cumQuote")

    # 订单类型和方向
    side: str = "BUY"
    type: str = "MARKET"
    orig_type: Optional[str] = Field(default=None, alias="origType")

    # 时间策略
    time_in_force: str = Field(default="GTC", alias="timeInForce")
    good_till_date: int = Field(default=0, alias="goodTillDate")

    # 仓位控制 - 实际返回bool类型
    reduce_only: bool = Field(default=False, alias="reduceOnly")
    close_position: bool = Field(default=False, alias="closePosition")
    position_side: str = Field(default="BOTH", alias="positionSide")

    # 止损止盈 - 实际返回字符串"0.00"格式
    stop_price: str = Field(default="0.00", alias="stopPrice")
    working_type: str = Field(default="CONTRACT_PRICE", alias="workingType")
    price_protect: bool = Field(default=False, alias="priceProtect")

    # 高级订单类型
    price_match: str = Field(default="NONE", alias="priceMatch")
    self_trade_prevention_mode: str = Field(
        default="NONE", alias="selfTradePreventionMode"
    )

    # 时间戳 - time字段可能不存在，使用Optional
    time: Optional[int] = None
    update_time: int = Field(..., alias="updateTime")

    model_config = {"populate_by_name": True}


class WSCancelOrderParams(BaseModel):
    """WebSocket撤单请求参数

    字段说明：
    - symbol: 交易对符号
    - order_id: 订单ID（可选，与clientOrderId二选一）
    - orig_client_order_id: 客户端订单ID（可选，与orderId二选一）
    - timestamp: 毫秒时间戳
    - api_key: API密钥
    - signature: Ed25519签名
    - recv_window: 接收窗口时间
    """

    symbol: str
    order_id: Optional[str] = Field(default=None, alias="orderId")
    orig_client_order_id: Optional[str] = Field(
        default=None, alias="origClientOrderId"
    )
    timestamp: int
    api_key: str = Field(..., alias="apiKey")
    signature: str
    recv_window: Optional[int] = Field(default=None, alias="recvWindow")

    model_config = {"populate_by_name": True}


class WSQueryOrderParams(BaseModel):
    """WebSocket查询订单请求参数

    字段说明：
    - symbol: 交易对符号
    - order_id: 订单ID（可选，与clientOrderId二选一）
    - orig_client_order_id: 客户端订单ID（可选，与orderId二选一）
    - timestamp: 毫秒时间戳
    - api_key: API密钥
    - signature: Ed25519签名
    - recv_window: 接收窗口时间
    """

    symbol: str
    order_id: Optional[str] = Field(default=None, alias="orderId")
    orig_client_order_id: Optional[str] = Field(
        default=None, alias="origClientOrderId"
    )
    timestamp: int
    api_key: str = Field(..., alias="apiKey")
    signature: str
    recv_window: Optional[int] = Field(default=None, alias="recvWindow")

    model_config = {"populate_by_name": True}
