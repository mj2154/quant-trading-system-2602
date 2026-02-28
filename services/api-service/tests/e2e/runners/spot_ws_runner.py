"""
现货WebSocket测试运行器

运行所有现货WebSocket测试:
- test_kline_sub.py: K线订阅
- test_quotes_sub.py: 报价订阅
- test_quotes_multi.py: 多报价订阅
- test_multi_sub.py: 多订阅管理

运行方式:
    python tests/e2e/runners/spot_ws_runner.py

作者: Claude Code
版本: v2.0.0
"""

import sys
from pathlib import Path

_current = Path(__file__).resolve()
_api_service_root = _current.parent.parent.parent
_src_path = _api_service_root / "src"
_tests_path = _api_service_root / "tests"

for p in [_src_path, _tests_path]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import asyncio
from tests.e2e.base_simple_test import SimpleE2ETestBase


class SpotWebSocketRunner(SimpleE2ETestBase):
    """现货WebSocket测试运行器"""

    def __init__(self):
        super().__init__()
        self.test_results = {"passed": 0, "failed": 0, "errors": []}

    async def run_all_tests(self):
        """运行所有现货WebSocket测试"""
        print("=" * 80)
        print("开始运行现货WebSocket端到端测试")
        print("=" * 80)

        tests = [
            ("K线订阅", self.test_kline_subscription),
            ("报价订阅", self.test_quotes_subscription),
            ("多报价订阅", self.test_quotes_multi_symbol),
            ("多订阅管理", self.test_multi_subscription),
        ]

        for test_name, test_method in tests:
            print(f"\n{'='*60}")
            print(f"测试: {test_name}")
            print(f"{'='*60}")

            try:
                result = await test_method()

                if result or test_name in ["K线订阅", "报价订阅", "多报价订阅", "多订阅管理"]:
                    self.test_results["passed"] += 1
                    print(f"✅ {test_name}: 通过")
                else:
                    self.test_results["failed"] += 1
                    print(f"❌ {test_name}: 失败")

            except Exception as e:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(f"{test_name}: {e!s}")
                print(f"❌ {test_name}: 异常 - {e!s}")

        # 打印结果
        print(f"\n{'='*80}")
        print(f"测试结果汇总")
        print(f"{'='*80}")
        print(f"通过: {self.test_results['passed']}")
        print(f"失败: {self.test_results['failed']}")

        if self.test_results["errors"]:
            print("\n错误详情:")
            for error in self.test_results["errors"]:
                print(f"  ❌ {error}")

        print(f"{'='*80}")

    # 测试方法
    async def test_kline_subscription(self):
        """测试K线订阅"""
        from tests.e2e.spot.ws.test_kline_sub import TestSpotKlineSubscription

        test = TestSpotKlineSubscription()
        async with test:
            return await test.test_kline_subscription()

    async def test_quotes_subscription(self):
        """测试报价订阅"""
        from tests.e2e.spot.ws.test_quotes_sub import TestSpotQuotesSubscription

        test = TestSpotQuotesSubscription()
        async with test:
            return await test.test_quotes_subscription()

    async def test_quotes_multi_symbol(self):
        """测试多报价订阅"""
        from tests.e2e.spot.ws.test_quotes_multi import TestSpotQuotesMultiSymbol

        test = TestSpotQuotesMultiSymbol()
        async with test:
            return await test.test_quotes_subscription_multi_symbol()

    async def test_multi_subscription(self):
        """测试多订阅管理"""
        from tests.e2e.spot.ws.test_multi_sub import TestSpotMultiSubscription

        test = TestSpotMultiSubscription()
        async with test:
            return await test.test_multi_subscription()


async def main():
    """主函数"""
    runner = SpotWebSocketRunner()
    async with runner:
        await runner.setup()
        await runner.run_all_tests()

    return 0 if runner.test_results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
