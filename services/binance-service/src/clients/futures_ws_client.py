"""币安期货WebSocket客户端"""

from .base_ws_client import BaseWSClient


class BinanceFuturesWSClient(BaseWSClient):
    """币安期货WebSocket客户端

    WS端点：wss://fstream.binance.com/ws
    客户端ID：binance-futures-ws-001

    说明：
    - 期货市场数据使用 fstream.binance.com 端点
    - 订阅格式：ws://fstream.binance.com/ws/<streamName>
    - 示例：wss://fstream.binance.com/ws/btcusdt@kline_1m
    """

    # 使用 fstream.binance.com/market/ws 端点（2026-04-23 变更后的新地址）
    # 旧地址 wss://fstream.binance.com/ws 已于 2026-04-23 永久下线
    # 新地址需要 /ws 后缀才能使用 SUBSCRIBE 消息订阅
    WS_URI = "wss://fstream.binance.com/market/ws"
    CLIENT_ID = "binance-futures-ws-001"
