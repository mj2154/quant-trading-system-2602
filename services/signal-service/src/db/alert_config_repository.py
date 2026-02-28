"""Repository for alert_configs table operations (for signal-service)."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from .database import Database

logger = logging.getLogger(__name__)


def _parse_params(params: Any) -> dict[str, Any]:
    """Parse params field from database, handling string or dict formats.

    The params field in alert_configs may be stored as JSON string or JSONB.
    This function ensures we always return a dict regardless of the storage format.
    """
    if params is None:
        return {}
    if isinstance(params, dict):
        return params
    if isinstance(params, str):
        try:
            return json.loads(params)
        except json.JSONDecodeError:
            logger.warning("Failed to parse params JSON: %s", params)
            return {}
    return {}


@dataclass(frozen=True)
class AlertConfigRecord:
    """Alert configuration record from alert_configs table."""

    id: UUID
    name: str
    description: str | None
    strategy_type: str
    symbol: str
    interval: str
    trigger_type: str
    params: dict[str, Any]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime
    created_by: str | None


class AlertConfigRepository:
    """Repository for alert_configs table operations (used by signal-service)."""

    def __init__(self, db: Database) -> None:
        """Initialize repository.

        Args:
            db: Database instance.
        """
        self._db = db

    async def find_by_id(self, alert_id: str) -> AlertConfigRecord | None:
        """Find an alert configuration by ID.

        Args:
            alert_id: Alert ID (string, since DB field is VARCHAR).

        Returns:
            Alert config record or None.
        """
        row = await self._db.fetchrow(
            """
            SELECT id, name, description, strategy_type, symbol, interval,
                   trigger_type, params, is_enabled,
                   created_at, updated_at, created_by
            FROM alert_configs
            WHERE id = $1
            """,
            alert_id,
        )
        if row:
            row_dict = dict(row)
            row_dict['params'] = _parse_params(row_dict.get('params'))
            return AlertConfigRecord(**row_dict)
        return None

    async def find_all(
        self, limit: int = 100, offset: int = 0
    ) -> list[AlertConfigRecord]:
        """Find all alert configurations.

        Args:
            limit: Maximum records to return.
            offset: Offset for pagination.

        Returns:
            List of alert config records.
        """
        rows = await self._db.fetch(
            """
            SELECT id, name, description, strategy_type, symbol, interval,
                   trigger_type, params, is_enabled,
                   created_at, updated_at, created_by
            FROM alert_configs
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        records = []
        for row in rows:
            row_dict = dict(row)
            row_dict['params'] = _parse_params(row_dict.get('params'))
            records.append(AlertConfigRecord(**row_dict))
        return records

    async def find_by_symbol(
        self, symbol: str, limit: int = 100
    ) -> list[AlertConfigRecord]:
        """Find alert configurations by symbol.

        Args:
            symbol: Trading pair symbol.
            limit: Maximum records to return.

        Returns:
            List of alert config records.
        """
        rows = await self._db.fetch(
            """
            SELECT id, name, description, strategy_type, symbol, interval,
                   trigger_type, params, is_enabled,
                   created_at, updated_at, created_by
            FROM alert_configs
            WHERE symbol = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            symbol,
            limit,
        )
        records = []
        for row in rows:
            row_dict = dict(row)
            row_dict['params'] = _parse_params(row_dict.get('params'))
            records.append(AlertConfigRecord(**row_dict))
        return records

    async def find_enabled(self) -> list[AlertConfigRecord]:
        """Find all enabled alert configurations.

        Returns:
            List of enabled alert config records.
        """
        rows = await self._db.fetch(
            """
            SELECT id, name, description, strategy_type, symbol, interval,
                   trigger_type, params, is_enabled,
                   created_at, updated_at, created_by
            FROM alert_configs
            WHERE is_enabled = TRUE
            ORDER BY created_at DESC
            """,
        )
        records = []
        for row in rows:
            row_dict = dict(row)
            row_dict['params'] = _parse_params(row_dict.get('params'))
            records.append(AlertConfigRecord(**row_dict))
        return records

    async def find_enabled_by_symbol_interval(
        self, symbol: str, interval: str
    ) -> list[AlertConfigRecord]:
        """Find enabled alert configurations by symbol and interval.

        Args:
            symbol: Trading pair symbol.
            interval: K-line interval.

        Returns:
            List of enabled alert config records.
        """
        rows = await self._db.fetch(
            """
            SELECT id, name, description, strategy_type, symbol, interval,
                   trigger_type, params, is_enabled,
                   created_at, updated_at, created_by
            FROM alert_configs
            WHERE is_enabled = TRUE
              AND symbol = $1
              AND "interval" = $2
            ORDER BY created_at DESC
            """,
            symbol,
            interval,
        )
        records = []
        for row in rows:
            row_dict = dict(row)
            row_dict['params'] = _parse_params(row_dict.get('params'))
            records.append(AlertConfigRecord(**row_dict))
        return records
