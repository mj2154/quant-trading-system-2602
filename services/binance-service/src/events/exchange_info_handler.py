"""
交易所信息处理器

从币安API获取交易所信息并写入数据库。

任务格式：
- action: "system.fetch_exchange_info"
- resource: "BINANCE" 或 "BINANCE:spot" 或 "BINANCE:futures"
- params: {"mode": "all"} 或 {"market_type": "SPOT"}

数据流程：
1. 解析任务载荷
2. 根据 market_type 调用对应的 HTTP client
3. 转换为 ExchangeInfo 模型
4. 全量替换 exchange_info 表（先删除旧数据，再插入新数据）

重要说明：
- 使用全量替换模式而非增量更新，确保数据库中的信息与币安API完全一致
- 当某个交易对从币安API中移除时，数据库中的对应记录也会被清理
- 通过数据库事务确保操作的原子性
"""

import logging
from typing import Optional

from clients import BinanceSpotHTTPClient, BinanceFuturesHTTPClient
from storage import ExchangeInfoRepository
from models import ExchangeInfoResponse, ExchangeInfo, MarketType

logger = logging.getLogger(__name__)


class ExchangeInfoHandler:
    """交易所信息处理器

    负责从币安API获取交易所信息并存储到数据库。
    """

    def __init__(
        self,
        spot_http: Optional[BinanceSpotHTTPClient] = None,
        futures_http: Optional[BinanceFuturesHTTPClient] = None,
        exchange_repo: Optional[ExchangeInfoRepository] = None,
    ) -> None:
        """初始化处理器

        Args:
            spot_http: 现货 HTTP 客户端
            futures_http: 期货 HTTP 客户端
            exchange_repo: 交易所信息仓储
        """
        self._spot_http = spot_http
        self._futures_http = futures_http
        self._exchange_repo = exchange_repo

    async def handle_fetch_exchange_info(
        self,
        action: str,
        resource: str,
        params: dict,
    ) -> None:
        """处理获取交易所信息任务

        Args:
            action: 任务动作，如 "system.fetch_exchange_info"
            resource: 资源标识，如 "BINANCE" 或 "BINANCE:spot"
            params: 额外参数字典，如 {"mode": "all"}
        """
        # 解析 market_type
        market_type = params.get("mode", "all")
        if resource:
            # 从 resource 中解析，如 "BINANCE:spot" -> "SPOT"
            if ":" in resource:
                _, suffix = resource.split(":", 1)
                if suffix.lower() == "spot":
                    market_type = "SPOT"
                elif suffix.lower() in ["futures", "perp", "perpetual"]:
                    market_type = "FUTURES"

        logger.info(
            f"获取交易所信息: action={action}, resource={resource}, mode={market_type}"
        )

        try:
            # 获取现货交易所信息
            if market_type in ["all", "SPOT"]:
                await self._sync_spot_exchange_info()

            # 获取期货交易所信息
            if market_type in ["all", "FUTURES"]:
                await self._sync_futures_exchange_info()

            logger.info("交易所信息同步完成")

        except Exception as e:
            logger.error(f"同步交易所信息失败: {e}")
            raise

    async def _sync_spot_exchange_info(self) -> None:
        """同步现货交易所信息"""
        if not self._spot_http:
            logger.warning("现货 HTTP 客户端未初始化，跳过现货交易所信息同步")
            return

        try:
            raw_info = await self._spot_http.get_exchange_info()

            # 使用 Pydantic 模型验证数据
            info_response = ExchangeInfoResponse.model_validate(raw_info)

            # 转换为 ExchangeInfo 模型并存储
            exchange_infos = []
            for symbol_data in info_response.symbols:
                exchange_info = ExchangeInfo(
                    exchange="BINANCE",
                    market_type=MarketType.SPOT,
                    symbol=symbol_data.symbol,
                    base_asset=symbol_data.base_asset,
                    quote_asset=symbol_data.quote_asset,
                    base_asset_precision=symbol_data.base_asset_precision,
                    quote_precision=symbol_data.quote_precision,
                    quote_asset_precision=symbol_data.quote_asset_precision,
                    base_commission_precision=symbol_data.base_commission_precision,
                    quote_commission_precision=symbol_data.quote_commission_precision,
                    status=symbol_data.status,
                    filters={f["filterType"]: f for f in symbol_data.filters},
                    order_types=symbol_data.order_types,
                    permissions=symbol_data.permissions,
                    iceberg_allowed=symbol_data.iceberg_allowed,
                    oco_allowed=symbol_data.oco_allowed,
                )
                exchange_infos.append(exchange_info)

            if self._exchange_repo:
                # 使用全量替换模式，确保数据一致性
                count = await self._exchange_repo.replace_exchange_infos(
                    exchange_infos, exchange="BINANCE", market_type=MarketType.SPOT
                )
                logger.info(f"已同步 {count} 条现货交易所信息")
            else:
                logger.warning("交易所信息仓储未初始化，无法写入数据")

        except Exception as e:
            logger.error(f"同步现货交易所信息失败: {e}")
            raise

    async def _sync_futures_exchange_info(self) -> None:
        """同步期货交易所信息"""
        if not self._futures_http:
            logger.warning("期货 HTTP 客户端未初始化，跳过期货交易所信息同步")
            return

        try:
            raw_info = await self._futures_http.get_exchange_info()

            # 使用 Pydantic 模型验证数据
            info_response = ExchangeInfoResponse.model_validate(raw_info)

            # 转换为 ExchangeInfo 模型并存储
            exchange_infos = []
            for symbol_data in info_response.symbols:
                exchange_info = ExchangeInfo(
                    exchange="BINANCE",
                    market_type=MarketType.FUTURES,
                    symbol=symbol_data.symbol,
                    base_asset=symbol_data.base_asset,
                    quote_asset=symbol_data.quote_asset,
                    base_asset_precision=symbol_data.base_asset_precision,
                    quote_precision=symbol_data.quote_precision,
                    quote_asset_precision=symbol_data.quote_asset_precision,
                    base_commission_precision=symbol_data.base_commission_precision,
                    quote_commission_precision=symbol_data.quote_commission_precision,
                    status=symbol_data.status,
                    filters={f["filterType"]: f for f in symbol_data.filters},
                    order_types=symbol_data.order_types,
                    permissions=symbol_data.permissions,
                    iceberg_allowed=symbol_data.iceberg_allowed,
                    oco_allowed=symbol_data.oco_allowed,
                )
                exchange_infos.append(exchange_info)

            if self._exchange_repo:
                # 使用全量替换模式，确保数据一致性
                count = await self._exchange_repo.replace_exchange_infos(
                    exchange_infos, exchange="BINANCE", market_type=MarketType.FUTURES
                )
                logger.info(f"已同步 {count} 条期货交易所信息")
            else:
                logger.warning("交易所信息仓储未初始化，无法写入数据")

        except Exception as e:
            logger.error(f"同步期货交易所信息失败: {e}")
            raise
