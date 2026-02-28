"""Database connection management for signal service."""

import logging

import asyncpg
from asyncpg import Connection, Pool, create_pool
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    """Database configuration."""

    host: str = "localhost"
    port: int = 5432
    user: str = "dbuser"
    password: str = "pass"
    database: str = "trading_db"
    min_size: int = 2
    max_size: int = 10


class Database:
    """Database connection pool manager."""

    def __init__(self, config: DatabaseConfig | None = None) -> None:
        """Initialize database with configuration.

        Args:
            config: Database configuration. If None, uses environment variables.
        """
        self._config = config or DatabaseConfig()
        self._pool: Pool | None = None

    async def connect(self) -> None:
        """Create connection pool."""
        self._pool = await create_pool(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password,
            database=self._config.database,
            min_size=self._config.min_size,
            max_size=self._config.max_size,
        )
        logger.info(
            "Database connection pool created: host=%s port=%d database=%s",
            self._config.host,
            self._config.port,
            self._config.database,
        )

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")

    async def create_dedicated_connection(self) -> Connection:
        """Create a dedicated connection for listening to notifications.

        This is needed because connections from the pool may be reused,
        which would cause the LISTEN state to be lost.

        Returns:
            A dedicated database connection.
        """
        conn = await asyncpg.connect(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password,
            database=self._config.database,
        )
        logger.debug("Created dedicated connection for notifications")
        return conn

    async def close_dedicated_connection(self, conn: Connection) -> None:
        """Close a dedicated connection.

        Args:
            conn: The connection to close.
        """
        await conn.close()
        logger.debug("Closed dedicated connection")

    @property
    def pool(self) -> Pool:
        """Get connection pool.

        Returns:
            Asyncpg connection pool.

        Raises:
            RuntimeError: If not connected.
        """
        if self._pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._pool

    async def execute(self, query: str, *args: object) -> str:
        """Execute a query and return status message.

        Args:
            query: SQL query string.
            *args: Query parameters.

        Returns:
            Status message from execute.
        """
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetchrow(self, query: str, *args: object) -> object | None:
        """Fetch one row from query result.

        Args:
            query: SQL query string.
            *args: Query parameters.

        Returns:
            Row data or None if not found.
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch(self, query: str, *args: object) -> list[object]:
        """Fetch all rows from query result.

        Args:
            query: SQL query string.
            *args: Query parameters.

        Returns:
            List of rows.
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchval(self, query: str, *args: object) -> object | None:
        """Fetch a single value from query result.

        Useful for queries like SELECT COUNT(*) or RETURNING id.

        Args:
            query: SQL query string.
            *args: Query parameters.

        Returns:
            The fetched value or None.
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
