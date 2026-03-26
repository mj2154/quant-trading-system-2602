"""
WebSocket消息协议模型

定义统一消息协议相关的所有数据模型。
严格遵循 TradingView API 规范设计文档 v2.0。

作者: Claude Code
版本: v2.0.0
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

# 使用本地基类进行命名转换
from ..base import CamelCaseModel, SnakeCaseModel

# 从 ws_payload 导入具体数据模型
from .ws_payload import ErrorData  # noqa: E402

# 从 trading 模块导入数据模型

# ==================== 协议常量 ====================

PROTOCOL_VERSION = "2.0"
WS_PATH = "/ws"
PING_INTERVAL = 20  # 秒
PING_TIMEOUT = 60  # 秒


# ==================== 通用消息模型 ====================


class WebSocketMessage(SnakeCaseModel):
    """
    统一WebSocket消息

    严格遵循07-websocket-protocol.md规范：
    - 接收前端camelCase输入，自动转换为snake_case内部字段
    - 使用 type 字段表示消息类型

    请求类型：GET_KLINES, GET_QUOTES, SUBSCRIBE, UNSUBSCRIBE 等
    """

    protocol_version: str = PROTOCOL_VERSION
    type: str  # 消息类型：GET_KLINES, SUBSCRIBE, UNSUBSCRIBE 等
    request_id: str
    timestamp: int  # 时间戳（毫秒）
    data: dict[str, Any] | None = None  # 消息数据

    def __str__(self) -> str:
        return f"WebSocketMessage(type={self.type}, request_id={self.request_id})"


# ==================== 请求消息模型 ====================


class MessageRequest(WebSocketMessage):
    """请求消息 - 用于前端发送的请求

    严格遵循07-websocket-protocol.md规范：
    - 使用 type 字段表示请求类型
    - 默认 type 为 GET（通用获取）
    """

    type: str = "GET"
    data: dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        return f"MessageRequest(type={self.type}, request_id={self.request_id})"


class ConfigRequest(SnakeCaseModel):
    """配置请求"""

    type: str = "config"


class SearchSymbolsRequest(SnakeCaseModel):
    """搜索交易对请求"""

    type: str = "search_symbols"
    query: str | None = None
    exchange: str | None = None
    type_filter: str | None = None
    limit: int = 50
    offset: int = 0

    def __str__(self) -> str:
        return f"SearchSymbolsRequest(query={self.query}, exchange={self.exchange})"


class ResolveSymbolRequest(SnakeCaseModel):
    """解析交易对请求"""

    type: str = "resolve_symbol"
    symbol: str

    def __str__(self) -> str:
        return f"ResolveSymbolRequest(symbol={self.symbol})"


class KlinesRequest(SnakeCaseModel):
    """K线数据请求

    注意：使用 interval 而非 resolution，以与数据库字段和内部逻辑保持一致。
    前端传入的 resolution 会在订阅转换器中自动转换为 interval。
    """

    type: str = "klines"
    symbol: str
    interval: str  # 统一使用 interval，与数据库字段和内部逻辑一致
    from_time: int
    to_time: int

    def __str__(self) -> str:
        return f"KlinesRequest(symbol={self.symbol}, interval={self.interval})"


class ServerTimeRequest(SnakeCaseModel):
    """服务器时间请求"""

    type: str = "server_time"


class QuotesRequest(SnakeCaseModel):
    """报价数据请求"""

    type: str = "quotes"
    symbols: list[str]

    def __str__(self) -> str:
        return f"QuotesRequest(symbols={self.symbols})"


class SubscribeRequest(SnakeCaseModel):
    """
    订阅请求

    严格遵循设计文档v2.0规范：
    使用订阅键数组格式，不支持字典格式。
    """

    subscriptions: list[str]

    def __str__(self) -> str:
        return f"SubscribeRequest(count={len(self.subscriptions)})"


class UnsubscribeRequest(SnakeCaseModel):
    """
    取消订阅请求

    精确取消或全部取消。
    """

    subscriptions: list[str] | None = None
    all: bool = False

    def __str__(self) -> str:
        if self.all:
            return "UnsubscribeRequest(all=True)"
        sub_count = len(self.subscriptions) if self.subscriptions else 0
        return f"UnsubscribeRequest(count={sub_count})"


class SubscriptionsRequest(SnakeCaseModel):
    """查询订阅请求

    遵循API设计文档v2.1规范：type 改为 subscriptions
    """

    type: str = "subscriptions"
    client_id: str | None = None


class MetricsRequest(SnakeCaseModel):
    """指标查询请求"""

    type: str = "metrics"


# ==================== 响应消息模型 ====================


class MessageResponseBase(CamelCaseModel):
    """响应基类

    严格遵循07-websocket-protocol.md规范：
    - 使用 type 字段表示消息类型
    - type 字段放在顶层，不在 data 内部
    - data 必须是 Pydantic BaseModel 实例

    内部使用snake_case，序列化输出camelCase。
    """

    protocol_version: str = PROTOCOL_VERSION
    type: str  # 消息类型：ACK, SUCCESS, ERROR, UPDATE 等
    request_id: str
    task_id: int | None = None
    timestamp: int
    data: CamelCaseModel  # 必须是 CamelCaseModel 实例，用于响应输出

    def __str__(self) -> str:
        return f"MessageResponseBase(type={self.type}, request_id={self.request_id})"


class MessageSuccess(MessageResponseBase):
    """成功响应消息

    严格遵循07-websocket-protocol.md规范：
    - type 字段使用具体数据类型，如 KLINES_DATA, CONFIG_DATA, SUBSCRIPTION_DATA 等
    - 成功响应的 type 使用数据类型而非 "SUCCESS"
    """

    type: str  # 数据类型：KLINES_DATA, CONFIG_DATA, SUBSCRIPTION_DATA 等

    def __str__(self) -> str:
        return f"MessageSuccess(type={self.type}, request_id={self.request_id}, task_id={self.task_id})"


class MessageError(MessageResponseBase):
    """错误响应消息

    严格遵循07-websocket-protocol.md规范：
    - type 字段值为 "ERROR"
    - 错误详情放在 data 内部

    使用 ErrorData 模型确保类型安全。
    """

    type: str = "ERROR"
    data: ErrorData

    def __str__(self) -> str:
        return f"MessageError(code={self.data.error_code}, message={self.data.error_message})"


class MessageUpdate(CamelCaseModel):
    """
    实时数据更新消息

    严格遵循07-websocket-protocol.md规范：
    - type 字段值为 "UPDATE"
    - subscriptionKey 提升到顶层
    - data 直接作为数据载荷（与设计文档保持一致，无 content 包装）
    - 注意：不包含 requestId 字段（服务器主动推送）

    内部使用snake_case，序列化输出camelCase。

    JSON 结构：
    {
        "type": "UPDATE",
        "timestamp": 123,
        "subscriptionKey": "...",
        "data": {...}
    }
    """

    protocol_version: str = PROTOCOL_VERSION
    type: str = "UPDATE"
    timestamp: int
    subscription_key: str
    data: CamelCaseModel  # 直接作为数据载荷，无 content 包装

    def __str__(self) -> str:
        return f"MessageUpdate(key={self.subscription_key})"
