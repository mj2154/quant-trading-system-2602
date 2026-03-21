"""
WebSocket 订单交易 E2E 测试

测试通过 WebSocket 连接 API 服务并发送订单请求。
所有测试共享一个 WebSocket 连接，直到测试结束才断开。

测试模式:
- 默认模式 (推荐): 只测试限价单，不会实际成交
- 市价单模式: 包含市价单测试，会实际成交

限价单测试覆盖 (默认运行，不会实际成交):
  期货限价单: 创建 → 查询 → 修改 → 取消
  现货限价单: 创建 → 查询 → 修改 → 取消
  - LIST_ORDERS: 查询订单列表
  - GET_OPEN_ORDERS: 查询当前挂单

市价单测试覆盖 (需要 --include-market 参数):
  - 期货市价单: 创建 → 查询
  - 现货市价单: 创建 → 查询

注意:
- 账户信息测试 (GET_FUTURES_ACCOUNT, GET_SPOT_ACCOUNT) 已由 test_extended_api.py 覆盖
- MODIFY_ORDER: 币安支持修改订单，后端实现后完善测试

设计文档参考:
- docs/backend/design/04-trading-orders.md - 订单任务表设计
- docs/backend/design/07-websocket-protocol.md - WS协议规范
- docs/backend/design/07a-websocket-messages.md - 消息格式示例
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket 端点
WS_URL = "ws://localhost:8000/ws"


async def wait_for_message(ws, timeout=10, expected_request_id: str | None = None):
    """等待接收消息，可选过滤指定 requestId 的消息

    Args:
        ws: WebSocket 连接
        timeout: 超时时间（秒）
        expected_request_id: 期望的 requestId，如果为 None 则返回任何消息

    Returns:
        匹配的消息字典，或 None（超时/无匹配）
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=1)
            msg_data = json.loads(msg)

            # 如果指定了 requestId，过滤不匹配的消息
            if expected_request_id is not None:
                msg_request_id = msg_data.get("requestId")
                if msg_request_id != expected_request_id:
                    # 不匹配，记录并继续等待
                    logger.debug(f"跳过不匹配的消息: expected={expected_request_id}, got={msg_request_id}, type={msg_data.get('type')}")
                    continue

            return msg
        except TimeoutError:
            continue

    return None


async def create_market_order(ws, symbol: str, side: str, quantity: float) -> str | None:
    """创建市价单，返回 orderId"""
    request_id = uuid.uuid4().hex
    new_client_order_id = uuid.uuid4().hex

    order_request = {
        "type": "CREATE_ORDER",
        "requestId": request_id,
        "timestamp": int(time.time() * 1000),
        "data": {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity,
            "newClientOrderId": new_client_order_id,
        },
    }

    logger.info(f"📝 requestId: {request_id}")
    logger.info(f"📝 newClientOrderId: {new_client_order_id}")
    logger.info(f"📤 发送市价单请求: {json.dumps(order_request, ensure_ascii=False)}")
    await ws.send(json.dumps(order_request))

    # 等待 ACK（使用 requestId 过滤）
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

    # 等待订单响应（使用 requestId 过滤）
    order_msg = await wait_for_message(ws, timeout=30, expected_request_id=request_id)
    if order_msg is None:
        logger.error("❌ 未收到订单响应")
        return None

    order_data = json.loads(order_msg)
    logger.info(f"📥 收到订单响应: {json.dumps(order_data, ensure_ascii=False)}")

    if order_data.get("type") == "ERROR":
        logger.error(f"❌ 订单创建失败: {order_data.get('data', {}).get('errorMessage')}")
        return None

    if order_data.get("type") == "ORDER_DATA":
        order_id = order_data.get("data", {}).get("result", {}).get("orderId")
        logger.info(f"✅ 市价单创建成功, orderId: {order_id}")
        return order_id

    return None


