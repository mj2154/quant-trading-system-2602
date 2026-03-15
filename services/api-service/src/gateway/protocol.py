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

from pydantic import BaseModel

from ..models.protocol.constants import PROTOCOL_VERSION
from ..models.protocol.ws_message import (
    KlinesRequest,
    MessageError,
    MessageRequest,
    MessageSuccess,
    MessageUpdate,
    SubscribeRequest,
    UnsubscribeRequest,
)


def parse_message(raw: dict[str, Any]) -> MessageRequest:
    """解析客户端消息

    使用 Pydantic 模型验证必要字段并返回标准化的请求模型。

    Args:
        raw: 原始消息字典

    Returns:
        MessageRequest 模型实例

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
        validated = MessageRequest.model_validate(
            {
                "protocolVersion": version or PROTOCOL_VERSION,
                "type": msg_type,
                "requestId": raw.get("requestId", ""),
                "timestamp": timestamp,
                "data": raw.get("data", {}),
            }
        )
        return validated
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
    data: BaseModel,
    response_type: str = "SUCCESS",
) -> MessageSuccess:
    """格式化成功响应

    使用 Pydantic 模型确保响应符合协议规范。

    严格遵循07-websocket-protocol.md规范：
    - type 字段使用具体数据类型（如 KLINES_DATA, CONFIG_DATA 等）
    - 不使用泛化的 "success"
    - data 字段直接使用数据模型，确保类型安全

    注意：此函数强制要求 data 为 Pydantic 模型，不接受字典。
    返回 MessageSuccess 模型，调用者如需 JSON 可调用 model_dump_json()。

    Args:
        request_id: 请求 ID
        data: 响应数据，必须是 Pydantic 模型
        response_type: 响应数据类型（如 KLINES_DATA, CONFIG_DATA 等）

    Returns:
        MessageSuccess 模型实例
    """
    response = MessageSuccess(
        type=response_type,
        request_id=request_id or "",
        protocol_version=PROTOCOL_VERSION,
        timestamp=_timestamp_ms(),
        data=data,
    )
    return response


def format_error_response(
    request_id: str | None,
    error_code: str,
    error_message: str,
) -> MessageError:
    """格式化错误响应

    使用 Pydantic 模型确保响应符合协议规范。

    严格遵循07-websocket-protocol.md规范：
    - type 字段值为 "ERROR"（在顶层）
    - 错误详情放在 data 内部（使用 ErrorData 模型）

    Args:
        request_id: 请求 ID
        error_code: 错误代码
        error_message: 错误信息

    Returns:
        MessageError 模型实例
    """
    from ..models.protocol.ws_payload import ErrorData

    error_data = ErrorData(
        error_code=error_code,
        error_message=error_message,
    )
    return MessageError(
        request_id=request_id or "",
        timestamp=_timestamp_ms(),
        data=error_data,
    )


def format_update_message(
    subscription_key: str,
    content: BaseModel,
) -> MessageUpdate:
    """格式化更新消息（服务器推送）

    使用 Pydantic 模型确保响应符合协议规范。

    严格遵循07-websocket-protocol.md规范：
    - type 字段值为 "UPDATE"
    - subscriptionKey 提升到顶层
    - content 作为数据载荷（不是 payload，避免与数据库 payload 混淆）
    - 不包含 requestId 字段（服务器主动推送）

    结构设计遵循"信封和信"原则：
    - subscriptionKey: 信封（标识数据类型）
    - content: 信（实际数据内容）

    注意：此函数强制要求 content 为 Pydantic 模型，不接受字典。

    Args:
        subscription_key: 订阅键（标识数据类型）
        content: 实时数据内容，必须是 Pydantic 模型

    Returns:
        MessageUpdate 模型实例
    """
    return MessageUpdate(
        timestamp=_timestamp_ms(),
        subscription_key=subscription_key,
        content=content,
    )


def _timestamp_ms() -> int:
    """获取当前时间戳（毫秒）"""
    return int(time.time() * 1000)
