"""
测试期货客户端 - RSA签名版本
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / "src"))

load_dotenv("/app/.env")

from clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient


def load_private_key(key_path: str) -> bytes:
    with open(key_path, "rb") as f:
        return f.read()


async def main():
    api_key = os.environ.get("BINANCE_API_KEY")
    proxy_url = os.environ.get("CLASH_PROXY_HTTP_URL", "http://clash-proxy:7890")

    key_dir = Path("/app/keys")
    private_key_pem = load_private_key(str(key_dir / "private_rsa.pem"))

    # 使用RSA签名
    client = BinanceFuturesPrivateHTTPClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        signature_type="rsa",
        proxy_url=proxy_url,
    )

    print("测试期货客户端 (RSA签名)")
    print("-" * 40)

    try:
        account = await client.get_account_info()
        print(f"总钱包余额: {account.total_wallet_balance}")
        print(f"总保证金余额: {account.total_margin_balance}")
        print(f"未实现盈亏: {account.total_unrealized_profit}")
        print("\n测试通过!")
    except Exception as e:
        print(f"失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
