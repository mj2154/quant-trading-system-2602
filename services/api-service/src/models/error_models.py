"""
错误码定义

集中管理所有错误码，避免硬编码。

作者: Claude Code
版本: v3.0.0
"""


from pydantic import BaseModel, Field


class ErrorCode:
    """
    统一错误码定义

    遵循以下约定：
    - 使用大写字母和下划线
    - 命名格式：类别_子类别_具体错误
    - 保持简洁但具有描述性
    """

    # ==================== 通用错误 ====================
    INTERNAL_ERROR = "INTERNAL_ERROR"  # 内部服务器错误
    INVALID_REQUEST = "INVALID_REQUEST"  # 无效请求
    MISSING_PARAMETER = "MISSING_PARAMETER"  # 缺少参数
    INVALID_PARAMETER = "INVALID_PARAMETER"  # 无效参数

    # ==================== 协议错误 ====================
    PROTOCOL_ERROR = "PROTOCOL_ERROR"  # 协议错误
    UNSUPPORTED_ACTION = "UNSUPPORTED_ACTION"  # 不支持的动作
    INVALID_MESSAGE_FORMAT = "INVALID_MESSAGE_FORMAT"  # 消息格式错误

    # ==================== GET 请求错误 ====================
    # config
    MISSING_TYPE = "MISSING_TYPE"  # 缺少GET类型
    UNKNOWN_TYPE = "UNKNOWN_TYPE"  # 未知GET类型

    # search_symbols
    SEARCH_ERROR = "SEARCH_ERROR"  # 搜索错误

    # resolve_symbol
    MISSING_SYMBOL = "MISSING_SYMBOL"  # 缺少符号
    INVALID_SYMBOL = "INVALID_SYMBOL"  # 无效符号
    SYMBOL_NOT_FOUND = "SYMBOL_NOT_FOUND"  # 符号未找到

    # klines
    MISSING_PARAMS = "MISSING_PARAMS"  # 缺少参数
    UNSUPPORTED_RESOLUTION = "UNSUPPORTED_RESOLUTION"  # 不支持的分辨率
    KLINES_ERROR = "KLINES_ERROR"  # K线错误

    # server_time
    SERVER_TIME_ERROR = "SERVER_TIME_ERROR"  # 服务器时间错误

    # quotes
    MISSING_SYMBOLS = "MISSING_SYMBOLS"  # 缺少符号列表
    INVALID_SYMBOLS = "INVALID_SYMBOLS"  # 无效符号列表
    TOO_MANY_SYMBOLS = "TOO_MANY_SYMBOLS"  # 符号过多
    QUOTES_ERROR = "QUOTES_ERROR"  # 报价错误

    # ==================== 订阅错误 ====================
    SUBSCRIBE_ERROR = "SUBSCRIBE_ERROR"  # 订阅错误
    UNSUBSCRIBE_ERROR = "UNSUBSCRIBE_ERROR"  # 取消订阅错误
    SUBSCRIPTION_NOT_FOUND = "SUBSCRIPTION_NOT_FOUND"  # 订阅未找到

    # ==================== 交易所错误 ====================
    EXCHANGE_NOT_AVAILABLE = "EXCHANGE_NOT_AVAILABLE"  # 交易所不可用
    EXCHANGE_ERROR = "EXCHANGE_ERROR"  # 交易所错误
    CONNECTION_ERROR = "CONNECTION_ERROR"  # 连接错误

    # ==================== 数据错误 ====================
    DATA_NOT_FOUND = "DATA_NOT_FOUND"  # 数据未找到
    DATA_ERROR = "DATA_ERROR"  # 数据错误
    INVALID_DATA_FORMAT = "INVALID_DATA_FORMAT"  # 数据格式错误

    # ==================== 认证错误 ====================
    UNAUTHORIZED = "UNAUTHORIZED"  # 未授权
    FORBIDDEN = "FORBIDDEN"  # 禁止访问
    INVALID_API_KEY = "INVALID_API_KEY"  # API密钥无效

    # ==================== 速率限制错误 ====================
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"  # 超出速率限制
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"  # 请求过多

    # ==================== 缓存错误 ====================
    CACHE_ERROR = "CACHE_ERROR"  # 缓存错误
    CACHE_MISS = "CACHE_MISS"  # 缓存未命中

    # ==================== WebSocket 错误 ====================
    WEBSOCKET_ERROR = "WEBSOCKET_ERROR"  # WebSocket错误
    WEBSOCKET_DISCONNECTED = "WEBSOCKET_DISCONNECTED"  # WebSocket断开
    WEBSOCKET_TIMEOUT = "WEBSOCKET_TIMEOUT"  # WebSocket超时

    # ==================== 配置错误 ====================
    CONFIG_ERROR = "CONFIG_ERROR"  # 配置错误
    INVALID_CONFIG = "INVALID_CONFIG"  # 无效配置


