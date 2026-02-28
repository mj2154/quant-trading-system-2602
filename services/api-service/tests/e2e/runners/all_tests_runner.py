"""
所有E2E测试运行器

一次性运行所有E2E测试:
- 现货REST API测试
- 现货WebSocket测试
- 期货REST API测试
- 期货WebSocket测试

运行方式:
    python tests/e2e/runners/all_tests_runner.py

作者: Claude Code
版本: v2.0.0
"""

import sys
from pathlib import Path

# 添加路径
_current = Path(__file__).resolve()
_api_service_root = _current.parent.parent.parent
_src_path = _api_service_root / "src"
_tests_path = _api_service_root / "tests"

for p in [_src_path, _tests_path]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import asyncio


async def run_all_tests():
    """运行所有E2E测试"""
    print("=" * 80)
    print("开始运行所有E2E端到端测试")
    print("=" * 80)

    results = {
        "spot_rest": {"passed": 0, "failed": 0, "errors": []},
        "spot_ws": {"passed": 0, "failed": 0, "errors": []},
        "futures_rest": {"passed": 0, "failed": 0, "errors": []},
        "futures_ws": {"passed": 0, "failed": 0, "errors": []},
    }

    # 导入测试模块
    from tests.e2e.spot.rest.test_config import TestSpotConfig
    from tests.e2e.spot.rest.test_search_symbols import TestSpotSearchSymbols
    from tests.e2e.spot.rest.test_klines import TestSpotKlines
    from tests.e2e.spot.rest.test_quotes import TestSpotQuotes
    from tests.e2e.spot.rest.test_multi_resolution import TestSpotMultiResolution
    from tests.e2e.spot.rest.test_validation import TestSpotValidation

    from tests.e2e.futures.rest.test_perpetual_klines import TestPerpetualKlines
    from tests.e2e.futures.rest.test_continuous_klines import TestContinuousKlines
    from tests.e2e.futures.rest.test_futures_quotes import TestFuturesQuotes
    from tests.e2e.futures.rest.test_multi_resolution import TestFuturesMultiResolution
    from tests.e2e.futures.rest.test_symbol_validation import TestFuturesSymbolValidation
    from tests.e2e.futures.rest.test_price_logic import TestFuturesPriceLogic
    from tests.e2e.futures.rest.test_perpetual_spot_comparison import TestPerpetualSpotComparison

    # 现货REST测试
    print("\n" + "=" * 60)
    print("📊 现货REST API测试")
    print("=" * 60)

    spot_rest_tests = [
        ("获取交易所配置", TestSpotConfig, "test_get_config"),
        ("搜索交易对", TestSpotSearchSymbols, "test_search_symbols"),
        ("获取现货K线数据", TestSpotKlines, "test_get_spot_klines"),
        ("获取现货报价数据", TestSpotQuotes, "test_get_spot_quotes"),
        ("多分辨率K线数据", TestSpotMultiResolution, "test_multi_resolution_klines"),
        ("格式验证", TestSpotValidation, "test_symbol_format_validation"),
    ]

    for test_name, test_class, test_method in spot_rest_tests:
        test = test_class()
        try:
            async with test:
                await test.connect()
                success = await getattr(test, test_method)()
                if success:
                    results["spot_rest"]["passed"] += 1
                    print(f"  ✅ {test_name}")
                else:
                    results["spot_rest"]["failed"] += 1
                    print(f"  ❌ {test_name}")
        except Exception as e:
            results["spot_rest"]["failed"] += 1
            results["spot_rest"]["errors"].append(f"{test_name}: {e!s}")
            print(f"  ❌ {test_name}: {e!s}")

    # 期货REST测试
    print("\n" + "=" * 60)
    print("📊 期货REST API测试")
    print("=" * 60)

    futures_rest_tests = [
        ("永续合约K线", TestPerpetualKlines, "test_get_perpetual_klines"),
        ("连续合约Kline", TestContinuousKlines, "test_get_continuous_klines"),
        ("期货报价", TestFuturesQuotes, "test_get_futures_quotes"),
        ("多分辨率K线", TestFuturesMultiResolution, "test_multi_resolution_futures_klines"),
        ("符号格式验证", TestFuturesSymbolValidation, "test_futures_symbol_format_validation"),
        ("价格逻辑验证", TestFuturesPriceLogic, "test_futures_price_logic"),
        ("永续与现货价格对比", TestPerpetualSpotComparison, "test_perpetual_vs_spot_comparison"),
    ]

    for test_name, test_class, test_method in futures_rest_tests:
        test = test_class()
        try:
            async with test:
                await test.connect()
                success = await getattr(test, test_method)()
                if success:
                    results["futures_rest"]["passed"] += 1
                    print(f"  ✅ {test_name}")
                else:
                    results["futures_rest"]["failed"] += 1
                    print(f"  ❌ {test_name}")
        except Exception as e:
            results["futures_rest"]["failed"] += 1
            results["futures_rest"]["errors"].append(f"{test_name}: {e!s}")
            print(f"  ❌ {test_name}: {e!s}")

    # 打印汇总
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)

    total_passed = sum(r["passed"] for r in results.values())
    total_failed = sum(r["failed"] for r in results.values())
    total = total_passed + total_failed

    for category, result in results.items():
        category_name = {
            "spot_rest": "现货REST",
            "spot_ws": "现货WebSocket",
            "futures_rest": "期货REST",
            "futures_ws": "期货WebSocket",
        }.get(category, category)
        print(f"{category_name}: {result['passed']}/{result['passed'] + result['failed']} 通过")

    print(f"\n总计: {total_passed}/{total} 通过")
    print(f"失败: {total_failed}")

    if any(r["errors"] for r in results.values()):
        print("\n错误详情:")
        for category, result in results.items():
            for error in result["errors"][:5]:
                print(f"  [{category}] {error}")

    print("=" * 80)

    return results


def main():
    """主函数"""
    try:
        results = asyncio.run(run_all_tests())
        total_failed = sum(r["failed"] for r in results.values())
        return 0 if total_failed == 0 else 1
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
