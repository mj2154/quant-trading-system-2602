"""
ExchangeInfoRepository 单元测试

测试 resolve_symbol 和相关方法。
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

# 添加src目录到路径
_api_service_root = Path(__file__).resolve().parent.parent.parent.parent
_src_path = _api_service_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import pytest
import asyncio

from db.exchange_info_repository import ExchangeInfoRepository


class AsyncContextManagerMock:
    """异步上下文管理器模拟"""

    def __init__(self, result):
        self.result = result

    async def __aenter__(self):
        return self.result

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


@pytest.fixture
def mock_conn():
    """创建模拟连接"""
    conn = MagicMock()
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock()
    return conn


@pytest.fixture
def mock_pool(mock_conn):
    """创建模拟连接池"""
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=AsyncContextManagerMock(mock_conn))
    return pool


@pytest.fixture
def repository(mock_pool):
    """创建仓储实例"""
    return ExchangeInfoRepository(mock_pool)


class TestExchangeInfoRepositoryResolveSymbol:
    """resolve_symbol 方法测试"""

    @pytest.mark.asyncio
    async def test_resolve_symbol_returns_symbol_info(self, repository, mock_conn):
        """测试 resolve_symbol 返回完整的 SymbolInfo"""
        # 模拟数据库返回
        mock_conn.fetchrow = AsyncMock(return_value={
            "symbol": "BTCUSDT",
            "base_asset": "BTC",
            "quote_asset": "USDT",
            "status": "TRADING",
            "quote_precision": 8,
            "base_asset_precision": 8,
            "filters": {"price_tick": 0.01},
            "order_types": ["LIMIT", "MARKET"],
            "permissions": ["SPOT"],
            "iceberg_allowed": True,
            "oco_allowed": True,
            "last_updated": 1699999999000,
        })

        result = await repository.resolve_symbol("BINANCE:BTCUSDT")

        assert result is not None
        assert result["symbol"] == "BINANCE:BTCUSDT"
        assert result["ticker"] == "BTCUSDT"
        assert result["name"] == "BTCUSDT"
        assert result["description"] == "BTC/USDT"
        assert result["exchange"] == "BINANCE"
        assert result["type"] == "crypto"

    @pytest.mark.asyncio
    async def test_resolve_symbol_with_lowercase_prefix(self, repository, mock_conn):
        """测试解析带小写前缀的交易对"""
        mock_conn.fetchrow = AsyncMock(return_value={
            "symbol": "ETHUSDT",
            "base_asset": "ETH",
            "quote_asset": "USDT",
            "status": "TRADING",
            "quote_precision": 8,
            "base_asset_precision": 8,
            "filters": {},
            "order_types": [],
            "permissions": ["SPOT"],
            "iceberg_allowed": False,
            "oco_allowed": True,
            "last_updated": 1699999999000,
        })

        result = await repository.resolve_symbol("binance:ETHUSDT")

        assert result is not None
        assert result["symbol"] == "BINANCE:ETHUSDT"
        assert result["ticker"] == "ETHUSDT"

    @pytest.mark.asyncio
    async def test_resolve_symbol_returns_none_for_nonexistent(self, repository, mock_conn):
        """测试解析不存在的交易对返回 None"""
        mock_conn.fetchrow = AsyncMock(return_value=None)

        result = await repository.resolve_symbol("BINANCE:NONEXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_symbol_with_market_type(self, repository, mock_conn):
        """测试解析指定市场类型的交易对"""
        mock_conn.fetchrow = AsyncMock(return_value={
            "symbol": "BTCUSDT",
            "base_asset": "BTC",
            "quote_asset": "USDT",
            "status": "TRADING",
            "quote_precision": 8,
            "base_asset_precision": 8,
            "filters": {},
            "order_types": [],
            "permissions": ["FUTURES"],
            "iceberg_allowed": False,
            "oco_allowed": False,
            "last_updated": 1699999999000,
        })

        result = await repository.resolve_symbol(
            "BINANCE:BTCUSDT",
            market_type="FUTURES"
        )

        assert result is not None
        assert result["type"] == "crypto"

    @pytest.mark.asyncio
    async def test_resolve_symbol_strips_prefix_from_ticker(self, repository, mock_conn):
        """测试从 ticker 中剥离前缀"""
        mock_conn.fetchrow = AsyncMock(return_value={
            "symbol": "SOLUSDT",
            "base_asset": "SOL",
            "quote_asset": "USDT",
            "status": "TRADING",
            "quote_precision": 8,
            "base_asset_precision": 8,
            "filters": {},
            "order_types": [],
            "permissions": ["SPOT"],
            "iceberg_allowed": False,
            "oco_allowed": False,
            "last_updated": 1699999999000,
        })

        result = await repository.resolve_symbol("BINANCE:SOLUSDT")

        assert result is not None
        assert result["ticker"] == "SOLUSDT"  # 不包含 BINANCE: 前缀

    @pytest.mark.asyncio
    async def test_resolve_symbol_handles_exception(self, repository, mock_conn):
        """测试数据库异常时返回 None"""
        mock_conn.fetchrow = AsyncMock(side_effect=Exception("Database error"))

        result = await repository.resolve_symbol("BINANCE:BTCUSDT")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_symbol_without_exchange_prefix(self, repository, mock_conn):
        """测试不带交易所前缀的交易对解析"""
        mock_conn.fetchrow = AsyncMock(return_value={
            "symbol": "BTCUSDT",
            "base_asset": "BTC",
            "quote_asset": "USDT",
            "status": "TRADING",
            "quote_precision": 8,
            "base_asset_precision": 8,
            "filters": {},
            "order_types": [],
            "permissions": ["SPOT"],
            "iceberg_allowed": False,
            "oco_allowed": False,
            "last_updated": 1699999999000,
        })

        # 不带前缀的交易对
        result = await repository.resolve_symbol("BTCUSDT")

        assert result is not None
        assert result["symbol"] == "BINANCE:BTCUSDT"
        assert result["ticker"] == "BTCUSDT"


class TestExchangeInfoRepositorySearchSymbols:
    """search_symbols 方法测试（参考现有实现）"""

    @pytest.mark.asyncio
    async def test_search_symbols_returns_list(self, repository, mock_conn):
        """测试搜索返回列表"""
        mock_conn.fetch = AsyncMock(return_value=[
            {
                "symbol": "BTCUSDT",
                "base_asset": "BTC",
                "quote_asset": "USDT",
                "status": "TRADING",
                "quote_precision": 8,
                "base_asset_precision": 8,
                "filters": {},
                "order_types": [],
                "permissions": ["SPOT"],
                "iceberg_allowed": False,
                "oco_allowed": False,
                "last_updated": 1699999999000,
            }
        ])

        results = await repository.search_symbols(query="BTC")

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["symbol"] == "BINANCE:BTCUSDT"
        assert results[0]["ticker"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_search_symbols_empty_query(self, repository, mock_conn):
        """测试空查询返回所有交易对"""
        mock_conn.fetch = AsyncMock(return_value=[])

        results = await repository.search_symbols(query="")

        assert isinstance(results, list)
        assert len(results) == 0
