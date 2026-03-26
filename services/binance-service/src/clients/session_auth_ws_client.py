"""
会话级认证 WebSocket 客户端基类

统一设计：
- start() = connect() + _do_session_logon() + 认证成功
- stop() = 停止认证 + disconnect()
- 子类只需实现 _do_session_logon() 和 _handle_message()

设计原则：
1. 一个主入口：start() 负责完整启动流程
2. 一个退出出口：stop() 负责完整停止流程
3. 认证方法抽象：_do_session_logon() 由子类实现签名逻辑
"""

import asyncio
import logging
from abc import abstractmethod
from typing import Awaitable, Callable, Optional

from clients.base_ws_client import BaseWSClient, WSDataPackage

logger = logging.getLogger(__name__)


class SessionAuthWSClient(BaseWSClient):
    """会话级认证 WebSocket 客户端基类

    统一流程：
    1. start() → connect() → _do_session_logon() → 认证成功
    2. 接收循环持续运行，通过 _handle_message() 处理消息
    3. stop() → 停止认证 → disconnect()

    子类只需实现：
    - _do_session_logon(): 构建签名 payload 并发送 session.logon
    - _handle_message(): 处理业务事件（账户更新、订单更新等）

    Attributes:
        CLIENT_ID: 客户端唯一标识
    """

    # 认证相关状态
    _auth_event: Optional[asyncio.Event] = None
    _auth_success: bool = False
    _session_authenticated: bool = False
    _session_auth_lock: asyncio.Lock = asyncio.Lock()

    async def start(self) -> bool:
        """启动客户端（统一入口）

        流程：连接 → 认证 → 启动接收循环
        不需要在外部单独调用 connect() 或 authenticate()

        Returns:
            启动并认证成功返回 True，否则返回 False
        """
        if self._state.connected:
            logger.info(f"[{self.CLIENT_ID}] 已连接，跳过启动")
            return True

        logger.info(f"[{self.CLIENT_ID}] 正在启动客户端（会话级认证模式）...")

        try:
            # 1. 连接 WebSocket（基类实现，建立连接并启动接收循环）
            await self.connect()

            if not self._state.connected:
                logger.error(f"[{self.CLIENT_ID}] 连接失败")
                return False

            # 2. 会话级认证
            auth_success = await self._do_session_logon()
            if not auth_success:
                logger.error(f"[{self.CLIENT_ID}] 会话认证失败")
                await self.stop()
                return False

            # 3. 认证成功
            async with self._session_auth_lock:
                self._session_authenticated = True
            logger.info(f"[{self.CLIENT_ID}] 客户端启动成功")
            return True

        except Exception as e:
            logger.error(f"[{self.CLIENT_ID}] 启动异常: {e}")
            await self.stop()
            return False

    async def stop(self) -> None:
        """停止客户端（统一出口）

        流程：停止认证状态 → 断开连接
        """
        logger.info(f"[{self.CLIENT_ID}] 正在停止客户端...")

        # 重置认证状态
        async with self._session_auth_lock:
            self._session_authenticated = False
        self._auth_event = None
        self._auth_success = False

        # 断开连接（基类实现）
        await self.disconnect()

        logger.info(f"[{self.CLIENT_ID}] 客户端已停止")

    @abstractmethod
    async def _do_session_logon(self) -> bool:
        """执行 session.logon 认证（子类必须实现）

        子类实现签名逻辑：
        1. 构建 auth_params = {apiKey, timestamp}
        2. payload = "apiKey=xxx&timestamp=xxx"（按键排序）
        3. 使用子类特定的签名方式（Ed25519/HMAC-SHA256）
        4. 发送 session.logon 请求
        5. 等待认证结果（使用 asyncio.Event 同步，超时 30s）

        Returns:
            认证是否成功
        """
        ...

    def is_authenticated(self) -> bool:
        """查询认证状态

        Returns:
            已认证返回 True，否则返回 False
        """
        return self._session_authenticated
