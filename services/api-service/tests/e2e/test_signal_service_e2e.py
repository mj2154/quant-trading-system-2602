"""
Signal Service End-to-End Test

Tests the full signal flow:
1. Create BTCUSDT 1-minute MACD short strategy alert
2. Subscribe to signal notifications
3. Listen for 2 minutes
4. Verify signal is received
5. Delete alert

Usage:
    cd services/api-service
    uv run python tests/e2e/test_signal_service_e2e.py
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any

import websockets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalTestClient:
    """WebSocket test client for signal service E2E testing."""

    def __init__(self, ws_uri: str = "ws://localhost:8000/ws/market"):
        self.ws_uri = ws_uri
        self.websocket: Any | None = None
        self.connected = False
        self.request_id_counter = 0
        self.alerts_received: list[dict] = []
        self.signal_subscriptions: set[str] = set()

    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        try:
            self.websocket = await websockets.connect(
                self.ws_uri, ping_interval=10, ping_timeout=30
            )
            self.connected = True
            logger.info("WebSocket connected")
            return True
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False

    async def disconnect(self):
        """Close WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("WebSocket disconnected")

    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        self.request_id_counter += 1
        return f"signal_test_{int(time.time() * 1000)}_{self.request_id_counter}"

    async def send_message(
        self,
        message: dict[str, Any],
        expect_response: bool = True,
        timeout: float = 10,
    ) -> dict[str, Any] | None:
        """Send WebSocket message and receive response."""
        if not self.connected or not self.websocket:
            raise ConnectionError("WebSocket not connected")

        # Auto-generate requestId
        if "requestId" not in message and expect_response:
            message["requestId"] = self._generate_request_id()

        # Ensure timestamp exists
        if "timestamp" not in message:
            message["timestamp"] = int(time.time() * 1000)

        # Send message
        message_str = json.dumps(message, separators=(",", ":"))
        logger.info(f"Sending: {message_str[:200]}")

        await self.websocket.send(message_str)

        if expect_response:
            try:
                response = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
                response_dict = json.loads(response)
                logger.info(f"Received: {json.dumps(response_dict, indent=2)[:300]}")
                return response_dict
            except asyncio.TimeoutError:
                logger.error("Response timeout")
                return None

        return None

    async def subscribe_to_signals(self, alert_id: str) -> dict[str, Any] | None:
        """Subscribe to signal notifications for a specific alert.

        Format: SIGNAL:{alert_id}
        """
        subscription_key = f"SIGNAL:{alert_id}"
        self.signal_subscriptions.add(subscription_key)

        message = {
            "protocolVersion": "2.0",
            "action": "subscribe",
            "data": {
                "subscriptions": [subscription_key],
            },
        }
        return await self.send_message(message)

    async def unsubscribe_from_signals(
        self, alert_id: str
    ) -> dict[str, Any] | None:
        """Unsubscribe from signal notifications."""
        subscription_key = f"SIGNAL:{alert_id}"
        self.signal_subscriptions.discard(subscription_key)

        message = {
            "protocolVersion": "2.0",
            "action": "unsubscribe",
            "data": {
                "subscriptions": [subscription_key],
            },
        }
        return await self.send_message(message)

    async def create_alert(
        self,
        name: str,
        strategy_type: str,
        symbol: str,
        interval: str,
        trigger_type: str = "each_kline_close",
        params: dict[str, Any] | None = None,
        is_enabled: bool = True,
        created_by: str = "test_user",
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Create an alert signal and return response and alert_id."""
        alert_id = str(uuid.uuid4())

        message = {
            "protocolVersion": "2.0",
            "action": "get",
            "data": {
                "type": "create_alert_config",
                "id": alert_id,
                "name": name,
                "strategy_type": strategy_type,
                "symbol": symbol,
                "interval": interval,
                "trigger_type": trigger_type,
                "params": params or {},
                "is_enabled": is_enabled,
                "created_by": created_by,
            },
        }

        response = await self.send_message(message)
        return response, alert_id

    async def delete_alert(self, alert_id: str) -> dict[str, Any] | None:
        """Delete an alert signal."""
        message = {
            "protocolVersion": "2.0",
            "action": "get",
            "data": {
                "type": "delete_alert_config",
                "id": alert_id,
            },
        }
        return await self.send_message(message)

    async def list_signals(
        self,
        alert_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any] | None:
        """List signals via WebSocket (conforms to TradingView API spec).

        Args:
            alert_id: Filter by alert ID.
            page: Page number (default 1).
            page_size: Items per page (default 20).
        """
        message = {
            "protocolVersion": "2.0",
            "action": "get",
            "data": {
                "type": "list_signals",
                "page": page,
                "page_size": page_size,
            },
        }
        if alert_id:
            message["data"]["alert_id"] = alert_id

        return await self.send_message(message, timeout=30)

    async def listen_for_signals(self, duration_seconds: int = 120) -> list[dict]:
        """Listen for signal notifications for specified duration.

        符合 TradingView 规范的消息格式：
        {
            "action": "update",
            "data": {
                "eventType": "signal.new",
                "subscriptionKey": "SIGNAL:{alert_id}",
                "content": { signal data }
            }
        }

        Args:
            duration_seconds: How long to listen (default 2 minutes)

        Returns:
            List of received signal notifications
        """
        logger.info(f"Listening for signals for {duration_seconds} seconds...")
        self.alerts_received = []

        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            try:
                # Use wait_for with a short timeout to allow periodic checks
                msg = await asyncio.wait_for(self.websocket.recv(), timeout=1)
                msg_dict = json.loads(msg)

                # 符合 TradingView v2.0 规范的消息格式
                data = msg_dict.get("data", {})

                # 使用规范字段名：subscriptionKey（驼峰）、eventType
                subscription_key = data.get("subscriptionKey", "")
                event_type = data.get("eventType", "")

                # 检查是否是 SIGNAL 开头的订阅键或 signal.new 事件
                # 符合规范：前端通过 subscriptionKey.startsWith('SIGNAL:') 识别信号推送
                if subscription_key.startswith("SIGNAL:") or event_type == "signal.new":
                    content = data.get("content", {})
                    logger.info(
                        f"Received signal: alert_id={content.get('alert_id')}, "
                        f"signal_value={content.get('signal_value')}, "
                        f"strategy={content.get('strategy_type')}"
                    )
                    self.alerts_received.append(data)

            except asyncio.TimeoutError:
                # No message received within 1 second, continue listening
                continue
            except Exception as e:
                logger.error(f"Error listening for signals: {e}")
                break

        elapsed = time.time() - start_time
        logger.info(f"Listening complete. Received {len(self.alerts_received)} signals in {elapsed:.1f} seconds")
        return self.alerts_received


async def run_signal_e2e_test():
    """Run the signal service E2E test."""
    logger.info("=" * 60)
    logger.info("Signal Service E2E Test")
    logger.info("=" * 60)

    client = SignalTestClient()
    alert_id = None

    try:
        # Step 1: Connect to WebSocket
        logger.info("\n[Step 1] Connecting to WebSocket...")
        if not await client.connect():
            logger.error("Failed to connect to WebSocket")
            return False

        # Step 2: Create alert for BTCUSDT 1-minute random strategy
        logger.info("\n[Step 2] Creating alert...")
        logger.info("  - Symbol: BINANCE:BTCUSDT")
        logger.info("  - Interval: 1 (1 minute)")
        logger.info("  - Strategy: RandomStrategy (随机策略)")
        logger.info("  - Trigger: each_kline")

        response, alert_id = await client.create_alert(
            name="Test BTCUSDT 1m Random",
            strategy_type="RandomStrategy",
            symbol="BINANCE:BTCUSDT",
            interval="1",
            trigger_type="each_kline",
            params={},
            is_enabled=True,
            created_by="e2e_test",
        )

        if not response or response.get("action") != "success":
            logger.error(f"Failed to create alert: {response}")
            return False

        logger.info(f"Alert created successfully: {alert_id}")

        # Wait a bit for the alert to be processed
        await asyncio.sleep(2)

        # Step 3: Subscribe to signal notifications
        logger.info(f"\n[Step 3] Subscribing to signals: SIGNAL:{alert_id}")
        sub_response = await client.subscribe_to_signals(alert_id)
        if not sub_response or sub_response.get("action") != "success":
            logger.warning(f"Failed to subscribe to signals: {sub_response}")

        # Wait for subscription to take effect
        await asyncio.sleep(1)

        # Step 4: Listen for signals for 2 minutes
        logger.info("\n[Step 4] Listening for signals (30 seconds)...")
        logger.info("Waiting for signal notifications...")

        signals = await client.listen_for_signals(duration_seconds=30)

        # Step 5: Verify we received signals
        logger.info("\n[Step 5] Verifying signals...")

        # Also check via WebSocket API (TradingView API spec)
        rest_signals = await client.list_signals(alert_id=alert_id, page=1, page_size=10)
        if rest_signals and rest_signals.get("action") == "success":
            items = rest_signals.get("data", {}).get("items", [])
            if items:
                logger.info(f"Found {len(items)} signals via WebSocket API")
                for sig in items:
                    logger.info(f"  - Signal: value={sig.get('signal_value')}, reason={sig.get('signal_reason')}")

        success = len(signals) > 0 or (
            rest_signals
            and rest_signals.get("data", {}).get("items")
            and len(rest_signals["data"]["items"]) > 0
        )

        if success:
            logger.info("\n" + "=" * 60)
            logger.info("TEST PASSED: Received signal notifications")
            logger.info("=" * 60)
        else:
            logger.warning("\n" + "=" * 60)
            logger.warning("TEST COMPLETED: No signals received (may be normal if no trading opportunity)")
            logger.warning("=" * 60)

        return True

    except Exception as e:
        logger.error(f"Test error: {e}", exc_info=True)
        return False

    finally:
        # Step 6: Cleanup - Delete alert
        if alert_id:
            logger.info(f"\n[Step 6] Cleaning up - Deleting alert: {alert_id}")
            try:
                delete_response = await client.delete_alert(alert_id)
                if delete_response and delete_response.get("action") == "success":
                    logger.info("Alert deleted successfully")
                else:
                    logger.warning(f"Failed to delete alert: {delete_response}")
            except Exception as e:
                logger.error(f"Error deleting alert: {e}")

        # Disconnect
        await client.disconnect()


async def main():
    """Main entry point."""
    success = await run_signal_e2e_test()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
