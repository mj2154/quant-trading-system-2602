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
    # 使用 fstream.binance.com 端点（正确的期货市场数据端点）
    WS_URI = "wss://fstream.binance.com/ws"
    CLIENT_ID = "binance-futures-ws-001"
