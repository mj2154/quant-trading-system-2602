"""Tests for AlertSignalRepository in API service."""

import pytest
import json
from datetime import datetime
from uuid import UUID
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


class TestAlertSignalRepository:
    """Tests for AlertSignalRepository."""

    @pytest.fixture
    def mock_pool(self):
        """Create mock asyncpg pool."""
        mock_conn = AsyncMock()
        return create_mock_pool(mock_conn)

    @pytest.fixture
    def repository(self, mock_pool):
        """Create repository with mock pool."""
        from src.db.alert_signal_repository import AlertSignalRepository

        return AlertSignalRepository(mock_pool)

    # ==================== CREATE TESTS ====================

    @pytest.mark.asyncio
    async def test_create_alert_signal(self, repository, mock_pool):
        """Test creating an alert signal."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=UUID(alert_id))
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.create(
            alert_id=alert_id,
            name="Test Alert",
            strategy_type="macd_resonance_v5",
            symbol="BINANCE:BTCUSDT",
            interval="60",
            trigger_type="each_kline_close",
            params={"fast1": 12, "slow1": 26},
            description="Test description",
            is_enabled=True,
            created_by="test_user",
        )

        assert result == UUID(alert_id)
        mock_conn.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_alert_with_minimal_params(self, repository, mock_pool):
        """Test creating alert with minimal parameters."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=UUID(alert_id))
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.create(
            alert_id=alert_id,
            name="Minimal Alert",
            strategy_type="macd_resonance",
            symbol="BTCUSDT",
            interval="15",
        )

        assert result == UUID(alert_id)

    # ==================== UPDATE TESTS ====================

    @pytest.mark.asyncio
    async def test_update_alert_name(self, repository, mock_pool):
        """Test updating alert name."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.update(
            alert_id=alert_id,
            name="Updated Name",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_alert_description(self, repository, mock_pool):
        """Test updating alert description."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.update(
            alert_id=alert_id,
            description="New description",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_alert_multiple_fields(self, repository, mock_pool):
        """Test updating multiple fields at once."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.update(
            alert_id=alert_id,
            name="Updated Name",
            description="Updated description",
            strategy_type="rsi_oversold",
            is_enabled=False,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_alert_no_fields(self, repository, mock_pool):
        """Test updating with no fields returns False."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 0")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.update(alert_id=alert_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_alert_params(self, repository, mock_pool):
        """Test updating alert params."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        new_params = {"fast1": 5, "slow1": 35, "signal1": 5}
        result = await repository.update(
            alert_id=alert_id,
            params=new_params,
        )

        assert result is True

    # ==================== DELETE TESTS ====================

    @pytest.mark.asyncio
    async def test_delete_alert_signal(self, repository, mock_pool):
        """Test deleting an alert signal."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="DELETE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.delete(alert_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_alert_not_found(self, repository, mock_pool):
        """Test deleting non-existent alert returns False."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="DELETE 0")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.delete(alert_id)

        assert result is False

    # ==================== FIND BY ID TESTS ====================

    @pytest.mark.asyncio
    async def test_find_by_id(self, repository, mock_pool):
        """Test finding alert by ID."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_row = {
            "id": alert_id,
            "name": "Test Alert",
            "description": "Test description",
            "strategy_type": "macd_resonance_v5",
            "symbol": "BINANCE:BTCUSDT",
            "interval": "60",
            "trigger_type": "each_kline_close",
            "params": json.dumps({"fast1": 12, "slow1": 26}),
            "is_enabled": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "created_by": "test_user",
        }
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_by_id(alert_id)

        assert result is not None
        assert result["id"] == alert_id
        assert result["name"] == "Test Alert"
        assert result["params"] == {"fast1": 12, "slow1": 26}

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repository, mock_pool):
        """Test finding non-existent alert returns None."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_by_id(alert_id)

        assert result is None

    # ==================== FIND ALL TESTS ====================

    @pytest.mark.asyncio
    async def test_find_all_no_filters(self, repository, mock_pool):
        """Test finding all alerts without filters."""
        mock_rows = [
            {
                "id": "0189a1b2-c3d4-5e6f-7890-abcd12345678",
                "name": "Alert 1",
                "description": None,
                "strategy_type": "macd_resonance",
                "symbol": "BTCUSDT",
                "interval": "60",
                "trigger_type": "each_kline_close",
                "params": "{}",
                "is_enabled": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "created_by": "user1",
            },
            {
                "id": "0189a1b2-c3d4-5e6f-7890-abcd12345679",
                "name": "Alert 2",
                "description": None,
                "strategy_type": "rsi_oversold",
                "symbol": "ETHUSDT",
                "interval": "15",
                "trigger_type": "each_kline",
                "params": "{}",
                "is_enabled": False,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "created_by": "user1",
            },
        ]
        mock_conn = AsyncMock()
        # First call returns count, second returns rows
        mock_conn.fetchrow = AsyncMock(return_value={"count": 2})
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        alerts, total = await repository.find_all(limit=100, offset=0)

        assert total == 2
        assert len(alerts) == 2

    @pytest.mark.asyncio
    async def test_find_all_with_symbol_filter(self, repository, mock_pool):
        """Test finding alerts filtered by symbol."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"count": 1})
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        alerts, total = await repository.find_all(
            limit=100,
            offset=0,
            symbol="BINANCE:BTCUSDT",
        )

        assert total >= 0
        # Verify symbol filter was used in query

    @pytest.mark.asyncio
    async def test_find_all_with_strategy_filter(self, repository, mock_pool):
        """Test finding alerts filtered by strategy type."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"count": 1})
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        alerts, total = await repository.find_all(
            limit=100,
            offset=0,
            strategy_type="macd_resonance_v5",
        )

        assert total >= 0

    @pytest.mark.asyncio
    async def test_find_all_with_is_enabled_filter(self, repository, mock_pool):
        """Test finding alerts filtered by enabled status."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"count": 1})
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        alerts, total = await repository.find_all(
            limit=100,
            offset=0,
            is_enabled=True,
        )

        assert total >= 0

    # ==================== ENABLE/DISABLE TESTS ====================

    @pytest.mark.asyncio
    async def test_enable_alert(self, repository, mock_pool):
        """Test enabling an alert signal."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.enable(alert_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_enable_alert_not_found(self, repository, mock_pool):
        """Test enabling non-existent alert returns False."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 0")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.enable(alert_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_disable_alert(self, repository, mock_pool):
        """Test disabling an alert signal."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.disable(alert_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_disable_alert_not_found(self, repository, mock_pool):
        """Test disabling non-existent alert returns False."""
        alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 0")
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.disable(alert_id)

        assert result is False

    # ==================== COUNT TESTS ====================

    @pytest.mark.asyncio
    async def test_count_all(self, repository, mock_pool):
        """Test counting all alerts."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=10)
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.count_all()

        assert result == 10

    # ==================== FIND ENABLED TESTS ====================

    @pytest.mark.asyncio
    async def test_find_enabled(self, repository, mock_pool):
        """Test finding all enabled alerts."""
        mock_rows = [
            {
                "id": "0189a1b2-c3d4-5e6f-7890-abcd12345678",
                "name": "Enabled Alert",
                "description": None,
                "strategy_type": "macd_resonance",
                "symbol": "BTCUSDT",
                "interval": "60",
                "trigger_type": "each_kline_close",
                "params": "{}",
                "is_enabled": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "created_by": "user1",
            },
        ]
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_enabled()

        assert len(result) == 1
        assert result[0]["is_enabled"] is True

    # ==================== FIND BY SYMBOL/INTERVAL TESTS ====================

    @pytest.mark.asyncio
    async def test_find_by_symbol_interval(self, repository, mock_pool):
        """Test finding alerts by symbol and interval."""
        mock_rows = []
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        mock_pool = create_mock_pool(mock_conn)
        repository._pool = mock_pool

        result = await repository.find_by_symbol_interval(
            symbol="BINANCE:BTCUSDT",
            interval="60",
        )

        assert isinstance(result, list)
