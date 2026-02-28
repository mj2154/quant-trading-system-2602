"""
期货REST API测试模块

测试用例:
- test_perpetual_klines: 永续合约K线数据
- test_continuous_klines: 连续合约K线数据
- test_futures_quotes: 期货报价数据
- test_multi_resolution: 多分辨率期货K线
- test_symbol_validation: 期货交易对格式验证
- test_price_logic: 期货价格逻辑验证
- test_perpetual_spot_comparison: 永续合约与现货价格对比

运行方式:
    # 运行单个测试
    pytest tests/e2e/futures/rest/test_perpetual_klines.py -v

    # 运行所有期货REST测试
    pytest tests/e2e/futures/rest/ -v

    # 使用运行器
    python tests/e2e/runners/futures_rest_runner.py
"""

from .rest.test_perpetual_klines import TestPerpetualKlines
from .rest.test_continuous_klines import TestContinuousKlines
from .rest.test_futures_quotes import TestFuturesQuotes
from .rest.test_multi_resolution import TestFuturesMultiResolution
from .rest.test_symbol_validation import TestFuturesSymbolValidation
from .rest.test_price_logic import TestFuturesPriceLogic
from .rest.test_perpetual_spot_comparison import TestPerpetualSpotComparison

__all__ = [
    "TestPerpetualKlines",
    "TestContinuousKlines",
    "TestFuturesQuotes",
    "TestFuturesMultiResolution",
    "TestFuturesSymbolValidation",
    "TestFuturesPriceLogic",
    "TestPerpetualSpotComparison",
]
