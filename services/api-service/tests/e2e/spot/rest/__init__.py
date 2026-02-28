"""
现货REST API测试模块

测试用例:
- TestSpotConfig: 获取交易所配置
- TestSpotSearchSymbols: 搜索交易对
- TestSpotKlines: 获取现货K线数据
- TestSpotQuotes: 获取现货报价数据
- TestSpotMultiResolution: 测试多分辨率K线数据
- TestSpotValidation: 交易对格式和时间范围验证
"""

from .test_config import TestSpotConfig
from .test_search_symbols import TestSpotSearchSymbols
from .test_klines import TestSpotKlines
from .test_quotes import TestSpotQuotes
from .test_multi_resolution import TestSpotMultiResolution
from .test_validation import TestSpotValidation

__all__ = [
    "TestSpotConfig",
    "TestSpotSearchSymbols",
    "TestSpotKlines",
    "TestSpotQuotes",
    "TestSpotMultiResolution",
    "TestSpotValidation",
]
