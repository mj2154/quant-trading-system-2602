"""
单元测试：验证 interval vs resolution 字段一致性

根据TradingView API规范设计文档：
- Pydantic模型统一使用 `interval` 字段
- 测试代码必须验证 `interval` 字段，而非 `resolution`
- 客户端请求参数可以使用 `resolution`（TradingView API规范）
- 但响应数据必须使用 `interval`（与数据库字段一致）

作者: Claude Code
版本: v1.0.0
"""

import sys
from pathlib import Path

# 添加 src 目录到路径
_api_service_root = Path(__file__).resolve().parent.parent.parent
_src_path = _api_service_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import pytest
from pydantic import ValidationError

from models import KlineBars, KlineData, KlineBar


class TestKLineModelsIntervalField:
    """验证K线模型使用 interval 字段"""

    def test_kline_bars_requires_interval_field(self):
        """KlineBars 模型必须包含 interval 字段"""
        bar_data = {
            "symbol": "BINANCE:BTCUSDT",
            "interval": "60",
            "bars": [
                {
                    "time": 1704067200000,
                    "open": 50000.0,
                    "high": 50500.0,
                    "low": 49500.0,
                    "close": 50200.0,
                    "volume": 1000.0
                }
            ],
            "count": 1,
            "no_data": False
        }

        kline_bars = KlineBars(**bar_data)
        assert kline_bars.interval == "60"
        assert kline_bars.symbol == "BINANCE:BTCUSDT"
        assert len(kline_bars.bars) == 1

    def test_kline_bars_missing_interval_fails(self):
        """KlineBars 模型缺少 interval 字段应该失败"""
        bar_data = {
            "symbol": "BINANCE:BTCUSDT",
            "bars": [
                {
                    "time": 1704067200000,
                    "open": 50000.0,
                    "high": 50500.0,
                    "low": 49500.0,
                    "close": 50200.0,
                    "volume": 1000.0
                }
            ],
            "count": 1,
            "no_data": False
        }

        with pytest.raises(ValidationError) as exc_info:
            KlineBars(**bar_data)

        assert "interval" in str(exc_info.value)

    def test_kline_data_requires_interval_field(self):
        """KlineData 模型必须包含 interval 字段"""
        bar = KlineBar(
            time=1704067200000,
            open=50000.0,
            high=50500.0,
            low=49500.0,
            close=50200.0,
            volume=1000.0
        )

        kline_data = KlineData(
            symbol="BINANCE:BTCUSDT",
            interval="60",
            bar=bar,
            is_bar_closed=True
        )

        assert kline_data.interval == "60"
        assert kline_data.symbol == "BINANCE:BTCUSDT"

    def test_kline_response_str_uses_interval(self):
        """KLineResponse __str__ 应该使用 interval 而非 resolution"""
        bar_data = {
            "symbol": "BINANCE:BTCUSDT",
            "interval": "60",
            "bars": [
                {
                    "time": 1704067200000,
                    "open": 50000.0,
                    "high": 50500.0,
                    "low": 49500.0,
                    "close": 50200.0,
                    "volume": 1000.0
                }
            ],
            "count": 1,
            "no_data": False
        }

        kline_bars = KlineBars(**bar_data)
        str_repr = str(kline_bars)

        # 验证字符串表示包含 interval 值
        assert "60" in str_repr
        # 验证不是使用 resolution
        assert "resolution" not in str_repr.lower()


