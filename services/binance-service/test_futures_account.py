"""
期货私有HTTP客户端测试脚本

用于测试期货账户信息获取功能。
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

import sys
sys.path.insert(0, str(Path(__file__).parent))

# 加载.env文件
load_dotenv()

from src.clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient


def load_private_key(key_path: str) -> bytes:
    """加载PEM格式私钥"""
    with open(key_path, "rb") as f:
        return f.read()


async def test_futures_account():
    """测试获取期货账户信息"""

    # 从环境变量获取API Key
    api_key = os.environ.get("BINANCE_API_KEY")
    if not api_key:
        print("请设置 BINANCE_API_KEY 环境变量")
        return False

    # 私钥路径
    key_dir = Path(__file__).parent / "keys"
    private_key_path = key_dir / "private_key.pem"

    if not private_key_path.exists():
        print(f"私钥文件不存在: {private_key_path}")
        return False

    # 加载私钥
    private_key_pem = load_private_key(str(private_key_path))

    # 使用代理（Docker中clash-proxy的HTTP端口）
    proxy_url = os.environ.get("PROXY_URL", "http://clash-proxy:7890")

    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"Proxy URL: {proxy_url}")
    print("-" * 50)

    # 创建客户端 - 使用代理
    client = BinanceFuturesPrivateHTTPClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        proxy_url=proxy_url,
    )

    try:
        # 测试获取期货账户信息
        print("正在调用 /fapi/v3/account ...")
        account_info = await client.get_account_info()

        print("成功获取期货账户信息!")
        print(f"  手续费等级: {account_info.fee_tier}")
        print(f"  能否交易: {account_info.can_trade}")
        print(f"  能否充值: {account_info.can_deposit}")
        print(f"  能否提现: {account_info.can_withdraw}")
        print(f"  总钱包余额: {account_info.total_wallet_balance}")
        print(f"  总保证金余额: {account_info.total_margin_balance}")
        print(f"  总未实现盈亏: {account_info.total_unrealized_profit}")

        # 显示持仓
        if account_info.positions:
            print(f"\n持仓数量: {len(account_info.positions)}")
            for pos in account_info.positions[:5]:
                print(f"  {pos.symbol}: {pos.position_amt} @ {pos.entry_price}")
                print(f"    未实现盈亏: {pos.unrealized_profit}")

        return True

    except Exception as e:
        error_msg = str(e)
        print(f"请求失败: {error_msg}")

        # 尝试获取响应内容
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"币安错误: {error_data}")
            except:
                print(f"响应内容: {e.response.text[:500]}")
        else:
            import traceback
            print("详细错误:")
            print(traceback.format_exc())

        return False


async def main():
    """主函数"""
    print("=" * 50)
    print("期货私有HTTP客户端测试")
    print("=" * 50)
    print()

    success = await test_futures_account()

    print()
    print("=" * 50)
    if success:
        print("测试通过!")
    else:
        print("测试失败，请检查配置")
    print("=" * 50)

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
