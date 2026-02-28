"""
任务仓储 - 基于新 tasks 表设计

使用 asyncpg 原生 SQL。
遵循 QUANT_TRADING_SYSTEM_ARCHITECTURE.md 设计：
- INSERT tasks → pg_notify('task.new')
- UPDATE tasks.status=completed → pg_notify('task.completed')

tasks 表字段：
- type: 任务类型（get_klines, get_server_time, get_quotes）
- payload: 任务参数
- result: 任务结果
- status: 任务状态（pending, processing, completed）

注意：所有方法统一使用 interval 参数，与数据库字段和内部逻辑保持一致。
"""

import json
import asyncpg
from datetime import datetime, timezone
from typing import Optional, Any


class TasksRepository:
    """任务仓储 - 基于 tasks 表

    职责：
    - 创建任务 (INSERT)
    - 查询任务 (SELECT)
    - 更新任务状态和结果 (UPDATE)
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_task(
        self,
        task_type: str,
        payload: dict[str, Any],
    ) -> int:
        """创建任务并返回任务ID

        Args:
            task_type: 任务类型 (get_klines, get_server_time, get_quotes)
            payload: 任务参数

        Returns:
            任务ID

        Raises:
            Exception: 创建失败
        """
        query = """
            INSERT INTO tasks (type, payload)
            VALUES ($1, $2)
            RETURNING id
        """
        import json
        payload_json = json.dumps(payload)
        async with self._pool.acquire() as conn:
            task_id = await conn.fetchval(query, task_type, payload_json)
        return task_id

    async def get_task(self, task_id: int) -> Optional[dict[str, Any]]:
        """根据ID获取任务

        Args:
            task_id: 任务ID

        Returns:
            任务字典或 None
        """
        query = """
            SELECT id, type, payload, result, status, created_at, updated_at
            FROM tasks
            WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, task_id)
        if row:
            return dict(row)
        return None

    async def update_task_result(
        self,
        task_id: int,
        result: dict[str, Any],
        status: str = "completed",
    ) -> bool:
        """更新任务结果和状态

        Args:
            task_id: 任务ID
            result: 任务结果
            status: 任务状态 (默认 completed)

        Returns:
            是否更新成功
        """
        query = """
            UPDATE tasks
            SET result = $1, status = $2, updated_at = NOW()
            WHERE id = $3
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, result, status, task_id)
        return result != "UPDATE 0"

    async def get_task_result(self, task_id: int) -> Optional[dict[str, Any]]:
        """获取任务结果

        Args:
            task_id: 任务ID

        Returns:
            任务结果或 None
        """
        query = """
            SELECT result, status
            FROM tasks
            WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, task_id)
        if row and row["result"]:
            # JSONB 字段返回 dict 类型，无需再转换
            return row["result"]
        return None

    async def get_pending_count(self) -> int:
        """获取待处理任务数量

        Returns:
            待处理任务数
        """
        query = """
            SELECT COUNT(*)
            FROM tasks
            WHERE status = 'pending'
        """
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query)

    async def get_stats(self) -> dict[str, int]:
        """获取任务统计

        Returns:
            任务统计字典
        """
        query = """
            SELECT status, COUNT(*) as count
            FROM tasks
            GROUP BY status
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)

        stats: dict[str, int] = {"pending": 0, "processing": 0, "completed": 0}
        for row in rows:
            stats[row["status"]] = row["count"]
        return stats

    async def cleanup_old_tasks(self, days: int = 7) -> int:
        """清理旧任务

        Args:
            days: 保留天数

        Returns:
            清理的任务数
        """
        query = """
            DELETE FROM tasks
            WHERE created_at < NOW() - INTERVAL '%s days'
            RETURNING id
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query % days)
            return len(rows)

    async def check_kline_endpoints_exist(
        self,
        symbol: str,
        interval: str,  # 统一使用 interval
        from_time: int,
        to_time: int,
    ) -> dict[str, Any]:
        """检查K线端点是否存在

        检查指定时间点的K线数据是否存在于klines_history表中。
        用于判断是同步返回数据还是创建异步任务。

        Args:
            symbol: 交易对符号 (如 "BINANCE:BTCUSDT")
            interval: K线周期 (如 "1m", "1h", "1d")
            from_time: 起始时间 (毫秒)
            to_time: 结束时间 (毫秒)

        Returns:
            {
                "from_exists": bool,
                "to_exists": bool,
                "from_bar": dict | None,  # 起始K线数据
                "to_bar": dict | None,    # 结束K线数据
            }
        """
        # interval 已经是标准格式，直接使用

        # 转换时间戳为TIMESTAMPTZ
        from_timestamp = datetime.fromtimestamp(from_time / 1000, tz=timezone.utc)
        to_timestamp = datetime.fromtimestamp(to_time / 1000, tz=timezone.utc)

        query = """
            SELECT
                open_time,
                close_time,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                number_of_trades
            FROM klines_history
            WHERE
                symbol = $1
                AND interval = $2
                AND open_time = $3
        """

        result: dict[str, Any] = {
            "from_exists": False,
            "to_exists": False,
            "from_bar": None,
            "to_bar": None,
        }

        async with self._pool.acquire() as conn:
            # 查询起始K线
            row = await conn.fetchrow(query, symbol, interval, from_timestamp)
            if row:
                result["from_exists"] = True
                result["from_bar"] = {
                    "time": int(row["open_time"].timestamp() * 1000),
                    "open": float(row["open_price"]),
                    "high": float(row["high_price"]),
                    "low": float(row["low_price"]),
                    "close": float(row["close_price"]),
                    "volume": float(row["volume"]),
                }

            # 查询结束K线
            row = await conn.fetchrow(query, symbol, interval, to_timestamp)
            if row:
                result["to_exists"] = True
                result["to_bar"] = {
                    "time": int(row["open_time"].timestamp() * 1000),
                    "open": float(row["open_price"]),
                    "high": float(row["high_price"]),
                    "low": float(row["low_price"]),
                    "close": float(row["close_price"]),
                    "volume": float(row["volume"]),
                }

        return result

    async def query_klines_range(
        self,
        symbol: str,
        interval: str,  # 统一使用 interval
        from_time: int,
        to_time: int,
    ) -> list[dict[str, Any]]:
        """查询指定时间范围内的K线数据

        用于同步返回K线数据场景。

        Args:
            symbol: 交易对符号 (如 "BINANCE:BTCUSDT")
            interval: K线周期 (如 "1m", "1h", "1d")
            from_time: 起始时间 (毫秒)
            to_time: 结束时间 (毫秒)

        Returns:
            K线数据列表
        """
        # interval 已经是标准格式，直接使用

        # 转换时间戳
        from_timestamp = datetime.fromtimestamp(from_time / 1000, tz=timezone.utc)
        to_timestamp = datetime.fromtimestamp(to_time / 1000, tz=timezone.utc)

        query = """
            SELECT
                open_time,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                number_of_trades
            FROM klines_history
            WHERE
                symbol = $1
                AND interval = $2
                AND open_time >= $3
                AND open_time <= $4
            ORDER BY open_time ASC
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, symbol, interval, from_timestamp, to_timestamp)

        klines = []
        for row in rows:
            klines.append({
                "time": int(row["open_time"].timestamp() * 1000),
                "open": float(row["open_price"]),
                "high": float(row["high_price"]),
                "low": float(row["low_price"]),
                "close": float(row["close_price"]),
                "volume": float(row["volume"]),
                "symbol": symbol,
                "interval": interval,  # 统一使用 interval
            })

        return klines

    async def get_account_info(self, account_type: str) -> dict[str, Any] | None:
        """查询账户信息

        Args:
            account_type: 账户类型 (SPOT / FUTURES)

        Returns:
            账户信息字典或 None（如果不存在）
        """
        query = """
            SELECT data, update_time, updated_at
            FROM account_info
            WHERE account_type = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, account_type)
        if row:
            # asyncpg 返回 JSONB 时是字符串，需要显式转换为字典
            data = row["data"]
            if isinstance(data, str):
                data = json.loads(data)
            return {
                "data": data,
                "update_time": row["update_time"],
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
        return None
