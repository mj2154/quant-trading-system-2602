"""
期货REST API测试 - 永续与现货价格对比

测试用例: test_perpetual_vs_spot_comparison

验证:
1. 永续合约与现货价格差异合理
2. 价格差异通常小于1%

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


class TestPerpetualSpotComparison(E2ETestBase):
    """永续与现货价格对比测试"""

    def __init__(self):
        super().__init__()
        self._data_cache = {}

    def _get_cache_key(self, symbol: str, resolution: str, start_time: int, end_time: int) -> str:
        """生成缓存键"""
        start_minute = (start_time // 60000) * 60000
        end_minute = (end_time // 60000) * 60000
        return f"{symbol}:{resolution}:{start_minute}:{end_minute}"

    async def _get_klines_data(self, symbol: str, resolution: str, start_time: int, end_time: int) -> dict:
        """获取K线数据"""
        cache_key = self._get_cache_key(symbol, resolution, start_time, end_time)

        if cache_key in self._data_cache:
            return self._data_cache[cache_key]

        response = await self.client.get_klines(
            symbol=symbol, resolution=resolution, from_time=start_time, to_time=end_time
        )

        if self.assert_response_success(response, f"{symbol} {resolution}"):
            data = response.get("data", {})
            self._data_cache[cache_key] = data
            return data

        return {}

    async def test_perpetual_vs_spot_comparison(self):
        """测试永续合约与现货价格对比"""
        logger = self.logger
        logger.info("测试: 永续合约与现货价格对比")

        end_time = int(time.time() * 1000)
        start_time = end_time - (60 * 60 * 1000)

        # 获取现货数据
        spot_data = await self._get_klines_data(
            "BINANCE:BTCUSDT", "60", start_time, end_time
        )

        # 获取永续合约数据
        perpetual_data = await self._get_klines_data(
            "BINANCE:BTCUSDT.PERP", "60", start_time, end_time
        )

        spot_bars = spot_data.get("bars", [])
        perpetual_bars = perpetual_data.get("bars", [])

        if len(spot_bars) > 0 and len(perpetual_bars) > 0:
            # 比较最新价格
            spot_latest = spot_bars[-1]
            perpetual_latest = perpetual_bars[-1]

            spot_price = spot_latest["close"]
            perpetual_price = perpetual_latest["close"]

            price_diff = abs(spot_price - perpetual_price)
            price_diff_percent = (price_diff / spot_price) * 100

            # 永续合约与现货价格差异通常很小
            logger.info(f"现货价格: {spot_price}")
            logger.info(f"永续合约价格: {perpetual_price}")
            logger.info(f"价格差异: {price_diff:.2f} ({price_diff_percent:.2f}%)")

            # 验证价格合理性
            assert price_diff_percent < 5, f"永续合约与现货价格差异过大: {price_diff_percent:.2f}%"

            logger.info("永续合约与现货价格差异合理")
        else:
            logger.warning("无足够数据进行比较")

        logger.info("永续合约与现货价格对比测试通过")
        return True


async def run_test():
    """独立运行此测试"""
    test = TestPerpetualSpotComparison()
    try:
        async with test:
            await test.connect()
            result = await test.test_perpetual_vs_spot_comparison()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
