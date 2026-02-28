"""Trigger condition engine for strategy execution.

This module determines when to execute strategy calculations based on trigger types:
- once_only: Execute once, then mark as completed
- each_kline: Execute on every kline update
- each_kline_close: Execute only when kline closes
- each_minute: Execute once per minute
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class TriggerType(StrEnum):
    """Trigger type enumeration."""

    ONCE_ONLY = "once_only"
    EACH_KLINE = "each_kline"
    EACH_KLINE_CLOSE = "each_kline_close"
    EACH_MINUTE = "each_minute"


@dataclass
class TriggerState:
    """State tracking for trigger execution."""

    # For once_only: tracks if already executed
    executed: bool = False

    # For each_minute: tracks last execution time
    last_executed_at: datetime | None = None

    # For each_kline_close: tracks last kline close time
    last_kline_close_time: str | None = None


class TriggerEngine(ABC):
    """Abstract base class for trigger engines."""

    @property
    @abstractmethod
    def trigger_type(self) -> TriggerType:
        """Get the trigger type."""
        ...

    @abstractmethod
    def should_execute(
        self,
        state: TriggerState,
        kline_data: dict[str, Any],
        current_time: datetime,
    ) -> tuple[bool, TriggerState]:
        """Determine if the strategy should execute.

        Args:
            state: Current trigger state.
            kline_data: Kline data from the notification.
            current_time: Current timestamp.

        Returns:
            Tuple of (should_execute, updated_state).
        """
        ...


class OnceOnlyTrigger(TriggerEngine):
    """Trigger that executes only once per configuration."""

    @property
    def trigger_type(self) -> TriggerType:
        return TriggerType.ONCE_ONLY

    def should_execute(
        self,
        state: TriggerState,
        kline_data: dict[str, Any],
        current_time: datetime,
    ) -> tuple[bool, TriggerState]:
        """Execute only if not executed before.

        Args:
            state: Current trigger state.
            kline_data: Kline data (not used).
            current_time: Current timestamp (not used).

        Returns:
            Tuple of (should_execute, updated_state).
        """
        if state.executed:
            return False, state

        # Mark as executed
        new_state = TriggerState(executed=True)
        return True, new_state


class EachKlineTrigger(TriggerEngine):
    """Trigger that executes on every kline update."""

    @property
    def trigger_type(self) -> TriggerType:
        return TriggerType.EACH_KLINE

    def should_execute(
        self,
        state: TriggerState,
        kline_data: dict[str, Any],
        current_time: datetime,
    ) -> tuple[bool, TriggerState]:
        """Execute on every kline update.

        Args:
            state: Current trigger state (not used).
            kline_data: Kline data (not used).
            current_time: Current timestamp (not used).

        Returns:
            Tuple of (should_execute, updated_state).
        """
        # Always execute on each kline
        return True, state


class EachKlineCloseTrigger(TriggerEngine):
    """Trigger that executes only when kline closes.

    Detects kline close by checking if the kline data indicates a closed kline.
    """

    @property
    def trigger_type(self) -> TriggerType:
        return TriggerType.EACH_KLINE_CLOSE

    def should_execute(
        self,
        state: TriggerState,
        kline_data: dict[str, Any],
        current_time: datetime,
    ) -> tuple[bool, TriggerState]:
        """Execute only when kline closes.

        Args:
            state: Current trigger state.
            kline_data: Kline data containing close time and is_closed flag.
                       Binance format: data.k.x = true/false
            current_time: Current timestamp (timezone-aware).

        Returns:
            Tuple of (should_execute, updated_state).
        """
        # Extract kline data - Binance uses "k" key for kline data
        kline = kline_data.get("k", {})

        # Check if kline is closed - Binance uses "x" field
        is_closed = kline.get("x", False)

        # Get close time from kline data
        kline_close_time = kline.get("T")  # Binance close timestamp in milliseconds

        # Check if this is a closed kline
        if is_closed:
            # Use close time as the unique identifier
            close_time_str = str(kline_close_time) if kline_close_time else None

            if close_time_str and state.last_kline_close_time == close_time_str:
                # Already processed this close
                return False, state

            # New closed kline
            new_state = TriggerState(last_kline_close_time=close_time_str)
            return True, new_state

        # If no is_closed flag, check if current time is past the kline close time
        if kline_close_time:
            try:
                # Parse close time (Binance uses milliseconds timestamp)
                if isinstance(kline_close_time, (int, float)):
                    # Make timezone-aware using UTC to match current_time's timezone
                    kline_close = datetime.fromtimestamp(kline_close_time / 1000, tz=current_time.tzinfo)
                else:
                    kline_close = datetime.fromisoformat(str(kline_close_time).replace("Z", "+00:00"))

                if current_time > kline_close:
                    # K-line has closed
                    close_time_str = str(kline_close_time)
                    if state.last_kline_close_time == close_time_str:
                        return False, state

                    new_state = TriggerState(last_kline_close_time=close_time_str)
                    return True, new_state
            except (ValueError, OSError):
                pass

        # Default: don't execute if we can't determine
        return False, state


class EachMinuteTrigger(TriggerEngine):
    """Trigger that executes once per minute.

    Uses a time window to ensure execution happens approximately once per minute.
    """

    WINDOW_SECONDS = 60  # 1 minute window

    @property
    def trigger_type(self) -> TriggerType:
        return TriggerType.EACH_MINUTE

    def should_execute(
        self,
        state: TriggerState,
        kline_data: dict[str, Any],
        current_time: datetime,
    ) -> tuple[bool, TriggerState]:
        """Execute once per minute.

        Args:
            state: Current trigger state.
            kline_data: Kline data (not used).
            current_time: Current timestamp.

        Returns:
            Tuple of (should_execute, updated_state).
        """
        if state.last_executed_at is None:
            # First execution
            new_state = TriggerState(last_executed_at=current_time)
            return True, new_state

        # Check if enough time has passed
        elapsed = (current_time - state.last_executed_at).total_seconds()
        if elapsed >= self.WINDOW_SECONDS:
            new_state = TriggerState(last_executed_at=current_time)
            return True, new_state

        return False, state


# Registry of trigger engines by type
TRIGGER_ENGINES: dict[TriggerType, TriggerEngine] = {
    TriggerType.ONCE_ONLY: OnceOnlyTrigger(),
    TriggerType.EACH_KLINE: EachKlineTrigger(),
    TriggerType.EACH_KLINE_CLOSE: EachKlineCloseTrigger(),
    TriggerType.EACH_MINUTE: EachMinuteTrigger(),
}


def get_trigger_engine(trigger_type: str | TriggerType) -> TriggerEngine:
    """Get trigger engine by type.

    Args:
        trigger_type: Trigger type string or enum.

    Returns:
        TriggerEngine instance.

    Raises:
        ValueError: If trigger type is unknown.
    """
    if isinstance(trigger_type, str):
        try:
            trigger_type = TriggerType(trigger_type)
        except ValueError:
            raise ValueError(f"Unknown trigger type: {trigger_type}")

    engine = TRIGGER_ENGINES.get(trigger_type)
    if engine is None:
        raise ValueError(f"No engine for trigger type: {trigger_type}")

    return engine


def create_trigger_state(trigger_type: str | TriggerType) -> TriggerState:
    """Create initial trigger state for a trigger type.

    Args:
        trigger_type: Trigger type.

    Returns:
        Initial TriggerState.
    """
    return TriggerState()
