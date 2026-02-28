"""
现货REST API测试 - K线数据

测试用例: test_get_spot_klines

验证:
1. 获取单个K线数据
2. 验证K线数据格式
3. 验证K线数据内容

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


class TestSpotKlines(E2ETestBase):
    """现货K线数据测试"""

    def __init__(self):
        super().__init__(auto_connect=False)

    async def test_get_spot_klines(self):
        """测试获取现货K线数据

        严格遵循v2.1规范：
        1. 客户端发送请求（携带 requestId）
        2. 服务端返回 ack 确认（返回 requestId）
        3. 服务端异步处理完成后返回 success（返回 requestId 和数据）

        使用严格验证：
        - assert_unified_response_format 验证统一响应格式
        - assert_kline_bars 验证K线Bar对象格式
        """
        logger = self.logger
        logger.info("测试: 获取现货K线数据")

        end_time = int(time.time() * 1000)
        start_time = end_time - (24 * 60 * 60 * 1000)

        # 测试用例
        test_cases = [
            {"symbol": "BINANCE:BTCUSDT", "resolution": "60", "name": "BTCUSDT 1小时K线"},
            {"symbol": "BINANCE:ETHUSDT", "resolution": "60", "name": "ETHUSDT 1小时K线"},
        ]

        passed = 0
        for test_case in test_cases:
            logger.info("  测试: %s", test_case["name"])

            # 注意：get_klines() 内部已经处理了 ack+success 两阶段响应
            response = await self.client.get_klines(
                symbol=test_case["symbol"],
                resolution=test_case["resolution"],
                from_time=start_time,
                to_time=end_time,
            )

            if not self.assert_response_success(response, test_case["name"]):
                logger.error("  %s: 响应失败", test_case["name"])
                continue

            # get_klines() 已返回 success 响应，无需额外等待
            # 严格验证统一响应格式 (v2.1规范)
            if not self.assert_unified_response_format(response, "klines"):
                logger.error("  %s: 统一响应格式验证失败", test_case["name"])
                continue
            data = response.get("data", {})

            if not data:
                logger.error("  %s: 无数据", test_case["name"])
                continue

            # 验证数据内容
            if not all(k in data for k in ["symbol", "interval", "bars", "count", "no_data"]):
                logger.error("  %s: 缺少必要字段 (symbol, interval, bars, count, no_data)", test_case["name"])
                missing = [k for k in ["symbol", "interval", "bars", "count", "no_data"] if k not in data]
                logger.error("    缺失字段: %s", missing)
                continue

            if data["symbol"] != test_case["symbol"]:
                logger.error("  %s: 符号不匹配", test_case["name"])
                continue

            # interval 与请求保持一致
            returned_interval = data.get("interval")
            if returned_interval and returned_interval != test_case["resolution"]:
                logger.warning("  %s: interval 不匹配（%s vs %s）",
                              test_case["name"], returned_interval, test_case["resolution"])

            # 严格验证 K线 Bar 对象格式
            bars = data.get("bars", [])
            if not self.assert_kline_bars(bars, test_case["name"]):
                logger.error("  %s: K线Bar对象格式验证失败", test_case["name"])
                continue

            count = data.get("count", 0)
            if count > 0:
                logger.info("    ✅ %s: 获得%d条K线数据", test_case["name"], count)
            else:
                logger.warning("    ⚠️ %s: 无数据", test_case["name"])

            passed += 1

        logger.info("现货K线测试: %d/%d 通过", passed, len(test_cases))
        return passed > 0


async def run_test():
    """独立运行此测试"""
    test = TestSpotKlines()
    try:
        async with test:
            await test.connect()
            result = await test.test_get_spot_klines()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
