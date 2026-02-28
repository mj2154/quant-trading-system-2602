"""
期货WebSocket测试 - 多期货订阅

测试用例: test_multi_futures_subscription

验证:
1. 多期货订阅请求成功
2. 能接收到K线和报价数据
3. 订阅管理正常工作

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


class TestMultiFuturesSubscription(SimpleE2ETestBase):
    """多期货订阅测试"""

    @simple_test
    async def test_multi_futures_subscription(self):
        """测试多期货订阅 - v2.0格式"""
        # v2.0格式订阅键列表
        subscriptions = [
            "BINANCE:BTCUSDT.PERP@KLINE_1",
            "BINANCE:ETHUSDT.PERP@KLINE_1",
            "BINANCE:BTCUSDT.PERP@QUOTES",
            "BINANCE:ETHUSDT.PERP@QUOTES",
        ]

        # 发送订阅请求
        response = await self.client.subscribe(subscriptions)
        if not self.assert_success(response, "多期货订阅"):
            return False

        # 监听5秒数据
        updates = await self.client.listen_updates(timeout=5)

        if not self.assert_data_received(updates, "多期货数据"):
            return False

        # 统计不同类型的数据
        kline_count = sum(
            1 for u in updates if "KLINE" in u.get("data", {}).get("subscriptionKey", "")
        )
        quotes_count = sum(
            1 for u in updates if "QUOTES" in u.get("data", {}).get("subscriptionKey", "")
        )

        print(f"K线: {kline_count}, 期货报价: {quotes_count}")

        # 验证数据
        if kline_count == 0:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("多期货订阅测试: 未接收到KLINE数据")
            return False
        if quotes_count == 0:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("多期货订阅测试: 未接收到QUOTES数据")
            return False

        # 验证K线payload格式
        if not self.assert_kline_payload_format(updates, "多期货订阅测试"):
            return False

        # 验证QUOTES payload格式
        if not self.assert_quotes_payload_format(updates, "多期货订阅测试"):
            return False

        # 取消所有订阅
        await self.client.unsubscribe()
        return True


async def run_test():
    """独立运行此测试"""
    test = TestMultiFuturesSubscription()
    try:
        async with test:
            await test.setup()
            result = await test.test_multi_futures_subscription()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
