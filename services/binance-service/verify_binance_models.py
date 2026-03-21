"""
验证币安数据模型是否与官方文档一致

通过实际调用币安API获取真实数据，然后用文档中定义的模型进行解析验证。
"""

import asyncio
import json
import os
from decimal import Decimal
from typing import Any

import httpx

# 使用环境变量中的代理配置
PROXY_URL = os.environ.get("CLASH_PROXY_HTTP_URL", "http://clash-proxy:7890")

# ============== 文档中的模型定义 ==============

from pydantic import BaseModel, ConfigDict, Field


class BinanceSpotKlineGetModel(BaseModel):
    """现货 K线 GET 响应模型 - 文档定义"""

    open_time: int = Field(alias="0")
    open_price: Decimal = Field(alias="1")
    high_price: Decimal = Field(alias="2")
    low_price: Decimal = Field(alias="3")
    close_price: Decimal = Field(alias="4")
    volume: Decimal = Field(alias="5")
    close_time: int = Field(alias="6")
    quote_volume: Decimal = Field(alias="7")
    number_of_trades: int = Field(alias="8")
    taker_buy_base_volume: Decimal = Field(alias="9")
    taker_buy_quote_volume: Decimal = Field(alias="10")
    unused: str = Field(alias="11")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotKlineWSData(BaseModel):
    """现货 K线 WS 内部数据模型 - 文档定义"""

    open_time: int = Field(alias="t")
    close_time: int = Field(alias="T")
    symbol: str = Field(alias="s")
    interval: str = Field(alias="i")
    first_trade_id: int = Field(alias="f")
    last_trade_id: int = Field(alias="L")
    open_price: Decimal = Field(alias="o")
    close_price: Decimal = Field(alias="c")
    high_price: Decimal = Field(alias="h")
    low_price: Decimal = Field(alias="l")
    volume: Decimal = Field(alias="v")
    number_of_trades: int = Field(alias="n")
    is_closed: bool = Field(alias="x")
    quote_volume: Decimal = Field(alias="q")
    taker_buy_base_volume: Decimal = Field(alias="V")
    taker_buy_quote_volume: Decimal = Field(alias="Q")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotKlineWSModel(BaseModel):
    """现货 K线 WS 事件模型 - 文档定义"""

    event_type: str = Field(alias="e")
    event_time: int = Field(alias="E")
    symbol: str = Field(alias="s")
    kline: BinanceSpotKlineWSData = Field(alias="k")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotTicker24hrGetModel(BaseModel):
    """现货 24hr Ticker GET 响应模型 - 文档定义"""

    symbol: str = Field()
    price_change: Decimal = Field(alias="priceChange")
    price_change_percent: Decimal = Field(alias="priceChangePercent")
    weighted_avg_price: Decimal = Field(alias="weightedAvgPrice")
    prev_close_price: Decimal = Field(alias="prevClosePrice")
    last_price: Decimal = Field(alias="lastPrice")
    last_qty: Decimal = Field(alias="lastQty")
    bid_price: Decimal = Field(alias="bidPrice")
    bid_qty: Decimal = Field(alias="bidQty")
    ask_price: Decimal = Field(alias="askPrice")
    ask_qty: Decimal = Field(alias="askQty")
    open_price: Decimal = Field(alias="openPrice")
    high_price: Decimal = Field(alias="highPrice")
    low_price: Decimal = Field(alias="lowPrice")
    volume: Decimal = Field()
    quote_volume: Decimal = Field(alias="quoteVolume")
    open_time: int = Field(alias="openTime")
    close_time: int = Field(alias="closeTime")
    first_id: int = Field(alias="firstId")
    last_id: int = Field(alias="lastId")
    count: int = Field()

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotTicker24hrWSModel(BaseModel):
    """现货 24hr Ticker WS 事件模型 - 文档定义"""

    event_type: str = Field(alias="e")
    event_time: int = Field(alias="E")
    symbol: str = Field(alias="s")
    price_change: Decimal = Field(alias="p")
    price_change_percent: Decimal = Field(alias="P")
    weighted_avg_price: Decimal = Field(alias="w")
    first_price: Decimal = Field(alias="x")
    last_price: Decimal = Field(alias="c")
    last_qty: Decimal = Field(alias="Q")
    best_bid_price: Decimal = Field(alias="b")
    best_bid_qty: Decimal = Field(alias="B")
    best_ask_price: Decimal = Field(alias="a")
    best_ask_qty: Decimal = Field(alias="A")
    open_price: Decimal = Field(alias="o")
    high_price: Decimal = Field(alias="h")
    low_price: Decimal = Field(alias="l")
    volume: Decimal = Field(alias="v")
    quote_volume: Decimal = Field(alias="q")
    open_time: int = Field(alias="O")
    close_time: int = Field(alias="C")
    first_trade_id: int = Field(alias="F")
    last_trade_id: int = Field(alias="L")
    number_of_trades: int = Field(alias="n")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesKlineGetModel(BaseModel):
    """期货 K线 GET 响应模型 - 文档定义"""

    open_time: int = Field(alias="0")
    open_price: Decimal = Field(alias="1")
    high_price: Decimal = Field(alias="2")
    low_price: Decimal = Field(alias="3")
    close_price: Decimal = Field(alias="4")
    volume: Decimal = Field(alias="5")
    close_time: int = Field(alias="6")
    quote_volume: Decimal = Field(alias="7")
    number_of_trades: int = Field(alias="8")
    taker_buy_base_volume: Decimal = Field(alias="9")
    taker_buy_quote_volume: Decimal = Field(alias="10")
    unused: str = Field(alias="11")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesKlineWSData(BaseModel):
    """期货 K线 WS 内部数据模型 - 文档定义"""

    open_time: int = Field(alias="t")
    close_time: int = Field(alias="T")
    symbol: str = Field(alias="s")
    interval: str = Field(alias="i")
    first_trade_id: int = Field(alias="f")
    last_trade_id: int = Field(alias="L")
    open_price: Decimal = Field(alias="o")
    close_price: Decimal = Field(alias="c")
    high_price: Decimal = Field(alias="h")
    low_price: Decimal = Field(alias="l")
    volume: Decimal = Field(alias="v")
    number_of_trades: int = Field(alias="n")
    is_closed: bool = Field(alias="x")
    quote_volume: Decimal = Field(alias="q")
    taker_buy_base_volume: Decimal = Field(alias="V")
    taker_buy_quote_volume: Decimal = Field(alias="Q")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesKlineWSModel(BaseModel):
    """期货 K线 WS 事件模型 - 文档定义"""

    event_type: str = Field(alias="e")
    event_time: int = Field(alias="E")
    symbol: str = Field(alias="s")
    kline: BinanceFuturesKlineWSData = Field(alias="k")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesTicker24hrGetModel(BaseModel):
    """期货 24hr Ticker GET 响应模型 - 文档定义"""

    symbol: str = Field()
    price_change: Decimal = Field(alias="priceChange")
    price_change_percent: Decimal = Field(alias="priceChangePercent")
    weighted_avg_price: Decimal = Field(alias="weightedAvgPrice")
    last_price: Decimal = Field(alias="lastPrice")
    last_qty: Decimal = Field(alias="lastQty")
    open_price: Decimal = Field(alias="openPrice")
    high_price: Decimal = Field(alias="highPrice")
    low_price: Decimal = Field(alias="lowPrice")
    volume: Decimal = Field()
    quote_volume: Decimal = Field(alias="quoteVolume")
    open_time: int = Field(alias="openTime")
    close_time: int = Field(alias="closeTime")
    first_id: int = Field(alias="firstId")
    last_id: int = Field(alias="lastId")
    count: int = Field()

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesTicker24hrWSModel(BaseModel):
    """期货 24hr Ticker WS 事件模型 - 文档定义"""

    event_type: str = Field(alias="e")
    event_time: int = Field(alias="E")
    symbol: str = Field(alias="s")
    price_change: Decimal = Field(alias="p")
    price_change_percent: Decimal = Field(alias="P")
    weighted_avg_price: Decimal = Field(alias="w")
    last_price: Decimal = Field(alias="c")
    last_qty: Decimal = Field(alias="Q")
    open_price: Decimal = Field(alias="o")
    high_price: Decimal = Field(alias="h")
    low_price: Decimal = Field(alias="l")
    volume: Decimal = Field(alias="v")
    quote_volume: Decimal = Field(alias="q")
    open_time: int = Field(alias="O")
    close_time: int = Field(alias="C")
    first_trade_id: int = Field(alias="F")
    last_trade_id: int = Field(alias="L")
    number_of_trades: int = Field(alias="n")

    model_config = ConfigDict(populate_by_name=True)