class ErrorMessage:
    """
    错误消息模板

    提供常用的错误消息模板，便于本地化。
    """

    # ==================== 通用错误消息 ====================
    @staticmethod
    def internal_error(details: str = "") -> str:
        """内部服务器错误"""
        return f"内部服务器错误: {details}" if details else "内部服务器错误"

    @staticmethod
    def invalid_request(message: str) -> str:
        """无效请求"""
        return f"无效请求: {message}"

    @staticmethod
    def missing_parameter(param: str) -> str:
        """缺少参数"""
        return f"缺少必需参数: {param}"

    @staticmethod
    def invalid_parameter(param: str, reason: str = "") -> str:
        """无效参数"""
        if reason:
            return f"无效参数 {param}: {reason}"
        return f"无效参数: {param}"

    # ==================== GET 请求错误消息 ====================
    @staticmethod
    def missing_type() -> str:
        """缺少GET类型"""
        return "GET请求缺少 type 字段"

    @staticmethod
    def unknown_type(type_name: str) -> str:
        """未知GET类型"""
        return f"未知的GET请求类型: {type_name}"

    @staticmethod
    def missing_symbol() -> str:
        """缺少符号"""
        return "缺少必需的 symbol 参数"

    @staticmethod
    def invalid_symbol(symbol: str) -> str:
        """无效符号"""
        return f"无效的交易对符号: {symbol}"

    @staticmethod
    def symbol_not_found(symbol: str) -> str:
        """符号未找到"""
        return f"交易对符号未找到: {symbol}"

    @staticmethod
    def unsupported_interval(interval: str) -> str:
        """不支持的周期"""
        return f"不支持的周期: {interval}"

    @staticmethod
    def missing_params() -> str:
        """缺少参数"""
        return "缺少必需参数 (symbol 和 interval)"

    @staticmethod
    def exchange_not_available(exchange: str) -> str:
        """交易所不可用"""
        return f"交易所不可用: {exchange}"

    @staticmethod
    def missing_symbols() -> str:
        """缺少符号列表"""
        return "缺少必需的 symbols 参数"

    @staticmethod
    def too_many_symbols(max_count: int) -> str:
        """符号过多"""
        return f"符号数量超过限制，最多允许 {max_count} 个符号"

    @staticmethod
    def quotes_error(details: str = "") -> str:
        """报价错误"""
        return f"获取报价失败: {details}" if details else "获取报价失败"

    # ==================== 订阅错误消息 ====================
    @staticmethod
    def subscribe_error(details: str = "") -> str:
        """订阅错误"""
        return f"订阅失败: {details}" if details else "订阅失败"

    @staticmethod
    def unsubscribe_error(details: str = "") -> str:
        """取消订阅错误"""
        return f"取消订阅失败: {details}" if details else "取消订阅失败"

    # ==================== WebSocket 错误消息 ====================
    @staticmethod
    def websocket_disconnected() -> str:
        """WebSocket断开"""
        return "WebSocket连接已断开"

    @staticmethod
    def websocket_timeout() -> str:
        """WebSocket超时"""
        return "WebSocket连接超时"

    @staticmethod
    def websocket_error(details: str = "") -> str:
        """WebSocket错误"""
        return f"WebSocket错误: {details}" if details else "WebSocket错误"

    # ==================== 数据错误消息 ====================
    @staticmethod
    def data_not_found(resource: str) -> str:
        """数据未找到"""
        return f"数据未找到: {resource}"

    @staticmethod
    def invalid_data_format(expected: str, actual: str = "") -> str:
        """数据格式错误"""
        if actual:
            return f"数据格式错误，期望: {expected}，实际: {actual}"
        return f"数据格式错误，期望: {expected}"

    # ==================== 速率限制错误消息 ====================
    @staticmethod
    def rate_limit_exceeded(limit: int, retry_after: int = 0) -> str:
        """超出速率限制"""
        if retry_after > 0:
            return f"超出速率限制，每秒最多 {limit} 次请求，请 {retry_after} 秒后重试"
        return f"超出速率限制，每秒最多 {limit} 次请求"

    @staticmethod
    def too_many_requests() -> str:
        """请求过多"""
        return "请求过多，请稍后重试"

    # ==================== 配置错误消息 ====================
    @staticmethod
    def config_error(details: str = "") -> str:
        """配置错误"""
        return f"配置错误: {details}" if details else "配置错误"

    @staticmethod
    def invalid_config(param: str, reason: str = "") -> str:
        """无效配置"""
        if reason:
            return f"无效配置 {param}: {reason}"
        return f"无效配置: {param}"


