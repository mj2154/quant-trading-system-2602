"""
测试 type 字段位置验证

根据TradingView API规范设计文档：
- type 字段必须位于 data 内部
- success 和 error action 必须有 data 字段且包含 type
- update action 的 type 也在 data 中
- get/subscribe/unsubscribe 是请求，不需要验证 type

用法: python tests/e2e/test_type_field_location.py
"""

import sys
from pathlib import Path

# 计算 api-service 根目录
_api_service_root = Path(__file__).resolve().parent.parent.parent
_src_path = _api_service_root / "src"

for p in [str(_src_path)]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import unittest
import importlib.util


class TestTypeFieldLocation(unittest.TestCase):
    """测试 type 字段位置验证"""

    def setUp(self):
        """导入被测试的方法"""
        # 动态导入以避免路径问题
        spec = importlib.util.spec_from_file_location(
            "base_e2e_test",
            _api_service_root / "tests" / "e2e" / "base_e2e_test.py"
        )
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

        # 创建测试基类实例以访问方法
        self.test_base = self.module.E2ETestBase(auto_connect=False)
        # 初始化test_results以避免KeyError
        self.test_base.test_results = {"passed": 0, "failed": 0, "errors": []}

    def test_type_in_data_for_success(self):
        """验证 success 响应的 type 在 data 内部"""
        correct_message = {
            "protocolVersion": "2.0",
            "action": "success",
            "requestId": "test_123",
            "timestamp": 1234567890,
            "data": {
                "type": "klines",
                "bars": []
            }
        }
        result = self.test_base.assert_message_format(correct_message, "success with type in data")
        self.assertTrue(result)

    def test_type_missing_in_data_for_success(self):
        """验证 success 响应缺少 data.type 会失败"""
        wrong_message = {
            "protocolVersion": "2.0",
            "action": "success",
            "requestId": "test_123",
            "timestamp": 1234567890,
            "data": {
                "bars": []
            }
        }
        result = self.test_base.assert_message_format(wrong_message, "success without type in data")
        self.assertFalse(result)

    def test_type_in_data_for_error(self):
        """验证 error 响应的 type 在 data 内部"""
        correct_message = {
            "protocolVersion": "2.0",
            "action": "error",
            "requestId": "test_123",
            "timestamp": 1234567890,
            "data": {
                "type": "error",
                "errorCode": "INVALID_SYMBOL",
                "errorMessage": "Invalid symbol"
            }
        }
        result = self.test_base.assert_message_format(correct_message, "error with type in data")
        self.assertTrue(result)

    def test_type_missing_in_data_for_error(self):
        """验证 error 响应缺少 data.type 会失败"""
        wrong_message = {
            "protocolVersion": "2.0",
            "action": "error",
            "requestId": "test_123",
            "timestamp": 1234567890,
            "data": {
                "errorCode": "INVALID_SYMBOL",
                "errorMessage": "Invalid symbol"
            }
        }
        result = self.test_base.assert_message_format(wrong_message, "error without type in data")
        self.assertFalse(result)

    def test_type_in_data_for_update(self):
        """验证 update 消息的 type 在 data 内部"""
        correct_message = {
            "protocolVersion": "2.0",
            "action": "update",
            "timestamp": 1234567890,
            "data": {
                "type": "klines",
                "subscriptionKey": "BINANCE:BTCUSDT@KLINE_1",
                "bars": [{"time": 1234567890, "open": 50000, "high": 50100, "low": 49900, "close": 50050, "volume": 100}]
            }
        }
        result = self.test_base.assert_message_format(correct_message, "update with type in data")
        self.assertTrue(result)

    def test_type_missing_in_data_for_update(self):
        """验证 update 消息缺少 data.type 会失败"""
        wrong_message = {
            "protocolVersion": "2.0",
            "action": "update",
            "timestamp": 1234567890,
            "data": {
                "subscriptionKey": "BINANCE:BTCUSDT@KLINE_1",
                "bars": [{"time": 1234567890, "open": 50000, "high": 50100, "low": 49900, "close": 50050, "volume": 100}]
            }
        }
        result = self.test_base.assert_message_format(wrong_message, "update without type in data")
        self.assertFalse(result)

    def test_no_type_validation_for_get_request(self):
        """验证 get 请求不强制验证 type 字段"""
        message = {
            "protocolVersion": "2.0",
            "action": "get",
            "requestId": "test_123",
            "timestamp": 1234567890,
            "data": {
                "type": "klines",
                "symbol": "BINANCE:BTCUSDT",
                "interval": "60",
                "from_time": 1234567890,
                "to_time": 1234567899
            }
        }
        result = self.test_base.assert_message_format(message, "get request")
        self.assertTrue(result)

    def test_no_type_validation_for_subscribe_request(self):
        """验证 subscribe 请求不强制验证 type 字段"""
        message = {
            "protocolVersion": "2.0",
            "action": "subscribe",
            "requestId": "test_123",
            "timestamp": 1234567890,
            "data": {
                "subscriptions": ["BINANCE:BTCUSDT@KLINE_1"]
            }
        }
        result = self.test_base.assert_message_format(message, "subscribe request")
        self.assertTrue(result)

    def test_no_type_validation_for_unsubscribe_request(self):
        """验证 unsubscribe 请求不强制验证 type 字段"""
        message = {
            "protocolVersion": "2.0",
            "action": "unsubscribe",
            "requestId": "test_123",
            "timestamp": 1234567890,
            "data": {
                "subscriptions": ["BINANCE:BTCUSDT@KLINE_1"]
            }
        }
        result = self.test_base.assert_message_format(message, "unsubscribe request")
        self.assertTrue(result)

    def test_data_missing_for_success(self):
        """验证 success 响应缺少 data 字段会失败"""
        wrong_message = {
            "protocolVersion": "2.0",
            "action": "success",
            "requestId": "test_123",
            "timestamp": 1234567890
        }
        result = self.test_base.assert_message_format(wrong_message, "success without data")
        self.assertFalse(result)

    def test_data_missing_for_error(self):
        """验证 error 响应缺少 data 字段会失败"""
        wrong_message = {
            "protocolVersion": "2.0",
            "action": "error",
            "requestId": "test_123",
            "timestamp": 1234567890
        }
        result = self.test_base.assert_message_format(wrong_message, "error without data")
        self.assertFalse(result)

    def test_data_missing_for_update(self):
        """验证 update 消息缺少 data 字段会失败"""
        wrong_message = {
            "protocolVersion": "2.0",
            "action": "update",
            "timestamp": 1234567890
        }
        result = self.test_base.assert_message_format(wrong_message, "update without data")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
