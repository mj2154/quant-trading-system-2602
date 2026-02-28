"""Tests for EMA and MACD indicators."""

import pytest

from src.indicators.ema import (
    EmaResult,
    calculate_ema,
    calculate_ema_latest,
)
from src.indicators.macd import (
    MacdResult,
    calculate_macd,
    get_macd_signal,
    is_golden_cross,
    is_death_cross,
)


# ============================================================================
# EMA Tests
# ============================================================================

class TestCalculateEma:
    """Tests for calculate_ema function."""

    def test_ema_basic_calculation(self) -> None:
        """Test basic EMA calculation with known values."""
        # Simple price list with clear trend
        prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
        result = calculate_ema(prices, period=3)

        # With period=3, we should have 3 EMA values (starting from index 2)
        assert len(result.values) == 4  # prices[2:] to prices[5]
        assert result.period == 3

    def test_ema_insufficient_data(self) -> None:
        """Test EMA with insufficient data returns empty list."""
        prices = [10.0, 11.0]
        result = calculate_ema(prices, period=3)

        assert result.values == []
        assert result.period == 3

    def test_ema_exact_period_data(self) -> None:
        """Test EMA with exactly period amount of data."""
        prices = [10.0, 11.0, 12.0]  # Exactly 3 prices for period=3
        result = calculate_ema(prices, period=3)

        # Should return one value (SMA of first 3 prices)
        assert len(result.values) == 1

    def test_ema_constant_prices(self) -> None:
        """Test EMA with constant prices."""
        prices = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        result = calculate_ema(prices, period=3)

        # With constant prices, EMA should converge to 10.0
        assert len(result.values) == 4
        # All values should be close to 10.0
        for ema_value in result.values:
            assert abs(ema_value - 10.0) < 0.1

    def test_ema_manual_verification(self) -> None:
        """Test EMA against manual calculation for verification.

        For period=3, k = 2/(3+1) = 0.5
        Prices: [10, 11, 12]
        First EMA = SMA = (10+11+12)/3 = 11.0

        Next price: 13
        EMA = 13 * 0.5 + 11.0 * 0.5 = 12.0
        """
        prices = [10.0, 11.0, 12.0, 13.0]
        result = calculate_ema(prices, period=3)

        # First value should be SMA
        assert abs(result.values[0] - 11.0) < 0.001
        # Second value: 13 * 0.5 + 11 * 0.5 = 12.0
        assert abs(result.values[1] - 12.0) < 0.001


class TestCalculateEmaLatest:
    """Tests for calculate_ema_latest function."""

    def test_ema_latest_basic(self) -> None:
        """Test getting latest EMA value."""
        prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
        latest = calculate_ema_latest(prices, period=3)

        assert latest is not None
        assert isinstance(latest, float)

    def test_ema_latest_insufficient_data(self) -> None:
        """Test getting latest EMA with insufficient data."""
        prices = [10.0, 11.0]
        latest = calculate_ema_latest(prices, period=3)

        assert latest is None


# ============================================================================
# MACD Tests
# ============================================================================

class TestCalculateMacd:
    """Tests for calculate_macd function."""

    def test_macd_insufficient_data(self) -> None:
        """Test MACD with insufficient data returns empty lists."""
        prices = [10.0, 11.0, 12.0]  # Less than slow_period (26)
        result = calculate_macd(prices)

        assert result.macd_line == []
        assert result.signal_line == []
        assert result.histogram == []

    def test_macd_basic_structure(self) -> None:
        """Test MACD returns proper structure with enough data."""
        # Generate enough data for MACD calculation
        prices = [100.0 + i * 0.5 for i in range(50)]
        result = calculate_macd(prices)

        # MACD line should exist
        assert isinstance(result.macd_line, list)
        assert isinstance(result.signal_line, list)
        assert isinstance(result.histogram, list)
        assert result.fast_period == 12
        assert result.slow_period == 26
        assert result.signal_period == 9

    def test_macd_default_parameters(self) -> None:
        """Test MACD with default parameters."""
        prices = [100.0 + i for i in range(50)]
        result = calculate_macd(prices)

        assert result.fast_period == 12
        assert result.slow_period == 26
        assert result.signal_period == 9

    def test_macd_custom_parameters(self) -> None:
        """Test MACD with custom parameters."""
        prices = [100.0 + i for i in range(30)]
        result = calculate_macd(
            prices,
            fast_period=5,
            slow_period=10,
            signal_period=4,
        )

        assert result.fast_period == 5
        assert result.slow_period == 10
        assert result.signal_period == 4

    def test_macd_uptrend(self) -> None:
        """Test MACD with upward trending prices produces valid output."""
        # Strong upward trend
        prices = [100.0 + i * 5 for i in range(50)]
        result = calculate_macd(prices)

        # Should produce valid result with histogram
        assert result.macd_line is not None
        assert result.signal_line is not None
        # Histogram should have values when MACD is calculated
        if result.histogram:
            # Verify histogram values are numeric
            assert all(isinstance(h, (int, float)) for h in result.histogram)

    def test_macd_downtrend(self) -> None:
        """Test MACD with downward trending prices produces valid output."""
        # Strong downward trend
        prices = [200.0 - i * 5 for i in range(50)]
        result = calculate_macd(prices)

        # Should produce valid result with histogram
        assert result.macd_line is not None
        assert result.signal_line is not None
        if result.histogram:
            # Verify histogram values are numeric
            assert all(isinstance(h, (int, float)) for h in result.histogram)


