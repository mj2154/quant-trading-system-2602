"""
订单任务处理器

根据 04-trading-orders.md 设计：
- 处理 order.create（创建订单）
- 处理 order.cancel（取消订单）
- 处理 order.query（查询订单状态）

职责：
- 解析订单任务参数
- 调用币安私有API执行订单操作
- 通过回调模式处理响应，更新 order_tasks 表状态
"""

import logging
from typing import TYPE_CHECKING, Any, Optional

from pydantic import ValidationError

from models.trading_order import (
    SpotWsOrderRequest,
    FuturesWsOrderRequest,
    SpotWsOrderResponse,
    FuturesWsOrderResponse,
    WsQueryOrderRequest,
    WsCancelOrderRequest,
)

if TYPE_CHECKING:
    from clients.futures_private_ws_client import BinanceFuturesPrivateWSClient
    from clients.spot_private_ws_client import BinanceSpotPrivateWSClient
    from db.order_tasks_repository import OrderTasksRepository

logger = logging.getLogger(__name__)


class OrderTaskHandler:
    """订单任务处理器

    处理 order_tasks 表中的订单任务：
    - order.create: 创建订单
    - order.cancel: 取消订单
    - order.query: 查询订单状态和WebSocket客户端

    支持HTTP：
    - WebSocket客户端（推荐）：使用私有WebSocket API，回调模式处理响应
    - HTTP客户端：使用私有REST API

    回调模式：
    - WS客户端发送请求时不等待响应
    - 收到响应时通过回调更新任务状态
    - 通过payload中的requestId关联请求和任务
    """

    def __init__(
        self,
        futures_client: Optional["BinanceFuturesPrivateWSClient"] = None,
        spot_client: Optional["BinanceSpotPrivateWSClient"] = None,
        futures_http_client: Optional["BinanceFuturesPrivateWSClient"] = None,
        spot_http_client: Optional["BinanceSpotPrivateWSClient"] = None,
        order_tasks_repo: "OrderTasksRepository" = None,
    ) -> None:
        """初始化处理器

        Args:
            futures_client: 期货私有WebSocket客户端（推荐）
            spot_client: 现货私有WebSocket客户端（推荐）
            futures_http_client: 期货私有HTTP客户端（备用）
            spot_http_client: 现货私有HTTP客户端（备用）
            order_tasks_repo: 订单任务仓储

        Note:
            WebSocket客户端优先，如果没有配置则使用HTTP客户端
            WS客户端会设置响应回调用于异步处理响应
        """
        # WebSocket客户端（优先）
        self._futures_ws_client = futures_client
        self._spot_ws_client = spot_client

        # 设置回调（仅WS客户端使用回调模式）
        if self._futures_ws_client:
            self._futures_ws_client.set_response_callback(self._handle_futures_response)
        if self._spot_ws_client:
            self._spot_ws_client.set_response_callback(self._handle_spot_response)

        # HTTP客户端（备用）
        self._futures_http_client = futures_http_client
        self._spot_http_client = spot_http_client
        self._repo = order_tasks_repo

    def _get_futures_client(self):
        """获取期货客户端（优先WS，其次HTTP）"""
        if self._futures_ws_client:
            return self._futures_ws_client
        return self._futures_http_client

    def _get_spot_client(self):
        """获取现货客户端（优先WS，其次HTTP）"""
        if self._spot_ws_client:
            return self._spot_ws_client
        return self._spot_http_client

    def _parse_symbol(self, symbol: str) -> tuple[str, str]:
        """解析语义化交易对符号，返回 (干净symbol, 市场类型)

        根据设计文档：
        - BINANCE:BTCUSDT → (BTCUSDT, SPOT)
        - BINANCE:BTCUSDT.PERP → (BTCUSDT, FUTURES)
        - BTCUSDT (无前缀) → (BTCUSDT, 默认为FUTURES)

        Args:
            symbol: 语义化符号，如 BINANCE:BTCUSDT 或 BTCUSDT

        Returns:
            (干净的交易对符号, 市场类型)
        """
        if not symbol:
            return symbol, "FUTURES"

        # 检查是否有 BINANCE: 前缀
        if symbol.upper().startswith("BINANCE:"):
            # 去掉前缀
            clean_symbol = symbol[len("BINANCE:"):]

            # 检查是否为期货（.PERP 后缀）
            if clean_symbol.upper().endswith(".PERP"):
                return clean_symbol[:-5], "FUTURES"  # 去掉 .PERP

            return clean_symbol, "SPOT"

        # 无前缀，默认当作期货处理（向后兼容）
        return symbol, "FUTURES"

    async def handle_task(self, payload: dict[str, Any]) -> None:
        """处理订单任务

        Args:
            payload: 任务载荷，包含 type, task_id, payload
        """
        task_type = payload.get("type", "")
        task_id = payload.get("task_id")
        params = payload.get("payload", {})

        logger.info(f"处理订单任务: {task_type} (task_id={task_id})")

        if not task_id:
            logger.error("任务ID无效")
            return

        # 标记为处理中
        await self._repo.set_processing(task_id)

        # 从数据库获取任务的 request_id（顶层字段）
        task = await self._repo.get_task_by_id(task_id)
        request_id = task.get("request_id") if task else None
        logger.info(f"任务 {task_id} 的 request_id: {request_id}")

        try:
            if task_type == "order.create":
                await self._handle_create_order(task_id, params, request_id)
            elif task_type == "order.cancel":
                await self._handle_cancel_order(task_id, params, request_id)
            elif task_type == "order.query":
                await self._handle_query_order(task_id, params, request_id)
            else:
                logger.warning(f"未知的订单任务类型: {task_type}")
                await self._repo.fail(task_id, f"未知的任务类型: {task_type}")

        except Exception as e:
            logger.error(f"处理订单任务失败: {e}")
            await self._repo.fail(task_id, str(e))

    async def _handle_create_order(
        self, task_id: int, params: dict[str, Any], request_id: str | None = None
    ) -> None:
        """处理订单创建任务

        使用 Pydantic 模型验证参数，自动处理 camelCase/snake_case 转换。

        Args:
            task_id: 任务ID
            params: 订单参数（蛇形或驼峰命名均可）
            request_id: 请求ID（从数据库顶层字段获取，用于发送给币安作为 clientOrderId）
        """
        # 解析语义化symbol，根据前缀自动判断市场类型
        # BINANCE:BTCUSDT → 现货
        # BINANCE:BTCUSDT.PERP → 期货
        raw_symbol = params.get("symbol", "") or params.get("symbol", "")
        symbol, market_type = self._parse_symbol(raw_symbol)

        # 使用 Pydantic 模型验证参数（自动 camelCase → snake_case 转换）
        try:
            if market_type == "SPOT":
                # 现货订单模型验证
                order_request = SpotWsOrderRequest.model_validate(params)
            else:
                # 期货订单模型验证
                order_request = FuturesWsOrderRequest.model_validate(params)
        except ValidationError as e:
            await self._repo.fail(task_id, f"参数验证失败: {e}")
            return

        # 从验证后的模型中提取参数（通用字段）
        side = order_request.side
        order_type = order_request.type
        quantity = order_request.quantity
        price = order_request.price
        time_in_force = order_request.time_in_force
        stop_price = order_request.stop_price
        new_client_order_id = order_request.new_client_order_id

        # 根据市场类型提取特有参数
        if market_type == "FUTURES":
            # 期货模型才有这些字段
            reduce_only = order_request.reduce_only
            position_side = order_request.position_side
        else:
            # 现货模型没有这些字段
            reduce_only = False
            position_side = None

        logger.info(
            f"创建订单: {symbol} {side} {order_type} qty={quantity} price={price} market={market_type}"
        )

        # 使用requestId关联请求和响应（从任务记录的顶层request_id字段获取）
        # 设计文档要求: request_id 从 payload 提升到顶层字段
        # request_id 已作为参数传入，直接使用（如果为 None 则使用 task_id 作为后备）
        if not request_id:
            request_id = str(task_id)

        if market_type == "FUTURES":
            # 优先使用WS客户端回调模式
            if self._futures_ws_client:
                try:
                    # 使用 _build_order_params 构建带签名的参数
                    # 注意：不再使用 to_binance_params()，因为它不包含 timestamp 和 signature
                    binance_params = self._futures_ws_client._build_order_params(
                        symbol=symbol,
                        side=side,
                        order_type=order_type,
                        quantity=quantity,
                        price=price,
                        time_in_force=time_in_force,
                        stop_price=stop_price,
                        reduce_only=reduce_only,
                        position_side=position_side,
                        new_client_order_id=new_client_order_id,
                    )

                    # 发送请求（不等待响应，通过回调处理）
                    await self._futures_ws_client.send_request("order.place", binance_params, request_id)
                    logger.info(f"订单创建请求已发送: requestId={request_id}")
                    # 注意：任务状态将在回调中更新
                    return
                except Exception as e:
                    logger.error(f"期货WS客户端发送请求失败: {e}")
                    # 降级到HTTP客户端

            # 使用HTTP客户端或旧版WS客户端（等待响应）
            client = self._get_futures_client()
            if not client:
                await self._repo.fail(task_id, "期货客户端未初始化")
                return

            result = await client.create_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                time_in_force=time_in_force,
                stop_price=stop_price,
                reduce_only=reduce_only,
                position_side=position_side,
                new_client_order_id=new_client_order_id,
            )
        elif market_type == "SPOT":
            # 现货 - 必须使用WS客户端
            if not self._spot_ws_client:
                await self._repo.fail(task_id, "现货WS客户端未初始化")
                return

            try:
                # 使用 _build_order_params 构建带签名的参数
                # 注意：不再使用 to_binance_params()，因为它不包含 timestamp 和 signature
                binance_params = self._spot_ws_client._build_order_params(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    time_in_force=time_in_force,
                    stop_price=stop_price,
                    new_client_order_id=new_client_order_id,
                )

                # 发送请求（不等待响应，通过回调处理）
                await self._spot_ws_client.send_request("order.place", binance_params, request_id)
                logger.info(f"订单创建请求已发送(现货): requestId={request_id}")
                # 注意：任务状态将在回调中更新
                return
            except Exception as e:
                logger.error(f"现货WS客户端发送请求失败: {e}")
                await self._repo.fail(task_id, f"现货WS客户端发送请求失败: {e}")
                return

        else:
            await self._repo.fail(task_id, f"未知的市场类型: {market_type}")

    async def _handle_cancel_order(
        self, task_id: int, params: dict[str, Any], request_id: str | None = None
    ) -> None:
        """处理订单取消任务

        Args:
            task_id: 任务ID
            params: 取消参数
            request_id: 请求ID（从数据库顶层字段获取）
        """
        # 验证必需字段
        if not params.get("symbol"):
            await self._repo.fail(task_id, "Missing required field: symbol")
            return
        if not params.get("orderId") and not params.get("clientOrderId"):
            await self._repo.fail(task_id, "Missing required field: orderId or clientOrderId")
            return

        # 解析语义化symbol，根据前缀自动判断市场类型
        raw_symbol = params.get("symbol", "")
        symbol, market_type = self._parse_symbol(raw_symbol)

        order_id = params.get("orderId")
        client_order_id = params.get("origClientOrderId") or params.get("clientOrderId")

        logger.info(f"取消订单: {symbol} orderId={order_id} clientOrderId={client_order_id} market={market_type}")

        # 使用requestId关联请求和响应（从任务记录的顶层request_id字段获取）
        # 设计文档要求: request_id 从 payload 提升到顶层字段
        # request_id 已作为参数传入，直接使用（如果为 None 则使用 task_id 作为后备）
        if not request_id:
            request_id = str(task_id)

        if market_type == "FUTURES":
            # 优先使用WS客户端回调模式
            if self._futures_ws_client:
                try:
                    cancel_params = self._futures_ws_client._build_cancel_order_params(
                        symbol=symbol,
                        order_id=str(order_id) if order_id else None,
                        orig_client_order_id=client_order_id,
                    )
                    await self._futures_ws_client.send_request("order.cancel", cancel_params, request_id)
                    logger.info(f"取消订单请求已发送: requestId={request_id}")
                    return
                except Exception as e:
                    logger.error(f"期货WS客户端发送请求失败: {e}")

            # 使用HTTP客户端
            client = self._get_futures_client()
            if not client:
                await self._repo.fail(task_id, "期货客户端未初始化")
                return

            result = await client.cancel_order(
                symbol=symbol,
                order_id=str(order_id) if order_id else None,
                client_order_id=client_order_id,
            )
        else:
            # 优先使用WS客户端回调模式
            if self._spot_ws_client:
                try:
                    cancel_params = self._spot_ws_client._build_cancel_order_params(
                        symbol=symbol,
                        order_id=str(order_id) if order_id else None,
                        orig_client_order_id=client_order_id,
                    )
                    await self._spot_ws_client.send_request("order.cancel", cancel_params, request_id)
                    logger.info(f"取消订单请求已发送: requestId={request_id}")
                    return
                except Exception as e:
                    logger.error(f"现货WS客户端发送请求失败: {e}")

            # 使用HTTP客户端
            client = self._get_spot_client()
            if not client:
                await self._repo.fail(task_id, "现货客户端未初始化")
                return

            result = await client.cancel_order(
                symbol=symbol,
                order_id=str(order_id) if order_id else None,
                client_order_id=client_order_id,
            )

        await self._repo.complete(task_id, result)
        logger.info(f"订单取消成功: {result.get('orderId')}")

    async def _handle_query_order(
        self, task_id: int, params: dict[str, Any], request_id: str | None = None
    ) -> None:
        """处理订单查询任务

        Args:
            task_id: 任务ID
            params: 查询参数
            request_id: 请求ID（从数据库顶层字段获取）
        """
        # 验证必需字段
        if not params.get("symbol"):
            await self._repo.fail(task_id, "Missing required field: symbol")
            return
        if not params.get("orderId") and not params.get("clientOrderId"):
            await self._repo.fail(task_id, "Missing required field: orderId or clientOrderId")
            return

        # 解析语义化symbol，根据前缀自动判断市场类型
        raw_symbol = params.get("symbol", "")
        symbol, market_type = self._parse_symbol(raw_symbol)

        order_id = params.get("orderId")
        client_order_id = params.get("origClientOrderId") or params.get("clientOrderId")

        logger.info(f"查询订单: {symbol} orderId={order_id} clientOrderId={client_order_id} market={market_type}")

        # 使用requestId关联请求和响应（从任务记录的顶层request_id字段获取）
        # 设计文档要求: request_id 从 payload 提升到顶层字段
        # request_id 已作为参数传入，直接使用（如果为 None 则使用 task_id 作为后备）
        if not request_id:
            request_id = str(task_id)

        if market_type == "FUTURES":
            # 优先使用WS客户端回调模式
            if self._futures_ws_client:
                try:
                    query_params = self._futures_ws_client._build_query_order_params(
                        symbol=symbol,
                        order_id=str(order_id) if order_id else None,
                        orig_client_order_id=client_order_id,
                    )
                    await self._futures_ws_client.send_request("order.status", query_params, request_id)
                    logger.info(f"查询订单请求已发送: requestId={request_id}")
                    return
                except Exception as e:
                    logger.error(f"期货WS客户端发送请求失败: {e}")

            # 使用HTTP客户端
            client = self._get_futures_client()
            if not client:
                await self._repo.fail(task_id, "期货客户端未初始化")
                return

            result = await client.get_order(
                symbol=symbol,
                order_id=str(order_id) if order_id else None,
                client_order_id=client_order_id,
            )
        else:
            # 优先使用WS客户端回调模式
            if self._spot_ws_client:
                try:
                    query_params = self._spot_ws_client._build_query_order_params(
                        symbol=symbol,
                        order_id=str(order_id) if order_id else None,
                        orig_client_order_id=client_order_id,
                    )
                    await self._spot_ws_client.send_request("order.status", query_params, request_id)
                    logger.info(f"查询订单请求已发送: requestId={request_id}")
                    return
                except Exception as e:
                    logger.error(f"现货WS客户端发送请求失败: {e}")

            # 使用HTTP客户端
            client = self._get_spot_client()
            if not client:
                await self._repo.fail(task_id, "现货客户端未初始化")
                return

            result = await client.get_order(
                symbol=symbol,
                order_id=str(order_id) if order_id else None,
                client_order_id=client_order_id,
            )

        await self._repo.complete(task_id, result)
        logger.info(f"订单查询成功: status={result.get('status')}")

    # ========== 回调处理方法 ==========

    async def _handle_futures_response(self, request_id: str, response: dict) -> None:
        """处理期货WS响应（回调）

        Args:
            request_id: 请求ID
            response: 响应数据
        """
        logger.info(f"[期货回调] 收到响应: requestId={request_id}, response={response}")

        # 1. 根据requestId查找任务
        task = await self._repo.find_by_request_id(request_id)
        if not task:
            logger.warning(f"[期货回调] 未找到任务: requestId={request_id}")
            return

        task_id = task["id"]

        # 2. 根据响应状态更新任务
        status = response.get("status", response.get("result", {}).get("status", 200))
        if status == 200:
            result = response.get("result", {})
            await self._repo.complete(task_id, result)
            logger.info(f"[期货回调] 任务完成: taskId={task_id}, orderId={result.get('orderId')}")
        else:
            error = response.get("error", {})
            error_msg = error.get("msg", "Unknown error") if isinstance(error, dict) else str(error)
            await self._repo.fail(task_id, error_msg)
            logger.error(f"[期货回调] 任务失败: taskId={task_id}, error={error_msg}")

    async def _handle_spot_response(self, request_id: str, response: dict) -> None:
        """处理现货WS响应（回调）

        Args:
            request_id: 请求ID
            response: 响应数据
        """
        logger.info(f"[现货回调] 收到响应: requestId={request_id}, response={response}")

        # 1. 根据requestId查找任务
        task = await self._repo.find_by_request_id(request_id)
        if not task:
            logger.warning(f"[现货回调] 未找到任务: requestId={request_id}")
            return

        task_id = task["id"]

        # 2. 根据响应状态更新任务
        status = response.get("status", response.get("result", {}).get("status", 200))
        if status == 200:
            result = response.get("result", {})
            await self._repo.complete(task_id, result)
            logger.info(f"[现货回调] 任务完成: taskId={task_id}, orderId={result.get('orderId')}")
        else:
            error = response.get("error", {})
            error_msg = error.get("msg", "Unknown error") if isinstance(error, dict) else str(error)
            await self._repo.fail(task_id, error_msg)
            logger.error(f"[现货回调] 任务失败: taskId={task_id}, error={error_msg}")
