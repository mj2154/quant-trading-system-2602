"""
端到端测试：模拟前端WebSocket连接，观察快速订阅/取消订阅是否会触发连接断开

测试流程：
1. 通过WebSocket连接到后端 (ws://localhost:8000/ws/market)
2. 发送订阅消息（使用v2.0格式）
3. 发送取消订阅消息
4. 观察连接是否断开
"""

import asyncio
import json
import logging

import websockets

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_rapid_subscribe_unsubscribe():
    """
    测试快速订阅和取消订阅是否会触发连接断开

    模拟日志中的行为：
    1. 订阅 ['BINANCE:ETHUSDT@TICKER', 'BINANCE:BTCUSDT@TICKER']
    2. 取消订阅 ['BINANCE:ETHUSDT@TICKER', 'BINANCE:BTCUSDT@TICKER']
    3. 订阅 ['BINANCE:ETHUSDT@KLINE_60']
    4. 订阅 ['BINANCE:ETHUSDT@TICKER']
    5. 检查连接是否断开
    """
    uri = "ws://localhost:8000/ws/market"

    try:
        logger.info("=" * 80)
        logger.info("开始E2E测试：快速订阅/取消订阅操作")
        logger.info("=" * 80)

        # 连接到后端
        logger.info(f"正在连接到 {uri}...")
        async with websockets.connect(uri, ping_interval=10, ping_timeout=30) as websocket:
            logger.info("✅ WebSocket连接成功")

            # 等待连接稳定
            await asyncio.sleep(0.5)

            # 步骤1：订阅两个流
            logger.info("\n" + "=" * 80)
            logger.info("步骤1：订阅 ['BINANCE:ETHUSDT@TICKER', 'BINANCE:BTCUSDT@TICKER']")
            logger.info("=" * 80)
            subscribe_msg_1 = {
                "protocolVersion": "2.0",
                "action": "subscribe",
                "data": {"subscriptions": ["BINANCE:ETHUSDT@TICKER", "BINANCE:BTCUSDT@TICKER"]},
            }
            await websocket.send(json.dumps(subscribe_msg_1))
            logger.info("✅ 已发送订阅消息")

            # 等待响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                logger.info(f"收到响应: {response[:200]}...")
            except TimeoutError:
                logger.warning("⚠️ 订阅响应超时")

            await asyncio.sleep(0.1)

            # 步骤2：取消订阅这两个流
            logger.info("\n" + "=" * 80)
            logger.info("步骤2：取消订阅 ['BINANCE:ETHUSDT@TICKER', 'BINANCE:BTCUSDT@TICKER']")
            logger.info("=" * 80)
            unsubscribe_msg_1 = {
                "protocolVersion": "2.0",
                "action": "unsubscribe",
                "data": {"subscriptions": ["BINANCE:ETHUSDT@TICKER", "BINANCE:BTCUSDT@TICKER"]},
            }
            await websocket.send(json.dumps(unsubscribe_msg_1))
            logger.info("✅ 已发送取消订阅消息")

            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                logger.info(f"收到响应: {response[:200]}...")
            except TimeoutError:
                logger.warning("⚠️ 取消订阅响应超时")

            await asyncio.sleep(0.1)

            # 步骤3：订阅一个新流
            logger.info("\n" + "=" * 80)
            logger.info("步骤3：订阅 ['BINANCE:ETHUSDT@KLINE_60']")
            logger.info("=" * 80)
            subscribe_msg_2 = {
                "protocolVersion": "2.0",
                "action": "subscribe",
                "data": {"subscriptions": ["BINANCE:ETHUSDT@KLINE_60"]},
            }
            await websocket.send(json.dumps(subscribe_msg_2))
            logger.info("✅ 已发送订阅消息")

            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                logger.info(f"收到响应: {response[:200]}...")
            except TimeoutError:
                logger.warning("⚠️ 订阅响应超时")

            await asyncio.sleep(0.1)

            # 步骤4：再订阅一个流
            logger.info("\n" + "=" * 80)
            logger.info("步骤4：订阅 ['BINANCE:ETHUSDT@TICKER']")
            logger.info("=" * 80)
            subscribe_msg_3 = {
                "protocolVersion": "2.0",
                "action": "subscribe",
                "data": {"subscriptions": ["BINANCE:ETHUSDT@TICKER"]},
            }
            await websocket.send(json.dumps(subscribe_msg_3))
            logger.info("✅ 已发送订阅消息")

            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                logger.info(f"收到响应: {response[:200]}...")
            except TimeoutError:
                logger.warning("⚠️ 订阅响应超时")

            # 检查连接状态
            logger.info("\n" + "=" * 80)
            logger.info("检查连接状态...")
            logger.info("=" * 80)

            # 等待一段时间观察
            logger.info("等待3秒观察连接状态...")
            await asyncio.sleep(3)

            # 尝试发送一个ping消息
            logger.info("发送ping消息测试连接...")
            ping_msg = {"action": "ping"}
            await websocket.send(json.dumps(ping_msg))

            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                logger.info(f"✅ 收到ping响应: {response[:100]}...")
                logger.info("✅ 连接仍然活跃")
                return True
            except TimeoutError:
                logger.error("❌ ping响应超时，连接可能已断开")
                return False

    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"❌ WebSocket连接已关闭: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 测试过程中发生异常: {e}", exc_info=True)
        return False


