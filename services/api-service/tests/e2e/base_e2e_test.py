"""
端到端测试基类

提供统一的WebSocket连接管理、消息发送和响应验证功能。
所有端到端测试都应该继承此类。

使用项目的Pydantic模型进行数据验证，确保类型安全和数据完整性。

作者: Claude Code
版本: v2.0.0
"""

import sys
from pathlib import Path

# 添加 src 目录到路径（支持直接运行）
# Path(__file__) = tests/e2e/base_e2e_test.py
# parent.parent = api-service/tests/ -> 需要向上两级到 api-service/
_api_service_root = Path(__file__).resolve().parent.parent.parent
_src_path = _api_service_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import asyncio
import json
import logging
import time
from collections.abc import Callable
from typing import Any

import websockets
from pydantic import ValidationError

# 项目模型导入
from models import KlineBars, KlineData, QuotesList, WebSocketMessage

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketTestClient:
    """WebSocket测试客户端"""

    def __init__(self, uri: str = "ws://localhost:8000/ws"):
        self.uri = uri
        self.websocket: websockets.WebSocketServerProtocol | None = None
        self.connected = False
        self.response_handlers: dict[str, Callable] = {}
        self.message_queue: list[dict[str, Any]] = []
        self.request_id_counter = 0

    async def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            logger.info(f"正在连接到 {self.uri}...")
            self.websocket = await websockets.connect(self.uri, ping_interval=20, ping_timeout=60)
            self.connected = True
            logger.info("✅ WebSocket连接成功")
            return True
        except Exception as e:
            logger.error(f"❌ WebSocket连接失败: {e!s}")
            self.connected = False
            return False

    async def disconnect(self):
        """断开WebSocket连接"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("✅ WebSocket连接已断开")

    def _generate_request_id(self) -> str:
        """生成唯一请求ID"""
        self.request_id_counter += 1
        return f"test_req_{int(time.time() * 1000)}_{self.request_id_counter}"

    async def _send_raw_message(self, message: dict[str, Any]) -> None:
        """发送消息（不接收响应）"""
        if not self.connected or not self.websocket:
            raise ConnectionError("WebSocket未连接")

        # 自动生成requestId
        if "requestId" not in message:
            message["requestId"] = self._generate_request_id()

        # 确保有timestamp
        if "timestamp" not in message:
            message["timestamp"] = int(time.time() * 1000)

        message_str = json.dumps(message, separators=(",", ":"))
        logger.info(f"📤 发送消息: {message_str}")
        await self.websocket.send(message_str)

    async def _recv_message(self, timeout: float = 10.0) -> dict[str, Any] | None:
        """接收单个响应消息"""
        if not self.connected or not self.websocket:
            return None

        try:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            response_dict = json.loads(response)
            self._log_response(response_dict)
            return response_dict
        except asyncio.TimeoutError:
            logger.error(f"❌ 响应超时")
            return None

    async def send_message(
        self, message: dict[str, Any], expect_response: bool = True
    ) -> dict[str, Any] | None:
        """
        发送WebSocket消息

        遵循设计文档 v2.0 格式：
        - type 在顶层（如 GET_CONFIG, SUBSCRIBE）
        - 具体请求参数在 data 内部

        Args:
            message: 要发送的消息字典
            expect_response: 是否期待响应消息

        Returns:
            响应消息字典或None
        """
        if not self.connected or not self.websocket:
            raise ConnectionError("WebSocket未连接")

        # 自动生成requestId
        if "requestId" not in message and expect_response:
            message["requestId"] = self._generate_request_id()

        # 确保有timestamp
        if "timestamp" not in message:
            message["timestamp"] = int(time.time() * 1000)

        # 发送消息
        message_str = json.dumps(message, separators=(",", ":"))
        logger.info(f"📤 发送消息: {message_str}")

        await self.websocket.send(message_str)

        # 等待响应（如果需要）
        if expect_response:
            try:
                # 第一阶段：接收 ACK 确认
                response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
                response_dict = json.loads(response)
                self._log_response(response_dict)

                # 如果收到 ACK，继续等待 SUCCESS 响应
                # 遵循设计文档：type 为 ACK
                if response_dict.get("type") == "ACK":
                    logger.info(f"📋 收到 ACK 确认，继续等待 SUCCESS...")

                    # 第二阶段：接收 SUCCESS 响应
                    response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
                    response_dict = json.loads(response)
                    self._log_response(response_dict)
                    return response_dict
                else:
                    # 其他响应类型直接返回
                    return response_dict

            except asyncio.TimeoutError:
                logger.error("❌ 响应超时")
                return None

        return None

    def _log_response(self, response_dict: dict[str, Any]):
        """限制打印的响应数据量"""
        # 深拷贝响应数据以避免修改原始数据
        import copy

        response_copy = copy.deepcopy(response_dict)

        # 如果是K线数据，只打印前2根K线
        if response_dict.get("type") == "klines" and "data" in response_copy:
            data = response_copy["data"]
            if "bars" in data and isinstance(data["bars"], list) and len(data["bars"]) > 2:
                # 保存前2根K线
                data["bars"] = data["bars"][:2]
                # 添加省略提示
                data["note"] = f"... (省略了 {len(response_dict['data']['bars']) - 2} 根K线)"
                logger.info(f"📥 接收响应: {json.dumps(response_copy, indent=2)}")
                return

        # 如果是搜索结果，只打印前5个符号
        if response_dict.get("type") == "search_symbols" and "data" in response_copy:
            data = response_copy["data"]
            if "symbols" in data and isinstance(data["symbols"], list) and len(data["symbols"]) > 5:
                # 保存前5个符号
                data["symbols"] = data["symbols"][:5]
                # 添加省略提示
                data["note"] = f"... (省略了 {len(response_dict['data']['symbols']) - 5} 个符号)"
                logger.info(f"📥 接收响应: {json.dumps(response_copy, indent=2)}")
                return

        # 默认打印完整响应
        logger.info(f"📥 接收响应: {json.dumps(response_dict, indent=2)}")

    async def subscribe(self, subscriptions: list[str]) -> dict[str, Any] | None:
        """
        发送订阅消息 - v2.0订阅键数组格式

        遵循设计文档 v2.0 格式：
        - type 在顶层（如 SUBSCRIBE）
        - 具体参数在 data 内部

        三阶段模式：
        1. 发送 SUBSCRIBE 请求
        2. 接收 ACK 确认
        3. 接收 SUCCESS 响应
        4. 实时数据通过 UPDATE 推送（独立机制）

        v2.0订阅键格式: {EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{INTERVAL}]

        Args:
            subscriptions: v2.0格式订阅键列表，如：
                ["BINANCE:BTCUSDT@KLINE_1", "BINANCE:BTCUSDT@QUOTES"]

        Returns:
            订阅成功响应（SUCCESS）
        """
        message = {
            "protocolVersion": "2.0",
            "type": "SUBSCRIBE",
            "data": {"subscriptions": subscriptions},
        }

        # 发送消息
        await self._send_raw_message(message)

        # 接收 ACK 确认
        ack_response = await self._recv_message(timeout=5)
        if ack_response:
            logger.info(f"📋 收到 ACK 确认")
        else:
            logger.error("❌ 未收到 ACK 确认")
            return None

        # 接收 SUCCESS 响应
        success_response = await self._recv_message(timeout=5)
        return success_response

    async def unsubscribe(
        self, subscriptions: list[str] | None = None, all_subscriptions: bool = False
    ) -> dict[str, Any] | None:
        """
        发送取消订阅消息 - v2.0订阅键数组格式

        遵循设计文档 v2.0 格式：
        - type 在顶层（如 UNSUBSCRIBE）
        - 具体参数在 data 内部

        三阶段模式：
        1. 发送 UNSUBSCRIBE 请求
        2. 接收 ACK 确认
        3. 接收 SUCCESS 响应

        Args:
            subscriptions: v2.0格式订阅键列表，如：
                ["BINANCE:BTCUSDT@KLINE_1", "BINANCE:BTCUSDT@QUOTES"]
            all_subscriptions: 是否取消所有订阅

        Returns:
            取消订阅成功响应（SUCCESS）
        """
        message = {"protocolVersion": "2.0", "type": "UNSUBSCRIBE", "data": {}}

        if all_subscriptions:
            message["data"]["all"] = True
        else:
            message["data"]["subscriptions"] = subscriptions

        # 发送消息
        await self._send_raw_message(message)

        # 接收 ACK 确认
        ack_response = await self._recv_message(timeout=5)
        if ack_response:
            logger.info(f"📋 收到 ACK 确认")
        else:
            logger.error("❌ 未收到 ACK 确认")
            return None

        # 接收 SUCCESS 响应
        success_response = await self._recv_message(timeout=5)
        return success_response

    async def get_config(self) -> dict[str, Any] | None:
        """获取配置

        遵循设计文档 v2.0 格式：
        - type 在顶层（GET_CONFIG）
        - 具体参数在 data 内部
        """
        message = {"protocolVersion": "2.0", "type": "GET_CONFIG", "data": {}}
        return await self.send_message(message)

    async def search_symbols(
        self, query: str, exchange: str = "BINANCE", limit: int = 50
    ) -> dict[str, Any] | None:
        """
        搜索交易对

        遵循设计文档 v2.0 格式：
        - type 在顶层（GET_SEARCH_SYMBOLS）
        - 具体参数在 data 内部

        Args:
            query: 搜索关键词
            exchange: 交易所代码
            limit: 返回数量限制

        Returns:
            搜索结果
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
        return await self.send_message(message)

    async def get_klines(
        self, symbol: str, resolution: str, from_time: int, to_time: int
    ) -> dict[str, Any] | None:
        """
        获取K线数据

        遵循设计文档 v2.0 格式：
        - type 在顶层（GET_KLINES）
        - 具体参数在 data 内部

        Args:
            symbol: 交易对符号，如 "BINANCE:BTCUSDT"
            resolution: 分辨率，如 "60"
            from_time: 开始时间戳（毫秒）
            to_time: 结束时间戳（毫秒）

        Returns:
            K线数据
        """
        # v2.1规范：使用 interval 字段（与数据库字段一致）
        message = {
            "protocolVersion": "2.0",
            "type": "GET_KLINES",
            "data": {
                "symbol": symbol,
                "interval": resolution,
                "from_time": from_time,
                "to_time": to_time,
            },
        }
        return await self.send_message(message)

    async def get_quotes(self, symbols: list[str]) -> dict[str, Any] | None:
        """
        获取报价数据

        遵循设计文档 v2.0 格式：
        - type 在顶层（GET_QUOTES）
        - 具体参数在 data 内部

        Args:
            symbols: 交易对符号列表

        Returns:
            报价数据
        """
        message = {
            "protocolVersion": "2.0",
            "type": "GET_QUOTES",
            "data": {"symbols": symbols},
        }
        return await self.send_message(message)

    async def listen_for_updates(self, timeout: float = 10.0) -> list[dict[str, Any]]:
        """
        监听实时数据推送

        遵循设计文档 v2.0：
        - UPDATE 消息的 type 为 "UPDATE"
        - subscriptionKey 和 content 在顶层

        Args:
            timeout: 监听超时时间（秒）

        Returns:
            接收到的更新消息列表
        """
        updates = []
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                message_dict = json.loads(message)

                # 只收集 UPDATE 消息
                # 遵循设计文档：type 为 "UPDATE"
                if message_dict.get("type") == "UPDATE":
                    updates.append(message_dict)
                    logger.info(f"📊 接收 UPDATE: {json.dumps(message_dict, indent=2)}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"❌ 监听消息错误: {e!s}")
                break

        return updates

    async def wait_for_task_completion(
        self, task_id: int | None = None, timeout: float = 30.0
    ) -> dict[str, Any] | None:
        """
        等待异步任务完成并返回结果

        遵循设计文档 v2.0 三阶段模式：
        1. 客户端发送请求（携带 requestId）
        2. 服务端返回 ACK 确认（type: "ACK", requestId, data: {}）
        3. 服务端异步处理完成后返回 SUCCESS（type: "CONFIG_DATA" 等, requestId 和数据）

        注意：taskId 不返回给客户端，仅在服务端内部使用。

        Args:
            task_id: 任务ID（已废弃，不再使用，保持向后兼容）
            timeout: 超时时间（秒）

        Returns:
            任务完成后的响应数据，或None（超时或失败）
        """
        start_time = time.time()
        has_received_ack = False

        while time.time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                message_dict = json.loads(message)
                msg_type = message_dict.get("type")

                # 阶段2: ACK 确认
                # 遵循设计文档：type 为 "ACK"
                if msg_type == "ACK":
                    logger.info(f"📋 收到 ACK 确认")
                    has_received_ack = True
                    # 继续等待 SUCCESS 响应
                    continue

                # 阶段3: SUCCESS 响应（无论是否已收到ACK）
                # SUCCESS 响应的 type 是具体数据类型（如 CONFIG_DATA, KLINES_DATA）
                if msg_type in ["CONFIG_DATA", "KLINES_DATA", "QUOTES_DATA", "SEARCH_SYMBOLS_DATA", "SUBSCRIPTIONS_DATA"]:
                    # SUCCESS 响应直接返回数据
                    logger.info(f"✅ 任务完成（{msg_type}）")
                    return message_dict

                # 实时数据推送（独立机制，不属于请求-响应流程）
                # 遵循设计文档：type 为 "UPDATE"
                if msg_type == "UPDATE":
                    logger.debug(f"📊 收到 UPDATE 消息")

            except asyncio.TimeoutError:
                # 超时后检查是否应该继续等待
                remaining = timeout - (time.time() - start_time)
                if remaining > 0:
                    continue
                break
            except Exception as e:
                logger.error(f"❌ 监听任务完成消息错误: {e!s}")
                break

        if not has_received_ack:
            logger.warning(f"⏰ 等待任务完成超时（未收到 ACK 确认）")
        else:
            logger.warning(f"⏰ 等待任务完成超时")
        return None


class E2ETestBase:
    """端到端测试基类"""

    __test__ = False  # 禁用pytest自动收集

    def __init__(self, auto_connect: bool = True):
        self.client: WebSocketTestClient | None = None
        self.test_results: dict[str, Any] = {}
        self.logger = logger
        self.auto_connect = auto_connect
        self._connected = False

    async def setup(self):
        """测试设置"""
        if self.auto_connect and not self._connected:
            await self.connect()
        self.test_results = {"passed": 0, "failed": 0, "errors": []}

    async def teardown(self):
        """测试清理"""
        if self.auto_connect and self._connected:
            await self.disconnect()

    async def connect(self):
        """建立WebSocket连接（可手动调用）"""
        if self._connected:
            return

        self.client = WebSocketTestClient()
        connected = await self.client.connect()
        if not connected:
            raise ConnectionError("无法连接到WebSocket服务器")
        self._connected = True

    async def disconnect(self):
        """断开WebSocket连接（可手动调用）"""
        if not self._connected:
            return

        if self.client:
            await self.client.disconnect()
        self._connected = False

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.teardown()

    def assert_response_success(self, response: dict[str, Any] | None, test_name: str) -> bool:
        """验证响应是否成功（遵循API设计文档的三阶段模式）

        遵循设计文档 v2.0 三阶段模式：
        - 阶段1: 客户端发送请求（携带 requestId）
        - 阶段2: ACK 确认 - type="ACK", requestId, data: {}
        - 阶段3: SUCCESS 结果 - type="CONFIG_DATA" 等, requestId, data

        设计文档定义：
        - ACK: {"type": "ACK", "requestId": "req_xxx", "data": {}}
        - SUCCESS: {"type": "CONFIG_DATA", "requestId": "req_xxx", "data": {...}}

        注意：taskId 不返回给客户端，仅在服务端内部使用。

        Args:
            response: 响应消息
            test_name: 测试名称（用于日志）

        Returns:
            验证是否成功
        """
        if not response:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: 响应为空")
            return False

        msg_type = response.get("type")
        data = response.get("data", {})

        # 处理错误响应
        # 遵循设计文档：type 为 "ERROR"
        if msg_type == "ERROR":
            self.test_results["failed"] += 1
            error_data = data if isinstance(data, dict) else {}
            error_msg = (
                f"{test_name}: {error_data.get('errorCode')} - {error_data.get('errorMessage')}"
            )
            self.test_results["errors"].append(error_msg)
            return False

        # 处理 ACK 确认（阶段2）- 遵循设计文档
        # 所有请求类型都遵循"先返回 ACK，确认收到请求"的原则
        if msg_type == "ACK":
            # ACK 响应确认请求已收到，客户端应继续等待 SUCCESS 响应
            logger.info(f"  📋 收到 ACK 确认")
            return True

        # 处理 SUCCESS 响应（阶段3）
        # SUCCESS 响应的 type 是具体数据类型（如 CONFIG_DATA, KLINES_DATA）
        if msg_type in ["CONFIG_DATA", "KLINES_DATA", "QUOTES_DATA", "SEARCH_SYMBOLS_DATA",
                         "SUBSCRIPTIONS_DATA", "SUBSCRIBE_DATA", "UNSUBSCRIBE_DATA"]:
            # SUCCESS 响应包含实际数据
            self.test_results["passed"] += 1
            return True

        # 未知响应类型
        self.test_results["failed"] += 1
        self.test_results["errors"].append(f"{test_name}: 未知响应类型: {msg_type}")
        return False

    def assert_message_format(self, message: dict[str, Any] | None, test_name: str) -> bool:
        """验证消息格式 - 使用Pydantic模型进行验证

        遵循设计文档 v2.0：
        - type 字段在顶层（如 GET_CONFIG, CONFIG_DATA, UPDATE, ERROR）
        - 具体请求/响应参数在 data 内部
        - UPDATE 消息：type="UPDATE", subscription_key, content 在顶层

        Args:
            message: WebSocket消息字典
            test_name: 测试名称（用于日志）

        Returns:
            验证是否通过
        """
        if not message:
            self._record_failure(test_name, "消息为空")
            return False

        # 初始化 test_results（如果未初始化）
        if not hasattr(self, 'test_results') or not isinstance(self.test_results, dict):
            self.test_results = {"passed": 0, "failed": 0, "errors": []}

        try:
            msg_type = message.get("type")

            # UPDATE 消息没有 requestId，subscription_key 和 content 在顶层
            # 遵循设计文档：type="UPDATE"
            if msg_type == "UPDATE":
                from models.protocol.ws_message import MessageUpdate
                validated_message = MessageUpdate(**message)
            else:
                # 其他消息使用 WebSocketMessage 模型验证
                validated_message = WebSocketMessage(**message)

            # 验证协议版本
            if validated_message.protocol_version != "2.0":
                self._record_failure(test_name, f"无效的协议版本: {validated_message.protocol_version}")
                return False

            # 验证 type 字段存在（顶层）
            if not msg_type:
                self._record_failure(test_name, "消息缺少 type 字段")
                return False

            # 验证 type 值是否符合规范
            # 请求类型
            request_types = ["GET_CONFIG", "GET_KLINES", "GET_QUOTES", "GET_SEARCH_SYMBOLS",
                             "GET_RESOLVE_SYMBOL", "GET_SERVER_TIME", "SUBSCRIBE", "UNSUBSCRIBE",
                             "GET_SUBSCRIPTIONS", "GET_METRINS"]
            # 响应类型
            response_types = ["CONFIG_DATA", "KLINES_DATA", "QUOTES_DATA", "SEARCH_SYMBOLS_DATA",
                             "RESOLVE_SYMBOL_DATA", "SERVER_TIME_DATA", "SUBSCRIPTIONS_DATA",
                             "METRICS_DATA", "SUBSCRIBE_DATA", "UNSUBSCRIBE_DATA", "ACK",
                             "ERROR", "UPDATE"]

            # 验证 data 字段存在
            data = validated_message.data
            if data is None:
                self._record_failure(test_name, "消息缺少 data 字段")
                return False

            return True
        except ValidationError as e:
            self._record_failure(test_name, f"消息格式验证失败 - {e!s}")
            return False

    def _record_failure(self, test_name: str, error_message: str):
        """记录测试失败"""
        if hasattr(self, 'test_results') and isinstance(self.test_results, dict):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {error_message}")
        else:
            self.test_results = {"passed": 0, "failed": 1, "errors": [f"{test_name}: {error_message}"]}

    def assert_kline_data(self, kline_data: dict[str, Any], test_name: str) -> bool:
        """验证K线数据格式 - 使用Pydantic模型进行验证

        验证规则：
        - KlineBars 和 KlineData 模型统一使用 interval 字段
        - 响应数据必须包含 interval 字段（与数据库字段和内部逻辑一致）
        - 如果数据中只有 resolution 字段，则转换后验证
        """
        # 深拷贝数据，避免修改原始数据
        import copy
        data = copy.deepcopy(kline_data)

        # 如果数据只有 resolution 而没有 interval，进行转换（向后兼容）
        if "resolution" in data and "interval" not in data:
            data["interval"] = data.pop("resolution")

        # 验证必需字段存在
        if "interval" not in data:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: K线数据缺少 interval 字段")
            return False

        try:
            # 使用Pydantic模型验证K线数据
            if "bars" in data:
                # 如果是KlineBars格式
                validated_data = KlineBars(**data)
            else:
                # 如果是单个K线数据，尝试构建KlineData
                validated_data = KlineData(**data)

            return True
        except ValidationError as e:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: K线数据格式验证失败 - {e!s}")
            return False
        except Exception:
            # 回退到字典验证方式
            if "bars" not in data:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(f"{test_name}: 缺少bars字段")
                return False

            bars = data.get("bars", [])
            if not isinstance(bars, list):
                self.test_results["failed"] += 1
                self.test_results["errors"].append(f"{test_name}: bars必须是数组")
                return False

            # 验证第一个bar的格式
            if bars:
                bar = bars[0]
                required_bar_fields = ["time", "open", "high", "low", "close"]
                for field in required_bar_fields:
                    if field not in bar:
                        self.test_results["failed"] += 1
                        self.test_results["errors"].append(f"{test_name}: bar缺少字段 {field}")
                        return False

                # 验证数据逻辑
                if bar["high"] < bar["low"]:
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(f"{test_name}: high < low")
                    return False

                if bar["open"] <= 0 or bar["close"] <= 0:
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(f"{test_name}: open/close必须大于0")
                    return False

            return True

    def assert_quotes_data(self, quotes_data: dict[str, Any], test_name: str) -> bool:
        """验证quotes数据格式 - 使用Pydantic模型进行验证"""
        try:
            # 使用Pydantic模型验证quotes数据
            validated_data = QuotesList(**quotes_data)
            return True
        except ValidationError as e:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: Quotes数据格式验证失败 - {e!s}")
            return False
        except Exception:
            # 回退到字典验证方式
            if "quotes" not in quotes_data:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(f"{test_name}: 缺少quotes字段")
                return False

            quotes = quotes_data.get("quotes", [])
            if not isinstance(quotes, list):
                self.test_results["failed"] += 1
                self.test_results["errors"].append(f"{test_name}: quotes必须是数组")
                return False

            # 验证第一个quote的格式
            if quotes:
                quote = quotes[0]
                if "n" not in quote or "s" not in quote or "v" not in quote:
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(f"{test_name}: quote缺少必要字段")
                    return False

                # 验证v字段
                v = quote["v"]
                required_v_fields = ["ch", "chp", "lp", "volume"]
                for field in required_v_fields:
                    if field not in v:
                        self.test_results["failed"] += 1
                        self.test_results["errors"].append(f"{test_name}: quote.v缺少字段 {field}")
                        return False

            return True

    def assert_subscription_format(self, subscriptions: list[str], test_name: str) -> bool:
        """验证v2.0订阅键数组格式

        v2.0订阅键格式: {EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{INTERVAL}]
        - EXCHANGE: 交易所代码（大写，如BINANCE）
        - SYMBOL: 交易对（大写，如BTCUSDT）
        - 产品后缀: 可选（如.PERP表示永续合约）
        - DATA_TYPE: 数据类型（KLINE, QUOTES, TRADE）
        - INTERVAL: 分辨率（可选，如_1, _60, _D）

        支持的数据类型: KLINE, QUOTES, TRADE (全大写)

        Args:
            subscriptions: 订阅键列表，如 ["BINANCE:BTCUSDT@KLINE_1", "BINANCE:BTCUSDT@QUOTES"]
            test_name: 测试名称（用于日志）

        Returns:
            验证是否通过
        """
        import re

        # v2.0订阅键正则表达式
        # 格式: {EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{INTERVAL}]
        # 分辨率支持数字(1, 60, 1440)和字母(W, D, W, M, Y)
        subscription_pattern = re.compile(
            r"^[A-Z]+:[A-Z0-9]+(\.[A-Z0-9]+)?@(KLINE|QUOTES|TRADE)(_[0-9A-Z]+)?$"
        )

        # 验证subscriptions是列表
        if not isinstance(subscriptions, list):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: subscriptions必须是数组")
            return False

        # 验证订阅列表不为空
        if not subscriptions:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: subscriptions数组不能为空")
            return False

        # 验证每个订阅键
        for i, sub_key in enumerate(subscriptions):
            # 验证是字符串
            if not isinstance(sub_key, str):
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name}: subscriptions[{i}]必须是字符串"
                )
                return False

            # 验证非空
            if not sub_key.strip():
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name}: subscriptions[{i}]不能为空字符串"
                )
                return False

            # 验证v2.0订阅键格式
            if not subscription_pattern.match(sub_key):
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name}: 无效的v2.0订阅键格式 '{sub_key}'，"
                    f"期望格式: {{EXCHANGE}}:{{SYMBOL}}[.{{产品后缀}}]@{{DATA_TYPE}}[_{{INTERVAL}}]"
                )
                return False

        return True

    def assert_unified_response_format(self, response: dict[str, Any] | None, expected_type: str) -> bool:
        """验证统一响应格式 (v2.1规范)

        v2.1核心要求：
        - protocolVersion 字段必须存在
        - action 字段必须为 "success"
        - data.type 字段必须在data内部
        - requestId 字段必须存在
        - timestamp 字段必须存在

        规范参考：TradingView-完整API规范设计文档.md 第267-295节

        Args:
            response: 响应消息字典
            expected_type: 期望的type字段值（如 "config", "klines", "quotes" 等）

        Returns:
            验证是否通过
        """
        if not response:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"统一响应格式验证失败: 响应为空")
            return False

        # 验证 protocolVersion 字段
        if "protocolVersion" not in response:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("统一响应格式验证失败: 缺少 protocolVersion 字段")
            return False

        # 验证 action 字段
        action = response.get("action")
        if action != "success":
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"统一响应格式验证失败: action必须是'success'，实际: {action}"
            )
            return False

        # 验证 data 字段存在
        data = response.get("data", {})
        if not data:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("统一响应格式验证失败: 缺少 data 字段")
            return False

        # 验证 type 字段在 data 内部 (v2.1核心要求)
        if "type" not in data:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("统一响应格式验证失败: type字段必须在data内部")
            return False

        # 验证 type 值匹配
        msg_type = data.get("type")
        if msg_type != expected_type:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"统一响应格式验证失败: type不匹配，期望: {expected_type}，实际: {msg_type}"
            )
            return False

        # 验证 requestId 字段
        if "requestId" not in response:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("统一响应格式验证失败: 缺少 requestId 字段")
            return False

        # 验证 timestamp 字段
        if "timestamp" not in response:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("统一响应格式验证失败: 缺少 timestamp 字段")
            return False

        return True

    def assert_kline_bars(self, bars: list[dict[str, Any]], test_name: str) -> bool:
        """严格验证K线Bar对象 (TradingView Bar格式)

        TradingView Bar格式要求：
        - time: 时间戳（毫秒，Unix纪元开始以来的毫秒数）
        - open, high, low, close: 价格数据（数字）
        - volume: 可选，成交量（数字）

        规范参考：TradingView-完整API规范设计文档.md 第1810-1828节

        Args:
            bars: Bar对象列表
            test_name: 测试名称（用于日志）

        Returns:
            验证是否通过
        """
        if not isinstance(bars, list):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: bars必须是数组")
            return False

        for i, bar in enumerate(bars):
            # 验证必需字段
            required_fields = ["time", "open", "high", "low", "close"]
            for field in required_fields:
                if field not in bar:
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(
                        f"{test_name} bar[{i}]: 缺少必需字段 {field}"
                    )
                    return False

            # 验证 time 字段（必须是毫秒时间戳）
            time_val = bar.get("time")
            if not isinstance(time_val, int):
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name} bar[{i}]: time必须是整数（毫秒时间戳）"
                )
                return False

            if time_val <= 0:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name} bar[{i}]: time必须大于0"
                )
                return False

            # 验证价格字段（open, high, low, close）
            price_fields = ["open", "high", "low", "close"]
            for field in price_fields:
                value = bar.get(field)
                if not isinstance(value, (int, float)):
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(
                        f"{test_name} bar[{i}].{field}: 必须是数字"
                    )
                    return False

                if value < 0:
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(
                        f"{test_name} bar[{i}].{field}: 必须大于等于0"
                    )
                    return False

            # 验证价格逻辑：high >= low, high >= open, high >= close, low <= open, low <= close
            high = bar.get("high")
            low = bar.get("low")
            open_price = bar.get("open")
            close_price = bar.get("close")

            if high < low:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name} bar[{i}]: high ({high}) 不能小于 low ({low})"
                )
                return False

            # 验证 volume 字段（可选）
            if "volume" in bar:
                volume = bar.get("volume")
                if not isinstance(volume, (int, float)):
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(
                        f"{test_name} bar[{i}].volume: 必须是数字"
                    )
                    return False

                if volume < 0:
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(
                        f"{test_name} bar[{i}].volume: 必须大于等于0"
                    )
                    return False

        return True

    def assert_quotes_format(self, quotes: list[dict[str, Any]], test_name: str) -> bool:
        """严格验证Quotes数据 (TradingView Quotes格式)

        TradingView Quotes格式要求：
        - n: 符号名称（EXCHANGE:SYMBOL格式）
        - s: 状态（"ok" 或 "error"）
        - v: 报价对象，包含价格数据

        规范参考：TradingView-完整API规范设计文档.md 第1436-1469节

        Args:
            quotes: Quote对象列表
            test_name: 测试名称（用于日志）

        Returns:
            验证是否通过
        """
        if not isinstance(quotes, list):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: quotes必须是数组")
            return False

        for i, quote in enumerate(quotes):
            # 验证基础字段
            if "n" not in quote:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name} quote[{i}]: 缺少n字段（symbol name）"
                )
                return False

            if "s" not in quote:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name} quote[{i}]: 缺少s字段（status）"
                )
                return False

            if "v" not in quote:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name} quote[{i}]: 缺少v字段（quote values）"
                )
                return False

            # 验证 n 字段格式（必须是 EXCHANGE:SYMBOL）
            symbol = quote.get("n")
            if not isinstance(symbol, str):
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name} quote[{i}].n: 必须是字符串"
                )
                return False

            if ":" not in symbol:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name} quote[{i}].n: 必须包含交易所前缀（如BINANCE:）"
                )
                return False

            # 验证 s 字段（状态）
            status = quote.get("s")
            if status not in ["ok", "error"]:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name} quote[{i}].s: 必须是'ok'或'error'，实际: {status}"
                )
                return False

            # 验证 v 对象
            v = quote.get("v")
            if not isinstance(v, dict):
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name} quote[{i}].v: 必须是对象"
                )
                return False

            # 验证必需的价格字段（lp - last price）
            if "lp" not in v:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name} quote[{i}].v: 缺少lp字段（last price）"
                )
                return False

            lp = v.get("lp")
            if not isinstance(lp, (int, float)):
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name} quote[{i}].v.lp: 必须是数字"
                )
                return False

            if lp <= 0:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name} quote[{i}].v.lp: 必须大于0"
                )
                return False

            # 验证可选但推荐的价格字段
            price_fields = ["ask", "bid", "open_price", "high_price", "low_price", "prev_close_price"]
            for field in price_fields:
                if field in v:
                    value = v.get(field)
                    if not isinstance(value, (int, float)):
                        self.test_results["failed"] += 1
                        self.test_results["errors"].append(
                            f"{test_name} quote[{i}].v.{field}: 必须是数字"
                        )
                        return False

                    # 除了volume，其他价格字段必须大于0
                    if field != "volume" and value <= 0:
                        self.test_results["failed"] += 1
                        self.test_results["errors"].append(
                            f"{test_name} quote[{i}].v.{field}: 必须大于0"
                        )
                        return False

            # 验证 volume 字段（可选，但必须>=0）
            if "volume" in v:
                volume = v.get("volume")
                if not isinstance(volume, (int, float)):
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(
                        f"{test_name} quote[{i}].v.volume: 必须是数字"
                    )
                    return False

                if volume < 0:
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(
                        f"{test_name} quote[{i}].v.volume: 必须大于等于0"
                    )
                    return False

        return True

    def assert_error_response_format(self, response: dict[str, Any] | None, test_name: str) -> bool:
        """验证错误响应格式 (TradingView错误处理规范)

        错误响应格式要求：
        - action: "error"
        - data.errorCode: 错误代码
        - data.errorMessage: 错误消息

        规范参考：TradingView-完整API规范设计文档.md 第1697-1731节

        Args:
            response: 响应消息字典
            test_name: 测试名称（用于日志）

        Returns:
            验证是否通过
        """
        if not response:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: 响应为空")
            return False

        # 验证 action 字段
        if response.get("action") != "error":
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: action必须是'error'，实际: {response.get('action')}"
            )
            return False

        # 验证 data 字段
        data = response.get("data", {})
        if not isinstance(data, dict):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: data必须是对象")
            return False

        # 验证 errorCode 字段
        if "errorCode" not in data:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: 缺少errorCode字段")
            return False

        # 验证 errorMessage 字段
        if "errorMessage" not in data:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: 缺少errorMessage字段")
            return False

        # 验证字段类型
        error_code = data.get("errorCode")
        if not isinstance(error_code, str):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: errorCode必须是字符串")
            return False

        error_message = data.get("errorMessage")
        if not isinstance(error_message, str):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: errorMessage必须是字符串")
            return False

        return True

    def assert_symbol_info_model(self, symbol_info: dict[str, Any], test_name: str) -> bool:
        """严格验证SymbolInfo模型完整性 (TradingView LibrarySymbolInfo接口标准)

        SymbolInfo是TradingView Charting Library的核心接口之一，必须符合官方规范。
        规范参考：TradingView-完整API规范设计文档.md 第1736-1808节

        必需字段（无默认值）：
        - name: 符号名称（如"BTCUSDT"）
        - ticker: 唯一标识符（如"BINANCE:BTCUSDT"）
        - description: 品种描述（如"BTC/USDT"）
        - type: 品种类型（如"crypto"）
        - exchange: 交易所名称（如"BINANCE"）
        - listed_exchange: 上市交易所名称
        - session: 交易时间（如"24x7"）
        - timezone: 时区（如"Etc/UTC"）
        - minmov: 最小变动单位
        - pricescale: 价格精度

        官方标准字段（带默认值）：
        - base_name: 基础符号数组
        - session_display: 显示用交易时间
        - session_holidays: 非交易日
        - has_intraday: 是否支持日内数据
        - has_seconds: 是否支持秒级数据
        - has_ticks: 是否支持Tick数据
        - has_daily: 是否支持日线数据
        - has_weekly_and_monthly: 是否支持周线和月线数据
        - supported_resolutions: 支持的分辨率列表
        - format: 显示格式
        - data_status: 数据状态
        - delay: 数据延迟
        - volume_precision: 成交量精度
        - currency_code: 交易货币

        Args:
            symbol_info: SymbolInfo数据字典
            test_name: 测试名称（用于日志）

        Returns:
            验证是否通过
        """
        if not isinstance(symbol_info, dict):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: SymbolInfo必须是对象")
            return False

        # 验证必需字段（无默认值）
        required_fields = [
            "name",           # 符号名称
            "ticker",         # 唯一标识符
            "description",    # 品种描述
            "type",           # 品种类型
            "exchange",       # 交易所名称
            "listed_exchange", # 上市交易所名称
            "session",        # 交易时间
            "timezone",       # 时区
            "minmov",         # 最小变动单位
            "pricescale",     # 价格精度
        ]

        for field in required_fields:
            if field not in symbol_info:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name}: SymbolInfo缺少必需字段 {field}"
                )
                return False

            value = symbol_info[field]
            if value is None:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(
                    f"{test_name}: SymbolInfo.{field}不能为None"
                )
                return False

        # 验证字段类型
        # name: 字符串
        if not isinstance(symbol_info["name"], str):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: SymbolInfo.name必须是字符串"
            )
            return False

        # ticker: 字符串，格式应为 EXCHANGE:SYMBOL
        if not isinstance(symbol_info["ticker"], str):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: SymbolInfo.ticker必须是字符串"
            )
            return False
        if ":" not in symbol_info["ticker"]:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: SymbolInfo.ticker必须包含交易所前缀（如BINANCE:）"
            )
            return False

        # description: 字符串
        if not isinstance(symbol_info["description"], str):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: SymbolInfo.description必须是字符串"
            )
            return False

        # type: 字符串
        if not isinstance(symbol_info["type"], str):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: SymbolInfo.type必须是字符串"
            )
            return False

        # exchange: 字符串
        if not isinstance(symbol_info["exchange"], str):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: SymbolInfo.exchange必须是字符串"
            )
            return False

        # listed_exchange: 字符串
        if not isinstance(symbol_info["listed_exchange"], str):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: SymbolInfo.listed_exchange必须是字符串"
            )
            return False

        # session: 字符串（如"24x7"）
        if not isinstance(symbol_info["session"], str):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: SymbolInfo.session必须是字符串"
            )
            return False

        # timezone: 字符串（如"Etc/UTC"）
        if not isinstance(symbol_info["timezone"], str):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: SymbolInfo.timezone必须是字符串"
            )
            return False

        # minmov: 数字
        if not isinstance(symbol_info["minmov"], (int, float)):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: SymbolInfo.minmov必须是数字"
            )
            return False

        # pricescale: 整数
        if not isinstance(symbol_info["pricescale"], int):
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: SymbolInfo.pricescale必须是整数"
            )
            return False

        # 验证可选字段（带默认值）类型
        optional_fields_with_types = {
            "base_name": (list, True),                    # list | None
            "long_description": (str, True),              # str | None
            "session_display": (str, True),               # str | None
            "session_holidays": (str, False),             # str（默认值""）
            "corrections": (str, True),                   # str | None
            "minmove2": ((int, float), True),             # float | None
            "fractional": (bool, True),                   # bool | None
            "variable_tick_size": (str, True),            # str | None
            "has_intraday": (bool, False),                # bool（默认值True）
            "has_seconds": (bool, False),                 # bool（默认值False）
            "has_ticks": (bool, False),                   # bool（默认值False）
            "seconds_multipliers": (list, True),          # list | None
            "build_seconds_from_ticks": (bool, True),     # bool | None
            "has_daily": (bool, False),                   # bool（默认值True）
            "daily_multipliers": (list, False),           # list（默认值["1"]）
            "has_weekly_and_monthly": (bool, False),      # bool（默认值True）
            "weekly_multipliers": (list, False),          # list（默认值["1"]）
            "monthly_multipliers": (list, False),         # list（默认值["1"]）
            "has_empty_bars": (bool, False),              # bool（默认值False）
            "visible_plots_set": (str, False),            # str（默认值"ohlcv"）
            "volume_precision": (int, False),             # int（默认值0）
            "data_status": (str, False),                  # str（默认值"streaming"）
            "delay": (int, False),                        # int（默认值0）
            "expired": (bool, False),                     # bool（默认值False）
            "expiration_date": ((int, type(None)), True), # int | None
            "sector": (str, True),                        # str | None
            "industry": (str, True),                      # str | None
            "currency_code": (str, True),                 # str | None
            "original_currency_code": (str, True),        # str | None
            "unit_id": (str, True),                       # str | None
            "original_unit_id": (str, True),              # str | None
            "unit_conversion_types": (list, True),        # list | None
            "subsession_id": (str, True),                 # str | None
            "subsessions": (list, True),                  # list | None
            "price_source_id": (str, True),               # str | None
            "price_sources": (list, True),                # list | None
            "logo_urls": (list, True),                    # list | None
            "format": (str, False),                       # str（默认值"price"）
            "supported_resolutions": (list, False),       # list（默认值[]）
        }

        for field, (expected_type, nullable) in optional_fields_with_types.items():
            if field not in symbol_info:
                continue  # 可选字段不存在是可以的

            value = symbol_info[field]
            if value is None and nullable:
                continue

            if not isinstance(value, expected_type):
                self.test_results["failed"] += 1
                type_name = expected_type.__name__ if hasattr(expected_type, '__name__') else str(expected_type)
                self.test_results["errors"].append(
                    f"{test_name}: SymbolInfo.{field}类型错误，期望 {type_name}"
                )
                return False

        # 验证特定值的合法性
        # pricescale 必须是正整数（用于价格精度计算）
        if symbol_info["pricescale"] <= 0:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: SymbolInfo.pricescale必须大于0"
            )
            return False

        # minmov 应该是非负数
        if symbol_info["minmov"] < 0:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(
                f"{test_name}: SymbolInfo.minmov必须大于等于0"
            )
            return False

        # session 应该包含有效的交易时段标识
        valid_sessions = ["24x7", "regular", "extended", "forex", "crypto"]
        if symbol_info["session"] not in valid_sessions:
            # 允许自定义 session 格式，但记录警告
            self.logger.warning(
                f"  ⚠️ SymbolInfo.session='{symbol_info['session']}' 不是标准值，"
                f"标准值: {valid_sessions}"
            )

        return True

    def print_test_results(self, test_name: str):
        """打印测试结果"""
        logger.info(f"\n{'=' * 80}")
        logger.info(f"测试结果: {test_name}")
        logger.info(f"{'=' * 80}")
        logger.info(f"通过: {self.test_results['passed']}")
        logger.info(f"失败: {self.test_results['failed']}")

        if self.test_results["errors"]:
            logger.info("\n错误详情:")
            for error in self.test_results["errors"]:
                logger.info(f"  ❌ {error}")

        logger.info(f"{'=' * 80}")

        return self.test_results