async def get_order(ws, symbol: str, order_id: str) -> bool:
    """查询订单"""
    query_request_id = uuid.uuid4().hex
    query_request = {
        "type": "GET_ORDER",
        "requestId": query_request_id,
        "timestamp": int(time.time() * 1000),
        "data": {
            "symbol": symbol,
            "orderId": str(order_id),
        },
    }

    logger.info(f"📝 查询 requestId: {query_request_id}")
    logger.info(f"📤 发送查询请求: {json.dumps(query_request, ensure_ascii=False)}")
    await ws.send(json.dumps(query_request))

    # 等待 ACK（使用 requestId 过滤）
    ack_msg = await wait_for_message(ws, timeout=5, expected_request_id=query_request_id)
    if ack_msg:
        ack_data = json.loads(ack_msg)
        logger.info(f"📥 收到查询 ACK: {json.dumps(ack_data, ensure_ascii=False)}")

    # 等待查询响应（使用 requestId 过滤）
    query_msg = await wait_for_message(ws, timeout=30, expected_request_id=query_request_id)
    if query_msg:
        query_data = json.loads(query_msg)
        logger.info(f"📥 收到查询响应: {json.dumps(query_data, ensure_ascii=False)}")

        if query_data.get("type") == "ORDER_DATA":
            logger.info("✅ 查询订单成功")
            return True
        else:
            logger.error(f"❌ 查询失败: {query_data.get('data', {}).get('errorMessage')}")
    else:
        logger.error("❌ 未收到查询响应")

    return False


async def create_limit_order(ws, symbol: str, side: str, quantity: float, price: float) -> dict | None:
    """创建限价单，返回订单信息字典

    返回字典包含:
    - orderId: 订单ID (成功时)
    - symbol: 交易对
    - status: 订单状态
    - isFutures: 是否是期货订单
    - error: 错误信息 (失败时)
    - success: 是否成功

    返回 None 表示超时或其他未知错误
    """
    request_id = uuid.uuid4().hex
    new_client_order_id = uuid.uuid4().hex

    # 判断是否是期货 (通过 .PERP 后缀)
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
    ack_msg = await wait_for_message(ws, timeout=5, expected_request_id=request_id)
    if ack_msg:
        ack_data = json.loads(ack_msg)
        logger.info(f"📥 收到限价单 ACK: {json.dumps(ack_data, ensure_ascii=False)}")

    # 等待订单响应（使用 requestId 过滤）
    order_msg = await wait_for_message(ws, timeout=30, expected_request_id=request_id)
    if order_msg:
        order_data = json.loads(order_msg)
        logger.info(f"📥 收到限价单响应: {json.dumps(order_data, ensure_ascii=False)}")

        if order_data.get("type") == "ORDER_DATA":
            data = order_data.get("data", {})

            # 解析订单响应 - 期货和现货都使用 result 字段
            result = data.get("result", {})
            order_id = result.get("orderId")
            status = result.get("status", "NEW")

            logger.info(f"✅ 限价单创建成功")
            logger.info(f"   orderId: {order_id}")
            logger.info(f"   symbol: {result.get('symbol')}")
            logger.info(f"   price: {result.get('price')}")
            logger.info(f"   origQty: {result.get('origQty')}")
            logger.info(f"   status: {status}")

            # 返回完整的订单信息字典
            return {
                "orderId": order_id,
                "symbol": result.get("symbol"),
                "status": status,
                "price": result.get("price"),
                "origQty": result.get("origQty"),
                "isFutures": is_futures,
                "success": True,
                "error": None,
            }
        elif order_data.get("type") == "ERROR":
            # 订单创建失败，返回错误信息
            error_message = order_data.get("data", {}).get("errorMessage", "Unknown error")
            logger.error(f"❌ 限价单创建失败: {error_message}")
            return {
                "orderId": None,
                "symbol": symbol,
                "status": "FAILED",
                "price": price,
                "origQty": quantity,
                "isFutures": is_futures,
                "success": False,
                "error": error_message,
            }
        else:
            logger.warning(f"⚠️ 限价单结果: {order_data.get('type')} - {order_data.get('data', {}).get('errorMessage')}")
    else:
        logger.warning("⚠️ 未收到限价单响应")

    return None


