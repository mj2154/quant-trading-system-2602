"""
简化版端到端测试基类

提供快速、轻量级的WebSocket测试功能。
特点：
- 最小化打印信息
- 快速验证（5-10秒）
- 简化的测试流程
- 连接复用：所有测试共享一个WebSocket连接

连接复用说明：
- 整个测试套件只创建一个WebSocket连接
- 所有测试方法共享这个连接
- 取消订阅不会导致连接断开
- 只有在所有测试完成后才关闭连接

作者: Claude Code
版本: v1.1.0
"""

import asyncio
import json
import logging
import time
from typing import Any

# 配置最小化日志
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class SimpleTestClient:
    """简化的WebSocket测试客户端"""

    def __init__(self, uri: str = "ws://localhost:8000/ws/market"):
        self.uri = uri
        self.websocket: Any | None = None
        self.connected = False

    async def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            import websockets

            self.websocket = await websockets.connect(self.uri, ping_interval=10, ping_timeout=30)
            self.connected = True
            return True
        except Exception:
            return False

    async def disconnect(self):
        """断开WebSocket连接"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False

    async def _send_message(self, message: dict[str, Any]) -> None:
        """发送消息（不接收响应）"""
        if not self.connected or not self.websocket:
            return

        # 自动生成requestId
        if "requestId" not in message:
            message["requestId"] = f"test_{int(time.time() * 1000)}"

        if "timestamp" not in message:
            message["timestamp"] = int(time.time() * 1000)

        message_str = json.dumps(message, separators=(",", ":"))
        await self.websocket.send(message_str)

    async def _recv_response(self, timeout: float = 5.0) -> dict[str, Any] | None:
        """接收响应"""
        try:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            return json.loads(response)
        except TimeoutError:
            return None

    async def _send_and_recv(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """发送消息并接收响应（最小化打印）

        注意：此方法只接收单个响应，不适用于三阶段模式。
        三阶段模式请使用 subscribe/unsubscribe 方法。
        """
        if not self.connected or not self.websocket:
            return None

        # 自动生成requestId
        if "requestId" not in message:
            message["requestId"] = f"test_{int(time.time() * 1000)}"

        if "timestamp" not in message:
            message["timestamp"] = int(time.time() * 1000)  # 毫秒级时间戳

        # 发送消息
        message_str = json.dumps(message, separators=(",", ":"))
        await self.websocket.send(message_str)

        # 接收响应（5秒超时）
        try:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=5)
            return json.loads(response)
        except TimeoutError:
            return None

    async def subscribe(
        self, subscriptions: list[str] | dict[str, Any]
    ) -> dict[str, Any] | None:
        """发送订阅消息 - 支持v2.0列表格式和v1.0字典格式

        三阶段模式（遵循设计文档）：
        1. 发送 subscribe 请求
        2. 接收 ack 确认（确认收到请求）
        3. 接收 success 响应（确认处理完成）
        4. 实时数据通过 update 推送（独立机制）

        Args:
            subscriptions: v2.0格式列表 ["BINANCE:BTCUSDT@KLINE_1"]
                          或v1.0格式字典 {"kline": [{"symbol": "...", "resolution": "1"}]}
        """
        # 将输入转换为v2.0订阅键列表
        if isinstance(subscriptions, list):
            # 直接使用v2.0格式
            subscription_keys = subscriptions
        else:
            # v1.0格式，转换为v2.0
            subscription_keys = self._convert_subscriptions_to_keys(subscriptions)

        message = {
            "protocolVersion": "2.0",
            "action": "subscribe",
            "data": {"subscriptions": subscription_keys},
        }

        # 发送消息
        await self._send_message(message)

        # 接收 ack 确认
        ack_response = await self._recv_response(timeout=5)
        if not ack_response or ack_response.get("action") != "ack":
            return ack_response  # 返回错误响应或None

        # 接收 success 响应
        success_response = await self._recv_response(timeout=5)
        return success_response

    async def unsubscribe(
        self, subscriptions: list[str] | dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """取消订阅 - 支持v2.0列表格式和v1.0字典格式

        三阶段模式（遵循设计文档）：
        1. 发送 unsubscribe 请求
        2. 接收 ack 确认（确认收到请求）
        3. 接收 success 响应（确认处理完成）

        Args:
            subscriptions: v2.0格式列表 ["BINANCE:BTCUSDT@KLINE_1"]
                         或v1.0格式字典 {"kline": [{"symbol": "..."}]}
                         None表示取消所有订阅
        """
        message = {"protocolVersion": "2.0", "action": "unsubscribe", "data": {}}

        if subscriptions is None:
            # 取消所有订阅
            message["data"]["all"] = True
        elif isinstance(subscriptions, list):
            # v2.0格式直接使用
            message["data"]["subscriptions"] = subscriptions
        else:
            # v1.0格式，转换为v2.0
            subscription_keys = self._convert_subscriptions_to_keys(subscriptions)
            message["data"]["subscriptions"] = subscription_keys

        # 发送消息
        await self._send_message(message)

        # 接收 ack 确认
        ack_response = await self._recv_response(timeout=5)
        if not ack_response or ack_response.get("action") != "ack":
            return ack_response

        # 接收 success 响应
        success_response = await self._recv_response(timeout=5)
        return success_response

    def _convert_subscriptions_to_keys(self, subscriptions_data: dict[str, Any]) -> list[str]:
        """将对象格式转换为v2.0订阅键格式

        Args:
            subscriptions_data: 对象格式，如:
                {
                    "quotes": [{"symbol": "BINANCE:BTCUSDT"}],
                    "kline": [{"symbol": "BINANCE:BTCUSDT", "resolution": "1"}]
                }

        Returns:
            v2.0订阅键列表，如:
                ["BINANCE:BTCUSDT@QUOTES", "BINANCE:BTCUSDT@KLINE_1"]
        """
        subscription_keys = []

        # 数据类型映射（前端使用的类型 -> 标准数据类型）
        # 注意：根据API规范，quotes 映射到 QUOTES（不是 TICKER）
        type_mapping = {"quotes": "QUOTES", "kline": "KLINE", "trade": "TRADE"}

        for sub_type, subs_list in subscriptions_data.items():
            # 转换为标准数据类型
            standard_type = type_mapping.get(sub_type, sub_type.upper())

            if not isinstance(subs_list, list):
                continue

            for sub_item in subs_list:
                if not isinstance(sub_item, dict):
                    continue

                symbol = sub_item.get("symbol", "").strip()
                if not symbol:
                    continue

                # 构建订阅键
                if standard_type == "KLINE":
                    resolution = sub_item.get("resolution", "1")
                    subscription_keys.append(f"{symbol}@{standard_type}_{resolution}")
                else:
                    subscription_keys.append(f"{symbol}@{standard_type}")

        return subscription_keys

    async def listen_updates(self, timeout: float = 5.0) -> list[dict[str, Any]]:
        """监听实时数据推送（快速版本）"""
        updates = []
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                message_dict = json.loads(message)

                if message_dict.get("action") == "update":
                    updates.append(message_dict)

            except TimeoutError:
                continue
            except Exception:
                break

        return updates


class SimpleE2ETestBase:
    """简化版端到端测试基类"""

    def __init__(self):
        self.client: SimpleTestClient | None = None
        self.test_results: dict[str, Any] = {"passed": 0, "failed": 0, "errors": []}
        self._initialized = False

    async def setup(self):
        """测试设置（仅初始化一次）"""
        if not self._initialized:
            self.client = SimpleTestClient()
            connected = await self.client.connect()
            if not connected:
                raise ConnectionError("无法连接到WebSocket服务器")
            self._initialized = True

    async def teardown(self):
        """测试清理（仅在所有测试完成后调用）"""
        if self.client:
            await self.client.disconnect()
            self._initialized = False

    async def __aenter__(self):
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.teardown()

    def assert_success(
        self,
        response: dict[str, Any] | None,
        test_name: str,
        expected_request_id: str | None = None,
    ) -> bool:
        """验证响应是否符合 v2.0 协议规范

        Args:
            response: 响应消息字典
            test_name: 测试名称（用于错误报告）
            expected_request_id: 期望的请求ID（可选，用于验证请求-响应对应关系）
        """
        if not response:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: 无响应")
            return False

        # 验证 protocolVersion（架构要求 v2.0）
        if response.get("protocolVersion") != "2.0":
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: protocolVersion 必须是 '2.0'，实际为 '{response.get('protocolVersion')}'"
            )
            return False

        # 验证 action
        if response.get("action") == "error":
            self.test_results["failed"] += 1
            # 打印完整的错误信息 - 修复字段名
            error_data = response.get("data", {})
            error_msg = error_data.get("errorMessage", "未知错误")
            error_code = error_data.get("errorCode", "UNKNOWN")
            full_error = f"{test_name}: [{error_code}] {error_msg}"
            self.test_results["errors"].append(full_error)
            print(f"  详细错误: {full_error}")
            return False

        # 验证 timestamp 存在且有效（架构要求）
        if "timestamp" not in response:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: 缺少 timestamp 字段")
            return False

        timestamp = response.get("timestamp")
        if not isinstance(timestamp, (int, float)):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: timestamp 必须是数值类型")
            return False

        # 可选：验证 requestId 与请求对应
        if expected_request_id is not None:
            response_request_id = response.get("requestId")
            if response_request_id != expected_request_id:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name}: requestId 不匹配，期望 '{expected_request_id}'，实际为 '{response_request_id}'"
                )
                return False

        self.test_results["passed"] += 1
        return True

    def assert_data_received(self, updates: list[dict[str, Any]], test_name: str) -> bool:
        """快速验证是否接收到数据"""
        if not updates:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: 未接收到数据")
            return False

        self.test_results["passed"] += 1
        return True

    def assert_quotes_payload_format(
        self, updates: list[dict[str, Any]], test_name: str, validate_types: bool = True
    ) -> bool:
        """验证QUOTES数据的content格式是否符合v2.1架构规范

        v2.1规范规定的 QUOTES content 格式:
        {
            "n": "BINANCE:BTCUSDT",        // 标的全名 (string)
            "s": "ok",                      // 状态 (string)
            "v": {
                "ch": 123.45,              // 价格变化 (number)
                "chp": 2.35,               // 价格变化百分比 (number)
                "lp": 50000.00,            // 最新价格 (number)
                "ask": 50001.00,           // 卖价 (number)
                "bid": 49999.00,           // 买价 (number)
                "spread": 2.00,            // 价差 (number)
                "volume": 1234.56          // 成交量 (number)
            }
        }

        Args:
            updates: 接收到的更新列表
            test_name: 测试名称
            validate_types: 是否验证字段类型

        Returns:
            验证是否通过
        """
        quotes_updates = [
            u for u in updates
            if "QUOTES" in u.get("data", {}).get("subscriptionKey", "")
        ]

        if not quotes_updates:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: 未接收到 QUOTES 数据")
            return False

        # 验证第一个 quotes 更新的 content 格式
        first_update = quotes_updates[0]
        data_content = first_update.get("data", {})
        # v2.1规范要求使用 content 字段
        if "content" not in data_content:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: payload 缺少 'content' 字段")
            return False

        content = data_content.get("content", {})

        # 检查是否包含 n, s, v 字段
        if "n" not in content:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: payload 缺少 'n' 字段")
            return False

        if "s" not in content:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: payload 缺少 's' 字段")
            return False

        if "v" not in content:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: payload 缺少 'v' 字段")
            return False

        # 验证 v 字段是字典类型
        v_value = content.get("v", {})
        if not isinstance(v_value, dict):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: content.v 必须是字典类型")
            return False

        # 验证 v 字段存在且为字典类型（字段是可选的，币安可能不提供所有字段）
        required_v_fields = ["lp"]  # 只有 lp 是必填的（最新价格）
        for field in required_v_fields:
            if field not in v_value:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(f"{test_name}: content.v 缺少必填字段 '{field}'")
                return False

        # 可选字段（如果存在则验证类型）
        optional_fields = ["open_price", "high_price", "low_price", "prev_close_price"]

        # 字段类型验证
        if validate_types:
            # n 和 s 应该是 string 类型
            if not isinstance(content.get("n"), str):
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name}: content.n 必须是字符串类型，实际为 {type(content.get('n')).__name__}"
                )
                return False

            if not isinstance(content.get("s"), str):
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name}: content.s 必须是字符串类型，实际为 {type(content.get('s')).__name__}"
                )
                return False

            # v 中的数值字段应该是 number 类型（如果字段存在才验证）
            number_fields = [
                "ch",
                "chp",
                "lp",  # 必填
                "ask",
                "bid",
                "spread",
                "volume",
                "open_price",
                "high_price",
                "low_price",
                "prev_close_price",
            ]
            for field in number_fields:
                if field in v_value and v_value.get(field) is not None and not isinstance(v_value.get(field), (int, float)):
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(
                        f"{test_name}: content.v.{field} 必须是数值类型，实际为 {type(v_value.get(field)).__name__}"
                    )
                    return False

        self.test_results["passed"] += 1
        return True

    def assert_kline_payload_format(
        self, updates: list[dict[str, Any]], test_name: str, resolution: str = "1"
    ) -> bool:
        """验证 K 线数据的 content 格式是否符合v2.1架构规范

        v2.1规范规定的 K 线 content 格式:
        {
            "time": 1703123456000,      // Unix时间戳（毫秒）
            "open": 42000.50,           // 开盘价
            "high": 42100.00,           // 最高价
            "low": 41950.00,            // 最低价
            "close": 42080.00,          // 收盘价
            "volume": 125.4321          // 成交量
        }

        Args:
            updates: 接收到的更新列表
            test_name: 测试名称
            resolution: K线周期（默认1分钟）

        Returns:
            验证是否通过
        """
        kline_updates = [
            u
            for u in updates
            if f"KLINE_{resolution}" in u.get("data", {}).get("subscriptionKey", "")
        ]

        if not kline_updates:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: 未接收到 KLINE_{resolution} 数据")
            return False

        first_update = kline_updates[0]
        data_content = first_update.get("data", {})
        # v2.1规范要求使用 content 字段
        if "content" not in data_content:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: payload 缺少 'content' 字段")
            return False

        payload = data_content.get("content", {})

        # 必填字段验证
        required_fields = ["time", "open", "high", "low", "close"]
        for field in required_fields:
            if field not in payload:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(f"{test_name}: payload 缺少 '{field}' 字段")
                return False

        # 字段类型验证（架构规定所有字段为 number 类型）
        number_fields = ["time", "open", "high", "low", "close"]
        for field in number_fields:
            if not isinstance(payload.get(field), (int, float)):
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name}: payload.{field} 必须是数值类型，实际为 {type(payload.get(field)).__name__}"
                )
                return False

        # volume 字段验证（可选，但存在时必须为数值类型）
        if "volume" in payload:
            if not isinstance(payload.get("volume"), (int, float)):
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name}: payload.volume 必须是数值类型，实际为 {type(payload.get('volume')).__name__}"
                )
                return False

        self.test_results["passed"] += 1
        return True

    def print_summary(self, test_name: str):
        """打印最小化测试结果"""
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]

        if failed == 0:
            print(f"[PASS] {test_name}: {passed}/{passed + failed} 通过")
        else:
            print(f"[WARN] {test_name}: {passed} 通过, {failed} 失败")
            for error in self.test_results["errors"]:
                print(f"  [FAIL] {error}")


def simple_test(test_func):
    """简化的测试装饰器（连接复用版）"""

    async def wrapper(*args, **kwargs):
        test_instance = args[0]
        try:
            # 只在第一个测试中初始化连接
            await test_instance.setup()

            # 执行测试
            result = await test_func(test_instance)

            # 返回测试结果，不关闭连接
            return result
        except Exception as e:
            test_instance.test_results["failed"] += 1
            test_instance.test_results["errors"].append(f"{test_func.__name__}: {e!s}")
            return False

    return wrapper
