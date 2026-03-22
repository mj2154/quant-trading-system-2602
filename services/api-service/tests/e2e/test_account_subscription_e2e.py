"""
现货账户订阅 E2E 测试（纯监听模式）

测试通过 WebSocket 连接 API 服务，订阅现货账户信息，
然后监听 30 秒，期间用户手动下单，验证是否能收到账户更新推送。

测试流程：
1. 连接 WebSocket
2. 获取初始账户信息
3. 订阅现货账户: BINANCE:SPOT@ACCOUNT
4. 监听 30 秒（用户在此时手动下单）
5. 验证账户更新事件

参考文档：
- docs/backend/design/VERIFICATION_REPORT_USER_STREAM.md - 现货 WS API 账户订阅验证
- docs/backend/design/07-websocket-protocol.md - WS协议规范
"""

import asyncio
import json
import logging
import sys
import time
import uuid
from pathlib import Path

# 添加 src 目录到路径
_api_service_root = Path(__file__).resolve().parent.parent
_src_path = _api_service_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket 端点
WS_URL = "ws://localhost:8000/ws"

# 账户订阅键
SPOT_ACCOUNT_SUBSCRIPTION = "BINANCE:SPOT@ACCOUNT"


async def wait_for_message(ws, timeout=10, expected_request_id: str | None = None):
    """等待接收消息，可选过滤指定 requestId 的消息"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=1)
            msg_data = json.loads(msg)

            if expected_request_id is not None:
                msg_request_id = msg_data.get("requestId")
                if msg_request_id != expected_request_id:
                    logger.debug(f"跳过不匹配的消息: expected={expected_request_id}, got={msg_request_id}")
                    continue

            return msg
        except asyncio.TimeoutError:
            continue

    return None


async def subscribe_account(ws, subscription: str) -> bool:
    """订阅账户信息

    订阅采用三阶段模式：
    1. 发送请求后立即收到 ACK
    2. 继续等待直到收到 SUBSCRIPTION_DATA 或成功响应
    """
    request_id = uuid.uuid4().hex

    subscribe_request = {
        "type": "SUBSCRIBE",
        "requestId": request_id,
        "timestamp": int(time.time() * 1000),
        "data": {
            "subscriptions": [subscription]
        },
    }

    logger.info(f"📤 发送订阅请求: {subscription}")
    await ws.send(json.dumps(subscribe_request))

    # 等待 SUBSCRIPTION_DATA 响应（忽略中间的 ACK）
    while True:
        response = await wait_for_message(ws, timeout=30, expected_request_id=request_id)
        if response is None:
            logger.error("❌ 未收到订阅响应")
            return False

        data = json.loads(response)
        msg_type = data.get("type")
        logger.info(f"📥 收到消息类型: {msg_type}")

        if msg_type == "ACK":
            logger.info("📝 收到 ACK，继续等待订阅结果...")
            continue

        if msg_type == "SUBSCRIPTION_DATA":
            status = data.get("data", {}).get("status")
            if status == "success":
                logger.info("✅ 订阅成功")
                return True
            else:
                logger.error(f"❌ 订阅失败: status={status}")
                return False

        if msg_type == "ERROR":
            error_msg = data.get("data", {}).get("errorMessage", "Unknown error")
            logger.error(f"❌ 订阅失败: {error_msg}")
            return False

        if msg_type == "ACK":
            continue

        logger.warning(f"⚠️ 收到意外消息类型: {msg_type}，继续等待")


async def create_market_buy_order(ws, symbol: str, quantity: float) -> str | None:
    """创建市价买单

    Args:
        ws: WebSocket 连接
        symbol: 交易对，如 BTCUSDT
        quantity: 购买数量

    Returns:
        orderId 或 None
    """
    request_id = uuid.uuid4().hex
    new_client_order_id = uuid.uuid4().hex

    # 现货市价买单使用 quantity（数量）
    order_request = {
        "type": "CREATE_ORDER",
        "requestId": request_id,
        "timestamp": int(time.time() * 1000),
        "data": {
            "symbol": symbol,
            "side": "BUY",
            "type": "MARKET",
            "quantity": quantity,
            "newClientOrderId": new_client_order_id,
        },
    }

    logger.info(f"📝 requestId: {request_id}")
    logger.info(f"📝 newClientOrderId: {new_client_order_id}")
    logger.info(f"📤 发送市价买单请求: {json.dumps(order_request, ensure_ascii=False)}")
    await ws.send(json.dumps(order_request))

    # 等待 ACK
    ack_msg = await wait_for_message(ws, timeout=5, expected_request_id=request_id)
    if ack_msg is None:
        logger.error("❌ 未收到 ACK 确认")
        return None

    ack_data = json.loads(ack_msg)
    logger.info(f"📥 收到 ACK: {json.dumps(ack_data, ensure_ascii=False)}")

    if ack_data.get("type") != "ACK":
        logger.error(f"❌ 期望 ACK 消息，实际收到: {ack_data.get('type')}")
        return None

    logger.info("✅ ACK 确认正确")

    # 等待订单响应
    order_msg = await wait_for_message(ws, timeout=30, expected_request_id=request_id)
    if order_msg is None:
        logger.error("❌ 未收到订单响应")
        return None

    order_data = json.loads(order_msg)
    logger.info(f"📥 收到订单响应: {json.dumps(order_data, ensure_ascii=False)}")

    if order_data.get("type") == "ERROR":
        error_msg = order_data.get("data", {}).get("errorMessage", "Unknown error")
        logger.error(f"❌ 订单创建失败: {error_msg}")
        return None

    if order_data.get("type") == "ORDER_DATA":
        result = order_data.get("data", {}).get("result", {})
        order_id = result.get("orderId")
        status = result.get("status")
        executed_qty = result.get("executedQty", "0")
        price = result.get("price", "0")

        logger.info(f"✅ 市价买单创建成功")
        logger.info(f"   orderId: {order_id}")
        logger.info(f"   symbol: {symbol}")
        logger.info(f"   status: {status}")
        logger.info(f"   executedQty: {executed_qty}")
        logger.info(f"   price: {price}")

        return order_id

    return None


async def create_market_sell_order(ws, symbol: str, quantity: float) -> str | None:
    """创建市价卖单

    Args:
        ws: WebSocket 连接
        symbol: 交易对，如 BTCUSDT
        quantity: 卖出数量

    Returns:
        orderId 或 None
    """
    request_id = uuid.uuid4().hex
    new_client_order_id = uuid.uuid4().hex

    order_request = {
        "type": "CREATE_ORDER",
        "requestId": request_id,
        "timestamp": int(time.time() * 1000),
        "data": {
            "symbol": symbol,
            "side": "SELL",
            "type": "MARKET",
            "quantity": quantity,
            "newClientOrderId": new_client_order_id,
        },
    }

    logger.info(f"📝 requestId: {request_id}")
    logger.info(f"📝 newClientOrderId: {new_client_order_id}")
    logger.info(f"📤 发送市价卖单请求: {json.dumps(order_request, ensure_ascii=False)}")
    await ws.send(json.dumps(order_request))

    # 等待 ACK
    ack_msg = await wait_for_message(ws, timeout=5, expected_request_id=request_id)
    if ack_msg is None:
        logger.error("❌ 未收到 ACK 确认")
        return None

    ack_data = json.loads(ack_msg)
    logger.info(f"📥 收到 ACK: {json.dumps(ack_data, ensure_ascii=False)}")

    if ack_data.get("type") != "ACK":
        logger.error(f"❌ 期望 ACK 消息，实际收到: {ack_data.get('type')}")
        return None

    logger.info("✅ ACK 确认正确")

    # 等待订单响应
    order_msg = await wait_for_message(ws, timeout=30, expected_request_id=request_id)
    if order_msg is None:
        logger.error("❌ 未收到订单响应")
        return None

    order_data = json.loads(order_msg)
    logger.info(f"📥 收到订单响应: {json.dumps(order_data, ensure_ascii=False)}")

    if order_data.get("type") == "ERROR":
        error_msg = order_data.get("data", {}).get("errorMessage", "Unknown error")
        logger.error(f"❌ 订单创建失败: {error_msg}")
        return None

    if order_data.get("type") == "ORDER_DATA":
        result = order_data.get("data", {}).get("result", {})
        order_id = result.get("orderId")
        status = result.get("status")

        logger.info(f"✅ 市价卖单创建成功")
        logger.info(f"   orderId: {order_id}")
        logger.info(f"   symbol: {symbol}")
        logger.info(f"   status: {status}")

        return order_id

    return None


async def listen_for_account_updates(ws, timeout: float = 30) -> list[dict]:
    """监听账户更新推送

    Args:
        ws: WebSocket 连接
        timeout: 超时时间（秒）

    Returns:
        收到的账户更新消息列表
    """
    updates: list[dict] = []
    start_time = time.time()

    logger.info(f"🔔 开始监听账户更新推送 (超时: {timeout}秒)...")

    while time.time() - start_time < timeout:
        try:
            message = await asyncio.wait_for(ws.recv(), timeout=1)
            message_dict = json.loads(message)

            # 只处理 UPDATE 类型且是账户订阅的消息
            if message_dict.get("type") == "UPDATE":
                subscription_key = message_dict.get("subscriptionKey")
                if subscription_key == SPOT_ACCOUNT_SUBSCRIPTION:
                    logger.info(f"📥 收到账户更新: {json.dumps(message_dict, ensure_ascii=False)}")
                    updates.append(message_dict)

        except asyncio.TimeoutError:
            continue
        except Exception as e:
            logger.warning(f"监听异常: {e}")
            break

    logger.info(f"🔔 监听结束，共收到 {len(updates)} 条账户更新")
    return updates


async def get_spot_account(ws) -> dict | None:
    """获取现货账户信息

    异步任务采用三阶段模式：
    1. 发送请求后立即收到 ACK
    2. 继续等待直到收到 ACCOUNT_DATA
    """
    request_id = uuid.uuid4().hex

    account_request = {
        "type": "GET_SPOT_ACCOUNT",
        "requestId": request_id,
        "timestamp": int(time.time() * 1000),
        "data": {},
    }

    logger.info(f"📤 发送获取现货账户请求")
    await ws.send(json.dumps(account_request))

    # 等待 ACCOUNT_DATA 响应（忽略中间的 ACK）
    while True:
        response = await wait_for_message(ws, timeout=30, expected_request_id=request_id)
        if response is None:
            logger.error("❌ 未收到账户信息响应")
            return None

        data = json.loads(response)
        msg_type = data.get("type")
        logger.info(f"📥 收到消息类型: {msg_type}")

        if msg_type == "ACK":
            logger.info("📝 收到 ACK，继续等待 ACCOUNT_DATA...")
            continue

        if msg_type == "ACCOUNT_DATA":
            logger.info(f"📥 收到现货账户响应")
            return data.get("data", {}).get("account", {})

        if msg_type == "ERROR":
            logger.error(f"❌ 获取账户信息失败: {data}")
            return None

        logger.warning(f"⚠️ 收到意外消息类型: {msg_type}，继续等待")


async def main():
    """主测试函数 - 纯监听模式

    测试流程：
    1. 连接 WebSocket
    2. 获取初始账户信息
    3. 订阅现货账户
    4. 监听 30 秒，用户在此期间手动下单
    5. 验证是否收到账户更新推送
    """
    logger.info("=" * 60)
    logger.info("🚀 现货账户订阅 E2E 测试（纯监听模式）")
    logger.info(f"📡 WebSocket URL: {WS_URL}")
    logger.info(f"📊 订阅键: {SPOT_ACCOUNT_SUBSCRIPTION}")
    logger.info("⏱️  监听时长: 30 秒")
    logger.info("💡 请在 30 秒内通过币安 App 或其他渠道手动下单")
    logger.info("=" * 60)

    test_passed = False
    account_updates: list[dict] = []
    subscribe_success = False

    try:
        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=60) as ws:
            logger.info(f"✅ 连接到 {WS_URL}")

            # Step 1: 获取初始账户信息
            logger.info("=" * 60)
            logger.info("Step 1: 获取初始账户信息")
            logger.info("=" * 60)
            initial_account = await get_spot_account(ws)
            if initial_account:
                initial_balances = initial_account.get("account", {}).get("balances", [])
                logger.info(f"✅ 初始账户信息获取成功")
                for b in initial_balances:
                    if float(b.get("free", 0)) > 0 or float(b.get("locked", 0)) > 0:
                        logger.info(f"   {b.get('asset')}: free={b.get('free')}, locked={b.get('locked')}")
            else:
                logger.warning("⚠️ 初始账户信息获取失败，继续测试")

            # Step 2: 订阅现货账户
            logger.info("=" * 60)
            logger.info("Step 2: 订阅现货账户")
            logger.info("=" * 60)
            subscribe_success = await subscribe_account(ws, SPOT_ACCOUNT_SUBSCRIPTION)
            if not subscribe_success:
                logger.error("❌ 订阅失败，测试终止")
                return

            # Step 3: 启动账户更新监听（等待 30 秒）
            logger.info("=" * 60)
            logger.info("Step 3: 开始监听账户更新 (30 秒)")
            logger.info("💡 请在此期间手动下单...")
            logger.info("=" * 60)

            account_updates = await listen_for_account_updates(ws, timeout=30)

            # Step 4: 验证结果
            logger.info("=" * 60)
            logger.info("Step 4: 验证结果")
            logger.info("=" * 60)

            if len(account_updates) > 0:
                logger.info(f"✅ 测试通过！共收到 {len(account_updates)} 条账户更新")

                # 检查事件类型
                # 消息结构（使用 alias 输出币安原始短字段名）:
                # {
                #     "type": "UPDATE",
                #     "timestamp": 1704067205000,
                #     "subscriptionKey": "BINANCE:SPOT@ACCOUNT",
                #     "content": {
                #         "e": "outboundAccountPosition",  // 币安原始事件类型（alias）
                #         "E": 1564034571105,
                #         "u": 1564034571073,
                #         "B": [...]
                #     }
                # }
                event_types = set()
                for update in account_updates:
                    content = update.get("content", {})
                    # 使用 alias，字段名为 "e"（不是 "eventType"）
                    event_type = content.get("e", "unknown")
                    event_types.add(event_type)
                    logger.debug(f"提取事件类型: {event_type}")

                logger.info(f"📊 收到的事件类型: {event_types}")

                # 验证是否包含预期的事件类型
                expected_events = {"executionReport", "outboundAccountPosition", "balanceUpdate"}
                actual_events = event_types & expected_events
                if actual_events:
                    logger.info(f"✅ 收到预期的事件: {actual_events}")
                    test_passed = True
                else:
                    logger.error(f"❌ 未收到预期的事件类型，收到: {event_types}")
            else:
                logger.error("❌ 未收到任何账户更新，测试失败")

    except Exception as e:
        logger.error(f"测试异常: {e}")
        import traceback
        traceback.print_exc()

    # 测试总结
    logger.info("=" * 60)
    logger.info("📋 测试总结:")
    logger.info(f"  - WebSocket 连接: ✅")
    logger.info(f"  - 账户订阅: {'✅' if subscribe_success else '❌'}")
    logger.info(f"  - 账户更新推送: {'✅' if len(account_updates) > 0 else '❌'}")
    logger.info(f"  - 总体结果: {'✅ 通过' if test_passed else '❌ 失败'}")
    logger.info("=" * 60)

    if not test_passed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
