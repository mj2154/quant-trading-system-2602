#!/usr/bin/env python3
"""
详细WebSocket测试 - 诊断消息接收问题
"""

import asyncio
import json
import time
import websockets

WS_URL = "ws://localhost:8000/ws"

async def test():
    print(f"[{time.strftime('%H:%M:%S')}] 连接 {WS_URL}...")

    async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=60) as ws:
        print(f"[{time.strftime('%H:%M:%S')}] ✅ 连接成功")

        # 发送请求（1分钟K线会触发异步任务）
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
            "requestId": f"test_{int(time.time() * 1000)}",
            "timestamp": int(time.time() * 1000),
        }

        print(f"[{time.strftime('%H:%M:%S')}] 📤 发送请求")
        await ws.send(json.dumps(request))

        # 连续接收所有消息
        print(f"[{time.strftime('%H:%M:%S')}] ⏳ 开始接收消息...")
        start = time.time()

        for i in range(20):
            elapsed = time.time() - start
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=8)
                data = json.loads(msg)

                print(f"\n[{time.strftime('%H:%M:%S')}] 消息 {i+1} (耗时: {elapsed:.2f}s)")
                print(f"  action: {data.get('action')}")

                if data.get('action') == 'ack':
                    task_id = data.get('data', {}).get('taskId')
                    print(f"  taskId: {task_id}")
                elif data.get('action') == 'success':
                    data_obj = data.get('data', {})
                    print(f"  data.type: {data_obj.get('type') if data_obj else None}")
                    print(f"  count: {data_obj.get('count') if data_obj else None}")
                    break
                else:
                    print(f"  原始消息: {msg[:200]}...")

            except asyncio.TimeoutError:
                print(f"[{time.strftime('%H:%M:%S')}] 消息 {i+1} 超时 (已等待 {elapsed:.2f}s)")
                break

        print(f"\n[{time.strftime('%H:%M:%S')}] 测试完成")

if __name__ == "__main__":
    asyncio.run(test())