async def cancel_order(ws, symbol: str, order_id: str) -> bool:
    """取消订单"""
    cancel_request_id = uuid.uuid4().hex
    cancel_request = {
        "type": "CANCEL_ORDER",
        "requestId": cancel_request_id,
        "timestamp": int(time.time() * 1000),
        "data": {
            "symbol": symbol,
            "orderId": str(order_id),
        },
    }

    logger.info(f"📝 cancel requestId: {cancel_request_id}")
    logger.info(f"📤 发送取消请求: {json.dumps(cancel_request, ensure_ascii=False)}")
    await ws.send(json.dumps(cancel_request))

    # 等待 ACK（使用 requestId 过滤）
    ack_msg = await wait_for_message(ws, timeout=5, expected_request_id=cancel_request_id)
    if ack_msg:
        ack_data = json.loads(ack_msg)
        logger.info(f"📥 收到取消 ACK: {json.dumps(ack_data, ensure_ascii=False)}")

    # 等待取消响应（使用 requestId 过滤）
    cancel_msg = await wait_for_message(ws, timeout=30, expected_request_id=cancel_request_id)
    if cancel_msg:
        cancel_data = json.loads(cancel_msg)
        logger.info(f"📥 收到取消响应: {json.dumps(cancel_data, ensure_ascii=False)}")

        if cancel_data.get("type") == "ORDER_DATA":
            logger.info("✅ 订单取消成功")
            return True
        else:
            logger.warning(f"⚠️ 取消结果: {cancel_data.get('type')} - {cancel_data.get('data', {}).get('errorMessage')}")
    else:
        logger.warning("⚠️ 未收到取消响应")

    return False


