"""
币安数据转换器

将币安格式数据转换为 TradingView 格式。
返回 Pydantic 模型以确保类型安全和数据验证。
"""

import logging
from typing import Any

from ..models.base import CamelCaseModel
from ..models.trading.kline_models import KlineBar
from ..models.trading.quote_models import QuotesData, QuotesValue

logger = logging.getLogger(__name__)


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
        data_type: 数据类型 (KLINE, QUOTES, TRADE, USERDATA)
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
    elif data_type == "USERDATA":
        # 用户数据流事件（现货/期货账户更新和订单更新）
        return convert_user_data_stream_event(data)
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
    # Trade 数据应该有对应的模型，未定义模型则抛出异常
    logger.error(f"[convert_trade] Trade 数据未定义模型: {data}")
    raise ValueError("Trade data model not implemented")


def convert_user_data_stream_event(data: dict) -> CamelCaseModel:
    """将币安用户数据流事件转换为符合协议的数据模型

    根据 07-websocket-protocol.md 设计：
    - 用户数据流事件统一使用币安原始短字段名
    - 不包含 subscriptionId 等内部字段（已在 binance-service 中移除）

    币安数据格式（已统一）：
    现货 outboundAccountPosition: {e: "outboundAccountPosition", E: 1704067205000, u: ..., B: [...]}
    现货 balanceUpdate: {e: "balanceUpdate", E: 1704067205000, a: "BTC", d: "...", T: ...}
    现货 executionReport: {e: "executionReport", E: ..., s: ..., ...}
    期货 ACCOUNT_UPDATE: {e: "ACCOUNT_UPDATE", E: ..., T: ..., a: {...}}
    期货 ORDER_TRADE_UPDATE: {e: "ORDER_TRADE_UPDATE", E: ..., T: ..., o: {...}}

    Returns:
        SpotAccountUpdate / SpotBalanceUpdateEvent / SpotExecutionReportEvent /
        FuturesAccountUpdate / FuturesOrderTradeUpdate 实例
    """
    event_type = data.get("e", "unknown")

    if event_type == "outboundAccountPosition":
        from ..models.trading.account_models import SpotAccountUpdate
        return SpotAccountUpdate.from_outbound_account_position(data)
    elif event_type == "balanceUpdate":
        from ..models.trading.account_models import SpotBalanceUpdateEvent
        return SpotBalanceUpdateEvent.from_balance_update(data)
    elif event_type == "executionReport":
        from ..models.trading.account_models import SpotExecutionReportEvent
        return SpotExecutionReportEvent.from_execution_report(data)
    elif event_type == "ACCOUNT_UPDATE":
        from ..models.trading.account_models import FuturesAccountUpdate
        return FuturesAccountUpdate.from_account_update_event(data)
    elif event_type == "ORDER_TRADE_UPDATE":
        from ..models.trading.account_models import FuturesOrderTradeUpdate
        return FuturesOrderTradeUpdate.from_order_trade_update_event(data)
    elif event_type == "TRADE_LITE":
        # 期货简化交易事件
        from ..models.trading.account_models import FuturesTradeLiteEvent
        return FuturesTradeLiteEvent.model_validate(data)
    elif event_type == "ACCOUNT_CONFIG_UPDATE":
        # 期货账户配置更新事件（杠杆/多资产模式变更）
        from ..models.trading.account_models import FuturesAccountConfigUpdate
        return FuturesAccountConfigUpdate.from_account_config_update_event(data)
    elif event_type == "MARGIN_CALL":
        # 期货保证金追缴事件（高优先级，涉及强平风险）
        from ..models.trading.account_models import FuturesMarginCallEvent
        return FuturesMarginCallEvent.model_validate(data)
    elif event_type == "ALGO_UPDATE":
        # 期货条件单更新事件
        from ..models.trading.account_models import FuturesAlgoUpdateEvent
        return FuturesAlgoUpdateEvent.model_validate(data)
    elif event_type == "STRATEGY_UPDATE":
        # 期货策略更新事件
        from ..models.trading.account_models import FuturesStrategyUpdateEvent
        return FuturesStrategyUpdateEvent.model_validate(data)
    elif event_type == "GRID_UPDATE":
        # 期货网格更新事件
        from ..models.trading.account_models import FuturesGridUpdateEvent
        return FuturesGridUpdateEvent.model_validate(data)
    elif event_type == "CONDITIONAL_ORDER_TRIGGER_REJECT":
        # 期货条件单触发拒绝事件
        from ..models.trading.account_models import FuturesConditionalOrderTriggerRejectEvent
        return FuturesConditionalOrderTriggerRejectEvent.model_validate(data)
    else:
        logger.error(f"[convert_user_data_stream_event] 未知事件类型: {event_type}, data: {data}")
        raise ValueError(f"Unknown user data stream event type: {event_type}")


def convert_unknown(data_type: str, data: dict) -> CamelCaseModel:
    """处理未知数据类型

    未知数据类型直接抛出异常，不进行后续处理。

    Args:
        data_type: 数据类型
        data: 原始数据

    Returns:
        不返回任何值，直接抛出异常
    """
    logger.error(f"[convert_unknown] 未知数据类型: data_type={data_type}, data={data}")
    raise ValueError(f"Unknown data type: {data_type}")
