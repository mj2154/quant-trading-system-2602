#!/usr/bin/env python3
"""
期货E2E测试套件运行器

执行所有期货WebSocket和REST API测试：
- WebSocket测试: ws/test_*.py
- REST API测试: rest/test_*.py

用法:
    cd /home/ppadmin/code/quant-trading-system/services/api-service
    uv run python tests/e2e/futures/run_all_tests.py

作者: Claude Code
版本: v1.0.0
"""

import asyncio
import sys
import importlib.util
from pathlib import Path

# 添加 api-service 根目录到路径
_api_service_root = Path(__file__).resolve().parent.parent.parent
_src_path = _api_service_root / "src"
_tests_path = _api_service_root / "tests"

for p in [_src_path, _tests_path]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def import_module_from_file(module_name: str, file_path: str):
    """从文件路径动态导入模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# 动态导入期货测试模块
_futures_dir = Path(__file__).parent

# WebSocket 测试模块
test_perpetual_kline_sub = import_module_from_file(
    "test_perpetual_kline_sub",
    str(_futures_dir / "ws" / "test_perpetual_kline_sub.py")
)
TestPerpetualKlineSubscription = test_perpetual_kline_sub.TestPerpetualKlineSubscription

test_futures_quotes_sub = import_module_from_file(
    "test_futures_quotes_sub",
    str(_futures_dir / "ws" / "test_futures_quotes_sub.py")
)
TestFuturesQuotesSubscription = test_futures_quotes_sub.TestFuturesQuotesSubscription

test_multi_futures_sub = import_module_from_file(
    "test_multi_futures_sub",
    str(_futures_dir / "ws" / "test_multi_futures_sub.py")
)
TestMultiFuturesSubscription = test_multi_futures_sub.TestMultiFuturesSubscription

# REST API 测试模块
test_perpetual_klines = import_module_from_file(
    "test_perpetual_klines",
    str(_futures_dir / "rest" / "test_perpetual_klines.py")
)
TestPerpetualKlines = test_perpetual_klines.TestPerpetualKlines

test_continuous_klines = import_module_from_file(
    "test_continuous_klines",
    str(_futures_dir / "rest" / "test_continuous_klines.py")
)
TestContinuousKlines = test_continuous_klines.TestContinuousKlines

test_futures_quotes = import_module_from_file(
    "test_futures_quotes",
    str(_futures_dir / "rest" / "test_futures_quotes.py")
)
TestFuturesQuotes = test_futures_quotes.TestFuturesQuotes

test_multi_resolution = import_module_from_file(
    "test_multi_resolution",
    str(_futures_dir / "rest" / "test_multi_resolution.py")
)
TestFuturesMultiResolution = test_multi_resolution.TestFuturesMultiResolution

test_symbol_validation = import_module_from_file(
    "test_symbol_validation",
    str(_futures_dir / "rest" / "test_symbol_validation.py")
)
TestFuturesSymbolValidation = test_symbol_validation.TestFuturesSymbolValidation

test_price_logic = import_module_from_file(
    "test_price_logic",
    str(_futures_dir / "rest" / "test_price_logic.py")
)
TestFuturesPriceLogic = test_price_logic.TestFuturesPriceLogic

test_perpetual_spot_comparison = import_module_from_file(
    "test_perpetual_spot_comparison",
    str(_futures_dir / "rest" / "test_perpetual_spot_comparison.py")
)
TestPerpetualSpotComparison = test_perpetual_spot_comparison.TestPerpetualSpotComparison


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
    print("期货E2E测试套件")
    print("="*60)

    results = {
        "passed": [],
        "failed": [],
    }

    # WebSocket测试
    ws_tests = [
        (TestPerpetualKlineSubscription, "永续K线订阅"),
        (TestFuturesQuotesSubscription, "期货报价订阅"),
        (TestMultiFuturesSubscription, "多期货订阅"),
    ]

    # REST API测试
    rest_tests = [
        (TestPerpetualKlines, "永续合约K线"),
        (TestContinuousKlines, "连续合约K线"),
        (TestFuturesQuotes, "期货报价数据"),
        (TestFuturesMultiResolution, "多分辨率期货K线"),
        (TestFuturesSymbolValidation, "交易对格式验证"),
        (TestFuturesPriceLogic, "价格逻辑验证"),
        (TestPerpetualSpotComparison, "永续与现货价格对比"),
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
