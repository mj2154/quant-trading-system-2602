"""
订阅键转换模块

负责解析订阅键和流名称的相互转换：
- 订阅键 -> 交易所流名称
- 交易所流名称 -> 订阅键

支持多个交易所：BINANCE, OKX, BYBIT, HUOBI

作者: Claude Code
版本: v1.0.0
"""

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# 支持的交易所列表
SUPPORTED_EXCHANGES = {"BINANCE", "OKX", "BYBIT", "HUOBI"}

# 数据类型映射
DATA_TYPE_MAPPING = {
    "KLINE": "KLINE",
    "TRADE": "TRADE",
    "TICKER": "TICKER",
    "QUOTES": "QUOTES",
    "DEPTH": "DEPTH",
    "BOOK": "BOOK",
}

# 流名称解析正则
STREAM_NAME_PATTERN = r"^([a-zA-Z0-9_]+)@([a-zA-Z]+)(?:_([0-9a-zA-Z]+))?$"

# 币安间隔映射（TradingView分辨率/interval -> 币安间隔格式）
BINANCE_INTERVAL_MAP = {
    # 数字格式 (分钟)
    "1": "1m",
    "3": "3m",
    "5": "5m",
    "15": "15m",
    "30": "30m",
    "60": "1h",
    "120": "2h",
    "240": "4h",
    "360": "6h",
    "720": "12h",
    "1440": "1d",
    "4320": "3d",
    "10080": "1w",
    "43200": "1M",
    # TradingView 字母格式
    "D": "1d",
    "W": "1w",
    "M": "1M",
}

# OKX间隔映射
OKX_INTERVAL_MAP = {
    "1": "1m",
    "3": "3m",
    "5": "5m",
    "15": "15m",
    "30": "30m",
    "60": "1H",
    "180": "3H",
    "360": "6H",
    "720": "12H",
    "1440": "1D",
    "4320": "3D",
    "10080": "1W",
    "43200": "1M",
}

# Bybit间隔映射
BYBIT_INTERVAL_MAP = {
    "1": "1",
    "3": "3",
    "5": "5",
    "15": "15",
    "30": "30",
    "60": "60",
    "120": "120",
    "240": "240",
    "360": "360",
    "720": "720",
    "1440": "D",
    "10080": "W",
    "43200": "M",
}

# 火币间隔映射
HUOBI_INTERVAL_MAP = {
    "1": "1min",
    "3": "3min",
    "5": "5min",
    "15": "15min",
    "30": "30min",
    "60": "60min",
    "240": "4hour",
    "1440": "1day",
}


# ==================== 共享转换函数 ====================


@lru_cache(maxsize=512)
def resolution_to_interval(resolution: str) -> str:
    """将 TradingView 分辨率转换为币安间隔格式

    支持的格式：
    - 数字格式: "1", "5", "60", "1440" -> "1m", "5m", "1h", "1d"
    - TradingView字母格式: "D", "W", "M" -> "1d", "1w", "1M"
    - 币安格式: "1m", "1h", "1d" -> 直接返回

    Args:
        resolution: TradingView 分辨率或币安间隔

    Returns:
        币安间隔格式字符串
    """
    # TradingView 字母格式 -> 币安格式
    if resolution == "D":
        return "1d"
    if resolution == "W":
        return "1w"
    if resolution == "M":
        return "1M"

    # 使用映射表
    if resolution in BINANCE_INTERVAL_MAP:
        return BINANCE_INTERVAL_MAP[resolution]

    # 已经是币安格式（包含 m, h, d, w, M 后缀）
    if resolution.endswith(("m", "h", "d", "w", "M")):
        return resolution

    # 兜底：数字格式转换为分钟
    try:
        minutes = int(resolution)
        if minutes < 60:
            return f"{minutes}m"
        elif minutes < 1440:
            return f"{minutes // 60}h"
        else:
            return f"{minutes // 1440}d"
    except ValueError:
        return "1m"


# ==================== 数据模型 ====================


@dataclass
class ParsedSubscription:
    """解析后的订阅信息"""
    exchange: str
    symbol: str
    data_type: str
    params: dict[str, Any] = None


@dataclass
class StreamInfo:
    """流信息数据类"""
    symbol: str
    data_type: str
    interval: str | None = None
    is_valid: bool = True
    error_message: str | None = None


# ==================== 订阅键解析器 ====================


