#!/usr/bin/env python3
"""
测试交易所信息全量替换功能

演示如何使用 ExchangeInfoRepository 的 replace_exchange_infos 方法
来确保数据库中的交易所信息与币安API完全一致。
"""

import asyncio
import asyncpg
import os
from typing import List

# 导入ExchangeInfo模型
from src.models.exchange_info import ExchangeInfo, MarketType


async def test_replace_exchange_infos():
    """测试全量替换交易所信息功能"""

    # 数据库连接配置
    DSN = os.getenv(
        "DATABASE_DSN",
        "postgresql://dbuser:pass@localhost:5432/trading_db"
    )

    # 创建连接池
    pool = await asyncpg.create_pool(DSN, min_size=1, max_size=1)

    try:
        # 创建 ExchangeInfoRepository 实例
        from src.storage.exchange_repository import ExchangeInfoRepository
        repo = ExchangeInfoRepository(pool)

        print("=== 测试全量替换交易所信息功能 ===\n")

        # 1. 先查询现有数据
        print("1. 查询现有数据")
        current_spot = await repo.get_all_trading(
            exchange="BINANCE",
            market_type=MarketType.SPOT
        )
        current_futures = await repo.get_all_trading(
            exchange="BINANCE",
            market_type=MarketType.FUTURES
        )
        print(f"   现货交易对数量: {len(current_spot)}")
        print(f"   期货交易对数量: {len(current_futures)}")

        # 2. 创建模拟数据
        print("\n2. 创建模拟数据")
        mock_infos = create_mock_exchange_infos()
        print(f"   模拟现货数据: {len(mock_infos['spot'])} 条")
        print(f"   模拟期货数据: {len(mock_infos['futures'])} 条")

        # 3. 执行全量替换（现货）
        print("\n3. 执行现货数据全量替换")
        replaced_count = await repo.replace_exchange_infos(
            infos=mock_infos['spot'],
            exchange="BINANCE",
            market_type=MarketType.SPOT
        )
        print(f"   替换结果: {replaced_count} 条记录")

        # 4. 执行全量替换（期货）
        print("\n4. 执行期货数据全量替换")
        replaced_count = await repo.replace_exchange_infos(
            infos=mock_infos['futures'],
            exchange="BINANCE",
            market_type=MarketType.FUTURES
        )
        print(f"   替换结果: {replaced_count} 条记录")

        # 5. 验证结果
        print("\n5. 验证替换结果")
        new_spot = await repo.get_all_trading(
            exchange="BINANCE",
            market_type=MarketType.SPOT
        )
        new_futures = await repo.get_all_trading(
            exchange="BINANCE",
            market_type=MarketType.FUTURES
        )
        print(f"   替换后现货交易对数量: {len(new_spot)}")
        print(f"   替换后期货交易对数量: {len(new_futures)}")

        # 6. 显示一些示例数据
        print("\n6. 示例数据（现货前5个）")
        for i, info in enumerate(new_spot[:5]):
            print(f"   {i+1}. {info.symbol} - {info.base_asset}/{info.quote_asset}")

        print("\n=== 测试完成 ===")
        print("\n重要说明:")
        print("- 全量替换会先删除旧数据，再插入新数据")
        print("- 这确保数据库中的信息与API完全一致")
        print("- 当交易对从API中移除时，数据库中也不会保留过时数据")

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await pool.close()


def create_mock_exchange_infos() -> dict[str, List[ExchangeInfo]]:
    """创建模拟的交易所信息数据"""

    spot_data = [
        ExchangeInfo(
            exchange="BINANCE",
            market_type=MarketType.SPOT,
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            price_precision=8,
            quantity_precision=8,
            status="TRADING",
            filters={},
            order_types=["LIMIT", "MARKET"],
            permissions=["SPOT"],
            iceberg_allowed=True,
            oco_allowed=True,
        ),
        ExchangeInfo(
            exchange="BINANCE",
            market_type=MarketType.SPOT,
            symbol="ETHUSDT",
            base_asset="ETH",
            quote_asset="USDT",
            price_precision=8,
            quantity_precision=8,
            status="TRADING",
            filters={},
            order_types=["LIMIT", "MARKET"],
            permissions=["SPOT"],
            iceberg_allowed=True,
            oco_allowed=True,
        ),
        ExchangeInfo(
            exchange="BINANCE",
            market_type=MarketType.SPOT,
            symbol="ADAUSDT",
            base_asset="ADA",
            quote_asset="USDT",
            price_precision=8,
            quantity_precision=8,
            status="TRADING",
            filters={},
            order_types=["LIMIT", "MARKET"],
            permissions=["SPOT"],
            iceberg_allowed=True,
            oco_allowed=True,
        ),
    ]

    futures_data = [
        ExchangeInfo(
            exchange="BINANCE",
            market_type=MarketType.FUTURES,
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            price_precision=8,
            quantity_precision=8,
            status="TRADING",
            filters={},
            order_types=["LIMIT", "MARKET", "STOP"],
            permissions=["TRD_GRP_001"],
            iceberg_allowed=True,
            oco_allowed=False,
        ),
        ExchangeInfo(
            exchange="BINANCE",
            market_type=MarketType.FUTURES,
            symbol="ETHUSDT",
            base_asset="ETH",
            quote_asset="USDT",
            price_precision=8,
            quantity_precision=8,
            status="TRADING",
            filters={},
            order_types=["LIMIT", "MARKET", "STOP"],
            permissions=["TRD_GRP_001"],
            iceberg_allowed=True,
            oco_allowed=False,
        ),
    ]

    return {
        "spot": spot_data,
        "futures": futures_data,
    }


if __name__ == "__main__":
    asyncio.run(test_replace_exchange_infos())
