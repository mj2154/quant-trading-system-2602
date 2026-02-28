#!/usr/bin/env python3
"""
交易所信息全量替换示例

演示如何使用 ExchangeInfoHandler 的全量替换功能来同步交易所信息。
这个脚本可以在系统启动时或定期执行，以确保数据一致性。
"""

import asyncio
import os
import sys
from typing import Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.binance_service.src.events.exchange_info_handler import ExchangeInfoHandler
from services.binance_service.src.storage import ExchangeInfoRepository
from services.binance_service.src.clients import (
    BinanceSpotHTTPClient,
    BinanceFuturesHTTPClient,
)


async def sync_exchange_info_example():
    """示例：如何同步交易所信息"""

    print("=" * 60)
    print("交易所信息全量替换示例")
    print("=" * 60)

    # 1. 配置数据库连接
    DSN = os.getenv(
        "DATABASE_DSN",
        "postgresql://dbuser:pass@localhost:5432/trading_db"
    )

    print(f"\n1. 数据库连接: {DSN[:30]}...")

    # 2. 创建 HTTP 客户端
    proxy_http = os.getenv("CLASH_PROXY_HTTP_URL")

    print(f"2. HTTP 代理: {'已配置' if proxy_http else '未使用'}")

    spot_http = BinanceSpotHTTPClient(proxy_url=proxy_http)
    futures_http = BinanceFuturesHTTPClient(proxy_url=proxy_http)

    # 3. 创建 ExchangeInfoHandler
    print("\n3. 初始化 ExchangeInfoHandler...")

    # 注意：这里只是演示如何创建 ExchangeInfoHandler
    # 实际使用时，需要创建数据库连接池和 ExchangeInfoRepository
    handler = ExchangeInfoHandler(
        spot_http=spot_http,
        futures_http=futures_http,
        exchange_repo=None,  # 实际使用时需要传入实际的 repository
    )

    print("   ✓ ExchangeInfoHandler 已创建")

    # 4. 演示如何调用同步功能
    print("\n4. 同步交易所信息...")

    # 示例 1: 同步现货信息
    print("\n   4.1 同步现货交易所信息")
    try:
        # 这里需要实际的数据库连接池
        # await handler._sync_spot_exchange_info()
        print("      调用 _sync_spot_exchange_info()")
        print("      将会执行：")
        print("        1. 从币安现货 API 获取最新数据")
        print("        2. 删除旧的现货交易所信息")
        print("        3. 插入新的现货交易所信息")
        print("      ⚡ 数据一致性保证：旧数据会被完全替换")
    except Exception as e:
        print(f"      ✗ 同步失败: {e}")

    # 示例 2: 同步期货信息
    print("\n   4.2 同步期货交易所信息")
    try:
        # await handler._sync_futures_exchange_info()
        print("      调用 _sync_futures_exchange_info()")
        print("      将会执行：")
        print("        1. 从币安期货 API 获取最新数据")
        print("        2. 删除旧的期货交易所信息")
        print("        3. 插入新的期货交易所信息")
        print("      ⚡ 数据一致性保证：旧数据会被完全替换")
    except Exception as e:
        print(f"      ✗ 同步失败: {e}")

    # 示例 3: 同时同步现货和期货
    print("\n   4.3 同时同步现货和期货")
    try:
        # await handler.handle_fetch_exchange_info(
        #     action="system.fetch_exchange_info",
        #     resource="BINANCE",
        #     params={"mode": "all"}
        # )
        print("      调用 handle_fetch_exchange_info(mode='all')")
        print("      将会执行：")
        print("        1. 同步现货交易所信息（全量替换）")
        print("        2. 同步期货交易所信息（全量替换）")
        print("      ⚡ 数据一致性保证：确保现货和期货数据都是最新的")
    except Exception as e:
        print(f"      ✗ 同步失败: {e}")

    # 5. 关闭客户端
    await spot_http.close()
    await futures_http.close()

    print("\n" + "=" * 60)
    print("示例完成")
    print("=" * 60)

    # 6. 总结
    print("\n📊 功能总结:")
    print("   • 全量替换确保数据库与 API 完全一致")
    print("   • 自动清理已移除的交易对")
    print("   • 在数据库事务中执行，保证原子性")
    print("   • 适用于数据一致性要求高的场景")

    print("\n🔧 实际使用:")
    print("   • 在系统启动时执行一次")
    print("   • 定期执行（如每天）")
    print("   • 在检测到数据不一致时执行")

    print("\n⚠️  注意事项:")
    print("   • 需要有效的数据库连接池")
    print("   • 需要配置币安 API 访问（代理）")
    print("   • 全量替换会删除所有旧数据")
    print("   • 适合数千级别的交易对数量")


def print_comparison():
    """对比增量更新和全量替换的区别"""

    print("\n" + "=" * 60)
    print("增量更新 vs 全量替换对比")
    print("=" * 60)

    comparison_data = [
        ("对比项", "增量更新 (upsert)", "全量替换 (replace)"),
        ("数据一致性", "可能保留过期数据", "完全同步，无过期数据"),
        ("数据清理", "需要手动清理", "自动清理过期数据"),
        ("性能开销", "较低", "较高（删除+插入）"),
        ("实现复杂度", "较简单", "较简单"),
        ("适用场景", "交易对数量很大", "数据一致性要求高"),
        ("错误处理", "较复杂", "简单（事务保证）"),
        ("适用规模", "数万级", "数千级"),
    ]

    # 打印表格
    col_widths = [20, 30, 30]
    for row in comparison_data:
        print(
            f"  {row[0]:<{col_widths[0]}} {row[1]:<{col_widths[1]}} {row[2]:<{col_widths[1]}}"
        )
        if row[0] == "对比项":
            print("  " + "-" * sum(col_widths))

    print("\n💡 建议:")
    print("   • 如果交易对数量 < 5000，建议使用全量替换")
    print("   • 如果交易对数量 > 50000，建议使用增量更新")
    print("   • 量化交易系统通常追求数据一致性，推荐全量替换")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(sync_exchange_info_example())

    # 显示对比
    print_comparison()
