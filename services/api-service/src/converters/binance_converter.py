"""
币安数据转换器

将币安格式数据转换为 TradingView 格式。
返回 Pydantic 模型以确保类型安全和数据验证。
"""

from typing import Any

from ..models.base import CamelCaseModel

from ..models.trading.kline_models import KlineBar
from ..models.trading.quote_models import QuotesData, QuotesValue


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


def convert_binance_to_tv(data_type: str, data: dict) -> CamelCaseModel:
    """将币安格式数据转换为TradingView格式

    返回 CamelCaseModel 以确保类型安全和数据验证。

    Args:
        data_type: 数据类型 (KLINE, QUOTES, TRADE, ACCOUNT)
        data: 币安原始数据

    Returns:
        TradingView格式的数据模型
    """
    if data_type == "KLINE":
        return convert_kline(data)
    elif data_type == "QUOTES":
        return convert_quotes(data)
    elif data_type == "TRADE":
        # Trade 数据直接转发，返回字典包装
        return convert_trade(data)
    elif data_type == "ACCOUNT":
        # 账户数据直接返回，不转换
        return convert_account(data)
    return convert_unknown(data_type, data)


def convert_kline(data: dict) -> KlineBar:
    """将币安K线数据转换为TV格式

    返回 KlineBar 模型以确保类型安全。

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

    KlineBar 字段 (TV格式):
    - time: 时间戳（毫秒）
    - open: 开盘价
    - high: 最高价
    - low: 最低价
    - close: 收盘价
    - volume: 成交量
    """
    k = data.get("k", {})

    return KlineBar(
        time=k.get("t", 0),
        open=to_float(k.get("o")) or 0.0,
        high=to_float(k.get("h")) or 0.0,
        low=to_float(k.get("l")) or 0.0,
        close=to_float(k.get("c")) or 0.0,
        volume=to_float(k.get("v")) or 0.0,
    )


def convert_quotes(data: dict) -> QuotesData:
    """将币安24hr ticker数据转换为TV quotes格式

    返回 QuotesData 模型以确保类型安全。

    严格遵循设计文档 07-websocket-protocol.md 和 08-api-models.md 格式：
    - v 字段使用 CamelCaseModel
    - 序列化时自动转换为 camelCase

    币安格式:
    {
        "e": "24hrTicker",
        "s": "BTCUSDT",
        "c": "69104.31000000",  // 最新价格
        "o": "69073.39000000",  // 24小时开盘价
        "h": "69109.88000000",  // 24小时最高价
        "l": "69073.39000000",  // 24小时最低价
        "v": "2.02170000",      // 24小时成交量
        "q": "139701.82894280", // 24小时成交额
        "p": "30.92000000",     // 价格变化
        "P": "0.45000000",      // 价格变化百分比
        ...
    }

    QuotesData 字段 (TV格式):
    - n: 标的全名（EXCHANGE:SYMBOL格式）
    - s: 状态（ok/error）
    - v: 报价值对象
    """
    symbol = data.get("s", "")
    last_price = to_float(data.get("c")) or 0.0
    open_price = to_float(data.get("o")) or 0.0
    high_price = to_float(data.get("h")) or 0.0
    low_price = to_float(data.get("l")) or 0.0
    volume = to_float(data.get("v")) or 0.0

    # 币安直接提供价格变化数据
    # "p": 价格变化, "P": 价格变化百分比
    price_change = to_float(data.get("p")) or 0.0
    price_change_percent = to_float(data.get("P")) or 0.0

    ask_price = to_float(data.get("a")) or 0.0
    bid_price = to_float(data.get("b")) or 0.0
    spread = (ask_price - bid_price) if ask_price and bid_price else 0.0

    # description 使用商品代码（如 BTCUSDT），与现货/期货保持一致
    description = symbol

    # 构建 QuotesValue 模型
    quotes_value = QuotesValue(
        ch=price_change,
        chp=price_change_percent,
        short_name=symbol,
        exchange="BINANCE",
        description=description,
        lp=last_price,
        ask=ask_price,
        bid=bid_price,
        spread=spread,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        prev_close_price=open_price,  # 24小时开盘价等同于前收盘价
        volume=volume,
    )

    # 构建 QuotesData 模型
    return QuotesData(
        n=f"BINANCE:{symbol}",
        s="ok",
        v=quotes_value,
    )


