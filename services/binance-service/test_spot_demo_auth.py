"""
测试现货Demo WebSocket认证
"""
import asyncio
import json
import time
import base64
from pathlib import Path

# 需要安装: pip install cryptography
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from websockets.asyncio.client import connect


async def test_spot_demo_auth():
    # 配置
    PROXY = "http://clash-proxy:7890"
    API_KEY = "Vqbrkc22iXV3BRgtiaavEQReeP8UIvjnBLIHbcGOA8Oq1FBFy1cnmCAVm7oBXiHm"
    PRIVATE_KEY_PATH = "/app/private_key.pem"

    # 加载私钥
    private_pem = Path(PRIVATE_KEY_PATH).read_bytes()
    private_key = serialization.load_pem_private_key(
        private_pem,
        password=None,
        backend=default_backend()
    )

    # Demo URL
    url = "wss://demo-ws-api.binance.com/ws-api/v3"

    print(f"连接: {url}")

    try:
        ws = await asyncio.wait_for(connect(url, proxy=PROXY), timeout=60)
        print("连接成功!")

        # 构造认证请求参数（按键名字母顺序）
        timestamp = int(time.time() * 1000)
        params = {
            "apiKey": API_KEY,
            "timestamp": timestamp,
        }
        # 按字母顺序排序: apiKey, timestamp
        # payload = "apiKey=xxx&timestamp=xxx"
        payload = f"apiKey={API_KEY}&timestamp={timestamp}"

        # Ed25519签名
        signature = base64.b64encode(private_key.sign(payload.encode())).decode()

        auth_msg = {
            "id": "auth-test-1",
            "method": "session.logon",
            "params": {
                "apiKey": API_KEY,
                "signature": signature,
                "timestamp": timestamp,
            }
        }

        print(f"发送认证请求...")
        print(f"  payload: {payload}")
        print(f"  signature: {signature[:50]}...")

        await ws.send(json.dumps(auth_msg))
        auth_resp = await asyncio.wait_for(ws.recv(), timeout=10)

        print(f"认证响应: {auth_resp}")

        auth_data = json.loads(auth_resp)
        if auth_data.get("status") == 200:
            print("认证成功!")

            # 查询账户信息
            timestamp2 = int(time.time() * 1000)
            payload2 = f"apiKey={API_KEY}&timestamp={timestamp2}"
            signature2 = base64.b64encode(private_key.sign(payload2.encode())).decode()

            account_msg = {
                "id": "account-test-1",
                "method": "account.status",
                "params": {
                    "apiKey": API_KEY,
                    "signature": signature2,
                    "timestamp": timestamp2,
                }
            }

            print("发送账户信息请求...")
            await ws.send(json.dumps(account_msg))
            account_resp = await asyncio.wait_for(ws.recv(), timeout=10)
            print(f"账户响应: {account_resp}")
        else:
            print(f"认证失败: {auth_data}")

        await ws.close()
        print("连接关闭")

    except Exception as e:
        import traceback
        print(f"错误: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_spot_demo_auth())
