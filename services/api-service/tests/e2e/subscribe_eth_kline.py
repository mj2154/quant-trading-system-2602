"""
ETHUSDT 1分钟K线实时订阅脚本

用途：持续订阅并打印 ETHUSDT 的1分钟K线数据，直到程序被关闭
运行方式：uv run python services/api-service/tests/e2e/subscribe_eth_kline.py
"""

import asyncio
import json
import signal
import sys
import time
import uuid
from datetime import datetime

import websockets


class EthKlineSubscriber:
    """ETHUSDT K线订阅客户端"""

    def __init__(self, uri: str = "ws://localhost:8000/ws"):
        self.uri = uri
        self.websocket = None
        self.running = False

    def _generate_request_id(self) -> str:
        return uuid.uuid4().hex

    async def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            self.websocket = await websockets.connect(
                self.uri,
                ping_interval=20,
                ping_timeout=60,
            )
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 已连接到 {self.uri}")
            return True
        except Exception as e:
            print(f"[错误] 连接失败: {e}")
            return False

    async def disconnect(self) -> None:
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 已断开连接")

    async def send_message(self, message: dict) -> None:
        """发送消息"""
        if not self.websocket:
            raise ConnectionError("WebSocket 未连接")

        message["requestId"] = self._generate_request_id()
        message["timestamp"] = int(time.time() * 1000)
        message["protocolVersion"] = "2.0"

        await self.websocket.send(json.dumps(message, separators=(",", ":")))

    async def recv_message(self, timeout: float = 10.0):
        """接收消息"""
        try:
            message = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            return json.loads(message)
        except asyncio.TimeoutError:
            return None

    async def subscribe_kline(self, subscription: str) -> dict:
        """订阅K线数据"""
        message = {
            "type": "SUBSCRIBE",
            "data": {"subscriptions": [subscription]},
        }

        await self.send_message(message)

        # 等待 ACK 响应
        ack = await self.recv_message(timeout=10)
        if not ack:
            raise RuntimeError("未收到 ACK 响应")

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 收到 ACK: {ack.get('type')}")

        # 等待 SUCCESS 响应
        success = await self.recv_message(timeout=30)
        if not success:
            raise RuntimeError("未收到 SUCCESS 响应")

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 收到 SUCCESS: {success.get('type')}")

        if success.get("data", {}).get("status") == "success":
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 订阅成功: {subscription}")
        else:
            print(f"[警告] 订阅可能失败: {success}")

        return success

    async def listen_realtime(self):
        """持续监听实时K线数据"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始监听实时数据... (按 Ctrl+C 退出)")
        print("-" * 80)

        while self.running:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
                message_dict = json.loads(message)

                # 处理 UPDATE 类型消息
                # 注意：根据协议，subscriptionKey 和 content 在顶层，不在 data 里
                if message_dict.get("type") == "UPDATE":
                    print(f"[DEBUG] 收到的完整消息: {message_dict}")
                    content = message_dict.get("content", {})
                    subscription_key = message_dict.get("subscriptionKey", "")

                    # 格式化输出
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] UPDATE - {subscription_key}")

                    # 打印K线数据
                    if content:
                        kline = content
                        print(f"  时间: {kline.get('time')}")
                        print(f"  开盘: {kline.get('open')}")
                        print(f"  最高: {kline.get('high')}")
                        print(f"  最低: {kline.get('low')}")
                        print(f"  收盘: {kline.get('close')}")
                        print(f"  成交量: {kline.get('volume')}")
                        print("-" * 80)

                # 处理其他类型消息
                elif message_dict.get("type"):
                    msg_type = message_dict.get("type")
                    if msg_type not in ["PING", "PONG"]:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 收到消息: {msg_type}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if self.running:
                    print(f"[错误] 接收消息失败: {e}")
                break

    async def run(self):
        """运行订阅"""
        # 连接到WebSocket
        if not await self.connect():
            return

        # 订阅 ETHUSDT 1分钟K线 (现货)
        # 期货使用: "BINANCE:ETHUSDT.PERP@KLINE_1"
        subscription = "BINANCE:ETHUSDT@KLINE_1"

        try:
            await self.subscribe_kline(subscription)

            # 设置运行标志
            self.running = True

            # 开始监听实时数据
            await self.listen_realtime()

        except KeyboardInterrupt:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 收到退出信号")
        except Exception as e:
            print(f"[错误] {e}")
        finally:
            self.running = False
            await self.disconnect()


async def main():
    """主函数"""
    subscriber = EthKlineSubscriber()

    # 设置信号处理，支持 Ctrl+C 优雅退出
    loop = asyncio.get_event_loop()

    def signal_handler():
        print("\n正在关闭...")
        subscriber.running = False

    # 注册信号处理器
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # 运行订阅
    await subscriber.run()


if __name__ == "__main__":
    print("=" * 80)
    print("ETHUSDT 1分钟K线实时订阅")
    print("订阅地址: ws://localhost:8000/ws")
    print("交易对: BINANCE:ETHUSDT@KLINE_1")
    print("按 Ctrl+C 退出")
    print("=" * 80)

    asyncio.run(main())
