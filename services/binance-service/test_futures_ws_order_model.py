"""
测试期货WS订单响应数据模型验证

验证返回的数据是否符合官方文档定义的数据模型。
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

from clients.futures_private_ws_client import BinanceFuturesPrivateWSClient
from models.ws_trading_models import WSOrderResponse, WSAuthResponse


def load_private_key(key_path: str) -> bytes:
    """加载PEM格式私钥"""
    with open(key_path, "rb") as f:
        return f.read()


async def test_order_response_model():
    """测试订单响应数据模型验证"""

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

    # 代理配置
    proxy_url = os.environ.get("PROXY_URL", "http://localhost:7890")

    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"Proxy URL: {proxy_url}")
    print("-" * 50)

    # 创建客户端 - 使用测试网
    client = BinanceFuturesPrivateWSClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        proxy_url=proxy_url,
        use_testnet=True,
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

        # 测试: 下单并验证响应数据模型
        print("正在下单 (MARKET单)...")
        order_result = await client.place_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.001,  # 最小数量
        )

        # 使用Pydantic模型验证响应数据
        print("正在验证订单响应数据模型...")
        try:
            validated_order = WSOrderResponse.model_validate(order_result)
            print(f"数据模型验证成功!")
            print(f"  订单ID: {validated_order.order_id}")
            print(f"  交易对: {validated_order.symbol}")
            print(f"  状态: {validated_order.status}")
            print(f"  方向: {validated_order.side}")
            print(f"  类型: {validated_order.type}")
            print(f"  成交数量: {validated_order.executed_qty}")
            print(f"  成交均价: {validated_order.avg_price}")
            print(f"  累计成交额: {validated_order.cum_quote}")
            print(f"  持仓方向: {validated_order.position_side}")
            print(f"  更新时间: {validated_order.update_time}")
        except Exception as e:
            print(f"数据模型验证失败: {e}")
            import traceback
            traceback.print_exc()
            return False

        print("-" * 50)

        # 测试: 查询订单并验证
        print(f"正在查询订单 {validated_order.order_id}...")
        order_info = await client.get_order(
            symbol="BTCUSDT",
            order_id=str(validated_order.order_id),
        )

        print("正在验证查询订单响应数据模型...")
        try:
            validated_query = WSOrderResponse.model_validate(order_info)
            print(f"查询订单数据模型验证成功!")
            print(f"  订单状态: {validated_query.status}")
            print(f"  成交数量: {validated_query.executed_qty}")
            print(f"  成交均价: {validated_query.avg_price}")
        except Exception as e:
            print(f"查询订单数据模型验证失败: {e}")
            import traceback
            traceback.print_exc()
            return False

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
    print("期货WS订单数据模型验证测试")
    print("=" * 50)
    print()

    success = await test_order_response_model()

    print()
    print("=" * 50)
    if success:
        print("测试通过! 数据模型符合官方文档定义")
    else:
        print("测试失败")
    print("=" * 50)

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