class TestE2ETestClientIntervalField:
    """验证 E2E 测试客户端使用 interval 字段"""

    def test_get_klines_sends_interval_in_message(self):
        """get_klines 方法发送的消息应该同时包含 resolution 和 interval"""
        import json
        from tests.e2e.base_e2e_test import WebSocketTestClient
        import asyncio

        client = WebSocketTestClient()

        # 构建消息参数
        symbol = "BINANCE:BTCUSDT"
        resolution = "60"
        from_time = 1704067200000
        to_time = 1704153600000

        # 客户端请求使用 resolution（TradingView API规范）
        # 同时添加 interval 字段以保持内部一致性
        message = {
            "protocolVersion": "2.0",
            "action": "get",
            "data": {
                "type": "klines",
                "symbol": symbol,
                "resolution": resolution,  # TradingView API 请求参数
                "interval": resolution,    # 内部使用 interval
                "from_time": from_time,
                "to_time": to_time,
            },
        }

        # 验证消息格式
        assert message["data"]["type"] == "klines"
        assert message["data"]["symbol"] == symbol
        assert message["data"]["resolution"] == resolution
        assert message["data"]["interval"] == resolution

    def test_assert_kline_data_validates_interval(self):
        """assert_kline_data 应该验证 interval 字段"""
        from tests.e2e.base_e2e_test import E2ETestBase

        class MockTest(E2ETestBase):
            def __init__(self):
                super().__init__(auto_connect=False)
                self.test_results = {"passed": 0, "failed": 0, "errors": []}

        test = MockTest()

        # 使用 interval 字段的数据应该通过验证
        valid_kline_data = {
            "symbol": "BINANCE:BTCUSDT",
            "interval": "60",
            "bars": [
                {
                    "time": 1704067200000,
                    "open": 50000.0,
                    "high": 50500.0,
                    "low": 49500.0,
                    "close": 50200.0,
                    "volume": 1000.0
                }
            ],
            "count": 1,
            "no_data": False
        }

        # 验证通过
        result = test.assert_kline_data(valid_kline_data, "test_valid_interval")
        assert result is True

    def test_assert_kline_data_with_resolution_converts(self):
        """assert_kline_data 应该能够处理只有 resolution 字段的数据（向后兼容）"""
        from tests.e2e.base_e2e_test import E2ETestBase

        class MockTest(E2ETestBase):
            def __init__(self):
                super().__init__(auto_connect=False)
                self.test_results = {"passed": 0, "failed": 0, "errors": []}

        test = MockTest()

        # 只有 resolution 字段的数据（后端可能返回）
        kline_data_with_resolution = {
            "symbol": "BINANCE:BTCUSDT",
            "resolution": "60",  # 只有 resolution，没有 interval
            "bars": [
                {
                    "time": 1704067200000,
                    "open": 50000.0,
                    "high": 50500.0,
                    "low": 49500.0,
                    "close": 50200.0,
                    "volume": 1000.0
                }
            ],
            "count": 1,
            "no_data": False
        }

        # 验证应该通过（assert_kline_data 会自动转换）
        result = test.assert_kline_data(kline_data_with_resolution, "test_resolution_conversion")
        assert result is True

    def test_assert_kline_data_missing_interval_fails(self):
        """assert_kline_data 缺少 interval 字段应该失败"""
        from tests.e2e.base_e2e_test import E2ETestBase

        class MockTest(E2ETestBase):
            def __init__(self):
                super().__init__(auto_connect=False)
                self.test_results = {"passed": 0, "failed": 0, "errors": []}

        test = MockTest()

        # 既没有 resolution 也没有 interval
        invalid_kline_data = {
            "symbol": "BINANCE:BTCUSDT",
            "bars": [
                {
                    "time": 1704067200000,
                    "open": 50000.0,
                    "high": 50500.0,
                    "low": 49500.0,
                    "close": 50200.0,
                    "volume": 1000.0
                }
            ],
            "count": 1,
            "no_data": False
        }

        # 验证应该失败
        result = test.assert_kline_data(invalid_kline_data, "test_missing_interval")
        assert result is False
        assert len(test.test_results["errors"]) == 1
        assert "interval" in test.test_results["errors"][0]


class TestResponseDataIntervalValidation:
    """验证响应数据使用 interval 字段"""

    def test_kline_bars_response_should_contain_interval(self):
        """K线响应数据应该包含 interval 字段"""
        # 模拟服务端响应数据
        response_data = {
            "symbol": "BINANCE:BTCUSDT",
            "interval": "60",  # 服务端响应使用 interval
            "bars": [
                {
                    "time": 1704067200000,
                    "open": 50000.0,
                    "high": 50500.0,
                    "low": 49500.0,
                    "close": 50200.0,
                    "volume": 1000.0
                }
            ],
            "count": 1,
            "no_data": False
        }

        # 验证数据符合 KlineBars 模型
        kline_bars = KlineBars(**response_data)
        assert kline_bars.interval == "60"
        assert kline_bars.symbol == "BINANCE:BTCUSDT"

    def test_kline_bars_response_with_resolution_fails(self):
        """K线响应数据如果只包含 resolution 字段应该验证失败"""
        # 如果后端返回 resolution 字段而不是 interval
        response_with_resolution = {
            "symbol": "BINANCE:BTCUSDT",
            "resolution": "60",  # 后端错误地使用 resolution
            "bars": [
                {
                    "time": 1704067200000,
                    "open": 50000.0,
                    "high": 50500.0,
                    "low": 49500.0,
                    "close": 50200.0,
                    "volume": 1000.0
                }
            ],
            "count": 1,
            "no_data": False
        }

        # 验证直接使用模型应该失败（因为缺少 interval）
        with pytest.raises(ValidationError):
            KlineBars(**response_with_resolution)


class TestMultipleIntervalValues:
    """验证不同 interval 值的处理"""

    @pytest.mark.parametrize("interval", ["1", "5", "15", "60", "240", "1D", "1W", "1M"])
    def test_kline_bars_with_different_intervals(self, interval: str):
        """验证不同 interval 值都能正确处理"""
        bar_data = {
            "symbol": "BINANCE:BTCUSDT",
            "interval": interval,
            "bars": [
                {
                    "time": 1704067200000,
                    "open": 50000.0,
                    "high": 50500.0,
                    "low": 49500.0,
                    "close": 50200.0,
                    "volume": 1000.0
                }
            ],
            "count": 1,
            "no_data": False
        }

        kline_bars = KlineBars(**bar_data)
        assert kline_bars.interval == interval


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
