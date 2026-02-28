"""
数据转换模型测试

测试 camelCase/snake_case 自动转换功能。
使用API服务本地的 base.py 模块。

测试场景：
1. CamelCaseModel: 验证序列化后字段为camelCase
2. SnakeCaseModel: 验证接收camelCase输入后转换为snake_case
3. WebSocket消息: 验证WSRequest/WSResponse的转换
4. 完整流程: 验证从前端请求到后端响应的完整数据流
"""

import pytest


class TestCamelCaseModel:
    """测试 CamelCaseModel 基类"""

    def test_serialize_to_camel_case(self):
        """验证序列化后字段为 camelCase"""
        from src.models.base import CamelCaseModel

        class ResponseModel(CamelCaseModel):
            protocol_version: str
            request_id: str
            task_id: int

        model = ResponseModel(
            protocol_version="2.0",
            request_id="test-123",
            task_id=456
        )

        # 序列化后应使用 camelCase (默认by_alias=True)
        data = model.model_dump()
        assert "requestId" in data
        assert "taskId" in data
        assert "protocolVersion" in data
        # 不应该有 snake_case 字段
        assert "request_id" not in data
        assert "task_id" not in data

    def test_serialize_json(self):
        """验证 JSON 序列化使用 camelCase"""
        from src.models.base import CamelCaseModel

        class ResponseModel(CamelCaseModel):
            protocol_version: str
            error_code: str
            error_message: str

        model = ResponseModel(
            protocol_version="2.0",
            error_code="1001",
            error_message="Test error"
        )

        import json
        json_str = model.model_dump_json()
        parsed = json.loads(json_str)

        assert "protocolVersion" in parsed
        assert "errorCode" in parsed
        assert "errorMessage" in parsed
        assert "protocol_version" not in json_str


class TestSnakeCaseModel:
    """测试 SnakeCaseModel 基类"""

    def test_parse_camel_case_input(self):
        """验证接收 camelCase 输入后转换为 snake_case"""
        from src.models.base import SnakeCaseModel

        class RequestModel(SnakeCaseModel):
            protocol_version: str
            request_id: str
            action: str

        # 传入 camelCase 数据
        data = {
            "protocolVersion": "2.0",
            "requestId": "test-123",
            "action": "get"
        }

        model = RequestModel(**data)

        # 内部字段应为 snake_case
        assert model.protocol_version == "2.0"
        assert model.request_id == "test-123"
        assert model.action == "get"

    def test_parse_mixed_case_input(self):
        """验证同时支持 camelCase 和 snake_case 输入"""
        from src.models.base import SnakeCaseModel

        class RequestModel(SnakeCaseModel):
            protocol_version: str
            request_id: str

        # 使用 snake_case 输入
        data = {
            "protocol_version": "2.0",
            "request_id": "test-456"
        }

        model = RequestModel(**data)

        assert model.protocol_version == "2.0"
        assert model.request_id == "test-456"


class TestWebSocketMessages:
    """测试 WebSocket 消息模型"""

    def test_ws_request_accepts_camel_case(self):
        """验证 WSRequest 接收 camelCase 输入"""
        from src.models.base import SnakeCaseModel

        # 定义 WSRequest
        class WSRequest(SnakeCaseModel):
            protocol_version: str = "2.0"
            action: str
            request_id: str
            timestamp: int = 1700000000000
            data: dict = {}

        # 前端发送 camelCase 请求
        request_data = {
            "protocolVersion": "2.0",
            "action": "get",
            "requestId": "req-001",
            "timestamp": 1700000000000
        }

        request = WSRequest(**request_data)

        # 内部转换为 snake_case
        assert request.protocol_version == "2.0"
        assert request.action == "get"
        assert request.request_id == "req-001"
        assert request.timestamp == 1700000000000

    def test_ws_response_serializes_to_camel_case(self):
        """验证 WSResponse 序列化为 camelCase"""
        from src.models.base import CamelCaseModel

        # 定义 WSResponse
        class WSResponse(CamelCaseModel):
            protocol_version: str = "2.0"
            action: str
            request_id: str | None = None
            data: dict = {}

        response = WSResponse(
            action="success",
            request_id="req-001",
            data={"result": "ok"}
        )

        # 序列化后应为 camelCase
        data = response.model_dump()

        assert "requestId" in data
        assert "protocolVersion" in data
        assert "action" in data
        # 不应该有内部字段名
        assert "request_id" not in data


class TestCompleteFlow:
    """测试完整数据流：前端请求 -> 后端处理 -> 前端响应"""

    def test_frontend_to_backend_flow(self):
        """验证从前端请求到后端响应的完整流程"""
        from src.models.base import SnakeCaseModel, CamelCaseModel

        # 定义消息模型
        class WSRequest(SnakeCaseModel):
            protocol_version: str = "2.0"
            action: str
            request_id: str
            timestamp: int = 1700000000000
            data: dict = {}

        class WSResponse(CamelCaseModel):
            protocol_version: str = "2.0"
            action: str
            request_id: str | None = None
            data: dict = {}

        import json

        # 1. 前端发送 camelCase 请求
        frontend_request = {
            "protocolVersion": "2.0",
            "action": "subscribe",
            "requestId": "flow-test-001",
            "data": {
                "symbol": "BTCUSDT",
                "interval": "1m"
            }
        }

        # 2. 后端接收并转换为 snake_case
        ws_request = WSRequest(**frontend_request)

        assert ws_request.action == "subscribe"
        assert ws_request.request_id == "flow-test-001"
        assert ws_request.data["symbol"] == "BTCUSDT"

        # 3. 后端处理业务逻辑（模拟）
        # 4. 后端返回 camelCase 响应
        ws_response = WSResponse(
            action="success",
            request_id=ws_request.request_id,
            data={
                "subscribed": True,
                "symbol": "BTCUSDT"
            }
        )

        # 5. 序列化响应为 JSON
        response_json = ws_response.model_dump_json()
        parsed = json.loads(response_json)

        # 6. 验证前端收到 camelCase 数据
        assert parsed["action"] == "success"
        assert parsed["requestId"] == "flow-test-001"
        assert parsed["data"]["subscribed"] is True


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_data(self):
        """测试空数据"""
        from src.models.base import SnakeCaseModel

        class TestSnake(SnakeCaseModel):
            field_a: str = ""

        model = TestSnake(fieldA="")
        assert model.field_a == ""

    def test_none_values(self):
        """测试 None 值"""
        from src.models.base import CamelCaseModel

        class TestModel(CamelCaseModel):
            optional_field: str | None = None

        model = TestModel(optional_field=None)
        data = model.model_dump()
        assert "optionalField" in data

    def test_numeric_values(self):
        """测试数值类型"""
        from src.models.base import SnakeCaseModel

        class TestModel(SnakeCaseModel):
            price_change: float
            quantity: int

        model = TestModel(priceChange=100.5, quantity=10)
        assert model.price_change == 100.5
        assert model.quantity == 10

    def test_nested_objects(self):
        """测试嵌套对象"""
        from src.models.base import CamelCaseModel
        from typing import Any

        class TestModel(CamelCaseModel):
            data: dict[str, Any]

        model = TestModel(data={"nestedField": "value"})
        dumped = model.model_dump()

        assert dumped["data"]["nestedField"] == "value"
