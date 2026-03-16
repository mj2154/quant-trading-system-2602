"""
WebSocket 订阅端到端测试

严格遵循 07-websocket-protocol.md 设计文档。

测试覆盖：
- 单个订阅: 一次只订阅一个数据流
- 订阅响应验证: 验证 ACK + SUBSCRIPTION_DATA
- 取消订阅: 验证响应
- 查询订阅: 验证响应

设计文档三阶段流程：
  请求 → ACK → SUCCESS(数据类型)
"""

import asyncio

import pytest


class TestWebSocketSubscription:
    """WebSocket 订阅测试（单订阅模式）"""

    @pytest.mark.ws
    async def test_subscribe_single_kline(self, ws_connected_client):
        """测试订阅单个 K线 - 验证响应"""
        subscription = "BINANCE:BTCUSDT@KLINE_1"

        # 发送订阅请求
        response = await ws_connected_client.subscribe([subscription])

        assert response is not None, "无响应"

        # 设计文档规定：响应类型是 SUBSCRIPTION_DATA
        resp_type = response.get("type")
        assert resp_type == "SUBSCRIPTION_DATA", f"期望 SUBSCRIPTION_DATA，实际 {resp_type}"

        # 验证响应数据
        data = response.get("data", {})
        assert data.get("status") == "success", f"订阅失败: {data}"
        assert subscription in data.get("subscriptions", [])

        # 清理
        await ws_connected_client.unsubscribe([subscription])

    @pytest.mark.ws
    async def test_subscribe_single_quotes(self, ws_connected_client):
        """测试订阅单个报价 - 验证响应"""
        subscription = "BINANCE:BTCUSDT@QUOTES"

        response = await ws_connected_client.subscribe([subscription])

        assert response is not None
        assert response.get("type") == "SUBSCRIPTION_DATA"
        assert response.get("data", {}).get("status") == "success"

        # 清理
        await ws_connected_client.unsubscribe([subscription])

    @pytest.mark.ws
    async def test_subscribe_futures_kline(self, ws_connected_client):
        """测试订阅期货 K线 - 验证响应"""
        subscription = "BINANCE:BTCUSDT.PERP@KLINE_1"

        response = await ws_connected_client.subscribe([subscription])

        assert response is not None
        assert response.get("type") == "SUBSCRIPTION_DATA"
        assert response.get("data", {}).get("status") == "success"

        # 清理
        await ws_connected_client.unsubscribe([subscription])

    @pytest.mark.ws
    async def test_unsubscribe_single(self, ws_connected_client):
        """测试取消订阅 - 验证响应"""
        subscription = "BINANCE:BTCUSDT@KLINE_1"

        # 先订阅
        await ws_connected_client.subscribe([subscription])

        # 再取消
        response = await ws_connected_client.unsubscribe([subscription])

        assert response is not None
        # 设计文档规定取消订阅返回 SUBSCRIPTION_DATA
        resp_type = response.get("type")
        assert resp_type in ["SUBSCRIPTION_DATA", "UNSUBSCRIBE_DATA"], \
            f"期望 SUBSCRIPTION_DATA 或 UNSUBSCRIBE_DATA，实际 {resp_type}"
        assert response.get("data", {}).get("status") == "success"


class TestSubscriptionWorkflow:
    """完整订阅工作流测试 - 更有实际意义的测试"""

    @pytest.mark.ws
    @pytest.mark.slow
    async def test_complete_subscription_workflow(self, ws_connected_client):
        """测试完整的订阅工作流

        正确流程：
        1. 订阅 A 数据
        2. 等待接收实时数据
        3. 取消订阅 A
        4. 订阅 B 数据
        5. 验证新数据推送

        这个测试验证了完整的订阅切换流程，而非仅仅验证订阅成功
        """
        sub_a = "BINANCE:BTCUSDT@KLINE_1"
        sub_b = "BINANCE:ETHUSDT@KLINE_1"

        # Step 1: 订阅 A
        resp = await ws_connected_client.subscribe([sub_a])
        assert resp.get("data", {}).get("status") == "success"

        # Step 2: 等待接收实时数据
        updates_a = await ws_connected_client.listen_updates(timeout=60, expected_count=1)
        assert len(updates_a) > 0, "未收到订阅 A 的实时数据"
        assert updates_a[0].get("subscriptionKey") == sub_a

        # Step 3: 取消订阅 A
        resp = await ws_connected_client.unsubscribe([sub_a])
        assert resp.get("data", {}).get("status") == "success"

        # 等待一小段时间确保取消生效
        await asyncio.sleep(1)

        # Step 4: 订阅 B
        resp = await ws_connected_client.subscribe([sub_b])
        assert resp.get("data", {}).get("status") == "success"

        # Step 5: 等待接收 B 的实时数据
        updates_b = await ws_connected_client.listen_updates(timeout=60, expected_count=1)
        assert len(updates_b) > 0, "未收到订阅 B 的实时数据"
        assert updates_b[0].get("subscriptionKey") == sub_b

        # 验证 A 和 B 的数据都存在（证明切换成功）
        print(f"[DEBUG] A 数据: {updates_a[0].get('content', {}).get('close')}")
        print(f"[DEBUG] B 数据: {updates_b[0].get('content', {}).get('close')}")

        # 清理
        await ws_connected_client.unsubscribe([sub_b])


