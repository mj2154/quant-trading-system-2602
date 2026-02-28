"""
数据库连接池配置

使用 asyncpg 原生异步驱动，直接执行 SQL，配合 TimescaleDB-Pg18。
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

# 从环境变量读取配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://dbuser:pass@timescale-db:5432/trading_db"
)

# 连接池
_pool: asyncpg.Pool | None = None
_lock = asyncio.Lock()


async def init_pool(min_size: int = 5, max_size: int = 20) -> asyncpg.Pool:
    """初始化连接池

    Args:
        min_size: 最小连接数
        max_size: 最大连接数
    """
    global _pool
    async with _lock:
        if _pool is None:
            _pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=min_size,
                max_size=max_size,
                command_timeout=30.0,
                statement_cache_size=100,
            )
    return _pool


async def get_pool() -> asyncpg.Pool:
    """获取连接池"""
    if _pool is None:
        raise RuntimeError("数据库连接池未初始化，请先调用 init_pool()")
    return _pool


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """获取数据库连接

    使用示例:
        async with get_connection() as conn:
            result = await conn.fetchval("SELECT 1")
    """
    pool = await get_pool()
    async with pool.acquire() as connection:
        yield connection


async def close_pool() -> None:
    """关闭连接池"""
    global _pool
    async with _lock:
        if _pool is not None:
            await _pool.close()
            _pool = None
