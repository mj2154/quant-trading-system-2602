"""Tests for repository modules."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock


class TestRealtimeDataRepository:
    """Tests for RealtimeDataRepository."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        mock = MagicMock()
        mock.pool = MagicMock()
        return mock

    @pytest.fixture
    def repository(self, mock_db):
        """Create repository with mock database."""
        from src.db.realtime_data_repository import RealtimeDataRepository

        return RealtimeDataRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_by_subscription_key_not_found(self, repository, mock_db):
        """Test getting non-existent subscription key."""
        mock_db.fetchrow = AsyncMock(return_value=None)

        result = await repository.get_by_subscription_key("NONEXISTENT")
        assert result is None


class TestStrategyConfigRepository:
    """Tests for StrategyConfigRepository in signal-service."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        mock = MagicMock()
        mock.pool = MagicMock()
        return mock

    @pytest.fixture
    def repository(self, mock_db):
        """Create repository with mock database."""
        from src.db.strategy_config_repository import StrategyConfigRepository

        return StrategyConfigRepository(mock_db)

    @pytest.mark.asyncio
    async def test_create(self, repository, mock_db):
        """Test creating a strategy configuration."""
        config_id = uuid4()
        mock_db.execute = AsyncMock(return_value="INSERT 0 1")
        mock_db.fetchrow = AsyncMock(
            return_value={"id": config_id}
        )

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
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(self, repository, mock_db):
        """Test updating a strategy configuration."""
        config_id = uuid4()
        mock_db.execute = AsyncMock(return_value="UPDATE 1")

        result = await repository.update(
            config_id=config_id,
            name="updated_name",
            is_enabled=False,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_no_fields(self, repository, mock_db):
        """Test updating with no fields returns False."""
        config_id = uuid4()

        result = await repository.update(config_id=config_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_description(self, repository, mock_db):
        """Test updating description."""
        config_id = uuid4()
        mock_db.execute = AsyncMock(return_value="UPDATE 1")

        result = await repository.update(
            config_id=config_id,
            description="Updated description",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_trigger_type(self, repository, mock_db):
        """Test updating trigger type."""
        config_id = uuid4()
        mock_db.execute = AsyncMock(return_value="UPDATE 1")

        result = await repository.update(
            config_id=config_id,
            trigger_type="once_only",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_macd_params(self, repository, mock_db):
        """Test updating MACD parameters."""
        config_id = uuid4()
        mock_db.execute = AsyncMock(return_value="UPDATE 1")

        result = await repository.update(
            config_id=config_id,
            macd_params={"fast": 10, "slow": 20, "signal": 5},
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_threshold(self, repository, mock_db):
        """Test updating threshold."""
        config_id = uuid4()
        mock_db.execute = AsyncMock(return_value="UPDATE 1")

        result = await repository.update(
            config_id=config_id,
            threshold=0.8,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, repository, mock_db):
        """Test updating multiple fields at once."""
        config_id = uuid4()
        mock_db.execute = AsyncMock(return_value="UPDATE 1")

        result = await repository.update(
            config_id=config_id,
            name="new_name",
            description="new description",
            is_enabled=False,
            threshold=0.9,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete(self, repository, mock_db):
        """Test deleting a strategy configuration."""
        config_id = uuid4()
        mock_db.execute = AsyncMock(return_value="DELETE 1")

        result = await repository.delete(config_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_db):
        """Test deleting non-existent config returns False."""
        config_id = uuid4()
        mock_db.execute = AsyncMock(return_value="DELETE 0")

        result = await repository.delete(config_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_find_by_id(self, repository, mock_db):
        """Test finding a configuration by ID."""
        config_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_db.fetchrow = AsyncMock(
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

        result = await repository.find_by_id(config_id)

        assert result is not None
        assert result.id == config_id
        assert result.name == "test_strategy"

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repository, mock_db):
        """Test finding non-existent configuration returns None."""
        config_id = uuid4()
        mock_db.fetchrow = AsyncMock(return_value=None)

        result = await repository.find_by_id(config_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_find_all(self, repository, mock_db):
        """Test finding all configurations."""
        config_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_db.fetch = AsyncMock(
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

        result = await repository.find_all(limit=10, offset=0)

        assert len(result) == 1
        assert result[0].name == "test_strategy"

    @pytest.mark.asyncio
    async def test_find_all_empty(self, repository, mock_db):
        """Test finding all configurations returns empty list."""
        mock_db.fetch = AsyncMock(return_value=[])

        result = await repository.find_all()

        assert result == []

    @pytest.mark.asyncio
    async def test_find_by_symbol(self, repository, mock_db):
        """Test finding configurations by symbol."""
        config_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_db.fetch = AsyncMock(
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

        result = await repository.find_by_symbol("BTCUSDT")

        assert len(result) == 1
        assert result[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_find_enabled(self, repository, mock_db):
        """Test finding enabled configurations."""
        config_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_db.fetch = AsyncMock(
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

        result = await repository.find_enabled()

        assert len(result) == 1
        assert result[0].is_enabled is True


class TestStrategySignalsRepository:
    """Tests for StrategySignalsRepository in signal-service."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        mock = MagicMock()
        mock.pool = MagicMock()
        return mock

    @pytest.fixture
    def repository(self, mock_db):
        """Create repository with mock database."""
        from src.db.strategy_signals_repository import StrategySignalsRepository

        return StrategySignalsRepository(mock_db)

    @pytest.mark.asyncio
    async def test_insert_signal(self, repository, mock_db):
        """Test inserting a signal."""
        signal_id = uuid4()
        mock_db.execute = AsyncMock(return_value="INSERT 0 1")
        mock_db.fetchrow = AsyncMock(
            return_value={"id": 1}
        )

        result = await repository.insert_signal(
            signal_id=signal_id,
            strategy_name="random",
            symbol="BTCUSDT",
            interval="1m",
            signal_value=True,
            signal_reason="Test reason",
            config_id=None,
            trigger_type="each_kline_close",
            source_subscription_key="BTCUSDT@KLINE_1m",
            metadata={"test": True},
        )

        assert result == 1

    @pytest.mark.asyncio
    async def test_insert_signal_no_metadata(self, repository, mock_db):
        """Test inserting a signal with no metadata."""
        signal_id = uuid4()
        mock_db.execute = AsyncMock(return_value="INSERT 0 1")
        mock_db.fetchrow = AsyncMock(
            return_value={"id": 2}
        )

        result = await repository.insert_signal(
            signal_id=signal_id,
            strategy_name="macd_resonance",
            symbol="ETHUSDT",
            interval="5m",
            signal_value=False,
            signal_reason="MACD cross",
        )

        assert result == 2

    @pytest.mark.asyncio
    async def test_get_latest_by_symbol(self, repository, mock_db):
        """Test getting latest signals by symbol."""
        signal_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_db.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "signal_id": signal_id,
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

        result = await repository.get_latest_by_symbol("BTCUSDT")

        assert len(result) == 1
        assert result[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_get_latest_by_symbol_empty(self, repository, mock_db):
        """Test getting latest signals returns empty list."""
        mock_db.fetch = AsyncMock(return_value=[])

        result = await repository.get_latest_by_symbol("NONEXISTENT")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_latest_by_strategy(self, repository, mock_db):
        """Test getting latest signals by strategy name."""
        signal_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_db.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "signal_id": signal_id,
                    "config_id": None,
                    "strategy_name": "macd_resonance",
                    "symbol": "BTCUSDT",
                    "interval": "1m",
                    "trigger_type": "each_kline_close",
                    "signal_value": True,
                    "signal_reason": "MACD cross",
                    "computed_at": now,
                    "source_subscription_key": "test",
                    "metadata": {},
                }
            ]
        )

        result = await repository.get_latest_by_strategy("macd_resonance")

        assert len(result) == 1
        assert result[0].strategy_name == "macd_resonance"

    @pytest.mark.asyncio
    async def test_get_latest_by_config_id(self, repository, mock_db):
        """Test getting latest signals by config ID."""
        config_id = uuid4()
        signal_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_db.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "signal_id": signal_id,
                    "config_id": config_id,
                    "strategy_name": "macd_resonance",
                    "symbol": "BTCUSDT",
                    "interval": "1m",
                    "trigger_type": "each_kline_close",
                    "signal_value": True,
                    "signal_reason": "MACD cross",
                    "computed_at": now,
                    "source_subscription_key": "test",
                    "metadata": {},
                }
            ]
        )

        result = await repository.get_latest_by_config_id(config_id)

        assert len(result) == 1
        assert result[0].config_id == config_id

    @pytest.mark.asyncio
    async def test_get_latest_by_symbol_and_interval(self, repository, mock_db):
        """Test getting latest signals by symbol and interval."""
        signal_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_db.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "signal_id": signal_id,
                    "config_id": None,
                    "strategy_name": "random",
                    "symbol": "BTCUSDT",
                    "interval": "5m",
                    "trigger_type": "each_kline_close",
                    "signal_value": True,
                    "signal_reason": "Test",
                    "computed_at": now,
                    "source_subscription_key": "test",
                    "metadata": {},
                }
            ]
        )

        result = await repository.get_latest_by_symbol_and_interval("BTCUSDT", "5m")

        assert len(result) == 1
        assert result[0].interval == "5m"

    @pytest.mark.asyncio
    async def test_get_by_time_range(self, repository, mock_db):
        """Test getting signals by time range."""
        signal_id = uuid4()
        now = datetime.now(timezone.utc)
        start_time = now.replace(hour=0, minute=0, second=0)
        end_time = now.replace(hour=23, minute=59, second=59)
        mock_db.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "signal_id": signal_id,
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

        result = await repository.get_by_time_range(start_time, end_time)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_time_range_with_filters(self, repository, mock_db):
        """Test getting signals by time range with symbol and strategy filters."""
        signal_id = uuid4()
        now = datetime.now(timezone.utc)
        start_time = now.replace(hour=0, minute=0, second=0)
        end_time = now.replace(hour=23, minute=59, second=59)
        mock_db.fetch = AsyncMock(return_value=[])

        result = await repository.get_by_time_range(
            start_time, end_time, symbol="BTCUSDT", strategy_name="random"
        )

        assert result == []
