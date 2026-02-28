"""
Demo网现货账户信息测试

使用代理连接 Demo 网获取账户信息。
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
from src.models.spot_account import SpotAccountInfo, Balance


def load_private_key(key_path: str) -> bytes:
    """加载PEM格式私钥"""
    with open(key_path, "rb") as f:
        return f.read()


async def test_spot_account_demo():
    """测试 Demo 网现货账户"""
    api_key = os.environ.get("BINANCE_API_KEY")
    if not api_key:
        print("请设置 BINANCE_API_KEY 环境变量")
        return False

    # RSA私钥路径
    key_dir = Path(__file__).parent / "keys"
    private_key_path = key_dir / "private_rsa_demo.pem"

    if not private_key_path.exists():
        print(f"RSA私钥文件不存在: {private_key_path}")
        return False

    private_key_pem = load_private_key(str(private_key_path))
    rsa_signer = RSASigner(private_key_pem)

    # 使用宿主机代理
    proxy_url = "http://127.0.0.1:7890"

    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"Private Key: {private_key_path.name}")
    print(f"Proxy: {proxy_url}")
    print("-" * 60)

    # Demo 网现货账户 API
    base_url = "https://demo-api.binance.com"
    timestamp = str(int(time.time() * 1000))

    # 构建query string
    query_string = f"timestamp={timestamp}&recvWindow=5000"

    # 生成RSA签名
    signature = rsa_signer.sign(query_string)
    signature_encoded = quote(signature, safe='')

    url = f"{base_url}/api/v3/account?{query_string}&signature={signature_encoded}"

    headers = {"X-MBX-APIKEY": api_key}

    print(f"请求URL: {url}")

    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            print(f"响应状态: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                # 使用币安数据模型解析
                account_info = SpotAccountInfo.model_validate(data)

                print("\n" + "=" * 60)
                print("SpotAccountInfo")
                print("=" * 60)

                # 账户基本信息
                print(f"\n--- 账户属性 ---")
                print(f"accountType:    {account_info.account_type}")
                print(f"canTrade:       {account_info.can_trade}")
                print(f"canWithdraw:    {account_info.can_withdraw}")
                print(f"canDeposit:     {account_info.can_deposit}")
                print(f"updateTime:     {account_info.update_time}")

                # 手续费率
                print(f"\n--- 手续费率 ---")
                print(f"makerCommission:  {account_info.maker_commission}")
                print(f"takerCommission: {account_info.taker_commission}")
                print(f"buyerCommission: {account_info.buyer_commission}")
                print(f"sellerCommission:{account_info.seller_commission}")

                if account_info.commission_rates:
                    cr = account_info.commission_rates
                    print(f"\n--- 手续费率详情 (commissionRates) ---")
                    print(f"maker: {cr.maker}")
                    print(f"taker: {cr.taker}")
                    print(f"buyer: {cr.buyer}")
                    print(f"seller: {cr.seller}")

                # 余额信息
                balances = account_info.balances
                print(f"\n--- 余额列表 (balances) ---")
                print(f"{'asset':<10} {'free':<25} {'locked':<25}")
                print("-" * 60)

                # 显示所有有余额的资产
                nonzero_count = 0
                for bal in balances:
                    free_amt = float(bal.free or "0")
                    locked_amt = float(bal.locked or "0")
                    if free_amt > 0 or locked_amt > 0:
                        nonzero_count += 1
                        print(f"{bal.asset:<10} {bal.free:<25} {bal.locked:<25}")

                print("-" * 60)
                print(f"有余额的资产数量: {nonzero_count}")
                print(f"总资产数量: {len(balances)}")
                print("=" * 60)
                return True
            else:
                print(f"响应内容: {response.text}")
                return False

    except Exception as e:
        print(f"请求失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=" * 60)
    print("Binance Demo 网现货账户测试")
    print("使用 SpotAccountInfo 数据模型")
    print("=" * 60)

    result = await test_spot_account_demo()

    print("\n" + "=" * 60)
    print(f"测试结果: {'✓ 成功' if result else '✗ 失败'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
