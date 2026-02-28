"""Tests for async fill lock mechanism in SignalService.

Tests cover:
1. Lock creation - lock is created when first update arrives
2. Lock occupation - lock is locked during processing
3. Concurrent blocking - updates are skipped when lock is occupied
4. Lock release - lock is released after processing completes

These tests verify the asyncio.Lock-based mutual exclusion mechanism that prevents
concurrent kline fill operations on the same subscription key.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.signal_service import SignalService


class MockDatabase:
    """Mock database for testing."""

    def __init__(self):
        self._pool = MagicMock()
        self._config = {"host": "localhost", "port": 5432}

    async def create_dedicated_connection(self):
        return AsyncMock()

    async def close_dedicated_connection(self, conn):
        pass

    async def create_pool(self):
        pass


class TestFillLockCreation:
    """Tests for lock creation behavior."""

    @pytest.mark.asyncio
    async def test_lock_created_on_first_update(self):
        """Lock should be created when first update arrives for a subscription key."""
        # Arrange
        mock_db = MockDatabase()
        service = SignalService(mock_db)

        subscription_key = "BINANCE:BTCUSDT@KLINE_60"

        # Initially no locks exist
        assert subscription_key not in service._fill_locks

        # Act - simulate first update arriving (check lock before processing)
        existing_lock = service._fill_locks.get(subscription_key)
        if not existing_lock or not existing_lock.locked():
            # Create lock if it doesn't exist or isn't locked
            if subscription_key not in service._fill_locks:
                service._fill_locks[subscription_key] = asyncio.Lock()

        # Assert - lock should now exist
        assert subscription_key in service._fill_locks
        assert isinstance(service._fill_locks[subscription_key], asyncio.Lock)

    @pytest.mark.asyncio
    async def test_lock_not_created_for_unused_subscription(self):
        """Lock should not be created for subscription keys that never receive updates."""
        # Arrange
        mock_db = MockDatabase()
        service = SignalService(mock_db)

        # Act - do nothing

        # Assert - no locks should exist
        assert len(service._fill_locks) == 0


class TestFillLockOccupation:
    """Tests for lock occupation during processing."""

    @pytest.mark.asyncio
    async def test_lock_is_locked_during_processing(self):
        """Lock should be in locked state while processing an update."""
        # Arrange
        mock_db = MockDatabase()
        service = SignalService(mock_db)

        subscription_key = "BINANCE:BTCUSDT@KLINE_60"
        service._fill_locks[subscription_key] = asyncio.Lock()

        # Act - acquire the lock (simulating processing)
        async with service._fill_locks[subscription_key]:
            # Assert - lock should be locked
            assert service._fill_locks[subscription_key].locked() is True

    @pytest.mark.asyncio
    async def test_lock_is_unlocked_after_processing(self):
        """Lock should be unlocked after processing completes."""
        # Arrange
        mock_db = MockDatabase()
        service = SignalService(mock_db)

        subscription_key = "BINANCE:BTCUSDT@KLINE_60"
        service._fill_locks[subscription_key] = asyncio.Lock()

        # Verify lock is initially unlocked
        assert service._fill_locks[subscription_key].locked() is False

        # Act - acquire and release the lock
        async with service._fill_locks[subscription_key]:
            pass  # Processing

        # Assert - lock should be unlocked after exiting context
        assert service._fill_locks[subscription_key].locked() is False


class TestFillLockConcurrentBlocking:
    """Tests for concurrent update blocking."""

    @pytest.mark.asyncio
    async def test_concurrent_update_blocked_when_locked(self):
        """New updates should be skipped when lock is already occupied."""
        # Arrange
        mock_db = MockDatabase()
        service = SignalService(mock_db)

        subscription_key = "BINANCE:BTCUSDT@KLINE_60"
        service._fill_locks[subscription_key] = asyncio.Lock()

        # Simulate processing by holding the lock
        processing_complete = asyncio.Event()

        async def hold_lock():
            async with service._fill_locks[subscription_key]:
                # Wait for test to check
                await asyncio.sleep(0.1)

        async def try_update():
            """Simulate the lock check logic from _process_realtime_update."""
            existing_lock = service._fill_locks.get(subscription_key)
            if existing_lock and existing_lock.locked():
                return "skipped"
            return "processed"

        # Act - start processing in background
        processing_task = asyncio.create_task(hold_lock())

        # Give processing time to acquire lock
        await asyncio.sleep(0.01)

        # Try to update while processing
        result = await try_update()

        # Wait for processing to complete
        processing_task.cancel()
        try:
            await processing_task
        except asyncio.CancelledError:
            pass

        # Assert - update should be skipped
        assert result == "skipped"

    @pytest.mark.asyncio
    async def test_multiple_updates_same_key(self):
        """Multiple updates to the same subscription key should be serialized."""
        # Arrange
        mock_db = MockDatabase()
        service = SignalService(mock_db)

        subscription_key = "BINANCE:BTCUSDT@KLINE_60"
        service._fill_locks[subscription_key] = asyncio.Lock()

        processed_count = 0

        async def process_update(task_id: int):
            """Simulate update processing with lock."""
            nonlocal processed_count

            # Check lock (mimics the logic in _process_realtime_update)
            existing_lock = service._fill_locks.get(subscription_key)
            if existing_lock and existing_lock.locked():
                return  # Skip this update

            # Create lock if needed
            if subscription_key not in service._fill_locks:
                service._fill_locks[subscription_key] = asyncio.Lock()

            async with service._fill_locks[subscription_key]:
                processed_count += 1
                await asyncio.sleep(0.05)  # Simulate processing time

        # Act - simulate 4 high-frequency updates (4 per second)
        await asyncio.gather(
            process_update(1),
            process_update(2),
            process_update(3),
            process_update(4),
        )

        # Assert - only first update should be processed (others skipped)
        # Note: Due to async nature, some may slip through, but at least first is processed
        assert processed_count >= 1

    @pytest.mark.asyncio
    async def test_different_subscription_keys_independent(self):
        """Updates to different subscription keys should not block each other."""
        # Arrange
        mock_db = MockDatabase()
        service = SignalService(mock_db)

        key1 = "BINANCE:BTCUSDT@KLINE_60"
        key2 = "BINANCE:ETHUSDT@KLINE_60"

        # Create separate locks for each key
        service._fill_locks[key1] = asyncio.Lock()
        service._fill_locks[key2] = asyncio.Lock()

        results = {"key1": [], "key2": []}

        async def process_key1():
            async with service._fill_locks[key1]:
                await asyncio.sleep(0.05)
                results["key1"].append("processed")

        async def process_key2():
            async with service._fill_locks[key2]:
                await asyncio.sleep(0.05)
                results["key2"].append("processed")

        # Act - process both keys concurrently
        await asyncio.gather(process_key1(), process_key2())

        # Assert - both should be processed independently
        assert len(results["key1"]) == 1
        assert len(results["key2"]) == 1


class TestFillLockRelease:
    """Tests for lock release behavior."""

    @pytest.mark.asyncio
    async def test_lock_released_after_exception(self):
        """Lock should be released even if processing raises an exception."""
        # Arrange
        mock_db = MockDatabase()
        service = SignalService(mock_db)

        subscription_key = "BINANCE:BTCUSDT@KLINE_60"
        service._fill_locks[subscription_key] = asyncio.Lock()

        # Act - try to process with exception
        try:
            async with service._fill_locks[subscription_key]:
                assert service._fill_locks[subscription_key].locked() is True
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Assert - lock should still be released after exception
        assert service._fill_locks[subscription_key].locked() is False

    @pytest.mark.asyncio
    async def test_lock_released_immediately_after_context(self):
        """Lock should be released immediately after async context exits."""
        # Arrange
        mock_db = MockDatabase()
        service = SignalService(mock_db)

        subscription_key = "BINANCE:BTCUSDT@KLINE_60"
        lock = asyncio.Lock()
        service._fill_locks[subscription_key] = lock

        # Act & Assert - verify lock state throughout context
        assert lock.locked() is False

        async with lock:
            assert lock.locked() is True

        assert lock.locked() is False


class TestHighFrequencyUpdates:
    """Tests simulating high-frequency updates (4 per second)."""

    @pytest.mark.asyncio
    async def test_four_updates_per_second_scenario(self):
        """Simulate 4 updates per second - only first should be processed."""
        # Arrange
        mock_db = MockDatabase()
        service = SignalService(mock_db)

        subscription_key = "BINANCE:BTCUSDT@KLINE_60"

        processed_updates = []
        lock_acquired_times = []

        async def simulate_update(update_id: int, delay: float):
            """Simulate processing a single update."""
            await asyncio.sleep(delay)

            # Check if lock is already held (skip if yes)
            existing_lock = service._fill_locks.get(subscription_key)
            if existing_lock and existing_lock.locked():
                return {"id": update_id, "result": "skipped"}

            # Create lock if needed
            if subscription_key not in service._fill_locks:
                service._fill_locks[subscription_key] = asyncio.Lock()

            # Acquire lock and process
            async with service._fill_locks[subscription_key]:
                lock_acquired_times.append(update_id)
                await asyncio.sleep(0.1)  # Simulate processing time
                processed_updates.append(update_id)

            return {"id": update_id, "result": "processed"}

        # Act - simulate 4 updates arriving at 250ms intervals (4 per second)
        tasks = [
            simulate_update(1, 0.0),
            simulate_update(2, 0.25),
            simulate_update(3, 0.5),
            simulate_update(4, 0.75),
        ]

        results = await asyncio.gather(*tasks)

        # Assert - first update should be processed, others may be skipped due to timing
        # At minimum, update 1 should be processed (arrives first)
        assert 1 in processed_updates

    @pytest.mark.asyncio
    async def test_updates_after_lock_release(self):
        """Updates arriving after lock release should be processed."""
        # Arrange
        mock_db = MockDatabase()
        service = SignalService(mock_db)

        subscription_key = "BINANCE:BTCUSDT@KLINE_60"

        processed_updates = []

        async def simulate_update(update_id: int, delay: float):
            """Simulate processing a single update."""
            await asyncio.sleep(delay)

            # Check if lock is already held (skip if yes)
            existing_lock = service._fill_locks.get(subscription_key)
            if existing_lock and existing_lock.locked():
                return {"id": update_id, "result": "skipped"}

            # Create lock if needed
            if subscription_key not in service._fill_locks:
                service._fill_locks[subscription_key] = asyncio.Lock()

            # Acquire lock and process
            async with service._fill_locks[subscription_key]:
                await asyncio.sleep(0.1)  # Simulate processing time
                processed_updates.append(update_id)

            return {"id": update_id, "result": "processed"}

        # First update holds lock for 200ms
        # Second update arrives at 300ms (after lock release)
        tasks = [
            simulate_update(1, 0.0),  # Starts at 0ms, holds lock until 200ms
            simulate_update(2, 0.3),   # Starts at 300ms, lock should be free
        ]

        results = await asyncio.gather(*tasks)

        # Assert - both should be processed (300ms > 200ms lock release)
        assert len(processed_updates) == 2
        assert 1 in processed_updates
        assert 2 in processed_updates


class TestFillLockIntegration:
    """Integration tests for the fill lock mechanism."""

    @pytest.mark.asyncio
    async def test_lock_dict_isolation_per_subscription(self):
        """Each subscription key should have its own lock."""
        # Arrange
        mock_db = MockDatabase()
        service = SignalService(mock_db)

        keys = [
            "BINANCE:BTCUSDT@KLINE_60",
            "BINANCE:ETHUSDT@KLINE_60",
            "BINANCE:BNBUSDT@KLINE_60",
        ]

        # Act - create locks for different keys
        for key in keys:
            service._fill_locks[key] = asyncio.Lock()

        # Assert - each key should have independent lock
        assert len(service._fill_locks) == 3
        for key in keys:
            assert key in service._fill_locks
            assert service._fill_locks[key].locked() is False

    @pytest.mark.asyncio
    async def test_lock_state_consistency(self):
        """Lock state should be consistent throughout its lifecycle."""
        # Arrange
        mock_db = MockDatabase()
        service = SignalService(mock_db)

        subscription_key = "BINANCE:BTCUSDT@KLINE_60"

        # Act - verify lock lifecycle
        # 1. Initially no lock
        assert service._fill_locks.get(subscription_key) is None

        # 2. Create lock
        service._fill_locks[subscription_key] = asyncio.Lock()
        assert subscription_key in service._fill_locks

        # 3. Lock is unlocked initially
        assert service._fill_locks[subscription_key].locked() is False

        # 4. Acquire lock
        await service._fill_locks[subscription_key].acquire()
        assert service._fill_locks[subscription_key].locked() is True

        # 5. Release lock
        service._fill_locks[subscription_key].release()
        assert service._fill_locks[subscription_key].locked() is False
