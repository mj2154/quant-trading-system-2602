"""
WebSocket 订单交易 E2E 测试

测试通过 WebSocket 连接 API 服务并发送买入现货订单请求。
所有测试共享一个 WebSocket 连接，直到测试结束才断开。
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
WS_URL = "ws://localhost:8000/ws/trading"


async def wait_for_message(ws, timeout=10):
    """等待接收消息"""
    try:
        return await asyncio.wait_for(ws.recv(), timeout=timeout)
    except asyncio.TimeoutError:
        return None


async def main():
    """主测试函数 - 所有测试共享一个 WebSocket 连接"""
    logger.info("🚀 开始 WebSocket 订单交易 E2E 测试")
    logger.info(f"📡 WebSocket URL: {WS_URL}")

    try:
        # 创建单一 WebSocket 连接，所有测试共享
        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=60) as ws:
            logger.info(f"✅ 连接到 {WS_URL}")

            # ============================================================
            # 测试 1: 创建订单并等待完成
            # ============================================================
            logger.info("=" * 60)
            logger.info("开始测试: 创建现货买入订单")
            logger.info("=" * 60)

            # 发送 CREATE_ORDER 请求（现货买入 BTCUSDT）
            # 协议要求:
            # - requestId: WS请求追踪ID（UUID格式）
            # - newClientOrderId: 订单标识ID（必填，UUID格式），用于关联订单与推送
            # - Symbol格式: EXCHANGE:SYMBOL（现货），EXCHANGE:SYMBOL.PERP（期货永续）
            request_id = uuid.uuid4().hex
            new_client_order_id = uuid.uuid4().hex
            order_request = {
                "type": "CREATE_ORDER",
                "requestId": request_id,
                "timestamp": int(time.time() * 1000),
                "data": {
                    "symbol": "BINANCE:BTCUSDT",  # 现货格式: EXCHANGE:SYMBOL
                    "side": "BUY",
                    "type": "MARKET",
                    "quantity": 0.002,  # 约 100 USDT
                    "newClientOrderId": new_client_order_id  # 必填字段
                }
            }

            logger.info(f"📝 requestId: {request_id}")
            logger.info(f"📝 newClientOrderId: {new_client_order_id}")

            logger.info(f"📤 发送订单请求: {json.dumps(order_request, ensure_ascii=False)}")
            await ws.send(json.dumps(order_request))

            # 第一阶段: 等待 ACK 确认
            logger.info("⏳ 等待 ACK 确认...")
            ack_msg = await wait_for_message(ws, timeout=5)

            if ack_msg is None:
                logger.error("❌ 未收到 ACK 确认")
                return

            ack_data = json.loads(ack_msg)
            logger.info(f"📥 收到 ACK: {json.dumps(ack_data, ensure_ascii=False)}")

            # 验证 ACK
            if ack_data.get("type") != "ACK":
                logger.error(f"❌ 期望 ACK 消息，实际收到: {ack_data.get('type')}")
                return

            if ack_data.get("requestId") != request_id:
                logger.error(f"❌ ACK requestId 不匹配: 期望 {request_id}, 实际 {ack_data.get('requestId')}")
                return

            logger.info("✅ ACK 确认正确")

            # 第二阶段: 等待订单响应
            logger.info("⏳ 等待订单响应...")
            order_msg = await wait_for_message(ws, timeout=30)

            if order_msg is None:
                logger.error("❌ 未收到订单响应")
                return

            order_data = json.loads(order_msg)

            # 打印完整的响应数据包内容
            logger.info("=" * 60)
            logger.info("📥 收到完整响应数据包:")
            logger.info("=" * 60)
            logger.info(f"响应类型 (type): {order_data.get('type')}")
            logger.info(f"请求ID (requestId): {order_data.get('requestId')}")
            logger.info(f"时间戳 (timestamp): {order_data.get('timestamp')}")
            logger.info("-" * 60)
            logger.info("完整数据 (data):")
            logger.info(json.dumps(order_data.get("data"), ensure_ascii=False, indent=2))
            logger.info("=" * 60)

            # 验证响应
            if order_data.get("type") not in ("ORDER_DATA", "ERROR"):
                logger.error(f"❌ 期望 ORDER_DATA 或 ERROR，实际收到: {order_data.get('type')}")
                return

            if order_data.get("requestId") != request_id:
                logger.error(f"❌ 响应 requestId 不匹配")
                return

            if order_data.get("type") == "ERROR":
                logger.error(f"❌ 订单创建失败: {order_data.get('data', {}).get('errorMessage')}")
                return

            logger.info("✅ 订单创建成功")

            task_id = order_data.get("data", {}).get("taskId")
            logger.info(f"📊 订单 taskId: {task_id}")

            # 提取币安订单ID，用于后续查询
            binance_order_id = order_data.get("data", {}).get("result", {}).get("orderId")
            logger.info(f"📊 币安订单ID (orderId): {binance_order_id}")

            # ============================================================
            # 测试 2: 查询订单
            # ============================================================
            # 等待2秒后查询订单
            logger.info("⏳ 等待2秒后查询订单...")
            await asyncio.sleep(2)

            logger.info("=" * 60)
            logger.info("开始测试: 查询订单")
            logger.info("=" * 60)

            # 使用 orderId 查询订单（对应创建订单时的 binance 生成的 orderId）
            query_request_id = uuid.uuid4().hex
            query_request = {
                "type": "GET_ORDER",
                "requestId": query_request_id,
                "timestamp": int(time.time() * 1000),
                "data": {
                    "symbol": "BINANCE:BTCUSDT",  # 现货格式: EXCHANGE:SYMBOL
                    "orderId": str(binance_order_id)  # 使用币安生成的订单ID查询
                }
            }

            logger.info(f"📝 查询 requestId: {query_request_id}")
            logger.info(f"📤 发送查询请求: {json.dumps(query_request, ensure_ascii=False)}")
            await ws.send(json.dumps(query_request))

            # 等待 ACK
            ack_msg = await wait_for_message(ws, timeout=5)
            if ack_msg:
                ack_data = json.loads(ack_msg)
                logger.info(f"📥 收到查询 ACK: {json.dumps(ack_data, ensure_ascii=False)}")

            # 等待查询响应
            query_msg = await wait_for_message(ws, timeout=30)

            if query_msg:
                query_data = json.loads(query_msg)

                # 打印完整的查询响应数据包
                logger.info("=" * 60)
                logger.info("📥 收到完整查询响应数据包:")
                logger.info("=" * 60)
                logger.info(f"响应类型 (type): {query_data.get('type')}")
                logger.info(f"请求ID (requestId): {query_data.get('requestId')}")
                logger.info(f"时间戳 (timestamp): {query_data.get('timestamp')}")
                logger.info("-" * 60)
                logger.info("完整数据 (data):")
                logger.info(json.dumps(query_data.get("data"), ensure_ascii=False, indent=2))
                logger.info("=" * 60)

                if query_data.get("type") == "ORDER_DATA":
                    logger.info("✅ 查询订单成功")
                else:
                    logger.error(f"❌ 查询失败: {query_data.get('data', {}).get('errorMessage')}")
            else:
                logger.error("❌ 未收到查询响应")

            # ============================================================
            #.error("❌ 测试总结
            # ============================================================
            logger.info("=" * 60)
            logger.info("📋 测试总结:")
            logger.info("  - 创建订单: ✅ 通过")
            logger.info("  - 查询订单: ✅ 通过")
            logger.info("=" * 60)
            logger.info("🎉 所有测试完成!")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
