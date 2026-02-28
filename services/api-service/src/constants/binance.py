"""
币安API常量定义

包含币安现货和期货交易的所有API端点、常量和枚举值。
"""

from typing import Dict, List


class BinanceBaseURL:
    """币安API基础URL"""

    # 现货交易
    SPOT_API = "https://api.binance.com"
    SPOT_API_V3 = "https://api.binance.com/api/v3"

    # 期货交易 (USDT本位)
    FUTURES_API = "https://fapi.binance.com"
    FUTURES_API_V1 = "https://fapi.binance.com/fapi/v1"

    # 期货交易 (币本位)
    COIN_MARGINED_FUTURES_API = "https://dapi.binance.com"
    COIN_MARGINED_FUTURES_API_V1 = "https://dapi.binance.com/dapi/v1"


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

    # 组合Streams
    @classmethod
    def get_combined_stream_url(cls, base: str, streams: List[str]) -> str:
        """生成组合Streams URL

        Args:
            base: 基础WebSocket URL
            streams: Stream名称列表

        Returns:
            组合后的WebSocket URL
        """
        stream_str = "/".join(streams)
        return f"{base}/stream?streams={stream_str}"


class BinanceEndpoints:
    """币安API端点"""

    # ========== 现货交易 API ==========

    # 市场数据
    SPOT_TICKER_24HR = "/api/v3/ticker/24hr"
    SPOT_TICKER_PRICE = "/api/v3/ticker/price"
    SPOT_TICKER_BOOK = "/api/v3/ticker/bookTicker"
    SPOT_KLINES = "/api/v3/klines"
    SPOT_UI_KLINES = "/api/v3/uiKlines"
    SPOT_DEPTH = "/api/v3/depth"
    SPOT_TRADES = "/api/v3/trades"
    SPOT_AGG_TRADES = "/api/v3/aggTrades"
    SPOT_AVG_PRICE = "/api/v3/avgPrice"

    # 账户信息
    SPOT_ACCOUNT = "/api/v3/account"
    SPOT_ORDER = "/api/v3/order"
    SPOT_OPEN_ORDERS = "/api/v3/openOrders"
    SPOT_ALL_ORDERS = "/api/v3/allOrders"
    SPOT_MY_TRADES = "/api/v3/myTrades"

    # ========== 期货交易 API (USDT本位) ==========

    # 市场数据
    FUTURES_TICKER_24HR = "/fapi/v1/ticker/24hr"
    FUTURES_TICKER_PRICE = "/fapi/v1/ticker/price"
    FUTURES_TICKER_BOOK = "/fapi/v1/ticker/bookTicker"
    FUTURES_KLINES = "/fapi/v1/klines"
    FUTURES_DEPTH = "/fapi/v1/depth"
    FUTURES_TRADES = "/fapi/v1/trades"
    FUTURES_AGG_TRADES = "/fapi/v1/aggTrades"
    FUTURES_PREMIUM_INDEX = "/fapi/v1/premiumIndex"
    FUTURES_FUNDING_RATE = "/fapi/v1/premiumIndex"
    FUTURES_OPEN_INTEREST = "/fapi/v1/openInterest"

    # 账户信息
    FUTURES_ACCOUNT = "/fapi/v2/account"
    FUTURES_BALANCE = "/fapi/v2/balance"
    FUTURES_ORDER = "/fapi/v1/order"
    FUTURES_OPEN_ORDERS = "/fapi/v1/openOrders"
    FUTURES_ALL_ORDERS = "/fapi/v1/allOrders"
    FUTURES_USER_TRADES = "/fapi/v1/userTrades"


