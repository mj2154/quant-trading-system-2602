"""
期货私有HTTP客户端测试 - HMAC SHA256签名版本

用于测试期货账户信息获取功能（使用HMAC签名）。
"""

import asyncio
import hashlib
import hmac
import os
from pathlib import Path
from dotenv import load_dotenv

import sys
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()


def load_private_key(key_path: str) -> bytes:
    """加载PEM格式私钥"""
    with open(key_path, "rb") as f:
        return f.read()


def load_api_secret() -> str:
    """从环境变量获取API Secret"""
    api_secret = os.environ.get("BINANCE_API_SECRET")
    if not api_secret:
        print("请设置 BINANCE_API_SECRET 环境变量")
        raise ValueError("BINANCE_API_SECRET not set")
    return api_secret


def create_hmac_signature(payload: str, secret: str) -> str:
    """使用HMAC SHA256生成签名"""
    signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


async def test_futures_account_hmac():
    """使用HMAC签名测试期货账户"""
    import httpx

    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = load_api_secret()

    if not api_key:
        print("请设置 BINANCE_API_KEY 环境变量")
        return False

    proxy_url = os.environ.get("PROXY_URL", "http://clash-proxy:7890")

    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"API Secret: {api_secret[:4]}...{api_secret[-4:]}")
    print(f"Proxy URL: {proxy_url}")
    print("-" * 50)
    print("使用 HMAC SHA256 签名")
    print("-" * 50)

    base_url = "https://fapi.binance.com"
    timestamp = str(int(asyncio.get_event_loop().time() * 1000))

    # 构建query string
    query_string = f"timestamp={timestamp}&recvWindow=5000"

    # 生成签名
    signature = create_hmac_signature(query_string, api_secret)

    url = f"{base_url}/fapi/v3/account?{query_string}&signature={signature}"

    headers = {
        "X-MBX-APIKEY": api_key,
    }

    print(f"\n请求URL: {url}")
    print(f"签名: {signature}")

    async with httpx.AsyncClient(proxy=proxy_url, timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)
            print(f"\n响应状态: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("\n成功获取期货账户信息!")
                print(f"  手续费等级: {data.get('feeTier')}")
                print(f"  能否交易: {data.get('canTrade')}")
                print(f"  能否充值: {data.get('canDeposit')}")
                print(f"  能否提现: {data.get('canWithdraw')}")
                print(f"  总钱包余额: {data.get('totalWalletBalance')}")
                print(f"  总保证金余额: {data.get('totalMarginBalance')}")

                positions = data.get('positions', [])
                if positions:
                    print(f"\n持仓数量: {len(positions)}")
                    for pos in positions[:3]:
                        print(f"  {pos.get('symbol')}: {pos.get('positionAmt')} @ {pos.get('entryPrice')}")
                return True
            else:
                print(f"错误响应: {response.text[:500]}")
                return False

        except Exception as e:
            print(f"请求失败: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    print("=" * 50)
    print("期货私有HTTP客户端测试 (HMAC)")
    print("=" * 50)
    print()

    success = await test_futures_account_hmac()

    print()
    print("=" * 50)
    if success:
        print("测试通过!")
    else:
        print("测试失败")
    print("=" * 50)

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
