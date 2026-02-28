#!/usr/bin/env python3
"""
简单K线测试 - 顺序验证
"""

import asyncio
import json
import time
import websockets

WS_URL = "ws://localhost:8000/ws/market"

async def test():
    print(f"[{time.strftime('%H:%M:%S')}] 连接...")
    async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=60) as ws:
        print(f"[{time.strftime('%H:%M:%S')}] ✅ 连接成功")

        # 测试1: BTCUSDT 1小时K线（同步响应）
        print(f"\n--- 测试1: BTCUSDT 1小时K线 ---")
        req1 = {
            "protocolVersion": "2.0", "action": "get",
            "data": {"type": "klines", "symbol": "BINANCE:BTCUSDT", "resolution": "60",
                     "from_time": int(time.time()*1000) - 24*60*60*1000, "to_time": int(time.time()*1000)},
            "requestId": "test_1", "timestamp": int(time.time()*1000)
        }
        await ws.send(json.dumps(req1))
        resp1 = await asyncio.wait_for(ws.recv(), timeout=10)
        data1 = json.loads(resp1)
        print(f"action: {data1.get('action')}")
        print(f"requestId: {data1.get('requestId')}")
        print(f"data.type: {data1.get('data', {}).get('type')}")
        print(f"count: {data1.get('data', {}).get('count')}")

        # 测试2: ETHUSDT 1小时K线（同步响应）
        print(f"\n--- 测试2: ETHUSDT 1小时K线 ---")
        await asyncio.sleep(0.5)  # 短暂等待
        req2 = {
            "protocolVersion": "2.0", "action": "get",
            "data": {"type": "klines", "symbol": "BINANCE:ETHUSDT", "resolution": "60",
                     "from_time": int(time.time()*1000) - 24*60*60*1000, "to_time": int(time.time()*1000)},
            "requestId": "test_2", "timestamp": int(time.time()*1000)
        }
        await ws.send(json.dumps(req2))
        resp2 = await asyncio.wait_for(ws.recv(), timeout=10)
        data2 = json.loads(resp2)
        print(f"action: {data2.get('action')}")
        print(f"requestId: {data2.get('requestId')}")
        print(f"data.type: {data2.get('data', {}).get('type')}")
        print(f"count: {data2.get('data', {}).get('count')}")

        # 测试3: BTCUSDT 1分钟K线（异步任务）
        print(f"\n--- 测试3: BTCUSDT 1分钟K线（异步） ---")
        await asyncio.sleep(0.5)
        req3 = {
            "protocolVersion": "2.0", "action": "get",
            "data": {"type": "klines", "symbol": "BINANCE:BTCUSDT", "resolution": "1",
                     "from_time": int(time.time()*1000) - 60*60*1000, "to_time": int(time.time()*1000)},
            "requestId": "test_3", "timestamp": int(time.time()*1000)
        }
        await ws.send(json.dumps(req3))
        resp3 = await asyncio.wait_for(ws.recv(), timeout=10)
        data3 = json.loads(resp3)
        print(f"action: {data3.get('action')}")
        print(f"requestId: {data3.get('requestId')}")

        if data3.get('action') == 'ack':
            print("等待异步任务完成...")
            resp4 = await asyncio.wait_for(ws.recv(), timeout=30)
            data4 = json.loads(resp4)
            print(f"action: {data4.get('action')}")
            print(f"requestId: {data4.get('requestId')}")
            print(f"data.type: {data4.get('data', {}).get('type')}")
            print(f"count: {data4.get('data', {}).get('count')}")

        print(f"\n✅ 测试完成")

if __name__ == "__main__":
    asyncio.run(test())
