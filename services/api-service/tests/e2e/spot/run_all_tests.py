#!/usr/bin/env python3
"""
现货E2E测试套件运行器

执行所有现货WebSocket和REST API测试：
- WebSocket测试: ws/test_*.py
- REST API测试: rest/test_*.py

用法:
    python run_all_tests.py

作者: Claude Code
版本: v1.0.0
"""

import asyncio
import sys
from pathlib import Path

# 添加 api-service 根目录到路径
_api_service_root = Path(__file__).resolve().parent
_src_path = _api_service_root / "src"
_tests_path = _api_service_root / "tests"

for p in [_src_path, _tests_path]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


# 导入测试模块
from tests.e2e.spot.ws.test_kline_sub import TestSpotKlineSubscription
from tests.e2e.spot.ws.test_quotes_sub import TestSpotQuotesSubscription
from tests.e2e.spot.ws.test_multi_sub import TestSpotMultiSubscription
from tests.e2e.spot.ws.test_quotes_multi import TestSpotQuotesMultiSymbol

from tests.e2e.spot.rest.test_config import TestSpotConfig
from tests.e2e.spot.rest.test_search_symbols import TestSpotSearchSymbols
from tests.e2e.spot.rest.test_klines import TestSpotKlines
from tests.e2e.spot.rest.test_quotes import TestSpotQuotes
from tests.e2e.spot.rest.test_multi_resolution import TestSpotMultiResolution
from tests.e2e.spot.rest.test_validation import TestSpotValidation


def get_first_test_method(test_instance):
    """获取测试类的第一个测试方法（跳过test_results等属性）"""
    for name in dir(test_instance):
        if name.startswith('test_'):
            attr = getattr(test_instance, name)
            # 跳过非可调用对象（如test_results字典）
            if callable(attr) and not isinstance(attr, dict):
                return name
    return None


async def run_ws_test(test_class, test_name: str):
    """运行WebSocket测试"""
    print(f"\n{'='*60}")
    print(f"运行WebSocket测试: {test_name}")
    print(f"{'='*60}")

    test = test_class()
    try:
        async with test:
            await test.setup()
            # 获取测试方法
            method_name = get_first_test_method(test)
            if not method_name:
                raise ValueError(f"未找到 {test_name} 的测试方法")
            test_method = getattr(test, method_name)
            result = await test_method()
            return result
    except Exception as e:
        import traceback
        print(f"  [ERROR] 测试执行失败: {e!s}")
        traceback.print_exc()
        return False


async def run_rest_test(test_class, test_name: str):
    """运行REST API测试"""
    print(f"\n{'='*60}")
    print(f"运行REST API测试: {test_name}")
    print(f"{'='*60}")

    test = test_class()
    try:
        async with test:
            await test.connect()
            # 获取测试方法
            method_name = get_first_test_method(test)
            if not method_name:
                raise ValueError(f"未找到 {test_name} 的测试方法")
            test_method = getattr(test, method_name)
            result = await test_method()
            return result
    except Exception as e:
        import traceback
        print(f"  [ERROR] 测试执行失败: {e!s}")
        traceback.print_exc()
        return False


async def main():
    """主测试运行函数"""
    print("\n" + "="*60)
    print("现货E2E测试套件")
    print("="*60)

    results = {
        "passed": [],
        "failed": [],
    }

    # WebSocket测试
    ws_tests = [
        (TestSpotKlineSubscription, "K线订阅"),
        (TestSpotQuotesSubscription, "报价订阅"),
        (TestSpotMultiSubscription, "多数据类型订阅"),
        (TestSpotQuotesMultiSymbol, "多符号报价订阅"),
    ]

    # REST API测试
    rest_tests = [
        (TestSpotConfig, "交易所配置"),
        (TestSpotSearchSymbols, "交易对搜索"),
        (TestSpotKlines, "K线数据"),
        (TestSpotQuotes, "报价数据"),
        (TestSpotMultiResolution, "多分辨率K线"),
        (TestSpotValidation, "参数验证"),
    ]

    # 运行WebSocket测试
    print("\n" + "-"*60)
    print("WebSocket 测试")
    print("-"*60)

    for test_class, test_name in ws_tests:
        try:
            result = await run_ws_test(test_class, test_name)
            if result:
                results["passed"].append(test_name)
            else:
                results["failed"].append(test_name)
        except Exception as e:
            print(f"  [ERROR] {test_name}: {e!s}")
            results["failed"].append(test_name)

    # 运行REST API测试
    print("\n" + "-"*60)
    print("REST API 测试")
    print("-"*60)

    for test_class, test_name in rest_tests:
        try:
            result = await run_rest_test(test_class, test_name)
            if result:
                results["passed"].append(test_name)
            else:
                results["failed"].append(test_name)
        except Exception as e:
            print(f"  [ERROR] {test_name}: {e!s}")
            results["failed"].append(test_name)

    # 打印汇总
    print("\n" + "="*60)
    print("测试汇总")
    print("="*60)
    print(f"通过: {len(results['passed'])}/{len(results['passed']) + len(results['failed'])}")
    print(f"失败: {len(results['failed'])}/{len(results['passed']) + len(results['failed'])}")

    if results["passed"]:
        print("\n通过的测试:")
        for name in results["passed"]:
            print(f"  [PASS] {name}")

    if results["failed"]:
        print("\n失败的测试:")
        for name in results["failed"]:
            print(f"  [FAIL] {name}")

    return len(results["failed"]) == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
