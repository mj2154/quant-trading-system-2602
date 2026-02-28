"""
WebSocket协议消息模型

使用 Pydantic v2 最佳实践。
遵循数据命名规范：内部使用snake_case，序列化输出camelCase。
"""

from typing import Any, Literal

from pydantic import Field

# 使用本地基类进行命名转换
from ..models.base import CamelCaseModel, SnakeCaseModel


class WSRequest(SnakeCaseModel):
    """WebSocket请求消息

    接收前端camelCase输入，自动转换为snake_case内部字段。
    """

    protocol_version: str = "2.0"
    action: Literal["get", "subscribe", "unsubscribe"]
    request_id: str
    timestamp: int = Field(default_factory=lambda: int(__import__("time").time() * 1000))
    data: dict[str, Any] = Field(default_factory=dict)


class WSResponse(CamelCaseModel):
    """WebSocket响应消息

    遵循API设计文档v2.1规范：type 字段放在 data 内部，不在外层
    内部使用snake_case，序列化输出camelCase。
    """

    protocol_version: str = "2.0"
    action: Literal["success", "error"]
    request_id: str | None = None
    task_id: int | None = None  # 异步任务 ID（用于三阶段模式）
    timestamp: int = Field(default_factory=lambda: int(__import__("time").time() * 1000))
    data: dict[str, Any] = Field(default_factory=dict)


class WSUpdate(CamelCaseModel):
    """WebSocket推送消息

    内部使用snake_case，序列化输出camelCase。
    """

    protocol_version: str = "2.0"
    action: Literal["update"] = "update"
    timestamp: int = Field(default_factory=lambda: int(__import__("time").time() * 1000))
    data: dict[str, Any]


class ErrorData(CamelCaseModel):
    """错误数据

    内部使用snake_case，序列化输出camelCase。
    """

    error_code: str
    error_message: str


class AckData(CamelCaseModel):
    """确认消息数据

    严格遵循 07-websocket-protocol.md 规范：
    - type 字段值为 "ACK"
    - data 为空对象 {}

    内部使用snake_case，序列化输出camelCase。
    """

    # 空数据对象，严格遵循协议文档
    pass


class MessageAck(CamelCaseModel):
    """WebSocket ACK 确认消息（严格遵循 07-websocket-protocol.md 三阶段模式）

    协议要求：
    - type 字段值为 "ACK"
    - data 为空对象 {}
    - 返回 requestId 用于关联

    内部使用snake_case，序列化输出camelCase。
    """

    protocol_version: str = "2.0"
    type: Literal["ACK"] = "ACK"  # 严格遵循协议：type="ACK"
    request_id: str | None = None
    timestamp: int = Field(default_factory=lambda: int(__import__("time").time() * 1000))
    data: AckData = Field(default_factory=AckData)  # 空对象
