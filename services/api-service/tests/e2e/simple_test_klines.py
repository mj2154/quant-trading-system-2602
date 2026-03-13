#!/usr/bin/env python3
"""
简单测试：验证是否能收到后端推送的klines数据
"""

import asyncio
import json
import websockets
import time

WS_URL = "ws://localhost:8000/ws"

async def test():
    print(f"[{time.strftime('%H:%M:%S')}] 连接到 {WS_URL}...")
    async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=60) as ws:
        print(f"[{time.strftime('%H:%M:%S')}] ✅ 连接成功")

        # 发送1分钟K线请求
        end_time = int(time.time() * 1000)
        start_time = end_time - (60 * 60 * 1000)  # 1小时

        req = {
            "protocolVersion": "2.0",
            "action": "get",
            "data": {
                "type": "klines",
                "symbol": "BINANCE:BTCUSDT",
                "interval": "1",
                "from_time": start_time,
                "to_time": end_time
            },
            "requestId": f"test_simple_{int(time.time() * 1000)}",
            "timestamp": int(time.time() * 1000)
        }

        print(f"[{time.strftime('%H:%M:%S')}] 📤 发送请求: interval=1")
        await ws.send(json.dumps(req))

        # 等待并接收所有消息
        messages_received = []
        start_wait = time.time()

        while time.time() - start_wait < 35:  # 最多等待35秒
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                messages_received.append(data)
                print(f"\n[{time.strftime('%H:%M:%S')}] 📥 收到消息 #{len(messages_received)}:")
                print(json.dumps(data, indent=2)[:500])

                # 如果收到success且有klines数据，说明成功了
                # v2.1规范：type 在 data 内部
                if data.get("action") == "success":
                    data_content = data.get("data", {})
                    msg_type = data_content.get("type")
                    if msg_type == "klines":
                        count = data_content.get("count", 0)
                        print(f"\n✅ 成功收到 {count} 条klines数据！")
                        return True

            except asyncio.TimeoutError:
                elapsed = int(time.time() - start_wait)
                print(f"[{time.strftime('%H:%M:%S')}] ⏳ 等待中... ({elapsed}秒)")
                continue

        print(f"\n❌ 超时，共收到 {len(messages_received)} 条消息")
        return False

if __name__ == "__main__":
    success = asyncio.run(test())
    exit(0 if success else 1)
