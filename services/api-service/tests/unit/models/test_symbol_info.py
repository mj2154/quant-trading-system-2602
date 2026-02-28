"""
SymbolInfo 模型单元测试

测试SymbolInfo模型的完整性和字段验证：
1. 必需字段验证（无默认值）
2. 可选字段类型验证（带默认值）
3. 字段值合法性验证
4. Pydantic模型验证

符合规范:
- TradingView-完整API规范设计文档.md 第1736-1808节
- LibrarySymbolInfo 接口标准

作者: Claude Code
版本: v2.1.0
"""

import sys
from pathlib import Path

# 添加src目录到路径
_api_service_root = Path(__file__).resolve().parent.parent.parent.parent
_src_path = _api_service_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import pytest
from pydantic import ValidationError

from models.trading.symbol_models import SymbolInfo


class TestSymbolInfoRequiredFields:
    """SymbolInfo必需字段测试"""

    def test_name_required(self):
        """name字段是必需的"""
        data = self._get_minimal_valid_data()
        del data["name"]

        with pytest.raises(ValidationError) as exc_info:
            SymbolInfo(**data)

        assert "name" in str(exc_info.value)

    def test_ticker_required(self):
        """ticker字段是必需的"""
        data = self._get_minimal_valid_data()
        del data["ticker"]

        with pytest.raises(ValidationError) as exc_info:
            SymbolInfo(**data)

        assert "ticker" in str(exc_info.value)

    def test_description_required(self):
        """description字段是必需的"""
        data = self._get_minimal_valid_data()
        del data["description"]

        with pytest.raises(ValidationError) as exc_info:
            SymbolInfo(**data)

        assert "description" in str(exc_info.value)

    def test_type_required(self):
        """type字段是必需的"""
        data = self._get_minimal_valid_data()
        del data["type"]

        with pytest.raises(ValidationError) as exc_info:
            SymbolInfo(**data)

        assert "type" in str(exc_info.value)

    def test_exchange_required(self):
        """exchange字段是必需的"""
        data = self._get_minimal_valid_data()
        del data["exchange"]

        with pytest.raises(ValidationError) as exc_info:
            SymbolInfo(**data)

        assert "exchange" in str(exc_info.value)

    def test_listed_exchange_required(self):
        """listed_exchange字段是必需的"""
        data = self._get_minimal_valid_data()
        del data["listed_exchange"]

        with pytest.raises(ValidationError) as exc_info:
            SymbolInfo(**data)

        assert "listed_exchange" in str(exc_info.value)

    def test_session_required(self):
        """session字段是必需的"""
        data = self._get_minimal_valid_data()
        del data["session"]

        with pytest.raises(ValidationError) as exc_info:
            SymbolInfo(**data)

        assert "session" in str(exc_info.value)

    def test_timezone_required(self):
        """timezone字段是必需的"""
        data = self._get_minimal_valid_data()
        del data["timezone"]

        with pytest.raises(ValidationError) as exc_info:
            SymbolInfo(**data)

        assert "timezone" in str(exc_info.value)

    def test_minmov_required(self):
        """minmov字段是必需的"""
        data = self._get_minimal_valid_data()
        del data["minmov"]

        with pytest.raises(ValidationError) as exc_info:
            SymbolInfo(**data)

        assert "minmov" in str(exc_info.value)

    def test_pricescale_required(self):
        """pricescale字段是必需的"""
        data = self._get_minimal_valid_data()
        del data["pricescale"]

        with pytest.raises(ValidationError) as exc_info:
            SymbolInfo(**data)

        assert "pricescale" in str(exc_info.value)

    def _get_minimal_valid_data(self) -> dict:
        """获取最小有效数据"""
        return {
            "name": "BTCUSDT",
            "ticker": "BINANCE:BTCUSDT",
            "description": "BTC/USDT",
            "type": "crypto",
            "exchange": "BINANCE",
            "listed_exchange": "BINANCE",
            "session": "24x7",
            "timezone": "Etc/UTC",
            "minmov": 1,
            "pricescale": 100,
        }


