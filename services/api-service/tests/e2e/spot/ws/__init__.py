"""
现货WebSocket测试模块

测试用例:
- test_kline_subscription: 订阅K线实时数据
- test_quotes_subscription: 订阅现货报价实时数据
- test_quotes_multi_symbol: 订阅多个现货报价实时数据
- test_multi_subscription: 多订阅管理（K线+现货报价）

运行方式:
    # 运行单个测试
    pytest tests/e2e/spot/ws/test_kline_sub.py -v

    # 运行所有现货WebSocket测试
    pytest tests/e2e/spot/ws/ -v

    # 使用运行器
    python tests/e2e/runners/spot_ws_runner.py
"""

from .test_kline_sub import TestSpotKlineSubscription
from .test_quotes_sub import TestSpotQuotesSubscription
from .test_quotes_multi import TestSpotQuotesMultiSymbol
from .test_multi_sub import TestSpotMultiSubscription

__all__ = [
    "TestSpotKlineSubscription",
    "TestSpotQuotesSubscription",
    "TestSpotQuotesMultiSymbol",
    "TestSpotMultiSubscription",
]
