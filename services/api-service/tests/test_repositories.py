"""Tests for repository modules in API service."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from contextlib import asynccontextmanager


def create_mock_pool(mock_conn):
    """Create a mock pool that returns a connection for async with."""

    @asynccontextmanager
    async def mock_acquire():
        yield mock_conn

    mock_pool = MagicMock()
    mock_pool.acquire = mock_acquire
    return mock_pool


class TestStrategyConfigRepositoryAPI:
    """Tests for StrategyConfigRepository in API service."""

    @pytest.fixture
    def mock_pool(self, request):
        """Create mock asyncpg pool."""
        mock_conn = AsyncMock()
        return create_mock_pool(mock_conn)

    @pytest.fixture
    def repository(self, mock_pool):
        """Create repository with mock pool."""
        from src.db.strategy_config_repository import StrategyConfigRepository

        return StrategyConfigRepository(mock_pool)

    @pytest.mark.asyncio
    async def test_create(self, repository, mock_pool):
        """Test creating a strategy configuration."""
        config_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=config_id)

        # Recreate pool with the mock connection
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.create(
            name="test_strategy",
            symbol="BTCUSDT",
            interval="1m",
            trigger_type="each_kline_close",
            macd_params={"fast": 12, "slow": 26, "signal": 9},
            threshold=0.5,
            description="Test strategy",
            created_by="test_user",
        )

        assert result == config_id

    @pytest.mark.asyncio
    async def test_create_with_defaults(self, repository, mock_pool):
        """Test creating with default values."""
        config_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=config_id)
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.create(
            name="test_strategy",
            symbol="BTCUSDT",
            interval="1m",
        )

        assert result == config_id

    @pytest.mark.asyncio
    async def test_update(self, repository, mock_pool):
        """Test updating a strategy configuration."""
        config_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.update(
            config_id=config_id,
            name="updated_name",
            is_enabled=False,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_no_fields(self, repository, mock_pool):
        """Test updating with no fields returns False."""
        config_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 0")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.update(config_id=config_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_description(self, repository, mock_pool):
        """Test updating description."""
        config_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.update(
            config_id=config_id,
            description="Updated description",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_trigger_type(self, repository, mock_pool):
        """Test updating trigger type."""
        config_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.update(
            config_id=config_id,
            trigger_type="once_only",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_macd_params(self, repository, mock_pool):
        """Test updating MACD parameters."""
        config_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.update(
            config_id=config_id,
            macd_params={"fast": 10, "slow": 20},
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_threshold(self, repository, mock_pool):
        """Test updating threshold."""
        config_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.update(
            config_id=config_id,
            threshold=0.8,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete(self, repository, mock_pool):
        """Test deleting a strategy configuration."""
        config_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="DELETE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.delete(config_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_pool):
        """Test deleting non-existent config returns False."""
        config_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="DELETE 0")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.delete(config_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_find_by_id(self, repository, mock_pool):
        """Test finding a configuration by ID."""
        config_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(
            return_value={
                "id": config_id,
                "name": "test_strategy",
                "description": "Test",
                "trigger_type": "each_kline_close",
                "macd_params": {"fast": 12},
                "threshold": 0.5,
                "symbol": "BTCUSDT",
                "interval": "1m",
                "is_enabled": True,
                "created_at": now,
                "updated_at": now,
                "created_by": "test_user",
            }
        )
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_by_id(config_id)

        assert result is not None
        assert result["id"] == config_id
        assert result["name"] == "test_strategy"

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repository, mock_pool):
        """Test finding non-existent configuration returns None."""
        config_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_by_id(config_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_find_all(self, repository, mock_pool):
        """Test finding all configurations."""
        config_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            return_value=[
                {
                    "id": config_id,
                    "name": "test_strategy",
                    "description": "Test",
                    "trigger_type": "each_kline_close",
                    "macd_params": {"fast": 12},
                    "threshold": 0.5,
                    "symbol": "BTCUSDT",
                    "interval": "1m",
                    "is_enabled": True,
                    "created_at": now,
                    "updated_at": now,
                    "created_by": "test_user",
                }
            ]
        )
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_all(limit=10, offset=0)

        assert len(result) == 1
        assert result[0]["name"] == "test_strategy"

    @pytest.mark.asyncio
    async def test_find_all_empty(self, repository, mock_pool):
        """Test finding all configurations returns empty list."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_all()

        assert result == []

    @pytest.mark.asyncio
    async def test_find_by_symbol(self, repository, mock_pool):
        """Test finding configurations by symbol."""
        config_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            return_value=[
                {
                    "id": config_id,
                    "name": "test_strategy",
                    "description": "Test",
                    "trigger_type": "each_kline_close",
                    "macd_params": {"fast": 12},
                    "threshold": 0.5,
                    "symbol": "BTCUSDT",
                    "interval": "1m",
                    "is_enabled": True,
                    "created_at": now,
                    "updated_at": now,
                    "created_by": "test_user",
                }
            ]
        )
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_by_symbol("BTCUSDT")

        assert len(result) == 1
        assert result[0]["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_find_enabled(self, repository, mock_pool):
        """Test finding enabled configurations."""
        config_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            return_value=[
                {
                    "id": config_id,
                    "name": "test_strategy",
                    "description": "Test",
                    "trigger_type": "each_kline_close",
                    "macd_params": {"fast": 12},
                    "threshold": 0.5,
                    "symbol": "BTCUSDT",
                    "interval": "1m",
                    "is_enabled": True,
                    "created_at": now,
                    "updated_at": now,
                    "created_by": "test_user",
                }
            ]
        )
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_enabled()

        assert len(result) == 1
        assert result[0]["is_enabled"] is True

    @pytest.mark.asyncio
    async def test_count_all(self, repository, mock_pool):
        """Test counting all configurations."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=5)
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.count_all()

        assert result == 5

    @pytest.mark.asyncio
    async def test_enable(self, repository, mock_pool):
        """Test enabling a strategy configuration."""
        config_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.enable(config_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_disable(self, repository, mock_pool):
        """Test disabling a strategy configuration."""
        config_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.disable(config_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_find_by_symbol_interval(self, repository, mock_pool):
        """Test finding configurations by symbol and interval."""
        config_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            return_value=[
                {
                    "id": config_id,
                    "name": "test_strategy",
                    "description": "Test",
                    "trigger_type": "each_kline_close",
                    "macd_params": {"fast": 12},
                    "threshold": 0.5,
                    "symbol": "BTCUSDT",
                    "interval": "1m",
                    "is_enabled": True,
                    "created_at": now,
                    "updated_at": now,
                    "created_by": "test_user",
                }
            ]
        )
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_by_symbol_interval("BTCUSDT", "1m")

        assert len(result) == 1
        assert result[0]["symbol"] == "BTCUSDT"
        assert result[0]["interval"] == "1m"


class TestStrategySignalsRepositoryAPI:
    """Tests for StrategySignalsRepository in API service."""

    @pytest.fixture
    def mock_pool(self):
        """Create mock asyncpg pool."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def repository(self, mock_pool):
        """Create repository with mock pool."""
        from src.db.strategy_signals_repository import StrategySignalsRepository

        return StrategySignalsRepository(mock_pool)

    @pytest.mark.asyncio
    async def test_find_by_id(self, repository, mock_pool):
        """Test finding a signal by ID."""
        signal_id = 1
        signal_uuid = uuid4()
        now = datetime.now(timezone.utc)
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(
            return_value={
                "id": signal_id,
                "signal_id": signal_uuid,
                "config_id": None,
                "strategy_name": "random",
                "symbol": "BTCUSDT",
                "interval": "1m",
                "trigger_type": "each_kline_close",
                "signal_value": True,
                "signal_reason": "Test",
                "computed_at": now,
                "source_subscription_key": "test",
                "metadata": {},
            }
        )
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_by_id(signal_id)

        assert result is not None
        assert result.id == signal_id

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repository, mock_pool):
        """Test finding non-existent signal returns None."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_signal_uuid(self, repository, mock_pool):
        """Test finding a signal by UUID."""
        signal_uuid = uuid4()
        now = datetime.now(timezone.utc)
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(
            return_value={
                "id": 1,
                "signal_id": signal_uuid,
                "config_id": None,
                "strategy_name": "random",
                "symbol": "BTCUSDT",
                "interval": "1m",
                "trigger_type": "each_kline_close",
                "signal_value": True,
                "signal_reason": "Test",
                "computed_at": now,
                "source_subscription_key": "test",
                "metadata": {},
            }
        )
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_by_signal_uuid(signal_uuid)

        assert result is not None
        assert result.signal_id == signal_uuid

    @pytest.mark.asyncio
    async def test_find_all(self, repository, mock_pool):
        """Test finding all signals with pagination."""
        signal_uuid = uuid4()
        now = datetime.now(timezone.utc)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "signal_id": signal_uuid,
                    "config_id": None,
                    "strategy_name": "random",
                    "symbol": "BTCUSDT",
                    "interval": "1m",
                    "trigger_type": "each_kline_close",
                    "signal_value": True,
                    "signal_reason": "Test",
                    "computed_at": now,
                    "source_subscription_key": "test",
                    "metadata": {},
                }
            ]
        )
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        records, total = await repository.find_all(page=1, page_size=10)

        assert len(records) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_find_all_with_filters(self, repository, mock_pool):
        """Test finding signals with filters."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=0)
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        records, total = await repository.find_all(
            page=1,
            page_size=10,
            symbol="BTCUSDT",
            strategy_name="macd_resonance",
            signal_value=True,
        )

        assert records == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_find_recent(self, repository, mock_pool):
        """Test finding recent signals."""
        signal_uuid = uuid4()
        now = datetime.now(timezone.utc)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "signal_id": signal_uuid,
                    "config_id": None,
                    "strategy_name": "random",
                    "symbol": "BTCUSDT",
                    "interval": "1m",
                    "trigger_type": "each_kline_close",
                    "signal_value": True,
                    "signal_reason": "Test",
                    "computed_at": now,
                    "source_subscription_key": "test",
                    "metadata": {},
                }
            ]
        )
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_recent(limit=10)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_find_recent_with_symbol(self, repository, mock_pool):
        """Test finding recent signals filtered by symbol."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_recent(limit=10, symbol="ETHUSDT")

        assert result == []

    @pytest.mark.asyncio
    async def test_find_by_config_id(self, repository, mock_pool):
        """Test finding signals by config ID."""
        config_id = uuid4()
        signal_uuid = uuid4()
        now = datetime.now(timezone.utc)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "signal_id": signal_uuid,
                    "config_id": config_id,
                    "strategy_name": "macd_resonance",
                    "symbol": "BTCUSDT",
                    "interval": "1m",
                    "trigger_type": "each_kline_close",
                    "signal_value": True,
                    "signal_reason": "Test",
                    "computed_at": now,
                    "source_subscription_key": "test",
                    "metadata": {},
                }
            ]
        )
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        records, total = await repository.find_by_config_id(config_id)

        assert len(records) == 1
        assert total == 1
        assert records[0].config_id == config_id

    @pytest.mark.asyncio
    async def test_find_by_strategy_name(self, repository, mock_pool):
        """Test finding signals by strategy name."""
        signal_uuid = uuid4()
        now = datetime.now(timezone.utc)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "signal_id": signal_uuid,
                    "config_id": None,
                    "strategy_name": "macd_resonance",
                    "symbol": "BTCUSDT",
                    "interval": "1m",
                    "trigger_type": "each_kline_close",
                    "signal_value": True,
                    "signal_reason": "Test",
                    "computed_at": now,
                    "source_subscription_key": "test",
                    "metadata": {},
                }
            ]
        )
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_by_strategy_name("macd_resonance")

        assert len(result) == 1
        assert result[0].strategy_name == "macd_resonance"

    @pytest.mark.asyncio
    async def test_find_all_invalid_order_by(self, repository, mock_pool):
        """Test find_all with invalid order_by uses default."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=0)
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        records, total = await repository.find_all(order_by="invalid_field")

        # Should use default "computed_at"
        assert records == []
        assert total == 0