class SubscriptionKeyParser:
    """订阅键解析器

    解析格式：EXCHANGE:SYMBOL@TYPE_PARAMS
    示例：BINANCE:BTCUSDT@KLINE_1m
    """

    SUPPORTED_EXCHANGES = SUPPORTED_EXCHANGES
    DATA_TYPE_MAPPING = DATA_TYPE_MAPPING

    @staticmethod
    def parse(sub_key: str) -> ParsedSubscription | None:
        """解析订阅键为组件"""
        try:
            if ":" not in sub_key:
                logger.warning(f"订阅键格式错误，缺少冒号: {sub_key}")
                return None

            parts = sub_key.split(":", 1)
            exchange = parts[0].upper()
            symbol_part = parts[1]

            if exchange not in SubscriptionKeyParser.SUPPORTED_EXCHANGES:
                logger.warning(f"不支持的交易所: {exchange}")
                return None

            if "@" in symbol_part:
                symbol, data_type_part = symbol_part.split("@", 1)
                data_type, params = SubscriptionKeyParser._parse_data_type(data_type_part)
            else:
                symbol = symbol_part
                data_type = "unknown"
                params = {}

            if not symbol:
                logger.warning(f"符号为空: {sub_key}")
                return None

            return ParsedSubscription(
                exchange=exchange, symbol=symbol, data_type=data_type, params=params or {}
            )

        except Exception as e:
            logger.error(f"解析订阅键失败: {sub_key}, 错误: {e}")
            return None

    @staticmethod
    def _parse_data_type(data_type_part: str) -> tuple[str, dict[str, Any]]:
        """解析数据类型部分"""
        params = {}

        if data_type_part.startswith("KLINE_"):
            data_type = "KLINE"
            interval_part = data_type_part.replace("KLINE_", "")

            # 存储为 interval，与数据库字段保持一致
            if interval_part.endswith("m"):
                try:
                    interval = int(interval_part[:-1])
                    params["interval"] = str(interval)
                except ValueError:
                    params["interval"] = "1"
            elif interval_part.endswith("h"):
                try:
                    interval = int(interval_part[:-1])
                    params["interval"] = str(interval * 60)
                except ValueError:
                    params["interval"] = "60"
            elif interval_part.endswith("d"):
                try:
                    interval = int(interval_part[:-1])
                    params["interval"] = str(interval * 1440)
                except ValueError:
                    params["interval"] = "1440"
            else:
                try:
                    interval = int(interval_part)
                    params["interval"] = str(interval)
                except ValueError:
                    params["interval"] = "1"

        elif data_type_part in ["TRADE", "TICKER", "QUOTES"]:
            data_type = data_type_part
        elif data_type_part.startswith("DEPTH_"):
            data_type = "DEPTH"
            depth_part = data_type_part.replace("DEPTH_", "")
            try:
                params["depth"] = str(int(depth_part))
            except ValueError:
                params["depth"] = "20"
        else:
            data_type = data_type_part
            logger.warning(f"未知数据类型: {data_type_part}")

        return data_type, params

    @staticmethod
    def to_stream_name(parsed: ParsedSubscription) -> str | None:
        """转换为交易所流名称"""
        try:
            if parsed.exchange == "BINANCE":
                return SubscriptionKeyParser._binance_to_stream_name(parsed)
            elif parsed.exchange == "OKX":
                return SubscriptionKeyParser._okx_to_stream_name(parsed)
            elif parsed.exchange == "BYBIT":
                return SubscriptionKeyParser._bybit_to_stream_name(parsed)
            elif parsed.exchange == "HUOBI":
                return SubscriptionKeyParser._huobi_to_stream_name(parsed)
            else:
                logger.warning(f"不支持的交易所: {parsed.exchange}")
                return None
        except Exception as e:
            logger.error(f"转换流名称失败: {parsed}, 错误: {e}")
            return None

    @staticmethod
    def _binance_to_stream_name(parsed: ParsedSubscription) -> str | None:
        """转换为币安流名称"""
        symbol_lower = parsed.symbol.lower()

        if parsed.data_type == "KLINE":
            interval = parsed.params.get("interval", "1")
            binance_interval = BINANCE_INTERVAL_MAP.get(interval, f"{interval}m")
            return f"{symbol_lower}@kline_{binance_interval}"
        elif parsed.data_type == "TRADE":
            return f"{symbol_lower}@trade"
        elif parsed.data_type == "TICKER":
            return f"{symbol_lower}@ticker"
        elif parsed.data_type == "QUOTES":
            return f"{symbol_lower}@ticker"
        elif parsed.data_type == "DEPTH":
            depth = parsed.params.get("depth", "20")
            return f"{symbol_lower}@depth{depth}"
        else:
            logger.warning(f"币安不支持的数据类型: {parsed.data_type}")
            return None

    @staticmethod
    def _okx_to_stream_name(parsed: ParsedSubscription) -> str | None:
        """转换为OKX流名称"""
        symbol_upper = parsed.symbol.upper()

        if parsed.data_type == "KLINE":
            interval = parsed.params.get("interval", "1")
            okx_interval = OKX_INTERVAL_MAP.get(interval, f"{interval}m")
            return f"{symbol_upper}/USDT@index/candle{okx_interval}"
        else:
            logger.warning(f"OKX暂不支持数据类型: {parsed.data_type}")
            return None

    @staticmethod
    def _bybit_to_stream_name(parsed: ParsedSubscription) -> str | None:
        """转换为Bybit流名称"""
        symbol_lower = parsed.symbol.lower()

        if parsed.data_type == "KLINE":
            interval = parsed.params.get("interval", "1")
            bybit_interval = BYBIT_INTERVAL_MAP.get(interval, "1")
            return f"{symbol_lower}@kline.{bybit_interval}"
        else:
            logger.warning(f"Bybit暂不支持数据类型: {parsed.data_type}")
            return None

    @staticmethod
    def _huobi_to_stream_name(parsed: ParsedSubscription) -> str | None:
        """转换为火币流名称"""
        symbol_lower = parsed.symbol.lower()

        if parsed.data_type == "KLINE":
            interval = parsed.params.get("interval", "1")
            huobi_interval = HUOBI_INTERVAL_MAP.get(interval, "1min")
            return f"{symbol_lower}.{huobi_interval}"
        else:
            logger.warning(f"火币暂不支持数据类型: {parsed.data_type}")
            return None

    @staticmethod
    def batch_parse(sub_keys: list[str]) -> dict[str, ParsedSubscription]:
        """批量解析订阅键"""
        results = {}
        for sub_key in sub_keys:
            parsed = SubscriptionKeyParser.parse(sub_key)
            if parsed:
                results[sub_key] = parsed
            else:
                logger.warning(f"解析失败: {sub_key}")
        return results

    @staticmethod
    def batch_to_stream_names(
        parsed_subs: dict[str, ParsedSubscription]
    ) -> dict[str, str]:
        """批量转换为流名称"""
        results = {}
        for sub_key, parsed in parsed_subs.items():
            stream_name = SubscriptionKeyParser.to_stream_name(parsed)
            if stream_name:
                results[sub_key] = stream_name
            else:
                logger.warning(f"流名称转换失败: {sub_key}")
        return results

    @staticmethod
    def group_by_exchange(parsed_subs: dict[str, ParsedSubscription]) -> dict[str, list[str]]:
        """按交易所分组订阅键"""
        grouped = {}
        for sub_key, parsed in parsed_subs.items():
            if parsed.exchange not in grouped:
                grouped[parsed.exchange] = []
            grouped[parsed.exchange].append(sub_key)
        return grouped