# ============== 验证函数 ==============

async def verify_spot_kline_get():
    """验证现货 K线 GET"""
    print("\n" + "=" * 60)
    print("验证现货 K线 GET (GET /api/v3/klines)")
    print("=" * 60)

    async with httpx.AsyncClient(proxy=PROXY_URL) as client:
        resp = await client.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": "BTCUSDT", "interval": "1m", "limit": 1},
            timeout=10.0,
        )
        data = resp.json()

    print(f"API响应类型: {type(data)}")
    print(f"数据条数: {len(data)}")
    print(f"第一条数据: {json.dumps(data[0], indent=2)}")

    # 验证：文档说数组格式，按索引访问
    # 需要将数组转为字典 {"0": ..., "1": ...}
    try:
        raw = data[0]
        dict_data = {str(i): v for i, v in enumerate(raw)}
        model = BinanceSpotKlineGetModel.model_validate(dict_data)
        print(f"\n✅ 解析成功!")
        print(f"   open_time: {model.open_time}")
        print(f"   open_price: {model.open_price}")
        print(f"   high_price: {model.high_price}")
        print(f"   low_price: {model.low_price}")
        print(f"   close_price: {model.close_price}")
        print(f"   volume: {model.volume}")
        return True
    except Exception as e:
        print(f"\n❌ 解析失败: {e}")
        return False


