"""
分辨率/间隔转换工具

提供 TradingView 格式与币安格式之间的转换函数：
- TradingView: "1", "60", "D", "W", "M"
- 币安: "1m", "1h", "1d", "1w", "1M"
"""


def resolution_to_interval(resolution: str) -> str:
    """将 TradingView 分辨率转换为币安间隔格式

    Args:
        resolution: TradingView 格式，如 "1", "5", "60", "1D", "D", "W", "M"

    Returns:
        币安间隔格式，如 "1m", "5m", "1h", "1d", "1w", "1M"
    """
    if not resolution:
        return ""

    # TradingView 格式映射（优先匹配）
    # 注意：必须先匹配 "D" 再匹配其他带数字的格式
    if resolution == "D":
        return "1d"
    if resolution == "W":
        return "1w"
    if resolution == "M":
        return "1M"

    # 如果已经是币安格式，按结尾字符处理
    # 注意：必须小写，币安 API 区分大小写（如 1d 正确，1D 错误）
    if resolution.endswith("M"):
        return resolution  # 月份是大写 M，保持不变（如 "1M"）
    if resolution.lower().endswith(("m", "h", "d", "w")):
        return resolution.lower()  # 其他转为小写

    # 数字格式：分钟 -> m, 小时 -> h, 天 -> d
    try:
        minutes = int(resolution)
        if minutes < 60:
            return f"{minutes}m"
        elif minutes < 1440:
            return f"{minutes // 60}h"
        else:
            return f"{minutes // 1440}d"
    except ValueError:
        return resolution


def interval_to_resolution(interval: str) -> str:
    """将币安间隔格式转换为 TradingView 分辨率

    Args:
        interval: 币安间隔格式，如 "1m", "5m", "1h", "1d", "1w", "1M"

    Returns:
        TradingView 格式，如 "1", "5", "60", "D", "W", "M"
    """
    if not interval:
        return ""

    if interval.endswith("m"):
        return interval[:-1]  # 1m -> 1, 5m -> 5
    elif interval.endswith("h"):
        return str(int(interval[:-1]) * 60)  # 1h -> 60
    elif interval.endswith("d"):
        return "D"
    elif interval.endswith("w"):
        return "W"
    elif interval.endswith("M"):
        return "M"

    return interval


def tv_interval_to_binance(tv_interval: str) -> str:
    """将 TradingView 间隔格式转为币安格式

    这是 resolution_to_interval 的别名，保持命名一致性

    Args:
        tv_interval: TradingView 间隔，如 "1", "5", "60", "D"

    Returns:
        币安格式，如 "1m", "5m", "1h", "1d"
    """
    return resolution_to_interval(tv_interval)


def binance_interval_to_tv(binance_interval: str) -> str:
    """将币安格式的K线周期转换为 TradingView 官方格式

    Args:
        binance_interval: 币安格式，如 "1m", "5m", "1h", "4h", "1d"

    Returns:
        TradingView 格式，如 "1", "5", "60", "240", "D"
    """
    mapping: dict[str, str] = {
        "1m": "1",
        "3m": "3",
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "1h": "60",
        "2h": "120",
        "4h": "240",
        "6h": "360",
        "12h": "720",
        "1d": "D",
        "3d": "3D",
        "1w": "W",
        "1M": "M",
    }
    return mapping.get(binance_interval, binance_interval)
