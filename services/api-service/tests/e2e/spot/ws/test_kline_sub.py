"""
现货WebSocket测试 - K线订阅

测试用例: test_kline_subscription

验证:
1. K线订阅请求成功
2. 能接收到K线实时数据
3. 数据格式正确

用法: 直接运行此文件即可
    python tests/e2e/spot/ws/test_kline_sub.py

作者: Claude Code
版本: v2.0.0
"""

import sys
from pathlib import Path

# 计算 api-service 根目录
# 路径: services/api-service/tests/e2e/spot/ws/test_kline_sub.py
# 需要向上 5 级: ws -> spot -> e2e -> tests -> api-service
_api_service_root = Path(__file__).resolve().parent.parent.parent.parent.parent
_src_path = _api_service_root / "src"
_tests_path = _api_service_root

# 显式添加路径，确保导入正确
for p in [_src_path, _tests_path]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# 验证路径计算是否正确
_debug = False
if _debug:
    print(f"[DEBUG] __file__ = {Path(__file__).resolve()}")
    print(f"[DEBUG] _api_service_root = {_api_service_root}")
    print(f"[DEBUG] _tests_path = {_tests_path}")
    print(f"[DEBUG] sys.path[:3] = {sys.path[:3]}")

import asyncio
from tests.e2e.base_simple_test import SimpleE2ETestBase, simple_test


class TestSpotKlineSubscription(SimpleE2ETestBase):
    """现货K线订阅测试"""

    @simple_test
    async def test_kline_subscription(self):
        """测试订阅K线实时数据"""
        # v2.0格式订阅键数组
        subscriptions = ["BINANCE:BTCUSDT@KLINE_1"]

        # 发送订阅请求
        response = await self.client.subscribe(subscriptions)
        if not self.assert_success(response, "K线订阅"):
            return False

        # 监听5秒数据
        updates = await self.client.listen_updates(timeout=5)

        if not self.assert_data_received(updates, "K线数据"):
            return False

        # 验证K线 payload 格式符合架构规范
        if not self.assert_kline_payload_format(updates, "K线数据", resolution="1"):
            return False

        print(f"接收{len(updates)}条K线更新（格式验证通过）")

        # 取消订阅
        await self.client.unsubscribe(subscriptions)
        return True


async def run_test():
    """独立运行此测试"""
    test = TestSpotKlineSubscription()
    try:
        async with test:
            await test.setup()
            result = await test.test_kline_subscription()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
