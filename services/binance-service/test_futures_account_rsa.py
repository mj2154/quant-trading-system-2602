"""
期货私有HTTP客户端测试 - RSA签名版本

使用代理连接。
"""

import asyncio
import os
import time
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv

import sys
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

import httpx
from src.utils.rsa_signer import RSASigner


def load_private_key(key_path: str) -> bytes:
    """加载PEM格式私钥"""
    with open(key_path, "rb") as f:
        return f.read()


async def test_futures_account_rsa():
    """使用RSA签名测试期货账户"""

    # 从环境变量获取期货API Key
    api_key = os.environ.get("BINANCE_FUTURES_API_KEY")
    if not api_key:
        print("请设置 BINANCE_FUTURES_API_KEY 环境变量")
        return False

    # RSA私钥路径
    key_dir = Path(__file__).parent / "keys"
    private_key_path = key_dir / "private_rsa.pem"

    if not private_key_path.exists():
        print(f"RSA私钥文件不存在: {private_key_path}")
        return False

    # 加载RSA私钥
    private_key_pem = load_private_key(str(private_key_path))

    # 创建RSA签名器
    rsa_signer = RSASigner(private_key_pem)

    # 使用代理
    proxy_url = os.environ.get("PROXY_URL", "http://clash-proxy:7890")

    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"Proxy: {proxy_url}")
    print("-" * 50)
    print("使用 RSA SHA256 签名")
    print("-" * 50)

    # 构建请求
    base_url = "https://fapi.binance.com"
    timestamp = str(int(time.time() * 1000))

    # 构建query string
    query_string = f"timestamp={timestamp}&recvWindow=5000"

    # 生成RSA签名
    signature = rsa_signer.sign(query_string)

    # URL编码签名
    signature_encoded = quote(signature, safe='')

    url = f"{base_url}/fapi/v3/account?{query_string}&signature={signature_encoded}"

    headers = {
        "X-MBX-APIKEY": api_key,
    }

    print(f"\n请求: {url[:80]}...")

    # 使用代理
    async with httpx.AsyncClient(proxy=proxy_url, timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)
            print(f"响应状态: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("\n成功获取期货账户信息!")
                print(f"  总钱包余额: {data.get('totalWalletBalance')}")
                print(f"  总保证金余额: {data.get('totalMarginBalance')}")
                print(f"  总未实现盈亏: {data.get('totalUnrealizedProfit')}")

                positions = data.get('positions', [])
                if positions:
                    print(f"\n持仓数量: {len(positions)}")
                    for pos in positions[:3]:
                        print(f"  {pos.get('symbol')}: {pos.get('positionAmt')}")
                return True
            else:
                print(f"错误: {response.text[:300]}")
                return False

        except Exception as e:
            print(f"请求失败: {e}")
            return False


async def main():
    print("=" * 50)
    print("期货私有HTTP客户端测试 (RSA + 代理)")
    print("=" * 50)
    print()

    success = await test_futures_account_rsa()

    print()
    print("=" * 50)
    print("测试通过!" if success else "测试失败")
    print("=" * 50)

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
