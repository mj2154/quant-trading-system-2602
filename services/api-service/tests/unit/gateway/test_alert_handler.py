"""Tests for AlertHandler in API service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestAlertHandler:
    """Tests for AlertHandler WebSocket operations."""

    @pytest.fixture
    def mock_alert_repo(self):
        """Create mock alert repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_signals_repo(self):
        """Create mock signals repository."""
        return AsyncMock()

    @pytest.fixture
    def handler(self, mock_alert_repo, mock_signals_repo):
        """Create handler with mock repositories."""
        from src.gateway.alert_handler import AlertHandler

        return AlertHandler(mock_alert_repo, mock_signals_repo)

    # ==================== CREATE ALERT TESTS ====================

    @pytest.mark.asyncio
    async def test_handle_create_alert_signal_success(self, handler, mock_alert_repo):
        """Test successful alert signal creation."""
        alert_id = str(uuid4())
        request_data = {
            "id": alert_id,
            "name": "Test MACD Alert",
            "description": "Test description",
            "strategy_type": "macd_resonance_v5",
            "symbol": "BINANCE:BTCUSDT",
            "interval": "60",
            "trigger_type": "each_kline_close",
            "params": {"fast1": 12, "slow1": 26, "signal1": 9},
            "is_enabled": True,
        }

        mock_alert_repo.create = AsyncMock(return_value=alert_id)

        result = await handler.handle_create_alert_signal(
            data=request_data,
            request_id="test_req_001",
        )

        assert result["action"] == "success"
        assert result["data"]["type"] == "create_alert_signal"
        assert result["data"]["id"] == alert_id
        assert "message" in result["data"]

    @pytest.mark.asyncio
    async def test_handle_create_alert_with_threshold(self, handler, mock_alert_repo):
        """Test creating alert with threshold parameter."""
        alert_id = str(uuid4())
        request_data = {
            "id": alert_id,
            "name": "Test Alert with Threshold",
            "strategy_type": "alpha_01",
            "symbol": "BINANCE:ETHUSDT",
            "interval": "15",
            "trigger_type": "each_kline_close",
            "params": {},
            "threshold": 0.5,
            "is_enabled": True,
        }

        mock_alert_repo.create = AsyncMock(return_value=alert_id)

        result = await handler.handle_create_alert_signal(
            data=request_data,
            request_id="test_req_002",
        )

        # Verify threshold is merged into params
        call_args = mock_alert_repo.create.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_handle_create_alert_validation_error(self, handler, mock_alert_repo):
        """Test creating alert with invalid data."""
        request_data = {
            # Missing required fields: id, name, strategy_type, symbol, interval
            "params": {},
        }

        result = await handler.handle_create_alert_signal(
            data=request_data,
            request_id="test_req_003",
        )

        assert result["action"] == "error"
        assert "errorCode" in result["data"]

    # ==================== LIST ALERTS TESTS ====================

    @pytest.mark.asyncio
    async def test_handle_list_alert_signals_success(self, handler, mock_alert_repo):
        """Test listing alert signals."""
        mock_alerts = [
            {
                "id": "0189a1b2-c3d4-5e6f-7890-abcd12345678",
                "name": "Alert 1",
                "strategy_type": "macd_resonance",
                "symbol": "BTCUSDT",
                "interval": "60",
                "is_enabled": True,
            },
            {
                "id": "0189a1b2-c3d4-5e6f-7890-abcd12345679",
                "name": "Alert 2",
                "strategy_type": "rsi_oversold",
                "symbol": "ETHUSDT",
                "interval": "15",
                "is_enabled": False,
            },
        ]
        mock_alert_repo.find_all = AsyncMock(return_value=(mock_alerts, 2))

        result = await handler.handle_list_alert_signals(
            data={"limit": 100, "offset": 0},
            request_id="test_req_004",
        )

        assert result["action"] == "success"
        assert result["data"]["type"] == "list_alert_signals"
        assert result["data"]["total"] == 2
        assert len(result["data"]["items"]) == 2

    @pytest.mark.asyncio
    async def test_handle_list_alert_signals_with_filters(self, handler, mock_alert_repo):
        """Test listing alerts with filters."""
        mock_alert_repo.find_all = AsyncMock(return_value=([], 0))

        result = await handler.handle_list_alert_signals(
            data={
                "limit": 50,
                "offset": 0,
                "is_enabled": True,
                "symbol": "BINANCE:BTCUSDT",
                "strategy_type": "macd_resonance_v5",
            },
            request_id="test_req_005",
        )

        # Verify filters were passed to repository
        mock_alert_repo.find_all.assert_called_once()
        call_kwargs = mock_alert_repo.find_all.call_args.kwargs
        assert call_kwargs["limit"] == 50
        assert call_kwargs["is_enabled"] is True

    @pytest.mark.asyncio
    async def test_handle_list_alert_signals_empty(self, handler, mock_alert_repo):
        """Test listing alerts when none exist."""
        mock_alert_repo.find_all = AsyncMock(return_value=([], 0))

        result = await handler.handle_list_alert_signals(
            data={},
            request_id="test_req_006",
        )

        assert result["action"] == "success"
        assert result["data"]["total"] == 0
        assert result["data"]["items"] == []

    @pytest.mark.asyncio
    async def test_handle_list_alert_signals_string_boolean(self, handler, mock_alert_repo):
        """Test listing alerts with string boolean filter."""
        mock_alert_repo.find_all = AsyncMock(return_value=([], 0))

        result = await handler.handle_list_alert_signals(
            data={"is_enabled": "true"},
            request_id="test_req_007",
        )

        # Verify string boolean is converted
        call_kwargs = mock_alert_repo.find_all.call_args.kwargs
        assert call_kwargs["is_enabled"] is True

    # ==================== UPDATE ALERT TESTS ====================

    @pytest.mark.asyncio
    async def test_handle_update_alert_signal_success(self, handler, mock_alert_repo):
        """Test successful alert update."""
        alert_id = str(uuid4())
        request_data = {
            "id": alert_id,
            "name": "Updated Alert Name",
            "description": "Updated description",
        }

        mock_alert_repo.update = AsyncMock(return_value=True)

        result = await handler.handle_update_alert_signal(
            data=request_data,
            request_id="test_req_008",
        )

        assert result["action"] == "success"
        assert result["data"]["type"] == "update_alert_signal"
        assert result["data"]["id"] == alert_id

    @pytest.mark.asyncio
    async def test_handle_update_alert_missing_id(self, handler, mock_alert_repo):
        """Test updating alert without ID."""
        request_data = {
            "name": "Updated Name",
        }

        result = await handler.handle_update_alert_signal(
            data=request_data,
            request_id="test_req_009",
        )

        assert result["action"] == "error"
        assert result["data"]["errorCode"] == "INVALID_PARAMETERS"

    @pytest.mark.asyncio
    async def test_handle_update_alert_invalid_id_format(self, handler, mock_alert_repo):
        """Test updating alert with invalid UUID format."""
        request_data = {
            "id": "invalid-uuid",
            "name": "Updated Name",
        }

        result = await handler.handle_update_alert_signal(
            data=request_data,
            request_id="test_req_010",
        )

        assert result["action"] == "error"
        assert result["data"]["errorCode"] == "INVALID_PARAMETERS"

    @pytest.mark.asyncio
    async def test_handle_update_alert_not_found(self, handler, mock_alert_repo):
        """Test updating non-existent alert."""
        alert_id = str(uuid4())
        request_data = {
            "id": alert_id,
            "name": "Updated Name",
        }

        mock_alert_repo.update = AsyncMock(return_value=False)

        result = await handler.handle_update_alert_signal(
            data=request_data,
            request_id="test_req_011",
        )

        assert result["action"] == "error"
        assert result["data"]["errorCode"] == "ALERT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_handle_update_alert_with_threshold(self, handler, mock_alert_repo):
        """Test updating alert with threshold parameter."""
        alert_id = str(uuid4())
        request_data = {
            "id": alert_id,
            "params": {},
            "threshold": 0.75,
        }

        mock_alert_repo.update = AsyncMock(return_value=True)

        result = await handler.handle_update_alert_signal(
            data=request_data,
            request_id="test_req_012",
        )

        # Verify threshold is merged into params in the update call

    # ==================== DELETE ALERT TESTS ====================

    @pytest.mark.asyncio
    async def test_handle_delete_alert_signal_success(self, handler, mock_alert_repo):
        """Test successful alert deletion."""
        alert_id = str(uuid4())
        request_data = {"id": alert_id}

        mock_alert_repo.delete = AsyncMock(return_value=True)

        result = await handler.handle_delete_alert_signal(
            data=request_data,
            request_id="test_req_013",
        )

        assert result["action"] == "success"
        assert result["data"]["type"] == "delete_alert_signal"
        assert result["data"]["id"] == alert_id

    @pytest.mark.asyncio
    async def test_handle_delete_alert_missing_id(self, handler, mock_alert_repo):
        """Test deleting alert without ID."""
        request_data = {}

        result = await handler.handle_delete_alert_signal(
            data=request_data,
            request_id="test_req_014",
        )

        assert result["action"] == "error"
        assert result["data"]["errorCode"] == "INVALID_PARAMETERS"

    @pytest.mark.asyncio
    async def test_handle_delete_alert_invalid_id_format(self, handler, mock_alert_repo):
        """Test deleting alert with invalid UUID format."""
        request_data = {"id": "not-a-uuid"}

        result = await handler.handle_delete_alert_signal(
            data=request_data,
            request_id="test_req_015",
        )

        assert result["action"] == "error"

    @pytest.mark.asyncio
    async def test_handle_delete_alert_not_found(self, handler, mock_alert_repo):
        """Test deleting non-existent alert."""
        alert_id = str(uuid4())
        request_data = {"id": alert_id}

        mock_alert_repo.delete = AsyncMock(return_value=False)

        result = await handler.handle_delete_alert_signal(
            data=request_data,
            request_id="test_req_016",
        )

        assert result["action"] == "error"
        assert result["data"]["errorCode"] == "ALERT_NOT_FOUND"

    # ==================== ENABLE/DISABLE ALERT TESTS ====================

    @pytest.mark.asyncio
    async def test_handle_enable_alert_signal_success(self, handler, mock_alert_repo):
        """Test successful alert enable."""
        alert_id = str(uuid4())
        request_data = {"id": alert_id, "is_enabled": True}

        mock_alert_repo.enable = AsyncMock(return_value=True)

        result = await handler.handle_enable_alert_signal(
            data=request_data,
            request_id="test_req_017",
        )

        assert result["action"] == "success"
        assert result["data"]["type"] == "enable_alert_signal"
        assert result["data"]["is_enabled"] is True

    @pytest.mark.asyncio
    async def test_handle_disable_alert_signal_success(self, handler, mock_alert_repo):
        """Test successful alert disable."""
        alert_id = str(uuid4())
        request_data = {"id": alert_id, "is_enabled": False}

        mock_alert_repo.disable = AsyncMock(return_value=True)

        result = await handler.handle_enable_alert_signal(
            data=request_data,
            request_id="test_req_018",
        )

        assert result["action"] == "success"
        assert result["data"]["is_enabled"] is False

    @pytest.mark.asyncio
    async def test_handle_enable_alert_missing_id(self, handler, mock_alert_repo):
        """Test enabling alert without ID."""
        request_data = {"is_enabled": True}

        result = await handler.handle_enable_alert_signal(
            data=request_data,
            request_id="test_req_019",
        )

        assert result["action"] == "error"
        assert result["data"]["errorCode"] == "INVALID_PARAMETERS"

    @pytest.mark.asyncio
    async def test_handle_enable_alert_missing_is_enabled(self, handler, mock_alert_repo):
        """Test enabling alert without is_enabled field."""
        alert_id = str(uuid4())
        request_data = {"id": alert_id}

        result = await handler.handle_enable_alert_signal(
            data=request_data,
            request_id="test_req_020",
        )

        assert result["action"] == "error"
        assert result["data"]["errorCode"] == "INVALID_PARAMETERS"

    @pytest.mark.asyncio
    async def test_handle_enable_alert_not_found(self, handler, mock_alert_repo):
        """Test enabling non-existent alert."""
        alert_id = str(uuid4())
        request_data = {"id": alert_id, "is_enabled": True}

        mock_alert_repo.enable = AsyncMock(return_value=False)

        result = await handler.handle_enable_alert_signal(
            data=request_data,
            request_id="test_req_021",
        )

        assert result["action"] == "error"
        assert result["data"]["errorCode"] == "ALERT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_handle_enable_alert_string_boolean(self, handler, mock_alert_repo):
        """Test enabling alert with string boolean."""
        alert_id = str(uuid4())
        request_data = {"id": alert_id, "is_enabled": "true"}

        mock_alert_repo.enable = AsyncMock(return_value=True)

        result = await handler.handle_enable_alert_signal(
            data=request_data,
            request_id="test_req_022",
        )

        assert result["action"] == "success"

    # ==================== LIST SIGNALS TESTS ====================

    @pytest.mark.asyncio
    async def test_handle_list_signals_success(self, handler, mock_signals_repo):
        """Test listing signals."""
        from datetime import datetime

        mock_signals = [
            {
                "id": 1,
                "alert_id": "0189a1b2-c3d4-5e6f-7890-abcd12345678",
                "strategy_type": "macd_resonance",
                "symbol": "BTCUSDT",
                "interval": "60",
                "trigger_type": "each_kline_close",
                "signal_value": True,
                "signal_reason": "MACD golden cross",
                "computed_at": datetime.now(),
            },
        ]

        mock_signal_obj = MagicMock()
        mock_signal_obj.id = 1
        mock_signal_obj.alert_id = "0189a1b2-c3d4-5e6f-7890-abcd12345678"
        mock_signal_obj.strategy_type = "macd_resonance"
        mock_signal_obj.symbol = "BTCUSDT"
        mock_signal_obj.interval = "60"
        mock_signal_obj.trigger_type = "each_kline_close"
        mock_signal_obj.signal_value = True
        mock_signal_obj.signal_reason = "MACD golden cross"
        mock_signal_obj.computed_at = datetime.now()
        mock_signal_obj.source_subscription_key = None
        mock_signal_obj.metadata = {}

        mock_signals_repo.find_all = AsyncMock(return_value=([mock_signal_obj], 1))

        result = await handler.handle_list_signals(
            data={"limit": 100, "offset": 0},
            request_id="test_req_023",
        )

        assert result["action"] == "success"
        assert result["data"]["type"] == "list_signals"

    @pytest.mark.asyncio
    async def test_handle_list_signals_no_repository(self, handler):
        """Test listing signals when signals repository is not initialized."""
        # Create handler without signals repo
        from src.gateway.alert_handler import AlertHandler

        handler_no_signals = AlertHandler(AsyncMock(), None)

        result = await handler_no_signals.handle_list_signals(
            data={},
            request_id="test_req_024",
        )

        assert result["action"] == "error"
        assert result["data"]["errorCode"] == "REPOSITORY_NOT_INITIALIZED"

    @pytest.mark.asyncio
    async def test_handle_list_signals_with_filters(self, handler, mock_signals_repo):
        """Test listing signals with filters."""
        mock_signals_repo.find_all = AsyncMock(return_value=([], 0))

        result = await handler.handle_list_signals(
            data={
                "symbol": "BTCUSDT",
                "strategy_type": "macd_resonance",
                "signal_value": True,
                "start_time": 1704067200000,
                "end_time": 1704153600000,
            },
            request_id="test_req_025",
        )

        # Verify filters were passed
        mock_signals_repo.find_all.assert_called_once()
