"""
期货私有WebSocket客户端测试 - 获取账户信息

测试通过WebSocket API获取期货测试网的账户信息。
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径 - binance-service使用src作为根目录
service_dir = Path(__file__).parent
sys.path.insert(0, str(service_dir / "src"))
sys.path.insert(0, str(service_dir))

# 加载.env文件
load_dotenv()

from clients.futures_private_ws_client import BinanceFuturesPrivateWSClient


def load_private_key(key_path: str) -> bytes:
    """加载PEM格式私钥"""
    with open(key_path, "rb") as f:
        return f.read()


async def test_futures_ws_account():
    """通过WebSocket API测试获取期货账户信息"""

    # 从环境变量获取API Key
    api_key = os.environ.get("BINANCE_API_KEY")
    if not api_key:
        print("请设置 BINANCE_API_KEY 环境变量")
        return False

    # 私钥路径 - 期货测试网使用Ed25519密钥
    key_dir = Path(__file__).parent / "keys"
    private_key_path = key_dir / "private_key.pem"

    if not private_key_path.exists():
        print(f"私钥文件不存在: {private_key_path}")
        return False

    # 加载私钥
    private_key_pem = load_private_key(str(private_key_path))

    # WSL中使用localhost:7890的代理
    proxy_url = os.environ.get("PROXY_URL", "http://localhost:7890")

    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"Proxy URL: {proxy_url}")
    print(f"WebSocket端点: wss://testnet.binancefuture.com/ws-fapi/v1")
    print("-" * 50)

    # 创建客户端 - 使用测试网
    client = BinanceFuturesPrivateWSClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        proxy_url=proxy_url,
        use_testnet=True,  # 使用测试网
    )

    try:
        # 连接并认证
        print("正在连接期货私有WebSocket...")
        await client.connect()

        if not client.is_authenticated:
            print("认证失败!")
            return False

        print("认证成功!")
        print("-" * 50)

        # 获取账户信息
        print("正在获取账户信息...")

        # 方法1: 获取账户余额 (account.balance)
        try:
            balance = await client.get_account_balance()
            print("成功获取账户余额 (account.balance)!")
            print(f"  响应: {balance}")
        except Exception as e:
            print(f"获取账户余额失败: {e}")

        print("-" * 50)

        # 方法2: 获取V2账户信息 (v2/account.status)
        try:
            account_v2 = await client.get_account_info_v2_ws()
            print("成功获取V2账户信息 (v2/account.status)!")
            print(f"  总钱包余额: {account_v2.get('totalWalletBalance')}")
            print(f"  总保证金余额: {account_v2.get('totalMarginBalance')}")
            print(f"  可用余额: {account_v2.get('availableBalance')}")

            assets = account_v2.get('assets', [])
            if assets:
                print(f"  资产数量: {len(assets)}")
                for asset in assets[:3]:
                    print(f"    {asset.get('asset')}: {asset.get('walletBalance')}")

            positions = account_v2.get('positions', [])
            if positions:
                print(f"  持仓数量: {len(positions)}")
                for pos in positions[:3]:
                    print(f"    {pos.get('symbol')}: {pos.get('positionAmt')}")
        except Exception as e:
            print(f"获取V2账户信息失败: {e}")

        return True

    except Exception as e:
        error_msg = str(e)
        print(f"请求失败: {error_msg}")

        import traceback
        print("详细错误:")
        print(traceback.format_exc())

        return False

    finally:
        # 断开连接
        print("正在断开连接...")
        await client.disconnect()
        print("连接已断开")


async def main():
    """主函数"""
    print("=" * 50)
    print("期货私有WebSocket API测试 - 获取账户信息")
    print("=" * 50)
    print()

    success = await test_futures_ws_account()

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
