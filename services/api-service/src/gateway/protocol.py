"""
消息协议封装

提供 WebSocket 消息的解析和格式化功能。
使用 Pydantic 模型进行数据验证，确保符合协议规范。

命名规范：
- data: 通用数据容器
- content: 实时推送的实际数据内容（避免与数据库 payload 混淆）
- payload: 数据库任务表的载荷字段
"""

import time
from typing import Any

from ..models.protocol.ws_message import (
    MessageSuccess,
    MessageError,
    MessageRequest,
    KlinesRequest,
    SubscribeRequest,
    UnsubscribeRequest,
)
from ..models.protocol.constants import PROTOCOL_VERSION


def parse_message(raw: dict[str, Any]) -> dict[str, Any]:
    """解析客户端消息

    使用 Pydantic 模型验证必要字段并返回标准化的请求格式。

    Args:
        raw: 原始消息字典

    Returns:
        解析后的请求字典

    Raises:
        ValueError: 消息格式无效
    """
    # 先用基础验证检查必要字段
    version = raw.get("protocolVersion") or raw.get("protocol_version")
    if version and version != PROTOCOL_VERSION:
        raise ValueError(f"Unsupported protocol version: {version}")

    msg_type = raw.get("type")
    if not msg_type:
        raise ValueError("Missing required field: type")

    timestamp = raw.get("timestamp")
    if not timestamp:
        raise ValueError("Missing required field: timestamp")

    # 使用 Pydantic 模型验证完整消息结构
    try:
        validated = MessageRequest.model_validate({
            "protocolVersion": version or PROTOCOL_VERSION,
            "type": msg_type,
            "requestId": raw.get("requestId", ""),
            "timestamp": timestamp,
            "data": raw.get("data", {}),
        })
        return validated.model_dump(by_alias=True)
    except Exception as e:
        raise ValueError(f"Invalid message format: {e}")


def validate_klines_request(data: dict[str, Any]) -> KlinesRequest:
    """验证 K线数据请求

    Args:
        data: 请求数据

    Returns:
        验证后的 KlinesRequest 模型

    Raises:
        ValidationError: 验证失败
    """
    return KlinesRequest.model_validate(data)


def validate_subscribe_request(data: dict[str, Any]) -> SubscribeRequest:
    """验证订阅请求

    Args:
        data: 请求数据

    Returns:
        验证后的 SubscribeRequest 模型

    Raises:
        ValidationError: 验证失败
    """
    return SubscribeRequest.model_validate(data)


def validate_unsubscribe_request(data: dict[str, Any]) -> UnsubscribeRequest:
    """验证取消订阅请求

    Args:
        data: 请求数据

    Returns:
        验证后的 UnsubscribeRequest 模型

    Raises:
        ValidationError: 验证失败
    """
    return UnsubscribeRequest.model_validate(data)


def format_success_response(
    request_id: str | None,
    data: dict[str, Any],
    response_type: str = "SUCCESS",
) -> dict[str, Any]:
    """格式化成功响应

    使用 Pydantic 模型确保响应符合协议规范。

    严格遵循07-websocket-protocol.md规范：
    - type 字段使用具体数据类型（如 KLINES_DATA, CONFIG_DATA 等）
    - 不使用泛化的 "success"

    Args:
        request_id: 请求 ID
        data: 响应数据
        response_type: 响应数据类型（如 KLINES_DATA, CONFIG_DATA 等）

    Returns:
        响应消息字典
    """
    response = MessageSuccess(
        type=response_type,
        request_id=request_id or "",
        protocol_version=PROTOCOL_VERSION,
        timestamp=_timestamp_ms(),
        data=data,
    )
    return response.model_dump(by_alias=True)


def format_error_response(
    request_id: str | None,
    error_code: str,
    error_message: str,
) -> dict[str, Any]:
    """格式化错误响应

    使用 Pydantic 模型确保响应符合协议规范。

    严格遵循07-websocket-protocol.md规范：
    - type 字段值为 "ERROR"

    Args:
        request_id: 请求 ID
        error_code: 错误代码
        error_message: 错误信息

    Returns:
        错误响应字典
    """
    response = MessageError(
        type="ERROR",
        request_id=request_id or "",
        protocol_version=PROTOCOL_VERSION,
        timestamp=_timestamp_ms(),
        data={
            "errorCode": error_code,
            "errorMessage": error_message,
        },
    )
    return response.model_dump(by_alias=True)


def format_update_message(
    event_type: str,
    content: dict[str, Any],  # 使用 content 避免与数据库 payload 混淆
    subscription_key: str,
) -> dict[str, Any]:
    """格式化更新消息（服务器推送）

    使用 Pydantic 模型确保响应符合协议规范。

    严格遵循07-websocket-protocol.md规范：
    - type 字段值为 "UPDATE"
    - 使用 content 字段存储实际数据，避免与数据库 payload 混淆
    - 不包含 requestId 字段（服务器主动推送）

    Args:
        event_type: 事件类型
        content: 实时数据内容
        subscription_key: 订阅键

    Returns:
        更新消息字典
    """
    from ..models.protocol.ws_message import MessageUpdate

    response = MessageUpdate(
        type="UPDATE",
        protocol_version=PROTOCOL_VERSION,
        timestamp=_timestamp_ms(),
        data={
            "eventType": event_type,
            "subscriptionKey": subscription_key,
            "content": content,
        },
    )
    return response.model_dump(by_alias=True)


def format_ping_message() -> dict[str, Any]:
    """格式化心跳消息

    Returns:
        心跳消息字典
    """
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "type": "PING",
        "timestamp": _timestamp_ms(),
    }


def format_pong_message() -> dict[str, Any]:
    """格式化心跳响应消息

    Returns:
        心跳响应消息字典
    """
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "type": "PONG",
        "timestamp": _timestamp_ms(),
    }


def _timestamp_ms() -> int:
    """获取当前时间戳（毫秒）"""
    return int(time.time() * 1000)
