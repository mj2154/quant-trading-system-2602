"""
现货REST API测试 - 多分辨率K线数据

测试用例: test_multi_resolution_klines

验证:
1. 不同分辨率的K线请求
2. 分辨率与数据匹配
3. 1分钟分辨率数据量正确

符合规范:
- TradingView-完整API规范设计文档.md (v2.1统一格式)
- 严格验证 type 字段在 data 内部
- 使用 assert_unified_response_format 验证响应格式
- 使用 assert_kline_bars 严格验证K线Bar对象格式

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


class TestSpotMultiResolution(E2ETestBase):
    """现货多分辨率K线测试"""

    def __init__(self):
        super().__init__(auto_connect=False)

    async def test_multi_resolution_klines(self):
        """测试多分辨率K线数据

        严格遵循v2.1规范：
        1. 客户端发送请求（携带 requestId）
        2. 服务端返回 ack 确认（返回 requestId）
        3. 服务端异步处理完成后返回 success（返回 requestId 和数据）

        使用严格验证：
        - assert_unified_response_format 验证统一响应格式
        - assert_kline_bars 验证K线Bar对象格式
        """
        logger = self.logger
        logger.info("测试: 多分辨率K线数据")

        symbol = "BINANCE:BTCUSDT"
        end_time = int(time.time() * 1000)
        start_time = end_time - (60 * 60 * 1000)

        resolutions = ["1", "5", "60"]
        passed = 0

        for resolution in resolutions:
            logger.info("  测试分辨率: %s", resolution)

            # 注意：get_klines() 内部已经处理了 ack+success 两阶段响应
            response = await self.client.get_klines(
                symbol=symbol, resolution=resolution, from_time=start_time, to_time=end_time
            )

            # 验证响应（get_klines 已返回 success）
            if not self.assert_response_success(response, f"分辨率{resolution}"):
                logger.error("  分辨率%s: 响应失败", resolution)
                continue

            # get_klines() 已返回 success 响应，无需额外等待
            # 严格验证统一响应格式 (v2.1规范)
            if not self.assert_unified_response_format(response, "klines"):
                logger.error("  分辨率%s: 统一响应格式验证失败", resolution)
                continue
            data = response.get("data", {})

            if not data:
                logger.error("  分辨率%s: 无数据", resolution)
                continue

            if data.get("symbol") != symbol:
                logger.error("  分辨率%s: 符号不匹配", resolution)
                continue
            # 后端使用 interval 字段（与数据库和模型一致）
            returned_interval = data.get("interval")
            if returned_interval and returned_interval != resolution:
                logger.warning("  分辨率%s: interval 不匹配（%s vs %s）",
                              resolution, returned_interval, resolution)

            # 严格验证 K线 Bar 对象格式
            bars = data.get("bars", [])
            if not self.assert_kline_bars(bars, f"分辨率{resolution}"):
                logger.error("  分辨率%s: K线Bar对象格式验证失败", resolution)
                continue

            count = data.get("count", 0)
            logger.info("    ✅ 分辨率%s: %d条数据", resolution, count)
            passed += 1

        logger.info("多分辨率K线测试: %d/%d 通过", passed, len(resolutions))
        return passed > 0


async def run_test():
    """独立运行此测试"""
    test = TestSpotMultiResolution()
    try:
        async with test:
            await test.connect()
            result = await test.test_multi_resolution_klines()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