async def test_multiple_pair_switches():
    """
    测试多次切换交易对
    """
    uri = "ws://localhost:8000/ws/market"

    try:
        logger.info("\n" + "=" * 80)
        logger.info("开始E2E测试：多次切换交易对")
        logger.info("=" * 80)

        async with websockets.connect(uri, ping_interval=10, ping_timeout=30) as websocket:
            logger.info("✅ WebSocket连接成功")
            await asyncio.sleep(0.5)

            # 连续切换多次
            pairs = [
                "BINANCE:BTCUSDT",
                "BINANCE:ETHUSDT",
                "BINANCE:LTCUSDT",
                "BINANCE:XRPUSDT",
                "BINANCE:BNBUSDT",
            ]

            for i in range(5):
                logger.info(f"\n切换到交易对 {i + 1}: {pairs[i % len(pairs)]}")

                # 订阅
                subscribe_msg = {
                    "protocolVersion": "2.0",
                    "action": "subscribe",
                    "data": {"subscriptions": [f"{pairs[i % len(pairs)]}@TICKER"]},
                }
                await websocket.send(json.dumps(subscribe_msg))
                await asyncio.sleep(0.05)

                # 取消订阅
                unsubscribe_msg = {
                    "protocolVersion": "2.0",
                    "action": "unsubscribe",
                    "data": {"subscriptions": [f"{pairs[i % len(pairs)]}@TICKER"]},
                }
                await websocket.send(json.dumps(unsubscribe_msg))
                await asyncio.sleep(0.05)

                # 订阅新交易对
                new_pair = pairs[(i + 1) % len(pairs)]
                subscribe_msg_2 = {
                    "protocolVersion": "2.0",
                    "action": "subscribe",
                    "data": {"subscriptions": [f"{new_pair}@TICKER"]},
                }
                await websocket.send(json.dumps(subscribe_msg_2))
                await asyncio.sleep(0.05)

            logger.info("✅ 完成5次交易对切换")

            # 检查连接状态
            await asyncio.sleep(2)
            logger.info("检查连接状态...")

            try:
                # 发送ping
                ping_msg = {"action": "ping"}
                await websocket.send(json.dumps(ping_msg))
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                logger.info("✅ 收到ping响应，连接正常")
                return True
            except TimeoutError:
                logger.error("❌ ping响应超时，连接已断开")
                return False

    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"❌ WebSocket连接已关闭: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 测试过程中发生异常: {e}", exc_info=True)
        return False


async def main():
    """运行所有E2E测试"""
    logger.info("=" * 80)
    logger.info("WebSocket连接E2E测试")
    logger.info("测试目的：验证快速订阅/取消订阅是否会触发连接断开")
    logger.info("=" * 80)

    # 测试1：快速顺序操作
    success1 = await test_rapid_subscribe_unsubscribe()

    # 等待一段时间
    await asyncio.sleep(2)

    # 测试2：多次切换交易对
    success2 = await test_multiple_pair_switches()

    # 输出测试结果
    logger.info("\n" + "=" * 80)
    logger.info("测试结果汇总")
    logger.info("=" * 80)
    logger.info(f"测试1（快速订阅/取消订阅）: {'✅ 通过' if success1 else '❌ 失败'}")
    logger.info(f"测试2（多次切换交易对）: {'✅ 通过' if success2 else '❌ 失败'}")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