async def verify_spot_kline_ws():
    """验证现货 K线 WS - 需要 WebSocket 连接"""
    print("\n" + "=" * 60)
    print("验证现货 K线 WS (<symbol>@kline_<interval>)")
    print("=" * 60)
    print("⚠️  WebSocket 验证需要建立连接，这里跳过")
    print("   请参考文档中的示例数据手动验证")
    return None


async def verify_spot_ticker_24hr_get():
    """验证现货 24hr Ticker GET"""
    print("\n" + "=" * 60)
    print("验证现货 24hr Ticker GET (GET /api/v3/ticker/24hr)")
    print("=" * 60)

    async with httpx.AsyncClient(proxy=PROXY_URL) as client:
        resp = await client.get(
            "https://api.binance.com/api/v3/ticker/24hr",
            params={"symbol": "BTCUSDT"},
            timeout=10.0,
        )
        data = resp.json()

    print(f"API响应字段: {list(data.keys())}")
    print(f"响应数据: {json.dumps(data, indent=2)}")

    try:
        model = BinanceSpotTicker24hrGetModel.model_validate(data)
        print(f"\n✅ 解析成功!")
        print(f"   symbol: {model.symbol}")
        print(f"   price_change: {model.price_change}")
        print(f"   price_change_percent: {model.price_change_percent}")
        print(f"   bid_price: {model.bid_price}")
        print(f"   ask_price: {model.ask_price}")
        return True
    except Exception as e:
        print(f"\n❌ 解析失败: {e}")
        return False


async def verify_spot_ticker_24hr_ws():
    """验证现货 24hr Ticker WS"""
    print("\n" + "=" * 60)
    print("验证现货 24hr Ticker WS (<symbol>@ticker)")
    print("=" * 60)
    print("⚠️  WebSocket 验证需要建立连接，这里跳过")
    print("   请参考文档中的示例数据手动验证")
    return None


async def verify_futures_kline_get():
    """验证期货 K线 GET"""
    print("\n" + "=" * 60)
    print("验证期货 K线 GET (GET /fapi/v1/klines)")
    print("=" * 60)

    async with httpx.AsyncClient(proxy=PROXY_URL) as client:
        resp = await client.get(
            "https://fapi.binance.com/fapi/v1/klines",
            params={"symbol": "BTCUSDT", "interval": "1m", "limit": 1},
            timeout=10.0,
        )
        data = resp.json()

    print(f"API响应类型: {type(data)}")
    print(f"数据条数: {len(data)}")
    print(f"第一条数据: {json.dumps(data[0], indent=2)}")

    # 注意：期货GET K线有12个字段，现货也有12个，都有unused字段
    print(f"\n字段数量: {len(data[0])}")

    try:
        raw = data[0]
        dict_data = {str(i): v for i, v in enumerate(raw)}
        model = BinanceFuturesKlineGetModel.model_validate(dict_data)
        print(f"\n✅ 解析成功!")
        print(f"   open_time: {model.open_time}")
        print(f"   open_price: {model.open_price}")
        return True
    except Exception as e:
        print(f"\n❌ 解析失败: {e}")
        return False


