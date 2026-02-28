"""
协议常量

定义WebSocket和API协议的常量。

作者: Claude Code
版本: v2.0.0
"""

# ==================== WebSocket协议版本 ====================

PROTOCOL_VERSION = "2.0"

# ==================== WebSocket路径 ====================

WS_PATH = "/ws/market"
WS_USER_DATA_PATH = "/ws/user"

# ==================== 心跳配置 ====================

PING_INTERVAL = 20  # 心跳间隔（秒）
PING_TIMEOUT = 60   # 心跳超时（秒）

# ==================== 消息动作类型 ====================

class WSAction:
    """WebSocket消息动作类型"""
    GET = "get"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SUCCESS = "success"
    UPDATE = "update"
    ERROR = "error"


# ==================== 消息数据类型 ====================

class WSMessageType:
    """WebSocket消息数据类型"""
    CONFIG = "config"
    SEARCH_SYMBOLS = "search_symbols"
    RESOLVE_SYMBOL = "resolve_symbol"
    KLINES = "klines"
    SERVER_TIME = "server_time"
    QUOTES = "quotes"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SUBSCRIPTIONS = "subscriptions"
    METRICS = "metrics"


# ==================== 订阅类型 ====================

class SubscriptionType:
    """数据订阅类型"""
    KLINE = "kline"
    TICKER = "ticker"
    MARK_PRICE = "mark_price"
    FUNDING_RATE = "funding_rate"
    OPEN_INTEREST = "open_interest"
    BOOK_TICKER = "bookTicker"


# ==================== 解析度映射 ====================

# TradingView解析度到数据库interval的映射
RESOLUTION_TO_INTERVAL = {
    "1": "1m",
    "3": "3m",
    "5": "5m",
    "15": "15m",
    "30": "30m",
    "60": "1h",
    "120": "2h",
    "240": "4h",
    "360": "6h",
    "480": "8h",
    "720": "12h",
    "D": "1d",
    "1D": "1d",
    "3D": "3d",
    "W": "1w",
    "1W": "1w",
    "M": "1M",
    "1M": "1M",
}

# 数据库interval到TradingView解析度的映射
INTERVAL_TO_RESOLUTION = {v: k for k, v in RESOLUTION_TO_INTERVAL.items()}


# ==================== 产品类型 ====================

class ProductType:
    """产品类型"""
    SPOT = "spot"
    FUTURES = "futures"
    COIN_FUTURES = "coin_futures"


# ==================== 错误代码 ====================

class WSErrorCode:
    """WebSocket错误代码"""
    UNKNOWN = "unknown"
    INVALID_REQUEST = "invalid_request"
    AUTH_REQUIRED = "auth_required"
    RATE_LIMIT = "rate_limit"
    INTERNAL_ERROR = "internal_error"
    SUBSCRIPTION_FAILED = "subscription_failed"
