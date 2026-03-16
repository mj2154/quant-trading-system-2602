"""
Pytest 配置和 Fixtures

统一管理所有 WebSocket E2E 测试的连接和配置。

协议格式（严格遵循 07-websocket-protocol.md）：
- 请求: {"protocolVersion": "2.0", "type": "GET_KLINES", "requestId": "...", "timestamp": ..., "data": {...}}
- ACK: {"protocolVersion": "2.0", "type": "ACK", "requestId": "...", "timestamp": ..., "data": {}}
- SUCCESS: {"protocolVersion": "2.0", "type": "KLINES_DATA", "requestId": "...", "timestamp": ..., "data": {...}}
- UPDATE: {"protocolVersion": "2.0", "type": "UPDATE", "timestamp": ..., "data": {"subscriptionKey": "...", "content": {...}}}
"""

import asyncio
import json
import uuid
from typing import Any

import pytest
import websockets


# ============================================================
# 配置
# ============================================================

def pytest_configure(config):
    """注册自定义标记"""
    config.addinivalue_line("markers", "spot: 现货产品测试")
    config.addinivalue_line("markers", "futures: 期货产品测试")
    config.addinivalue_line("markers", "rest: REST API 测试")
    config.addinivalue_line("markers", "ws: WebSocket 订阅测试")
    config.addinivalue_line("markers", "slow: 慢速测试")