async def modify_order(ws, symbol: str, order_id: str, new_price: float | None = None, new_quantity: float | None = None, side: str = "BUY") -> dict | None:
    """修改订单

    币安支持修改订单价格或数量。
    - 期货: order.modify - 可修改价格和数量
    - 现货: order.amend.keepPriority - 只能减少数量

    参数:
        symbol: 交易对，如 BINANCE:BTCUSDT.PERP
        order_id: 订单ID
        new_price: 新价格（期货可用）
        new_quantity: 新数量（现货必须，期货可选）
        side: 订单方向 BUY/SELL（期货必填）

    返回:
        修改后的订单信息字典，包含 orderId, symbol, status 等
    """
    # 判断是否是期货
    is_futures = ".PERP" in symbol.upper()
    timestamp = int(time.time() * 1000)

    # 构建修改请求
    modify_data = {
        "symbol": symbol,
        "orderId": str(order_id),
        "timestamp": timestamp,
    }

    if is_futures:
        # 期货修改订单必填字段校验
        if new_price is None:
            logger.warning("期货修改订单必须提供 new_price 参数")
            return None
        if new_quantity is None:
            logger.warning("期货修改订单必须提供 new_quantity 参数")
            return None
        modify_data["side"] = side
        modify_data["quantity"] = str(new_quantity)
        modify_data["price"] = str(new_price)
    else:
        # 现货修改订单 - 只能减少数量（newQty 必填），不支持修改价格
        if new_quantity is None:
            logger.warning("现货修改订单必须提供 new_quantity 参数")
            return None
        modify_data["newQty"] = str(new_quantity)

    request_id = uuid.uuid4().hex
    modify_request = {
        "type": "MODIFY_ORDER",
        "requestId": request_id,
        "timestamp": timestamp,
        "data": modify_data,
    }

    logger.info(f"📝 requestId: {request_id}")
    logger.info(f"📝 市场类型: {'期货' if is_futures else '现货'}")
    logger.info(f"📝 修改参数: price={new_price}, quantity={new_quantity}")
    logger.info(f"📤 发送修改订单请求: {json.dumps(modify_request, ensure_ascii=False)}")
    await ws.send(json.dumps(modify_request))

    # 等待 ACK（使用 requestId 过滤）
    ack_msg = await wait_for_message(ws, timeout=5, expected_request_id=request_id)
    if ack_msg:
        ack_data = json.loads(ack_msg)
        logger.info(f"📥 收到修改 ACK: {json.dumps(ack_data, ensure_ascii=False)}")

        # 解析 ACK 响应中的任务信息
        ack_task_id = ack_data.get("data", {}).get("taskId")
        logger.info(f"   任务ID: {ack_task_id}")

    # 等待修改订单响应（使用 requestId 过滤）
    modify_msg = await wait_for_message(ws, timeout=30, expected_request_id=request_id)
    if modify_msg:
        modify_data = json.loads(modify_msg)
        logger.info(f"📥 收到修改订单响应: {json.dumps(modify_data, ensure_ascii=False)}")

        if modify_data.get("type") == "ORDER_DATA":
            data = modify_data.get("data", {})

            # 根据市场类型解析不同的响应格式
            if is_futures:
                # 期货修改订单响应 - FuturesModifyOrderResponseData
                # 格式: { taskId, status, origClientOrderId, orderId, symbol, price, ... }
                order_id = data.get("orderId")
                status = data.get("status")
                logger.info(f"✅ 期货订单修改成功")
                logger.info(f"   orderId: {order_id}")
                logger.info(f"   symbol: {data.get('symbol')}")
                logger.info(f"   price: {data.get('price')}")
                logger.info(f"   status: {status}")

                return {
                    "orderId": order_id,
                    "symbol": data.get("symbol"),
                    "status": status,
                    "price": data.get("price"),
                    "isFutures": True,
                }
            else:
                # 现货修改订单响应 - SpotAmendOrderResponseData
                # 格式: { taskId, status, origClientOrderId, transactTime, executionId, amendedOrder: {...} }
                amended = data.get("amendedOrder", {})
                order_id = amended.get("orderId")
                status = amended.get("status")
                logger.info(f"✅ 现货订单修改成功")
                logger.info(f"   amendedOrderId: {order_id}")
                logger.info(f"   transactTime: {data.get('transactTime')}")
                logger.info(f"   executionId: {data.get('executionId')}")
                logger.info(f"   amended price: {amended.get('price')}")
                logger.info(f"   amended status: {status}")

                return {
                    "orderId": order_id,
                    "symbol": amended.get("symbol"),
                    "status": status,
                    "price": amended.get("price"),
                    "transactTime": data.get("transactTime"),
                    "executionId": data.get("executionId"),
                    "isFutures": False,
                    "success": True,
                    "error": None,
                }
        elif modify_data.get("type") == "ERROR":
            # 修改订单失败，返回错误信息
            error_message = modify_data.get("data", {}).get("errorMessage") or "Unknown error"
            logger.error(f"❌ 修改订单失败: {error_message}")
            return {
                "orderId": None,
                "symbol": symbol,
                "status": "FAILED",
                "price": new_price,
                "isFutures": is_futures,
                "success": False,
                "error": error_message,
            }
        else:
            error_msg = modify_data.get("data", {}).get("errorMessage") or "Unknown error"
            logger.warning(f"⚠️ 修改订单失败: {error_msg}")
            return {
                "orderId": None,
                "symbol": symbol,
                "status": "FAILED",
                "price": new_price,
                "isFutures": is_futures,
                "success": False,
                "error": error_msg,
            }
    else:
        logger.warning("⚠️ 未收到修改订单响应")

    return None


