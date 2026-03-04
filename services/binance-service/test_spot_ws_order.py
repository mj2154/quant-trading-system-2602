"""
现货私有WebSocket客户端测试 - 订单功能

测试通过WebSocket API进行现货订单操作。
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径
service_dir = Path(__file__).parent
sys.path.insert(0, str(service_dir / "src"))
sys.path.insert(0, str(service_dir))

# 加载.env文件
load_dotenv()

from clients.spot_private_ws_client import BinanceSpotPrivateWSClient
from models.trading_order import SpotOrderResponse


def load_private_key(key_path: str) -> bytes:
    """加载PEM格式私钥"""
    with open(key_path, "rb") as f:
        return f.read()


async def test_spot_order():
    """通过WebSocket API测试现货订单功能"""

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

    # WSL中使用localhost:7890的代理
    proxy_url = os.environ.get("PROXY_URL", "http://localhost:7890")

    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"Proxy URL: {proxy_url}")
    print(f"WebSocket端点: wss://demo-ws-api.binance.com/ws-api/v3")
    print("-" * 50)

    # 创建客户端
    client = BinanceSpotPrivateWSClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        proxy_url=proxy_url,
    )

    try:
        # 连接并认证
        print("正在连接现货私有WebSocket...")
        await client.connect()

        if not client.is_authenticated:
            print("认证失败!")
            return False

        print("认证成功!")
        print("-" * 50)

        # 测试1: 下市价单
        print("正在下单 (MARKET单)...")
        order_result = None
        try:
            order_result = await client.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,  # 小数量测试
            )

            # 使用数据模型验证响应
            validated_order = SpotOrderResponse.model_validate(order_result)
            print(f"下单成功! 响应已通过模型验证:")
            print(f"  订单ID: {validated_order.order_id}")
            print(f"  订单列表ID: {validated_order.order_list_id}")
            print(f"  交易对: {validated_order.symbol}")
            print(f"  方向: {validated_order.side}")
            print(f"  类型: {validated_order.order_type}")
            print(f"  状态: {validated_order.status}")
            print(f"  原始数量: {validated_order.orig_qty}")
            print(f"  成交数量: {validated_order.executed_qty}")
            print(f"  累计成交金额: {validated_order.cummulative_quote_qty}")
            if validated_order.fills:
                print(f"  成交明细:")
                for fill in validated_order.fills:
                    print(f"    价格: {fill.get('price')}, 数量: {fill.get('qty')}")
            print(f"  自成交预防: {validated_order.self_trade_prevention_mode}")
        except Exception as e:
            print(f"下单失败: {e}")

        print("-" * 50)

        # 测试2: 查询订单（如果有订单ID）
        # 先获取刚才的订单ID
        if order_result and "orderId" in order_result:
            order_id = order_result["orderId"]
            print(f"正在查询订单 {order_id}...")
            try:
                order_info = await client.get_order(
                    symbol="BTCUSDT",
                    order_id=order_id,
                )
                print(f"查询成功! 响应: {order_info}")
            except Exception as e:
                print(f"查询订单失败: {e}")

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
    print("现货私有WebSocket API测试 - 订单功能")
    print("=" * 50)
    print()

    success = await test_spot_order()

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
