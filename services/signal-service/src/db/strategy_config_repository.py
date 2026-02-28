"""Repository for strategy_configurations table operations."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from .database import Database

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StrategyConfigRecord:
    """Strategy configuration record."""

    id: UUID
    name: str
    description: str | None
    trigger_type: str
    macd_params: dict[str, Any]
    threshold: float
    symbol: str
    interval: str
    is_enabled: bool
    created_at: datetime
    updated_at: datetime
    created_by: str | None


class StrategyConfigRepository:
    """Repository for strategy_configurations table operations."""

    def __init__(self, db: Database) -> None:
        """Initialize repository.

        Args:
            db: Database instance.
        """
        self._db = db

    async def create(
        self,
        name: str,
        symbol: str,
        interval: str,
        trigger_type: str = "each_kline_close",
        macd_params: dict[str, Any] | None = None,
        threshold: float = 0.0,
        description: str | None = None,
        created_by: str | None = None,
    ) -> UUID:
        """Create a new strategy configuration.

        Args:
            name: Strategy name.
            symbol: Trading pair symbol.
            interval: K-line interval.
            trigger_type: Trigger type (once_only, each_kline, each_kline_close, each_minute).
            macd_params: MACD parameters JSON.
            threshold: Resonance threshold.
            description: Strategy description.
            created_by: Creator identifier.

        Returns:
            Created config UUID.
        """
        await self._db.execute(
            """
            INSERT INTO strategy_configurations (
                name, symbol, interval, trigger_type,
                macd_params, threshold, description, created_by
            )
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8)
            RETURNING id
            """,
            name,
            symbol,
            interval,
            trigger_type,
            json.dumps(macd_params) if macd_params else "{}",
            threshold,
            description,
            created_by,
        )
        logger.info(
            "Strategy config created: name=%s symbol=%s interval=%s",
            name,
            symbol,
            interval,
        )
        # Get the created ID
        row = await self._db.fetchrow(
            "SELECT id FROM strategy_configurations WHERE name = $1 AND symbol = $2 AND interval = $3",
            name,
            symbol,
            interval,
        )
        return row["id"] if row else UUID("00000000-0000-0000-0000-000000000000")

    async def update(
        self,
        config_id: UUID,
        name: str | None = None,
        description: str | None = None,
        trigger_type: str | None = None,
        macd_params: dict[str, Any] | None = None,
        threshold: float | None = None,
        is_enabled: bool | None = None,
    ) -> bool:
        """Update a strategy configuration.

        Args:
            config_id: Configuration UUID.
            name: New name.
            description: New description.
            trigger_type: New trigger type.
            macd_params: New MACD parameters.
            threshold: New threshold.
            is_enabled: New enabled status.

        Returns:
            Whether update was successful.
        """
        # Build dynamic update query
        updates: list[str] = []
        values: list[Any] = []
        param_idx = 1

        if name is not None:
            updates.append(f"name = ${param_idx}")
            values.append(name)
            param_idx += 1

        if description is not None:
            updates.append(f"description = ${param_idx}")
            values.append(description)
            param_idx += 1

        if trigger_type is not None:
            updates.append(f"trigger_type = ${param_idx}")
            values.append(trigger_type)
            param_idx += 1

        if macd_params is not None:
            updates.append(f"macd_params = ${param_idx}::jsonb")
            values.append(json.dumps(macd_params))
            param_idx += 1

        if threshold is not None:
            updates.append(f"threshold = ${param_idx}")
            values.append(threshold)
            param_idx += 1

        if is_enabled is not None:
            updates.append(f"is_enabled = ${param_idx}")
            values.append(is_enabled)
            param_idx += 1

        if not updates:
            return False

        updates.append("updated_at = NOW()")
        values.append(config_id)

        query = f"""
            UPDATE strategy_configurations
            SET {', '.join(updates)}
            WHERE id = ${param_idx}
        """
        result = await self._db.execute(query, *values)
        return result == "UPDATE 1"

    async def delete(self, config_id: UUID) -> bool:
        """Delete a strategy configuration.

        Args:
            config_id: Configuration UUID.

        Returns:
            Whether deletion was successful.
        """
        result = await self._db.execute(
            "DELETE FROM strategy_configurations WHERE id = $1",
            config_id,
        )
        return result == "DELETE 1"

    async def find_by_id(self, config_id: UUID) -> StrategyConfigRecord | None:
        """Find a configuration by ID.

        Args:
            config_id: Configuration UUID.

        Returns:
            Configuration record or None.
        """
        row = await self._db.fetchrow(
            """
            SELECT id, name, description, trigger_type, macd_params,
                   threshold, symbol, interval, is_enabled,
                   created_at, updated_at, created_by
            FROM strategy_configurations
            WHERE id = $1
            """,
            config_id,
        )
        if row:
            return StrategyConfigRecord(**row)
        return None

    async def find_all(self, limit: int = 100, offset: int = 0) -> list[StrategyConfigRecord]:
        """Find all configurations.

        Args:
            limit: Maximum records to return.
            offset: Offset for pagination.

        Returns:
            List of configuration records.
        """
        rows = await self._db.fetch(
            """
            SELECT id, name, description, trigger_type, macd_params,
                   threshold, symbol, interval, is_enabled,
                   created_at, updated_at, created_by
            FROM strategy_configurations
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        return [StrategyConfigRecord(**row) for row in rows]

    async def find_by_symbol(
        self,
        symbol: str,
        limit: int = 100,
    ) -> list[StrategyConfigRecord]:
        """Find configurations by symbol.

        Args:
            symbol: Trading pair symbol.
            limit: Maximum records to return.

        Returns:
            List of configuration records.
        """
        rows = await self._db.fetch(
            """
            SELECT id, name, description, trigger_type, macd_params,
                   threshold, symbol, interval, is_enabled,
                   created_at, updated_at, created_by
            FROM strategy_configurations
            WHERE symbol = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            symbol,
            limit,
        )
        return [StrategyConfigRecord(**row) for row in rows]

    async def find_enabled(self) -> list[StrategyConfigRecord]:
        """Find all enabled configurations.

        Returns:
            List of enabled configuration records.
        """
        rows = await self._db.fetch(
            """
            SELECT id, name, description, trigger_type, macd_params,
                   threshold, symbol, interval, is_enabled,
                   created_at, updated_at, created_by
            FROM strategy_configurations
            WHERE is_enabled = TRUE
            ORDER BY created_at DESC
            """,
        )
        return [StrategyConfigRecord(**row) for row in rows]