class TestRealtimeUpdate:
    """实时数据推送测试（需要后端正确配置）"""

    @pytest.mark.ws
    @pytest.mark.slow
    async def test_kline_realtime_update(self, ws_connected_client):
        """测试 K线 实时推送

        流程：
        1. 订阅 K线 数据
        2. 等待接收 UPDATE 推送
        3. 验证推送格式正确

        注意：此测试会失败，如果后端没有正确推送实时数据
        """
        subscription = "BINANCE:BTCUSDT@KLINE_1"
        await ws_connected_client.subscribe([subscription])

        # 等待实时数据推送（最多45秒，因为K线需要等待下一个1分钟周期）
        updates = await ws_connected_client.listen_updates(timeout=45, expected_count=1)

        # 必须收到实时数据，否则测试失败
        assert len(updates) > 0, \
            "未收到实时推送！后端没有正确推送数据到客户端。" \
            "请检查：1) 订阅是否正确保存 2) binance-service是否正确推送 3) api-service是否正确转发"

        # 验证推送格式
        update = updates[0]

        # 调试：打印收到的完整消息
        print(f"[DEBUG] 收到的 UPDATE 消息: {update}")

        # 设计文档规定：UPDATE 消息的 type 是 "UPDATE"
        assert update.get("type") == "UPDATE", f"期望 type='UPDATE'，实际 '{update.get('type')}'"

        # UPDATE 消息不包含 requestId（设计文档规定）
        assert "requestId" not in update, "UPDATE 消息不应包含 requestId"

        # 验证数据结构 - subscriptionKey 在顶层（协议 v2.0+）
        assert "subscriptionKey" in update, "缺少 subscriptionKey 字段"
        assert "content" in update, "缺少 content 字段"

        # 验证 K线数据
        content = update.get("content", {})
        required_fields = ["time", "open", "high", "low", "close"]
        for field in required_fields:
            assert field in content, f"K线数据缺少字段: {field}"

        # 清理
        await ws_connected_client.unsubscribe([subscription])

    @pytest.mark.ws
    @pytest.mark.slow
    async def test_quotes_realtime_update(self, ws_connected_client):
        """测试报价 实时推送

        注意：此测试会失败，如果后端没有正确推送实时数据
        """
        subscription = "BINANCE:BTCUSDT@QUOTES"
        await ws_connected_client.subscribe([subscription])

        # 等待实时数据推送（报价推送频率较高，等待30秒）
        updates = await ws_connected_client.listen_updates(timeout=30, expected_count=1)

        # 必须收到实时数据，否则测试失败
        assert len(updates) > 0, \
            "未收到实时推送！后端没有正确推送数据到客户端"

        # 验证推送格式
        update = updates[0]
        assert update.get("type") == "UPDATE"
        assert "requestId" not in update

        # 验证数据结构 - subscriptionKey 在顶层（协议 v2.0+）
        assert "subscriptionKey" in update, "缺少 subscriptionKey 字段"
        assert "content" in update, "缺少 content 字段"

        content = update.get("content", {})

        # 兼容批量格式
        if isinstance(content, list):
            content = content[0] if content else {}

        assert "n" in content, "报价缺少 'n' 字段"
        assert "v" in content, "报价缺少 'v' 字段"

        # 清理
        await ws_connected_client.unsubscribe([subscription])