def convert_trade(data: dict) -> CamelCaseModel:
    """将币安trade数据转换为TV格式

    返回 CamelCaseModel 以确保类型安全。
    Trade 数据直接转发原始数据，使用字典包装。

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

    返回: 使用通用模型包装的字典数据
    """
    # Trade 数据直接转发，使用动态字典模型
    return _DictWrapper(data=data)


def convert_account(data: dict) -> CamelCaseModel:
    """将账户数据转换为符合协议的数据模型

    根据 07-websocket-protocol.md 设计：
    - 账户更新推送统一使用币安原始短字段名
    - 不包含 subscriptionId 等内部字段（已在 binance-service 中移除）

    币安数据格式（已统一）：
    现货 outboundAccountPosition: {e: "outboundAccountPosition", E: 1704067205000, u: ..., B: [...]}
    现货 balanceUpdate: {e: "balanceUpdate", E: 1704067205000, a: "BTC", d: "...", T: ...}
    现货 executionReport: {e: "executionReport", E: ..., s: ..., ...}
    期货 ACCOUNT_UPDATE: {e: "ACCOUNT_UPDATE", E: ..., T: ..., a: {...}}
    期货 ORDER_TRADE_UPDATE: {e: "ORDER_TRADE_UPDATE", E: ..., s: ..., ...}

    使用 SpotAccountUpdate / SpotBalanceUpdateEvent / SpotExecutionReportEvent 模型进行转换，
    确保类型安全和符合协议定义。所有模型使用 alias 输出币安原始短字段名。

    Returns:
        SpotAccountUpdate / SpotBalanceUpdateEvent / SpotExecutionReportEvent / FuturesAccountUpdate 实例
    """
    # 数据已经是直接的事件对象，不需要再提取 event 字段
    event_type = data.get("e", "unknown")

    # 根据事件类型选择对应的模型
    if event_type == "outboundAccountPosition":
        # 现货账户余额更新事件
        from ..models.trading.account_models import SpotAccountUpdate
        return SpotAccountUpdate.from_outbound_account_position(data)
    elif event_type == "balanceUpdate":
        # 现货余额更新事件
        from ..models.trading.account_models import SpotBalanceUpdateEvent
        return SpotBalanceUpdateEvent.from_balance_update(data)
    elif event_type == "executionReport":
        # 现货订单执行报告事件
        from ..models.trading.account_models import SpotExecutionReportEvent
        return SpotExecutionReportEvent.from_execution_report(data)
    elif event_type == "ACCOUNT_UPDATE" or event_type == "ORDER_TRADE_UPDATE":
        # 期货账户更新事件
        return _create_futures_account_update(data)
    else:
        # 未知事件类型，使用通用包装
        return _DictWrapper(data=data)


def _create_futures_account_update(event_data: dict) -> CamelCaseModel:
    """创建期货账户更新模型

    Args:
        event_data: 币安期货事件数据 (e, E, T, a 字段)

    Returns:
        FuturesAccountUpdate 实例
    """
    from ..models.trading.account_models import FuturesAccountUpdate

    # 从 a 字段提取余额和持仓更新
    a_data = event_data.get("a", {})

    return FuturesAccountUpdate(
        reason=a_data.get("m", ""),
        balances=a_data.get("B", []),
        positions=a_data.get("P", []),
    )


def convert_unknown(data_type: str, data: dict) -> CamelCaseModel:
    """处理未知数据类型

    返回 CamelCaseModel 以确保类型安全。

    Args:
        data_type: 数据类型
        data: 原始数据

    Returns: 使用通用模型包装的字典数据
    """
    return _DictWrapper(data={"data_type": data_type, "data": data})


class _DictWrapper(CamelCaseModel):
    """通用字典包装器

    用于包装无法用具体模型表示的原始数据。
    确保返回类型始终为 CamelCaseModel。
    """

    data: dict[str, Any] = {}
