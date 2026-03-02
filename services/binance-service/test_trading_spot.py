"""
现货交易测试程序

测试现货下单功能，每次下单100 USDT。
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from clients.spot_private_http_client import BinanceSpotPrivateHTTPClient


def load_credentials() -> tuple[str, bytes]:
    """加载API凭证"""
    load_dotenv()

    # 优先使用专用配置，否则使用通用配置
    api_key = os.environ.get("BINANCE_SPOT_API_KEY") or os.environ.get("BINANCE_API_KEY")
    private_key_path = os.environ.get("BINANCE_SPOT_PRIVATE_KEY_PATH") or os.environ.get("BINANCE_PRIVATE_KEY_PATH")

    if not api_key or not private_key_path:
        raise ValueError("Missing BINANCE_SPOT_API_KEY or BINANCE_API_KEY")

    with open(private_key_path, "rb") as f:
        private_key = f.read()

    return api_key, private_key


def create_client() -> BinanceSpotPrivateHTTPClient:
    """创建现货客户端"""
    api_key, private_key = load_credentials()
    # 从环境变量获取签名类型和代理
    signature_type = os.environ.get("BINANCE_SIGNATURE_TYPE", "rsa")
    proxy_url = os.environ.get("CLASH_PROXY_HTTP_URL", "http://127.0.0.1:7890")
    return BinanceSpotPrivateHTTPClient(
        api_key=api_key,
        private_key_pem=private_key,
        signature_type=signature_type,
        proxy_url=proxy_url,
    )


async def test_get_account_info():
    """测试获取账户信息"""
    client = create_client()
    print("\n=== 测试: 获取现货账户信息 ===")
    info = await client.get_account_info()
    print(f"  可交易: {info.can_trade}")
    print(f"  资产数量: {len(info.balances)}")
    # 显示余额
    for b in info.balances:
        if float(b.free) > 0 or float(b.locked) > 0:
            print(f"    {b.asset}: free={b.free}, locked={b.locked}")
    return info


async def test_market_buy():
    """测试市价买入 - 100 USDT"""
    client = create_client()
    print("\n=== 测试: 现货市价买入 100 USDT ===")

    # 使用 quoteOrderQty 指定USDT金额
    symbol = "BTCUSDT"
    quote_order_qty = 100.0  # 100 USDT

    try:
        result = await client.create_order(
            symbol=symbol,
            side="BUY",
            order_type="MARKET",
            quantity=None,  # 使用quoteOrderQty
            quote_order_qty=quote_order_qty,
            new_order_resp_type="FULL",
        )
        print(f"  订单ID: {result.get('orderId')}")
        print(f"  状态: {result.get('status')}")
        print(f"  成交数量: {result.get('executedQty')}")
        print(f"  成交均价: {result.get('cummulativeQuoteQty')}")
        return result
    except Exception as e:
        print(f"  错误: {e}")
        return None


async def test_market_sell():
    """测试市价卖出"""
    client = create_client()
    print("\n=== 测试: 现货市价卖出 ===")

    # 先获取一些BTC
    symbol = "BTCUSDT"
    quantity = 0.001  # 卖出少量BTC

    try:
        result = await client.create_order(
            symbol=symbol,
            side="SELL",
            order_type="MARKET",
            quantity=quantity,
            new_order_resp_type="FULL",
        )
        print(f"  订单ID: {result.get('orderId')}")
        print(f"  状态: {result.get('status')}")
        print(f"  成交数量: {result.get('executedQty')}")
        return result
    except Exception as e:
        print(f"  错误: {e}")
        return None


async def test_limit_order():
    """测试限价单 - 100 USDT"""
    client = create_client()
    print("\n=== 测试: 现货限价买入 100 USDT ===")

    symbol = "BTCUSDT"
    quantity = 0.001  # 约100 USDT
    price = 95000.0  # 设置高价确保不成交

    try:
        result = await client.create_order(
            symbol=symbol,
            side="BUY",
            order_type="LIMIT",
            quantity=quantity,
            price=price,
            time_in_force="GTC",
            new_order_resp_type="FULL",
        )
        print(f"  订单ID: {result.get('orderId')}")
        print(f"  状态: {result.get('status')}")
        print(f"  价格: {result.get('price')}")
        print(f"  数量: {result.get('origQty')}")
        return result
    except Exception as e:
        print(f"  错误: {e}")
        return None


async def test_cancel_order():
    """测试撤销订单"""
    client = create_client()
    print("\n=== 测试: 撤销订单 ===")

    # 先下一个限价单
    symbol = "BTCUSDT"
    quantity = 0.001
    price = 99000.0

    try:
        # 下限价单
        order_result = await client.create_order(
            symbol=symbol,
            side="BUY",
            order_type="LIMIT",
            quantity=quantity,
            price=price,
            time_in_force="GTC",
        )
        order_id = order_result.get("orderId")
        print(f"  下单成功，订单ID: {order_id}")

        # 等待一下
        await asyncio.sleep(1)

        # 撤销订单
        cancel_result = await client.cancel_order(
            symbol=symbol,
            order_id=str(order_id),
        )
        print(f"  撤销成功: {cancel_result.get('status')}")
        return cancel_result
    except Exception as e:
        print(f"  错误: {e}")
        return None


async def test_get_open_orders():
    """测试查询挂单"""
    client = create_client()
    print("\n=== 测试: 查询现货挂单 ===")

    try:
        orders = await client.get_open_orders(symbol="BTCUSDT")
        print(f"  挂单数量: {len(orders)}")
        for order in orders[:3]:
            print(f"    订单ID: {order.get('orderId')}, 类型: {order.get('side')} {order.get('type')}, 价格: {order.get('price')}, 状态: {order.get('status')}")
        return orders
    except Exception as e:
        print(f"  错误: {e}")
        return None


async def test_order():
    """测试查询订单"""
    client = create_client()
    print("\n=== 测试: 查询订单 ===")

    try:
        # 查询最近的一个订单
        orders = await client.get_all_orders(symbol="BTCUSDT", limit=1)
        if orders:
            order = orders[0]
            order_id = order.get("orderId")
            print(f"  查询订单ID: {order_id}")
            print(f"    状态: {order.get('status')}")
            print(f"    成交数量: {order.get('executedQty')}")

            # 用这个ID查询
            detail = await client.get_order(symbol="BTCUSDT", order_id=str(order_id))
            print(f"  订单详情: {detail.get('status')}")
        else:
            print("  没有历史订单")
        return orders
    except Exception as e:
        print(f"  错误: {e}")
        return None


async def main():
    """主函数"""
    print("=" * 50)
    print("现货交易功能测试 - Demo网")
    print("=" * 50)

    try:
        # 1. 获取账户信息
        await test_get_account_info()

        # 2. 测试限价单（先下后撤）
        await test_limit_order()
        await test_cancel_order()

        # 3. 查询挂单
        await test_get_open_orders()

        # 4. 查询订单
        await test_order()

        # 5. 测试市价单（实际成交）
        print("\n" + "=" * 50)
        print("注意: 即将执行真实市价单交易")
        print("=" * 50)
        await test_market_buy()

        # 再次获取余额
        print("\n=== 交易后余额 ===")
        await test_get_account_info()

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
