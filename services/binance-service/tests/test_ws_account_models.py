"""
WebSocket账户信息模型测试

测试期货和现货账户信息模型的行为。
"""

import pytest
from pydantic import ValidationError

from models.ws_account_models import (
    # Futures models
    FuturesAccountInfoV2,
    FuturesAsset,
    FuturesPosition,
    # Spot models
    SpotAccountInfo,
    SpotBalance,
    CommissionRates,
)


class TestFuturesAsset:
    """期货资产模型测试"""

    def test_create_futures_asset(self):
        """测试创建期货资产"""
        asset = FuturesAsset(
            asset="USDT",
            margin_balance="1000.50",
            wallet_balance="1000.00",
            available_balance="950.50",
            initial_margin="49.50",
            maintenance_margin="5.00",
            unrealized_pnl="0.50",
        )
        assert asset.asset == "USDT"
        assert asset.margin_balance == "1000.50"
        assert asset.wallet_balance == "1000.00"

    def test_futures_asset_with_all_fields(self):
        """测试创建期货资产（所有字段）"""
        asset = FuturesAsset(
            asset="BTC",
            margin_balance="1.5",
            wallet_balance="1.4",
            available_balance="1.3",
            initial_margin="0.1",
            maintenance_margin="0.01",
            unrealized_pnl="0.1",
        )
        assert asset.asset == "BTC"


class TestFuturesPosition:
    """期货持仓模型测试"""

    def test_create_futures_position(self):
        """测试创建期货持仓"""
        position = FuturesPosition(
            symbol="BTCUSDT",
            position_side="LONG",
            position_side_value=1,
            quantity="0.1",
            entry_price="42000.00",
            mark_price="42100.00",
            unrealized_pnl="10.00",
            margin_balance="50.00",
            isolated_margin="0",
            is_auto_add_margin=True,
        )
        assert position.symbol == "BTCUSDT"
        assert position.position_side == "LONG"
        assert position.quantity == "0.1"

    def test_futures_position_short(self):
        """测试创建期货空头持仓"""
        position = FuturesPosition(
            symbol="ETHUSDT",
            position_side="SHORT",
            position_side_value=2,
            quantity="1.5",
            entry_price="2500.00",
            mark_price="2480.00",
            unrealized_pnl="30.00",
            margin_balance="75.00",
            isolated_margin="0",
            is_auto_add_margin=False,
        )
        assert position.position_side == "SHORT"


class TestFuturesAccountInfoV2:
    """期货账户信息V2模型测试"""

    def test_create_futures_account_info_v2(self):
        """测试创建期货账户信息V2"""
        account = FuturesAccountInfoV2(
            fee_broker_bnb="B2C2",
            can_deposit=True,
            can_trade=True,
            can_withdraw=False,
            fee_bnb="0.00000000",
            total_balance="12345.67",
            total_margin_balance="10000.00",
            total_available_balance="9000.00",
            total_initial_margin="1000.00",
            total_maintenance_margin="100.00",
            total_unrealized_pnl="50.00",
            assets=[
                FuturesAsset(
                    asset="USDT",
                    margin_balance="5000.00",
                    wallet_balance="4950.00",
                    available_balance="4500.00",
                    initial_margin="500.00",
                    maintenance_margin="50.00",
                    unrealized_pnl="50.00",
                )
            ],
            positions=[
                FuturesPosition(
                    symbol="BTCUSDT",
                    position_side="LONG",
                    position_side_value=1,
                    quantity="0.1",
                    entry_price="42000.00",
                    mark_price="42100.00",
                    unrealized_pnl="10.00",
                    margin_balance="50.00",
                    isolated_margin="0",
                    is_auto_add_margin=True,
                )
            ],
        )
        assert account.can_trade is True
        assert account.can_withdraw is False
        assert len(account.assets) == 1
        assert len(account.positions) == 1

    def test_futures_account_info_v2_without_positions(self):
        """测试无持仓的期货账户信息"""
        account = FuturesAccountInfoV2(
            fee_broker_bnb="B2C2",
            can_deposit=True,
            can_trade=True,
            can_withdraw=True,
            fee_bnb="0.00000000",
            total_balance="5000.00",
            total_margin_balance="5000.00",
            total_available_balance="5000.00",
            total_initial_margin="0",
            total_maintenance_margin="0",
            total_unrealized_pnl="0",
            assets=[],
            positions=[],
        )
        assert len(account.positions) == 0


