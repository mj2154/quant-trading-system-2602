"""
测试现货客户端 - RSA签名版本
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / "src"))

import os
from dotenv import load_dotenv

load_dotenv("/app/.env")

from clients.spot_private_http_client import BinanceSpotPrivateHTTPClient


def load_private_key(key_path: str) -> bytes:
    with open(key_path, "rb") as f:
        return f.read()


async def main():
    api_key = os.environ.get("BINANCE_API_KEY")
    proxy_url = os.environ.get("CLASH_PROXY_HTTP_URL", "http://clash-proxy:7890")

    key_dir = Path("/app/keys")
    private_key_pem = load_private_key(str(key_dir / "private_rsa.pem"))

    # 使用RSA签名
    client = BinanceSpotPrivateHTTPClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        signature_type="rsa",
        proxy_url=proxy_url,
    )

    print("测试现货客户端 (RSA签名)")
    print("-" * 40)

    try:
        account = await client.get_account_info()
        print(f"账户类型: {account.account_type}")
        print(f"能否交易: {account.can_trade}")
        print(f"能否充值: {account.can_deposit}")
        print(f"能否提现: {account.can_withdraw}")
        print(f"手续费-挂单: {account.maker_commission}")
        print(f"手续费-吃单: {account.taker_commission}")
        print("\n部分余额:")
        for balance in account.balances[:5]:
            if float(balance.free or 0) > 0 or float(balance.locked or 0) > 0:
                print(f"  {balance.asset}: free={balance.free}, locked={balance.locked}")
        print("\n测试通过!")
    except Exception as e:
        print(f"失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