class TestSymbolInfoFieldTypes:
    """SymbolInfo字段类型测试"""

    def test_name_must_be_string(self):
        """name必须是字符串"""
        data = self._get_minimal_valid_data()
        data["name"] = 123  # 错误类型

        with pytest.raises(ValidationError):
            SymbolInfo(**data)

    def test_ticker_must_be_string(self):
        """ticker必须是字符串"""
        data = self._get_minimal_valid_data()
        data["ticker"] = 456  # 错误类型

        with pytest.raises(ValidationError):
            SymbolInfo(**data)

    def test_description_must_be_string(self):
        """description必须是字符串"""
        data = self._get_minimal_valid_data()
        data["description"] = True  # 错误类型

        with pytest.raises(ValidationError):
            SymbolInfo(**data)

    def test_type_must_be_string(self):
        """type必须是字符串"""
        data = self._get_minimal_valid_data()
        data["type"] = []  # 错误类型

        with pytest.raises(ValidationError):
            SymbolInfo(**data)

    def test_exchange_must_be_string(self):
        """exchange必须是字符串"""
        data = self._get_minimal_valid_data()
        data["exchange"] = None  # 错误类型

        with pytest.raises(ValidationError):
            SymbolInfo(**data)

    def test_session_must_be_string(self):
        """session必须是字符串"""
        data = self._get_minimal_valid_data()
        data["session"] = 999  # 错误类型

        with pytest.raises(ValidationError):
            SymbolInfo(**data)

    def test_timezone_must_be_string(self):
        """timezone必须是字符串"""
        data = self._get_minimal_valid_data()
        data["timezone"] = {}  # 错误类型

        with pytest.raises(ValidationError):
            SymbolInfo(**data)

    def test_minmov_must_be_number(self):
        """minmov必须是数字"""
        data = self._get_minimal_valid_data()
        data["minmov"] = "invalid"  # 错误类型

        with pytest.raises(ValidationError):
            SymbolInfo(**data)

    def test_pricescale_must_be_integer(self):
        """pricescale必须是整数"""
        data = self._get_minimal_valid_data()
        data["pricescale"] = 1.5  # 错误类型

        with pytest.raises(ValidationError):
            SymbolInfo(**data)

    def _get_minimal_valid_data(self) -> dict:
        """获取最小有效数据"""
        return {
            "name": "BTCUSDT",
            "ticker": "BINANCE:BTCUSDT",
            "description": "BTC/USDT",
            "type": "crypto",
            "exchange": "BINANCE",
            "listed_exchange": "BINANCE",
            "session": "24x7",
            "timezone": "Etc/UTC",
            "minmov": 1,
            "pricescale": 100,
        }


class TestSymbolInfoOptionalFields:
    """SymbolInfo可选字段测试"""

    def test_base_name_optional(self):
        """base_name是可选字段"""
        data = self._get_minimal_valid_data()
        # 不提供base_name应该是有效的
        symbol_info = SymbolInfo(**data)
        assert symbol_info.base_name is None

    def test_base_name_must_be_list(self):
        """base_name必须是列表"""
        data = self._get_minimal_valid_data()
        data["base_name"] = "invalid"  # 应该是列表

        with pytest.raises(ValidationError):
            SymbolInfo(**data)

    def test_long_description_optional(self):
        """long_description是可选字段"""
        data = self._get_minimal_valid_data()
        symbol_info = SymbolInfo(**data)
        assert symbol_info.long_description is None

    def test_session_display_optional(self):
        """session_display是可选字段"""
        data = self._get_minimal_valid_data()
        symbol_info = SymbolInfo(**data)
        assert symbol_info.session_display is None

    def test_session_holidays_default_empty_string(self):
        """session_holidays默认值为空字符串"""
        data = self._get_minimal_valid_data()
        symbol_info = SymbolInfo(**data)
        assert symbol_info.session_holidays == ""

    def test_has_intraday_default_true(self):
        """has_intraday默认值为True"""
        data = self._get_minimal_valid_data()
        symbol_info = SymbolInfo(**data)
        assert symbol_info.has_intraday is True

    def test_has_seconds_default_false(self):
        """has_seconds默认值为False"""
        data = self._get_minimal_valid_data()
        symbol_info = SymbolInfo(**data)
        assert symbol_info.has_seconds is False

    def test_has_ticks_default_false(self):
        """has_ticks默认值为False"""
        data = self._get_minimal_valid_data()
        symbol_info = SymbolInfo(**data)
        assert symbol_info.has_ticks is False

    def test_has_daily_default_true(self):
        """has_daily默认值为True"""
        data = self._get_minimal_valid_data()
        symbol_info = SymbolInfo(**data)
        assert symbol_info.has_daily is True

    def test_has_weekly_and_monthly_default_true(self):
        """has_weekly_and_monthly默认值为True"""
        data = self._get_minimal_valid_data()
        symbol_info = SymbolInfo(**data)
        assert symbol_info.has_weekly_and_monthly is True

    def test_daily_multipliers_default(self):
        """daily_multipliers默认值为["1"]"""
        data = self._get_minimal_valid_data()
        symbol_info = SymbolInfo(**data)
        assert symbol_info.daily_multipliers == ["1"]

    def test_volume_precision_default_zero(self):
        """volume_precision默认值为0"""
        data = self._get_minimal_valid_data()
        symbol_info = SymbolInfo(**data)
        assert symbol_info.volume_precision == 0

    def test_data_status_default_streaming(self):
        """data_status默认值为 streaming """
        data = self._get_minimal_valid_data()
        symbol_info = SymbolInfo(**data)
        assert symbol_info.data_status == "streaming"

    def test_delay_default_zero(self):
        """delay默认值为0"""
        data = self._get_minimal_valid_data()
        symbol_info = SymbolInfo(**data)
        assert symbol_info.delay == 0

    def test_format_default_price(self):
        """format默认值为 price """
        data = self._get_minimal_valid_data()
        symbol_info = SymbolInfo(**data)
        assert symbol_info.format == "price"

    def test_supported_resolutions_default_empty(self):
        """supported_resolutions默认值为空列表"""
        data = self._get_minimal_valid_data()
        symbol_info = SymbolInfo(**data)
        assert symbol_info.supported_resolutions == []

    def _get_minimal_valid_data(self) -> dict:
        """获取最小有效数据"""
        return {
            "name": "BTCUSDT",
            "ticker": "BINANCE:BTCUSDT",
            "description": "BTC/USDT",
            "type": "crypto",
            "exchange": "BINANCE",
            "listed_exchange": "BINANCE",
            "session": "24x7",
            "timezone": "Etc/UTC",
            "minmov": 1,
            "pricescale": 100,
        }


