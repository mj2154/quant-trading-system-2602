"""
测试现货用户数据流订阅 - 订阅账户信息更新

测试流程：
1. 创建 BinanceSpotPrivateWSClient 并认证（使用 start()）
2. 调用 subscribe_user_data_stream() 订阅用户数据流
3. 设置数据回调，接收 outboundAccountPosition, balanceUpdate, executionReport 事件
4. 打印收到的数据
5. 调用 unsubscribe_user_data_stream() 取消订阅

【重要】此测试必须在 Docker 容器中运行！

运行方式：
    docker exec -it binance-service /bin/bash
    cd /app
    uv run python test_spot_user_stream_subscription.py
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径
service_dir = Path(__file__).parent
sys.path.insert(0, str(service_dir / "src"))
sys.path.insert(0, str(service_dir))

# 加载.env文件
load_dotenv()


def load_private_key(key_path: str) -> bytes:
    """加载PEM格式私钥"""
    with open(key_path, "rb") as f:
        return f.read()


async def test_spot_user_stream_subscription():
    """测试现货用户数据流订阅"""

    print("=" * 70)
    print("测试现货用户数据流订阅 - 账户信息更新（集成版）")
    print("=" * 70)

    # ========== 1. 获取 API 凭证 ==========
    api_key = os.environ.get("BINANCE_API_KEY")
    if not api_key:
        print("错误: 请设置 BINANCE_API_KEY 环境变量")
        return False

    # 私钥路径
    key_path = os.environ.get("BINANCE_PRIVATE_KEY_PATH", "/app/keys/private_key.pem")
    key_path = Path(key_path)

    if not key_path.exists():
        print(f"错误: 私钥文件不存在: {key_path}")
        return False

    private_key_pem = load_private_key(str(key_path))

    # 代理配置（Docker中使用 clash-proxy）
    proxy_url = os.environ.get("CLASH_PROXY_WS_URL", "http://clash-proxy:7890")

    print(f"\n[配置]")
    print(f"  API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"  私钥: {key_path}")
    print(f"  代理: {proxy_url}")
    print(f"  WebSocket: wss://demo-ws-api.binance.com/ws-api/v3")

    # ========== 2. 创建 BinanceSpotPrivateWSClient 并认证 ==========
    print(f"\n[步骤1] 创建 BinanceSpotPrivateWSClient 并认证...")

    from clients.spot_private_ws_client import BinanceSpotPrivateWSClient

    private_ws_client = BinanceSpotPrivateWSClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        proxy_url=proxy_url,
    )

    try:
        # 使用 start() 统一初始化（连接 + session.logon 认证）
        print("  正在连接并认证 (session.logon)...")
        auth_success = await private_ws_client.start()
        if not auth_success:
            print("  错误: session.logon 认证失败")
            return False
        print("  成功: session.logon 认证通过")

        # ========== 3. 订阅用户数据流 ==========
        print(f"\n[步骤2] 订阅用户数据流 (userDataStream.subscribe)...")

        # 统计收到的消息
        message_count = {
            "outboundAccountPosition": 0,
            "balanceUpdate": 0,
            "executionReport": 0,
            "unknown": 0
        }

        async def on_account_update(package):
            """账户数据回调

            现货事件格式：{"subscriptionId": 0, "event": {...}}
            事件类型：outboundAccountPosition, balanceUpdate, executionReport
            """
            # 提取 event 字段
            event_wrapper = package.data
            event_data = event_wrapper.get("event", {})
            event_type = event_data.get("e", "unknown")
            message_count[event_type] = message_count.get(event_type, 0) + 1

            print(f"\n{'='*70}")
            print(f"[收到事件] {event_type}")
            print(f"{'='*70}")

            if event_type == "outboundAccountPosition":
                print("\n[账户位置更新事件]")
                print(f"  事件时间: {event_data.get('E')}")
                print(f"  更新时间: {event_data.get('u')}")

                # 余额列表
                balances = event_data.get("B", [])
                if balances:
                    print(f"  余额列表 ({len(balances)} 项):")
                    for bal in balances:
                        print(f"    - {bal.get('a')}: "
                              f"可用={bal.get('f')}, "
                              f"冻结={bal.get('l')}, "
                              f"报价={bal.get('r')}")

            elif event_type == "balanceUpdate":
                print("\n[余额更新事件]")
                print(f"  事件时间: {event_data.get('E')}")
                print(f"  资产名称: {event_data.get('a')}")
                print(f"  余额变更: {event_data.get('d')}")
                print(f"  余额类型: {event_data.get('T')}")

            elif event_type == "executionReport":
                print("\n[订单执行报告事件]")
                print(f"  事件时间: {event_data.get('E')}")
                print(f"  交易对: {event_data.get('s')}")
                print(f"  订单ID: {event_data.get('i')}")
                print(f"  客户端订单ID: {event_data.get('c')}")
                print(f"  订单方向: {event_data.get('S')}")  # BUY/SELL
                print(f"  订单类型: {event_data.get('o')}")  # MARKET/LIMIT/...
                print(f"  订单状态: {event_data.get('x')}")  # NEW/CANCELED/FILLED/...
                print(f"  成交数量: {event_data.get('l')}")
                print(f"  成交价格: {event_data.get('L')}")
                print(f"  累计成交数量: {event_data.get('z')}")
                print(f"  成交金额: {event_data.get('n')} {event_data.get('N')}")

            else:
                print(f"\n[原始数据]")
                print(json.dumps(package.data, indent=2))

            print(f"\n[统计] outboundAccountPosition={message_count['outboundAccountPosition']}, "
                  f"balanceUpdate={message_count['balanceUpdate']}, "
                  f"executionReport={message_count['executionReport']}")

        # 设置断连回调（当连接断开时触发）
        async def on_reconnect():
            print("\n[断连回调] 连接已断开，将触发重连")

        private_ws_client.set_reconnect_callback(on_reconnect)

        # 调用统一的订阅接口
        success = await private_ws_client.subscribe_user_data_stream(callback=on_account_update)
        if not success:
            print("  错误: 用户数据流订阅失败")
            return False
        print("  成功: userDataStream.subscribe 请求已发送")

        # ========== 4. 等待接收数据 ==========
        print(f"\n[步骤3] 等待接收数据... (超时 30 秒)")
        print("  (将持续接收账户更新事件，按 Ctrl+C 停止)\n")
        print("  提示: 请在测试期间在币安现货账户进行交易操作（如下单、充值等）")

        # 等待 30 秒，期间可以手动下单或查看账户变化
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            print("\n  等待被取消")

        # ========== 5. 取消订阅 ==========
        print(f"\n[步骤4] 取消订阅...")

        await private_ws_client.unsubscribe_user_data_stream()
        print("  用户数据流已取消订阅")

        # ========== 6. 清理 ==========
        print(f"\n[步骤5] 清理...")

        await private_ws_client.stop()
        print("  私有WebSocket已停止")

        # ========== 7. 打印统计 ==========
        print(f"\n{'='*70}")
        print("测试完成")
        print(f"{'='*70}")
        print(f"\n[统计结果]")
        print(f"  outboundAccountPosition 事件: {message_count['outboundAccountPosition']} 次")
        print(f"  balanceUpdate 事件: {message_count['balanceUpdate']} 次")
        print(f"  executionReport 事件: {message_count['executionReport']} 次")

        total_events = (message_count['outboundAccountPosition'] +
                       message_count['balanceUpdate'] +
                       message_count['executionReport'])

        if total_events > 0:
            print("\n✓ 测试通过! 成功接收账户更新数据")
            return True
        else:
            print("\n! 提示: 未收到任何账户更新事件")
            print("  这可能是因为测试期间没有账户变化（如下单、充值等）")
            print("  请确保账户有持仓或挂单，或在测试期间进行交易操作")
            return True  # 不算失败，只是没收到事件

    except Exception as e:
        print(f"\n异常: {e}")
        import traceback
        traceback.print_exc()

        try:
            await private_ws_client.stop()
        except:
            pass

        return False


async def main():
    """主函数"""
    print("\n测试开始时间:", time.strftime("%Y-%m-%d %H:%M:%S"))

    success = await test_spot_user_stream_subscription()

    print("\n测试结束时间:", time.strftime("%Y-%m-%d %H:%M:%S"))

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
