"""
简化的期货WebSocket端到端测试

只保留3个核心测试用例，快速验证基本功能。
特点：
- 5秒快速验证
- 最小化打印信息
- 简化验证逻辑

测试覆盖：
1. 订阅永续合约K线
2. 订阅期货报价
3. 多期货订阅管理

作者: Claude Code
版本: v1.0.0
"""

import asyncio

from tests.e2e.base_simple_test import SimpleE2ETestBase, simple_test


class TestFuturesWebSocketE2E(SimpleE2ETestBase):
    """简化的期货WebSocket测试"""

    @simple_test
    async def test_perpetual_kline(self):
        """测试订阅永续合约K线（快速版） - v2.0格式"""
        # v2.0格式订阅键
        subscriptions = ["BINANCE:BTCUSDT.PERP@KLINE_1"]

        # 发送订阅请求
        response = await self.client.subscribe(subscriptions)
        if not self.assert_success(response, "永续合约K线订阅"):
            return False

        # 监听5秒数据
        updates = await self.client.listen_updates(timeout=5)

        if not self.assert_data_received(updates, "永续合约K线数据"):
            return False

        print(f"  📊 接收{len(updates)}条永续合约K线更新")

        # 取消订阅
        await self.client.unsubscribe(subscriptions)
        return True

    @simple_test
    async def test_futures_quotes(self):
        """测试订阅期货报价（快速版） - v2.0格式"""
        # v2.0格式订阅键
        subscriptions = ["BINANCE:BTCUSDT.PERP@QUOTES"]

        # 发送订阅请求
        response = await self.client.subscribe(subscriptions)
        if not self.assert_success(response, "期货报价订阅"):
            return False

        # 监听5秒数据
        updates = await self.client.listen_updates(timeout=5)

        if not self.assert_data_received(updates, "期货报价数据"):
            return False

        # 验证数据格式
        futures_quotes_count = sum(
            1
            for u in updates
            if "BTCUSDT.PERP@QUOTES" in u.get("data", {}).get("subscriptionKey", "")
        )
        if futures_quotes_count == 0:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("期货报价数据: 未接收到PERP QUOTES格式数据")
            return False

        # 验证payload格式是否符合{n, s, v}结构
        if not self.assert_quotes_payload_format(updates, "期货报价数据"):
            return False

        print(f"  📊 期货报价: {futures_quotes_count}条PERP QUOTES数据（格式验证通过）")

        # 取消订阅
        await self.client.unsubscribe(subscriptions)
        return True

    @simple_test
    async def test_multi_futures_subscription(self):
        """测试多期货订阅（快速版） - v2.0格式"""
        # v2.0格式订阅键
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

        print(f"  📊 K线: {kline_count}, 期货报价: {quotes_count}")

        # 验证数据格式
        if kline_count == 0:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("多期货订阅测试: 未接收到KLINE数据")
            return False
        if quotes_count == 0:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("多期货订阅测试: 未接收到QUOTES数据")
            return False

        # 验证payload格式是否符合{n, s, v}结构
        if not self.assert_quotes_payload_format(updates, "多期货订阅测试"):
            return False

        # 取消所有订阅
        await self.client.unsubscribe()
        return True

    async def run_all_tests(self):
        """运行所有简化测试"""
        print("=" * 60)
        print("🚀 简化版期货WebSocket测试（快速验证）")
        print("=" * 60)

        tests = [
            self.test_perpetual_kline,
            self.test_futures_quotes,
            self.test_multi_futures_subscription,
        ]

        for test in tests:
            await test()

        self.print_summary("期货WebSocket")
        return self.test_results


async def main():
    """主函数"""
    test = TestFuturesWebSocketE2E()

    try:
        async with test:
            await test.run_all_tests()
    except Exception as e:
        print(f"❌ 测试执行失败: {e!s}")


if __name__ == "__main__":
    asyncio.run(main())
