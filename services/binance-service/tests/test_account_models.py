"""
测试币安现货账户信息数据模型

测试账户信息Pydantic模型能够正确解析API响应。
"""

import pytest
from pydantic import ValidationError


class TestSpotAccountInfo:
    """币安账户信息模型测试"""

    def test_parse_full_account_response(self):
        """测试解析完整的账户响应数据"""
        from src.models.spot_account import SpotAccountInfo

        response_data = {
            "accountType": "SPOT",
            "balances": [
                {"asset": "BTC", "free": "1.00000000", "locked": "0.50000000"},
                {"asset": "USDT", "free": "1000.00000000", "locked": "0.00000000"},
            ],
            "canTrade": True,
            "canWithdraw": True,
            "canDeposit": True,
            "updateTime": 1234567890,
        }

        account = SpotAccountInfo.model_validate(response_data)

        assert account.account_type == "SPOT"
        assert account.can_trade is True
        assert account.can_withdraw is True
        assert account.can_deposit is True
        assert account.update_time == 1234567890
        assert len(account.balances) == 2

    def test_parse_balance_asset(self):
        """测试解析余额资产信息"""
        from src.models.spot_account import SpotAccountInfo, Balance

        response_data = {
            "accountType": "SPOT",
            "balances": [
                {"asset": "BNB", "free": "10.5", "locked": "2.5"},
            ],
            "canTrade": True,
            "canWithdraw": True,
            "canDeposit": True,
            "updateTime": 1234567890,
        }

        account = SpotAccountInfo.model_validate(response_data)

        bnb_balance = next(b for b in account.balances if b.asset == "BNB")
        assert bnb_balance.asset == "BNB"
        assert bnb_balance.free == "10.5"
        assert bnb_balance.locked == "2.5"

    def test_parse_empty_balances(self):
        """测试解析空余额"""
        from src.models.spot_account import SpotAccountInfo

        response_data = {
            "accountType": "SPOT",
            "balances": [],
            "canTrade": True,
            "canWithdraw": True,
            "canDeposit": True,
            "updateTime": 1234567890,
        }

        account = SpotAccountInfo.model_validate(response_data)

        assert len(account.balances) == 0

    def test_missing_required_field(self):
        """测试缺少必需字段应抛出验证错误"""
        from src.models.spot_account import SpotAccountInfo

        response_data = {
            "balances": [
                {"asset": "BTC", "free": "1.0", "locked": "0.0"},
            ],
        }

        with pytest.raises(ValidationError):
            SpotAccountInfo.model_validate(response_data)

    def test_optional_fields(self):
        """测试可选字段"""
        from src.models.spot_account import SpotAccountInfo

        # 只有必需字段
        response_data = {
            "accountType": "SPOT",
            "balances": [],
        }

        account = SpotAccountInfo.model_validate(response_data)

        assert account.account_type == "SPOT"
        assert account.can_trade is None
        assert account.can_withdraw is None
        assert account.can_deposit is None
        assert account.update_time is None

    def test_permissions_field(self):
        """测试权限字段解析"""
        from src.models.spot_account import SpotAccountInfo

        response_data = {
            "accountType": "SPOT",
            "balances": [],
            "permissions": ["SPOT", "MARGIN"],
        }

        account = SpotAccountInfo.model_validate(response_data)

        assert account.permissions == ["SPOT", "MARGIN"]

    def test_buyer_commission_and_seller_commission(self):
        """测试买卖手续费率"""
        from src.models.spot_account import SpotAccountInfo

        response_data = {
            "accountType": "SPOT",
            "balances": [],
            "buyerCommission": "0.001",
            "sellerCommission": "0.001",
        }

        account = SpotAccountInfo.model_validate(response_data)

        assert account.buyer_commission == "0.001"
        assert account.seller_commission == "0.001"


class TestBalance:
    """余额模型测试"""

    def test_balance_with_zero_values(self):
        """测试零值余额"""
        from src.models.spot_account import Balance

        data = {"asset": "BTC", "free": "0.00000000", "locked": "0.00000000"}

        balance = Balance.model_validate(data)

        assert balance.asset == "BTC"
        assert balance.free == "0.00000000"
        assert balance.locked == "0.00000000"

    def test_balance_with_large_values(self):
        """测试大额数值"""
        from src.models.spot_account import Balance

        data = {
            "asset": "USDT",
            "free": "999999999.99999999",
            "locked": "111111111.11111111",
        }

        balance = Balance.model_validate(data)

        assert balance.free == "999999999.99999999"
        assert balance.locked == "111111111.11111111"

    def test_balance_missing_optional_fields(self):
        """测试缺少可选字段"""
        from src.models.spot_account import Balance

        data = {"asset": "BTC"}

        balance = Balance.model_validate(data)

        assert balance.asset == "BTC"
        assert balance.free is None
        assert balance.locked is None

    def test_balance_asset_case_sensitivity(self):
        """测试资产名称大小写"""
        from src.models.spot_account import Balance

        data = {"asset": "btc", "free": "1.0", "locked": "0.0"}

        balance = Balance.model_validate(data)

        assert balance.asset == "btc"
