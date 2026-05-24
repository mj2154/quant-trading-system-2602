"""pytest configuration for signal service tests."""

import sys
from datetime import UTC
from pathlib import Path

import pytest

# Add src directory to path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_strategy_input():
    """Sample strategy input for testing."""
    from datetime import datetime

    from src.strategies.base import StrategyInput

    return StrategyInput(
        symbol="BINANCE:BTCUSDT",
        interval="1",
        kline_data={
            "time": 1704067200000,
            "open": 42000.50,
            "high": 42100.00,
            "low": 41950.00,
            "close": 42080.00,
            "volume": 125.4321,
        },
        subscription_key="BINANCE:BTCUSDT@KLINE_1",
        computed_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_db():
    """Mock database for testing."""
    from unittest.mock import MagicMock

    from src.db.database import Database

    db = MagicMock(spec=Database)
    db.pool = MagicMock()
    return db