class BinanceStreams:
    """币安WebSocket Streams"""

    # ========== 现货交易 Streams ==========

    # 行情数据
    SPOT_TRADE_STREAM = "{symbol}@trade"
    SPOT_KLINE_STREAM = "{symbol}@kline_{interval}"
    SPOT_KLINE_STREAM_UTC8 = "{symbol}@kline_{interval}@+08:00"
    SPOT_DEPTH_STREAM = "{symbol}@depth"
    SPOT_DIFF_DEPTH_STREAM = "{symbol}@diffDepth"
    SPOT_TICKER_STREAM = "{symbol}@ticker"
    SPOT_MINI_TICKER_STREAM = "{symbol}@miniTicker"
    SPOT_BOOK_TICKER_STREAM = "{symbol}@bookTicker"

    # 账户数据
    SPOT_OUTBOUND_ACCOUNT_POSITION = "outboundAccountPosition"
    SPOT_OUTBOUND_ORDER_POSITION = "outboundOrderPosition"

    # 组合Streams
    SPOT_ALL_TICKER_STREAM = "!ticker@arr"
    SPOT_ALL_MINI_TICKER_STREAM = "!miniTicker@arr"
    SPOT_ALL_BOOK_TICKER_STREAM = "!bookTicker@arr"
    SPOT_ALL_ROLLING_TICKER_STREAM = "!ticker@{window_size}@arr"
    SPOT_ALL_DIFF_DEPTH_STREAM = "!depth@arr"

    # ========== 期货交易 Streams (USDT本位) ==========

    # 行情数据
    FUTURES_TRADE_STREAM = "{symbol}@trade"
    FUTURES_KLINE_STREAM = "{symbol}@kline_{interval}"
    FUTURES_CONTINUOUS_KLINE_STREAM = "{symbol}_perp@continuousKline_{interval}"
    FUTURES_INDEX_KLINE_STREAM = "{symbol}@indexPriceKline_{interval}"
    FUTURES_MARK_KLINE_STREAM = "{symbol}@markPriceKline_{interval}"
    FUTURES_DEPTH_STREAM = "{symbol}@depth"
    FUTURES_DIFF_DEPTH_STREAM = "{symbol}@diffDepth"
    FUTURES_TICKER_STREAM = "{symbol}@ticker"
    FUTURES_MINI_TICKER_STREAM = "{symbol}@miniTicker"
    FUTURES_BOOK_TICKER_STREAM = "{symbol}@bookTicker"
    FUTURES_LIQUIDATION_STREAM = "{symbol}@forceOrder"

    # 账户数据
    FUTURES_ACCOUNT_UPDATE = "accountUpdate"
    FUTURES_ORDER_UPDATE = "executionReport"

    # 组合Streams
    FUTURES_ALL_TICKER_STREAM = "!ticker@arr"
    FUTURES_ALL_MINI_TICKER_STREAM = "!miniTicker@arr"
    FUTURES_ALL_DIFF_DEPTH_STREAM = "!depth@arr"
    FUTURES_ALL_BOOK_TICKER_STREAM = "!bookTicker@arr"


class BinanceSymbol:
    """常用交易对"""

    # 主流币对
    BTCUSDT = "BTCUSDT"
    ETHUSDT = "ETHUSDT"
    BNBUSDT = "BNBUSDT"
    ADAUSDT = "ADAUSDT"
    XRPUSDT = "XRPUSDT"
    SOLUSDT = "SOLUSDT"
    DOTUSDT = "DOTUSDT"
    DOGEUSDT = "DOGEUSDT"
    AVAXUSDT = "AVAXUSDT"
    SHIBUSDT = "SHIBUSDT"

    # USDT交易对
    LTCUSDT = "LTCUSDT"
    LINKUSDT = "LINKUSDT"
    MATICUSDT = "MATICUSDT"
    ATOMUSDT = "ATOMUSDT"
    VETUSDT = "VETUSDT"
    FILUSDT = "FILUSDT"
    TRXUSDT = "TRXUSDT"
    ETCUSDT = "ETCUSDT"
    XLMUSDT = "XLMUSDT"
    BCHUSDT = "BCHUSDT"

    # BTC交易对
    ETHBTC = "ETHBTC"
    BNBBTC = "BNBBTC"
    ADABTC = "ADABTC"
    XRPBTC = "XRPBTC"
    SOLBTC = "SOLBTC"
    DOTBTC = "DOTBTC"
    DOGEBTC = "DOGEBTC"
    AVAXBTC = "AVAXBTC"
    LTCBTC = "LTCBTC"
    LINKBTC = "LINKBTC"

    # 稳定币交易对
    BTCBUSD = "BTCBUSD"
    ETHBUSD = "ETHBUSD"
    BNBBUSD = "BNBBUSD"
    BTCDAI = "BTCDAI"
    ETHDAI = "ETHDAI"

    @classmethod
    def get_major_pairs(cls) -> List[str]:
        """获取主流交易对"""
        return [
            cls.BTCUSDT,
            cls.ETHUSDT,
            cls.BNBUSDT,
            cls.ADAUSDT,
            cls.XRPUSDT,
            cls.SOLUSDT,
            cls.DOTUSDT,
            cls.DOGEUSDT,
            cls.AVAXUSDT,
            cls.SHIBUSDT,
        ]

    @classmethod
    def get_usdt_pairs(cls) -> List[str]:
        """获取USDT交易对"""
        return [
            cls.BTCUSDT,
            cls.ETHUSDT,
            cls.BNBUSDT,
            cls.ADAUSDT,
            cls.XRPUSDT,
            cls.SOLUSDT,
            cls.DOTUSDT,
            cls.DOGEUSDT,
            cls.AVAXUSDT,
            cls.SHIBUSDT,
            cls.LTCUSDT,
            cls.LINKUSDT,
            cls.MATICUSDT,
            cls.ATOMUSDT,
            cls.VETUSDT,
            cls.FILUSDT,
            cls.TRXUSDT,
            cls.ETCUSDT,
            cls.XLMUSDT,
            cls.BCHUSDT,
        ]

    @classmethod
    def get_btc_pairs(cls) -> List[str]:
        """获取BTC交易对"""
        return [
            cls.ETHBTC,
            cls.BNBBTC,
            cls.ADABTC,
            cls.XRPBTC,
            cls.SOLBTC,
            cls.DOTBTC,
            cls.DOGBTC,
            cls.AVAXBTC,
            cls.LTCBTC,
            cls.LINKBTC,
        ]


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


