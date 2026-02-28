#!/usr/bin/env python3
"""Signal Service Entry Point.

A service that listens for realtime data updates and calculates strategy signals.
"""

import asyncio
import signal
import sys
import logging
import os
from datetime import timezone
from pathlib import Path


class CSTFormatter(logging.Formatter):
    """Custom formatter that uses China Standard Time (UTC+8)."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Override formatTime to use UTC+8 timezone."""
        import datetime
        dt = datetime.datetime.fromtimestamp(record.created, tz=timezone.utc)
        cst_dt = dt.astimezone(datetime.timezone(datetime.timedelta(hours=8)))
        if datefmt:
            return cst_dt.strftime(datefmt)
        return cst_dt.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.db.database import Database, DatabaseConfig
from src.services.signal_service import SignalService

# Import all strategy modules to trigger registration
import src.strategies.macd_resonance_strategy  # noqa: F401
import src.strategies.alpha_01_strategy  # noqa: F401
from src.strategies.registry import StrategyRegistry

# Configure logging with China Standard Time (UTC+8)
formatter = CSTFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S,%f")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.basicConfig(
    level=logging.INFO,
    handlers=[handler],
)
logger = logging.getLogger(__name__)


def get_db_host() -> str:
    """Get database host from environment or default."""
    return os.environ.get("DATABASE_HOST", "localhost")


def get_db_password() -> str:
    """Get database password from environment or default."""
    return os.environ.get("DATABASE_PASSWORD", "pass")


async def main() -> None:
    """Main entry point for signal service."""
    logger.info("Starting Signal Service")

    # Create database configuration from environment or defaults
    db_config = DatabaseConfig(
        host=get_db_host(),
        port=5432,
        user="dbuser",
        password=get_db_password(),
        database="trading_db",
        min_size=2,
        max_size=5,
    )

    # Create database connection
    db = Database(db_config)
    await db.connect()
    logger.info("Database connected")

    # Discover and register strategies, then sync to database
    logger.info("Discovering and registering strategies")
    StrategyRegistry.discover_strategies()
    await StrategyRegistry.sync_to_database(db)
    logger.info(f"Registered {len(StrategyRegistry.get_all())} strategies")

    # Create signal service - strategies are dynamically loaded from alert configs
    # Each alert has its own strategy instance keyed by alert_id
    signal_service = SignalService(db=db)

    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    def signal_handler() -> None:
        """Handle shutdown signals."""
        logger.info("Shutdown signal received")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # Start the service
    await signal_service.start()

    # Wait for shutdown
    await shutdown_event.wait()

    # Stop the service
    await signal_service.stop()
    await db.close()

    logger.info("Signal Service stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Fatal error: %s", str(e))
        sys.exit(1)
