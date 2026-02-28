"""
Demo网期货账户信息测试

使用代理连接 Demo 网获取期货账户信息。
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
from src.models.futures_account import FuturesAccountInfo, FuturesAsset, FuturesPosition


def load_private_key(key_path: str) -> bytes:
    """加载PEM格式私钥"""
    with open(key_path, "rb") as f:
        return f.read()


async def test_futures_account_demo():
    """测试 Demo 网期货账户"""
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

    # Demo 网期货账户 API
    base_url = "https://demo-fapi.binance.com"
    timestamp = str(int(time.time() * 1000))

    # 构建query string
    query_string = f"timestamp={timestamp}&recvWindow=5000"

    # 生成RSA签名
    signature = rsa_signer.sign(query_string)
    signature_encoded = quote(signature, safe='')

    url = f"{base_url}/fapi/v3/account?{query_string}&signature={signature_encoded}"

    headers = {"X-MBX-APIKEY": api_key}

    print(f"请求URL: {url}")

    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            print(f"响应状态: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                # 使用币安数据模型解析
                account_info = FuturesAccountInfo.model_validate(data)

                print("\n" + "=" * 60)
                print("FuturesAccountInfo")
                print("=" * 60)

                # 账户余额汇总
                print(f"\n--- 账户余额汇总 (仅计算 USDT 资产) ---")
                print(f"totalWalletBalance:        {account_info.total_wallet_balance}")
                print(f"totalMarginBalance:        {account_info.total_margin_balance}")
                print(f"totalUnrealizedProfit:    {account_info.total_unrealized_profit}")
                print(f"totalInitialMargin:       {account_info.total_initial_margin}")
                print(f"totalMaintMargin:         {account_info.total_maint_margin}")
                print(f"totalPositionInitialMargin: {account_info.total_position_initial_margin}")
                print(f"totalOpenOrderInitialMargin: {account_info.total_open_order_initial_margin}")

                # 可用余额
                print(f"\n--- 可用余额 ---")
                print(f"availableBalance:   {account_info.available_balance}")
                print(f"maxWithdrawAmount:  {account_info.max_withdraw_amount}")

                # 资产列表
                assets = account_info.assets
                if assets:
                    print(f"\n--- 资产列表 (assets) ---")
                    print(f"{'asset':<10} {'walletBalance':<18} {'marginBalance':<18} {'unrealizedProfit':<18} {'availableBalance':<18}")
                    print("-" * 90)
                    for asset in assets:
                        print(f"{asset.asset:<10} "
                              f"{asset.wallet_balance or '0':<18} "
                              f"{asset.margin_balance or '0':<18} "
                              f"{asset.unrealized_profit or '0':<18} "
                              f"{asset.available_balance or '0':<18}")
                    print("-" * 90)

                # 持仓列表
                positions = account_info.positions
                if positions:
                    print(f"\n--- 持仓列表 (positions) ---")
                    print(f"{'symbol':<15} {'positionSide':<12} {'positionAmt':<15} {'unrealizedProfit':<18} {'notional':<15}")
                    print("-" * 90)
                    for pos in positions:
                        print(f"{pos.symbol:<15} "
                              f"{pos.position_side or 'BOTH':<12} "
                              f"{pos.position_amt or '0':<15} "
                              f"{pos.unrealized_profit or '0':<18} "
                              f"{pos.notional_value or '0':<15}")
                    print("-" * 90)
                else:
                    print(f"\n--- 持仓列表 (positions) ---")
                    print("无持仓")

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
    print("Binance Demo 网期货账户测试")
    print("使用 FuturesAccountInfo 数据模型")
    print("=" * 60)

    result = await test_futures_account_demo()

    print("\n" + "=" * 60)
    print(f"测试结果: {'✓ 成功' if result else '✗ 失败'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
