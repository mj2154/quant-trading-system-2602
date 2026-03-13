#!/usr/bin/env python3
"""
测试quotes数据格式
"""

import asyncio
import json
import time
import websockets

WS_URL = "ws://localhost:8000/ws"

async def test():
    print(f"[{time.strftime('%H:%M:%S')}] 连接...")
    async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=60) as ws:
        print(f"[{time.strftime('%H:%M:%S')}] ✅ 连接成功")

        # 发送quotes请求
        req = {
            "protocolVersion": "2.0", "action": "get",
            "data": {"type": "quotes", "symbols": ["BINANCE:BTCUSDT"]},
            "requestId": "test_quotes", "timestamp": int(time.time() * 1000)
        }
        print(f"[{time.strftime('%H:%M:%S')}] 📤 发送请求")
        await ws.send(json.dumps(req))

        # 接收响应
        for i in range(5):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(msg)
                print(f"\n--- 消息 {i+1} ---")
                print(json.dumps(data, indent=2))

                if data.get("action") == "success":
                    print(f"\ndata.type: {data.get('data', {}).get('type')}")
                    print(f"data.result: {data.get('data', {}).get('result')}")
                    break
            except asyncio.TimeoutError:
                print("超时")
                break

if __name__ == "__main__":
    asyncio.run(test())
