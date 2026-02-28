"""Listener for alert_config database notifications.

This listener handles:
- alert_config.new: New alert configuration created
- alert_config.update: Alert configuration updated
- alert_config.delete: Alert configuration deleted
"""

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class AlertSignalListener:
    """Listener for alert_config PostgreSQL notifications.

    This listener connects to the database and listens for NOTIFY events
    on the 'alert_config.new', 'alert_config.update', and 'alert_config.delete' channels.
    """

    def __init__(
        self,
        connection,
        on_new: callable | None = None,
        on_update: callable | None = None,
        on_delete: callable | None = None,
    ) -> None:
        """Initialize listener.

        Args:
            connection: Asyncpg connection for listening.
            on_new: Callback for new alert signals.
            on_update: Callback for updated alert signals.
            on_delete: Callback for deleted alert signals.
        """
        self._connection = connection
        self._on_new = on_new
        self._on_update = on_update
        self._on_delete = on_delete
        self._listening = False
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Start listening for notifications."""
        if self._listening:
            logger.warning("Already listening for alert_config notifications")
            return

        logger.info("Starting to listen for alert_config notifications")
        await self._connection.add_listener("alert_config.new", self._handle_new)
        await self._connection.add_listener("alert_config.update", self._handle_update)
        await self._connection.add_listener("alert_config.delete", self._handle_delete)
        self._listening = True

    async def stop(self) -> None:
        """Stop listening for notifications."""
        if not self._listening:
            return

        logger.info("Stopping alert_config listener")
        self._listening = False

        # Cancel all pending tasks
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

        await self._connection.remove_listener("alert_config.new", self._handle_new)
        await self._connection.remove_listener("alert_config.update", self._handle_update)
        await self._connection.remove_listener("alert_config.delete", self._handle_delete)

    def _handle_notification(
        self, channel: str, payload: str
    ) -> None:
        """Handle incoming notification.

        Args:
            channel: Channel name ('alert_config.new', 'alert_config.update', 'alert_config.delete').
            payload: JSON payload string.
        """
        try:
            data = json.loads(payload)
            # Database notification uses wrapped format:
            # {"event_id": "...", "event_type": "...", "timestamp": "...", "data": {"id": "...", ...}}
            # We need to extract the inner 'data' object to get alert fields
            inner_data = data.get("data", {})
            logger.debug(
                "Received %s notification: alert_id=%s name=%s",
                channel,
                inner_data.get("id"),
                inner_data.get("name"),
            )

            # Schedule async callback - pass inner data for easier access
            task = asyncio.create_task(self._dispatch_callback(channel, inner_data))
            self._tasks.append(task)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse notification payload: %s", str(e))

    async def _dispatch_callback(self, channel: str, data: dict[str, Any]) -> None:
        """Dispatch callback based on channel."""
        try:
            if channel == "alert_config.new" and self._on_new:
                self._on_new(data)
            elif channel == "alert_config.update" and self._on_update:
                self._on_update(data)
            elif channel == "alert_config.delete" and self._on_delete:
                self._on_delete(data)
        except Exception as e:
            logger.error("Error in alert callback: %s", str(e))
        finally:
            # Remove completed task
            self._tasks = [t for t in self._tasks if not t.done()]

    async def _handle_new(
        self, connection: Any, pid: int, channel: str, payload: str
    ) -> None:
        """Handle new alert config notification."""
        self._handle_notification(channel, payload)

    async def _handle_update(
        self, connection: Any, pid: int, channel: str, payload: str
    ) -> None:
        """Handle updated alert config notification."""
        self._handle_notification(channel, payload)

    async def _handle_delete(
        self, connection: Any, pid: int, channel: str, payload: str
    ) -> None:
        """Handle deleted alert config notification."""
        self._handle_notification(channel, payload)
