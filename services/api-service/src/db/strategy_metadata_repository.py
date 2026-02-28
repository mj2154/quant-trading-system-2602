"""Strategy metadata repository for querying strategies from database."""
from typing import Any
from asyncpg import Pool


class StrategyMetadataRepository:
    """Repository for strategy metadata."""

    def __init__(self, pool: Pool) -> None:
        """Initialize repository.

        Args:
            pool: AsyncPG connection pool.
        """
        self._pool = pool

    async def find_all(self) -> list[dict[str, Any]]:
        """Get all strategy metadata from database.

        Returns:
            List of strategy metadata dictionaries.
        """
        query = """
            SELECT type, name, description, params, created_at, updated_at
            FROM alert_strategy_metadata
            ORDER BY type
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]

    async def find_by_type(self, strategy_type: str) -> dict[str, Any] | None:
        """Get strategy metadata by type.

        Args:
            strategy_type: Strategy type identifier.

        Returns:
            Strategy metadata dictionary or None if not found.
        """
        query = """
            SELECT type, name, description, params, created_at, updated_at
            FROM alert_strategy_metadata
            WHERE type = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, strategy_type)
            return dict(row) if row else None
