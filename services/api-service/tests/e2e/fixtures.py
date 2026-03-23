"""
pytest Fixtures - WebSocket 连接管理

提供可复用的 WebSocket 连接 fixtures，支持：
- 独立连接（每个测试一个连接）
- 已连接客户端
- 自动清理
- 并发控制（避免触发交易所API限流）

协议格式（严格遵循 07-websocket-protocol.md）：
- 请求: {"protocolVersion": "2.0", "type": "SUBSCRIBE", "requestId": "...", "timestamp": ..., "data": {...}}
- ACK: {"protocolVersion": "2.0", "type": "ACK", "requestId": "...", "timestamp": ..., "data": {}}
- SUCCESS: {"protocolVersion": "2.0", "type": "KLINES_DATA", "requestId": "...", "timestamp": ..., "data": {...}}
- UPDATE: {"protocolVersion": "2.0", "type": "UPDATE", "timestamp": ..., "subscriptionKey": "...", "data": {...}}
  注意：UPDATE 推送不包含 requestId
"""

import asyncio
import json
import uuid
from typing import Any

import websockets
import pytest


class WebSocketTestClient:
    """WebSocket 测试客户端（严格遵循协议设计）"""

    def __init__(self, uri: str = "ws://localhost:8000/ws"):
        self.uri = uri
        self.websocket: websockets.WebSocketServerProtocol | None = None
        self.connected = False

    async def connect(self, timeout: float = 10.0) -> bool:
        """建立连接"""
        try:
            self.websocket = await asyncio.wait_for(
                websockets.connect(self.uri, ping_interval=20, ping_timeout=60),
                timeout=timeout,
            )
            self.connected = True
            return True
        except Exception:
            self.connected = False
            return False

    async def disconnect(self) -> None:
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False

    def _generate_request_id(self) -> str:
        """生成 UUID 格式的 requestId（协议要求：32位hex）"""
        return uuid.uuid4().hex

    async def _send_message(self, message: dict[str, Any]) -> None:
        """发送消息"""
        if not self.websocket:
            raise ConnectionError("WebSocket 未连接")

        await self.websocket.send(json.dumps(message, separators=(",", ":")))

    async def _recv_message(self, timeout: float = 10.0) -> dict[str, Any] | None:
        """接收单条消息"""
        try:
            message = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            return json.loads(message)
        except asyncio.TimeoutError:
            return None

    async def _send_and_wait_response(
        self,
        message: dict[str, Any],
        wait_success: bool = True,
    ) -> dict[str, Any]:
        """
        发送消息并等待响应（支持两种模式）

        模式1（三阶段）：请求 -> ACK -> SUCCESS
        模式2（同步）：请求 -> SUCCESS（直接返回数据，无ACK）

        Args:
            message: 请求消息
            wait_success: 是否等待 SUCCESS 响应

        Returns:
            SUCCESS 响应（如果 wait_success=True）或 ACK（如果 False）
        """
        if not self.connected or not self.websocket:
            raise ConnectionError("WebSocket 未连接")

        # 自动添加必要字段
        if "requestId" not in message:
            message["requestId"] = self._generate_request_id()
        if "timestamp" not in message:
            message["timestamp"] = int(asyncio.get_event_loop().time() * 1000)
        if "protocolVersion" not in message:
            message["protocolVersion"] = "2.0"

        # 发送请求
        await self._send_message(message)

        # 第一阶段：接收第一个响应
        first_response = await self._recv_message(timeout=10)
        if not first_response:
            raise RuntimeError("未收到任何响应")

        # 如果是 ACK，继续等待 SUCCESS
        if first_response.get("type") == "ACK":
            if wait_success:
                success = await self._recv_message(timeout=30)
                if not success:
                    raise RuntimeError("未收到 SUCCESS 响应")
                return success
            return first_response

        # 如果直接收到 SUCCESS/ERROR（同步模式），直接返回
        return first_response

    async def subscribe(
        self, subscriptions: list[str]
    ) -> dict[str, Any]:
        """
        发送订阅请求（等待 ACK + SUCCESS）

        三阶段：
        1. 发送 SUBSCRIBE
        2. 接收 ACK
        3. 接收 SUCCESS（SUBSCRIPTION_DATA）
        """
        message = {
            "type": "SUBSCRIBE",
            "data": {"subscriptions": subscriptions},
        }
        return await self._send_and_wait_response(message)

    async def unsubscribe(
        self, subscriptions: list[str] | None = None
    ) -> dict[str, Any]:
        """发送取消订阅请求"""
        data: dict[str, Any] = {}
        if subscriptions:
            data["subscriptions"] = subscriptions
        else:
            data["all"] = True

        message = {"type": "UNSUBSCRIBE", "data": data}
        return await self._send_and_wait_response(message)

    async def get_config(self) -> dict[str, Any]:
        """获取交易所配置"""
        message = {"type": "GET_CONFIG", "data": {}}
        return await self._send_and_wait_response(message)

    async def search_symbols(self, query: str) -> dict[str, Any]:
        """搜索交易对"""
        message = {"type": "SEARCH_SYMBOLS", "data": {"query": query}}
        return await self._send_and_wait_response(message)

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        from_time: int,
        to_time: int,
    ) -> dict[str, Any]:
        """获取K线数据

        注意：API 使用 interval 字段（不是 resolution）
        """
        message = {
            "type": "GET_KLINES",
            "data": {
                "symbol": symbol,
                "interval": interval,
                "fromTime": from_time,
                "toTime": to_time,
            },
        }
        return await self._send_and_wait_response(message)

    async def get_quotes(self, symbols: list[str]) -> dict[str, Any]:
        """获取报价数据"""
        message = {"type": "GET_QUOTES", "data": {"symbols": symbols}}
        return await self._send_and_wait_response(message)

    async def listen_updates(
        self, timeout: float = 5.0, expected_count: int = 1
    ) -> list[dict[str, Any]]:
        """
        监听实时数据推送

        协议要求：
        - UPDATE 消息的 type="UPDATE"
        - UPDATE 消息不包含 requestId
        - UPDATE 消息包含 subscriptionKey 和 data（data 直接作为载荷，无 content 包装）

        Args:
            timeout: 超时时间（秒）
            expected_count: 期望接收的消息数量

        Returns:
            UPDATE 类型的消息列表
        """
        updates: list[dict[str, Any]] = []
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                message_dict = json.loads(message)

                # 只收集 type="UPDATE" 的消息
                if message_dict.get("type") == "UPDATE":
                    updates.append(message_dict)
                    if len(updates) >= expected_count:
                        break

            except asyncio.TimeoutError:
                continue
            except Exception:
                break

        return updates


# ============================================================
# Pytest Fixtures
# ============================================================


@pytest.fixture
async def ws_client(ws_uri: str) -> WebSocketTestClient:
    """
    创建独立的 WebSocket 连接

    每个使用此 fixture 的测试都会获得一个全新的连接。
    测试结束后自动断开。
    """
    client = WebSocketTestClient(ws_uri)
    yield client
    await client.disconnect()


@pytest.fixture
async def ws_connected_client(ws_client: WebSocketTestClient) -> WebSocketTestClient:
    """
    创建已连接的 WebSocket 客户端

    相当于 ws_client + auto-connect。
    """
    connected = await ws_client.connect()
    if not connected:
        pytest.fail("无法连接到 WebSocket 服务器")

    yield ws_client
    await ws_client.disconnect()
