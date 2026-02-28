"""
期货REST API测试 - 永续合约K线

测试用例: test_get_perpetual_klines

验证:
1. 永续合约K线请求成功
2. 数据包含symbol, resolution, bars, count字段
3. K线格式正确

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


class TestPerpetualKlines(E2ETestBase):
    """永续合约K线数据测试"""

    def __init__(self):
        super().__init__()
        self.perpetual_symbols = ["BINANCE:BTCUSDT.PERP", "BINANCE:ETHUSDT.PERP"]
        self._data_cache = {}

    def _get_common_klines_params(self):
        """获取通用的K线参数（使用历史时间范围）"""
        end_time = int(time.mktime(time.strptime("2026-02-01 04:00:00", "%Y-%m-%d %H:%M:%S"))) * 1000
        start_time = end_time - (24 * 60 * 60 * 1000)
        return {
            "end_time": end_time,
            "start_time": start_time,
        }

    def _get_cache_key(self, symbol: str, resolution: str, start_time: int, end_time: int) -> str:
        """生成缓存键"""
        start_minute = (start_time // 60000) * 60000
        end_minute = (end_time // 60000) * 60000
        return f"{symbol}:{resolution}:{start_minute}:{end_minute}"

    async def _get_klines_data(
        self, symbol: str, resolution: str, start_time: int, end_time: int
    ) -> dict | None:
        """获取K线数据（遵循三阶段模式）

        服务端返回格式（v2.1统一格式）：
        - ack: {"action": "ack", "data": {"message": "..."}}
        - success: {"action": "success", "data": {...}}

        注意：永续合约数据使用异步任务，需要等待success响应。
        """
        cache_key = self._get_cache_key(symbol, resolution, start_time, end_time)

        if cache_key in self._data_cache:
            return self._data_cache[cache_key]

        # 发送请求
        # 注意：get_klines() 内部已经处理了 ack+success 两阶段响应
        response = await self.client.get_klines(
            symbol=symbol, resolution=resolution, from_time=start_time, to_time=end_time
        )

        # 步骤1: 验证响应（get_klines 已返回 success）
        if not self.assert_response_success(response, f"{symbol} {resolution}"):
            self.logger.error("%s %s: 获取响应失败", symbol, resolution)
            return None

        # get_klines() 已返回 success 响应，无需再调用 wait_for_task_completion()
        # 直接使用 response 作为结果
        result = response

        # 步骤2: 提取数据
        data = result.get("data", {})

        # 缓存结果
        self._data_cache[cache_key] = data
        return data

    async def test_get_perpetual_klines(self):
        """测试获取永续合约K线数据"""
        logger = self.logger
        logger.info("测试: 获取永续合约K线数据")

        # 使用历史时间范围（永续合约数据最新到2026-02-01）
        params = self._get_common_klines_params()
        passed = 0

        for symbol in self.perpetual_symbols:
            logger.info("测试: %s", symbol)

            data = await self._get_klines_data(
                symbol, "60", params["start_time"], params["end_time"]
            )

            if not data:
                logger.warning("%s: 无数据", symbol)
                continue

            # 验证数据内容
            if data.get("symbol") != symbol:
                logger.error("%s: 符号不匹配 (期望: %s, 实际: %s)", symbol, symbol, data.get("symbol"))
                continue

            if not self.assert_kline_data(data, f"永续合约{symbol}"):
                logger.error("%s: K线数据格式错误", symbol)
                continue

            bars = data.get("bars", [])
            count = data.get("count", 0)

            if count > 0:
                # 验证K线基本字段
                for bar in bars[:3]:
                    assert bar["time"] > 0, "时间戳必须大于0"
                    assert bar["open"] > 0, "开盘价必须大于0"
                    assert bar["high"] > 0, "最高价必须大于0"
                    assert bar["low"] > 0, "最低价必须大于0"
                    assert bar["close"] > 0, "收盘价必须大于0"
                    assert bar["volume"] >= 0, "成交量必须大于等于0"
                    assert bar["high"] >= bar["low"], "最高价必须大于等于最低价"

                logger.info("%s: 获得%d条永续合约K线数据", symbol, count)
            else:
                logger.warning("%s: 无K线数据", symbol)

            passed += 1

        logger.info("永续合约K线测试: %d/%d 通过", passed, len(self.perpetual_symbols))
        return passed > 0


async def run_test():
    """独立运行此测试"""
    test = TestPerpetualKlines()
    try:
        async with test:
            await test.connect()
            result = await test.test_get_perpetual_klines()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