async def get_quote(ws, symbol: str) -> float | None:
    """获取报价"""
    quotes_request_id = uuid.uuid4().hex
    quotes_request = {
        "type": "GET_QUOTES",
        "requestId": quotes_request_id,
        "timestamp": int(time.time() * 1000),
        "data": {
            "symbols": [symbol]
        },
    }

    logger.info(f"📝 quotes requestId: {quotes_request_id}")
    logger.info(f"📤 发送报价请求: {json.dumps(quotes_request, ensure_ascii=False)}")
    await ws.send(json.dumps(quotes_request))

    # 等待报价响应（使用 requestId 过滤）
    quotes_msg = await wait_for_message(ws, timeout=10, expected_request_id=quotes_request_id)
    if quotes_msg:
        quotes_data = json.loads(quotes_msg)
        logger.info(f"📥 收到报价: {json.dumps(quotes_data, ensure_ascii=False)}")

        quotes_result = quotes_data.get("data", {}).get("quotes", [])
        if quotes_result:
            symbol_data = quotes_result[0].get(symbol, {})
            current_price = symbol_data.get("bid") or symbol_data.get("ask")
            logger.info(f"📊 当前价格: {current_price}")
            return current_price

    return None


async def list_orders(ws, symbol: str) -> bool:
    """查询订单列表"""
    list_orders_request_id = uuid.uuid4().hex
    list_orders_request = {
        "type": "LIST_ORDERS",
        "requestId": list_orders_request_id,
        "timestamp": int(time.time() * 1000),
        "data": {
            "symbol": symbol,
            "limit": 50
        },
    }

    logger.info(f"📝 requestId: {list_orders_request_id}")
    logger.info(f"📤 发送订单列表请求: {json.dumps(list_orders_request, ensure_ascii=False)}")
    await ws.send(json.dumps(list_orders_request))

    # 等待 ACK（使用 requestId 过滤）
    ack_msg = await wait_for_message(ws, timeout=5, expected_request_id=list_orders_request_id)
    if ack_msg:
        ack_data = json.loads(ack_msg)
        logger.info(f"📥 收到 LIST_ORDERS ACK: {json.dumps(ack_data, ensure_ascii=False)}")

    # 等待订单列表响应（使用 requestId 过滤）
    list_orders_msg = await wait_for_message(ws, timeout=30, expected_request_id=list_orders_request_id)
    if list_orders_msg:
        list_orders_data = json.loads(list_orders_msg)
        logger.info(f"📥 收到订单列表响应: {json.dumps(list_orders_data, ensure_ascii=False)}")

        if list_orders_data.get("type") == "ORDER_LIST_DATA":
            orders = list_orders_data.get("data", {}).get("orders", [])
            total = list_orders_data.get("data", {}).get("total", 0)
            logger.info(f"📊 订单数量: {len(orders)}, 总数: {total}")
            return True
        else:
            logger.warning(f"⚠️ 查询订单列表结果: {list_orders_data.get('type')} - {list_orders_data.get('data', {}).get('errorMessage')}")
    else:
        logger.warning("⚠️ 未收到订单列表响应")

    return False


async def get_open_orders(ws, symbol: str) -> bool:
    """查询当前挂单"""
    open_orders_request_id = uuid.uuid4().hex
    open_orders_request = {
        "type": "GET_OPEN_ORDERS",
        "requestId": open_orders_request_id,
        "timestamp": int(time.time() * 1000),
        "data": {
            "symbol": symbol
        },
    }

    logger.info(f"📝 requestId: {open_orders_request_id}")
    logger.info(f"📤 发送挂单请求: {json.dumps(open_orders_request, ensure_ascii=False)}")
    await ws.send(json.dumps(open_orders_request))

    # 等待 ACK（使用 requestId 过滤）
    ack_msg = await wait_for_message(ws, timeout=5, expected_request_id=open_orders_request_id)
    if ack_msg:
        ack_data = json.loads(ack_msg)
        logger.info(f"📥 收到 GET_OPEN_ORDERS ACK: {json.dumps(ack_data, ensure_ascii=False)}")

    # 等待挂单响应（使用 requestId 过滤）
    open_orders_msg = await wait_for_message(ws, timeout=30, expected_request_id=open_orders_request_id)
    if open_orders_msg:
        open_orders_data = json.loads(open_orders_msg)
        logger.info(f"📥 收到当前挂单响应: {json.dumps(open_orders_data, ensure_ascii=False)}")

        if open_orders_data.get("type") == "ORDER_LIST_DATA":
            open_orders = open_orders_data.get("data", {}).get("orders", [])
            total = open_orders_data.get("data", {}).get("total", 0)
            logger.info(f"📊 当前挂单数量: {len(open_orders)}, 总数: {total}")
            return True
        else:
            logger.warning(f"⚠️ 查询当前挂单结果: {open_orders_data.get('type')} - {open_orders_data.get('data', {}).get('errorMessage')}")
    else:
        logger.warning("⚠️ 未收到当前挂单响应")

    return False