# ============================================================
# 测试客户端
# ============================================================

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
        """生成 UUID 格式的 requestId"""
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
        发送消息并等待响应

        三阶段模式：请求 -> ACK -> SUCCESS
        同步模式：请求 -> SUCCESS（直接返回数据）
        """
        import time as time_module

        if not self.connected or not self.websocket:
            raise ConnectionError("WebSocket 未连接")

        # 自动添加必要字段
        if "requestId" not in message:
            message["requestId"] = self._generate_request_id()
        if "timestamp" not in message:
            message["timestamp"] = int(time_module.time() * 1000)
        if "protocolVersion" not in message:
            message["protocolVersion"] = "2.0"

        await self._send_message(message)

        # 第一阶段：接收响应
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

        return first_response

    # ========== REST API 方法 ==========

    async def get_config(self) -> dict[str, Any]:
        """获取交易所配置"""
        return await self._send_and_wait_response({"type": "GET_CONFIG", "data": {}})

    async def get_server_time(self) -> dict[str, Any]:
        """获取服务器时间"""
        return await self._send_and_wait_response({"type": "GET_SERVER_TIME", "data": {}})

    async def search_symbols(self, query: str, exchange: str = "BINANCE") -> dict[str, Any]:
        """搜索交易对"""
        return await self._send_and_wait_response({
            "type": "GET_SEARCH_SYMBOLS",
            "data": {"query": query, "exchange": exchange},
        })

    async def resolve_symbol(self, symbol: str) -> dict[str, Any]:
        """解析交易对"""
        return await self._send_and_wait_response({
            "type": "GET_RESOLVE_SYMBOL",
            "data": {"symbol": symbol},
        })

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        from_time: int,
        to_time: int,
    ) -> dict[str, Any]:
        """获取K线数据"""
        return await self._send_and_wait_response({
            "type": "GET_KLINES",
            "data": {
                "symbol": symbol,
                "interval": interval,
                "fromTime": from_time,
                "toTime": to_time,
            },
        })

    async def get_quotes(self, symbols: list[str]) -> dict[str, Any]:
        """获取报价数据"""
        return await self._send_and_wait_response({
            "type": "GET_QUOTES",
            "data": {"symbols": symbols},
        })

    # ========== 订阅方法 ==========

    async def subscribe(self, subscriptions: list[str]) -> dict[str, Any]:
        """订阅数据"""
        return await self._send_and_wait_response({
            "type": "SUBSCRIBE",
            "data": {"subscriptions": subscriptions},
        })

    async def unsubscribe(self, subscriptions: list[str] | None = None) -> dict[str, Any]:
        """取消订阅"""
        data: dict[str, Any] = {}
        if subscriptions:
            data["subscriptions"] = subscriptions
        else:
            data["all"] = True
        return await self._send_and_wait_response({"type": "UNSUBSCRIBE", "data": data})

    async def get_subscriptions(self) -> dict[str, Any]:
        """查询当前订阅"""
        return await self._send_and_wait_response({"type": "GET_SUBSCRIPTIONS", "data": {}})

    # ========== 账户查询方法 ==========

    async def get_futures_account(self) -> dict[str, Any]:
        """获取期货账户信息"""
        return await self._send_and_wait_response({"type": "GET_FUTURES_ACCOUNT", "data": {}})

    async def get_spot_account(self) -> dict[str, Any]:
        """获取现货账户信息"""
        return await self._send_and_wait_response({"type": "GET_SPOT_ACCOUNT", "data": {}})

    # ========== 订单查询方法 ==========

    async def get_open_orders(self, symbol: str | None = None) -> dict[str, Any]:
        """查询当前挂单"""
        data: dict[str, Any] = {}
        if symbol:
            data["symbol"] = symbol
        return await self._send_and_wait_response({"type": "GET_OPEN_ORDERS", "data": data})

    async def list_orders(
        self,
        symbol: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """查询订单列表"""
        data: dict[str, Any] = {"limit": limit}
        if symbol:
            data["symbol"] = symbol
        if start_time:
            data["startTime"] = start_time
        if end_time:
            data["endTime"] = end_time
        return await self._send_and_wait_response({"type": "LIST_ORDERS", "data": data})

    # ========== 策略元数据方法 ==========

    async def get_strategy_metadata(self) -> dict[str, Any]:
        """获取所有策略元数据"""
        return await self._send_and_wait_response({"type": "GET_STRATEGY_METADATA", "data": {}})

    async def get_strategy_metadata_by_type(self, strategy_type: str) -> dict[str, Any]:
        """获取指定策略元数据"""
        return await self._send_and_wait_response({
            "type": "GET_STRATEGY_METADATA_BY_TYPE",
            "data": {"strategyType": strategy_type},
        })

    # ========== 信号查询方法 ==========

    async def list_signals(
        self,
        page: int = 1,
        page_size: int = 20,
        symbol: str | None = None,
        strategy_type: str | None = None,
        from_time: int | None = None,
        to_time: int | None = None,
    ) -> dict[str, Any]:
        """查询历史信号"""
        data: dict[str, Any] = {"page": page, "pageSize": page_size}
        if symbol:
            data["symbol"] = symbol
        if strategy_type:
            data["strategyType"] = strategy_type
        if from_time:
            data["fromTime"] = from_time
        if to_time:
            data["toTime"] = to_time
        return await self._send_and_wait_response({"type": "LIST_SIGNALS", "data": data})

    # ========== 服务指标方法 ==========

    async def get_metrics(self) -> dict[str, Any]:
        """获取服务指标"""
        return await self._send_and_wait_response({"type": "GET_METRICS", "data": {}})

    # ========== 实时数据监听 ==========

    async def listen_updates(
        self, timeout: float = 5.0, expected_count: int = 1
    ) -> list[dict[str, Any]]:
        """
        监听实时数据推送

        返回 UPDATE 类型的消息列表
        """
        import time as time_module

        updates: list[dict[str, Any]] = []
        start_time = time_module.time()

        while time_module.time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                message_dict = json.loads(message)

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

@pytest.fixture(scope="session")
def ws_uri() -> str:
    """WebSocket 连接 URI"""
    return "ws://localhost:8000/ws"


@pytest.fixture
async def ws_client(ws_uri: str) -> WebSocketTestClient:
    """创建独立的 WebSocket 连接"""
    client = WebSocketTestClient(ws_uri)
    yield client
    await client.disconnect()


@pytest.fixture
async def ws_connected_client(ws_client: WebSocketTestClient) -> WebSocketTestClient:
    """创建已连接的 WebSocket 客户端"""
    connected = await ws_client.connect()
    if not connected:
        pytest.fail("无法连接到 WebSocket 服务器")
    yield ws_client
    await ws_client.disconnect()


# ============================================================
# 测试数据参数化
# ============================================================

# 产品类型配置
SPOT_PRODUCT = "spot"
FUTURES_PRODUCT = "futures"

# 测试数据：交易对符号
TEST_SYMBOLS = {
    SPOT_PRODUCT: ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT"],
    FUTURES_PRODUCT: ["BINANCE:BTCUSDT.PERP", "BINANCE:ETHUSDT.PERP"],
}

# 测试数据：K线订阅键
KLINE_SUBSCRIPTION_KEYS = {
    SPOT_PRODUCT: "BINANCE:BTCUSDT@KLINE_1",
    FUTURES_PRODUCT: "BINANCE:BTCUSDT.PERP@KLINE_1",
}

# 测试数据：报价订阅键
QUOTES_SUBSCRIPTION_KEYS = {
    SPOT_PRODUCT: "BINANCE:BTCUSDT@QUOTES",
    FUTURES_PRODUCT: "BINANCE:BTCUSDT.PERP@QUOTES",
}
