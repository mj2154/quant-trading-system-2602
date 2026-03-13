#!/usr/bin/env python3
"""
检查推送消息的原始格式
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

        request = {
            "protocolVersion": "2.0",
            "action": "get",
            "data": {
                "type": "klines",
                "symbol": "BINANCE:BTCUSDT",
                "resolution": "1",
                "from_time": int(time.time() * 1000) - 60 * 60 * 1000,
                "to_time": int(time.time() * 1000),
            },
            "requestId": "test_request_123",
            "timestamp": int(time.time() * 1000),
        }

        print(f"[{time.strftime('%H:%M:%S')}] 📤 发送请求")
        await ws.send(json.dumps(request))

        # 接收并打印原始消息
        for i in range(5):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(msg)

                print(f"\n--- 消息 {i+1} 原始内容 ---")
                print(msg)
                print(f"\n--- 字段分析 ---")
                print(f"keys: {list(data.keys())}")
                print(f"taskId in root: {data.get('taskId')}")
                print(f"data.keys: {list(data.get('data', {}).keys()) if data.get('data') else None}")
                print(f"data.taskId: {data.get('data', {}).get('taskId')}")

                if data.get('action') == 'success' and data.get('data', {}).get('type') == 'klines':
                    break

            except asyncio.TimeoutError:
                print(f"[{time.strftime('%H:%M:%S')}] 超时")
                break

if __name__ == "__main__":
    asyncio.run(test())