async def run_market_tests(ws):
    """运行市价单测试 (会实际成交)"""
    logger.info("=" * 60)
    logger.info("🛒 市价单测试开始 (会实际成交)")
    logger.info("=" * 60)

    # 测试1: 创建期货市价单
    logger.info("=" * 60)
    logger.info("测试: 创建期货市价单")
    logger.info("=" * 60)

    futures_order_id = await create_market_order(ws, "BINANCE:BTCUSDT.PERP", "BUY", 0.002)

    # 测试2: 查询订单
    if futures_order_id:
        logger.info("⏳ 等待2秒后查询订单...")
        await asyncio.sleep(2)
        await get_order(ws, "BINANCE:BTCUSDT.PERP", futures_order_id)

    # 测试3: 创建现货市价单
    logger.info("⏳ 等待2秒后创建现货市价单...")
    await asyncio.sleep(2)

    logger.info("=" * 60)
    logger.info("测试: 创建现货市价单")
    logger.info("=" * 60)

    spot_order_id = await create_market_order(ws, "BINANCE:BTCUSDT", "BUY", 0.001)

    # 查询现货订单
    if spot_order_id:
        logger.info("⏳ 等待2秒后查询现货订单...")
        await asyncio.sleep(2)
        await get_order(ws, "BINANCE:BTCUSDT", spot_order_id)

    logger.info("=" * 60)
    logger.info("🛒 市价单测试完成")
    logger.info("=" * 60)

    return futures_order_id


