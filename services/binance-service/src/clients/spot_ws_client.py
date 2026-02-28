"""币安现货WebSocket客户端"""

from .base_ws_client import BaseWSClient


class BinanceSpotWSClient(BaseWSClient):
    """币安现货WebSocket客户端

    WS端点：wss://stream.binance.com:9443/ws
    客户端ID：binance-spot-ws-001
    """

    WS_URI = "wss://stream.binance.com:9443/ws"
    CLIENT_ID = "binance-spot-ws-001"
