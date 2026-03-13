#!/usr/bin/env python3
"""
测试 - 捕获服务端推送的完整消息格式
"""

import asyncio
import json
import time
import websockets

WS_URL = "ws://localhost:8000/ws"

async def test_klines():
    print(f"[{time.strftime('%H:%M:%S')}] 连接 {WS_URL}...")

    try:
        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=60) as ws:
            print(f"[{time.strftime('%H:%M:%S')}] ✅ 连接成功")

            # 创建一个新连接，发送请求后连续接收
            request = {
                "protocolVersion": "2.0",
                "action": "get",
                "data": {
                    "type": "klines",
                    "symbol": "BINANCE:BTCUSDT",
                    "resolution": "1",  # 1分钟K线，会触发异步任务
                    "from_time": int(time.time() * 1000) - 60 * 60 * 1000,  # 最近1小时
                    "to_time": int(time.time() * 1000),
                },
                "requestId": f"test_{int(time.time() * 1000)}",
                "timestamp": int(time.time() * 1000),
            }

            print(f"[{time.strftime('%H:%M:%S')}] 📤 发送请求 (resolution=1)")
            await ws.send(json.dumps(request))

            # 连续接收消息
            for i in range(10):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10)
                    elapsed = time.time() - start_time
                    data = json.loads(msg)

                    print(f"\n[{time.strftime('%H:%M:%S')}] --- 消息 {i+1} (耗时: {elapsed:.2f}s) ---")
                    print(json.dumps(data, indent=2))

                    # 检查关键字段
                    print(f"\n字段检查:")
                    print(f"  - action: {data.get('action')}")
                    print(f"  - taskId (根层): {data.get('taskId')}")
                    print(f"  - requestId: {data.get('requestId')}")
                    data_obj = data.get('data', {})
                    print(f"  - data.type: {data_obj.get('type') if data_obj else None}")
                    print(f"  - data.taskId: {data_obj.get('taskId') if data_obj else None}")

                    if data.get('action') == 'success' and data_obj.get('type') == 'klines':
                        print(f"\n  ✅ 找到klines成功响应!")
                        break

                except asyncio.TimeoutError:
                    print(f"[{time.strftime('%H:%M:%S')}] 消息 {i+1} 超时")
                    break

    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ❌ 错误: {e}")

if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(test_klines())
