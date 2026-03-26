"""
测试期货 listenKey 获取

直接通过 REST API 测试能否正确获取 listenKey。
根据文档：
1. POST /fapi/v1/listenKey 获取 listenKey
2. listenKey 有效期 60 分钟
3. 需要使用 HMAC-SHA256 或其他签名方式签名
"""

import asyncio
import os
import sys
import time
import hmac
import hashlib
import httpx
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径
service_dir = Path(__file__).parent
sys.path.insert(0, str(service_dir / "src"))
sys.path.insert(0, str(service_dir))

# 加载.env文件
load_dotenv()


def get_signature(params: dict, secret_key: str) -> str:
    """生成 HMAC-SHA256 签名

    根据期货 API 文档，签名 payload 为按 key 字母排序的 query string
    """
    # 按字母顺序排序参数
    sorted_params = sorted(params.items())
    query_string = "&".join([f"{k}={v}" for k, v in sorted_params])
    signature = hmac.new(
        secret_key.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature


async def test_create_listen_key():
    """测试创建 listenKey"""
    print("=" * 60)
    print("测试期货 listenKey 获取")
    print("=" * 60)

    # 获取 API 凭证
    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        print("错误: 请设置 BINANCE_API_KEY 和 BINANCE_API_SECRET 环境变量")
        return False

    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print()

    # 期货测试网端点
    base_url = "https://testnet.binancefuture.com"

    # 代理配置
    proxy_url = os.environ.get("PROXY_URL", "http://localhost:7890")
    print(f"代理: {proxy_url}")

    # 构建请求参数
    timestamp = int(time.time() * 1000)
    params = {
        "timestamp": timestamp,
    }

    # 生成签名
    signature = get_signature(params, api_secret)
    print(f"签名: {signature[:16]}...")
    print()

    # 构建完整请求
    url = f"{base_url}/fapi/v1/listenKey"
    headers = {
        "X-MBX-APIKEY": api_key,
    }

    print("-" * 60)
    print(f"请求: POST {url}")
    print(f"Headers: {headers}")
    print(f"Params: {params}")
    print(f"Signature: {signature}")
    print("-" * 60)

    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=30) as client:
            response = await client.post(
                url,
                headers=headers,
                params={**params, "signature": signature},
            )

            print()
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.text}")

            if response.status_code == 200:
                data = response.json()
                listen_key = data.get("listenKey")
                if listen_key:
                    print()
                    print("=" * 60)
                    print(f"✓ listenKey 获取成功!")
                    print(f"listenKey: {listen_key}")
                    print("=" * 60)
                    return True, listen_key
                else:
                    print("错误: 响应中未包含 listenKey")
                    return False, None
            else:
                print(f"错误: HTTP {response.status_code}")
                return False, None

    except Exception as e:
        print(f"请求异常: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_renew_listen_key(listen_key: str):
    """测试续期 listenKey"""
    print()
    print("=" * 60)
    print("测试期货 listenKey 续期")
    print("=" * 60)

    if not listen_key:
        print("错误: 需要有效的 listenKey")
        return False

    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")

    base_url = "https://testnet.binancefuture.com"
    proxy_url = os.environ.get("PROXY_URL", "http://localhost:7890")

    timestamp = int(time.time() * 1000)
    params = {
        "timestamp": timestamp,
    }

    signature = get_signature(params, api_secret)

    url = f"{base_url}/fapi/v1/listenKey"
    headers = {
        "X-MBX-APIKEY": api_key,
    }

    print(f"请求: PUT {url}")
    print(f"Headers: {headers}")
    print(f"Params: {params}")
    print(f"Signature: {signature}")

    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=30) as client:
            response = await client.put(
                url,
                headers=headers,
                params={**params, "signature": signature},
            )

            print()
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.text}")

            if response.status_code == 200:
                print()
                print("✓ listenKey 续期成功!")
                return True
            else:
                print(f"错误: HTTP {response.status_code}")
                return False

    except Exception as e:
        print(f"请求异常: {e}")
        return False


async def main():
    """主函数"""
    print()
    print("测试开始时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print()

    # 测试创建 listenKey
    success, listen_key = await test_create_listen_key()

    if success and listen_key:
        # 测试续期
        await test_renew_listen_key(listen_key)

    print()
    print("测试结束时间:", time.strftime("%Y-%m-%d %H:%M:%S"))

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
