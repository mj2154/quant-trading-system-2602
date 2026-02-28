"""
简化的现货WebSocket端到端测试

只保留4个核心测试用例，快速验证基本功能。
特点：
- 5秒快速验证
- 最小化打印信息
- 简化验证逻辑

测试覆盖：
1. 订阅K线实时数据
2. 订阅现货报价实时数据
3. 订阅多个现货报价实时数据
4. 多订阅管理（K线+现货报价）

作者: Claude Code
版本: v1.1.0
"""

import asyncio

from tests.e2e.base_simple_test import SimpleE2ETestBase, simple_test


class TestSpotWebSocketE2E(SimpleE2ETestBase):
    """简化的现货WebSocket测试"""

    @simple_test
    async def test_kline_subscription(self):
        """测试订阅K线实时数据（快速版） - v2.0格式"""
        # v2.0格式订阅键
        subscriptions = ["BINANCE:BTCUSDT@KLINE_1"]

        # 发送订阅请求
        response = await self.client.subscribe(subscriptions)
        if not self.assert_success(response, "K线订阅"):
            return False

        # 监听5秒数据
        updates = await self.client.listen_updates(timeout=5)

        if not self.assert_data_received(updates, "K线数据"):
            return False

        print(f"  📊 接收{len(updates)}条K线更新")

        # 取消订阅
        await self.client.unsubscribe(subscriptions)
        return True

    @simple_test
    async def test_quotes_subscription(self):
        """测试订阅报价实时数据（快速版） - v2.0格式"""
        # v2.0格式订阅键
        subscriptions = ["BINANCE:BTCUSDT@QUOTES"]

        # 发送订阅请求
        response = await self.client.subscribe(subscriptions)
        if not self.assert_success(response, "现货报价订阅"):
            return False

        # 监听5秒数据
        updates = await self.client.listen_updates(timeout=5)

        if not self.assert_data_received(updates, "现货报价数据"):
            return False

        # 验证数据格式
        quotes_count = sum(
            1 for u in updates if "QUOTES" in u.get("data", {}).get("subscriptionKey", "")
        )
        if quotes_count == 0:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("现货报价数据: 未接收到QUOTES格式数据")
            return False

        # 验证payload格式是否符合{n, s, v}结构
        if not self.assert_quotes_payload_format(updates, "现货报价数据"):
            return False

        print(f"  📊 现货报价: {quotes_count}条QUOTES数据（格式验证通过）")

        # 取消订阅
        await self.client.unsubscribe(subscriptions)
        return True

    @simple_test
    async def test_quotes_subscription_multi_symbol(self):
        """测试订阅多个现货报价实时数据（快速版） - v2.0格式"""
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

        # 验证payload格式是否符合{n, s, v}结构
        if not self.assert_quotes_payload_format(updates, "多现货报价数据"):
            return False

        print(f"  📊 多现货报价: {quotes_count}条QUOTES数据（格式验证通过）")

        # 取消订阅
        await self.client.unsubscribe(subscriptions)
        return True

    @simple_test
    async def test_multi_subscription(self):
        """测试多订阅管理（快速版） - v2.0格式"""
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

        print(f"  📊 K线: {kline_count}, 现货报价: {quotes_count}")

        # 验证数据格式
        if kline_count == 0:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("多订阅测试: 未接收到KLINE数据")
            return False
        if quotes_count == 0:
            self.test_results["failed"] += 1
            self.test_results["errors"].append("多订阅测试: 未接收到QUOTES数据")
            return False

        # 验证payload格式是否符合{n, s, v}结构
        if not self.assert_quotes_payload_format(updates, "多订阅测试"):
            return False

        # 取消所有订阅
        await self.client.unsubscribe()
        return True

    async def run_all_tests(self):
        """运行所有简化测试（连接复用版）"""
        print("=" * 60)
        print("🚀 简化版现货WebSocket测试（快速验证）")
        print("=" * 60)

        tests = [
            self.test_kline_subscription,
            self.test_quotes_subscription,
            self.test_quotes_subscription_multi_symbol,
            self.test_multi_subscription,
        ]

        # 使用上下文管理器只在开始和结束时创建/销毁连接
        async with self:
            for test in tests:
                await test()

        self.print_summary("现货WebSocket")
        return self.test_results


async def main():
    """主函数"""
    test = TestSpotWebSocketE2E()

    try:
        # run_all_tests 内部已处理连接管理
        await test.run_all_tests()
    except Exception as e:
        print(f"❌ 测试执行失败: {e!s}")


if __name__ == "__main__":
    asyncio.run(main())
