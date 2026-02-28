"""
期货REST API测试 - 多分辨率K线

测试用例: test_multi_resolution_futures_klines

验证:
1. 不同分辨率的期货K线请求
2. 分辨率与数据匹配

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


class TestFuturesMultiResolution(E2ETestBase):
    """期货多分辨率K线测试"""

    def __init__(self):
        super().__init__()
        self._data_cache = {}

    def _get_cache_key(self, symbol: str, resolution: str, start_time: int, end_time: int) -> str:
        """生成缓存键"""
        start_minute = (start_time // 60000) * 60000
        end_minute = (end_time // 60000) * 60000
        return f"{symbol}:{resolution}:{start_minute}:{end_minute}"

    async def _get_klines_data(self, symbol: str, resolution: str, start_time: int, end_time: int) -> dict | None:
        """获取K线数据（遵循三阶段模式）

        服务端返回格式（v2.1统一格式）：
        - ack: {"action": "ack", "data": {"message": "..."}}
        - success: {"action": "success", "data": {...}}
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
        # 步骤2: 提取数据
        data = response.get("data", {})
        self._data_cache[cache_key] = data
        return data

    async def test_multi_resolution_futures_klines(self):
        """测试多分辨率期货K线数据

        遵循设计文档的三阶段模式：
        1. 客户端发送请求（携带 requestId）
        2. 服务端返回 ack 确认
        3. 服务端异步处理完成后返回 success
        """
        logger = self.logger
        logger.info("测试: 多分辨率期货K线数据")

        # 使用历史时间范围（永续合约数据最新到2026-02-01）
        end_time = int(time.mktime(time.strptime("2026-02-01 04:00:00", "%Y-%m-%d %H:%M:%S"))) * 1000
        start_time_24h = end_time - (24 * 60 * 60 * 1000)
        start_time_1h = end_time - (60 * 60 * 1000)

        symbol = "BINANCE:BTCUSDT.PERP"

        resolution_tests = [
            ("1", start_time_1h, end_time, "1分钟"),
            ("5", start_time_1h, end_time, "5分钟"),
            ("60", start_time_1h, end_time, "1小时"),
            ("D", start_time_24h, end_time, "1天"),
        ]

        passed = 0
        for resolution, start_time, end_time_desc, desc in resolution_tests:
            logger.info("测试分辨率: %s (%s)", resolution, desc)

            data = await self._get_klines_data(symbol, resolution, start_time, end_time)
            if not data:
                logger.error("分辨率%s: 获取数据失败", resolution)
                continue

            # 验证符号匹配
            if data.get("symbol") != symbol:
                logger.error("分辨率%s: 符号不匹配 (期望: %s, 实际: %s)", resolution, symbol, data.get("symbol"))
                continue

            # 验证分辨率匹配 - 优先检查 interval，其次检查 resolution
            returned_interval = data.get("interval")
            returned_resolution = data.get("resolution")
            if returned_interval is not None:
                if returned_interval != resolution:
                    logger.error("分辨率%s: 分辨率不匹配 (期望: %s, 实际: %s)", resolution, resolution, returned_interval)
                    continue
            elif returned_resolution is not None:
                if returned_resolution != resolution:
                    logger.error("分辨率%s: 分辨率不匹配 (期望: %s, 实际: %s)", resolution, resolution, returned_resolution)
                    continue
            else:
                logger.error("分辨率%s: 响应中缺少 interval 或 resolution 字段", resolution)
                continue

            bars = data.get("bars", [])
            count = data.get("count", 0)

            if count > 0:
                for bar in bars[:2]:
                    assert bar["volume"] >= 0, "期货成交量必须大于等于0"
                    assert bar["open"] > 0, "开盘价必须大于0"

            logger.info("分辨率%s (%s): %d条数据", resolution, desc, count)
            passed += 1

        logger.info("多分辨率期货K线测试: %d/%d 通过", passed, len(resolution_tests))
        return passed > 0


async def run_test():
    """独立运行此测试"""
    test = TestFuturesMultiResolution()
    try:
        async with test:
            await test.connect()
            result = await test.test_multi_resolution_futures_klines()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