class TestSymbolInfoValueConstraints:
    """SymbolInfo值约束测试

    注意：当前模型仅验证字段类型，不验证值范围约束。
    以下测试验证当前模型的真实行为。
    """

    def test_pricescale_accepts_positive_values(self):
        """pricescale接受正值"""
        data = self._get_minimal_valid_data()
        data["pricescale"] = 100

        symbol_info = SymbolInfo(**data)
        assert symbol_info.pricescale == 100

    def test_pricescale_accepts_large_values(self):
        """pricescale接受大值（外汇精度）"""
        data = self._get_minimal_valid_data()
        data["pricescale"] = 100000  # EUR/USD精度
        data["minmov"] = 1

        symbol_info = SymbolInfo(**data)
        assert symbol_info.pricescale == 100000

    def test_minmov_accepts_zero(self):
        """minmov可以为0"""
        data = self._get_minimal_valid_data()
        data["minmov"] = 0

        symbol_info = SymbolInfo(**data)
        assert symbol_info.minmov == 0

    def test_minmov_accepts_fractional_values(self):
        """minmov接受分数值（外汇精度）"""
        data = self._get_minimal_valid_data()
        data["minmov"] = 0.00001
        data["pricescale"] = 100000

        symbol_info = SymbolInfo(**data)
        assert symbol_info.minmov == 0.00001

    def test_volume_precision_accepts_zero(self):
        """volume_precision可以为0"""
        data = self._get_minimal_valid_data()
        data["volume_precision"] = 0

        symbol_info = SymbolInfo(**data)
        assert symbol_info.volume_precision == 0

    def test_volume_precision_accepts_high_values(self):
        """volume_precision接受高值（加密货币精度）"""
        data = self._get_minimal_valid_data()
        data["volume_precision"] = 8  # BTC精度

        symbol_info = SymbolInfo(**data)
        assert symbol_info.volume_precision == 8

    def test_delay_accepts_zero(self):
        """delay可以为0"""
        data = self._get_minimal_valid_data()
        data["delay"] = 0

        symbol_info = SymbolInfo(**data)
        assert symbol_info.delay == 0

    def test_delay_accepts_positive_values(self):
        """delay接受正值（延迟数据）"""
        data = self._get_minimal_valid_data()
        data["delay"] = 1000  # 1秒延迟

        symbol_info = SymbolInfo(**data)
        assert symbol_info.delay == 1000

    def _get_minimal_valid_data(self) -> dict:
        """获取最小有效数据"""
        return {
            "name": "BTCUSDT",
            "ticker": "BINANCE:BTCUSDT",
            "description": "BTC/USDT",
            "type": "crypto",
            "exchange": "BINANCE",
            "listed_exchange": "BINANCE",
            "session": "24x7",
            "timezone": "Etc/UTC",
            "minmov": 1,
            "pricescale": 100,
        }


