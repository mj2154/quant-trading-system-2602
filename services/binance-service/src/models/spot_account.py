"""
币安现货账户信息数据模型

对应 /api/v3/account API 响应。
字段名严格与币安官方文档一致: https://binance-docs.github.io/apidocs/spot/rest-api/account-endpoints#account-information-user_data
"""

from typing import Optional

from pydantic import BaseModel, Field


class CommissionRates(BaseModel):
    """手续费率详情

    对应 API 返回的 commissionRates 对象
    """

    maker: Optional[str] = Field(None, description="挂单手续费率")
    taker: Optional[str] = Field(None, description="吃单手续费率")
    buyer: Optional[str] = Field(None, description="买入手续费率")
    seller: Optional[str] = Field(None, description="卖出手续费率")


class Balance(BaseModel):
    """余额信息

    对应 API 返回的 balances 数组元素
    """

    asset: str = Field(..., description="资产名称")
    free: Optional[str] = Field(None, description="可用数量")
    locked: Optional[str] = Field(None, description="锁定数量")


class SpotAccountInfo(BaseModel):
    """现货账户信息

    对应 /api/v3/account API 响应。
    使用 alias 解析 API 返回的驼峰命名，
    model_dump() 默认输出蛇形命名（与前端约定一致）。
    """

    # 手续费相关 (alias 用于解析 API 返回数据)
    maker_commission: Optional[int | str] = Field(None, alias="makerCommission", description="挂单手续费率")
    taker_commission: Optional[int | str] = Field(None, alias="takerCommission", description="吃单手续费率")
    buyer_commission: Optional[int | str] = Field(None, alias="buyerCommission", description="买入手续费率")
    seller_commission: Optional[int | str] = Field(None, alias="sellerCommission", description="卖出手续费率")
    commission_rates: Optional[CommissionRates] = Field(None, alias="commissionRates", description="手续费率详情")

    # 交易权限
    can_trade: Optional[bool] = Field(None, alias="canTrade", description="是否可交易")
    can_withdraw: Optional[bool] = Field(None, alias="canWithdraw", description="是否可提现")
    can_deposit: Optional[bool] = Field(None, alias="canDeposit", description="是否可充值")

    # 账户属性
    brokered: Optional[bool] = Field(None, description="是否经纪商")
    require_self_trade_prevention: Optional[bool] = Field(None, alias="requireSelfTradePrevention", description="是否需要自成交预防")
    prevent_sor: Optional[bool] = Field(None, alias="preventSor", description="是否阻止SOR订单")

    # 时间与类型
    update_time: Optional[int] = Field(None, alias="updateTime", description="最后更新时间戳")
    account_type: str = Field(..., alias="accountType", description="账户类型")

    # 余额与权限
    balances: list[Balance] = Field(default_factory=list, description="余额列表")
    permissions: Optional[list[str]] = Field(None, description="账户权限列表")
    uid: Optional[int] = Field(None, description="用户ID")

    model_config = {
        "populate_by_name": True,
    }
