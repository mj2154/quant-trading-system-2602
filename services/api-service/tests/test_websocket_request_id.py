"""
测试 WebSocketMessage 模型的 request_id 字段验证

根据 TradingView API 规范，requestId 是所有请求消息的必需字段（除了 update 消息）。

遵循 TDD 流程：
1. 编写测试（RED - 应该失败）
2. 运行测试验证失败
3. 修改代码（GREEN - 通过）
4. 验证测试通过
"""

import pytest
from pydantic import ValidationError

from src.models.websocket import (
    WebSocketMessage,
    MessageRequest,
    MessageUpdate,
    MessageResponseBase,
    MessageSuccess,
)


class TestWebSocketMessageRequestId:
    """测试 WebSocketMessage 模型的 request_id 字段验证"""

    def test_request_message_requires_request_id(self):
        """
        测试请求消息必须包含 request_id

        根据 TradingView API 规范：
        - requestId: 客户端生成，用于追踪整个请求-响应流程
        - 所有GET、订阅、取消订阅请求都必须包含requestId
        """
        # 缺少 request_id 应该抛出验证错误
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessage(
                action="get",
                timestamp=1234567890,
                data={"type": "klines"}
            )

        # 验证错误信息包含 request_id 相关的提示
        assert "request_id" in str(exc_info.value) or "requestId" in str(exc_info.value)

    def test_request_message_with_request_id_valid(self):
        """测试包含 request_id 的有效请求消息"""
        msg = WebSocketMessage(
            action="get",
            request_id="req-12345",
            timestamp=1234567890,
            data={"type": "klines"}
        )
        assert msg.request_id == "req-12345"
        assert msg.action == "get"

    def test_request_message_accepts_empty_string(self):
        """测试空字符串 request_id 通过验证（Pydantic 视为有效 str）

        注意：Pydantic 将空字符串视为有效的 str 类型。
        requestId 只需存在（非 Optional），不要求非空。
        业务逻辑层的非空验证应在其他地方实现。
        """
        # 空字符串应该能通过 Pydantic 验证
        msg = WebSocketMessage(
            action="get",
            request_id="",
            timestamp=1234567890,
            data={"type": "klines"}
        )
        assert msg.request_id == ""

    def test_subscribe_request_requires_request_id(self):
        """测试订阅请求必须包含 request_id"""
        with pytest.raises(ValidationError):
            WebSocketMessage(
                action="subscribe",
                timestamp=1234567890,
                data={"subscriptions": ["btcusdt@kline_1m"]}
            )

    def test_unsubscribe_request_requires_request_id(self):
        """测试取消订阅请求必须包含 request_id"""
        with pytest.raises(ValidationError):
            WebSocketMessage(
                action="unsubscribe",
                timestamp=1234567890,
                data={"subscriptions": ["btcusdt@kline_1m"]}
            )


class TestMessageRequestRequestId:
    """测试 MessageRequest 类的 request_id 字段验证"""

    def test_message_request_requires_request_id(self):
        """测试 MessageRequest 必须包含 request_id"""
        with pytest.raises(ValidationError):
            MessageRequest(
                action="get",
                timestamp=1234567890,
                data={"type": "server_time"}
            )

    def test_message_request_with_request_id_valid(self):
        """测试包含 request_id 的有效 MessageRequest"""
        request = MessageRequest(
            request_id="request-001",
            timestamp=1234567890,
            data={"type": "server_time"}
        )
        assert request.request_id == "request-001"
        assert request.action == "get"


class TestMessageUpdateRequestId:
    """测试 MessageUpdate 模型的 request_id 字段

    注意：MessageUpdate 是服务器主动推送的消息，不应该包含 requestId。
    当前 MessageUpdate 是独立模型，不继承 WebSocketMessage，
    所以不受 request_id 必需字段的影响。
    """

    def test_message_update_without_request_id(self):
        """测试 MessageUpdate 不需要 request_id（服务器主动推送）"""
        update = MessageUpdate(
            timestamp=1234567890,
            data={
                "subscriptionKey": "btcusdt@kline_1m",
                "payload": {"open": 50000, "high": 50100, "low": 49900, "close": 50050}
            }
        )
        assert update.action == "update"
        assert update.timestamp == 1234567890
        assert "subscriptionKey" in update.data

    def test_message_update_not_inherits_websocket_message(self):
        """验证 MessageUpdate 是独立模型，不继承 WebSocketMessage"""
        # MessageUpdate 不应该有 request_id 字段
        update = MessageUpdate(timestamp=1234567890, data={"test": "data"})
        # 检查是否存在 request_id 属性
        has_request_id = hasattr(update, 'request_id')
        assert not has_request_id or getattr(update, 'request_id', None) is None


class TestMessageResponseBaseRequestId:
    """测试 MessageResponseBase 的 request_id 字段验证"""

    def test_response_requires_request_id(self):
        """测试响应消息必须包含 request_id"""
        with pytest.raises(ValidationError):
            MessageResponseBase(
                action="success",
                timestamp=1234567890,
                data={"type": "server_time", "value": 1234567890}
            )

    def test_response_with_request_id_valid(self):
        """测试包含 request_id 的有效响应"""
        response = MessageResponseBase(
            action="success",
            request_id="req-123",
            timestamp=1234567890,
            data={"type": "server_time", "value": 1234567890}
        )
        assert response.request_id == "req-123"

    def test_success_response_requires_request_id(self):
        """测试成功响应必须包含 request_id"""
        with pytest.raises(ValidationError):
            MessageSuccess(
                timestamp=1234567890,
                data={"type": "server_time"}
            )


class TestRequestIdAsAlias:
    """测试 request_id 字段的 alias 为 requestId"""

    def test_request_id_alias_works(self):
        """测试使用 camelCase alias 也能正确解析"""
        # 使用 requestId (camelCase) 作为字段名
        msg = WebSocketMessage(
            action="get",
            requestId="alias-test-123",
            timestamp=1234567890,
            data={"type": "klines"}
        )
        assert msg.request_id == "alias-test-123"

    def test_request_id_alias_with_validation_error(self):
        """测试缺少 requestId 时验证失败"""
        with pytest.raises(ValidationError):
            WebSocketMessage(
                action="get",
                timestamp=1234567890,
                data={}
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