# ==================== 流解析器 ====================


class StreamParser:
    """流解析器 - 解析交易所WebSocket流名称

    解析格式：SYMBOL@TYPE_INTERVAL
    示例：btcusdt@kline_1h, btcusdt@ticker
    """

    # 支持的数据类型
    SUPPORTED_DATA_TYPES = {
        "kline": "K线数据",
        "ticker": "Ticker数据",
        "trade": "Trade数据",
        "miniTicker": "Mini Ticker",
        "depth": "深度数据",
        "bookTicker": "最优买卖价",
        "aggTrade": "聚合交易",
    }

    # 有效间隔
    VALID_INTERVALS = {
        "1m", "3m", "5m", "15m", "30m", "45m",
        "1h", "2h", "3h", "4h", "6h", "8h", "12h",
        "1d", "3d", "5d",
        "1w", "1M", "3M", "6M", "1y",
    }

    @staticmethod
    @lru_cache(maxsize=1024)
    def parse(stream_name: str) -> StreamInfo:
        """解析流名称"""
        try:
            if not stream_name or not isinstance(stream_name, str):
                return StreamInfo(
                    symbol="", data_type="", is_valid=False,
                    error_message="流名称为空或格式错误"
                )

            match = re.match(STREAM_NAME_PATTERN, stream_name)
            if not match:
                return StreamInfo(
                    symbol="", data_type="", is_valid=False,
                    error_message=f"流名称格式错误: {stream_name}"
                )

            symbol = match.group(1).upper()
            data_type = match.group(2)
            interval = match.group(3)

            if data_type not in StreamParser.SUPPORTED_DATA_TYPES:
                return StreamInfo(
                    symbol=symbol, data_type=data_type, interval=interval, is_valid=False,
                    error_message=f"不支持的数据类型: {data_type}"
                )

            if data_type == "kline" and interval:
                if not StreamParser._validate_interval(interval):
                    return StreamInfo(
                        symbol=symbol, data_type=data_type, interval=interval, is_valid=False,
                        error_message=f"无效的间隔格式: {interval}"
                    )

            return StreamInfo(symbol=symbol, data_type=data_type, interval=interval, is_valid=True)

        except Exception as e:
            return StreamInfo(
                symbol="", data_type="", is_valid=False,
                error_message=f"解析异常: {e}"
            )

    @staticmethod
    @lru_cache(maxsize=1024)
    def to_subscription_key(stream_name: str, exchange: str = "BINANCE") -> str | None:
        """将流名称转换为订阅键"""
        parsed = StreamParser.parse(stream_name)
        if not parsed.is_valid:
            logger.warning(f"流名称解析失败: {stream_name} - {parsed.error_message}")
            return None

        # 构建订阅键
        if parsed.data_type == "kline":
            # 需要转换间隔到 TradingView 分辨率格式（用于订阅键）
            resolution = StreamParser._interval_to_resolution(parsed.interval)
            return f"{exchange}:{parsed.symbol}@KLINE_{resolution}"
        else:
            return f"{exchange}:{parsed.symbol}@{parsed.data_type.upper()}"

    @staticmethod
    @lru_cache(maxsize=256)
    def _validate_interval(interval: str) -> bool:
        """验证间隔格式"""
        return interval in StreamParser.VALID_INTERVALS

    @staticmethod
    def _interval_to_resolution(interval: str) -> str:
        """将间隔转换为分辨率（分钟）"""
        if interval.endswith("m"):
            return interval[:-1]
        elif interval.endswith("h"):
            return str(int(interval[:-1]) * 60)
        elif interval.endswith("d"):
            return str(int(interval[:-1]) * 1440)
        elif interval.endswith("w"):
            return str(int(interval[:-1]) * 10080)
        elif interval.endswith("M"):
            return str(int(interval[:-1]) * 43200)
        return interval

    @staticmethod
    @lru_cache(maxsize=1024)
    def extract_symbol(stream_name: str) -> str | None:
        """从流名称中提取交易对"""
        parsed = StreamParser.parse(stream_name)
        return parsed.symbol if parsed.is_valid else None

    @staticmethod
    @lru_cache(maxsize=1024)
    def extract_data_type(stream_name: str) -> str | None:
        """从流名称中提取数据类型"""
        parsed = StreamParser.parse(stream_name)
        return parsed.data_type if parsed.is_valid else None

    @staticmethod
    def build_stream_name(
        symbol: str, data_type: str, interval: str | None = None, contract_type: str | None = None
    ) -> str:
        """构建币安流名称"""
        symbol_lower = symbol.lower()

        if data_type == "continuousKline":
            if not interval:
                raise ValueError("continuousKline类型必须提供间隔参数")
            if not contract_type:
                raise ValueError("continuousKline类型必须提供合约类型参数")
            return f"{symbol_lower}_{contract_type}@{data_type}_{interval}"
        elif data_type == "kline":
            if not interval:
                raise ValueError("kline类型必须提供间隔参数")
            return f"{symbol_lower}@{data_type}_{interval}"
        else:
            return f"{symbol_lower}@{data_type}"

    @staticmethod
    @lru_cache(maxsize=1024)
    def is_valid(stream_name: str) -> bool:
        """验证流名称是否有效"""
        parsed = StreamParser.parse(stream_name)
        return parsed.is_valid

    @staticmethod
    def get_supported_data_types() -> dict[str, str]:
        """获取支持的数据类型"""
        return StreamParser.SUPPORTED_DATA_TYPES.copy()


# ==================== 便捷函数 ====================


def parse_subscription_key(sub_key: str) -> ParsedSubscription | None:
    """便捷函数：解析订阅键"""
    return SubscriptionKeyParser.parse(sub_key)


def subscription_key_to_stream(sub_key: str) -> str | None:
    """便捷函数：订阅键转流名称"""
    parsed = SubscriptionKeyParser.parse(sub_key)
    if parsed:
        return SubscriptionKeyParser.to_stream_name(parsed)
    return None


def stream_to_subscription_key(stream_name: str, exchange: str = "BINANCE") -> str | None:
    """便捷函数：流名称转订阅键"""
    return StreamParser.to_subscription_key(stream_name, exchange)


def parse_stream_name(stream_name: str) -> StreamInfo:
    """便捷函数：解析流名称"""
    return StreamParser.parse(stream_name)


__all__ = [
    "ParsedSubscription",
    "StreamInfo",
    "SubscriptionKeyParser",
    "StreamParser",
    "parse_subscription_key",
    "subscription_key_to_stream",
    "stream_to_subscription_key",
    "parse_stream_name",
]
