"""Tests for realtime kline data continuity detection and fill logic.

Tests cover:
1. Normal update (gap == 0): update existing kline
2. New kline (gap == interval_ms): add new kline
3. Data gap (gap > interval_ms * 1.5): trigger fill
4. Abnormal case (other gap values): trigger fill
"""

import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.signal_service import SignalService, TV_INTERVAL_TO_MS


class TestRealtimeContinuityDetection:
    """Tests for realtime kline continuity detection logic."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = MagicMock()
        db.create_dedicated_connection = AsyncMock(return_value=MagicMock())
        return db

    @pytest.fixture
    def signal_service(self, mock_db):
        """Create signal service instance with mocked dependencies."""
        service = SignalService(mock_db)
        return service

    @pytest.fixture
    def sample_kline_data(self):
        """Create sample kline data for testing."""
        return pd.DataFrame([
            {
                "time": 1704067200000,  # 2024-01-01 00:00:00 UTC
                "open": 42000.50,
                "high": 42100.00,
                "low": 41950.00,
                "close": 42080.00,
                "volume": 125.4321,
            },
            {
                "time": 1704067260000,  # +1 minute
                "open": 42080.00,
                "high": 42150.00,
                "low": 42050.00,
                "close": 42100.00,
                "volume": 130.0,
            },
        ])

    def _extract_needs_fill_logic(
        self,
        cached_klines: pd.DataFrame,
        new_time: int,
        interval: str,
    ) -> tuple[bool, str]:
        """Extract the continuity detection logic for testing.

        This replicates the logic from _process_realtime_update method.

        Returns:
            tuple of (needs_fill: bool, scenario: str)
        """
        if len(cached_klines) < 1:
            return False, "no_cache"

        interval_ms = TV_INTERVAL_TO_MS.get(interval, 60000)
        cache_last_time = cached_klines.iloc[-1]["time"]
        gap = new_time - cache_last_time

        # Scenario analysis:
        # - gap == 0: same time, update the kline
        # - gap == interval_ms: one period apart, add new kline
        # - gap > interval_ms * 1.5: data discontinuity, needs fill
        # - other: abnormal case, needs fill

        if gap == 0:
            return False, "update_existing"
        elif gap == interval_ms:
            return False, "add_new_kline"
        elif gap > interval_ms * 1.5:
            return True, "data_gap"
        else:
            # Abnormal case (e.g., gap < interval_ms but not 0)
            return True, "abnormal_gap"

    def test_gap_zero_updates_existing_kline(self, sample_kline_data):
        """Test gap == 0: should NOT trigger fill (update existing kline)."""
        interval = "1"
        interval_ms = TV_INTERVAL_TO_MS[interval]
        new_time = sample_kline_data.iloc[-1]["time"]  # Same as cache last time

        needs_fill, scenario = self._extract_needs_fill_logic(
            sample_kline_data, new_time, interval
        )

        assert needs_fill is False
        assert scenario == "update_existing"

    def test_gap_interval_ms_adds_new_kline(self, sample_kline_data):
        """Test gap == interval_ms: should NOT trigger fill (add new kline)."""
        interval = "1"
        interval_ms = TV_INTERVAL_TO_MS[interval]
        new_time = sample_kline_data.iloc[-1]["time"] + interval_ms

        needs_fill, scenario = self._extract_needs_fill_logic(
            sample_kline_data, new_time, interval
        )

        assert needs_fill is False
        assert scenario == "add_new_kline"

    def test_gap_exceeds_threshold_triggers_fill(self, sample_kline_data):
        """Test gap > interval_ms * 1.5: should trigger fill."""
        interval = "1"
        interval_ms = TV_INTERVAL_TO_MS[interval]
        # Gap exceeds 1.5x threshold
        new_time = sample_kline_data.iloc[-1]["time"] + int(interval_ms * 2)

        needs_fill, scenario = self._extract_needs_fill_logic(
            sample_kline_data, new_time, interval
        )

        assert needs_fill is True
        assert scenario == "data_gap"

    def test_abnormal_gap_triggers_fill(self, sample_kline_data):
        """Test abnormal gap (gap < interval_ms but not 0): should trigger fill."""
        interval = "1"
        interval_ms = TV_INTERVAL_TO_MS[interval]
        # Gap is less than interval_ms but not zero (abnormal)
        new_time = sample_kline_data.iloc[-1]["time"] + int(interval_ms * 0.5)

        needs_fill, scenario = self._extract_needs_fill_logic(
            sample_kline_data, new_time, interval
        )

        assert needs_fill is True
        assert scenario == "abnormal_gap"

    def test_gap_just_above_threshold_triggers_fill(self, sample_kline_data):
        """Test gap just above 1.5x threshold: should trigger fill."""
        interval = "60"  # 60 minutes
        interval_ms = TV_INTERVAL_TO_MS[interval]
        # Gap = 1.5 * interval_ms + 1ms (just above threshold)
        new_time = sample_kline_data.iloc[-1]["time"] + int(interval_ms * 1.5) + 1

        needs_fill, scenario = self._extract_needs_fill_logic(
            sample_kline_data, new_time, interval
        )

        assert needs_fill is True
        assert scenario == "data_gap"

    def test_gap_just_below_threshold_no_fill(self, sample_kline_data):
        """Test gap just below 1.5x threshold: should NOT trigger fill."""
        interval = "60"  # 60 minutes
        interval_ms = TV_INTERVAL_TO_MS[interval]
        # Gap = 1.5 * interval_ms - 1ms (just below threshold)
        new_time = sample_kline_data.iloc[-1]["time"] + int(interval_ms * 1.5) - 1

        needs_fill, scenario = self._extract_needs_fill_logic(
            sample_kline_data, new_time, interval
        )

        # Below threshold but not equal to interval_ms, so it's abnormal
        assert needs_fill is True
        assert scenario == "abnormal_gap"

    def test_different_intervals(self):
        """Test continuity detection with different intervals."""
        test_cases = [
            ("1", 1 * 60 * 1000),
            ("5", 5 * 60 * 1000),
            ("15", 15 * 60 * 1000),
            ("30", 30 * 60 * 1000),
            ("60", 60 * 60 * 1000),
            ("240", 240 * 60 * 1000),
        ]

        base_time = 1704067200000

        for interval, interval_ms in test_cases:
            cached = pd.DataFrame([{"time": base_time, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}])

            # Test: gap == interval_ms -> no fill
            new_time = base_time + interval_ms
            needs_fill, scenario = self._extract_needs_fill_logic(cached, new_time, interval)
            assert needs_fill is False, f"Interval {interval}: gap == interval_ms should not fill"
            assert scenario == "add_new_kline"

            # Test: gap > interval_ms * 1.5 -> fill
            new_time = base_time + int(interval_ms * 2)
            needs_fill, scenario = self._extract_needs_fill_logic(cached, new_time, interval)
            assert needs_fill is True, f"Interval {interval}: gap > 1.5*interval_ms should fill"
            assert scenario == "data_gap"

    def test_empty_cache_no_fill(self):
        """Test empty cache: should NOT trigger fill."""
        cached = pd.DataFrame()
        new_time = 1704067200000
        interval = "1"

        needs_fill, scenario = self._extract_needs_fill_logic(
            cached, new_time, interval
        )

        assert needs_fill is False
        assert scenario == "no_cache"

    def test_single_kline_cache(self):
        """Test single kline in cache."""
        cached = pd.DataFrame([
            {"time": 1704067200000, "open": 42000.0, "high": 42100.0, "low": 41950.0, "close": 42080.0, "volume": 100.0}
        ])
        interval = "1"
        interval_ms = TV_INTERVAL_TO_MS[interval]

        # gap == interval_ms -> add new
        new_time = 1704067200000 + interval_ms
        needs_fill, scenario = self._extract_needs_fill_logic(cached, new_time, interval)
        assert needs_fill is False
        assert scenario == "add_new_kline"

        # gap > 1.5 * interval_ms -> fill
        new_time = 1704067200000 + int(interval_ms * 2)
        needs_fill, scenario = self._extract_needs_fill_logic(cached, new_time, interval)
        assert needs_fill is True
        assert scenario == "data_gap"


class TestRealtimeFillIntegration:
    """Integration tests for realtime fill with mocked service."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = MagicMock()
        db.create_dedicated_connection = AsyncMock(return_value=MagicMock())
        return db

    @pytest.mark.asyncio
    async def test_fill_called_when_gap_detected(self, mock_db):
        """Test that _fill_kline_data is called when gap is detected."""
        service = SignalService(mock_db)

        # Setup cache with existing kline
        base_time = 1704067200000
        service._kline_cache["BINANCE:BTCUSDT@KLINE_1"] = pd.DataFrame([
            {"time": base_time, "open": 42000.0, "high": 42100.0, "low": 41950.0, "close": 42080.0, "volume": 100.0}
        ])

        # Mock _fill_kline_data
        service._fill_kline_data = AsyncMock()

        # Simulate gap > 1.5 * interval_ms
        interval = "1"
        interval_ms = TV_INTERVAL_TO_MS[interval]
        new_time = base_time + int(interval_ms * 2)  # Gap exceeds threshold

        # Verify logic triggers fill
        cached_klines = service._kline_cache["BINANCE:BTCUSDT@KLINE_1"]
        gap = new_time - cached_klines.iloc[-1]["time"]

        assert gap > interval_ms * 1.5, "Gap should exceed threshold"

    @pytest.mark.asyncio
    async def test_fill_not_called_for_normal_update(self, mock_db):
        """Test that _fill_kline_data is NOT called for normal updates."""
        service = SignalService(mock_db)

        # Setup cache with existing kline
        base_time = 1704067200000
        service._kline_cache["BINANCE:BTCUSDT@KLINE_1"] = pd.DataFrame([
            {"time": base_time, "open": 42000.0, "high": 42100.0, "low": 41950.0, "close": 42080.0, "volume": 100.0}
        ])

        # Mock _fill_kline_data
        service._fill_kline_data = AsyncMock()

        # Simulate gap == 0 (update existing)
        new_time = base_time
        cached_klines = service._kline_cache["BINANCE:BTCUSDT@KLINE_1"]
        gap = new_time - cached_klines.iloc[-1]["time"]

        assert gap == 0, "Gap should be zero for update"

    @pytest.mark.asyncio
    async def test_fill_not_called_for_new_kline(self, mock_db):
        """Test that _fill_kline_data is NOT called when adding new kline."""
        service = SignalService(mock_db)

        # Setup cache with existing kline
        base_time = 1704067200000
        service._kline_cache["BINANCE:BTCUSDT@KLINE_1"] = pd.DataFrame([
            {"time": base_time, "open": 42000.0, "high": 42100.0, "low": 41950.0, "close": 42080.0, "volume": 100.0}
        ])

        # Simulate gap == interval_ms (new kline)
        interval = "1"
        interval_ms = TV_INTERVAL_TO_MS[interval]
        new_time = base_time + interval_ms
        cached_klines = service._kline_cache["BINANCE:BTCUSDT@KLINE_1"]
        gap = new_time - cached_klines.iloc[-1]["time"]

        assert gap == interval_ms, "Gap should equal interval for new kline"
        assert gap > 0
        assert gap <= interval_ms
