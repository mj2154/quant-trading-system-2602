"""
测试期货 WebSocket 认证，查看收到的响应数据包内容
"""
import asyncio
import json
import time
import base64
import os
from pathlib import Path

# 需要安装: pip install cryptography
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from websockets.asyncio.client import connect


async def test_futures_ws_auth():
    # 配置 - 使用环境变量或默认值
    PROXY = os.environ.get("PROXY_URL", "http://clash-proxy:7890")
    API_KEY = os.environ.get("BINANCE_API_KEY", "Vqbrkc22iXV3BRgtiaavEQReeP8UIvjnBLIHbcGOA8Oq1FBFy1cnmCAVm7oBXiHm")
    PRIVATE_KEY_PATH = os.environ.get("PRIVATE_KEY_PATH", "/app/keys/private_key.pem")

    # 加载私钥
    print(f"加载私钥: {PRIVATE_KEY_PATH}")
    private_pem = Path(PRIVATE_KEY_PATH).read_bytes()
    private_key = serialization.load_pem_private_key(
        private_pem,
        password=None,
        backend=default_backend()
    )

    # Testnet URL
    url = "wss://testnet.binancefuture.com/ws-fapi/v1"

    print(f"\n{'='*60}")
    print(f"测试期货 WebSocket 认证")
    print(f"{'='*60}")
    print(f"URL: {url}")
    print(f"代理: {PROXY}")
    print(f"API Key: {API_KEY[:10]}...")
    print(f"{'='*60}\n")

    try:
        print("1. 建立 WebSocket 连接...")
        ws = await asyncio.wait_for(connect(url, proxy=PROXY), timeout=60)
        print("   连接成功!\n")

        # 构造认证请求参数（按键名字母顺序）
        timestamp = int(time.time() * 1000)
        params = {
            "apiKey": API_KEY,
            "timestamp": timestamp,
        }
        # 按字母顺序排序: apiKey, timestamp
        payload = f"apiKey={API_KEY}&timestamp={timestamp}"

        # Ed25519签名
        signature = base64.b64encode(private_key.sign(payload.encode())).decode()

        auth_msg = {
            "id": "futures-auth-test-1",
            "method": "session.logon",
            "params": {
                "apiKey": API_KEY,
                "signature": signature,
                "timestamp": timestamp,
            }
        }

        print("2. 发送认证请求...")
        print(f"   payload: {payload}")
        print(f"   signature: {signature[:30]}...")
        print(f"   完整请求: {json.dumps(auth_msg, indent=2)}\n")

        await ws.send(json.dumps(auth_msg))

        print("3. 等待认证响应...\n")

        # 读取所有响应（可能会收到多条消息）
        responses = []
        start_time = time.time()
        timeout = 10

        while time.time() - start_time < timeout:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=3)
                responses.append(resp)
                print(f"   收到消息 [{len(responses)}]: {resp}\n")
            except asyncio.TimeoutError:
                # 没有更多消息了
                break

        print(f"   共收到 {len(responses)} 条消息\n")

        # 分析响应
        for i, resp in enumerate(responses):
            try:
                data = json.loads(resp)
                print(f"消息 {i+1} 解析结果:")
                print(json.dumps(data, indent=4, ensure_ascii=False))
                print()

                # 检查状态码
                status = data.get("status")
                if status == 200:
                    print(f"   >>> 认证成功! (status={status})")
                    result = data.get("result", {})
                    print(f"       authorizedSince: {result.get('authorizedSince')}")
                    print(f"       connectedSince: {result.get('connectedSince')}")
                    print(f"       serverTime: {result.get('serverTime')}")
                elif status == 400:
                    error = data.get("error", {})
                    print(f"   >>> 认证失败! (status={status})")
                    print(f"       error code: {error.get('code')}")
                    print(f"       error msg: {error.get('msg')}")
                elif status == 401:
                    error = data.get("error", {})
                    print(f"   >>> 认证失败! (status={status})")
                    print(f"       error code: {error.get('code')}")
                    print(f"       error msg: {error.get('msg')}")
                else:
                    print(f"   >>> 其他状态: status={status}")

            except json.JSONDecodeError as e:
                print(f"   JSON 解析错误: {e}")

        print("\n4. 关闭连接...")
        await ws.close()
        print("   连接已关闭")

    except Exception as e:
        import traceback
        print(f"\n错误: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_futures_ws_auth())