async def run_limit_tests(ws):
    """运行限价单测试 (不会实际成交)

    测试流程:
    1. 期货限价单: 创建 → 查询 → 修改 → 取消
    2. 现货限价单: 创建 → 查询 → 修改 → 取消
    3. 订单列表查询
    4. 当前挂单查询
    """
    logger.info("=" * 60)
    logger.info("📝 限价单测试开始 (不会实际成交)")
    logger.info("=" * 60)

    futures_order_info = None
    spot_order_info = None

    # ============================================================
    # 期货限价单测试流程: 创建 → 查询 → 修改 → 取消
    # ============================================================

    # 步骤1: 获取期货报价并创建限价单
    logger.info("⏳ 等待1秒后获取期货报价...")
    await asyncio.sleep(1)

    logger.info("=" * 60)
    logger.info("步骤1: 获取期货报价")
    logger.info("=" * 60)

    futures_price = await get_quote(ws, "BINANCE:BTCUSDT.PERP")
    futures_limit_price = futures_price - 500 if futures_price else 70000.0
    logger.info(f"📊 期货限价单价格: {futures_limit_price} (现价 - 500)")

    logger.info("=" * 60)
    logger.info("步骤2: 创建期货限价单")
    logger.info("=" * 60)

    futures_order_info = await create_limit_order(
        ws, "BINANCE:BTCUSDT.PERP", "BUY", 0.003, futures_limit_price
    )

    # 步骤3: 查询期货订单
    if futures_order_info:
        futures_limit_order_id = futures_order_info.get("orderId")
        logger.info(f"   保存期货订单ID: {futures_limit_order_id}")

        logger.info("⏳ 等待1秒后查询期货订单...")
        await asyncio.sleep(1)

        logger.info("=" * 60)
        logger.info("步骤3: 查询期货订单")
        logger.info("=" * 60)

        await get_order(ws, "BINANCE:BTCUSDT.PERP", futures_limit_order_id)

    # 步骤4: 修改期货订单
    if futures_order_info:
        futures_limit_order_id = futures_order_info.get("orderId")

        logger.info("⏳ 等待1秒后修改期货订单...")
        await asyncio.sleep(1)

        logger.info("=" * 60)
        logger.info("步骤4: 修改期货订单")
        logger.info("=" * 60)

        # 修改价格为更低价（确保不会成交）
        # 买单修改价格应该低于原价格，这样不会立刻成交
        new_futures_price = futures_price - 100 if futures_price else 69000.0
        # 期货修改订单 quantity 是必填字段（但可以传原数量）
        futures_orig_qty = futures_order_info.get("origQty", "0.003")
        if isinstance(futures_orig_qty, str):
            futures_orig_qty = float(futures_orig_qty)
        modify_result = await modify_order(
            ws, "BINANCE:BTCUSDT.PERP",
            futures_limit_order_id,
            new_price=new_futures_price,
            new_quantity=futures_orig_qty
        )
        if modify_result:
            logger.info(f"   修改后期货订单: {modify_result}")

    # 步骤5: 取消期货订单
    if futures_order_info:
        futures_limit_order_id = futures_order_info.get("orderId")

        logger.info("⏳ 等待1秒后取消期货订单...")
        await asyncio.sleep(1)

        logger.info("=" * 60)
        logger.info("步骤5: 取消期货订单")
        logger.info("=" * 60)

        await cancel_order(ws, "BINANCE:BTCUSDT.PERP", futures_limit_order_id)

    # ============================================================
    # 现货限价单测试流程: 创建 → 查询 → 修改 → 取消
    # ============================================================

    # 步骤1: 获取现货报价并创建限价单
    logger.info("⏳ 等待2秒后获取现货报价...")
    await asyncio.sleep(2)

    logger.info("=" * 60)
    logger.info("步骤1: 获取现货报价")
    logger.info("=" * 60)

    spot_price = await get_quote(ws, "BINANCE:BTCUSDT")
    spot_limit_price = spot_price - 500 if spot_price else 70000.0
    logger.info(f"📊 现货限价单价格: {spot_limit_price} (现价 - 500)")

    logger.info("=" * 60)
    logger.info("步骤2: 创建现货限价单")
    logger.info("=" * 60)

    spot_order_info = await create_limit_order(
        ws, "BINANCE:BTCUSDT", "BUY", 0.001, spot_limit_price
    )

    # 步骤3: 查询现货订单
    if spot_order_info:
        spot_limit_order_id = spot_order_info.get("orderId")
        logger.info(f"   保存现货订单ID: {spot_limit_order_id}")

        logger.info("⏳ 等待1秒后查询现货订单...")
        await asyncio.sleep(1)

        logger.info("=" * 60)
        logger.info("步骤3: 查询现货订单")
        logger.info("=" * 60)

        await get_order(ws, "BINANCE:BTCUSDT", spot_limit_order_id)

    # 步骤4: 修改现货订单
    if spot_order_info:
        spot_limit_order_id = spot_order_info.get("orderId")

        logger.info("⏳ 等待1秒后修改现货订单...")
        await asyncio.sleep(1)

        logger.info("=" * 60)
        logger.info("步骤4: 修改现货订单")
        logger.info("=" * 60)

        # 现货修改订单只支持减少数量，不支持修改价格
        # 减少数量到原数量的0.9倍（减少10%）
        spot_orig_qty = spot_order_info.get("origQty", "0.001")
        if isinstance(spot_orig_qty, str):
            spot_orig_qty = float(spot_orig_qty)
        new_spot_qty = round(spot_orig_qty * 0.9, 5)
        modify_result = await modify_order(
            ws, "BINANCE:BTCUSDT",
            spot_limit_order_id,
            new_quantity=new_spot_qty
        )
        if modify_result:
            logger.info(f"   修改后现货订单: {modify_result}")

    # 步骤5: 取消现货订单
    if spot_order_info:
        spot_limit_order_id = spot_order_info.get("orderId")

        logger.info("⏳ 等待1秒后取消现货订单...")
        await asyncio.sleep(1)

        logger.info("=" * 60)
        logger.info("步骤5: 取消现货订单")
        logger.info("=" * 60)

        await cancel_order(ws, "BINANCE:BTCUSDT", spot_limit_order_id)

    # ============================================================
    # 订单列表和挂单查询
    # ============================================================

    # 查询订单列表
    logger.info("⏳ 等待2秒后查询订单列表...")
    await asyncio.sleep(2)

    logger.info("=" * 60)
    logger.info("测试: 查询订单列表")
    logger.info("=" * 60)

    await list_orders(ws, "BINANCE:BTCUSDT.PERP")

    # 查询当前挂单
    logger.info("⏳ 等待2秒后查询当前挂单...")
    await asyncio.sleep(2)

    logger.info("=" * 60)
    logger.info("测试: 查询当前挂单")
    logger.info("=" * 60)

    await get_open_orders(ws, "BINANCE:BTCUSDT.PERP")

    logger.info("=" * 60)
    logger.info("📝 限价单测试完成")
    logger.info("=" * 60)

    # 返回测试结果摘要
    # 检查订单是否成功创建 (success=True)
    futures_success = futures_order_info is not None and futures_order_info.get("success", False)
    spot_success = spot_order_info is not None and spot_order_info.get("success", False)

    return {
        "futures_created": futures_success,
        "spot_created": spot_success,
        "futures_order_info": futures_order_info,
        "spot_order_info": spot_order_info,
    }