class BinanceTimeInForce:
    """订单有效期限"""

    # GOOD_TIL_CANCELLED - 撤销前一直有效
    GTC = "GTC"

    # GOOD_TIL_CROSSING - 触发后立即成交或撤销
    GTX = "GTX"

    # IMMEDIATE_OR_CANCEL - 立即成交或撤销
    IOC = "IOC"

    # FILL_OR_KILL - 全部成交或撤销
    FOK = "FOK"


class BinanceOrderType:
    """订单类型"""

    # 限价单
    LIMIT = "LIMIT"

    # 市价单
    MARKET = "MARKET"

    # 止损单
    STOP = "STOP"

    # 止损限价单
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"

    # 止盈单
    TAKE_PROFIT = "TAKE_PROFIT"

    # 止盈限价单
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"

    # 限价止盈止损单
    LIMIT_MAKER = "LIMIT_MAKER"


class BinanceOrderSide:
    """订单方向"""

    # 买入
    BUY = "BUY"

    # 卖出
    SELL = "SELL"


class BinanceOrderStatus:
    """订单状态"""

    # 等待成交
    NEW = "NEW"

    # 部分成交
    PARTIALLY_FILLED = "PARTIALLY_FILLED"

    # 全部成交
    FILLED = "FILLED"

    # 已撤销
    CANCELED = "CANCELED"

    # 替换为新订单
    REPLACED = "REPLACED"

    # 等待撤销
    PENDING_CANCEL = "PENDING_CANCEL"

    # 等待替换
    PENDING_REPLACE = "PENDING_REPLACE"

    # 已拒绝
    REJECTED = "REJECTED"


class BinanceContingencyType:
    """订单联动类型"""

    # OCO订单
    OCO = "OCO"


class BinanceResponseType:
    """API响应类型"""

    # ACK响应
    ACK = "ACK"

    # 结果响应
    RESULT = "RESULT"

    # 完整响应
    FULL = "FULL"


class BinancePermissions:
    """账户权限"""

    # 现货交易
    SPOT = "SPOT"

    # 杠杆交易
    MARGIN = "MARGIN"

    # 期货交易
    FUTURES = "FUTURES"


class BinanceRateLimit:
    """API限速配置"""

    # 请求权重
    REQUEST_WEIGHT = "REQUEST_WEIGHT"

    # 下单次数
    ORDERS = "ORDERS"

    # 原始请求
    RAW_REQUESTS = "RAW_REQUESTS"


class BinanceRateLimitInterval:
    """限速间隔"""

    # 分钟
    MINUTE = "MINUTE"

    # 秒
    SECOND = "SECOND"

    # 天
    DAY = "DAY"


class BinanceWebSocketMethods:
    """WebSocket方法"""

    # 订阅
    SUBSCRIBE = "SUBSCRIBE"

    # 取消订阅
    UNSUBSCRIBE = "UNSUBSCRIBE"

    # 列出订阅
    LIST_SUBSCRIPTIONS = "LIST_SUBSCRIPTIONS"


class BinanceStreamStatus:
    """WebSocket Stream状态"""

    # 交易状态
    TRADING = "TRADING"

    # 交易暂停
    HALT = "HALT"

    # 交易中断
    BREAK = "BREAK"


class BinanceConfig:
    """币安API配置"""

    # WebSocket连接限制
    MAX_WEBSOCKET_STREAMS = 1024
    MAX_WEBSOCKET_CONNECTIONS_PER_MINUTE = 300

    # WebSocket消息限制
    MAX_MESSAGES_PER_SECOND = 5

    # K线数据限制
    MAX_KLINE_LIMIT = 1000
    DEFAULT_KLINE_LIMIT = 500

    # 深度数据限制
    MAX_DEPTH_LIMIT = 5000
    DEFAULT_DEPTH_LIMIT = 100

    # 交易数据限制
    MAX_TRADES_LIMIT = 1000
    DEFAULT_TRADES_LIMIT = 500
