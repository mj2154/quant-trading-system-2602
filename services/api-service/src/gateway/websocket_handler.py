"""
WebSocket 处理器

处理 /ws/market 端点的连接和消息。
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from .client_manager import ClientManager
from .task_router import TaskRouter
from .protocol import (
    parse_message,
    format_success_response,
    format_error_response,
    PROTOCOL_VERSION,
)

logger = logging.getLogger(__name__)


async def _safe_send(client_manager: ClientManager, client_id: str, message: dict) -> bool:
    """安全发送消息，捕获连接断开等异常

    Returns:
        True: 发送成功
        False: 发送失败（连接已断开）
    """
    try:
        await client_manager.send(client_id, message)
        return True
    except Exception as e:
        logger.debug(f"Failed to send message to {client_id}: {e}")
        return False


async def _safe_close(websocket: WebSocket, code: int = 1000) -> None:
    """安全关闭 WebSocket 连接

    Args:
        websocket: WebSocket 连接
        code: 关闭代码
    """
    try:
        await websocket.close(code=code)
    except Exception:
        pass  # 连接已关闭，静默忽略


async def ws_market(
    websocket: WebSocket,
    client_manager: ClientManager,
    task_router: TaskRouter,
) -> None:
    """WebSocket 端点 /ws/market

    处理客户端连接、消息收发、订阅管理。

    Args:
        websocket: FastAPI WebSocket 连接
        client_manager: 客户端管理器
        task_router: 任务路由器
    """
    # 接受连接
    await websocket.accept()

    # 注册客户端
    client_id = await client_manager.connect(websocket)
    logger.info(f"Client connected: {client_id}")

    try:
        while True:
            # 接收消息
            try:
                raw_data = await websocket.receive_text()
            except WebSocketDisconnect:
                break

            # 解析消息
            try:
                logger.info(f"Received WebSocket message: {raw_data[:200]}...")
                message = json.loads(raw_data)
                request = parse_message(message)
            except (json.JSONDecodeError, ValueError) as e:
                error_msg = format_error_response(
                    request_id=None,
                    error_code="INVALID_MESSAGE",
                    error_message=str(e),
                )
                await _safe_send(client_manager, client_id, error_msg)
                continue

            # 获取请求 ID
            request_id = message.get("requestId")

            # 路由任务
            try:
                response = await task_router.handle(
                    client_id=client_id,
                    request=request,
                )
                # _handle_get 返回 None 时表示消息已由 handler 内部发送（如实时订阅确认）
                if response is None:
                    logger.debug(f"Response is None, message already sent by handler")
                else:
                    # 设置 requestId 用于三阶段模式关联
                    if request_id:
                        response["requestId"] = request_id
                    await _safe_send(client_manager, client_id, response)
            except Exception as e:
                logger.exception(f"Error handling request: {e}")
                error_msg = format_error_response(
                    request_id=request_id,
                    error_code="INTERNAL_ERROR",
                    error_message="Internal server error",
                )
                await _safe_send(client_manager, client_id, error_msg)

    except asyncio.CancelledError:
        logger.info(f"Client connection cancelled: {client_id}")
    except RuntimeError as e:
        # 处理 WebSocket 相关运行时错误（如连接已关闭）
        logger.debug(f"WebSocket runtime error (connection may be closed): {e}")
    finally:
        # 断开连接
        await client_manager.disconnect(client_id)
        logger.info(f"Client disconnected: {client_id}")