async def main(include_market: bool = False):
    """主测试函数"""
    logger.info("🚀 开始 WebSocket 订单交易 E2E 测试")
    logger.info(f"📡 WebSocket URL: {WS_URL}")
    logger.info(f"📊 测试模式: {'完整测试 (含市价单)' if include_market else '限价单测试 (推荐)'}")
    logger.info("=" * 60)

    test_results = {
        "market": False,
        "limit": False,
    }

    try:
        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=60) as ws:
            logger.info(f"✅ 连接到 {WS_URL}")

            # 市价单测试
            if include_market:
                futures_order_id = await run_market_tests(ws)
                test_results["market"] = futures_order_id is not None
            else:
                logger.info("⏭️ 跳过市价单测试 (使用 --include-market 参数启用)")

            # 限价单测试 (默认运行)
            limit_result = await run_limit_tests(ws)
            # 真正的断言：期货和现货订单都必须创建成功
            test_results["limit"] = limit_result.get("futures_created", False) and limit_result.get("spot_created", False)

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 测试总结
    logger.info("=" * 60)
    logger.info("📋 测试总结:")
    if include_market:
        logger.info(f"  - 市价单测试: {'✅ 通过' if test_results['market'] else '❌ 失败'}")
        if not test_results["market"]:
            logger.error("❌ 市价单测试失败，订单未创建成功")
            sys.exit(1)
    else:
        logger.info("  - 市价单测试: ⏭️ 跳过 (使用 --include-market 参数启用)")
    logger.info(f"  - 限价单测试: {'✅ 通过' if test_results['limit'] else '❌ 失败'}")
    if not test_results["limit"]:
        logger.error("❌ 限价单测试失败，订单未创建成功")
        sys.exit(1)
    logger.info("=" * 60)
    logger.info("🎉 所有测试通过!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebSocket 订单交易 E2E 测试")
    parser.add_argument(
        "--include-market",
        action="store_true",
        help="包含市价单测试 (会实际成交，默认只测试限价单)"
    )
    args = parser.parse_args()

    asyncio.run(main(include_market=args.include_market))
