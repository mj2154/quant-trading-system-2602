#!/usr/bin/env python3
"""
测试币安私有WebSocket认证 - 简化版本
"""
import asyncio
import os
import sys
import time
import websockets
import uuid
import json
from pathlib import Path

# 添加src目录到路径（支持本地和Docker环境）
SRC_PATH = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_PATH))

from utils.ed25519_signer import Ed25519Signer


async def test_futures_ws_no_proxy():
    """不使用代理测试期货WebSocket"""
    api_key = os.environ.get("BINANCE_API_KEY", "")
    private_key_path = os.environ.get("BINANCE_PRIVATE_KEY_PATH", str(SRC_PATH.parent / "keys" / "private_key.pem"))

    # 加载私钥
    with open(private_key_path, "rb") as f:
        private_key_pem = f.read()

    signer = Ed25519Signer(private_key_pem)
    timestamp = int(time.time() * 1000)

    # 期货WS API端点
    ws_uri = "wss://ws-fapi.binance.com/ws-fapi/v1"

    print(f"连接期货WS: {ws_uri} (不使用代理)")

    # 创建认证payload（按键名字母顺序）
    payload = f"apiKey={api_key}&timestamp={timestamp}"
    print(f"Payload: {payload}")

    signature = signer.sign(payload)
    print(f"签名: {signature[:50]}...")

    auth_request = {
        "id": str(uuid.uuid4()),
        "method": "session.logon",
        "params": {
            "apiKey": api_key,
            "signature": signature,
            "timestamp": timestamp,
        },
    }

    try:
        # 不使用代理
        async with websockets.connect(ws_uri) as ws:
            print("连接成功!")

            await ws.send(json.dumps(auth_request))
            print("认证请求已发送")

            # 接收多个响应
            for i in range(5):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=15)
                    print(f"响应 {i+1}: {response[:200]}..." if len(response) > 200 else f"响应 {i+1}: {response}")
                except asyncio.TimeoutError:
                    print(f"等待响应 {i+1} 超时")
                    break

    except Exception as e:
        print(f"连接失败: {e}")
        import traceback
        traceback.print_exc()


async def test_spot_ws_no_proxy():
    """不使用代理测试现货WebSocket"""
    api_key = os.environ.get("BINANCE_API_KEY", "")
    private_key_path = os.environ.get("BINANCE_PRIVATE_KEY_PATH", str(SRC_PATH.parent / "keys" / "private_key.pem"))

    # 加载私钥
    with open(private_key_path, "rb") as f:
        private_key_pem = f.read()

    signer = Ed25519Signer(private_key_pem)
    timestamp = int(time.time() * 1000)

    # 现货WS API端点
    ws_uri = "wss://ws-api.binance.com/ws-api/v3"

    print(f"\n{'='*50}")
    print(f"连接现货WS: {ws_uri} (不使用代理)")

    # 创建认证payload
    payload = f"apiKey={api_key}&timestamp={timestamp}"
    print(f"Payload: {payload}")

    signature = signer.sign(payload)
    print(f"签名: {signature[:50]}...")

    auth_request = {
        "id": str(uuid.uuid4()),
        "method": "session.logon",
        "params": {
            "apiKey": api_key,
            "signature": signature,
            "timestamp": timestamp,
        },
    }

    try:
        async with websockets.connect(ws_uri) as ws:
            print("连接成功!")

            await ws.send(json.dumps(auth_request))
            print("认证请求已发送")

            # 接收多个响应
            for i in range(5):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=15)
                    print(f"响应 {i+1}: {response[:200]}..." if len(response) > 200 else f"响应 {i+1}: {response}")
                except asyncio.TimeoutError:
                    print(f"等待响应 {i+1} 超时")
                    break

    except Exception as e:
        print(f"连接失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    print("="*50)
    print("测试期货WebSocket (无代理)")
    print("="*50)
    await test_futures_ws_no_proxy()

    print("\n" + "="*50)
    print("测试现货WebSocket (无代理)")
    print("="*50)
    await test_spot_ws_no_proxy()


if __name__ == "__main__":
    asyncio.run(main())