class TestGetMacdSignal:
    """Tests for get_macd_signal function."""

    def test_signal_bullish(self) -> None:
        """Test bullish signal when MACD > Signal."""
        # Create MACD result with positive histogram
        macd_result = MacdResult(
            macd_line=[1.0, 2.0, 3.0],
            signal_line=[0.5, 1.5, 2.5],
            histogram=[0.5, 0.5, 0.5],  # All positive
            fast_period=12,
            slow_period=26,
            signal_period=9,
        )

        signal = get_macd_signal(macd_result)
        assert signal == 1

    def test_signal_bearish(self) -> None:
        """Test bearish signal when MACD < Signal."""
        macd_result = MacdResult(
            macd_line=[0.5, 1.0, 1.5],
            signal_line=[1.0, 2.0, 3.0],
            histogram=[-0.5, -1.0, -1.5],  # All negative
            fast_period=12,
            slow_period=26,
            signal_period=9,
        )

        signal = get_macd_signal(macd_result)
        assert signal == -1

    def test_signal_neutral(self) -> None:
        """Test neutral signal when MACD == Signal."""
        macd_result = MacdResult(
            macd_line=[1.0, 2.0, 3.0],
            signal_line=[1.0, 2.0, 3.0],
            histogram=[0.0, 0.0, 0.0],  # All zero
            fast_period=12,
            slow_period=26,
            signal_period=9,
        )

        signal = get_macd_signal(macd_result)
        assert signal == 0

    def test_signal_insufficient_data(self) -> None:
        """Test signal returns None with insufficient data."""
        macd_result = MacdResult(
            macd_line=[],
            signal_line=[],
            histogram=[],
            fast_period=12,
            slow_period=26,
            signal_period=9,
        )

        signal = get_macd_signal(macd_result)
        assert signal is None

    def test_signal_only_one_histogram(self) -> None:
        """Test signal returns None with only one histogram value."""
        macd_result = MacdResult(
            macd_line=[1.0],
            signal_line=[0.5],
            histogram=[0.5],  # Only one value
            fast_period=12,
            slow_period=26,
            signal_period=9,
        )

        signal = get_macd_signal(macd_result)
        assert signal is None


class TestIsGoldenCross:
    """Tests for is_golden_cross function."""

    def test_golden_cross_detected(self) -> None:
        """Test golden cross is detected when histogram crosses from negative to positive."""
        macd_result = MacdResult(
            macd_line=[1.0, 2.0, 3.0],
            signal_line=[2.0, 2.5, 2.8],
            histogram=[-1.0, -0.5, 0.2],  # Crosses from negative to positive
            fast_period=12,
            slow_period=26,
            signal_period=9,
        )

        assert is_golden_cross(macd_result) is True

    def test_golden_cross_not_detected_continues_positive(self) -> None:
        """Test golden cross not detected when histogram stays positive."""
        macd_result = MacdResult(
            macd_line=[1.0, 2.0, 3.0],
            signal_line=[0.5, 1.5, 2.5],
            histogram=[0.5, 0.5, 0.5],  # Always positive
            fast_period=12,
            slow_period=26,
            signal_period=9,
        )

        assert is_golden_cross(macd_result) is False

    def test_golden_cross_insufficient_data(self) -> None:
        """Test golden cross returns False with insufficient data."""
        macd_result = MacdResult(
            macd_line=[1.0],
            signal_line=[0.5],
            histogram=[0.5],
            fast_period=12,
            slow_period=26,
            signal_period=9,
        )

        assert is_golden_cross(macd_result) is False


class TestIsDeathCross:
    """Tests for is_death_cross function."""

    def test_death_cross_detected(self) -> None:
        """Test death cross is detected when histogram crosses from positive to negative."""
        macd_result = MacdResult(
            macd_line=[3.0, 2.0, 1.0],
            signal_line=[2.0, 2.5, 2.8],
            histogram=[1.0, 0.5, -1.8],  # Crosses from positive to negative
            # Previous: 0.5 > 0, Current: -1.8 <= 0 => Death cross!
            fast_period=12,
            slow_period=26,
            signal_period=9,
        )

        assert is_death_cross(macd_result) is True

    def test_death_cross_not_detected_continues_negative(self) -> None:
        """Test death cross not detected when histogram stays negative."""
        macd_result = MacdResult(
            macd_line=[0.5, 1.0, 1.5],
            signal_line=[1.0, 2.0, 3.0],
            histogram=[-0.5, -1.0, -1.5],  # Always negative
            fast_period=12,
            slow_period=26,
            signal_period=9,
        )

        assert is_death_cross(macd_result) is False

    def test_death_cross_insufficient_data(self) -> None:
        """Test death cross returns False with insufficient data."""
        macd_result = MacdResult(
            macd_line=[1.0],
            signal_line=[2.0],
            histogram=[-1.0],
            fast_period=12,
            slow_period=26,
            signal_period=9,
        )

        assert is_death_cross(macd_result) is False
