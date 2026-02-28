"""
期货WebSocket测试 - 永续合约K线订阅

测试用例: test_perpetual_kline

验证:
1. 永续合约K线订阅请求成功
2. 能接收到永续合约K线实时数据
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


class TestPerpetualKlineSubscription(SimpleE2ETestBase):
    """永续合约K线订阅测试"""

    @simple_test
    async def test_perpetual_kline(self):
        """测试订阅永续合约K线 - v2.0格式"""
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

        # 验证payload格式
        if not self.assert_kline_payload_format(updates, "永续合约K线数据"):
            return False

        print(f"接收{len(updates)}条永续合约K线更新（v2.0格式验证通过）")

        # 取消订阅
        await self.client.unsubscribe(subscriptions)
        return True


async def run_test():
    """独立运行此测试"""
    test = TestPerpetualKlineSubscription()
    try:
        async with test:
            await test.setup()
            result = await test.test_perpetual_kline()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
