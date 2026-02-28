"""
测试现货和期货私有客户端
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 加载本地.env
load_dotenv()

from clients.spot_private_http_client import BinanceSpotPrivateHTTPClient
from clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient


def load_private_key(key_path: str) -> bytes:
    with open(key_path, "rb") as f:
        return f.read()


async def test_spot_client():
    """测试现货客户端"""
    print("\n" + "=" * 50)
    print("测试现货客户端 (RSA签名)")
    print("=" * 50)

    api_key = os.environ.get("BINANCE_API_KEY")
    proxy_url = os.environ.get("CLASH_PROXY", "http://127.0.0.1:7890")

    key_dir = Path(__file__).parent / "keys"
    private_key_pem = load_private_key(str(key_dir / "private_rsa.pem"))

    client = BinanceSpotPrivateHTTPClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        signature_type="rsa",
        proxy_url=proxy_url,
    )

    try:
        account = await client.get_account_info()
        print(f"账户类型: {account.account_type}")
        print(f"能否交易: {account.can_trade}")
        print(f"能否充值: {account.can_deposit}")
        print(f"能否提现: {account.can_withdraw}")
        print(f"手续费-挂单: {account.maker_commission}")
        print(f"手续费-吃单: {account.taker_commission}")

        # 显示有余额的资产
        balances_with_asset = [b for b in account.balances if float(b.free or 0) > 0 or float(b.locked or 0) > 0]
        print(f"\n有余额的资产数量: {len(balances_with_asset)}")
        print("部分余额 (前5个):")
        for balance in balances_with_asset[:5]:
            print(f"  {balance.asset}: free={balance.free}, locked={balance.locked}")

        await client.close()
        return True, "测试通过"
    except Exception as e:
        await client.close()
        return False, str(e)


async def test_futures_client():
    """测试期货客户端"""
    print("\n" + "=" * 50)
    print("测试期货客户端 (RSA签名)")
    print("=" * 50)

    api_key = os.environ.get("BINANCE_API_KEY")
    proxy_url = os.environ.get("CLASH_PROXY", "http://127.0.0.1:7890")

    key_dir = Path(__file__).parent / "keys"
    private_key_pem = load_private_key(str(key_dir / "private_rsa.pem"))

    client = BinanceFuturesPrivateHTTPClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        signature_type="rsa",
        proxy_url=proxy_url,
    )

    try:
        account = await client.get_account_info()
        print(f"总钱包余额: {account.total_wallet_balance}")
        print(f"总保证金余额: {account.total_margin_balance}")
        print(f"未实现盈亏: {account.total_unrealized_profit}")
        print(f"总初始保证金: {account.total_initial_margin}")
        print(f"能否交易: {account.can_trade}")

        # 显示持仓
        positions_with_amt = [p for p in account.positions if float(p.position_amt or 0) != 0]
        print(f"\n持仓数量: {len(positions_with_amt)}")
        if positions_with_amt:
            print("持仓详情 (前3个):")
            for pos in positions_with_amt[:3]:
                print(f"  {pos.symbol}: {pos.position_amt} @ {pos.entry_price} (PNL: {pos.unrealized_profit})")

        await client.close()
        return True, "测试通过"
    except Exception as e:
        await client.close()
        return False, str(e)


async def main():
    print("=" * 50)
    print("币安私有客户端测试")
    print("=" * 50)

    # 测试现货客户端
    spot_success, spot_msg = await test_spot_client()

    # 测试期货客户端
    futures_success, futures_msg = await test_futures_client()

    # 输出总结
    print("\n" + "=" * 50)
    print("测试结果总结")
    print("=" * 50)
    print(f"现货客户端: {'✓ ' + spot_msg if spot_success else '✗ ' + spot_msg}")
    print(f"期货客户端: {'✓ ' + futures_msg if futures_success else '✗ ' + futures_msg}")

    if spot_success and futures_success:
        print("\n所有测试通过!")
    else:
        print("\n部分测试失败!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
