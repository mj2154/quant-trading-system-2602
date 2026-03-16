"""Strategy metadata repository for querying strategies from database."""

import json
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

    def _parse_params(self, params: Any) -> list[dict[str, Any]]:
        """Parse params field from database.

        AsyncPG returns jsonb columns as strings, need to parse them.

        Args:
            params: The params field from database (could be string or list).

        Returns:
            Parsed params as list.
        """
        if params is None:
            return []
        if isinstance(params, str):
            try:
                return json.loads(params)
            except json.JSONDecodeError:
                return []
        if isinstance(params, list):
            return params
        return []

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
            result = []
            for row in rows:
                row_dict = dict(row)
                row_dict["params"] = self._parse_params(row_dict.get("params"))
                result.append(row_dict)
            return result

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
            if not row:
                return None
            row_dict = dict(row)
            row_dict["params"] = self._parse_params(row_dict.get("params"))
            return row_dict
