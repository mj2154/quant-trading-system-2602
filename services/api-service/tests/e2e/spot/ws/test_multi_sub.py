"""
现货WebSocket测试 - 多订阅管理

测试用例: test_multi_subscription

验证:
1. K线和报价同时订阅成功
2. 能接收到两种类型的数据
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


class TestSpotMultiSubscription(SimpleE2ETestBase):
    """多订阅管理测试"""

    @simple_test
    async def test_multi_subscription(self):
        """测试多订阅管理 - v2.0格式"""
        # v2.0格式订阅键
        subscriptions = ["BINANCE:BTCUSDT@KLINE_1", "BINANCE:BTCUSDT@QUOTES"]

        # 发送订阅请求
        response = await self.client.subscribe(subscriptions)
        if not self.assert_success(response, "多订阅"):
            return False

        # 监听5秒数据
        updates = await self.client.listen_updates(timeout=5)

        if not self.assert_data_received(updates, "多订阅数据"):
            return False

        # 统计不同类型的数据
        kline_count = sum(
            1 for u in updates if "KLINE" in u.get("data", {}).get("subscriptionKey", "")
        )
        quotes_count = sum(
            1 for u in updates if "QUOTES" in u.get("data", {}).get("subscriptionKey", "")
        )

        print(f"K线: {kline_count}, 现货报价: {quotes_count}")

        # 验证数据
        if kline_count == 0:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("多订阅测试: 未接收到KLINE数据")
            return False
        if quotes_count == 0:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("多订阅测试: 未接收到QUOTES数据")
            return False

        # 验证 payload 格式
        if not self.assert_quotes_payload_format(updates, "多订阅测试"):
            return False

        # 验证 K 线 payload 格式
        if not self.assert_kline_payload_format(updates, "多订阅测试", resolution="1"):
            return False

        # 取消所有订阅
        await self.client.unsubscribe()
        return True


async def run_test():
    """独立运行此测试"""
    test = TestSpotMultiSubscription()
    try:
        async with test:
            await test.setup()
            result = await test.test_multi_subscription()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
