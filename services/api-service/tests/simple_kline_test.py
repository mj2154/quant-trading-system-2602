#!/usr/bin/env python3
"""
K线获取测试 - 调试版
"""

import asyncio
import json
import time
import websockets

WS_URL = "ws://localhost:8000/ws/market"

async def test_klines():
    start = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] 连接 {WS_URL}...")

    try:
        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=60) as ws:
            print(f"[{time.strftime('%H:%M:%S')}] ✅ 连接成功")

            request = {
                "protocolVersion": "2.0",
                "action": "get",
                "data": {
                    "type": "klines",
                    "symbol": "BINANCE:BTCUSDT",
                    "resolution": "60",
                    "from_time": int(time.time() * 1000) - 24 * 60 * 60 * 1000,
                    "to_time": int(time.time() * 1000),
                },
                "requestId": f"test_{int(time.time() * 1000)}",
                "timestamp": int(time.time() * 1000),
            }

            print(f"[{time.strftime('%H:%M:%S')}] 📤 发送请求")
            await ws.send(json.dumps(request))

            # 连续接收消息
            for i in range(5):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=15)
                    elapsed = time.time() - start
                    data = json.loads(msg)

                    print(f"\n[{time.strftime('%H:%M:%S')}] --- 消息 {i+1} (耗时: {elapsed:.2f}s) ---")
                    print(json.dumps(data, indent=2))

                except asyncio.TimeoutError:
                    print(f"[{time.strftime('%H:%M:%S')}] 消息 {i+1} 超时")
                    break

    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ❌ 错误: {e}")

if __name__ == "__main__":
    asyncio.run(test_klines())
