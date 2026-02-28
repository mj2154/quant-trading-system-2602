"""Listener for realtime.update database notifications."""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

RealtimeUpdateCallback = Callable[[dict[str, Any]], None]


class RealtimeUpdateListener:
    """Listener for realtime.update PostgreSQL notifications.

    This listener connects to the database and listens for NOTIFY events
    on the 'realtime.update' channel.
    """

    def __init__(self, connection, callback: RealtimeUpdateCallback) -> None:
        """Initialize listener.

        Args:
            connection: Asyncpg connection for listening.
            callback: Callback function to handle notifications.
        """
        self._connection = connection
        self._callback = callback
        self._listening = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start listening for notifications."""
        if self._listening:
            logger.warning("Already listening for realtime.update")
            return

        logger.info("Starting to listen for realtime.update notifications")
        await self._connection.add_listener("realtime.update", self._handle_notification)
        self._listening = True

        # Start background task to keep connection alive
        self._task = asyncio.create_task(self._keepalive())

    async def stop(self) -> None:
        """Stop listening for notifications."""
        if not self._listening:
            return

        logger.info("Stopping realtime.update listener")
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        await self._connection.remove_listener("realtime.update", self._handle_notification)
        self._listening = False

    async def _handle_notification(
        self, connection: Any, pid: int, channel: str, payload: str
    ) -> None:
        """Handle incoming notification.

        Args:
            connection: The connection that received the notification.
            pid: Process ID of the notifying backend.
            channel: Channel name ('realtime.update').
            payload: JSON payload string.
        """
        try:
            data = json.loads(payload)
            # Only log for KLINE data (not QUOTES) to reduce noise
            data_type = data.get("data", {}).get("data_type")
            if data_type == "KLINE":
                logger.debug(
                    "Received realtime.update notification: event_id=%s subscription_key=%s",
                    data.get("event_id"),
                    data.get("data", {}).get("subscription_key"),
                )
            # Call the callback with the notification data
            self._callback(data)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse notification payload: %s", str(e))

    async def _keepalive(self) -> None:
        """Keep connection alive with periodic queries."""
        while self._listening:
            try:
                await asyncio.sleep(30)
                # Execute a simple query to keep connection alive
                await self._connection.execute("SELECT 1")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Keepalive query failed: %s", str(e))
                break
