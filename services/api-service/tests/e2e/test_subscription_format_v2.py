"""
v2.0订阅格式验证测试

验证assert_subscription_format()方法是否正确支持v2.0订阅键数组格式。

v2.0订阅键格式: {EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{INTERVAL}]
支持的数据类型: KLINE, QUOTES, TRADE (全大写)

用法: python tests/e2e/test_subscription_format_v2.py
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
import re


class TestSubscriptionFormatV2(unittest.TestCase):
    """测试v2.0订阅键数组格式验证"""

    def setUp(self):
        """导入被测试的方法"""
        # 动态导入以避免路径问题
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "base_e2e_test",
            _api_service_root / "tests" / "e2e" / "base_e2e_test.py"
        )
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

        # 创建测试基类实例以访问方法
        self.test_base = self.module.E2ETestBase()
        # 初始化test_results以避免KeyError
        self.test_base.test_results = {"passed": 0, "failed": 0, "errors": []}

    def test_valid_kline_subscription_v2(self):
        """测试有效的KLINE订阅v2.0格式"""
        subscriptions = ["BINANCE:BTCUSDT@KLINE_1"]
        result = self.test_base.assert_subscription_format(subscriptions, "KLINE订阅")
        self.assertTrue(result, "有效的KLINE订阅应通过验证")

    def test_valid_kline_multiple_resolutions(self):
        """测试多个K线周期的v2.0订阅"""
        subscriptions = [
            "BINANCE:BTCUSDT@KLINE_1",
            "BINANCE:BTCUSDT@KLINE_60",
            "BINANCE:BTCUSDT@KLINE_D",
        ]
        result = self.test_base.assert_subscription_format(subscriptions, "多周期KLINE订阅")
        self.assertTrue(result, "多周期KLINE订阅应通过验证")

    def test_valid_quotes_subscription_v2(self):
        """测试有效的QUOTES订阅v2.0格式"""
        subscriptions = ["BINANCE:BTCUSDT@QUOTES"]
        result = self.test_base.assert_subscription_format(subscriptions, "QUOTES订阅")
        self.assertTrue(result, "有效的QUOTES订阅应通过验证")

    def test_valid_trade_subscription_v2(self):
        """测试有效的TRADE订阅v2.0格式"""
        subscriptions = ["BINANCE:BTCUSDT@TRADE"]
        result = self.test_base.assert_subscription_format(subscriptions, "TRADE订阅")
        self.assertTrue(result, "有效的TRADE订阅应通过验证")

    def test_valid_perpetual_future_subscription(self):
        """测试永续合约订阅格式"""
        subscriptions = ["BINANCE:BTCUSDT.PERP@KLINE_1"]
        result = self.test_base.assert_subscription_format(subscriptions, "永续合约订阅")
        self.assertTrue(result, "永续合约订阅应通过验证")

    def test_valid_multiple_subscriptions(self):
        """测试多个不同类型的订阅"""
        subscriptions = [
            "BINANCE:BTCUSDT@KLINE_1",
            "BINANCE:BTCUSDT@QUOTES",
            "BINANCE:BTCUSDT@TRADE",
            "BINANCE:ETHUSDT@KLINE_60",
        ]
        result = self.test_base.assert_subscription_format(subscriptions, "多类型订阅")
        self.assertTrue(result, "多类型订阅应通过验证")

    def test_valid_with_product_suffix(self):
        """测试带产品后缀的订阅格式"""
        subscriptions = [
            "BINANCE:BTCUSDT.PERP@KLINE_1",     # 永续合约
            "BINANCE:BTCUSDT.210625@KLINE_1",   # 交割合约
        ]
        result = self.test_base.assert_subscription_format(subscriptions, "产品后缀订阅")
        self.assertTrue(result, "带产品后缀的订阅应通过验证")

    def test_invalid_subscription_not_array(self):
        """测试非数组格式应失败"""
        # v1.0字典格式 - 应该失败
        subscriptions = {"kline": [{"symbol": "BINANCE:BTCUSDT", "resolution": "1"}]}
        result = self.test_base.assert_subscription_format(subscriptions, "字典格式测试")
        self.assertFalse(result, "字典格式应被拒绝")

    def test_invalid_subscription_type(self):
        """测试无效的订阅数据类型应失败"""
        subscriptions = ["BINANCE:BTCUSDT@INVALID"]
        result = self.test_base.assert_subscription_format(subscriptions, "无效数据类型测试")
        self.assertFalse(result, "无效数据类型应被拒绝")

    def test_invalid_subscription_key_format(self):
        """测试无效的订阅键格式应失败"""
        subscriptions = ["INVALID_FORMAT"]  # 缺少必需的@符号
        result = self.test_base.assert_subscription_format(subscriptions, "格式错误测试")
        self.assertFalse(result, "格式错误的订阅键应被拒绝")

    def test_invalid_empty_string(self):
        """测试空字符串订阅键应失败"""
        subscriptions = [""]
        result = self.test_base.assert_subscription_format(subscriptions, "空字符串测试")
        self.assertFalse(result, "空字符串订阅键应被拒绝")

    def test_invalid_missing_exchange(self):
        """测试缺少交易所的订阅键应失败"""
        subscriptions = ["BTCUSDT@KLINE_1"]  # 缺少EXCHANGE:
        result = self.test_base.assert_subscription_format(subscriptions, "缺少交易所测试")
        self.assertFalse(result, "缺少交易所的订阅键应被拒绝")

    def test_invalid_missing_symbol(self):
        """测试缺少交易对的订阅键应失败"""
        subscriptions = ["BINANCE:@KLINE_1"]  # 缺少SYMBOL
        result = self.test_base.assert_subscription_format(subscriptions, "缺少交易对测试")
        self.assertFalse(result, "缺少交易对的订阅键应被拒绝")

    def test_empty_list(self):
        """测试空列表应失败"""
        subscriptions = []
        result = self.test_base.assert_subscription_format(subscriptions, "空列表测试")
        self.assertFalse(result, "空列表订阅应被拒绝")


class TestSubscriptionKeyRegex(unittest.TestCase):
    """测试v2.0订阅键正则表达式"""

    def setUp(self):
        """设置正则表达式"""
        # v2.0订阅键格式: {EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{INTERVAL}]
        # 数据类型: KLINE, QUOTES, TRADE (全大写)
        # 分辨率: 数字(1, 60, 1440) 或 字母(W, D, W, M, Y)
        self.pattern = re.compile(
            r"^[A-Z]+:[A-Z0-9]+(\.[A-Z0-9]+)?@(KLINE|QUOTES|TRADE)(_[0-9A-Z]+)?$"
        )

    def test_valid_kline_pattern(self):
        """测试有效的KLINE模式匹配"""
        valid_keys = [
            "BINANCE:BTCUSDT@KLINE_1",
            "BINANCE:BTCUSDT@KLINE_60",
            "BINANCE:BTCUSDT@KLINE_D",
            "BINANCE:BTCUSDT.PERP@KLINE_1",
        ]
        for key in valid_keys:
            with self.subTest(key=key):
                self.assertIsNotNone(
                    self.pattern.match(key),
                    f"'{key}' 应该匹配v2.0格式"
                )

    def test_valid_quotes_pattern(self):
        """测试有效的QUOTES模式匹配"""
        valid_keys = [
            "BINANCE:BTCUSDT@QUOTES",
            "BINANCE:ETHUSDT@QUOTES",
        ]
        for key in valid_keys:
            with self.subTest(key=key):
                self.assertIsNotNone(
                    self.pattern.match(key),
                    f"'{key}' 应该匹配v2.0格式"
                )

    def test_valid_trade_pattern(self):
        """测试有效的TRADE模式匹配"""
        valid_keys = [
            "BINANCE:BTCUSDT@TRADE",
            "BINANCE:ETHUSDT@TRADE",
        ]
        for key in valid_keys:
            with self.subTest(key=key):
                self.assertIsNotNone(
                    self.pattern.match(key),
                    f"'{key}' 应该匹配v2.0格式"
                )

    def test_invalid_patterns(self):
        """测试无效模式不应匹配"""
        invalid_keys = [
            "INVALID_FORMAT",      # 缺少@
            "BINANCE:BTCUSDT",     # 缺少数据类型
            "BINANCE:BTCUSDT@",    # 空数据类型
            "BINANCE:BTCUSDT@TICKER",  # 无效数据类型
            "BINANCE:BTCUSDT@kline_1", # 小写kline
            ":BTCUSDT@KLINE_1",    # 缺少交易所
            "BINANCE:@KLINE_1",    # 缺少交易对
            "BINANCE:BTCUSDT@KLINE_",  # 空分辨率
        ]
        for key in invalid_keys:
            with self.subTest(key=key):
                self.assertIsNone(
                    self.pattern.match(key),
                    f"'{key}' 不应该匹配v2.0格式"
                )


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
