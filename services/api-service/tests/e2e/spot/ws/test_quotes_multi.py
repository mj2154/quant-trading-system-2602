"""
现货WebSocket测试 - 多报价订阅

测试用例: test_quotes_subscription_multi_symbol

验证:
1. 多个报价订阅请求成功
2. 能接收到多个报价实时数据
3. 数据格式正确

作者: Claude Code
版本: v2.0.0
"""

import sys
from pathlib import Path

_current = Path(__file__).resolve()
_api_service_root = _current.parent.parent.parent.parent
_src_path = _api_service_root / "src"
_tests_path = _api_service_root / "tests"

for p in [_src_path, _tests_path]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import asyncio
from tests.e2e.base_simple_test import SimpleE2ETestBase, simple_test


class TestSpotQuotesMultiSymbol(SimpleE2ETestBase):
    """多报价订阅测试"""

    @simple_test
    async def test_quotes_subscription_multi_symbol(self):
        """测试订阅多个现货报价实时数据 - v2.0格式"""
        # v2.0格式订阅键
        subscriptions = ["BINANCE:BTCUSDT@QUOTES", "BINANCE:ETHUSDT@QUOTES"]

        # 发送订阅请求
        response = await self.client.subscribe(subscriptions)
        if not self.assert_success(response, "多现货报价订阅"):
            return False

        # 监听5秒数据
        updates = await self.client.listen_updates(timeout=5)

        if not self.assert_data_received(updates, "多现货报价数据"):
            return False

        # 验证数据格式
        quotes_count = sum(
            1 for u in updates if "QUOTES" in u.get("data", {}).get("subscriptionKey", "")
        )
        if quotes_count == 0:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("多现货报价数据: 未接收到QUOTES格式数据")
            return False

        # 验证payload格式
        if not self.assert_quotes_payload_format(updates, "多现货报价数据"):
            return False

        print(f"多现货报价: {quotes_count} 条 QUOTES 数据（格式验证通过，包含 ask/bid/spread）")

        # 取消订阅
        await self.client.unsubscribe(subscriptions)
        return True


async def run_test():
    """独立运行此测试"""
    test = TestSpotQuotesMultiSymbol()
    try:
        async with test:
            await test.setup()
            result = await test.test_quotes_subscription_multi_symbol()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
