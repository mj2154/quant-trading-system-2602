#!/usr/bin/env python3
"""
测试币安私有WebSocket认证 - 调试版本
"""
import asyncio
import os
import sys
import time
from pathlib import Path

# 添加src目录到路径（支持本地和Docker环境）
SRC_PATH = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_PATH))

from utils.ed25519_signer import Ed25519Signer


def test_signature():
    """测试签名生成"""
    api_key = os.environ.get("BINANCE_API_KEY", "")
    private_key_path = os.environ.get("BINANCE_PRIVATE_KEY_PATH", str(SRC_PATH.parent / "keys" / "private_key.pem"))

    print(f"API Key: {api_key}")

    # 加载私钥
    with open(private_key_path, "rb") as f:
        private_key_pem = f.read()

    # 创建签名器
    signer = Ed25519Signer(private_key_pem)

    # 测试签名
    timestamp = int(time.time() * 1000)
    print(f"Timestamp: {timestamp}")

    # 测试不同的payload格式
    payloads = [
        f"timestamp={timestamp}",  # 无apiKey
        f"apiKey={api_key}&timestamp={timestamp}",  # 字母顺序
        f"timestamp={timestamp}&apiKey={api_key}",  # 添加顺序
    ]

    print("\n测试不同payload格式:")
    for i, payload in enumerate(payloads):
        print(f"\n--- Payload {i+1}: {payload}")
        try:
            signature = signer.sign(payload)
            print(f"签名: {signature[:50]}...")
        except Exception as e:
            print(f"签名失败: {e}")


async def test_ws_direct():
    """直接测试WebSocket连接"""
    import websockets
    import uuid
    import json
    import base64

    api_key = os.environ.get("BINANCE_API_KEY", "")
    private_key_path = os.environ.get("BINANCE_PRIVATE_KEY_PATH", str(SRC_PATH.parent / "keys" / "private_key.pem"))
    proxy_url = os.environ.get("CLASH_PROXY_WS_URL", "http://clash-proxy:7890")

    # 加载私钥
    with open(private_key_path, "rb") as f:
        private_key_pem = f.read()

    signer = Ed25519Signer(private_key_pem)
    timestamp = int(time.time() * 1000)

    # 期货WS API端点
    ws_uri = "wss://ws-fapi.binance.com/ws-fapi/v1"

    print(f"\n连接期货WS: {ws_uri}")
    print(f"使用代理: {proxy_url}")

    # 创建认证payload（按键名字母顺序）
    # 根据文档：apiKey=xxx&timestamp=xxx
    payload = f"apiKey={api_key}&timestamp={timestamp}"
    print(f"Payload: {payload}")

    # 生成签名
    signature = signer.sign(payload)
    print(f"签名: {signature}")

    # 构建认证请求
    auth_request = {
        "id": str(uuid.uuid4()),
        "method": "session.logon",
        "params": {
            "apiKey": api_key,
            "signature": signature,
            "timestamp": timestamp,
        },
    }

    print(f"\n认证请求: {json.dumps(auth_request)}")

    # 连接
    try:
        async with websockets.connect(
            ws_uri,
            proxy=proxy_url.replace("http://", "").replace("https://", ""),
            additional_headers={"Content-Type": "application/json"},
        ) as ws:
            print("连接成功!")

            # 发送认证请求
            await ws.send(json.dumps(auth_request))
            print("认证请求已发送")

            # 等待响应
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=10)
                print(f"响应: {response}")
            except asyncio.TimeoutError:
                print("等待响应超时")

    except Exception as e:
        print(f"连接失败: {e}")
        import traceback
        traceback.print_exc()


async def test_spot_ws_direct():
    """直接测试现货WebSocket连接"""
    import websockets
    import uuid
    import json

    api_key = os.environ.get("BINANCE_API_KEY", "")
    private_key_path = os.environ.get("BINANCE_PRIVATE_KEY_PATH", str(SRC_PATH.parent / "keys" / "private_key.pem"))
    proxy_url = os.environ.get("CLASH_PROXY_WS_URL", "http://clash-proxy:7890")

    # 加载私钥
    with open(private_key_path, "rb") as f:
        private_key_pem = f.read()

    signer = Ed25519Signer(private_key_pem)
    timestamp = int(time.time() * 1000)

    # 现货WS API端点
    ws_uri = "wss://ws-api.binance.com/ws-api/v3"

    print(f"\n{'='*50}")
    print(f"连接现货WS: {ws_uri}")
    print(f"使用代理: {proxy_url}")

    # 创建认证payload
    payload = f"apiKey={api_key}&timestamp={timestamp}"
    print(f"Payload: {payload}")

    signature = signer.sign(payload)
    print(f"签名: {signature}")

    auth_request = {
        "id": str(uuid.uuid4()),
        "method": "session.logon",
        "params": {
            "apiKey": api_key,
            "signature": signature,
            "timestamp": timestamp,
        },
    }

    print(f"\n认证请求: {json.dumps(auth_request)}")

    try:
        async with websockets.connect(
            ws_uri,
            proxy=proxy_url.replace("http://", "").replace("https://", ""),
        ) as ws:
            print("连接成功!")

            await ws.send(json.dumps(auth_request))
            print("认证请求已发送")

            try:
                response = await asyncio.wait_for(ws.recv(), timeout=10)
                print(f"响应: {response}")
            except asyncio.TimeoutError:
                print("等待响应超时")

    except Exception as e:
        print(f"连接失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    # 测试签名
    print("="*50)
    print("测试签名")
    print("="*50)
    test_signature()

    # 测试期货WS
    print("\n" + "="*50)
    print("测试期货WebSocket")
    print("="*50)
    await test_ws_direct()

    # 测试现货WS
    await test_spot_ws_direct()


if __name__ == "__main__":
    asyncio.run(main())
