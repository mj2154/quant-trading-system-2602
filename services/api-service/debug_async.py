import asyncio
import websockets
import json
import time

async def test():
    uri = "ws://localhost:8000/ws/market"
    async with websockets.connect(uri, ping_interval=20, ping_timeout=60) as ws:
        end_time = int(time.time() * 1000)
        start_time = end_time - (24 * 60 * 60 * 1000)

        msg = {
            "protocolVersion": "2.0",
            "action": "get",
            "data": {
                "type": "klines",
                "symbol": "BINANCE:BTCUSDT",
                "resolution": "1",
                "from_time": start_time,
                "to_time": end_time,
            },
            "timestamp": int(time.time() * 1000),
        }
        await ws.send(json.dumps(msg))
        print("发送请求")

        # 第一个响应
        resp = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(resp)
        print(f"action={data.get('action')}")
        print(f"data={json.dumps(data.get('data', {}))}")

        if data.get('action') == 'ack':
            task_id = data.get('data', {}).get('taskId')
            print(f"任务ID: {task_id}")
            print("等待任务完成...")
            for i in range(60):
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=2)
                    data = json.loads(resp)
                    print(f"[{i}] action={data.get('action')}, type={data.get('data', {}).get('type')}")
                    if data.get('action') == 'success' and data.get('data', {}).get('type') == 'klines':
                        bars = len(data.get('data', {}).get('bars', []))
                        print(f"成功! 收到 {bars} 条K线")
                        break
                except asyncio.TimeoutError:
                    pass

if __name__ == "__main__":
    asyncio.run(test())
