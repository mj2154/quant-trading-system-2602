"""
期货交易测试程序

测试期货下单功能，每次下单100 USDT。
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient


def load_credentials() -> tuple[str, bytes]:
    """加载API凭证"""
    load_dotenv()

    # 优先使用专用配置，否则使用通用配置
    api_key = os.environ.get("BINANCE_FUTURES_API_KEY") or os.environ.get("BINANCE_API_KEY")
    private_key_path = os.environ.get("BINANCE_FUTURES_PRIVATE_KEY_PATH") or os.environ.get("BINANCE_PRIVATE_KEY_PATH")

    if not api_key or not private_key_path:
        raise ValueError("Missing BINANCE_FUTURES_API_KEY or BINANCE_API_KEY")

    with open(private_key_path, "rb") as f:
        private_key = f.read()

    return api_key, private_key


def create_client() -> BinanceFuturesPrivateHTTPClient:
    """创建期货客户端"""
    api_key, private_key = load_credentials()
    # 从环境变量获取签名类型和代理
    signature_type = os.environ.get("BINANCE_SIGNATURE_TYPE", "rsa")
    proxy_url = os.environ.get("CLASH_PROXY_HTTP_URL", "http://127.0.0.1:7890")
    return BinanceFuturesPrivateHTTPClient(
        api_key=api_key,
        private_key_pem=private_key,
        signature_type=signature_type,
        proxy_url=proxy_url,
    )


async def test_get_balance():
    """测试获取余额"""
    client = create_client()
    print("\n=== 测试: 获取账户余额 ===")
    balances = await client.get_balance()
    for b in balances:
        if float(b.get("balance", 0)) > 0:
            print(f"  {b['asset']}: {b['balance']}")
    return balances


async def test_get_account_info():
    """测试获取账户信息"""
    client = create_client()
    print("\n=== 测试: 获取账户信息 ===")
    info = await client.get_account_info()
    print(f"  钱包余额: {info.total_wallet_balance}")
    print(f"  保证金余额: {info.total_margin_balance}")
    print(f"  可用余额: {info.available_balance}")
    print(f"  资产数量: {len(info.assets)}")
    return info


async def test_market_buy():
    """测试市价买入 - 100 USDT"""
    client = create_client()
    print("\n=== 测试: 期货市价买入 100 USDT ===")

    # 获取当前价格来计算数量
    # 假设BTCUSDT价格约50000，100 USDT可买0.002 BTC
    symbol = "BTCUSDT"
    quantity = 0.002  # 约100 USDT

    try:
        result = await client.create_order(
            symbol=symbol,
            side="BUY",
            order_type="MARKET",
            quantity=quantity,
            new_order_resp_type="RESULT",
        )
        print(f"  订单ID: {result.get('orderId')}")
        print(f"  状态: {result.get('status')}")
        print(f"  成交数量: {result.get('executedQty')}")
        print(f"  成交均价: {result.get('avgPrice')}")
        return result
    except Exception as e:
        print(f"  错误: {e}")
        return None


async def test_market_sell():
    """测试市价卖出"""
    client = create_client()
    print("\n=== 测试: 期货市价卖出 ===")

    symbol = "BTCUSDT"
    quantity = 0.002

    try:
        result = await client.create_order(
            symbol=symbol,
            side="SELL",
            order_type="MARKET",
            quantity=quantity,
            new_order_resp_type="RESULT",
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
    print("\n=== 测试: 期货限价买入(低于市价) ===")

    symbol = "BTCUSDT"
    # 期货最小下单金额100 USDT，当前价格约66000，需要至少0.002 BTC
    quantity = 0.002
    price = 50000.0  # 设置低于市价的价格，应该会立即成交

    try:
        print(f"  尝试下单: {symbol}, 数量: {quantity}, 价格: {price}")

        result = await client.create_order(
            symbol=symbol,
            side="BUY",
            order_type="LIMIT",
            quantity=quantity,
            price=price,
            time_in_force="GTC",
            new_order_resp_type="RESULT",
        )
        print(f"  订单ID: {result.get('orderId')}")
        print(f"  状态: {result.get('status')}")
        print(f"  价格: {result.get('price')}")
        print(f"  数量: {result.get('origQty')}")
        print(f"  成交数量: {result.get('executedQty')}")
        return result
    except Exception as e:
        # 打印详细错误信息
        print(f"  错误: {e}")
        if hasattr(e, 'response'):
            try:
                error_data = e.response.json()
                print(f"  详细错误: {error_data}")
            except:
                pass
        return None


async def test_cancel_order():
    """测试撤销订单"""
    client = create_client()
    print("\n=== 测试: 撤销订单 ===")

    # 先下一个低于市价的限价单，确保不会成交
    # 期货最小下单金额100 USDT
    symbol = "BTCUSDT"
    quantity = 0.002  # 0.002 * 50000 = 100 USDT
    price = 50000.0  # 使用合理价格

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
        print(f"  下单成功，订单ID: {order_id}, 状态: {order_result.get('status')}")

        # 等待一下
        await asyncio.sleep(0.5)

        # 撤销订单
        cancel_result = await client.cancel_order(
            symbol=symbol,
            order_id=str(order_id),
        )
        print(f"  撤销成功: {cancel_result.get('status')}")
        print(f"  订单ID: {cancel_result.get('orderId')}")
        return cancel_result
    except Exception as e:
        print(f"  错误: {e}")
        if hasattr(e, 'response'):
            try:
                error_data = e.response.json()
                print(f"  详细错误: {error_data}")
            except:
                pass
        return None


async def test_get_open_orders():
    """测试查询挂单"""
    client = create_client()
    print("\n=== 测试: 查询挂单 ===")

    try:
        orders = await client.get_open_orders(symbol="BTCUSDT")
        print(f"  挂单数量: {len(orders)}")
        for order in orders[:3]:
            print(f"    订单ID: {order.get('orderId')}, 类型: {order.get('side')} {order.get('type')}, 价格: {order.get('price')}, 状态: {order.get('status')}")
        return orders
    except Exception as e:
        print(f"  错误: {e}")
        return None


async def test_set_leverage():
    """测试设置杠杆"""
    client = create_client()
    print("\n=== 测试: 设置杠杆 ===")

    try:
        result = await client.set_leverage(
            symbol="BTCUSDT",
            leverage=20,
        )
        print(f"  设置成功: 杠杆 {result.get('leverage')}")
        return result
    except Exception as e:
        print(f"  错误: {e}")
        return None


async def main():
    """主函数"""
    print("=" * 50)
    print("期货交易功能测试 - Demo网")
    print("=" * 50)

    try:
        # 1. 获取账户信息
        await test_get_balance()
        await test_get_account_info()

        # 2. 设置杠杆
        await test_set_leverage()

        # 3. 测试限价单（先下后撤）
        await test_limit_order()
        await test_cancel_order()

        # 4. 查询挂单
        await test_get_open_orders()

        # 5. 测试市价单（实际成交）
        print("\n" + "=" * 50)
        print("注意: 即将执行真实市价单交易")
        print("=" * 50)
        await test_market_buy()

        # 再次获取余额
        print("\n=== 交易后余额 ===")
        await test_get_balance()

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
