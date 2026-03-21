#!/usr/bin/env python3
"""
期货限价单下单测试脚本

功能：
1. 创建期货限价单
2. 追踪订单任务表数据
3. 显示完整的请求/响应流程
"""

import argparse
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
import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# WebSocket 端点
WS_URL = "ws://localhost:8000/ws"

# 数据库连接
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "dbuser",
    "password": "pass",
    "database": "trading_db",
}


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
                    logger.debug(f"跳过不匹配的消息: expected={expected_request_id}, got={msg_request_id}, type={msg_data.get('type')}")
                    continue

            return msg
        except TimeoutError:
            continue

    return None


async def query_order_tasks(conn, request_id: str = None, limit: int = 5):
    """查询订单任务表"""
    if request_id:
        sql = """
            SELECT id, type, request_id, status, payload, result, created_at, updated_at
            FROM order_tasks
            WHERE request_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        rows = await conn.fetch(sql, request_id, limit)
    else:
        sql = """
            SELECT id, type, request_id, status, payload, result, created_at, updated_at
            FROM order_tasks
            ORDER BY created_at DESC
            LIMIT $1
        """
        rows = await conn.fetch(sql, limit)

    return rows


async def print_order_task(conn, task_id: int):
    """打印单个订单任务的详细信息"""
    sql = """
        SELECT id, type, request_id, status, payload, result, created_at, updated_at
        FROM order_tasks
        WHERE id = $1
    """
    row = await conn.fetchrow(sql, task_id)
    if row:
        logger.info(f"=" * 60)
        logger.info(f"订单任务详情 (id={row['id']}):")
        logger.info(f"  type: {row['type']}")
        logger.info(f"  request_id: {row['request_id']}")
        logger.info(f"  status: {row['status']}")
        logger.info(f"  payload: {json.dumps(row['payload'], ensure_ascii=False, indent=2)}")
        logger.info(f"  result: {json.dumps(row['result'], ensure_ascii=False, indent=2)}")
        logger.info(f"  created_at: {row['created_at']}")
        logger.info(f"  updated_at: {row['updated_at']}")
        logger.info(f"=" * 60)
    return row


async def create_futures_limit_order(ws, symbol: str, side: str, quantity: float, price: float) -> dict | None:
    """创建期货限价单，返回订单信息字典"""
    request_id = uuid.uuid4().hex
    new_client_order_id = uuid.uuid4().hex

    is_futures = ".PERP" in symbol.upper()

    order_request = {
        "type": "CREATE_ORDER",
        "requestId": request_id,
        "timestamp": int(time.time() * 1000),
        "data": {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "quantity": quantity,
            "newClientOrderId": new_client_order_id,
            "price": price,
            "timeInForce": "GTC",
        },
    }

    logger.info(f"📝 requestId: {request_id}")
    logger.info(f"📝 newClientOrderId: {new_client_order_id}")
    logger.info(f"📝 市场类型: {'期货' if is_futures else '现货'}")
    logger.info(f"📤 发送限价单请求: {json.dumps(order_request, ensure_ascii=False)}")
    await ws.send(json.dumps(order_request))

    # 等待 ACK（使用 requestId 过滤）
    logger.info("⏳ 等待 ACK...")
    ack_msg = await wait_for_message(ws, timeout=5, expected_request_id=request_id)
    if ack_msg:
        ack_data = json.loads(ack_msg)
        logger.info(f"📥 收到 ACK: {json.dumps(ack_data, ensure_ascii=False)}")
    else:
        logger.error("❌ 未收到 ACK")

    # 等待订单响应（使用 requestId 过滤）
    logger.info("⏳ 等待订单响应...")
    order_msg = await wait_for_message(ws, timeout=30, expected_request_id=request_id)
    if order_msg:
        order_data = json.loads(order_msg)
        logger.info(f"📥 收到订单响应: {json.dumps(order_data, ensure_ascii=False)}")

        if order_data.get("type") == "ORDER_DATA":
            data = order_data.get("data", {})
            result = data.get("result", {})
            order_id = result.get("orderId")
            status = result.get("status", "NEW")

            logger.info(f"✅ 限价单创建成功")
            logger.info(f"   orderId: {order_id}")
            logger.info(f"   symbol: {result.get('symbol')}")
            logger.info(f"   price: {result.get('price')}")
            logger.info(f"   origQty: {result.get('origQty')}")
            logger.info(f"   status: {status}")

            return {
                "requestId": request_id,
                "orderId": order_id,
                "symbol": result.get("symbol"),
                "status": status,
                "price": result.get("price"),
                "origQty": result.get("origQty"),
                "isFutures": is_futures,
            }
        elif order_data.get("type") == "ERROR":
            logger.error(f"❌ 订单创建失败: {order_data.get('data', {}).get('errorMessage')}")
        else:
            logger.warning(f"⚠️ 限价单结果: {order_data.get('type')} - {order_data.get('data', {}).get('errorMessage')}")
    else:
        logger.warning("⚠️ 未收到限价单响应（超时）")

    return None


async def main():
    parser = argparse.ArgumentParser(description="期货限价单下单测试")
    parser.add_argument("--symbol", default="BINANCE:BTCUSDT.PERP", help="交易对符号")
    parser.add_argument("--side", default="BUY", help="方向: BUY/SELL")
    parser.add_argument("--quantity", type=float, default=0.001, help="数量")
    parser.add_argument("--price", type=float, default=None, help="价格（默认市价-500）")
    args = parser.parse_args()

    logger.info("🚀 开始期货限价单下单测试")
    logger.info(f"📡 WebSocket URL: {WS_URL}")
    logger.info(f"📊 参数: symbol={args.symbol}, side={args.side}, quantity={args.quantity}, price={args.price}")

    # 连接数据库
    logger.info("🔌 连接数据库...")
    conn = await asyncpg.connect(**DB_CONFIG)
    logger.info("✅ 数据库连接成功")

    # 查看测试前的任务列表
    logger.info("📋 测试前的订单任务列表:")
    tasks = await query_order_tasks(conn, limit=3)
    for t in tasks:
        logger.info(f"  id={t['id']}, type={t['type']}, request_id={t['request_id']}, status={t['status']}")

    try:
        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=60) as ws:
            logger.info(f"✅ 连接到 {WS_URL}")

            # 如果没有指定价格，先获取报价
            if args.price is None:
                # 先获取报价
                logger.info("⏳ 获取期货报价...")
                quotes_request_id = uuid.uuid4().hex
                quotes_request = {
                    "type": "GET_QUOTES",
                    "requestId": quotes_request_id,
                    "timestamp": int(time.time() * 1000),
                    "data": {
                        "symbols": [args.symbol]
                    },
                }
                await ws.send(json.dumps(quotes_request))

                # 等待报价响应（注意：GET_QUOTES 可能返回 ACK + QUOTES_DATA 两个消息）
                # 先等待 ACK
                ack_msg = await wait_for_message(ws, timeout=5, expected_request_id=quotes_request_id)
                if ack_msg:
                    ack_data = json.loads(ack_msg)
                    logger.info(f"📥 收到 QUOTES ACK: {json.dumps(ack_data, ensure_ascii=False)}")

                # 再等待 QUOTES_DATA
                quotes_msg = await wait_for_message(ws, timeout=10, expected_request_id=quotes_request_id)
                if quotes_msg:
                    quotes_data = json.loads(quotes_msg)
                    logger.info(f"📥 收到报价数据: {json.dumps(quotes_data, ensure_ascii=False)}")

                    quotes_result = quotes_data.get("data", {}).get("quotes", [])
                    if quotes_result:
                        # 处理不同的响应格式
                        quote_item = quotes_result[0]
                        # 格式可能是 {"BINANCE:BTCUSDT.PERP": {...}} 或 {"n": "BINANCE:BTCUSDT.PERP", "v": {...}}
                        symbol_key = args.symbol
                        if symbol_key in quote_item:
                            symbol_data = quote_item[symbol_key]
                        elif "v" in quote_item:
                            symbol_data = quote_item["v"]
                        else:
                            symbol_data = quote_item

                        current_price = symbol_data.get("bid") or symbol_data.get("ask") or symbol_data.get("lp")
                        if current_price:
                            args.price = current_price - 500
                            logger.info(f"📊 当前价格: {current_price}, 下单价格: {args.price}")
                        else:
                            logger.warning("⚠️ 无法获取价格，使用默认价格 70000")
                            args.price = 70000
                else:
                    logger.warning("⚠️ 未获取到报价，使用默认价格 70000")
                    args.price = 70000

            # 创建订单
            logger.info("=" * 60)
            logger.info("开始创建期货限价单...")
            logger.info("=" * 60)

            order_result = await create_futures_limit_order(
                ws, args.symbol, args.side, args.quantity, args.price
            )

            # 等待一下让数据库写入
            await asyncio.sleep(1)

            # 查看测试后的任务列表
            logger.info("📋 测试后的订单任务列表:")
            tasks = await query_order_tasks(conn, limit=5)
            for t in tasks:
                logger.info(f"  id={t['id']}, type={t['type']}, request_id={t['request_id']}, status={t['status']}")

            # 如果有订单结果，打印对应任务详情
            if order_result and order_result.get("requestId"):
                logger.info(f"📋 查找 request_id={order_result['requestId']} 的任务:")
                tasks = await query_order_tasks(conn, request_id=order_result["requestId"], limit=1)
                if tasks:
                    await print_order_task(conn, tasks[0]["id"])
                else:
                    logger.warning(f"⚠️ 未找到 request_id={order_result['requestId']} 的任务")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()
        logger.info("🔌 数据库连接已关闭")


if __name__ == "__main__":
    asyncio.run(main())