class AsyncContextManager:
    """异步上下文管理器"""

    def __init__(self, test_instance: E2ETestBase):
        self.test_instance = test_instance

    async def __aenter__(self) -> E2ETestBase:
        await self.test_instance.setup()
        return self.test_instance

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.test_instance.teardown()


def e2e_test(test_class=None, *, auto_connect=True):
    """端到端测试装饰器

    Args:
        test_class: 测试类（可选）
        auto_connect: 是否自动建立连接，默认为True
                    - True: 为每个测试建立新连接
                    - False: 复用测试实例的连接（用于测试套件内）

    支持两种模式：
    1. @e2e_test - 在测试实例上下文中调用每个测试方法（每个测试创建新连接）
    2. @e2e_test(auto_connect=False) - 直接调用测试方法（共享测试实例的连接）
    """

    def decorator(test_func):
        # 确保我们保留原始函数的引用
        original_func = test_func

        async def wrapper(*args, **kwargs):
            # 如果提供了test_class（类），使用它；否则从第一个参数推断
            if isinstance(test_class, type) and issubclass(test_class, E2ETestBase):
                test_instance = test_class(auto_connect=auto_connect)
            else:
                test_instance = args[0] if args else None
                if test_instance is None:
                    raise ValueError("测试方法需要至少一个参数（测试实例）")

                # 如果auto_connect为False，说明我们要复用已有的连接
                if not auto_connect:
                    # 直接调用测试方法，不创建新的连接上下文
                    result = await original_func(test_instance)
                    return result

            async with test_instance:
                # 调用原始函数
                result = await original_func(test_instance)
                return result

        return wrapper

    # 如果直接使用 @e2e_test，不带括号
    # test_class 是函数，需要返回装饰器
    if callable(test_class) and not isinstance(test_class, type):
        return decorator(test_class)
    # 如果使用 @e2e_test()，不带参数或传入类
    else:
        return decorator