class TestSymbolInfoCompleteModel:
    """SymbolInfo完整模型测试"""

    def test_complete_btcusdt_symbol_info(self):
        """测试完整的BTC/USDT SymbolInfo"""
        data = {
            "name": "BTCUSDT",
            "ticker": "BINANCE:BTCUSDT",
            "description": "Bitcoin/USDT",
            "type": "crypto",
            "exchange": "BINANCE",
            "listed_exchange": "BINANCE",
            "session": "24x7",
            "timezone": "Etc/UTC",
            "minmov": 1,
            "pricescale": 100,
            "base_name": ["BINANCE:BTC", "BINANCE:USDT"],
            "has_intraday": True,
            "has_daily": True,
            "has_weekly_and_monthly": True,
            "volume_precision": 2,
            "currency_code": "USDT",
            "supported_resolutions": ["1", "3", "5", "15", "60", "240", "1D", "1W", "1M"],
        }

        symbol_info = SymbolInfo(**data)

        assert symbol_info.name == "BTCUSDT"
        assert symbol_info.ticker == "BINANCE:BTCUSDT"
        assert symbol_info.description == "Bitcoin/USDT"
        assert symbol_info.type == "crypto"
        assert symbol_info.exchange == "BINANCE"
        assert symbol_info.session == "24x7"
        assert symbol_info.pricescale == 100
        assert symbol_info.base_name == ["BINANCE:BTC", "BINANCE:USDT"]
        assert symbol_info.volume_precision == 2
        assert symbol_info.currency_code == "USDT"

    def test_complete_ethusdt_symbol_info(self):
        """测试完整的ETH/USDT SymbolInfo"""
        data = {
            "name": "ETHUSDT",
            "ticker": "BINANCE:ETHUSDT",
            "description": "Ethereum/USDT",
            "type": "crypto",
            "exchange": "BINANCE",
            "listed_exchange": "BINANCE",
            "session": "24x7",
            "timezone": "Etc/UTC",
            "minmov": 1,
            "pricescale": 100,
            "has_intraday": True,
            "has_seconds": False,
            "has_daily": True,
            "has_weekly_and_monthly": True,
            "volume_precision": 4,
            "currency_code": "USDT",
        }

        symbol_info = SymbolInfo(**data)

        assert symbol_info.name == "ETHUSDT"
        assert symbol_info.ticker == "BINANCE:ETHUSDT"
        assert symbol_info.volume_precision == 4

    def test_forex_pair_symbol_info(self):
        """测试外汇交易对SymbolInfo"""
        data = {
            "name": "EURUSD",
            "ticker": "FX:EURUSD",
            "description": "Euro/US Dollar",
            "type": "forex",
            "exchange": "FX",
            "listed_exchange": "FX",
            "session": "regular",
            "timezone": "Etc/UTC",
            "minmov": 0.00001,
            "pricescale": 100000,
            "has_intraday": True,
            "has_daily": True,
            "has_weekly_and_monthly": True,
            "volume_precision": 0,
            "supported_resolutions": ["1", "5", "15", "30", "60", "240", "1D", "1W"],
        }

        symbol_info = SymbolInfo(**data)

        assert symbol_info.name == "EURUSD"
        assert symbol_info.type == "forex"
        assert symbol_info.pricescale == 100000
        assert symbol_info.minmov == 0.00001

    def test_stock_symbol_info(self):
        """测试股票SymbolInfo"""
        data = {
            "name": "AAPL",
            "ticker": "NASDAQ:AAPL",
            "description": "Apple Inc.",
            "type": "stock",
            "exchange": "NASDAQ",
            "listed_exchange": "NASDAQ",
            "session": "regular",
            "timezone": "America/New_York",
            "minmov": 0.01,
            "pricescale": 100,
            "has_intraday": True,
            "has_daily": True,
            "has_weekly_and_monthly": True,
            "volume_precision": 0,
            "currency_code": "USD",
            "sector": "Technology",
            "industry": "Consumer Electronics",
        }

        symbol_info = SymbolInfo(**data)

        assert symbol_info.name == "AAPL"
        assert symbol_info.type == "stock"
        assert symbol_info.timezone == "America/New_York"
        assert symbol_info.sector == "Technology"
        assert symbol_info.industry == "Consumer Electronics"


class TestSymbolInfoStringRepresentation:
    """SymbolInfo字符串表示测试"""

    def test_str_representation(self):
        """测试字符串表示"""
        data = {
            "name": "BTCUSDT",
            "ticker": "BINANCE:BTCUSDT",
            "description": "BTC/USDT",
            "type": "crypto",
            "exchange": "BINANCE",
            "listed_exchange": "BINANCE",
            "session": "24x7",
            "timezone": "Etc/UTC",
            "minmov": 1,
            "pricescale": 100,
        }

        symbol_info = SymbolInfo(**data)
        str_repr = str(symbol_info)

        assert "BTCUSDT" in str_repr
        assert "BINANCE" in str_repr
