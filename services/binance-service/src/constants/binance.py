"""
币安API常量定义

保留实际使用的常量，其他未使用的类已删除以简化代码。
"""

from typing import List


class BinanceAccountSubscriptionKey:
    """账户信息订阅键常量

    订阅键格式：BINANCE:ACCOUNT@{ACCOUNT_TYPE}

    用途：
    - 现货账户: BINANCE:ACCOUNT@SPOT
    - 期货账户: BINANCE:ACCOUNT@FUTURES
    """

    # 现货账户订阅键
    SPOT = "BINANCE:ACCOUNT@SPOT"

    # 期货账户订阅键
    FUTURES = "BINANCE:ACCOUNT@FUTURES"

    @classmethod
    def get_all(cls) -> list[str]:
        """获取所有账户订阅键"""
        return [cls.SPOT, cls.FUTURES]


class BinanceUserStreamURL:
    """币安用户数据流WebSocket端点"""

    # 现货用户数据流
    SPOT_USER_STREAM = "wss://stream.binance.com:9443/ws"

    # 期货用户数据流
    FUTURES_USER_STREAM = "wss://fstream.binance.com/ws"


class BinanceUserStreamAPI:
    """币安用户数据流REST API"""

    # 现货 - 创建/续期/关闭 listenKey
    SPOT_LISTEN_KEY_API = "api/v3/userDataStream"

    # 期货 - 创建/续期/关闭 listenKey
    FUTURES_LISTEN_KEY_API = "fapi/v1/listenKey"

    @classmethod
    def get_spot_create_url(cls) -> str:
        return f"https://api.binance.com/{cls.SPOT_LISTEN_KEY_API}"

    @classmethod
    def get_futures_create_url(cls) -> str:
        return f"https://fapi.binance.com/{cls.FUTURES_LISTEN_KEY_API}"


class BinanceWebSocketURL:
    """币安WebSocket端点"""

    # 现货交易WebSocket
    SPOT_WS = "wss://stream.binance.com:9443"
    SPOT_WS_SECURE = "wss://stream.binance.com:443"
    SPOT_WS_DATA = "wss://data-stream.binance.vision"

    # 期货交易WebSocket
    FUTURES_WS = "wss://fstream.binance.com"
    FUTURES_WS_SECURE = "wss://fstream.binance.com/ws"

    # 期货交易WebSocket (币本位)
    COIN_MARGINED_FUTURES_WS = "wss://dstream.binance.com"
    COIN_MARGINED_FUTURES_WS_SECURE = "wss://dstream.binance.com/ws"

    @classmethod
    def get_combined_stream_url(cls, base: str, streams: List[str]) -> str:
        """生成组合Streams URL"""
        stream_str = "/".join(streams)
        return f"{base}/stream?streams={stream_str}"


class BinanceInterval:
    """K线时间间隔"""

    # 分钟
    INTERVAL_1M = "1m"
    INTERVAL_3M = "3m"
    INTERVAL_5M = "5m"
    INTERVAL_15M = "15m"
    INTERVAL_30M = "30m"

    # 小时
    INTERVAL_1H = "1h"
    INTERVAL_2H = "2h"
    INTERVAL_4H = "4h"
    INTERVAL_6H = "6h"
    INTERVAL_8H = "8h"
    INTERVAL_12H = "12h"

    # 天
    INTERVAL_1D = "1d"
    INTERVAL_3D = "3d"

    # 周
    INTERVAL_1W = "1w"

    # 月
    INTERVAL_1M_MONTH = "1M"

    @classmethod
    def get_all(cls) -> List[str]:
        """获取所有间隔"""
        return [
            cls.INTERVAL_1M,
            cls.INTERVAL_3M,
            cls.INTERVAL_5M,
            cls.INTERVAL_15M,
            cls.INTERVAL_30M,
            cls.INTERVAL_1H,
            cls.INTERVAL_2H,
            cls.INTERVAL_4H,
            cls.INTERVAL_6H,
            cls.INTERVAL_8H,
            cls.INTERVAL_12H,
            cls.INTERVAL_1D,
            cls.INTERVAL_3D,
            cls.INTERVAL_1W,
            cls.INTERVAL_1M_MONTH,
        ]

    @classmethod
    def get_minute_intervals(cls) -> List[str]:
        """获取分钟级间隔"""
        return [
            cls.INTERVAL_1M,
            cls.INTERVAL_3M,
            cls.INTERVAL_5M,
            cls.INTERVAL_15M,
            cls.INTERVAL_30M,
        ]

    @classmethod
    def get_hour_intervals(cls) -> List[str]:
        """获取小时级间隔"""
        return [
            cls.INTERVAL_1H,
            cls.INTERVAL_2H,
            cls.INTERVAL_4H,
            cls.INTERVAL_6H,
            cls.INTERVAL_8H,
            cls.INTERVAL_12H,
        ]

    @classmethod
    def get_day_intervals(cls) -> List[str]:
        """获取日级间隔"""
        return [
            cls.INTERVAL_1D,
            cls.INTERVAL_3D,
        ]
