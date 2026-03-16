"""
pytest 风格测试基类

提供严格的数据验证功能，确保：
1. 响应符合设计规范（type在顶层）
2. 实时数据推送格式正确
3. 验证收到的是真实实时数据（而非缓存数据）

协议格式（严格遵循 07-websocket-protocol.md）：
- 请求: {"protocolVersion": "2.0", "type": "SUBSCRIBE", "requestId": "...", "timestamp": ..., "data": {...}}
- ACK: {"protocolVersion": "2.0", "type": "ACK", "requestId": "...", "timestamp": ..., "data": {}}
- SUCCESS: {"protocolVersion": "2.0", "type": "KLINES_DATA", "requestId": "...", "timestamp": ..., "data": {...}}
- UPDATE: {"protocolVersion": "2.0", "type": "UPDATE", "timestamp": ..., "data": {"subscriptionKey": "...", "content": {...}}}
  注意：UPDATE 推送不包含 requestId
"""

import pytest


class RealtimeTestMixin:
    """
    实时数据测试 Mixin

    提供实时数据推送的严格验证功能。
    严格遵循 07-websocket-protocol.md 规范。
    """

    def assert_is_realtime_update(
        self,
        message: dict,
        subscription_key: str | None = None,
    ) -> bool:
        """
        验证消息是实时推送（type="UPDATE"），而非ACK/SUCCESS响应

        关键验证点（严格遵循协议）：
        1. type 必须是 "UPDATE"（在顶层）
        2. 不包含 requestId（实时推送是无状态的）
        3. 包含 data.subscriptionKey
        4. 包含 data.content 数据
        """
        # 验证 type（协议要求在顶层）
        msg_type = message.get("type")
        if msg_type != "UPDATE":
            pytest.fail(f"期望 type='UPDATE', 实际为 '{msg_type}'")

        # 关键：实时推送不包含 requestId（协议明确要求）
        if "requestId" in message:
            pytest.fail(
                f"UPDATE 推送不应包含 requestId 字段，实际收到: {message.get('requestId')}"
            )

        # 验证 data 字段
        data = message.get("data")
        if not data:
            pytest.fail("UPDATE 消息缺少 data 字段")

        # 验证 subscriptionKey
        subscription_key_received = data.get("subscriptionKey")
        if not subscription_key_received:
            pytest.fail("UPDATE 消息缺少 subscriptionKey 字段")

        if subscription_key and subscription_key not in subscription_key_received:
            pytest.fail(
                f"subscriptionKey 不匹配，期望包含 '{subscription_key}', "
                f"实际为 '{subscription_key_received}'"
            )

        # 验证 content
        content = data.get("content")
        if content is None:
            pytest.fail("UPDATE 消息缺少 content 字段")

        return True

    def assert_kline_update(
        self,
        message: dict,
        resolution: str = "1",
    ) -> bool:
        """
        验证K线实时推送的数据格式

        符合 TradingView K线格式：
        {
            "time": 1703123456000,  // Unix时间戳（毫秒）
            "open": 42000.50,
            "high": 42100.00,
            "low": 41950.00,
            "close": 42080.00,
            "volume": 125.4321
        }
        """
        self.assert_is_realtime_update(message, f"KLINE_{resolution}")

        data = message.get("data", {})
        content = data.get("content", {})

        # 必填字段
        required_fields = ["time", "open", "high", "low", "close"]
        for field in required_fields:
            if field not in content:
                pytest.fail(f"K线数据缺少必填字段: {field}")
            if not isinstance(content[field], (int, float)):
                pytest.fail(f"K线字段 {field} 必须是数值类型")

        # 时间戳应该是毫秒级的
        time_value = content.get("time", 0)
        if time_value < 1000000000000:
            pytest.fail(
                f"K线时间戳应该是毫秒级 (>= 1000000000000), 实际为 {time_value}"
            )

        # 验证OHLC逻辑
        high = content.get("high", 0)
        low = content.get("low", 0)
        open_price = content.get("open", 0)
        close_price = content.get("close", 0)

        if high < max(open_price, close_price, low):
            pytest.fail(f"high 值不正确: high={high} < max(open,close,low)")
        if low > min(open_price, close_price, high):
            pytest.fail(f"low 值不正确: low={low} > min(open,close,high)")

        return True

    def assert_quotes_update(
        self,
        message: dict,
        symbol: str | None = None,
    ) -> bool:
        """
        验证报价实时推送的数据格式

        符合 TradingView Quotes 格式：
        {
            "n": "BINANCE:BTCUSDT",
            "s": "ok",
            "v": {
                "lp": 50000.00,    // 最新价格（必填）
                "ch": 123.45,     // 价格变化
                "chp": 2.35,      // 价格变化百分比
                "bid": 49999.00,  // 买价
                "ask": 50001.00,  // 卖价
                "spread": 2.00    // 价差
            }
        }
        """
        self.assert_is_realtime_update(message, "QUOTES")

        data = message.get("data", {})
        content = data.get("content", {})

        # 兼容单条和批量格式
        if isinstance(content, list):
            # 批量格式，取第一条
            if not content:
                pytest.fail("QUOTES 批量数据为空")
            content = content[0]

        # 必填字段
        if "n" not in content:
            pytest.fail("QUOTES 数据缺少 'n' 字段 (标的全名)")
        if "s" not in content:
            pytest.fail("QUOTES 数据缺少 's' 字段 (状态)")
        if "v" not in content:
            pytest.fail("QUOTES 数据缺少 'v' 字段 (报价值对象)")

        # 验证 symbol 匹配
        if symbol and content.get("n") != symbol:
            pytest.fail(f"symbol 不匹配，期望 '{symbol}', 实际为 '{content.get('n')}'")

        # 验证 v 字段
        v = content.get("v", {})
        if not isinstance(v, dict):
            pytest.fail("QUOTES v 字段必须是字典类型")

        # 最新价格是必填的
        if "lp" not in v:
            pytest.fail("QUOTES v 字段缺少必填字段 'lp' (最新价格)")
        if not isinstance(v["lp"], (int, float)):
            pytest.fail("QUOTES lp 字段必须是数值类型")

        return True


