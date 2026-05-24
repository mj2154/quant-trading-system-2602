"""Tests for SignalService."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from datetime import UTC, datetime

from src.services.alert_signal import LoadedAlertConfig
from src.services.signal_service import SignalService
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
        mock.close_dedicated_connection = AsyncMock()
        return mock

    @pytest.fixture
    def signal_service(self, mock_db):
        """Create signal service with mock dependencies."""
        return SignalService(db=mock_db)

    def test_service_initialization(self, signal_service):
        """Test service initialization."""
        assert signal_service._running is False
        assert signal_service._listener is None
        assert signal_service._alerts == {}
        assert signal_service._alerts_by_key == {}

    @pytest.mark.asyncio
    async def test_start_service(self, signal_service, mock_db):
        """Test starting the service."""
        mock_conn = AsyncMock()
        mock_db.pool.acquire = AsyncMock(return_value=mock_conn)
        mock_db.create_dedicated_connection = AsyncMock(return_value=mock_conn)

        with patch.object(
            signal_service._alert_mgr,
            "load_alerts_from_db",
            new_callable=AsyncMock,
        ), patch.object(
            signal_service._alert_mgr,
            "cleanup_stale_subscriptions",
            new_callable=AsyncMock,
        ), patch.object(
            signal_service._alert_mgr,
            "ensure_subscriptions",
            new_callable=AsyncMock,
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
        now = datetime.now(UTC)
        config = LoadedAlertConfig(
            alert_id=alert_id,
            name="test_alert",
            strategy_type="MACDResonanceStrategyV5",
            symbol="BINANCE:BTCUSDT",
            interval="60",
            trigger_type="each_kline_close",
            params={"fast_period": 12, "slow_period": 26},
            is_enabled=True,
            strategy=MagicMock(),
            trigger_state=TriggerState(),
            created_at=now,
            updated_at=now,
            created_by="test_user",
        )

        assert config.alert_id == alert_id
        assert config.name == "test_alert"
        assert config.strategy_type == "MACDResonanceStrategyV5"
        assert config.symbol == "BINANCE:BTCUSDT"
        assert config.interval == "60"
        assert config.is_enabled is True

    def test_config_immutability(self):
        """Test LoadedAlertConfig allows mutation (plain dataclass, not frozen)."""
        alert_id = uuid4()
        now = datetime.now(UTC)
        config = LoadedAlertConfig(
            alert_id=alert_id,
            name="test_alert",
            strategy_type="MACDResonanceStrategyV5",
            symbol="BINANCE:BTCUSDT",
            interval="60",
            trigger_type="each_kline_close",
            params={},
            is_enabled=True,
            strategy=MagicMock(),
            trigger_state=TriggerState(),
            created_at=now,
            updated_at=now,
            created_by="test_user",
        )

        # Plain dataclass: mutation is allowed
        config.name = "new_name"
        assert config.name == "new_name"
