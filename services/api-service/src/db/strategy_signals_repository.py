"""
信号仓储 - 基于 strategy_signals 表

使用 asyncpg 原生 SQL。
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SignalRecord:
    """信号记录 - 严格遵循 design/QUANT_TRADING_SYSTEM_ARCHITECTURE.md 设计"""

    id: int
    alert_id: str | None
    strategy_type: str
    symbol: str
    interval: str
    trigger_type: str | None
    signal_value: bool | None
    computed_at: datetime
    source_subscription_key: str | None
    metadata: dict[str, Any]


class StrategySignalsRepository:
    """信号仓储 - 基于 strategy_signals 表

    职责：
    - 查询信号列表
    - 根据条件过滤信号
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        """初始化仓储

        Args:
            pool: asyncpg 连接池
        """
        self._pool = pool

    def _parse_row(self, row: asyncpg.Record) -> dict[str, Any]:
        """Convert asyncpg.Record to dict, parsing JSON fields.

        Args:
            row: Database record.

        Returns:
            Dictionary with parsed JSON fields.
        """
        result = dict(row)
        # Map alert_id field (database column is already alert_id)
        result["alert_id"] = str(result["alert_id"]) if result["alert_id"] else None
        # Parse JSON fields
        if "metadata" in result and isinstance(result["metadata"], str):
            result["metadata"] = json.loads(result["metadata"])
        return result

    async def find_by_id(self, signal_id: int) -> SignalRecord | None:
        """根据ID获取信号

        Args:
            signal_id: 信号数据库ID

        Returns:
            信号记录或 None
        """
        query = """
            SELECT
                id, alert_id, strategy_type, symbol, interval,
                trigger_type, signal_value, computed_at,
                source_subscription_key, metadata
            FROM strategy_signals
            WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, signal_id)
        if row:
            return SignalRecord(**self._parse_row(row))
        return None

    async def find_all(
        self,
        page: int = 1,
        page_size: int = 20,
        symbol: str | None = None,
        strategy_type: str | None = None,
        interval: str | None = None,
        signal_value: bool | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        order_by: str = "computed_at",
        order_dir: str = "desc",
    ) -> tuple[list[SignalRecord], int]:
        """查询信号列表

        Args:
            page: 页码
            page_size: 每页数量
            symbol: 交易对过滤
            strategy_type: 策略名称过滤
            interval: K线周期过滤
            signal_value: 信号值过滤
            start_time: 开始时间过滤
            end_time: 结束时间过滤
            order_by: 排序字段
            order_dir: 排序方向

        Returns:
            (信号列表, 总数)
        """
        # 构建动态查询条件
        conditions = []
        params = []
        param_idx = 1

        if symbol:
            conditions.append(f"symbol = ${param_idx}")
            params.append(symbol)
            param_idx += 1

        if strategy_type:
            conditions.append(f"strategy_type = ${param_idx}")
            params.append(strategy_type)
            param_idx += 1

        if interval:
            conditions.append(f"interval = ${param_idx}")
            params.append(interval)
            param_idx += 1

        if signal_value is not None:
            conditions.append(f"signal_value = ${param_idx}")
            params.append(signal_value)
            param_idx += 1

        if start_time:
            conditions.append(f"computed_at >= ${param_idx}")
            params.append(start_time)
            param_idx += 1

        if end_time:
            conditions.append(f"computed_at <= ${param_idx}")
            params.append(end_time)
            param_idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # 验证排序字段
        allowed_order_by = ["computed_at", "created_at", "id"]
        if order_by not in allowed_order_by:
            order_by = "computed_at"

        order_dir = "DESC" if order_dir.lower() == "desc" else "ASC"

        # 查询总数
        count_query = f"SELECT COUNT(*) FROM strategy_signals {where_clause}"
        async with self._pool.acquire() as conn:
            total = await conn.fetchval(count_query, *params)

        # 查询列表
        offset = (page - 1) * page_size
        list_query = f"""
            SELECT
                id, alert_id, strategy_type, symbol, interval,
                trigger_type, signal_value, computed_at,
                source_subscription_key, metadata
            FROM strategy_signals
            {where_clause}
            ORDER BY {order_by} {order_dir}
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([page_size, offset])
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(list_query, *params)

        records = [SignalRecord(**self._parse_row(row)) for row in rows]
        return records, total

    async def find_recent(
        self,
        limit: int = 10,
        symbol: str | None = None,
    ) -> list[SignalRecord]:
        """获取最近的信号

        Args:
            limit: 返回数量限制
            symbol: 交易对过滤

        Returns:
            信号列表
        """
        conditions = []
        params = []
        param_idx = 1

        if symbol:
            conditions.append(f"symbol = ${param_idx}")
            params.append(symbol)
            param_idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT
                id, alert_id, strategy_type, symbol, interval,
                trigger_type, signal_value, computed_at,
                source_subscription_key, metadata
            FROM strategy_signals
            {where_clause}
            ORDER BY computed_at DESC
            LIMIT ${param_idx}
        """
        params.append(limit)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [SignalRecord(**self._parse_row(row)) for row in rows]

    async def find_by_alert_id(
        self,
        alert_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SignalRecord], int]:
        """根据告警ID获取信号

        Args:
            alert_id: 告警ID (alert_signals.id)
            page: 页码
            page_size: 每页数量

        Returns:
            (信号列表, 总数)
        """
        # 查询总数
        count_query = "SELECT COUNT(*) FROM strategy_signals WHERE alert_id = $1"
        async with self._pool.acquire() as conn:
            total = await conn.fetchval(count_query, alert_id)

        # 查询列表
        offset = (page - 1) * page_size
        query = """
            SELECT
                id, alert_id, strategy_type, symbol, interval,
                trigger_type, signal_value, computed_at,
                source_subscription_key, metadata
            FROM strategy_signals
            WHERE alert_id = $1
            ORDER BY computed_at DESC
            LIMIT $2 OFFSET $3
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, alert_id, page_size, offset)

        records = [SignalRecord(**self._parse_row(row)) for row in rows]
        return records, total

    async def find_by_strategy_type(
        self,
        strategy_type: str,
        limit: int = 10,
    ) -> list[SignalRecord]:
        """根据策略名称获取信号

        Args:
            strategy_type: 策略名称
            limit: 返回数量限制

        Returns:
            信号列表
        """
        query = """
            SELECT
                id, alert_id, strategy_type, symbol, interval,
                trigger_type, signal_value, computed_at,
                source_subscription_key, metadata
            FROM strategy_signals
            WHERE strategy_type = $1
            ORDER BY computed_at DESC
            LIMIT $2
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, strategy_type, limit)

        return [SignalRecord(**self._parse_row(row)) for row in rows]
