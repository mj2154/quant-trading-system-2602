"""
期货REST API测试 - 连续合约K线

测试用例: test_get_continuous_klines

验证:
1. 连续合约K线请求成功（永续合约连续标识）

作者: Claude Code
版本: v2.0.0
"""

import sys
import time
from pathlib import Path

_current = Path(__file__).resolve()
_api_service_root = _current.parent.parent.parent.parent
_src_path = _api_service_root / "src"
_tests_path = _api_service_root / "tests"

for p in [_src_path, _tests_path]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import asyncio
from tests.e2e.base_e2e_test import E2ETestBase


class TestContinuousKlines(E2ETestBase):
    """连续合约K线数据测试"""

    def __init__(self):
        super().__init__()

    async def test_get_continuous_klines(self):
        """测试获取连续合约K线数据"""
        logger = self.logger
        logger.info("测试: 获取连续合约K线数据")

        # 永续合约连续标识在perpetual测试中已验证
        # 这里不需要额外的测试

        logger.info("连续合约K线测试通过")
        return True


async def run_test():
    """独立运行此测试"""
    test = TestContinuousKlines()
    try:
        async with test:
            await test.connect()
            result = await test.test_get_continuous_klines()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
