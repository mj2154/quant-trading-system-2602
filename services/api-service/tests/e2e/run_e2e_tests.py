"""
端到端测试运行器（简化版）

统一运行所有端到端测试，15秒内完成验证。
特点：
- 15秒内完成所有测试
- 最小化输出
- 清晰的结果展示

使用方法：
1. 运行所有测试: python run_e2e_tests.py
2. 详细模式: python run_e2e_tests.py --verbose
3. 只测试现货: python run_e2e_tests.py --spot-only
4. 只测试期货: python run_e2e_tests.py --futures-only

作者: Claude Code
版本: v1.0.0
"""

import argparse
import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入简化测试
from tests.e2e.test_futures_ws_e2e import TestFuturesWebSocketE2E
from tests.e2e.test_spot_ws_e2e import TestSpotWebSocketE2E


class E2ETestRunner:
    """简化的测试运行器"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: dict[str, Any] = {}
        self.total_passed = 0
        self.total_failed = 0
        self.start_time = None
        self.end_time = None

    def print_header(self):
        """打印头部信息"""
        print("=" * 60)
        print("⚡ E2E测试运行器（简化版）")
        print("=" * 60)
        print(f"开始时间: {datetime.now().strftime('%H:%M:%S')}")
        print(f"模式: {'详细' if self.verbose else '快速'}")
        print("=" * 60)

    def print_suite_start(self, name: str):
        """打印测试套件开始"""
        print(f"\n▶️  运行: {name}")

    def print_suite_end(self, name: str, result: dict[str, Any]):
        """打印测试套件结束"""
        passed = result.get("passed", 0)
        failed = result.get("failed", 0)

        if failed == 0:
            print(f"   ✅ {name}: {passed} 通过")
        else:
            print(f"   ⚠️  {name}: {passed} 通过, {failed} 失败")
            if self.verbose:
                for error in result.get("errors", []):
                    print(f"      ❌ {error}")

    def print_final_summary(self):
        """打印最终总结"""
        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 0

        print("\n" + "=" * 60)
        print("📊 最终测试报告")
        print("=" * 60)
        print(f"总通过: {self.total_passed}")
        print(f"总失败: {self.total_failed}")
        print(f"总耗时: {total_time:.1f}秒")
        print("=" * 60)

    async def run_suite(self, name: str, test_class) -> dict[str, Any]:
        """运行单个测试套件"""
        self.print_suite_start(name)

        test_instance = test_class()

        try:
            async with test_instance:
                result = await test_instance.run_all_tests()
                return result
        except Exception as e:
            print(f"   ❌ {name}: 执行失败 - {e!s}")
            return {"passed": 0, "failed": 1, "errors": [f"测试套件执行失败: {e!s}"]}

    async def run_spot_only(self):
        """只运行现货测试"""
        result = await self.run_suite("现货WebSocket", TestSpotWebSocketE2E)
        self.results["spot"] = result
        self.total_passed += result.get("passed", 0)
        self.total_failed += result.get("failed", 0)
        self.print_suite_end("现货WebSocket", result)

    async def run_futures_only(self):
        """只运行期货测试"""
        result = await self.run_suite("期货WebSocket", TestFuturesWebSocketE2E)
        self.results["futures"] = result
        self.total_passed += result.get("passed", 0)
        self.total_failed += result.get("failed", 0)
        self.print_suite_end("期货WebSocket", result)

    async def run_all(self):
        """运行所有简化测试"""
        self.start_time = time.time()

        # 现货测试
        result1 = await self.run_suite("现货WebSocket", TestSpotWebSocketE2E)
        self.results["spot"] = result1
        self.total_passed += result1.get("passed", 0)
        self.total_failed += result1.get("failed", 0)
        self.print_suite_end("现货WebSocket", result1)

        # 期货测试
        result2 = await self.run_suite("期货WebSocket", TestFuturesWebSocketE2E)
        self.results["futures"] = result2
        self.total_passed += result2.get("passed", 0)
        self.total_failed += result2.get("failed", 0)
        self.print_suite_end("期货WebSocket", result2)

        self.end_time = time.time()
        self.print_final_summary()

        return self.results


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="E2E测试运行器（简化版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python run_e2e_tests.py                      # 运行所有测试
  python run_e2e_tests.py --verbose           # 详细模式
  python run_e2e_tests.py --spot-only         # 只测试现货
  python run_e2e_tests.py --futures-only      # 只测试期货
        """,
    )

    parser.add_argument("--verbose", action="store_true", help="详细模式（显示错误详情）")

    parser.add_argument("--spot-only", action="store_true", help="只运行现货WebSocket测试")

    parser.add_argument("--futures-only", action="store_true", help="只运行期货WebSocket测试")

    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_arguments()
    runner = E2ETestRunner(verbose=args.verbose)

    # 打印头部
    runner.print_header()

    # 确定运行模式
    if args.spot_only:
        await runner.run_spot_only()
    elif args.futures_only:
        await runner.run_futures_only()
    else:
        await runner.run_all()

    # 返回适当的退出码
    return 1 if runner.total_failed > 0 else 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