# ==================== 币安API错误模型 ====================


BINANCE_ERROR_CODES: dict[int, dict[str, str]] = {
    -2015: {"message": "API认证失败或权限不足", "description": "API密钥无效、IP被限制或权限不足"},
    -2014: {"message": "API密钥不存在", "description": "提供的API密钥在系统中不存在"},
    -1021: {"message": "时间戳超出有效窗口", "description": "请求时间戳超出recvWindow限制"},
    -1003: {"message": "请求频率过高", "description": "超出API速率限制"},
    -1013: {"message": "无效的资产代码", "description": "提供的资产代码无效"},
    -1022: {"message": "签名无效", "description": "请求签名验证失败"},
}


class BinanceAPIError(BaseModel):
    """币安API错误模型"""

    code: int = Field(..., description="错误码")
    msg: str = Field(..., description="错误消息")
    http_status: int | None = Field(default=None, description="HTTP状态码")
    retry_after: int | None = Field(default=None, description="重试等待时间（秒）")
    description: str | None = Field(default=None, description="错误描述")

    def __init__(self, **data):
        super().__init__(**data)
        # 自动填充description属性
        if self.description is None and self.code in BINANCE_ERROR_CODES:
            self.description = BINANCE_ERROR_CODES[self.code].get("description")


class AuthenticationError(BinanceAPIError):
    """认证错误"""

    pass


class RateLimitError(BinanceAPIError):
    """速率限制错误"""

    pass


class TimestampError(BinanceAPIError):
    """时间戳错误"""

    pass


class SignatureError(BinanceAPIError):
    """签名错误"""

    pass


# ==================== 错误类型常量 ====================

ACCOUNT_ERROR = "ACCOUNT_ERROR"
AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
TIMESTAMP_ERROR = "TIMESTAMP_ERROR"
RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
SIGNATURE_ERROR = "SIGNATURE_ERROR"


# ==================== 错误工厂函数 ====================


def create_binance_error(
    code: int, msg: str, http_status: int | None = None, retry_after: int | None = None
) -> BinanceAPIError:
    """根据错误码创建相应的错误实例"""
    error_classes = {
        -2015: AuthenticationError,
        -2014: AuthenticationError,
        -1021: TimestampError,
        -1003: RateLimitError,
        -1022: SignatureError,
    }

    error_class = error_classes.get(code, BinanceAPIError)
    return error_class(code=code, msg=msg, http_status=http_status, retry_after=retry_after)
