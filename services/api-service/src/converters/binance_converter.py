"""
币安数据转换器

将币安格式数据转换为 TradingView 格式。
"""

from typing import Any


def to_float(value: Any) -> float | None:
    """安全转换为浮点数"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def convert_binance_to_tv(data_type: str, data: dict) -> dict:
    """将币安格式数据转换为TradingView格式

    Args:
        data_type: 数据类型 (KLINE, QUOTES, TRADE, ACCOUNT)
        data: 币安原始数据

    Returns:
        TradingView格式的数据
    """
    if data_type == "KLINE":
        return convert_kline(data)
    elif data_type == "QUOTES":
        return convert_quotes(data)
    elif data_type == "TRADE":
        return convert_trade(data)
    elif data_type == "ACCOUNT":
        # 账户数据直接返回，不需要转换
        return data
    return data


def convert_kline(data: dict) -> dict:
    """将币安K线数据转换为TV格式

    币安格式:
    {
        "e": "kline",
        "s": "BTCUSDT",
        "k": {
            "t": 1770640680000,  // 开始时间
            "T": 1770640739999,  // 结束时间
            "o": "69073.39000000",  // 开盘价
            "c": "69104.31000000",  // 收盘价
            "h": "69109.88000000",  // 最高价
            "l": "69073.39000000",  // 最低价
            "v": "2.02170000",  // 成交量
            "n": 1149,  // 交易笔数
            ...
        }
    }

    TV格式:
    {
        "time": 1770640680000,  // 时间戳（毫秒）
        "open": 69073.39,
        "high": 69109.88,
        "low": 69073.39,
        "close": 69104.31,
        "volume": 2.0217
    }
    """
    k = data.get("k", {})

    return {
        "time": k.get("t"),
        "open": to_float(k.get("o")),
        "high": to_float(k.get("h")),
        "low": to_float(k.get("l")),
        "close": to_float(k.get("c")),
        "volume": to_float(k.get("v")),
    }


def convert_quotes(data: dict) -> dict:
    """将币安24hr ticker数据转换为TV quotes格式

    币安格式:
    {
        "e": "24hrTicker",
        "s": "BTCUSDT",
        "c": "69104.31000000",  // 最新价格
        "o": "69073.39000000",  // 24小时开盘价
        "h": "69109.88000000",  // 24小时最高价
        "l": "69073.39000000",  // 24小时最低价
        "v": "2.02170000",  // 24小时成交量
        "q": "139701.82894280",  // 24小时成交额
        ...
    }

    TV quotes格式:
    {
        "n": "BINANCE:BTCUSDT",
        "s": "ok",
        "v": {
            "ch": 0.45,
            "chp": 0.65,
            "lp": 69104.31,
            "ask": 69105.00,
            "bid": 69104.00,
            "spread": 1.00,
            "volume": 2.0217
        }
    }
    """
    symbol = data.get("s", "")
    last_price = to_float(data.get("c"))
    high_price = to_float(data.get("h"))
    low_price = to_float(data.get("l"))
    volume = to_float(data.get("v"))

    # 币安直接提供价格变化数据
    # "p": 价格变化, "P": 价格变化百分比
    price_change = to_float(data.get("p"))
    price_change_percent = to_float(data.get("P"))

    ask_price = to_float(data.get("a"))
    bid_price = to_float(data.get("b"))
    spread = (ask_price - bid_price) if ask_price and bid_price else 0

    return {
        "n": f"BINANCE:{symbol}",
        "s": "ok",
        "v": {
            "ch": price_change,
            "chp": price_change_percent,
            "lp": last_price,
            "ask": ask_price,
            "bid": bid_price,
            "spread": spread,
            "volume": volume,
            "high": high_price,
            "low": low_price,
        }
    }


def convert_trade(data: dict) -> dict:
    """将币安trade数据转换为TV格式

    币安格式:
    {
        "e": "trade",
        "s": "BTCUSDT",
        "t": 5930420503,  // 交易ID
        "p": "69104.31000000",  // 价格
        "q": "0.00021000",  // 数量
        "T": 1770640694074,  // 时间戳
        "m": true,  // 买方类型
    }

    TV trade格式: 直接转发原始数据
    """
    return data
