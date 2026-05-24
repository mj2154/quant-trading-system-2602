"""K-line cache initialization and fill management."""

import asyncio
import logging
from typing import Any

import pandas as pd

from ..db.database import Database
from ..db.realtime_data_repository import RealtimeDataRepository
from ..db.tasks_repository import TasksRepository
from .constants import REQUIRED_KLINES, RETRY_DELAY_SECONDS
from .kline_cache import _init_kline_cache
from .kline_utils import _format_kline_time
from .kline_validator import _check_kline_data_validity
from .task_waiter import _wait_for_task_completion

logger = logging.getLogger(__name__)


class KlineCacheManager:
    """Manages K-line cache initialization, filling, and validation."""

    def __init__(
        self,
        db: Database,
        realtime_repo: RealtimeDataRepository,
        tasks_repo: TasksRepository,
        kline_cache: dict[str, pd.DataFrame],
    ) -> None:
        self._db = db
        self._realtime_repo = realtime_repo
        self._tasks_repo = tasks_repo
        self._kline_cache = kline_cache

    async def init_cache_for_key(self, subscription_key: str) -> None:
        """Initialize K-line cache for a subscription key.

        Implements three-condition check and fill loop:
        1. Check quantity >= REQUIRED_KLINES
        2. Check kline continuity
        3. Check last kline time = previous period

        If all conditions met, initialize cache and return.
        Otherwise, enter fill loop until task succeeds.
        """
        if "@" not in subscription_key:
            logger.error("Invalid subscription key format: %s", subscription_key)
            return

        symbol_with_prefix = subscription_key.split("@")[0]
        interval = subscription_key.split("@")[1].replace("KLINE_", "")
        symbol = symbol_with_prefix

        history = await self._realtime_repo.get_klines_history(
            symbol=symbol,
            interval=interval,
            limit=REQUIRED_KLINES,
        )

        is_valid, reason = _check_kline_data_validity(history, interval, REQUIRED_KLINES)

        if is_valid:
            await self.do_init_cache(subscription_key, history)
            return

        logger.warning(
            "K-line data validation failed: subscription_key=%s reason=%s, entering fill loop",
            subscription_key,
            reason,
        )

        await self.fill_kline_data(subscription_key, symbol, interval)

    async def fill_kline_data(
        self, subscription_key: str, symbol: str, interval: str
    ) -> None:
        """Fill kline data by creating tasks and waiting for completion.

        Loop until task succeeds (infinite loop as per design):
        1. Create task: get_klines, limit=1000
        2. Listen for task notification (5s timeout)
        3. On failure/timeout: sleep 2s, retry
        4. On success: re-query data, initialize cache

        Connection is reused across retries to avoid overhead.
        """
        retry_count = 0
        conn = await self._db.create_dedicated_connection()

        try:
            while True:
                retry_count += 1

                logger.info(
                    "Creating kline fill task: subscription_key=%s retry=%d",
                    subscription_key,
                    retry_count,
                )

                task_id = await self._tasks_repo.create_task(
                    task_type="get_klines",
                    payload={
                        "symbol": symbol,
                        "interval": interval,
                        "limit": 1000,
                    },
                )

                task_status = await _wait_for_task_completion(
                    self._db, self._tasks_repo, task_id, timeout=5, conn=conn
                )

                if task_status == "completed":
                    logger.info(
                        "Kline fill task completed: subscription_key=%s retry=%d",
                        subscription_key,
                        retry_count,
                    )

                    history = await self._realtime_repo.get_klines_history(
                        symbol=symbol,
                        interval=interval,
                        limit=REQUIRED_KLINES,
                    )
                    logger.info(
                        "fill_kline_data: Queried history: subscription_key=%s symbol=%s "
                        "interval=%s history_count=%d",
                        subscription_key, symbol, interval, len(history),
                    )

                    await self.do_init_cache(subscription_key, history)
                    return

                logger.warning(
                    "Kline fill task failed/timeout: subscription_key=%s status=%s retry=%d",
                    subscription_key,
                    task_status,
                    retry_count,
                )

                await asyncio.sleep(RETRY_DELAY_SECONDS)

            logger.error(
                "Kline fill loop exited unexpectedly: subscription_key=%s retry_count=%d",
                subscription_key,
                retry_count,
            )
        finally:
            await self._db.close_dedicated_connection(conn)
            logger.debug("Closed dedicated connection for kline fill: %s", subscription_key)

    async def do_init_cache(
        self,
        subscription_key: str,
        history: list[dict[str, Any]],
    ) -> None:
        """Initialize kline cache with given history data."""
        _init_kline_cache(
            cache=self._kline_cache,
            subscription_key=subscription_key,
            history=history,
            required_klines=REQUIRED_KLINES,
        )

        cached_klines = self._kline_cache.get(subscription_key, pd.DataFrame())
        cached_count = len(cached_klines)

        first_time_raw = cached_klines.iloc[0]["time"] if len(cached_klines) > 0 else None
        last_time_raw = cached_klines.iloc[-1]["time"] if len(cached_klines) > 0 else None

        first_time = _format_kline_time(first_time_raw)
        last_time = _format_kline_time(last_time_raw)

        logger.info(
            "Initialized K-line cache: subscription_key=%s klines=%d time_range=[%s -> %s]",
            subscription_key, cached_count, first_time, last_time,
        )