class RESTTestMixin:
    """
    REST API 测试 Mixin

    提供 REST API 响应的验证功能。
    严格遵循 07-websocket-protocol.md 规范。
    """

    def assert_response_success(
        self,
        response: dict | None,
        test_name: str = "请求",
    ) -> bool:
        """验证响应成功"""
        if response is None:
            pytest.fail(f"{test_name}: 无响应")

        # 验证 protocolVersion
        if response.get("protocolVersion") != "2.0":
            pytest.fail(
                f"{test_name}: protocolVersion 必须是 '2.0', "
                f"实际为 '{response.get('protocolVersion')}'"
            )

        # 验证是否有错误（type="ERROR"）
        if response.get("type") == "ERROR":
            error_data = response.get("data", {})
            error_msg = error_data.get("errorMessage", "未知错误")
            error_code = error_data.get("errorCode", "UNKNOWN")
            pytest.fail(f"{test_name}: [{error_code}] {error_msg}")

        return True

    def assert_ack_response(
        self,
        response: dict | None,
        test_name: str = "请求",
    ) -> bool:
        """验证收到 ACK 确认"""
        if response is None:
            pytest.fail(f"{test_name}: 无响应")

        # 验证 type="ACK"
        if response.get("type") != "ACK":
            pytest.fail(f"{test_name}: 期望 type='ACK', 实际为 '{response.get('type')}'")

        # 验证包含 requestId
        if "requestId" not in response:
            pytest.fail(f"{test_name}: ACK 响应缺少 requestId 字段")

        return True

    def assert_response_data(
        self,
        response: dict,
        expected_type: str,
    ) -> dict:
        """
        验证响应数据类型

        Args:
            response: 响应消息
            expected_type: 期望的 type 字段值

        Returns:
            data 字段内容
        """
        self.assert_response_success(response)

        data = response.get("data")
        if not data:
            pytest.fail("响应缺少 data 字段")

        actual_type = response.get("type")
        if actual_type != expected_type:
            pytest.fail(
                f"响应类型不匹配，期望 type='{expected_type}', 实际为 '{actual_type}'"
            )

        return data


class AsyncTestBase(RealtimeTestMixin, RESTTestMixin):
    """
    异步测试基类

    结合了 REST API 测试和实时数据推送测试功能。

    使用方式：
        class TestMyFeature(AsyncTestBase):
            @pytest.mark.ws
            @pytest.mark.spot
            async def test_kline_subscription(self, ws_connected_client):
                # 订阅
                response = await ws_connected_client.subscribe(["BINANCE:BTCUSDT@KLINE_1"])
                self.assert_response_success(response, "订阅")

                # 监听实时数据
                updates = await ws_connected_client.listen_updates(timeout=5)

                # 验证收到的是实时推送（type="UPDATE"）
                assert len(updates) > 0
                self.assert_kline_update(updates[0], resolution="1")
    """

    pass