async def verify_futures_ticker_24hr_get():
    """验证期货 24hr Ticker GET"""
    print("\n" + "=" * 60)
    print("验证期货 24hr Ticker GET (GET /fapi/v1/ticker/24hr)")
    print("=" * 60)

    async with httpx.AsyncClient(proxy=PROXY_URL) as client:
        resp = await client.get(
            "https://fapi.binance.com/fapi/v1/ticker/24hr",
            params={"symbol": "BTCUSDT"},
            timeout=10.0,
        )
        data = resp.json()

    print(f"API响应字段: {list(data.keys())}")
    print(f"响应数据: {json.dumps(data, indent=2)}")

    # 检查字段差异
    print(f"\n⚠️  注意期货与现货的差异:")
    print(f"   期货没有: prevClosePrice, bidPrice, bidQty, askPrice, askQty")
    print(f"   现货有: prevClosePrice, bidPrice, bidQty, askPrice, askQty")

    try:
        model = BinanceFuturesTicker24hrGetModel.model_validate(data)
        print(f"\n✅ 解析成功!")
        print(f"   symbol: {model.symbol}")
        print(f"   price_change: {model.price_change}")
        print(f"   last_price: {model.last_price}")
        return True
    except Exception as e:
        print(f"\n❌ 解析失败: {e}")
        return False


async def verify_futures_ticker_24hr_ws():
    """验证期货 24hr Ticker WS"""
    print("\n" + "=" * 60)
    print("验证期货 24hr Ticker WS (<symbol>@ticker)")
    print("=" * 60)
    print("⚠️  WebSocket 验证需要建立连接，这里跳过")
    print("   请参考文档中的示例数据手动验证")
    return None


async def verify_futures_kline_ws():
    """验证期货 K线 WS"""
    print("\n" + "=" * 60)
    print("验证期货 K线 WS (<symbol>@kline_<interval>)")
    print("=" * 60)
    print("⚠️  WebSocket 验证需要建立连接，这里跳过")
    print("   请参考文档中的示例数据手动验证")
    return None


async def main():
    """运行所有验证"""
    print("\n" + "#" * 60)
    print("# 币安数据模型验证脚本")
    print("# 通过实际API调用验证文档中的模型定义")
    print("#" * 60)

    results = {}

    # 1. 现货 K线 GET
    results["spot_kline_get"] = await verify_spot_kline_get()

    # 2. 现货 K线 WS (跳过)
    results["spot_kline_ws"] = await verify_spot_kline_ws()

    # 3. 现货 24hr Ticker GET
    results["spot_ticker_get"] = await verify_spot_ticker_24hr_get()

    # 4. 现货 24hr Ticker WS (跳过)
    results["spot_ticker_ws"] = await verify_spot_ticker_24hr_ws()

    # 5. 期货 K线 GET
    results["futures_kline_get"] = await verify_futures_kline_get()

    # 6. 期货 K线 WS (跳过)
    results["futures_kline_ws"] = await verify_futures_kline_ws()

    # 7. 期货 24hr Ticker GET
    results["futures_ticker_get"] = await verify_futures_ticker_24hr_get()

    # 8. 期货 24hr Ticker WS (跳过)
    results["futures_ticker_ws"] = await verify_futures_ticker_24hr_ws()

    # 总结
    print("\n" + "#" * 60)
    print("# 验证结果总结")
    print("#" * 60)

    for name, result in results.items():
        status = "✅ PASS" if result else ("⏭️  SKIP" if result is None else "❌ FAIL")
        print(f"  {name}: {status}")


if __name__ == "__main__":
    asyncio.run(main())
