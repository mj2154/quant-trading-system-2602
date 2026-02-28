"""
期货REST API测试运行器

运行所有期货REST API测试:
- test_perpetual_klines.py: 永续合约K线
- test_continuous_klines.py: 连续合约K线
- test_futures_quotes.py: 期货报价
- test_multi_resolution.py: 多分辨率K线
- test_symbol_validation.py: 符号格式验证
- test_price_logic.py: 价格逻辑验证
- test_perpetual_spot_comparison.py: 永续与现货价格对比

运行方式:
    python tests/e2e/runners/futures_rest_runner.py

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


async def run_all_tests():
    """运行所有期货REST API测试"""
    from tests.e2e.futures.rest.test_perpetual_klines import TestPerpetualKlines
    from tests.e2e.futures.rest.test_continuous_klines import TestContinuousKlines
    from tests.e2e.futures.rest.test_futures_quotes import TestFuturesQuotes
    from tests.e2e.futures.rest.test_multi_resolution import TestFuturesMultiResolution
    from tests.e2e.futures.rest.test_symbol_validation import TestFuturesSymbolValidation
    from tests.e2e.futures.rest.test_price_logic import TestFuturesPriceLogic
    from tests.e2e.futures.rest.test_perpetual_spot_comparison import TestPerpetualSpotComparison

    print("=" * 80)
    print("开始运行期货REST API端到端测试")
    print("=" * 80)

    tests = [
        ("永续合约K线", TestPerpetualKlines, "test_get_perpetual_klines"),
        ("连续合约K线", TestContinuousKlines, "test_get_continuous_klines"),
        ("期货报价", TestFuturesQuotes, "test_get_futures_quotes"),
        ("多分辨率K线", TestFuturesMultiResolution, "test_multi_resolution_futures_klines"),
        ("符号格式验证", TestFuturesSymbolValidation, "test_futures_symbol_format_validation"),
        ("价格逻辑验证", TestFuturesPriceLogic, "test_futures_price_logic"),
        ("永续与现货价格对比", TestPerpetualSpotComparison, "test_perpetual_vs_spot_comparison"),
    ]

    results = {"passed": 0, "failed": 0, "errors": []}

    for test_name, test_class, test_method_name in tests:
        print(f"\n{'='*60}")
        print(f"测试: {test_name}")
        print(f"{'='*60}")

        test = test_class()
        try:
            async with test:
                await test.connect()
                test_method = getattr(test, test_method_name)
                success = await test_method()

                if success:
                    results["passed"] += 1
                    print(f"✅ {test_name}: 通过")
                else:
                    results["failed"] += 1
                    results["errors"].append(f"{test_name}: 失败")
                    print(f"❌ {test_name}: 失败")

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{test_name}: {e!s}")
            print(f"❌ {test_name}: 异常 - {e!s}")

    # 打印结果
    print(f"\n{'='*80}")
    print(f"测试结果汇总")
    print(f"{'='*80}")
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")

    if results["errors"]:
        print("\n错误详情:")
        for error in results["errors"]:
            print(f"  ❌ {error}")

    print(f"{'='*80}")

    return results


def main():
    """主函数"""
    try:
        results = asyncio.run(run_all_tests())
        return 0 if results["failed"] == 0 else 1
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
