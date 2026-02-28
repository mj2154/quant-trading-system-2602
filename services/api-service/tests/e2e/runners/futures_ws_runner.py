"""
期货WebSocket测试运行器

运行所有期货WebSocket测试:
- test_perpetual_kline_sub.py: 永续合约K线订阅
- test_futures_quotes_sub.py: 期货报价订阅
- test_multi_futures_sub.py: 多期货订阅

运行方式:
    python tests/e2e/runners/futures_ws_runner.py

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


class FuturesWebSocketRunner(SimpleE2ETestBase):
    """期货WebSocket测试运行器"""

    def __init__(self):
        super().__init__()
        self.test_results = {"passed": 0, "failed": 0, "errors": []}

    async def run_all_tests(self):
        """运行所有期货WebSocket测试"""
        print("=" * 80)
        print("开始运行期货WebSocket端到端测试")
        print("=" * 80)

        tests = [
            ("永续合约K线订阅", self.test_perpetual_kline),
            ("期货报价订阅", self.test_futures_quotes),
            ("多期货订阅", self.test_multi_futures_subscription),
        ]

        for test_name, test_method in tests:
            print(f"\n{'='*60}")
            print(f"测试: {test_name}")
            print(f"{'='*60}")

            try:
                result = await test_method()

                if result:
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
    async def test_perpetual_kline(self):
        """测试永续合约K线订阅"""
        from tests.e2e.futures.ws.test_perpetual_kline_sub import TestPerpetualKlineSubscription

        test = TestPerpetualKlineSubscription()
        async with test:
            return await test.test_perpetual_kline()

    async def test_futures_quotes(self):
        """测试期货报价订阅"""
        from tests.e2e.futures.ws.test_futures_quotes_sub import TestFuturesQuotesSubscription

        test = TestFuturesQuotesSubscription()
        async with test:
            return await test.test_futures_quotes()

    async def test_multi_futures_subscription(self):
        """测试多期货订阅"""
        from tests.e2e.futures.ws.test_multi_futures_sub import TestMultiFuturesSubscription

        test = TestMultiFuturesSubscription()
        async with test:
            return await test.test_multi_futures_subscription()


async def main():
    """主函数"""
    runner = FuturesWebSocketRunner()
    async with runner:
        await runner.setup()
        await runner.run_all_tests()

    return 0 if runner.test_results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
