"""
消息协议封装

提供 WebSocket 消息的解析和格式化功能。

命名规范：
- data: 通用数据容器
- content: 实时推送的实际数据内容（避免与数据库 payload 混淆）
- payload: 数据库任务表的载荷字段
"""

import json
from typing import Any

PROTOCOL_VERSION = "2.0"


def parse_message(raw: dict[str, Any]) -> dict[str, Any]:
    """解析客户端消息

    验证必要字段并返回标准化的请求格式。

    Args:
        raw: 原始消息字典

    Returns:
        解析后的请求字典

    Raises:
        ValueError: 消息格式无效
    """
    # 验证协议版本
    version = raw.get("protocolVersion") or raw.get("protocol_version")
    if version and version != PROTOCOL_VERSION:
        raise ValueError(f"Unsupported protocol version: {version}")

    # 验证消息类型（严格遵循07-websocket-protocol.md）
    msg_type = raw.get("type")
    if not msg_type:
        raise ValueError("Missing required field: type")

    # 验证时间戳
    timestamp = raw.get("timestamp")
    if not timestamp:
        raise ValueError("Missing required field: timestamp")

    return {
        "protocolVersion": version or PROTOCOL_VERSION,
        "type": msg_type,  # 遵循07-websocket-protocol.md规范：使用type字段
        "requestId": raw.get("requestId"),
        "timestamp": timestamp,
        "data": raw.get("data", {}),
    }


def format_success_response(
    request_id: str | None,
    data: dict[str, Any],
    response_type: str = "SUCCESS",
) -> dict[str, Any]:
    """格式化成功响应

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
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "type": response_type,  # 使用具体数据类型，非 "success"
        "requestId": request_id,
        "timestamp": _timestamp(),
        "data": data,
    }


def format_error_response(
    request_id: str | None,
    error_code: str,
    error_message: str,
) -> dict[str, Any]:
    """格式化错误响应

    严格遵循07-websocket-protocol.md规范：
    - type 字段值为 "ERROR"

    Args:
        request_id: 请求 ID
        error_code: 错误代码
        error_message: 错误信息

    Returns:
        错误响应字典
    """
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "type": "ERROR",  # 遵循07-websocket-protocol.md规范
        "requestId": request_id,
        "timestamp": _timestamp(),
        "data": {
            "errorCode": error_code,
            "errorMessage": error_message,
        },
    }


def format_update_message(
    event_type: str,
    content: dict[str, Any],  # 使用 content 避免与数据库 payload 混淆
    subscription_key: str,
) -> dict[str, Any]:
    """格式化更新消息（服务器推送）

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
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "type": "UPDATE",  # 遵循07-websocket-protocol.md规范
        "timestamp": _timestamp_ms(),
        "data": {
            "eventType": event_type,
            "subscriptionKey": subscription_key,
            "content": content,  # 使用 content 而非 payload
        },
    }


def format_ping_message() -> dict[str, Any]:
    """格式化心跳消息

    Returns:
        心跳消息字典
    """
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "type": "PING",
        "timestamp": _timestamp(),
    }


def format_pong_message() -> dict[str, Any]:
    """格式化心跳响应消息

    Returns:
        心跳响应消息字典
    """
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "type": "PONG",
        "timestamp": _timestamp(),
    }


def _timestamp() -> int:
    """获取当前时间戳（秒）"""
    import time
    return int(time.time())


def _timestamp_ms() -> int:
    """获取当前时间戳（毫秒）"""
    import time
    return int(time.time() * 1000)
