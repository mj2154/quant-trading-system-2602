"""
Ed25519签名验证测试脚本

用于测试币安API密钥和Ed25519签名是否配置正确。
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
import sys

sys.path.insert(0, str(Path(__file__).parent))

# 加载.env文件
load_dotenv()

from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient


def load_private_key(key_path: str) -> bytes:
    """加载PEM格式私钥"""
    with open(key_path, "rb") as f:
        return f.read()


async def test_api_key():
    """测试API密钥和签名"""

    # 从环境变量获取API Key
    api_key = os.environ.get("BINANCE_API_KEY")
    if not api_key:
        print("❌ 请设置 BINANCE_API_KEY 环境变量")
        print("   export BINANCE_API_KEY='你的API密钥'")
        return False

    # 私钥路径 - 使用本地文件
    key_dir = Path(__file__).parent / "keys"
    private_key_path = key_dir / "private_key.pem"

    if not private_key_path.exists():
        print(f"❌ 私钥文件不存在: {private_key_path}")
        return False

    # 加载私钥
    private_key_pem = load_private_key(str(private_key_path))

    # 创建客户端 - 不使用代理
    client = BinanceSpotPrivateHTTPClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        proxy_url=None,  # 不使用代理
    )

    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print("-" * 40)

    try:
        # 测试获取账户信息
        print("正在调用 /api/v3/account ...")
        account_info = await client.get_account_info()

        print("✅ 签名验证成功！")
        print(f"   账户ID: {account_info.account_type}")
        print(f"   余额数量: {len(account_info.balances)}")
        print(f"   能否交易: {account_info.can_trade}")
        print(f"   能否充值: {account_info.can_deposit}")
        print(f"   能否提现: {account_info.can_withdraw}")

        # 显示部分余额
        print("\n部分余额:")
        for balance in account_info.balances[:5]:
            if float(balance.free) > 0 or float(balance.locked) > 0:
                print(f"   {balance.asset}: free={balance.free}, locked={balance.locked}")

        return True

    except Exception as e:
        error_msg = str(e)
        print(f"❌ 请求失败: {error_msg}")

        # 尝试获取响应内容
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"   币安错误: {error_data}")
            except:
                print(f"   响应内容: {e.response.text[:200]}")
        else:
            import traceback
            print("   详细错误:")
            print(traceback.format_exc())

        # 常见错误提示
        if "-2015" in error_msg:
            print("\n💡 提示: Invalid API key 或 Invalid signature")
            print("   请检查:")
            print("   1. API Key是否正确")
            print("   2. 公钥是否已提交给币安")
            print("   3. 私钥是否与提交的公钥匹配")
        elif "-1022" in error_msg:
            print("\n💡 提示: Signature for this request is not valid")
            print("   签名生成可能有问题")

        return False


async def main():
    """主函数"""
    print("=" * 40)
    print("币安Ed25519签名测试")
    print("=" * 40)
    print()

    success = await test_api_key()

    print()
    print("=" * 40)
    if success:
        print("🎉 测试通过！")
    else:
        print("❌ 测试失败，请检查配置")
    print("=" * 40)

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
