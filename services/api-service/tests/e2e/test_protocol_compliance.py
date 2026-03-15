"""
WebSocket API 协议合规性测试

严格遵循设计文档: docs/backend/design/07-websocket-protocol.md

测试目标：
1. 验证所有 GET 请求使用正确的 "type" 字段
2. 验证 SUBSCRIBE/UNSUBSCRIBE 使用正确的 "type" 字段
3. 验证响应数据格式符合设计规范
4. 使用 Pydantic 模型验证响应数据

协议规范要求：
- 客户端请求使用 "type" 字段，不使用 "action" 字段
- GET 请求格式: {"type": "GET_CONFIG", "data": {...}}
- SUBSCRIBE 格式: {"type": "SUBSCRIBE", "data": {"subscriptions": [...]}}

作者: Claude Code
版本: v1.0.0
"""

import sys
from pathlib import Path

# 添加路径
_api_service_root = Path(__file__).resolve().parent.parent.parent
_src_path = _api_service_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import asyncio
import json
import logging
import time
import uuid
from typing import Any

import websockets

# 导入项目模型用于验证
from models import (
    ConfigData,
    SearchSymbolsData,
    ServerTimeData,
    SubscribeData,
    SubscriptionsData,
)
from pydantic import ValidationError

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProtocolCompliantClient:
    """严格遵循协议规范的 WebSocket 测试客户端

    设计文档规定的请求格式:
    - GET 请求: {"type": "GET_CONFIG", "requestId": "...", "timestamp": ..., "data": {...}}
    - SUBSCRIBE: {"type": "SUBSCRIBE", "requestId": "...", "timestamp": ..., "data": {...}}
    - UNSUBSCRIBE: {"type": "UNSUBSCRIBE", "requestId": "...", "timestamp": ..., "data": {...}}
    """

    def __init__(self, uri: str = "ws://localhost:8000/ws"):
        self.uri = uri
        self.websocket: websockets.WebSocketServerProtocol | None = None
        self.connected = False
        self.request_id_counter = 0

    async def connect(self) -> bool:
        """建立 WebSocket 连接"""
        try:
            logger.info(f"正在连接到 {self.uri}...")
            self.websocket = await websockets.connect(self.uri, ping_interval=20, ping_timeout=60)
            self.connected = True
            logger.info("WebSocket 连接成功")
            return True
        except Exception as e:
            logger.error(f"WebSocket 连接失败: {e!s}")
            return False

    async def disconnect(self):
        """断开 WebSocket 连接"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("WebSocket 连接已断开")

    def _generate_request_id(self) -> str:
        """生成唯一请求 ID (UUID v4 hex 格式)"""
        self.request_id_counter += 1
        return uuid.uuid4().hex

    async def _send_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """发送消息并接收响应（三阶段模式）

        三阶段模式（遵循设计文档）:
        1. 发送请求（携带 requestId）
        2. 接收 ACK 确认（action: "ack"）
        3. 接收最终响应（action: "success"，type 在 data 内部）
        """
        if not self.connected or not self.websocket:
            raise ConnectionError("WebSocket 未连接")

        # 确保必要字段
        if "requestId" not in message:
            message["requestId"] = self._generate_request_id()
        if "timestamp" not in message:
            message["timestamp"] = int(time.time() * 1000)
        if "protocolVersion" not in message:
            message["protocolVersion"] = "2.0"

        request_id = message["requestId"]
        msg_type = message.get("type", "UNKNOWN")

        logger.info(f"发送消息: type={msg_type}, requestId={request_id}")
        message_str = json.dumps(message, separators=(",", ":"))
        await self.websocket.send(message_str)

        # 第一阶段: 等待 ACK
        try:
            ack_response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            ack_data = json.loads(ack_response)
            logger.info(f"收到 ACK 原始响应: {ack_data}")
            # 设计文档规定: ACK 响应的 type 是 "ACK"
            ack_type = ack_data.get("type")
            logger.info(f"收到 ACK: type={ack_type}")

            # 第二阶段: 等待 SUCCESS
            success_response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            success_data = json.loads(success_response)
            logger.info(f"收到 SUCCESS 原始响应: {success_data}")
            logger.info(f"收到 SUCCESS: type={success_data.get('type')}")

            return success_data

        except asyncio.TimeoutError:
            logger.error("响应超时")
            return None

    # ========== GET 请求方法 ==========

    async def get_config(self) -> dict[str, Any] | None:
        """获取配置 (GET_CONFIG)

        设计文档: 07-websocket-protocol.md 1.1 获取数据源配置
        请求格式: {"type": "GET_CONFIG", ...}
        响应格式: {"type": "CONFIG_DATA", "data": {...}}
        """
        message = {
            "protocolVersion": "2.0",
            "type": "GET_CONFIG",
            "data": {},
        }
        return await self._send_message(message)

    async def get_search_symbols(
        self, query: str = "", exchange: str = "BINANCE", limit: int = 50
    ) -> dict[str, Any] | None:
        """搜索交易对 (GET_SEARCH_SYMBOLS)

        设计文档: 07-websocket-protocol.md 1.2 搜索交易对
        请求格式: {"type": "GET_SEARCH_SYMBOLS", "data": {"query": "...", "exchange": "..."}}
        响应格式: {"type": "SEARCH_SYMBOLS_DATA", "data": {"symbols": [...], "total": N}}
        """
        message = {
            "protocolVersion": "2.0",
            "type": "GET_SEARCH_SYMBOLS",
            "data": {
                "query": query,
                "exchange": exchange,
                "limit": limit,
            },
        }
        return await self._send_message(message)

    async def get_resolve_symbol(self, symbol: str) -> dict[str, Any] | None:
        """解析交易对 (GET_RESOLVE_SYMBOL)

        设计文档: 07-websocket-protocol.md 1.3 解析交易对
        请求格式: {"type": "GET_RESOLVE_SYMBOL", "data": {"symbol": "..."}}
        响应格式: {"type": "SYMBOL_DATA", "data": {...}}
        """
        message = {
            "protocolVersion": "2.0",
            "type": "GET_RESOLVE_SYMBOL",
            "data": {"symbol": symbol},
        }
        return await self._send_message(message)

    async def get_klines(
        self, symbol: str, interval: str, from_time: int, to_time: int
    ) -> dict[str, Any] | None:
        """获取 K 线数据 (GET_KLINES)

        设计文档: 07-websocket-protocol.md 1.4 获取K线数据
        请求格式: {"type": "GET_KLINES", "data": {"symbol": "...", "interval": "...", ...}}
        响应格式: {"type": "KLINES_DATA", "data": {"symbol": "...", "bars": [...]}}
        """
        message = {
            "protocolVersion": "2.0",
            "type": "GET_KLINES",
            "data": {
                "symbol": symbol,
                "interval": interval,
                "from_time": from_time,
                "to_time": to_time,
            },
        }
        return await self._send_message(message)

    async def get_server_time(self) -> dict[str, Any] | None:
        """获取服务器时间 (GET_SERVER_TIME)

        设计文档: 07-websocket-protocol.md
        请求格式: {"type": "GET_SERVER_TIME", "data": {}}
        响应格式: {"type": "SERVER_TIME_DATA", "data": {"server_time": N}}
        """
        message = {
            "protocolVersion": "2.0",
            "type": "GET_SERVER_TIME",
            "data": {},
        }
        return await self._send_message(message)

    async def get_subscriptions(self) -> dict[str, Any] | None:
        """查询订阅 (GET_SUBSCRIPTIONS)

        设计文档: 07-websocket-protocol.md 1.6 查询订阅
        请求格式: {"type": "GET_SUBSCRIPTIONS", "data": {}}
        响应格式: {"type": "SUBSCRIPTION_DATA", "data": {"subscriptions": [...]}}
        """
        message = {
            "protocolVersion": "2.0",
            "type": "GET_SUBSCRIPTIONS",
            "data": {},
        }
        return await self._send_message(message)

    # ========== 订阅方法 ==========

    async def subscribe(self, subscriptions: list[str]) -> dict[str, Any] | None:
        """订阅数据 (SUBSCRIBE)

        设计文档: 07-websocket-protocol.md 2.1 订阅数据
        请求格式: {"type": "SUBSCRIBE", "data": {"subscriptions": [...]}}
        响应格式: {"type": "SUBSCRIPTION_DATA", "data": {"status": "success", "subscriptions": [...]}}
        """
        message = {
            "protocolVersion": "2.0",
            "type": "SUBSCRIBE",
            "data": {"subscriptions": subscriptions},
        }
        return await self._send_message(message)

    async def unsubscribe(self, subscriptions: list[str] | None = None) -> dict[str, Any] | None:
        """取消订阅 (UNSUBSCRIBE)

        设计文档: 07-websocket-protocol.md 2.2 取消订阅
        请求格式: {"type": "UNSUBSCRIBE", "data": {"subscriptions": [...]}}
        响应格式: {"type": "SUBSCRIPTION_DATA", "data": {"status": "success"}}
        """
        message = {
            "protocolVersion": "2.0",
            "type": "UNSUBSCRIBE",
            "data": {"subscriptions": subscriptions or []},
        }
        return await self._send_message(message)

    # ========== 实时数据监听 ==========

    async def listen_updates(self, timeout: float = 5.0) -> list[dict[str, Any]]:
        """监听实时数据推送

        设计文档: 07-websocket-protocol.md 3. 实时数据推送
        推送格式: {"action": "update", "data": {"subscriptionKey": "...", "content": {...}}}
        """
        updates = []
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                message_dict = json.loads(message)

                if message_dict.get("action") == "update":
                    updates.append(message_dict)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"监听错误: {e!s}")
                break

        return updates


class ResponseValidator:
    """响应数据验证器 - 使用 Pydantic 模型验证响应格式"""

    @staticmethod
    def validate_config_response(response: dict[str, Any]) -> tuple[bool, str]:
        """验证 GET_CONFIG 响应格式

        设计文档: 07-websocket-protocol.md 1.1.1 CONFIG_DATA 数据模型定义
        期望字段:
        - type: "CONFIG_DATA"
        - data: ConfigData 模型
        """
        if not response:
            return False, "响应为空"

        # 验证顶层字段
        if response.get("protocolVersion") != "2.0":
            return False, f"protocolVersion 应为 '2.0'，实际为 '{response.get('protocolVersion')}'"

        # 验证响应类型（设计文档规定 type 在顶层）
        if response.get("type") != "CONFIG_DATA":
            return False, f"type 应为 'CONFIG_DATA'，实际为 '{response.get('type')}'"

        # 验证 data 字段存在且不为空
        data = response.get("data")
        if not data:
            return False, "data 字段为空，设计文档规定应包含 supports_search, supported_resolutions 等字段"

        if data == {}:
            return False, "data 字段是空对象 {}，设计文档规定应包含实际配置数据"

        # 使用 Pydantic 模型验证数据格式
        try:
            ConfigData.model_validate(data)
            return True, "验证通过"
        except ValidationError as e:
            return False, f"数据模型验证失败: {e}"

    @staticmethod
    def validate_search_symbols_response(response: dict[str, Any]) -> tuple[bool, str]:
        """验证 GET_SEARCH_SYMBOLS 响应格式

        设计文档: 07-websocket-protocol.md 1.2.1 搜索结果数据模型定义
        """
        if not response:
            return False, "响应为空"

        if response.get("type") != "SEARCH_SYMBOLS_DATA":
            return False, f"type 应为 'SEARCH_SYMBOLS_DATA'，实际为 '{response.get('type')}'"

        data = response.get("data")
        if not data:
            return False, "缺少 data 字段"

        # 验证必要字段
        required_fields = ["symbols", "total", "count"]
        for field in required_fields:
            if field not in data:
                return False, f"缺少必要字段: {field}"

        # 使用 Pydantic 模型验证
        try:
            SearchSymbolsData.model_validate(data)
            return True, "验证通过"
        except ValidationError as e:
            return False, f"数据模型验证失败: {e}"

    @staticmethod
    def validate_server_time_response(response: dict[str, Any]) -> tuple[bool, str]:
        """验证 GET_SERVER_TIME 响应格式

        设计文档: 07-websocket-protocol.md
        """
        if not response:
            return False, "响应为空"

        if response.get("type") != "SERVER_TIME_DATA":
            return False, f"type 应为 'SERVER_TIME_DATA'，实际为 '{response.get('type')}'"

        data = response.get("data", {})
        if "server_time" not in data:
            return False, "缺少 server_time 字段"

        # 验证是数值类型
        server_time = data.get("server_time")
        if not isinstance(server_time, int):
            return False, f"server_time 应为整数类型，实际为 {type(server_time)}"

        return True, "验证通过"

    @staticmethod
    def validate_subscribe_response(response: dict[str, Any]) -> tuple[bool, str]:
        """验证 SUBSCRIBE 响应格式

        设计文档: 07-websocket-protocol.md 2.1 订阅响应
        """
        if not response:
            return False, "响应为空"

        # 设计文档规定成功响应的 type 是 SUBSCRIPTION_DATA
        if response.get("type") != "SUBSCRIPTION_DATA":
            return False, f"type 应为 'SUBSCRIPTION_DATA'，实际为 '{response.get('type')}'"

        data = response.get("data")
        if not data:
            return False, "缺少 data 字段"

        # 验证必要字段
        if "status" not in data:
            return False, "缺少 status 字段"

        if "subscriptions" not in data:
            return False, "缺少 subscriptions 字段"

        # 使用 Pydantic 模型验证
        try:
            SubscribeData.model_validate(data)
            return True, "验证通过"
        except ValidationError as e:
            return False, f"数据模型验证失败: {e}"

    @staticmethod
    def validate_klines_response(response: dict[str, Any]) -> tuple[bool, str]:
        """验证 GET_KLINES 响应格式

        设计文档: 07-websocket-protocol.md 1.4.1 K线数据模型定义
        """
        if not response:
            return False, "响应为空"

        # 设计文档规定 type 为 KLINES_DATA
        if response.get("type") != "KLINES_DATA":
            return False, f"type 应为 'KLINES_DATA'，实际为 '{response.get('type')}'"

        data = response.get("data")
        if not data:
            return False, "缺少 data 字段"

        # 验证必要字段
        required_fields = ["symbol", "interval", "bars"]
        for field in required_fields:
            if field not in data:
                return False, f"缺少必要字段: {field}"

        # 验证 bars 是数组
        bars = data.get("bars")
        if not isinstance(bars, list):
            return False, f"bars 应为数组类型，实际为 {type(bars)}"

        return True, "验证通过"

    @staticmethod
    def validate_subscriptions_response(response: dict[str, Any]) -> tuple[bool, str]:
        """验证 GET_SUBSCRIPTIONS 响应格式

        设计文档: 07-websocket-protocol.md 1.6.1 SUBSCRIPTION_DATA 数据模型定义
        """
        if not response:
            return False, "响应为空"

        if response.get("type") != "SUBSCRIPTION_DATA":
            return False, f"type 应为 'SUBSCRIPTION_DATA'，实际为 '{response.get('type')}'"

        data = response.get("data")
        if not data:
            return False, "缺少 data 字段"

        # 使用 Pydantic 模型验证
        try:
            SubscriptionsData.model_validate(data)
            return True, "验证通过"
        except ValidationError as e:
            return False, f"数据模型验证失败: {e}"


class ProtocolComplianceTest:
    """协议合规性测试套件"""

    def __init__(self):
        self.client: ProtocolCompliantClient | None = None
        self.validator = ResponseValidator()
        self.test_results: dict[str, Any] = {"passed": 0, "failed": 0, "errors": []}

    async def setup(self):
        """测试设置"""
        self.client = ProtocolCompliantClient()
        connected = await self.client.connect()
        if not connected:
            raise ConnectionError("无法连接到 WebSocket 服务器")

    async def teardown(self):
        """测试清理"""
        if self.client:
            await self.client.disconnect()

    async def __aenter__(self):
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.teardown()

    def _record_result(self, test_name: str, passed: bool, message: str = ""):
        """记录测试结果"""
        if passed:
            self.test_results["passed"] += 1
            logger.info(f"[PASS] {test_name}")
        else:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {message}")
            logger.error(f"[FAIL] {test_name}: {message}")

    # ========== 测试用例 ==========

    async def test_get_config(self):
        """测试 GET_CONFIG 请求"""
        logger.info("=" * 60)
        logger.info("测试: GET_CONFIG (获取配置)")
        logger.info("=" * 60)

        response = await self.client.get_config()
        if not response:
            self._record_result("GET_CONFIG", False, "无响应")
            return

        # 验证协议格式
        is_valid, msg = self.validator.validate_config_response(response)
        self._record_result("GET_CONFIG 响应格式", is_valid, msg)

        if is_valid:
            data = response.get("data", {})
            logger.info(f"  支持的分辨率: {data.get('supported_resolutions')}")
            logger.info(f"  货币代码: {data.get('currency_codes')}")

    async def test_get_search_symbols(self):
        """测试 GET_SEARCH_SYMBOLS 请求"""
        logger.info("=" * 60)
        logger.info("测试: GET_SEARCH_SYMBOLS (搜索交易对)")
        logger.info("=" * 60)

        response = await self.client.get_search_symbols(query="BTC", limit=10)
        if not response:
            self._record_result("GET_SEARCH_SYMBOLS", False, "无响应")
            return

        is_valid, msg = self.validator.validate_search_symbols_response(response)
        self._record_result("GET_SEARCH_SYMBOLS 响应格式", is_valid, msg)

        if is_valid:
            data = response.get("data", {})
            symbols = data.get("symbols", [])
            logger.info(f"  搜索到 {len(symbols)} 个交易对")
            for sym in symbols[:3]:
                logger.info(f"    - {sym.get('symbol')}: {sym.get('description')}")

    async def test_get_resolve_symbol(self):
        """测试 GET_RESOLVE_SYMBOL 请求"""
        logger.info("=" * 60)
        logger.info("测试: GET_RESOLVE_SYMBOL (解析交易对)")
        logger.info("=" * 60)

        response = await self.client.get_resolve_symbol(symbol="BINANCE:BTCUSDT")
        if not response:
            self._record_result("GET_RESOLVE_SYMBOL", False, "无响应")
            return

        # 验证响应类型
        expected_type = "SYMBOL_DATA"
        actual_type = response.get("type")
        is_valid = actual_type == expected_type
        self._record_result(
            "GET_RESOLVE_SYMBOL 响应类型",
            is_valid,
            f"期望 {expected_type}，实际 {actual_type}" if not is_valid else ""
        )

        if is_valid:
            data = response.get("data", {})
            logger.info(f"  解析结果: {data}")

    async def test_get_server_time(self):
        """测试 GET_SERVER_TIME 请求"""
        logger.info("=" * 60)
        logger.info("测试: GET_SERVER_TIME (获取服务器时间)")
        logger.info("=" * 60)

        response = await self.client.get_server_time()
        if not response:
            self._record_result("GET_SERVER_TIME", False, "无响应")
            return

        is_valid, msg = self.validator.validate_server_time_response(response)
        self._record_result("GET_SERVER_TIME 响应格式", is_valid, msg)

        if is_valid:
            data = response.get("data", {})
            logger.info(f"  服务器时间: {data.get('server_time')}")

    async def test_get_klines(self):
        """测试 GET_KLINES 请求"""
        logger.info("=" * 60)
        logger.info("测试: GET_KLINES (获取K线数据)")
        logger.info("=" * 60)

        # 获取最近1小时的K线数据
        now = int(time.time() * 1000)
        from_time = now - 3600 * 1000  # 1小时前
        to_time = now

        response = await self.client.get_klines(
            symbol="BINANCE:BTCUSDT",
            interval="1",
            from_time=from_time,
            to_time=to_time,
        )
        if not response:
            self._record_result("GET_KLINES", False, "无响应")
            return

        is_valid, msg = self.validator.validate_klines_response(response)
        self._record_result("GET_KLINES 响应格式", is_valid, msg)

        if is_valid:
            data = response.get("data", {})
            bars = data.get("bars", [])
            logger.info(f"  获取到 {len(bars)} 根K线")
            if bars:
                first_bar = bars[0]
                logger.info(f"  第一根K线: time={first_bar.get('time')}, open={first_bar.get('open')}")

    async def test_subscribe_unsubscribe(self):
        """测试 SUBSCRIBE/UNSUBSCRIBE 请求"""
        logger.info("=" * 60)
        logger.info("测试: SUBSCRIBE / UNSUBSCRIBE")
        logger.info("=" * 60)

        subscriptions = ["BINANCE:BTCUSDT@KLINE_1"]

        # 测试订阅
        sub_response = await self.client.subscribe(subscriptions)
        if not sub_response:
            self._record_result("SUBSCRIBE", False, "无响应")
        else:
            is_valid, msg = self.validator.validate_subscribe_response(sub_response)
            self._record_result("SUBSCRIBE 响应格式", is_valid, msg)

            if is_valid:
                data = sub_response.get("data", {})
                logger.info(f"  订阅状态: {data.get('status')}")
                logger.info(f"  订阅的键: {data.get('subscriptions')}")

        # 监听实时数据
        if sub_response and sub_response.get("action") == "success":
            logger.info("  监听实时数据...")
            updates = await self.client.listen_updates(timeout=3)
            if updates:
                logger.info(f"  接收到 {len(updates)} 条实时数据")
            else:
                logger.info("  未接收到实时数据（可能正常）")

        # 测试取消订阅
        unsub_response = await self.client.unsubscribe(subscriptions)
        if not unsub_response:
            self._record_result("UNSUBSCRIBE", False, "无响应")
        else:
            data = unsub_response.get("data", {})
            is_valid = data.get("status") == "success"
            self._record_result("UNSUBSCRIBE 响应", is_valid, "取消订阅失败" if not is_valid else "")

    async def test_get_subscriptions(self):
        """测试 GET_SUBSCRIPTIONS 请求"""
        logger.info("=" * 60)
        logger.info("测试: GET_SUBSCRIPTIONS (查询订阅)")
        logger.info("=" * 60)

        response = await self.client.get_subscriptions()
        if not response:
            self._record_result("GET_SUBSCRIPTIONS", False, "无响应")
            return

        is_valid, msg = self.validator.validate_subscriptions_response(response)
        self._record_result("GET_SUBSCRIPTIONS 响应格式", is_valid, msg)

        if is_valid:
            data = response.get("data", {})
            subs = data.get("subscriptions", [])
            logger.info(f"  当前订阅数: {len(subs)}")

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("=" * 60)
        logger.info("WebSocket API 协议合规性测试")
        logger.info("=" * 60)

        tests = [
            self.test_get_config,
            self.test_get_search_symbols,
            self.test_get_resolve_symbol,
            self.test_get_server_time,
            self.test_get_klines,
            self.test_subscribe_unsubscribe,
            self.test_get_subscriptions,
        ]

        for test in tests:
            try:
                await test()
            except Exception as e:
                logger.error(f"测试异常: {test.__name__}: {e!s}")
                self._record_result(test.__name__, False, str(e))

        # 打印测试结果
        logger.info("=" * 60)
        logger.info("测试结果汇总")
        logger.info("=" * 60)
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]
        total = passed + failed

        if failed == 0:
            logger.info(f"[全部通过] {passed}/{total}")
        else:
            logger.info(f"[部分失败] 通过: {passed}, 失败: {failed}")
            for error in self.test_results["errors"]:
                logger.error(f"  - {error}")

        return self.test_results


async def main():
    """主函数"""
    test = ProtocolComplianceTest()

    try:
        async with test:
            results = await test.run_all_tests()
            return 0 if results["failed"] == 0 else 1
    except Exception as e:
        logger.error(f"测试执行失败: {e!s}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