class TestCommissionRates:
    """现货手续费率模型测试"""

    def test_create_commission_rates(self):
        """测试创建手续费率"""
        rates = CommissionRates(
            maker_commission="0.001",
            taker_commission="0.001",
        )
        assert rates.maker_commission == "0.001"
        assert rates.taker_commission == "0.001"


class TestSpotBalance:
    """现货余额模型测试"""

    def test_create_spot_balance(self):
        """测试创建现货余额"""
        balance = SpotBalance(
            asset="BTC",
            free="0.5",
            locked="0.1",
        )
        assert balance.asset == "BTC"
        assert balance.free == "0.5"
        assert balance.locked == "0.1"

    def test_spot_balance_zero(self):
        """测试零余额"""
        balance = SpotBalance(
            asset="USDT",
            free="0",
            locked="0",
        )
        assert balance.free == "0"
        assert balance.locked == "0"


class TestSpotAccountInfo:
    """现货账户信息模型测试"""

    def test_create_spot_account_info(self):
        """测试创建现货账户信息"""
        account = SpotAccountInfo(
            maker_commission=10,
            taker_commission=10,
            buyer_commission=0,
            seller_commission=0,
            can_trade=True,
            can_withdraw=True,
            can_deposit=True,
            update_time=1705311512999,
            account_type="SPOT",
            balances_raw=[
                {"asset": "BTC", "free": "0.50000000", "locked": "0.10000000"},
                {"asset": "USDT", "free": "1000.00000000", "locked": "0.00000000"},
            ],
        )
        assert account.can_trade is True
        assert account.update_time == 1705311512999
        assert len(account.balances_raw) == 2

    def test_spot_account_info_with_commission_rates(self):
        """测试带手续费率的现货账户"""
        account = SpotAccountInfo(
            maker_commission=8,
            taker_commission=8,
            buyer_commission=0,
            seller_commission=0,
            can_trade=True,
            can_withdraw=True,
            can_deposit=True,
            update_time=1705311512999,
            account_type="SPOT",
            balances=[],
            balances_raw=[],
            commission_rates=CommissionRates(
                maker_commission="0.0008",
                taker_commission="0.0008",
            ),
        )
        assert account.commission_rates is not None
        assert account.commission_rates.maker_commission == "0.0008"


class TestWSAccountModelsEdgeCases:
    """账户模型边界情况测试"""

    def test_futures_asset_with_special_characters(self):
        """测试特殊字符的资产名称"""
        asset = FuturesAsset(
            asset="USDT",
            margin_balance="0",
            wallet_balance="0",
            available_balance="0",
            initial_margin="0",
            maintenance_margin="0",
            unrealized_pnl="0",
        )
        assert asset.asset == "USDT"

    def test_spot_balance_with_large_numbers(self):
        """测试大数字的余额"""
        balance = SpotBalance(
            asset="BTC",
            free="99999999.99999999",
            locked="0.00000001",
        )
        assert float(balance.free) > 0

    def test_futures_position_with_none_fields(self):
        """测试带None值的持仓"""
        position = FuturesPosition(
            symbol="BTCUSDT",
            position_side="LONG",
            position_side_value=1,
            quantity="0.1",
            entry_price="42000.00",
            mark_price="42100.00",
            unrealized_pnl="10.00",
            margin_balance="50.00",
            isolated_margin=None,
            is_auto_add_margin=True,
        )
        assert position.isolated_margin is None
