#!/usr/bin/env python3
"""Subscription Manager Service Entry Point.

Sole authority for managing realtime_data table subscriptions.
Listens for subscription_task_new notifications and monitors health.
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import timezone
from pathlib import Path

import asyncpg


class CSTFormatter(logging.Formatter):
    """Custom formatter that uses China Standard Time (UTC+8)."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        import datetime as dt
        dt_obj = dt.datetime.fromtimestamp(record.created, tz=timezone.utc)
        cst_dt = dt_obj.astimezone(dt.timezone(dt.timedelta(hours=8)))
        if datefmt:
            return cst_dt.strftime(datefmt)
        return cst_dt.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]


sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.health_monitor import HealthMonitor
from src.services.subscription_service import SubscriptionService

formatter = CSTFormatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S,%f",
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.basicConfig(
    level=logging.INFO,
    handlers=[handler],
)
logger = logging.getLogger(__name__)


def get_db_host() -> str:
    return os.environ.get("DATABASE_HOST", "localhost")


def get_db_password() -> str:
    return os.environ.get("DATABASE_PASSWORD", "pass")


async def _heartbeat_loop(pool: asyncpg.Pool, interval: int = 10) -> None:
    """Periodically update subscription-manager heartbeat in service_heartbeats."""
    while True:
        try:
            await asyncio.sleep(interval)
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO service_heartbeats (subscriber_id, last_heartbeat)
                    VALUES ('subscription-manager', NOW())
                    ON CONFLICT (subscriber_id)
                    DO UPDATE SET last_heartbeat = NOW()
                    """
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Heartbeat update failed")


async def main() -> None:
    """Main entry point for subscription-manager service."""
    logger.info("Starting Subscription Manager Service")

    db_host = get_db_host()
    db_password = get_db_password()

    pool = await asyncpg.create_pool(
        host=db_host,
        port=5432,
        user="dbuser",
        password=db_password,
        database="trading_db",
        min_size=2,
        max_size=5,
    )
    logger.info("Database pool created (host=%s)", db_host)

    subscription_service = SubscriptionService(pool)
    health_monitor = HealthMonitor(pool)

    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    def signal_handler() -> None:
        logger.info("Shutdown signal received")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    heartbeat_task = asyncio.create_task(_heartbeat_loop(pool))
    logger.info("Heartbeat started")

    await subscription_service.start()
    await health_monitor.start()

    await shutdown_event.wait()

    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM service_heartbeats WHERE subscriber_id = 'subscription-manager'"
            )
    except Exception:
        logger.exception("Failed to delete heartbeat")
    logger.info("Heartbeat stopped")

    await health_monitor.stop()
    await subscription_service.stop()
    await pool.close()

    logger.info("Subscription Manager Service stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Fatal error: %s", e)
        sys.exit(1)
