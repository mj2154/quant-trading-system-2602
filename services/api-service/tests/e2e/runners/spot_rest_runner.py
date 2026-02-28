"""
现货REST API测试运行器

运行所有现货REST API测试:
- test_config.py: 获取交易所配置
- test_search_symbols.py: 搜索交易对
- test_klines.py: 获取现货K线数据
- test_quotes.py: 获取现货报价数据
- test_multi_resolution.py: 多分辨率K线数据
- test_validation.py: 格式验证

运行方式:
    python tests/e2e/runners/spot_rest_runner.py

作者: Claude Code
版本: v2.0.0
"""

import sys
from pathlib import Path

# 添加路径
_current = Path(__file__).resolve()
_api_service_root = _current.parent.parent.parent  # runners/ -> tests/e2e/ -> api-service/
_src_path = _api_service_root / "src"
_tests_path = _api_service_root / "tests"

for p in [_src_path, _tests_path]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import asyncio
from tests.e2e.spot.rest.test_config import TestSpotConfig
from tests.e2e.spot.rest.test_search_symbols import TestSpotSearchSymbols
from tests.e2e.spot.rest.test_klines import TestSpotKlines
from tests.e2e.spot.rest.test_quotes import TestSpotQuotes
from tests.e2e.spot.rest.test_multi_resolution import TestSpotMultiResolution
from tests.e2e.spot.rest.test_validation import TestSpotValidation


async def run_all_tests():
    """运行所有现货REST API测试"""
    print("=" * 80)
    print("开始运行现货REST API端到端测试")
    print("=" * 80)

    tests = [
        ("获取交易所配置", TestSpotConfig),
        ("搜索交易对", TestSpotSearchSymbols),
        ("获取现货K线数据", TestSpotKlines),
        ("获取现货报价数据", TestSpotQuotes),
        ("多分辨率K线数据", TestSpotMultiResolution),
        ("格式验证", TestSpotValidation),
    ]

    results = {"passed": 0, "failed": 0, "errors": []}

    for test_name, test_class in tests:
        print(f"\n{'='*60}")
        print(f"测试: {test_name}")
        print(f"{'='*60}")

        test = test_class()
        try:
            async with test:
                await test.connect()

                # 根据测试类调用相应的测试方法
                if hasattr(test, f"test_{test_name.replace(' ', '_').lower()}"):
                    test_method = getattr(test, f"test_{test_name.replace(' ', '_').lower()}")
                    success = await test_method()
                else:
                    success = await test.test_get_spot_klines() if "K线" in test_name else False

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
