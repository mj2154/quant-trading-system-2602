"""Repository for strategy_signals table operations."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .database import Database

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StrategySignalRecord:
    """Strategy signal record."""

    id: int
    alert_id: str
    strategy_type: str
    symbol: str
    interval: str
    trigger_type: str | None
    signal_value: bool | None
    signal_reason: str | None
    computed_at: datetime
    source_subscription_key: str | None
    metadata: dict[str, Any]


class StrategySignalsRepository:
    """Repository for strategy_signals table operations."""

    def __init__(self, db: Database) -> None:
        """Initialize repository.

        Args:
            db: Database instance.
        """
        self._db = db

    async def insert_signal(
        self,
        alert_id: str,
        strategy_type: str,
        symbol: str,
        interval: str,
        signal_value: bool | None,
        signal_reason: str,
        trigger_type: str | None = None,
        source_subscription_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Insert a new strategy signal.

        Args:
            alert_id: Associated alert ID (required).
            strategy_type: Strategy type.
            symbol: Trading pair.
            interval: K-line interval.
            signal_value: Signal value (True=long, False=short, None=no signal).
            signal_reason: Reason for the signal.
            trigger_type: Trigger type (inherited from config).
            source_subscription_key: Source subscription key.
            metadata: Additional metadata.

        Returns:
            Inserted record ID.
        """
        result = await self._db.execute(
            """
            INSERT INTO strategy_signals (
                alert_id, strategy_type, symbol, interval,
                trigger_type, signal_value, signal_reason,
                source_subscription_key, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
            RETURNING id
            """,
            alert_id,
            strategy_type,
            symbol,
            interval,
            trigger_type,
            signal_value,
            signal_reason,
            source_subscription_key,
            json.dumps(metadata) if metadata else "{}",
        )
        logger.info(
            "Signal inserted: alert_id=%s strategy=%s symbol=%s interval=%s signal_value=%s",
            alert_id,
            strategy_type,
            symbol,
            interval,
            signal_value,
        )
        # Parse result to get ID
        if result and "INSERT" in result:
            row = await self._db.fetchrow(
                "SELECT id FROM strategy_signals WHERE alert_id = $1", alert_id
            )
            if row:
                return row["id"]
        return 0

    async def get_latest_by_symbol(
        self, symbol: str, limit: int = 10
    ) -> list[StrategySignalRecord]:
        """Get latest signals for a symbol.

        Args:
            symbol: Trading pair symbol.
            limit: Maximum number of records to return.

        Returns:
            List of latest signals.
        """
        rows = await self._db.fetch(
            """
            SELECT id, alert_id, strategy_type, symbol, interval,
                   trigger_type, signal_value, signal_reason,
                   computed_at, source_subscription_key, metadata
            FROM strategy_signals
            WHERE symbol = $1
            ORDER BY computed_at DESC
            LIMIT $2
            """,
            symbol,
            limit,
        )
        return [StrategySignalRecord(**row) for row in rows]

    async def get_latest_by_strategy(
        self, strategy_type: str, limit: int = 10
    ) -> list[StrategySignalRecord]:
        """Get latest signals for a strategy.

        Args:
            strategy_type: Strategy type.
            limit: Maximum number of records to return.

        Returns:
            List of latest signals.
        """
        rows = await self._db.fetch(
            """
            SELECT id, alert_id, strategy_type, symbol, interval,
                   trigger_type, signal_value, signal_reason,
                   computed_at, source_subscription_key, metadata
            FROM strategy_signals
            WHERE strategy_type = $1
            ORDER BY computed_at DESC
            LIMIT $2
            """,
            strategy_type,
            limit,
        )
        return [StrategySignalRecord(**row) for row in rows]

    async def get_latest_by_alert_id(
        self, alert_id: str, limit: int = 10
    ) -> list[StrategySignalRecord]:
        """Get latest signals for an alert ID.

        Args:
            alert_id: Alert ID (required).
            limit: Maximum number of records to return.

        Returns:
            List of latest signals.
        """
        rows = await self._db.fetch(
            """
            SELECT id, alert_id, strategy_type, symbol, interval,
                   trigger_type, signal_value, signal_reason,
                   computed_at, source_subscription_key, metadata
            FROM strategy_signals
            WHERE alert_id = $1
            ORDER BY computed_at DESC
            LIMIT $2
            """,
            alert_id,
            limit,
        )
        return [StrategySignalRecord(**row) for row in rows]

    async def get_latest_by_symbol_and_interval(
        self, symbol: str, interval: str, limit: int = 10
    ) -> list[StrategySignalRecord]:
        """Get latest signals for a symbol and interval.

        Args:
            symbol: Trading pair symbol.
            interval: K-line interval.
            limit: Maximum number of records to return.

        Returns:
            List of latest signals.
        """
        rows = await self._db.fetch(
            """
            SELECT id, alert_id, strategy_type, symbol, interval,
                   trigger_type, signal_value, signal_reason,
                   computed_at, source_subscription_key, metadata
            FROM strategy_signals
            WHERE symbol = $1 AND interval = $2
            ORDER BY computed_at DESC
            LIMIT $3
            """,
            symbol,
            interval,
            limit,
        )
        return [StrategySignalRecord(**row) for row in rows]

    async def get_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        symbol: str | None = None,
        strategy_type: str | None = None,
        limit: int = 100,
    ) -> list[StrategySignalRecord]:
        """Get signals within a time range.

        Args:
            start_time: Start of time range.
            end_time: End of time range.
            symbol: Optional symbol filter.
            strategy_type: Optional strategy type filter.
            limit: Maximum number of records to return.

        Returns:
            List of signals in time range.
        """
        query = """
            SELECT id, alert_id, strategy_type, symbol, interval,
                   trigger_type, signal_value, signal_reason,
                   computed_at, source_subscription_key, metadata
            FROM strategy_signals
            WHERE computed_at >= $1 AND computed_at <= $2
        """
        params: list[Any] = [start_time, end_time]
        param_idx = 3

        if symbol:
            query += f" AND symbol = ${param_idx}"
            params.append(symbol)
            param_idx += 1

        if strategy_type:
            query += f" AND strategy_type = ${param_idx}"
            params.append(strategy_type)
            param_idx += 1

        query += f" ORDER BY computed_at DESC LIMIT ${param_idx}"
        params.append(limit)

        rows = await self._db.fetch(query, *params)
        return [StrategySignalRecord(**row) for row in rows]
