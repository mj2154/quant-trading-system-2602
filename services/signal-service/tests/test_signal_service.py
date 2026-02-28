"""Tests for SignalService."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.signal_service import SignalService, LoadedAlertConfig
from src.services.trigger_engine import TriggerState


class TestSignalService:
    """Tests for SignalService class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database with async pool methods."""
        mock = MagicMock()
        mock.pool = MagicMock()
        mock.pool.acquire = AsyncMock()
        mock.pool.release = AsyncMock()
        return mock

    @pytest.fixture
    def signal_service(self, mock_db):
        """Create signal service with mock dependencies."""
        return SignalService(db=mock_db)

    def test_service_initialization(self, signal_service):
        """Test service initialization."""
        assert signal_service._running is False
        assert signal_service._listener is None
        assert signal_service._strategies == {}
        assert signal_service._loaded_alerts == {}

    @pytest.mark.asyncio
    async def test_start_service(self, signal_service, mock_db):
        """Test starting the service."""
        # Mock pool.acquire() to return an async mock connection
        mock_conn = AsyncMock()
        mock_db.pool.acquire = AsyncMock(return_value=mock_conn)

        # Mock the repository methods
        with patch.object(
            signal_service._realtime_repo,
            "get_by_subscription_key",
            new_callable=AsyncMock,
            return_value=None,
        ), patch.object(
            signal_service._realtime_repo,
            "insert_subscription",
            new_callable=AsyncMock,
            return_value=1,
        ), patch.object(
            signal_service._alert_repo,
            "find_enabled",
            new_callable=AsyncMock,
            return_value=[],  # No alerts in test
        ):
            await signal_service.start()
            assert signal_service._running is True

        await signal_service.stop()

    @pytest.mark.asyncio
    async def test_stop_service(self, signal_service):
        """Test stopping the service."""
        await signal_service.stop()
        assert signal_service._running is False


class TestLoadedAlertConfig:
    """Tests for LoadedAlertConfig dataclass."""

    def test_config_creation(self):
        """Test LoadedAlertConfig creation."""
        alert_id = uuid4()
        config = LoadedAlertConfig(
            config_id=alert_id,
            name="test_alert",
            strategy_type="MACDResonanceStrategyV5",
            symbol_pattern="BINANCE:BTCUSDT",
            interval="60",
            trigger_type="each_kline_close",
            params={"fast_period": 12, "slow_period": 26},
            is_enabled=True,
            trigger_state=TriggerState(),
        )

        assert config.config_id == alert_id
        assert config.name == "test_alert"
        assert config.strategy_type == "MACDResonanceStrategyV5"
        assert config.symbol_pattern == "BINANCE:BTCUSDT"
        assert config.interval == "60"
        assert config.is_enabled is True

    def test_config_immutability(self):
        """Test LoadedAlertConfig is immutable (frozen=True)."""
        alert_id = uuid4()
        config = LoadedAlertConfig(
            config_id=alert_id,
            name="test_alert",
            strategy_type="MACDResonanceStrategyV5",
            symbol_pattern="BINANCE:BTCUSDT",
            interval="60",
            trigger_type="each_kline_close",
            params={},
            is_enabled=True,
            trigger_state=TriggerState(),
        )

        # Should raise FrozenInstanceError
        with pytest.raises(Exception):  # frozen.dataclasses.FrozenInstanceError
            config.name = "new_name"
