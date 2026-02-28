"""
期货WebSocket测试模块

测试用例:
- test_perpetual_kline: 订阅永续合约K线
- test_futures_quotes: 订阅期货报价
- test_multi_futures: 多期货订阅管理

运行方式:
    # 运行单个测试
    pytest tests/e2e/futures/ws/test_perpetual_kline_sub.py -v

    # 运行所有期货WebSocket测试
    pytest tests/e2e/futures/ws/ -v

    # 使用运行器
    python tests/e2e/runners/futures_ws_runner.py
"""

from .test_perpetual_kline_sub import TestPerpetualKlineSubscription
from .test_futures_quotes_sub import TestFuturesQuotesSubscription
from .test_multi_futures_sub import TestMultiFuturesSubscription

__all__ = [
    "TestPerpetualKlineSubscription",
    "TestFuturesQuotesSubscription",
    "TestMultiFuturesSubscription",
]
