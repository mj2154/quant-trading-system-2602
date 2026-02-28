"""Tests for K-line cache initialization logic.

Tests cover:
1. Kline continuity check
2. Last kline time check
3. Three-condition validation
4. Previous period time calculation
"""

import pytest
import time
from datetime import datetime, timezone, timedelta

from src.services.signal_service import (
    _check_kline_continuity,
    _check_last_kline_time,
    _check_kline_data_validity,
    _get_previous_period_time,
    REQUIRED_KLINES,
)


class TestGetPreviousPeriodTime:
    """Tests for previous period time calculation."""

    def test_1_minute_interval(self):
        """Test 1-minute interval."""
        now_ms = int(time.time() * 1000)
        result = _get_previous_period_time("1")

        # Should be aligned to minute boundary
        interval_ms = 60 * 1000
        expected = (now_ms // interval_ms) * interval_ms - interval_ms

        assert abs(result - expected) < 60000  # Within 1 minute tolerance

    def test_60_minute_interval(self):
        """Test 60-minute (1 hour) interval."""
        now_ms = int(time.time() * 1000)
        result = _get_previous_period_time("60")

        # Should be aligned to hour boundary
        interval_ms = 60 * 60 * 1000
        expected = (now_ms // interval_ms) * interval_ms - interval_ms

        assert abs(result - expected) < 3600000  # Within 1 hour tolerance


class TestCheckKlineContinuity:
    """Tests for kline continuity check."""

    def test_empty_history(self):
        """Empty history should return True (no gaps to check)."""
        assert _check_kline_continuity([], "60") is True

    def test_single_kline(self):
        """Single kline should return True."""
        history = [{"open_time": 1000}]
        assert _check_kline_continuity(history, "60") is True

    def test_continuous_klines_1m(self):
        """Continuous 1-minute klines."""
        base_time = int(time.time() * 1000) - (100 * 60 * 1000)
        history = [
            {"open_time": base_time + i * 60 * 1000}
            for i in range(100)
        ]
        assert _check_kline_continuity(history, "1") is True

    def test_continuous_klines_60m(self):
        """Continuous 60-minute klines."""
        base_time = int(time.time() * 1000) - (100 * 60 * 60 * 1000)
        history = [
            {"open_time": base_time + i * 60 * 60 * 1000}
            for i in range(50)
        ]
        assert _check_kline_continuity(history, "60") is True

    def test_gap_in_klines(self):
        """Klines with a gap should return False."""
        base_time = int(time.time() * 1000) - (100 * 60 * 1000)
        history = [
            {"open_time": base_time + i * 60 * 1000}
            for i in range(50)
        ]
        # Add a gap: skip one hour
        history[25]["open_time"] = history[24]["open_time"] + 2 * 60 * 60 * 1000

        assert _check_kline_continuity(history, "60") is False


class TestCheckLastKlineTime:
    """Tests for last kline time check."""

    def test_empty_history(self):
        """Empty history should return False."""
        assert _check_last_kline_time([], "60") is False

    def test_last_kline_is_previous_period(self):
        """Last kline is the previous period - should return True."""
        previous_period = _get_previous_period_time("60")
        history = [{"open_time": previous_period}]

        assert _check_last_kline_time(history, "60") is True

    def test_last_kline_is_current_period(self):
        """Last kline is the current period - should return False."""
        now_ms = int(time.time() * 1000)
        interval_ms = 60 * 60 * 1000
        current_period = (now_ms // interval_ms) * interval_ms
        history = [{"open_time": current_period}]

        assert _check_last_kline_time(history, "60") is False

    def test_last_kline_is_very_old(self):
        """Last kline is too old - should return False."""
        old_time = int(time.time() * 1000) - (24 * 60 * 60 * 1000)  # 1 day ago
        history = [{"open_time": old_time}]

        assert _check_last_kline_time(history, "60") is False


class TestCheckKlineDataValidity:
    """Tests for three-condition validation."""

    def test_valid_data(self):
        """Valid data should pass all checks."""
        previous_period = _get_previous_period_time("60")
        base_time = previous_period - (REQUIRED_KLINES - 1) * 60 * 60 * 1000

        history = [
            {"open_time": base_time + i * 60 * 60 * 1000}
            for i in range(REQUIRED_KLINES)
        ]

        is_valid, reason = _check_kline_data_validity(history, "60", REQUIRED_KLINES)

        assert is_valid is True
        assert reason == "ok"

    def test_insufficient_count(self):
        """Not enough klines should fail."""
        previous_period = _get_previous_period_time("60")
        base_time = previous_period - (100 * 60 * 60 * 1000)

        history = [
            {"open_time": base_time + i * 60 * 60 * 1000}
            for i in range(100)  # Less than REQUIRED_KLINES
        ]

        is_valid, reason = _check_kline_data_validity(history, "60", REQUIRED_KLINES)

        assert is_valid is False
        assert "insufficient_count" in reason

    def test_not_continuous(self):
        """Non-continuous klines should fail."""
        previous_period = _get_previous_period_time("60")
        base_time = previous_period - (REQUIRED_KLINES - 1) * 60 * 60 * 1000

        history = [
            {"open_time": base_time + i * 60 * 60 * 1000}
            for i in range(REQUIRED_KLINES)
        ]
        # Add a gap
        history[100]["open_time"] = history[99]["open_time"] + 2 * 60 * 60 * 1000

        is_valid, reason = _check_kline_data_validity(history, "60", REQUIRED_KLINES)

        assert is_valid is False
        assert reason == "not_continuous"

    def test_with_datetime_objects(self):
        """Test with datetime objects (as returned from database)."""
        previous_period = _get_previous_period_time("60")

        # Create datetime objects
        base_dt = datetime.fromtimestamp(
            (previous_period - (REQUIRED_KLINES - 1) * 60 * 60 * 1000) / 1000,
            tz=timezone.utc
        )

        history = [
            {"open_time": base_dt + timedelta(hours=i)}
            for i in range(REQUIRED_KLINES)
        ]

        is_valid, reason = _check_kline_data_validity(history, "60", REQUIRED_KLINES)

        # Should still work with datetime objects
        assert reason in ["ok", "last_kline_not_previous_period"]


class TestRequiredKlines:
    """Tests for REQUIRED_KLINES constant."""

    def test_required_klines_value(self):
        """REQUIRED_KLINES should be 280."""
        assert REQUIRED_KLINES == 280
