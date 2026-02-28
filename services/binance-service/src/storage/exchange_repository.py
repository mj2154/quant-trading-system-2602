"""
交易所信息存储

负责将交易所交易对信息写入 exchange_info 表。
支持两种写入模式：
1. upsert_exchange_infos(): 增量更新（保留现有记录，仅更新/插入）
2. replace_exchange_infos(): 全量替换（删除旧数据，重新插入，确保数据一致性）

使用 upsert_exchange_info() 存储过程实现高效的插入或更新。
"""

import json
import logging
from typing import Optional

import asyncpg

from models import ExchangeInfo

logger = logging.getLogger(__name__)


class ExchangeInfoRepository:
    """交易所信息仓储

    职责：
    - 将交易所信息写入 exchange_info 表
    - 支持两种写入模式：
      * upsert_exchange_infos(): 增量更新，保留现有记录
      * replace_exchange_infos(): 全量替换，删除旧数据后重新插入
    - 查询交易所信息

    数据一致性说明：
    - 增量更新：仅更新API返回的交易对，不影响其他记录
    - 全量替换：删除指定交易所和市场类型的所有记录，重新插入API返回的数据
      这种方式确保数据库中的信息与API完全一致，避免残留过时数据
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        """初始化仓储

        Args:
            pool: asyncpg 连接池
        """
        self._pool = pool

    async def upsert_exchange_info(
        self,
        data: ExchangeInfo,
    ) -> int:
        """Upsert 单条交易所信息

        Args:
            data: ExchangeInfo 模型实例

        Returns:
            记录的数据库ID
        """
        query = """
            SELECT upsert_exchange_info(
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28
            )
        """

        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                query,
                data.exchange,
                data.market_type,
                data.symbol,
                data.base_asset,
                data.quote_asset,
                data.status,
                data.base_asset_precision,
                data.quote_precision,
                data.quote_asset_precision,
                data.base_commission_precision,
                data.quote_commission_precision,
                json.dumps(data.filters),
                json.dumps(data.order_types),
                json.dumps(data.permissions),
                data.iceberg_allowed,
                data.oco_allowed,
                data.oto_allowed,
                data.opo_allowed,
                data.quote_order_qty_market_allowed,
                data.allow_trailing_stop,
                data.cancel_replace_allowed,
                data.amend_allowed,
                data.peg_instructions_allowed,
                data.is_spot_trading_allowed,
                data.is_margin_trading_allowed,
                json.dumps(data.permission_sets),
                data.default_self_trade_prevention_mode,
                json.dumps(data.allowed_self_trade_prevention_modes),
            )

        logger.debug(
            f"交易所信息已写入: {data.exchange}:{data.symbol} ({data.market_type})"
        )
        return result

    async def upsert_exchange_infos(
        self,
        infos: list[ExchangeInfo],
    ) -> int:
        """批量Upsert交易所信息

        Args:
            infos: ExchangeInfo 模型实例列表

        Returns:
            处理的记录数
        """
        if not infos:
            return 0

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for info in infos:
                    await conn.fetchval(
                        """
                        SELECT upsert_exchange_info(
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                            $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28
                        )
                        """,
                        info.exchange,
                        info.market_type,
                        info.symbol,
                        info.base_asset,
                        info.quote_asset,
                        info.status,
                        info.base_asset_precision,
                        info.quote_precision,
                        info.quote_asset_precision,
                        info.base_commission_precision,
                        info.quote_commission_precision,
                        json.dumps(info.filters),
                        json.dumps(info.order_types),
                        json.dumps(info.permissions),
                        info.iceberg_allowed,
                        info.oco_allowed,
                        info.oto_allowed,
                        info.opo_allowed,
                        info.quote_order_qty_market_allowed,
                        info.allow_trailing_stop,
                        info.cancel_replace_allowed,
                        info.amend_allowed,
                        info.peg_instructions_allowed,
                        info.is_spot_trading_allowed,
                        info.is_margin_trading_allowed,
                        json.dumps(info.permission_sets),
                        info.default_self_trade_prevention_mode,
                        json.dumps(info.allowed_self_trade_prevention_modes),
                    )

        logger.info(f"批量写入 {len(infos)} 条交易所信息")
        return len(infos)

    async def get_by_symbol(
        self,
        exchange: str,
        market_type: str,
        symbol: str,
    ) -> Optional[ExchangeInfo]:
        """根据交易对获取交易所信息

        Args:
            exchange: 交易所名称
            market_type: 市场类型
            symbol: 交易对符号

        Returns:
            ExchangeInfo 实例或 None
        """
        query = """
            SELECT
                exchange,
                market_type,
                symbol,
                base_asset,
                quote_asset,
                status,
                base_asset_precision,
                quote_precision,
                quote_asset_precision,
                base_commission_precision,
                quote_commission_precision,
                filters,
                order_types,
                permissions,
                iceberg_allowed,
                oco_allowed,
                oto_allowed,
                opo_allowed,
                quote_order_qty_market_allowed,
                allow_trailing_stop,
                cancel_replace_allowed,
                amend_allowed,
                peg_instructions_allowed,
                is_spot_trading_allowed,
                is_margin_trading_allowed,
                permission_sets,
                default_self_trade_prevention_mode,
                allowed_self_trade_prevention_modes,
                last_updated
            FROM exchange_info
            WHERE exchange = $1
              AND market_type = $2
              AND symbol = $3
        """

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, exchange, market_type, symbol)

        if row:
            return ExchangeInfo(
                exchange=row["exchange"],
                market_type=row["market_type"],
                symbol=row["symbol"],
                base_asset=row["base_asset"],
                quote_asset=row["quote_asset"],
                status=row["status"],
                base_asset_precision=row["base_asset_precision"],
                quote_precision=row["quote_precision"],
                quote_asset_precision=row["quote_asset_precision"],
                base_commission_precision=row["base_commission_precision"],
                quote_commission_precision=row["quote_commission_precision"],
                filters=row["filters"],
                order_types=row["order_types"],
                permissions=row["permissions"],
                iceberg_allowed=row["iceberg_allowed"],
                oco_allowed=row["oco_allowed"],
                oto_allowed=row["oto_allowed"],
                opo_allowed=row["opo_allowed"],
                quote_order_qty_market_allowed=row["quote_order_qty_market_allowed"],
                allow_trailing_stop=row["allow_trailing_stop"],
                cancel_replace_allowed=row["cancel_replace_allowed"],
                amend_allowed=row["amend_allowed"],
                peg_instructions_allowed=row["peg_instructions_allowed"],
                is_spot_trading_allowed=row["is_spot_trading_allowed"],
                is_margin_trading_allowed=row["is_margin_trading_allowed"],
                permission_sets=row["permission_sets"],
                default_self_trade_prevention_mode=row[
                    "default_self_trade_prevention_mode"
                ],
                allowed_self_trade_prevention_modes=row[
                    "allowed_self_trade_prevention_modes"
                ],
                last_updated=row["last_updated"],
            )
        return None

    async def get_all_trading(
        self,
        exchange: str = "BINANCE",
        market_type: Optional[str] = None,
    ) -> list[ExchangeInfo]:
        """获取所有交易中的交易对信息

        Args:
            exchange: 交易所名称
            market_type: 市场类型（可选）

        Returns:
            ExchangeInfo 实例列表
        """
        query = """
            SELECT
                exchange,
                market_type,
                symbol,
                base_asset,
                quote_asset,
                status,
                base_asset_precision,
                quote_precision,
                quote_asset_precision,
                base_commission_precision,
                quote_commission_precision,
                filters,
                order_types,
                permissions,
                iceberg_allowed,
                oco_allowed,
                oto_allowed,
                opo_allowed,
                quote_order_qty_market_allowed,
                allow_trailing_stop,
                cancel_replace_allowed,
                amend_allowed,
                peg_instructions_allowed,
                is_spot_trading_allowed,
                is_margin_trading_allowed,
                permission_sets,
                default_self_trade_prevention_mode,
                allowed_self_trade_prevention_modes,
                last_updated
            FROM exchange_info
            WHERE exchange = $1
              AND status = 'TRADING'
        """
        params: list = [exchange]

        if market_type:
            query += " AND market_type = $2"
            params.append(market_type)

        query += " ORDER BY symbol"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            ExchangeInfo(
                exchange=row["exchange"],
                market_type=row["market_type"],
                symbol=row["symbol"],
                base_asset=row["base_asset"],
                quote_asset=row["quote_asset"],
                status=row["status"],
                base_asset_precision=row["base_asset_precision"],
                quote_precision=row["quote_precision"],
                quote_asset_precision=row["quote_asset_precision"],
                base_commission_precision=row["base_commission_precision"],
                quote_commission_precision=row["quote_commission_precision"],
                filters=row["filters"],
                order_types=row["order_types"],
                permissions=row["permissions"],
                iceberg_allowed=row["iceberg_allowed"],
                oco_allowed=row["oco_allowed"],
                oto_allowed=row["oto_allowed"],
                opo_allowed=row["opo_allowed"],
                quote_order_qty_market_allowed=row["quote_order_qty_market_allowed"],
                allow_trailing_stop=row["allow_trailing_stop"],
                cancel_replace_allowed=row["cancel_replace_allowed"],
                amend_allowed=row["amend_allowed"],
                peg_instructions_allowed=row["peg_instructions_allowed"],
                is_spot_trading_allowed=row["is_spot_trading_allowed"],
                is_margin_trading_allowed=row["is_margin_trading_allowed"],
                permission_sets=row["permission_sets"],
                default_self_trade_prevention_mode=row[
                    "default_self_trade_prevention_mode"
                ],
                allowed_self_trade_prevention_modes=row[
                    "allowed_self_trade_prevention_modes"
                ],
                last_updated=row["last_updated"],
            )
            for row in rows
        ]

    async def count_by_market(self, exchange: str = "BINANCE") -> dict[str, int]:
        """统计各市场类型的交易对数量

        Args:
            exchange: 交易所名称

        Returns:
            市场类型 -> 数量的映射
        """
        query = """
            SELECT market_type, COUNT(*) as count
            FROM exchange_info
            WHERE exchange = $1
            GROUP BY market_type
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, exchange)

        return {row["market_type"]: row["count"] for row in rows}

    async def replace_exchange_infos(
        self,
        infos: list[ExchangeInfo],
        exchange: str,
        market_type: str,
    ) -> int:
        """全量替换交易所信息

        先删除指定交易所和市场类型的所有记录，然后插入新记录。
        这确保数据库中的信息与API返回的信息完全一致。

        Args:
            infos: 新的交易所信息列表
            exchange: 交易所名称
            market_type: 市场类型

        Returns:
            插入的记录数
        """
        if not infos:
            logger.warning("没有要替换的交易所信息")
            return 0

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # 删除旧数据
                deleted_count = await conn.execute(
                    "DELETE FROM exchange_info WHERE exchange = $1 AND market_type = $2",
                    exchange,
                    market_type,
                )
                logger.info(
                    f"已删除 {deleted_count} 条旧的 {exchange}:{market_type} 交易所信息"
                )

                # 插入新数据
                inserted_count = 0
                for info in infos:
                    await conn.fetchval(
                        """
                        SELECT upsert_exchange_info(
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                            $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28
                        )
                        """,
                        exchange,
                        market_type,
                        info.symbol,
                        info.base_asset,
                        info.quote_asset,
                        info.status,
                        info.base_asset_precision,
                        info.quote_precision,
                        info.quote_asset_precision,
                        info.base_commission_precision,
                        info.quote_commission_precision,
                        json.dumps(info.filters),
                        json.dumps(info.order_types),
                        json.dumps(info.permissions),
                        info.iceberg_allowed,
                        info.oco_allowed,
                        info.oto_allowed,
                        info.opo_allowed,
                        info.quote_order_qty_market_allowed,
                        info.allow_trailing_stop,
                        info.cancel_replace_allowed,
                        info.amend_allowed,
                        info.peg_instructions_allowed,
                        info.is_spot_trading_allowed,
                        info.is_margin_trading_allowed,
                        json.dumps(info.permission_sets),
                        info.default_self_trade_prevention_mode,
                        json.dumps(info.allowed_self_trade_prevention_modes),
                    )
                    inserted_count += 1

                logger.info(
                    f"已插入 {inserted_count} 条新的 {exchange}:{market_type} 交易所信息"
                )
                return inserted_count

    async def close(self) -> None:
        """关闭连接池"""
        await self._pool.close()
