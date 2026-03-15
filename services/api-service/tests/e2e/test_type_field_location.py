"""
测试 type 字段位置验证

根据 WebSocket API 协议规范 (07-websocket-protocol.md)：
- 顶层 type：消息类型（如 CONFIG_DATA, KLINES_DATA, ERROR, ACK）
- data 内部 type：数据类型（如 search_symbols, klines, quotes）
- 请求消息使用 action 字段（如 success, error, update）
- 响应消息使用 type 字段（在顶层）

设计文档示例：
```json
{
    "protocolVersion": "2.0",
    "type": "CONFIG_DATA",    // 顶层：消息类型
    "requestId": "...",
    "timestamp": ...,
    "data": {
        "type": "search_symbols",   // data内部：数据类型
        "symbols": [...]
    }
}
```

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

    def test_type_in_top_level_for_success(self):
        """验证 success 响应的 type 在顶层（设计文档 v16.2.2 规范）"""
        # 根据设计文档：type 在顶层，data.type 是数据类型
        correct_message = {
            "protocolVersion": "2.0",
            "type": "KLINES_DATA",  # 顶层：消息类型
            "requestId": "test_123",
            "timestamp": 1234567890,
            "data": {
                "type": "klines",   # data内部：数据类型
                "bars": []
            }
        }
        result = self.test_base.assert_message_format(correct_message, "success with type in top level")
        self.assertTrue(result)

    def test_type_missing_in_top_level_for_success(self):
        """验证 success 响应缺少顶层 type 会失败"""
        wrong_message = {
            "protocolVersion": "2.0",
            "requestId": "test_123",
            "timestamp": 1234567890,
            "data": {
                "type": "klines",
                "bars": []
            }
        }
        result = self.test_base.assert_message_format(wrong_message, "success without type in top level")
        self.assertFalse(result)

    def test_type_in_data_for_error(self):
        """验证 error 响应的 type 在顶层（与 success 一致）"""
        correct_message = {
            "protocolVersion": "2.0",
            "type": "ERROR",  # 顶层：消息类型
            "requestId": "test_123",
            "timestamp": 1234567890,
            "data": {
                "errorCode": "INVALID_PARAMETER",  # data内部：具体错误信息
                "errorMessage": "Invalid parameter"
            }
        }
        result = self.test_base.assert_message_format(correct_message, "error with type in top level")
        self.assertTrue(result)

    def test_type_in_data_for_update(self):
        """验证 update 消息的 type 在顶层（设计文档 v16.2.2 规范）"""
        correct_message = {
            "protocolVersion": "2.0",
            "type": "UPDATE",  # 顶层：消息类型
            "data": {
                "content": {  # data内部：推送内容
                    "type": "kline",
                    "symbol": "BINANCE:BTCUSDT"
                }
            }
        }
        result = self.test_base.assert_message_format(correct_message, "update with type in top level")
        self.assertTrue(result)

    def test_ack_type_in_top_level(self):
        """验证 ACK 响应的 type 在顶层"""
        correct_message = {
            "protocolVersion": "2.0",
            "type": "ACK",  # 顶层：消息类型
            "requestId": "test_123",
            "timestamp": 1234567890,
            "data": {}  # ACK 的 data 为空对象
        }
        result = self.test_base.assert_message_format(correct_message, "ACK with type in top level")
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
