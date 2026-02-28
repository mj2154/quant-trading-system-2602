"""
期货REST API测试 - 价格逻辑验证

测试用例: test_futures_price_logic

验证:
1. 期货价格合理性
2. 高低价逻辑正确

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


class TestFuturesPriceLogic(E2ETestBase):
    """期货价格逻辑测试"""

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

    async def test_futures_price_logic(self):
        """测试期货价格逻辑验证"""
        logger = self.logger
        logger.info("测试: 期货价格逻辑验证")

        end_time = int(time.time() * 1000)
        start_time = end_time - (60 * 60 * 1000)
        symbol = "BINANCE:BTCUSDT.PERP"

        data = await self._get_klines_data(symbol, "60", start_time, end_time)
        bars = data.get("bars", [])

        if len(bars) > 0:
            # 验证期货特有的价格逻辑
            for bar in bars:
                assert bar["open"] > 0, "开盘价必须大于0"
                assert bar["high"] > 0, "最高价必须大于0"
                assert bar["low"] > 0, "最低价必须大于0"
                assert bar["close"] > 0, "收盘价必须大于0"

                # 高低价逻辑
                assert bar["high"] >= bar["low"], "最高价必须大于等于最低价"
                assert bar["high"] >= bar["open"], "最高价必须大于等于开盘价"
                assert bar["high"] >= bar["close"], "最高价必须大于等于收盘价"
                assert bar["low"] <= bar["open"], "最低价必须小于等于开盘价"
                assert bar["low"] <= bar["close"], "最低价必须小于等于收盘价"

                assert bar["volume"] >= 0, "成交量必须大于等于0"

            logger.info(f"期货价格逻辑验证通过: {len(bars)}条数据")
        else:
            logger.warning("无期货K线数据可验证")

        logger.info("期货价格逻辑测试通过")
        return True


async def run_test():
    """独立运行此测试"""
    test = TestFuturesPriceLogic()
    try:
        async with test:
            await test.connect()
            result = await test.test_futures_price_logic()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
