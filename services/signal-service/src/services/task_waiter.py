"""Task completion waiter using PostgreSQL NOTIFY/LISTEN."""

import asyncio
import json
import logging
from typing import Any

from ..db.database import Database
from ..db.tasks_repository import TasksRepository

logger = logging.getLogger(__name__)


async def _wait_for_task_completion(
    db: Database,
    tasks_repo: TasksRepository,
    task_id: int,
    timeout: int,
    conn: Any = None,
) -> str | None:
    """Wait for task completion via notification or timeout.

    Uses PostgreSQL NOTIFY/LISTEN on task_completed and task_failed channels.
    If conn is provided, reuses it instead of creating a new connection.

    Args:
        db: Database instance for creating dedicated connections.
        tasks_repo: Tasks repository for querying task status on timeout.
        task_id: Task ID to wait for.
        timeout: Timeout in seconds.
        conn: Optional existing dedicated connection to reuse.

    Returns:
        Task status: "completed", "failed", or None on timeout.
    """
    should_close = conn is None
    if should_close:
        conn = await db.create_dedicated_connection()

    completed_event = asyncio.Event()
    failed_event = asyncio.Event()

    async def handle_completed(
        connection: Any, _pid: int, channel: str, payload: str
    ) -> None:
        """Handle task_completed notification."""
        try:
            data = json.loads(payload)
            if data.get("id") == task_id:
                completed_event.set()
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse task_completed payload: %s", e)
        except Exception as e:
            logger.error("Unexpected error in task_completed handler: %s", e)

    async def handle_failed(
        connection: Any, _pid: int, channel: str, payload: str
    ) -> None:
        """Handle task_failed notification."""
        try:
            data = json.loads(payload)
            if data.get("id") == task_id:
                failed_event.set()
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse task_failed payload: %s", e)
        except Exception as e:
            logger.error("Unexpected error in task_failed handler: %s", e)

    await conn.add_listener("task_completed", handle_completed)
    await conn.add_listener("task_failed", handle_failed)

    try:
        done, pending = await asyncio.wait(
            [
                asyncio.create_task(completed_event.wait()),
                asyncio.create_task(failed_event.wait()),
            ],
            timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        if completed_event.is_set():
            return "completed"
        if failed_event.is_set():
            return "failed"

        status = await tasks_repo.get_task_status(task_id)
        logger.debug(
            "Task wait timeout: task_id=%s timeout=%ds status=%s",
            task_id,
            timeout,
            status,
        )

        if status == "processing":
            return None

        return status

    except Exception as e:
        logger.error(
            "Error waiting for task completion: task_id=%s error=%s",
            task_id,
            e,
        )
        return None
    finally:
        await conn.remove_listener("task_completed", handle_completed)
        await conn.remove_listener("task_failed", handle_failed)
        if should_close:
            await db.close_dedicated_connection(conn)
