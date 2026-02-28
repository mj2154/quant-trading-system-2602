"""Integration tests for K-line cache fill loop.

Tests the complete fill loop including:
1. Connection reuse across retries
2. Task notification handling
3. Success and failure scenarios
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from src.services.signal_service import SignalService, REQUIRED_KLINES


class TestKlineFillLoop:
    """Integration tests for kline fill loop."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        mock = MagicMock()

        # Mock dedicated connection
        mock_conn = AsyncMock()
        mock.create_dedicated_connection = AsyncMock(return_value=mock_conn)
        mock.close_dedicated_connection = AsyncMock()

        # Mock pool
        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock()
        mock.pool = mock_pool

        return mock

    @pytest.fixture
    def mock_realtime_repo(self):
        """Create mock realtime repository."""
        mock = AsyncMock()

        # Return insufficient klines for first call
        call_count = {"count": 0}

        async def mock_get_klines_history(symbol, interval, limit):
            call_count["count"] += 1
            if call_count["count"] == 1:
                # First call: return insufficient data (simulate missing data)
                return []
            else:
                # Subsequent calls: return valid data
                previous_period = int(datetime.now(timezone.utc).timestamp() * 1000)
                previous_period = (previous_period // (60 * 60 * 1000)) * (60 * 60 * 1000) - (60 * 60 * 1000)
                base_time = previous_period - (REQUIRED_KLINES - 1) * 60 * 60 * 1000
                return [
                    {"open_time": base_time + i * 60 * 60 * 1000}
                    for i in range(REQUIRED_KLINES)
                ]

        mock.get_klines_history = mock_get_klines_history
        return mock

    @pytest.fixture
    def mock_tasks_repo(self):
        """Create mock tasks repository."""
        mock = AsyncMock()
        mock.create_task = AsyncMock(return_value=1)  # Return task ID 1
        mock.get_task_status = AsyncMock(return_value="completed")
        return mock

    @pytest.fixture
    def signal_service(self, mock_db, mock_realtime_repo, mock_tasks_repo):
        """Create signal service with mocked dependencies."""
        service = SignalService.__new__(SignalService)
        service._db = mock_db
        service._realtime_repo = mock_realtime_repo
        service._tasks_repo = mock_tasks_repo
        service._kline_cache = {}
        return service

    @pytest.mark.asyncio
    async def test_fill_loop_creates_single_connection(self, signal_service, mock_db):
        """Test that fill loop creates only one connection and reuses it."""
        # Reset mock call count before the test
        mock_db.create_dedicated_connection.reset_mock()
        mock_db.close_dedicated_connection.reset_mock()

        async def mock_wait(conn, task_id, timeout):
            return "completed"

        with patch.object(signal_service, "_wait_for_task_completion_with_conn", mock_wait):
            await signal_service._fill_kline_data("BINANCE:BTCUSDT@KLINE_60", "BTCUSDT", "60")

        # Should create connection once per fill loop call
        assert mock_db.create_dedicated_connection.call_count == 1

        # Should close connection once
        assert mock_db.close_dedicated_connection.call_count == 1

        # Cache should be initialized
        assert "BINANCE:BTCUSDT@KLINE_60" in signal_service._kline_cache

    @pytest.mark.asyncio
    async def test_fill_loop_retries_on_failure(self, signal_service, mock_db):
        """Test that fill loop retries on task failure."""
        # Reset mock call count
        mock_db.create_dedicated_connection.reset_mock()
        mock_db.close_dedicated_connection.reset_mock()

        call_count = {"count": 0}

        async def mock_wait(conn, task_id, timeout):
            call_count["count"] += 1
            if call_count["count"] < 3:
                # First two attempts fail
                return "failed"
            else:
                # Third attempt succeeds
                return "completed"

        with patch.object(signal_service, "_wait_for_task_completion_with_conn", mock_wait):
            await signal_service._fill_kline_data("BINANCE:BTCUSDT@KLINE_60", "BTCUSDT", "60")

        # Should have retried multiple times
        assert call_count["count"] >= 3

        # Should still create only one connection (reused)
        assert mock_db.create_dedicated_connection.call_count == 1

    @pytest.mark.asyncio
    async def test_fill_loop_with_timeout(self, signal_service, mock_db):
        """Test that fill loop handles timeout correctly."""
        # Reset mock call count
        mock_db.create_dedicated_connection.reset_mock()
        mock_db.close_dedicated_connection.reset_mock()

        call_count = {"count": 0}

        async def mock_wait(conn, task_id, timeout):
            call_count["count"] += 1
            if call_count["count"] < 2:
                # First attempt times out
                return None
            else:
                # Second attempt succeeds
                return "completed"

        with patch.object(signal_service, "_wait_for_task_completion_with_conn", mock_wait):
            await signal_service._fill_kline_data("BINANCE:BTCUSDT@KLINE_60", "BTCUSDT", "60")

        # Should have retried
        assert call_count["count"] >= 2

    @pytest.mark.asyncio
    async def test_fill_loop_creates_task_with_correct_payload(self, signal_service, mock_tasks_repo, mock_db):
        """Test that fill loop creates task with correct payload."""
        # Reset mock call count
        mock_db.create_dedicated_connection.reset_mock()
        mock_db.close_dedicated_connection.reset_mock()

        async def mock_wait(conn, task_id, timeout):
            return "completed"

        with patch.object(signal_service, "_wait_for_task_completion_with_conn", mock_wait):
            await signal_service._fill_kline_data("BINANCE:BTCUSDT@KLINE_60", "BTCUSDT", "60")

        # Verify task was created with correct payload
        mock_tasks_repo.create_task.assert_called_once()
        call_args = mock_tasks_repo.create_task.call_args

        assert call_args[1]["task_type"] == "get_klines"
        assert call_args[1]["payload"]["symbol"] == "BTCUSDT"
        assert call_args[1]["payload"]["interval"] == "60"
        assert call_args[1]["payload"]["limit"] == 1000

    @pytest.mark.asyncio
    async def test_fill_loop_closes_connection_on_error(self, signal_service, mock_db):
        """Test that connection is closed even if error occurs."""
        # Reset mock call count
        mock_db.create_dedicated_connection.reset_mock()
        mock_db.close_dedicated_connection.reset_mock()

        async def mock_wait(conn, task_id, timeout):
            raise Exception("Test error")

        with pytest.raises(Exception):
            with patch.object(signal_service, "_wait_for_task_completion_with_conn", mock_wait):
                await signal_service._fill_kline_data("BINANCE:BTCUSDT@KLINE_60", "BTCUSDT", "60")

        # Connection should still be closed
        assert mock_db.close_dedicated_connection.call_count == 1
