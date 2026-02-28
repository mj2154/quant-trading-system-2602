"""
期货REST API测试模块

测试用例:
- TestPerpetualKlines: 永续合约K线数据测试
- TestContinuousKlines: 连续合约K线数据测试
- TestFuturesQuotes: 期货报价数据测试
- TestFuturesMultiResolution: 多分辨率期货K线测试
- TestFuturesSymbolValidation: 期货交易对格式验证
- TestFuturesPriceLogic: 期货价格逻辑验证
- TestPerpetualSpotComparison: 永续合约与现货价格对比
"""

from .test_perpetual_klines import TestPerpetualKlines
from .test_continuous_klines import TestContinuousKlines
from .test_futures_quotes import TestFuturesQuotes
from .test_multi_resolution import TestFuturesMultiResolution
from .test_symbol_validation import TestFuturesSymbolValidation
from .test_price_logic import TestFuturesPriceLogic
from .test_perpetual_spot_comparison import TestPerpetualSpotComparison

__all__ = [
    "TestPerpetualKlines",
    "TestContinuousKlines",
    "TestFuturesQuotes",
    "TestFuturesMultiResolution",
    "TestFuturesSymbolValidation",
    "TestFuturesPriceLogic",
    "TestPerpetualSpotComparison",
]
