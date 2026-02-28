"""
现货用户数据流客户端

管理现货账户的 listenKey 创建、续期和 WebSocket 连接。
接收现货账户更新事件（outboundAccountPosition, balanceUpdate, executionReport）。

API文档: https://binance-docs.github.io/apidocs/spot/cn/#user-data-stream
"""

import asyncio
import json
import logging
import time
from typing import Callable, Awaitable, Optional

import httpx

logger = logging.getLogger(__name__)


class SpotUserStreamClient:
    """现货用户数据流客户端

    职责：
    1. 管理 listenKey 的创建、续期和关闭
    2. 建立 WebSocket 连接接收账户更新事件
    3. 将接收到的数据通过回调传递给调用方

    数据流程：
    1. start() -> 创建 listenKey -> 建立 WebSocket 连接
    2. 接收事件 -> 解析事件 -> 调用 _data_callback
    3. stop() -> 关闭 WebSocket -> 关闭 listenKey

    事件类型：
    - outboundAccountPosition: 账户余额变化
    - balanceUpdate: 充值/提取/划转
    - executionReport: 订单更新
    """

    # listenKey 有效期（毫秒）
    LISTEN_KEY_EXPIRY_MS = 60 * 60 * 1000  # 60分钟
    # 续期间隔（秒），提前5分钟续期
    RENEW_INTERVAL_SEC = (LISTEN_KEY_EXPIRY_MS / 1000) - 5 * 60

    def __init__(
        self,
        api_key: str,
        private_key_pem: bytes,
        signature_type: str = "ed25519",
        proxy_url: Optional[str] = None,
    ) -> None:
        """初始化客户端

        Args:
            api_key: 币安 API Key
            private_key_pem: 私钥 PEM 格式
            signature_type: 签名类型 ("ed25519" 或 "rsa")
            proxy_url: 可选的代理 URL
        """
        self._api_key = api_key
        self._private_key_pem = private_key_pem
        self._signature_type = signature_type
        self._proxy_url = proxy_url

        self._listen_key: Optional[str] = None
        self._ws_connection: Optional[any] = None
        self._running = False
        self._receive_task: Optional[asyncio.Task] = None
        self._renew_task: Optional[asyncio.Task] = None
        self._data_callback: Optional[Callable[[dict], Awaitable[None]]] = None

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._running and self._ws_connection is not None

    def set_data_callback(self, callback: Callable[[dict], Awaitable[None]]) -> None:
        """设置数据回调

        Args:
            callback: 异步回调函数，接收解析后的账户数据
        """
        self._data_callback = callback

    async def start(self) -> bool:
        """启动客户端

        Returns:
            是否成功启动
        """
        if self._running:
            logger.warning("现货用户数据流客户端已在运行")
            return True

        try:
            # 1. 创建 listenKey
            self._listen_key = await self._create_listen_key()
            if not self._listen_key:
                logger.error("创建 listenKey 失败")
                return False

            logger.info(f"现货 listenKey 已创建: {self._listen_key[:10]}...")

            # 2. 建立 WebSocket 连接
            from websockets.asyncio.client import connect

            ws_url = f"wss://stream.binance.com:9443/ws/{self._listen_key}"
            connect_kwargs: dict[str, str] = {}
            if self._proxy_url:
                connect_kwargs["proxy"] = self._proxy_url

            self._ws_connection = await connect(ws_url, **connect_kwargs)
            self._running = True

            logger.info("现货用户数据流 WebSocket 已连接")

            # 3. 启动接收循环
            self._receive_task = asyncio.create_task(self._receive_loop())

            # 4. 启动续期任务
            self._renew_task = asyncio.create_task(self._renew_loop())

            return True

        except Exception as e:
            logger.error(f"启动现货用户数据流客户端失败: {e}")
            await self.stop()
            return False

    async def stop(self) -> None:
        """停止客户端"""
        if not self._running:
            return

        logger.info("停止现货用户数据流客户端...")
        self._running = False

        # 取消续期任务
        if self._renew_task:
            self._renew_task.cancel()
            try:
                await self._renew_task
            except asyncio.CancelledError:
                pass
            self._renew_task = None

        # 取消接收任务
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        # 关闭 WebSocket
        if self._ws_connection:
            try:
                await self._ws_connection.close()
            except Exception as e:
                logger.warning(f"关闭 WebSocket 时出错: {e}")
            self._ws_connection = None

        # 关闭 listenKey
        if self._listen_key:
            await self._close_listen_key(self._listen_key)
            self._listen_key = None

        logger.info("现货用户数据流客户端已停止")

    async def _receive_loop(self) -> None:
        """接收数据循环"""
        logger.info("现货用户数据流接收循环启动")

        try:
            async for message in self._ws_connection:
                if not self._running:
                    break

                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning("收到无效的 JSON 消息")
                except Exception as e:
                    logger.error(f"处理现货用户数据流消息时出错: {e}")

        except asyncio.CancelledError:
            logger.info("现货用户数据流接收循环已取消")
        except Exception as e:
            logger.error(f"现货用户数据流接收循环异常: {e}")
        finally:
            if self._running:
                # 尝试重新连接
                logger.info("现货用户数据流断开，尝试重新连接...")
                await self._reconnect()

    async def _handle_message(self, message: dict) -> None:
        """处理接收到的消息

        Args:
            message: WebSocket 消息
        """
        event_type = message.get("e", "unknown")

        logger.debug(f"收到现货账户事件: {event_type}")

        # 解析事件数据
        if event_type == "outboundAccountPosition":
            # 账户余额变化
            processed_data = {
                "source": "websocket",
                "event_type": event_type,
                "update_time": message.get("u"),  # 事件结束时间
                "balances": message.get("B", []),
            }
        elif event_type == "balanceUpdate":
            # 充值/提取/划转
            processed_data = {
                "source": "websocket",
                "event_type": event_type,
                "update_time": message.get("u"),
                "asset": message.get("a"),
                "balance_delta": message.get("d"),
                "clear_time": message.get("T"),
            }
        elif event_type == "executionReport":
            # 订单更新
            processed_data = {
                "source": "websocket",
                "event_type": event_type,
                "update_time": message.get("T"),
                "symbol": message.get("s"),
                "side": message.get("S"),
                "order_type": message.get("o"),
                "order_status": message.get("X"),
                "order_id": message.get("i"),
                "client_order_id": message.get("c"),
                "price": message.get("p"),
                "quantity": message.get("q"),
                "accumulated_quantity": message.get("z"),
            }
        else:
            # 未知事件类型
            logger.warning(f"未知的现货账户事件类型: {event_type}")
            processed_data = {
                "source": "websocket",
                "event_type": event_type,
                "raw": message,
            }

        # 调用回调
        if self._data_callback:
            try:
                await self._data_callback(processed_data)
            except Exception as e:
                logger.error(f"调用数据回调失败: {e}")

    async def _renew_loop(self) -> None:
        """续期循环

        每隔 RENEW_INTERVAL_SEC 秒续期一次 listenKey
        """
        logger.info("现货用户数据流续期循环启动")

        while self._running:
            try:
                await asyncio.sleep(self.RENEW_INTERVAL_SEC)
                if not self._running:
                    break

                # 续期 listenKey
                success = await self._renew_listen_key()
                if success:
                    logger.debug("现货 listenKey 续期成功")
                else:
                    logger.warning("现货 listenKey 续期失败")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"现货 listenKey 续期循环异常: {e}")

        logger.info("现货用户数据流续期循环结束")

    async def _reconnect(self) -> None:
        """重新连接"""
        if not self._running:
            return

        # 关闭旧连接
        if self._ws_connection:
            try:
                await self._ws_connection.close()
            except Exception:
                pass
            self._ws_connection = None

        # 等待后重试
        for attempt in range(5):
            if not self._running:
                return

            logger.info(f"尝试重新连接现货用户数据流 (尝试 {attempt + 1}/5)...")
            await asyncio.sleep(5)

            success = await self.start()
            if success:
                logger.info("现货用户数据流重连成功")
                return

        logger.error("现货用户数据流重连失败，停止客户端")
        await self.stop()

    # ========== listenKey 管理 ==========

    async def _create_listen_key(self) -> Optional[str]:
        """创建 listenKey

        Returns:
            listenKey 字符串，失败返回 None
        """
        try:
            url = "https://demo-api.binance.com/api/v3/userDataStream"

            headers = {"X-MBX-APIKEY": self._api_key}

            async with httpx.AsyncClient(proxy=self._proxy_url) as client:
                response = await client.post(url, headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data.get("listenKey")

        except Exception as e:
            logger.error(f"创建现货 listenKey 失败: {e}")
            return None

    async def _renew_listen_key(self) -> bool:
        """续期 listenKey

        Returns:
            是否成功
        """
        if not self._listen_key:
            return False

        try:
            url = "https://demo-api.binance.com/api/v3/userDataStream"

            headers = {"X-MBX-APIKEY": self._api_key}
            params = {"listenKey": self._listen_key}

            async with httpx.AsyncClient(proxy=self._proxy_url) as client:
                response = await client.put(url, headers=headers, params=params, timeout=10.0)
                response.raise_for_status()
                return True

        except Exception as e:
            logger.error(f"续期现货 listenKey 失败: {e}")
            return False

    async def _close_listen_key(self, listen_key: str) -> None:
        """关闭 listenKey

        Args:
            listen_key: 要关闭的 listenKey
        """
        try:
            url = "https://demo-api.binance.com/api/v3/userDataStream"

            headers = {"X-MBX-APIKEY": self._api_key}
            params = {"listenKey": listen_key}

            async with httpx.AsyncClient(proxy=self._proxy_url) as client:
                response = await client.delete(url, headers=headers, params=params, timeout=10.0)
                response.raise_for_status()
                logger.info(f"现货 listenKey 已关闭: {listen_key[:10]}...")

        except Exception as e:
            logger.warning(f"关闭现货 listenKey 失败: {e}")
