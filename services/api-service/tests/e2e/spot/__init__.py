"""
现货REST API测试模块

测试用例:
- test_get_config: 获取交易所配置
- test_search_symbols: 搜索交易对
- test_get_spot_klines: 获取现货K线数据
- test_get_spot_quotes: 获取现货报价数据
- test_multi_resolution_klines: 测试多分辨率K线数据
- test_symbol_format_validation: 交易对格式验证
- test_time_range_validation: 时间范围验证

运行方式:
    # 运行单个测试
    pytest tests/e2e/spot/rest/test_config.py -v

    # 运行所有现货REST测试
    pytest tests/e2e/spot/rest/ -v

    # 使用运行器
    python tests/e2e/runners/spot_rest_runner.py
"""

from .rest.test_config import TestSpotConfig
from .rest.test_search_symbols import TestSpotSearchSymbols
from .rest.test_klines import TestSpotKlines
from .rest.test_quotes import TestSpotQuotes
from .rest.test_multi_resolution import TestSpotMultiResolution
from .rest.test_validation import TestSpotValidation

__all__ = [
    "TestSpotConfig",
    "TestSpotSearchSymbols",
    "TestSpotKlines",
    "TestSpotQuotes",
    "TestSpotMultiResolution",
    "TestSpotValidation",
]
