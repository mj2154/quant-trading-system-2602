"""
账户订阅服务 v1.2

统一管理现货和期货账户的 WebSocket 订阅和定期快照。

数据更新策略（严格按照设计文档）：
1. 初始化：REST API 完整数据 -> 写入 account_info 表 + realtime_data 表
2. 实时推送：WebSocket 用户数据流 -> 直接覆盖写入 realtime_data 表
3. 定期兜底：REST API 完整快照 -> 覆盖写入 account_info 表 + realtime_data 表

关键约束：
- WebSocket 推送的是增量数据（仅包含变化的资产/持仓）
- realtime_data 表中的数据是增量数据的直接覆盖，不需要后端合并
- 前端必须先 GET 完整数据初始化，再订阅增量更新

数据存储说明：
- account_info 表：存储完整数据，供 GET 请求使用
- realtime_data 表：存储实时数据，用于 WebSocket 订阅推送

订阅键格式：
- 现货: BINANCE:ACCOUNT@SPOT
- 期货: BINANCE:ACCOUNT@FUTURES

存储到 realtime_data 表，触发 realtime.update 通知给 API 网关。
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from constants.binance import BinanceAccountSubscriptionKey
from clients.spot_user_stream_client import SpotUserStreamClient
from clients.futures_user_stream_client import FuturesUserStreamClient
from clients.spot_private_http_client import BinanceSpotPrivateHTTPClient
from clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient

logger = logging.getLogger(__name__)


class AccountSubscriptionService:
    """账户订阅服务 v1.1

    职责：
    1. 管理现货和期货账户的 WebSocket 连接
    2. 处理增量推送事件（直接覆盖写入）
    3. 定期获取完整快照（兜底机制）
    4. 将数据写入 realtime_data 表

    配置：
    - snapshot_interval: 完整快照间隔（秒），默认 5 分钟
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        api_key: str,
        futures_api_key: str,
        private_key_pem: bytes,
        signature_type: str = "ed25519",
        proxy_url: Optional[str] = None,
        snapshot_interval: int = 300,  # 默认 5 分钟
    ) -> None:
        """初始化服务

        Args:
            pool: 数据库连接池
            api_key: 现货 API Key
            futures_api_key: 期货 API Key
            private_key_pem: 私钥 PEM 格式
            signature_type: 签名类型
            proxy_url: 可选的代理 URL
            snapshot_interval: 完整快照间隔（秒）
        """
        self._pool = pool
        self._api_key = api_key
        self._futures_api_key = futures_api_key
        self._private_key_pem = private_key_pem
        self._signature_type = signature_type
        self._proxy_url = proxy_url
        self._snapshot_interval = snapshot_interval

        # 私有 HTTP 客户端
        self._spot_private_http: Optional[BinanceSpotPrivateHTTPClient] = None
        self._futures_private_http: Optional[BinanceFuturesPrivateHTTPClient] = None

        # 用户数据流客户端
        self._spot_user_stream: Optional[SpotUserStreamClient] = None
        self._futures_user_stream: Optional[FuturesUserStreamClient] = None

        # 状态
        self._running = False
        self._snapshot_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """启动服务"""
        if self._running:
            logger.warning("账户订阅服务已在运行")
            return

        logger.info("启动账户订阅服务 v1.1...")

        # 初始化现货私有 HTTP 客户端
        if self._api_key and self._private_key_pem:
            self._spot_private_http = BinanceSpotPrivateHTTPClient(
                api_key=self._api_key,
                private_key_pem=self._private_key_pem,
                signature_type=self._signature_type,
                proxy_url=self._proxy_url,
            )
            logger.info("现货私有 HTTP 客户端已初始化")
        else:
            logger.warning("现货 API Key 未配置，现货账户订阅不可用")

        # 初始化期货私有 HTTP 客户端
        if self._futures_api_key and self._private_key_pem:
            self._futures_private_http = BinanceFuturesPrivateHTTPClient(
                api_key=self._futures_api_key,
                private_key_pem=self._private_key_pem,
                signature_type=self._signature_type,
                proxy_url=self._proxy_url,
            )
            logger.info("期货私有 HTTP 客户端已初始化")
        else:
            logger.warning("期货 API Key 未配置，期货账户订阅不可用")

        # ========== 启动时立即获取快照（初始化） ==========
        if self._spot_private_http:
            await self._fetch_spot_snapshot()

        if self._futures_private_http:
            await self._fetch_futures_snapshot()

        # 启动现货用户数据流（增量推送）
        if self._spot_private_http:
            self._spot_user_stream = SpotUserStreamClient(
                api_key=self._api_key,
                private_key_pem=self._private_key_pem,
                signature_type=self._signature_type,
                proxy_url=self._proxy_url,
            )
            self._spot_user_stream.set_data_callback(self._handle_spot_data)
            await self._spot_user_stream.start()

        # 启动期货用户数据流（增量推送）
        if self._futures_private_http:
            self._futures_user_stream = FuturesUserStreamClient(
                api_key=self._futures_api_key,
                private_key_pem=self._private_key_pem,
                signature_type=self._signature_type,
                proxy_url=self._proxy_url,
            )
            self._futures_user_stream.set_data_callback(self._handle_futures_data)
            await self._futures_user_stream.start()

        # 启动定期快照任务（兜底机制）
        self._snapshot_task = asyncio.create_task(self._snapshot_loop())

        self._running = True
        logger.info("账户订阅服务 v1.1 已启动")

    async def stop(self) -> None:
        """停止服务"""
        if not self._running:
            return

        logger.info("停止账户订阅服务...")

        # 停止定期快照任务
        if self._snapshot_task:
            self._snapshot_task.cancel()
            try:
                await self._snapshot_task
            except asyncio.CancelledError:
                pass
            self._snapshot_task = None

        # 停止用户数据流客户端
        if self._spot_user_stream:
            await self._spot_user_stream.stop()
            self._spot_user_stream = None

        if self._futures_user_stream:
            await self._futures_user_stream.stop()
            self._futures_user_stream = None

        # 关闭 HTTP 客户端
        if self._spot_private_http:
            await self._spot_private_http.close()
            self._spot_private_http = None

        if self._futures_private_http:
            await self._futures_private_http.close()
            self._futures_private_http = None

        self._running = False
        logger.info("账户订阅服务已停止")

    # ========== 数据处理回调（直接覆盖写入） ==========

    async def _handle_spot_data(self, data: dict) -> None:
        """处理现货账户数据 - 直接覆盖写入

        WebSocket 推送的是增量数据，直接写入 realtime_data 表覆盖。

        Args:
            data: 解析后的账户数据（增量数据）
        """
        try:
            # 直接写入 realtime_data 表（覆盖）
            await self._write_realtime_data(
                subscription_key=BinanceAccountSubscriptionKey.SPOT,
                data_type="ACCOUNT",
                data=data,
            )

            logger.debug(f"现货账户数据已更新: {data.get('event_type')}")

        except Exception as e:
            logger.error(f"处理现货账户数据失败: {e}")

    async def _handle_futures_data(self, data: dict) -> None:
        """处理期货账户数据 - 直接覆盖写入

        WebSocket 推送的是增量数据，直接写入 realtime_data 表覆盖。

        Args:
            data: 解析后的账户数据（增量数据）
        """
        try:
            # 直接写入 realtime_data 表（覆盖）
            await self._write_realtime_data(
                subscription_key=BinanceAccountSubscriptionKey.FUTURES,
                data_type="ACCOUNT",
                data=data,
            )

            logger.debug(f"期货账户数据已更新: {data.get('event_type')}")

        except Exception as e:
            logger.error(f"处理期货账户数据失败: {e}")

    # ========== 实时数据写入 ==========

    async def _write_realtime_data(
        self,
        subscription_key: str,
        data_type: str,
        data: dict,
    ) -> None:
        """写入实时数据到数据库

        Args:
            subscription_key: 订阅键
            data_type: 数据类型
            data: 实时数据
        """
        try:
            # 使用 UPSERT 写入数据（覆盖）
            query = """
                INSERT INTO realtime_data (subscription_key, data_type, data, event_time)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (subscription_key) DO UPDATE SET
                    data = EXCLUDED.data,
                    event_time = EXCLUDED.event_time,
                    updated_at = NOW()
            """

            data_json = json.dumps(data)

            async with self._pool.acquire() as conn:
                await conn.execute(
                    query,
                    subscription_key,
                    data_type,
                    data_json,
                )

            logger.debug(f"已写入实时数据: {subscription_key}")

        except Exception as e:
            logger.error(f"写入实时数据失败: {e}")

    # ========== 账户信息写入 ==========

    async def _write_account_info(
        self,
        account_type: str,
        data: dict,
        update_time: int | None = None,
    ) -> None:
        """写入账户信息到 account_info 表

        Args:
            account_type: 账户类型 (SPOT / FUTURES)
            data: 账户数据
            update_time: 币安返回的更新时间
        """
        try:
            query = """
                INSERT INTO account_info (account_type, data, update_time, updated_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (account_type) DO UPDATE SET
                    data = EXCLUDED.data,
                    update_time = EXCLUDED.update_time,
                    updated_at = EXCLUDED.updated_at
            """

            data_json = json.dumps(data)

            async with self._pool.acquire() as conn:
                await conn.execute(
                    query,
                    account_type,
                    data_json,
                    update_time,
                    datetime.now(timezone.utc),
                )

            logger.debug(f"已写入账户信息: {account_type}")

        except Exception as e:
            logger.error(f"写入账户信息失败: {e}")

    # ========== 快照任务（兜底机制） ==========

    async def _snapshot_loop(self) -> None:
        """定期获取完整快照（兜底机制）

        每隔 snapshot_interval 秒获取一次完整快照，覆盖写入 realtime_data 表
        """
        logger.info("账户快照循环启动")

        while self._running:
            try:
                # 等待间隔
                await asyncio.sleep(self._snapshot_interval)
                if not self._running:
                    break

                # 获取现货快照
                if self._spot_private_http:
                    await self._fetch_spot_snapshot()

                # 获取期货快照
                if self._futures_private_http:
                    await self._fetch_futures_snapshot()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"账户快照循环异常: {e}")

        logger.info("账户快照循环结束")

    async def _fetch_spot_snapshot(self) -> None:
        """获取现货账户完整快照

        同时写入：
        1. account_info 表 - 存储完整数据（供 GET 请求）
        2. realtime_data 表 - 存储快照数据（用于订阅推送）
        """
        try:
            # 调用 REST API 获取账户信息
            account_info = await self._spot_private_http.get_account_info()

            # 转换为存储格式
            # 注意：balances 是 Pydantic 模型列表，不是字典列表
            snapshot_data = {
                "source": "rest_api",
                "snapshot_time": account_info.update_time,
                "balances": [
                    {
                        "asset": b.asset,
                        "free": b.free,
                        "locked": b.locked,
                    }
                    for b in account_info.balances
                    if float(b.free or "0") > 0 or float(b.locked or "0") > 0
                ],
            }

            # 写入 account_info 表（完整数据，供 GET 请求）
            await self._write_account_info(
                account_type="SPOT",
                data=snapshot_data,
                update_time=account_info.update_time,
            )

            # 写入 realtime_data 表（快照数据，用于订阅推送）
            await self._write_realtime_data(
                subscription_key=BinanceAccountSubscriptionKey.SPOT,
                data_type="ACCOUNT",
                data=snapshot_data,
            )

            logger.info(f"现货账户快照已更新 (update_time={account_info.update_time})")

        except Exception as e:
            logger.error(f"获取现货账户快照失败: {e}")

    async def _fetch_futures_snapshot(self) -> None:
        """获取期货账户完整快照

        同时写入：
        1. account_info 表 - 存储完整数据（供 GET 请求）
        2. realtime_data 表 - 存储快照数据（用于订阅推送）
        """
        try:
            # 调用 REST API 获取账户信息
            account_info = await self._futures_private_http.get_account_info()

            # 从 assets 数组中获取最新更新时间（V3 API 在 assets[0] 中返回 updateTime）
            snapshot_time = (
                account_info.assets[0].update_time
                if account_info.assets and account_info.assets[0].update_time
                else None
            )

            # 转换为存储格式
            # 注意：positions 和 assets 是 Pydantic 模型列表，不是字典列表
            # V3 API 返回字段：symbol, positionSide, positionAmt, unrealizedProfit,
            # isolatedMargin, notional, isolatedWallet, initialMargin, maintMargin, updateTime
            snapshot_data = {
                "source": "rest_api",
                "snapshot_time": snapshot_time,
                "total_wallet_balance": account_info.total_wallet_balance,
                "total_unrealized_profit": account_info.total_unrealized_profit,
                "total_margin_balance": account_info.total_margin_balance,
                "available_balance": account_info.available_balance,
                "positions": [
                    {
                        "symbol": p.symbol,
                        "position_amt": p.position_amt,
                        "unrealized_profit": p.unrealized_profit,
                        "isolated_margin": p.isolated_margin,
                        "notional": p.notional_value,
                        "isolated_wallet": p.isolated_wallet,
                        "initial_margin": p.initial_margin,
                        "maint_margin": p.maint_margin,
                        "position_side": p.position_side,
                    }
                    for p in account_info.positions
                    if float(p.position_amt or "0") != 0
                ],
                "assets": [
                    {
                        "asset": a.asset,
                        "wallet_balance": a.wallet_balance,
                        "unrealized_profit": a.unrealized_profit,
                        "margin_balance": a.margin_balance,
                        "available_balance": a.available_balance,
                    }
                    for a in account_info.assets
                ],
            }

            # 写入 account_info 表（完整数据，供 GET 请求）
            await self._write_account_info(
                account_type="FUTURES",
                data=snapshot_data,
                update_time=snapshot_time,
            )

            # 写入 realtime_data 表（快照数据，用于订阅推送）
            await self._write_realtime_data(
                subscription_key=BinanceAccountSubscriptionKey.FUTURES,
                data_type="ACCOUNT",
                data=snapshot_data,
            )

            logger.info(f"期货账户快照已更新 (snapshot_time={snapshot_time})")

        except Exception as e:
            logger.error(f"获取期货账户快照失败: {e}")
